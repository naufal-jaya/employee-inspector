"""Unit tests for the compliance rule engine (no models required)."""

from compliance.rules import analyze_compliance
from model.detector import Detection


def _person(x1=0, y1=0, x2=100, y2=200):
    return Detection("Person", 0.9, [x1, y1, x2, y2])


def _ppe(name, x1=10, y1=10, x2=40, y2=40):
    return Detection(name, 0.8, [x1, y1, x2, y2])


def test_no_persons_returns_empty():
    assert analyze_compliance([_ppe("Hardhat")]) == []


def test_fully_compliant_is_low_risk():
    result = analyze_compliance([
        _person(),
        _ppe("Hardhat"),
        _ppe("Safety Vest"),
        _ppe("Mask"),
    ])[0]
    assert result["compliance_status"] == "Compliant"
    assert result["missing_ppe"] == []
    assert result["risk_level"] == "Low"


def test_negative_wins_over_positive():
    result = analyze_compliance([
        _person(),
        _ppe("Hardhat"),
        _ppe("NO-Hardhat"),
    ])[0]
    assert result["missing_ppe"] == ["Hardhat"]
    assert result["detected_ppe"] == []
    assert result["compliance_status"] == "Non-compliant"
    assert result["risk_level"] == "High"


def test_critical_item_without_evidence_is_missing():
    result = analyze_compliance([_person()])[0]
    assert result["missing_ppe"] == ["Hardhat"]
    assert result["compliance_status"] == "Non-compliant"
    assert result["risk_level"] == "High"


def test_non_critical_item_stays_neutral_without_evidence():
    result = analyze_compliance([
        _person(),
        _ppe("Safety Vest"),
    ])[0]
    assert result["detected_ppe"] == ["Safety Vest"]
    assert "Mask" not in result["missing_ppe"]
    assert result["missing_ppe"] == ["Hardhat"]  # critical only
    assert result["risk_level"] == "High"


def test_single_non_critical_missing_is_medium_risk():
    result = analyze_compliance([
        _person(),
        _ppe("Hardhat"),
        _ppe("NO-Safety Vest"),
    ])[0]
    assert result["missing_ppe"] == ["Safety Vest"]
    assert result["compliance_status"] == "Non-compliant"
    assert result["risk_level"] == "Medium"


def test_two_missing_items_is_high_risk():
    result = analyze_compliance([
        _person(),
        _ppe("NO-Mask"),
        _ppe("NO-Safety Vest"),
    ])[0]
    assert set(result["missing_ppe"]) == {"Hardhat", "Mask", "Safety Vest"}
    assert result["risk_level"] == "High"


def test_ppe_outside_all_person_boxes_is_ignored():
    result = analyze_compliance([
        _person(),
        _ppe("Hardhat", x1=500, y1=500, x2=600, y2=600),
    ])[0]
    assert result["missing_ppe"] == ["Hardhat"]
    assert result["detected_ppe"] == []


def test_person_ids_are_sequential():
    results = analyze_compliance([_person(x2=100), _person(x1=200, x2=300)])
    assert [r["person_id"] for r in results] == [1, 2]


def test_recommendation_mentions_person_id():
    result = analyze_compliance([_person()])[0]
    assert "Pegawai #1" in result["recommendation"]
