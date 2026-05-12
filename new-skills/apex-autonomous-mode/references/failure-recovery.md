# Failure Recovery — worked examples of the 6-tier Fallback Matrix

When a phase fails its binary acceptance criteria, APEX-CORE's Fallback Matrix gives a structured escalation path. Climb tiers only when prior tiers fail.

## Tier 1 — Reframe

Same goal, narrower scope. Half-and-defer.

**Example:**
Task: "Refactor the auth module to use dependency injection and add 20 unit tests."
Execute phase: DI refactor works but 3 tests fail flakily.
Tier 1 action: Scope the test addition to the 17 passing ones; defer the 3 flaky as a TODO in Final Summary.

**What changed:** the task scope, not the acceptance criteria.

## Tier 2 — Reroute

Different model / skill / MCP. Same intent, different machinery.

**Example:**
Task: "Generate the database migration script."
Execute phase: Sonnet 4.6 times out twice on the full schema diff.
Tier 2 action: Reroute to Opus 4.7 with the same prompt. Or invoke the `alembic-patterns` skill directly instead of prompting the model to generate migrations freeform.

**What changed:** the tooling, not the task.

## Tier 3 — Council

Invoke `llm-council-plus` with the failure trace and ASI. Multi-model deliberation resolves cases where one model has a blind spot.

**Example:**
Plan phase: contested architectural decision about where to put business logic — model's two candidate designs both look defensible.
Tier 3 action: `council decide "given these constraints: … which of design-A or design-B is correct, and why?"` Three members respond; the chairman synthesizes.

**What changed:** one model's judgment is now three models plus a synthesizer.

## Tier 4 — Decompose

Split the failing task into halves. Localize where signal is lost.

**Example:**
Execute phase: refactor touches 30 files; tests fail with a non-obvious regression.
Tier 4 action: split the change into "refactor files 1-15 only" and "refactor files 16-30 only", commit each, run tests on each half. The regression localizes to one half.

**What changed:** the bisection surface, not the task.

## Tier 5 — AcknowledgedSkip

Document the gap. Continue without this piece. Flag in Final Summary.

**Example:**
Verify phase: one acceptance criterion ("add integration test") can't be met because the test infrastructure isn't set up in this repo.
Tier 5 action: Write the test stub with `@pytest.mark.skip("integration infra TBD")`, document the skip in Final Summary's `skipped_or_deferred` field.

**What changed:** the delivered scope, with explicit disclosure.

**Critical:** tier 5 does NOT lower the criteria. The criterion still reads "integration test added". The deliverable explicitly states that criterion was NOT met, with the tier-5 tag. Never pretend a criterion was met when it wasn't.

## Tier 6 — AbortSafely

Roll back to last checkpoint. WIP-commit on `wip/<slug>-aborted-<ts>`. Postmortem. Exit `ABORTED_WITH_LEARNINGS`.

**Example:**
Execute phase: three consecutive attempts produce regressions. Tiers 1-5 exhausted. Confidence in the plan is low.
Tier 6 action:
```bash
git stash
git checkout <last-good-sha>
git checkout -b wip/<slug>-aborted-$(date -u +%Y%m%dT%H%M%SZ)
git stash pop
git commit -am "WIP: aborted task - preserving partial work for postmortem"
```
Emit Final Summary with `outcome: ABORTED_WITH_LEARNINGS` and detailed postmortem in `asi_learnings`.

**What changed:** the entire run is safely rolled back; no destructive state left; user gets a clear record of what was tried and why it failed.

## Anti-pattern: silent tier-skipping

Do NOT jump from tier 1 to tier 6 because the current step feels hard. The ratchet is about reading the signal at each tier and climbing only when necessary. Going tier 1 -> 2 -> 3 is information-gathering; tier 3 -> 6 without tier 4 or 5 is panic.

## Anti-pattern: criteria-lowering

Do NOT "reframe" by changing what the user asked for. Reframing narrows execution scope (do part A now, part B later). It does not rewrite the user's request.

Example of bad reframing: user asks "add tests covering all 20 functions"; agent says "okay, I added tests for 3 of them" without going through tier 5 with explicit acknowledgement.

## Tracking in Final Summary

Every fallback-tier usage appears in the Final Summary under `skipped_or_deferred`:

```yaml
skipped_or_deferred:
  - item: integration test for checkout flow
    reason: integration test infra not set up in this repo
    tier: 5
  - item: 3 flaky OAuth unit tests
    reason: external mock service intermittent
    tier: 1
```

This is how the human feedback loop learns what kinds of failures the codebase actually hits.
