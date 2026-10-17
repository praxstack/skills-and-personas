# Zero-API Visual Runtime control specification

## Product boundary

Prax Visual Lab is a separately versioned, local, deterministic visual-learning runtime for `prax-teach-v2`. The host tutor remains human-operated ChatGPT/Codex conversation. The runtime never calls a model, provider, API, telemetry endpoint, CDN, remote font, or cloud service. The existing Markdown/HTML renderer and host-chat route remain the universal fallback.

## North Star

The learner can later retrieve, explain, apply, discriminate, and transfer the idea without the tutor—and the system can show honest evidence for that claim. Engineering fixtures and agent tests cannot satisfy the external learner gates.

## Architecture

Versioned lesson JSON is validated, built into a static local artifact, and rendered with standards-based Web Components. Pure domain modules own floating-point, Rubik's, and lost-update transitions. The runtime owns exact/structural grading, ordered hints, static fallback, and local receipts. Ambiguous explanations are retained and handed to the host tutor only when the learner deliberately copies a receipt.

## Acceptance ledger

ZV-00..ZV-35 are engineering criteria. EG-ZV-01 representative accessibility, EG-ZV-02 immediate learning, EG-ZV-03 delayed 7–14 day retention, and EG-ZV-04 novel transfer require genuine observations and stay `waiting_external` until they exist. Synthetic data, automated accessibility checks, generated receipts, or planned delays cannot promote an external gate.

## Promotion gates

The candidate remains project-scoped. Global install/replacement, merge, push, deploy, publication, paid or metered calls, participant recruitment, and material deletion require explicit human authorization. Rollback is removal of `runtime/prax-visual-lab`, its examples and evidence, restoring the previous candidate commit/archive, and leaving the static renderer and installed skill unchanged.

## Implementation decision

The candidate has no TypeScript compiler or UI framework and must ship as a zero-dependency offline browser artifact. Native ES modules plus Web Components are the lower-complexity equivalent of the proposed TypeScript boundary; JSDoc and Node tests provide the type/contract surface without adding a build dependency. This is a deliberate scope decision, not a hidden framework migration.
