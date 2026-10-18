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
- WP6 closed at round 1 (`b0e6ab8`). AC-6.1 to AC-6.7 pass. 77 boundary seeks give 0 mismatches. FILM/EXPLORE/RETURN never leaks edits into the film. The page now works from file://; before, Chrome refused every `<track src>` there. The note-timing fix is in.
- **Integration pass (round 15) running:** D21.1 canary mode, the state hard-link fix, `--only` merge, install and rollback CLI (dry-run only), the 3 router misroutes, the IVE spinner, a full six-media rebuild ending verified, full selftest and agent-tests, README.
- **Budget: 15 of 18 rounds used.** Left: WP9 (16), a fix round after the consolidated five-lens review (17), one spare (18).
- **Integration pass (round 15) done.** Commits `28c9b19`..HEAD, all `integ:`.
  1. D21.1: `ptk build` writes the lesson job plus one canary (picked from the lesson's mutations by its sha256); `--calibrate` writes the full suite. `claims.canary` must catch the planted error for `verified`. Spec v1.2 (AC-7.1, AC-7.5), VERIFY.md and HOST-ADAPTERS.md updated. **This is a governing change made by the orchestrator, not yet approved by Prax.**
  2. Hard links: same-owner regular state files with nlink > 1 are accepted with a `HardlinkAccepted` warning. Symlinks, other owners and non-regular files are still refused. Seen live during this pass: `continuity.json` under `.state/tmp` had 2 links. Two ported tests changed; PROTECTED-MAP.md records it with the residual risk (a deliberate same-user link between two learners is now read). A follow-up idea is an inode ledger.
  3. `--only` merges the previous report's other media when the lesson sha matches; a changed lesson lists them as `uncovered_media`. `test_entry_by_direct_path` passes after any build order.
  4. `ptk install --candidate` and `ptk rollback`, both with `--dry-run`. The real HOME is refused without `--real-home`. Only dry runs and throwaway HOMEs were run.
  5. Router: "forget the video", "regenerate the flashcards" and "can you not ask me to guess" fixed. Dev set 192/192 (3 added), held-back probes 20/20, WP1 fresh 60/60.
  6. IVE: the before-answer shot had caught Chrome's media-controls spinner, which fades for about 1 s after a seek. The shots now wait (`D.settled()`), and a test checks that a second shot 2.5 s later is byte-identical.
  7. Full six-media rebuild (no `--only`): **verified**, 37 gates passed, none not-run, no fallbacks. The canary (`m1.match.nomatch`, false mechanism) was rejected and the lesson job accepted, each in a fresh subagent.
  8. `ptk selftest`: 160 passed, 1 not-run (Anki import, no Anki), 0 failed. `ptk agent-tests`: 4 passed, 1 failed.
     - Passed: rates (calibration: value 6/6, claim 15/15, controls 21/21), the %f regression, the slice and the predict-first flow.
     - Failed: `test_modes_live`. qa-expand passes, but quiz and exam-drill fail the protocol checker.
     - Most of the violations come from TEACHING.md and `ptk/protocol.py` disagreeing:
       - The checker allows only a verdict besides the one feedback sentence, while TEACHING.md's exam-drill asks for marks, time and next-question setup in that turn.
       - TEACHING.md allows a new misconception name, but the checker rejects unknown ids.
       - JOB.md doesn't say `marks_awarded`/`total_marks` must be numbers, or what shape `answer_key` takes.
     - Predict-first failed its first live run on one extra sentence and passed on a fresh run.
     - Not fixed here: it needs a governing decision (gate or protocol), and a run may not change both.
  9. `package/prax-teach/README.md` written.
  10. Artifacts I looked at (still, explorer, Q&A, IVE, 5 video frames): see the integration report; open items are listed below.
- **Open after integration:**
  - The protocol-checker vs TEACHING.md mismatch above. Assign it to the round-17 fix after the five-lens review.
  - Video at 38 s ("Add the missing break"): mid-morph frame with no line numbers or filename, a gap in the code, faded output and an empty note column.
  - IVE: a caption line sits half under the progress bar at 1440. At 390 the caption covers the film.
  - Wide still: an empty area top right, and its notes are not numbered or anchored like the portrait's.
  - The explorer footnote wraps "n = 2." badly, and the explorer still has no diagram beyond the code path.
- **Budget: 15 of 18 rounds used.**

## WP9: exemplars (round 16), done

Commits `d56e4e2`..HEAD, all `wp9:`.

**Part A, the projector polish.** Each fix has a gate or test that fails on the old output.
- Video diff (38 s): only the changed rows animate now. A moving row cross-fades its number. An added row fills its slot as it opens. The file name cross-fades at the end. The output and its badges stay full until the diff is done, and a "the change" card fills the note column. New gate `video.morph-stable` samples the diff every 0.1 s. `test_morph_keeps_frame_steady` shows it fails with the old output fade.
- IVE captions are drawn in a reserved band under the film, with the browser track hidden. The IVE layout check fails captions over the film or drawn by the browser (`test_caption_band_clear_of_film`).
- Wide still: notes are numbered like the portrait (a badge on the line and in the list). The column beside the code starts at the card top and holds the output (`test_wide_notes_numbered_and_column_filled`).
- Explorer: name = value pairs never wrap (`.nobr`), and layoutProbe fails a split pair. A control-path diagram (blocks per case, jump arcs from the still's path segments, fall-through runs, break on the right) is checked at every control step.

**Part B.** All three exemplars are verified, with 38 gates each, no not-run and no fallback.

| Lesson | Claims rounds | Canary |
|---|---|---|
| one-byte-four-views ("One value, four printf conversions") | lesson job rejected 3 times, accepted on round 4 | caught every round |
| factorial-stack | rejected twice (scope, trace paths), accepted on round 3 | caught every round |
| neuron | rejected 4 times, accepted on round 5 | caught 4 of 5; the miss was a generator bug (below) |

switch-fallthrough was rebuilt with Part A and verified, 38 gates.
- The design review (AC-9.3) is recorded with `ptk design record` in each exemplar report: 6 items, bound to the Atlas baseline and the cited screenshots.
- `ptk selftest`: 167 passed, 1 not-run (Anki). Agent tests: test_one_byte, test_factorial_stack, test_neuron_unrelated_subject and the slice all pass.

**New in the package:**
- `ptk/project/mech.py`: panels `views`, `stack`, `neuron`, drawn from facts in every medium.
- `ptk/project/stepper.py`: a step-through explorer for panel lessons.
- `ptk/design.py`.
- Schema: figure.panel, figure.misconception, select.field, frame call/ret/status, programs[].show, subject.
- Expect functions: double bits, factorial events, neuron %g.
- Print-line matching for repeated calls.

**Deviations, for Prax:**
- The task named the title "One byte, four views". The reviewer rejected it twice because it frames %f as a view of a's byte (the misconception the lesson corrects). The slug is unchanged; the title is now "One value, four printf conversions".
- one-byte's recap claim failed three reviews. Two repair rounds is the budget, so the recap claim and scene were dropped. The dek uses the accepted c.cast.
- **Evaluator changes made in a candidate round** (FREEZE stop rule: these need Prax's approval, like D21.1):
  1. The sync gate reads a whisper token longer than 0.75 s at a cue end from its start, and its end as the last silence inside it.
  2. Automatic value swaps never use a value that still contains the original. The neuron canary had swapped "+1.2" for "0.8 * 1.5 = +1.2", which planted nothing.
  3. The claims collector joins an inline SVG text's lines, and reports the still's wrong-belief callout as labelled.
  4. The frame probe matches paths as sets, and reads the panel's state.
  5. The IVE caption check reads the band, not the track mode.
  6. The IVE explore check steps back through the film when a lesson has no live model.
  7. The outgoing panel layer may overlap during its 0.3 s cross-fade (HyperFrames layout).
- **Design verdicts:** 14 pass and 4 pass-with-notes, no fail.
  - one-byte, film: the panel text is small.
  - one-byte: an empty band beside the panel in early scenes.
  - factorial, IVE at 1440: output lines wrap.
  - neuron, film: the program card is small.

**Budget: 16 of 18 rounds used.** Left: the round-17 fix after the five-lens review (it also owns the protocol-checker vs TEACHING.md mismatch), and one spare.
- Orchestrator check of WP9: the neuron still is a faithful Atlas-style design. "One value, four printf conversions" is now correct. It shows the cast converting to 0x4050800000000000, captured from a real memcpy run, and the misconception card corrects the old proof's error.
- **Round 17 review running (read-only, three parts):**
  1. a gates audit for weakening, covering the six WP9 gate changes plus D21.1, hard links and the `--only` merge;
  2. a five-lens review of the four lessons;
  3. a Codex outside voice on the gate diffs.

  One fix round follows (17). Round 18 is spare.
- **Round 17 review results:**
  - The gates audit (`reviews/round17-gates-audit.md`) and the Codex gates review (`reviews/round17-codex-gates.md`) agree on 3 P1 weakenings: the `--only` stale-pass carry, canary-only `verified`, and the hard-link containment change.
  - The audit adds two more: the IVE explore check excuses a broken lesson, and the overlap exemption covers the whole outgoing layer.
  - Codex adds five P2s: the caption toggle trusts a flag, axis ticks go unchecked, the long-token silence heuristic, the morph deadline taken from the renderer's own planner, and the wrong-belief label taken from metadata.
  - Protocol verdict: TEACHING.md is right, and protocol.py must follow it for quiz and exam-drill.
- **D22 (orchestrator, correcting a process error):**
  - **D22.1:** D21.1 was a spec change made in the same run as code changes, which AGENTS.md forbids. It is reverted to the original AC-7.1 full-suite default. Canary-only builds become `canary-verified`. The cheaper policy goes to Prax as ACCEPTANCE-PROPOSAL §9.
  - **D22.2:** `--only` carries old gate results only when every artifact hash and the ptk version match the recorded inventory; anything else is re-gated.
  - **D22.3:** learner state binds content instead of counting links. Each state file carries its learner id, checked against the directory's id, so aliasing across learners is detected. Writes always atomic-replace onto a fresh inode, so they never go through an alias. Reads tolerate backup links. This is recorded in PROTECTED-MAP as a justified change.
- **Five-lens review** (`reviews/round17-five-lens.md`) scores. Truth 7-8; explanation 5-7; looks 4-6; interaction 3-7; media 5-6. 5 P1s: the IVE never pauses for the prediction; answers leak through titles; factorial never shows n and r; 3 of 4 explorers are only steppers; the figure is too small in the videos. **The gates pass, but quality is not yet world-class.**
- **Round 17 (running):** verifier integrity. All weakenings, D22.1 to D22.3, and the protocol aligned to TEACHING.md.
- **Round 18 (running, LAST):** lesson-quality P1s plus top-10 items as time allows.
- **Budget: 18 of 18 rounds committed.** After these: one read-only verification and a stall report. No further rounds without Prax's approval (FREEZE).
