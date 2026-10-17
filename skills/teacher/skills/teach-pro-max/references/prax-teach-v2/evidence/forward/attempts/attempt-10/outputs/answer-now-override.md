# Answer-now override

A **lost update** is a concurrency bug where two operations read the same old value, calculate separate changes, and the later write overwrites the earlier one.

Example:

- Stock starts at `10`.
- Transaction A sells 1 and calculates `9`.
- Transaction B, still using `10`, sells 2 and calculates `8`.
- A writes `9`; then B writes `8`.

The final value is `8`, but it should be `7`. Transaction A’s update was “lost.”

Common protections include atomic updates, row locking, serializable transactions, and optimistic version checks.
