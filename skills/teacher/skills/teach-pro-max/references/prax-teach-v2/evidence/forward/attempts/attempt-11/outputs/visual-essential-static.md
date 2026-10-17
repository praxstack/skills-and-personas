# Two-thread lost update

Assume `counter` starts at `0`. Each increment is three separate operations:

```text
temporary = counter
temporary = temporary + 1
counter = temporary
```

One possible interleaving:

| Step | Thread A | Thread B | A temporary | B temporary | Shared counter |
|---:|---|---|---:|---:|---:|
| 0 | — | — | — | — | 0 |
| 1 | Read counter | — | 0 | — | 0 |
| 2 | — | Read counter | 0 | 0 | 0 |
| 3 | Add 1 | — | 1 | 0 | 0 |
| 4 | — | Add 1 | 1 | 1 | 0 |
| 5 | Write temporary | — | 1 | 1 | **1** |
| 6 | — | Write temporary | 1 | 1 | **1** |

```text
Expected: 0 + 1 + 1 = 2
Actual:                     1
```

Both threads calculated from the same stale value, `0`. At step 6, Thread B writes its `1` into the same memory location after Thread A already wrote `1`. The stored number remains `1`, so Thread A’s increment is no longer represented. This is a **lost update** race.
