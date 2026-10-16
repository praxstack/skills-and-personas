## Purpose

Make every engineering and learning claim traceable to exact bytes, reproducible commands, declared limitations, and the correct human-evidence gate.

## ADDED Requirements

### Requirement: Evidence SHALL be claim-scoped

Evidence records SHALL identify the criterion, exact package or lesson bytes, command and version, result, limitation, and whether the evidence is synthetic, agent-level, engineering, or human-observed.

#### Scenario: Synthetic fixture result
- **WHEN** a synthetic lesson fixture passes its evaluator
- **THEN** the receipt labels it synthetic and cannot promote a delayed human-learning criterion

### Requirement: Builds SHALL be reproducible

The package builder SHALL emit a manifest and rollback receipt, reject undeclared files or remote assets, and produce byte-identical output for identical declared inputs.

#### Scenario: Undeclared remote asset
- **WHEN** a lesson references a remote font, CDN, image, or script
- **THEN** the build fails closed before packaging

### Requirement: External learner gates SHALL remain explicit

The tracker SHALL distinguish engineering criteria from representative accessibility, immediate, delayed, transfer, and generalization observations and SHALL keep unavailable external gates waiting rather than passing them from fixtures.

#### Scenario: No elapsed delay available
- **WHEN** a delayed retention observation has not occurred
- **THEN** the delayed gate remains waiting_external and the project cannot claim scientific completion

### Requirement: Promotion SHALL require human authorization

The system SHALL stop before global installation, canonical replacement, merge, push, deploy, publication, metered spending, participant recruitment, or material deletion until the corresponding approval is recorded.

#### Scenario: Candidate package is green
- **WHEN** engineering verification passes but promotion approval is absent
- **THEN** the candidate remains a local package and no canonical skill is changed
