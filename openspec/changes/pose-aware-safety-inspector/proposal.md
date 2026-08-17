## Why

The current MVP (YOLOv8 PPE compliance) is technically sound but (1) **cannot currently run via `docker compose up`** because `yolov8n.pt` is referenced but never committed, violating the competition's reproducibility rule; and (2) is a commodity idea — plain object-detection PPE compliance is the most common AIC project, offering no differentiation. We need a distinct innovation aligned with the "AI for the Backbone of the Economy" theme (Smart Manufacturing / workplace safety) to win.

## What Changes

- **Fase 0 — Reproducibility fix**: commit `yolov8n.pt` and `yolov8n-pose.pt` under `backend/model/weights/`, un-ignore them in `.gitignore`, align `docker-compose.yml` env paths (`BASE_MODEL_PATH`, new `POSE_MODEL_PATH`) so `docker compose up --build` starts cleanly offline.
- **Fase 1 — Pose-aware compliance**: switch person detection from plain YOLOv8 to YOLOv8-pose (COCO 17 keypoints); verify each PPE item is genuinely *worn* on the correct body region (head/torso) instead of merely *carried*; add fallback to legacy box-containment when keypoints are low-confidence (label `uncertain`, never falsely accuse). Add fall detection (shoulder→hip vector) emitting a `Fall-Detected` hazard.
- **Fase 2 — Economic risk scoring**: add a deterministic scoring module producing a single 0–100 risk score from compliance and hazard results, surfaced in the API response and frontend metrics.
- **Fase 4 — Live camera input**: add a third frontend input mode that captures single frames from the browser webcam (getUserMedia) and sends each frame as one synchronous request — keeping the backend stateless/sync and within MVP constraints (no streaming, no background jobs).
- **Fase 5 — Documentation & cleanup**: rewrite README to match the actual implementation (3-class dataset, preprocessing, dual-model + pose architecture, fine-tuning steps, innovation features) and remove dead references (`Mask`/`NO-*`, `Safety Cone`, `Ladder`).

## Capabilities

### New Capabilities

- `reproducible-runtime`: Model weights required at runtime (`yolov8n.pt`, `yolov8n-pose.pt`, `best.pt`) are committed and wired via docker-compose so the system starts reliably with `docker compose up --build` offline.
- `pose-aware-compliance`: Pose-keypoint verification that PPE is worn on the correct body region (worn vs carried), a safe `uncertain` fallback, and pose-based fall detection (`Fall-Detected` hazard), working for both image and video endpoints.
- `economic-scoring`: Deterministic compliance risk score (0–100) computed from compliance and hazard results and exposed in the API response and UI.
- `live-camera-input`: Browser webcam mode that captures single frames and analyzes them through the existing synchronous image endpoint without backend streaming or background processing.

### Modified Capabilities

<!-- No existing specs in openspec/specs/; nothing to modify. -->

## Impact

- **Backend**: `backend/model/detector.py` (pose model + keypoints + fall detection), `backend/compliance/rules.py` (worn/carried verification + fallback), new `backend/compliance/economics.py`, `backend/main.py` (response shape gains `hazards`, per-person `verification`/`carried_ppe`, economic summary).
- **Frontend**: new `Live Camera` tab (`index.html`/`app.js`), new metric cards for economic/risk outputs.
- **Infra**: `docker-compose.yml` env paths; `.gitignore` un-ignores runtime `.pt` files; commit `yolov8n-pose.pt` and `yolov8n.pt` (~13 MB total).
- **Docs**: `README.md` rewritten to match actual dataset/model/preprocessing.
- **Dependencies**: none new — YOLOv8-pose ships with the existing `ultralytics` dependency.
- **Domain scope**: unchanged (construction/worker safety, 3-class fine-tuned model). No retraining.
