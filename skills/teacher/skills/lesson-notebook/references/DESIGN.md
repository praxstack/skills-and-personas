# Lesson notebook design system

Source: AskTheMove (askthemove.online), `praxstack/ChessLab` `site/DESIGN.md` at commit f3f8255, written for a chess coach. This file keeps its rules and swaps the chess specifics for any subject. Where the two differ, the AskTheMove file wins for AskTheMove and this one wins for the teacher.

## Personality

A patient coach sits next to you with a pencil and marks up your work in a lesson notebook. It looks like the subject at first glance (a circuit, a cell, a proof, a timeline) and like teaching at second glance: every mark says something.

References carried over: Chernev's *Logical Chess* pacing (one step, one reason, then the next), Rough Notation's mark vocabulary (underline, circle, box, highlight, bracket, cross-out) drawn in sequence, Bartosz Ciechanowski's explainers (one idea per figure, and the figure changes as the text explains it), Josh Comeau's warm small interactive figures, and Excalidraw's rough diagram language sitting next to crisp UI.

## Layout

One sheet of quad-ruled paper (26px squares) with a red double margin rule down the left.

- Desktop: contents on the left, the lesson in the middle (text 64ch or less, figure as wide as the column), the coach's margin notes on the right.
- Tablet: margin notes flow under the lesson.
- Phone: the margin rule moves to 8px from the edge, content gets 24px on the left and 16px on the right, and everything stacks: lesson, then contents, then notes. Figures may switch to a stacked layout (`viewBox` as a function of `narrow`).
- Section heads have no eyebrows on every section and no decorative numbers. Numbers appear only where order is real.

## Tokens

All colours are OKLCH custom properties on `:root` in `assets/notebook.css`. Components use tokens only.

| Token | Use | Contrast on paper |
| --- | --- | --- |
| `--paper` | the page | |
| `--paper-2` | machine printouts | |
| `--card` | form fields, figure sheets | |
| `--grid` | quad ruling, low alpha | decorative |
| `--margin` | margin rule | decorative only |
| `--ink` | printed text | about 16:1 |
| `--ink-2` | secondary text | about 9:1 |
| `--graphite` | pencil and machine text | about 7:1 |
| `--red` | the red pen: mistakes, marking | about 5.4:1 |
| `--blue` | ballpoint blue: explaining, the one primary action | about 7.7:1 |
| `--green` | a confirmed right answer (borders and marks, not body text) | check with visual-qa |
| `--highlight` | highlighter swipes behind key words | ink on it 13:1 |

The chalkboard variant (`data-board="chalk"`) redefines the same tokens on a dark green slate with chalk-white ink, so components don't change.

## Type

| Role | Face | Size |
| --- | --- | --- |
| Hero | Vollkorn 800 | clamp(2.2rem, 1.2rem + 3.6vw, 4rem) |
| Section | Vollkorn 750 | clamp(1.5rem, 1.1rem + 1.4vw, 2.2rem) |
| Body | Vollkorn 400 | 1.125rem, line height 1.6, 64ch or less |
| Coach note | Kalam 400 | 1.3rem, 1.06rem minimum |
| Machine | Courier Prime 400 | 0.94rem; labels 0.81rem caps, +0.06em tracking |

Numbers in tables and figures use lining, tabular figures (`lnum tnum`); Vollkorn's oldstyle figures stay in prose. Kalam's slant is handwriting, not emphasis, and never sets a heading.

## The pen (motion)

| Gesture | How | Timing |
| --- | --- | --- |
| Stroke | path with `pathLength="1"`, `stroke-dashoffset` 1 to 0, seeded wobble | about 1.1 ms per pixel, 260 to 1100 ms, easeInOutCubic |
| Pen lift | pause between marks | about 200 ms |
| Handwriting | each word revealed left to right with `clip-path` | 34 ms per character, extra after commas and full stops, 2.5 s cap per note |
| Highlighter | one left-to-right swipe | 520 ms ease-out |

- Draw once, when the figure first appears. Moving a slider redraws instantly, without the pen.
- Under reduced motion every drawing is shown finished and nothing autoplays.
- Frame-exact export uses `progress` on marks instead of timers, so a video frame is a pure function of time.

## Anti-patterns

- Childish sketch styling: wobbly borders everywhere, tape, doodle people, rainbow notes.
- Marks that say nothing.
- Long body copy in handwriting.
- Generic SaaS structure: three-card feature grids, icon tiles, an eyebrow on every section.
- Calm-wellness softness: gradients, blobs, glass, pastel pills.
- Invented numbers. Every figure in a figure comes from the lesson's model.
- Em dashes and strings of middle dots in copy.
- Colour as the only signal.
