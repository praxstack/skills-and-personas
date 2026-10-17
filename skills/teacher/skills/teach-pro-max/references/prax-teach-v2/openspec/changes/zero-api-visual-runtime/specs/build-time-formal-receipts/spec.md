## Purpose

Offer one removable, build-time formal-verification boundary that can catch a material lesson error or expose a usable proof state without making theorem proving a learner-runtime dependency.

## ADDED Requirements

### Requirement: Formal verification SHALL be build-time only

The learner artifact SHALL not execute a theorem prover, download a toolchain, or call a model; proof checking SHALL happen before packaging with a pinned toolchain and recorded inputs.

#### Scenario: Offline artifact use
- **WHEN** a learner opens a packaged formal lesson without the build environment
- **THEN** the preverified proof-state sequence and static equivalent remain available

### Requirement: Formal receipts SHALL be provenance-bound

The adapter SHALL export proof-state JSON, source hashes, toolchain version, imported modules, warnings, axioms, and result status in a versioned receipt that can be validated independently.

#### Scenario: Stale proof input
- **WHEN** the lesson source or toolchain hash differs from the recorded receipt
- **THEN** packaging rejects the receipt as stale

### Requirement: Lean SHALL earn retention

The project SHALL keep the Lean adapter only if the predeclared experiment catches a material content error or gives learners a usable proof-state representation without violating runtime, accessibility, maintenance, or cognitive-cost gates.

#### Scenario: Experiment does not meet threshold
- **WHEN** the Lean experiment fails its declared value threshold
- **THEN** the adapter is removed or deferred while the generic formal-receipt contract remains valid
