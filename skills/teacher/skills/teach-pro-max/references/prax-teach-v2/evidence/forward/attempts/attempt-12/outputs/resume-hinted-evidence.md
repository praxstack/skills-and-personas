# Resume hinted evidence

Resuming from the supplied snapshot; no filesystem workspace was read.

Your course topic is composite B-tree index selection. The saved learner-authored evidence is unchanged:

> “Use the index for WHERE a = 42 because a is the leading indexed column.”

It was recorded as correct with `hint_level: 3` (`strongest_hint`) in session `forward-session-1`. The state remains **scaffolded** because no unassisted evidence exists yet.

Fresh retrieval, without a hint:

Assume an index on `(a, b)`. Can it support `WHERE b = 7`? Explain your reasoning using left-prefix ordering.
