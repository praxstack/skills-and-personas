# Quick bounded explanation

A composite index on `(a, b)` is sorted first by `a`, then by `b` within each `a` value—like a phone book sorted by last name, then first name.

So for:

```sql
SELECT * FROM orders WHERE a = 42;
```

the database can jump directly to the first index entry where `a = 42` and scan only that contiguous section. It doesn’t need a condition on `b`; `b` simply refines the ordering inside the matching `a` group.

This is the **leftmost-prefix rule**: an index on `(a, b)` can generally support searches on:

- `a`
- `a` and `b`

But usually not efficiently on `b` alone, because identical `b` values are scattered across different `a` groups.

It “may” help because the optimizer can still prefer a full table scan when the table is small or the `a` filter matches a large share of rows.
