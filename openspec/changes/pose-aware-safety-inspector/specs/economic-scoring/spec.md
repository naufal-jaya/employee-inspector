## ADDED Requirements

### Requirement: Risk score output
The `/api/analyze` response summary SHALL include a deterministic `risk_score` from 0 to 100, computed from per-person missing/carried PPE, hazard detections, and risk severity. The score SHALL be reproducible for the same input.

#### Scenario: Fully compliant scene scores high
- **WHEN** all workers are compliant and no hazards are present
- **THEN** the response `risk_score` is above 90

#### Scenario: Violations lower the score
- **WHEN** a worker is missing a hardhat or a fall hazard is present
- **THEN** the response `risk_score` decreases relative to the fully-compliant baseline

### Requirement: Risk score shown in the UI
The frontend SHALL display the risk score as a metric card alongside the existing safety metrics.

#### Scenario: Metrics visible after image analysis
- **WHEN** a user analyzes an image and the result panel renders
- **THEN** the risk score metric card displays the returned value

### Requirement: No financial loss/savings estimates exposed
The response and UI SHALL NOT expose illustrative IDR loss/savings figures, so the system does not present raw rupiah estimates that could be mistaken for precise claims.

#### Scenario: Response contains only the risk score
- **WHEN** an image analysis completes
- **THEN** the response summary contains `risk_score` and no `estimated_loss_per_incident` / `potential_savings` fields
