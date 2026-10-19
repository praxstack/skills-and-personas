# B0: visual-quality measures for Track B (AC-10.1 to AC-10.5)

Written 2026-10-19 on branch `v22/b0`, before any visual work. These are new, stricter checks. No existing test, gate, projector, template or lesson was changed. They need an independent review before B1 to B5 start (FREEZE-v2, "a check script that implements a SPEC v1.4 measure is candidate code, but it is written and independently reviewed before the work it measures").

## Short answer

All five checks run under `ptk selftest`, and each one fails and passes on purpose against its own synthetic fixtures. Against the rc1 builds:

| Lesson | 10.1 still | 10.2 mechanism | 10.3 video | 10.4 live captions | 10.5 narration |
|---|---|---|---|---|---|
| switch-fallthrough | fail | fail | fail | pass | fail |
| one-byte-four-views | fail | fail | fail | pass | fail |
| factorial-stack | fail | fail | fail | pass | fail |
| neuron | fail | fail | fail | fail | fail |

The failures match the final five-lens review: tall stills with code and hashes, no switch figure, inverted output size in one-byte, empty frame areas, the neuron caption that never updates, the unexplained `1.11022e-16`, and narration at about 195 wpm with "unsigned car".

## Where the checks live

- `package/prax-teach/tests/test_still_layout.py` (AC-10.1)
- `package/prax-teach/tests/test_mechanism_figures.py` (AC-10.2)
- `package/prax-teach/tests/test_video_layout.py` (AC-10.3)
- `package/prax-teach/tests/test_live_captions.py` (AC-10.4)
- `package/prax-teach/tests/test_narration.py` (AC-10.5)
- `package/prax-teach/tests/_b0.py`: shared helpers (not a test module). Rendered-DOM extraction, geometry, capture fact lookup, composition harness, MP4 frame grab, spoken word count.
- `package/prax-teach/tests/fixtures/layout/`: the synthetic pass and fail fixtures (132 KB).

`ptk selftest` picks them up by file name. Run one with `ptk selftest -k test_still_layout` (or any part of a test id). Each lesson gets its own test, `test_lesson_<slug>`. It reports `not-run` with "not built: lessons/<slug>/build/<path>" when the build it needs is missing, never `passed`. Full measurements go to `$PTK_STATE/b0-measures/ac10.<n>-<slug>.json`. Nothing is written into a lesson build: composition pages are rebuilt in `$PTK_STATE/tmp` behind a read-only link.

All rendering goes through ptk's own `node/shoot.mjs` (one Playwright browser per call, network blocked), whisper through `ptk.verify.media.whisper_words`, silences through `media.silences`, frames through ffmpeg. The five lesson runs take about 4 minutes on this Mac.

## AC-10.1 still layout

**Method.** Each SVG is loaded in Playwright at its natural size and read from the rendered DOM (bounding boxes, computed fonts and opacity), not from attributes alone.

**Thresholds and rules.**
- Landscape: width / height ≥ 1.5 for the viewBox, the rendered `<svg>` box and the 2x PNG when it exists.
- Figure-led: for each `[data-role="figure"]` element, the hull of its painted content (text, media, shapes with a visible fill or stroke; a fill-only rect over 10% of the canvas is a background and is ignored). The union of those hulls must cover ≥ 50% of the canvas.
- No code block: no run of 3 or more monospace text lines stacked as consecutive lines (baseline step 0.5 to 2.4 font sizes, overlapping or within 200 px horizontally) where each line is a source line of the lesson's programs, carries `data-src-line`, or looks like C (ends in `;`, `{` or `}`, or starts with `#include`, `case`, `switch (`, `return`, a type and a name, `printf(` and similar). One or two code tokens in a figure are allowed.
- No hash text: no visible text that names "sha256"/"sha-256", holds a 7+ character prefix of any sha256 found in `lesson.json`, or holds a run of 7+ lowercase hex characters with at least one digit and one letter that is not part of a `0x` literal. `0x4050800000000000`, `4294967295` and `01000010` pass; `stdout sha256 … 38ae3b01ef4a` fails.
- Portrait: `<id>-portrait-light.svg` and `-dark.svg` exist and are taller than wide.
- Both themes of the wide still are measured. Hash text on the portrait is recorded, not gated, because AC-10.1 names the wide still.

**Markup contract.** Mark the hero figure group `data-role="figure"`. Code lines that remain anywhere keep `data-src-line`.

**rc1 result.** Every wide still fails on all four rules, in both themes. The PNGs are the 2x of these sizes (the review's 2400 x 2658 and so on).

| Lesson | Wide size | w/h | Figure | Old panel box (info) | Code blocks | Hash text |
|---|---|---|---|---|---|---|
| switch-fallthrough | 1200 x 1329 | 0.90 | 0% | none | 13 + 13 lines | provenance footer |
| one-byte-four-views | 1200 x 1405 | 0.85 | 0% | 15.3% | 5 + 6 lines | provenance footer |
| factorial-stack | 1200 x 1707 | 0.70 | 0% | 17.0% | 8 + 4 lines | provenance footer |
| neuron | 1200 x 1400 | 0.86 | 0% | 21.7% | 12 lines | provenance footer |

"Figure" is 0% because rc1 has no `data-role="figure"` mark. The `data-key="panel"` box is shown only to say how far rc1 is from 50% even if the mark were added. All four portraits exist and are portrait (400 x 1649 to 400 x 2143).

**Fixtures.** `still-pass/` (1200 x 560, figure 65.6%, portrait present) passes. `still-fail/` (1200 x 1600, figure 7.8%, a 4-line code block, a hash footer, no portrait) fails with exactly those five reasons. `test_hash_rule_spares_values` pins the hash rule on values and digests.

**Blind spots.**
- The figure mark is self-declared. The painted hull resists an empty group, but a stray mark far away or a large stroked card still inflates it. A reviewer's eye is still needed.
- Code drawn as an image, or in a proportional font, escapes the code-block rule. So does a block whose lines look like neither the lesson's source nor C.
- An all-digit or uppercase hash that is not in `lesson.json`, or a hash split across elements, escapes the hash rule.

## AC-10.2 mechanism figures

**Method.** Playwright reads the rendered wide stills (both themes) and the video composition at each scene's settled point. Every drawn value is compared with the value read again from `build/capture/<program>.stdout` (line N, whitespace field K) or the captured platform, not from `lesson.json`. A `lesson.json` value that differs from its capture is reported too.

**Markup contract** (projectors must emit this):
- One element per mechanism: `data-role="mechanism" data-kind="<kind>"`.
- Every drawn value inside it: `data-fact="<fact id>"` on the element whose own text is exactly the value. A `data-fact` or `data-m` on an enclosing group does not count.
- `data-part` marks the pieces of each kind:
  - **control-path** (switch): `label data-line=L` for every `case`/`default` line, drawn as a column in line order and showing the label text; `enter data-line=L` at the first label on the final path; `fall data-line=L` on each later label control runs past; `leave data-line=L` on the last path line inside the switch body (the break, line 12); `path`, whose box spans from enter to leave; and the final state's output facts drawn inside the mechanism.
  - **stack-column** (factorial): `frame data-call=<call fact | main>` for every call in the trace plus main. Each call frame holds its call fact, a `n` part showing the number in the call, and a `ret` part with its return fact (paired from the capture line `factorial(K) = V`). Frames form one column: x overlap ≥ 50% of the narrower frame, no y overlap, ordered by depth. `return data-from=<callee> data-to=<caller | main>` for each return, lying between the two frames, and the caller frame shows the returned value.
  - **bytes** (one-byte): `bytes data-var="a"` with sizeof(int) cells and `bytes data-var="(double)a"` with 8 cells; each `byte data-offset=k data-fact=<fact>` reads "42", "0x42" or "01000010" and matches its capture. Exactly one cell of `a` has `data-low="true"`, at the least significant offset. The cells, in memory order and the captured endianness, must rebuild `a` from the trace (66) and the IEEE-754 bits of `(double)66`, which the test computes itself with `struct`.
  - **neuron**: at least 3 `panel` parts, and every fact the lesson's `figure.panel` names (x, w, t per term, bias, sum, out) drawn inside.
- Video: at least one scene's settled frame shows a mechanism of the lesson's kind, and every value any visible mechanism draws matches its capture. Structure is checked on the stills only.

**rc1 result.** All four fail the same way: no `data-role="mechanism"` in either wide still and in none of the video scenes (switch 0 of 7, one-byte 0 of 7, factorial 0 of 9, neuron 0 of 6). Behind the markup, the content gaps the reviewer named are still there. The switch has no path figure, factorial draws arcs, and one-byte never draws `00 00 00 42`. The one-byte lesson has no captured fact for each byte, so B2 needs a capture that prints them before the bytes figure can pass.

**Fixtures.** `mech/<kind>/` holds a small lesson per kind (`lesson.json`, `capture/p1.stdout`, the switch source). Each `pass.svg` passes, checking 3, 9, 12 and 9 values. Each `fail.svg` fails for its own reasons: wrong entry, missing leave and a wrong output (switch); frames in a row, no returns and a missing base-case return (factorial); a wrong byte and the low mark on the wrong end (bytes); two panels, a missing sum and a wrong term (neuron). `bytes/none.svg` fails with "no-mechanism".

**Blind spots.**
- A value drawn without `data-fact` is not compared. A mechanism with no facts fails, and each kind requires its own facts, but an extra unmarked number would slip through.
- "Return values flowing up" is read as "from callee frame to caller frame", declared by `data-from`/`data-to`. The screen direction is not enforced, because the narration says new frames sit on top, which makes returns flow down on screen. This needs a reviewer decision.
- The structure is checked on the stills only. The video is checked for presence and values. The explorer and the IVE live panel are not checked here.

## AC-10.3 video layout

**Method.** Each scene's sub-composition is loaded on its own at 1920 x 1080 with the same GSAP and fonts, and its paused timeline is seeked like the renderer seeks it. Two points per scene: the midpoint and the settled point (as `frames.py` picks them). CSS px at that size equal video px. Then one frame per scene, at the settled point, is cut from the encoded MP4 as a cross-check.

**Thresholds and rules.**
- Output ≥ code: every visible output value is at least as large as the visible code lines, with 0.5 px tolerance. An output value is an element whose `data-fact` or `data-m` is a stdout fact, or that sits in `data-role="output"`. A code line is text inside `data-key="code"` or carrying `data-src-line`. An identifier drawn in a figure with `data-code` is a figure label, not a code line.
- Teaching text ≥ 28 px: claim, misconception and question text, the scene title, `data-role="teaching"`, and any unmarked non-monospace prose of 4+ words that is not chrome or a label.
- Mechanism ≥ 55% of the frame in mechanism scenes, measured as for figures (union of painted hulls of visible `data-role="mechanism"` elements). A mechanism scene is a storyboard scene whose `key_nodes` name `panel` or `mechanism`, one whose root says `data-scene-kind="mechanism"`, or one that shows a mechanism. A lesson with no mechanism scene fails.
- No empty region > 20%: the largest rectangle on a 20 px grid that no drawn content touches. Card backgrounds are not content, so an empty card counts as empty.
- MP4 cross-check: the frame at quarter size (480 x 270, area filter); a 5 x 5 block (20 px at 1080p) is empty when its gray levels span ≤ 10 values. The largest rectangle of empty blocks must be ≤ 20%. The DOM cannot hide an empty frame this way.
- Phone fold: the IVE at 390 x 844, light and dark, after it is ready. A visible `data-role="mechanism"` must lie fully inside the first screen (top ≥ 0, bottom ≤ 844) and be ≥ 75% of the viewport wide. The film does not count as the figure.

**Markup contract.** `data-role="mechanism"` (as AC-10.2) on the video figure and on the IVE live figure. Code lines inside `data-key="code"` or with `data-src-line`. Output values with `data-fact`/`data-m` of a stdout fact or inside `data-role="output"`. Teaching text with `data-claim`, `data-misconception`, `data-question`, `data-label="scene-title"` or `data-role="teaching"`. Optional `data-scene-kind="mechanism"` on a scene root.

**rc1 result.** All four fail.

| Lesson | Frames | Mechanism frames, coverage (old panel max, info) | Output < code | Min teaching px | Max empty, DOM | Max empty, MP4 | Phone fold |
|---|---|---|---|---|---|---|---|
| switch-fallthrough | 14 | none: no mechanism scene | 0 | 38 | 32.1% (5 frames over) | 17.6% | no figure |
| one-byte-four-views | 14 | 12, 0% (39.3%) | 12 frames, 18 px vs 23.4 px | 30 | 37.0% (4 frames) | 32.4% (sc1), 22.0% (sc2) | panel top at 1052 px |
| factorial-stack | 18 | 16, 0% (39.3%) | 2 frames (recap), 12 px vs 16.2 px | 30 | 31.3% (8 frames) | 31.3% (sc8), 26.6% (sc9), 20.8% (sc7), 20.5% (sc1) | panel top at 995 px |
| neuron | 12 | 12, 0% (43.3%) | 0 | 30 | 21.6% (2 frames) | 13.1% | panel top at 946 px |

Teaching text already passes in rc1 (30 px minimum). The 12 to 13 px recap text the review saw is the factorial recap's output values. The output rule catches it. Even with the mark added, no rc1 panel reaches 55% (best 43.3%).

**Fixtures.** `video-pass/` (mechanism 57.4%, output 40 px over 26 px code, teaching 32 px, largest empty 9.3% in the DOM and 8.0% on its screenshot) passes. `video-fail/` (mechanism 8.8%, 18 px teaching text, 18 px output under 26 px code, empty right half 66.7% in both) fails all five ways. `ive-fold-pass.html` passes and `ive-fold-fail.html` (figure under a 700 px film) fails in both schemes.

**Blind spots.**
- "Its code line" is read as the code listing's size; all rows of a listing share one size in every rc1 template.
- Two DOM samples and one MP4 frame per scene. A frame between them that empties out is not seen.
- A textured or noisy background would read as content in the pixel check; the DOM check still applies.
- The storyboard decides which scenes must show the mechanism, beyond one required scene. A lesson could mark fewer scenes.
- The fold is checked at load only, not after an interaction. The film is dark in both page themes (theme `dark` in `timing.json`), so a light film is not measured.

## AC-10.4 live captions

**Method.** In Playwright, a walker steps every control and re-reads the page after each step (one animation frame).
- Controls: every visible range slider (each value), radio group (each option), `aria-pressed` toggle and checkbox (both states). Controls in one region are combined: up to 1500 combinations are all visited (the neuron's 41 x 21 grid is), above that each control is swept alone. Then every other button (Next, Previous, …) is pressed until disabled, at most 12 times, at every combination when there are 12 or fewer.
- Pages: the explorer, and the IVE explore panel (`#xp`) after "Pause and explore" near the end of the film. Each at 1440 x 900 light and 390 x 844 dark.
- Drawn state, read from what is drawn, never from a data flag: "name = value" pairs in visible text that is not prose; a slider's visible readout named by its label; a checked radio's visible label named by its fieldset legend ("Value of a"); any element marked `data-state-var`. A name drawn only in a code listing is compared with that listing (the source's initialiser).
- Sentences: visible prose (`p`, `li`, `figcaption`, `caption`, `dd`, `[data-claim]`, `[data-claims]`, `[data-describes]`, `[aria-live]`, 3+ words) split into sentences. Two assertion forms are read: "name = value", and "name prints as value" for a name the region draws. Each must match its own region (the closest `[data-role="explore"]`, `.knob`, `.step`, `#xp` or `main`). An "=" assertion about a name the region does not draw fails as unbound. A sentence with "captured" in it describes the captured run and is skipped.
- Rounding: when a drawn value is nonzero with magnitude below 1e-9, a visible sentence in the same innermost region must mention binary64 or double, and rounding. On the neuron lesson that state must be reached.

**Markup contract.** Put `data-state-var="<name>"` on the element that displays a live value when it is not already written as "name = value". Wrap each live region in `data-role="explore"`. A sentence about the captured run says "captured". The rounding note becomes visible in the same region as the tiny value.

**rc1 result.**
- switch-fallthrough: pass. 12 combinations (n 0 to 5, break toggle), 13 assertions per explorer page, 0 problems.
- one-byte-four-views: pass. 10 combinations, 26 assertions per explorer page, 0 problems.
- factorial-stack: pass. 12 combinations plus the step buttons, 5 assertions per explorer page, 0 problems.
- neuron: fail. 865 combinations and 872 steps per explorer page, 2,554 failing assertions per page. The fixed sentence "With w2 = -1 and b = -1, z prints as -0.2 and a is 0" fails at load (b is -0.2 and z is 0.6 on screen) and at every grid point but one. z = 1.11022e-16 (and 2.22045e-16) is reached at 4 grid points with no explanation.
- The IVE explore panel has no state sentences in any rc1 lesson (0 assertions), so the IVE part passes without testing anything yet.

**Fixtures.** `explorer-pass.html` (two sliders, a sentence rebuilt from the drawn values, a binary64 note shown at the tiny values) passes all 861 combinations with the tiny case reached 4 times and explained 4 times. `explorer-fail.html` (the same sliders under the rc1 fixed sentence) fails at load and at the tiny case.

**Blind spots.**
- Only "name = value" and "name prints as value" are read. "The program prints that sum, z, as 0.6", word numbers ("two") and output lines described in words are not checked. "is", "equals" and "stays" were dropped after they flagged rules such as "until n is 1" as state.
- Any sentence containing "captured" is skipped, so a projector could hide a stale sentence behind that word.
- Updates that land later than one animation frame would show up as failures, not passes.
- The IVE caption band (narration captions) is not part of this check.

## AC-10.5 narration

**Method and thresholds.**
- Pace ≤ 170 wpm per line, from the final audio. The MP4's audio is resampled to 16 kHz mono and `silencedetect` (-40 dB, 0.12 s) finds the silences. Each line's window runs between the midpoints of the gaps to its neighbours, and the last window ends where the audio ends. The planned timeline only separates lines. Speech starts where the first silence in the window ends and stops where the last one begins, so pauses inside a line count. Words are the TTS input (the `spoken` form): whitespace tokens, hyphenated parts counted apart ("print-f" is 2), numbers counted as read aloud ("66" is 2, "1.5" is 3). The whisper word span, the planned rate and an unexpanded word count are recorded beside it, never gated.
- Hedges: none of "in this lesson's drawing", "on this machine", "basically", "it's worth noting", "as you can see", "simply" in a narration line, unless one of that line's claims lists the phrase in `needs_hedge` (case-insensitive, whole words).
- Repeats: no sentence (`ptk.text.sentences`, lowercased, spacing and end punctuation ignored) twice in one lesson.
- "unsigned char": for each line whose text says it, neither the built `spoken` form nor the current lexicon's transform reads "unsigned car", and whisper hears "unsigned char" in that line's window as often as the text says it. This is stricter than the sync gate, whose lexicon accepts "car".
- Values on screen: a number in a line that equals a captured value (a fact, a field of a stdout line, a platform size; numbers after "line", "case", "step", "scene" and similar are skipped) must be visible within 0.5 s after it is spoken. It counts outside the code listing, or inside it when the number is a literal of the program source ("stores 66" next to `int a = 66;`). The spoken time is whisper's time for that word when whisper wrote it as digits, else its position in the line's measured speech span.

**Markup contract.** Claims that truly need a hedge carry `"needs_hedge": ["on this machine"]`. That is a claims field (Track A), so the claims reviewers see each exemption.

**rc1 result.** All four fail. 34 of 48 lines run over 170 wpm and 14 over 195 (the review counted 13 over 195).

| Lesson | Max wpm | Median wpm | Lines over 170 | Hedges | Repeats | "unsigned char" | Values missing |
|---|---|---|---|---|---|---|---|
| switch-fallthrough | 218.8 | 199.2 | 11 of 12 | 0 | 0 | n/a | 0 of 0 |
| one-byte-four-views | 240.4 | 191.2 | 9 of 12 | 3 ("on this machine") | 0 | fails 3 ways: spoken, lexicon, heard as "unsigned car" | 1 of 15 ("4" bytes in sc1.1) |
| factorial-stack | 221.2 | 175.2 | 9 of 13 | 2 ("in this lesson's drawing") | 0 | n/a | 0 of 24 |
| neuron | 203.7 | 168.8 | 5 of 11 | 1 ("on this machine") | 1 (sc6.2 repeats sc1.0) | n/a | 0 of 28 |

**Fixtures.** Synthetic tone audio: a 5-word line over 2.5 s (120 wpm) passes; a 10-word line in 2.0 s (300 wpm) fails, although its planned slot gives 150 wpm. Hedge, repeat, "unsigned char" and values-on-screen fixtures each pass a clean case and fail a broken one; the word counter is pinned on numbers and hyphens.

**Blind spots.**
- The gate counts numbers as spoken words. The review's rates used written words. Both are recorded; they differ only for numbers over 20 and decimals.
- Breath or room noise above -40 dB would stretch a line and lower its rate. Kokoro output is clean, so this does not bite today.
- Any claim can be given `needs_hedge`; the claims review has to judge each one.
- Only "unsigned char" is checked here. Other lexicon readings stay with the existing sync gate.
- Values on screen covers numbers, not word outputs such as "two" or "done". A small number in a rule sentence that happens to equal a captured value is still checked. Whisper base.en errors can affect the "unsigned char" and word-time parts.

## What a reviewer should check first

1. The stack-column direction decision (callee to caller, not screen-up).
2. Whether the hedge exemption belongs on claims (`needs_hedge`) or on storyboard lines.
3. Whether the explorer walk should also read "is" and "equals" assertions, given the false positives seen on factorial.
4. Whether one MP4 frame per scene is enough for the pixel cross-check.
