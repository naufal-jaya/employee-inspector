"""Unit tests for the economic risk score module."""

from compliance.economics import economic_impact


def _person_result(risk_level, compliant=False):
    return {
        "compliance_status": "Compliant" if compliant else "Non-compliant",
        "risk_level": risk_level,
        "missing_ppe": [] if compliant else ["Hardhat"],
        "carried_ppe": [],
    }


def test_clean_scene_scores_100():
    econ = economic_impact([_person_result("Low", compliant=True)], [])
    assert econ["risk_score"] == 100.0


def test_high_risk_lowers_score():
    econ = economic_impact([_person_result("High")], [])
    assert econ["risk_score"] == 70.0  # 100 - 30


def test_hazards_deduct_from_score():
    hazard = {"class_name": "Fall-Detected", "bbox": [0, 0, 10, 10], "confidence": 0.9}
    econ = economic_impact([_person_result("Medium")], [hazard])
    assert econ["risk_score"] == 60.0  # 100 - 15 - 25
