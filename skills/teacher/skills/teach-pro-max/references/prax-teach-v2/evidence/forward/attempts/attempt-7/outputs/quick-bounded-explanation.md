# Quick bounded explanation

A typical composite B-tree index on `(a, b)` is ordered first by `a`, then by `b` within each `a` value—like a phone book sorted by last name, then first name.

So for:

```sql
SELECT * FROM t WHERE a = 42;
```

the database can jump directly to the contiguous index range where `a = 42`, instead of scanning the whole table. This is the **leftmost-prefix rule**: an index on `(a, b)` can usually support searches on `a`, or on `a` and `b`, but not efficiently on `b` alone.

It only *may* help because the optimizer might still prefer a table scan—for example, if `a = 42` matches most rows, the table is tiny, or fetching full rows through the index would cost more.
