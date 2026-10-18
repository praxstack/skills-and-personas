# Host adapters: running claims-review jobs

`ptk build` stops at `claims-pending` (exit 4) after writing `build/claims-jobs/<job>.json`:
one lesson job, plus up to 12 mutation jobs, each paired with a control. They all look alike on
purpose. The build report's `claims.jobs` lists them and `claims.job_tokens` gives their size.

## The contract (every host)

1. **One fresh subagent per job.** Don't reuse a subagent across jobs and don't batch jobs into one prompt.
   The subagent must not have seen the build, the lesson folder or another job.
2. **It reads exactly two files:** the job file and the rubric at the job's `rubric_path`
   (`ptk/verify/rubric.md`). Tell it not to open anything else. Don't paste the build report,
   `mutations.json`, anything under `$PTK_STATE/claims-private/`, or your opinion of the claims.
   Don't say which job is the lesson, a mutation or a control. You don't know either: the roles live
   only in `$PTK_STATE/claims-private/`.
3. **It writes one JSON file** to the job's `review_path`, and nothing else.
4. **Then run `ptk claims check <lesson>`.** It checks each review's schema, coverage and manifest echo,
   and recomputes each manifest from the current lesson, artifact texts, sources and rubric.
   - exit 0: verified. Exit 1: a reviewer rejected something, a review is stale, or the catch or
     control rates miss the thresholds. Read `ptk report <lesson>`.
   - exit 4 again: some reviews were unusable (empty, a refusal, prose, wrong schema). ptk moved each
     one to `claims-review/invalid/` and added a `retry` block with a schema reminder to its job file.
     Run those jobs once more, each in a new subagent, then `ptk claims check` again. A second bad
     review fails the gate with `ClaimsReviewInvalid`.
   - exit 5: reviews are missing. Run the jobs that have no file at `review_path`.
5. **If the host can't run subagents,** leave the reviews missing. The gate stays `not-run` and the
   build is `incomplete`. Never write a review yourself, and never report the lesson as verified.

The prompt for each job (fill in the two paths):

> You are a claims reviewer. Read the rubric at RUBRIC and the job at JOB. Don't open any other file.
> Follow the rubric and write the review JSON to the job's review_path. Reply with one line: the
> review path and the overall verdict.

## Per host

| Host | One job | Parallel | Notes |
|---|---|---|---|
| Claude Code | Agent tool, one call per job, `subagent_type: general-purpose`, the prompt above. | Several Agent calls in one message. | The Agent tool starts each subagent with a clean context. |
| Codex | `codex exec --ephemeral -s workspace-write -C <build dir> "<prompt>"` | One process per job; run them side by side. | `-s workspace-write` lets it write `claims-review/`; `--ephemeral` keeps no session to leak into the next job. |
| Hermes | `hermes -z "<prompt>" --in <build dir> --ignore-rules` | One process per job. | `-z` is one-shot (prints only the final reply); `--ignore-rules` keeps AGENTS.md, memory and preloaded skills out of the reviewer's context. |
| OpenCode | `opencode run "<prompt>"` from the build dir, one per job. | One process per job. | Not installed on this Mac (2026-10-18); command taken from OpenCode's documented non-interactive mode. Until it is installed and tested, treat OpenCode as a host without subagents (step 5). |

## The agent-mediated test suite

`ptk agent-tests` writes the same kind of jobs for the claims tests and exits 4:

- `tests/test_regression_f_cast.py::test_same_bits_claim_rejected` (AC-7.6): two jobs under
  `$PTK_STATE/agent-tests/claims/f-cast-regression/`.
- `tests/test_mutation_claims.py::test_real_reviewer_rates` (AC-7.5): jobs under
  `$PTK_STATE/agent-tests/claims/rates/<lesson>/`.

Run every listed job with the contract above, then `ptk agent-tests` again. Reviews of unchanged jobs
are kept, because a job id is its manifest hash; any input change gives new job ids and needs new reviews.
