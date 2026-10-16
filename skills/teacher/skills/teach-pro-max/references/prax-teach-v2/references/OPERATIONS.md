# Operations and evidence guide

This page is the executable companion to the teaching policy. It separates a
capability being documented, implemented, exercised against a real dependency,
evaluated, and scientifically supported.

## Runtime profiles

| Profile | Install | Use |
|---|---|---|
| Teaching kernel | Python standard library | Mode and visual routing; consented learner evidence; correction, export, and physical deletion |
| Durable review | `uv sync --frozen --python 3.12` | The teaching kernel plus the pinned real `fsrs==6.3.1` scheduler |
| Artifact authoring | `npm ci` with Node 22 | Sanitized deterministic Markdown-to-HTML rendering |
| Flint chart build | `npm --prefix integrations/flint ci` | Optional pinned Flint SVG/spec/table compilation after the visual router chooses a chart |
| SkillOpt research | Exact SkillOpt 0.2.0 source commit plus its isolated environment | Offline proposal generation; never automatic adoption |

Quick mode has no persistence or optional-integration dependency. Missing FSRS,
Flint, or SkillOpt must fail clearly at that boundary; it must not degrade into
an unlabeled substitute.

## Route before creating state

```bash
python3 scripts/prax_teach.py route \
  --request "Explain database indexes in two minutes"

python3 scripts/prax_teach.py visual-route \
  --job "Compare a distribution across twelve groups" \
  --exact-quantitative
```

The first command selects `quick`, `lesson`, or `course`. The second selects
`none`, `static`, `interactive`, or `motion`. A result that says Flint is
eligible never says Flint is required.

After rendering a durable retrieval or visual artifact, verify the delivered
bytes rather than treating the route decision as evidence:

```bash
python3 scripts/prax_teach.py visual-verify \
  --route-output /absolute/path/to/route.json \
  --source /absolute/path/to/lesson.md \
  --html /absolute/path/to/lesson.html \
  --forbidden-answer-file /absolute/path/to/forbidden-answer.json \
  --receipt /absolute/path/to/visual-receipt.json
```

Use `--check` to recompute a frozen receipt. The command scans the exact source,
generated HTML, accessibility text, hidden/default surfaces, and linked textual
assets; checks structural/static-fallback integrity; and fails closed on
opaque, animated, remote, executable, stale, or answer-leaking delivery. For a
Prax Visual Lab route it reruns the packaged runtime verifier and also checks
the complete static fallback. Arbitrary external interactive, animation, or
video runtimes remain unverified until their own bounded inspection path runs.

The automated leakage check is limited to declared textual answers. It records
semantic visual leakage through geometry, color, emphasis, or layout as
`manual_review_required` rather than pretending to evaluate meaning.

## Create a learner workspace only after consent

Explain the stored scope, location, purpose, and inspect/correct/export/delete
controls before invoking `init`.

```bash
python3 scripts/prax_teach.py init /absolute/path/to/learning-workspace \
  --learner-id learner-local-1 \
  --goal "Apply index-selection principles to unseen workloads" \
  --horizon-days 30 \
  --consent \
  --timestamp 2026-08-04T10:00:00Z
```

Without `--consent`, the command exits before creating the workspace or its
parents. The initialized directory and state files use private permissions. A
consented initialization creates the stable `lessons/`, `reference/`,
`assets/`, and `state/` structure; the first three remain empty until reviewed
course material is added. Every resumed operation rechecks the workspace and
state directory permissions, required state-file type and permissions, and
every caller-controlled path ancestor without following symlinks. It fails
closed instead of silently changing permissions. Required state and lock files
must also have one filesystem link, so a hardlink cannot alias another
learner's bytes. A parent-generation lock plus post-lock inode checks prevents
a blocked operation from being redirected when a workspace pathname is reused.
During the complete locked operation, held workspace and state-directory
descriptors bind reads and atomic replacements to the validated generation;
renaming an ancestor and replacing it with a symlink therefore fails closed
instead of redirecting a learner-state write into another workspace.

## Record and rebuild evidence

Register the exact reviewed source version before any observation refers to it.
Repeat `--supports` for each claim, concept, or item ID the source supports:

```bash
python3 scripts/prax_teach.py source-add /absolute/path/to/learning-workspace \
  --source-id postgres-index-docs \
  --title "PostgreSQL multicolumn indexes" \
  --url https://www.postgresql.org/docs/18/indexes-multicolumn.html \
  --author-or-publisher "PostgreSQL Global Development Group" \
  --source-type official-doc \
  --retrieved-at 2026-08-04 \
  --version-or-date PostgreSQL-18-2026-08-04 \
  --license-or-use-note "Official documentation; cite and link." \
  --supports composite-index-prefix \
  --limitations "Database-specific behavior still requires its own documentation."
```

This writes the canonical, sorted `state/sources.json` registry. The curated
`RESOURCES.md` is its human-readable companion, not a substitute for the
machine record. A material source change gets a new `version_or_date`; existing
records and observations retain their old binding.

```bash
python3 scripts/prax_teach.py observe /absolute/path/to/learning-workspace \
  --response "The range column should follow the equality prefix." \
  --session session-1 \
  --concept composite-index-prefix \
  --dimension application \
  --score 0.9 \
  --hint-level 0 \
  --item application-1 \
  --item-version v1 \
  --content-version sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --source-id postgres-index-docs \
  --source-version PostgreSQL-18-2026-08-04 \
  --timestamp 2026-08-04T10:05:00Z

python3 scripts/prax_teach.py rebuild /absolute/path/to/learning-workspace
python3 scripts/prax_teach.py show /absolute/path/to/learning-workspace
```

Use `--response` for the exact inline learner answer or `--response-ref` for an
exact consented artifact/transcript reference; the options are mutually
exclusive and one is required. Observation records also preserve a six-field
rubric, optional exact learner-authored note, and separately labeled optional
agent inference. Every evidence append or rebuild first persists a
content-bound state transaction covering `sessions.jsonl`, `concepts.json`, and
`misconceptions.json`. A later locked operation completes an interrupted
transaction only when each current file matches its recorded preimage or exact
target; divergent bytes fail closed. Recovery runs before consent withdrawal,
so an interruption cannot leave projections unreadable after persistence is
disabled. Append also rejects an unknown source ID or version before changing
the log or projections.

`sessions.jsonl` is append-only evidence. `concepts.json` and
`misconceptions.json` are deterministic projections. A durable mastery state
requires multiple dimensions, an unassisted higher-order response, and later
session retrieval; one response cannot produce it.

The current concept projection contains observed concepts only and emits
`emerging`, `developing`, `provisional`, or `durable`. No record means no active
evidence; it is not a stored `unobserved` state. Corrections and explicit
version invalidations retain their compensating events but remove superseded
observations from the current projection rather than emitting a `stale` state.
The misconception projection emits only `suspected` for one active supporting
observation and `supported` for two or more. It supports auditable learner
rejection, but it does not yet infer repair, resolution, or recurrence states.

Use `correct` for a compensating correction. Invalidate one exact content
version, optionally combined with an item or source selector, without
invalidating newer content that uses the same source:

```bash
python3 scripts/prax_teach.py invalidate-version \
  /absolute/path/to/learning-workspace \
  --content-version sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --reason "This content version was withdrawn" \
  --timestamp 2026-08-04T10:10:00Z

python3 scripts/prax_teach.py invalidate-version \
  /absolute/path/to/learning-workspace \
  --source-id postgres-index-docs \
  --source-version PostgreSQL-18-2026-08-04 \
  --reason "This exact documentation snapshot was withdrawn" \
  --timestamp 2026-08-04T10:10:00Z
```

The command appends a compensating invalidation event containing the exact
matching observation IDs and rebuilds the current projections. It fails when
the digest is malformed, no observation matches, or every match was
already invalidated. A local `--item-version` such as `v1` is never treated as
globally unique: it is accepted only together with `--item`. Correction,
invalidation, and misconception-rejection timestamps must be no earlier than
every observation they compensate; replay enforces the same causal invariant.
Likewise, `--source-id` requires `--source-version`; a source ID alone is never
a cross-version invalidation selector.
An observation item ID remains bound to one concept, objective, content ID, and
evidence dimension; each item-ID/version pair remains bound to one exact
content digest. A changed content digest therefore requires a new item version.

Export the inspectable learner workspace to an external path:

```bash
python3 scripts/prax_teach.py export \
  /absolute/path/to/learning-workspace \
  /absolute/path/to/learner-export.zip \
  --timestamp 2026-08-04T10:20:00Z
```

Export validates the complete source library and every event reference before
writing the ZIP. It includes `RESOURCES.md`, `state/sources.json`, and a
`manifest.json` provenance section binding the source-library digest, every
active source-record digest, and the active event IDs supported by that record.
An unresolved active source reference fails closed and leaves no export.

Preview scoped physical deletion before confirming it:

```bash
python3 scripts/prax_teach.py delete \
  /absolute/path/to/learning-workspace \
  --concept composite-index-prefix \
  --dry-run

python3 scripts/prax_teach.py delete \
  /absolute/path/to/learning-workspace \
  --concept composite-index-prefix \
  --confirm

python3 scripts/prax_teach.py delete \
  /absolute/path/to/learning-workspace \
  --item index-prefix-transfer-2 \
  --dry-run
```

The preview reports selected event IDs, dependent correction, rejection, or
invalidation events that must also be removed, partially affected invalidation
events that must be rewritten, matching review records that must be scrubbed,
and the remaining event/review counts. Confirmation first persists a private,
content-bound deletion journal containing the complete retained target state,
then replaces both logs and both projections. If interruption occurs between
replacements, the next locked state operation idempotently completes the same
transaction even after persistence consent was withdrawn; the journal is
removed only after every target byte is verified. Confirmation returns the same
plan when the input state has not changed. A preview is not a reservation: if
another process changes the workspace before confirmation, compare the newly
returned plan instead of assuming the earlier preview still applies. A concept
selector can remove review-only state even when no observation exists. An exact
item selector removes only that item's evidence and reviews. A control event
without a concept is removed only when an earlier retained review no longer
owns that item. Scheduler event version 2 binds every review to its exact
observation event, session, concept, content/item/source versions, and
tutor/model/prompt version. Event- and session-scoped deletion therefore match
reviews by causal provenance instead of guessing. Removing a linked review also
removes every later review/control suffix for that item, because those FSRS card
transitions depend on the removed transition. The preview exposes the exact
`review_match_basis` and all causally dependent rows before confirmation.

## Withdraw persistence or delete all state

Withdraw consent for future persistent learning writes while retaining the
existing data long enough to inspect, export, or delete it:

```bash
python3 scripts/prax_teach.py disable-persistence \
  /absolute/path/to/learning-workspace \
  --reason "Learner withdrew consent" \
  --timestamp 2026-08-04T10:15:00Z
```

This one learner-authorized control write sets
`consent.persistent_state: false` and records `disabled_at` and
`disable_reason`. It is not deletion. Subsequent observation, correction,
misconception-rejection, invalidation, projection-rebuild, review, and scheduler
mutation commands fail because active persistence consent is absent. `show`,
`export`, scoped `delete`, and `delete --all-state` remain available. The
current CLI has no in-place persistence re-enable operation. Export validates
and derives projections in memory; it does not rebuild or replace any learner
workspace file after withdrawal.

Preview and then remove the one exact validated workspace:

```bash
python3 scripts/prax_teach.py delete \
  /absolute/path/to/learning-workspace \
  --all-state \
  --dry-run

python3 scripts/prax_teach.py delete \
  /absolute/path/to/learning-workspace \
  --all-state \
  --confirm
```

The preview names the resolved workspace and returns file/directory counts plus
a SHA-256 fingerprint of the complete relative-entry, mode, size, and content
inventory without echoing potentially sensitive filenames. Confirmation
recomputes the plan, writes a private parent-side tombstone bound to the exact
original path, deterministic quarantine path, workspace device/inode, and
plan, then renames that workspace into the quarantine and uses the platform's
symlink-safe recursive deletion. The tombstone is removed only after the
quarantine is gone. A retry under the parent-generation lock therefore finishes
the same confirmed deletion after interruption—even when recursive removal
already deleted part of the tree—without restoring partial learner state to the
live path. A symlink or non-regular entry anywhere in the original tree blocks
confirmation. An unchanged workspace produces an identical preview and
confirmation plan; as with scoped deletion, compare the returned plan if the
tree could have changed between commands.

## Schedule review with the real FSRS adapter

Use the locked environment so the scheduler cannot silently fall back:

```bash
.venv/bin/python scripts/prax_teach.py review /absolute/path/to/learning-workspace \
  --observation-event evt-3769e2077bb08a470f12c9a13e4f1d48

.venv/bin/python scripts/prax_teach.py due /absolute/path/to/learning-workspace \
  --at 2026-08-12T12:00:00Z
```

The command accepts no caller-authored score, hint, dimension, item, source, or
time. Under the learner-state lock it resolves one active, unused observation,
verifies its content/source/model provenance, derives the performance inputs,
and atomically appends the version-2 scheduler transition through the same
content-bound state journal. The review log records the observation snapshot,
derived rating and reason, package/algorithm version, FSRS card transition,
review log, and due time. The observation remains concept-mastery evidence;
scheduling is a separate derived domain with an immutable causal link.

The learner can `snooze`, `reschedule`, `disable-reviews`, `enable-reviews`, or
export the queue. While review scheduling is disabled, a new `review` is
rejected without changing the log; learner control actions remain available,
and `enable-reviews` explicitly restores scheduling. Per-item review time is
monotonic, one observation can schedule at most once, and an item remains bound
to one concept, objective, content, dimension, source set, and model/prompt
version throughout its review history. Card IDs are deterministically derived
from the item ID, card fields and timestamps are range-checked, and replay
invokes the pinned FSRS version again to reject a content-bound but forged
transition.

Scheduler event version 1 is rejected. It lacks the observation and provenance
needed for a truthful automatic migration, so the candidate does not fabricate
those links. Back up an affected learner workspace and regenerate review state
only from still-valid observations.

The executable rating derivation is ordered and explicit:

- score below `0.8` becomes `Again`;
- otherwise, hint level `3` or higher becomes `Hard`;
- otherwise, an unassisted application, discrimination, or transfer response
  scoring at least `0.9` becomes `Easy`;
- every remaining score of at least `0.8` becomes `Good`.

Thus a score from `0.6` through `0.79` is not treated as successful review
performance. These thresholds are the tested adapter policy, not a claim that
they are optimal for real learners.

The adapter derives a horizon-specific FSRS configuration from the consented
goal: target retention is stricter for near-term horizons and relaxes only
within a bounded policy for longer horizons; `maximum_interval` is capped at
the learner's horizon and fuzzing is disabled. Every review receipt records the
policy version, requested horizon, desired retention and cap. This is an
engineering scheduling policy, not evidence that the chosen schedule is
optimal for real learners.

## Render and validate instructional artifacts

```bash
SOURCE_DATE_EPOCH=1785844800 node scripts/render_markdown.mjs \
  --trusted-root /absolute/path/to/workspace \
  /absolute/path/to/workspace/lesson.md
SOURCE_DATE_EPOCH=1785844800 node scripts/render_markdown.mjs \
  --check \
  --trusted-root /absolute/path/to/workspace \
  /absolute/path/to/workspace/lesson.md
python3 scripts/validate_workspace.py /absolute/path/to/workspace
```

Markdown is canonical. Rendering uses pinned Marked plus an allowlist sanitizer,
then writes atomically. `--check` compares the entire expected byte stream, not
only the embedded source hash.

## Compile an optional Flint chart

```bash
SOURCE_DATE_EPOCH=1785844800 node integrations/flint/render_flint.mjs \
  --input fixtures/flint/retrieval-by-session.flint.json \
  --output-dir /absolute/path/to/chart-output \
  --backend vegalite \
  --trusted-root /absolute/path/to
```

The adapter accepts reviewed inline rows only, disables file references,
rejects unresolved compiler or renderer warnings, and emits the original Flint
source, separately editable prepared data and semantic spec, SVG, backend spec,
semantic table, hashes, versions, normalized invocation/API, explicit known
limitations, and an explicit no-chart-correctness claim. `SOURCE_DATE_EPOCH` is
required so `generated_at` is non-null and reproducible.
The durable manifest reports network isolation as unverified unless an external
trace actually measured it; it never infers isolation from the absence of a URL.

## Export reviewed learning items

One reviewed item model can produce deterministic formats:

```bash
python3 scripts/export_learning.py export anki items.json exports/items.txt
python3 scripts/export_learning.py export qti items.json exports/qti.zip
python3 scripts/export_learning.py export liascript items.json exports/lesson.md
python3 scripts/export_learning.py export h5p items.json exports/activity.h5p
```

Anki output is official text-import format, not a falsely labeled `.apkg`. QTI
and H5P outputs are bounded ZIP packages. The H5P export is a thin content
package and still requires a compatible H5P host runtime.

## Prepare SkillOpt without touching the candidate

```bash
python3 integrations/skillopt/prepare_source.py \
  --source /absolute/path/to/SkillOpt-at-e4ea6a6 \
  --destination /absolute/path/to/new-prepared-clone
```

The command verifies the exact source commit, copies only tracked Git blobs into
a new clone without Git or cache state, adds the adapter, and registers it in
both `scripts/train.py` and `scripts/eval_only.py`. Public train and
`valid_seen` selection data form the optimizer-visible interface. External
`valid_unseen`, test, and OOD banks stay outside the target package and are run
only through the package-owned measured macOS sandbox executor (or a separately
trusted equivalent).

After a real run, `stage_proposal.py` validates an exact score structure and
byte bindings, then writes a separate quarantined `SKILL.md`. The supplied score
JSON remains self-attested: the quarantine receipt is explicitly ineligible for
evidence or adoption until the proposal is independently rerun through the
trusted isolated evaluator with repeated trials and cross-model gates. The
helper never edits the base skill and never adopts a proposal.

## Run agent and learner-study machinery

`scripts/evaluate.py` plans randomized paired runs, executes each arm in a fresh
read-only package clone and workspace, and applies hard gates before soft score.
The trusted macOS executor uses a default-deny `sandbox-exec` profile and
measured adversarial probes for hidden/candidate/source reads, outside writes,
and network access. Claim-bearing runners must use the package-selected Xcode
Python with exact `-I -S` isolation flags. The evaluator hashes the complete
root-owned Python framework closure before and after all runs and binds that
digest into every result, receipt, manifest, and report; an undeclared local
import therefore hard-fails instead of silently expanding the runner. A real
provider requires a separate trusted broker outside the target sandbox. Bundled
fixtures and the durable sandbox smoke remain public containment-mechanism
tests, never candidate-quality or held-out proof.

The `run` command writes `results.jsonl`, per-run receipts, `report.json`, and
`manifest.json` as one atomic archive. The manifest hashes the report and the
canonical receipt set; the report binds the spec, hidden-bank digest, target
package, matrix, runner, sandbox/probe evidence, results, and receipts. Only
that same-run report can carry a held-out candidate-quality claim. The
standalone `report` command is intentionally unable to authenticate or promote
held-out JSONL.

`scripts/study.py` validates a frozen parallel study protocol and creates seeded
user-level assignments and HMAC-blinded assessment IDs. `allocate` requires the
external private `--blinding-key` and the external `--task-bank` whose bytes
match `protocol.task_bank_hash`. The private allocation rows carry a set-level
HMAC over every assignment plus the exact participant-roster and task-bank
hashes. `analyze` requires that same key and task bank plus `--participants`;
it rebuilds and authenticates the complete allocation before consuming scores.
Changing an arm, baseline, instruction timestamp, learner, assessment ID,
allocation count, roster, key, task bank, or protocol/task-bank binding fails
closed. Keep all three authority inputs outside the teaching workspace. On
POSIX, create the blinding key under a private non-symlink directory, make it
current-user owned, and apply `chmod 600`; public key modes, writable ancestors,
and symlinked ancestors are rejected before any output is written.

The external task bank must conform to
`schemas/study-task-bank.schema.json`, cover both primary outcomes, and use
unique task IDs. Each JSONL score must conform to
`schemas/study-score.schema.json`; its task, outcome, and rubric reference must
agree with that bank. The analysis receipt records both raw and canonical score
hashes plus the score-schema hash and non-secret task/rubric bindings. Score
file order cannot change the analysis. Identical repeated assessment/outcome
rows are deduplicated and counted; any conflicting repeated row blocks report
creation. Output publication is descriptor-anchored, so replacing the report
parent with a symlink during publication fails closed.

The primary estimand is intention-to-treat: every assigned learner remains in
the analysis and a missing outcome uses the predeclared zero-adjusted-change
policy; complete-case results are sensitivity analysis only. Bootstrap
resampling occurs at learner level. Synthetic inputs always retain
`supports_human_learning_claim: false`.

## Bind forward behavior and independent review

The public forward rubric is frozen at `evals/forward-behavior.json`. Run each
case in a separate fresh context, preserve the exact learner-facing output under
`evidence/forward/outputs`, and bind every output plus the instructional sources
in `evidence/forward/run.json`. A separate reviewer scores every required and
forbidden item. All eight cases must pass the non-compensatory hard gate; failed
attempts remain under `evidence/forward/attempts` and cannot be overwritten as if
they never happened. These runs test tutor behavior only, not comparative or
human learning outcomes.

After features, status documents, generated HTML, and inspection evidence are
final, freeze the exact review surface:

```bash
python3 scripts/review_payload.py . \
  --output evidence/reviews/payload.json
python3 scripts/review_payload.py . \
  --output evidence/reviews/payload.json \
  --check
```

The manifest excludes only the review receipts themselves, the full verification
receipt, Git metadata, and runtime/cache directories. Code/standards, frozen-spec,
and architecture-council receipts must all bind the same payload hash, close every
actionable finding, and record an independent recheck. Any later durable edit
invalidates the payload and all three reviews.

Each receipt records the orchestration task identity used for the review. That
is structural provenance, not cryptographic proof of who authored the review;
the required attestation keeps cryptographic authorship explicitly unverified.

## Clean full verification

From a clean candidate checkout on macOS with Node 22, `uv`, and `ruff`
available, install only the pinned locks and use the exact SkillOpt source
commit outside the package:

```bash
npm ci
npm --prefix integrations/flint ci
uv sync --frozen --python 3.12
git -C /absolute/path/to/SkillOpt-v0.2.0 rev-parse HEAD
.venv/bin/python scripts/verify.py --level full \
  --skillopt-source /absolute/path/to/SkillOpt-v0.2.0 \
  --receipt evidence/verification/full.json
```

The SkillOpt checkout must report
`e4ea6a6771e797ef820cdd8bfea64c57e0481065`. On macOS, full verification
forces the evaluator and SkillOpt adversarial `sandbox-exec` tests and rejects
any skipped Python test; a nested sandbox that cannot apply the profiles must
fail rather than produce a green release receipt. The schema-v3 receipt binds
all durable release bytes (except itself), executable modes, the verifier,
lockfiles, observed runtime versions, bounded gate summaries, log-retention
policy, and a successful final validator postflight. The validator recomputes
that binding, so a later edit makes the receipt stale.

## Candidate-local commit and immutable package

Do this only after the final Markdown/HTML set, forward receipt, frozen review
payload, three independent review receipts, schema-v3 full-verification receipt,
and final validator are current. A durable edit after payload generation
invalidates the reviews; a durable edit after full verification invalidates the
full receipt.

Initialize Git only inside the candidate, inspect the exact staged surface, and
create the reviewed commit:

```bash
git init .
git config user.name "Prax Teach v2 release"
git config user.email "prax-teach-v2@local.invalid"
git config commit.gpgsign false
git add --all
git diff --cached --check
git status --short
git commit -m "Build prax-teach-v2 engineering candidate"
git status --short
```

The final status must be empty. Do not initialize Git in the parent reports
directory and do not include private banks, learner workspaces, caches,
dependencies, or `.git` in the package.

Build from immutable blobs in `HEAD`, not from mutable working-tree bytes. Keep
the release receipt outside the committed tree so recording the commit and
archive hash cannot make the reviewed payload stale:

```bash
SHORT_SHA="$(git rev-parse --short=12 HEAD)"
SOURCE_DATE_EPOCH=1785844800 .venv/bin/python scripts/build_package.py \
  --force "../prax-teach-v2-${SHORT_SHA}.zip" \
  > "../prax-teach-v2-${SHORT_SHA}.release.json"
unzip -t "../prax-teach-v2-${SHORT_SHA}.zip"
shasum -a 256 "../prax-teach-v2-${SHORT_SHA}.zip"
```

Build a second ZIP from the same `HEAD` to a different sibling filename and
compare SHA-256 values. Inspect `PACKAGE-MANIFEST.json` inside the archive and
confirm its commit, `prax-teach-v2-reviewed-full` release gate, payload and
review bindings, full-verification binding, and absence of `.git`. The sibling
release JSON is the non-circular durable record of the commit and archive
SHA-256. No push, installation, or production replacement is implied.

## Evidence boundary

Passing every bundled test supports an engineering claim: the mechanisms exist
and their specified boundaries were exercised. It cannot establish that real
learners retain or transfer better. That stronger claim requires consented human
participants, blind unseen tasks, an appropriate delay, uncertainty reporting,
accessibility field checks, and replication.
