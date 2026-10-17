# Lesson: attempt before transfer answer

## Tutor — worked-case prompt

By the end, you’ll be able to inspect a two-thread trace, identify the stale read and overwriting write, and explain exactly which update was lost. We’ll finish with a fresh transfer case whose answer I’ll keep hidden until you attempt it.

Start with this trace:

```text
Shared balance starts at 100

Thread A: withdraw 30          Thread B: deposit 20
A1: read balance → a = 100
                               B1: read balance → b = 100
A2: compute a = 70
                               B2: compute b = 120
A3: write balance = 70
                               B3: write balance = 120
```

Diagnose it in your own words: Is this a lost update, and if so, which update was lost? Name the stale read and the later write that provide the decisive evidence, then compare the observed final balance with the balance expected if both operations took effect. You can also say “I don’t know yet.”

## Learner — first attempt

Yes, it is a lost update. B1 is the stale read and B3 overwrites A3. I think B's deposit was the update that got lost because A wrote first. If both applied, it should be 90, but it ends at 120.

## Tutor — repair and worked example

You correctly found the stale read, the overwrite, and both final balances. One label is reversed: **A’s withdrawal was lost**, not B’s deposit. The final `120` still contains B’s `+20`, but A’s `−30` has disappeared.

Use this rule: don’t ask which update wrote first; ask **which update’s effect is absent after the later stale-based write**.

Worked example:

```text
Counter starts at 10

T1 reads 10, computes 12
T2 reads 10, computes 15
T2 writes 15
T1 writes 12
```

The final `12` contains T1’s `+2`; T2’s `+5` is absent. Therefore T1’s later write overwrote—and lost—T2’s update.

Now revise the original diagnosis in one causal sentence: which update was lost, and how did `B1` followed by `B3` cause that loss?

## Learner — corrected explanation

A's withdrawal was lost: B1 read the old balance of 100 before A's write, so B3 later wrote 120 from that stale value and erased A's minus 30 effect.

## Tutor — unseen transfer prompt

Exactly. You now have the right causal chain: stale snapshot → later write derived from it → earlier effect disappears. Because I supplied the decision rule first, this counts as a scaffolded correction; now try it independently in a different form.

```text
Shared record initially:
{ title: "Draft", archived: false }

Thread A                              Thread B
A1: read the whole record
                                      B1: read the whole record
A2: change its copy's title
    to "Final"
                                      B2: change its copy's archived
                                          value to true
A3: write its whole copy:
    { title: "Final", archived: false }
                                      B3: write its whole copy:
                                          { title: "Draft", archived: true }
```

Final record:

```text
{ title: "Draft", archived: true }
```

Diagnose this fresh case: is it a lost update even though the threads changed different fields? Identify the lost update, the stale read, and the overwriting write, then state what the record should contain if both intentions survive.

## Learner — unassisted transfer attempt

Yes, it is still a lost update. B1 read the old whole record with title Draft. B3 later overwrote A3 with that stale title, so A's title change to Final was lost. If both intentions survived, the result should be `{ title: "Final", archived: true }`.

## Tutor — evidence-calibrated close

Correct. You identified all four decisive elements: B’s stale whole-record read, B3’s later overwrite, A’s missing title change, and the intended combined state.

Evidence observed:

- On the first case, you found the race but reversed which update was lost; you corrected that after an explicit rule and worked example, so that success was scaffolded.
- On this fresh case, you transferred the reasoning to a non-numeric whole-record update with no case-specific hint. That is evidence of immediate, unassisted transfer.

This supports “can currently diagnose an explicit two-thread lost-update trace.” It does not yet establish delayed retention or durable mastery because we have not tested you after a delay or against a confusable safe-concurrency case.

A suitable next check is a no-hint discrimination pair in 48–72 hours: one genuine lost update and one concurrent trace where both effects safely survive. Diagnose which is which and justify from the reads, writes, and final state. No files or learner state were created.
