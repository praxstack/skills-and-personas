# Quick bounded explanation

A composite B-tree index on `(a, b)` is sorted first by `a`, then by `b` within each `a` value—like a phone book sorted by last name, then first name.

So for:

```sql
SELECT * FROM t WHERE a = 42;
```

the database can jump directly to the contiguous section where `a = 42`, instead of scanning the whole table. This is the **leftmost-prefix rule**: an index on `(a, b)` can generally support queries on `a`, or on `a` and `b`, but usually not efficiently on `b` alone.

It may only help—not always—because the optimizer might prefer a table scan if `a` has low selectivity, the table is small, or the query needs many rows.
