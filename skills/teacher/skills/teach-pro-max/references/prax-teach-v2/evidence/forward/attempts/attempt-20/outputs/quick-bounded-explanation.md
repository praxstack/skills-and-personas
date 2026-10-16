# Composite-index explanation

A composite index on `(a, b)` is sorted first by `a`, then by `b` within each `a` value.

So for:

```sql
SELECT * FROM t WHERE a = 42;
```

the database can jump directly to the contiguous section where `a = 42` and scan only that range, instead of checking every table row. It does not need a condition on `b`; `a` is the index’s leading column.

It may also help avoid table lookups if the index contains everything the query needs. But it usually won’t help much for `WHERE b = ...` alone, because `b` is not the leading column. The optimizer can still choose a full scan when `a` matches most rows or the table is small.

Quick check: why would `(a, b)` generally help `WHERE a = 42 AND b = 7` even more than `WHERE a = 42`?
