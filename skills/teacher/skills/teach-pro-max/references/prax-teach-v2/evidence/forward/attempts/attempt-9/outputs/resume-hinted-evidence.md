# Resume hinted evidence

I resumed from the supplied synthetic snapshot; no filesystem workspace was read because no validated path was supplied, and no files were changed.

The preserved evidence is:

- Original response: “Use the index for WHERE a = 42 because a is the leading indexed column.”
- Result: correct
- Dimension: application
- Hint level: `3`
- Hint label: `strongest_hint`
- Session: `forward-session-1`
- State: scaffolded, not durable

One correct response with that hint does not yet show independent performance. You can inspect, correct, or retest this state at any time.

This retrieval is delivered through host chat without custom artifact controls or scripts. Host-UI keyboard, focus, reduced-motion, and assistive-technology behavior remain unverified.

**Learner action — fresh unassisted retrieval:** A table has a composite B-tree index on `(customer_id, created_at, status)`. Under ordinary left-prefix lookup—ignoring skip-scan and full index scans—can it support an efficient seek for this query?

```sql
SELECT *
FROM orders
WHERE created_at >= DATE '2026-07-01'
  AND status = 'paid';
```

Reply **yes**, **no**, or **I don’t know**, then justify your choice by naming the usable contiguous left prefix, if any.
