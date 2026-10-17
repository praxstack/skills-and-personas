# Forward attempt 9 — passed, then invalidated

Attempt 9 passed all eight public forward-behavior cases and its independent
reviewer recomputed all 18 declared bindings. It is retained here rather than
silently overwritten.

It is **not** release evidence for the current package. After that review,
remediation changed teaching and routing sources, including `SKILL.md`,
`references/ARTIFACT-CONTRACT.md`, `references/VISUALIZATION-ROUTER.md`, and
`scripts/praxteach/routing.py`. Those byte changes made the attempt's frozen
source bindings stale. A complete fresh-context rerun of all eight cases is
required; a partial rerun or reuse of these outputs is ineligible.

The archived byte identities are:

- `run.json`: `bf0a5500deac00dc1adf3ef9379beff872638cc8c46f70cb163afb50ee891872`
- `receipt.json`: `f00b43df9983dc4ac1beb585069d71fd29a54901caae07dc7d5f71fd72bf6346`

This archive supports auditability only. It does not support candidate
superiority, accessibility-field, or learner-outcome claims.
