# Bounded CLI review workers

This launcher transports a small task pack to an installed subscription CLI. It
is not a teaching engine, scheduler, credential manager or evaluator. It does
not install or promote a teaching candidate.

Use `grok` or `cursor-agent`, authenticated through the provider's existing
login. API-key environment variables are removed from the child environment;
cached provider authentication/configuration still needs separate inspection.
The launcher does not guarantee a particular billing arrangement. Never fall
back to API keys or another provider automatically.

## Run one review

Export only the files needed for a task into a scratch directory outside synced
learner-data folders. Include a `TASK.md` with its objective, source references,
allowed actions, output contract and acceptance check. Do not include secrets,
learner records or private evaluation cases. Packs are limited to 200 files /
8 MB and cannot contain symlinks. Keep output outside the pack.

```bash
python3 -B tools/teach-orchestration/run_readonly.py \
  --provider grok \
  --workspace /private/tmp/prax-task-pack \
  --task /private/tmp/prax-task-pack/TASK.md \
  --output /private/tmp/prax-worker-result \
  --timeout 90
```

The output directory must be new. The runner saves raw stdout/stderr and a
receipt with input/output hashes, elapsed time, exit status and input changes.
Keep raw logs local: provider output may contain personal data or reasoning.
Publish only inspected, redacted evidence. Exit zero and
`returned_requires_review` mean transport completed; they never mean the answer
is correct or a product gate passed. Review the answer against its sources,
run the applicable deterministic checks and record acceptance separately.

Grok uses its default model, plan mode, a four-turn cap and disabled web search /
subagents. Cursor requests Composer 2.5 in ask mode. Neither uses force/YOLO or
automatic MCP approval. Read-only modes are provider tool policies, not OS
sandboxing; input hashes detect changes in the exported pack but cannot prove
that no other host path changed. CLI history/caches may still be written. A
local timeout terminates that process group; it cannot promise cancellation of
an already submitted remote request or a provider-owned shared daemon. These
limits rule out giving this runner sensitive data or arbitrary untrusted code.

For implementation, use a separately authorized task in its own worktree with
explicit file ownership, a fixed baseline and checks. This launcher deliberately
does not expose a write mode. The integration owner reviews the diff, verifies
the actual artifacts and decides whether to accept it. A CLI can do edits; this
review transport is not permission to modify teaching code or its evaluator.

## Local checks

```bash
python3 -B tools/teach-orchestration/test_run_readonly.py
```

Tests cover timeout receipts, nonzero exits, input changes, API-key removal,
symlink refusal and the separation of transport success from content acceptance.
They use synthetic local executables, not subscription calls.
