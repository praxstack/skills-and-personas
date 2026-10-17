# Visual essential static

Two threads both run:

```text
counter += 1
```

That operation is really **read → add → write**:

| Step | Thread | Action | Shared counter |
|---:|:---:|---|---:|
| 0 | — | Initial state | `0` |
| 1 | A | Read `0` | `0` |
| 2 | B | Read `0` | `0` |
| 3 | A | Compute `0 + 1 = 1` locally | `0` |
| 4 | B | Compute `0 + 1 = 1` locally | `0` |
| 5 | A | Write `1` | `1` |
| 6 | B | Write `1`, overwriting A’s result | `1` |

Both increments happened, but both started from the same old value. The final counter is `1`; the expected value was `2`. This is a **lost update**.
