# Progress ledger: Prax Teach v2.1 autonomous run

Pipeline Prax asked for on 2026-10-18:
1. /plan-ceo-review
2. /plan-eng-review
3. /product-management:write-spec
4. /implement-from-spec, then /code-review-and-quality, repeated until the review is clean

Use /deep-research where it helps. Run it all without stopping to ask.

## Done
- [x] Installed the v2 clean package at `~/.agents/skill-library/prax-teach-v2`. It's configured and passes 22/22 JS tests. `~/.agents/skills/prax-teach-v2` points to it, and the previous target is recorded in FREEZE.md.
- [x] Linked the hyperframes, hyperframes-cli, hyperframes-core, hyperframes-animation and manim-video skills into `~/.agents/skills`, plus the claude, codex, hermes and opencode mirrors.
- [x] Five reviews of v2 (114 issues) and three proofs: `../clean-install-20261018/review-20261018/{reports,proof}`.
- [x] Wrote FREEZE.md and the routing holdout (hashed) before any planning.
- [x] CEO review: `plan/CEO-PLAN.md`. Scope expansion with approach B, the lesson compiler. Decisions D1–D18 are recorded. The outside voice is `plan/outside-voice-codex.md`. Spec review rounds: 6/10, then 7/10, then round 3 is pending.

## Next
- [ ] Round 3 review result → fill in "Reviewer Concerns", then the GSTACK REVIEW REPORT, then the review log.
- [ ] /plan-eng-review on CEO-PLAN.md.
- [ ] /product-management:write-spec, producing `spec/SPEC.md` with EARS acceptance criteria for each work package.
- [ ] /implement-from-spec, WP0 first (vertical slice and spikes), in the dependency order of D18.5. Budget: 18 implement-and-review rounds in total.
- [ ] After WP0 and WP1, ask Prax for one 5-minute predict-first session (D18.6). This doesn't block the tooling packages.
- [ ] Acceptance: run the holdout, the protected map and both exemplars. Prax approves `plan/ACCEPTANCE-PROPOSAL.md` (pending).

## Waiting on Prax
- Approve or edit `plan/ACCEPTANCE-PROPOSAL.md`. That would make it FREEZE v2 and adopt the drafted end-to-end set in `plan/proposed/`.
- The live predict-first session (D18.6).
- Any system-wide installs: BasicTeX or Typst for Manim math (D4.15).
