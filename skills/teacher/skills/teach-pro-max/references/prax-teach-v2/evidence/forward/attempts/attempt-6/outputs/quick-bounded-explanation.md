# Quick bounded explanation

A composite B-tree index on `(a, b)` is ordered first by `a`, then by `b` within each `a` value. So all rows with the same `a` are grouped together.

For example:

```sql
CREATE INDEX idx_orders ON orders(customer_id, created_at);

SELECT * FROM orders WHERE customer_id = 42;
```

The database can use the index to jump directly to the entries where `customer_id = 42` and scan that contiguous range. It doesn’t need a condition on `created_at`.

This is the **leftmost-prefix rule**: an index on `(a, b)` can generally support searches on:

- `a`
- `a` and `b`

But usually not `b` alone, because entries are not globally ordered by `b`.

It “may” help rather than “will” help because the optimizer might prefer a table scan if the table is small or `a` matches a large proportion of rows.
