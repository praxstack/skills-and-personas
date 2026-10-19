# Round 17: five-lens review of the four v2.1 lessons

Reviewer: Claude, read-only pass, 2026-10-18.
Lessons: switch-fallthrough, one-byte-four-views, factorial-stack, neuron. All four build reports say `verified`.
Reference: Neuron Atlas `production-v2/demo/exports/baseline.png`.

Evidence lives under `v2.1/.state/review17/` (written `S/` below):
- `S/stills/`: all 16 still PNGs, downscaled, plus portrait crops.
- `S/pages/`: explorer, Q&A and IVE from file:// at 390 and 1440, light and dark (48 shots, `info.json` has scroll widths and console errors), plus page text dumps.
- `S/interact/`: driven states (wrong answers, full reveals, switch n = 0/1/4/5, break toggle, stepper ends, IVE explore, question window, keyboard).
- `S/frames/`: 52 video frames at chapter midpoints and 0.25 s after each chapter start, contact sheets `sheet-<lesson>.jpg`, full-res checks.
- `S/asr/`: whisper base.en transcripts of every narration track.

What passed and needs no work: no console errors and no horizontal scroll at 390 or 1440 on any page (`S/pages/info.json`). file:// works everywhere, tracks load as blob URLs. Captions match the spoken audio to within whisper's 1 s resolution (switch checked line by line). Q&A gating works: Reveal stays disabled until "Check my answer" runs, and wrong answers name the misconception and the correcting claim. The switch explorer is correct for every n in 0..5 and for the break toggle, including no-match and the closing-brace end on n = 4 (`S/interact/switch-explorer-n*.png`). Focus rings are visible (`S/interact/kbd-zoom.png`). Every number in every medium matches the captured stdout.

No P0. Five distinct P1s: X1 and X2 below, factorial's missing n and r, stepper-only explorers (one-byte, factorial, neuron), and a mechanism panel shrunk to a corner in the one-byte and neuron videos.

---

## Cross-lesson findings (apply to all four)

**X1. P1, Interaction. The IVE never gates the prediction.**
Evidence: the IVE script has no pause at the question cue (`build/ive/index.html`, no `pause()` outside `enterExplore`). Driving factorial from 33.3 s, the film played to 39.3 s straight through the question and into the answer (`S/interact/factorial-stack-ive-after-question.png`). Switch did the same from 8.3 s to 14.3 s. The side panel shows only the prompt, with no options and no input. The silence between "Pause here and predict" and the answer is 3.8 s in switch (8.53 to 12.33) and factorial (33.10 to 36.90), and "Pause here and predict" is read at 220 wpm.
Fix: auto-pause on the question cue, show the same options as the Q&A, require a pick, then play. Hold the answer cue until the learner commits.

**X2. P1, Explanation. Chapter and layer titles leak answers while the question is open (AC-5.7).**
Evidence: one-byte asks what `printf("%f\n", (double)a)` prints, and the IVE chapter list and Q&A layer 3 both show "Six digits after the point" from the moment the page loads (`S/pages/one-byte-four-views-ive.txt`, `-qa.txt`). Switch shows "Fall through" under its open question, and the page title itself is "A missing break falls through".
Fix: hide titles of chapters and layers after the open question until it is answered, or give them neutral titles until then. Add a test that checks the rendered DOM, not only the VTT.

**X3. P2, Explanation. Q&A layers after the first are not questions.**
Evidence: every layer 2..n says "Predict this step, then reveal it." with no prompt (`S/interact/*-qa-wrong.png`). Factorial asks you to "predict" the Recap. The layer title often gives the answer ("Back to main", "Two integer views").
Fix: give each layer one bounded question (for example, "What does factorial(2) return?"), or label it as a walkthrough rather than a prediction.

**X4. P2, Looks and Media. Spoken-form text leaks into written media.**
Evidence: Q&A reveals and IVE captions read "Percent f prints...", "ub dot c", "factorial of 2", "1.2 minus 0.4 minus 0.2" (`S/interact/*-qa-all.png`, IVE caption band). For a C course, written text should keep `%f`, `ub.c`, `factorial(2)`.
Fix: captions and Q&A use the claim `text`. Only TTS uses `said`.

**X5. P2, Looks. Two visual identities and neither light theme is Atlas.**
Evidence: dark uses Nunito Sans and matches Atlas well (`S/stills/neuron-wide-dark.png`). Light uses Source Serif 4 titles, with Caveat handwriting for annotations, code identifiers and the misconception correction (`S/stills/switch-fallthrough-wide-light.png`, `factorial-stack-wide-light.png`). Handwritten `factorial(3)` reads as a decorative gimmick, and identifiers belong in mono.
Fix: one type system in both themes (Atlas sans plus mono), with only colour tokens changing.

**X6. P2, Looks. "Wide" stills are tall posters, not Atlas figures.**
Evidence: every wide PNG is 2400 x 2500 to 3270 (taller than wide). Portraits are 800 x 3170 to 4400 (about 1:5). Atlas is 2240 x 870. The hero figure (neuron panel, stack strip, value lanes) takes a third or less. The rest is a code block where every executed line is highlighted, so the highlight carries no information (neuron lines 5 to 15, one-byte lines 5 to 18). Sha256 provenance footers sit on learner-facing images.
Fix: make the wide still one landscape hero figure like Atlas. Move the code and the long caption to a second panel or the portrait. Put the hashes in metadata.

**X7. P2, Media. The film is unreadable on a phone.**
Evidence: `S/pages/v/switch-fallthrough-ive-390-light.png`. The 1920x1080 frame shrinks to about 360 px wide, and code drops to about 3 px. The side panel mirrors the state, which helps, but the film adds nothing at 390.
Fix: at narrow widths, collapse the film to audio plus captions over the live panel, or render a portrait cut.

**X8. P2, Explanation. The correct option is first in 3 of 4 lessons.**
Evidence: factorial "main got 6", one-byte "66.000000", neuron "0.6" are all option 1 (`S/pages/*-qa.txt`).
Fix: shuffle the options with a deterministic seed per lesson.

**X9. P2, Cards. Cards are thin and predictable.**
Evidence: each lesson has 3 or 4 cards (`build/cards/*.md`). Every misconception card is "True or false? <wrong belief>" with the answer always False. One-byte card 1's "Why" pastes six claims (bits, %d, %u, %c) to explain a %f answer. There is no card for the UB rule, which is the most exam-relevant fact in that lesson.
Fix: add rule cards (cloze or short answer) for UB, switch no-match, and ReLU at negative z. Trim each "Why" to the one relevant claim. Mix true and false statements.

**X10. P3, Interaction.** The IVE has no keyboard shortcuts. Space with focus on the body does nothing (`S/interact` log). On load there is an empty caption box, an empty "TRANSCRIPT" heading and an empty "VARIABLES" heading (factorial and neuron) (`S/pages/v/factorial-stack-ive-1440-dark.png`). The IVE emits `postMessage(e, '*')` with session ids to any parent. That is low risk but sloppy.

**X11. P3, Media.** Reduced motion is honoured in CSS (one `prefers-reduced-motion` block per page, no keyframes), but nothing offers a still-frame path through the film. The posters `ive/posters/sc*.jpg` exist and could drive one.

---

## switch-fallthrough

**Truth**
- P2. `with_break.c` still falls through: case 1 has no break. gcc-16 warns at line 7 (`lesson.json` diagnostics, p2). The scene is called "Add the missing break" but the fixed program still has one. The compare panel in the still starts at line 8, so the learner never sees it (`S/stills/switch-fallthrough-wide-light.png`). Fix: add a break to case 1 in p2, or show the warning and say why it doesn't matter for n = 2.
- P3. Clang's diagnostics are empty because `-Wimplicit-fallthrough` is not in clang's `-Wall`. That warning flag is the practical defence, and it is worth one line.
- Everything else is precise: match rule, no-match with no default (explorer n = 0 and n = 5), end of body on n = 4, and "smallest enclosing switch or loop".

**Explanation**
- P2. The distractors miss the commonest wrong answer, which is that fallthrough runs to the end: "two, three, four, done". Add it as a misconception. It tests whether the learner sees that the break on line 12 stops it.
- P2. On-screen text in the video repeats the narration word for word (`S/frames/sheet-switch-fallthrough.jpg`, right column). With IVE captions as well, the same sentence appears three times. Fix: on-screen text should show the mechanism tag ("enters here", "no break"), not the sentence.
- Good: the explorer's path diagram and the per-n "What happens" text are the best explanation in the set (`S/pages/v/switch-fallthrough-explorer-1440-dark.png`). The video doesn't use that path diagram. It should.

**Looks**
- Dark still and video are clean and close to Atlas. Light theme: see X5. The "no break" pill sits next to case 3 when it refers to the gap after line 9. Move it onto the gap.
- P3. The toggle label "break after case 2 off" mixes sans and mono and reads oddly.

**Interaction**
- Strong. The domain is n = 0..5 plus a break toggle. The IVE live controls lock until 0:17 and then explain why ("These controls unlock after the film answers its prediction") (`S/interact/switch-fallthrough-ive-explore0.png`). Weakness: X1.

**Media**
- P2. The pace is fast: 214, 220, 236 and 225 wpm on four of eleven cues (`build/video/timing.json`). Target about 165.
- ASR confirms clean pronunciation ("N equal to 2", "fallthrough.c").

## one-byte-four-views

**Truth**
- P2. The %f lane says "CONVERTS TO 0x4050800000000000, PRINTS 66.000000" (`S/stills/one-byte-four-views-wide-dark.png`, `S/frames/full-byte-t79.png`). The cast converts to the value 66.0. The hex is its representation. Labelling the bit pattern as the conversion result blurs value and bits, which is the very misconception this lesson fights. Fix: "converts to 66.0, stored as 0x4050800000000000".
- P3. The panel shows 8 bits as "LOW BYTE" of a 4-byte int and never shows `00 00 00 42` or sizeof(int) = 4. A GATE learner could leave thinking `a` is one byte. The directory name "one-byte-four-views" points the same way.
- P3. Misconception m.samebits says "printf reinterprets the same bits", but the question is about the cast form. The belief behind "0.000000" is really "the cast reinterprets the bits". Reword it.
- The double bits, %c via unsigned char, %u conversion and UB claim (7.21.6.1p9) are all correct.

**Explanation**
- P1 (see X2). "Six digits after the point" gives away the predict answer on the IVE and Q&A.
- P2. Scene order and states disagree. sc5 "Two integer views" uses state s2 (line 13 highlighted, the %f line), and s1 (%d and %u) is never a scene of its own. The cast scene already reveals 66, 66 and 66.000000 together (`S/frames/one-byte-four-views-07-t33.30.jpg`). The Q&A shows %d and %u outputs in the cast layer, two layers before "Two integer views" (`S/interact/one-byte-four-views-qa-all.png`). Fix: d/u, then cast, then f, then c, then bits, with one state per scene.
- P2. The UB point is only stated, never shown. Showing the clang `-Wformat` warning from ub.c would make "compiled for its warning" concrete.

**Looks**
- P1. In the video, the mechanism panel (value plus lanes) is small and pushed into the top right. Lane text is about 16 px at 1080p, while code is about 26 px and output is the largest text in the frame (`S/frames/full-byte-t79.png`, `sheet-one-byte-four-views.jpg`). The hierarchy is upside down. Fix: the lanes are the hero, and code shrinks to the 5 relevant lines.
- P3. The still's lede and the %f lane caption are the same sentence.

**Interaction**
- P1 (shared with factorial and neuron). The explorer is a 5-step stepper with nothing to change (`S/pages/v/one-byte-four-views-explorer-1440-dark.png`). The obvious knob is `a`: with a in {66, 200, -1, 321}, %c wraps, `(unsigned)-1` prints 4294967295, and the low byte changes. That knob is the lesson.

**Media**
- P2. Sync: scene 7 starts at 62.4 s, but state s4 (line 18, output line 7 and the UB lane) appears only at about 75 s, under the last sentence. "Without the cast ... undefined" (68.9 to 75.7) plays while no UB lane is on screen (`S/frames/one-byte-four-views-13-t71.98.jpg` against `full-byte-t79.png`).
- P2. Pronunciation: whisper hears "ub dot c" as "up.c" (`S/asr/one-byte-four-views.txt`). Say "U B dot C". "unsigned char" is said as "unsigned car". That is acceptable but worth a lexicon entry.

## factorial-stack

**Truth**
- Sound. 6.2.4p6 and 6.8.6.4p3 are used correctly, and "C does not name a stack" is said honestly. P3: "TOP FIRST" is clear, but the portrait still lays frames out left to right while the narration says "waits under the new one" (`S/stills/fact-pl.png`). Keep one orientation.

**Explanation**
- P1. The lesson's thesis is "each call gets its own n and its own r", and no medium ever shows n or r in a frame. `trace[*].state.vars` is `{}` in every state (`lesson.json`). Frames read "factorial(2) WAITING" (`S/frames/full-factorial-t45.png`), and the IVE "VARIABLES" heading is empty. The returned value never visibly lands in the caller's r (`r = 2 * 1`). The arrow points at the frame, not at a slot. Fix: every frame shows `n = 3, r = ?`. On return, the value flies into the caller's `r = n * ▢`, which then resolves to 6.
- P2. The predict question "What is the last line?" can be answered from knowing 3! = 6, without the stack. Ask instead for line 4 of the output, or for the order of the seven lines. Interleaving is what the stack explains.
- P2. The misconception box under "The 1 from the base case comes back to main" corrects with the generic c.unwind text, which doesn't say "main gets 6, not 1".

**Looks**
- P2. The code-path arcs on the left of the code turn into a tangle of five overlapping curves (`S/stills/factorial-stack-wide-dark.png`, `S/frames/full-factorial-t45.png`). For recursion, a single path line misleads. Drop it and use per-frame line markers.
- P2. The wide still leaves the right half empty beside OUTPUT. The stack strip at the top is the best figure in the set, but its type is small.

**Interaction**
- P1 (shared). The explorer is a 7-step stepper, and n can't be changed. Steps highlight the whole executed path (lines 4 to 9 plus 13 at step 4), so the current line is lost (`S/interact/factorial-explorer-step4.png`). Fix: an n of 1 to 5 knob and a distinct current-line marker. Prev and Next disable correctly at both ends, and arrow keys move the step radios.

**Media**
- Pace is fine apart from the predict line. The returns arrow animates in the film, which is good. Recap shows only "main RUNNING" while narrating growth and shrinkage. Use the step strip from the still as the recap frame.

## neuron

**Truth**
- P2. The double values are not exactly what's drawn. `0.8 * 1.5` is 1.2000000000000002 and z is 0.6000000000000001 (checked in Python with the same IEEE doubles). The still labels "SUM 0.6" and "OUTPUT 0.6" as if exact. c.toy says the program prints with %g, but never says %g rounds to 6 significant digits. For a C learner that one sentence is worth adding: `z == 0.6` is false here.
- P3. "ReLU passes a positive z ... turns a negative z into 0" leaves out z = 0. Say "max(0, z)" or "z ≤ 0 gives 0".

**Explanation**
- Strongest visual in the set. The multiply, follow-the-endpoint, gate panel is a faithful port of Atlas (`S/stills/neuron-wide-dark.png`).
- P2. Predict replaces the whole neuron panel with a mostly empty question box (`S/frames/neuron-04-t36.78.jpg`). Keep the panel visible and overlay the question.

**Looks**
- P1. In the video the neuron panel is about a third of the frame width, and its labels are about 11 px at 1080p. The output box is the largest element (`S/frames/sheet-neuron.jpg`, `neuron-check.jpg`). Atlas fills the frame with the figure. Fix: the panel spans the full width, and code and output become a thin strip or move to the IVE side panel.
- P3. The a-axis has no tick values, where Atlas shows 1.5. "BIAS / ADDED DIRECTLY" uses label styling for both lines, while inputs show the expression in mono.

**Interaction**
- P1. Four fixed steps, and no slider for w2, b or x. The misconception m.negterm ("ReLU outputs 0 whenever any term is negative") is exactly what a slider kills: drag b to -1.0 and watch z cross 0 and the dot run onto the flat part.

**Media**
- P2. Multiply scene: "0.8 times 1.5 is plus 1.2 ..." plays from 17.1 to 28.0 s, but +1.2 and -0.4 appear only with the second sentence at about 28 s (`S/frames/neuron-03-t26.63.jpg` against `neuron-check-t33.jpg`). Values are spoken about 10 s before they're shown. The add bars also appear during Multiply, ahead of the Add scene.
- P3. "ReLU" is spoken "ray-loo". "REL-oo" is more common. The pace (116 to 174 wpm) is the best of the four.

---

## Top 10 fixes, ranked by quality gained

1. Gate the IVE prediction: pause on the question cue, show the options, require a pick, then play the answer (X1).
2. Stop answer leaks: no future chapter or layer titles until the question is answered, with a DOM-level test (X2).
3. Factorial: show `n` and `r` in every frame and animate the return value into the caller's `r` in all media.
4. Give every explorer one real knob: neuron w2 and b sliders, factorial n of 1 to 5, one-byte a in {66, 200, -1, 321}.
5. Make the mechanism the hero of the video frame (neuron and one-byte): figure at 60% or more of the frame, code as a narrow strip, output smaller.
6. Replace "Predict this step, then reveal it" with one real question per Q&A layer, and use written text (`%f`, `factorial(2)`) in Q&A and captions.
7. One-byte: one state per scene in a sensible order. Show the UB lane when the UB sentence plays. Relabel "CONVERTS TO <bits>" as value plus representation.
8. One visual identity in both themes (drop Caveat and the serif light theme). Make the wide still an Atlas-like landscape hero. Move hashes out of learner images.
9. Cards: add rule and cloze cards (printf UB, switch no-match, ReLU at negative z). Trim "Why" to one claim. Mix true and false.
10. Pacing and sync: about 165 wpm, a slower predict line with at least 8 s of thinking time when ungated. Fix "ub dot c". Show values when they are spoken (neuron multiply, one-byte scene 7). Fix `with_break.c` case 1.

## Scores (1 to 10)

| Lesson | Truth | Explanation | Looks | Interaction | Media |
|---|---|---|---|---|---|
| switch-fallthrough | 8 | 7 | 6 | 7 | 6 |
| one-byte-four-views | 7 | 5 | 4 | 4 | 5 |
| factorial-stack | 8 | 5 | 6 | 4 | 6 |
| neuron | 7 | 6 | 6 | 3 | 6 |

Justifications:
- **switch / Truth 8:** every claim matches C17, but the "fixed" program still falls through from case 1.
- **switch / Explanation 7:** the explorer path diagram and per-n text teach the mechanism. The video only narrates it and the Q&A layers are filler.
- **switch / Looks 6:** dark is clean and Atlas-like. Light handwriting and the tall poster still pull it down.
- **switch / Interaction 7:** a real value domain and an honest unlock rule. The film still doesn't stop for the prediction.
- **switch / Media 6:** captions sync well, but four cues run at 214 to 236 wpm with a 3.8 s predict gap.
- **one-byte / Truth 7:** the facts are right, but "converts to <bit pattern>" blurs value and representation in the lesson about exactly that.
- **one-byte / Explanation 5:** states and scenes are out of order, %d and %u are revealed early, and the predict answer leaks through a title.
- **one-byte / Looks 4:** the value lanes, the actual figure, are small type in a corner. The code block dominates.
- **one-byte / Interaction 4:** a stepper with nothing to vary, when the value of `a` is the whole topic.
- **one-byte / Media 5:** the UB lane appears about 7 s after the UB sentence, and "ub dot c" is heard as "up.c".
- **factorial / Truth 8:** precise standard citations and an honest "C has no stack" framing. Only the stack orientation is inconsistent.
- **factorial / Explanation 5:** the lesson promises per-call n and r and never shows them. The predict question is solvable without the stack.
- **factorial / Looks 6:** good stack strip and return arrow, spoiled by arc tangles and empty half-pages.
- **factorial / Interaction 4:** a 7-step stepper, n is fixed, and the current line is hidden in a block highlight.
- **factorial / Media 6:** fine pacing and a good return animation, but the recap frame shows nothing of the growth it narrates.
- **neuron / Truth 7:** the arithmetic is right as printed, but %g rounding hides 0.6000000000000001 and ReLU at z = 0 is left out.
- **neuron / Explanation 6:** the Atlas panel shows multiply, add and gate well. Predict hides it, and nothing lets you test the misconception.
- **neuron / Looks 6:** the dark still is the closest thing to Atlas here (8 on its own). The video shrinks the same figure to a third of the frame.
- **neuron / Interaction 3:** four fixed steps on the one topic that most needs sliders.
- **neuron / Media 6:** the calmest narration, but the multiply values are spoken about 10 s before they appear.
