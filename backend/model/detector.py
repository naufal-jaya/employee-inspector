"""
PPE Detector
------------
Thin wrapper around a fine-tuned YOLOv8 model plus a YOLOv8-pose person model.
Loads weights once at startup and exposes a single synchronous `predict()` call,
matching the MVP constraint: one request in, one inference pass, one response out.

The person model is a COCO pose model (17 keypoints) so compliance rules can
verify that PPE is actually *worn* on the correct body region rather than
merely carried. A pose-based fall detector also runs on each person.
"""

import os
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from ultralytics import YOLO

# COCO pose keypoint indices
KPT_NOSE = 0
KPT_LEFT_EYE = 1
KPT_RIGHT_EYE = 2
KPT_LEFT_EAR = 3
KPT_RIGHT_EAR = 4
KPT_LEFT_SHOULDER = 5
KPT_RIGHT_SHOULDER = 6
KPT_LEFT_HIP = 11
KPT_RIGHT_HIP = 12

HEAD_KPTS = (KPT_NOSE, KPT_LEFT_EYE, KPT_RIGHT_EYE, KPT_LEFT_EAR, KPT_RIGHT_EAR)
TORSO_KPTS = (KPT_LEFT_SHOULDER, KPT_RIGHT_SHOULDER, KPT_LEFT_HIP, KPT_RIGHT_HIP)

# Confidence a keypoint must reach to be used for pose verification.
KEYPOINT_CONF_THRESHOLD = 0.5
# Fall detection: shoulder->hip vector must be this much wider than tall.
FALL_HORIZONTAL_RATIO = 1.5
# Minimum length (px) of the shoulder->hip vector for a fall to be considered.
FALL_MIN_LENGTH_PX = 40.0


@dataclass
class Detection:
    class_name: str
    confidence: float
    bbox: List[float]  # [x1, y1, x2, y2] in pixel coordinates
    track_id: int = -1  # -1 means no tracking (image mode); set for video mode
    keypoints: Optional[np.ndarray] = None  # shape (17, 2) pixel coords or None
    keypoint_conf: Optional[np.ndarray] = None  # shape (17,) or None


def _bbox_height(bbox: List[float]) -> float:
    return float(bbox[3] - bbox[1])


def _point_confident(keypoint_conf: Optional[np.ndarray], kpt_idx: int) -> bool:
    if keypoint_conf is None or keypoint_conf.size <= kpt_idx:
        return False
    return bool(keypoint_conf[kpt_idx] >= KEYPOINT_CONF_THRESHOLD)


def _region_center(
    keypoints: Optional[np.ndarray],
    keypoint_conf: Optional[np.ndarray],
    kpt_indices: tuple,
) -> Optional[np.ndarray]:
    """Mean of confident keypoints for a body region, or None if none are confident."""
    if keypoints is None or keypoint_conf is None:
        return None
    pts = [
        keypoints[i]
        for i in kpt_indices
        if _point_confident(keypoint_conf, i) and not np.allclose(keypoints[i], 0.0)
    ]
    if not pts:
        return None
    return np.mean(np.array(pts), axis=0)


def is_fallen(
    keypoints: Optional[np.ndarray],
    keypoint_conf: Optional[np.ndarray],
    bbox: List[float],
) -> tuple:
    """
    Pose-based fall detection.

    A person is considered fallen when the shoulder-center -> hip-center vector
    is predominantly horizontal AND its length is above a minimum. Using the
    limb vector (rather than box aspect ratio) avoids false positives from
    standing workers with arms spread.

    Returns (is_fallen: bool, confidence: float).
    """
    shoulder = _region_center(keypoints, keypoint_conf, (KPT_LEFT_SHOULDER, KPT_RIGHT_SHOULDER))
    hip = _region_center(keypoints, keypoint_conf, (KPT_LEFT_HIP, KPT_RIGHT_HIP))
    if shoulder is None or hip is None:
        return False, 0.0

    dx = float(shoulder[0] - hip[0])
    dy = float(shoulder[1] - hip[1])
    length = float(np.hypot(dx, dy))

    used = [i for i in (KPT_LEFT_SHOULDER, KPT_RIGHT_SHOULDER, KPT_LEFT_HIP, KPT_RIGHT_HIP) if _point_confident(keypoint_conf, i)]
    conf = np.mean([keypoint_conf[i] for i in used]) if used else 0.0

    if length < FALL_MIN_LENGTH_PX:
        return False, conf

    # Horizontal dominance: |dx| > ratio * |dy|
    if abs(dx) > FALL_HORIZONTAL_RATIO * abs(dy):
        return True, conf
    return False, conf


class PPEDetector:
    def __init__(self, ppe_weights_path: str, pose_weights_path: str, confidence_threshold: float = 0.5):
        if not os.path.exists(ppe_weights_path):
            raise FileNotFoundError(f"PPE model weights not found at '{ppe_weights_path}'.")
        if not os.path.exists(pose_weights_path):
            raise FileNotFoundError(f"Pose model weights not found at '{pose_weights_path}'.")

        self.ppe_model = YOLO(ppe_weights_path)
        self.person_model = YOLO(pose_weights_path)
        self.confidence_threshold = confidence_threshold
        self.ppe_class_names = self.ppe_model.names  # dict[int, str]

    @staticmethod
    def _extract_keypoints(result, index: int):
        """Return (xy (17,2), conf (17,)) for a single detection, or (None, None)."""
        kpts = result.keypoints
        if kpts is None or kpts.xy is None or len(kpts.xy) <= index:
            return None, None
        xy = kpts.xy[index].cpu().numpy()
        conf = kpts.conf[index].cpu().numpy() if kpts.conf is not None else np.zeros(len(xy))
        return xy, conf

    def predict(self, image: np.ndarray) -> List[Detection]:
        """
        Run one synchronous inference pass on a single image (H, W, 3 - BGR or RGB).
        Returns a flat list of Detection objects (persons + PPE + hazards).
        """
        # 1. Detect Persons + keypoints using the COCO pose model
        person_results = self.person_model.predict(
            source=image,
            conf=self.confidence_threshold,
            classes=[0],
            verbose=False,
        )

        # 2. Detect PPE using the fine-tuned model
        ppe_results = self.ppe_model.predict(
            source=image,
            conf=self.confidence_threshold,
            imgsz=1088,
            verbose=False,
        )

        detections: List[Detection] = []
        persons: List[Detection] = []

        # Extract Person detections with keypoints
        if person_results:
            for i, box in enumerate(person_results[0].boxes):
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                xy, kconf = self._extract_keypoints(person_results[0], i)
                det = Detection(
                    class_name="Person",
                    confidence=conf,
                    bbox=[x1, y1, x2, y2],
                    keypoints=xy,
                    keypoint_conf=kconf,
                )
                detections.append(det)
                persons.append(det)

        # 3. Extract PPE detections (ignoring Person if it happens to predict it)
        if ppe_results:
            for box in ppe_results[0].boxes:
                cls_id = int(box.cls[0])
                class_name = self.ppe_class_names[cls_id]
                if class_name == "Person":
                    continue  # Ignore fine-tuned person detections, rely on pose model
                conf = float(box.conf[0])
                
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                detections.append(Detection(class_name=class_name, confidence=conf, bbox=[x1, y1, x2, y2]))

        # 4. Pose-based fall detection for each person
        for p in persons:
            fallen, conf = is_fallen(p.keypoints, p.keypoint_conf, p.bbox)
            if fallen:
                detections.append(Detection(class_name="Fall-Detected", confidence=conf, bbox=p.bbox))

        return detections

    def predict_tracked(self, image: np.ndarray) -> List[Detection]:
        """
        Like predict(), but uses YOLO's built-in tracker on the person model
        so each person gets a stable `track_id` across video frames.
        Only use this for video; the tracker holds state between calls.
        Call `person_model.predictor.trackers[0].reset()` to reset state
        between separate videos.
        """
        # Track all classes using the custom ByteTrack config tuned for workplace stability.
        _tracker_cfg = os.path.join(os.path.dirname(__file__), "bytetrack_workplace.yaml")
        
        # Track persons with pose model for keypoints + stable IDs
        person_results = self.person_model.track(
            source=image,
            conf=self.confidence_threshold,
            classes=[0],
            persist=True,
            verbose=False,
            tracker=_tracker_cfg,
        )

        # Detect PPE with the fine-tuned model (no tracking needed for PPE items)
        ppe_results = self.ppe_model.predict(
            source=image,
            conf=self.confidence_threshold,
            imgsz=1088,
            verbose=False,
        )

        detections: List[Detection] = []
        persons: List[Detection] = []

        # Extract tracked Person detections with keypoints
        if person_results and person_results[0].boxes is not None:
            boxes = person_results[0].boxes
            for i, box in enumerate(boxes):
                conf = float(box.conf[0])
                    
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                tid = int(box.id[0]) if box.id is not None else (i + 1)
                xy, kconf = self._extract_keypoints(person_results[0], i)
                det = Detection(
                    class_name="Person",
                    confidence=conf,
                    bbox=[x1, y1, x2, y2],
                    track_id=tid,
                    keypoints=xy,
                    keypoint_conf=kconf,
                )
                detections.append(det)
                persons.append(det)

        # Extract PPE detections
        if ppe_results and ppe_results[0].boxes is not None:
            for box in ppe_results[0].boxes:
                cls_id = int(box.cls[0])
                class_name = self.ppe_class_names[cls_id]
                if class_name == "Person":
                    continue
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                detections.append(Detection(class_name=class_name, confidence=conf, bbox=[x1, y1, x2, y2]))

        # 4. Pose-based fall detection for each tracked person
        for p in persons:
            fallen, conf = is_fallen(p.keypoints, p.keypoint_conf, p.bbox)
            if fallen:
                detections.append(Detection(class_name="Fall-Detected", confidence=conf, bbox=p.bbox))

        return detections
