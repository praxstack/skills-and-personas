# Visual route: essential static

Assume `counter` starts at `0`, and both threads execute:

```text
counter = counter + 1
```

Because this is a non-atomic read–modify–write operation, one legal interleaving is:

| Step | Thread A | Thread B | Shared `counter` |
|---:|---|---|---:|
| 0 | — | — | 0 |
| 1 | Read `counter` → `A.tmp = 0` | — | 0 |
| 2 | — | Read `counter` → `B.tmp = 0` | 0 |
| 3 | Compute `A.tmp = 0 + 1` | — | 0 |
| 4 | — | Compute `B.tmp = 0 + 1` | 0 |
| 5 | Write `A.tmp` → `counter = 1` | — | 1 |
| 6 | — | Write `B.tmp` → `counter = 1` | 1 |

Thread B’s final write overwrites Thread A’s update. Two increments occurred, so the expected result was `2`; the actual result is `1`. This is a **lost update** race.
