# Lesson attempt before transfer answer

## Turn 1 — Learner

Create a focused lesson that teaches me to diagnose a two-thread lost update. Include an unseen transfer task and do not reveal its answer before my attempt.

## Turn 1 — Tutor

We’ll focus on one outcome: given a two-thread interleaving, you’ll be able to locate the lost update and justify a repair from the actual read–compute–write sequence. After we work through this case, I’ll give you a genuinely different, unseen transfer task; its answer stays hidden until you attempt it.

Start with diagnosis—no need to know the formal terminology yet.

`counter` starts at `10`. Each individual read and write is atomic, but the whole increment is not.

```text
Step   Thread A                       Thread B
1      a = counter   // a = 10
2                                     b = counter   // b = 10
3      a = a + 1     // a = 11
4                                     b = b + 1     // b = 11
5      counter = a   // counter = 11
6                                     counter = b   // counter = 11
```

If both increments took effect, `counter` would end at `12`.

What is the earliest numbered step after which this shown execution can no longer end at `12`, and why? Answer in one or two sentences. If you’re unsure, say `I don’t know` and name the step you’re torn about.

## Turn 2 — Learner

Step 5, because that is when Thread A writes 11 and overwrites the shared value.

## Turn 2 — Tutor

You’re correctly looking at the moment a write reaches shared memory and noticing that the value written is `11`. The part to revise is the overwrite claim: at step 5, Thread A replaces the initial `10`; Thread B has not written an update yet.

To locate the earliest point of no return, inspect the thread-local values before either write. Which earlier numbered step first leaves both threads holding values derived from the same shared `counter` value? Reply with the step and your reason.

## Turn 3 — Learner

I’m not sure. Hint 1, please.

## Turn 3 — Tutor

**Hint 1 — Orienting prompt:** Temporarily ignore the additions and writes. Look only at the reads in steps 1 and 2, and track when `a` and `b` have each copied a value from the shared `counter`.

After which of those two steps are both local copies fixed from the same shared value? Reply with the step and what `a` and `b` contain then.

## Turn 4 — Learner

Step 2; both a and b now contain 10, copied from the same shared value.

## Turn 4 — Tutor

Correct—with Hint 1, you located the earliest causal point. Once step 2 finishes, both local copies are `10`. Neither thread rereads `counter`, so both later compute a fixed result of `11`. Step 5 publishes A’s increment; step 6 publishes B’s independently computed `11`, which does not include A’s increment. The loss becomes visible at the final write, but the paired reads from the same starting value are what make this shown execution unable to reach `12`.

This is a read–modify–write race: making each read and write atomic is not enough when another thread can change the shared state between one thread’s read and its write.

A teammate proposes putting a mutex around only steps 5 and 6, so the writes cannot overlap, while leaving steps 1–4 outside the mutex. Would that guarantee a final value of `12`? Answer yes or no, then state which operations one increment’s protected boundary must include.

## Turn 5 — Learner

No. The mutex must cover the read, compute, and write as one critical section for each increment.

## Turn 5 — Tutor

Exactly. Locking only the writes would merely serialize publication of values that may already be stale. The protected boundary must begin before the read and end after the corresponding write, so another thread cannot base a competing update on the same old state.

### Unseen transfer task

A service stores this shared record:

```text
profile = { theme: "light", language: "en" }
```

Both changes below are intended to persist. Each thread reads a private copy, modifies it, and atomically replaces the entire shared record; replacement does not merge fields.

```text
1. Thread A reads profile into a
2. Thread B reads profile into b
3. Thread A sets a.theme = "dark"
4. Thread B sets b.language = "fr"
5. Thread A writes profile = a
6. Thread B writes profile = b
```

Diagnose this execution in three or four sentences: state the final shared record, identify whether a logical update is lost and which one, explain the cause using the private copies, and propose one safe update strategy. Make your attempt before requesting a hint; you can also say **Answer now**.

## Turn 6 — Learner

The final record is {theme: "light", language: "fr"}. Thread A’s dark-theme update is lost because B’s private copy still had theme = "light" and B replaced the entire record after A. Protect the whole read–modify–write with a lock, or use an atomic compare-and-swap/retry so B cannot commit a stale whole-record copy.

## Turn 6 — Tutor

Your transfer diagnosis is correct. You traced the final record accurately, identified A’s lost logical change, connected it to B’s stale private copy, and proposed two valid repair families. The governing principle is that a whole-record update must either serialize the complete read–modify–write or detect a stale commit and retry from fresh state; no correction is needed here.

### Lesson close

- **Outcome:** You can diagnose a two-thread lost update from the local and shared state, distinguish the causal stale reads from the later write where the loss becomes visible, and justify a safe update boundary.
- **Observed evidence:** Your first diagnosis placed the problem at step 5. With Hint 1, you revised it to the earliest causal point at step 2, so that first success was scaffolded. You then selected the full critical-section boundary correctly, and you solved the unseen whole-record transfer without a hint by tracing state, naming the lost change, explaining the cause, and proposing valid repairs.
- **Remaining uncertainty:** We have not observed delayed recall, and one unassisted transfer does not show how reliably you will diagnose other interleavings or choose among locking, atomic read–modify–write, and compare-and-swap under different constraints.
- **Next retrieval for a 30-day retention horizon:** In 3 days, solve a fresh interleaving without notes or hints and state the final state, earliest causal point, lost effect, and safe repair. If that is unassisted, repeat with new cases around day 14 and day 30; if you need help, review the read–modify–write model and retry sooner.
