# Motion Canvas guide

How to build and render a narrated explainer with Motion Canvas 3.17.2 in this pipeline. The starter project
(`assets/template/`, copied to `<project>/source/`) already implements the mini film end to end; a new film
replaces `src/scenes/` and keeps `src/kit/`.

## Contents

1. Setup
2. How rendering works (and why not the editor's Render button)
3. Project anatomy
4. Timing API
5. Kit catalogue
6. Recipes
7. Rendering
8. Gotchas (symptom, fix)
9. Laptop differences
10. Themes

## 1. Setup

```bash
python3 $S/mc.py setup --project .     # copies assets/template to source/ (if absent), then npm ci
```

- Install time measured here: 9 s with an empty npm cache, 5 s warm; `node_modules` is about 290 MB (66 MB of it
  is the ffmpeg binary the editor's own Render button uses). Node 18+ (tested with 22).
- Pinned (exact, with `package-lock.json`): `@motion-canvas/core`, `2d`, `ui`, `vite-plugin`, `ffmpeg` 3.17.2;
  `vite` 6.4.4 (the plugin's peer range says 4.x or 5.x, so the template's `.npmrc` sets
  `legacy-peer-deps`); `typescript` 5.9.3; `@codemirror/language` 6.12.4, `@lezer/cpp` 1.1.6, `@lezer/highlight`
  1.2.5 (code colours); `@fontsource/inter` 5.3.0, `@fontsource/jetbrains-mono` 5.3.0, `@fontsource/bangers` 5.2.8.
- Never `npm i @motion-canvas/...` unpinned or `npm create @motion-canvas` (interactive): it pulls Vite 7 and the
  plugin build hangs. Add a package only with an exact version (`npm i -E pkg@x.y.z`), then rerun `mc.py setup`.
- Browser: `capture.mjs` uses the template's `playwright-core` 1.56.1 (installed by `npm ci`) and Chromium at
  `/opt/pw-browsers/chromium`. Override with `CHROMIUM=/path/to/chrome`. Never run `playwright install` here.
- Fonts come from `@fontsource` (bundled into the build); Google Fonts is blocked and not needed.

## 2. How rendering works

Motion Canvas has no render CLI, and its editor Render button needs a person (or a scripted click) and runs
about 7 minutes per minute of film. The template instead ships a headless page, `render.html` + `src/render.ts`:
it builds the project with the same `Renderer` class the Render button uses, then draws any frame on demand
(`playback.seek` / `progress` + `stage.render`). It implements the `capture.mjs` page contract (`READY`, `TOTAL`,
`renderFrame(t)`, `CAPTURE_SELECTOR = '#mc'`), so the shared capturer does segments, resume, the time budget,
stills and the benchmark. Checked here: 16 consecutive frames plus forward and backward seeks were
pixel-identical (max difference 0) to the editor's PNG image-sequence export of the same frames.

`mc.py build` runs `tsc --noEmit` and `vite build` into `source/dist/`. It skips the build when nothing in
`source/` changed, because any change to `dist/` restarts the render segments.

## 3. Project anatomy

```
source/
  package.json, package-lock.json   pinned versions (do not loosen)
  vite.config.ts      Motion Canvas plugin; builds render.html; serves ../voice/narration.wav to the editor
  render.html         headless render page (do not edit)
  tsconfig.json       strict-ish TS; `npx tsc --noEmit -p .` is the typecheck
  src/
    timing.ts         written by voice.py --emit (TIMING: lines, chapters, total, fps). Never edit by hand
    project.ts        fonts (@fontsource + document.fonts.load), makeProject({experimentalFeatures: true})
    project.meta      size 1920x1080, fps 30, background, editor exporter settings
    render.ts         the harness behind render.html (do not edit)
    kit/              reusable pieces (below). Keep; extend with new pieces when a film needs them
      theme.ts        palette C, fonts F, sizes S, FRAME (safe area 96 px, caption band 180 px, header line), C++ colours
      clock.ts        timing helpers (waitUntilLine, waitUntilCue, ...), background()
      world.tsx       createWorld: layers, camera, backdrop with parallax, vignette, grain, film clock
      chrome.tsx      captions, chapter cards, chapter tag, show title, progress bar (all from TIMING)
      graph.tsx       Graph (persistent subject) and Route (token flights, reject)
      decoder.tsx     InputPanel (raw input whose entries fly into the subject)
      cards.tsx       panel(), QuestionCard (countdown ring), TitleCard
      code.tsx        CodePanel (syntax colours, ligatures off, active-line bar, context lines recede to grey)
      table.tsx       Table (DP rows, dry runs)
      ladder.tsx      Ladder (complexity rungs, the pick)
      tree.tsx        BranchFan (brute-force explosion)
      fx.tsx          pop, appear, vanish, bump, Chip, Counter, ripple, burst, stamp, floatUp, drawArrow
    scenes/           THE FILM (replace for a new film)
      data.ts         the subject's layout, input rows, ladder rungs, the C++ and line numbers
      film.tsx        one scene: builds world + subject + chrome, runs the chapters in order, ends at TOTAL
      film-context.ts the Film bag passed to chapters ({w, g, cam, input, chrome})
      ch0-intro.tsx ... ch5-code.tsx   one generator per chapter
```

One scene for the whole film is deliberate: the subject persists across chapters and the camera moves it,
instead of scene cuts rebuilding it. Chapters are plain generator functions run with `yield*` in order.

## 4. Timing API

`timing.ts` exports `TIMING` (`total`, `fps`, `chapters[{n,name,start,end}]`, `lines[{id, chapter, start,
voiceAt, voiceDur, think, end, cap, say}]`). Import helpers from `../kit`:

| Helper | Meaning |
|---|---|
| `yield* waitUntilLine('p3', off?)` | the voice starts line p3 (+ off s) |
| `yield* waitUntilCue('p4', 'The answer', off?)` | the voice reaches that phrase (estimated from its position in `say`; throws if absent) |
| `yield* waitUntilThink('q1')` | the voice of q1 ended: the think pause starts |
| `yield* waitUntilLineEnd('a2', -0.05)` | just before the slot of a2 ends (clean-up time) |
| `yield* waitUntilLineStart('i1')` | the slot starts (before the lead-in silence) |
| `yield* waitUntilTime(chapter(3).start - 0.6)` | absolute time, for camera moves under a chapter card |
| `line(id)`, `chapter(n)`, `voiceAt`, `voiceEnd`, `room(id)` | raw numbers (`line('q1').think` = seconds) |
| `background(task)` | run a task without waiting, safe anywhere (see Gotchas) |

Rules that keep a film in sync:

- Wait with `yield*` only on cues. Start a beat's animations with `yield all(...)` / `yield chain(...)`
  (spawned, non-blocking) so a long animation can never push the next cue late.
- A cue that is reached late prints `[timing] late by X s at <cue>` once; `mc.py stills` lists them. Fix them
  all before rendering.
- `film.tsx` ends with `yield* waitUntilTime(TOTAL)`. The harness warns if the scene length differs from
  `TIMING.total` by more than 2 frames.
- Chapter cards are drawn by `Chrome` in the silence between chapters, mostly in the chapter's first second
  (voice.py's `chapter_lead`): about 1.2 s, gone 0.4 s before the first word. Move the camera for a chapter at
  `chapter(n).start - 0.6` so the move happens under the card, and bring the chapter's first panel in as the
  card leaves, `yield* waitUntilTime(cardOut(n))` (half way through its exit; `cardWindow(n)` has all the
  times), never under the card, or the card slides out over content already on screen.
- The card is opaque and moves in CLEAR (0.3 s) after the previous chapter's last word. A chapter's final
  clean-up therefore starts at `voiceEnd(last line)` and finishes within 0.25 s; nothing from the old chapter is
  left under the band. The subject (the world layer) fades out at that last word and fades back in (0.3 s) as the
  band leaves, so the chapter's camera move happens under the card while the subject is hidden, and the subject
  is on screen when the chapter's voice starts (qa.py `chapter-entry`).

## 5. Kit catalogue

Layers from `createWorld(view)`: `w.world` (moved by the camera: the subject), `w.hud` (screen-fixed panels),
`w.top` (bursts, flyers), `w.chrome` (captions, cards). `w.camera`, `w.time` (film-time signal).

| Piece | Signature | Example |
|---|---|---|
| Camera | `cam.frame(focus, anchor, zoom, d)`, `to({focus, anchor, zoom}, d)`, `pushIn(focus, zoom, d)`, `shake(s, d)`, `set({...})` | `yield cam.frame(g.center(), [-500, 40], 0.84, 1.2)` puts the graph centre at screen (-500, 40) |
| Graph | `new Graph({nodes: [{id, x, y, label?, valueSide?}], edges: [{from, to, w?, bend?, pillSide?}], radius?})` | `w.world.add(g.root); yield* g.popNodes(); yield* g.drawEdges()` |
| Graph state | `highlightNode(id, color)`, `resetNode`, `focusOn(ids)`, `unfocus`, `highlightEdge`, `resetAll`, `setValue(id, text, color)`, `labels(on)` | `yield g.setValue(3, '700', C.good)` |
| Graph motion | `fire(from, to, color, d, rippleTarget?)`, `ripple(id, color)`, `tag(id, text, color, side)` returns a Chip | `yield g.fire(0, 1, C.good, 0.45)` |
| Route | `g.route(path, color, 'plane'|'dot'|'none')`: `fly(d, onArrive?, keepToken?)`, `reject(at?, label?)`, `recolor`, `dim`, `fade`, `showAll` | `const r = g.route([0, 1, 3]); yield* r.fly(2)` |
| InputPanel | `new InputPanel({position, rows: [{name, parts, list?} or {assign: [[name, value]]}], title})`: `showRow(i)`, `mark(row, i, color)`, `fly(row, i, layer, target, d)`, `flyAll` | `yield* inp.fly(0, 2, w.top, g.edge(2, 0).pill)` |
| QuestionCard | `new QuestionCard({position, width})`: `ask(n, text)`, `countdown(seconds)`, `answer(text, color)`, `hide()` | `yield* q.countdown(line('q1').think)` |
| TitleCard | `new TitleCard({kicker, lines, accent?, subtitle?})`: `in(d, arc)`, `out(d)` | plane flies a dashed arc under the title |
| Chrome | `new Chrome(w, {show, cardFor?, label?, captions?})`: `run()` | `yield chrome.run()` once in film.tsx |
| CodePanel | `new CodePanel({position, width, height, code, title?, fontSize?})` (fontSize 30 by default; at 30 px a line holds 56 characters in 1090 px, so wrap long signatures): `show`, `reveal(n, d)`, `focus(line or [a, b])`, `clearFocus`, `hide` | `yield cp.focus(CODE.relax)` |
| Table | `new Table({position, cols, rows: [{label, values?}], cellW?, cellH?, labelW?, headLabel?})`: `showHeader`, `showRow(r)`, `copyRow(a, b)`, `set(r, c, v, color)`, `flash`, `mark`, `markRow`, `hide` | `yield* t.copyRow(0, 1)` |
| Ladder | `new Ladder({position, rungs: [{name, time, space, cost 0..1, note?}], width?, rungH?})`: `show(i)`, `pick(i, label?)` (gold outline; the star tab hangs below the last rung, above any other), `hide` | `yield lad.pick(2)` |
| BranchFan | `new BranchFan({position, branch, depth, width, height, rootLabel?})`: `grow(d, onLevel?)`, `prune(leaves, color?)`, `hide` | `yield fan.grow(1.6, n => counter.to(n))` |
| Chip | `new Chip(text, color, {position, fontSize?, mono?})` (30 px by default; the text is the colour lifted towards ink, so it reads on its own tint): `show`, `hide`, `set(text, color?)` | `const c = new Chip('k + 1 = 2', C.gold, {position: [500, 0]})` |
| Counter | `new Counter({label, position})`: `show`, `to(v, d)`, `color(c)`, `hide` | ticks the number as it tweens |
| burst | `burst(layer, text, {at, size?, color?, rotation?, hold?})` (runs in, holds, pops out; widens to fit text; text with a digit is lettered in Inter 800, since Bangers' 7 reads as 1) | `yield burst(w.top, '700!', {at: [610, -95], size: 118})` |
| stamp | `stamp(layer, text, {at, color?, rotation?, fontSize?})` returns `{node, slam()}` | `yield all(st.slam(), cam.shake(0.7))` |
| small fx | `pop(node)`, `appear(node)`, `vanish(node)`, `bump(node)`, `ripple(layer, at, color)`, `floatUp(layer, text, at)`, `drawArrow(layer, a, b)` | `yield floatUp(w.top, '+100', pointIn(w.top, g.root, g.along(0, 1)))` |
| coordinates | `posIn(layer, node)`, `pointIn(layer, fromNode, p)` | place a hud/top item over a moving world point |

Style tokens live in `theme.ts`: `C` (bg, panel, ink, muted, accent #FF5B2E, good, bad, cool, gold, and the
kit's other roles), `F` (display/body Inter, mono JetBrains Mono, comic Bangers), `S` sizes, `FRAME` safe area.
Change the palette there (or pick a registry theme, section 10), not in scenes. Text in a hue uses `inkOf(C.good)`,
never `C.good` itself (the same colour with `original`, the solved ink with a theme).

Legibility (the visuals gate runs `legibility.py` on the stills: nothing under 26 px, 4.5:1 contrast):

- `S` is what the kit uses: `small` 28 (the floor: header, panel titles, notes, table heads), `label` 30 (chips,
  row labels, kickers, ladder chips), `code` 30, `mono` 32, `caption` 40, `body` 42, `headline` 84. The chapter
  tag is 30 px and the show title 28 px, both on `FRAME.headerY` (text 96 px below the top edge); captions end
  on `FRAME.captionBottom` (96 px above the bottom edge).
- Text colours: `ink` and `muted` (#A39E96, 6.5:1 on the panels) only. `dim` (#6B6760, 3:1) is for strokes and
  decoration, never text. Code comments are #A8A196. Text on a tint of its own colour uses `lift(color)`.
- Show focus with colour, weight or a bar, never by fading text: unfocused code lines turn grey (5.5:1 or more),
  receded ladder rungs keep their text and dim only their cost bar, `g.focusOn()` fades shapes but turns labels
  muted.
- Chapter cards: the title is #FFF4EC on a deep burnt-orange band (#B23A12 to #7C230A, 5.9:1 or more); the
  numeral is #FFF4EC with a dark shadow. The bright accent is not used as a text ground (white on it is 3.1:1).
- World-layer text (pills 40, values 38, tags 42 px) is scaled by the camera: keep the zoom at 0.8 or more while
  the small print is on (`labels(false)` for a thumbnail below that). Node labels (0.95 x radius) stay readable
  down to zoom 0.5.
- A label with no ascender or capital (`new`, `one`) is only x-height tall and measures about 25% small; write
  plain-word labels in capitals (`NEW`, `ROUND 0`).

## 6. Recipes

Decode an input (entries fly onto the subject while it draws):

```tsx
yield* waitUntilCue('p1', 'Each flight', -0.15);
yield sequence(0.24, input.showRow(0, 0.3),
  ...EDGES.map((e, i) => all(input.fly(0, i, w.top, g.edge(e.from, e.to).pill, 0.55),
                             delay(0.18, g.drawEdge(e.from, e.to, 0.45)))));
```

Trace a route with a running total:

```tsx
const r = g.route([0, 1, 3], C.good);
yield r.fly(2.2, i => i === 1 ? cost.to(100, 0.5) : cost.to(700, 0.6));
```

Reject an illegal route (too many stops, over budget):

```tsx
const bad = g.route([0, 1, 2, 3], C.accent, 'dot');
yield chain(bad.fly(0.8), bad.reject(2, '2 stops > k'));   // later: yield bad.fade(0.3)
```

Think countdown (question, pause, answer):

```tsx
yield* waitUntilLine('q1');
yield q.ask(1, 'What is simpler to count than stops?');
yield* waitUntilThink('q1');
yield* q.countdown(line('q1').think);        // exact length: the answer line starts on time
yield* waitUntilLine('a1');
yield q.answer('Flights: at most k + 1 = 2');
```

DP row update (read old, write new), with the edge that causes it firing on the subject:

```tsx
yield* t.copyRow(0, 1, 0.5);
yield all(g.fire(0, 1, C.good, 0.5), delay(0.4, all(t.set(1, 1, '100'), g.setValue(1, '100', C.good))));
```

Code walkthrough synced to lines (active-line bar moves as the voice explains):

```tsx
yield* waitUntilLine('c1');
yield all(cp.focus(CODE.init), t.showRow(0, 0.05, 0.3));   // quick pop: the row settles before it is copied
yield* waitUntilCue('c1', 'Round zero');
yield chain(all(cp.focus(CODE.copy, 0.3), t.copyRow(0, 1, 0.45)),
            all(cp.focus(CODE.relax, 0.3), g.fire(0, 1, C.good, 0.45)));
```

Camera moves (under the chapter card, then small moves inside a chapter):

```tsx
yield* waitUntilTime(chapter(2).start - 0.6);
yield cam.frame(g.center(), [-520, 30], 0.8, 1.2);           // subject left, room on the right (zoom >= 0.8: weights stay >= 28 px)
yield all(cam.frame(g.center(), [650, -255], 0.5, 1.2), g.labels(false, 0.4));   // thumbnail corner, small print off
yield cam.pushIn(g.pos(3), 1.25, 0.8);                        // emphasis
```

Chapter clean-up (everything a chapter added leaves before the next card):

```tsx
yield* waitUntilTime(voiceEnd('b1'));   // clear within 0.25 s of the last word
yield all(fan.hide(), routes.hide(), g.resetAll(0.3), delay(0.5, vanish(fan.node, 0)));
```

A new film: edit `scenes/data.ts` (nodes, edges, input rows, rungs, code and its line numbers), write one
`chN-*.tsx` per chapter keyed to your line ids, list them in `film.tsx`, set `SHOW` and the title card. If the
subject is not a graph (an array, a grid, a tree), add a kit piece in `src/kit/` with the same shape as Graph
(a `root` node, state methods, motion methods returning generators) and keep the camera and chrome.

## 7. Rendering

```bash
python3 $S/mc.py stills --project .                 # one still per line + build/stills-sheet.jpg (~5 s for 14)
python3 $S/mc.py stills --project . --at chapters   # or --at 12.5,30,41.2 (add --keep to keep the others)
python3 $S/mc.py bench --project .                  # fps of one worker and the full-film ETA
python3 $S/mc.py render --project . --max-minutes 100 [--workers 2] [--segment 20]
python3 $S/mc.py editor --project .                 # the Motion Canvas editor at http://127.0.0.1:9000 (voice plays)
```

- `render` writes `build/silent.mp4` (H.264, yuv420p) from 20 s segments listed in
  `build/segments/manifest.json`. It stops cleanly at the budget with exit code 3; run the same command again and
  only unfinished segments render. Any change to the built page restarts the segments (a half-old film is worse
  than a slow one), so do not touch `source/` between resumed runs.
- Run it in the background with a log when the ETA is over 2 minutes:
  `python3 $S/mc.py render --project . > build/render.log 2>&1 &` and poll the log.
- Measured here (1080p30, 4 CPUs, 2 workers): bench 10.1 frames/s per worker; the mini film's earlier 62 s cut (1867
  frames) rendered in 2.4 minutes, so a 6-minute film takes about 15. With six other render jobs on the same
  CPUs it ran at 1.0 to 1.4 frames/s in total (23 to 32 minutes for the mini film): bench first.
- Stills are rendered by the same harness, so a still is exactly the frame the video will show.
- `python3 $S/legibility.py --project .` measures every text in the stills (about 2 minutes for 14 on a busy
  machine) and marks failures in `stills/legibility/`. A text caught mid-fade is a timing problem: make it land
  before the still (stills sit at 65% of each line's voice), do not hide it.

## 8. Gotchas (symptom, fix)

- Spawned animation stops halfway (a ripple, a fade-out tail, a token that never fades): Motion Canvas cancels
  a thread's spawned children when that thread ends, and every argument of `all()`, `sequence()`, `delay()` is
  its own short thread. Inside such a generator use `background(task)` (spawns on the film's root thread).
- `[timing] late by ...`: a `yield*` animation ran past the next cue. Spawn it with `yield` or shorten it.
- `!=`, `<=`, `++` drawn as single ligature glyphs in code: set `letterSpacing={0.01}` on Code/Txt with JetBrains
  Mono (CodePanel does).
- Arrowheads or round caps visible on edges that are not drawn yet: a Line with `end={0}` still draws its
  arrow and caps. Keep `opacity={0}` until it draws (Graph does).
- Spaces vanish in layout text (`n = 4` shows as `n=4`, `time O(..)` runs together): Txt inside a layout trims
  leading/trailing spaces. Use the no-break space `' '`.
- Code lines all equally bright although `focus()` ran, and the log says "Code uses experimental draw hooks":
  `makeProject({experimentalFeatures: true})` (the template sets it).
- Wrong font in the first frames, or text measured too narrow: fonts must load before the project; project.ts
  imports `@fontsource/*` CSS and awaits `document.fonts.load(...)` for every weight used. Add new weights there.
- `TypeError: motionCanvas is not a function` in vite.config: the plugins are CommonJS; unwrap `.default`
  (the template does).
- `Top-level await is not available in the configured target environment`: the plugin sets
  `build.target: 'modules'`; the template's `explainer:target` plugin (listed after it) sets `esnext`.
- A Txt not yet added to the scene reports width 0: measure with a canvas (`measure(text, font)` in fx.tsx).
- Segments restart on every resume: something rewrote `source/dist` (a manual `vite build`). Use `mc.py`, which
  skips unchanged builds.
- A render you stop by hand keeps running: `capture.mjs` can ignore SIGTERM while a frame is in flight. Kill its
  node PID and its ffmpeg and chromium children by PID (`kill -9`); the unfinished segment is redone next run.
- Editor server left running blocks port 9000: stop it by PID (`mc.py editor` runs vite itself, so its PID is
  the server's). Never `pkill -f vite` (it matches your own shell).
- MP4 is huge (50+ Mbps, hundreds of MB for a minute) and renders slowly: something changes every pixel every
  frame (animated noise, a full-frame shimmer). x264 cannot compress it. Keep texture static in screen space
  (the kit's grain is: 57 Mbps per-frame grain vs 4.4 Mbps static, same look). A normal film is 3-8 Mbps.
- Random values differ between editor and render: use `useRandom()` or `rng(seed)` from world.tsx, never
  `Math.random()` (frames must be deterministic for resume and stills).

## 9. Laptop differences

- `mc.py editor` gives the live editor with the narration playing: scrub the timeline, tweak, and save; Vite
  hot-reloads the scene. The editor's own Render button also works there (Video (FFmpeg) exporter, output in
  `source/output/`), but `mc.py render` is faster and resumable.
- Use the local Chrome: `CHROMIUM="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"` (macOS) or
  `npx playwright install chromium` (inside `source/`, so it matches the pinned playwright-core).
- More cores: `--workers` defaults to up to 4; on an 8+ core laptop pass `--workers 6`.
- ffmpeg must be on PATH for capture and mixing (`brew install ffmpeg`).

## 10. Themes

The film's palette is `original` (the dark editorial look above, unchanged) unless `source/src/theme-film.ts`
holds a registry theme (`references/themes.md`). The template ships that file as a stub (`export const THEME =
null`), which means `original`.

```bash
python3 $S/vstate.py set theme=tokyonight-day
python3 $S/theme.py emit tokyonight-day --format ts --out source/src/theme-film.ts
python3 $S/mc.py stills --project . && python3 $S/legibility.py --project .
```

Back to `original`: copy `$SKILL/assets/template/src/theme-film.ts` over it and `vstate.py set theme=original`.
`kit/theme.ts` imports the file and maps the tokens onto the kit's roles (`themed()`); scenes keep using `C`:

| Kit role (`C.`) | Theme token |
|---|---|
| `bg`; backdrop key light `bgGlow` / rim `bgCool` / corner `bgCorner` | `bg` (+ a `bg2` gradient); `bg` mixed 13% (dark) or 7% (light) towards `lights[n]`, `cool`, `violet` |
| `panel`, `panelHi` (top of a panel's gradient), `cell` | `panel`; `panel2` (dark) or `panel` lightened towards `bg` (light); between `panel` and `panel2` |
| `line`, `hair`, `border`, `stroke`, `edge`, `grid` | `line`, `line2` and `dim` mixed (idle edges and node rings stay visible on light grounds) |
| node disc `nodeHi`/`nodeLo`, `pill` | `panel2`/`deep` (dark), `panel` lightened/`panel2` (light); `panel` |
| `ink`, `muted`, `dim` | `text`, `muted`, `dim` |
| `accent`, `accent2`, `good`, `bad`, `cool`, `gold` (fills, strokes, glows) | `accent`, `warm`, `good`, `bad`, `cool`, `gold` |
| text in a hue: `inkOf(c)`, chips and pills: `lift(c)` | `<hue>Ink`; `<hue>Ink` moved towards `text` (k + 0.25) |
| on a fill (burst lettering, the fan's root): `onFill(c, original)` | `on<Hue>` |
| `shade` (caption band), `shadow` (drop shadows: `shade(a)`) | `deep`; `shadow` (light themes at about a third of the alpha) |
| chapter card band `cardA..C` + `cardInk` | `panel2` to `panel`, title in `text`; two edge stripes and the numeral in the chapter's key light (`lights[n]`, its ink) |
| code: syntax colours, `recede` | `accentInk` (keywords), `coolInk`, `goldInk`, `dim` (comments), `goodInk`, `muted`, `text`, `warmInk`; `muted` |

What changes on a theme besides the colours: each chapter has its own backdrop key light from `lights`, which
cross-fades under the chapter card. On light themes coloured glows become soft shadows (`glow()`), grain
multiplies (dark themes: screen), and the vignette is a gentle `deep` edge. The vignette's clear centre is wider
(640 px), because it lies over the world layer and the solved inks have less margin than the original palette.
Chip fills are opaque tints (`tint()`) so a chip's shadow never shows through under its text.
