# Answer-now override

A **lost update** is a concurrency bug where two operations read the same old value, then one write overwrites the other.

Example: a balance is 100. Two requests both read 100:

- Request A adds 10 and writes 110.
- Request B subtracts 20 and writes 80.

The correct result is 90, but the final value is 80—A’s update was lost. Atomic updates, locking, or version checks can prevent this.
