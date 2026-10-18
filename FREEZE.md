# Freeze record: Prax Teach v2.1 improvement loop

Written 2026-10-18, before any planning or implementation, as `/Users/prax/AGENTS.md` (identity preservation) requires. Changing anything here needs Prax's explicit approval and a new version of this file.

## Original objective (Prax's words, 2026-10-18)

"Review the skill and make sure it can produce world class all kind of explainer visualisation still, interactive, videos, TTS etc." Then: "World-class aesthetics and mathematically correct still-image explainer artifacts. The best possible approaches, 10 or even 20 different ways, to produce any artifact: a still explainer, an interactive explorer, a Q&A expander, flash cards, or, most importantly, a video explainer and interactive video explorers." Then: run /plan-ceo-review, /plan-eng-review, /product-management:write-spec, /implement-from-spec and /code-review-and-quality in a loop, autonomously, with /deep-research if needed.

## Success definition

The skill, installed from its own package on this Mac, can produce each of the six artifact types for a C or DSA topic with:
1. every displayed value generated from a real compiled run or computed by code, and checked by an automated assertion that fails on tampering;
2. every conceptual claim checked by a separate claims review (values alone are not enough: the v2 proof stated "printf never changes the bits" for a `(double)` cast);
3. a world-class look in light and dark, at 1440 px and 390 px, with measured contrast;
4. narrated video with local TTS, synced WebVTT captions, chapters, measured loudness and inspected frames;
5. teaching behaviour that respects the learner workspace contract (Prax's C workspace: one prediction, wait for the attempt).

## Non-goals

- No claims about human learning outcomes.
- No cloud TTS, cloud rendering or paid services without Prax's permission.
- No edits to the accepted v2 bytes. v2 stays installed and runnable until v2.1 is accepted.

## Baseline (frozen)

- Package: `~/Developer/prax-teach-evaluation-20261016/clean-install-20261018/deliverables/prax-teach-v2-clean-install.zip`, sha256 `c4827533185ad7db90aaf3af25edd97f6cf9d3a8b3e868a1b683ef3ba552205f`, accepted source commit `389f6f9067c40de4ebed10a48d6048ed90d58b0c`.
- Installed copy: `~/.agents/skill-library/prax-teach-v2` (configured, 22/22 JS tests).
- Review of the baseline: `../clean-install-20261018/review-20261018/reports/01..05` (114 issues: 9 critical) and proofs in `../clean-install-20261018/review-20261018/proof/`.

## Rollback pointer

- `~/.agents/skills/prax-teach-v2` is a symlink. Reinstall v2 by pointing it back to `/Users/prax/.agents/skill-library/prax-teach-v2` (the clean v2 install). The pre-2026-10-18 target was `/Users/prax/Developer/skills-and-personas-recovery-20261016/.worktrees/visual-intuition/skills/teach-pro-max/references/prax-teach-v2`.
- v2.1 installs side by side under a new name until accepted; it never overwrites v2.

## Evaluator and holdout

- `holdout/routing-prompts.jsonl`: labelled prompts written before planning. Implementers must not read this folder. Only the acceptance step runs it. Its sha256 is recorded in `holdout/SHA256` so later edits are visible.
- Acceptance compares v2.1 against both the v2 baseline and the last accepted v2.1 candidate. Accept only a held-out improvement with no regression on the protected checks below.

## Protected checks (must never regress)

- v2's 22 JS tests and its passing Python tests still pass, or each removal is justified in writing.
- One skill entry per host (Claude Code, Codex, Hermes, OpenCode).
- The tamper test: a deliberately wrong figure must fail verification.
- No network access at teach time beyond what Prax approved.

## Mutable and protected paths

- Mutable: `~/Developer/prax-teach-evaluation-20261016/v2.1/**`.
- Protected: `~/.agents/skill-library/prax-teach-v2/**` (baseline), the C study repo, every other skill.

## Budget and stop rule

- At most 3 implement→review rounds per spec work package. Stop a package after 2 rounds with no newly passing acceptance check, park it with findings, and continue with the next.
- A run may change the candidate or its spec/evaluator, never both. A spec change needs Prax's approval.
- Report stalls instead of weakening a gate.
