# Lost-update lesson

## Learner turn 1

Create a focused lesson that teaches me to diagnose a two-thread lost update. Include an unseen transfer task and do not reveal its answer before my attempt.

## Tutor turn 1

Goal: diagnose a lost update from an execution trace and explain the exact conflicting operations.

We’ll work through one case, then you’ll get an unseen transfer task. Its answer stays hidden until you attempt it.

Shared balance starts at `100`:

```text
Thread A: read balance → 100
Thread B: read balance → 100
Thread A: compute 100 + 30 → 130
Thread A: write balance ← 130
Thread B: compute 100 - 20 → 80
Thread B: write balance ← 80
```

Diagnose this in one sentence: what update was lost, and which operation erased it? “I don’t know” is a valid answer.

## Learner turn 2

I think neither update was lost because both calculations completed; the final value should combine them as 110.

## Tutor turn 2

Hint 1: follow the writes, not merely the completed calculations. Thread B writes a value computed from its earlier read.

Revise your diagnosis: what value remains in shared balance, and which update is absent from it?

## Learner turn 3

The shared balance ends at 80 because Thread B writes last from its stale read of 100. Thread A's +30 update is absent, so B's write erased A's update.

## Tutor turn 3

Correct. Both calculations completed, but only Thread B’s result remained in shared memory. Its stale `100` produced `80`, which overwrote Thread A’s `130`.

A reliable diagnostic is:

1. Expand each update into `read → compute → write`.
2. Find a write based on a value that became stale.
3. Check whether that write overwrote another thread’s completed change.

Your diagnosis was correct with one hint, so this is scaffolded evidence—not yet independent transfer.

Unseen transfer task:

```text
Initial shared profile:
{ theme: "light", fontSize: 14 }

Thread A reads:
{ theme: "light", fontSize: 14 }

Thread B reads:
{ theme: "light", fontSize: 14 }

Thread A changes its copy’s theme to "dark"
Thread A writes:
{ theme: "dark", fontSize: 14 }

Thread B changes its copy’s fontSize to 18
Thread B writes:
{ theme: "light", fontSize: 18 }
```

Diagnose the final shared state and identify any update that disappeared, including the exact stale operation responsible.

## Learner turn 4

The final shared state is { theme: "light", fontSize: 18 }. Thread A's dark-theme update disappeared because Thread B wrote its whole stale copy, whose theme was still "light", after changing only fontSize. That stale full-object write overwrote A's theme change.

## Tutor turn 4

Correct. You traced the final write, identified its stale source, and caught that a whole-object replacement can erase a change to a different field.

Teach it back in your own words: why doesn’t “both threads completed their calculations” prevent a lost update, and what rule would you use to spot one in a new trace?

## Learner turn 5

Completed calculations do not protect an update because the shared result is determined by writes, and a later write can be based on a stale read. In a new trace I expand each update into read, compute, write; then I find any write derived from an older snapshot and check whether it overwrote a newer committed change.

## Tutor turn 5

Lesson outcome met with limited evidence:

- Initial diagnosis: correct after Hint 1.
- Unseen transfer: correct without hints.
- Teach-back: accurately identified stale-read-derived writes as the diagnostic signal.

Your explanation is strong, but durable recall and discrimination from other race conditions remain untested.

Retention horizon: one week (provisional). Next retrieval: one fresh, unassisted trace in three days. No files or learner state were created.
