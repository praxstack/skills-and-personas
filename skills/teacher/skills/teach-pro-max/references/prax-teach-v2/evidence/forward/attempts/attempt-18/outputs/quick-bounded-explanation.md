# Quick bounded explanation

A composite index on `(a, b)` is sorted first by `a`, then by `b`—like a phone book grouped by last name, then first name.

So for:

```sql
SELECT * FROM items WHERE a = 10;
```

the database can quickly jump to the section where `a = 10`, then scan the contiguous matching entries. It does not need a condition on `b`; `b` simply helps order rows within each `a` group.

This is called the **leftmost-prefix rule**:

- `(a, b)` helps queries filtering on `a`
- `(a, b)` can help filtering on both `a` and `b`
- `(a, b)` generally does not help much when filtering only on `b`

It may still choose a table scan if `a` matches most rows or the table is tiny.
