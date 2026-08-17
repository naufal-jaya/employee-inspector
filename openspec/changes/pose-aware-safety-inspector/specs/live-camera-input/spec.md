## ADDED Requirements

### Requirement: Webcam single-frame capture mode
The frontend SHALL provide a Live Camera tab that requests webcam access via `getUserMedia`, captures a single frame, and submits it to the existing synchronous `/api/analyze` endpoint. The backend SHALL NOT stream video or run background processing.

#### Scenario: Capture frame from webcam
- **WHEN** the user grants webcam permission and activates Live mode
- **THEN** the frontend captures one frame and posts it to `/api/analyze`, displaying the annotated result

### Requirement: Lightweight response mode
The `/api/analyze` endpoint SHALL support a `light=true` query parameter that omits the base64 `annotated_image` from the response so the client can render boxes from JSON for a faster live feel.

#### Scenario: Light mode omits annotation
- **WHEN** a request is sent with `light=true`
- **THEN** the response contains the detection data but no base64 `annotated_image`

#### Scenario: Default mode still returns annotation
- **WHEN** a request is sent without `light=true`
- **THEN** the response contains the base64 `annotated_image` as before

### Requirement: No backend background work in live mode
Live mode SHALL reuse the existing synchronous request path and SHALL NOT introduce websockets, background jobs, or streaming endpoints.

#### Scenario: Backend remains stateless per frame
- **WHEN** live mode posts successive frames
- **THEN** each frame is processed as an independent synchronous request with no shared background state
