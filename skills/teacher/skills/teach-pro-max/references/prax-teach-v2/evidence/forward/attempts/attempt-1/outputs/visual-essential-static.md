# Visual essential static

Assume `counter = 0`, and `counter++` is a three-step read–modify–write operation:

| Step | Thread 1 | Thread 2 | Shared `counter` |
|---:|---|---|---:|
| 0 | — | — | **0** |
| 1 | Read `counter` → `t1 = 0` | — | **0** |
| 2 | Compute `t1 + 1` → `t1 = 1` | — | **0** |
| 3 | Paused | Read `counter` → `t2 = 0` | **0** |
| 4 | Paused | Compute `t2 + 1` → `t2 = 1` | **0** |
| 5 | Write `t1` → `counter = 1` | — | **1** |
| 6 | — | Write `t2` → `counter = 1` | **1** |

Both threads read the old value `0`, so both calculate `1`. Thread 2’s final write overwrites Thread 1’s write.

```text
Expected after two increments: 2
Actual result:                1
Lost update:                  1
```

The race occurs because the entire read–modify–write sequence is not atomic.
