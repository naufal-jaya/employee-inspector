"""
Unit tests for pose-aware compliance geometry.

Covers the worn / carried / uncertain verification in rules.py and the
fall detection heuristic in detector.py, using synthetic detections so the
tests run without model weights or network access.
"""

import numpy as np
import pytest

from compliance.rules import analyze_compliance
from model.detector import Detection, is_fallen


def _person(keypoint_conf_value=0.9):
    """Person standing; head region around (150, ~126), torso around (150, ~315)."""
    keypoints = np.array([
        [150, 120],   # 0 nose
        [145, 125],   # 1 left eye
        [155, 125],   # 2 right eye
        [135, 130],   # 3 left ear
        [165, 130],   # 4 right ear
        [140, 250],   # 5 left shoulder
        [160, 250],   # 6 right shoulder
        [130, 300],   # 7 left elbow
        [170, 300],   # 8 right elbow
        [120, 350],   # 9 left wrist
        [180, 350],   # 10 right wrist
        [140, 380],   # 11 left hip
        [160, 380],   # 12 right hip
        [140, 430],   # 13 left knee
        [160, 430],   # 14 right knee
        [140, 470],   # 15 left ankle
        [160, 470],   # 16 right ankle
    ], dtype=float)
    conf = np.full(17, keypoint_conf_value)
    return Detection(
        class_name="Person",
        confidence=0.9,
        bbox=[100, 100, 200, 500],
        keypoints=keypoints,
        keypoint_conf=conf,
    )


def test_worn_ppe_is_compliant():
    person = _person()
    hardhat = Detection(class_name="Hardhat", confidence=0.9, bbox=[145, 110, 155, 135])
    vest = Detection(class_name="Safety Vest", confidence=0.9, bbox=[145, 300, 155, 360])

    results = analyze_compliance([person, hardhat, vest])

    assert len(results) == 1
    r = results[0]
    assert r["verification"] == "worn"
    assert r["worn_ppe"] == ["Hardhat", "Safety Vest"]
    assert r["carried_ppe"] == []
    assert r["missing_ppe"] == []
    assert r["compliance_status"] == "Compliant"
    assert r["person_confidence"] == 0.9


def test_carried_ppe_is_violation():
    person = _person()
    # Hardhat far from the head region (down at hand level) -> carried
    hardhat = Detection(class_name="Hardhat", confidence=0.9, bbox=[120, 250, 140, 275])

    results = analyze_compliance([person, hardhat])

    assert len(results) == 1
    r = results[0]
    assert r["verification"] == "carried"
    assert r["carried_ppe"] == ["Hardhat"]
    assert "Hardhat" in r["missing_ppe"]
    assert r["compliance_status"] == "Non-compliant"
    assert r["person_confidence"] == 0.9


def test_uncertain_never_accuses():
    # Pose unreliable (all keypoints low confidence) but both PPE items are detected.
    person = _person(keypoint_conf_value=0.1)
    hardhat = Detection(class_name="Hardhat", confidence=0.9, bbox=[145, 110, 155, 135])
    vest = Detection(class_name="Safety Vest", confidence=0.9, bbox=[145, 300, 155, 360])

    results = analyze_compliance([person, hardhat, vest])

    assert len(results) == 1
    r = results[0]
    assert r["verification"] == "uncertain"
    # The detected PPE is treated as present (fallback), not carried/missing.
    assert r["carried_ppe"] == []
    assert r["worn_ppe"] == []
    assert set(r["detected_ppe"]) == {"Hardhat", "Safety Vest"}
    assert r["missing_ppe"] == []
    assert r["compliance_status"] == "Compliant"
    assert r["person_confidence"] == 0.9


def test_explicit_negative_class_is_violation():
    """NO-Hardhat detection should directly mark Hardhat as missing."""
    person = _person()
    no_hardhat = Detection(class_name="NO-Hardhat", confidence=0.85, bbox=[145, 110, 155, 135])
    vest = Detection(class_name="Safety Vest", confidence=0.9, bbox=[145, 300, 155, 360])

    results = analyze_compliance([person, no_hardhat, vest])

    assert len(results) == 1
    r = results[0]
    assert "Hardhat" in r["missing_ppe"]
    assert r["compliance_status"] == "Non-compliant"
    assert r["risk_level"] == "High"


def test_standing_person_is_not_fallen():
    person = _person()
    fallen, conf = is_fallen(person.keypoints, person.keypoint_conf, person.bbox)
    assert fallen is False


def test_lying_person_is_fallen():
    keypoints = np.zeros((17, 2))
    # Shoulder center around (150, 100); hip center around (200, 100): horizontal.
    keypoints[5] = [140, 95]    # left shoulder
    keypoints[6] = [160, 105]   # right shoulder
    keypoints[11] = [195, 95]   # left hip
    keypoints[12] = [205, 105]  # right hip
    conf = np.full(17, 0.9)
    bbox = [100, 80, 260, 130]  # wide box, lying orientation

    fallen, c = is_fallen(keypoints, conf, bbox)
    assert fallen is True
    assert c > 0.5


def test_fall_requires_confident_keypoints():
    keypoints = np.zeros((17, 2))
    keypoints[5] = [140, 95]
    keypoints[6] = [160, 105]
    keypoints[11] = [195, 95]
    keypoints[12] = [205, 105]
    conf = np.zeros(17)  # no confident keypoints

    fallen, _ = is_fallen(keypoints, conf, [100, 80, 260, 130])
    assert fallen is False