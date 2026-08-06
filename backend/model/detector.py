"""
PPE Detector
------------
Wrapper around two YOLOv8 models, both loaded once at startup:
  - a fine-tuned PPE model: detects APD/objects (Hardhat, Safety Vest, ...)
  - a COCO-pretrained model: reliably detects the "Person" class
`predict()` is a single synchronous call that merges both outputs, so the
MVP constraint (one request in, one response out) still holds.
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
    def __init__(
        self,
        weights_path: str,
        confidence_threshold: float = 0.4,
        person_model_path: str = "model/weights/yolov8s.pt",
        person_confidence: float = 0.3,
    ):
        if not os.path.exists(weights_path):
            raise FileNotFoundError(
                f"Model weights not found at '{weights_path}'. "
                f"Train the model first (see backend/training/train.py) "
                f"or place your fine-tuned 'best.pt' in backend/model/weights/."
            )
        self.model = YOLO(weights_path)
        self.confidence_threshold = confidence_threshold
        self.person_confidence = person_confidence
        self.class_names = self.model.names  # dict[int, str]

        # The fine-tuned PPE model is strong on PPE items but weak on the
        # "Person" class. A COCO-pretrained YOLO is used to reliably detect
        # people (COCO class id 0 = person), keeping per-worker compliance
        # usable even when the PPE model misses full-body persons.
        if os.path.exists(person_model_path):
            self.person_model = YOLO(person_model_path)
        else:
            self.person_model = None
            print(
                f"[WARN] Person model not found at '{person_model_path}'. "
                f"Person detection disabled; compliance will rely only on the "
                f"PPE model's own Person detections."
            )

    def _detect_persons(self, image: np.ndarray) -> List[Detection]:
        """Run the COCO person detector and return Person detections only."""
        if self.person_model is None:
            return []
        results = self.person_model.predict(
            source=image,
            conf=self.person_confidence,
            classes=[0],  # COCO class "person"
            verbose=False,
        )
        persons: List[Detection] = []
        if not results:
            return persons
        for box in results[0].boxes:
            persons.append(
                Detection(
                    class_name="Person",
                    confidence=float(box.conf[0]),
                    bbox=box.xyxy[0].tolist(),
                )
            )
        return persons

    @staticmethod
    def _center_in_box(box: List[float], outer: List[float], margin: float = 15.0) -> bool:
        """True if the center point of `box` falls inside `outer` (with margin)."""
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        return (
            (outer[0] - margin) <= cx <= (outer[2] + margin)
            and (outer[1] - margin) <= cy <= (outer[3] + margin)
        )

    def predict(self, image: np.ndarray) -> List[Detection]:
        """
        Run synchronous inference on a single image (H, W, 3).
        Returns a flat list of Detection objects: PPE/object detections from
        the fine-tuned model plus reliable Person detections from the COCO
        person model.

        Person boxes are never merged with each other (avoids under-counting
        when several people stand close together). A Person detected by the
        PPE model is only dropped when its center already falls inside a COCO
        person box, i.e. it is a duplicate of the same person.
        """
        results = self.model.predict(
            source=image,
            conf=self.confidence_threshold,
            verbose=False,
        )

        detections: List[Detection] = []
        if results:
            for box in results[0].boxes:
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

        # Merge PPE/object detections with the COCO person detections.
        merged = [d for d in detections if d.class_name != "Person"]
        persons = self._detect_persons(image)

        # Add PPE-model persons that are not already covered by a COCO box.
        ppe_persons = [d for d in detections if d.class_name == "Person"]
        for p in sorted(ppe_persons, key=lambda d: d.confidence, reverse=True):
            if any(self._center_in_box(p.bbox, k.bbox) for k in persons):
                continue
            persons.append(p)

        merged.extend(persons)
        return merged
