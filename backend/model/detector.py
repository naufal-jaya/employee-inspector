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
    def __init__(self, ppe_weights_path: str, person_weights_path: str, confidence_threshold: float = 0.4):
        if not os.path.exists(ppe_weights_path):
            raise FileNotFoundError(f"PPE model weights not found at '{ppe_weights_path}'.")
        if not os.path.exists(person_weights_path):
            raise FileNotFoundError(f"Person base model weights not found at '{person_weights_path}'.")
            
        self.ppe_model = YOLO(ppe_weights_path)
        self.person_model = YOLO(person_weights_path)
        self.confidence_threshold = confidence_threshold
        self.ppe_class_names = self.ppe_model.names  # dict[int, str]

    def predict(self, image: np.ndarray) -> List[Detection]:
        """
        Run one synchronous inference pass on a single image (H, W, 3 - BGR or RGB).
        Returns a flat list of Detection objects.
        """
        # 1. Detect Persons using the base COCO model (class 0 is Person)
        person_results = self.person_model.predict(
            source=image,
            conf=0.25,  # Lower confidence to ensure we catch everyone
            classes=[0],
            verbose=False,
        )

        # 2. Detect PPE using the fine-tuned model
        ppe_results = self.ppe_model.predict(
            source=image,
            conf=self.confidence_threshold,
            verbose=False,
        )

        detections: List[Detection] = []
        
        # Extract Person detections
        if person_results:
            for box in person_results[0].boxes:
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                detections.append(Detection(class_name="Person", confidence=conf, bbox=[x1, y1, x2, y2]))

        # Extract PPE detections (ignoring Person if it happens to predict it)
        if ppe_results:
            for box in ppe_results[0].boxes:
                cls_id = int(box.cls[0])
                class_name = self.ppe_class_names[cls_id]
                if class_name == "Person":
                    continue  # Ignore fine-tuned person detections, rely on COCO
                conf = float(box.conf[0])
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
        # 1. Track Persons — assigns persistent track IDs across frames
        person_results = self.person_model.track(
            source=image,
            conf=0.25,
            classes=[0],
            persist=True,
            verbose=False,
            tracker="bytetrack.yaml",
        )

        # 2. Detect PPE (no tracking needed, just find what's there)
        ppe_results = self.ppe_model.predict(
            source=image,
            conf=self.confidence_threshold,
            verbose=False,
        )

        detections: List[Detection] = []

        # Extract tracked Person detections
        if person_results and person_results[0].boxes is not None:
            boxes = person_results[0].boxes
            for i, box in enumerate(boxes):
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                # track_id is available only when tracking succeeded
                tid = int(box.id[0]) if box.id is not None else (i + 1)
                detections.append(Detection(
                    class_name="Person", confidence=conf,
                    bbox=[x1, y1, x2, y2], track_id=tid
                ))

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

        return detections
