# Quick bounded explanation

A composite B-tree index on `(a, b)` is sorted first by `a`, and then by `b` within each `a` value.

Think of a phone book ordered by `(last_name, first_name)`. Even if you only know the last name, you can jump directly to that section. Similarly:

```sql
SELECT * FROM records WHERE a = 42;
```

can use the `(a, b)` index to find the contiguous range where `a = 42`, avoiding a full table scan. This is called the **leftmost-prefix rule**: an index on `(a, b)` generally supports queries on `a`, or on both `a` and `b`, but usually not efficiently on `b` alone.

It may not help much if `a` has very few distinct values, the table is tiny, or the query returns most rows—in those cases, the optimizer may prefer a table scan.
