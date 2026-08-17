## ADDED Requirements

### Requirement: Risk score output
The `/api/analyze` response summary SHALL include a deterministic `risk_score` from 0 to 100, computed from per-person missing/carried PPE, hazard detections, and risk severity. The score SHALL be reproducible for the same input.

#### Scenario: Fully compliant scene scores high
- **WHEN** all workers are compliant and no hazards are present
- **THEN** the response `risk_score` is above 90

#### Scenario: Violations lower the score
- **WHEN** a worker is missing a hardhat or a fall hazard is present
- **THEN** the response `risk_score` decreases relative to the fully-compliant baseline

### Requirement: Economic impact estimates
The response SHALL include `estimated_loss_per_incident` (IDR) and `potential_savings` (IDR) computed from sourced public workplace-safety statistics (e.g. BPJS Ketenagakerjaan) documented in the README. Values SHALL be derived deterministically from the same inputs as the risk score.

#### Scenario: Estimates returned with analysis
- **WHEN** an image analysis completes
- **THEN** the response contains `estimated_loss_per_incident` and `potential_savings` in IDR derived from the documented source statistics

### Requirement: Economic outputs shown in the UI
The frontend SHALL display the risk score and economic estimates as metric cards alongside the existing safety metrics.

#### Scenario: Metrics visible after image analysis
- **WHEN** a user analyzes an image and the result panel renders
- **THEN** the risk score and economic estimate metric cards display the returned values
