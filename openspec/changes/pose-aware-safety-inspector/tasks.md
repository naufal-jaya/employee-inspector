## 1. Fase 0 — Reproducibility fix (unblocks everything)

- [x] 1.1 Download `yolov8n.pt` and `yolov8n-pose.pt` into `backend/model/weights/`
- [x] 1.2 Un-ignore runtime weights in `.gitignore` (`!backend/model/weights/yolov8n.pt`, `!backend/model/weights/yolov8n-pose.pt`)
- [x] 1.3 Update `docker-compose.yml`: `BASE_MODEL_PATH=/app/model/weights/yolov8n.pt`, add `POSE_MODEL_PATH=/app/model/weights/yolov8n-pose.pt`
- [x] 1.4 Align default env paths in `backend/main.py` with committed files
- [x] 1.5 Verify `docker compose up --build` starts and `GET /health` returns `model_loaded: true`
- [x] 1.6 Commit + push (commit message includes Fase 0)

## 2. Fase 1 — Pose-aware compliance (image + video)

- [x] 2.1 Extend `Detection` dataclass in `detector.py` with `keypoints` and keypoint confidence
- [x] 2.2 Load `yolov8n-pose.pt` as the person model; wire `POSE_MODEL_PATH` config
- [x] 2.3 Extract keypoints in `predict()` and `predict_tracked()` for each person
- [x] 2.4 Implement fall detection (hip→shoulder horizontal vector) emitting synthetic `Fall-Detected`
- [x] 2.5 Add `PPE_BODY_REGION` map and `_verify_ppe_worn()` in `rules.py` (worn / carried / uncertain fallback)
- [x] 2.6 Surface `worn_ppe`, `carried_ppe`, `verification` in per-person results; count carried as violation, never uncertain
- [x] 2.7 Update `main.py`: hazard list, carried/fall annotations, `hazards` in response and summary
- [x] 2.8 Add lightweight unit test for pose geometry (worn vs carried vs uncertain) in `backend/tests/`
- [x] 2.9 Commit + push

## 3. Fase 2 — Economic risk & ROI scoring

- [x] 3.1 Create `backend/compliance/economics.py` with sourced constants and compute functions
- [x] 3.2 Integrate `risk_score`, `estimated_loss_per_incident`, `potential_savings` into `/api/analyze` summary
- [x] 3.3 Add economic metric cards to `frontend/index.html` and render in `frontend/app.js`
- [x] 3.4 Commit + push

## 4. Fase 4 — Live camera mode (final polish)

- [x] 4.1 Add Live Camera tab with `getUserMedia` capture loop in `frontend/app.js` + `index.html`
- [x] 4.2 Support `light=true` on `/api/analyze` to omit base64 annotation; frontend draws boxes from JSON
- [x] 4.3 Commit + push

## 5. Fase 5 — Documentation & cleanup

- [x] 5.1 Rewrite `README.md` to match actual implementation (3-class dataset, preprocessing, dual-model + pose architecture, fine-tuning steps, innovation features, economic sources)
- [x] 5.2 Remove dead code references (`Mask`/`NO-*`, `Safety Cone`, `Ladder`) while keeping `Fall-Detected`
- [x] 5.3 Final end-to-end verification via `docker compose up --build`
- [ ] 5.4 Final commit + push before deadline
