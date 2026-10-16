# Visual essential static

Assume `counter = 0`, and each increment is three separate operations:

```text
read counter → local
local = local + 1
write local → counter
```

| Step | Thread A | Thread B | Shared `counter` |
|---:|---|---|---:|
| 0 | — | — | 0 |
| 1 | Read `0` into `a` | — | 0 |
| 2 | — | Read `0` into `b` | 0 |
| 3 | Set `a = 1` | — | 0 |
| 4 | — | Set `b = 1` | 0 |
| 5 | Write `a` (`1`) | — | 1 |
| 6 | — | Write `b` (`1`), overwriting A’s result | **1** |

```text
Thread A:  read 0 ── add 1 ── write 1
Thread B:         read 0 ── add 1 ── write 1
Shared:           0 ─────────── 1 ────── 1
```

Two increments occurred, so the correct result is `2`. The actual result is `1` because both threads calculated from the same old value, and B’s final write erased A’s increment. This is a **lost update race**.
