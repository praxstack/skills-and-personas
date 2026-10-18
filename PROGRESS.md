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
- [x] WP0, round 1 (implement): AC-0.1 to AC-0.5 pass, 24 of 24 gates, status verified. The sandbox-exec render isolation works, so Docker wasn't needed.
- [x] WP0 code review (`reviews/wp0-review.md`): 0 P0, 4 P1, 9 P2, 12 P3. Verdict: fix first.
- [x] Three external sessions read and merged as D20.x (`plan/EXTERNAL-INPUTS.md`). Spec is now v1.1.
- [ ] WP0, round 2 (fix): the four P1s, the cheap P2s, and the design fixes (arcs drawn in the video, recap, filling the frame). **Budget used: 2 of 18 rounds.**
- [ ] Then WP1 ∥ WP2, following D18.5 and the spec v1.1 ACs.
  - [x] WP0 (2026-10-18): AC-0.1 to AC-0.5 pass. `ptk selftest` 8/8, `ptk agent-tests` 1/1. The slice `lessons/switch-fallthrough` is `verified` with 24/24 gates passed and none not-run. Render isolation uses sandbox-exec, not Docker. The real reviewer subagents ran 5 rounds: rounds 1 to 3 found real defects (3 overbroad or wrong claims, a misleading provenance line, an unbacked alt sentence). Every round rejected the planted false claim. Reviews are archived in `.state/review-rounds/`.
- [ ] After WP0 and WP1, ask Prax for one 5-minute predict-first session (D18.6). This doesn't block the tooling packages.
- [ ] Acceptance: run the holdout, the protected map and both exemplars. Prax approves `plan/ACCEPTANCE-PROPOSAL.md` (pending).

## Waiting on Prax
- Pick the one candidate line to keep (recommended: v2.1, importing Neuron Atlas as the taste reference and second exemplar, and retiring the media-routing branch after porting its fixtures).
- An export of `session_019X3PnGRsDY2WNFxYmXJdAk`, if it should be included.
- Approve or edit `plan/ACCEPTANCE-PROPOSAL.md`. That would make it FREEZE v2 and adopt the drafted end-to-end set in `plan/proposed/`.
- The live predict-first session (D18.6).
- Any system-wide installs: BasicTeX or Typst for Manim math (D4.15).
