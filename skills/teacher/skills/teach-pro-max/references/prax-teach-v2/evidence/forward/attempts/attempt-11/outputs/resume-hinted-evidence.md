# Resume hinted evidence

Resumed from the supplied snapshot `forward-resume-index-course`; no filesystem workspace was read because no validated path was supplied.

Your prior response was: “Use the index for WHERE a = 42 because a is the leading indexed column.” It was correct, with exact `hint_level: 3` and `hint_label: "strongest_hint"`. That counts as scaffolded application evidence, not durable mastery.

Fresh unassisted check: Given an index on `(customer_id, created_at)`, which query can use its left-prefix ordering more directly—and why?

1. `WHERE customer_id = 42 AND created_at >= '2026-08-01'`
2. `WHERE created_at >= '2026-08-01'`
