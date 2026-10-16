# HyperFrames guide

HyperFrames (npm `hyperframes`, the HeyGen open-source renderer) turns an HTML page with a registered GSAP timeline
into an MP4: it loads `index.html` in headless Chrome, seeks `window.__timelines["main"]` frame by frame, and encodes
the frames with ffmpeg. This skill's template is one such page: a reusable kit plus two scene files.

## Contents

1. [Setup](#1-setup)
2. [Project anatomy](#2-project-anatomy)
3. [Timing API](#3-timing-api)
4. [Kit catalogue](#4-kit-catalogue)
5. [Recipes](#5-recipes)
6. [Rendering](#6-rendering)
7. [Gotchas](#7-gotchas)
8. [Laptop differences](#8-laptop-differences)

## 1. Setup

```bash
cp -r $SKILL/assets/template <project>/source
cd <project>/source && npm ci --no-audit --no-fund     # 7 to 12 s here; postinstall runs setup.mjs
```

Pinned in `package.json` (exact versions, lockfile shipped): `hyperframes 0.8.137`, `gsap 3.15.0`,
`@fontsource/inter 5.3.0`, `@fontsource/jetbrains-mono 5.3.0`, `@fontsource/bangers 5.3.0`. Node 22 or newer
(HyperFrames requires it). 81 packages, about 150 MB in `node_modules/` (never deliver it; `package.py` skips it).

`setup.mjs` (run by `npm ci`/`npm install`, or `npm run setup`) copies what the page loads into `vendor/`:
`vendor/js/` (gsap, DrawSVG, MotionPath, SplitText, Text, CustomEase; all free since GSAP 3.13, all in the plain
`gsap` npm package), `vendor/fonts/*.woff2` (latin subsets) and `vendor/fonts.css`. `vendor/` is generated: do
not edit it, re-run setup after changing font weights.

Environment (the render script sets these when unset; set them yourself for raw `npx hyperframes` calls):

| Variable | Value here | Why |
|---|---|---|
| `HYPERFRAMES_BROWSER_PATH` | `/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell` | no browser download in the sandbox |
| `HYPERFRAMES_SKIP_SKILLS` | `1` | stops the CLI offering to install its own agent skills |
| `HYPERFRAMES_NO_TELEMETRY` | `1` | no network calls during renders |

Check: `node $S/render_hyperframes.mjs --project . --lint` prints `lint: 0 errors, 0 warnings`.

## 2. Project anatomy

```
source/
  index.html          layers + script tags + the inline registration (do not restructure; see Gotchas)
  timing.js           window.TIMING, written by voice.py --emit source/timing.js (never edit by hand)
  scenes/subject.js   THIS film's data: graph layout, camera shots, input text, the exact compiled code
  scenes/film.js      THIS film's choreography: KIT.film() builds every tween, keyed to line ids
  kit/tokens.js       the one style file: palette, chapter light colours, fonts, sizes, safe area
  kit/core.js         timeline, timing lookups (KIT.L, KIT.cue), builders, tween helpers
  kit/*.js            camera, background, cards, captions, graph, decoder, question, code, table, ladder,
                      burst, widgets (catalogue below)
  style/kit.css       layout and look of the kit pieces (uses the CSS variables tokens.js writes)
  setup.mjs           copies vendor files out of node_modules
  package.json        exact pins; package-lock.json; hyperframes.json and meta.json (CLI project files)
```

A new film replaces `scenes/subject.js` and `scenes/film.js` only. Change the look in `kit/tokens.js` (colours,
fonts, sizes) and `style/kit.css`. Layers, back to front: `#bg` (lights, floor, bokeh), `#scene > #cam > #drift >
#world` (the persistent subject, moved by the camera; `#wsvg` + `#whtml`), `#hud` (+ `#hudsvg`; screen-space panels,
notes, bursts), `#chrome` (header, chapter tag, pips), `#fx` (grain, vignette, sweeps), `#cards` (title, stings),
`#caps` (captions, always on top).

## 3. Timing API

`timing.js` is the clock. Scenes read it through `KIT` (`const K = KIT, L = K.L` at the top of `film.js`):

| Expression | Meaning |
|---|---|
| `L.p3.start` / `L.p3.end` | the line's slot (includes its lead-in and think pause) |
| `L.p3.voiceAt` / `L.p3.voiceEnd` | the voice starts / stops |
| `L.q1.thinkEnd` | end of the think pause after a question |
| `K.cue(L.p4, 'the answer', 0.1)` | when a phrase of `say` is spoken (character-proportional, within ~0.3 s); throws if the phrase is not in `say` |
| `K.frac(L.p4, 0.5)` | halfway through the spoken part |
| `K.chapter(2).start` / `.end`, `K.chapters` | chapter slots (`n`, `name`) |
| `K.SC.ex1.start` | scene slots (the `scene` field of the script) |
| `K.T.total` | film length; the render is exactly this long |

`KIT.L.<id>` throws on an unknown id, so a renamed line fails loudly at lint/stills time instead of animating at
`NaN`. All tweens go on one paused timeline, `KIT.tl`, at absolute times. Small offsets (`+ 0.2`) are fine; a bare
number of seconds is not (re-voicing would leave the picture behind). `K.finish()` ends `KIT.film()`.

## 4. Kit catalogue

Tones are names from `tokens.js` (`accent`, `accentText` (the orange for text on a bright light), `good`, `bad`, `cool`, `gold`, `violet`, `ink`, `mute`, `dim`) or a hex.
`mute` (#B8B2A7) is secondary text, `dim` (#9C968B) the quietest text: both stay at least 4.5:1 on the panels and the
background, so de-emphasise with them (or with `tok.dimOpacity`, 0.8, which code lines and ladder rungs step back
to) and show focus with colour, weight or a highlight bar, never with near-invisible text.
Sizes are `tok.size` (px at 1080p): title 116, headline 84, body 44, caption 40, code 30, label 30, chip 30, world 32,
node 30. Nothing on screen goes under 26 px (legibility.py fails it); 30 is the floor the kit uses.
World coordinates are 1920x1080 in `#world`; HUD coordinates are screen pixels. Text in `#world` (node labels, weight
chips, tags) is counter-scaled: the camera sets `--inv` = 1 / zoom on `#world`, and `K.wfs(base)` /
`K.wscale(base)` / `K.wgrow(base)` keep it at least `tok.size.world` px on screen when a shot zooms out, so a graph
shrunk to a thumbnail keeps readable labels (give such shots enough zoom that the labels do not crowd).

| Piece | Call (one-line example) |
|---|---|
| Builders | `K.el('div', 'chip mono', parent, {left: 100, top: 40}, html)`, `K.svg('circle', {r: 9}, svg)`, `K.rand(seed)` (never `Math.random`), `K.decor(el)` (decorative: skipped by `--check`) |
| Tweens | `K.hidden(els)` at build, `K.show(el, t, 0.5, {y: 24})`, `K.hide(el, t)`, `K.pop(el, t)`, `K.pulse`, `K.shake`, `K.drawable(path)` + `K.draw(path, t, d)`, `K.count(el, t, d, a, b)`, `K.type(el, t, nChars)`, `K.riseChars(el, t)` |
| Changing value | `const v = K.stack(parent, {left, top, width, height}); v.to(t, '100', {color, mode: 'flip'})` (reversible). `mode: 'fade'` is sequential (old text out, then the new one in), so a changing label never shows two texts at once |
| Background | `K.background({floor: true, bokeh: 22, grain: true, vignette: true})`: per-chapter key/rim lights, canvas perspective floor, bokeh, grain, vignette; `K.sweep(t)` |
| Camera | `K.cam.init(shot)`, `K.cam(t, {cx, cy, zoom, sx, sy, tilt}, d, ease)`, `K.cam.push(t, d, 1.05)`, `K.cam.drift(9)`, `K.cam.toScreen(wx, wy, t)` |
| Header | `K.chrome({tag: 'LC 787', title})`: brand, chapter tag, chapter pips |
| Title | `const T = K.titleCard({kicker, lines: ['Cheapest Flights', 'Within K Stops'], at, flourish: true}); T.out(t)` |
| Chapter stings | `K.chapterCards({skip: [0], hold: 0.1})`: one sting per chapter; tag + pips update. It never covers content: at the previous chapter's last spoken word the subject layers (`#cam` world, `#hud` panels) fade out over 0.3 s, the card enters 0.3 s later over empty ground and leaves at start + hold (fading 0.3 s), then the subject fades back in over 0.25 s. Anything film.js brings in under the card appears with the layers after it has gone. `K.cardIn(n)` / `K.cardClear(n)` give the card's entry time and the time it has gone (subject layers returning): start a chapter's first entrances at `K.cardClear(n)`, not at its first line's `voiceAt`, so the subject is on screen when the chapter's voice starts (voice.py leads each chapter's first line by 1 s; qa.py's chapter-entry check measures it). Keep film-specific overlays outside `#cam`/`#hud` (such as the title card) out by the last word too |
| Lower third | `K.lowerThird('EXAMPLE 2', t, 3, {tone: 'gold'})` |
| Captions | `K.captions({emphasis: /(\b\d+\b|∞)/g})`: every line's `cap`, bottom band, two lines max, O(...) set in mono |
| Graph (subject) | `const G = K.graph({nodes, edges, r: 50})`; `G.nodesIn(t, 0.16)`, `G.edgeIn(i, t, d)`, `G.light(id, t, tone)`, `G.lightAll(t)`, `G.ring(id, t, tone)`, `G.pulse(id, t)`, `G.edgeTone(i, t, tone)`, `G.fire(i, t, tone, d)`, `G.route(ids, t, d, tone, {lightNodes, tint})` -> `{clear, dim, reject, end}`, `G.tag(id, 'START', t, tone, side)`, `G.edgeTag(i, 'FLIGHT 1', t, tone)`, `G.value(id, t, html, {side, tone})`, `G.dim(t, 0.28, keepIds)` / `G.undim(t)`, `G.idx(u, v)`, `G.pos(id)`, `G.mid(i)` |
| Mascot | `G.mascotAt(id, t)`, `G.hop([0, 1, 3], t, 1.0, {trail: 'good', onLand})` -> `{lands, end, trail}`, `G.blink(t)`, `G.look(t, dx)`, `G.mascotOut(t)` |
| Input decoder | `const D = K.decoder({rows: F.input, y: 206, fs: 30}); D.tok('e0', 1, '[0,1,100]'); D.hl('e0', t); D.fly('e0', t, 0.75, K.cam.toScreen(x, y, t + 0.75)); D.dimTok; D.show; D.hide; D.pos(id)` |
| Question card | `const Q = K.question({n: 1, line: L.q1, text}); Q.answer(L.a1.voiceAt); Q.out(t)` (ring counts `think` seconds) |
| Code panel | `const P = K.code({code: F.code, x: 96, y: 196, fs: 30, lh: 1.2, wrap: 58, title: 'solution.cpp'}); P.show(t); P.reveal(t, 1, 5); P.focus(t, [6, 7]); P.unfocus(t); P.lineY(n); P.out(t)`. Code is 30-36 px; `wrap` (columns) soft-wraps a long line on screen before its trailing `//` comment (the line keeps its number); `P.focus` steps the other lines back to `tok.dimOpacity` |
| Table / DP row | `const TB = K.table({x, y, cols: ['0','1','2','3'], colTitle: 'city', rows: ['old','new'], rowGap: 58, labelFs: 36}); TB.show(t); TB.rowIn(r, t); TB.fill(r, vals, t); TB.set(r, c, '100', t, {tone}); TB.mark; TB.strike(r, c, t); TB.arrow([0,0], [1,1], t, tone, '+100'); TB.center(r, c); TB.out(t)`. Headers and row labels are `labelFs` (30; 36 for short x-height-only words like "new"); an arrow between two cells of one row arcs under the row (`{bend}` = depth) |
| Ladder | `const LD = K.ladder({x, y, w, rungs: [{name, time, space, cost}]}); LD.show(t); LD.focus(i, t, tone); LD.strike(i, t); LD.pick(i, t, 'INTERVIEW PICK'); LD.out(t)` |
| Burst | `K.burst('700!', t, {x, y, tone: 'gold', size: 0.85, hold: 1.4, rot: 8})` (add a `pop` sfx to the line) |
| HUD widgets | `K.meter({x, y, label: 'COST', value: '0'})` (`.show`, `.count(t, d, a, b)`, `.to(t, '700', tone)`, `.out`), `K.pips({x, y, label, max})` (`.fill(i, t, tone)`), `K.note(html, t, {x, y, tone, size})`, `K.headline(html, t, {y, size, tone})`, `K.fanTree({x, y, w, h, branch, depth})` (`.grow(t, perLevel, tone)`, `.out`) |

## 5. Recipes

**Decode an input** (the text maps to the picture): register tokens, then highlight and fly each entry to the
point on the subject where its piece appears, and draw that piece as the copy lands.

```js
const D = K.decoder({ rows: F.input, y: 206 });
trip.forEach((s, i) => D.tok('e' + i, 1, s));
D.show(K.chapter(1).start - 0.2);
const t0 = K.cue(L.p1, 'each flight');
G.edges.forEach((e, i) => { const t = t0 + i * 0.3, land = t + 0.75;
  D.hl('e' + i, t); D.fly('e' + i, t, 0.75, K.cam.toScreen(e.mx, e.my, land)); G.edgeIn(i, land - 0.3, 0.5); });
```

**Trace a route / the answer**: `G.hop([0, 1, 3], L.p4.voiceAt + 0.5, 1.0, {trail: 'good', onLand: (n, t) => ...})`
moves the mascot and draws the glowing trail leg by leg; pair it with `cost.count(...)` and a burst at
`K.cue(L.p4, 'the answer')`.

**Reject an illegal route**: `const r = G.route([0, 1, 2, 3], t, 1.2, 'accent'); r.reject(t + 1.4, '2 STOPS > k');`
(turns rose, shakes, shows the label, then dims); clear it later with `r.clear(t2)`.

**Think countdown**: `const Q = K.question({n: 1, line: L.q1, text})` slides in as `q1` starts and runs the ring
over `L.q1.think` seconds; keep the subject visible and give it something to show during the pause; at the answer
line `Q.answer(L.a1.voiceAt)`.

**DP row update**: `TB.arrow([0, 0], [1, 1], t, 'good', '+100'); TB.set(1, 1, '100', t + 0.35, {tone: 'good'});` and
fire the matching edge on the graph at the same moment (`G.fire(E(0, 1), t - 0.2, 'good')`), so the table and the
subject tell the same story.

**Code walkthrough synced to the voice**: reveal in chunks as the chapter sting leaves (`ch(5) + 0.35` on), then move the highlight with
cues: `P.focus(K.cue(L.c1, 'round zero'), [6, 7])`, `P.focus(K.cue(L.c1, 'round one'), [10, 11])`; fill the dry-run
table on the same cues.

**Camera moves**: define shots in `subject.js` (`{cx, cy, zoom, sx, sy, tilt}`: world point `(cx, cy)` lands at
screen `(sx, sy)`). Move about 0.5 s before a chapter or line starts: `K.cam(K.chapter(4).start - 0.5, S.ladder,
1.1)`. Moves must not overlap. `K.cam.push(t, d, 1.05)` adds a slow push-in during a long line; the drift is always on.
Make room for HUD panels by moving the subject aside with `sx`/`zoom` rather than hiding it (persistent subject).

**Comic callout**: `K.burst('NOPE!', t, {x, y, tone: 'bad', tone2: 'accent', size: 0.7, hold: 0.9})` at most once or
twice a chapter, at a payoff; add `"sfx": "pop"` to that line in `script.json`.

## 6. Rendering

All through `$S/render_hyperframes.mjs` (run from the project folder; it finds `source/`):

```bash
node $S/render_hyperframes.mjs --project . --lint                 # hyperframes lint
node $S/render_hyperframes.mjs --project . --check                # lint + JS errors + layout + contrast at every line
node $S/render_hyperframes.mjs --project . --stills lines         # one PNG per line (65% into its voice) -> stills/
node $S/render_hyperframes.mjs --project . --stills chapters      # one per chapter
node $S/render_hyperframes.mjs --project . --stills 16.4,38.3 --keep   # exact times, keep the others
node $S/render_hyperframes.mjs --project . --range 30,36          # draft preview -> build/preview.mp4
node $S/render_hyperframes.mjs --project . --bench 6              # fps + ETA for the whole film
mkdir -p build && nohup node $S/render_hyperframes.mjs --project . --workers 2 --max-minutes 100 \
  > build/render.log 2>&1 &                                         # full render, background
tail -n 3 build/render.log                                          # poll
```

How it works: the CLI has no frame-range flag, so `index.html` declares two composition variables, `segFrom` and
`segTo`, and its inline script registers a wrapper timeline that plays the film from `segFrom` to `segTo`
(`film.tweenFromTo(from, to)`). Each segment (20 s by default, `--segment`) is one
`hyperframes render . -f 30 -q high -w 2 --variables '{"segFrom":a,"segTo":b}'` with frame-exact bounds; the
script checks every segment's frame count, records it in `build/segments/manifest.json`
(`{"segments": [{"from", "to", "done", ...}]}`), skips finished segments on a re-run, and joins them with ffmpeg's
concat demuxer (stream copy) into `build/silent.mp4` (H.264, yuv420p, exactly `round(total * fps)` frames). The
manifest is keyed by fps, quality, timing hash and a hash of the source tree: change a scene and the next run
starts over. `--max-minutes` (default 100) stops before a segment that would not finish in budget (exit 3; run
the same command again). `--force` restarts. Stills use `hyperframes snapshot` (about 1.5 s per frame).

Measured here (4 CPUs, software GL, 2 workers, `-q high`, every effect on): about 4 frames/s on a quiet machine and
1.7 frames/s with eight jobs sharing it (the smoke film's earlier 62 s cut: 1867 frames in 18.5 min, 3 segments), plus about 6 s
start-up per segment. Draft quality is about 25% faster. A 6-minute film is 45 minutes to 2 hours here: start it
early, in the background, and let `--max-minutes` stop and resume it.
Segmented output was checked against a one-piece render of the same range: identical frames in the first segment,
same content (encoder noise only, best match at zero frame offset) after each join.

`--check` runs `hyperframes check` at every line (65% into its voice) with the caption band (bottom sixth) declared,
and prints each finding with its time and line id: overlapping text, text under an opaque panel, text overflowing its
box, text in the caption band, WCAG contrast below 3:1, JS errors. Lights, grain, vignette, stings, bursts and flying
token copies are marked `data-layout-ignore` (`K.decor`), and the vignette and caption scrim are pseudo-elements, so
findings are about content. A finding seen at one sample only is listed as `transient`: still look at it (a badge
covering a weight chip showed up that way). About 2 minutes for 14 lines with an idle machine.

Other CLI tools that help while building: `npx hyperframes validate` (JS errors, missing assets, contrast),
`npx hyperframes snapshot . --at 3.5,12 --no-end` (raw stills), `npx hyperframes preview` (studio). Run them inside
`source/` with the environment above.

## 6b. Themes

The film's colours come from `source/theme.js` (loaded by `index.html` before `kit/tokens.js`). The template ships a
stub (`window.THEME = null`): the kit keeps its own palette, the verified dark editorial look (`original`). For a
registry theme (`references/themes.md`, `python3 $S/theme.py list`):

```bash
python3 $S/vstate.py set theme=rosepine-dawn
python3 $S/theme.py emit rosepine-dawn --format global --out source/theme.js
```

then re-shoot the stills and run `legibility.py` as usual. Put the stub back and `vstate.py set theme=original` (both: the
state alone does not change the picture) to return to the original palette. Never hand-edit `theme.js`; re-emit it after `themes.json` changes.

`kit/tokens.js` maps the theme onto the kit's roles; everything else reads those roles (`tok.color.*`, the CSS
variables, `K.tone` / `K.ink` / `K.on` / `K.tint` / `K.shade` in `kit/core.js`), so no kit file holds a colour:

| Kit role | Theme token |
|---|---|
| `bg`, `bg2`, `panel`, `panel2`, `line`, `line2`, `deep` | same names |
| `slab` (sting slabs, lower thirds, stamps) | `panel` |
| `edge` (idle edges, node rims) | `line2`, moved toward `text` until 3:1 on `bg` |
| `ink`, `mute`, `dim` (text) | `text`, `muted`, `dim` |
| `accent`, `good`, `bad`, `cool`, `gold`, `violet`, `warm` (fills: shapes, routes, borders) | same names; `badDeep` = `bad` |
| `K.ink(tone)` (text in a hue: values, captions' emphasis, the brand tag, notes' highlights) | `<hue>Ink`; `accentText` = `accentInk` |
| `K.on(tone)` (tags, lit node numbers, the Q badge, the check, the reject label, burst words) | `on<Hue>` |
| `light[]` chapter key lights, `rim[]`, `lightInk[]` (sting number, chapter tag) | `lights`, `lights` turned by three, the matching `<hue>Ink` |
| code syntax kw / ty / nu / fn / st / op / comment, line numbers | `accentInk` / `coolInk` / `goldInk` / `goodInk` / `violetInk` / `muted` / `dim`, `dim` |
| mascot, node discs, traffic-light dots, burst highlight | shaded from `accent`; `panel`/`panel2`/`line2`; `bad`/`warm`/`good`; the burst fill |
| shadows, caption band, vignette | `shadow`; `deep` |

Dark themes run the chapter lights at 0.7 strength (the header text sits in the key light, and theme `muted` has less
margin than the original's). Light themes (`tone: light`) also switch: grain `multiply` at 0.05 (dark: `screen` 0.04), chapter lights at 0.55 and
bokeh at 0.6 strength, route glows about half as strong, drop shadows a soft `shadow` tint at 0.4 strength, the
decoder copy in flight gets a soft shadow instead of a glow, the caption halo becomes `bg`, the vignette a gentle
`deep` edge. In every theme the vignette shades only the ground (`#bg`), not the subject and text above it. In any theme, inks clear 4.6:1 only at full strength, so the step-back opacity (`tok.dimOpacity`) rises
until every ink still clears 4.6:1 (usually 1: focus is then the highlight bar and border alone), and highlights under
text (`K.tint`: code cursor, decoder token, marked cell) are only as strong as the inks on them allow.

## 7. Gotchas

| Symptom | Cause | Fix |
|---|---|---|
| Lint: `gsap_timeline_not_registered` | lint wants the `window.__timelines["main"] = ...` assignment in the same inline `<script>` that calls `gsap.timeline` | keep the template's inline registration block as it is; kit files may create timelines freely |
| A segment renders the whole film length (holds the last frame) | a static `data-duration` on `#root` or a `.clip` fixes the composition length | no static durations: the inline script stamps `data-start`/`data-duration` from the range (lint and render both accept this) |
| Lint: `invalid_parent_traversal_in_asset_path` | a `../` path in CSS or HTML | keep assets below `source/`; fonts.css lives in `vendor/` next to `vendor/fonts/` |
| Squares or fallback fonts, or a stalled render | Google Fonts is blocked here | `@fontsource/*` woff2 copied by setup.mjs, `font-display: block`; symbols missing from the latin subset (→ ∞ ≤) fall back to system Inter/DejaVu |
| `!=` shows as one glyph, `<=` as ≤ | JetBrains Mono ligatures | `.mono { font-variant-ligatures: none; font-feature-settings: "liga" 0, "calt" 0 }` (in kit.css) |
| "SplitText is a Club plugin" or missing DrawSVG | old advice | GSAP 3.13+ ships every plugin free in the `gsap` npm package; register them (core.js does) |
| One-frame flash of an element before its entrance (qa.py "flicker") | `from()`/`fromTo()` with immediate render on a paused timeline seeked out of order | `K.hidden(el)` at build, entrances via `fromTo(..., {immediateRender: false})` (all kit helpers do this) |
| A value is wrong after seeking backwards | `onUpdate`/`textContent` writes are not reversible | change values with `K.stack(...).to(t, html)` or `K.count` (both seek-safe) |
| Frames differ between renders | `Math.random()`, `Date.now()`, CSS animations, `requestAnimationFrame` | `K.rand(seed)`; every motion on `KIT.tl` |
| Render about 2x slower than expected | big repaints: CSS 3D planes with animated backgrounds, full-frame blur filters, `backdrop-filter` | the floor is a canvas drawn per frame; avoid `backdrop-filter`; keep blur filters on small elements |
| `KIT.L.x9: no line "x9"` thrown | the scene uses a line id not in the script | rename in `film.js` (the error lists the ids) |
| `KIT.cue: "..." is not in the say of p4` | cue phrase must be a substring of `say` (spoken words, not `cap`) | quote the spoken text |
| Snapshot files are `frame-NN-at-Ts.png` in `snapshots/` | CLI default | use `--stills`, which renames them to `<start>-<id>.png` in `stills/` |
| Text blurry at the tilt | 3D-transformed text is resampled | keep reading text (code, tables, questions) in `#hud`, not in `#world` |
| legibility.py fails a text that reads fine in the film | it was still fading or popping in at the line's still (65% into the voice), or a world label shrank with a zoomed-out shot | land entrances well before the still (start them earlier, shorten them); size world text with `K.wfs`/`K.wscale` so it keeps `tok.size.world` on screen |
| A chapter sting covers content | content outside the faded layers (`#cam`, `#hud`), such as a title card in `#cards`, is still on screen when the card enters (last word + 0.3) | put subject content in the world or the HUD (the kit fades both around every card), or hide the overlay by the previous chapter's last word |
| `--check` reports a deliberate overlap (a badge on purpose over a panel) | the audit cannot know intent | put `data-layout-allow-overlap` (or `-overflow`, `-occlusion`) on that text element; `K.decor(el)` for pure decoration |
| A full-frame overlay makes every text "occluded" in `--check` | a gradient with alpha > 0.6 counts as opaque | draw such overlays as pseudo-elements (`#fx.vig::after`), which hit-testing ignores |
| `hyperframes render` warns about missing browser | `HYPERFRAMES_BROWSER_PATH` unset | the render script sets it to the sandbox headless shell |

## 8. Laptop differences

- Browser: the render script sets `HYPERFRAMES_BROWSER_PATH` only when the sandbox headless shell exists; on a
  laptop HyperFrames finds or downloads its own Chrome (`npx hyperframes browser`, `npx hyperframes doctor`). On macOS
  with a GPU it may engage `--experimental-fast-capture` by itself (the CLI says about 2x faster).
- Workers: `--workers 4` (or more on 8+ cores); each worker is one Chrome (~256 MB). Not measured here; run
  `--bench 6` first and trust its ETA.
- Fonts: the same woff2 files load from `vendor/`, so frames match the sandbox; system Inter is not needed.
- Voice: `edge_voice_swap.py` (delivered next to the MP4) swaps the Kokoro voice for an Edge voice line by line,
  each line starting where the picture expects it; no re-render needed.
- Studio: `npx hyperframes preview` opens a scrubbable editor for the same `index.html` (not needed here).
