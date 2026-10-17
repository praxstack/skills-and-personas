# Static lost-update interleaving

Assume one shared variable:

```text
counter = 0
```

Each `counter++` is really three separate operations:

```text
read counter → local value
add 1 to local value
write local value → counter
```

Here is the interleaving:

| Step | Thread 1 | Thread 2 | Shared `counter` |
|---:|---|---|---:|
| 0 | — | — | 0 |
| 1 | Read `counter` → `t1 = 0` | — | 0 |
| 2 | — | Read `counter` → `t2 = 0` | 0 |
| 3 | Compute `t1 = t1 + 1` → `1` | — | 0 |
| 4 | — | Compute `t2 = t2 + 1` → `1` | 0 |
| 5 | Write `t1` → `counter = 1` | — | 1 |
| 6 | — | Write `t2` → `counter = 1` | **1** |

```text
Thread 1:  read 0 ── add 1 ── write 1
Thread 2:       read 0 ── add 1 ── write 1
                                      ↑
                         overwrites Thread 1's write
```

Both threads completed an increment, so the expected result was `2`. The actual result is `1` because both read the old value before either wrote back. This is a **lost update**: Thread 2’s final write replaces Thread 1’s result instead of building on it.
