# Answer-now override

A lost update is a concurrency bug where two operations read the same old value, then one write overwrites the other.

Example: a balance starts at 100.

- Transaction A reads 100 and adds 20 → writes 120.
- Transaction B also read 100 and subtracts 10 → writes 90.

The final balance is 90, not 110. A’s update was “lost.” Atomic updates, locking, serializable transactions, or version checks can prevent it.
