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

## Integration notes (orchestrator)
- WP3 closed at round 1 (`e7b67e5`): AC-3.1 to AC-3.7 pass. Dark theme follows Atlas. Coral replaces Atlas salmon (it was 0.4 L* from lavender); the rule is raised to 3.35:1; Nunito Sans stands in for Avenir. Claims verify is waiting on integration.
- WP2 closed after 2 rounds (`d107345`, `2f89d7d`). Rerun myself: 21 bypass, 31 capture and 14 security tests pass.
- **Integration pass** (after WP4 and WP7 land): rebuild every medium of the switch lesson, run every claims job once, then `ptk claims check`. Builders do not rerun full lesson reviews mid-flight, because changing inputs make them stale.
- **Open bugs for WP8:**
  - `ptk build --only <x>` deletes the outputs of other media (seen with `--only still` deleting `build/ive`).
  - `.state/selftest-*.json` is shared between runs that happen in parallel.
- WP1 closed after 2 rounds (`eb55c96`). It now handles negation and refusal, a rebuild intent, and confidence, and the protocol checker grades against ground truth. The loader is 3,542 tokens. Fresh 60/60; untuned probes written after the fix 17/20.
  - Known misroutes: "forget the video", "regenerate the flashcards", "can you not ask me to guess".
  - The hidden holdout measures routing at acceptance.
- **Rule for every builder:** no `git stash`, no amend, no history rewrite in the shared tree.
- **Budget: 10 of 18 rounds used.**
- Orchestrator hotfix `3b89295`: dropped the capture hard-link check. A macOS background process gives new files under ~/Developer a second link within seconds, so every new lesson was rejected. I reproduced it, then added a test.
- WP4 closed at round 1. AC-4.1 to AC-4.8 pass, and each test also checks a tampered copy. The real Anki import is not-run because Anki isn't installed. Remaining weak spots: the explorer has no diagram beyond the code path, and the Q&A is a single column at 1440.
- WP5 round 1 running: video quality (no hard cut at the program change, no empty panels, an Atlas palette option), a renderer-neutral interface, sync failure fixtures, the `--only` deletion bug.
- **Budget: 12 of 18 rounds used.** Left: WP6, WP8, WP9, the integration pass, and one consolidated five-lens review of WP3, WP4, WP5 and WP7.
- **For WP8:** add genanki to `ptk host setup` (currently only in `registry/requirements-cards.txt`).
- WP7 closed at round 1. AC-7.1 to AC-7.6 pass. Real reviewer subagents caught value mutations 6/6 and claim mutations 15/15, and accepted 21/21 controls. The %f regression was rejected twice and the corrected claim accepted. Jobs are about 5.9k tokens, but each reviewer run costs about 90k.
- **D21.1 (orchestrator, cost):** the full mutation suite (up to 12 mutations plus controls) becomes a calibration run. It runs on a rubric or reviewer-model change and at acceptance. A normal build writes the lesson job plus one canary mutation, so each build still proves the reviewer catches a planted error, at about 2 reviews instead of 23. This is a spec v1.2 change to AC-7.1, made in the integration pass (build.py and claims.py).
- WP8 round 1 running: packaging, hosts, renderer port, state engine port, registry, protected map.
- **Budget: 13 of 18 rounds used.**
- WP5 closed at round 1 (`7c7cf66`). AC-5.1 to AC-5.7 pass: −16.0 LUFS, sync 0.05 s at starts and 0.11 s at ends, WER 2.9%. `hyperframes check` gives 0 errors and 0 warnings. The program change is now a diff, and the dark Atlas palette is the default video theme. I looked at the frames myself; they are polished.
  - Open: at 37.2 s the note already says "With a break..." while the frame still shows fallthrough.c. Assigned to WP6.
- WP6 round 1 running: FILM/EXPLORE/RETURN, half-open chapters, one-frame seek tolerance, file://, the poster flake.
- **Budget: 14 of 18 rounds used.**
- WP8 closed at round 1 (`2df1ab6`). AC-8.1 to AC-8.8 pass. The package is 2.3 MB and reproducible. Real Codex and Hermes discovery each find one entry. Rollback is tested on 4 hosts. The ported state engine passes 106 v2 tests. The renderer passes on Node 22 and 24. npm audit is clean.
- **Integration bug (found by WP8, cause confirmed by the orchestrator):** new files under ~/Developer **and Prax's C study workspace** get st_nlink 2 within about 6 s; the home folder root does not. A Time Machine backup (backupd) was running, and revisiond is also active. The ported v2 state engine refuses hard-linked state files, so learner-state writes in the study workspace would fail intermittently.
  - Fix in the integration pass: accept nlink>1 for regular files the user owns, opened with O_NOFOLLOW, and log a warning.
  - Record it in PROTECTED-MAP.md as a changed protected behaviour, with this reason.
- **Budget: 14 of 18 rounds used.** WP8 was counted when it started.
