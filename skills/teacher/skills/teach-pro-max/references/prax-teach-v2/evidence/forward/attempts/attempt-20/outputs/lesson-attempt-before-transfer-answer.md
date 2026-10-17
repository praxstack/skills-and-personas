# Lost-update lesson

## User

Create a focused lesson that teaches me to diagnose a two-thread lost update. Include an unseen transfer task and do not reveal its answer before my attempt.

## Assistant

Outcome: given a two-thread trace, identify any lost effect, the stale read, and the decisive overwriting write.

Inventory starts at `50`.

```text
T1 reads 50
T2 reads 50
T1 sells 8 and writes 42
T2 receives 5 and writes 55
```

What is the final value, is an update lost, and which read and write caused it?

## User

The final value is 55. I think T2’s `+5` delivery was lost because T2 used an old value, and T1’s write of 42 caused it.

## Assistant

Hint 1: Starting from `50`, check separately whether the final `55` still reflects the `−8` and whether it reflects the `+5`. Then revise which effect is missing and which later write removed it.

## User

The `+5` is present, but the `−8` is missing. T1’s sale was lost. T2 read the stale value `50`, then its write of `55` overwrote T1’s `42`. If both operations survived, the result would be `47`.

## Assistant

Correct. A lost update occurs when a later read–modify–write uses stale state and overwrites an earlier effect.

Contrast this safe trace:

```text
score starts at 30
T1 reads 30 and writes 40
T2 reads 40 and writes 35
```

The final `35` preserves both changes because T2 read T1’s result.

Unseen transfer problem:

```text
Shared task starts as:
{ status: "draft", owner: "unassigned" }

T1 reads the task
T2 reads the task
T1 sets status to "published" and replaces the whole task
T2 sets owner to "Ana" in its saved copy and replaces the whole task
```

Diagnose whether a lost update occurs. Name the missing effect, stale read, decisive write, and combined state that should remain.

## User

Yes. T1’s status change is lost. T2 read the original task with status `"draft"`, then its whole-task write restored that stale status while setting the owner. T2’s write is decisive. The combined state should be `{ status: "published", owner: "Ana" }`.

## Assistant

Correct, without a case-specific hint. You transferred the diagnosis from arithmetic updates to whole-record replacement.

Teach it back in two or three sentences: what general procedure would you use, and why can edits to different fields still conflict?

## User

First, record what each thread read and compute the state that would preserve every intended change. Then compare that state with the actual final write and locate the stale-based write that made an earlier effect disappear. Different fields can still conflict when each thread replaces the whole record instead of updating only its own field.

## Assistant

Accurate teach-back. Observed evidence: a correct repair after one orienting hint, followed by immediate unassisted transfer and explanation. Delayed retention remains untested, so retry a fresh no-hint lost-update versus safe-interleaving pair in about 48 hours. No files or learner state were created.
