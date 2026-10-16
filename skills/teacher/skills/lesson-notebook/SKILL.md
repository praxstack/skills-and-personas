---
name: lesson-notebook
description: The teacher's default look for every visual it makes, a hand-drawn whiteboard lesson. Quad-ruled paper, a red margin rule, three voices (printed book serif, machine printout, the coach's handwriting) and a pen that draws marks and writes notes live. Use it for explorables, diagrams, animations and video frames unless the learner or project asks for another style. Includes the CSS tokens, OFL fonts, seeded hand-drawn stroke geometry (ink.js), the pen animator (pen.js) and a bundler that makes single-file pages.
---

# Lesson notebook

A patient coach sits next to the learner with a pencil and marks up a lesson notebook. The page is printed matter. The coach writes over it, step by step, in blue ink and red pen. Every mark says something.

The system is adapted from the AskTheMove site (praxstack/ChessLab, `site/DESIGN.md`, commit f3f8255), generalized from chess to any subject. Full rules: [references/DESIGN.md](references/DESIGN.md).

## Use it by default

- Explorables, concept animations and explained diagrams already load it. Hand-written pages link `assets/notebook.css` or go through `scripts/bundle.py`.
- Switch away only when the learner asks, the host project has its own design system (use theirs), or the subject has a stronger native look (a terminal session, a real photo, a map).
- `data-board="chalk"` on `<html>` gives the chalkboard variant for night study. Same voices, dark slate.

## The three voices

| Voice | Says | Face | Class |
| --- | --- | --- | --- |
| The book | explanations, headings, the question | Vollkorn | default body, `.t-book` in SVG |
| The machine | computed numbers, code output, readouts, labels | Courier Prime | `.nb-print`, `.nb-label`, `.t-print` |
| The coach | notes, hints, arrows, circles, ticks, "look for" | Kalam | `.nb-hand`, `.nb-note`, `.t-hand` |

Colour carries a role, never meaning alone: blue ink explains, red pen marks a mistake or the thing to look at, graphite pencil does the working, the highlighter marks the key word, green confirms. Every mark is also said in words.

## Files

- `assets/notebook.css`: tokens, paper, voices, buttons, fields, SVG classes (`f-*` fills, `s-*` strokes, `tone-*` ink).
- `assets/ink.js`: seeded hand-drawn geometry (line, arrow, curvedArrow, loop, ring, underline, tick, cross, bracket, swipe). Deterministic: the same seed draws the same wobble every time.
- `assets/pen.js`: `drawIn(root)` draws every `[data-pen]` mark and writes every `[data-write]` note in document order; `inkMark(parent, paths, { tone, progress })` and `handText(...)` build them. Reduced motion shows everything finished.
- `assets/fonts/`: Vollkorn, Kalam, Courier Prime (Latin subsets, SIL OFL 1.1, see `OFL.txt`).
- `scripts/bundle.py`: inline CSS, fonts and modules into one HTML file (`--fragment` for hosts that wrap pages, like Claude artifacts).

## Drawing a figure

```js
import { arrow, loop } from "./ink.js";
import { inkMark, handText, drawIn } from "./pen.js";
inkMark(svg, arrow([[40, 120], [220, 80]], { seed: 7, head: 10 }), { tone: "red" });
inkMark(svg, [loop(260, 80, 30, 18, { seed: 8 })], { tone: "blue" });
handText(svg, 300, 70, "this is the bottleneck", { tone: "red" });
drawIn(svg); // the pen draws them in order
```

## Rules that keep it from turning childish

- The book is printed and crisp. Only the coach's marks are hand-drawn. No wobbly border on every box, no tape, no doodle people, no rainbow sticky notes.
- A coach note is about 60 words at most. Long text stays in the book voice.
- Every circle, arrow or underline points at a claim the text makes. A mark that says nothing gets deleted.
- Motion is the pen only: strokes and handwriting. Nothing loops, bounces or floats.
- Text is 4.5:1 against its background, figure text is at least 11px as drawn, and every figure has a text alternative. `visual-qa` checks all of it.
