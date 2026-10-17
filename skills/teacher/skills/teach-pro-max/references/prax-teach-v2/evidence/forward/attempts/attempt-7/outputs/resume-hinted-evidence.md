# Resume hinted evidence

I resumed from the supplied synthetic snapshot `forward-resume-index-course`; no filesystem learner workspace was read, and I’ll continue without writing learner-state files.

The learner-authored response is preserved exactly:

> Use the index for WHERE a = 42 because a is the leading indexed column.

It was correct with `hint_level: 3` and `hint_label: "strongest_hint"`. This is scaffolded application evidence—not durable mastery—because no later unassisted evidence exists.

This check is delivered through host chat without custom artifact controls or scripts. Host-UI keyboard, focus, reduced-motion, and assistive-technology behavior remains unverified.

**Your action — fresh unassisted retrieval:** Given a composite B-tree index on `(tenant_id, created_at, status)` and the query `WHERE tenant_id = 7 AND status = 'open'`, can the index support the query through left-prefix ordering? Which indexed columns, if any, form the usable contiguous prefix, and why?
