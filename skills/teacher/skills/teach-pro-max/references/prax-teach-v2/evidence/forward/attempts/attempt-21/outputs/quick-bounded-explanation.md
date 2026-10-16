# Composite-index explanation

A composite index on `(a, b)` is ordered first by `a`, then by `b` within each `a` value—like a phone book sorted by last name, then first name.

So for:

```sql
SELECT * FROM t WHERE a = 42;
```

the database can jump directly to the section where `a = 42` instead of scanning the whole table. In index terms, `a` is the leftmost prefix of `(a, b)`.

The same index commonly helps:

```sql
WHERE a = 42 AND b = 7
```

but usually does not efficiently help a query filtering only on `b`, because entries with the same `b` are scattered across different `a` groups.

Whether the database actually uses the index still depends on factors such as table size, selectivity, statistics, and the columns the query must return.
