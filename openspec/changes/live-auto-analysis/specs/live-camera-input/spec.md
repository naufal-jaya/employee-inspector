## MODIFIED Requirements

### Requirement: Webcam single-frame capture mode
The frontend SHALL provide a Live Camera tab that requests webcam access via `getUserMedia` and continuously submits successive frames to the existing synchronous `/api/analyze` endpoint on an automatic throttle of approximately one second while the camera is active, without requiring a manual capture action. The backend SHALL NOT stream video or run background processing.

#### Scenario: Automatic analysis after starting the camera
- **WHEN** the user grants webcam permission and starts Live mode
- **THEN** the frontend begins submitting frames to `/api/analyze` automatically at roughly one-second intervals with no further user interaction

#### Scenario: No queue buildup on slow inference
- **WHEN** a previous frame request is still in flight
- **THEN** the frontend skips submitting another frame until the pending request completes

#### Scenario: Analysis stops with the camera
- **WHEN** the user stops the camera
- **THEN** the frontend stops submitting frames and clears the overlay