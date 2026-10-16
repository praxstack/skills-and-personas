# Composite-index explanation

A composite index on `(a, b)` is sorted by `a` first, then by `b` within each `a` value.

So for:

```sql
SELECT * FROM items WHERE a = 42;
```

the database can jump directly to the section where `a = 42`, then scan only that contiguous range. It does not need `b` to use the index; `b` simply provides the secondary ordering.

This is called the **leftmost-prefix rule**: an index on `(a, b)` can generally support lookups on `a`, or on both `a` and `b`, but not efficiently on `b` alone:

```sql
-- Can use (a, b)
WHERE a = 42
WHERE a = 42 AND b = 7

-- Usually cannot use it efficiently
WHERE b = 7
```

It may still choose a table scan if `a` matches a very large fraction of the table, or if fetching the remaining columns from the table costs more than scanning directly. And if the query also needs results ordered by `b` within a particular `a`, the same index may avoid a separate sort.
