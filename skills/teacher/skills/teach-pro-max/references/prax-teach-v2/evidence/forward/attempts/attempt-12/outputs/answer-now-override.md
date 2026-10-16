# Answer-now override

A **lost update** is a concurrency bug where two operations read the same old value, then one overwrites the other’s change.

Example:

- Balance is 10.
- A reads 10 and plans to add 5 → 15.
- B reads 10 and plans to subtract 3 → 7.
- A writes 15.
- B writes 7.

The correct result should be 12, but A’s update was lost because B wrote an outdated value afterward.

Prevent it with atomic updates, transactions/row locks, or optimistic locking with a version column.
