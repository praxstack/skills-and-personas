# Two-thread lost update

Initial state: `counter = 0`

Both threads execute: `counter = counter + 1`

```text
Step   Thread 1                  Thread 2                  Shared counter
----   ------------------------  ------------------------  --------------
1      reads counter: 0                                    0
2                               reads counter: 0            0
3      computes 0 + 1 = 1                                  0
4                               computes 0 + 1 = 1          0
5      writes 1                                            1
6                               writes 1                    1
```

Both threads read the same old value, `0`. Each computes `1`, and Thread 2 overwrites Thread 1’s write with `1`.

Expected result: `2`  
Actual result: `1`

The increment is a read–modify–write sequence, not one indivisible operation. A lock or atomic increment is required to prevent this interleaving.
