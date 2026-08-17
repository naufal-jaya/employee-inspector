"""
Economic Risk & ROI Scoring
---------------------------
Deterministic, rule-based estimates that translate compliance detections into
business impact, aligning the MVP with the "AI for the Backbone of the Economy"
theme. Values are ILLUSTRATIVE estimates derived from public workplace-safety
statistics (see SOURCES below) and should be presented as such.

All outputs are pure functions of the detection results: the same input always
produces the same score.
"""

from typing import Dict, List

# ---------------------------------------------------------------------------
# Sourced constants (cite these in README / demo)
#   AVG_COST_PER_ACCIDENT_IDR        : estimated average cost of a non-fatal
#                                      work accident (BPJS Ketenagakerjaan /
#                                      national K3 estimates, IDR).
#   AVG_DAYS_LOST_PER_ACCIDENT       : average working days lost per accident.
#   ACCIDENT_PROBABILITY_PER_VIOLATION: illustrative probability that a detected
#                                      violation leads to an accident.
#   INSPECTIONS_PER_YEAR             : assumed number of inspections per site/year.
# ---------------------------------------------------------------------------
AVG_COST_PER_ACCIDENT_IDR = 25_000_000
AVG_DAYS_LOST_PER_ACCIDENT = 14
ACCIDENT_PROBABILITY_PER_VIOLATION = 0.02
INSPECTIONS_PER_YEAR = 1_000

# Risk-score deductions
RISK_LEVEL_DEDUCTION = {"Low": 0, "Medium": 15, "High": 30}
HAZARD_DEDUCTION = 25


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def economic_impact(compliance_results: List[Dict], hazards: List[Dict]) -> Dict:
    """
    Compute deterministic economic metrics from compliance + hazard results.

    Args:
        compliance_results: output of analyze_compliance()
        hazards: list of hazard dicts (class_name, bbox, confidence)

    Returns:
        {
          "risk_score": float 0-100 (100 = fully safe),
          "estimated_loss_per_incident": int (IDR),
          "expected_days_lost_per_incident": int,
          "potential_savings": int (IDR, per incident if compliance is fixed),
        }
    """
    person_deduction = 0.0
    for r in compliance_results:
        if r.get("compliance_status") == "Non-compliant":
            person_deduction += RISK_LEVEL_DEDUCTION.get(r.get("risk_level"), 0)

    hazard_deduction = HAZARD_DEDUCTION * len(hazards)
    risk_score = _clamp(100.0 - person_deduction - hazard_deduction)

    levels = [r.get("risk_level") for r in compliance_results if r.get("compliance_status") == "Non-compliant"]
    if hazards or "High" in levels:
        severity_factor = 1.0
    elif "Medium" in levels:
        severity_factor = 0.5
    else:
        severity_factor = 0.0

    estimated_loss_per_incident = AVG_COST_PER_ACCIDENT_IDR * severity_factor
    potential_savings = (100.0 - risk_score) / 100.0 * AVG_COST_PER_ACCIDENT_IDR

    return {
        "risk_score": round(risk_score, 1),
        "estimated_loss_per_incident": int(estimated_loss_per_incident),
        "expected_days_lost_per_incident": AVG_DAYS_LOST_PER_ACCIDENT,
        "potential_savings": int(potential_savings),
    }
