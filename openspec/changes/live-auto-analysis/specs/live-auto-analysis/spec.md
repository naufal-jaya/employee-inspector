## ADDED Requirements

### Requirement: Overlay annotations on the live video feed
The frontend SHALL render detection boxes and labels from the latest `/api/analyze` response as an overlay drawn directly on top of the moving webcam video feed, so annotations appear on the live view rather than on a separate frozen canvas.

#### Scenario: Boxes appear on the live feed
- **WHEN** a live analysis response is received while the camera is streaming
- **THEN** the overlay canvas positioned over the video displays the object boxes and person compliance boxes aligned with the current frame

#### Scenario: Overlay is cleared on stop
- **WHEN** the user stops the camera
- **THEN** the overlay canvas is cleared of all annotations

### Requirement: Live-updating results panel
The metrics cards (Risk Score, Persons, Violations, Hazards) and the Worker Compliance list SHALL refresh automatically after each completed live analysis, without a manual action.

#### Scenario: Metrics refresh per analysis
- **WHEN** a live analysis response is received
- **THEN** the metrics and Worker Compliance list reflect the latest response data

### Requirement: Tab-switch pause and resume
When the user leaves the Live Camera tab, the analysis loop SHALL pause while the camera keeps running; when the user returns to the tab, the loop SHALL resume automatically if the camera is still active.

#### Scenario: Leaving the tab pauses analysis
- **WHEN** the user switches to the Image or Video tab while Live is active
- **THEN** no new frames are submitted until the user returns to the Live Camera tab

#### Scenario: Returning to the tab resumes analysis
- **WHEN** the user switches back to the Live Camera tab while the camera is still active
- **THEN** the analysis loop resumes automatically