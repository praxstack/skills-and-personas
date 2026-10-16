# Static lost-update interleaving

Assume `counter = 0`, and each `counter++` expands into three operations:

```text
local = counter
local = local + 1
counter = local
```

`local₁` and `local₂` belong to their respective threads.

| Step | Thread 1 | Thread 2 | Shared `counter` |
|---:|---|---|---:|
| 0 | — | — | 0 |
| 1 | Read `counter` → `local₁ = 0` | — | 0 |
| 2 | — | Read `counter` → `local₂ = 0` | 0 |
| 3 | Compute `local₁ = 1` | — | 0 |
| 4 | — | Compute `local₂ = 1` | 0 |
| 5 | Write `local₁` → `counter = 1` | — | 1 |
| 6 | — | Write `local₂` → `counter = 1` | **1** |

Thread 2’s final write is based on its stale earlier read of `0`, so it overwrites Thread 1’s update.

```text
Two increments attempted
Expected final value: 2
Actual final value:   1
Lost update:          1
```

This is a **lost-update race**: the read–modify–write sequence was not atomic.
