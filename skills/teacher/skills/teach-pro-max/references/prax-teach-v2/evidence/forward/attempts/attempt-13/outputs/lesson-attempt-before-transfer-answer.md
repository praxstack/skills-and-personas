# Diagnosing a two-thread lost update

## Learner turn 1

Teach me how a two-thread read-modify-write race can lose an update. Do not give me the transfer answer before I attempt it. I want to diagnose from traces.

## Tutor turn 1

Let’s diagnose a trace before discussing the rule.

Shared `count` starts at `0`. Each thread intends to increment it once:

```text
1. T1 reads count → 0
2. T2 reads count → 0
3. T1 computes 0 + 1 → 1 locally
4. T2 computes 0 + 1 → 1 locally
5. T1 writes count ← 1
6. T2 writes count ← 1
```

What final value does this produce, and which events explain why? Give your best diagnosis—or say “I don’t know.”

## Learner turn 2

The final value is 1. Both threads read the same old 0 and compute 1; T1 writes 1 at step 5, then T2 writes its stale 1 at step 6, so one intended increment is no longer represented.

## Tutor turn 2

Exactly. You tracked both local snapshots and the stale overwrite.

The general mechanism is that the read–modify–write sequence has a gap between reading and writing. Without synchronization, both threads can compute from the same old state, so a later write can erase the effect of an earlier one.

Now try a different operation:

```text
Shared stock = 5

1. T1 reads stock → 5
2. T2 reads stock → 5
3. T2 computes 5 − 1 → 4 locally
4. T1 computes 5 − 1 → 4 locally
5. T2 writes stock ← 4
6. T1 writes stock ← 4
```

Diagnose this trace: what should `stock` be if both sales take effect, what value does the trace leave, and which event makes one sale disappear?

## Learner turn 3

If both sales take effect, stock should be 3. The trace leaves 4. T1’s write at step 6 is based on the stale read of 5 and overwrites the effect of T2’s sale, so one decrement disappears.

## Tutor turn 3

Correct. You identified both the expected result (`3`) and why the observed `4` occurs: T1 writes a value derived from stale state.

Now distinguish it from a safe ordering:

```text
x = 0

1. T1 reads x → 0
2. T1 computes 1
3. T1 writes x ← 1
4. T2 reads x → 1
5. T2 computes 2
6. T2 writes x ← 2
```

Does this trace lose an update? State the final value and the key difference from the earlier traces.

## Learner turn 4

No update is lost. The final value is 2. The key difference is that T2 reads the committed value 1 after T1 writes it, rather than computing from the same stale snapshot.

## Tutor turn 4

Correct. You distinguished serialized visibility from overlapping stale reads. Across three traces, you independently identified the expected result, stale computation, and overwriting write without hints.

Teach-back: in one sentence, what must be true about the reads and writes for a read-modify-write race to lose an update?

## Learner turn 5

An update is lost whenever the two writes overlap.

## Tutor turn 5

Trace each write back to the read that supplied its input value. Revise your sentence to describe the relationship between those reads and the later writes.

## Learner turn 6

An update is lost when multiple threads read the same stale state before either committed write is visible, compute separately, and a later write overwrites the effect of an earlier one.

## Tutor turn 6

That’s the precise rule. The writes need not happen simultaneously; they can be sequential while still being based on the same stale pre-write state.

You correctly diagnosed three traces, then corrected the teach-back after one hint. This supports accurate trace diagnosis for these examples, but not yet broad mastery across locking or atomic-operation traces.

No retention horizon was specified. For retention, revisit a fresh trace in a day or two—especially one where the updates do not conflict.
