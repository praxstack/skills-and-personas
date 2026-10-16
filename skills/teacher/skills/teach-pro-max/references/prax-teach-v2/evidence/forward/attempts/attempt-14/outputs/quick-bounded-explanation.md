# Quick bounded explanation

A composite index on `(a, b)` is sorted first by `a`, then by `b` within each `a` value. Because `a` is the leading column, the database can jump directly to the section containing `a = 42` instead of scanning the whole table.

For example:

```sql
CREATE INDEX idx ON table_name (a, b);

SELECT * FROM table_name WHERE a = 42;
```

The database can seek to the entries for `a = 42` and scan only that range. It may still need to fetch the full rows, and the optimizer will use the index only if that is cheaper than other plans.

The `b` column does not help narrow a query filtering only on `a`; it becomes useful when the query also filters or sorts by `b`. The same index generally cannot efficiently support a query filtering only on `b`, because `b` is not the leading column.
