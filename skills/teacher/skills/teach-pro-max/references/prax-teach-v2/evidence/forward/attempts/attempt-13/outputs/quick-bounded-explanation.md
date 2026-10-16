# Quick bounded explanation

A composite index on `(a, b)` is sorted lexicographically:

```text
(a=1, b=...)
(a=1, b=...)
(a=2, b=...)
(a=2, b=...)
```

So for:

```sql
SELECT * FROM items WHERE a = 2;
```

the database can jump directly to the first entry where `a = 2`, then scan the contiguous block of entries with that value. It does not need to use `b`—the index’s leftmost column is enough to narrow the search.

This is called the **leftmost-prefix rule**: an index on `(a, b, c)` can generally help with filters on `a`, or `(a, b)`, or `(a, b, c)`, but not efficiently with `b` alone.

Whether it actually chooses that index depends on statistics, selectivity, table size, and whether scanning the table is cheaper. The tradeoff is extra storage and slower writes because inserts and updates must maintain both columns in index order.
