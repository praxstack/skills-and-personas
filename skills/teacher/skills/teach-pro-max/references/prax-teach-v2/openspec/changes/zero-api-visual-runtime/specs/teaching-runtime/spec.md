## Purpose

Connect the host tutor and local visual lessons through an explicit receipt bridge while keeping open-ended interpretation in the host conversation and deterministic behavior in the local artifact.

## ADDED Requirements

### Requirement: Host and runtime responsibilities SHALL remain separate

The host tutor SHALL interpret natural-language explanations and misconceptions, while the local runtime SHALL own deterministic transitions, exact graders, static fallbacks, and receipt production.

#### Scenario: Ambiguous learner explanation
- **WHEN** a learner submits an open-ended explanation that cannot be judged structurally
- **THEN** the runtime preserves the text and routes interpretation to the human-operated host tutor

### Requirement: Receipt sharing SHALL be learner-controlled

The runtime SHALL provide copy and export actions but SHALL never automatically upload a receipt, scrape a host conversation, or infer subscription credentials.

#### Scenario: Learner does not share a receipt
- **WHEN** a learner completes a local lesson and declines to export
- **THEN** the receipt remains local and no host request is made

### Requirement: Static fallback SHALL be the universal route

If a separately versioned interactive runtime is missing, incompatible, or unverified, the teaching skill SHALL route to host chat or a static state sequence without implying that the artifact grades or persists interaction.

#### Scenario: Runtime unavailable
- **WHEN** the interactive renderer cannot be verified for the current lesson
- **THEN** the skill delivers a static equivalent and states the runtime limitation
