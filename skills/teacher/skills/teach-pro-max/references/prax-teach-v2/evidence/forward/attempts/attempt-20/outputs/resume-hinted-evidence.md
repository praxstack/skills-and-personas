# Resumed scaffolded evidence

Resuming from the supplied snapshot for **composite B-tree index selection**.

Previous evidence preserved: “Use the index for WHERE a = 42 because a is the leading indexed column.” Correct, learner-authored, with `hint_level: 3` (`strongest_hint`). Status: scaffolded; no unassisted evidence yet. No filesystem workspace was read.

Fresh retrieval—no hint:

Given an index on `(customer_id, created_at, status)`, can it efficiently support this query?

```sql
WHERE created_at >= '2026-01-01'
  AND status = 'open'
```

Answer yes or no, and justify your decision using left-prefix ordering.
