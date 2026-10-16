# Resume hinted evidence

I’m resuming from the supplied saved snapshot; no filesystem workspace was read.

Goal: composite B-tree index selection. Choose whether an index supports an unseen query and justify it from left-prefix ordering. Retention horizon: 30 days.

Preserved prior evidence:

- `concept_id`: `composite-index-left-prefix`
- `dimension`: `application`
- Original learner-authored response: “Use the index for WHERE a = 42 because a is the leading indexed column.”
- `correct`: `true`
- `hint_level`: `3`
- `hint_label`: `strongest_hint`
- `session_id`: `forward-session-1`
- `learner_authored`: `true`

The derived state remains `scaffolded` and non-durable: one correct application response used the strongest hint; no later unassisted evidence exists. This is not yet unassisted mastery.

Next retrieval — answer without a hint:

A composite B-tree index is `(a, b)`. A new query filters only `b = 42`. Can the index efficiently support this query? Answer yes or no and justify your decision from left-prefix ordering.
