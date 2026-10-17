# Answer-now override

A **lost update** happens when two operations read the same old value, both compute a change, and the later write overwrites the earlier one.

Example:

- Balance starts at ₹100.
- A reads ₹100 and adds ₹20 → writes ₹120.
- B also read ₹100 and subtracts ₹10 → writes ₹90.
- Final balance is ₹90, but it should be ₹110.

A’s update was “lost.” Prevent it with atomic updates, locking/transactions, or optimistic concurrency checks such as version numbers.
