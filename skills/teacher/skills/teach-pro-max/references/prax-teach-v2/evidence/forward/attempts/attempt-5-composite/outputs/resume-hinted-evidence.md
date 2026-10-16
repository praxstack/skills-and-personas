# Resume hinted evidence

I’m resuming from the supplied synthetic workspace `forward-resume-index-course`.

Saved evidence, preserved exactly:

- Original response: “Use the index for WHERE a = 42 because a is the leading indexed column.”
- Result: correct
- Hint level: `3` (`strongest_hint`)
- Classification: scaffolded, not durable
- Remaining uncertainty: no later unassisted evidence exists

No state has been changed.

Unassisted check: Given a composite B-tree index on `(a, b)`, can a query filtering only on `b`, with no condition on `a`, use the index’s left prefix to seek directly to matching rows? Explain your reasoning in one or two sentences. “I don’t know” is fine.
