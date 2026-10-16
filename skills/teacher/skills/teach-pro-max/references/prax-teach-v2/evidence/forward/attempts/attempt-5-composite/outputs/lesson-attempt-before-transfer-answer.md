# Focused lesson: diagnosing a two-thread lost update

## Tutor — initial diagnosis

Goal: Given an interleaved trace, identify the final stored value, the value expected if both operations took effect, and exactly which update disappeared.

We’ll use this sequence: initial diagnosis → compact model → guided practice → an unseen transfer task with changed surface details. I’ll keep each answer hidden until you attempt it.

Start with `balance = 100`:

```text
1. Thread A reads balance into a
2. Thread B reads balance into b
3. Thread A computes a + 20
4. Thread B computes b - 15
5. Thread A writes its computed value to balance
6. Thread B writes its computed value to balance
```

Assume each read and write is atomic, with no lock, retry, or transaction conflict detection.

What final value is stored, what value would reflect both operations, and which update—if any—was lost? Explain your diagnosis in one or two sentences. “I don’t know yet” is a valid answer.

## Learner — first attempt

The final value is 85 and the combined value should be 105. I think B's minus 15 was lost because A wrote first.

## Tutor — light hint

You correctly computed both values: the stored value is `85`, while applying both operations would produce `105`.

The part to revise is which update was lost. “Lost” means its effect is absent from the final stored value—not that its thread wrote first.

Hint 1: `85` is exactly the value Thread B computed from its original read. So whose operation is missing from `85`?

Revise just this statement: **Thread ___’s update was lost because ___ overwrote it.**

## Learner — revised attempt

Thread A's plus 20 update was lost because Thread B overwrote it with 85, which B computed from its earlier read of 100.

## Tutor — diagnostic method, worked example, and unassisted practice

Exactly. Thread A’s `+20` effect is absent because Thread B’s later write used the stale value it had read before A’s update. You reached the correct diagnosis after one cue, so we’ll now test the method unassisted.

Use this diagnostic:

1. Record what each thread read.
2. Calculate what each thread will write.
3. Replay the writes in actual order.
4. Calculate the value containing both operations.
5. Compare the two values: the missing effect is the lost update.

Worked example: inventory starts at `50`. A shipment thread reads `50` and computes `+10`; an order thread also reads `50` and computes `-4`. The shipment writes `60`, then the order writes `46`. The stored value is `46`, but both operations should yield `56`; therefore the shipment’s `+10` was lost.

Now try a similar case unassisted:

```text
score starts at 60

1. Thread A reads score
2. Thread B reads score
3. Thread A computes +12
4. Thread B computes -8
5. Thread B writes its result
6. Thread A writes its result
```

What is the final stored value, what value includes both operations, and which update was lost?

## Learner — unassisted similar case

The final stored value is 72. If both operations survived it would be 64, so Thread B's minus 8 update was lost when A later wrote 72 from its stale read.

## Tutor — unseen transfer prompt

Correct—and unassisted this time. You derived both values and identified the lost operation from the later stale write, which is the full diagnostic method.

A settings service stores the entire profile as one record:

```json
{
  "email": "old@example.com",
  "alerts": true
}
```

Two threads execute this interleaving:

```text
1. Thread A loads the whole profile into localA
2. Thread B loads the whole profile into localB
3. Thread A changes localA.email to "new@example.com"
4. Thread B changes localB.alerts to false
5. Thread A saves all of localA
6. Thread B saves all of localB
```

Each save replaces the entire stored profile.

Diagnose the result: what profile is finally stored, what profile should contain both changes, and is there a lost update? If so, identify it and explain the causal chain.

## Learner — unseen transfer attempt

The final stored profile is `{ email: "old@example.com", alerts: false }`. If both changes survived it would be `{ email: "new@example.com", alerts: false }`. Yes, A's email update was lost: B read the old whole profile, then B's later whole-record save restored the stale email while keeping B's alerts change.

## Tutor — evidence-calibrated close

Correct. You recognized the deeper pattern: threads can modify different fields and still lose an update when each later replaces the whole record from a stale snapshot.

Lesson outcome achieved for this session:

- On the first trace, you calculated both values correctly but reversed which update was lost; one cue resolved that gap.
- You then diagnosed a similar case unassisted.
- You correctly transferred the method to a whole-record replacement case and explained the causal chain unassisted.

That is strong evidence of immediate application and transfer. It is not yet evidence of delayed retention or durable mastery because we have not tested you after time has passed.

For a one-week retention goal, try a fresh, no-notes diagnosis in about 48 hours—ideally contrasting this bug with an atomic update or a rejected versioned write. If that is correct unassisted, retrieve it once more after seven days. No files or learner state were created.
