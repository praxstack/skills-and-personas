# B0: visual-quality measures for Track B (AC-10.1 to AC-10.5)

Written 2026-10-19 on branch `v22/b0`, before any visual work. Revised the same day after an independent adversarial review (verdict "ready after P1 fixes"). Every finding is fixed; see "Review findings" at the end. These are new, stricter checks. No projector, template or lesson was changed, and no existing test or gate was weakened. The one change outside `tests/` is a new optional, closed-list schema field (`needs_hedge`, below). FREEZE-v2 requires an independent review before B1 to B5 start.

## Short answer

All five checks run under `ptk selftest`. Each passes its good fixtures and fails its bad fixtures, including every input the reviewer crafted to slip past the first version. Against the rc1 builds, every lesson fails every check:

| Lesson | 10.1 still | 10.2 mechanism | 10.3 video | 10.4 live captions | 10.5 narration |
|---|---|---|---|---|---|
| switch-fallthrough | fail | fail | fail | fail | fail |
| one-byte-four-views | fail | fail | fail | fail | fail |
| factorial-stack | fail | fail | fail | fail | fail |
| neuron | fail | fail | fail | fail | fail |

AC-10.4 used to pass three lessons. It now fails them because of two reviewer rules. A sentence about the captured run must be marked `data-captured` (switch says "The captured runs use n = 2." unmarked). And the IVE must bind sentences once the explorer does (one-byte and factorial have none in the IVE).

## Where the checks live

- `package/prax-teach/tests/test_still_layout.py` (AC-10.1), `test_mechanism_figures.py` (AC-10.2), `test_video_layout.py` (AC-10.3), `test_live_captions.py` (AC-10.4), `test_narration.py` (AC-10.5).
- `package/prax-teach/tests/_b0.py`: shared helpers (not a test module). Rendered-DOM extraction, pixel-difference coverage, geometry, capture fact lookup, composition harness, MP4 frame grab, spoken word count.
- `package/prax-teach/tests/fixtures/layout/`: synthetic pass and fail fixtures; `adversarial/` holds the reviewer's crafted inputs, each now a negative fixture.
- `package/prax-teach/schemas/lesson.schema.json`: optional claim field `needs_hedge`, closed list `["on this machine"]`.

Run one with `ptk selftest -k test_still_layout` (any part of a test id). Each lesson gets `test_lesson_<slug>`. It reports `not-run` with "not built: lessons/<slug>/build/<path>" when its build is missing, never `passed`. Full measurements go to `$PTK_STATE/b0-measures/ac10.<n>-<slug>.json`. Nothing is written into a lesson build: composition pages are rebuilt in `$PTK_STATE/tmp` behind a read-only link, and every change made to a page for a measurement is undone before the next one. Rendering goes through ptk's own `node/shoot.mjs` (Playwright, network blocked), whisper through `ptk.verify.media`, frames and image differences through ffmpeg. The 20 lesson tests take about 4 minutes.

## Shared measurement rules

- **Painted coverage (figures, mechanisms).** The page is shot with the marked group shown and again with it at opacity 0 (no reflow). The 20 px cells where any pixel changes by more than 12 levels in a colour channel are counted after a one-cell dilation. Before the first shot, anything in the group drawn at under 0.3 effective opacity (element opacity times fill, stroke or colour alpha) is hidden, and so is any image that does not decode. Ground-coloured strokes and fills, faint dots, empty or broken images and empty groups therefore count for nothing.
- **Text size.** Font size times the rendered scale: the SVG screen matrix, or the product of CSS transforms and zoom on every HTML ancestor, using the square root of the determinant so rotation does not change it.
- **Text lines.** SVG text is measured one drawn line at a time, so tspans on several baselines in one `<text>` are several lines.
- **Ink.** Text, media, and shapes drawn at 0.3 opacity or more, except fill-only shapes over 10% of the canvas, which are backgrounds.

## AC-10.1 still layout

**Rules** (both themes, each SVG at its natural size):
- Landscape: width / height ≥ 1.5 for the viewBox, the rendered `<svg>` and the 2x PNG.
- Figure-led: the `[data-role="figure"]` elements paint ≥ 50% of the canvas (painted coverage).
- No code block: no 3+ stacked monospace lines that are source lines of the lesson, carry `data-src-line`, or read as C.
- No hash text: no visible text naming "sha" or "sha256" in any case, holding a 7+ character prefix of any sha256 in `lesson.json`, or holding a 7+ hex run (any case) with a digit and a letter outside a `0x` literal.
- Portrait: both themes exist and are taller than wide. Their figure paints ≥ 25% and draws the same set of facts as the wide figure. Hash text on the portrait fails too.
- Provenance off the picture: each program's stdout sha256 prefix is in the SVG's `<title>`, `<desc>`, `<metadata>` or `data-provenance`, or in `still/index.html`.

**Contract.** `data-role="figure"` on the hero; facts drawn in it carry `data-fact`; provenance goes in `<desc>`/`<metadata>` or the still page.

**rc1.** All four fail every rule except "portrait exists": wide w/h 0.70 to 0.90, figure 0%, code blocks (4 to 13 lines), the sha256 footer, portraits with no figure, provenance only on the image. The old `data-key="panel"` box would cover 15 to 22% (info only).

**Fixtures.** `still-pass/` (three gridded panels with values, 89.8% painted, portrait carrying the same facts, provenance in `<desc>`) passes. `still-fail/` fails six ways. The reviewer's `adversarial/still-g1` to `g5` all fail on figure coverage, and g5 also fails on its tspan code block and on "SHA 38AE3B01EF4A".

**Blind spots.** The figure mark is self-declared; painted coverage stops empty or invisible marks but not a dense decorative pattern. Code drawn as an image or in a proportional font escapes. An all-digit hash not in `lesson.json` escapes.

## AC-10.2 mechanism figures

**Contract.**
- Container: `data-role="mechanism" data-kind="<kind>"`, inside a `data-role="figure"` element and on the canvas.
- Values: `data-fact` on the element whose own drawn text is exactly the value. An empty element with `data-fact` counts for nothing. A value must be drawn at ≥ 0.3 opacity and ≥ 6 px, inside the canvas, and not in the ground colour. It must equal the value read again from `build/capture`.
- Every other number drawn inside a mechanism must be bound. It needs `data-from-fact` (each number appears in that fact's captured value) or `data-src-line` (each number appears in that source line), or it must be an axis tick (`data-tick` inside `data-axis`). Otherwise it fails as unbound.
- Every visible mechanism is checked, not just the first. Those of the lesson's kind must also pass the kind's structure and, on the wide still, paint ≥ 25% of the canvas.
- Kinds (`data-part` names):
  - **control-path**: `label data-line=L` for every case/default line, in a column; `enter` at the first label on the final path; `fall` on exactly the later labels on the path; `leave` on the last path line inside the switch body; a `path` that spans enter to leave and stays between them; the final state's outputs drawn inside.
  - **stack-column**: a `frame data-call=<call fact | main>` per call plus main, in one column. Each caller sits above its callee (main at the top). Each call frame shows its call, its `n` and its `ret` value. A `return data-from=<callee> data-to=<caller>` line runs from the callee's frame up to the caller's frame (its end is higher on screen and nearer the caller), lies between them, and the caller shows the returned value.
  - **bytes**: `bytes data-var="a"` with sizeof(int) `byte data-offset=k` cells and `bytes data-var="(double)a"` with 8. Each cell text is "42", "0x42" or "01000010" and carries its captured fact. Exactly one `data-low="true"` cell, at the least significant offset. The cells must rebuild `a` from the trace and the IEEE-754 bits of `(double)a` (computed with `struct`).
  - **neuron**: 3+ `panel` parts and every fact in the lesson's `figure.panel`.
- Video: at least one scene's settled frame shows a mechanism of the kind, and every value any visible mechanism draws matches its capture.

**rc1.** All four: no mechanism in either wide still or in any video scene. Behind the markup, the switch has no path figure, factorial draws arcs, one-byte never draws `00 00 00 42` and has no captured per-byte facts yet.

**Fixtures.** A pass and a fail per kind, plus `control-path/fail-path.svg` (extra fall, path past the break), `bytes/faint-tiny.svg` (right bytes at 0.1 opacity and 20% scale), `bytes/none.svg`, and the reviewer's `adversarial/mech-stack-attr.svg`. That last one fails on empty ret groups, main at the bottom, returns flowing down, an unbound "n = 1", no figure, and a second mechanism drawing 7.

**Blind spots.** Structure is checked on the stills; the video checks presence and values. The explorer and IVE figures are not checked here.

## AC-10.3 video layout

**Rules.**
- Samples at 25%, 50% and 75% of every scene and at its settled point, in the rendered composition at 1920 x 1080.
- Output ≥ code. Output means `data-fact`/`data-m` of a stdout fact, `data-role="output"`, or any monospace text equal to a captured output line. Code means `data-key="code"`, `data-src-line`, or any monospace line that is a source line or reads as C. Axis ticks are neither.
- Teaching text ≥ 28 px: claim, misconception and question text, scene title, `data-role="teaching"`, and any non-monospace prose of 4+ words. Chrome and label marks no longer exempt prose.
- Mechanism scenes: the visible mechanisms paint ≥ 55% of the frame (painted coverage). A mechanism scene comes from storyboard `key_nodes` (`panel`/`mechanism`), `data-scene-kind="mechanism"`, or a visible mechanism. At least one is required.
- DOM empty region ≤ 20%: the largest 20 px-grid rectangle no ink touches.
- MP4 empty region ≤ 20%: every frame at 2 fps, skipping 0.5 s around each cut, at quarter size, median filtered (3 x 3). A 20 px block is empty when its gray range is ≤ 10.
- Phone fold (IVE at 390 x 844, both themes): measured at load and again after one interaction ("Pause and explore", else the first enabled button). A visible mechanism must lie fully in the first screen, be ≥ 75% of its width, and paint ≥ 30% of its own box.

**rc1.**

| Lesson | DOM samples | Output < code | Min teaching px | Mechanism painted (old panel box, info) | Max empty DOM | MP4 frames over 20% | Fold |
|---|---|---|---|---|---|---|---|
| switch-fallthrough | 28 | 0 | 38 | no mechanism scene | 32.1% | 21 of 115 (max 33.9%) | fail |
| one-byte-four-views | 28 | 24 | 12.5 | 0% (39.3%) | 37.0% | 63 of 180 (max 37.0%) | fail |
| factorial-stack | 36 | 36 | 12.5 | 0% (39.3%) | 31.3% | 83 of 174 (max 31.3%) | fail |
| neuron | 24 | 4 | 9.8 | 0% (43.3%) | 21.6% | 0 of 198 (max 17.0%) | fail |

The small "teaching" text is now 4+ word chrome headings such as "ADD / FOLLOW THE ENDPOINT" at 13 to 20 px.

**Fixtures.** `video-pass` (63.5% painted) passes. `video-fail` fails five ways. `video-unmarked` has no markup at all: monospace output under monospace code, chrome-marked prose at 16 px, a ground-coloured full-frame "mechanism", and a 90% fill-only card. It fails on each. `adversarial/text-transforms.html` pins the size rule: 40 px text under scale 0.5, a halving viewBox and zoom 0.5 reads 20 px, and rotated text stays 40 px. The fold fixtures cover top, below a film, and pushed below by a click.

**Blind spots.** "Its code line" is read as the code listing's size. Samples are four per scene in the DOM and two per second on the MP4; a shorter flash is not seen. The film is dark in both page themes, so a light film is not measured.

## AC-10.4 live captions

**Rules.**
- Controls: the walker steps every slider value, radio option, toggle and checkbox state, combining controls within a region (all 861 neuron grid points). It presses step buttons until disabled. It runs on the explorer and the IVE explore panel, at 1440 light and 390 dark.
- Prose: any visible block, any tag including SVG text, whose own inline text has 3+ words. Controls, buttons and code listings are not prose. Drawn state is read only outside prose:
  - "name = value" pairs;
  - slider readouts named by their label;
  - checked radios named by their legend;
  - `data-state-var` elements.
  A `data-state-var` inside a sentence does not bind it.
- Sentences: "name = value" and "name prints as value" assertions must match their region's drawn state. Unbound "=" assertions fail. A block marked `data-captured="<fact ids>"` is not compared with live state; every number in it must appear in those facts' captured values. The word "captured" alone no longer skips anything.
- Model (neuron): at every step the drawn z and a are recomputed from the drawn w2 and b in binary64 (x1, w1, x2 from the capture) and compared after %g rounding.
- Rounding: a drawn value below 1e-9 that is not zero needs a visible binary64/double rounding sentence in its region. Neuron must reach that state.
- IVE: not-run when its panel has no controls or no assertions, unless the explorer has assertions: then it fails.

**Contract.** `data-role="explore"` on live regions; `data-state-var` on live readouts outside sentences; `data-captured="<fact ids>"` on sentences about captured runs.

**rc1.**
- switch-fallthrough: 10 mismatches per page, all from the unmarked "The captured runs use n = 2." (explorer 26 assertions, IVE 12).
- one-byte-four-views: explorer 26 assertions, 0 problems. The IVE binds none.
- factorial-stack: explorer 5 assertions, 0 problems. The IVE binds none.
- neuron: 872 steps per page; the model agrees with the drawn z and a at all 872. 2,550 mismatches come from the fixed sentence, and z = 1.11022e-16 (and 2.22045e-16) is reached at 4 grid points with no explanation. The IVE binds none.

**Fixtures.** `explorer-pass.html` passes all 861 combinations (captured sentence bound, model agrees, tiny case explained). `explorer-fail.html` fails on the stale sentence, a captured sentence with an uncaptured number, a model disagreement (no ReLU clamp) and the unexplained tiny value. The reviewer's three pages fail with mismatches.

**Blind spots.** Only the two assertion forms are read; word numbers and paraphrases are not. The model exists for the neuron only. The IVE caption band is not part of this check.

## AC-10.5 narration

**Rules.**
- Pace ≤ 170 wpm per line, from the MP4 audio. Silences come from silencedetect (-40 dB, 0.12 s), with windows between the midpoints of neighbouring gaps; the last window ends at the audio's end. Words are the TTS input with numbers counted as spoken.
- Hedges: none of the six phrases in any narration sentence. The only exemption is "on this machine", and only in a sentence that is a sentence of one of the line's claims, when that claim lists it in `needs_hedge` and cites a platform fact.
- No verbatim repeated sentence.
- "unsigned char" is never "unsigned car" in the TTS input or the current lexicon, and whisper hears "unsigned char".
- Every lexicon token used: the TTS input equals the current lexicon's transform, and whisper hears each code token in an accepted form.
- Values: each spoken number that is a captured value must be on screen within 0.5 s, drawn by an element whose `data-fact`/`data-m` names a fact holding that number. The code listing counts only for source literals. Spoken numbers that are neither captured nor source literals fail.

**Contract.** `needs_hedge` (schema, closed list) on claims that truly need "on this machine"; values bound with `data-fact`/`data-m`.

**rc1.**

| Lesson | Max / median wpm | Lines > 170 | Hedges | Repeats | unsigned char | Values missing | Uncaptured numbers |
|---|---|---|---|---|---|---|---|
| switch-fallthrough | 218.8 / 199.2 | 11 of 12 | 0 | 0 | n/a | 0 of 0 | none |
| one-byte-four-views | 240.4 / 191.2 | 9 of 12 | 3 | 0 | fails (spoken, lexicon, heard) | 1 of 15 ("4" bytes) | "66.0" |
| factorial-stack | 221.2 / 175.2 | 9 of 13 | 2 | 0 | n/a | 0 of 31 | none |
| neuron | 203.7 / 168.8 | 5 of 11 | 1 | 1 | n/a | 3 of 28 (the "0" in a ReLU rule) | "6" (significant digits) |

**Blind spots.** The gate counts numbers as spoken words (the unexpanded rate is recorded). A small number in a rule sentence that equals a captured value is still checked, which is how neuron's "0" fails. Whisper base.en errors can affect the heard checks.

## Review findings and what changed

| # | Finding | Answer |
|---|---|---|
| P1.1 | Hull coverage: corner dots, ground-colour stroke, ground-colour fill, empty `<image>` scored 98 to 100% | Coverage is now the pixel difference with the group hidden, 20 px cells, one-cell dilation, under 0.3 opacity ignored. Undecodable images are hidden (Chrome paints its broken-image icon otherwise). The four inputs score 0%. Positive fixture is a real three-panel drawing. |
| P1.2 | Stale captions passed (div prose, data-state-var in the sentence, the word "captured") | Prose is any visible block of 3+ words whatever its tag; drawn state is read only outside prose; only `data-captured` skips live comparison, and those numbers are checked against the capture; the neuron is recomputed by an independent binary64 model. All three crafted pages fail. |
| P1.3 | One sample per scene | DOM at 25/50/75% plus settled; MP4 at 2 fps, 0.5 s guard around cuts. |
| P1.4 | Loose binding | Empty `data-fact` elements count for nothing; unbound numbers in a mechanism fail; every mechanism is checked; it must sit on the canvas, inside the figure, paint ≥ 25% of the still, and its values must be visibly drawn. |
| P1.5 | Stack direction | Enforced both ways: caller above callee (main at the top), and each return line ends higher, nearer the caller. |
| P1.6 | Code as tspans in one `<text>` | Each drawn line is its own item; the reviewer's g5 fails on its code block. |
| P2.7 | Values on screen loosely bound | Needs an element bound to a fact holding the number; uncaptured, non-literal spoken numbers fail. |
| P2.8 | needs_hedge too open | Closed allowlist ("on this machine", platform-fact claims only, in the claim's own sentence); added to the lesson schema as a closed enum; the claims job copies each claim whole, pinned by `test_needs_hedge_in_schema_and_claims_job`. No lesson text was edited. |
| P2.9 | Control path loose | Falls must equal the expected set; the path must stay between enter and leave. |
| P2.10 | DOM empty and flat frames | Fill-only shapes over 10% are background whatever their shape; MP4 frames are median filtered before the flatness test. |
| P2.11 | Size rule needed markup | Code and output are also found by monospace text; chrome and label marks no longer exempt prose; text size is now correct under scale, viewBox, zoom and rotation (the reviewer's page is a fixture). |
| P2.12 | IVE part tested nothing | Not-run with no controls or no assertions, failed when the explorer binds and the IVE does not. |
| P2.13 | Missing checks | Added: every lexicon token used, portrait carries the same figure, provenance off the picture, fold re-measured after one interaction. |

## Parked after round 2 (orchestrator, 2026-10-19)

B0 used both of its rounds (FREEZE-v2: at most 2 per deliverable). The second independent review (files in `$PTK_STATE/review-b0/r2`) confirmed every round-1 hole closed and found five new ones. They are parked, not fixed, and recorded here as known blind spots:

1. **Coverage counts fill-only cards and dilates sparse marks.** A blank full-canvas card scores 100%; a 3 px dot lattice scores 96%. Applies to stills and the video mechanism check.
2. **Generated text escapes the caption check.** A stale sentence in CSS `::before { content }` passes, because the check reads `textContent`.
3. **A faint texture hides empty space.** A 12 px checker of 14 grey levels drops an empty half-frame from 58% to 0.08%.
4. **Values just outside the mechanism are unchecked.** A wrong value placed inside the figure but outside the mechanism passes.
5. **Widely spaced code escapes.** A 4-line C block at 2.6× line spacing passes the code-block rule.

**Mitigation:** every Track B review and the final verification must inspect the built stills, explorers, IVE pages and sampled video frames for exactly these five tricks, and report each as found or not found. Prax's visual verdict stays the final gate.

**Rules stricter than the spec, kept as written** (not loosened): spoken numbers must be captured values or source literals; any non-monospace text of 4+ words must be ≥ 28 px in video; the portrait must draw every fact the wide still draws. If one of these blocks good work, it is reported, not weakened.
