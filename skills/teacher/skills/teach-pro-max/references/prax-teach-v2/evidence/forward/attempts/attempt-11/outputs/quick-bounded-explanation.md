# Quick bounded explanation

Think of an index on `(a, b)` as a phone book sorted:

1. first by `a`
2. then by `b` within each `a`

So for:

```sql
WHERE a = 42
```

the database can jump directly to the section where `a = 42`, then scan only that section. This works because `a` is the index’s leftmost column.

By contrast, filtering only on `b` often cannot use the index efficiently: matching `b` values may be scattered across every `a` section.

The index may still not help much if `a` has very few distinct values or the query returns most of the table—the optimizer may prefer a table scan. But structurally, `(a, b)` can support searches on `a`, as well as searches on both `a` and `b`.
