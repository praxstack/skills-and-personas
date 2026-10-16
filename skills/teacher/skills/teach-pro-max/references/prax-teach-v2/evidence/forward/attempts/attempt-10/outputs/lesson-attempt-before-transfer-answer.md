# Lesson: attempt before transfer answer

## Tutor turn 1

We’ll build toward this outcome: given a two-thread execution trace, you can identify a lost update and explain precisely where it occurs. After guided practice, I’ll give you an unseen transfer task; its answer will remain hidden until you attempt it.

### First diagnosis

A shared balance starts at `100`.

```text
T1 reads balance → 100
T2 reads balance → 100
T1 computes 100 + 20
T1 writes balance → 120
T2 computes 100 - 10
T2 writes balance → 90
```

Assume ordinary reads and writes—no locks, transactions, or atomic update operation.

In a few lines, diagnose:

1. The final stored balance.
2. Which update was lost.
3. Why the trace permits that loss.

“I don’t know yet” is a valid answer.

## Learner turn 1

The final balance is 90. T1’s +20 update was lost. Both threads read the same starting 100; T2 later wrote 90 from its stale copy, overwriting T1’s 120 instead of incorporating it.

## Tutor turn 2

Exactly right—and unassisted. You reconstructed both the stored result and the causal mechanism: T2’s write was based on a stale read, so it replaced rather than composed with T1’s update.

The diagnostic rule is:

> A lost update occurs when overlapping read–modify–write operations derive new values from the same old state, and a later write overwrites an earlier operation’s effect.

Contrast that with this safe interleaving:

```text
score starts at 40
T1 reads 40, adds 5, writes 45
T2 reads 45, subtracts 3, writes 42
```

No update is lost because T2 reads the result of T1’s completed write.

### Guided practice

```text
stock starts at 12
T1 reads stock → 12
T2 reads stock → 12
T2 computes 12 - 4
T2 writes stock → 8
T1 computes 12 + 3
T1 writes stock → 15
```

Diagnose the final stored value, which operation—if any—was lost, and what the final value would have been if both operations had been preserved.

## Learner turn 2

The final stored value is 15. T2’s subtraction of 4 was lost when T1 wrote 15 from its stale read of 12. If both changes were preserved, the result would be 12 - 4 + 3 = 11.

## Tutor turn 3

Correct again, unassisted. You tracked the write order, identified the stale snapshot, and compared the observed result (`15`) with the correctly composed result (`11`). That is the full diagnostic method.

### Unseen transfer task

A profile service stores this document:

```json
{
  "theme": "light",
  "email": "old@example.com"
}
```

Two request threads use whole-document read–modify–write operations:

```text
T1 reads the document
T2 reads the document
T1 changes theme to "dark"
T1 writes its whole document
T2 changes email to "new@example.com"
T2 writes its whole document
```

Without assuming any automatic merge, diagnose:

1. The final stored document.
2. Whether a lost update occurred and precisely what was lost.
3. The trace evidence that distinguishes this from two safe updates to different fields.

## Learner turn 3

The final document is `{"theme":"light","email":"new@example.com"}`. Yes, T1’s theme change to dark was lost. T2’s whole-document write used the stale copy that still had theme light and overwrote T1’s later state; different logical fields are not safe when each thread replaces the entire document.

## Tutor turn 4

Correct. The key transfer insight is that the overwrite unit is the whole document, not the individual field. T2’s stale document therefore restores `"theme": "light"` while saving its email change.

Lesson outcome met for this session: you correctly diagnosed three traces, including a changed-domain transfer case, all without hints. You demonstrated application, causal explanation, and transfer—not merely recognition.

Your learner-authored decision rule was especially strong:

> Different logical fields are not safe when each thread replaces the entire document.

What remains uncertain is retention over time and whether you can distinguish lost-update prevention mechanisms; neither was tested. For a one-week retention goal, try one fresh, unassisted trace in 2–3 days. No learner state or files were created.

## Learner turn 4

I’m still unsure about prevention mechanisms. Before we close, give me one short compare-and-set or retry trace to diagnose.

## Tutor turn 5

### Compare-and-set retry trace

```text
balance starts at (value=100, version=7)

T1 reads (100, v7) and computes 120
T2 reads (100, v7) and computes 90

T1 compare-and-set(expected=v7, new=120) → succeeds; version becomes v8
T2 compare-and-set(expected=v7, new=90)  → fails

T2 rereads (120, v8) and recomputes 110
T2 compare-and-set(expected=v8, new=110) → succeeds; version becomes v9
```

What is the final balance, did a lost update occur, and which event prevented or repaired the dangerous stale write?

## Learner turn 5

The final balance is 110, but T1’s +20 was lost because T2 eventually wrote 110 instead of leaving T1’s 120.

## Tutor turn 6

Your final balance of `110` is correct.

Hint: judge preservation by whether both intended changes are represented in the final value—not by whether T1’s intermediate value of `120` remains unchanged.

Revise only this part: was either update actually lost, and what in the trace supports your answer?

## Learner turn 6

No update was lost. The final 110 equals 100 + 20 - 10, so both changes are represented. T2’s stale compare-and-set failed at version 7; after rereading version 8 it recomputed from 120 and successfully applied the subtraction.

## Tutor turn 7

Correct on revision. The failed compare-and-set rejected T2’s stale write; rereading and recomputing rebased the subtraction onto T1’s result.

Evidence observed:

- Three lost-update diagnoses, including cross-domain transfer: correct and unassisted.
- Compare-and-set/retry diagnosis: correct after one principle cue, so this is scaffolded evidence.
- Remaining uncertainty: unassisted recognition of prevention mechanisms after a delay.

Your useful decision rule is: check whether every intended change survives in the final state, not whether an intermediate value remains unchanged.

For a one-week retention goal, diagnose a fresh compare-and-set trace without hints in 2–3 days. No learner state or files were created.
