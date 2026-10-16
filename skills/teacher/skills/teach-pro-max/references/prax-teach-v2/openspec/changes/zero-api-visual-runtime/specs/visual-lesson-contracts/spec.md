## Purpose

Define portable, versioned lesson and learning-receipt contracts so visual interactions remain inspectable, deletable, reproducible, and safe to share.

## ADDED Requirements

### Requirement: Lesson specifications SHALL be versioned

Each lesson SHALL declare a stable identifier, semantic version, learning objective, ordered states, available learner actions, hint levels, static fallback, and grader limits.

#### Scenario: Invalid lesson specification
- **WHEN** a lesson omits its identifier, version, objective, state sequence, or fallback
- **THEN** validation rejects it with a field-specific error and produces no artifact

### Requirement: Receipts SHALL be explicit and local

The runtime SHALL create a versioned receipt containing only declared observations, attempts, actions, hint level, learner-authored explanation, and deterministic results; it SHALL support inspect, copy, JSON export, validated import, and scoped deletion.

#### Scenario: Export and import a receipt
- **WHEN** a learner exports a valid receipt and imports it into the same lesson version
- **THEN** the receipt round-trips without changing declared values or silently adding inference

### Requirement: Corrupt or unrelated receipts SHALL fail closed

Import SHALL reject malformed, unknown-version, cross-lesson, oversized, or schema-incompatible receipts without mutating existing learner state.

#### Scenario: Cross-lesson receipt
- **WHEN** a receipt for lesson A is imported into lesson B
- **THEN** import fails and lesson B's state remains unchanged

### Requirement: Learner-authored evidence SHALL remain distinct

The contract SHALL distinguish learner-authored text and observed actions from tutor or runtime inference and SHALL preserve hint level and uncertainty for every scored observation.

#### Scenario: Scaffolded success
- **WHEN** a learner succeeds after receiving a hint
- **THEN** the receipt records the hint level and does not label the result as unassisted mastery
