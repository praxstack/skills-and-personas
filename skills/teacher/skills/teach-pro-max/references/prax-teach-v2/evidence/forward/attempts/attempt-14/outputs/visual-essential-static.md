# Two-thread lost update

Let `counter = 0`. Each increment consists of three separate actions:

1. read the shared value
2. add 1 locally
3. write the local result back

| Step | Thread A | Thread B | Shared `counter` |
|---:|---|---|---:|
| 0 | — | — | 0 |
| 1 | reads `0` | — | 0 |
| 2 | holds local `1` | — | 0 |
| 3 | holds local `1` | reads `0` | 0 |
| 4 | holds local `1` | holds local `1` | 0 |
| 5 | writes `1` | holds local `1` | 1 |
| 6 | — | writes `1` | 1 |

Both threads read the same old value, `0`. Both calculate `1`. Thread B then overwrites Thread A’s write with its own `1`.

Expected after two increments: `2`
Actual result: `1` — one increment was lost.

A lock or atomic increment makes the read–add–write sequence indivisible, so the final value becomes `2`.
