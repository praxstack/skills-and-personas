# Visual intuition revision: proposed evaluation contract v1

Status: DRAFT FOR HUMAN APPROVAL together with DESIGN-v1.md. No candidate implementation or quality run has started. This is an engineering/agent-behavior evaluation, not a human-learning study.

## Fixed product objective

A general skill builds concrete understanding through complete, connected visual explanations, purposeful media and optional practice. Explicit user overrides, honest evidence and consent boundaries remain protected. The neuron-to-LLM request is a visible development example only.

## Approved changes versus protected invariants

| Intentionally changed policy | Protected behavior |
|---|---|
| Explanation first instead of compulsory initial attempt | Requested quizzes still preserve genuine attempt-before-answer boundaries |
| Complete bounded lesson instead of quick-by-default teaching | Explicit brevity, direct-answer requests and ordinary tasks remain honored |
| Optional check and learner-led continuation | No fabricated performance, mastery, learner history or scheduler rating |
| Automatic resume with active directory consent | No new learner-state scope without consent; withdrawal stops personalization/tracking |
| Purposeful media selection instead of interactive-first mandate | Exact semantics, accessible alternatives and truthful capability/inspection claims |
| Explicit preference/continuity support | Existing schemas/events remain readable; no silent migration or unsafe filesystem writes |
| Lesson files may persist without learner tracking | Explicit save-nothing prohibits durable artifacts; saved content must not embed learner history |
| Forget-progress preserves sibling lesson artifacts | Destructive operations remain scoped, previewed and confirmed |

Historical test expectations conflicting with the left column are identified as deliberate policy changes. Do not erase or relabel their old results. Right-column protections remain non-compensatory release conditions.

## Run phases and separation

1. Approve/version this contract and DESIGN-v1.md, with baseline commit and package hashes retained.
2. In a separate evaluation-setup phase, an independent evaluator creates and seals six unseen scenario files and rubrics outside all candidate-visible workspaces. Hash the full bank, runner configuration, target source, budgets and scoring rubric before any candidate edits. Inspect the implementation of the existing evaluation runner and validate its containment path; do not invent a new framework.
3. Freeze the evaluation implementation and bank in a separate version. Candidate workers may read this contract and public development material, but never the hidden scenarios, answers or grader instructions. Public development fixtures are never called held-out.
4. Implement one isolated candidate against that frozen setup. Candidate changes cannot alter the evaluator, thresholds, sealed bank, protected policies or historical receipts.
5. Run the acceptance suite once the candidate is frozen. Failed outputs remain receipts. Any further candidate requires a fresh independent sealed bank under the same approved contract before another candidate-edit phase; do not reuse disclosed failed cases as hidden tests.

The original baseline and current accepted version are identical for the first run. Any later run compares against both. No promotion follows an unavailable or untrustworthy acceptance run.

## Scenario matrix and repetition budget

Six independent scenario families, each with three paired baseline/candidate repetitions in the same primary host: 36 target runs maximum for one candidate. Hidden scenario wording and expected content are evaluator-owned. Use one science mechanism, one quantitative/mathematical relation, one procedural/computing concept, one historical/interpretive topic, one language concept, and one expert-level explanation in a domain different from the visible neural-network example.

Across these scenarios, cover: normal visual-first delivery; a meaningful contrast/formal bridge; requested media unavailable and essential-medium exception; clarification after confusion; consent decline plus lesson-artifact persistence; active resume with optional practice skipped. Protective public negative probes cover explicit quiz, brevity, ordinary-task non-trigger, save-nothing, withdrawn consent and unsafe state. These are explicitly public and do not add to the unseen claim.

Capture real turn boundaries for multi-turn behavior. Use paired equivalent tools, model settings, deadlines and workspace state. Record the exact host/model/configuration once authentication and sandbox support are verified. Baseline and candidate must not share learned state or generated outputs.

Primary host: use the existing Codex CLI if authenticated and capable of the required containment. Secondary host: four public smoke scenarios using the installed Claude CLI if authenticated and usable. This is a second-host smoke check, not evidence of reliability across every app. CLI availability is confirmed; authentication and suitable isolation have not yet been checked. An unavailable second host limits portability claims and must be reported. An unavailable isolated primary acceptance path blocks promotion.

## Scoring and thresholds

Five dimensions, each 0-2, total 0-10:

1. Mechanism/meaning: accurate relationships and intermediate reasoning make why/how explicit.
2. Story coherence: concrete anchor, necessary prerequisites and connected scenes make the explanation followable.
3. Visual purpose: each representation/control has an explanatory job; no decorative substitute for missing reasoning.
4. Concrete-to-general connection: appropriate formal mapping or meaningful contrast, without unnecessary complexity or invented causality.
5. Learner control and adaptation: accepted delivery/style overrides, optional practice and targeted clarification are respected.

Anchors: 0 = absent, wrong or materially misleading; 1 = present but incomplete or unclear; 2 = explicit, correct and coherent for the requested level. A suitable contrast/formal mapping is assessed by usefulness, not mandatory inclusion of both. A valid static choice can earn full marks. Factual or consent violations are hard failures independent of score.

Acceptance requires all of:
- No protected critical failure in candidate runs, public probes or security regressions.
- Candidate mean score at least 8/10 overall; each scenario's three-run mean at least 7/10; no dimension scores zero in a candidate run.
- Candidate overall paired mean gain at least 1 point over baseline; no scenario-mean regression; at least five of six scenario means improve.
- All applicable deterministic regression checks pass, with approved policy-expectation changes reported separately.
- Representative rendered inspection passes for the actual artifacts used for delivery claims; no claimed check is merely planned.

These are proposed product acceptance thresholds, not validated educational effect sizes or population significance tests. Publish all three repetitions and their range, not just the best run. Inconsistent or borderline results are inconclusive; do not add unplanned repetitions or lower thresholds to obtain a pass. Independent graders inspect frozen outputs; an AI rubric score cannot prove that people learned.

## Deterministic and delivery checks

Use the existing Python and JavaScript tests appropriate to the runtime changes, plus focused new continuity/routing cases. Run the full applicable suites before promotion. In particular: consent/withdrawal, no-write initialization, schema validation, filesystem containment, stale concurrent updates, optional continuity inspection/export/deletion, unchanged evidence under coverage-only updates, old workspace compatibility, preserved lesson hashes under forget-progress, mode overrides, visual route integrity, renderer parity and distribution manifests.

Validate state with the runtime, not merely the generic artifact validator. Exercise a static explanation and an available animation/interactive route in a real browser; test labels, representative states, keyboard controls, reduced motion and fallback. Do not claim screen-reader or representative-user validation from automated checks.

The package specifies Node 22, while the live default is Node 26.12.0. Use a project-isolated supported Node version for package checks; do not change the user's global Node installation. Retain the locked Python dependencies in an isolated supported interpreter.

## Budgets and stop rules

At most two candidate revisions under this approved project objective. Each candidate run is capped at 120 minutes elapsed from the first candidate edit through evaluation, with at most 36 primary hidden target runs plus four secondary public smoke runs. Public diagnostics remain within the same elapsed-time bound. No paid API purchase, subscription change, unapproved dependency service or automatic publication.

No budget extension by the agent. If the planned checks do not fit, stop and report incomplete validation, preserving the candidate and installed baseline. Two no-gain candidates end this attempt. A different budget or evaluator is a new human-approved run version, not an exception made inside the run.

## Protected and mutable paths

Protected: this contract and the approved design after freezing; independent sealed evaluation materials; historical evidence/archives; original baseline source; existing learner directories; unrelated skills, global host settings and human-owned identity policy.

Candidate-mutable categories: primary/wrapper skill instructions; mode/teaching/visual/operations references required by the approved behavior; request routing; one continuity module and narrow state/export/CLI hooks; additive continuity schema; focused public tests and approved new-policy fixtures; corresponding generated documentation and current package manifests after verification. Enumerate exact paths in the implementation plan before edits. More than these categories requires a scope decision; no unrelated refactoring.

## Receipts and rollback

Keep outputs, test logs, hashes and inspection receipts outside the package content they attest to. Store the evaluation specification digest and baseline/candidate hashes with the results. Record used tooling and unverified host limitations. Historical receipts apply only to their original bytes.

No installed changes until acceptance and review pass. Retain original shared-skill link targets and source checkout. Rollback restores the previous targets/version and verifies all affected SKILL.md paths plus distribution integrity. No learner-state migration is part of promotion or rollback.
