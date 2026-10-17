# Lost-update diagnostic lesson

## Learner turn 1

Create a focused lesson that teaches me to diagnose a two-thread lost update. Include an unseen transfer task and do not reveal its answer before my attempt.

## Tutor turn 1

Let’s target one skill: given an interleaved trace, identify the conflicting read/write and justify the diagnosis. After your attempt, I’ll give you a separate unseen transfer case with changed details.

`counter` starts at `0`. Each thread runs `counter = counter + 1` once. Reads and writes are separate, with no synchronization:

```text
T1: read counter -> 0
T2: read counter -> 0
T1: compute 1
T2: compute 1
T1: write counter = 1
T2: write counter = 1
```

What is your diagnosis? State the final counter value and point to the exact interleaving step(s) that explain it. If unsure, say “I don’t know” and identify what you would inspect next.

## Learner turn 2

I think the final counter is 2 because each thread increments once. I do not see a lost update in that trace.

## Tutor turn 2

One hint: track the value each thread actually writes, not just the number of increment commands. Both computations begin from the same read, and the later write may replace the earlier result.

Re-read the trace and revise: after T2’s write, which increments are reflected in the stored value?

## Learner turn 3

The final counter is 1. Both threads read 0 and independently compute 1; T1 writes 1, then T2 writes the same stale result 1, so T1’s increment is no longer separately reflected.

## Tutor turn 3

Correct. The final `counter` is `1`: both threads read `0`, compute `1`, and T2’s later write stores the same stale result, so T1’s increment is not separately reflected.

The diagnostic rule is to trace each read–compute–write chain and check whether writes are based on the same prior value. You reached this after one hint; now apply it to a fresh case.

**Unseen transfer**

`stock` starts at `10`. T1 sells 3; T2 sells 4. Reads and writes are separate:

```text
T1: read stock -> 10
T2: read stock -> 10
T1: compute 7
T2: compute 6
T2: write stock = 6
T1: write stock = 7
```

What is the final `stock`, and which sale is not reflected? Explain by naming the stale read/write relationship.

## Learner turn 4

Final stock is 7. T2’s four-unit sale is not reflected: both threads read the old stock 10, T2 writes 6, and T1 then overwrites it with 7 computed from its stale read.

## Tutor turn 4

Correct. Final `stock` is `7`: T1’s later write of stale `7` overwrote T2’s `6`, so T2’s four-unit sale disappeared.

Core rule: follow each read–compute–write chain and check whether a later write is based on an older shared value. Your transfer to subtraction was correct without an additional hint—evidence of transfer on this item, not yet durable mastery.

Lesson close:

- Target met: diagnose the final value and missing update from an interleaved two-thread trace.
- Learner-authored rule: both threads read old state, compute independently, and a later write can overwrite the other result.
- Remaining uncertainty: live-code diagnosis and repair strategy were not tested.
- Provisional retention horizon: one week. Retrieve a fresh trace in 3 days, including one where the reads differ, and decide whether it is still a lost update.
- No files or learner state were changed; this remained ephemeral.
