"""
Economic Risk Scoring
---------------------
Deterministic, rule-based risk score (0-100) that summarizes compliance
detections. Kept deliberately minimal: only the risk score is exposed; the
illustrative IDR loss/savings estimates were removed because raw rupiah
figures could be mistaken for precise claims.

All outputs are pure functions of the detection results: the same input always
produces the same score.
"""

from typing import Dict, List

# Risk-score deductions
RISK_LEVEL_DEDUCTION = {"Low": 0, "Medium": 15, "High": 30}
HAZARD_DEDUCTION = 25


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def economic_impact(compliance_results: List[Dict], hazards: List[Dict]) -> Dict:
    """
    Compute a deterministic risk score (0-100; 100 = fully safe).

    Args:
        compliance_results: output of analyze_compliance()
        hazards: list of hazard dicts (class_name, bbox, confidence)

    Returns:
        { "risk_score": float 0-100 }
    """
    person_deduction = 0.0
    for r in compliance_results:
        if r.get("compliance_status") == "Non-compliant":
            person_deduction += RISK_LEVEL_DEDUCTION.get(r.get("risk_level"), 0)

    hazard_deduction = HAZARD_DEDUCTION * len(hazards)
    risk_score = _clamp(100.0 - person_deduction - hazard_deduction)

    return {"risk_score": round(risk_score, 1)}
