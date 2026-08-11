"""
PPE Compliance Detection API
----------------------------
Single synchronous endpoint that takes one image and returns:
  - per-person PPE compliance analysis
  - an annotated image (bounding boxes + status colors) as base64

Deliberately scoped to match the competition's MVP rules:
  - no background jobs / queues
  - no auto-logging pipeline
  - static model parameters at inference time
"""

import base64
import io
import os

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

from compliance.rules import analyze_compliance
from model.detector import PPEDetector

MODEL_WEIGHTS_PATH = os.getenv("MODEL_WEIGHTS_PATH", "model/weights/best.pt")
BASE_MODEL_PATH = os.getenv("BASE_MODEL_PATH", "model/weights/yolov8n.pt")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.4"))

app = FastAPI(title="PPE Compliance Detection API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # MVP only; restrict in real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)

detector: PPEDetector | None = None


@app.on_event("startup")
def load_model():
    """Load model weights exactly once when the container starts."""
    global detector
    detector = PPEDetector(MODEL_WEIGHTS_PATH, BASE_MODEL_PATH, CONFIDENCE_THRESHOLD)


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": detector is not None}


def _get_class_color(class_name: str) -> tuple:
    if class_name == "Fall-Detected" or class_name.startswith("NO-"):
        return (50, 50, 239)     # Bright Red for Violations / Hazards
    elif class_name in ["Hardhat", "Gloves", "Goggles", "Mask", "Safety Vest"]:
        return (47, 191, 113)    # Emerald Green for Compliant PPE
    elif class_name == "Person":
        return (235, 140, 40)    # Soft Cyan/Blue for Person
    else:
        return (52, 177, 242)    # Amber/Yellow for Equipment & Hazards (Ladder, Safety Cone)


def _draw_annotations(image_bgr: np.ndarray, detections: list, compliance_results: list) -> np.ndarray:
    annotated = image_bgr.copy()
    
    # 1. Draw bounding boxes for ALL detected objects (PPE, Persons, Hazards, Equipment)
    for d in detections:
        x1, y1, x2, y2 = [int(v) for v in d.bbox]
        color = _get_class_color(d.class_name)
        label = f"{d.class_name} {d.confidence * 100:.1f}%"

        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        (text_w, text_h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        
        # Ensure label stays within image bounds
        label_y1 = max(y1 - text_h - 6, 0)
        label_y2 = max(y1, text_h + 6)
        cv2.rectangle(annotated, (x1, label_y1), (x1 + text_w + 6, label_y2), color, -1)
        cv2.putText(
            annotated, label, (x1 + 3, label_y2 - 3),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA
        )

    # 2. Draw person compliance summary overlay
    for r in compliance_results:
        x1, y1, x2, y2 = [int(v) for v in r["person_bbox"]]
        comp_color = (0, 200, 0) if r["compliance_status"] == "Compliant" else (0, 0, 220)
        status_label = f"Person #{r['person_id']} [{r['compliance_status']}]"

        # Draw a subtle double border for person boxes
        cv2.rectangle(annotated, (x1 - 2, y1 - 2), (x2 + 2, y2 + 2), comp_color, 1)
        (tw, th), _ = cv2.getTextSize(status_label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        
        # Position label inside top of person box or right above
        box_y = y2 if y1 < 25 else y1 - 2
        cv2.rectangle(annotated, (x1, box_y - th - 6), (x1 + tw + 8, box_y), comp_color, -1)
        cv2.putText(
            annotated, status_label, (x1 + 4, box_y - 4),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA
        )

    return annotated


def _encode_to_base64(image_bgr: np.ndarray) -> str:
    success, buffer = cv2.imencode(".jpg", image_bgr)
    if not success:
        raise RuntimeError("Failed to encode annotated image")
    return "data:image/jpeg;base64," + base64.b64encode(buffer).decode("utf-8")


@app.post("/api/analyze")
async def analyze(image: UploadFile = File(...)):
    if detector is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")

    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    raw_bytes = await image.read()
    try:
        pil_image = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Could not decode image")

    image_rgb = np.array(pil_image)
    image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)

    # 1. Core inference (synchronous, single pass)
    detections = detector.predict(image_bgr)

    # 2. Rule-based compliance layer
    compliance_results = analyze_compliance(detections)

    # 3. Visual annotation for ALL detected objects + person compliance
    annotated = _draw_annotations(image_bgr, detections, compliance_results)
    annotated_b64 = _encode_to_base64(annotated)

    # 4. Format all detected objects output
    all_objects = [
        {
            "class_name": d.class_name,
            "confidence": round(d.confidence, 4),
            "confidence_percent": f"{d.confidence * 100:.1f}%",
            "bbox": [round(v, 1) for v in d.bbox],
            "category": (
                "hazard" if (d.class_name == "Fall-Detected" or d.class_name.startswith("NO-"))
                else "compliant_ppe" if d.class_name in ["Hardhat", "Gloves", "Goggles", "Mask", "Safety Vest"]
                else "person" if d.class_name == "Person"
                else "equipment"
            )
        }
        for d in detections
    ]

    # Calculate overall compliance score
    total_persons = len(compliance_results)
    compliant_persons = sum(1 for r in compliance_results if r["compliance_status"] == "Compliant")
    safety_score = round((compliant_persons / total_persons * 100), 1) if total_persons > 0 else 100.0

    return {
        "summary": {
            "total_objects": len(all_objects),
            "person_count": total_persons,
            "compliant_persons": compliant_persons,
            "safety_score": safety_score,
            "violations_count": sum(1 for d in all_objects if d["category"] == "hazard")
        },
        "all_objects": all_objects,
        "results": compliance_results,
        "annotated_image": annotated_b64,
    }

