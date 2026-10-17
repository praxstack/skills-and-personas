# Lost-update answer

A **lost update** happens when two operations read the same old value, both modify it, and the later write overwrites the earlier one.

Example: a balance starts at £100.

- Deposit reads £100 and plans to write £110.
- Withdrawal also reads £100 and plans to write £80.
- Deposit writes £110, then withdrawal writes £80.

The correct balance is £90, but it ends at £80—the deposit was lost. Prevent this with atomic updates, locking, or optimistic concurrency checks.
