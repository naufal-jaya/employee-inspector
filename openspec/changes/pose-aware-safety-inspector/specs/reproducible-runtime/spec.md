## ADDED Requirements

### Requirement: Runtime model weights are committed and wired
The repository SHALL include the three model weights required at runtime (`backend/model/weights/best.pt`, `backend/model/weights/yolov8n.pt`, `backend/model/weights/yolov8n-pose.pt`) so the system starts without downloading anything from the internet. The `.gitignore` SHALL NOT exclude these files. The docker-compose service SHALL reference the committed paths via `MODEL_WEIGHTS_PATH`, `BASE_MODEL_PATH`, and `POSE_MODEL_PATH`.

#### Scenario: Fresh clone starts backend offline
- **WHEN** a user clones the repository with no network access and runs `docker compose up --build`
- **THEN** the backend container starts without a `FileNotFoundError` for model weights

#### Scenario: Health endpoint reports model loaded
- **WHEN** the backend has started successfully
- **THEN** `GET /health` returns `{"status": "ok", "model_loaded": true}`

### Requirement: Demo runs via docker compose per README
The system SHALL be runnable by following the README instructions using only `docker compose up --build`, with the frontend on port 3000 and backend API on port 8000.

#### Scenario: Follow README to run the demo
- **WHEN** a user follows the README run instructions exactly
- **THEN** the frontend loads at `http://localhost:3000` and the API docs are available at `http://localhost:8000/docs`
