# Resume hinted evidence

Course resumed for composite B-tree index selection.

Prior evidence (preserved): “Use the index for WHERE a = 42 because a is the leading indexed column.” Correct, learner-authored application response, `hint_level: 3` (`strongest_hint`). Status: scaffolded; no unassisted evidence yet.

Fresh retrieval: An index is `(customer_id, created_at)`. Can it support:

```sql
WHERE created_at >= '2026-01-01'
```

Answer yes/no and justify using left-prefix ordering.
