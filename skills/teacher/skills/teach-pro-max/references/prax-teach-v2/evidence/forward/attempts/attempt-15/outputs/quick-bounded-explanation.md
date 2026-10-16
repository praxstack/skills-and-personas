# Composite index left-prefix explanation

A composite index on `(a, b)` is sorted first by `a`, then by `b` within each `a` value.

So for:

```sql
SELECT * FROM orders WHERE a = 42;
```

the database can jump directly to the section where `a = 42` and scan only that contiguous portion of the index. It does not need a condition on `b`; the index’s leftmost column, `a`, is enough.

Think of it like a phone book sorted by last name, then first name. You can efficiently find everyone with the last name “Patel” even if you do not know their first name. But finding someone by first name alone is difficult because first names are scattered across the book.

The index is especially useful when `a` is selective, meaning relatively few rows match. The database may still choose a full table scan if the table is small or most rows have `a = 42`.

The key rule is: a composite index generally helps queries using a prefix of its columns—`a`, or `(a, b)`—but usually not queries filtering only on `b`.
