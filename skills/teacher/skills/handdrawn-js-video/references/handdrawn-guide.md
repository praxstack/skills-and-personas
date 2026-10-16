# Hand-drawn canvas guide

Plain JavaScript on one 2D canvas. Every frame is drawn from scratch by `renderFrame(t)`, a pure function of
`t`: no clock, no `Math.random`, no state carried between frames. That is what lets `capture.mjs` render any
frame on any worker in any order, and what makes the hand-drawn feel controllable: line boil, stop-motion
jitter and stroke-on drawing are all functions of `t` and a seed.

Contents: [Setup](#setup) · [Project anatomy](#project-anatomy) · [Timing API](#timing-api) ·
[Kit catalogue](#kit-catalogue) · [Recipes](#recipes) · [Styles](#styles) · [Themes](#themes) · [Rendering](#rendering) ·
[Gotchas](#gotchas) · [Laptop differences](#laptop-differences)

## Setup

Nothing to install here. The template ships its own pinned files, so a project is one copy:

```bash
cp -r $SKILL/assets/template source        # in the project folder
```

| Piece | Version | Where |
|---|---|---|
| opentype.js (glyph outlines for stroke-on lettering) | 2.0.0 | `source/vendor/opentype.min.js` (MIT) |
| @fontsource/patrick-hand (body hand lettering) | 5.3.0 | `source/fonts/patrick-hand-latin-400-normal.woff` |
| @fontsource/caveat-brush (titles, headlines, callouts) | 5.3.0 | `source/fonts/caveat-brush-latin-400-normal.woff` |
| @fontsource/caveat 700 (the whiteboard style's lettering) | 5.3.0 | `source/fonts/caveat-latin-700-normal.woff` |
| @fontsource/jetbrains-mono 400 + 700 (code, table digits) | 5.3.0 | `source/fonts/jetbrains-mono-latin-*.woff` |
| Playwright (only `capture.mjs` uses it) | 1.56.1 | `playwright-core` in `source/node_modules` (`npm ci` in phase 3) |
| Chromium | 1194 | `/opt/pw-browsers/chromium` (found automatically) |

`source/package.json` pins the same versions. To re-vendor or upgrade: `cd source && npm i && npm run vendor`
(about 2 s here, 6.6 MB of node_modules you do not ship). Fonts are WOFF, not WOFF2, because opentype.js reads
WOFF without a decompressor. Google Fonts is blocked in the sandbox and never needed.

Preview while building (optional; stills are the real check):

```bash
python3 -m http.server 8000      # from the project folder, then open http://localhost:8000/source/index.html
```

Click to play with `voice/narration.wav`; space pauses, left/right seek 2 s, number keys jump to chapters,
`?t=31.5` starts at a time, `?style=chalk` previews another style. Stop the server when done.

## Project anatomy

```
source/
  index.html        canvas #c (1920x1080) + script tags in load order; never needs editing
  timing.js         window.TIMING, written by voice.py --emit source/timing.js (do not edit)
  theme.js          window.THEME: null (original) or a registry theme emitted by theme.py (see Themes)
  style.js          STYLE_NAME ('paper' | 'chalk' | 'blueprint' | 'whiteboard') and every colour, font, size, boil rate
  kit/styles/       the style interface (index.js) and one file per extra style (whiteboard.js); see Styles
  scenes.js         THE FILM: buildFilm() declares every element, keyed to line ids. Replace this file.
  main.js           page contract (READY, TOTAL, renderFrame, CAPTURE_SELECTOR) + preview player
  kit/core.js       maths, easing, seeded noise, timing API, boil, pop, layers, camera
  kit/ink.js        textures, backdrop, rough strokes, cut-outs, sprites, cards, tags, stamps
  kit/type.js       font loading, stroke-on hand lettering, hand-drawn symbols, monospace code
  kit/parts.js      captions, chapter labels, title card, question card, callout, stamp, label, arrow, chip, scenery
  kit/graph.js      the persistent subject (weighted digraph) and the travelling token (paper plane)
  kit/boards.js     input note, code card, dry-run table, complexity ladder
  kit/mascot.js     Pip and the paper plane
  fonts/ vendor/    pinned local files (see Setup)
```

A new film edits `scenes.js` (and maybe `style.js`). The kit stays; extend it rather than drawing one-offs in
scenes when a piece could be reused. The shipped `scenes.js` is the full mini film (LC 787, all 14 line ids):
read it first, it is the best example of every recipe below.

Draw order each frame: backdrop (parallax 0.35) → `back` layers (scenery, own depth) → `world` layers under the
camera, by `z` → `screen` layers (captions, chapter labels, question cards) → light, vignette, grain. The
backdrop and scenery follow the camera's keyed moves but not its idle drift, so they are pixel-still between
moves (cheap to encode); the world drifts gently so holds never freeze.

## Timing API

`voice.py` writes `timing.js`: `{total, fps, width, height, chapters: [{n, name, start, end}], lines: [{id,
chapter, scene, start, voiceAt, voiceDur, think, end, cap, say}]}`. Scenes never use raw seconds for story beats:

| Helper | Returns |
|---|---|
| `L.p3` | the line object; unknown id throws with the list of valid ids (READY fails, capture prints it) |
| `vAt('p3', f)` | time `f` (0..1) of the way through line p3's spoken words |
| `vEnd('p3')` | last word (the think pause starts here) |
| `lStart('p3')`, `lEnd('p3')` | the line's whole slot (lead-in to the end of its pause) |
| `sayAt('p3', 'one stop', off)` | estimated moment a phrase is spoken (character position; within ~0.3 s) |
| `chapterStart(n)`, `chapterEnd(n)` | chapter bounds; the chapter's corner label pops 0.5 s before the start and is written by it |
| `inLine(t, id)`, `lineAt(t)`, `chapterAt(t)` | queries inside a draw function |
| `TIMING_.total` | the film length (the render is exactly this long) |

Small offsets in seconds (`+ 0.3`) are fine for choreography between beats. At boot, ids that no scene reads
are printed as a console error: every line must change something on screen.

Motion helpers (kit/core.js): `P(t, a, d, ease)` progress 0..1; `env(t, a, b, fi, fo)` in-hold-out;
`track(t, [[t, v...], ...])` keyframes; `ticker(t, t0, d, a, b)` counting number; `pop(t, t0, d)` →
`{s, sx, sy}` squash-and-stretch spring; `popEnv(t, a, b)` pop in, shrink out; `Ease.{out, inOut, back,
expoOut, ...}`; `rnd(seed, k)` and `noise1(seed, x)` seeded randomness; `boilSeed(id, t)` changes 8-12x/s.

## Kit catalogue

Positions are `[x, y]` world units or a function `t => [x, y]` (follow something that moves). Every element
takes `at` and `until`; `z` orders layers. Boards take `keys` from `slideKeys(x, y, at, out, from, to, rot)`.

| Call | What it draws | Example |
|---|---|---|
| `captionBand()` | current line's `cap`, 2 lines max, bottom 180 px; leaves in chapter gaps | `captionBand();` |
| `chapterLabels({skip})` | torn label "01 · The problem" pops into the top-left corner in the gap (the old one slides off left as its chapter ends), is written by the chapter start (before its caption and first content) and stays as the lower third; it never sits over content | `chapterLabels({ skip: [0] });` |
| `titleCard({lines, kicker, at, until, stamp, stampAt})` | big torn card, brush title written on | see scenes.js intro |
| `questionCard(q, a, {n})` | Q badge, question written, countdown ring for q's `think`, answer + check | `questionCard('q1', 'a1', { n: 1 });` |
| `callout(text, pos, {at, until, size, colors})` | comic burst with action lines, pops | `callout('700!', gw(440,-270), { at })` |
| `stamp(text, pos, {at, until, size, color, shake})` | rubber stamp slams in (optional camera shake); heavy lettering in the colour's text shade on a cream slip, so it reads on any backdrop | `stamp('TOO MANY STOPS', p, { at, shake: 6 })` |
| `label(text, pos, {at, until, font, size, color, align, rot, halo, strikeAt})` | written-on hand lettering; `strikeAt` pens a line through it | `label('400 · 2 stops', p, { at, strikeAt })` |
| `arrow([from, to], {at, dur, bend, color})` | rough arrow drawn on | `arrow([[600,300],[800,420]], { at })` |
| `circle(pos, rx, ry, {at, color})` | pen loop around something | `circle([900,500], 80, 40, { at })` |
| `strike(p1, p2, {at})` | pen strike line | `strike([700,400],[900,400], { at })` |
| `chip(text, from, to, {at, dur, size})` | paper tag flies on an arc (text → picture) | `chip('100', a, b, { at })` |
| `scenery()` | paper hills and clouds with parallax (paper style only) | `scenery();` |
| `graph({nodes, edges, r, z, bend})` | the subject; `edges: [[u, v, w, bend?], ...]` | see below |
| `token(g)` | paper plane (Pip aboard) flying routes | `const plane = token(g);` |
| `note({w, h, rule, keys})` | ruled input note; `.line(r, text, at, {x, color, size})`, `.hl(r, {at, until})`, `.ring(r, {at})`, `.spanXY(r, i0, i1, t)` | decoder |
| `codeCard({code, size, lh, padT, padB, title, keys})` | code card (size 30-36, default `S.size.code` 32); `.reveal(a, b, at, dur)`, `.focus(a, b, {at, until})`, `.lineXY(n, t)` | code walkthrough |
| `table({cols, rows, cw, rh, hh, labelW, headSize, labelSize, at, keys})` | grid draws on (header chips `S.size.head`, row labels `S.size.rowLabel`); `.cell(r, c, text, at, {color, ring})`, `.row(r, vals, at, stagger)`, `.hlRow(r, {at, until})`, `.cellXY(r, c, t)` | dry run |
| `ladder({w, rungH, n, keys})` | complexity ladder; `.rung(i, {name, cx, cost, at, color})`, `.pick(i, at)` | approaches |
| `camera(keys, {drift})`, `shake(at, amp, dur)` | `[t, x, y, zoom, rot]` = world point at screen centre | see Recipes |
| `world(z, fn)`, `screen(z, fn)`, `back(depth, z, fn)` | your own layer: `fn(ctx, t)` | custom drawings |

Graph methods (all chainable, all times in seconds): `g.place([[t, x, y, scale], ...])` where the map sits;
`g.showNodes(t0, stagger)`, `g.showEdges(t0, stagger)`, `g.showEdge(e, t0, dur, tagAt)`; `g.mark(i, text,
{at, until, side: 'down'|'up', color, size})` (default `S.size.mark`; in `paper` it is lettered on a torn paper slip); `g.ring(i, {at, until, dash})`; `g.glow(i, {at, until})`;
`g.hl(edges, {at, dur, until, color, dash, w, glow})` draws edges on in order; `g.fire(edges, {at, gap, color})`
pulses along edges; `g.dim({at, until, alpha, edges, nodes})`; `g.relabel(i, text, at)`. Lookups:
`g.route([0, 1, 3])` → edge indices, `g.edgeIndex(u, v)`, `g.nodeXY(i, t)`, `g.tagXY(e, t)`, `g.xf(t)`.
Edges bend outward from the graph's centre automatically (antiparallel pairs split); override with a 4th
number. Weight tags (`S.size.tag`, never scaled below `S.size.tagMin` when the map shrinks) sit beside their edge
on the outer side.

Token: `plane.fly(route, {at, legDur, pause, trail, until, hold, cost, stopLabel, dash, ghost, expr})`
returns the landing time; `plane.park(i, {at, until, side: 'left'|'right'|'up'})`; `plane.poseAt(t)`.

Low level (kit/ink.js, kit/type.js) for custom layers: `inkLine(ctx, pts, {color, w, prog, from, alpha, seed,
t, dash, glow, tip})` is the one rough stroke (pass `t` so it boils; it multiplies the alpha of the group it is
drawn in, so a fading board fades its lines too); `inkArrow`, `inkEllipse`, `inkRect`,
`hatch`; `cutout(g, pts, color)` paper piece with torn rim and shadow; `sprite(w, h, ox, oy, fn)` + `blit(ctx,
sp, x, y, {sx, sy, rot, alpha, jit, t})` bake once and jitter; `drawCard`, `tagSprite`, `stampSprite`,
`discSprite`; `drawText(ctx, text, x, y, {font, size, color, align, write, t, boil, halo, maxW, vivid})` with
`^{...}` superscripts; `drawMono(ctx, text, x, y, {size, colors, write})`; `curvePts`, `quadPts`, `polyAt`.

## Recipes

**Decode an input.** Write the raw input on a note line by line, highlight each entry as it is read, fly its
value to the subject, then draw the edge (scenes.js chapter 1):

```js
FLIGHTS.forEach(([u, v, w], e) => {
  const te = fly0 + e * 0.48, text = `[${u}, ${v}, ${w}]`;
  nt.line(2 + e, text, te - 0.35, { x: 130, dur: 0.35 });
  nt.hl(2 + e, { at: te, until: te + 0.7 });
  chip(String(w), (t) => nt.spanXY(2 + e, text.lastIndexOf(' ') + 1, text.length - 1, t), (t) => g.tagXY(e, t), { at: te + 0.05 });
  g.showEdge(e, te + 0.1, 0.55, te + 0.62);
});
```

**Trace a route.** `const land = plane.fly([0, 1, 3], { at: vAt('p4'), trail: S.accent, cost: true,
stopLabel: 'stop' });` then `callout('700!', ..., { at: land + 0.05 })`. The trail stays until `until`.

**Reject an illegal route.** Ghost it, price it, strike it, stamp it, all after the legal answer landed:
`g.hl(g.route([0,1,2,3]), { at, color: S.bad, dash: true, glow: false })`, `label('400 · 2 stops', p,
{ color: S.bad, strikeAt })`, `stamp('TOO MANY STOPS', p, { at, shake: 6 })`.

**Think countdown.** `questionCard('q1', 'a1', { n: 1 })` reads the question line's `think` seconds for the
ring and writes the answer line's `cap` under it with a check. Put the visual hint for the question (a ring,
a dashed route) on the subject during the pause, and the reveal on the answer line.

**DP row update.** Show the old row, mark new cells `?`, fire the edge, fly the value into the cell, write it:
`rows.cell(1, c, '?', vEnd('q2') + c * 0.1, { color: S.inkSoft })`; `g.fire(0, { at })`; `chip('100', (t) =>
g.tagXY(0, t), (t) => rows.cellXY(1, 1, t), { at })`; `rows.cell(1, 1, '100', at + 0.6, { ring: true })`.

**Code walkthrough synced to lines.** `code.reveal(1, 5, at, 0.7)` types lines; `code.focus(6, 11, { at:
sayAt('c1', 'Round zero'), until })` swipes a highlighter, points the gutter arrow and dims the rest. Pair
each focus with the table row it fills (`dry.hlRow(1, ...)`) and the edges it relaxes (`g.fire`).

**Camera.** One `camera([...])` call for the film. Push in on the beat (zoom 1.04-1.07 over ~0.6 s), hold,
ease back before the next chapter. Keep the zoom near 1 while a wide board (code card) is on screen. A slow
drift is added automatically so holds never freeze; `stamp(..., { shake: 6 })` adds a hit.

**Move the subject between chapters.** `g.place` keys: the map steps aside for the brute-force tree, centres
under question cards, shrinks top-right for code. A helper `gw(x, y)` turns map coordinates into a moving
world point so labels and callouts follow the map.

## Styles

A style is how things are drawn: strokes, fills, textures, labels and motion. It is its own axis, independent of
the theme (the colours): every style works with `original` and with the 30 registry themes, and one `scenes.js`
serves every style, because scenes only call the kit and read `S.*` tokens.

**Pick one** in the brief's Style section, record it, and set it in the film:

```bash
python3 $S/vstate.py set style=whiteboard          # the record; the default is paper
sed -i "s/^const STYLE_NAME = .*/const STYLE_NAME = 'whiteboard';/" source/style.js
```

Preview another style without editing with `index.html?style=whiteboard` (the render always uses `STYLE_NAME`).

| Style | Looks like | What it changes | Cost here (4 shared cores) |
|---|---|---|---|
| `paper` (default) | warm paper, cut-outs with torn white rims and drop shadows, washi tape, Pip in a paper plane, parallax hills and clouds | the baseline: boil 10 fps, stop-motion jitter | baseline |
| `chalk` | slate board, chalk strokes, no shadows | strokes through a speckled chalk mask, boil 8 fps, plane as line art | about paper |
| `blueprint` | drafting blue with a grid, white line work | thinner lines, boil 12 fps | about paper |
| `whiteboard` | marker on a whiteboard; a dark glass board on dark themes | see below | about 1.4x paper (8.2 vs 11.6 frames/s per worker here) |
| `papercraft-riso` | cut-paper pieces printed on a risograph: halftone spot inks, out of register, stop-motion drops | see below | about 1.3x paper (7.7 vs 10.0 frames/s per worker here) |
| `watercolor` | layered watercolor washes with a brush-pen ink line, on cold-press paper | see below | about 2x paper (122 vs 59 ms per frame here) |

`whiteboard` (`kit/styles/whiteboard.js`): the graph draws itself. Every line is a marker stroke with a pressure
taper (a filled outline, perfect-freehand's idea, no library), revealed along its length when the scene keys it;
graph nodes are drawn on too (ring, then hachure, then the label written). A marker follows the tip of whatever is
being drawn or written and is hidden between strokes. Glowing strokes (the highlighted route, the plane's trail)
become a hachured band; nodes, bursts and stars are hachure-filled. Labels are Caveat Bold
(`fonts/caveat-latin-700-normal.woff`, @fontsource/caveat 5.3.0, OFL) with a thin outline for marker weight. The
board carries faint ghosting of old marker and is locked to the world (`backDepth: 1`), so drawings never slide on
it during camera drift; boards are sheets held by magnets; settled strokes boil by under a pixel at 10 fps (3
frames at 30 fps) and strokes being drawn hold still; nothing jitters or floats. Chapter changes are an eraser
that wipes the old corner label off and sweeps the board, then the new label is drawn in the corner with the pen
(written by the chapter start, like paper's). On a light theme the board is the theme's paper lifted toward
white; on a dark theme it is the theme's ground with glass reflections and light inks. Sizes: Caveat's x-height is
0.37 em (Patrick Hand 0.48), and `legibility.py` measures a lower-case word by its x-height, so `fontSize` draws
hand text at `max(1.12 x size, 0.6 x size + 29)` (the 40 px label size becomes 53 px) and brush text 10% larger,
and the corner label sits at 0.62. Layouts written for paper still fit; check long lines on notes and cards.

`papercraft-riso` (`kit/styles/papercraft-riso.js`): every node, tag, chip, card and burst is a cut piece of card
stock with a light edge toward the light (top left), a dark edge away from it, a soft blurred shadow and paper
fibre. Coloured pieces are printed in halftone: each ink is its own dot screen at its own angle (A 15°, B 75°),
multiplied over the stock (screened on the dark stock of a dark theme), and 1 to 3 px out of register with the cut,
so a sliver of bare stock shows on one side and two-ink overprints fringe. Lines are solid ink with a little ink
starvation; a glowing stroke (the route, a trail) gets a halftone band printed under it, out of register with the
line. Three spot inks come from the theme: the key (its text ink), ink A (its accent) and ink B (the hue furthest
from the accent: teal on `original`, gold on Catppuccin). The city palette, the scenery hills and clouds, the
rules and the tape are A, B and their overprint; `good`, `bad` and `gold` still print as their own drum where a
scene uses them for meaning, because no three inks reproduce the accent, red and green on every registry theme.
Text is never halftoned: it prints as solid, registered ink in Fredoka (`fonts/fredoka-latin-600/700-normal.woff`,
@fontsource/fredoka 5.3.0, OFL), set at 0.95 (hand) and 0.78 (brush) of the size because it is wide; nodes carry a
pasted stock window for their label, and tags, slips and a burst's middle are plain stock. Live strokes and bands
shift by a per-shot offset (a new shot at every chapter, never per frame), each piece keeps the register of its own
print, and small registration marks in the frame corners show the offsets. Motion: pieces drop in from above
(bigger and a little turned), land with a small overshoot and settle, on 12 fps steps (the `pop` hook returns a
`rot` that every popping piece applies), boards slide on the same steps (`stepFps`), and nothing jitters, floats or
boils. The backdrop is a bright stock with a halftone vignette in the key ink that fades out 120 px inside the frame.

`watercolor` (`kit/styles/watercolor.js`): every node, burst, star, hill and cloud is a wash painted with Tyler
Hobbs' method on plain Canvas 2D: the shape is deformed by recursive midpoint displacement (each vertex has its own
variance), then about 30 layers, each deformed again, are laid at about 4% opacity (7% on dark themes) through a
random circle mask, deepening toward the ink in groups of five. Each layer leaves extra pigment along its own edge,
so the edge pools darker while the outside stays soft; the layers are softened by a sub-pixel blur, then pigment
lifts off the paper's peaks and settles in its valleys (granulation). Each wash is painted **once** into a cached
canvas (`cached`) and only drawn after that; never re-paint the layers per frame. Graph nodes bloom: the cached
wash is revealed through a growing, irregular wet front, then the ink ring is drawn and the label written (the
`node` hook). State is shown by wash colour: a glowing node (the target) gets a halo wash that blooms behind it (the
`glow` hook), the highlighted route and the plane's trail get a wash along their length in their colour, painted
once per edge in a canonical frame and revealed as the line draws, and relaxations are a wet gold stroke. Every
line is a brush-pen stroke with a pressure taper (perfect-freehand's idea, no library): it lands thin, swells and
lifts off thin, and it never boils. The paper is cold-press: a tileable height field lit from the top left (the
tooth) with a few pale background washes. Text pieces (tags, slips, cards, the caption band, chapter labels) are
deckle-edged scraps of the same paper with a pale wash and a loose ink border, so text stays crisp ink on a light
ground; a burst's middle is paper left bare inside the wash. Pieces land a touch large and settle, without squash or
bounce (the `pop` hook, never drawn smaller than their size, so a label is never caught under 26 px); nothing
jitters, floats or boils. Fonts are the paper ones; flying chips are 40 px (`size.chip`), as in papercraft-riso. On a dark theme the paper is the theme's ground
and the washes are light pigment on it (like gouache on black paper), dense enough that labels on nodes read in
the dark ink.

**The style interface** (`kit/styles/index.js`, kept small on purpose; the next styles plug in the same way). A
style is one file that calls `defineStyle(name, def)` and is listed in `index.html` before `style.js`:

- `palette(P, T, Colour)` (required) returns the whole `S` token set. `P` is the base palette (`paper` unless
  `def.base` says otherwise), already recoloured by `themeStyle` when a registry theme is on; `T` is the theme or
  null. Derive every colour from `P` and `T` with `Colour.mix/alpha/ensure`; never write new colour literals, and
  re-solve text colours with `Colour.ensure` against the style's own surfaces.
- Optional `font` and `size` merge over `FONT` and `SIZE`. Optional tokens the kit reads: `fontFiles`,
  `fontSize(font, size)`, `textStroke`, `textBoil`, `backDepth`, `float`, `stepFps` (absent = paper behaviour).
- Optional hooks, each replacing one piece of kit drawing when present: `beginFrame(t)`, `stroke(ctx, pts, o)`
  (every `inkLine`), `penTip`, `cutout`, `card`, `disc`, `node`, `glow`, `backdrop`, `overlay`, `plane`,
  `chapterLabels`, `pop` (the entrance; its optional `rot` is applied by every piece that pops). The kit calls them as `if (STYLE.x) return STYLE.x(...)`; the built-in styles define none, which is why `paper`
  renders pixel for pixel as before. Hooks run inside `renderFrame(t)`: derive everything from `t` and seeds,
  and reset per-frame state in `beginFrame` (never carry it to the next frame).

Change `S.node` for the subject's palette, `S.accent/good/bad/gold` for meaning, `grainBoil` (grain flicker, bigger files), `SIZE` for type sizes (quality
bar: headline 72-96, body 40-48, captions 38-44, code 30-36), `boilFps` (8-12), `jitter`, `stroke.rough`.

**Text size and colour (what `legibility.py` checks: nothing under 26 px, and 4.5:1 contrast for every text at every size, no tolerance).**
`SIZE` in style.js: title 118, headline 84, chapter 88 (corner label at 0.56), body 44, label 40, small 34,
caption 42, code 32, table 46, tag 34, mark 44, chip 34, head 32 (table header chips), rowLabel 36. The hand
fonts are short (Patrick Hand x-height 0.48 em, Caveat Brush lower case 0.40 em), so a lower-case word like
`src` measures about two thirds of its font size: keep words on the board at `S.size.label` (40) or more and
nothing below `S.size.small` (34). Colours: the bright meaning colours (`S.accent`, `S.good`, `S.bad`, `S.gold`,
`S.cool`, `S.lilac`, `S.sky`) are for fills, strokes and highlights; when one is passed as a text colour,
`drawText` (and stamps) letter it in its darker text shade from the theme's `txt` map, which keeps at least
4.5:1 on the cards and on the darkest paper a label sits on (the mottled tan under the vignette, about `#C0B298`;
pass `vivid: true` for decoration that is not meant to be read). Secondary
text uses `S.inkSoft` (paper `#292A3A`, nearly the ink, because it must reach 4.5:1 on that tan), never `S.inkFaint` (lines only). De-emphasised code lines are mixed
toward `S.codeDim` (paper `#45475D`, about 8:1 on the card), not faded, and the focused lines turn bold under
the highlighter. The paper backdrop's vignette is `.28` and its deep blobs are scaled by `deepBlob` 0.6 so the
open paper never gets dark enough to sink ink text.

## Themes

The 30 registry themes (`references/themes.md`, `python3 $S/theme.py list`) recolour the chosen style. The theme
file is `source/theme.js`, loaded before `style.js`; the template ships it as `window.THEME = null`, which means
`original` (the style's own palette, pixel for pixel). To use a theme:

```bash
python3 $S/vstate.py set theme=catppuccin-mocha
python3 $S/theme.py emit catppuccin-mocha --format global --out source/theme.js    # back to original: copy the template's theme.js
```

`themeStyle()` in `style.js` maps the tokens onto the style's roles; scenes and kit only read `S.*`, so nothing
else changes. Light themes keep the paper look (white cut-outs on a tinted paper); dark themes become dark
paper: the same cut-outs, torn rims, tape and shadows on the theme's ground, lettered in light ink.

| Kit role | Theme token |
|---|---|
| paper `bg`, mottling `bgDeep` / `bgLight` | dark: `bg`, `deep` / `bg2`; light: `deep` (the paper), `deep` / `bg` |
| `card` (notes, code card, tags, slips, caption band) | dark: between `bg` and `panel`; light: `bg` lifted toward white |
| `cardEdge` (torn rim) | dark: `card` mixed toward `text`; light: white |
| `ink`, `cardInk`, `inkSoft`, `inkFaint` | `text`, `text`, `muted`, `text` at .32 (lines only) |
| `accent`, `cool`, `gold`, `lilac`, `sky`, `good`, `bad`, `warm` (fills) | `accent`, `cool`, `gold`, `violet`, `accent`, `good`, `bad`, `warm` |
| `txt` (text in a meaning colour) | the matching `<hue>Ink` |
| `node` (the subject's discs) | `warm`, `cool`, `gold`, `violet`, `accent`, `bad`, `good`, warm+gold |
| `nodeInk`, `S.inkOn(fill)` (labels on fills: discs, header chips, bursts) | `on<Hue>`, else the better of `text` / `bg` |
| `syntax`, `codeDim` | the inks (`accentInk` keywords, `warmInk` types, `goodInk` numbers, `violetInk` strings, `goldInk` calls), `dim` |
| `hl` (highlighter), `glow`, `burst`, `tape` | `gold` at low alpha, `gold`, `warm` + `gold`, `gold` |
| `shadow`, `vignette`, chapter shade (`shade`) | dark: black, `deep`, `deep`; light: `shadow` at low alpha (never black) |
| grain | `screen` on dark themes, `multiply` on light ones, lower strength |
| key light | dark: tinted per chapter from `lights`, eased across each chapter change; light: soft white |
| glows (`inkLine` `glow`, fire pulses) | dark: glow; light: a soft drop shadow (`glowShadow`), never a smudge |
| Pip's clothes, the paper plane, hills, clouds | `cool` / `warm` / `gold` / `accent`; plane and clouds from `card` (light) or `text` (dark) |

Text colours get headroom: the hand fonts and the thin 32 px mono measure well under their colour's nominal
ratio, so `style.js` lifts each text colour (same hue) until it clears 8.5:1 (`ink`), 6.5:1 (`inkSoft`, code)
or 6:1 (`txt`, on-fill labels) on the paper, the card and a highlighted card row (`Colour.ensure`). Check a theme
exactly like the original: render the stills, run `legibility.py`, and look at them. The 30 themes were proven
on the `paper` style (the starter film); `chalk` and `blueprint` take the same mapping but were not measured.

## Rendering

Commands run from the project folder; capture.mjs serves `source/` over http and drives headless Chromium.

```bash
node $S/capture.mjs --page source/index.html --stills lines --timing timing.json --stills-dir stills
node $S/capture.mjs --page source/index.html --stills 16.6,31,54.9 --stills-dir stills     # extra moments
node $S/capture.mjs --page source/index.html --bench 3                                     # fps + ETA
mkdir -p build && nohup node $S/capture.mjs --page source/index.html --out build/silent.mp4 \
  --workers 4 --crf 21 --max-minutes 100 > build/render.log 2>&1 &
```

Stills take about 0.3 s each. Measured here on 4 CPUs shared with eight other render jobs (load average
25-43): `--bench` 6.8-8.2 frames/s for one worker; the mini film's earlier 62 s cut (1867 frames) in 10.1 min with 2 workers
(3.1 frames/s overall). On a quiet 4-core machine expect 25-30 frames/s with 4 workers (the bake-off film
rendered at about 30), so a 6-minute film (10,800 frames) takes 6-8 minutes.
Segments (20 s) are recorded in `build/segments/manifest.json`; if a run stops (budget, crash, 2-hour cap),
run the same command again and finished segments are skipped. Any edit to `source/` restarts the segments.
Page errors and `console.error` from the page are printed in the log.

## Gotchas

- **`!=` drawn as `≠` in code.** JetBrains Mono has ligatures and `fillText` applies them. Symptom: `≠`, `=>`
  arrows, merged `->` in code. Fix: draw code only with `drawMono`/`codeCard` (one glyph per cell).
- **Symbol in the wrong font or a box.** Patrick Hand and Caveat Brush lack `→ ← ∞ ≤ ≥ ≠ ✓ ✗ ★`; the kit draws
  those as hand strokes (`HAND_GLYPHS` in kit/type.js). Other symbols fall back to a system font: add them to
  `HAND_GLYPHS` or write the word.
- **Seams in the paper texture.** Tiles must wrap: draw every fibre at +/- the tile size (`wrapDraw`).
- **Flicker at segment joins or A-B-A flicker in QA.** Something reads a clock or `Math.random`, or carries
  state between frames. Use `rnd(seed, k)`, `noise1`, `boilSeed(id, t)`; derive everything from `t`.
- **Lines shimmer instead of boil.** A seed that changes every frame. Pass `t` and a fixed `seed` to ink
  functions; they step the seed at `S.boilFps`.
- **Capture fails at READY with "unknown line id".** A scene reads an id not in script.json; the message lists
  the valid ids. `sayAt` throws the same way when the phrase is not in the line's `say`.
- **Blank or fallback text in a browser preview.** Opened as `file://`, the font fetch fails. Serve over http.
- **Camera push cuts off a board or caption-band text.** Keep text inside x 96..1824, y 96..900 at the zoom
  in use; check the still at the end of each push.
- **Weight tag sits on its edge or another tag.** Give that edge an explicit bend (`[u, v, w, 0.18]`) or move
  a node; tags follow the bend side.
- **The MP4 is 10+ Mbit/s.** Something full-frame changes every frame. Measured on 6 s of the mini film:
  grain moving on boil frames + drifting backdrop + crf 17 = 13.6 Mbit/s; still grain = 9.3; backdrop and
  scenery on the still camera = 6.6; plus `--crf 21` = 3.3 (no visible difference). Keep `grainBoil: false`.
- **Something never leaves.** Elements default to `until: Infinity`; give boards an `out` in `slideKeys` and
  labels an `until`, or chapters pile up.
- **A new board hides under the chapter label.** The corner label owns roughly x 96..640, y 96..184 of the
  screen; boards start at y 196 or lower and question cards at x 470 for that reason.
- **`legibility.py` flags a text.** Open its marked copy in `stills/legibility/`. Too small: use the `S.size`
  token for that kind of text (short lower-case words need `label` size or more). Too faint: give it a text
  shade (any bright meaning colour passed to `drawText` gets one), letter it on a card or slip instead of the open
  paper, or keep it off a busy texture. Still writing on when the still is taken: land it earlier (start it
  0.3-0.6 s before the word is spoken, `dur` 0.45-0.6), never shrink or fade it.

## Laptop differences

- Playwright: phase 3's `npm ci` installs the pinned `playwright-core`. It uses an installed Chrome (found on
  macOS and in the usual Linux paths, or `CHROMIUM=/path/to/chrome`); without one, `npx playwright install chromium`.
- Preview in a real browser (`python3 -m http.server`); hardware is faster, so `--workers` can match cores.
- `edge_voice_swap.py` (in the delivered folder) re-voices with an Edge neural voice, which the sandbox blocks.
