# Lost-update lesson

## Learner turn 1

Create a focused lesson that teaches me to diagnose a two-thread lost update. Include an unseen transfer task and do not reveal its answer before my attempt.

## Tutor turn 1

## Focused lesson: diagnose a two-thread lost update

Goal: Given an interleaving, identify:

1. The shared state.
2. Each thread’s read and write.
3. The write that overwrites another thread’s update.
4. The smallest synchronization boundary that prevents it.

### First prediction

Start with `counter = 0`:

```text
Thread A: tmp = counter
Thread A: tmp = tmp + 1
Thread A: counter = tmp

Thread B: tmp = counter
Thread B: tmp = tmp + 1
Thread B: counter = tmp
```

One possible schedule is:

```text
A reads counter
B reads counter
A writes counter
B writes counter
```

What final value can result, and which two operations demonstrate the lost update? If uncertain, say “I don’t know.”

### Unseen transfer task

Later, diagnose this new case without copying the counter example:

```text
inventory = 10

Thread A: seen = inventory
Thread A: seen = seen - 3
Thread A: inventory = seen

Thread B: seen = inventory
Thread B: seen = seen - 4
Thread B: inventory = seen
```

Do not solve the transfer task yet; we’ll use it after your first diagnosis.

## Learner turn 2

I think the final value is 2 because both threads increment once. The two writes show both increments completed, so I do not see a lost update.

## Tutor turn 2

Track the value each thread reads into its own private `tmp`. If both reads happen before either write, what value does each thread eventually write to `counter`?

Revise your answer with the two write values and the resulting final value.

## Learner turn 3

Both threads read 0 into separate temporary variables, so each computes and writes 1. The final value is 1, not 2. The second write of 1 overwrites the first completed increment, so one update is lost.

## Tutor turn 3

Correct. You tracked the private reads, computed both writes, and identified the overwrite. The key principle is that “read → modify → write” is one logical update, but the threads can interleave those steps.

Worked trace:

```text
A reads 0
B reads 0
A writes 1
B writes 1
```

Now attempt the transfer task:

```text
inventory = 10

Thread A: seen = inventory
Thread A: seen = seen - 3
Thread A: inventory = seen

Thread B: seen = inventory
Thread B: seen = seen - 4
Thread B: inventory = seen
```

What final inventory results under the analogous interleaving, which update is lost, and what operation must be protected to prevent it?

## Learner turn 4

Under the analogous interleaving, both threads read 10. A computes and writes 7, then B writes 6 from its stale read, so the final inventory is 6 instead of the correct 3. A's subtraction of 3 is lost. The entire read-modify-write sequence must be protected atomically, for example by one lock around it.

## Tutor turn 4

Correct. You transferred the diagnosis: both threads used stale reads, A’s update was overwritten, and the full read–modify–write sequence needs atomic protection.

Evidence observed: your first diagnosis became correct after one hint (scaffolded); your transfer diagnosis was correct. That demonstrates application, but not yet independent retention.

Teach-back in one sentence: why must protection cover the entire read–modify–write sequence rather than only the write?

## Learner turn 5

Protection must cover read, modify, and write together because locking only the final write still allows both threads to compute from the same stale value, so a later write can still erase an earlier update.

## Tutor turn 5

Exactly. Locking only the write would still allow stale calculations; the whole read–modify–write must be atomic.

Lesson complete:

- Initial diagnosis: correct after one hint (scaffolded).
- Transfer diagnosis: correct.
- Teach-back: correct and causal.

Next retrieval: diagnose a fresh interleaving tomorrow without using the template.
