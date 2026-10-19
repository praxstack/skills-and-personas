# Two coordinated goal prompts

The source, reviews and lesson outputs were pushed first at commit 0fa37ee8e8d6b8e25d62f02a45b092de0f3df197 on `archive/prax-teach-handoff-20261019`. The archive verifier checks the published bytes. None of these prompts has been activated.

Read [COUNTERS-RESOLUTION.md](COUNTERS-RESOLUTION.md) for the corrected smoke evidence and counter dispositions, then [ORCHESTRATION.md](ORCHESTRATION.md). It reconciles the plans and states the final recommended architecture, ownership, sequencing and proposed caps. Then read [SHARED-CONTRACT.md](SHARED-CONTRACT.md) and give [CODEX-GOAL.md](CODEX-GOAL.md) to Codex and [CLAUDE-GOAL.md](CLAUDE-GOAL.md) to Claude. The detailed requirements and commands are in [CODEX.md](CODEX.md) and [CLAUDE.md](CLAUDE.md).

Codex owns the general teacher and integration. Claude owns the isolated C adapter. Separate branches, state roots and output paths prevent concurrent edits/builds. Preserve the newer general teacher already in remote main; earlier local-only audits did not include it.

Both commands are single lines below 4,000 characters. They state an end condition, name checks whose actual output must be shown, preserve frozen evaluation, and include a stop condition. Human visual acceptance is separate from a review-ready engineering candidate.

Missing before implementation: approval of the new governing version and finite budgets. The general proposal is 8 rounds; the C proposal is now a choice between the original 3 and Claude's later 4, with privacy retained. These are proposals, not an assumed approval. The prior v2.2 budget is exhausted. Drafting or publishing these commands does not grant either budget. The agent can prepare the exact freeze/plan for that approval without starting candidate changes.
