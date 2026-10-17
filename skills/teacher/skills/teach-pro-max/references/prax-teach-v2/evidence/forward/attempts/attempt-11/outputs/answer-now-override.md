# Answer-now override

A **lost update** happens when two operations read the same old value, each calculates a new value, and the later write overwrites the earlier one.

Example: a counter starts at `10`.

- A reads `10` and plans to write `11`.
- B also reads `10` and plans to write `11`.
- A writes `11`, then B writes `11`.

Two increments occurred, but the result is `11` instead of `12`—A’s update was lost. Atomic updates, locking, or optimistic version checks prevent this.
