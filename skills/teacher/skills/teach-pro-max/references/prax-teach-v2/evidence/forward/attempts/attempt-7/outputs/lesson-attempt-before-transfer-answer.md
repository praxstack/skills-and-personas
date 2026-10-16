# Lesson: attempt before transfer answer

## Tutor turn 1

### Focused lesson: diagnosing a two-thread lost update

**Outcome:** Given an execution trace, you’ll identify whether an update was lost, locate the decisive event, and explain the cause. After explanation and guided practice, you’ll receive an unseen transfer task whose answer stays hidden until your attempt.

Say **Answer now** at any point if you want the direct explanation.

#### Learner action 1 — Diagnose the trace

Assume each individual read and write is atomic, but there is no synchronization around the complete operation.

Initial shared value: `score = 40`

- Thread T1 adds `5`.
- Thread T2 adds `7`.

```text
1. T1 reads score into local variable a
2. T2 reads score into local variable b
3. T1 computes a = a + 5
4. T1 writes a into score
5. T2 computes b = b + 7
6. T2 writes b into score
```

Without running it, reply with:

```text
Final score:
Score expected if both additions survive:
First decisive event:
Reason:
```

If you’re unsure, reply **“I don’t know”** and name the first line that becomes unclear.

This lesson runs through host chat without custom controls, scripts, or stored learner state. Host-UI keyboard, focus, reduced-motion, and assistive-technology behavior remains unverified.

## Learner turn 1

Final score: 52  
Score expected if both additions survive: 52  
First decisive event: line 4  
Reason: T1 writes first, so both additions are included.

## Tutor turn 2

You correctly calculated `52` as the value if both additions survive.

**Hint 1 — Principle cue:** A thread’s local variable does not automatically change when another thread writes to the shared variable. Track what value `b` still contains after line 4.

**Learner action 2 — Revise:** Recompute lines 3–6, then resubmit the four fields.

## Learner turn 2

Final score: 47  
Score expected if both additions survive: 52  
First decisive event: line 6  
Reason: b stayed 40 after T1 wrote 45, so T2 computed 47 and line 6 overwrote T1’s update.

## Tutor turn 3

Correct. Your revised diagnosis is fully accurate.

- `b` is a snapshot, not a live reference to `score`.
- Line 2 creates the vulnerability, but no update has been lost yet.
- Line 6 makes the loss real by writing a value that omits T1’s completed addition.

Because you used one principle cue, this is scaffolded success; we’ll now test the method independently.

### Diagnostic method

1. Track shared state and each thread’s local state separately.
2. Compute the result if every intended operation survives.
3. Execute the listed interleaving literally.
4. Find the write based on an older read that replaces another thread’s effect.

### Worked example

Inventory begins at `10`.

```text
1. T1 reads 10 and computes 10 − 2 = 8
2. T2 reads 10 and computes 10 − 3 = 7
3. T2 writes 7
4. T1 writes 8
```

Both purchases should leave `5`, but the trace leaves `8`. At line 4, T1 writes a value derived from its earlier read of `10`, replacing T2’s reduction.

### Learner action 3 — Independent practice

Shared value: `remaining = 30`

- T1 reserves `8`.
- T2 releases `5`.

```text
1. T1 reads remaining into a
2. T2 reads remaining into b
3. T1 computes a = a − 8
4. T1 writes a into remaining
5. T2 computes b = b + 5
6. T2 writes b into remaining
```

Reply with:

```text
Final remaining:
Expected remaining:
First decisive event:
Reason:
```

The unseen transfer task follows this attempt.

## Learner turn 3

Final remaining: 35  
Expected remaining: 27  
First decisive event: line 6  
Reason: b still contains the stale read of 30, so T2 writes 35 and replaces T1’s reservation result of 22.

## Tutor turn 4

Correct. You independently tracked both local snapshots, derived the final and intended values, and identified the decisive overwrite at line 6. That is evidence of unassisted application on a structurally similar trace; transfer to a different representation remains untested.

### Learner action 4 — Unseen transfer

A service stores each profile as one JSON object:

```json
{
  "theme": "light",
  "email_opt_in": false
}
```

Assume `load()` returns a separate local copy, `save()` replaces the entire stored object, and there is no locking or version check.

```text
1. T1 loads the profile into p1
2. T2 loads the profile into p2
3. T1 changes p1.theme to "dark"
4. T2 changes p2.email_opt_in to true
5. T1 saves p1
6. T2 saves p2
```

Diagnose the trace without hints:

```text
Final stored profile:
Profile expected if both changes survive:
Lost update present—yes or no:
First decisive event and reason:
```

## Learner turn 4

Final stored profile: `{"theme":"light","email_opt_in":true}`  
Profile expected if both changes survive: `{"theme":"dark","email_opt_in":true}`  
Lost update present—yes  
First decisive event and reason: line 6; p2 was loaded before T1’s change, so saving the whole stale object replaces the stored dark theme with light while keeping T2’s email change.

## Tutor turn 5

Exactly right. This is successful unassisted transfer: you moved from numeric increments to whole-object persistence and correctly reasoned about the actual write granularity.

The general pattern is:

1. Two threads read the same earlier version.
2. Each derives a new value independently.
3. A later write replaces shared state without incorporating the intervening change.

Different logical fields do not prevent a lost update when `save()` replaces their shared container.

Typical protections include:

- Locking the entire **load → modify → save** sequence.
- Comparing a version or ETag when saving, then retrying after a conflict.
- Using truly atomic field-level updates when the storage system supports them.

Locking only `save()` is insufficient because both stale local copies may already exist before either save begins.

### Learner action 5 — Teach-back

In one or two sentences, explain why updates to separate fields were still able to conflict here, and name one protection with the correct boundary.

## Learner turn 5

They conflicted because each thread saved an entire object copied from the same old version, so the second whole-object save replaced the first thread’s field change. Use optimistic concurrency by comparing a version/ETag at save and retrying the full load-modify-save operation after a conflict.

## Tutor turn 6

Lesson complete. Your teach-back is correct: whole-object replacement made the separate field edits conflict, and optimistic concurrency is appropriate provided the version comparison and write occur atomically.

Evidence observed:

- Initial diagnosis corrected after one principle cue: scaffolded.
- Similar numeric trace diagnosed without hints.
- Unseen whole-object transfer diagnosed without hints.
- Cause and prevention boundary explained without hints.

You can now diagnose the requested pattern independently within this session. What remains untested is delayed recall and systems with different semantics, such as automatic conflict rejection or atomic field updates.

For retention, try a fresh trace without notes in 2–3 days and determine whether it exhibits a lost update, safely serializes, or rejects a conflicting write. No files or durable learner state were created.
