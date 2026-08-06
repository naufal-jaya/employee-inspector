"""Unit tests for the two-model merge logic (no model loading)."""

import numpy as np

from model.detector import PPEDetector, Detection


class _Box:
    def __init__(self, cls_id, conf, xyxy):
        self.cls = [cls_id]
        self.conf = [conf]
        self.xyxy = [xyxy]


class _Result:
    def __init__(self, boxes):
        self.boxes = boxes


class _Model:
    def __init__(self, boxes):
        self._boxes = boxes

    def predict(self, source=None, conf=None, classes=None, verbose=False):
        if classes is not None:
            return [_Result([b for b in self._boxes if b.cls[0] in classes])]
        return [_Result(self._boxes)]


def _make_detector(ppe_boxes, person_boxes):
    det = object.__new__(PPEDetector)
    det.class_names = {0: "Person", 1: "Hardhat", 2: "NO-Hardhat"}
    det.confidence_threshold = 0.4
    det.person_confidence = 0.3
    det.model = _Model(ppe_boxes)
    det.person_model = _Model(person_boxes)
    return det


def _ppe_box(cls_id, conf=0.8, xyxy=(10.0, 10.0, 40.0, 40.0)):
    return _Box(cls_id, conf, np.array(xyxy, dtype=float))


def _person_box(conf=0.9, xyxy=(0.0, 0.0, 100.0, 200.0)):
    return _Box(0, conf, np.array(xyxy, dtype=float))


def test_center_in_box_basic():
    det = _make_detector([], [])
    assert det._center_in_box([0, 0, 10, 10], [0, 0, 100, 200]) is True
    assert det._center_in_box([0, 0, 10, 10], [50, 50, 100, 200]) is False
    assert det._center_in_box([80, 180, 110, 210], [0, 0, 100, 200]) is True  # margin


def test_merge_drops_duplicate_person_box():
    det = _make_detector(
        [_ppe_box(1), _ppe_box(0, xyxy=(0.0, 0.0, 100.0, 200.0))],
        [_person_box()],
    )
    merged = det.predict(np.zeros((300, 300, 3), dtype=np.uint8))
    persons = [d for d in merged if d.class_name == "Person"]
    assert len(persons) == 1
    assert len(merged) == 2  # Hardhat + 1 person


def test_merge_keeps_distinct_person_boxes():
    det = _make_detector(
        [_ppe_box(0, xyxy=(0.0, 0.0, 50.0, 100.0))],
        [_person_box(xyxy=(200.0, 0.0, 300.0, 150.0))],
    )
    merged = det.predict(np.zeros((300, 300, 3), dtype=np.uint8))
    persons = [d for d in merged if d.class_name == "Person"]
    assert len(persons) == 2


def test_merge_without_person_model_keeps_ppe_persons():
    det = _make_detector([_ppe_box(0)], [])
    det.person_model = None
    merged = det.predict(np.zeros((300, 300, 3), dtype=np.uint8))
    assert [d.class_name for d in merged] == ["Person"]


def test_non_person_detections_pass_through_unchanged():
    det = _make_detector([_ppe_box(1), _ppe_box(2, conf=0.6)], [])
    merged = det.predict(np.zeros((300, 300, 3), dtype=np.uint8))
    assert [d.class_name for d in merged] == ["Hardhat", "NO-Hardhat"]
    assert all(d.confidence > 0 for d in merged)
