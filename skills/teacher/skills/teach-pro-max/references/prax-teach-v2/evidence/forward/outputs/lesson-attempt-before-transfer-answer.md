# Lost-update lesson

## User

Create a focused lesson that teaches me to diagnose a two-thread lost update. Include an unseen transfer task and do not reveal its answer before my attempt.

## Assistant

We’ll build one skill: diagnose a lost update from the exact reads and writes. After this trace and a repair exercise, you’ll get an unseen money-transfer task; its answer stays hidden until you attempt it.

An inventory starts at `stock = 10`:

```text
T1 (sell 3)                 T2 (restock 5)
a = read(stock)  // 10
                            b = read(stock)  // 10
write(stock, a - 3) // 7
                            write(stock, b + 5) // 15
```

Diagnose this run: what value is stored, what value should reflect both operations, and which update disappeared? Explain in 2–4 lines—or say “I don’t know.”

## User

The stored value is 15 and it should be 12. I think the restock disappeared because T2 wrote last, but I’m not fully sure.

## Assistant

Your values are correct: stored `15`, expected `12`.

Hint: compare the final `15` with each operation’s standalone result—sale-only gives `7`, restock-only gives `15`.

Which update disappeared? Revise just that part.

## User

The sale disappeared. T2 calculated 15 from its stale read of 10, then its last write overwrote T1’s sale result of 7.

## Assistant

Correct. T2’s write preserved its own `+5` but replaced the entire shared value, erasing T1’s `−3`.

The diagnostic pattern is: both threads read the same old value, independently compute new values, then write whole replacements. The later write can overwrite the earlier update.

Now compare this schedule:

```text
T1 reads 10
T1 writes 7
T2 reads 7
T2 writes 12
```

Is this still a lost update? Point to the decisive evidence in the trace.

## User

No. T2 reads 7 after T1’s write, so its final 12 incorporates both the sale and restock instead of overwriting a result computed from stale state.

## Assistant

Correct. The decisive evidence is that T2 reads the value produced by T1, so its computation includes both changes.

Unseen transfer task:

```text
Initial: A = $100, B = $40, C = $60

T1: transfer $30 from A to B
T2: transfer $20 from A to C

T1 reads A → 100
T2 reads A → 100
T1 reads B → 40
T2 reads C → 60
T1 writes A → 70
T1 writes B → 70
T2 writes A → 80
T2 writes C → 80
```

Diagnose the execution: give the observed final balances, the balances if both transfers took effect, the exact lost update, and one invariant that exposes the bug.

## User

Observed balances are A=$80, B=$70, C=$80. If both transfers took effect they should be A=$50, B=$70, C=$80. T2’s write of A=$80 overwrote T1’s earlier A=$70, so T1’s $30 debit from A was lost even though its credit to B remained. The total-balance invariant exposes it: observed total is $230 instead of the conserved $200.

## Assistant

Exactly right. You diagnosed the unseen transfer unassisted: final state, intended state, overwritten debit, and violated conservation invariant.

Evidence observed:

- Inventory diagnosis: correct after one orienting hint.
- Safe interleaving discrimination: correct unassisted.
- Novel transfer diagnosis: correct unassisted.

Your decision rule: trace each read’s source, then check whether a later whole-value write erases an earlier update; use invariants to catch impossible outcomes.

Retention horizon: provisionally one week. Re-test in 48 hours using raw logs where you must reconstruct the reads and writes. Durable mastery remains unverified until delayed retrieval. No files or learner state were created.
