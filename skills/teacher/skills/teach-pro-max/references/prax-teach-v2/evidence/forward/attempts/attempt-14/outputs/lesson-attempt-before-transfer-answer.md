# Diagnosing a two-thread lost update

## Learner turn 1

Teach me how a two-thread read-modify-write race can lose an update. Do not give me the transfer answer before I attempt it. I want to diagnose from traces.

## Tutor turn 1

Let’s diagnose this from one trace.

Shared value starts at `100`. T1 intends `+10`; T2 intends `−10`.

```text
1. T1 reads 100
2. T2 reads 100
3. T1 computes 110
4. T2 computes 90
5. T1 writes 110
6. T2 writes 90
```

What final value does this trace produce, and at which step does one thread’s update stop being reflected? Explain what evidence in the trace led you there.

## Learner turn 2

The final value is 90. T1’s +10 stops being reflected at step 6, when T2 writes 90 from its earlier read of 100 over T1’s committed 110; both computations used the same stale state.

## Tutor turn 2

Your diagnosis is precise: both threads computed from the same stale value, and T2’s later absolute write replaced T1’s already-written result.

The key rule is: a read-modify-write is three separate actions—read, compute, write. Without synchronization, another thread can interleave between them.

Try this new trace:

```text
Shared stock = 10
T1 intends to sell 3
T2 intends to sell 4

1. T1 reads 10
2. T1 computes 7
3. T2 reads 10
4. T2 computes 6
5. T2 writes 6
6. T1 writes 7
```

What stock remains, which sale is no longer represented, and why?

## Learner turn 3

Stock remains 7. T2’s sale of 4 is no longer represented because T1 writes 7 at step 6 from its stale read of 10, overwriting T2’s committed 6.

## Tutor turn 3

Correct. Both local calculations are valid for the value each thread read, but T1’s later write is based on an older snapshot and overwrites T2’s newer result. Both sales should leave stock at `3`; the trace leaves `7`, so T2’s update was lost.

Teach-back: in one sentence, why can both threads calculate correctly while the final shared value is wrong?

## Learner turn 4

Because the two writes happened at the same time.

## Tutor turn 4

Check the ordering: the trace gives a definite sequence for the writes. Focus on what value T1 had read before its write, and revise your sentence.

## Learner turn 5

Both threads calculate correctly from the value they read, but T1 later writes a result derived from stale 10 after T2 already committed 6, so the later stale write erases T2’s update.

## Tutor turn 5

That revision is correct: the later write was stale and erased T2’s committed update.

You diagnosed two traces and explained the mechanism. One ordering hint was needed, so this is scaffolded evidence—not yet unassisted mastery. No files or learner state changed.

Provisional retention horizon: one week. Next retrieval: diagnose a new trace and identify whether synchronization prevents the overwrite.
