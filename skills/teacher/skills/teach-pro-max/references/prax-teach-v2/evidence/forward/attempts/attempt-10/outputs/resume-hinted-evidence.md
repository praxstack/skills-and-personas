# Resume hinted evidence

I’m resuming from the supplied snapshot; no filesystem workspace was read.

Your prior learner-authored response was: “Use the index for WHERE a = 42 because a is the leading indexed column.” It was correct application evidence with hint level `3 strongest_hint`. Its status remains `scaffolded` and not durable because there is no later unassisted evidence. The retention goal is 30 days.

Fresh unassisted retest:

```sql
CREATE INDEX idx_orders
ON orders (customer_id, status, created_at);

SELECT *
FROM orders
WHERE customer_id = 17
  AND created_at >= DATE '2026-08-01';
```

Does this index fully support both filters, only part of them, or neither? Justify your choice using left-prefix ordering.

Reply with **Retest:** followed by your answer. You may instead reply **Inspect** to review the supplied state or **Correct** to dispute it.

This is delivered through host chat without custom artifact controls or scripts; host-UI keyboard, focus, reduced-motion, and assistive-technology behavior remains unverified.
