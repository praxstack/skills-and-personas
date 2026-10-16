# Remotion guide

How to build and render an explainer with the starter project in `assets/template/`. The pipeline around it
(voice, music, mix, QA, delivery) is in `SKILL.md` and the shared references.

## Contents

1. [Setup](#1-setup)
2. [Project anatomy](#2-project-anatomy)
3. [Timing API](#3-timing-api)
4. [Kit catalogue](#4-kit-catalogue)
5. [Recipes](#5-recipes)
6. [Rendering](#6-rendering)
7. [Gotchas](#7-gotchas)
8. [Laptop differences](#8-laptop-differences)
9. [License](#9-license)
10. [Themes](#10-themes)

## 1. Setup

Pinned versions (exact, in `package.json` and `package-lock.json`):

| Package | Version |
|---|---|
| `remotion`, `@remotion/cli`, `@remotion/renderer` | 4.0.533 |
| `react`, `react-dom` | 19.3.0 |
| `@fontsource/inter`, `instrument-serif`, `jetbrains-mono`, `bangers` | 5.3.0 |
| Node | 22 (22.22.0 here) |
| ffmpeg / ffprobe | any recent build (6.1.1 here) |

Install the project (from the video project folder):

```bash
test -d source || cp -r $SKILL/assets/template source
test -d source/node_modules || (cd source && npm ci --no-audit --no-fund)    # 14-18 s here, 258 packages
python3 $S/voice.py --project . --emit source/src/timing.json                # the timing the scenes read
```

Browser:

- `render_remotion.mjs` uses, in order: `--browser <path>`, then `$REMOTION_BROWSER_EXECUTABLE`, then the
  newest `/opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell`. Here that is
  `/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell`.
- With none of these, Remotion downloads its own headless shell on first use. That is fine on a laptop and
  blocked in some sandboxes.
- Never run `playwright install`.

The raw command the script wraps, for reference:

```bash
cd source && npx remotion render build/bundle Film out.mp4 --frames=0-899 --concurrency=2 \
  --browser-executable=/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell \
  --codec=h264 --crf=18 --pixel-format=yuv420p --color-space=bt709 --muted --image-format=jpeg
```

Live preview on a laptop: `cd source && npx remotion studio src/index.ts` (a scrubber; edits hot-reload). In a
sandbox, review with stills instead.

## 2. Project anatomy

```
source/
  package.json, package-lock.json   pinned deps; "type": "module"
  remotion.config.ts                jpeg frames, h264, crf 18, yuv420p, bt709, muted (studio/CLI defaults)
  tsconfig.json                     editor help only; nothing type-checks the render
  public/grain.png                  static film grain tile (Finish)
  src/
    index.ts, Root.tsx              registers <Composition id="Film">; durationInFrames = round(total * fps)
    Film.tsx                        the layer stack (keep): Backdrop > World(Subject, SceneWorld) > Dust >
                                    SceneHud > ChapterTag/Progress > ChapterStings > Captions > Finish
    timing.json                     written by voice.py --emit (ships with the mini film's timing)
    lib/timing.ts                   the clock: TIMING, f(), fPhrase(), fThink(), chapterStart() ...
    lib/motion.ts                   ease, pop (springs), span, bump, track (keyframes), steps, drift, shake
    lib/span.tsx                    <Span from to> + useF(): Sequences that keep absolute frames
    kit/                            reusable components (section 4); change the look in kit/tokens.ts
    kit/theme.ts                    the theme file (section 10): a stub meaning `original`, or an emitted theme
    scenes/                         THE FILM: replace these for a new topic
      data.ts                       facts: graph layout (MAP), places (PLACE), input text, code
      director.ts                   the subject + camera, cue by cue (graphAt, placeAt, cameraAt, BEAT)
      Problem.tsx ... Code.tsx      one file per chapter: a ...World part and a ...Hud part
      index.tsx                     wires the chapter parts into Subject / SceneWorld / SceneHud
```

What to edit for a new film:

1. `data.ts`: the subject's nodes and edges (world units in a `W x H` box), its `PLACE` per chapter, the input
   text and the code.
2. `director.ts`: what the subject does per line.
3. One chapter file per chapter.
4. `tokens.ts` only for a new palette.

If the subject is not a graph (an array, a grid, a tree), write a new kit component in the same style, and keep
it out of `scenes/`: a pure state object built per frame from cues, plus a component that draws it with depth
(shadow, gradient, glow on what is active).

## 3. Timing API

`src/timing.json` holds:

- `total`, `fps`, `width`, `height`
- `chapters[] {n, name, start, end}`
- `lines[] {id, chapter, scene, start, voiceAt, voiceDur, think, end, cap, say}`

All times are in seconds. `lib/timing.ts` turns them into frames:

| Helper | Frame of |
|---|---|
| `f('p3')`, `f('p3', 0.4)` | the voice starting line p3 (plus 0.4 s) |
| `fSaid('q1')` | the voice finishing q1 (its `think` pause starts here) |
| `fThink('q1')` | `[start, end]` of q1's think pause |
| `fPhrase('p4', 'seven hundred', -0.2)` | the voice reaching that phrase. It is estimated from the character position in `say` and is good to about 0.2 s. It throws if the phrase is missing. |
| `fStart('p1')`, `fEnd('p1')` | the line's whole slot: lead-in, voice, pad and think |
| `chapterStart(2)`, `chapterEnd(2)` | chapter boundaries (the sting plays in the gap between `chapterEnd(1)` and `chapterStart(2)`; start new content at `chapterStart` or later) |
| `sec(0.6)` | a duration in frames |
| `L.p3`, `TIMING`, `lineAt(fr)`, `chapterAt(fr)` | raw access |

Rules:

- **No literal frame or second counts in scenes.** Durations via `sec()` are fine.
- **An unknown id throws** with the list of valid ids, so script edits fail loudly.
- **`TOTAL_FRAMES = round(TIMING.total * fps)`.** `Root.tsx` and the render script share this formula, so
  the length always matches the voice (the render gate allows +/- 1 s).
- **Mount by time.** `<Span from={fStart('q2')} to={fEnd('a2')}>` mounts its children only then. Inside it,
  `useF()` returns the absolute frame, so `f('a2')` keeps working. Plain `<Sequence>` would restart the frame
  at 0.

Motion helpers (`lib/motion.ts`). All of them take absolute frames:

| Helper | Use |
|---|---|
| `ease(fr, start, dur, EASE.out)` | 0 to 1 eased. `EASE.inOut` for moves, `EASE.in` for exits |
| `pop(fr, start, SPRING.pop)` | 0 to 1 spring with overshoot, for appearances. `SPRING.calm` settles without overshoot |
| `span(fr, from, to)`, `bump(fr, at, hold)` | fade in and out; a highlight that lands, holds and fades |
| `track(fr, [[frame, {x, y}, dur?], ...])` | continuous keyframes: each key moves from wherever the value is (camera, places) |
| `steps(fr, [[frame, value], ...])` | discrete value plus `pop` since it changed (focus index) |
| `drift`, `shake`, `rand` | slow idle motion, a hit shake, deterministic noise |

## 4. Kit catalogue

All positions are px in the 1920x1080 frame. The safe area (`SAFE`) is x 96 to 1824 and y 96 to 880: text stays
96 px from every edge, also at the extreme frame of a camera push. The caption band is y 900 to 984; its text is
bottom-anchored just above `SAFE.bottom` (984), so a two-line caption grows upward. Components take `fr` (from `useF()`) unless they read
TIMING themselves.

Text size and contrast (checked by `legibility.py`, see quality-bar.md): `SIZE` is title 128, headline 84, body 44,
caption 40, code 30, label 30, small 30. `SIZE.small` is the smallest the kit draws (chips, weight tags, table
headers, notes); never go under it, so a camera pull-back or the checker's tolerance cannot take text below the
26 px floor. Words in lowercase only (x-height) read smaller than their font size: use caps or 32 px and up.
Secondary text uses `C.muted` or `C.faint` (both at least 4.5:1 on the stage and on panels); de-emphasise with
colour, weight or a highlight bar, never with opacity under about 0.8.

**Chrome and type**

- **`tokens.ts`**
  - `C`: the palette. `bg`, `ink`, `muted` (secondary text), `faint` (tertiary: line numbers, used entries;
    still at least 5:1 on panels), `accent` (orange, the thing being looked at), `accentText` (the accent for
    small text on an accent-tinted fill), `amber`, `amberHi` (the outline and tint of the decoder's active entry,
    lighter so the text on it keeps 4.5:1), `mint` (valid/answer), `rose` (illegal/wrong), `cyan`,
    `violet`, `burst`.
  - `FONT`: `sans` Inter, `serif` Instrument Serif, `mono` JetBrains Mono, `comic` Bangers.
  - `SIZE`, `SAFE`, `NO_LIGA`, `SHADOW`, `glow()`.
- **`Panel`, `Label`, `Chip`, `Dots`, `ArrowGlyph`, `BigO`, `RichText`** (`kit/Panel.tsx`)
  - `<Chip color={C.mint} size={34}>k stops</Chip>` is a pill.
  - `<BigO s="O(n^(k+1))" />` draws real superscripts (0.7 em): set BigO at 38 px or more so the exponent
    stays above the 26 px floor.
  - `<RichText text="0 → 1 costs 700, O(k·E)" />` tints numbers, sets `[arrays]` in mono and draws `→` as an
    SVG arrow.
- **`TitleCard`**
  - `<TitleCard fr from={fStart('i1')} to={fEnd('i1')} kicker="LeetCode 787 · medium" lines={['Cheapest Flights', 'Within K Stops']} accent="K" />`
  - Words spring in, a rule grows and a plane loops over the title.
- **`ChapterStings`, `ChapterTag`, `ChapterProgress`** (`kit/Chapter.tsx`): no props; driven by
  `TIMING.chapters`.
  - Stings: a comic halftone band ("02 · BRUTE FORCE") that lives only in the gap between chapters
    (`stingTimes(n)`): it sweeps in when the previous chapter ends, holds, and wipes away the frame before
    `chapterStart(n)`; then the corner tag pops in. So a chapter's content must be gone by its `fEnd` (last line)
    and the next chapter's content must start at `chapterStart(n)` or later, never under the band. The band only
    sweeps over empty ground: the subject fades out at the previous chapter's last word, moves while invisible
    (`gapMove(n, PLACE.x)` as a `placeAt` key) and fades back in at its new place after the band has left
    (`subjectShown(fr)`, multiplied into `placeAt`'s opacity).
- **`Captions`**: no props. The bottom band shows the current line's `cap` from 0.12 s before its voice, wraps
  to two balanced lines, and draws numbers and `→` via RichText.
- **`Backdrop`, `Dust`, `Finish`**: the depth and light layer.
  - `Backdrop`: drifting warm and cool key lights, plus a dot grid with 0.35x camera parallax.
  - `Dust`: particles at 1.3x parallax.
  - `Finish`: static grain and a vignette.

**Camera**

- `camera(fr, [[frame, {x, y, z, r}, dur?], ...], driftAmp = 7)` returns a `Cam`. Partial keys are filled from
  `CAM_HOME`.
- `<World cam>` transforms the world layer.
- `toScreen(cam, worldPoint)` anchors a HUD item (a burst) on a world object.

**Subject: `Graph`** (`kit/Graph.tsx`)

- **Data:** `GraphData {W, H, R, nodes: [{id, x, y, valueSide?, badgeSide?}], edges: [{id, from, to, w, bend}]}`.
- **Place:** `Place {x, y, s, o}` puts the graph in the world. `nodeWorld`, `edgeTagWorld` and
  `graphToWorld` convert positions.
- **State:** `GraphState` is built fresh each frame and chains:
  - `.node(id)`, `.edge(id)`, `.nodes(ids, fn)`, `.edges(ids, fn)`: raw state. A node has `show`; an edge has
    `draw` (0..1) and `tag`.
  - `.dimExcept(v, keepNodes, keepEdges)`: focus.
  - `.ring(id, color, o)`, `.badge(id, 'START', color, o)`, `.value(id, '700', color, pop, o)`,
    `.pulse(id, fr, at, color)`.
  - `.route(edgeIds, p, color, {token: 'plane' | 'dot', o})` and
    `.routeAt(fr, edgeIds, start, dur, color, opts)`: a highlighted path drawn over time, with a travelling
    token.
  - `.fire(edgeId, fr, start, dur, color)`: a pulse runs along the edge (a relaxation).
  - `.strike(edgeId, v)`: a rose X on the edge (illegal or blocked).
- **Draw:** `<Graph data={MAP} st={g} place={placeAt(fr)} uid="map" />` draws floor shadows, edges that draw on
  (the arrowhead appears at the end), glow layers, weight tags, and shaded nodes with badges and value pills.
- **Text keeps its screen size:** weight tags, badges and value pills never draw under `minPx` (default
  `SIZE.small`, 30 px) whatever `place.s` is, and grow their pills to fit. A small placement (a thumbnail next to
  code or a table) therefore needs room: about `s >= 0.5` for a 1000-unit-wide graph.

**Explaining pieces**

- **`InputDecoder`**: the raw input as text. Tagged entries `{{id|text}}` light up (`hl`), fly into the
  subject (`fly`), get notes (`notes`) and fade once used (`done`). `inputLayout(spec, x, y)` gives entry
  boxes for aiming. `fromEnd: true` on a flight starts the copy just past the end of its row (fading in), so it
  never crosses the rest of the row on its way out.
- **`QuestionCard`**
  - `<QuestionCard fr label="Question 1" text="..." at={f('q1')} think={fThink('q1')} settle={f('a1')} out={fEnd('a1')} />`
  - The countdown ring runs exactly the think pause; the card settles smaller for the answer.
  - `CountdownRing` can also be used on its own.
- **`Tree`**: a recursion tree.
  - Nodes `{id, parent, label, sub, at, tone: 'ok' | 'cut' | 'win' | 'dim', toneAt}` appear level by level.
  - `limit={{depth, label, at}}` draws the k+1 line; cut nodes get an X badge.
- **`DPTable`**: rows of keyed cells. A `CellKey` is `[frame, value, color?]`; the cell pops and glows when it
  changes. Props: `cols`, `rows: [{label, sub?, at, cells, color?}]`, `cw`, `ch`, `labelW`, `labelFs`
  (row label size, default 34; sub-labels are 28 px caps), `rowGap`, `fs` (cell text, default 38).
  `dpLayout(...).cell(r, c)` gives a cell centre (for arrows and bursts).
- **`Ladder`**: complexity rungs.
  - Each rung is `{name, time: 'O(k·E)', space, cost: 0..1, color, at, note}`, climbing upward as approaches
    improve.
  - `focus={[[frame, i]]}` highlights a rung; `pick={{i, at}}` stamps "INTERVIEW PICK".
- **`CodePanel`**
  - `<CodePanel fr x y code={CPP} fs={30} lh={36} title="solution.cpp" badge="k + 1 rounds" reveal={[[first, last, frame]]} active={[[frame, first, last]]} pulse={[[frame, line]]} />`
  - Code is 30 to 36 px (`fs`); 18 lines at 30/36 fit beside a table. Ligatures are off and C++/Python are
    coloured. The active-line highlight glides between ranges; the active lines turn bold and the others dim
    to `CODE_DIM` (0.8 opacity, still above 4.5:1; line numbers do not dim). `codeLayout()` gives line
    positions.
- **`Burst`**
  - `<Burst fr at text="700!" x y size={240} rot={-8} seed={3} hold={50} />`
  - A comic star with an offset shadow, halftone, speed lines, overshoot and wobble. Text with digits uses
    Inter 900 italic, other text uses Bangers.
  - Use 3 to 5 per film, on events.

## 5. Recipes

Every recipe below is live in the mini film; the file is named so you can copy from it.

**Decode an input** (`Problem.tsx`, `director.ts` p1/p2)

- When the voice says "Each flight", each entry highlights in the decoder.
- A clone of its price flies to the edge's tag position (`fly: {id: 'f0', char: 5, len: 3, to: edgeTagWorld(MAP, PLACE.decode, 'e01')}`).
- In `graphAt` the edge's `draw` runs from that flight's start, so the edge grows as the number lands.
- `src`/`dst` fly to their nodes and the nodes get START/END badges.
- When the decode ends, the panel slides out and `placeAt` re-centres the graph.

**Trace a route** (`director.ts` p4)

- `g.routeAt(fr, ['e01', 'e13'], BEAT.routeStart(), BEAT.routeDur, C.accent, {token: 'plane'})`: the path
  lights edge by edge while a plane flies it, paced to the voice listing the cities ("zero, one, three").
  `routeAt` eases in-out over legs + 0.35, so with two legs the token lands at about 47% and 67% of `dur`
  (`BEAT.leg1()`, `BEAT.leg2()`).
- A fare receipt in the HUD fills in leg by leg (`StopsAndFare`); its total lands on the spoken number
  (`BEAT.totalAt()`, the "seven hundred" of "costs seven hundred"), not seconds later.
- At the answer, `routeAt` again in `C.mint`, with `g.value('3', '700', C.mint, pop(fr, answer))` and
  `g.pulse('3', ...)`.

**Reject an illegal route** (`director.ts` b1, `Brute.tsx`)

- Draw the route in `C.rose` and `g.strike('e23', pop(fr, t))`.
- In the tree, set `tone: 'cut', toneAt: t` on the node past the limit.
- Optionally add a `Burst text="NOPE!"`.
- Dim it afterwards (`o` falls) instead of deleting it, so the viewer sees what was ruled out.

**A think countdown** (`Intuition.tsx`)

- `QuestionCard` with `think={fThink('q1')}` and `settle={f('a1')}`.
- Keep the subject visible under the card (`PLACE.question` puts the graph low and small) and light the hint
  on it during the pause.

**A DP row update** (`Intuition.tsx` a2, `Code.tsx` dry run)

- Cells as key lists, e.g. `[[0, '∞'], [f('a2', 0.6), '100', C.mint]]`.
- Draw arrows from the source cell to the target with `dpLayout().cell()`.
- In `graphAt`, write the same value onto the subject (`g.value`) and fire the edge, so the table and the
  picture agree.

**Code walkthrough synced to the narration** (`Code.tsx`)

- Line ranges are named in `data.ts` (`CODE_LINE.relax = [11, 12]`).
- The `active` keys come from the narration: `[fPhrase('c1', 'Round zero') + sec(0.35), ...CODE_LINE.relax]`.
- A `pulse` flashes the line whose effect lands in the table at that moment.

**Camera moves** (`director.ts` `cameraAt`)

- Push in on the answer, hold, and pull back home before the next line (`[fEnd('p4', -0.55), CAM_HOME, sec(0.7)]`).
- Things that must stay put (chips, receipts, question cards, bursts) go in a `...Hud` part.
- Things that should feel physical (subject, tables, code) go in the world.
- Keep `z` at 1.1 or below unless the World content is centred, and preview the extreme frame as a still.

**Move the persistent subject between chapters** (`director.ts` `placeAt`)

- One `track` over `PLACE` entries. Inside a chapter, key moves to lines (`[fStart('q2'), PLACE.question2, sec(0.9)]`).
- Between chapters use `gapMove(n, PLACE.ladder)`: the subject fades out at the last word, moves while it is
  invisible under the sting, and fades back in at the new place once the band is gone (`subjectShown` in
  `placeAt`). Within a chapter the graph never disappears; it slides, shrinks and re-centres.

**Plan before coding.** Write one row per script line: the line id, what changes on screen, and the cue
(`f`, `fPhrase`, or `fThink`). Every line needs at least one change, which the quality bar requires.

## 6. Rendering

All commands run from the project folder. `$S` is the skill's `scripts/`.

| Command | What it does |
|---|---|
| `node $S/render_remotion.mjs --project . --stills lines` | one still per line (65% into its voice) -> `stills/` |
| `... --stills chapters` / `busy` / `15.9,55.4` / `f:300,900` | per chapter / 8 longest lines / seconds / frames |
| `... --bench 3 --concurrency N` | renders 3 s from 45% in; prints fps and the full-film estimate; writes `build/bench.json` |
| `... --concurrency N --max-minutes 100` | the full render (resumable), see below |
| `--segment 30`, `--crf 18`, `--comp Film`, `--force`, `--keep-segments`, `--scale 0.5` (stills), `--browser <path>` | options |

What a full render does:

1. Installs `node_modules` if missing.
2. Bundles `src/` into `build/bundle`. It re-bundles only when `src/`, `public/`, `package.json` or the
   config change; a hash is stamped in `build/bundle/.stamp`.
3. Checks that `source/src/timing.json` has the same hash as the project's `timing.json`.
4. Splits the film into 30 s frame ranges, recorded in `build/segments/manifest.json` as
   `{"segments": [{"from", "to", "done", "fps", ...}]}`. Each range renders to a `.part.mp4`. Its frame count
   is verified before it is renamed and marked `done`. A re-run skips done segments. A changed source or timing
   starts over, because old segments would not match.
5. Before each segment it checks the budget. If the next segment will not fit in `--max-minutes`, it prints
   `Stopping cleanly` and exits with code 3; run the same command again. After each segment it prints the fps
   and the ETA.
6. Concatenates with ffmpeg `-c copy`, which is lossless because every segment has identical settings, into
   `build/silent.mp4` with `+faststart`. It verifies the frame count, then deletes the segment files and keeps
   the manifest for the gate.

Speeds measured on this 4-core sandbox (1920x1080, 30 fps):

| Run | Speed |
|---|---|
| bake-off, 7.4 min film, concurrency 4 | about 25 min wall (about 9 fps) |
| mini film, concurrency 2, light load | 3.9 to 6.5 fps |
| mini film, concurrency 2, heavy load (load avg 30-60) | 1.9 fps bench; 1.8 to 2.3 fps full render (earlier 62 s cut: 15.5 min, resumed once) |
| stills | about 20 s to bundle, then 3 to 10 s per still (2 in parallel; 14 stills in about 1 min under load) |

Plan with the bench number. A 6-minute film at 5 fps is about 36 minutes: one background run with
`--max-minutes 100` is enough. Above about 12 minutes of film at low fps, expect two runs. More concurrency
than cores is slower, and each worker is a Chromium tab using 300 to 500 MB.

## 7. Gotchas

- **yuvj420p output.**
  - **Symptom:** ffprobe shows `yuvj420p` (full range) although `--pixel-format=yuv420p` was passed. Players
    and the gate expect `yuv420p`, and some show washed-out or crushed blacks.
  - **Fix:** `--color-space=bt709` (in the script and `remotion.config.ts`) makes Remotion write tv-range
    yuv420p. If a concat still comes out yuvj420p, the script re-encodes once with
    `scale=in_range=pc:out_range=tv`.
- **Ligatures in code.**
  - **Symptom:** in JetBrains Mono, `!=`, `<=`, `->`, `++` and `==` render as single joined glyphs.
  - **Fix:** `fontFeatureSettings: '"calt" 0, "liga" 0'` (`NO_LIGA`) together with
    `fontVariantLigatures: 'none'`. It is set on the root in `Film.tsx` and again in `CodePanel`.
- **Fonts.**
  - **Symptom:** the first frames use a fallback font, or Google Fonts requests hang (blocked here).
  - **Fix:** `@fontsource/*` imports in `kit/fonts.ts`. `useFontsReady()` calls `delayRender` until
    `document.fonts.load()` resolves for every face in `FACES`. A new face needs its import and a `FACES` entry.
- **Missing glyphs.**
  - **Symptom:** `→`, `∞` and `≤` are missing from the npm latin subsets, so they render in DejaVu or as boxes.
  - **Fix:** `RichText` draws `→` as SVG; the stacks end in DejaVu Sans / DejaVu Sans Mono, which have `∞` and
    `≤`.
- **Bangers 7 looks like 1.**
  - **Symptom:** "700!" reads as "100!".
  - **Fix:** `Burst` switches text with digits to Inter 900 italic. Do the same for any numeral in the comic
    font.
- **TypeScript is stripped, never checked.**
  - **Symptom:** a misspelt prop or wrong type renders nothing, with no error.
  - **Fix:** review stills. `npx tsc` is only a weak check here (no React types, `strict` off).
  - **Node 22 type stripping:** node scripts can import `.ts` files such as `data.ts`. Only erasable syntax
    works: no `enum`, no namespaces, no parameter properties, and `import type` for types. JSON needs
    `with {type: 'json'}` and `.tsx` cannot be imported.
- **Slow renders.**
  - **Symptom:** a 7.4-minute film took about 25 minutes at concurrency 4, and minutes more under load.
  - **Fix:** bench first, render in the background with `--max-minutes`, and re-run to resume. Avoid
    `filter: blur()`, `backdrop-filter` and large animated SVG filters. The kit glows with box-shadow and a few
    small SVG blurs.
- **Animated grain.**
  - **Symptom:** per-frame noise raised the bitrate to 33 Mbps and slowed encoding.
  - **Fix:** a static grain tile with `mix-blend-mode: overlay` (`Finish`); movement comes from the lights and
    dust.
- **Camera crops.**
  - **Symptom:** after a push-in, chips near the frame edge are cut off or slide into the caption band.
  - **Fix:** put them in the HUD, and push gently (z up to 1.1) or toward the centre of mass. Check the
    extreme frame with a still.
- **`<Sequence>` frame reset.**
  - **Symptom:** inside a Sequence, cues fire late or never.
  - **Fix:** use `<Span>` with `useF()` (absolute frames).
- **No box-sizing reset.**
  - **Symptom:** padded panels overflow their width.
  - **Fix:** `Film.tsx` sets `box-sizing: border-box` globally.
- **Stale timing.**
  - **Symptom:** the render script refuses with "is not the project's timing.json".
  - **Fix:** re-run `voice.py --emit source/src/timing.json` after any script change.

## 8. Laptop differences

- **Browser:** with no `/opt/pw-browsers`, Remotion downloads a headless shell to its cache on first render.
  Use `REMOTION_BROWSER_EXECUTABLE=/path/to/chrome` to point at an installed one.
- **Speed:** the render is CPU-bound and scales with real cores up to about the core count. A laptop with
  more and faster cores than this 4-core sandbox renders several times faster. Run `--bench` with
  `--concurrency` set to its core count, and plan from that number.
- **Studio:** `npx remotion studio src/index.ts` gives a scrubbable live preview, the fastest way to tune
  timing by eye.
- **Fonts:** identical everywhere, because they are bundled from npm. Only the DejaVu fallbacks for `∞` and `≤`
  differ, and they are replaced by the OS's own symbol font.
- **Voice:** `edge_voice_swap.py` (shared) re-voices the delivered MP4 with edge-tts on a laptop. Re-timing the
  animation to a new voice means re-running voice.py and rendering again.
- **Windows:** use WSL or Git Bash for the shell commands. Remotion itself runs natively.

## 9. License

Remotion is not MIT. It uses the Remotion License:

- **Free:** individuals, non-profits, and for-profit organisations of up to 3 people.
- **Paid:** larger companies need a company license (see remotion.dev/license) before using it commercially.

Tell the person this when the video is for an employer.

## 10. Themes

The film is drawn in its original palette (`original`, the dark-editorial look above) unless a theme file says
otherwise. The 30 registry themes and their tokens are in `themes.md`.

- **Theme file:** `source/src/kit/theme.ts`. The template ships a stub (`export const THEME = null`) that means
  `original`: `tokens.ts` then uses its original values unchanged.
- **Emit:** `python3 $S/theme.py emit <id> --format ts --out source/src/kit/theme.ts`, after
  `python3 $S/vstate.py set theme=<id>`. Re-shoot the stills and run `legibility.py`; the render script re-bundles
  on its own because the source changed. To go back, copy the stub from `$SKILL/assets/template/src/kit/theme.ts`.
- **One place:** `tokens.ts` imports `THEME` and maps it onto the kit's roles. Kit components and scenes use only
  `C`, `S` and the helpers below, never a hex value, so a new scene stays themeable if it does the same.

| Kit role | Theme token |
|---|---|
| `C.bg`, `C.bgLift` | `bg`, `bg2` (stage gradient) |
| `C.ink`, `C.muted`, `C.faint` | `text`, `muted`, `dim` |
| `C.line`, `C.line2` | `line`, `line2` |
| `C.panel`, `C.panelTop`; `S.*` cards (code, question, recap, rung, fare, tag box, pills) | `panel`, `panel2` (opaque) |
| `C.accent`, `C.accentText` | `accent`, `accentInk` |
| `C.amber`, `C.amberHi`, `C.burst` | `gold` |
| `C.mint`, `C.rose`, `C.cyan`, `C.violet` | `good`, `bad`, `cool`, `violet` |
| sting band `accent -> S.stingMid -> STING_END` | `accent -> warm -> gold` when one text colour clears 4.6:1 on all of it, else solid `accent` with `onAccent` |
| caption band, sting shade | `deep` at the original alphas |
| vignette | `deep`, drawn on the ground (in `Backdrop`) instead of over everything, so it never washes out text |
| backdrop key lights (`keyLights(n)`) | `lights`, a pair per chapter, cross-faded in the chapter gap (light themes: mixed toward white) |
| shadows (`sh(a)`, `SHADOW`) | `shadow` (light themes at 0.3 of the alpha) |
| code syntax (`CODE_INK`) | `violetInk`, `coolInk`, `goldInk`, `goodInk`, `warmInk`, `text`, `muted`, `dim` |

Helpers (all the identity on `original`, so the starter look is unchanged):

- Text roles keep a margin over theme.py's flat-surface targets: `C.muted` 6.2:1, `C.faint` 5.3:1 and every ink
  5.3:1 on `bg`, `bg2`, `deep`, `panel` and `panel2` (same hue, lightness moved), because thin, scaled or
  tinted-over glyphs measure lower in the stills.
- `ink(fill)`: text or a thin stroke in a hue (`<hue>Ink`). Kit components apply it to the colour you pass, so
  scenes keep passing fills: `<Chip color={C.mint}>`, `g.value('3', '700', C.mint, ...)`.
- `on(fill)`: text on a filled shape of that hue (`on<Hue>`): badges, notes, flying chips, stamps.
- `mark(fill)`: a ring, route, arrow or border that must show on the ground: the fill moved to 3:1 against `bg`
  (only pale fills on light themes change).
- `inkOn(colour, surface)`: text on a tinted surface (active code line, hot DP cell, focused rung, lit decoder
  entry) lifted to 4.6:1 there; the solved inks have no margin for tints.
- `hlEdge(fill)`: the outline of a highlight hugging text (decoder entry, code pulse); none under a theme (tint only).
- `halo(colour, blur, spread?, alphaHex?)` and `glow()`: a coloured glow; on light themes a soft tinted shadow.
  `GLOW_K` scales the SVG blur glows (0.3 on light themes).

Under any theme the decoder highlights lose their glow, the code pulse flashes at half strength (`S.pulseA`) and the
weight-tag pills are taller (`S.tagH`), so no outline or haze sits inside a text's measuring box. Light themes also switch the grain to `multiply` (brightened, so it only adds dark specks), the burst to light
letters on a dark outline, and code lines no longer step back to 0.8 opacity under any theme (`CODE_DIM` 1):
focus is the bar, the bold weight and the accent line number.

