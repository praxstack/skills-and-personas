# Visual essential static

Assume `counter = 0`, and `counter++` is three operations: read, add, write.

| Step | Thread A | Thread B | Shared `counter` |
|---:|---|---|---:|
| 1 | Read `counter` → `a = 0` | — | 0 |
| 2 | — | Read `counter` → `b = 0` | 0 |
| 3 | Compute `a + 1` → `1` | — | 0 |
| 4 | — | Compute `b + 1` → `1` | 0 |
| 5 | Write `1` | — | 1 |
| 6 | — | Write `1`, overwriting A’s update | 1 |

```text
Expected: 0 + 1 + 1 = 2
Actual:                 1
```

Both threads calculated from the same stale value, so one increment was lost. A lock or atomic increment prevents this interleaving.
