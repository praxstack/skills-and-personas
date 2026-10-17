# Visual route: essential static

Assume `counter = 0` and each `counter++` expands to:

`read counter → add 1 locally → write result`

| Step | Thread 1 | Thread 2 | Shared `counter` |
|---:|---|---|---:|
| 0 | — | — | **0** |
| 1 | Read `counter` into `r₁` → `r₁ = 0` | — | 0 |
| 2 | — | Read `counter` into `r₂` → `r₂ = 0` | 0 |
| 3 | Compute `r₁ + 1` → `r₁ = 1` | — | 0 |
| 4 | — | Compute `r₂ + 1` → `r₂ = 1` | 0 |
| 5 | Write `r₁` → `counter = 1` | — | **1** |
| 6 | — | Write `r₂` → `counter = 1` | **1** |

```text
Thread 1:  read 0 ── compute 1 ── write 1
Thread 2:       read 0 ── compute 1 ────── write 1
                                               ↑
                                  overwrites the shared counter
```

Both threads incremented, so the expected result was `2`. The actual result is `1` because both calculated from the same old value. This is a **lost update**: the complete read–modify–write operation was not atomic.
