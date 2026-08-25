"""
Compliance Rule Engine
----------------------
Takes raw YOLO detections (Person + PPE classes) for a SINGLE frame and
turns them into per-person compliance decisions. This is deliberately
rule-based (not a second neural net) to keep the MVP inference path
simple, fast, deterministic, and easy to justify to judges.

Pose-aware verification: each PPE item is checked against the person's
COCO keypoints to decide whether it is actually WORN on the correct body
region, CARRIED (present but not worn), or UNCERTAIN (pose data unreliable).
An `uncertain` outcome never adds a violation on its own — it falls back to
the legacy presence-based deduction so we do not falsely accuse a worker.
"""

from typing import List, Dict

import numpy as np

from model.detector import Detection

# ---------------------------------------------------------------------------
# PPE schema: maps a required "positive" (compliant) class to its "negative"
# (violation) counterpart. Keys are the required PPE inventory used for
# implicit deduction. Swap this dict when you retrain on a new PPE class set.
# ---------------------------------------------------------------------------
PPE_SCHEMA = {
    "Hardhat": "NO-Hardhat",
    "Safety Vest": "NO-Safety Vest",
}

# Body region each PPE class must be worn on (pose verification).
PPE_BODY_REGION = {
    "Hardhat": "head",
    "Safety Vest": "torso",
}

# Detections that are hazards, not PPE — never associated to a person.
HAZARD_CLASSES = set()

# How much missing PPE matters. Used for risk scoring only.
CRITICAL_ITEMS = {"Hardhat"}  # missing this alone already pushes risk to High

PERSON_CLASS = "Person"
ASSOCIATION_MARGIN_PX = 80  # tolerance when checking if a PPE box "belongs" to a person
# Distance (as a fraction of the person box height) inside which a PPE item
# counts as worn on its body region.
VERIFY_MARGIN_RATIO = 0.40


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
    candidates = []
    item_cx, item_cy = _center(item.bbox)
    for p in persons:
        w = p.bbox[2] - p.bbox[0]
        h = p.bbox[3] - p.bbox[1]
        # Use a dynamic margin: 20% of person's width/height
        margin_x = w * 0.2
        margin_y = h * 0.2
        
        if (p.bbox[0] - margin_x) <= item_cx <= (p.bbox[2] + margin_x) and \
           (p.bbox[1] - margin_y) <= item_cy <= (p.bbox[3] + margin_y):
            candidates.append(p)
            
    if not candidates:
        return None
        
    # If multiple candidates overlap, pick the one whose center is closest 
    # to the PPE center, NORMALIZED by the person's dimensions.
    # This prevents a background person (whose center might be absolutely 
    # closer to a tall foreground person's head) from stealing the PPE.
    def normalized_dist(p):
        pcx, pcy = _center(p.bbox)
        w = max(1, p.bbox[2] - p.bbox[0])
        h = max(1, p.bbox[3] - p.bbox[1])
        return ((pcx - item_cx) / w)**2 + ((pcy - item_cy) / h)**2
        
    return min(candidates, key=normalized_dist)


def _verify_ppe_worn(item: Detection, person: Detection) -> str:
    """
    Spatial verification of a single PPE item against a person.

    Returns one of:
      - "worn":      item is on the correct body region (vertical bounding box overlap)
      - "carried":   item belongs to person but is not worn properly
    """
    region = PPE_BODY_REGION.get(item.class_name)
    if region is None:
        return "worn"  # item not in schema -> no verification needed

    person_height = person.bbox[3] - person.bbox[1]
    item_cy = (item.bbox[1] + item.bbox[3]) / 2  # vertical center of PPE

    if region == "head":
        # Head zone = top 35 % of the person bounding box
        head_bottom = person.bbox[1] + person_height * 0.35
        if item_cy <= head_bottom:
            return "worn"
    elif region == "torso":
        # Torso zone = from 15 % to 70 % of the person bounding box
        torso_top = person.bbox[1] + person_height * 0.15
        torso_bottom = person.bbox[1] + person_height * 0.70
        if torso_top <= item_cy <= torso_bottom:
            return "worn"

    # If it didn't match the zones, assume carried
    return "carried"


def _risk_level(missing_ppe: set) -> str:
    if not missing_ppe:
        return "Low"
    if missing_ppe & CRITICAL_ITEMS or len(missing_ppe) >= 2:
        return "High"
    return "Medium"


def _recommendation(person_idx: int, missing_ppe: set, carried_ppe: set) -> str:
    if not missing_ppe:
        return f"Pegawai #{person_idx}: APD lengkap, sesuai SOP."
    items = ", ".join(sorted(missing_ppe))
    if carried_ppe:
        items += f" (dibawa tapi tidak dipakai: {', '.join(sorted(carried_ppe))})"
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
        "track_id": -1,
        "person_bbox": [...],
        "person_confidence": 0.95,
        "detected_ppe": ["Hardhat", "Safety Vest"],
        "worn_ppe": ["Hardhat"],
        "carried_ppe": ["Safety Vest"],
        "missing_ppe": [],
        "compliance_status": "Non-compliant",
        "risk_level": "High",
        "verification": "carried",
        "recommendation": "..."
      },
      ...
    ]
    """
    persons = [d for d in detections if d.class_name == PERSON_CLASS]
    ppe_items = [
        d for d in detections
        if d.class_name != PERSON_CLASS and d.class_name not in HAZARD_CLASSES
    ]

    # init empty bucket per person
    buckets = {
        id(p): {"person": p, "worn": set(), "carried": set(), "uncertain": set(), "missing": set()}
        for p in persons
    }

    for item in ppe_items:
        matched_person = _best_matching_person(item, persons)
        if matched_person is None:
            continue  # PPE item not clearly tied to any detected person, ignore for MVP

        bucket = buckets[id(matched_person)]

        # negative class (e.g. "NO-Hardhat") -> explicit violation
        matched_negative = None
        for positive, negative in PPE_SCHEMA.items():
            if item.class_name == negative:
                matched_negative = positive
                break
        if matched_negative is not None:
            bucket["missing"].add(matched_negative)
            continue

        # positive class -> verify worn vs carried vs uncertain
        verification = _verify_ppe_worn(item, matched_person)
        if verification == "worn":
            bucket["worn"].add(item.class_name)
        elif verification == "carried":
            bucket["carried"].add(item.class_name)
        else:
            bucket["uncertain"].add(item.class_name)

    # IMPLICIT DEDUCTION
    # Required PPE that is neither worn nor uncertain-present is missing.
    # Carried items are treated as missing (a violation) but also tracked.
    for _, bucket in buckets.items():
        present = bucket["worn"] | bucket["uncertain"]
        for required_ppe in PPE_SCHEMA.keys():
            if required_ppe not in present:
                bucket["missing"].add(required_ppe)
        
        # Conflict resolution: if YOLO predicted BOTH 'Hardhat' and 'NO-Hardhat' 
        # (common since per-class NMS allows overlapping boxes of different classes),
        # the positive 'worn' presence takes precedence over the explicit negative.
        bucket["missing"] = bucket["missing"] - present

    results = []
    for idx, (_, bucket) in enumerate(buckets.items(), start=1):
        missing = bucket["missing"]
        carried = bucket["carried"]

        if carried:
            verification = "carried"
        elif bucket["uncertain"]:
            verification = "uncertain"
        elif bucket["worn"]:
            verification = "worn"
        else:
            verification = "uncertain"

        results.append({
            "person_id": idx,
            "track_id": getattr(bucket["person"], "track_id", -1),
            "person_bbox": bucket["person"].bbox,
            "person_confidence": bucket["person"].confidence,
            "detected_ppe": sorted(bucket["worn"] | bucket["uncertain"]),
            "worn_ppe": sorted(bucket["worn"]),
            "carried_ppe": sorted(carried),
            "missing_ppe": sorted(missing),
            "compliance_status": "Non-compliant" if missing else "Compliant",
            "risk_level": _risk_level(missing),
            "verification": verification,
            "recommendation": _recommendation(idx, missing, carried),
        })
    return results