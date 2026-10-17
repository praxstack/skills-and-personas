# Three.js film guide

A Three.js "toy diorama" scene with a DOM text layer on top, driven by a seekable tween timeline keyed to the
voice. This guide covers the template in `assets/template/` (copied to `<project>/source/`).

## Contents

1. [Setup](#setup)
2. [Project anatomy](#project-anatomy)
3. [Timing API](#timing-api)
4. [Kit catalogue](#kit-catalogue)
5. [Recipes](#recipes)
6. [Themes](#themes)
7. [Rendering](#rendering)
8. [Gotchas](#gotchas)
9. [Laptop differences](#laptop-differences)

## Setup

```bash
cp -r $SKILL/assets/template source
(cd source && npm ci --no-audit --no-fund)          # ~5-10 s; lockfile pins every version
python3 $S/voice.py --project . --emit source/src/timing.js
node $S/film3d.mjs build --project .                 # esbuild bundle -> source/dist/film.js (~1 s, 2.7 MB)
```

Pinned versions (package.json + package-lock.json): `three` 0.186.1, `esbuild` 0.28.2, `inter-ui` 4.1.1,
`jetbrains-mono` 1.0.6 (the NL cut: no ligatures), `@fontsource/bangers` 5.3.0. Node 18+ (tested on 22). Fonts are
bundled into `dist/film.js` as woff2 data URLs, so the page works offline from `file://` (Google Fonts are
blocked here). No Theatre.js and no GSAP: `src/kit/time.js` is the whole animation engine.

Browser and capture: `$S/capture.mjs` loads the template's pinned `playwright-core` 1.56.1 (installed by `npm ci`)
and finds Chromium itself (`/opt/pw-browsers/chromium` here, an installed Chrome on a laptop; `CHROME=/path/to/chrome`
overrides). `film3d.mjs` always passes `--webgl`
(SwiftShader) unless `GPU=1` is set.

## Project anatomy

| File | What it is | Edit it? |
|---|---|---|
| `src/film.js` | THE SCENES: graph data, code, named camera shots, one block per chapter of tweens | yes, this is the film |
| `src/kit/style.js` | palette `C`, glow levels `GLOW`, light/glow drawing `FX`, ink helpers, fonts `FONT`, sizes | to change the look |
| `src/theme.js` | the theme: the shipped stub (`THEME = null`, the original palette) or a file from `theme.py emit` | via `theme.py` only |
| `src/timing.js` | `window.TIMING`, written by `voice.py --emit` (stamped with the timing hash) | never by hand |
| `src/kit/time.js` | timing helpers (`at`, `word`, ...), easings, `rand(seed)`, the `Timeline` | rarely |
| `src/kit/stage.js` | renderer, quality presets, lights, the set (desk, board, toys, skyline, bokeh) | to change the world |
| `src/kit/camera.js` | `CameraRig`: orbit shots, shake, `fit()` | rarely |
| `src/kit/graph3d.js` | `Graph`: pillars on sand islands, glowing arcs, weight tags, badges, flags | rarely |
| `src/kit/token.js` | `Token`: the mascot that flies routes (and translucent ghost copies) | rarely |
| `src/kit/overlay.js` | DOM layer: 1920x1080 stage scaled to the page, `Anchor`, `fmt()` | rarely |
| `src/kit/ui.js` | panels: captions, chapter marks, cards, code, rows, ladder, bursts, decoder, tree | to add a panel |
| `src/kit/film.css` | every overlay style (in 1920x1080 px, whatever the render size) | to restyle panels |
| `src/main.js` | the page contract (`READY`, `TOTAL`, `renderFrame`), fonts, `?preview` player | no |
| `index.html` / `fast.html` / `draft.html` | the same film at quality `final` / `fast` / `draft` | no |
| `build.mjs` | esbuild bundle; rewrites `dist/film.js` only when its bytes change | no |

`main.js` per frame: `tl.seek(t)` sets every tweened prop, then each of `film.things` runs `apply(t)` (camera
first so labels project through the new camera), then the overlay lays out text, then the scene renders. The
overlay is authored in 1920x1080 stage pixels and scaled to the render size, so a 1280x720 render shows the
same layout.

## Timing API

From `src/kit/time.js` (all times in seconds; ids are script line ids):

| Helper | Meaning |
|---|---|
| `at('p4')`, `at('p4', 0.5)`, `at('p4', 1)` | voice of line p4 starts / is halfway / ends |
| `word('p4', 'The answer', f = 0)` | when that phrase is spoken (from its character position in `say`; throws if absent) |
| `start('p4')`, `end('p4')`, `dur('p4')` | the line's slot (`end` includes its think pause and gap) |
| `think('q1')` | `[from, to]` of the think pause after a question line |
| `TOTAL`, `LINES`, `L.p4`, `CHAPTERS`, `chapterStart(n)`, `lineAt(t)` | raw timing |
| `E.out`, `inOut`, `outBack`, `outElastic`, `outExpo`, ... | easings; `p(t, a, d, ease)` = eased 0..1 progress |
| `rand(seed)` | deterministic random generator (never `Math.random()`) |

The `Timeline` (one per film, created in `buildFilm`):

```js
tl.to(obj, { x: 1, tone: '#ff5b2e', target: [0, 2, 0] }, at('p1'), 0.6, 'out')   // tween props
tl.fromTo(obj, { on: 0 }, { on: 1 }, time, 0.4)                                // explicit start
tl.set(obj, { route: [0, 1, 3], u: 0 }, time)                                   // jump
tl.pulse(obj, { glow: 2.5 }, time, 0.6)                                         // up and back
tl.valueAt(obj, 'u', time)                                                      // what it will be then
```

Numbers interpolate, `#rrggbb` strings blend, arrays of equal length interpolate element-wise; other strings and
arrays of another length switch at the end of a `to` (use `set` to switch at the start). A prop must exist on
the object before it is tweened. For each prop, tweens are sorted by start time and each starts from wherever
the previous one is at that moment, so seeking any `t` in any order gives the same frame.

## Kit catalogue

3D (each is an entry of `things`, applied every frame):

- **`new CameraRig(stage, SHOT.establish)`** - props `target [x,y,z]`, `dist`, `az` (degrees around, 0 = front),
  `el` (degrees above), `fov`, `frame [fx, fy]` (where the target lands on screen, `[0.5, 0.5]` = centre; a lens
  shift, not a turn), `drift` (slow float, 0 = locked). `cam.shot(tl, time, SHOT.x, d = 1.4, ease)` moves there
  (d 0 = cut); `cam.shake(tl, time, d, amount)`; `cam.fit(points, [l, t, r, b], {az, el})` returns a shot that
  fits those points into that box of the 1920x1080 frame. `cam.shot(tl, at('b1'), cam.fit(g.bounds(null, { flags: [0, 3] }), [96, 160, 1140, 860], { az: -16, el: 52 }))`
- **`new Graph(stage, ui, { nodes, edges, pillar = 2.6, arc = 1 })`** - nodes `{ id, pos: [x, z], color, h }`
  on a board about -12..12 by -7..7; edges `[a, b, w, { labelAt, bend }]`. `g.n(id)` props: `rise` 0..1 (grow
  from the board), `glow`, `tone`, `dim`, `lift`, `value`/`valueOn`/`valueTone` (badge above), `tag`/`tagOn`/
  `tagTone` (flag below). `g.e(a, b)` props: `draw` 0..1, `glow` (GLOW.* levels; above 1 blooms), `tone`, `dim`,
  `fire` 0..1 (a bead travels; outside 0..1 hidden), `label`, `labelOn`, `labelTone`, `labelPop` (pulse it when the
  label changes: `tl.set` the new label, then `tl.pulse(g.e(a, b), { labelPop: 1 }, t, 0.45)`). Weight tags are
  32 px; move one with `labelAt` when it sits on a pillar or next to another tag. Helpers: `g.top(id)`,
  `g.mid(a, b)`, `g.curve(a, b)`, `g.routePoint(route, u)`, `g.bounds(ids?, { flags })` (islands, pillars with
  their badges, arcs with their weight tags, and the flags of the node ids in `flags`, so `cam.fit` keeps all of
  them on screen). `tl.to(g.e(0, 1), { draw: 1 }, at('p1'), 0.6)`
- **`new Token(stage, g, { color, ghost, size })`** - props `route` (set it), `u` 0..route.length-1 (one unit per
  flight), `on`, `jump` (tween 0 -> 1 = one hop), `hop` (arc height), `shake` 0..1 (a "no" wobble), `x y z`
  offsets; `tok.where()` = its position. `tl.to(tok.p, { u: 2 }, at('p4'), 2, 'inOut')`
- **`stage`** (`createStage()`): `scene`, `camera`, `key` (warm spot) and `rim` lights, `set` (desk, board, toys),
  `quality`, `rbox(w, h, d, r)` rounded-box geometry, `std(color)` / `matte(color)` materials, `shade(obj)`.

Overlay (DOM, crisp at any size; text accepts `**bold**` and `^(superscript)` via `fmt`):

- **`frame(ui)`, `new Captions(ui)`, `new ChapterMarks(ui)`** - vignette, the caption band (current line's
  `cap`, two lines max, words brighten as spoken; it fades in just before a chapter's first voice and out after
  its last line, and inside a chapter the next caption replaces the last at the line change, never half-faded), comic chapter banner at each chapter start and the
  "01 THE PROBLEM" corner tag. Automatic from TIMING.
- **`new TitleCard(ui, { kicker, title, title2, sub })`** - props `on`, `k` (entrance 0..1).
- **`new Card(ui, { kicker, big, small, top })`** - centred card (recap, definitions); prop `on`.
- **`new QuestionCard(ui, { n, text }).countdown(tl, 'q1', until, { from })`** - shows at the question's voice
  (or at `from`; pass `{ from: enter('q1') }` when the question opens a chapter), the ring and number count down
  its think pause, hides at `until`.
- **`new CodePanel(ui, { code, file, x, y, w, size = 30, lh = 1.36 })`** - syntax-coloured C++, ligatures off.
  Keep `size` at 30-36 (the quality bar's code size): indent with 2 spaces and give the panel about 1040 px so
  most lines fit; a line too long wraps and continues 2ch right of its own indent. Comments are `C.comment`,
  dimmer than code but about 7:1. Props `on`, `shown` (lines revealed), `active` (1-based line), `hl`.
  `code.reveal(tl, n, time)`, `code.focus(tl, 9, time)` (the highlight bar glides to line 9).
- **`new ArrayRow(ui, { label, values, heads, x, y })`** - a DP/dist row. `row.write(tl, i, v, time, tone)`
  flashes and writes a cell; `row.cell(i)` props `v`, `flash`, `tone`.
- **`new Ladder(ui, { rungs: [{ name, time, space, cost, tone }], x, y })`** - complexity ladder, 880 px wide
  (put it at x 944 for the right half); a rung takes no room until its `on` rises, so the panel grows rung by
  rung. `lad.rung(i)` props `on`, `hi`; `lad.p` props `on`, `pick` (rung index), `pickOn` (the "INTERVIEW PICK"
  stamp, which hangs below the picked rung's right corner, clear of its text).
- **`new Burst(ui, { text: '700!', tone, world: () => v3 | pos: [x, y], size })`** - comic burst;
  `burst.pop(tl, time, hold)`.
- **`chip(ui, { world: () => v3 | pos: [x, y], text, tone, cls: 'chip big', format: (n) => ..., offset, pivot })`**
  - a label pinned to a 3D point or a screen point; props `on`, `text`, `tone`, `n` (for `format`), `scale`,
  `dx`, `dy`. A live counter: `format: (n) => \`cost **${Math.round(n)}**\`` and tween `n`.
- **`new Decoder(ui, rows, { x, y })`** - the raw input as text; a row is `['plain', ['token', 'id'], ...]`.
  `dec.row(i).on`, `dec.tok(id)` props `hi`, `sent`, `fly`; `dec.target(id, () => g.top(1)).send(tl, id, time)`
  flies a copy of the token into the 3D scene.
- **`new RecTree(ui, { tree: [0, [1, [2], [3]]], title, x, y, w, h })`** - recursion tree; `tree.level(tl, depth,
  time)` reveals a level; `tree.node(i)` props `on`, `tone`, `note`, `noteOn` (breadth-first order). A note is a
  30 px verdict under a leaf ('700 ✓') in its tone lightened toward white: `tl.set` the note with `noteOn: 0`,
  then tween `noteOn` to 1 with the leaf, so it never switches mid-fade.

## Recipes

Small helpers at the top of `buildFilm` in `film.js` (`light`, `fire`, `fly`, `teleport`, `resetEdges`,
`badge`, `badges`, `badgesOff`, `relabel`, `enter`, `leave`) cover most beats; copy them into a new film.

**Text that lands before the still.** Line stills are taken 65% into each line's voice and chapter stills 45%
into the chapter; anything still fading in then is a timing bug, not a legibility one. Let rows, badges and
notes land a beat before the words that name them. A badge or label that changes text switches with `tl.set`
at the start of its tween (`badge(i, value, tone, time)`, `relabel(a, b, label, tone, time)`), never at the end.

**Chapter banners.** The banner sweeps in 0.78 s before a chapter starts and sweeps out 0.5-0.8 s into it.
Nothing may sit under it: a chapter's panels and badges leave by `leave(id)` (= `end(id) - 0.35`, with a fade of
0.3 s or less) on its last line, and the next chapter's panels enter at `enter(id)` (= `start(id) + 0.7`, once
the banner has gone) on its first; the 3D subject may change behind the banner. A chapter's first line has a
1 s lead (the voice starts at `start(id) + 1.0`), so key the subject's entrance to `start(id)`, never to `at(id)`:
it must be on screen as the voice starts (qa.py `chapter-entry`). Check in motion after the
render: `ffmpeg -ss <start-0.6> -t 1.6 -i build/silent.mp4 -vf fps=10,scale=960:-1,tile=4x4 -frames:v 1 chN.jpg`
for every chapter.

**Decode an input** (p1): show the decoder as the banner leaves, raise one pillar per node, land the flight rows,
then send each flight from its row into its arc.

```js
tl.to(dec.p, { on: 1 }, enter('p1'), 0.4);
NODES.forEach((n, i) => tl.to(g.n(n.id), { rise: 1 }, start('p1') + 0.1 + i * 0.13, 0.65, 'outBack'));   // behind the banner, up before the voice
EDGES.forEach((_, i) => tl.to(dec.row(2 + i), { on: 1 }, word('p1', 'Each flight') - 0.2 + i * 0.08, 0.3));
EDGES.forEach(([a, b], i) => {
  const t0 = word('p1', 'Each flight') + 0.15 + i * 0.32;   // every row is in before the first flyer leaves
  dec.target(`f${i}`, () => g.mid(a, b)).send(tl, `f${i}`, t0, 0.55);
  tl.to(g.e(a, b), { draw: 1, labelOn: 1 }, t0 + 0.5, 0.6, 'out');
});
```

**Trace a route** (p4): set the route, tween `u` one leg at a time, fire each edge, count the cost on a chip
that rides the token, then light the answer and hop.

```js
tl.set(tok.p, { route: [0, 1, 3], u: 0 }, t0);
tl.to(tok.p, { u: 1 }, t0, 0.9, 'inOut'); fire(0, 1, t0, 0.9);
tl.to(tok.p, { u: 2 }, t0 + 1.25, 1.0, 'inOut'); fire(1, 3, t0 + 1.25, 1.0);
const cost = chip(ui, { world: () => tok.where(), offset: [0, -30], format: (n) => `cost **${Math.round(n)}**`, tone: C.hot });
tl.to(cost, { on: 1 }, t0, 0.35, 'outBack').to(cost, { n: 700 }, t0 + 1.9, 0.45);
light([[0, 1], [1, 3]], 'good', land, 0.4);
tl.to(tok.p, { jump: 0 }, land - 0.01, 0.01).to(tok.p, { jump: 1 }, land, 0.5, 'linear');
```

**Reject an illegal route** (a2): fire the edge in `C.bad`, dim it, pin a red chip to its apex, and wobble the
token: `fire(1, 3, t, 0.5, C.bad); light([[1, 3]], 'dim', t + 0.5); chip(ui, { world: () => g.mid(1, 3), text:
'not this round', tone: C.bad, pivot: [-50, 0] })`, `tl.pulse(tok.p, { shake: 1 }, t, 0.6)`.

**Think countdown** (q1): `new QuestionCard(ui, { n: 1, text }).countdown(tl, 'q1', at('a1') - 0.1)` and a
camera shot that puts the graph under the card: `cam.fit(g.bounds(), [260, 410, 1660, 880], { az: -4, el: 42 })`.
Keep something moving during the pause (a pulse on the edges in question).

**DP row update** (q2/a2, c1): two `ArrayRow`s (`dist`, `next`); each relaxation fires the edge, then
`next.write(tl, v, value, t + 0.6)` and the node badge `tl.to(g.n(v), { value: '100', valueTone: C.good }, ...)`.
Copy with `dist.write(...)` per cell at the end of the round.

**Code walkthrough synced to lines** (c1): `code.reveal(tl, 15, enter('c1') + 0.05, 0.6)` (the lines cascade in,
all shown before the first focus), then `code.focus(tl, n, word('c1', 'Round zero') - 0.3)` before each spoken
step, and the matching 3D action right after it.

**Camera moves**: one `cam.shot` per line (dolly in on the subject of the sentence, orbit 10-30 degrees between
beats, pull back for recaps). Hand-tune shots that show the board alone (`{ target, dist, az, el }`); solve every
shot that shares the screen with a panel with `cam.fit(g.bounds(), box, { az, el })`, where `box` is the free
part of the 1920x1080 frame (left, top, right, bottom; keep the bottom above 880 for captions). `cam.shake` on
impacts (bursts).

**A new 3D prop**: build meshes with `rbox`/`std`/`matte`, add them to `stage.scene`, keep a `p` object of
props, and push an object with `apply(t)` into `things`; tween its props on `tl`.

## Themes

The film's colours come from `src/theme.js`. The template ships a stub (`export const THEME = null`), which means
`original`: the palette in `style.js` exactly as the starter film was verified. To use a registry theme
(`references/themes.md`, `python3 $S/theme.py list`):

```bash
python3 $S/vstate.py set theme=github-light
python3 $S/theme.py emit github-light --format js --out source/src/theme.js     # ES module, bundled by build.mjs
```

`style.js` imports it and derives every role from the tokens (`themed()`); no other file holds a colour (film.css
reads CSS variables that `main.js` sets from `C`). Back to the original: copy `src/theme.js` from the template.

| Kit role | Token |
|---|---|
| sky (zenith, upper, horizon, warm band, below), fog | dark: `deep`, `bg2`+`violet`, `warm`; light: `bg2`+`accent`, `bg2`, `bg`, `bg`+`warm`, `deep` |
| desk, board, grid, sand islands, skyline, toys | `panel`/`panel2`/`deep` tinted with `warm`, `accent`, `gold`, `line2`, `good` |
| node blocks `C.node[0..7]` | `cool gold violet accent warm good bad violet` (pushed to 3:1 on the board when a pastel fill would vanish) |
| `hot` `good` `bad` `cool` `gold` / mascot `token` | `accent` `good` `bad` `cool` `gold` / `warm` (fills: arcs, glows, rings, bars) |
| idle arc `edge`, dimmed `dim` | dark: `text`, `line`; light: `muted`, `line2` |
| key light per chapter | `lights[n]` (a 12-30% tint of white), cross-faded behind each chapter banner; rim `accent`, fill `warm` |
| text `ink` / `inkSoft` / `inkFaint` / code comments | `text` / `muted` / `dim` / `dim` |
| panels, captions, badges, code panel | `panel` at 93-97% opacity, borders `line`/`line2`; code highlight `accent` at 10-16% |
| text in a hue (badge values, chip numbers, table heads, tree notes, title line 2) | `<hue>Ink` via `inkOf(tone)` |
| text on a fill (flags, tags, stamp, flyers, bursts, chapter band, tree nodes, block numbers) | `on<Hue>` via `onOf(tone)`, on a plate `plateOf(tone)` (the fill pushed to 6.2:1 against its on-colour) |
| syntax `k ty nu op fnc`, decoder keys | `violetInk accentInk goldInk warmInk goodInk`, `accentInk` |
| shadows, vignette, bottom fade, page | `shadow` (light themes at about 40% of the dark alpha), `deep`, `bg` |

Light themes (`tone: light`) also switch `FX`: no HDR glow (an active arc keeps its fill colour and gains a
translucent halo instead of blooming to white), normal instead of additive blending for halos, spills and bokeh
(tinted fills, not smudges), dark beads on the arcs, no bloom pass, lower key and rim light with more hemisphere
fill, a lighter bottom fade, and the outlines become a soft grey. Comic strokes take the colour opposite their text (`strokeOf`), so dark letters get
a light ring and light letters a dark one. With any theme the sky shader is tone-mapped like the other materials,
so draft stills match the final look. Check a theme like any palette: stills, `legibility.py`, and look.

## Rendering

```bash
node $S/film3d.mjs bench --project . --q final              # 2 s sample per worker -> frames/s and ETA
node $S/film3d.mjs stills chapters|lines|busy|12.5,40 --project . [--q draft]
node $S/film3d.mjs render --project . --q final --workers 2 --max-minutes 100 > build/render.log 2>&1
```

`render` rebuilds the bundle, then runs `capture.mjs` (screenshot mode: WebGL canvas + DOM text in one image)
over 10 s segments recorded in `build/segments/manifest.json`, and concatenates them into `build/silent.mp4`
(H.264, yuv420p, the project's size and fps). Exit code 3 = the `--max-minutes` budget ran out: run the same
command again; finished segments are kept. The page is stamped, so editing `source/` invalidates old segments.
`--from/--to` render a time range; `--q draft` writes `build/draft/draft.mp4` (a timing check, never the final).

Quality presets (`window.QUALITY` in each html, or `?q=` in a browser; single overrides `?bloom=0&msaa=0&shadow=1024&scale=0.75&aa=fxaa`):

| Preset | 3D render scale | Bloom | MSAA | Shadow map | Use |
|---|---|---|---|---|---|
| `draft` | 0.75 | off | off | 1024 | stills while editing, timing checks |
| `fast` | 0.75 | on | 4x | 1536 | long films without a GPU (text stays full-res) |
| `final` | 1.0 | on | 4x | 2048 | the delivered render |

Speed measured here (SwiftShader, 4 CPUs), frames/s for one worker from `bench`, and the real render:

| Size | Preset | Quiet box (load 3-9) | Note |
|---|---|---|---|
| 1920x1080 | final | 0.61 per worker, ~0.8 with 2 | 6-min film: ~4 h, three 100-minute runs |
| 1920x1080 | fast | 0.97 per worker, ~1.3 with 2 | 6-min film: ~2.3 h, two runs |
| 1920x1080 | draft | 1.17 per worker | timing checks only |
| 1280x720 | final | 1.32 per worker, ~1.8 with 2 | the demo's earlier 62 s cut: ~24 min quiet |

Under heavy load (other renders; load average 20-55) the smoke test's 62 s demo (an earlier cut, before the 71 s retime) at 1280x720 final took 51.4
minutes with 2 workers (0.6 frames/s), and `bench` under load (0.21 per worker) predicted 150 minutes: bench
numbers swing with the load, so re-bench when the machine is busy and budget for the slow case. A second worker
adds only about a third (SwiftShader already uses every core). Stills: ~3 s each at draft, ~9 s at final.
Always `bench` first and pick the preset from the ETA; never run more than 2 workers on a shared box.

## Gotchas

- **Slow render** - symptom: ETA in hours. SwiftShader is fill-bound: pixels x passes. Use `--q fast`, fewer
  workers on a loaded box (they fight for the same CPUs), Lambert (`matte`) for anything that does not need
  highlights, and no extra full-screen passes. Shadows: one shadow-casting light only.
- **Frames jump at 10 s boundaries** - something depends on the previous frame (accumulated state, a clock,
  `Math.random`). Make it a function of `t`, or a tween.
- **Text with ligatures** (`!=` as one glyph) - the font was not loaded with `featureSettings: '"calt" 0, "liga" 0'`
  or a panel uses a non-mono font; mono classes in `film.css` also set `font-feature-settings`.
- **Labels swim or lag a frame** - an anchor projected before the camera moved. Keep the camera first in
  `things` (main.js applies `things` before `ui.apply`).
- **Token stuck on a node or teleporting** - a `route` changed with `tl.to` (it switches only at the tween's
  end) or a `set` sits at a time earlier than you think. Change routes with `tl.set` via `fly()`/`teleport()`,
  and probe the state: in the browser console `renderFrame(15); FILM.things` shows every prop.
- **White blobs where glowing edges meet** - too many HDR edges into one block. Glow levels are in `GLOW`;
  bloom threshold is 1.1 (only emissive things bloom); edge tubes darken near their ends by design.
- **Graph hidden by a panel** - frame with `cam.fit(g.bounds(), box)`; re-check after any layout change.
- **`PCFSoftShadowMap` warnings / hard shadows** - r186 removed it; the stage uses `PCFShadowMap` with
  `shadow.radius` (2-5) for soft edges.
- **Washed-out colours** - colours must be set as hex strings (sRGB) or `new THREE.Color(hex)`; the renderer
  uses `NeutralToneMapping` and sRGB output. Do not multiply a material colour above 1 unless it should glow.
- **`window.TIMING is missing`** - `src/timing.js` was not emitted: `python3 $S/voice.py --project . --emit source/src/timing.js`.
- **Page error in a still** - capture prints `page error:`; the page also draws the stack in red. Open
  `source/draft.html?preview&t=<time>` in a browser for the console.

## Laptop differences

- **GPU**: run with `GPU=1 node $S/film3d.mjs render ...`. Hardware WebGL is 20-50x faster than SwiftShader; a
  6-minute 1080p film renders in minutes and `--workers 4` is fine. The look is the same (same shaders); MSAA
  edges can differ by a pixel.
- **Preview**: `(cd source && node build.mjs --watch)` and open `source/index.html?preview` - it plays in real
  time with a GPU (space, arrows, `&t=40`).
- **Chrome**: an installed Chrome works; set `CHROME=/path/to/chrome` if Playwright's Chromium is absent.
  `npx playwright install chromium` is only for laptops, never on this sandbox.
- **Voice**: Edge voices are reachable on a laptop; `$S/edge_voice_swap.py` re-voices a finished film. Re-emit
  `source/src/timing.js` and re-render if the timing changes.
- **Fonts**: bundled; nothing to install.
