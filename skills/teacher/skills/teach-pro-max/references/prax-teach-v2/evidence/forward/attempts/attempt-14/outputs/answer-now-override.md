# Answer-now override

A lost update is a concurrency bug where two operations read the same old value, then one overwrites the other’s change.

Example: both read a balance of $100. One adds $10 and writes $110; the other subtracts $20 based on the old $100 and writes $80. The first update is lost—the correct result should be $90.

Prevent it with locking, optimistic version checks, or an atomic database update.
