# Visual essential static

Assume `counter = 0`. Each `counter++` is really three operations:

```text
read counter → add 1 locally → write result
```

| Step | Thread 1 | Thread 2 | Shared `counter` |
|---:|---|---|---:|
| 0 | — | — | 0 |
| 1 | Read `0` into `t1` | — | 0 |
| 2 | Set `t1 = 1` | — | 0 |
| 3 | — | Read `0` into `t2` | 0 |
| 4 | — | Set `t2 = 1` | 0 |
| 5 | Write `t1` (`1`) | — | 1 |
| 6 | — | Write `t2` (`1`), overwriting Thread 1’s update | **1** |

```text
Expected: 0 + 1 + 1 = 2
Actual:                  1
```

Both threads read the same old value before either write became visible. Each computes `1`, so the second write replaces the first instead of adding another increment. This is a **lost update**, caused by a race condition.
