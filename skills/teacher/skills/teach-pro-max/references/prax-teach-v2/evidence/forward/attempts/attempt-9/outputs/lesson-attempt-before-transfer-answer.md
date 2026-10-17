# Lesson: attempt before transfer answer

## Tutor turn 1

Our target: given a two-thread execution trace, diagnose whether a lost update occurred and identify the exact write responsible. Later, you’ll attempt an unseen transfer case before I reveal its answer.

A shared variable `score` starts at `100`:

| Step | Event |
|---:|---|
| 1 | T1 reads `score` → `100` |
| 2 | T2 reads `score` → `100` |
| 3 | T1 computes local value `90` |
| 4 | T2 computes local value `120` |
| 5 | T1 writes `90` to `score` |
| 6 | T2 writes `120` to `score` |

Final shared value: `120`.

**Your attempt:** Does this trace contain a lost update? If yes, name the intended change that failed to survive and the exact event that caused it. If no, explain why. “I don’t know yet” is also valid.

## Learner turn 1

Yes. T1 intended to subtract 10, but that change did not survive. Step 6 caused the loss: T2 wrote 120 using the stale value 100 and overwrote T1’s write of 90.

## Tutor turn 2

Correct—this was an unassisted diagnosis. You identified both the lost logical change and the decisive overwrite. One useful precision: the danger begins when T2 reads the stale `100`; the loss becomes observable when T2 writes `120`.

Decision rule: a lost update occurs when two threads perform read–modify–write operations from the same old state, and a later write replaces rather than incorporates the earlier update.

Worked example: inventory starts at `12`. A sale computes `12 − 2 = 10`; a restock independently computes `12 + 5 = 17`. If the writes are `10`, then `17`, the observed result is `17` instead of the composed result `15`, so the sale was lost.

Now discriminate this trace:

| Step | Event |
|---:|---|
| 1 | T1 reads `100` |
| 2 | T1 computes `90` |
| 3 | T1 writes `90` |
| 4 | T2 reads `90` |
| 5 | T2 computes `110` |
| 6 | T2 writes `110` |

**Your attempt:** Is there a lost update here? Answer yes or no, then justify it using the value T2 read and the result of composing both intended changes.

## Learner turn 2

No. T2 read 90, which already included T1’s subtraction of 10. T2 then added 20 and wrote 110; composing both intended changes from 100 also gives 110, so neither update was lost.

## Tutor turn 3

Correct. Overlap alone does not imply a lost update: T2 read a state that already contained T1’s change, and the final value preserves both operations. That’s a second unassisted success, now on discrimination.

### Unseen transfer task

A service saves settings by replacing the entire document.

Initial shared document:

```json
{"theme":"light","alerts":true}
```

Execution:

1. T1 reads the document.
2. T2 reads the document.
3. T1 changes `theme` to `"dark"` in its local copy.
4. T2 changes `alerts` to `false` in its local copy.
5. T1 replaces the shared document with `{"theme":"dark","alerts":true}`.
6. T2 replaces it with `{"theme":"light","alerts":false}`.

**Your attempt:** Diagnose whether this is a lost update, even though the threads intended to change different fields. Identify any lost change, the decisive event, and the stale information involved.

## Learner turn 3

Yes. T1’s theme change to dark was lost. Step 6 is decisive: T2 replaces the entire document with a local copy based on the stale initial theme light, so its whole-document write restores light while changing alerts to false.

## Tutor turn 4

Exactly. This is the key transfer: logically separate field edits can conflict when the physical write replaces the whole record. You correctly separated the stale-read cause from the decisive overwriting write.

So far, you’ve shown unassisted recognition, discrimination, and transfer within this session. Durable recall remains untested.

**Final teach-back:** In no more than three steps, state a general procedure for diagnosing a lost update in any two-thread execution trace. Include what you inspect about each read, the combined intended result, and the decisive write.

## Learner turn 4

1. Trace what state each thread read and whether either read was stale relative to another intended change.
2. Compute the result that would preserve both intended changes and compare it with the final shared state.
3. If a change is missing, identify the later write that replaced rather than incorporated it; that write is the decisive lost-update event.

## Tutor turn 5

Lesson complete. Your teach-back is accurate and operational: trace each read, compute the outcome that preserves every intended change, then locate the write that removed a change instead of incorporating it.

Evidence observed, all without hints:

- Correct diagnosis of a lost update and its decisive write.
- Correct rejection of a similar trace that preserved both updates.
- Correct transfer to whole-document replacement across different fields.
- Correct learner-authored diagnostic procedure.

This supports immediate recognition, discrimination, explanation, and transfer—not durable mastery, since delayed retrieval has not been tested. For retention over the next week, diagnose a fresh trace without notes in 2–3 days, then repeat after one week.

No files or durable learner state were created.

## Learner turn 5

I’m not fully confident yet. Please give me one more short two-thread trace to diagnose before we close.

## Tutor turn 6

Confidence is best calibrated with another attempt.

`compare-and-set(expected, new)` writes only when the shared value still equals `expected`; otherwise it fails without changing anything.

A shared balance starts at `50`:

1. T1 reads `50` and computes `40`.
2. T2 reads `50` and computes `70`.
3. T1 runs `compare-and-set(50, 40)`; it succeeds.
4. T2 runs `compare-and-set(50, 70)`; it fails.
5. T2 rereads `40` and recomputes `60`.
6. T2 runs `compare-and-set(40, 60)`; it succeeds.

Final balance: `60`.

**Your attempt:** Is either intended update lost? Diagnose the trace and identify the event that determines your answer.

## Learner turn 6

Yes. T1’s subtraction was lost at step 6, because the final balance is 60 instead of T1’s 40.

## Tutor turn 7

**Hint 1:** Compare the final `60` with the result of applying both intended changes—`−10` and `+20`—once to the starting `50`, rather than comparing it only with T1’s intermediate `40`.

**Revised attempt:** Recalculate that combined result, then decide again whether either update was lost.

## Learner turn 7

Applying both changes gives 50 - 10 + 20 = 60, which matches the final balance. No update was lost. Step 4 prevents the stale write by rejecting T2’s compare-and-set, and steps 5–6 recompute and apply T2’s change to T1’s updated value.

## Tutor turn 8

Correct revision. The final `60` preserves both changes, and the failed compare-and-set prevents T2’s stale computation from overwriting T1.

Your initial gap was treating T1’s intermediate `40` as the required final value. The reliable comparison is against the result of composing all intended changes. Because this answer followed Hint 1, it counts as scaffolded success.

Lesson evidence:

- Unassisted diagnosis of a basic lost update.
- Unassisted rejection of a non-loss interleaving.
- Unassisted transfer to whole-document replacement.
- Scaffolded diagnosis of conflict detection and retry.

The remaining uncertainty is diagnosing synchronization mechanisms such as compare-and-set without prompting. For one-week retention, try a fresh CAS/retry trace without notes in 1–2 days, then again after one week. No files or learner state were created.
