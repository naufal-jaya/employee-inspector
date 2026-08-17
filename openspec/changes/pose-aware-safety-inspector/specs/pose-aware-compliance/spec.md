## ADDED Requirements

### Requirement: Person detection uses pose keypoints
The person detector SHALL use a COCO pose model that returns 17 body keypoints alongside person boxes, for both the image endpoint and the video (tracked) endpoint. Each detection SHALL carry keypoint coordinates and per-keypoint confidence values.

#### Scenario: Person detected with keypoints
- **WHEN** an image containing a worker is submitted to `/api/analyze`
- **THEN** the returned person detection includes keypoints for the worker's body

#### Scenario: Video tracking preserves keypoints
- **WHEN** a video is analyzed via `/api/analyze-video`
- **THEN** each tracked person frame carries keypoints associated with its `track_id`

### Requirement: PPE is verified as worn or carried
For each PPE item in `PPE_BODY_REGION` (e.g. Hardhat → head, Safety Vest → torso), the system SHALL verify the item is worn on the correct body region using keypoint geometry. A PPE item whose box center is inside its body region is `worn`. A PPE item detected but located outside its region is `carried`. The per-person result SHALL include `worn_ppe`, `carried_ppe`, and a `verification` value (`worn` | `carried` | `uncertain`).

#### Scenario: Hardhat carried in hand is flagged
- **WHEN** a worker is detected with a hardhat box far from the head keypoints
- **THEN** the hardhat is listed in `carried_ppe`, excluded from `worn_ppe`, and counted as a violation

#### Scenario: Worn hardhat is compliant
- **WHEN** a worker's hardhat box center is within the head region derived from confident head keypoints
- **THEN** the hardhat is listed in `worn_ppe` and does not contribute to a violation

### Requirement: Uncertain verification does not accuse
When the keypoints needed to verify a PPE region have confidence below the configured threshold, the system SHALL mark that item's verification as `uncertain` and fall back to the legacy box-containment logic. An `uncertain` outcome SHALL NOT add a violation on its own.

#### Scenario: Back-turned worker is not falsely accused
- **WHEN** a worker's head keypoints are low-confidence and no hardhat is detected near the head
- **THEN** the worker is not automatically flagged as missing a hardhat due to uncertain pose data, and the verification is reported as `uncertain`

### Requirement: Fall detection hazard
The system SHALL emit a synthetic `Fall-Detected` hazard when the hip-center→shoulder-center vector is predominantly horizontal for a sufficiently large person box. Fall hazards SHALL appear in a `hazards` list in the response and count toward the summary.

#### Scenario: Lying worker detected as a fall
- **WHEN** a person is detected in a horizontal orientation with a large enough bounding box
- **THEN** a `Fall-Detected` hazard is included in the response hazards and in the violations count

#### Scenario: Standing worker is not a fall
- **WHEN** a person's shoulder→hip vector is predominantly vertical
- **THEN** no `Fall-Detected` hazard is emitted for that person

### Requirement: Pose verification applies to image and video endpoints
The worn/carried/uncertain verification and fall detection SHALL behave consistently in both `/api/analyze` and `/api/analyze-video` (per-frame).

#### Scenario: Consistent results across endpoints
- **WHEN** the same scene is analyzed as both an image and a single video frame
- **THEN** the verification outcomes for the same person match within the configured thresholds
