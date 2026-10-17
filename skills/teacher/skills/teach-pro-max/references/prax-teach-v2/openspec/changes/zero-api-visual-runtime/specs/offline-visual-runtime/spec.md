## Purpose

Provide a deterministic, offline visual-learning runtime that lets learners manipulate exact models while preserving a complete accessible static fallback.

## ADDED Requirements

### Requirement: Runtime SHALL remain offline

The runtime SHALL make no network request, telemetry call, remote asset load, API call, or model-provider request during build or learner use.

#### Scenario: Network interception
- **WHEN** a lesson attempts to request a remote URL during a guarded run
- **THEN** the request is blocked and the verification run fails

### Requirement: Runtime SHALL preserve static fallback

Every lesson SHALL provide equivalent conceptual content through static HTML that remains usable with JavaScript disabled, reduced motion, print output, and keyboard navigation.

#### Scenario: JavaScript disabled
- **WHEN** a learner opens a lesson with JavaScript disabled
- **THEN** the lesson sequence, essential meaning, instructions, and answer-independent content remain available

### Requirement: Runtime SHALL expose deterministic learner controls

Interactive state SHALL change only through declared learner actions and SHALL produce the same output for the same lesson version, input sequence, and initial state.

#### Scenario: Replaying an action sequence
- **WHEN** the same sequence is replayed against the same lesson version
- **THEN** the state projection and receipt fields are byte-stable

### Requirement: Runtime SHALL preserve learner agency

The runtime SHALL allow a learner to step back, request only the next ordered hint, reset a lesson, and stop without silently uploading or deleting local evidence.

#### Scenario: Learner requests a hint
- **WHEN** a learner requests help before completing the current step
- **THEN** only the next declared hint level is shown and the learner may attempt the step again
