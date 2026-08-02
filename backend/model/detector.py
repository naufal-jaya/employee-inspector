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


class PPEDetector:
    def __init__(self, weights_path: str, confidence_threshold: float = 0.4):
        if not os.path.exists(weights_path):
            raise FileNotFoundError(
                f"Model weights not found at '{weights_path}'. "
                f"Train the model first (see backend/training/train.py) "
                f"or place your fine-tuned 'best.pt' in backend/model/weights/."
            )
        self.model = YOLO(weights_path)
        self.confidence_threshold = confidence_threshold
        self.class_names = self.model.names  # dict[int, str]

    def predict(self, image: np.ndarray) -> List[Detection]:
        """
        Run one synchronous inference pass on a single image (H, W, 3 - BGR or RGB).
        Returns a flat list of Detection objects.
        """
        results = self.model.predict(
            source=image,
            conf=self.confidence_threshold,
            verbose=False,
        )

        detections: List[Detection] = []
        if not results:
            return detections

        result = results[0]
        for box in result.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            detections.append(
                Detection(
                    class_name=self.class_names[cls_id],
                    confidence=conf,
                    bbox=[x1, y1, x2, y2],
                )
            )
        return detections
