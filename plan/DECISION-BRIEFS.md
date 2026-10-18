# Decision briefs (2026-10-18)

Each brief has the evidence, the exact change, and what Prax decides. The full evidence is in `EVIDENCE-HARDLINKS.md`, `EVIDENCE-PREDICT-FIRST.md` and `EVIDENCE-CHECKS-AND-DROPPED-CLAIMS.md`.

## 1. Acceptance rules

See `ACCEPTANCE-COMPARISON.md`: eight itemized decisions, each with its reason and consequence. Canary mode is a separate decision.

## 2. Canary mode

Provisional. It is not proposed for adoption.

- All four lessons were `canary-verified`, and all four failed the full suite.
- The best status canary mode can give is `canary-verified`.

## 3. Learner state and hard links

**Cause (proven; my earlier claim "macOS backups" was wrong).**
- Google Drive for desktop backs up `~/Developer` and `~/Study`.
- About 0.1 to 1.5 s after a file is created, Drive hard-links it into a hidden `.tmp.driveupload` folder until the upload finishes.
- The evidence:
  - the probe files' inodes were found in that folder with identical content;
  - Drive's log says "RegisterUpload Creating hard link to …";
  - Time Machine was idle, with no destination, while the links appeared;
  - folders Drive doesn't back up (home root, /tmp, ~/Documents, ~/Desktop) stay at 1 link.

**Exact behaviour change:**

| Version | Rule |
|---|---|
| v2 | Refuses any state file, journal or lock with st_nlink ≠ 1 (exit 5). |
| b74277b (integration) | Accepts any multi-link regular file the user owns, with a warning. This let learner B's state be read as A's. Superseded. |
| e0e1d37 (current, D22.3) | The state folder and every file it writes carry a learner id in xattr `user.praxteach.learner`. A multi-link file is read only if it carries this workspace's id. Writes atomic-replace onto a fresh inode. |

- **Newly accepted:** the learner's own file with the right id and an extra link.
- **Newly refused:** a single-link file tagged with another workspace's id.

**Privacy and consent findings:**
- **Delete does not fully delete.** ptk's full delete reported `all_state_deleted`, but `learner.json` (learner id and goal) remained in `.tmp.driveupload`, queued for upload to Google.
- **Existing exposure.** There are already 4,040 staged copies (about 220 MB) under `~/Developer`, including the v2.1 test fixtures.
- **Nobody is told.** Export and inspect can't see these copies, and the consent text doesn't mention Google.
- **What the xattr binding covers.** It stops cross-learner hard-link aliasing, but not copies made without xattrs. A restore without xattrs locks the learner out until `rebind --confirm`.
- **Consent rules.** "No write before consent" is unchanged. But read-only commands now write xattrs even after consent is withdrawn, which is a regression to fix.
- **"Safely" was unsupported.** My earlier word "safely" is withdrawn.

**Decisions for Prax:**
1. Allow learner state in Drive-backed folders at all? Recommended: refuse by default, with an explicit opt-in.
2. Approve D22.3 with the fixes in REPAIR-PLAN A6?
3. Should read-only commands ever write xattrs after consent is withdrawn? Recommended: no.
4. What to do about learner and test data already staged in Drive. This is Prax's Drive; nothing will be touched without his say.

## 4. The teaching rule (predict-first)

**Which rule drifted, and where.** Every step after the first was mine, in this session:
1. **30 Sep, commit `4890911` in the C repo.** An OpenCode agent (kai-mori, gpt-6.1-sol) wrote AGENTS.md "Ask one bounded prediction… Wait for the attempt" and NOTES.md "Start the first learning session with one short C output prediction", committed under Prax's git name. Prax had only asked whether it would use Socratic methods.
2. **16 Oct.** v2 went explanation-first: "Deliver the whole explanation without prediction, quiz or teach-back barriers." This matches Prax.
3. **18 Oct, 02:29.** Prax turned down a prediction question: "answer now, build best visualiser based intuition building full course."
4. **18 Oct, about 03:26: the drift.** My review finding T1 treated workspace instruction files as "an explicit style selection" that "overrides the explanation-first default". The agent-written note became "Prax's contract".
5. **Same day.** I froze it as FREEZE criterion 5 (`e29321b`), then carried it into the CEO plan, spec AC-1.3 and AC-1.6, D20.7 (which made "answer now" an exception instead of the default), TEACHING.md, the router and the checker.
6. **The hidden test labels also encode the drift.** Some workspace rows are labelled "prediction-first".

**Is the checker conflict downstream?** Yes, for whether it blocks acceptance. Once prediction is opt-in, predict-first stops being the default path. The wording clash (naming the misconception in its own sentence) still needs a small checker fix.

**Corrected rule (Prax's preference):**
- A complete visual explanation first, for every teaching request, including in the C workspace.
- Optional practice afterwards.
- Prediction barriers only in explicitly requested practice modes: quiz, exam-drill, Socratic, "let me predict".
- "Answer now" ends questioning.
- Workspace files never switch the default to prediction.

**What changes:**
- **Evaluator** (needs Prax): FREEZE criterion 5, the holdout labels, and ACCEPTANCE-PROPOSAL item 5.
- **Implementation** (REPAIR-PLAN A4): spec AC-1.3 and AC-1.6, TEACHING.md, route rules, workspace.py, SKILL.md and the tests.
- **The C workspace's AGENTS.md and NOTES.md** carry the drifted wording. That repo is protected, so editing it is Prax's call.

## 5. Check changes made while building (each its own item; no blanket approval)

| # | Change (commits) | Before → after | Classification at HEAD | Pinned by |
|---|---|---|---|---|
| 1 | Sync, stretched whisper token (`6bb548d`, `790eec8`, `992fa05`; fixed `8ca70da`) | The old gate measured the end of a stretched token wrongly (false fail). The WP9 version could falsely pass when speech resumed (Codex: 2.0 vs 4.05 s). Now the chosen silence must contain the token end, or the later boundary stands. | Bug correction (after the r17 fix) | `test_refine_stretch_needs_a_silence_holding_the_token_end` |
| 2 | Canary generator (`c7bb1ab`) | A value swap could "plant" an unchanged value (no error), which only ever caused false failures. Now it always plants a real error. | Bug correction | `test_value_swap_plants_a_real_error` |
| 3 | Claims text collector (`ee7b25f`, `790eec8`; fixed `8295590`) | Wrapped SVG lines were split mid-sentence (false unmapped). The wrong-belief label was trusted from metadata. Now lines are joined, and the label must be drawn text inside the misconception box. | Bug correction (after the r17 fix) | collector join and label tests |
| 4 | Frame probe, paths as sets plus panel state (`4b27a8f`, `790eec8`; guards `c5f3c65`) | Dot-based visualisations failed on ordered path comparison. Now set comparison, plus ambiguity and lost-panel guards. | Bug correction; the panel part is stricter | frame-state tests |
| 5 | IVE caption check (`4b27a8f`; fixed `c955aff`) | It had trusted a `data-on` flag. Now it measures drawn caption text after each toggle. | Bug correction (after the r17 fix) | caption control tests |
| 6 | IVE explore check (`4b27a8f`; partly fixed `baccb0f`) | The silent pass for broken lessons is removed. But panel lessons still pass AC-6.6 with step-through and no live edit, and the spec text was never changed. | **Changed acceptance requirement: needs Prax** | explore-mode test |
| 7 | Panel overlap during cross-fade (`790eec8`; limited `c5f3c65`) | It had exempted the whole outgoing layer. Now only a measured fade ≤ 1 s. | Bug correction (after the r17 fix) | overlap probe |
| 8 | Axis ticks, unlisted (`d56e4e2`; fixed in r17) | A linear fit among labels let consistently wrong labels pass. It still needs binding to an independently computed data scale. | Stricter, but **incomplete** | REPAIR-PLAN A5 |
| 9 | Morph output deadline, unlisted (`270af89`; fixed `6786236`) | The deadline came from the renderer's own planner. Now old output must stay readable until new output is visibly present. | Stricter (after the r17 fix) | `test_morph_keeps_frame_steady` |
| 10 | Factorial chip overlap exemption (round 18) | Exempts chip overlap. Nobody audited it, and it has no probe. | **Unaudited: needs review** | none yet (REPAIR-PLAN A5) |

## 6. Dropped claims (each dropped after three correct rejections)

| Claim | Why dropped | What the lesson lost | Correct wording to restore |
|---|---|---|---|
| switch `c.warn` | It said gcc warns about the fall-through. gcc-16 gives no warning when a case falls into a case that only breaks (verified by compiling). | The "how to catch this bug" advice. The mechanism is intact. | "gcc-16 `-Wimplicit-fallthrough` (part of `-Wextra`) warns when a case with statements falls into the next case; here case 2 falls into case 3, which has statements, so it warns." This must be checked against a real compile before use. |
| neuron `c.kformula` | The slider formula sat on static cards, failed for NaN inputs, and stated b's range wrong. | The explorer's stated formula. Variant cards p3 and p4 have no explanation. A small gap. | The formula bounded to the slider's actual finite range, on live cards only. |
| one-byte `c.recap` | It implied the value changes. The value 66 stays the same; the type and the bits change. | The recap scene. Nothing now says `%u` keeps a's bits. A small gap. | "The value 66 stays the same in every view; `(double)a` changes the type and the bits, `%u` reads the same bits as unsigned." |

All three are restored in REPAIR-PLAN A2.

## 7. The live session and installing

- **The live session:** usability feedback only. It never replaces correctness checks. It runs explanation-first, once the corrected rule is in.
- **Installing:** deferred, per Prax. The `prax-teach-v2` link stays on v2.
