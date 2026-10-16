# Lost-update lesson

## Learner turn 1

Create a focused lesson that teaches me to diagnose a two-thread lost update. Include an unseen transfer task and do not reveal its answer before my attempt.

## Tutor turn 1

We’ll build one skill: given a two-thread execution trace, identify the lost update, distinguish expected from observed state, and name the synchronization point that would prevent it. I’ll give an unseen transfer task after your first attempt.

### First diagnosis

`counter` starts at `0`. Each thread runs `counter = counter + 1`, whose read and write are separate:

```text
T1: read counter → 0
T2: read counter → 0
T1: write counter ← 1
T2: write counter ← 1
```

What should the final value be if both increments take effect, what value was actually observed, and where exactly was the update lost?

If you’re unsure, say so and explain what part is unclear.

## Learner turn 2

The final value should be 2, and I think it was observed as 2 because both threads performed an increment. I do not see where an update was lost.

## Tutor turn 2

Your expected value of **2** is correct. The gap is in tracing the observed writes: focus on the value each thread read before it wrote, especially the final write.

**Hint:** Did either thread read the other thread’s newly written `1`?

Revise your diagnosis: what value does the final write use, and which increment does that overwrite?

## Learner turn 3

Neither thread read the other's 1; both read the old 0 and each computed 1. T2's final write stores 1 again, overwriting T1's completed increment. The observed value is 1, so T1's increment was lost.

## Tutor turn 3

Correct. You identified the complete failure:

- Expected: `2`
- Observed: `1`
- Cause: both threads computed from stale `0`; T2’s final write replaced T1’s result.

The diagnostic rule is: trace each **read → compute → write**. If two threads read the same old value and one later writes a result based on that stale value, a lost update occurred. The fix must make the whole read-modify-write operation atomic, such as with a lock or database transaction.

### Guided practice

Initial balance: `50`

```text
T1: read 50
T2: read 50
T1: compute 70       # deposit 20
T2: compute 40       # withdraw 10
T1: write 70
T2: write 40
```

What final balance should result if both operations apply, what balance was observed, and whose update was lost?

## Learner turn 4

If both operations apply, the balance should be 60. The observed balance is 40 because T2 writes last from its stale read of 50. T1's deposit of 20 was lost when T2's write replaced 70 with 40.

## Tutor turn 4

Exactly right. Your guided diagnosis was accurate and independently reasoned from the trace.

### Unseen transfer task

An API stores `likes = 100`. Two requests each run `likes = likes + 1`:

```text
Request A: read 100
Request B: read 100
Request B: write 101
Request A: write 101
```

Diagnose this trace: state the expected final value, observed final value, whether a lost update occurred, and the evidence from the read/write order.

## Learner turn 5

The expected value is 102, but the observed value is 101, so one update was lost. Both requests read the same old 100; B wrote 101, then A wrote its own 101 from that stale read, replacing B's completed increment instead of building on it.

## Tutor turn 5

Correct. You transferred the rule to a new context:

- Expected: `102`
- Observed: `101`
- Lost update: B’s increment, overwritten by A’s stale write.

Lesson close:

- Outcome met: you diagnosed expected vs. observed state, identified stale reads, and named the overwritten update.
- Evidence: correct guided application and unassisted transfer. The first diagnosis used one hint, so this is strong evidence—not yet durable mastery.
- Learner-authored rule: “Both requests read the same old value; a later stale write replaces a completed increment.”
- Remaining uncertainty: none observed in this lesson; broader confidence needs another retrieval.
- Files/state changed: none.
- Next retrieval: retry one fresh trace in about **3 days** (provisional horizon), without hints.
