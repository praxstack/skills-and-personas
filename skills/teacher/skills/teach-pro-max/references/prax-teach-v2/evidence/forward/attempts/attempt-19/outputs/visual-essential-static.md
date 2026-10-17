# Lost update: static trace

Suppose `counter = 0` and both threads run:

```python
counter += 1
```

That statement is really three operations:

```text
read counter → add 1 → write counter
```

A possible interleaving:

```text
Counter: 0

Thread A                 Thread B
---------                ---------
read 0
                         read 0
compute 1
                         compute 1
write 1
                         write 1

Final counter: 1
```

Both threads calculated from the same old value, so Thread B overwrote Thread A’s update. The expected result was `2`, but one increment was lost.

The fix is to make the whole read–modify–write operation atomic, commonly with a lock:

```python
with lock:
    counter += 1
```
