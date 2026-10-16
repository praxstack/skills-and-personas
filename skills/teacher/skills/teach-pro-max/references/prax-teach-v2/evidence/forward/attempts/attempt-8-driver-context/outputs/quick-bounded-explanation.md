# Quick bounded explanation

A composite B-tree index on `(a, b)` is ordered first by `a`, then by `b` within each `a` value—like a phone book sorted by surname, then first name.

So for:

```sql
SELECT * FROM t WHERE a = 42;
```

the database can seek directly to the first index entry where `a = 42` and scan only that contiguous range, avoiding a full-table scan. This is the **leftmost-prefix rule**: an index on `(a, b)` can generally support searches on `a`, or on both `a` and `b`, but usually not efficiently on `b` alone.

It may still choose not to use the index if `a` has very few distinct values, the query matches much of the table, or the table is small enough that a full scan is cheaper.
