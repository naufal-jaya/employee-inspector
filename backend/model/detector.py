"""
PPE Detector
------------
Thin wrapper around a fine-tuned YOLOv8 model.
Loads weights once at startup and exposes a single synchronous `predict()` call,
matching the MVP constraint: one request in, one inference pass, one response out.
"""

import os
from dataclasses import dataclass
from typing import List

import numpy as np
from ultralytics import YOLO


@dataclass
class Detection:
    class_name: str
    confidence: float
    bbox: List[float]  # [x1, y1, x2, y2] in pixel coordinates
    track_id: int = -1  # -1 means no tracking (image mode); set for video mode


class PPEDetector:
    def __init__(self, ppe_weights_path: str, confidence_threshold: float = 0.5):
        if not os.path.exists(ppe_weights_path):
            raise FileNotFoundError(f"PPE model weights not found at '{ppe_weights_path}'.")

        self.model = YOLO(ppe_weights_path)
        self.confidence_threshold = confidence_threshold
        self.class_names = self.model.names  # dict[int, str]

    def predict(self, image: np.ndarray) -> List[Detection]:
        """
        Run one synchronous inference pass on a single image (H, W, 3 - BGR or RGB).
        Returns a flat list of Detection objects.
        """
        results = self.model.predict(
            source=image,
            conf=0.40,
            imgsz=1088,
            verbose=False,
        )

        detections: List[Detection] = []
        if results and results[0].boxes is not None:
            for box in results[0].boxes:
                cls_id = int(box.cls[0])
                class_name = self.class_names[cls_id]
                conf = float(box.conf[0])
                
                # Person gets 40% threshold, PPE gets 50% (self.confidence_threshold)
                if class_name != "Person" and conf < self.confidence_threshold:
                    continue
                
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                detections.append(Detection(class_name=class_name, confidence=conf, bbox=[x1, y1, x2, y2]))

        return detections

    def predict_tracked(self, image: np.ndarray) -> List[Detection]:
        """
        Like predict(), but uses YOLO's built-in tracker so objects get a stable
        `track_id` across video frames.
        """
        _tracker_cfg = os.path.join(os.path.dirname(__file__), "bytetrack_workplace.yaml")
        
        results = self.model.track(
            source=image,
            conf=0.40,
            persist=True,
            verbose=False,
            tracker=_tracker_cfg,
        )

        detections: List[Detection] = []
        if results and results[0].boxes is not None:
            for i, box in enumerate(results[0].boxes):
                cls_id = int(box.cls[0])
                class_name = self.class_names[cls_id]
                conf = float(box.conf[0])
                
                # Person gets 40% threshold, PPE gets 50% (self.confidence_threshold)
                if class_name != "Person" and conf < self.confidence_threshold:
                    continue
                
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                tid = int(box.id[0]) if box.id is not None else (i + 1)
                detections.append(Detection(
                    class_name=class_name,
                    confidence=conf,
                    bbox=[x1, y1, x2, y2],
                    track_id=tid
                ))

        return detections
