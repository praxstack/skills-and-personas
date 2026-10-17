# Resumed scaffolded evidence

Resume point: composite B-tree index selection.

The supplied saved state records this exact prior response:

> “Use the index for WHERE a = 42 because a is the leading indexed column.”

It was correct, but used `strongest_hint`, so it is scaffolded evidence—not yet unassisted mastery. No filesystem workspace was read; we’ll continue in this chat without creating learner-state files.

Fresh retrieval—no hint yet:

An index is defined on `(a, b, c)`. Can it support this query?

```sql
SELECT * FROM t WHERE b = 7 AND c = 9;
```

Answer **yes or no**, and justify your decision using left-prefix ordering.
