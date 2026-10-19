---
name: explorable
description: Build an interactive lesson where one executable model drives every view, a figure the learner manipulates, live readouts, optional practice questions, a narrated film, margin notes and a report back to the teacher. Complete explanation first, with immediate controls; attempt-first only for explicitly requested practice. One hint after a miss, taught directly after a second, and a "still confused?" button that swaps in a different explanation and records what was tried. Use for any "teach me X" where something can be varied, in any subject. Builds to one self-contained HTML file in the lesson-notebook style.
---

# Explorable

The learner sees the complete mechanism and explanation, then can manipulate the figure or try optional practice. Every number on screen comes from one model function, so the figure, the questions, the film and the checks can't disagree.

## Build one

1. Quantitative lessons use a checked pure function from parameters to state. Qualitative lessons use a sourced selection/context model. Do not invent measurements for a language or history lesson.
2. Write `checks`: facts the model must satisfy (limits, symmetries, a known value). They run in the test.
3. Draw the figure from the state with `kit` (below). Draw the claim, not decoration.
4. Write 3 to 7 steps. Each step: one idea, which controls are live, what to look for, an optional check, a margin note, and at least one other way to explain it.
5. Build, test, look:

```sh
python3 scripts/build.py assets/examples/seasons.lesson.js -o seasons.html        # one file, opens anywhere
node scripts/test_lesson.mjs seasons.html                                  # drives every step in Chromium
node scripts/check_code.mjs lesson.js --include course.model.js            # structural check; does not execute authored code
node scripts/check_code.mjs lesson.js --include course.model.js --trust-authored-code  # only after reviewing/trusting every input
node ../visual-qa/scripts/check_page.mjs seasons.html --eval "window.__explorable.check()"
```

Use `--fragment` when publishing to a host that wraps pages (Claude artifacts). Open the screenshots before showing the learner anything.

`test_lesson.mjs`, `check_page.mjs`, narration, and `bundle_lesson.mjs` load the
lesson in Chromium and execute its JavaScript. Run them only for a lesson and
includes you have reviewed and chosen to trust. Chromium is part of the render
pipeline, not a hostile-code sandbox; use the [bundled checker sandbox](references/SANDBOX.md) or an external restricted environment for
third-party material.

## The lesson file

```js
window.LESSON = {
  id: "seasons-v1", title: "Why seasons happen", subtitle: "...", subject: "Earth science", level: "...",
  params: { day: { label: "Date", min: 1, max: 365, step: 1, value: 172, fmt: (v) => "21 Jun" } },
  model: (p) => ({ elev: ... }),                       // pure; the single source of truth
  readouts: (s, p) => [["noon sun", `${s.elev.toFixed(0)}°`]],
  figure: {
    viewBox: (narrow) => (narrow ? "0 0 340 690" : "0 0 700 360"),  // or a string
    label: (s, p) => "A sentence describing what the figure shows right now",
    draw(g, s, p, kit) { /* kit.el, kit.mark, kit.hand, kit.ink, kit.seed, kit.group, kit.narrow */ },
  },
  steps: [{
    id /* optional, stable */, title, say /* HTML */, set: { day: 172 }, controls: ["day"], lookFor: "...",
    ask: { kind: "choice", q, options: [...], answer: 2, hint, why },   // or kind: "number", answer: (p, s) => n, tol, unit
    // options show in a shuffled order (fixed per question; all-number options stay sorted; keepOrder: true opts out).
    // Add needsFigure: true when q can't be answered without the figure (a course's "Quiz me" leaves it out).
    note: "the margin note this step earns",
    alts: [{ label: "A torch on a table", say: "...", set: { ... } }],
  }],
  film: [{ chapter, say, set }],     // optional; defaults to one scene per step
  misconceptions: [...], deeper: [...], checks: [{ name, test: (model) => bool }],
};
```

`kit.mark(ink.arrow(...), { tone: "red" })` and `kit.hand(x, y, "text", { tone: "blue" })` draw in the coach's hand; the pen animates them when a step opens and redraws instantly when a slider moves. `kit.group("translate(...)")` returns a kit for a sub-panel, which is how a figure rearranges itself when `kit.narrow` is true.

### More lesson fields

- `hook`: HTML shown above step 1 under "Why this mattered": the stakes or the story (who needed this, what broke without it). Short.
- `code`: `{ title, cpp, python, stdin(params), expect(params), cases: [params...] }`. Mark lines with a trailing `//@id` (C++) or `#@id` (Python). A step with `line: "id"` (or `line: (p, s) => "id"`) shows the panel with that line lit. The Code tab shows the whole program; Python runs in the browser (Pyodide, in a Web Worker with a Stop button and a 10 s limit, so an endless loop never freezes the lesson) where the host allows it, and every panel shows what the model says the program prints for the current inputs. The default `check_code.mjs` invocation is structural and reports code as unverified. Only after reviewing every lesson/include, pass `--trust-authored-code` to compile and run both languages. For third-party executable examples, use `--sandbox --sandbox-image sha256:...`; see [sandbox setup](references/SANDBOX.md).
- `ask: { kind: "explain", q, model, points: [...] }`: the learner writes the idea in their own words first, then sees the teacher's version and ticks the key points they covered. The text goes into the report so the teacher can correct it.
- Shared course code: put the model in one file that sets `window.Something` and build with `--include course.model.js` (also for `check_code.mjs`).
- `figure.narrowText`: text scale on narrow screens (default 1). Raise it until `visual-qa` stops flagging figure text under 11px.
- Readout labels are set in capitals. When case carries meaning (`|a|` against `|A|`), give the row a third item: `["|a|", "5", { keepCase: true }]`. Long values wrap on phones.

Every page also has: "Or see it as a film / code" under "Still confused?", a "Questions to chase" list in the margin that goes into the report, Board (auto/paper/chalk) and Sound buttons.

## What the page does

- Layout: contents, lesson, margin notes, kept apart, with Film and "Notes and report" as their own tabs. Progress, answers and notes stay ephemeral unless the learner checks "Remember progress on this device". Withdrawing it removes this page's local progress and consent key; it cannot erase exported or externally copied records. The page works when storage is blocked. Saved progress is matched to steps by key (the step's `id`, else its title and question), so a step that is inserted, removed or moved never inherits another step's answers; give steps an `id` if you expect to reword them.
- Questions: Next is always available in the default explanation style. Optional practice lives in a closed detail after the explanation. Only explicitly requested practice locks Next until the question is resolved or shown. A miss gets the hint. A second miss, or "Show me", teaches it directly. Every attempt is recorded.
- "Still confused? Try another way": cycles through `alts`, changing the representation, example or analogy, and records which ones were tried.
- Film: the same figure, eased between each scene's parameters, with captions, play, pause, scrub, chapters, speed and a transcript (the human-sounding voice is in the narrated video: `scripts/narrate.py`).
- The end isn't a score. "Where to next?" offers: got it, go deeper, another example, explain it differently, practise. Then a plain-text report (steps, misses, explanations tried, notes, choice) the learner copies back to the teacher, so the next session fits them.
- Chalkboard toggle, keyboard control of the film, reduced motion, phone layout.

## Rules

- Every visual explains something. The step's `say` states the claim, `lookFor` says where to look, and the figure's label says it in words.
- Explain first. Attempt-first applies only to `style: "practice-first"` or `?practice=1` after an explicit learner request. `?practice=0` exits it.
- One idea per step. If a step needs two sliders and three paragraphs, split it.
- Numbers come from the model, never typed into the figure by hand.
- `alts` must change one thing (the example, the representation, the granularity or the analogy), not repeat the same explanation louder.
- Phone first: test the narrow layout. `visual-qa` fails figure text under 11px as drawn.

Examples: `assets/examples/seasons.lesson.js` (Earth science, no code).

## Six formats from one lesson

Add `sources: [{title, url, note}]` and an honest `limits` statement to source-grounded lessons. After reviewing the executable lesson, build the explorer, render narrated video, then use `node scripts/bundle_lesson.mjs explorer.html --out output --video lesson.mp4 --timing lesson.timing.json`. The exporter produces editable still/PNG, Q&A, cards, static fallback and interactive video. Real video and matching timing/captions are required for the video explorer; missing media is not silently labelled complete.
