"""
PPE Detector
------------
Thin wrapper around a fine-tuned YOLOv8 model. Loads weights once at
startup and exposes a single synchronous `predict()` call, matching the
MVP constraint: one request in, one inference pass, one response out.
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
    def __init__(self, ppe_weights_path: str, confidence_threshold: float = 0.4):
        if not os.path.exists(ppe_weights_path):
            raise FileNotFoundError(f"PPE model weights not found at '{ppe_weights_path}'.")
            
        self.ppe_model = YOLO(ppe_weights_path)
        self.confidence_threshold = confidence_threshold
        # Lower threshold for Person — recovers recall on PPE-context images immediately
        self.person_conf_threshold = 0.15
        self.ppe_class_names = self.ppe_model.names  # dict[int, str]

    def predict(self, image: np.ndarray) -> List[Detection]:
        """
        Run one synchronous inference pass on a single image (H, W, 3 - BGR or RGB).
        Returns a flat list of Detection objects.
        """
        # Run prediction with the lowest required threshold so we get all potential boxes
        min_conf = min(self.confidence_threshold, self.person_conf_threshold)
        results = self.ppe_model.predict(
            source=image,
            conf=min_conf,
            verbose=False,
        )

        detections: List[Detection] = []
        
        if results and results[0].boxes is not None:
            for box in results[0].boxes:
                cls_id = int(box.cls[0])
                class_name = self.ppe_class_names[cls_id]
                conf = float(box.conf[0])
                
                # Apply class-specific confidence thresholds
                req_conf = self.person_conf_threshold if class_name == "Person" else self.confidence_threshold
                if conf < req_conf:
                    continue

                x1, y1, x2, y2 = box.xyxy[0].tolist()
                detections.append(Detection(class_name=class_name, confidence=conf, bbox=[x1, y1, x2, y2]))

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
        min_conf = min(self.confidence_threshold, self.person_conf_threshold)
        
        results = self.ppe_model.track(
            source=image,
            conf=min_conf,
            persist=True,
            verbose=False,
            tracker=_tracker_cfg,
        )

        detections: List[Detection] = []

        if results and results[0].boxes is not None:
            boxes = results[0].boxes
            for i, box in enumerate(boxes):
                cls_id = int(box.cls[0])
                class_name = self.ppe_class_names[cls_id]
                conf = float(box.conf[0])
                
                # Apply class-specific confidence thresholds
                req_conf = self.person_conf_threshold if class_name == "Person" else self.confidence_threshold
                if conf < req_conf:
                    continue
                    
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                tid = int(box.id[0]) if box.id is not None else (i + 1)
                detections.append(Detection(
                    class_name=class_name, confidence=conf,
                    bbox=[x1, y1, x2, y2], track_id=tid
                ))

        return detections
