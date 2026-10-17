# Lost update: static trace

Assume `counter = 0`, and each `counter += 1` expands into three non-atomic steps:

```text
read shared counter → add 1 locally → write result back
```

```text
Shared counter: 0

Step   Thread 1                         Thread 2                         Shared
────   ──────────────────────────────   ──────────────────────────────   ──────
 1     reads counter → local1 = 0                                        0
 2                                      reads counter → local2 = 0        0
 3     local1 = local1 + 1 → 1                                           0
 4                                      local2 = local2 + 1 → 1           0
 5     writes local1 → counter = 1                                       1
 6                                      writes local2 → counter = 1       1
                                         ▲
                                         └─ overwrites Thread 1's update
```

Both threads incremented their private copy, but both started from `0`. Therefore:

```text
Expected counter: 2
Actual counter:   1
Lost updates:     1
```

The race exists because the complete read–modify–write operation was not atomic.
