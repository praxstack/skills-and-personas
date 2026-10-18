# Final five-lens review of the four v2.1 lessons

Reviewer: Claude, independent read-only pass, 2026-10-18.
Lessons: switch-fallthrough, one-byte-four-views, factorial-stack, neuron. All four build reports say `canary-verified`, not full-suite `verified` (D22.1).
Reference: Neuron Atlas `production-v2/demo/exports/baseline.png` (2240 x 870, one landscape figure, three panels).
Baseline for comparison: `reviews/round17-five-lens.md`. The builder claimed looks 7-8 and interaction 7-8. I checked that claim myself and did not take it on trust.

Evidence is under `v2.1/.state/final-review/` (written `F/` below):
- `F/stills/`: all 16 stills downscaled, plus `portraits-sheet.png`.
- `F/pages/`: explorer, Q&A and IVE from file:// at 390 and 1440, light and dark (48 shots, in Chrome with H.264). `info.json` holds scroll widths and console errors. Text dumps are in `*-qa.txt`, `*-explorer.txt` and `*-ive.txt`.
- `F/interact/`: the IVE question flow at 1440 and 390 for every lesson (`*-ive-ask-*`, `*-ive-verdict-*`, `*-ive-after-*`, `ive-log.json`), a phone-viewport ask shot, and explorer knob runs (`explore-log.json`, `neuron-explorer-*.png`, `onebyte-explorer-a*.png`, `factorial-explorer-n5-*.png`, `switch-explorer-n4.png`, `neuron-explorer-z0-crop.png`).
- `F/frames/`: 91 video frames (chapter start +0.4 s, midpoint, end -0.6 s, and the question pause point) and `sheet-<lesson>.jpg`.

## What I checked, and what held up

- **No console errors and no horizontal scroll** on any of the 48 page loads (`F/pages/info.json`).
- **The IVE now gates the prediction (round-17 X1 fixed).** On all four lessons, at 1440 and at 390:
  - The film stops at `pause_at`, within 0.03 s.
  - It stays stopped for 3 s. Calling `play()` snaps it back to the pause point.
  - It shows the same options as the Q&A and holds until a pick.
  - A wrong pick shows "Your pick", the named misconception and the correction. The film then jumps to `resume_at` and plays, so the think gap is never heard (`F/interact/ive-log.json`).
  - At 390 the options land in the viewport with focus on the first one (`F/interact/neuron-ive-ask-390-viewport.png`).
- **No answer leaks while the question is open (X2 fixed).**
  - Chapters after the question read "Opens after you answer".
  - The transcript only lists cues already reached.
  - The page title is now neutral ("How a switch runs its cases").
  - Q&A layers whose title would give the answer away are sealed too (`F/interact/ive-log.json` askText, `F/pages/*-qa.txt`).
- **Every explorer has a real knob (round-17 P1 fixed).**
  - Neuron has w2 and b sliders.
  - Factorial has n from 1 to 5, with its own stepper.
  - One-byte has a in {66, 200, -1, 321}, with a comparison table.
  - Switch has n from 0 to 5 plus a break toggle.
  - The values are right: (unsigned)-1 = 4294967295, %c of 321 = A, factorial(5) = 120, switch n = 4 prints four, done. %c of 200 and of -1 is reported honestly as "byte 200" and "byte 255" (`F/interact/explore-log.json`).
- **Factorial now shows n and r in every frame** of the still, the film, the IVE panel and the explorer. The returned value lands in the caller's slot (`r = 2 * [1]`) (`F/frames/factorial-stack/t060.02.png`, `F/stills/factorial-stack-wide-light.png`).
- **The mechanism is the hero of the film in neuron and one-byte (fixed).**
  - Neuron frames now read like Atlas: three panels across the full width, values large, code and output a strip below (`F/frames/neuron/t054.20.png`).
  - One-byte lanes take the left 60% (`F/frames/one-byte-four-views/t090.53.png`).
- **Sync is fixed.**
  - One-byte: the %f lane appears at 40.8 s and the UB lane at 84.5 s, as each sentence starts.
  - Neuron: +1.2 and -0.4 are on screen from 18.3 s.
- **Written text is written (X4 fixed).** Captions and Q&A use `%f`, `ub.c` and `factorial(2)`. Only the TTS uses the spoken form, and "U B dot C" is now said correctly.
- **One type system (X5 fixed).** Light theme no longer uses Caveat or a serif. Both themes share the Atlas sans plus mono.
- **Truth fixes landed.**
  - `with_break.c` has a break on case 1.
  - The %f lane reads "THE NEW DOUBLE'S BITS 0x4050800000000000 / PRINTS 66.000000".
  - Neuron says %g rounds to 6 significant digits and that z is not exactly 0.6, and covers z ≤ 0.
  - The factorial question is now "What is line 4 of the output?", which needs the stack to answer.
- **Q&A layers are real questions now (X3 fixed).** Correct options are shuffled to positions 2, 2, 2 and 3 (X8 fixed). Switch adds the "two, three, four, done" distractor.
- **Cards grew to 6 to 9 per lesson (X9 fixed).** They now mix true and false, and add rule cards for UB, a break ending the switch, and ReLU max(0, z).
- **Space toggles play and pause** in the IVE.

## Scores (1 to 10), round 17 in brackets

| Lesson | Truth | Explanation | Looks | Interaction | Media |
|---|---|---|---|---|---|
| switch-fallthrough | 9 (8) | 8 (7) | 7 (6) | 9 (7) | 7 (6) |
| one-byte-four-views | 8 (7) | 7 (5) | 6 (4) | 8 (4) | 7 (5) |
| factorial-stack | 9 (8) | 8 (5) | 7 (6) | 8 (4) | 7 (6) |
| neuron | 9 (7) | 7 (6) | 8 (6) | 8 (3) | 8 (6) |

Justifications:
- **switch / Truth 9:** `with_break.c` is now fully fixed, and the explorer is exact for n = 0 to 5. Clang's missing `-Wimplicit-fallthrough` is still never mentioned.
- **switch / Explanation 8:** real layer questions and the commonest wrong answer as a distractor. The film's right column still repeats the narration word for word (`F/frames/switch-fallthrough/t029.57.png`).
- **switch / Looks 7:** clean and consistent in both themes, but there is no mechanism figure, only code with arcs. The wide still is a 2400 x 2658 poster.
- **switch / Interaction 9:** a gated prediction, a real n domain, a break toggle, honest "computed, not captured" labels, and Space works.
- **switch / Media 7:** captions are correct, but cues still run at 197 to 215 wpm (sc1.0, sc2.0, sc3.1, sc4.1). The plain MP4 keeps its 3.8 s ungated gap.
- **one-byte / Truth 8:** value and bits are now kept apart. The narration says a is 4 bytes, but no medium ever draws `00 00 00 42`.
- **one-byte / Explanation 7:** sensible scene order, the UB lane is shown when spoken, and the explorer table is excellent. The lede and the %f caption are still the same sentence in the still.
- **one-byte / Looks 6:** the lanes lead now. Scene 1 leaves about 60% of the frame empty (`F/frames/one-byte-four-views/t007.03.png`). Output values (about 18 px) are smaller than their index digits (about 28 px). The still is still a tall poster.
- **one-byte / Interaction 8:** the a knob is the lesson, and it is honest about non-ASCII bytes.
- **one-byte / Media 7:** sync is fixed, but "unsigned car" remains and sc1.0 runs at 209 wpm.
- **factorial / Truth 9:** precise, the "C has no stack" framing is honest, and n = 1 to 5 runs are captured.
- **factorial / Explanation 8:** the thesis (own n, own r) is finally shown. The question needs the stack. "In this lesson's drawing" hedging is heavy in the narration.
- **factorial / Looks 7:** good frames and return arrows. The five-arc tangle beside lines 4 to 9 survives in the film and recap (`F/frames/factorial-stack/t088.68.png`), and the recap strip uses about 13 px type with the lower-left 45% empty.
- **factorial / Interaction 8:** the n knob works with a distinct current-line marker. It is a second stepper under the first, which is redundant UI, and the IVE "VARIABLES" heading is still empty.
- **factorial / Media 7:** the return animation is good. sc8.0 runs at 217 wpm.
- **neuron / Truth 9:** %g rounding and z ≤ 0 are covered. The explorer honestly prints `z = 1.11022e-16` at w2 = -1, b = -0.8, but never says why (`F/interact/neuron-explorer-z0-crop.png`).
- **neuron / Explanation 7:** strong panels, but there are two problems:
  - The fixed sentence under the sliders ("With w2 = -1 and b = -1, z prints as -0.2 and a is 0") sits under a panel showing z = 0.6 at load, and it never updates.
  - The recap repeats the opening sentence word for word.
- **neuron / Looks 8:** the film frames match Atlas closely. Two misses remain:
  - The wide still is a 2400 x 2800 poster with a code block and hashes.
  - The knob's ReLU plot has unequal axis scales, so the slope reads as about 0.4.
- **neuron / Interaction 8:** the sliders kill m.negterm directly (b = -1 gives a = 0, `F/interact/neuron-explorer-b-1.png`). The 1e-16 surprise is unexplained.
- **neuron / Media 8:** calm pace (103 to 161 wpm on most cues) and values shown when spoken. In the Add scene the gate dot appears about 13 s before the Gate narration.

**Builder's claim check:** "looks 7-8, interaction 7-8".
- Interaction: confirmed, and slightly understated (8 to 9).
- Looks: true for neuron (8), switch (7) and factorial (7), but not for one-byte (6). Looks is still the weakest lens.

## Remaining issues

**P0:** none.

**P1:** none in the lessons. One process item: all four reports are `canary-verified`, not full-suite `verified`. The B1 and B2 claims-suite runs must pass before these are called verified.

**P2:**
1. Wide stills are tall posters, not Atlas figures (round-17 X6, unfixed). Sizes are 2400 x 2658 / 2800 / 2810 / 3414. The hero figure is a third or less of the image, and sha256 footers sit on learner images (`F/stills/*-wide-*.png`).
2. Switch has no mechanism figure in any medium except the explorer's path diagram (`F/pages/switch-fallthrough-explorer-1440-dark.png`). The film is code plus a sentence.
3. Film type hierarchy is off.
   - Output values are smaller than their index digits in one-byte, factorial and neuron, and code is about 12 px at 1080p in neuron.
   - One-byte scene 1 and factorial recap leave large empty areas (`F/frames/one-byte-four-views/t007.03.png`, `F/frames/factorial-stack/t088.68.png`).
4. Factorial code-path arcs are still a tangle of overlapping curves (`F/frames/factorial-stack/t088.68.png`, `F/stills/factorial-stack-wide-dark.png`).
5. The neuron explorer has two problems:
   - The fixed caption contradicts the panel on load.
   - The `1.11022e-16` result is not explained. That is a great teaching moment ("z == 0 is false in double") that the lesson currently wastes.
6. On a phone the film is unreadable (round-17 X7, unfixed). The live panel mirrors the film well and the ask flow works at 390, but the video itself is about 360 px wide with about 3 px code (`F/interact/neuron-ive-ask-390-viewport.png`).
7. Narration voice and pace:
   - Hedges recur in the narration: "In this lesson's drawing" twice, "On this machine" 4 times, plus more on the pages.
   - The neuron recap repeats sc1.0 word for word.
   - 13 of 48 cues run above 195 wpm.
   - "unsigned car" remains in the TTS.
8. In the switch film, on-screen text repeats the narration word for word, so with IVE captions the same sentence shows up to three times.
9. One-byte never shows that a is 4 bytes (`00 00 00 42`), even though the narration now says it.

**P3:**
- The IVE still shows an empty caption box on load and while paused, an empty TRANSCRIPT heading at 0:00, and an empty VARIABLES heading (factorial, neuron).
- The film stays dark inside the light theme.
- At 390, after a pick, the "ON SCREEN NOW" label lags the film's scene title by one state (`F/interact/v/factorial-stack-ive-verdict-sc4-390.png`).
- The neuron Add scene shows the gate dot early.
- `postMessage(e, '*')` is unchanged.

## Is it world-class by the Atlas standard?

Not yet, but it is now close in places, and it is a real course.

The neuron film frames are at the Atlas level. The four explorers and the gated IVE are better than Atlas, which has no interaction at all. Truth is solid everywhere.

What keeps it from world-class is looks discipline outside neuron:
- the stills are tall posters with code blocks and hashes, where Atlas is one calm landscape figure;
- switch has no figure at all;
- the film type hierarchy is inverted in places, and empty halves remain;
- the narration still sounds like a compliance document ("on this machine", "in this lesson's drawing").

If Prax liked the Atlas baseline, he will like neuron. He will find switch and one-byte competent but plain.

## The 5 changes that would move it most

1. **Make every wide still a landscape hero figure like Atlas.** Aim for about 2240 x 870: the mechanism only, with no code block and no hashes. Keep the code, output and provenance for the portrait and for metadata.
2. **Give switch a figure.** Promote the explorer's path diagram (the labels in a column, the path line, "enters here", "no break", "leaves") to the hero of the film and the still.
3. **Run a film typography and layout pass.**
   - Output values should be larger than their indices.
   - Code stays a readable strip of only the relevant lines.
   - Fill the empty areas, or centre the figure when it is alone.
   - Replace the factorial arcs with per-frame line markers.
4. **Turn explorer surprises into lessons.**
   - Neuron: bind the caption to the slider state, and explain `1.11022e-16`: z is not exactly 0 in double, and ReLU still passes it.
   - One-byte: draw all 4 bytes of a so that "low byte" makes sense.
5. **Make the narration sound like a teacher.**
   - Cut the hedges, or say each one once per lesson.
   - Never repeat a sentence word for word.
   - Cap the pace at about 170 wpm.
   - Fix "unsigned char" in the lexicon.
   - At 390, offer an audio plus live-panel mode in place of the shrunken film.
