# Lost update: static trace

`counter += 1` is a read–modify–write operation, not one indivisible action.

```text
Initial counter = 0

Time   Thread 1                 Thread 2                 counter
───    ────────────────────     ────────────────────     ───────
1      reads 0                                            0
2                               reads 0                    0
3      computes 0 + 1 = 1                                0
4                               computes 0 + 1 = 1        0
5      writes 1                                           1
6                               writes 1                  1
```

Both threads read the same old value, so both calculate `1`. Thread 2 then overwrites Thread 1’s update. The expected result is `2`, but the actual result is `1`: one increment was lost.

An atomic increment or lock makes the read–modify–write sequence indivisible.
