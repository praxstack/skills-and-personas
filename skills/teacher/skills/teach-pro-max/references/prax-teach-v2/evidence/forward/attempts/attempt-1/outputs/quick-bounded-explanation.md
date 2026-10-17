# Quick bounded explanation

A composite B-tree index on `(a, b)` is ordered first by `a`, then by `b` within each `a` value. So rows sharing the same `a` are stored together in the index.

For:

```sql
SELECT * FROM items WHERE a = 42;
```

the database can seek directly to the first index entry where `a = 42` and scan only that contiguous range. It doesn’t need a condition on `b`; `(a)` is the leftmost prefix of `(a, b)`.

Think of a phone book sorted by `(last_name, first_name)`: you can efficiently find everyone with the last name “Shah” without knowing their first names.

The index may still be skipped if `a` is not selective or the table is small. And the reverse generally doesn’t hold: filtering only on `b` cannot efficiently seek through an index ordered by `(a, b)`.
