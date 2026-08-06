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
        person_model_path: str = "model/weights/yolov8n.pt",
    ):
        if not os.path.exists(weights_path):
            raise FileNotFoundError(
                f"Model weights not found at '{weights_path}'. "
                f"Train the model first (see backend/training/train.py) "
                f"or place your fine-tuned 'best.pt' in backend/model/weights/."
            )
        self.model = YOLO(weights_path)
        self.confidence_threshold = confidence_threshold
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
            conf=self.confidence_threshold,
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
    def _same_person(a: List[float], b: List[float]) -> bool:
        """True if two person boxes likely refer to the same person.

        Compares box centers instead of IoU so that two distinct people
        standing close together (heavily overlapping boxes) are not merged.
        """
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        acx, acy = (ax1 + ax2) / 2, (ay1 + ay2) / 2
        bcx, bcy = (bx1 + bx2) / 2, (by1 + by2) / 2
        dist = ((acx - bcx) ** 2 + (acy - bcy) ** 2) ** 0.5
        a_diag = ((ax2 - ax1) ** 2 + (ay2 - ay1) ** 2) ** 0.5
        b_diag = ((bx2 - bx1) ** 2 + (by2 - by1) ** 2) ** 0.5
        return dist < 0.5 * min(a_diag, b_diag)

    def predict(self, image: np.ndarray) -> List[Detection]:
        """
        Run synchronous inference on a single image (H, W, 3).
        Returns a flat list of Detection objects: PPE/object detections from
        the fine-tuned model plus reliable Person detections from the COCO
        person model. Duplicate person boxes (same center, from both models)
        are deduplicated keeping the higher-confidence one.
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
        person_candidates = [d for d in detections if d.class_name == "Person"]
        person_candidates.extend(self._detect_persons(image))

        kept_persons: List[Detection] = []
        for p in sorted(person_candidates, key=lambda d: d.confidence, reverse=True):
            if any(self._same_person(p.bbox, k.bbox) for k in kept_persons):
                continue
            kept_persons.append(p)

        merged.extend(kept_persons)
        return merged
