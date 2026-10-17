# Lost-update lesson

## Learner turn 1

Create a focused lesson that teaches me to diagnose a two-thread lost update. Include an unseen transfer task and do not reveal its answer before my attempt.

## Tutor turn 1

By the end, you’ll be able to trace a two-thread lost update, identify exactly what was overwritten, and choose a safe repair. We’ll finish with a fresh transfer task; its answer stays sealed until your attempt.

This is a live host-chat lesson with no custom controls or scripts; keyboard, focus, and assistive-technology behavior has not been independently verified.

An account starts at `100`:

```text
T1 reads balance → 100
T2 reads balance → 100
T1 subtracts 30 locally
T2 adds 20 locally
T1 writes 70
T2 writes 120
```

Each read and write is individually atomic.

**Learner action — First prediction:** What final balance is stored, and which update was lost? Reply with your reasoning, or say “I don’t know.”

## Learner turn 2

I think the final balance is 90 because both changes should combine: 100 - 30 + 20. So I don't think either update was lost.

## Tutor turn 2

Your combined arithmetic correctly gives the intended balance. Now trace the schedule rather than combining the operations.

**Hint 1:** Look only at the final two writes. What concrete value is written last, and does that value include T1’s subtraction?

Revise your answer.

## Learner turn 3

T2 writes 120 last, and that value came from T2's old read of 100, so it does not include T1's subtraction. The stored balance is 120 and T1's subtract-30 update was lost.

## Tutor turn 3

Exactly. Your revised trace is correct: the stored value is `120`, and T1’s `-30` update is overwritten. This was correct with Hint 1, so it’s scaffolded evidence rather than an unassisted diagnosis.

A lost update follows this pattern:

1. Two threads read the same old shared value.
2. Each computes a new value privately.
3. One write replaces the other instead of building on it.

Individual reads and writes can be atomic while the whole read–modify–write operation is not.

Worked example: if two threads both read a counter at `10`, increment locally, and each writes `11`, the final counter is `11`, not `12`. One increment has been lost.

**Unseen transfer task — no answer shown**

Initial balances:

```text
checking = 100
rent     = 0
savings  = 0
```

Each transfer independently reads its source and destination before writing:

```text
T1: transfer 30 from checking to rent
T2: transfer 20 from checking to savings

T1 reads checking → 100 and rent → 0
T2 reads checking → 100 and savings → 0
T1 writes rent → 30
T2 writes savings → 20
T1 writes checking → 70
T2 writes checking → 80
```

**Learner action:** Diagnose this in three lines: the final balances, the lost update, and the balance invariant that exposes the bug.

## Learner turn 4

Final balances are checking = 80, rent = 30, savings = 20. T2's checking write of 80 overwrote T1's debit to 70, so T1's checking-side update was lost. The invariant checking + rent + savings should remain 100, but the final sum is 130, exposing the bug.

## Tutor turn 4

Correct on all three:

- Final state: `checking = 80`, `rent = 30`, `savings = 20`.
- T2’s stale calculation overwrote T1’s checking debit.
- The total rises from `100` to `130`, proving the transfer invariant was violated.

This is strong unassisted transfer evidence: you traced the concrete writes and used an invariant to detect a bug spanning multiple fields.

**Learner action — Teach-back:** In one sentence, state a general diagnostic rule for recognizing a lost update.

## Learner turn 5

A lost update occurs when concurrent operations derive writes from the same stale shared state and a later write overwrites an earlier operation instead of incorporating it.

## Tutor turn 5

That rule is accurate and complete.

Lesson evidence:

- Initial diagnosis: correct after Hint 1, so scaffolded.
- Unseen transfer: correct and unassisted, including the violated invariant.
- Teach-back: correct general rule stated independently.

You can diagnose a lost update in a fresh two-thread trace. Durable recall remains untested.

Retention horizon: **1 week (provisional)**. Retry a new trace without notes in **48 hours**, then again after one week if successful. No files or learner state were changed.
