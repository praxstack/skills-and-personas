# Quick bounded explanation

A composite B-tree index on `(a, b)` is sorted first by `a`, then by `b` within each `a` value:

```text
(a=1, b=2)
(a=1, b=7)
(a=2, b=1)
(a=2, b=9)
```

Because every row with the same `a` is contiguous, a query such as:

```sql
SELECT * FROM records WHERE a = 2;
```

can seek directly to the first `a = 2` entry and scan only that section of the index. This is called the **leftmost-prefix rule**: an index on `(a, b)` can generally support predicates on `(a)` or `(a, b)` because both begin with the index’s first column.

The reverse usually isn’t true. Filtering only on `b` cannot perform the same efficient seek because `b` values are scattered across the different `a` groups.

“May help” matters: the optimizer might still prefer a table scan if `a` matches most rows, and a dedicated index on `(a)` is smaller and cheaper to maintain. But if you already need `(a, b)` for other queries, it can often serve queries filtering only on `a` too.
