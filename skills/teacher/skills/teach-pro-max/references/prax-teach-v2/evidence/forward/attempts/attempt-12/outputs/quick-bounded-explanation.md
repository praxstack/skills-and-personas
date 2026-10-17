# Quick bounded explanation

An index on `(a, b)` is sorted by `a` first, then `b`:

```text
(41, 9), (42, 1), (42, 7), (42, 20), (43, 2)
```

For `WHERE a = 42`, the database can jump directly to the contiguous `(42, …)` section instead of scanning every row. The leading column `a` is the useful prefix; `b` is optional for this query.

It generally won’t help much with `WHERE b = 7` alone, because `b` is not the leading column.
