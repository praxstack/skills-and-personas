# Two-thread lost update

`counter += 1` is a read–modify–write sequence:

```text
counter = 0

Step   Thread 1                    Thread 2                    Shared counter
----   --------------------------  --------------------------  --------------
1      reads counter: tmp1 = 0                                0
2                                  reads counter: tmp2 = 0      0
3      computes tmp1 = 0 + 1 -> 1                              0
4                                  computes tmp2 = 0 + 1 -> 1  0
5      writes counter = tmp1                                  1
6                                  writes counter = tmp2       1
```

Thread 2 writes its stale value `1` after Thread 1 has already written `1`, overwriting that update. The final counter is `1`, although two increments occurred; the expected result was `2`.
