# Two-thread lost update

Assume `counter = 0`. Each increment is three separate operations:

1. Read shared counter
2. Add `1` locally
3. Write local value back

| Step | Thread 1 | Thread 2 | Shared counter |
|---:|---|---|---:|
| 0 | — | — | `0` |
| 1 | Read `0` | — | `0` |
| 2 | — | Read `0` | `0` |
| 3 | Local value becomes `1` | — | `0` |
| 4 | — | Local value becomes `1` | `0` |
| 5 | Write `1` | — | `1` |
| 6 | — | Write `1` | `1` |

Both threads read the same old value, `0`. Thread 2’s write replaces Thread 1’s write with the same value, so two increments produce `1` instead of the expected `2`.

This is a lost update: the read–modify–write sequence must be atomic.
