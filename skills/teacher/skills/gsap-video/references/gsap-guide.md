# GSAP video guide

How the GSAP starter film is built, how to write a new film with its kit, and how to render it.

## Contents
1. Setup
2. Project anatomy
3. Timing API
4. Kit catalogue
5. Recipes
6. Rendering
7. Gotchas
8. Laptop differences
9. Themes

## 1. Setup

```bash
cp -r $SKILL/assets/template source
(cd source && npm ci --no-audit --no-fund && npm run vendor)
```

| Package (exact pin) | Why |
|---|---|
| `gsap` 3.15.0 | timeline + DrawSVG, MotionPath, MorphSVG, SplitText, Text, CustomEase (all free since 3.13) |
| `inter-ui` 4.1.1 | Inter 4 variable woff2 (full glyph set; `opsz` gives Inter Display at headline sizes) |
| `@fontsource/jetbrains-mono` 5.3.0 | code and numbers (400/600/700) |
| `@fontsource/bangers` 5.3.0 | comic bursts and stamps |
| `playwright-core` 1.56.1 (dev) | lets `capture.mjs`/`gsap_check.mjs` find Playwright inside source/; no browser download |

`npm run vendor` (`tools/vendor.mjs`) copies the scripts and fonts into `source/vendor/` and writes
`vendor/VERSIONS.txt`. The page only loads from `vendor/`, so renders work offline and `package.py` ships a
self-contained source folder. Install measured here: 6.5 s with an empty npm cache, 2 s warm (24 MB of
node_modules, 0.6 MB vendored). No environment variables are needed. Browser: `capture.mjs` finds `/opt/pw-browsers/chromium`; set `CHROMIUM=/path/to/chrome` elsewhere.
Node 18+ (tested on 22).

## 2. Project anatomy

| File | What it is | Edit? |
|---|---|---|
| `index.html` | loads styles, tokens, vendor scripts, `timing.js`, the kit, `scenes.js`, `main.js` | rarely |
| `timing.js` | `window.TIMING`, written by `voice.py --emit source/timing.js` (hash on line 1) | never by hand |
| `theme.js` | `window.THEME`: a stub (`null` = the original palette) or a theme emitted by `theme.py` (section 9) | only via `theme.py emit` |
| `tokens.js` | palette, fonts, sizes, safe area, chapter lighting moods; maps a theme onto the kit's roles | yes: the look |
| `styles.css` | fonts (@font-face), component styles; screen text is >= 28 px, world text 32-36 px (it shrinks with the camera) | for new components |
| `scenes.js` | `window.Film.build(K)`: this film's data and every tween | yes: the film |
| `main.js` | page contract: `READY`, `TOTAL`, `renderFrame(t)`; preview player | no |
| `kit/core.js` | `K`: timeline, line helpers, tween wrappers with the fight detector, DOM/SVG utils | no |
| `kit/stage.js` | layers, background canvas (lights, bokeh, dots, grain, vignette), camera, moods, captions, lower third | no |
| `kit/graph.js` | `K.graph`: persistent directed weighted graph, token, routes, fires, flags, badges | no |
| `kit/panels.js` | decoder, code panel, table, ladder, meter | no |
| `kit/cards.js` | title, chapter slab, question card, callout, stamp, note, result card, trees | no |
| `kit/array.js` | `K.barRow`/`K.tempRow` array subject, `K.stackCol` stack, `K.channel`, `K.heat` | no |
| `kit/<new>.js` | a subject the kit lacks (grid, tree, list): yours, loaded after `kit/array.js` | yes: new file |
| `tools/vendor.mjs` | copies GSAP + fonts into `vendor/` | no |

Layers, back to front: background canvas (`.bgc`, half resolution, drawn per frame), `svg#scene` with
`g#cam > g#world` (the camera transform; world layers `back, panels, edges, trails, nodes, labels, tokens, fx`),
`#ui` (screen-space panels), `#fx`, `#cards` (title, chapter slabs), `#hud` (lower third + progress), `#caps`.
World space moves with the camera; everything in `#ui`/`#cards` is screen space (1920x1080 pixels).
"no" in the Edit column means the file works as is and other films rely on it: to change one, copy the
component into a new file under a new name. New components go in new files (add the `<script>` tag in
`index.html` and the classes in `styles.css`).

Page contract (what `capture.mjs` needs): `window.READY` resolves after `document.fonts.load(...)`, the build
and `K.finalize()`; `window.TOTAL = TIMING.total`; `window.renderFrame(t)` = `K.tl.seek(t, false)` +
`K.ambient(t)` (camera transform, background canvas, captions, lower third: all pure functions of t). The
timeline is padded with `K.tl.set({}, {}, TOTAL)`, and a build that runs past TOTAL logs a warning.

## 3. Timing API

`const { L, C } = K;` inside `Film.build(K)`. Every line of the script is `L.<id>`:

| Field | Meaning |
|---|---|
| `start`, `end`, `dur` | the line's slot (includes lead-in and think pause) |
| `voiceAt`, `voiceDur`, `vEnd` | when the voice starts, how long it speaks, when it stops |
| `think` | seconds of silence after the voice (questions) |
| `at('phrase', frac=0)` | when the voice says that phrase (estimated from its position in `say`); throws if absent |
| `p(f)` | `voiceAt + f * voiceDur` |
| `next`, `prev`, `cap`, `say`, `chapter`, `scene`, `i` | neighbours and script fields |

Unknown ids throw with the list of real ids (`K.has(id)` tests). `K.chapter(n)` gives `{n, name, start, end}`.
`K.TOTAL`, `K.W`, `K.H`, `K.SAFE {l, t, r, b}` (b = 900, top of the caption band), `K.C` colours, `K.Z` sizes.

Tween wrappers (use these, not `gsap.to`; times are absolute seconds on the master timeline):

```js
K.to(el, { autoAlpha: 1, duration: 0.4 }, L.p1.voiceAt);         // from current state
K.fromTo(el, { scale: 0.3 }, { scale: 1 }, L.p1.at('price'));      // immediateRender: false
K.set(el, { autoAlpha: 0 }, L.p1.end);                              // instant, reverts when seeking back
K.init(el, { autoAlpha: 0 });                                       // pre-film state (build time)
K.fadeIn(el, t) K.fadeOut(el, t) K.pop(el, t) K.pulse(el, t) K.count(el, t, 700)
K.everyFrame((t) => ...)                                            // pure function of t, runs each frame
```

Each wrapper records element+property intervals; overlaps go to `K.warnings` (printed by `gsap_check`).
Pass `overlapOk: true` in the vars only when the overlap is intended.

## 4. Kit catalogue

All return times or handles; positions are pixels (world or screen as noted).

**Stage and camera** (`kit/stage.js`)
- `K.cam.start(view)`; `K.cam.frame(rect, box?, {pad, minS, maxS})` -> view that fits a world rect into a
  screen box; `K.cam.to(t, view|rect, {dur=1.4, ease, box, pad, maxS})`; `K.cam.push(t, worldPt, 1.25)`;
  `K.cam.at(t)`, `toScreen(p, t)`, `toWorld(q, t)` (build-time math). A slow drift is added every frame.
- `K.mood(t, n | {key, rim, glow})`, `K.autoMoods()` (one per chapter, from `tokens.moods`).
- `K.captions.hideFor(lineId)`; captions are automatic from `cap` (wrap at 84 chars, two lines).
- `K.hud.show(n, t, name, hideAt)` (called by chapter cards, which hide the tag and progress bar while the slab is up).

**Graph** (`kit/graph.js`): `const G = K.graph({nodes: [{id, x, y}], edges: [{from, to, w}], r: 56})` in world space.
- edges are ids `'01'` (from+to); `G.node(id)`, `G.edge(id)`, `G.edgeBetween(a, b)`, `G.pos(id)`, `G.beside(edgeId, d)`
- `G.showNodes(ids, t)`, `G.drawEdges(ids, t)` (DrawSVG), `G.showAll(t)`
- `G.lightNode(id, t, color)`, `G.unlightNode(id, t)`, `G.ripple(p, t)`, `G.fire(edgeId, t, color)` (comet + weight flash)
- `G.trail(edgeId, t, color, d)`, `G.clearTrails(t)`; `G.placeToken(id, t)`, `G.hideToken(t)`
- `G.route(t, ['0','1','3'], {leg, hold, color, trail})` -> `{end, arrive[]}`: the paper plane flies (MotionPath)
- `G.reject(t, path)` -> time the cross lands; `G.flag(id, 'SRC', 'accent', t, 'bottom')`
- `G.badge(id, text, t, {color, dx, dy, until})`, `G.badgeAt(worldPt, text, t, o)`; `G.fade(t, opacity)`
- `G.bbox(ids?, pad)` -> world rect for camera framing (includes flags when `ids` is null)
- Weights and flags are 36 px, badges 32 px in world space: frame the graph at camera scale 0.8 or more so they
  stay above 26 px on screen (the starter's tightest views, code and upperRight, frame it at about 0.81).

**Panels** (`kit/panels.js`)
- `K.decoder({x, y, w, title, lines, size=30})` (world): `.show(t)`, `.mark(i, t, {color, until})`,
  `.chip(i, t, worldPt, {text, col})` flies a value into the graph (it slides out along its own row first, so it never
  crosses the rows above) and returns its landing time, `.hide(t)`.
- `K.codePanel({x, y, w, title, code, size=30, maxLines})` (screen; size defaults to `tokens.size.code`, keep it
  30-36): `.show(t)`, `.reveal(t, a, b)`, `.revealAll(t)`, `.focus(t, a, b)` (active-line bar; the other lines
  dim to opacity 0.75, still >= 4.5:1; scrolls if needed), `.unfocus(t)`, `.hide(t)`. At 30 px a 1000 px panel
  fits 50 characters per line and 14 lines (702 px high).
- `K.table({x, y, title, cols, colHead, rows: [{id, label, values, hidden}], cw, ch})`: `.show(t)`,
  `.showRow(id, t)`, `.set(id, col, value, t, {color, flash})`, `.copyRow(from, to, t)`, `.ring(id, col, t)`,
  `.cell(id, col)` -> screen rect, `.hide(t)`.
- `K.ladder({x, y, w, title, rungs: [{name, time, space, cost: 0..1, note}]})`: `.show(t)`, `.rung(i, t)`,
  `.focus(i, t)`, `.pick(i, t, label)`, `.hide(t)`.
- `K.meter({x | right, y, label, value, color})`: `.show(t)`, `.to(t, value, d, {pulse})`, `.hide(t)`. Each
  `.to` pulses the box for 0.4 s; for a counter that ticks faster than that, pass `{pulse: false}` or drive
  `meter.val` through `K.channel` (below).

**Cards** (`kit/cards.js`, screen space)
- `K.titleCard({kicker, title: 'Line\nLine', sub}, tIn, tOut)`; `K.chapterCards({skip, opts})` (a slab per chapter
  in the pause before it, then the lower third); `K.chapterCard(n, t, {name, color})`.
  The slab covers the left 900 px from `K.cardIn(n)` (chapter start - 0.78 s) to `K.cardClear(n)` (start + 0.56 s).
  Left-side screen content of the last chapter must be gone by `K.cardIn(n)` (`panel.hide(K.cardIn(n) - 0.4, 0.35)`)
  and the new chapter's must arrive at `K.cardClear(n)` or later (`ladder.show(K.cardClear(4))`); `K.afterCards(t)`
  moves a time out of any card window. The chapter's first caption and `K.question` wait for the card by
  themselves. World content counts too: a graph in the left half fades out before the card and back in after
  it (`G.fade(K.cardIn(n) - 0.35, 0, 0.3); G.fade(K.cardClear(n), 1, 0.45)`, the starter's chapters 2 and 3) while
  the camera reframes it. `gsap_check` lists any screen element or world text visible under a slab.
- `K.question(L.q1, {n, x, cy=498, w=800, size=64, text, banner})`: words light up as spoken (not yet spoken:
  opacity 0.5, still readable), ring counts the think seconds. `banner: true` with `{x: 96, w: 1728, cy: 258, size: 46}` makes a full-width top banner with the
  ring on the right, so a wide subject (an array row) stays visible under it.
- `K.callout('700!', t, {x, y | at: worldPt, dx, dy, color, rot, size, hold})`: comic burst (one options
  object); `K.stamp(text, t, {x, y | at, color, rot, size, hold})`.
  Both add an entry to `K.moments`, so `gsap_check` audits the frame where they are at full size. Digits and
  lowercase letters in a burst are set in Inter Black: Bangers' 7 reads as a 1 ("700!" looked like "100!") and
  it has capitals only ("k + 1" read "K + 1"), so write comic words in capitals ('+1 FLIGHT').
- `K.note(text, t, {x, y, w, size, color, until})`; `K.resultCard({x, y, w, kicker, big, color, lines}, t, tOut)`.
- `K.tree({x, y, w, h, root, r(d), color, heat})`, `K.fanTree({branching, depth, rootLabel, heat: ['amber','accent','rose']})`,
  `K.dfsTree(G, src, depth)`: `.grow(t, per)` -> time each level lands, `.mark(path, t)`, `.hide(t)`.

**Array and stack** (`kit/array.js`, world space)
- `const R = K.barRow({x0, stride, base, values, lo, hi, titles: {index, answer}, unit, barW})`: value bars
  (height and heat colour from the value between `lo` and `hi`), an index row and an answer row.
  `K.tempRow({...})` is the same row drawn as thermometers (titles day/answer, unit °).
- `R.showTubes(t)`, `R.fill(i, t, v)`, `R.setAll(t, values, {lo, hi, cells})` (morph to another example; extra
  bars fade), `R.showIdx(t)`, `R.showCells(t)`, `R.answer(i, v, t, {color})`, `R.clearAnswers(t)`,
  `R.cols(t, ids, alpha)` (fade columns a panel would cover), `R.flash(i, t, color)`, `R.tint`, `R.idxColor`.
- `R.arc(j, i, t, {color, label, until})` an arc from j to i with a pill label; `R.clearArcs(t)`;
  `R.tag(i, text, t, {color, until, solid})`; `const M = R.marker('accent', 'today')` then `M.to(i, t)`,
  `M.show(t, i)`, `M.hide(t)` (a highlight column that slides between bars: pointers i, j, lo, hi).
- `R.labelPt(i)`, `R.cellPt(i)`, `R.rect(i0, i1, {top: 'arcs'|'tags'|'labels', bottom: 'cells'|'idx'})` -> world
  rect for `K.cam.to`.
- `const S = K.stackCol({R, x, w, top, bottom, title, topText, colorOf, chipText: (i, v) => [left, right]})`:
  `S.show(t)`, `S.push(i, v, t)` (a chip lifts off bar i into the next slot), `S.flashTop(t, color)`,
  `S.pop(t, i, {value, write})` -> `{j, land}` (the top chip flies to answer cell j and writes `value`, default
  `i - j`), `S.clear(t)`, `S.fade(t, a)`, `S.rect()`, `S.depth()`.
- `const ch = K.channel(el)`: `ch.to(t, vars, d)` / `ch.set(t, vars)` collect many updates of one property set
  and emit them in time order at finalize, each cut short where the next begins, so fast counters and repeated
  colour changes never trip the overlap check. One channel per property group of an element.
- `K.heat(f)`: cyan (0) to cream to amber to accent (1), for colouring values.

**Utilities** (`kit/core.js`): `K.svg(tag, attrs, parent)`, `K.html(tag, cls, inner, parent, style)`, `K.fmt('O(n^(k+1))')`
(real superscripts), `K.textW(text, font)`, `K.fit(text, font, maxW, max)`, `K.col('mint')`, `K.rng(seed)`,
`K.layer.<name>` (world layers), `K.ui` (screen layer).

## 5. Recipes

Decode an input (values fly from the text into the subject):

```js
dec.show(L.p1.voiceAt + 0.35);
FLIGHTS.forEach((id, i) => {                       // FLIGHTS = ['01', '12', '20', '13', '23']
  const t = L.p1.at('each flight') + i * 0.32;
  dec.mark(2 + i, t, { until: t + 0.9 });            // highlight the input line
  const land = dec.chip(2 + i, t, G.edge(id).mid, { text: `[${id[0]}, ${id[1]}, ${G.edge(id).w}]` });
  G.drawEdge(id, land - 0.35, 0.6);                  // the edge draws on as the chip lands
});
```

Trace a route, counting its cost:

```js
const cost = K.meter({ right: 96, y: 176, label: 'cost', value: 0, color: 'accent' });
cost.show(L.p4.voiceAt);
const fly = G.route(L.p4.voiceAt + 0.1, ['0', '1', '3'], { leg: 1.05, color: 'accent' });
cost.to(fly.arrive[0], 100, 0.4);
cost.to(fly.arrive[1], 700, 0.6);
K.callout('700!', L.p4.at('the answer'), { at: G.pos('3'), dx: 150, dy: -170, color: 'amber', rot: 8 });
```

Reject an illegal route: `const tx = G.reject(L.x.at('too many'), ['0','1','2','3']); K.stamp('2 stops', tx, {...})`.

Think countdown: `K.question(L.q1, { n: 1 })` and, on the subject, a ghost hint in the think pause
(`G.route(L.q1.vEnd, path, { color: 'violet' })`). The caption is hidden for that line automatically.

DP row update (Bellman-Ford round):

```js
tb.ring('old', 0, t, { color: 'accent' });                  // read from the old row
G.fire('01', t, 'accent');                                   // the flight relaxes
tb.set('new', 1, '100', t + 0.6, { color: 'accent' });      // write the new row
tb.copyRow('new', 'old', L.x2.at('copy'));                  // end of round
```

Code walkthrough synced to the voice: `code.focus(L.c1.at('for each flight'), 9)`; `code.focus(L.c1.at('if'), 11, 12)`;
pair each focus with the table write and edge fire it causes, at the same phrase.

Camera: build named views once (`G.bbox()` plus a screen box), then `K.cam.to(t, rect, {box})` per scene; push in
on the moment of truth (`K.cam.push(t, G.pos('3'), 1.3)`); pull out for the outro. Never overlap two camera moves.

Monotonic stack (next greater element, daily temperatures, stock span):

```js
const R = K.barRow({ x0: 330, stride: 130, base: 680, values: A, lo: 60, hi: 80 });
const S = K.stackCol({ R, x: 1330, w: 250, top: 400, bottom: 700, colorOf: (v) => K.heat((v - 60) / 20) });
const today = R.marker('accent', 'i');
let t = L.d1.voiceAt;
A.forEach((v, i) => {                                  // one beat per element, keyed to the dry-run lines
  today.to(i, t);
  while (S.depth() && S.topChip().v < v) { S.flashTop(t + 0.2); const { land } = S.pop(t + 0.5, i); t = land; }
  t = S.push(i, v, t + 0.3) + 0.2;
});
```

Chapter lighting is automatic (`K.autoMoods()`); change hues in `tokens.moods`.

## 6. Rendering

All through the shared `capture.mjs` in screenshot mode (no `CAPTURE_SELECTOR`), from the project folder:

```bash
node $S/gsap_check.mjs --page source/index.html                                  # lint (errors exit 1)
node $S/capture.mjs --page source/index.html --prime 0.25 --stills chapters --timing timing.json --stills-dir stills
node $S/capture.mjs --page source/index.html --prime 0.25 --stills lines --timing timing.json --stills-dir stills
node $S/capture.mjs --page source/index.html --prime 0.25 --bench 3              # fps + ETA
node $S/capture.mjs --page source/index.html --out build/silent.mp4 --prime 0.25 --workers 4 --max-minutes 100 > build/render.log 2>&1
```

- Bursts and stamps: `gsap_check` prints their full-size times as a comma list; pass it to `--stills`.
- Segments of 20 s go to `build/segments/` with `manifest.json`; re-running skips finished segments; exit 3 =
  budget reached, run again. A change to any file in `source/` restarts all segments. Only finished segments
  survive a kill (a container restart killed this skill's smoke render before any 20 s segment was done, and
  it started over): on a slow or shared machine add `--segment 10`.
- `--prime 0.25` plays each worker's page from 0 to its segment start in 0.25 s steps before capturing, so
  every tween records its start values in playback order.
- Speed measured in this sandbox (4 CPUs, no GPU, JPEG screenshots): `--bench` about 7 frames/s per worker on a
  nearly idle machine (3-5 under heavy load). The demo's earlier 62 s cut (1867 frames) with 2 workers while
  eight other renders ran: 4.7-6.2 min (6.6-5.2 frames/s at load averages 20-36). Before the grain was made still it took
  12-26 min (encoding per-frame noise is expensive too). Budget 10-20 min for a 6-minute film with 4 workers
  on a quiet machine.
- File size: about 5 Mbit/s at `--crf 17` and about 3 at `--crf 20` (check which default your `capture.mjs` has). Anything re-randomised every
  frame (grain, noise) multiplies it: animated grain measured 37 Mbit/s.
- What costs time: full-screen DOM layers (each one composited every frame), SVG filters, huge blurred
  shadows. The template keeps all atmosphere in one half-resolution canvas (about 25 ms a frame
  instead of about 75 ms for separate DOM layers).

## 7. Gotchas

| Symptom | Cause | Fix |
|---|---|---|
| A frame flashes the wrong state for one frame (QA flicker) | two tweens on one element+property overlap, or a `from` tween rendered at build | use `K.fromTo` (immediateRender off), fix each `gsap_check` overlap warning, render with `--prime 0.25` |
| Element visible before its entrance | no pre-film state | `K.init(el, {autoAlpha: 0})` |
| `!=` or `->` drawn as one glyph | JetBrains Mono ligatures | keep `.mono` (`font-feature-settings: "calt" 0, "liga" 0`) |
| Wrong widths, text overflowing at frame 0 | measured before fonts loaded | measure inside `Film.build` (READY waits for fonts) |
| Render at 1-2 fps | SVG filters, many full-screen layers, `backdrop-filter` | gradients and stacked strokes; draw atmosphere in the canvas |
| `phrase "x" is not in its say text` | `at('...')` after the script changed | re-voice, then update the phrase |
| World text unreadable | camera scale too small | keep the subject's view at scale >= 0.8 (bigger screen box, narrower panel beside it); `gsap_check` warns < 26 px, `legibility.py` fails it |
| A chapter card sweeps over a panel that is still fading out, or the new chapter's panel or caption shows under the leaving card (LC 739 chapter 4) | content timed at the chapter start, inside the card window | hide left-side panels (and fade a left-side graph) by `K.cardIn(n)`, show new ones from `K.cardClear(n)`; `gsap_check` lists each case |
| `legibility.py` flags dim code or a faint label | text dimmed by opacity below 4.5:1 (code once dimmed to 0.42, question words to 0.22) | dim no further than the kit does (0.75 code, 0.5 unspoken words, `--dim` labels); mark focus with a bar or colour |
| Things drift between preview and render | `Date.now()`, rAF, CSS animations | only timeline tweens and `K.everyFrame(t => ...)` |
| Token stays on screen after a scene | nothing hides it | `G.hideToken(t)` / `K.fadeOut(el, t)` at the scene change |
| A burst covers a label or leaves the frame edge | placed by eye at one camera view | put bursts in empty screen space; `gsap_check` audits every burst (`K.moments`) |
| The MP4 is huge (30+ Mbit/s) | something high-frequency changes every frame (animated grain, noise, sparkle) | keep textures still; the template's grain is fixed to the screen (37 -> 5 Mbit/s measured) |
| Text in the caption band | content placed below y = 900 | keep the subject in `K.SAFE` (96 px margins, bottom 900) |
| Fonts 404 / blank page | `npm run vendor` not run | run it; `gsap_check` lists failed requests |
| Overlap warning between a size tween and a colour tween on one SVG element | the fight detector keys on element + property, and `attr: {...}` counts as one property | tween geometry through `attr`, colour through `fill`/`stroke` (CSS), or use one `K.channel` per property group |
| Overlap warnings on a fast counter | `meter.to` pulses for 0.4 s each time | `meter.to(t, v, d, {pulse: false})`, or `K.channel(meter.val)` |
| A dashed stroke will not draw on | DrawSVG sets `stroke-dasharray` itself, replacing the dash pattern | fade dashed strokes in (or draw a solid stroke, then swap) |
| A full-frame decorative SVG in `#ui` is flagged off the safe area and overlapping everything | `gsap_check` measures each top-level screen element's box | trim the SVG to its content, or mark it `data-qa="skip"` if it is decoration |
| The question card hides a wide subject | the default card is 800 px wide at mid-height | `K.question(L.q1, {n: 1, banner: true, x: 96, w: 1728, cy: 258, size: 46})` |
| A burst in Bangers shows `O(n)` as `O(N)` | Bangers has capitals only | `K.callout` now sets lowercase letters in Inter Black; still keep longer case-sensitive text (O(n log n)) in a note or the caption |

## 8. Laptop differences

- Chrome: `capture.mjs` looks for Chromium in the usual places (including macOS Google Chrome); otherwise
  `CHROMIUM=/path/to/chrome`, or `npx playwright install chromium` once (fine on a laptop, not here).
- More cores: `--workers` up to CPU count minus one. A GPU does not help screenshot capture much.
- Preview with audio: `python3 -m http.server 8765 --bind 127.0.0.1` in the project folder, open
  `http://127.0.0.1:8765/source/index.html`. Opening the file directly (`file://`) blocks the fonts.
- Voice: the delivered folder has `edge_voice_swap.py`, which re-voices the finished MP4 with an Edge neural
  voice (for example `en-IN-NeerjaNeural`) on a laptop where edge-tts is reachable; each line keeps its start
  time, so nothing is re-rendered.

## 9. Themes

The film keeps the kit's own dark palette (`original`) unless the brief names one of the 30 registry themes
(`references/themes.md`, `python3 $S/theme.py list`). To use one:

```bash
python3 $S/vstate.py set theme=<id>
python3 $S/theme.py emit <id> --format global --out source/theme.js    # window.THEME = {...}; carries theme-id + sha
```

`index.html` loads `theme.js` before `tokens.js`. The template ships `theme.js` as a stub (`window.THEME = null`),
which means `original`: tokens.js then keeps every value as the starter film was verified (its stills are
bit-identical). To go back, copy the stub from `$SKILL/assets/template/theme.js`. Re-emit after `themes.json`
changes; the visuals gate checks the sha.

Every kit colour comes from tokens.js, in four maps (all published as CSS variables too):

| Map | CSS | JS | Use |
|---|---|---|---|
| `color` (fills) | `--accent` | `K.C.accent`, `K.col('accent')` | areas, thick strokes, glows |
| `inks` | `--i-accent` | `K.ink('accent')` | text and thin strokes in a hue |
| `ons` | `--on-accent` | `K.on('accent')` | text on a filled shape of that hue |
| `look` (roles) | `--glass`, `--codeBg`, ... | `K.U.glass` | every other surface, line, shadow, sheen |

`K.vis(c)` is a hue as a visible stroke: in a theme, a fill under 3:1 against `bg` is moved towards its ink
until it reaches 3:1 (trails, comets, ripples, borders); `K.flashCol(c)` is a cell flash (a tint in themes).
In `original`, inks equal fills, every on-colour is the near-black and `K.vis` returns the fill.

Role mapping (`themed()` in tokens.js):

| Kit role | Theme token |
|---|---|
| `bg`, `bg2`, `panel` | `bg`, `bg2`, `panel` |
| `ink` / `dim` / `faint` (text) | `text` / `muted` / `dim` |
| `accent`, `mint`, `rose`, `amber`, `cyan`, `violet` (+ `warm`) | `accent`, `good`, `bad`, `gold`, `cool`, `violet`, `warm`; their inks and on-colours |
| `black` (comic outlines, HUD frame) | `deep` on dark themes, `text` on light ones |
| cards, decoder, meters, code, log, captions | mixes of `bg`, `panel`, `panel2` (`deep`/`bg2` for captions), nearly opaque |
| code syntax | `kw` violetInk, `ty` coolInk, `nu` warmInk, `st` goodInk, `fn` accentInk, `cm` muted, line numbers `dim` |
| chapter lights (`moods`) | key `lights[n]`, rim `lights[n+3]`; the chapter slab is that light with its on-colour, its gradient running away from the label |
| shadows | `shadow` (full on dark grounds, 0.4x on light) |

What changes on a light theme (`tone: light`): the chapter lights and bokeh screen instead of add (they
lighten, never smudge), grain is dark specks only, the vignette is a gentle `deep` edge, SVG halos are weaker,
the pool under the subject is white, shadows are soft. On every theme: code lines outside the focus are not
dimmed (the solved inks have no headroom for opacity; the bar marks the focus), and unspoken question words
are the `dim` ink instead of half opacity.

Check a theme the same way as the original: shoot the stills and run `legibility.py` (0 failing).

