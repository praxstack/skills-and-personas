# Resume hinted evidence

I’m resuming from the supplied snapshot; no filesystem workspace was read because no validated path was supplied.

Your prior response was: “Use the index for WHERE a = 42 because a is the leading indexed column.” It was correct, learner-authored application evidence at hint level `3` (`strongest_hint`). It remains `scaffolded`, not durable, because there is no later unassisted evidence.

Fresh unassisted retest: Assume an ordinary composite B-tree index on `(a, b, c)`, with no skip-scan. For:

```sql
WHERE a = 42 AND b >= 10 AND c = 7
```

Which predicates can narrow the index search bounds, and why, based on left-prefix ordering?
