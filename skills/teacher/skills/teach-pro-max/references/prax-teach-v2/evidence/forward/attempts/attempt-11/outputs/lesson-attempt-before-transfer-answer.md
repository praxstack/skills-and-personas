# Diagnosing a two-thread lost update

## Tutor turn 1

We’ll keep this focused and ephemeral in host chat; no files, custom controls, or scripts. Host-UI keyboard, focus, reduced-motion, and assistive-technology behavior remain unverified.

Two threads share `balance = 100`:

```text
Thread A: read balance → add 10 → write result
Thread B: read balance → add 20 → write result
```

After both threads finish, `balance` is `120`, not `130`.

**Learner action 1:** Write one legal interleaving of the six read/add/write steps that produces `120`, then mark the exact step where an update becomes lost. “I don’t know” is a valid answer.

## Learner turn 1

A reads 100. B reads 100. A adds 10 to its local value, B adds 20 to its local value. A writes 110. B writes 120. The update becomes lost when B writes 120 over A’s 110.

## Tutor turn 2

Correct. Your interleaving is legal, and you identified the exact manifestation: B’s final write overwrites A’s result.

The root cause begins earlier: both threads read the same stale value before either completes the full read–modify–write operation. Protecting only the writes would not fix it; the whole operation must be atomic, for example with a lock around read–add–write or an atomic increment.

Contrast:

```text
A reads 100 → adds 10 → writes 110
B reads 110 → adds 20 → writes 130
```

No update is lost because B reads A’s completed result.

**Learner action 2 — unseen transfer:** An inventory counter starts at `12`.

```text
Reservation thread: read available → subtract 5 → write result
Cancellation thread: read available → add 2 → write result
```

Both threads finish, but `available` is `14`.

Diagnose this by giving one legal interleaving and identifying precisely which update was lost and when.

## Learner turn 2

Reservation reads 12. Cancellation reads 12. Reservation subtracts 5 locally; cancellation adds 2 locally. Reservation writes 7, then cancellation writes 14. The reservation’s subtraction is lost when the cancellation writes 14 over 7. Both read the stale 12 before either full update completed.

## Tutor turn 3

Correct. The serial result should be `9`; ending at `14` shows that the subtraction vanished. You correctly identified both the overwrite point and the deeper cause: overlapping, unprotected read–modify–write operations.

Lesson evidence:

- Two correct, unassisted diagnoses, including one unseen transfer.
- You produced legal interleavings and explained the causal mechanism.
- Highest hint used: none.
- Your rule: “Both read the stale 12 before either full update completed.”

This supports immediate debugging and transfer, but not yet durable recall. In 48 hours, retry with a new trace and identify both the stale-read window and the critical section that must be atomic. No files or learner state were stored.

## Learner turn 3

Give me one more harder trace so I can check whether I can distinguish a lost update from a safe retry.

## Tutor turn 4

`CAS(expectedVersion, newValue)` writes only when the current version matches; otherwise it fails without changing anything.

```text
Initial state: inventory = 10, version = 4

T1 reads (10, v4), computes 10 − 3 = 7
T2 reads (10, v4), computes 10 + 2 = 12

T1: CAS(v4, 7)  → succeeds; state becomes (7, v5)
T2: CAS(v4, 12) → fails; state remains (7, v5)

T2 reads (7, v5), computes 7 + 2 = 9
T2: CAS(v5, 9)  → succeeds; state becomes (9, v6)
```

**Learner action 3:** Is this a lost update or a safe retry? Justify your diagnosis by identifying which intended changes survive and the single event that makes the classification decisive.

## Learner turn 4

It is a lost update because T2’s first CAS failed, so its computed value 12 was lost.

## Tutor turn 5

**Hint 1 — orienting prompt:** Track the intended operations (`−3` and `+2`), not whether every temporary local value gets written. Compare the final value `9` with the result of applying each intended operation exactly once.

**Learner action 4:** Revise your classification and identify the decisive event.

## Learner turn 5

It is a safe retry. Starting from 10, applying −3 and +2 exactly once gives 9, which is the final value. T2’s failed CAS is decisive because it prevents the stale write of 12; T2 then rereads version 5 and successfully applies +2 to 7.

## Tutor turn 6

Correct revised diagnosis. T2’s failed CAS discards only a tentative stale computation; it does not discard the intended `+2` operation. The reread and recomputation preserve both operations, producing `9`.

Evidence:

- Lost-update diagnosis and unseen transfer: correct, unassisted.
- Retry discrimination: correct after Hint 1, so this is scaffolded success.
- Remaining uncertainty: whether you can make that distinction unassisted on a fresh trace.

Decision rule: track whether every intended logical operation affects the committed final state—not whether every temporary value gets written. Retry a fresh discrimination trace in about 48 hours for retention evidence.
