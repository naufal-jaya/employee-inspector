## Context

The MVP is a synchronous FastAPI service with a dual-model architecture (`backend/model/detector.py`): a COCO person model (`yolov8n.pt`) plus a fine-tuned PPE model (`best.pt`, classes `Hardhat`, `Safety Vest`, `Person`). Compliance decisions are rule-based in `backend/compliance/rules.py` using bounding-box containment (PPE box center inside person box) plus implicit deduction (any required PPE not detected → missing). The system must run offline via `docker compose up --build` per competition rules, but `yolov8n.pt` is referenced yet never committed, so startup currently fails.

Constraints:
- Backend stays synchronous & stateless; no background jobs, queues, or automated logging.
- Frontend remains a minimal single-input → single-output UI.
- Model parameters static at runtime; no auto-tuning.
- All work committed to a public GitHub repo.

## Goals / Non-Goals

**Goals:**
- Make `docker compose up --build` start reliably offline (Fase 0).
- Verify that PPE is actually *worn* (pose keypoints) rather than merely *carried*, without falsely accusing people when pose data is unreliable.
- Detect falls from pose geometry and surface them as hazards.
- Add a deterministic economic risk score backed by public statistics.
- Add a compliant "live" webcam mode (per-frame synchronous capture).
- Keep everything domain-agnostic so the fine-tuned class schema can change without code changes.

**Non-Goals:**
- No retraining / no new dataset (stay on the 3-class construction model).
- No real-time streaming (RTSP/WebSocket/background frame processing).
- No autoscaling, database, or multi-user features.
- No changes to the video endpoint's temporal aggregation logic beyond what pose verification requires.

## Decisions

### D1 — Swap the person model to YOLOv8-pose (`yolov8n-pose.pt`)
- **Decision**: Replace the plain COCO person model with `yolov8n-pose.pt` (same `ultralytics` library, COCO 17 keypoints). Persons + keypoints come from the pose model; PPE still comes from the fine-tuned model.
- **Rationale**: Keypoints (head/torso) are exactly what "worn vs carried" verification needs; zero new dependencies; similar inference cost to the current person model.
- **Alternatives considered**: A separate pose-estimation library (adds deps), or training keypoint regression into the fine-tuned model (needs dataset + retraining). Both rejected.

### D2 — Domain-agnostic body-region mapping
- **Decision**: Add `PPE_BODY_REGION = {"Hardhat": "head", "Safety Vest": "torso"}` next to `PPE_SCHEMA`. To switch domain, only the schema + region map change; verification logic is untouched.
- **Rationale**: Matches the existing `PPE_SCHEMA`-swap design; future MBG/garment pivot costs nothing.

### D3 — Worn vs carried verification with a safe fallback
- **Decision**: Compute head region = centroid of confident head keypoints (COCO 0–4, nose/eyes/ears) and torso region = centroid of shoulders (5,6) + hips (11,12). A PPE box center is *worn* if it falls within its region's radius (threshold scaled by person box height, ~0.15×). If the needed keypoints have insufficient confidence (< `KEYPOINT_CONF_THRESHOLD`, default 0.5) → `verification: "uncertain"` and fall back to the legacy box-containment logic; **uncertain never adds a violation**. If keypoints are confident but the PPE is far from the region → `carried`, added to `carried_ppe`, and treated as missing (a violation).
- **Rationale**: Guards against false accusations when faces/heads are occluded or persons are small — the biggest demo risk.
- **Alternatives considered**: Strict pose-only verification (rejected: too many false positives on backs-turned and distant workers).

### D4 — Fall detection from shoulder→hip vector, not box aspect ratio
- **Decision**: If the hip-center→shoulder-center vector is predominantly horizontal (`|dx| > 1.5 × |dy|`) and the person box is large enough, emit a synthetic `Fall-Detected` hazard (reusing the color/hazard path already half-present in `main.py`).
- **Rationale**: Box aspect ratio alone false-positives on workers with arms spread; the limb vector is more semantically correct.
- **Alternatives considered**: Aspect-ratio-only (rejected), training a fall class (needs dataset — rejected).

### D5 — Economic scoring as a pure deterministic module
- **Decision**: New `backend/compliance/economics.py` with sourced constants (BPJS Ketenagakerjaan workplace-injury statistics), producing `risk_score` (0–100), `estimated_loss_per_incident` (IDR), and `potential_savings`. Computed synchronously inside `/api/analyze`; surfaced as summary fields and frontend metric cards.
- **Rationale**: Directly addresses the "Backbone of the Economy" theme with a defensible, sourced estimate; zero model work.
- **Risk framing**: Labeled as estimates based on national averages, not precise per-site values.

### D6 — Live camera = per-frame synchronous capture, not streaming
- **Decision**: Frontend tab uses `getUserMedia`, captures a frame (throttled ~2 FPS, downscaled), and POSTs it to the existing `/api/analyze`. Add an optional `light=true` query that skips base64 annotation so the client can draw boxes itself for responsiveness. Backend remains stateless/synchronous.
- **Rationale**: Gives a "live" demo feel while strictly respecting the MVP sync/no-background-jobs constraint.
- **Alternatives considered**: RTSP/IP-camera streaming with background processing (rejected — violates competition scope).

## Risks / Trade-offs

- [Low-confidence head keypoints (backs turned, distant workers) cause mis-verification] → Mitigation: `uncertain` fallback to legacy logic; never treat uncertain as a violation.
- [Fall detection false positives (crouching/sitting workers)] → Mitigation: require vector length above a person-size-scaled threshold and horizontal dominance; expose as a hazard, not a hard accusation.
- [Two+ models add startup RAM/CPU] → Mitigation: same class of model sizes as today; weights loaded once at startup; acceptable for demo hardware.
- [`light=true` live mode still ~1–2 FPS on CPU] → Mitigation: downscale frames client-side and skip annotation; frame rate is a demo cosmetic, not a scored capability.
- [Economic figures may be questioned by judges] → Mitigation: cite sources in code + README, frame as illustrative estimates, keep the primary output the risk score.

## Migration Plan

1. Fase 0 first — commit weights, fix env paths, prove `docker compose up --build` works before touching features.
2. Fase 1 (pose) — additive changes to `Detection`/`rules.py`; legacy behavior preserved via fallback.
3. Fase 2 (economics) — additive; no breaking API change.
4. Fase 4 (live cam) — additive frontend tab; `light=true` is optional on the backend.
5. Fase 5 (docs/cleanup) — README + dead-code removal; final commit.
Rollback: each fase is an isolated commit; reverting a feature is a single commit checkout.

## Open Questions

- None blocking. Minor: exact economic constants will be pinned during implementation and cited in README.
