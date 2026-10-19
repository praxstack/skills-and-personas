# Round 17: gates audit of caf32de..4cda9c1

Auditor: adversarial review of every checking-code change made while lessons were being made to pass.
Scope: the `integ:` and `wp9:` commits. I did not read `holdout/` or `plan/proposed/`.
Method: before/after diffs, then a counterexample per change. Two probes ran in a throwaway worktree under `.state/audit` with its own `PTK_STATE`. Both were removed afterwards. No video was rebuilt.

## Verdicts at a glance

| Change | Verdict | Severity |
| --- | --- | --- |
| `--only` merges the previous report | weakening, must redesign | P1 |
| D21.1 canary-only default | weakening as shipped, needs Prax approval and a calibration link | P1 |
| Hard-linked learner-state files accepted | justified need, too broad, needs Prax approval and a narrower check | P2 |
| IVE explore check for lessons without live editing | weakening through a silent fallback, redesign | P2 |
| Outgoing panel layer may overlap | weakening, the exemption is wider than the cross-fade | P2 |
| Frame probe: paths as sets, panel state | justified, needs an ambiguity guard | P3 |
| IVE caption check on the caption band | justified, needs a test | P3 |
| Claims collection: wrapped SVG lines joined, wrong-belief label | justified, needs tests | P3 |
| Sync: stretched whisper tokens | justified, tested | P3 |
| Canary generator: no value swap that still says the value | justified, tested | none |
| test_modes_live disagreement | TEACHING.md is right, protocol.py is wrong | P2 |

---

## P1-1. `--only` carries stale `passed` gates over changed output on disk

Confidence: high. Reproduced.

File: `package/prax-teach/ptk/build.py:130-153` (merge_previous) and `:228` (artifact list).

Before (caf32de): a `--only qa` build reported `media: ["qa"]` and only qa gates. Other media on disk were not claimed.

After (812389c):

```python
if prev and prev.get("status") in CARRY_FROM and prev.get("lesson_sha256") \
        and prev.get("lesson_sha256") == rep.get("lesson_sha256"):
    keep = [m for m in SUPPORTED if m in prev.get("media", []) and m not in rebuilt and m in on_disk]
...
out["gates"] = list(rep["gates"]) + [g for g in prev["gates"] if g.get("medium") in keep] if keep else list(rep["gates"])
```

and later, unchanged:

```python
rep["artifacts"] = _artifact_list(build_dir)
```

The carry condition checks only that `lesson.json` has the same hash and that the folder is not empty. It never checks that the carried medium's files still have the hashes the previous report recorded. Then `_artifact_list` re-hashes whatever is on disk now. So `claims.artifacts-unchanged` compares against the tampered bytes and passes.

Counterexample, run:
1. Copied `lessons/switch-fallthrough` (status `verified`, canary mode) into the worktree.
2. In both light SVGs, set the fill of the output value `three` (`data-fact="f.p1.l2"`) to `#fbfaf6`, the page colour. The value is now invisible.
3. `ptk build lessons/sf --only qa`.

Result: exit 4, `claims-pending`, `merged_from_previous: [still, video, ive, explorer, cards]`, `visual.still.contrast: passed`. The report lists `still/switch-fallthrough-wide-light.svg` with sha256 `f0705dea...`, which is the tampered file (original `06999aaf...`). The claims job texts are unchanged, so the reviewer accepts again and the lesson goes to `verified` with an invisible output value.

A first attempt that changed the value text from `three` to `four` was caught by `claims.mapping` (medium `all`, recomputed). So value text tampering is caught. Anything a per-medium gate checks and the text mapping does not (contrast, layout, OCR, fonts, PNG/SVG drift, video frames) is carried blind.

Same hole, second route: gates are carried across a change of ptk itself. A still built before WP9's new still checks, then `--only qa` after the upgrade, carries old still gates that never ran the new checks. `rep["tools"]` is recorded but not compared.

Fix:
- Carry a medium only if every previous artifact under it is still on disk with the same sha256, and no new file appeared. Otherwise list it in `uncovered_media`.
- Also require the same ptk package version (or a hash of `ptk/verify` and `ptk/project`) and the same tool versions.
- Build the artifact list for carried media from the previous report, not from disk, so `claims.artifacts-unchanged` keeps its meaning.
- Add a test: tamper a carried SVG, run `--only qa`, assert the still is uncovered (or failed), not passed.

## P1-2. D21.1 canary-only default is an unapproved governing change and links to no calibration

Confidence: high on the governance facts, medium on the risk size.

Files: `package/prax-teach/ptk/verify/claims.py:599-640` (plan_variants, canary_order, write_jobs), `:806`, `:813-835` (_canary_gate); `spec/SPEC.md` v1.2 changelog and AC-7.1, AC-7.5.

Before: every build wrote the lesson job plus up to 12 mutations, each with a clean control, and `claims.sensitivity` held the E22 thresholds (90% claims, 100% values, 95% controls).

After:

```python
numbered = list(enumerate(muts, 1))
return out + [("mutation", i, m) for i, m in canary_order(lesson, numbered)]
...
if not calibrate and role == "mutation" and any(m["role"] == "mutation" for m in priv["jobs"].values()):
    break  # canary mode: one planted error is enough
```

Problems:
1. Governance. The spec itself says: "This is a governing change made by the orchestrator, not yet approved by Prax (FREEZE stop rule)." FREEZE says "A run may change the candidate or its spec/evaluator, never both. A spec change needs Prax's approval." This range changed both.
2. Nothing makes a `verified` build depend on a calibration run. `--calibrate` is a doc instruction ("run on a rubric or reviewer-model change"). There is no ledger of the rubric sha and reviewer model last calibrated, and no gate that fails when they differ.
3. One sample. A reviewer that catches half of all planted errors passes the canary half the time. The old suite would have failed it on rates. Controls are gone, so the false-reject rate is unmeasured in normal builds.
4. "Awake for THIS lesson" is not guaranteed. The lesson job and the canary job run in different subagents. A catch on the canary says nothing about the lesson job's subagent. Reviews also persist in `claims-review/` keyed by manifest hash, so a canary review from an earlier build with identical inputs answers the new build. That is fine for content but it means no reviewer had to be awake for this build.
5. The docstring says "no fixed rule says which claim is planted". That is not true: the pick is `sha256(lesson.sha256() + ":canary")`, computable by any host agent holding the package. With two jobs, a diff against the lesson also shows which one is planted. The old suite had the same exposure, but with 25 jobs the cost of gaming it was higher.

Counterexample: a reviewer setup with 50% claim sensitivity, run on switch-fallthrough. Canary mode reaches `verified` with probability 0.5. Calibration mode fails `claims.sensitivity` (50% < 90%). No probe was run; this needs real reviewer subagents.

Fix: keep canary mode only after Prax approves v1.2. Add a calibration record in `$PTK_STATE` (rubric sha, reviewer model id, date, rates). Make `claims.canary` fail, or the status at most `degraded`, when there is no passing calibration for the current rubric sha. Consider two canaries (one value, one claim) chosen with a per-build nonce kept in `claims-private`, not from the lesson hash.

## P2-1. Hard-link acceptance opens a cross-learner read and export

Confidence: high. The false positive is real; the leak is by design and tested.

File: `package/prax-teach/ptk/state/io.py:44-66` (link_count_ok), used in `secure_workspace`, `read_bytes`, the workspace lock, `continuity.py`, `state.py`.

Before: `if required_stat.st_nlink != 1: raise SafetyError(...)`.

After: accepted when `st_nlink > 1`, regular file, owned by the effective user, with a `HardlinkAccepted` warning.

The false positive is real. I created a file under `v2.1/.state/audit`: `st_nlink` was 1, then 2 nine seconds later, same inode.

The cost: `tests/ported_v2/test_state_security.py` used to assert exit 5 and no export. It now asserts only that a warning is printed, and the export to `linked-export.zip` succeeds. So learner B's `sessions.jsonl`, hard-linked into learner A's workspace, is read by `show` and packed into A's export. Writes go by rename, so B's file is not modified. But the read and export cross the learner boundary. PROTECTED-MAP says this "is not yet approved by Prax".

Fix: accept an extra link only if the inode is one the engine wrote (the inode ledger PROTECTED-MAP already proposes), or at least refuse when the `(st_dev, st_ino)` matches a state file in any other registered learner workspace. Get Prax's approval either way.

## P2-2. IVE explore check silently falls back for a broken switch lesson

Confidence: high. Unit probe run.

File: `package/prax-teach/ptk/verify/visual.py:612-618`; `ptk/project/ive.py:143-151`.

Before: `"edit_marked_yours": e2.get("origin") == "yours" and ...`

After:

```python
live_edit = ive_proj.live_model(lesson) is not None
"edit_marked_yours": e2.get("origin") == ("yours" if live_edit else "step") and ...
```

`live_model` catches `ModelReferenceError` and returns None. So the gate picks "no live editing" for any lesson whose switch model fails, not only for panel lessons.

Counterexample, run: load switch-fallthrough, drop `figure.compare.program`. `live_model` returns None, `explorer.switch_model` raises `ModelReferenceError`, `figure.panel` is absent. Built with media still, video, ive (no explorer), the IVE ships without live editing and `ive.explore-return` expects and accepts a step back. Before, the same lesson failed.

Also, AC-6.6 says "In EXPLORE, live edits are visibly separate from the recorded film". For three of four exemplars there are no live edits at all, and the check named `edit_marked_yours` passes on a step through the film. That is a scope decision the spec has not made.

Fix: decide the mode from the lesson's declared shape (`figure.panel` present means step mode), and fail when a non-panel lesson has no live model. Rename the check per mode and record `live_edit` in `measured`. Ask Prax whether panel lessons need a live edit to meet AC-6.6.

## P2-3. The overlap exemption covers the whole outgoing layer, at all times

Confidence: medium-high. Static analysis of HyperFrames' layout audit; no render.

Files: `package/prax-teach/ptk/project/video.py:618`, `:670-672`; `ptk/verify/frames.py:52-58`.

Before (WP9 earlier): `class="mlayer mbefore"`, opacity fades.
After: `class="mlayer mbefore" data-layout-allow-overlap=""`, autoAlpha fades.

HyperFrames' `hasAllowOverlapFlag` walks up the ancestors (`layout-audit.browser.js:668-671`). With the flag on the layer's `<svg>`, every text in the outgoing panel is exempt from `content_overlap` against anything (code card, notes, captions) while it is visible. HyperFrames' own guide says to mark "the specific layering participant, never a scene/root wrapper".

Counterexample (not run): remove or break the `.mbefore` fade-out tween. The old layer stays fully shown under the new one for the whole scene. Layout: exempt. Frame probe: `fullL` holds both layers and `panel` reads the last one, so the state matches and `moving` is false. Before the flag, HyperFrames reported the overlap as a warning, which `hf_check_clean` treats as a failure.

Fix: in `PROBE_JS`, flag a frame where more than one `.mlayer` has `eop >= 0.99` (outside the fade window that is a defect). Better still, put the flag only on the text that must cross the incoming layer, or drop it and let the probe own the cross-fade check.

## P2-4. test_modes_live: protocol.py contradicts TEACHING.md

Confidence: high. I ran `protocol.check_transcript` on the stored transcripts in `.state/agent-jobs/protocol{,-run1}/{quiz,exam-drill}`.

AC-1.8: "Modes quiz, exam-drill (timed GATE MCQ/NAT) and qa-expand shall each have a protocol in references/TEACHING.md and one transcript test each." So TEACHING.md is the protocol of record. protocol.py is the oracle that has to encode it. AC-1.6's one-hint rule is written "When predict-first runs".

Where they disagree (`ptk/protocol.py:155-166` feedback_unit, `:168-182` _grade, `:289-305` check_exam_drill):
- TEACHING quiz step 2 puts "the next question in the same turn". The checker splits by sentence and flags the question's lead-in ("Question 2 of 3: now add one line...") as a second explanation.
- TEACHING quiz step 4 needs the score, the weakest item, one next action and an offer of another round. The checker flags each as a second correction.
- TEACHING exam step 3 needs marks earned and time against the limit. The checker flags "+1 mark, 50 s of your 90." Step 4 says reveal the key after the attempt. The checker flags "The answer is C (two, done)."
- `_grade` compares the attempt to `str(answer_key)`. For an exam key `{"option": "B", ...}`, the attempt "B" never matches. For the quiz key "two\ndone\n", "only two and done" does not match.
- `marks_awarded` must be int or float, so a GATE fraction like "-1/3" fails.

Verdict: TEACHING.md is right. Fix protocol.py: make the one-item rule mode-aware (allow the mode's required marks, time, score, weakest item, next action, key reveal and the whole next-question block), grade option keys by letter and output keys by line sequence, and accept fractional marks. Do not weaken TEACHING.md to fit the checker. After the fix, rerun the live test. The transcripts may still have real faults (run1 omitted the `feedback` field).

## P3-1. Frame probe compares paths as sets

Confidence: high. Justified, needs a guard.

File: `ptk/verify/frames.py:166`. Before: `sorted(s.get("path", [])) == sorted(probe["path"])`. After: `sorted(set(...)) == sorted(set(...))` plus `probe.get("panel", "none") in ("none", st["id"])`.

Justified: `video.py:410` now draws one dot per line (`dict.fromkeys(run)`), so a frame cannot show how often a line was passed. The multiset compare could never match factorial's six states with repeated lines.

Gap: two trace states with the same program, line, output and path set become indistinguishable, and `match_state` returns the first. None collide in the four lessons today (checked). For panel lessons, `panel` reads `"none"` when no `.mlayer` exists, so a render that lost its panel still matches.

Fix: at validate time, fail when two states collide under set semantics without a panel to separate them. In `match_state`, treat `panel == "none"` as unknown for a lesson with `figure.panel`.

## P3-2. IVE caption check on the caption band

Confidence: medium. Justified, needs a test.

File: `ptk/verify/visual.py:485-490`, `:598-600`. Before: native track mode `["showing","hidden","showing"]`. After: `band.dataset.on` toggles `["true","false","true"]`, track `hidden`, and band text equals cue 0 text.

The new check reads a data attribute, not what is drawn. A CSS slip that hides `.capband` while `data-on="true"` passes. Only one cue is checked. `tests/test_ive.mjs` does not check the text at all. Fix: assert the band's computed visibility and bounding box when on, and the text at a second cue.

## P3-3. Claims collection: wrapped SVG lines joined; wrong-belief label

Confidence: medium-high. Justified, needs tests.

File: `ptk/verify/claims.py:76-117` (`_Collector`), `:126-136`.

Joining is right: before, each wrapped line of a mapped inline-SVG sentence was its own run and failed as a partial claim. Inner tspans now take the outer text's mapping, but the outer check (whole claim, label regex `fullmatch`, chrome regex) stays strict, so I found no way to slip prose through.

The wrong-belief annotation keys on `data-in` identity with a `data-chrome="wrong_belief"` element. `still-measure.js` checks that every `data-in` text sits inside its box, and the contrast gate covers visibility, so the annotation is grounded. No test covers either change. Add one for the tspan join and one asserting the reviewer sees `"still (labelled as a wrong belief)"` only when the label is in the same box.

## P3-4. Sync: stretched whisper tokens

Confidence: medium-high. Justified.

File: `ptk/verify/media.py:154-169`. New branch: when the last token is longer than 0.75 s, offset is the last silence start inside the token.

This is stricter in the case that matters: a caption that hangs over a pause. Old rule: anchor near the stretched end, no silence in window, default `w1.end`, so the hanging caption passed. New rule: offset is the real silence start, so it fails by about the pause length. `tests/test_media.py::test_refine_ignores_stretched_last_token` covers four real cases.

Residual: `max` picks a later silence if whisper dropped words inside the stretch. The WER limit (0.10) makes that unlikely to pass. Add a test for the hanging-caption direction so the strictness is pinned.

## Canary generator (no finding)

File: `ptk/verify/mutation_claims.py:62-69`. Signed numbers are now nudged, and a pool swap that still contains the value is refused. A generator bug can only cause a false failure (the canary is "accepted"), never a false pass, because `caught()` needs an overall reject naming the planted claim or a changed text. Tested by `test_value_swap_plants_a_real_error`.

## Process note

Both P1 items and P2-1 came from making the exemplars pass or from orchestrator decisions in the integration pass. The spec bump (v1.2) and the protected-behaviour change are both marked "not yet approved by Prax". Per FREEZE, they should be parked for approval, not shipped as the accepted baseline.
