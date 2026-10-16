# Resume hinted evidence

We’re resuming from the supplied saved snapshot for **composite B-tree index selection**. No filesystem workspace was read.

Saved evidence, preserved exactly:

- Response: “Use the index for WHERE a = 42 because a is the leading indexed column.”
- Correct: `true`
- Hint: `hint_level: 3` (`strongest_hint`)
- Session: `forward-session-1`
- Learner-authored: `true`
- State: `scaffolded`; no later unassisted evidence exists
- Retention horizon: 30 days

Fresh unassisted retrieval:

Given an index on `(a, b, c)`, can it support `WHERE b = 7 AND c = 9`? Answer yes or no, and justify your decision using left-prefix ordering.
