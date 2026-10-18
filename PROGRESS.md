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
- [x] CEO review complete: 3 spec-review rounds, the Codex outside voice and the review report.
- [x] Eng review complete: E0–E25, `plan/TEST-PLAN.md`, Codex eng outside voice.
- [x] `spec/SPEC.md` written: EARS criteria AC-0.x to AC-9.x, each with a named test.
- [ ] /implement-from-spec, WP0 first (vertical slice and spikes), in the dependency order of D18.5. Budget: 18 implement-and-review rounds in total.
- [ ] After WP0 and WP1, ask Prax for one 5-minute predict-first session (D18.6). This doesn't block the tooling packages.
- [ ] Acceptance: run the holdout, the protected map and both exemplars. Prax approves `plan/ACCEPTANCE-PROPOSAL.md` (pending).

## Waiting on Prax
- Approve or edit `plan/ACCEPTANCE-PROPOSAL.md`. That would make it FREEZE v2 and adopt the drafted end-to-end set in `plan/proposed/`.
- The live predict-first session (D18.6).
- Any system-wide installs: BasicTeX or Typst for Manim math (D4.15).
