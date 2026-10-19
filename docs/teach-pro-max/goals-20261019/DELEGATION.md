# Subscription workers and the debate, in plain terms

19 October 2026. Codex remains the integration owner. This adds a delegation
method; it does not approve new teaching rounds or change frozen evaluation.

## Objective

One general teaching skill: accurate, visually excellent, intuition-building
explanations across subjects, delivered as stills, explorers, Q&A, cards,
narrated video and interactive video. Explain first; practice is optional.
Passing checks alone does not establish world-class visual quality.

## What each session did

| Session | Useful work | Limit or mistake |
| --- | --- | --- |
| Earlier routing/council session | Reproduced video/narration routing defects and inspected packaging. | Did not render media itself; mixed product and validator/digest edits; its framed, tool-free council did not independently verify facts. |
| Claude C evaluation | Built four real C-oriented lessons and a substantial renderer/checking pipeline; improved interaction and corrected many issues. | The experiment narrowed to C. Final wording/control failures prevent calling its lessons verified. A C-only schema is a poor default for a general teacher. |
| Codex audit/orchestration | Preserved work, checked evidence, identified scope drift and selected the existing general teacher plus optional C adapter. | Earlier claimed smoke evidence was missing; that was wrong. The sibling archive preserves it. Binary archives in public Git also need a better long-term home. |
| Claude counter-review | Agreed with the architecture and corrected evidence, baseline and evaluation details. | Its four-round estimate is a proposal, not a necessity; parts of its proposed evaluator behavior already exist. |

These are tasks and evidence, not a ranking of model intelligence. None of
these sessions alone has established that the skill meets the original goal.

## The six counters and our response

1. **"The smoke reports exist."** Correct. We verified all six lesson hashes
   and 83 recorded artifacts. Four automatic passes remain claims-pending; two
   builds failed. We corrected our report rather than rebuilding to manufacture
   replacement evidence.
2. **"Large archives should not live in Git."** Agreed. They burden ordinary
   full clones. Release assets plus manifests/hashes are preferable. Rewriting
   already-pushed history is a separate approval-gated migration; nothing has
   been removed.
3. **"Hidden tests cannot be public."** Agreed. Previously published prompts
   are regression tests. Fresh cases must stay with an independent evaluator
   outside public repositories and archives; publish their digest and results.
4. **"Fixing clean controls may change the evaluator."** Agreed with the
   governance concern. Some so-called clean copies contain actual errors.
   Catching planted errors while rejecting those copies does not establish
   reviewer reliability. The code already requires the planted claim's ID to
   be rejected, but that does not prove the planted change caused rejection.
   Keep existing scores intact, diagnose paired outcomes separately and obtain
   approval before changing scoring, eligibility or thresholds. Do not remove
   difficult controls after seeing results.
5. **"Three C rounds may be too few; use four."** Plausible, not proven.
   Budget choice remains open. Privacy prerequisites apply before testing;
   privacy cannot silently move out of scope to fit a smaller budget.
6. **"Name the exact baseline."** Agreed. Preserve the release tag, restored
   checks commit and chosen source snapshot separately. A tag and a later
   repair commit are different checkpoints. Exact IDs are recorded in
   COUNTERS-RESOLUTION.md.

The independent routing session's later admission adds one useful rule: render,
operate and listen to actual output before judging media capability. Its claim
that its patch is still uncommitted is historical; it has since been saved and
pushed, without being accepted. We should not merge the validator/digest edits
or run another council merely because the old session proposed it.

## Recommended division of labor

| Owner | Work | Acceptance |
| --- | --- | --- |
| Codex | Keep scope, design the explanation, integrate the general teacher and compatible C adapter; own final judgment. | Verify source, diff, rendered behavior and media. Keep failed required criteria visible. |
| Grok CLI | Small read-only consistency reviews, bounded alternatives and source checks; later isolated implementation tasks if measured performance supports them. | Each answer checked against source or an independently run calculation; no evaluator authority. |
| Cursor Composer 2.5 | After authentication works: narrow mechanical changes, component scaffolding and running named checks in its own worktree. | Scoped diff and actual outputs; no broad architecture or evaluator decisions delegated by default. |
| Claude | Optional, scarce specialist review of C wording/semantics or a specific remaining C defect. | Small task pack and a concrete receipt. General progress must not depend on Claude quota. |

Start with one external worker at a time. Expand to two only for independent
tasks after authentication and task quality are measured. Do not repeatedly
send whole histories or create councils for work a tool can directly check.
Providers' subscription quotas are separate. Installed CLI/login status alone
does not prove an executable request works or guarantee its billing route.

## What was actually tested

See WORKER-PROBE.json. Grok, using its existing grok.com login and default
model, read a synthetic input and correctly returned its nonce and total 53.
Its JSON transport envelope parsed, but the answer text included unsolicited
prose, violating the task's strict JSON-only instruction. This is evidence of
working transport and one correct answer, not an intelligence benchmark or
permission to trust subsequent work. The response reported high context usage
for a tiny task; investigate inherited context before scaling.

Cursor status recognized an account, but model listing and two small execution
attempts failed authentication. Composer 2.5 did not produce an answer, so its
quality is unmeasured here. No auth reset, browser login, API-key fallback or
Claude call was made.

The project-local read-only launcher records stdout/stderr, hashes, timeout,
exit status and input changes. Six synthetic transport tests pass. A real
Cursor run through it correctly produced a failure receipt, not a success.
Provider read-only modes are not OS containment; see the runner README.

## Outcome and next step

Keep the existing general teacher as the base and C as an optional adapter.
The two product tracks can progress independently. Retain the old C results and
all failed evidence. Do not restart exhausted rounds or revise acceptance to
make a candidate pass.

The next product deliverable is the governing-only freeze: exact baselines,
mutable/protected paths, private evaluator ownership, fixed checks, finite
budgets and stop rule. Present that concrete version for approval before
candidate edits. Proposed caps remain four C rounds and eight general rounds,
with the general track reviewed after its first fresh qualitative lesson.
Neither cap is approved by this document. General work should not wait for the
C pack to pass.

The tradeoff is deliberate: reuse preserves substantial working media code,
while the adapter boundary prevents C assumptions from defining every subject.
Independent checks reduce self-certification but cost time and quota. CLI
workers can save implementation effort, but add authentication, context and
review overhead. A small, verifiable task is worthwhile; an unbounded parallel
conversation is not a substitute for product progress.

Nothing was installed, merged, or changed in the teaching candidate/evaluator
by this delegation work. Local process sessions and durable task/result files
are sufficient for communication. They can be resumed from receipts; continued
autonomous monitoring after this orchestrator stops is not promised.
