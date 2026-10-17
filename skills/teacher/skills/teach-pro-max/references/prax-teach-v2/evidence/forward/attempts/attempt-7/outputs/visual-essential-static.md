# Visual route: essential static

Assume `counter = 0` and `counter++` is not atomic:

```text
counter++ means:
1. read counter into a private temporary
2. add 1 to that temporary
3. write the temporary back
```

| Step | Thread A | Thread B | Shared `counter` |
|---:|---|---|---:|
| 0 | — | — | 0 |
| 1 | Read `counter` → `a = 0` | — | 0 |
| 2 | — | Read `counter` → `b = 0` | 0 |
| 3 | Compute `a = a + 1` → `1` | — | 0 |
| 4 | — | Compute `b = b + 1` → `1` | 0 |
| 5 | Write `a` → `counter = 1` | — | 1 |
| 6 | — | Write `b` → `counter = 1` | **1** |

Static timeline:

```text
Thread A:  read 0 ── compute 1 ── write 1
Thread B:       read 0 ── compute 1 ── write 1
Shared:    0 ───────────────────→ 1 ──→ 1
                                           ↑
                              overwrites A's update
```

Two increments occurred, so a serial execution would finish at `2`. Instead, both threads calculated from the same stale value, and Thread B’s write replaced Thread A’s contribution. The final value is therefore `1`: a **lost update** race.
