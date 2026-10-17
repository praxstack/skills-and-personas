# Lost-update answer

A **lost update** is a concurrency bug where two actors read the same old value, both modify it, and the later write overwrites the earlier one.

Example: balance is 10.

- A reads 10 and adds 5 → plans to write 15.
- B reads 10 and adds 7 → plans to write 17.
- A writes 15; B writes 17.

The final balance is 17, so A’s update was lost. Usually you prevent this with locking, transactions, or optimistic version checks.
