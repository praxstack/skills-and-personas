# Answer-now override

A **lost update** is a concurrency bug where two operations read the same old value, each computes a change, and the later write overwrites the earlier one—so one update disappears.

Example: a balance starts at 100.

- A reads 100 and adds 20 → 120
- B also reads 100 and subtracts 10 → 90
- A writes 120
- B writes 90

The final balance is 90, but it should be 110. A’s update was “lost.” Atomic updates, row locks, or version checks can prevent this.
