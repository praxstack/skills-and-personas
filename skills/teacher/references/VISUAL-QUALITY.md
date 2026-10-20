# Visual quality

A visual is done when it teaches the claim, reads on a phone, works in both themes, and says in words what it shows. `skills/visual-qa` measures what can be measured. The rest is looking.

## The bar

- **True.** Every number comes from the model or a cited source. Labels match the explanation word for word where it matters.
- **Focused.** One claim per figure. The first thing the eye lands on is the thing the lesson is about.
- **Legible.** Body text 4.5:1, large text 3:1, nothing under 12px, figure text at least 11px after scaling, on desktop and phone.
- **Calm.** Motion only where the change is the point. Reduced motion shows the end state, and nothing is lost.
- **Accessible.** A text alternative that says what the figure shows now, with its numbers; captions and a transcript on anything with sound; colour never the only signal; every control reachable by keyboard.
- **Robust.** No console errors, no sideways scroll, works without storage, works offline once loaded.

## The routine

```sh
node skills/visual-qa/scripts/check_page.mjs page.html --out shots/ [--eval "window.__explorable.check()"]
node skills/explorable/scripts/test_lesson.mjs page.html          # explorables: every step, every path
python3 skills/visual-qa/scripts/check_video.py clip.mp4 --sheet sheet.png
```

Then open `shots/desktop-light.png`, `shots/phone-light.png` and the contact sheet and answer the four questions in `skills/visual-qa/SKILL.md`. Fix, rebuild, re-run.

## Bugs these checks have already caught

Real failures found while building the bundled examples. Look for them first:

- Figure text shrank to about 6px on phones because a wide `viewBox` was squeezed into a narrow column. Fix: a narrow layout (`viewBox` as a function of `narrow`) and no height cap on phones.
- A handwritten note ran past the figure's edge and was clipped. Fix: shorter notes; coach notes are short by rule.
- A screenshot taken mid-pen-stroke looked broken. The checker now waits for every animation to finish.
- Arrowheads floated free of their shafts because `vector-effect: non-scaling-stroke` broke `pathLength` dashes in Chromium. Removed.
- Vollkorn's oldstyle figures made "1.0" read like "I.O" in a figure. Figures now use lining numerals.
- A weight label sat on top of its own line. Labels go beside what they name, never on it.

## Worked mechanism example

[Collecting flags before changing the denominator](MECHANISM-STORYBOARD-EXAMPLE.md)
shows stable segment identities, explicit scale changes, a presentation-only
phase parameter, and different compositions for an opening scene and complete
still. It records the current export hooks and motion limits without adding a
new evaluator or acceptance threshold.
