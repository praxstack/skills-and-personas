# Quick bounded explanation

A composite index on `(a, b)` is typically ordered first by `a`, then by `b` within each `a` value—like a phone book sorted by last name, then first name.

So for:

```sql
SELECT * FROM items WHERE a = 42;
```

the database can jump directly to the first index entry where `a = 42` and scan the contiguous block of matching entries. It doesn’t need a separate index on `a`; `(a, b)` already has `a` as its leftmost prefix.

Conceptually, the index looks like:

```text
(1, 3), (1, 8), (2, 1), (2, 9), (3, 4)
```

All entries sharing the same `a` are grouped together.

This is called the leftmost-prefix rule:

- `(a, b)` can usually help filters on `a`, or on both `a` and `b`.
- It usually cannot efficiently help a filter only on `b`, because identical `b` values are scattered across different `a` groups.

Whether the database actually uses the index depends on selectivity, table size, statistics, and query cost. If nearly every row has the same `a`, a full table scan may still be cheaper.
