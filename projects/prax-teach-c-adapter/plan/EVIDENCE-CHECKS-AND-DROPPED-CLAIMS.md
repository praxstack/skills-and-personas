# Evidence: the WP9 check changes and the dropped claims

Written 2026-10-18 from a read-only pass over the git history at HEAD `2e0a515`. I did not read `holdout/` or `plan/proposed/`.

How I got the facts:
- Code: `git show` on each commit, before and after. Every quote below is from git.
- Behaviour: I ran `refine()` from five versions of `media.py` on the same inputs. I also ran each pinned test with `ptk selftest -k <name>`. Every test I name passed. Side effect: selftest writes its reports to `.state/selftest/`.
- Reviewer verdicts: each lesson's `build/claims-review/` keeps only the latest round. So the rejections of the dropped claims survive only in this session's subagent transcripts, under `~/.claude/projects/-Users-prax-Study-Actual-Study-Gate2027-01-Interview-Preperation-01-C/ff394d66-ca3e-47d2-830d-06ce3eb04ec0/subagents/`. I cite them by agent file. Transcript times are UTC, commit times are IST (UTC+5:30), and I give both in IST below.
- gcc: I compiled a small test file with gcc-16 16.2.0 to check one reviewer's reason.

Counting: the WP9 self-report in `PROGRESS.md` (at `4cda9c1`) lists **seven** evaluator changes, not five or six. The IVE caption check and the IVE explore check are separate items there, so I report them as 5a and 5b.

## Summary

| # | Change | WP9 commit(s) | As shipped in WP9 | Round 17 | My final classification at HEAD |
|---|---|---|---|---|---|
| 1 | Sync: whisper stretches a word over a pause | `6bb548d`, `790eec8`, `992fa05` | changed acceptance requirement (had a false pass) | `8ca70da` closed the hole | **bug correction** |
| 2 | Canary generator: value swaps plant a real error | `c7bb1ab` | bug correction | no change needed | **bug correction** |
| 3 | Claims collector: wrapped SVG lines joined; wrong-belief callout reported as labelled | `ee7b25f`, `790eec8` | join: bug correction. Label: changed acceptance requirement (trusted metadata) | `8295590` bound the label to the drawing | **bug correction** |
| 4 | Frame probe: paths as sets; reads the panel's state | `4b27a8f`, `790eec8` | bug correction with two holes | `c5f3c65` closed both | **bug correction** (panel part is stricter) |
| 5a | IVE caption check on the caption band | `4b27a8f` | changed acceptance requirement (trusted a flag) | `c955aff` measures drawn text | **bug correction** |
| 5b | IVE explore check for lessons without live editing | `4b27a8f` | changed acceptance requirement (silent fallback) | `baccb0f` removed the fallback | **changed acceptance requirement** (still open for Prax) |
| 6 | Outgoing panel layer may overlap during its cross-fade | `790eec8` | changed acceptance requirement (exemption wider than the fade) | `c5f3c65` added a frame probe | **bug correction**, now bounded |

Three more WP9-era check changes were not on the self-reported list. They are in "Also found" at the end of Part A.

| Dropped claim | Lesson | Commit | Why dropped | Lesson weaker? |
|---|---|---|---|---|
| `c.warn` (gcc's fallthrough warning) | switch-fallthrough | `1c6a0cf` | three rejections, each for a real exception to "gcc warns" | Yes. The mechanism is intact, but the lesson no longer tells the learner how to catch the bug. |
| `c.kformula` (the explorer's z formula) | neuron | `48da9d7` | three rejections: slider wording on static cards, NaN, "the program" has fixed w2 and b | Slightly. The explorer and two variant cards lost their only explanation. |
| `c.recap` | one-byte-four-views | `3099079` | three rejections. The last one: (double)a keeps the value 66, so "a new value" is wrong | Slightly. The mechanism is still taught, but the lesson lost its synthesis scene and the "%u keeps a's bits" fact. |

---

# Part A. The seven check changes

## 1. Sync gate: a whisper token stretched over a pause

**Commits.** It took three WP9 commits:
- `6bb548d` first introduced it, with a 1.0 s threshold, reading the offset from the token's start.
- `790eec8` lowered the threshold to 0.75 s.
- `992fa05` changed the rule to "last silence that starts inside the token".

Round 17 then fixed it in `8ca70da`.

File: `package/prax-teach/ptk/verify/media.py`, `refine()`. `SYNC_TOL = 0.5` s.

**Before (at `1526bb0`):**
```python
anchor = max(w1["start"], w1["end"] - 0.6)
offset = min((s for s in starts if anchor - 0.2 <= s <= w1["end"] + 1.0), default=w1["end"])
```

**After WP9 (`992fa05`):**
```python
stretched = w1["end"] - w1["start"] > 0.75
if stretched:
    offset = max((s for s in starts if w1["start"] - 0.2 <= s <= w1["end"]), default=w1["end"])
    return round(onset, 3), round(offset, 3)
anchor = max(w1["start"], w1["end"] - 0.6)
offset = min((s for s in starts if anchor - 0.2 <= s <= w1["end"] + 1.0), default=w1["end"])
```

**At HEAD (`8ca70da`):**
```python
STRETCH_END_SLACK = 0.3
...
if stretched:
    held = [s for s, e in silence_spans(starts, ends)
            if w1["start"] - 0.2 <= s <= w1["end"] and s <= w1["end"] <= e + STRETCH_END_SLACK]
    if held:
        return round(onset, 3), round(max(held), 3)
anchor = max(w1["start"], w1["end"] - 0.6)   # falls through to the old rule
```

**Behaviour.** I ran each version's `refine()` on three inputs. The values are measured offsets in seconds.

| Input | before (`1526bb0`) | `6bb548d` / `790eec8` | `992fa05` (WP9 final) | HEAD |
|---|---|---|---|---|
| factorial "on." stretched 31.74 to 35.5, real speech ends 31.95 | 35.61 | 31.95 | 31.95 | 31.95 |
| Codex case: token [1, 4], short pause [2, 2.2], speech resumes, silence at 4.05, cue ends at 2 | 4.05 | **2.0** | **2.0** | 4.05 |
| neuron "0.6." pause inside the word, real end 60.28 | 60.28 | 59.34 | 60.28 | 60.28 |

- Before WP9, a cue that ended on time (31.95) was measured at 35.61. That failed sync by about 3.6 s even though the audio was right, so the old rule rejected valid output.
- The same old rule passed a caption that hangs over the pause. A cue ending at 35.5 measured 35.61, which is within tolerance. So the old rule also accepted a real defect.
- `6bb548d` and `790eec8` broke the neuron case: 59.34 against a real end of 60.28 is a false fail.
- `992fa05`, the version WP9 shipped, measured Codex's case at 2.0. A cue ending at 2 then passed, although speech ran to about 4.05. That is a false pass, so as shipped the change accepted invalid output.

**WP9 classification:** changed acceptance requirement. It fixed one false fail but opened a false pass.

**Round 17.** The gates audit (P3-4) called it "justified, tested" and "stricter in the case that matters". It asked for a test of the hanging-caption direction. Codex gates #6 found the false pass and reproduced 4.05 → 2. `8ca70da` now moves the offset only to a silence that holds the token's end, and otherwise falls back to the old rule.

**Pinned at HEAD:**
- `tests/test_media.py::test_refine_ignores_stretched_last_token`. It asserts the factorial offset is 31.95, a normal last word still gives 31.95, a genuinely late word gives 33.4, one-byte's "run." gives 79.89, and neuron's "0.6." gives 60.28.
- `tests/test_media.py::test_refine_stretch_needs_a_silence_holding_the_token_end`. It asserts Codex's case gives `off == 4.05` and `abs(off - 2.0) > media.SYNC_TOL`. It asserts the hanging caption measures 31.95, so a cue ending at 35.5 fails. And it asserts a silence that ends well before the token's end does not count, so with no held silence the later boundary 61.2 stands.

Both tests passed.

**Final: bug correction.** At HEAD the rule is the old rule unless a silence really holds the stretched token's end. In that case it measures the real end of speech. It accepts the on-time cue the old rule rejected, and it rejects the hanging caption the old rule accepted. I found no input that HEAD passes and the old rule failed where the audio is wrong.

Residual risk: the 0.3 s slack, and `max(held)` picking a later silence if whisper dropped words. The WER gate (0.10) limits that.

## 2. Canary generator: value-swap canaries always plant a real error

**Commit.** `c7bb1ab`, file `ptk/verify/mutation_claims.py`, `_other_value()`.

**Before:**
```python
m = re.fullmatch(r"(-?)(\d+)((?:\.\d+)?)", v)
...
return next((p for p in pool if p != v and p.isalpha() == v.isalpha()), None)
```

**After (unchanged at HEAD):**
```python
m = re.fullmatch(r"([-+]?)(\d+)((?:\.\d+)?)", v)
...
# another value, but never one that still says v (a swap to "0.8 * 1.5 = +1.2" for "+1.2" plants nothing)
return next((p for p in pool if p != v and v not in p and p.isalpha() == v.isalpha()), None)
```

**Behaviour.**
- Before, "+1.2" did not match the number regex because of its leading "+". The generator then picked the pool value "0.8 * 1.5 = +1.2". The "mutated" claim still said +1.2, so it stayed true and the reviewer rightly accepted it.
- `caught()` needs an overall reject naming the planted claim or a changed text. So the canary counted as missed, and the lesson failed the canary gate because the generator had planted nothing.
- After the fix, "+1.2" is nudged to "+2.2", and a pool value that contains the original is never used.

The only side effect: when every candidate in the pool contains the value, no automatic swap is made for that claim, so there can be fewer automatic canaries. This never turns a missed catch into a pass.

**Round 17.** Gates audit: "no finding … A generator bug can only cause a false failure … never a false pass." Codex gates #9 lists it as a legitimate fix. No r17 commit touched it.

**Pinned:** `tests/test_mutation_claims.py::test_value_swap_plants_a_real_error`. It asserts:
- `_other_value("+1.2", ["0.8 * 1.5 = +1.2", "-0.4"]) == "+2.2"`
- `_other_value("-0.4", []) == "-1.4"`
- `"main got 6"` skips the pool item that contains it and picks `"enter factorial(1)"`

The test passed.

**Final: bug correction.** The old generator caused false canary failures and never false passes.

## 3. Claims collector: wrapped SVG lines joined, and the wrong-belief callout reported as labelled

There are two separate changes here.

### 3a. Joining wrapped inline-SVG lines

**Commit.** `ee7b25f`, `ptk/verify/claims.py`, `_Collector`. This collects texts from HTML pages: the video compositions and the IVE.

**Before.** Every text node was its own item:
```python
def handle_data(self, data):
    ...
    for tag, attrs in reversed(self.stack):
        for a in MAP_ATTRS:
            if a in attrs:
                self.items.append((a[5:], attrs[a], data))
```

**After.** An inline SVG `<text>` is one run. A `<tspan>` with a `y` adds a space before it:
```python
if tag == "text" and self.svg_text is None and any(t == "svg" for t, _ in self.stack):
    ...
elif tag == "tspan" and self.svg_text is not None and "y" in a and self.svg_text[3]:
    self.svg_text[3].append(" ")
```

**Behaviour.** Before, a claim sentence wrapped over two `<tspan y=…>` lines in a video or IVE SVG became two half sentences. Each half failed mapping as a partial claim. So a correctly drawn, wrapped claim was rejected. The still's SVG path (`_svg_texts`) already joined lines this way, so this only brings HTML pages into line with stills. After the change, the joined sentence must still match the whole claim. A half sentence on its own still fails.

### 3b. Reporting the still's wrong-belief callout as labelled

**Commit.** `790eec8`, `_svg_texts`. This changes what the reviewer is told about where a misconception appears.

**Before:**
```python
raw.append((src[0], src[1], body, svg.name))
```

**After WP9:**
```python
labelled = {el.get("data-in") for el in root.iter() if el.get("data-chrome") == "wrong_belief" and el.get("data-in")}
...
if src[0] == "misconception" and el.get("data-in") and el.get("data-in") in labelled:
    where = "still (labelled as a wrong belief)"
```

**Behaviour.**
- Before, the reviewer saw the misconception's false statement placed in "neuron-wide-light.svg", with nothing saying it was shown as wrong. A reviewer could fairly reject it as a false statement in the artifact, even though the still labels it.
- After WP9, the reviewer is told it is labelled whenever any element with `data-chrome="wrong_belief"` shares its `data-in`.
- Codex gates #4 showed the hole: an empty `<g data-chrome="wrong_belief" data-in="x"/>` makes an unlabelled misconception look labelled. That could get a reviewer to accept a still that presents a false belief as fact.

**WP9 classification:** 3a is a bug correction. 3b is a changed acceptance requirement, because it trusted metadata.

**Round 17.** Gates audit P3-3: "Justified, needs tests". It said the outer check stays strict for the join, and that `still-measure.js` grounds `data-in`. Codex gates #4 called the label a P2 that "fabricates reviewer evidence".

`8295590` fixed it. `_labelled_boxes()` now needs:
- a `<text>` whose words are the chrome string;
- `_drawn()`: painted, with no `display:none`, `visibility:hidden`, `opacity:0` or `fill="none"` on it or any ancestor;
- `_untransformed()`: no `transform`;
- `_inside()`: inside the same `<rect id>` as the misconception, by geometry.

The misconception text itself must also be inside that box. In its own words: "The label's own data-in is not trusted; the geometry decides."

**Pinned:**
- `tests/test_claims_collect.py::test_wrapped_svg_lines_join_into_one_claim`. It asserts a two-line still and the same SVG inline in HTML both give one run `f"{a} {b}"`, a plain tspan joins with nothing, and the half sentence alone fails `map_item`.
- `tests/test_claims_collect.py::test_wrong_belief_label_must_be_drawn_in_the_box`. It asserts the real neuron still reports `"still (labelled as a wrong belief)"`. It also asserts that each of these drops the claim back to `"s.svg"`: an empty `<g>`, the label moved to `y="40"`, `fill="none"`, `opacity="0"`, and wrong words.

Both tests passed.

**Final: bug correction.** Both parts stop the old collector from rejecting valid output. At HEAD the label annotation needs a drawn label in the same box, so it can no longer be faked with metadata.

## 4. Frame probe: paths compared as sets, and the panel's state read

**Commits.**
- `4b27a8f` reads the panel state. It is stricter: a new match condition.
- `790eec8` compares paths as sets. It is looser. The same commit changed the renderer to draw one dot per line: `for n in dict.fromkeys(run)  # one dot per line, however often the path passes it`.

File: `ptk/verify/frames.py`, `match_state()`.

**Before (at `1526bb0`):**
```python
if (s["program"] == probe["program"] and s["line"] == probe["line"]
        and sorted(s.get("path", [])) == sorted(probe["path"]) and s["output"] == probe["output"]):
    return st["id"]
```

**After WP9 (`790eec8`):**
```python
and sorted(set(s.get("path", []))) == sorted(set(probe["path"])) and s["output"] == probe["output"]
and probe.get("panel", "none") in ("none", st["id"])):
    return st["id"]
```

**Behaviour.**
- With one dot per line, a frame cannot show how many times a line was passed. The multiset comparison could never match factorial's states, because recursion repeats lines. So valid frames came back "unknown" and failed `video.scene-layout`.
- Set comparison fixes that.
- Reading the panel state adds a real constraint: a frame whose panel shows the wrong state no longer matches.

WP9 left two holes:
1. Two trace states with the same program, line, output and path set became indistinguishable. `match_state` returned the first one.
2. `panel == "none"` (no `.mlayer` drawn) matched any state, so a panel lesson that lost its panel still passed.

**WP9 classification:** bug correction (the set comparison) with a stricter part (the panel) and two gaps.

**Round 17.** Gates audit P3-1: "Justified, needs a guard." Codex gates #9 lists the path set as legitimate. `c5f3c65`:
- `match_state` returns `"ambiguous"` when more than one state fits, and `scene_layout_gate` treats that as a failure.
- `set_collisions()` fails a lesson without a panel that has indistinguishable states.
- For a lesson with `figure.panel`, the drawn panel must equal the state: `probe.get("panel") == st["id"]`. A lost panel (`"none"`) matches nothing.

Round 18 `f8c028c` then made question scenes keep the panel too. Its `answer_on_panel` check fails a question frame whose panel shows an answer fact.

**Pinned:** `tests/test_frame_state.py::test_path_set_matching_refuses_ambiguity`. It asserts:
- a twin state with a repeated path gives `"ambiguous"`;
- `set_collisions(twin) == [[s0, "s-twin"]]`, and the slice has none;
- for neuron, `{"panel": "none"}` gives `"unknown"` in a normal scene, with no scene, and (since r18) in a question scene.

The test passed.

**Final: bug correction.** The set comparison matches what a frame can actually show. Both WP9 gaps are closed, and the panel reading makes the probe stricter than it was before WP9.

## 5a. IVE caption check reads the caption band

**Commit.** `4b27a8f`, `ptk/verify/visual.py`, `ive.controls`. WP9 moved the IVE's captions out of the browser's native track into a drawn band under the film.

**Before:**
```js
const caps = [...v.textTracks].find((t) => t.kind === 'captions'); const cb = document.getElementById('caps');
const m0 = caps.mode; cb.click(); const m1 = caps.mode; cb.click(); const m2 = caps.mode;
```
```python
ctl.get("caption_modes") == ["showing", "hidden", "showing"]
```

**After WP9:**
```js
const band = document.getElementById('capband'); ...
const m0 = band.dataset.on; cb.click(); const m1 = band.dataset.on; ...
```
```python
ctl.get("caption_modes") == ["true", "false", "true"]
and ctl.get("caption_track_mode") == "hidden" and ctl.get("caption_text") == timing["cues"][0]["text"]
```

**Behaviour.**
- With band captions, the native track is always `hidden`. The old check would fail every IVE built the new way, even when the captions toggled correctly.
- The WP9 check read a data attribute that the page's own script sets. A CSS slip that keeps the caption drawn while `data-on="false"` passed. That is gates audit P3-2 and Codex #7.
- It also checked only one cue.

**WP9 classification:** changed acceptance requirement. It replaced a check on what the browser draws with a check on a flag.

**Round 17.** `c955aff` measures `#captext` as drawn after each click:
- computed `visibility`;
- `display` and `opacity` up the tree;
- colour not transparent;
- a box of at least 1 × 1.

It wants `[True, False, True]`, the first cue's text, the text at a second cue, and the native track `hidden`. `test_ive.mjs` now measures the same way.

**Pinned:**
- `tests/test_ive.py::test_caption_toggle_measures_rendered_text`. On the built slice IVE, it asserts the real page passes `captions_ok`. It also builds a "slip" page: the caption is forced visible and its text can't be cleared, while `data_on` still toggles `["true","false","true"]`. It asserts `shown == [True, True, True]` there, and that `captions_ok` fails it.
- `tests/test_ive.py::test_caption_band_clear_of_film`, from WP9, pins the band layout.

Both tests passed.

**Final: bug correction.** The old track-mode check would reject the new, valid caption band. HEAD judges the band by what is drawn, at two cues.

## 5b. IVE explore check for lessons without live editing

**Commit.** `4b27a8f`, `visual.py`, `ive.explore-return`. The IVE script also gained `if (!r && !b) document.getElementById('prev').click();`, so with no live controls it steps back through the film.

**Before:**
```python
"edit_marked_yours": e2.get("origin") == "yours" and bool(e2.get("edit")) and e2.get("border") == "dashed"
and e1.get("border") != "dashed" and e2.get("output") != e1.get("output"),
```

**After WP9:**
```python
live_edit = ive_proj.live_model(lesson) is not None
"edit_marked_yours": e2.get("origin") == ("yours" if live_edit else "step") and bool(e2.get("edit"))
```

**Behaviour.**
- Before, every lesson had to show a live edit marked "yours" in EXPLORE. The three panel exemplars (one-byte, factorial, neuron) have no live model, so they could not pass.
- After, a dashed "step" back through the recorded film passes instead.
- `live_model()` returns None whenever the switch model raises `ModelReferenceError`. So a broken switch lesson silently dropped to step mode and passed. The audit's counterexample, P2-2, was run: drop `figure.compare.program` and the lesson passes.

**WP9 classification:** changed acceptance requirement.

**Round 17.** Gates audit P2-2: "weakening through a silent fallback, redesign". It also said: "AC-6.6 says 'In EXPLORE, live edits are visibly separate from the recorded film'. For three of four exemplars there are no live edits at all … That is a scope decision the spec has not made." It asked Prax to decide.

`baccb0f` added `explore_mode()`. A `figure.panel` declares step mode. Any other lesson must build its live model, otherwise `live_model_builds` is false and the gate fails. The check is now named `live_edit_marked_yours` or `step_back_marked`.

**Pinned:** `tests/test_ive.py::test_explore_mode_is_declared_not_inferred`. It asserts:
- the switch lesson is `mode == "live"` and fails on a step-back page;
- the broken switch (no `compare.program`) has `mode == "live"`, `live_model_builds` false, and a model error;
- neuron is `mode == "step"` with `step_back_marked`, and fails if the step is not marked off the film.

The test passed.

**Final: changed acceptance requirement.** The silent fallback is gone, which is good. But at HEAD, a panel lesson meets AC-6.6 with a step back through the recorded film and no live edit, and the spec text was never changed. `spec/SPEC.md` AC-6.6 still reads: "In EXPLORE, live edits are visibly separate from the recorded film." `reviews/final-verification.md` lists "the seven WP9 evaluator changes" as "still waiting on Prax's approval". This one is the substantive decision: does a step-through explorer count as EXPLORE for AC-6.6?

## 6. The outgoing panel layer may overlap during its cross-fade

**Commit.** `790eec8`, `ptk/project/video.py`. This is a renderer change that opts an element out of HyperFrames' layout audit. `hf_check_clean` (`ptk/build.py:319`) fails on any HyperFrames warning.

**Before (`4b27a8f`):**
```python
attrs=f'class="mlayer mbefore" {fit}'
...
js.append("d.to(q('.mbefore'), { opacity: 0, duration: 0.3, ease: 'power1.in' }, 0.45);")
```

**After:**
```python
attrs=f'class="mlayer mbefore" data-layout-allow-overlap="" {fit}'
...
# autoAlpha: a layer at opacity 0 is also visibility:hidden, so only the cross-fade overlaps the two
js.append("d.to(q('.mbefore'), { autoAlpha: 0, duration: 0.3, ease: 'power1.in' }, 0.45);")
```

**Behaviour.**
- Before, a panel scene draws the previous state's layer under the new one and cross-fades. HyperFrames reported the two layers overlapping, as a warning, and that failed the build. This held even for a normal 0.3 to 0.45 s cross-fade, and even when the old layer was at opacity 0, so a valid transition was rejected.
- The autoAlpha change, a renderer fix, removed the opacity-0 overlap.
- The flag exempts the whole outgoing `<svg>` from overlap checks for as long as it is visible. HyperFrames' `hasAllowOverlapFlag` walks ancestors.
- The audit's counterexample: break the fade-out tween, and the old layer stays fully shown all scene, with no layout failure and no frame-probe failure.

**WP9 classification:** changed acceptance requirement. The exemption was wider than the fade.

**Round 17.** Gates audit P2-3: "weakening, the exemption is wider than the cross-fade". `c5f3c65` added `LAYERS_JS`, `layer_samples()` and `layer_overlap_problems()`, run inside `video.scene-layout` every 0.05 s on every panel scene. Two layers may be on screen together only while:
- one of them is fading (opacity changing frame to frame);
- for at most `MAX_CROSSFADE = 1.0` s;
- ending before the scene ends.

The flagged layer must be gone at the scene's end. The flag itself stays in the renderer (`video.py:680` at HEAD).

**Pinned:** `tests/test_frame_state.py::test_panel_overlap_only_while_cross_fading`. It asserts:
- the measured neuron sc4 curves pass;
- an outgoing layer stuck at 1 gives `layer-never-fades-out` and `overlap-not-fading`;
- a layer stuck at 0.5 gives `layer-never-fades-out`;
- a 1.5 s fade gives `cross-fade-too-long`;
- a single layer passes.

The test passed.

**Final: bug correction, now bounded.** The old audit rejected every valid cross-fade. At HEAD the exemption is still on the whole layer, but the probe limits it to a real fade of 1 s or less. Overlap of the panel box with other content is still audited on the incoming layer, which has the same box and no flag.

Residual: round 18 `15fbdd4` added a second `data-layout-allow-overlap` on the factorial return-value chips (`video.py:700`). No audit covered it, and no probe bounds it the way the layer probe does. The chips do fade to opacity 0 by `FLIGHT + 0.55`, but nothing checks that.

## Also found: WP9 check changes that were not on the self-reported list

- **Axis-tick labels (`d56e4e2`, wp9).** It added `"axis-tick": "[−-]?\\d+(?:\\.\\d+)?"` to `LABEL_PATTERNS`. Any number in an axis-tick label then mapped as chrome and was never reviewed. That is a changed acceptance requirement. Codex gates #5 changed a tick to 999 and it passed. `8295590` (r17) requires a linear tick scale. `65bfe2b` (r18) binds data marks to the facts' values. Pinned by `test_claims_collect.py::test_axis_ticks_bound_to_a_linear_scale` and `tests/test_axis_ticks.py::test_ticks_bound_to_the_data`. Both passed.
- **Morph output deadline (`270af89`, wp9).** It changed `outputs_at = reveal + plan["outputs_at"] * plan["k"]` to `reveal + min(plan["outputs_at"], vproj.MORPH - 0.05) * plan["k"]`. The old output could then fade before the new output arrived and still pass. That is a changed acceptance requirement (Codex #8). `6786236` (r17) measures it on frames instead, with no planner time: `morph_output_problems`. Pinned by `test_frame_state.py::test_morph_output_stays_readable_until_the_new_output_is_on_screen`, which passed. The commit notes this made the switch video fail until a projector fix in round 18.
- **`film_cue` (`4b27a8f`).** It now skips cue 0 (`cue_list[1:]`). This is minor and I found no effect on what passes.

---

# Part B. The claims dropped after repeated rejections

All three were dropped under the "two repair rounds" budget, not because the idea was unfixable. In each case at least one reviewer accepted the final wording while another rejected it.

## B1. switch-fallthrough `c.warn` (gcc's fallthrough warning)

**History.** Added in `15fbdd4` (r18, 17:55), repaired in `65bfe2b` (18:51) and `b006728` (18:59), dropped in `1c6a0cf` (19:14). The commit message: "c.warn (gcc's fallthrough warning) failed review three times in different ways; by the two-repair budget it is dropped with its narration line."

Kind: `caveat`. Sources, the same in every version:
- GCC manual, Warning Options, `-Wimplicit-fallthrough`, quote "Warn when a switch case falls through." (https://gcc.gnu.org/onlinedocs/gcc/Warning-Options.html)
- "gcc-16 diagnostics recorded by capture for programs/fallthrough.c", clause `programs[0].diagnostics`.

| Version | Text | Justification |
|---|---|---|
| v1 `15fbdd4` | "gcc warns about a case that can run on into the next one when -Wimplicit-fallthrough is on, as it is under -Wextra." | "GCC documents -Wimplicit-fallthrough (warn when a switch case falls through) and enables -Wimplicit-fallthrough=3 with -Wextra. The capture compiles every program with gcc-16 -Wall -Wextra and records its diagnostics: fallthrough.c gets 'this statement may fall through' at lines 7 and 9." |
| v2 `65bfe2b` | "gcc warns about a case that can run on into the next one when -Wimplicit-fallthrough is on, as it is under -Wextra, unless the fallthrough is marked as intended." | v1 plus: "it stays silent where the fallthrough is marked as intended (a [[fallthrough]] / __attribute__((fallthrough)) statement or a recognised comment) and for an empty case." |
| v3 `b006728` | "gcc warns about a case whose statements can run on into the next case when -Wimplicit-fallthrough is on, as it is under -Wextra, unless the fallthrough is marked as intended." | same as v2 |

**Rejections:**
1. **v1, 18:41 IST.** Agent `a8911b07ba0ef7f01`, job `job-245c115989`: "stated unconditionally, but gcc does not warn for every case that can run into the next one. It stays silent when the fallthrough is marked intentional (__attribute__((fallthrough)), [[fallthrough]], or a recognised /* FALLTHRU */ comment at the default level 3) and when a case label has no statements of its own. Add that qualifier." A second review in the same round, `ab08a57e2c3547767`, rejected it for the marked-fallthrough exception.
2. **v2, 18:57 IST.** Agent `ab8ef4ae2926a17fb`, job `job-28d82c514f`: "gcc does not warn for every case that runs on into the next one when it isn't marked. An empty case such as `case 1: case 2:` falls through with no warning. The justification names that exception, but the sentence leaves it out." Agent `a824391d69fb38984` gave the same reason and also noted the cited field name.
3. **v3, 19:05 IST.** Agent `a85c817afb373a984`, job `job-da09bc20af`: "-Wimplicit-fallthrough is a heuristic and gcc does not warn for every case that can run on into the next one even when unmarked; e.g. it stays silent when the case falls into a label followed only by break (the 'terminated branch' exception) … Scope it, e.g. 'gcc can warn ...' or 'here gcc warns at lines 7 and 9'." Another review of v3 at the same time, `a5402b52544ceb639`, accepted it.

**I checked rejection 3 with gcc-16 16.2.0** (`-Wextra -c`). A case with a statement that falls into `case 2: break;` gets **no** warning. A case falling into a case with statements does warn. An empty case gets none. So all three rejections were correct, and v3 is still false as a general statement.

**What the lesson lost** (`1c6a0cf`, `lessons/switch-fallthrough/lesson.json`, −24 lines):
- the claim `c.warn`;
- the third narration line of scene `sc6` "Add the missing breaks": "gcc warns about a case whose statements can run on into the next case when -Wimplicit-fallthrough is on, as it is under -Wextra, unless the fallthrough is marked as intended." This was text `t.255` in the claims job, and it was in the film, the transcript and the captions.

At HEAD no learner-facing text mentions gcc or the warning. I searched all 68 teaching texts in the current claims job. Only `c.fix`'s *justification* still says "gcc-16 with -Wextra … reports nothing for with_break.c, while it warns twice for fallthrough.c", and learners never see a justification.

**Is the explanation weaker?** The mechanism is not. Entry at the matching label, running on past later labels, and `break` ending the switch are all still taught (`c.recap`, `c.fix`, `c.withbreak`, the trace). What is gone is the practical defence: compile with `-Wextra` to catch a missing break, and mark a deliberate fallthrough. For a lesson whose misconception is "a case stops at the next label", that is a real gap in what the learner can *do*, not in what they understand.

**A correct version**, scoped to the captured run as reviewer 3 suggested: "Here, gcc-16 with -Wextra warns 'this statement may fall through' at lines 7 and 9 of fallthrough.c and says nothing for with_break.c." It could be followed by a hedged general caveat: "-Wextra turns on -Wimplicit-fallthrough, which flags many unmarked fallthroughs but not all of them."

## B2. neuron `c.kformula` (the explorer's formula)

This is not `c.formula`. `c.formula` ("This neuron multiplies each input by its weight, adds the bias, then gates the sum with ReLU.") is still in the lesson at HEAD, and the final claims suite accepted it.

**History.** Added in `15fbdd4` (r18, 17:55) with the new neuron explorer. Repaired in `4701c7e` (20:02) and `f3c254c` (20:17). Dropped in `48da9d7` (20:31): "drop the neuron formula claim after three rejections (two-repair budget); the explorer keeps its computed-values provenance line."

Kind: `mechanism`. Facts: `f.k1.z`, `f.k2.z`, `f.k3.z`. Sources: "programs/neuron.c" lines 8-14, and "captured run of programs/neuron_k1.c, neuron_k2.c, neuron_k3.c" stdout lines 1-4. The justification was the same in every version:

> "programs/neuron.c computes t1 = x1 * w1, t2 = x2 * w2, z = t1 + t2 + b left to right in double and a = fmax(0.0, z). The explorer's values are computed by ptk/expect_neuron.py with the same binary64 operations in the same order and printed in %g / %+g form; three variant programs (neuron_k1.c to neuron_k3.c) were compiled and run and their output matches the table at those points."

| Version | Text |
|---|---|
| v1 `15fbdd4` | "The sliders change w2 and b. z = 0.8 × 1.5 + 0.4 × w2 + b, computed in double as the program does, and a = max(0, z)." |
| v2 `4701c7e` | "For any w2 and b, the program computes z = 0.8 × 1.5 + 0.4 × w2 + b in double, left to right, and a = max(0, z)." |
| v3 `f3c254c` | "For w2 and b between -2 and 2, the program computes z = 0.8 × 1.5 + 0.4 × w2 + b in double, left to right, and a = max(0, z)." |

**Rejections.** Twelve reviews accepted the claim itself between 18:40 and 19:53 IST. The rejections were:
1. **v1, 19:53 IST.** Agent `aeb0e5e584bfcf430`, job `job-e6ba200e00`. The claim was accepted, but its text `t.087` was rejected: "the text says 'The sliders change w2 and b', but it appears on the static cards 'cards out:p2', 'cards out:p3' and 'cards out:p4', where there are no sliders … Reword it for the cards." This is a medium problem, not a truth problem.
2. **v2, 20:08 IST.** Job `job-80833b06d9`, plus canary job `job-8f4a531c5c` (agent `abc835601cd4706fa`): "'for any w2 and b' covers every double, including NaN and infinities. With w2 or b NaN (or -inf/+inf making t2 + b NaN), z is NaN and fmax(0.0, z) returns 0 (C17 §7.12.12.2 footnote, §F.10.9.2), which is not max(0, z). Scope it to finite values, e.g. the explorer's range."
3. **v3, 20:22 IST.** Agent `a79e9b92119f3078d`, job `job-1d62a4f484`: "'the program' is neuron.c, which fixes w2 = -1.0 and b = -0.2, so no program in the job computes z over the range -2 to 2; only three variant points (p2-p4) were run, and the range values come from ptk/expect_neuron.py and a 'table' that are not in the job and cannot be checked … Reword to scope it to edited copies of the program (or the explorer's model) and cite the checked points." Another review of v3, `a954b31214521c7b0`, accepted it.

All three rejections are right. One more defect no reviewer named: v3 says "b between -2 and 2", but the explorer's `b` slider runs from -1.0 to 1.0 (`figure.explore.sliders` at HEAD).

**What the lesson lost** (`48da9d7`, −22 lines):
- the claim;
- its entry in `figure.explore.claims`, which is now `["c.kzero", "c.relu"]`.

Its text `t.087` was drawn in the explorer and on the three variant output cards. At HEAD:
- The explorer shows `c.kzero` ("With w2 = -1 and b = -1, z prints as -0.2 and a is 0 …"), `c.relu`, and the chrome line `k_computed`: "Computed with the program's formula in double, in the program's order. Captured runs agree at {count} points."
- `cards out:p2` carries `c.kzero`.
- `cards out:p3` (neuron_k2.c, z = 1.7, a = 1.7) and `cards out:p4` (neuron_k3.c, z = -0.6, a = 0) have `"why": []`. Those two cards now show output with no explanation. out:p4 is the "ReLU clamps a negative z" case.

**Is the explanation weaker?** A little. The film still teaches the full mechanism: `c.formula`, `c.mul`, `c.add`, `c.relu`, `c.out`, and `c.kzero` for one variant. What the explorer lost is the explicit relation it is built to show: z = 1.2 + 0.4·w2 + b, so z moves 0.4 per unit of w2 and 1 per unit of b. Without it, the provenance line refers to "the program's formula" that the explorer no longer states, and two cards have no "why".

**A correct version**, scoped to the explorer's model, with checked points cited: "In the explorer, z = 0.8 × 1.5 + 0.4 × w2 + b, computed in double in neuron.c's order, and a = max(0, z). Copies of neuron.c compiled with (w2, b) = (-1, -1), (0.5, 0.3) and (-2, -1) print z = -0.2, 1.7 and -0.6." The slider ranges (w2 from -2 to 2, b from -1 to 1) keep the inputs finite, so the NaN objection does not arise. The cards for p3 and p4 would each need their own one-line why, for example for p4: "Here z prints as -0.6, which is negative, so a is 0."

## B3. one-byte-four-views `c.recap`

**History.** Drafted in `51b7eb2` (wp9, 14:55), repaired in `790eec8` (16:04) and `992fa05` (16:13), dropped in `3099079` (16:21): "c.recap was rejected three times (the third time because (double)a keeps the value 66 and changes only the type and bits). Two repair rounds are the budget, so the recap scene and claim are gone and the dek uses the accepted c.cast."

Kind: `mechanism`.

| Version | Text | Justification | Sources and facts |
|---|---|---|---|
| v1 `51b7eb2` | "Every view here shows the value 66. Only (double)a gives printf a different bit pattern." | "%d, %u and %c print 66, 66 and the character with code 66 (lines 3, 4, 6 of the run); (unsigned)a keeps the bits of 66 in an unsigned int (6.3.1.3p1, and 66 has the same representation there); %c uses the low byte 0x42. The double 66.0 is 0x4050800000000000 (line 7)." | captured run of programs/views.c stdout lines 3-7; C17 N2176 §6.3.1.3 ¶1. Facts f.d, f.u, f.c, f.dbits |
| v2 `790eec8` | "%d, %u and %c all work from the int value 66. %f works from a new value, the double that (double)a made." | "Line 11 passes a to %d, line 12 passes (unsigned)a, which is still 66 (6.3.1.3p1), and line 14 passes a to %c, which converts it to unsigned char 66 (7.21.6.1p8); the run printed 66, 66 and B. Line 13 passes (double)a, a new double 66.0 (6.3.1.4p2), whose bits are 0x4050800000000000 on this binary64 machine (run line 7), and %f prints it as 66.000000." | same sources. Facts f.d, f.u, f.c, f.f |
| v3 `992fa05` | "%d and %c get the int a, and %u gets the unsigned int 66, which has the same bits. %f gets a new value, the double 66.0, whose bits differ." | "Line 11 passes a to %d and line 14 passes a to %c (which converts it to unsigned char inside printf, 7.21.6.1p8). Line 12 passes (unsigned)a: 66 is representable in unsigned int, so the value is unchanged (6.3.1.3p1), and a nonnegative value has the same representation in a signed type and its unsigned type (6.2.5p9). Line 13 passes (double)a, the double 66.0 (6.3.1.4p2), whose bits on this binary64 machine are 0x4050800000000000 (run line 7), not 0x42." | C17 §6.2.5 ¶9 (with its quote), §6.3.1.4 ¶2, captured run lines 3-7. Facts f.d, f.u, f.c, f.f, f.dbits |

**Rejections:**
1. **v1, 15:51 IST.**
   - Agent `a6237c577c8323a2f`: "'Every view here shows the value 66' is false for stdout line 7 (0x4050800000000000) … 'Only (double)a gives printf a different bit pattern' is false too: line 9 passes the pointer b and line 18 passes u."
   - Agent `a58f6a374f8095718` gave the same verdict and named line 18.
2. **v2, 16:11 IST.**
   - Agent `a039e6e0370b94c3b`: "%u does not work from the int value: line 12 passes (unsigned)a, a new unsigned int value made by a conversion, the same kind of step the sentence calls 'a new value' for %f."
   - Agent `a8eb2015d89b7b54d` gave the same verdict.
3. **v3, 16:19 IST.**
   - Agent `ae56fbafacd26ad6c`: "it says %f 'gets a new value, the double 66.0', set against %u keeping 66. But the clause it cites, 6.3.1.4p2, says the converted value is unchanged, just like 6.3.1.3p1 for unsigned. What is new is the type and the representation, not the value. Fix: '%f gets the same value 66 converted to double (66.0), whose bits differ on this machine.'"
   - In the same round, agent `a9bb05645a19fade0` accepted v3 ("True as worded").

The third rejection is correct. The reviewer's own one-line fix was available and was not tried.

**What the lesson lost** (`3099079`, `lessons/one-byte-four-views/lesson.json`, −51/+1):
- the claim;
- scene `sc8` "Recap" (view `summary`, state `s4`, mechanism `s2`, key nodes code, output and panel), with its narration: "Percent d and percent c get the int a, and percent u gets the unsigned int 66, which has the same bits. Percent f gets a new value, the double 66.0, whose bits differ."
- `figure.title_claim` changed from `c.recap` to `c.cast`.

The film now ends on sc7 "Without the cast", the undefined-behaviour scene, with no closing synthesis.

**Is the explanation weaker?** A little. Each piece is still taught on its own:
- `c.d`, `c.u` ("the value stays 66"), `c.char`;
- `c.cast` ("(double)a converts the value 66 to the double 66.0 … bits 0x4050800000000000, not the bits of a");
- `c.samebits`, `c.dbits`.

What is lost:
1. The one sentence that sets the four conversions side by side, which is the point of a lesson titled around four conversions.
2. The fact that (unsigned)a keeps a's bits (§6.2.5 ¶9). That contrast is exactly what makes the double's different bits stand out. No remaining claim states it: `c.u` talks only about the value.

**A correct version**, following the third reviewer's fix: "%d and %c get the int a. %u gets (unsigned)a: still the value 66, with the same bits as a. %f gets (double)a: the same value 66 as the double 66.0, whose bits on this machine are 0x4050800000000000, not a's."

---

## Files and commands

- Code: `package/prax-teach/ptk/verify/{media,mutation_claims,claims,frames,visual}.py`, `package/prax-teach/ptk/project/video.py`, `package/prax-teach/ptk/build.py:319`.
- Reviews: `reviews/round17-gates-audit.md`, `reviews/round17-codex-gates.md`, `reviews/final-verification.md`, `PROGRESS.md` (WP9 section and the round 17/18 notes).
- Tests run, all passing:
  - `test_refine_ignores_stretched_last_token`, `test_refine_stretch_needs_a_silence_holding_the_token_end`
  - `test_value_swap_plants_a_real_error`
  - `test_wrapped_svg_lines_join_into_one_claim`, `test_wrong_belief_label_must_be_drawn_in_the_box`, `test_axis_ticks_bound_to_a_linear_scale`, `test_ticks_bound_to_the_data`
  - `test_path_set_matching_refuses_ambiguity`, `test_panel_overlap_only_while_cross_fading`, `test_morph_output_stays_readable_until_the_new_output_is_on_screen`
  - `test_explore_mode_is_declared_not_inferred`, `test_caption_toggle_measures_rendered_text`, `test_caption_band_clear_of_film`
