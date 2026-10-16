## Purpose

Supply three reusable, cross-domain lessons that make representation, state change, and concurrency behavior visible without embedding a model or relying on decorative animation.

## ADDED Requirements

### Requirement: Floating-point lesson SHALL expose representation error

The lesson SHALL let a learner predict, step through, compare decimal intent with binary representation, explain the observed result, and solve an unseen transfer item.

#### Scenario: Floating-point prediction and transfer
- **WHEN** a learner predicts the result of `0.1 + 0.2`, steps through the representation, and answers a fresh decimal-boundary case
- **THEN** the lesson records prediction, observed result, explanation, hint use, and transfer result separately

### Requirement: Rubik's lesson SHALL preserve legal moves

The lesson SHALL model legal cube moves with an inspectable state representation, synchronize notation and spatial/static views, and reject illegal or malformed moves.

#### Scenario: Legal move sequence
- **WHEN** a learner applies a valid move sequence and requests a comparison view
- **THEN** all views represent the same state and the cube invariants remain valid

### Requirement: Lost-update lesson SHALL expose interleaving causality

The lesson SHALL let a learner interleave two operations, compare the timeline with the final state, identify the lost update, and transfer the reasoning to an unseen schedule.

#### Scenario: Concurrent interleaving
- **WHEN** two read-modify-write operations are interleaved without synchronization
- **THEN** the lesson shows the causal steps that lose an update and preserves an unassisted or scaffolded result label

### Requirement: Labs SHALL share runtime components

The three lessons SHALL use the same public state-stepper, parameter-lab, compare-views, ordered hint engine, and receipt panel contracts rather than lesson-specific forks of core behavior.

#### Scenario: Shared component contract
- **WHEN** the lesson manifest is inspected
- **THEN** each lab references the shared component versions and no lab supplies a private replacement for their core transitions
