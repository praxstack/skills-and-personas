# Host adapters: running claims-review jobs

`ptk build` exits 4 (claims-pending) after writing `build/claims-jobs/<job>.json`. Each job must be reviewed by a **separate** subagent that sees only:

1. the job file, and
2. `references/CLAIMS-RUBRIC.md`.

Do not tell the subagent which job is the lesson and which is a mutation. Do not paste the build report, the private map (`build/claims-private.json`) or your own opinion of the claims.

The subagent writes its review to the job's `review_path`. Then run `ptk claims check <lesson>`.

| Host | How to run one job |
|---|---|
| Claude Code | Agent tool, one call per job: "Review the claims job at <job path> with the rubric at <rubric path>. Write the review JSON to the job's review_path." |
| Codex | `codex exec "<same prompt>"`, one process per job |
| Hermes, OpenCode | their subagent command with the same prompt |

If the host has no subagent facility, leave the reviews missing: the claims gate stays `not-run` and the build is `incomplete`, never `verified`.
