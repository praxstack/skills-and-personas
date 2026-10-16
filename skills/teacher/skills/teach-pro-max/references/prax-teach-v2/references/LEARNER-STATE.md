# Learner-state contract

## Contents

1. [Principles](#principles)
2. [Workspace files](#workspace-files)
3. [Observation schema](#observation-schema)
4. [Concept state](#concept-state)
5. [Misconceptions](#misconceptions)
6. [Review scheduling](#review-scheduling)
7. [Consent and correction](#consent-and-correction)
8. [Resume and migration](#resume-and-migration)
9. [Validation invariants](#validation-invariants)

## Principles

- Store raw observations separately from interpreted state.
- Link every inference to evidence IDs.
- Keep learner-authored content distinct from agent-authored inference.
- Represent uncertainty and contradictory evidence.
- Track concept dimensions rather than a personality or global ability label.
- Let the learner inspect, correct, retest, export, and delete state.
- Minimize data and never persist without explicit consent.
- Version content, items, models, prompts, and sources that affect interpretation.

## Workspace files

```text
state/
├── learner.json
├── concepts.json
├── misconceptions.json
├── reviews.jsonl
├── sessions.jsonl
└── sources.json
```

### `learner.json`

Store only learner-approved settings:

```json
{
  "schema_version": "1",
  "learner_id": "local-pseudonym",
  "consent": {
    "persistent_state": true,
    "granted_at": "2026-08-03T12:00:00.000000Z",
    "scope": ["goal", "practice_evidence", "reviews", "access_preferences"]
  },
  "goal": {
    "statement": "Choose and justify database indexes for production queries",
    "target_performance": "Solve unseen schema and workload cases without hints",
    "retention_horizon_days": 30
  },
  "preferences": {
    "response_pace": "concise",
    "reduced_motion": true,
    "response_modes": ["text", "code"]
  }
}
```

Do not store diagnoses, protected traits, health data, or inferred “learning styles.” Access preferences are functional choices, not ability labels.

### `sessions.jsonl`

Append one observation or session event per line. Never edit history silently. Corrections are new events referencing the corrected event.

### `concepts.json`

Store the current derived view and evidence links. It may be rebuilt from observations.

### `misconceptions.json`

Store specific incorrect rules or mental models only when supported by learner reasoning. Do not equate one wrong answer with a stable misconception.

### `reviews.jsonl`

Store scheduler inputs, outputs, performance-derived ratings, overrides, and due-item events.

### `sources.json`

Store the canonical machine-validated source library. Every record is bound by
`source_id` plus `version_or_date` and includes the title, absolute URL,
author/publisher, source type, retrieval date, license/use note, supported claim
or item IDs, and limitations. An observation cannot be appended unless every
versioned source reference resolves here. `RESOURCES.md` remains the curated
human-readable guide; it is exported alongside this registry but does not
replace it.

An evidence append or projection rebuild commits `sessions.jsonl`,
`reviews.jsonl`, `concepts.json`, and `misconceptions.json` through one private,
content-bound state journal. Each target records its preimage and final SHA-256
digest. A later locked operation completes an interrupted journal only when
every current file is either that preimage or exact target; divergent state
fails closed. Recovery happens before a consent-withdrawal write, preventing an
interrupted append from becoming permanently uninspectable once persistence is
disabled.

## Observation schema

Record at minimum:

```json
{
  "schema_version": "1",
  "event_id": "evt-3769e2077bb08a470f12c9a13e4f1d48",
  "event_type": "observation",
  "session_id": "session-1",
  "timestamp": "2026-08-03T12:34:56.000000Z",
  "content_id": "lesson-index-prefixes",
  "content_version": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "objective_id": "objective:index-choice",
  "concept_id": "composite-index-prefix",
  "item_id": "item-transfer-03",
  "item_version": "v1",
  "response": "The range column should follow the equality prefix.",
  "response_ref": null,
  "result": {
    "correct": false,
    "score": 0.75
  },
  "rubric": {
    "score": 0.75,
    "dimensions": {
      "recognition": null,
      "recall": null,
      "explanation": null,
      "application": null,
      "discrimination": null,
      "transfer": 0.75
    }
  },
  "dimension": "transfer",
  "confidence": {
    "provenance": "learner_reported",
    "value": 0.8
  },
  "hint_level": 2,
  "attempt_number": 2,
  "source_provenance": [
    {
      "source_id": "postgres-index-docs",
      "version_or_date": "PostgreSQL-18-2026-08-04"
    }
  ],
  "model_and_prompt_version": "prax-teach-v2-core-1.0.0",
  "agent_inference": {
    "summary": "Understands prefix matching; transfer remains uncertain",
    "certainty": 0.62
  },
  "learner_authored": null
}
```

Store either the exact inline `response` or an exact `response_ref` to a
consented artifact or transcript location, never both. The unused field is
explicitly `null`. `learner_authored` is exact learner text or `null`;
`agent_inference` is a separate summary/certainty object or `null`, never a
substitute for the learner's words. The rubric always names all six dimensions,
using `null` where no dimension was scored. Its primary dimension and overall
score must agree with `result`; `correct` is derived from the executable `0.8`
threshold rather than supplied independently.

Each `source_provenance` entry binds both the stable source ID and the exact
version/date registered in `sources.json`. Source-based invalidation requires
that same pair, so withdrawing one version cannot silently invalidate a newer
version with the same source ID. Export revalidates the references and includes
the source library, its digest, each active source-record digest, and the active
event IDs supported by that record in `manifest.json`.

Use `null` rather than invented precision. Do not record keystroke-level or response-time data unless it serves an explicit, consented purpose.

The observation caller must supply `content_id`, `objective_id`, and the actual
tutor/model/prompt version or content digest. The engine validates and preserves
those values; it does not derive them from the concept or replace them with its
own runtime version. Accepted timestamps are normalized to UTC with exactly six
fractional-second digits (`YYYY-MM-DDTHH:MM:SS.ffffffZ`). Projection order is by
the represented instant, not by the input timestamp spelling.

## Concept state

Represent each dimension separately:

```json
{
  "confidence": 0.875,
  "concept_id": "composite-index-prefix",
  "contradictions": [],
  "dimensions": {
    "recognition": {"estimate": 0.9, "evidence_ids": ["evt-11111111111111111111111111111111"]},
    "recall": {"estimate": 0.85, "evidence_ids": ["evt-22222222222222222222222222222222"]},
    "explanation": {"estimate": null, "evidence_ids": []},
    "application": {"estimate": null, "evidence_ids": []},
    "discrimination": {"estimate": null, "evidence_ids": []},
    "transfer": {"estimate": null, "evidence_ids": []}
  },
  "evidence_ids": [
    "evt-11111111111111111111111111111111",
    "evt-22222222222222222222222222222222"
  ],
  "higher_order_evidence_ids": [],
  "last_updated": "2026-08-03T12:40:00.000000Z",
  "status": "developing",
  "status_reason": "Independent evidence spans dimensions but lacks an unassisted higher-order item.",
  "unassisted_dimensions": ["recall", "recognition"]
}
```

### Current executable status vocabulary

- `emerging`: partial or highly scaffolded evidence;
- `developing`: some independent evidence but incomplete dimensions or contradictions;
- `provisional`: multiple independent demonstrations without later-session confirmation;
- `durable`: later-session unassisted recall plus independent evidence in at
  least two dimensions, including application, discrimination, or transfer.

The projection materializes only concepts that have at least one active
observation. A concept with no usable evidence is therefore absent; it does not
carry a stored `unobserved` status. A correction or explicit version
invalidation excludes the superseded observation from the current projection
while its observation and compensating event remain in `sessions.jsonl`; the
current implementation does not emit a stored `stale` status.

Status is an explainable convenience, not a psychometric fact.

### Current executable update rules

- Treat an unassisted score of at least `0.8` as positive independent evidence.
- Reduce the weight of evidence as hint level rises, with a nonzero floor.
- Give application, discrimination, and transfer evidence a modestly higher
  weight than recognition, recall, or explanation evidence.
- Keep observations below `0.6` visible as contradictions and prevent them from
  supporting a durable status.
- Require independent evidence in at least two dimensions, at least one
  higher-order item, and recall in a later session after higher-order evidence
  before emitting `durable`.
- Rebuild from active observations after a correction or explicit invalidation
  instead of rewriting historical events.
- Never treat a model-generated estimate as ground truth.

The current algorithm does not apply time decay by itself. Materializing
`unobserved` or `stale`, adding time decay, or changing the aggregation model
requires a versioned schema/algorithm migration and new replay tests. BKT or
another interpretable model remains a possible future extension only after
calibration and held-out evaluation. Predictive accuracy alone would not show
that model-driven adaptation improves learning.

## Misconceptions

Use this shape:

```json
{
  "claim": "Column order does not matter in a composite index",
  "concept_id": "composite-index-prefix",
  "evidence_ids": ["evt-33333333333333333333333333333333"],
  "last_tested": "2026-08-03T12:45:00.000000Z",
  "learner_confirmed": false,
  "misconception_id": "mis-0123456789abcdef01234567",
  "provenance": ["tutor_inference"],
  "state": "suspected"
}
```

### Current executable misconception vocabulary

- `suspected`: one active observation contains the exact claim and learner
  reasoning;
- `supported`: two or more active observations for the same concept contain the
  exact claim.

Every claim records `learner_reported` or `tutor_inference` provenance. Tutor
inferences default to unconfirmed and cannot be relabeled learner-confirmed;
only an explicit learner report can be confirmed. A learner rejection appends a
separate auditable event and excludes that supporting observation from the
current misconception projection without rewriting the original observation.
The claim remains projected when other active, unrejected observations still
support it.

The current projection does **not** automate `repairing`, `resolved`, or
`recurred` states. Targeted practice and later transfer can still be recorded as
ordinary evidence, but the system does not infer those misconception lifecycle
labels. Adding them would require explicit evidence-transition rules, schema and
algorithm versioning, replay tests, and a migration; until then they are future
extension guidance, not implemented behavior.

## Review scheduling

Keep item scheduling separate from concept state.

Scheduler input:

- item ID/version;
- actual correctness or rubric result;
- response independence and hint level;
- prior schedule state;
- desired retention horizon;
- learner override.

Scheduler output:

- due time;
- target retention probability if the scheduler exposes one;
- chosen performance rating and its derivation;
- reason;
- algorithm/version.

The current adapter maps observed performance in this order: a score below
`0.8` is `Again`; at or above `0.8`, hint level `3` or higher is `Hard`; an
otherwise unassisted application, discrimination, or transfer score of at least
`0.9` is `Easy`; and every remaining score at or above `0.8` is `Good`. These
are transparent engineering thresholds, not learner-outcome evidence or a
claim of optimal scheduling.

Never turn “the learner seemed comfortable” into a scheduler rating. The
executable scheduler requires the pinned tested FSRS implementation and fails
clearly when it is unavailable; it never substitutes an unlabeled heuristic.
Review replay re-invokes that pinned implementation and compares the complete
card and review-log transition. Item IDs have stable concept/dimension bindings,
card IDs are deterministic, review time is monotonic, and learner-disabled
review scheduling rejects new reviews without changing the log.

Scheduler event version `2` accepts only a validated, active observation event
ID. Under the learner-workspace lock, the scheduler derives item/version,
concept, objective, content/version, session, dimension, score, hint level,
source/version references, and tutor/model/prompt provenance from that exact
observation. A caller cannot submit a second free-form performance description,
and one observation cannot create two FSRS reviews. Each stored review carries
the complete minimal causal snapshot, which must continue to match the
referenced observation during validation and replay.

Correcting or invalidating an observation atomically replaces the evidence log,
review log, and projections. It removes a review derived from that observation
and every later review, snooze, or reschedule for the same item because those
rows depend on the removed card transition. Global learner review-enable/disable
choices remain separate. Scoped event or session deletion uses the recorded
observation/session link instead of guessing and applies the same causal-suffix
rule.

## Consent and correction

Before state creation, resolve the exact workspace and obtain consent. Show material updates at session close.

Support these operations:

- show my learner model;
- explain why a concept has this status;
- correct this inference;
- mark this note as learner-authored;
- retest this concept;
- export my data;
- delete this exact item, session, concept inference, or all state;
- disable persistence or review scheduling.

Withdrawing persistence consent records the withdrawal reason and time, sets
`persistent_state` to false, and then blocks new evidence, correction,
invalidation, projection, review, and scheduler writes. It does not erase data
already stored. Inspection, export, scoped deletion, and full-state deletion
remain available so the learner is not locked out of control after withdrawal.
Export derives projections in memory and performs no workspace write after
withdrawal.

On POSIX, a state operation holds verified workspace and state-directory
descriptors for the full workspace-lock scope. State reads and atomic
replacements use those descriptors and revalidate the lexical parent
generation, so an ancestor rename or symlink swap cannot redirect a control or
evidence write into another learner workspace.

Scoped deletion must preview not only the selected observations but also
dependent events, required invalidation rewrites, and matching review records.
For unchanged input, confirmation returns the identical plan before persisting
a private, content-bound deletion journal and replacing the evidence log,
review log, and both projections. A later locked operation idempotently
completes an interrupted journal, including after persistence withdrawal, so a
partially applied deletion cannot strand a removed concept in a stale
projection. Full deletion separately previews counts and a non-revealing
SHA-256 fingerprint of the exact workspace tree, and rejects symlinks or
non-regular entries before removing that workspace. Confirmation first writes
a private parent-side tombstone bound to the original path, deterministic
quarantine path, workspace device/inode, and preview plan. It then renames the
workspace into that quarantine. If interruption occurs at any point during
recursive removal, a retry under the parent-generation lock finishes deleting
the same bound generation—even if only part of the tree remains—and removes the
tombstone last. A partially deleted quarantine is never restored to the live
workspace path. A preview is not a lock;
compare the confirmation plan whenever state may have changed between the two
commands. If backups or external exports exist, explain their retention
separately.

Deletion previews name the causal observation/session/concept/item matching
basis, every scheduler row in the dependent same-item suffix, and the remaining
event/review counts. Confirmation revalidates that exact plan before the
content-bound transaction replaces any state file.

## Resume and migration

On resume:

1. Resolve the intended workspace; do not guess among similar paths.
2. Validate schema versions and JSON/JSONL parseability.
3. Read consent scope before other state.
4. Summarize the goal, due reviews, recent evidence, uncertainty, and conflicts.
5. Start with a due retrieval or current-goal check, not a long recap.
6. Update only after new observable evidence.

On schema migration:

- back up the exact state files;
- migrate deterministically with a versioned script;
- preserve event IDs and provenance;
- emit a migration report;
- validate invariants;
- let the learner inspect changes.

Scheduler event version `1` cannot be migrated automatically because it lacks
the observation, session, content, source-version, and tutor/model/prompt
provenance needed to establish causality truthfully. This candidate rejects v1
review rows. A learner-controlled migration must back up the workspace and
regenerate review state only from still-valid observation events; it must not
infer or fabricate the missing link.

Do not silently reconstruct missing history from model memory.

## Validation invariants

- Every concept evidence ID exists in `sessions.jsonl`.
- Every inferred status has a non-empty reason.
- `durable` includes later-session, unassisted evidence.
- Learner-authored and agent-inferred fields never share the same storage slot.
- Every misconception links to an observation of reasoning, not only a wrong choice.
- Every review decision records algorithm/version and an exact active
  observation-event input, including session/content/item/source/model/prompt
  versions; the stored snapshot matches that observation and is used at most
  once.
- Each observation item ID has one concept/objective/content/dimension binding,
  and each item-ID/version pair has one content digest.
- Review card IDs match their item IDs; stored FSRS transitions replay exactly.
- No durable state exists without consent metadata.
- Timestamps, IDs, and schema versions are valid and unique where required.
- Explicit source, content, or item-version invalidation leaves an auditable
  event and excludes matching evidence from the current projection; it does not
  assign a `stale` status.
