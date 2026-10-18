# Final verification: Prax Teach v2.1 (acceptance step A)

Run 2026-10-18, about 20:55 to 22:00 IST, at commit `22032c7`. Read-only for the product: no product code, test, lesson or gate was changed.

Where the work ran:
- Clean worktree: `v2.1/.state/final-verify` (`git worktree add --detach`, at HEAD).
- `PTK_STATE` was the main `v2.1/.state`, so the venvs, models, browsers and Node tools were reused. The `bin/ptk` shim falls back to `$HOME/.local/share/prax-teach` in a worktree, so `PTK_STATE` was set explicitly.
- The agent tests used `v2.1/.state/final-verify-state`. It symlinks to the main state, but has its own `agent-jobs`, so the shared protocol transcripts under the main state were never touched.
- Logs, scripts and saved transcripts: `v2.1/.state/final-verify-logs/`.

## Verdict

**Yes. v2.1 beats the v2 baseline on the frozen evaluator, with no protected regression.**

- **Holdout:** v2.1 wins on all three fields: mode 84% vs 63%, visual route 78% vs 47%, medium 72% vs 19%.
- **Protected checks:** all four hold.
  - The v2 JS and Python tests are either ported and passing, or removed with a written reason, as FREEZE allows.
  - Each host gets one entry.
  - Tampering is caught.
  - The network gates pass.
- **No previous accepted v2.1 exists**, so the baseline was the only comparison.

Three things are still open. They don't change the verdict, but Prax should see them before he accepts:
1. **`test_predict_first_flow` failed 2 of 2 fresh live runs**, and both failed the same way: a missing rule that is the same in both runs. TEACHING.md says "name it and give its correction claim", and the tutor names the misconception in its own sentence. The checker allows a single sentence, so it reads that naming sentence as a second correction. The mismatch is between the checker and TEACHING.md, not in tutor quality. It still blocks AC-1.6 as written.
2. **Changes that are still waiting on Prax's approval:**
   - the hard-link protected-behaviour change (PROTECTED-MAP, D22.3);
   - the seven WP9 evaluator changes;
   - ACCEPTANCE-PROPOSAL.
   Until he approves, they stay candidate-side.
3. **All four main-tree lesson builds are `canary-verified`, not `verified`.** The full claims suite (D22.1) runs in final steps B1 and B2, not here.

## 1. Test suites

### `ptk selftest` (217 tests)

| Run | Passed | Not-run | Failed |
|---|---|---|---|
| A. Clean worktree, no lesson builds | 188 | 28 | 1 |
| B. Same worktree, main-tree builds copied in (lesson sha256 matches for all 4) | 199 | 17 | 1 |
| C. The 18 left over from B, rerun one by one after fixing a copy mistake of mine | 16 | 1 | 1 |
| D. The 2 path-bound tests, run from the main tree (its package is byte-identical to HEAD) | 2 | 0 | 0 |
| **Net** | **216** | **1** | **0** |

What each non-pass was caused by:
- **`test_cards::test_anki_import`, not-run.** There is no Anki package or app. This is the known not-run.
- **27 not-run in run A.** Each one needs a built lesson (video, IVE, neuron still, a slice build to tamper, design verdicts). A clean worktree has none, because `build/` is gitignored. With the builds copied in, all 27 pass, except the whisper fixture (below).
  - In run B, the slice build got nested as `build/build`. That was my copy mistake. Once I fixed it, run C passed every IVE and `--only` test.
- **`test_slice::test_entry_by_direct_path`, failed in A, B and C. The test environment caused it, not the product.**
  - In A there is no build report, so `ptk report` prints nothing to stdout and the test raises `JSONDecodeError`. This is a small robustness bug in the test: it should raise NotRun when no report exists.
  - In B and C, the copied report names the main tree's `SKILL.md` and `ptk` path, not the worktree's.
  - It passes from the main tree (run D).
- **`test_media::test_whisper_timestamps_on_fixture`, not-run in the worktree.** It finds its proof MP4 through `V21.parent`, which points to `.state/` inside a worktree. It passes from the main tree (run D).
- **`test_state::test_legacy_unbound_state_migrates`, reported failing before: it passed 7 of 7 times here.** That is once in the full run and 6 repeats in a separate state. The earlier failure ("rebind wrote through the old link") came from the check `st_nlink == 1` on the old inode. A backupd/revisiond hard link to that inode would trip it, and that is the macOS behaviour recorded in PROGRESS. That cause is likely but not proven. The test is timing-sensitive on this Mac.
- **`test_video::test_schedule_from_durations`, failing in an earlier run, passes now.** It was fixed by r18 `8a14788`.

### `ptk agent-tests -k modes` and `-k predict` (live tutor subagents, one fresh subagent per tutor turn)

| Test | Result | Turns |
|---|---|---|
| `test_modes_live` (quiz, exam-drill, qa-expand) | **passed** | quiz 11, exam-drill 9, qa-expand 5 |
| `test_predict_first_flow`, run 1 | **failed** | 7 |
| `test_predict_first_flow`, run 2 (fresh job) | **failed** | 7 |

Both predict-first failures, word for word:
- Run 1: `turn 2: a second correction or explanation besides the one feedback item: 'You expected the next case label to stop it.'`
- Run 2: `turn 2: a second correction or explanation besides the one feedback item: 'That's the "next case label stops it" idea.'`

**Cause.**
- TEACHING.md#predict-first step 4 says: "Misconception: name it and give its correction claim."
- JOB.md says the feedback item is one sentence.
- `protocol.feedback_unit` lets only a verdict, a question or a sentence of four words or fewer sit beside that item.
- Both tutors named the misconception in a separate sentence, then gave the correction as the feedback item.

Everything else in both transcripts passed the checker: classification against ground truth, artifact after the attempt, consent, one evidence event, and the stop rule.

**Fix.** Either the protocol or the job needs to say "name it inside the one sentence", or the checker needs to accept one naming sentence. That is a governing change, so it needs Prax's decision.

**My copy mistake again.** In run 1, the slice still was missing at turn 2, so the tutor showed it at turn 4. That is not the cause of the failure. Run 2 had the still and failed the same way.

Saved transcripts: `.state/final-verify-logs/transcripts/`.

## 2. Routing holdout (frozen evaluator)

The holdout hash matches the frozen record: `sha256(holdout/routing-prompts.jsonl) = 8b9240cc8a6d117f9f9a8400ec1049112d181f665b65dc9d0edaf90b1d52f0b1`, the same as `holdout/SHA256`. The file has 32 prompts. For 4 of them, the C workspace was passed as `--workspace`. The other 28 used an empty temp dir.

### Mapping (written before any prompt was routed, applied by `.state/final-verify-logs/holdout_score.py`)

v2.1 (`ptk route --json`) to the expected labels:

- **mode:**
  - intent `ordinary_task` → `ordinary_task`
  - intent `rebuild` → `lesson`
  - mode `quick` → `quick`
  - every other teaching mode → `lesson`. That covers explain, lesson, predict-first, socratic, quiz, exam-drill, qa-expand and full-pack. The holdout files every bounded teaching session under `lesson`, and v2.1 has no course mode.
- **visual_route:**
  - `ordinary_task` → `none`
  - media has video or ive → `motion`
  - else explorer → `interactive`
  - else still → `static`
  - else `none`
- **medium** (the first rule that applies wins):
  - `ordinary_task` → `none`
  - predict-first → `prediction-first`
  - socratic, quiz and exam-drill keep their own names
  - qa-expand → `qa-expander`
  - quick → `direct-answer`
  - ive → `interactive-video`
  - video with narration → `narrated-video`; video without narration → `video`
  - explorer → `explorer`
  - still → `still`
  - cards → `flashcards`
  - qa → `qa-expander`
  - else the mode name (for example `explain`), which matches no label

v2 to the expected labels. v2 has two routers: `prax_teach.py route --request` and `prax_teach.py visual-route --job`, both given the same prompt.
- **mode:** `ordinary_task` → `ordinary_task`; otherwise the route's mode (quick, lesson or course).
- **visual_route:** `ordinary_task` → `none`; otherwise visual-route's `route` field. That is the requested route, not the delivery route.
- **medium:** v2 has no medium output, so I derived one:
  - ordinary_task → `none`
  - quick → `direct-answer`
  - motion → `video`
  - interactive → `explorer`
  - static → `still`
  - none → `explain`, which matches no label
- v2 takes no workspace input.

### Accuracy

| Field | v2 | v2.1 |
|---|---|---|
| mode | 20/32 (62.5%) | **27/32 (84.4%)** |
| visual_route | 15/32 (46.9%) | **25/32 (78.1%)** |
| medium | 6/32 (18.8%) | **23/32 (71.9%)** |
| all three | 5/32 (15.6%) | **20/32 (62.5%)** |

How much the result depends on my mapping choices:
- **v2.1 `explain` → `quick` instead of `lesson`:** v2.1 mode stays 27/32.
- **v2.1 medium with media before mode-named labels:** H21 becomes a hit, so medium goes to 24/32.
- **v2's medium score** is mostly structural, because v2 has no medium concept at all. The mode and visual-route gaps are the fair comparison.

### Every miss (bold = wrong field)

| id | prompt | ws | expected (mode / visual / medium) | v2.1 | v2 |
|---|---|---|---|---|---|
| H01 | teach me how printf %d works as a narrated video |  | lesson / motion / narrated-video | lesson / motion / narrated-video | lesson / **none** / **explain** |
| H02 | make me a narrated explainer video about pointers |  | lesson / motion / narrated-video | lesson / motion / narrated-video | **ordinary_task** / **none** / **none** |
| H03 | explain recursion with a video I can pause and poke at |  | lesson / motion / interactive-video | lesson / motion / interactive-video | lesson / **none** / **explain** |
| H04 | show the bit pattern of int a = 66 |  | quick / static / still | **lesson** / **none** / **explain** | **lesson** / **none** / **explain** |
| H05 | draw the stack frames for factorial(3) |  | lesson / static / still | lesson / static / still | lesson / **none** / **explain** |
| H06 | let me play with how p++ walks an array |  | lesson / interactive / explorer | lesson / interactive / explorer | lesson / **none** / **explain** |
| H07 | make flash cards for integer promotion in C |  | lesson / none / flashcards | lesson / none / flashcards | **ordinary_task** / none / **none** |
| H08 | quiz me on C integer promotion |  | lesson / none / quiz | lesson / none / quiz | lesson / none / **explain** |
| H09 | give me a Socratic session on malloc and free |  | lesson / none / socratic | lesson / none / socratic | lesson / none / **explain** |
| H10 | what does sizeof(char) return? just the answer |  | quick / none / direct-answer | quick / none / direct-answer | **lesson** / none / **explain** |
| H11 | fix the off-by-one in my loop |  | ordinary_task / none / none | ordinary_task / none / none | ordinary_task / none / none |
| H12 | rename this variable across the file |  | ordinary_task / none / none | ordinary_task / none / none | ordinary_task / none / none |
| H13 | teach me the compile pipeline: preprocess, compile, assemble, link |  | lesson / static / still | lesson / **none** / **explain** | lesson / **none** / **explain** |
| H14 | animate how quicksort partitions an array |  | lesson / motion / video | lesson / motion / **narrated-video** | lesson / motion / video |
| H15 | explain big-O of binary search with a graph |  | lesson / static / still | lesson / **none** / **explain** | lesson / static / still |
| H16 | build me an explorer for two's complement |  | lesson / interactive / explorer | lesson / interactive / explorer | **ordinary_task** / **none** / **none** |
| H17 | expand this: why is i++ + ++i undefined? layer by layer |  | lesson / none / qa-expander | lesson / none / qa-expander | lesson / none / **explain** |
| H18 | continue my C course from last time |  | course / none / resume | **lesson** / none / **explain** | **ordinary_task** / none / **none** |
| H19 | teach me pointers | C | lesson / static / prediction-first | lesson / **none** / prediction-first | lesson / **none** / **explain** |
| H20 | teach me how printf %c works | C | lesson / static / prediction-first | lesson / **none** / prediction-first | lesson / **none** / **explain** |
| H21 | make a narrated video on struct padding | C | lesson / motion / narrated-video | lesson / motion / **prediction-first** | **ordinary_task** / **none** / **none** |
| H22 | explain it again simpler |  | quick / none / re-explain | **lesson** / none / **explain** | **lesson** / none / **explain** |
| H23 | turn this lesson into Anki cards |  | lesson / none / flashcards | lesson / none / flashcards | lesson / none / **explain** |
| H24 | make a 3Blue1Brown style video on the master theorem |  | lesson / motion / narrated-video | lesson / motion / narrated-video | **ordinary_task** / **none** / **none** |
| H25 | show memory layout of struct {char c; int i;} |  | quick / static / still | **lesson** / **none** / **explain** | **lesson** / static / still |
| H26 | I want an interactive video on linked list insertion with chapters |  | lesson / motion / interactive-video | lesson / motion / interactive-video | lesson / **none** / **explain** |
| H27 | teach me GATE-style pointer arithmetic with timed practice | C | lesson / none / exam-drill | lesson / none / exam-drill | lesson / none / **explain** |
| H28 | explain what a segfault is, no files please |  | lesson / static / save-nothing | lesson / **none** / **explain** | lesson / **none** / **explain** |
| H29 | write the unit tests for this function |  | ordinary_task / none / none | ordinary_task / none / none | ordinary_task / none / none |
| H30 | create a visual explainer of how a hash table resolves collisions |  | lesson / static / still | lesson / static / still | **ordinary_task** / **none** / **none** |
| H31 | voice over this explainer in a British accent |  | lesson / motion / narrated-video | lesson / motion / narrated-video | lesson / **none** / **explain** |
| H32 | make me a cheat sheet image for C format specifiers |  | quick / static / still | **lesson** / static / still | **ordinary_task** / **none** / **none** |

**What the v2.1 misses have in common.**
- **No still from implicit visual words.** The v2.1 router never infers a still from "show the bit pattern", "show memory layout", "with a graph", "pipeline", or a predict-first workspace. That covers H04, H13, H15, H19, H20, H25 and H28. It gives a still only when one is named or drawn.
- **No course or resume mode** (H18), and no re-explain label (H22).
- **Mode labels win over media.** H21's predict-first contract wins the medium label.
- **"Animate" is narrated by default** (H14).
- H04, H18 and H25 came back as `confidence: low`. Every other route was `high`.

## 3. Protected checks (FREEZE)

| Check | Evidence | Result |
|---|---|---|
| (a) One skill entry per host | `test_hosts::test_one_entry_per_host` passed for claude-code, codex, hermes and opencode, both side by side and after the flip. The planted nested copy is not seen as a second entry. Codex and Hermes real-host discovery came back clean. `test_install_rollback` passed on all 4 hosts with v2's reads restored. `test_install_and_rollback_cli_throwaway_home` passed. `test_packaging::test_tree_limits` passed: 209 files, 2.84 MB, tree sha `c90a758f…`. | **holds** |
| (b) Tamper fails verification | `test_mutation::test_still_value_mutations`: 44/44 mutations caught, 4 clean controls pass. Manual tamper on a copy of one-byte-four-views (`.state/final-verify-logs/tamper/`): see below. | **holds** |
| (c) No network at teach time | `test_render_isolation::test_canaries_fail_render_succeeds`: DNS, HTTPS and child-connect blocked, the render ran offline, the frame reads "offline". `test_visual::test_no_network`: the canary request was blocked and failed the gate. `test_security::test_capture_denies_network`: connect DENIED. Routing and the protocol need no network. | **holds** |
| (d) v2's 22 JS tests and passing Python tests | See below. | **holds** (6 JS removals and the Python replacements/removals are justified in writing, as FREEZE allows) |

The manual tamper in (b):
- The built `one-byte-four-views-wide-dark.svg` passes clean, with 21 values checked and 0 problems.
- I changed `0x4050800000000000` to `…0001` in the SVG. The check caught it: `f.dbits shown 0x4050800000000001, captured and expected 0x4050800000000000`.
- I set fact `f.vm1.u` to `4294967294` in the lesson model. `check_expectations` raised `ExpectationMismatch`, expected `4294967295`.

Details for (d):
- **Baseline, rerun now in a copy of the v2 install** (`.state/final-verify-logs/v2copy`, so the protected bytes stay untouched):
  - JS: 22/22 passed on Node 22.23.3.
  - Python: discovery from `tests/` ran 234 tests, with 5 errors (whole-module import or setup errors in build_package, current_evidence, skillopt_adapter, validator_cli and one loader error) and 1 skip. That is consistent with Report 04's "not passing in an install" modules.
- **JS mapping:** the 16 ported names match `tests/test_render.mjs` exactly. The 6 absent ones are the 5 Flint adapter tests and the bulk-render snapshot test, each with a reason in PROTECTED-MAP. `test_render::test_svg_math_video`: 20/20 on Node 22 and 20/20 on Node 24.
- **Python mapping:**
  - All 12 ported modules have the same test method names as v2, 106 in all. The only absences are the 4 routing tests that PROTECTED-MAP lists as replaced by `test_route.py`.
  - An AST comparison of every assert line in each ported method against v2 finds **0 differences**, so no assertion was weakened.
  - `test_state::test_ported_v2_suite` ran 106 tests and passed.
- **Changed protected behaviour:** hard-linked learner state (D22.3) is documented in PROTECTED-MAP with its tests and residual risk. It is still **pending Prax's approval**. Its new tests passed: cross-learner refused, backup link reads with a warning, writes never go through an alias, and legacy migration.

## 4. Numeric claims audit (all four lessons)

**What I covered:**
- every claim's text and justification;
- the misconception corrections;
- the trace labels and storyboard narration;
- all line-number references, which I checked against the program sources.

The misconception *statements* are false on purpose, so I skipped them.

**How I checked.** Python `struct` and `fractions` for binary64. A C program compiled with the real clang, `/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang` (Apple clang 21.0.0), with the Xcode SDK and DEVELOPER_DIR pinned. That is the developer dir recorded in `.state/setup-inventory.json`. I also used gcc-16 with the real toolchain on PATH, and called no `/usr/bin` shim. Source: `.state/final-verify-logs/audit/audit.c`.

**Result: no false numeric or representability statement.** What I checked, by lesson:

- **one-byte-four-views:**
  - sizeof(int) is 4, CHAR_BIT is 8, UINT_MAX is 4294967295, UCHAR_MAX is 255.
  - 66 → 01000010 / 0x42; 200 → 11001000 / 0xC8; −1 → 11111111 / 0xFF; 321 → 01000001 / 0x41, since 321 = 256 + 65.
  - %u of −1 is 4294967295, which is −1 + 2^32.
  - %c bytes are 200, 255 (−1 + 256) and 65 (321 − 256). ASCII 65 is A and 66 is B, and ASCII stops at 127.
  - (double)66 has bits 0x4050800000000000: 66 = 1.03125 × 2^6, biased exponent 1029 = 0x405, fraction 2^−5.
  - 66, 200, −1 and 321 are all exact in double, so %f prints 66.000000, 200.000000, −1.000000 and 321.000000.
  - Every line reference is right: views.c 5, 13 and 15–18; ub.c 5; output lines 3–6.
- **factorial-stack:**
  - The results are 1!, 2!, 3!, 4! and 5! = 1, 2, 6, 24 and 120.
  - The entry order is 3, 2, 1 and the result order is 1, 2, 3.
  - Lines 5–9 and 13–14 are right.
- **neuron:**
  - 0.8, 0.4, 0.2, 0.6 and 1.2 have no exact binary64 form; 1.5 does.
  - 0.8 × 1.5 = 1.2000000000000002, the least double above 1.2, and `%+g` prints +1.2.
  - 0.4 × −1 is exactly −(double 0.4).
  - z = 0.6000000000000001, the least double above 0.6. `z == 0.6` is false and `%g` prints 0.6.
  - k1: z = −0.19999999999999984, which prints −0.2, and fmax(0, z) = 0 (+0).
  - k2: z prints 1.7. k3: z prints −0.6 and a = 0.
  - Lines 5–15 are right.
- **switch-fallthrough:**
  - Lines 4, 5, 8–10, 12 and 16 in fallthrough.c are right, and so are lines 8, 9, 11, 14, 17 and 18 in with_break.c.
  - "gcc-16 -Wextra warns twice for fallthrough.c, nothing for with_break.c" is true when compiled with `-c`, as ptk compiles. Both warnings are at fallthrough.c:7 and :9.
  - Under `-fsyntax-only`, gcc reports nothing, because that warning comes from a later pass. This doesn't make the claim wrong.

**One weak citation, not a false statement.** one-byte's c.cast and c.dbits say double is "IEC 60559 binary64 (Annex F)". The format part is true by measurement: DBL_MANT_DIG is 53, FLT_RADIX is 2, and the bit pattern matches. But neither Apple clang nor gcc-16 defines `__STDC_IEC_559__` on this platform, so the implementation does not itself claim Annex F conformance. Citing Annex F as the authority is weaker than citing the measured format. The neuron claims say "binary64" with the same Annex F citation.

## Files

- Report: `v2.1/reviews/final-verification.md` (this file).
- Logs: `v2.1/.state/final-verify-logs/`:
  - `selftest*.{out,err}`, `holdout_score.py`, `holdout-results.json`;
  - `audit/`, `tamper/`, `transcripts/`;
  - `v2-js.txt`, `v2-py-discover.txt`.
- Selftest reports: `v2.1/.state/selftest/auto-20261018T152845Z-2756-0140211d.json` (clean run A), plus the run B report named in `selftest2.out`.
