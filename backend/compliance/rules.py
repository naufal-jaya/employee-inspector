"""
Compliance Rule Engine
----------------------
Takes raw YOLO detections (Person + PPE classes) for a SINGLE frame and
turns them into per-person compliance decisions. This is deliberately
rule-based (not a second neural net) to keep the MVP inference path
simple, fast, deterministic, and easy to justify to judges.

Assumes a dataset/class schema similar to the public "Construction Site
Safety Image Dataset" (Roboflow), i.e. classes include:
    Person, Hardhat, NO-Hardhat, Safety Vest, NO-Safety Vest, Mask, NO-Mask

If you fine-tune on a different PPE set (e.g. hairnet/apron for a
kitchen/MBG context), only PPE_SCHEMA below needs to change — the
association + scoring logic stays the same.
"""

from typing import List, Dict
from model.detector import Detection

# ---------------------------------------------------------------------------
# PPE schema: maps a "positive" (compliant) class to its "negative"
# (violation) counterpart. Swap this dict when you retrain on a new
# PPE class set (e.g. dapur MBG: Hairnet/NO-Hairnet, Apron/NO-Apron, ...).
# ---------------------------------------------------------------------------
PPE_SCHEMA = {
    "Hardhat": "NO-Hardhat",
    "Safety Vest": "NO-Safety Vest",
    "Mask": "NO-Mask",
    "Gloves": "NO-Gloves",
    "Goggles": "NO-Goggles",
}

# How much missing PPE matters. Used for risk scoring only.
CRITICAL_ITEMS = {"Hardhat"}  # missing this alone already pushes risk to High

PERSON_CLASS = "Person"
ASSOCIATION_MARGIN_PX = 15  # tolerance when checking if a PPE box "belongs" to a person


def _center(bbox: List[float]):
    x1, y1, x2, y2 = bbox
    return (x1 + x2) / 2, (y1 + y2) / 2


def _point_in_box(point, bbox: List[float], margin: float = 0.0) -> bool:
    x, y = point
    x1, y1, x2, y2 = bbox
    return (x1 - margin) <= x <= (x2 + margin) and (y1 - margin) <= y <= (y2 + margin)


def _best_matching_person(item: Detection, persons: List[Detection]):
    """A PPE detection can only belong to the person whose box actually
    contains its center point. If several match (crowded frame), pick the
    smallest person box (tightest/most specific match)."""
    candidates = [
        p for p in persons
        if _point_in_box(_center(item.bbox), p.bbox, margin=ASSOCIATION_MARGIN_PX)
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda p: (p.bbox[2] - p.bbox[0]) * (p.bbox[3] - p.bbox[1]))


def _risk_level(missing_ppe: set) -> str:
    if not missing_ppe:
        return "Low"
    if missing_ppe & CRITICAL_ITEMS or len(missing_ppe) >= 2:
        return "High"
    return "Medium"


def _recommendation(person_idx: int, missing_ppe: set) -> str:
    if not missing_ppe:
        return f"Pegawai #{person_idx}: APD lengkap, sesuai SOP."
    items = ", ".join(sorted(missing_ppe))
    return (
        f"Pegawai #{person_idx}: tidak menggunakan {items}. "
        f"Segera tegur dan hentikan aktivitas sebelum kontak dengan area kerja."
    )


def analyze_compliance(detections: List[Detection]) -> List[Dict]:
    """
    Main entry point. Returns a list of per-person compliance records:
    [
      {
        "person_id": 1,
        "detected_ppe": ["Hardhat", "Safety Vest"],
        "missing_ppe": ["Mask"],
        "compliance_status": "Non-compliant",
        "risk_level": "Medium",
        "recommendation": "..."
      },
      ...
    ]
    """
    persons = [d for d in detections if d.class_name == PERSON_CLASS]
    ppe_items = [d for d in detections if d.class_name != PERSON_CLASS]

    # init empty bucket per person
    buckets = {id(p): {"person": p, "detected": set(), "missing": set()} for p in persons}

    for item in ppe_items:
        matched_person = _best_matching_person(item, persons)
        if matched_person is None:
            continue  # PPE item not clearly tied to any detected person, ignore for MVP

        bucket = buckets[id(matched_person)]
        # positive class (e.g. "Hardhat")
        if item.class_name in PPE_SCHEMA:
            bucket["detected"].add(item.class_name)
        # negative class (e.g. "NO-Hardhat") -> strip prefix for readability
        else:
            for positive, negative in PPE_SCHEMA.items():
                if item.class_name == negative:
                    bucket["missing"].add(positive)

    # IMPLICIT DEDUCTION
    # Bypass the model's inability to detect 'NO-*' classes.
    # If a required PPE item is not found in the person's detected bucket,
    # we automatically flag it as missing.
    for _, bucket in buckets.items():
        for required_ppe in PPE_SCHEMA.keys():
            if required_ppe not in bucket["detected"]:
                bucket["missing"].add(required_ppe)

    results = []
    for idx, (_, bucket) in enumerate(buckets.items(), start=1):
        missing = bucket["missing"]
        results.append({
            "person_id": idx,
            "person_bbox": bucket["person"].bbox,
            "detected_ppe": sorted(bucket["detected"]),
            "missing_ppe": sorted(missing),
            "compliance_status": "Non-compliant" if missing else "Compliant",
            "risk_level": _risk_level(missing),
            "recommendation": _recommendation(idx, missing),
        })
    return results
