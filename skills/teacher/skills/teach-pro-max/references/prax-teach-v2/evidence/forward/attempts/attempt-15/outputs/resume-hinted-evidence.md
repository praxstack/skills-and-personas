# Resume hinted evidence

Welcome back. I’m using the supplied saved snapshot; no filesystem workspace was read.

Saved response, unchanged: “Use the index for WHERE a = 42 because a is the leading indexed column.”

It was marked `correct=true`, with `hint_level=3 strongest_hint`; status: `scaffolded`, not yet durable because there is no later unassisted evidence.

Fresh retrieval—no hint:

Given an index on `(a, b, c)`, does it efficiently support:

```sql
WHERE b = 7 AND c = 9
```

Answer yes or no, and justify your answer using left-prefix ordering. You can also choose: `inspect`, `correct`, or `retest`.
