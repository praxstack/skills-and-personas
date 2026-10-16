# Diagnosing a two-thread lost update

## Learner turn 1

Teach me how a two-thread read-modify-write race can lose an update. Do not give me the transfer answer before I attempt it. I want to diagnose from traces.

## Tutor turn 1

We’ll practice one skill: reading an interleaved trace to find when a thread’s value becomes stale.

Initial state: `counter = 10`

```text
1. Thread A: read counter → 10
2. Thread B: read counter → 10
3. Thread A: compute 10 + 1 → 11
4. Thread B: compute 10 + 1 → 11
5. Thread A: write counter = 11
6. Thread B: write counter = 11
```

Your turn: What final value does this trace produce, and at which point does the update get lost? Give your reasoning in 1–3 sentences.

## Learner turn 2

The final value is 11. The update gets lost when Thread B writes its stale computed 11 at step 6, overwriting Thread A's write; both reads happened before either write.

## Tutor turn 2

Exactly. You identified the two essential clues:

- The final value is `11`, although two increments were attempted.
- Thread B’s write is based on its earlier, stale read and overwrites Thread A’s newer value.

The core rule is that “read, modify, write” is one logical operation, even if each individual step looks simple. Without synchronization, another thread can intervene between those steps.

Now diagnose this trace:

```text
Initial counter = 20

1. Thread A: read counter → 20
2. Thread B: read counter → 20
3. Thread A: compute 20 + 1 → 21
4. Thread A: write counter = 21
5. Thread B: compute 20 + 1 → 21
6. Thread B: write counter = 21
```

What final value results, and is an update lost? Cite the decisive events.

## Learner turn 3

Final value 21, and yes, one update is lost. Both threads read 20; A writes 21 at step 4, then B computes from stale 20 and writes 21 at step 6, so only one increment remains.

## Tutor turn 3

Correct. You traced the stale read to B’s later write, which overwrites A’s update. If the operations were serialized, B would read A’s `21` and produce `22`; the race prevents that.

You diagnosed both traces without hints. Teach it back in one sentence: what must be protected to make a read-modify-write increment safe?

## Learner turn 4

The entire read-compute-write sequence must be atomic—using a lock, atomic fetch-add, or a correctly retried compare-and-swap—so no thread can commit from a stale read.

## Tutor turn 4

Exactly. You stated the complete rule: protect the whole read–compute–write sequence, or use an atomic operation that retries stale reads.

So far, you correctly diagnosed two traces, explained the overwrite, and transferred the principle without hints. For retention, revisit a fresh interleaving later and check whether each write is based on the latest read.

## Learner turn 5

Give me a harder compare-and-swap retry trace. I want to diagnose whether a failed first CAS necessarily means a lost update.

## Tutor turn 5

`CAS(expected → new)` writes only when the current value still equals `expected`; otherwise it fails and leaves the counter unchanged.

Diagnose this trace:

```text
Initial counter = 40

1. Thread A: read → 40
2. Thread B: read → 40
3. Thread A: CAS(40 → 41) succeeds; counter = 41
4. Thread B: CAS(40 → 41) fails; counter = 41
5. Thread A: read → 41
6. Thread A: CAS(41 → 42) succeeds; counter = 42
7. Thread B: reread → 42
8. Thread B: CAS(42 → 43) succeeds; counter = 43
```

Did any increment get lost? What does B’s first failed CAS tell you? State the final value and cite the decisive events.

## Learner turn 6

It is a lost update because Thread B’s first CAS failed, although the final value is 43 after the retries.

## Tutor turn 6

Hint: A failed CAS does not change the counter. Track whether B’s increment is later committed successfully, rather than treating the failed attempt itself as the final outcome.

Revise your diagnosis: did the trace lose an update, and which successful writes account for the final value?

## Learner turn 7

No update is lost. The successful CAS operations at steps 3, 6, and 8 commit three increments, taking 40 to 43. B’s first CAS failure only detected that its expected value was stale; its retry later succeeds.

## Tutor turn 7

Correct. A failed CAS signals interference; it does not itself lose an update. Here, three successful CAS operations commit three increments, so the counter reaches `43`.

Your correction came after one principle hint, so this trace is scaffolded evidence. For the next retrieval, inspect a trace where a thread stops after a failed CAS and determine whether its intended update ever commits.
