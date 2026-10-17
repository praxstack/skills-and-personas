# Answer-now override

A lost update happens when two concurrent operations read the same old value, modify it, and write back—so the later write overwrites the earlier one.

Example: both requests read a counter as `10`, each adds `1`, and both save `11`; one increment is lost. Prevent it with atomic updates, row locks, or optimistic locking/version checks.
