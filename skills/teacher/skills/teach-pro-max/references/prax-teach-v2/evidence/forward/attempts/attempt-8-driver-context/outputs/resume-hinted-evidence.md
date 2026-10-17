# Resume hinted evidence

I’m resuming from the supplied synthetic snapshot; no filesystem workspace path was supplied, so no filesystem workspace was read.

Your preserved learner-authored response was: “Use the index for WHERE a = 42 because a is the leading indexed column.” It was recorded as correct application evidence with `hint_level: 3` and `hint_label: strongest_hint`. The current status therefore remains `scaffolded`, not `durable`; unassisted application and 30-day retention are still unverified.

Fresh unassisted check:

Given a composite B-tree index on `(tenant_id, created_at, status)`, consider:

```sql
SELECT *
FROM orders
WHERE created_at >= DATE '2026-08-01'
  AND status = 'paid';
```

Assume ordinary left-prefix behavior with no optimizer-specific skip-scan. Would you choose this index to seek efficiently to the matching rows? Answer **yes**, **no**, or **I don’t know**, then justify your choice from the indexed column order.
