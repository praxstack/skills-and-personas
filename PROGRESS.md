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
- [x] WP0, round 2 (fix): the four P1s, P2-1/4/6(label)/7/8 and P3-1/3/7(part)/8/10/11/12, plus the design fixes (arcs drawn in the video, recap without reset, frame filled, file label). Slice `verified`, 26/26 gates, `ptk selftest` 16/16, `ptk agent-tests` 1/1. Reviews archived in `.state/review-rounds/round6-wp0-fix1/`. Deferred: P2-2, P2-3, P2-5, P2-6 evidence, P2-9, P3-2, P3-4, P3-5, P3-6, P3-9. **Budget used: 3 of 18 rounds.**
- [x] WP0 fix round 2 (`34009c9`): the explorer and frame agree at the program change. WP0 is closed after 3 rounds.
- [x] WP1 round 1 (`7530137`, `03ca5a3`): AC-1.1 to AC-1.9 pass. The loader is 2,947 tokens. The dev set scores 109/109, but it is tuned: 12 of 56 fresh phrasings missed before fixes. A review with 60 new prompts is running.
- [x] WP2 round 1 (`75a31ad`): AC-2.1 to AC-2.8 pass, selftest 43/43. The review (`reviews/wp2-review.md`) found 2 P1s: pragmas or line markers can disable the program's own checks, and a symlink gets around the read limit. Fix round 2 is running.
- [ ] Running: WP3 round 1 (stills plus the Atlas dark theme), WP4 round 1 (explorer, Q&A, cards), WP7 round 1 (claims gate, mutations with controls, the %f regression).
- **Budget: 9 of 18 rounds used**, counting one per implement or fix pass: WP0 ×3, WP1, WP2 ×2, WP3, WP4, WP7. Left: fix rounds for WP1, WP3, WP4 and WP7, then WP5, WP6, WP8 and WP9. If the budget runs out, stop and report per FREEZE. Do not extend it.
- [ ] After WP0 and WP1, ask Prax for one 5-minute predict-first session (D18.6). This doesn't block the tooling packages.
- [ ] Acceptance: run the holdout, the protected map and both exemplars. Prax approves `plan/ACCEPTANCE-PROPOSAL.md` (pending).

## Waiting on Prax
- Pick the one candidate line to keep (recommended: v2.1, importing Neuron Atlas as the taste reference and second exemplar, and retiring the media-routing branch after porting its fixtures).
- An export of `session_019X3PnGRsDY2WNFxYmXJdAk`, if it should be included.
- Approve or edit `plan/ACCEPTANCE-PROPOSAL.md`. That would make it FREEZE v2 and adopt the drafted end-to-end set in `plan/proposed/`.
- The live predict-first session (D18.6).
- Any system-wide installs: BasicTeX or Typst for Manim math (D4.15).
