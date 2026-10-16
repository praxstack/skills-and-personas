# Revideo guide

How the starter project in `assets/template/` is built, how to make a new film from it, and how to render it.
Revideo is a fork of Motion Canvas with a headless render API (`@revideo/renderer`): scenes are TypeScript
generator functions that animate signals; `renderVideo` runs them in headless Chromium and encodes with FFmpeg.

## Contents
1. Setup
2. Project anatomy
3. Timing API
4. Kit catalogue
   Themes
5. Recipes
6. Rendering
7. Gotchas
8. Laptop differences

## 1. Setup

```bash
cp -r "$SKILL/assets/template" source
(cd source && PUPPETEER_SKIP_DOWNLOAD=1 npm ci --no-audit --no-fund)     # ~15-40 s, ~350 MB node_modules
(cd source && npx tsc --noEmit -p .)                                      # typecheck: silent when fine
```

- Pinned: `@revideo/core @revideo/2d @revideo/renderer @revideo/ffmpeg @revideo/vite-plugin @revideo/ui` all
  `0.11.0` (the newest 0.x line; npm's `latest` tag points at a stray 2024 `1.6.0` publish, do not use it).
  `@revideo/ui` is needed even headless (the renderer imports it). Fonts: `@fontsource/inter`,
  `@fontsource/jetbrains-mono`, `@fontsource/bangers` 5.3.0. `package-lock.json` is committed: use `npm ci`.
- `PUPPETEER_SKIP_DOWNLOAD=1` stops puppeteer downloading its own Chrome; the render script points at a local
  one (`CHROMIUM=/path` to override; it tries `/opt/pw-browsers/chromium`, `/usr/bin/chromium`, Google Chrome).
- Needs `ffmpeg` and `ffprobe` on PATH, Node 20.19+ or 22.12+ (Vite 8 needs it; tested 22).

## 2. Project anatomy

| File | What it is | Edit for a new film? |
|---|---|---|
| `src/timing.ts` | written by `voice.py --emit source/src/timing.ts` (hash-stamped) | never by hand |
| `src/data.ts` | the film's facts: graph nodes/edges, input text, the exact C++, dry-run rows, ladder rungs | yes |
| `src/film.tsx` | the one scene: `setupStage`, then one generator per chapter | yes (the chapter functions) |
| `src/project.ts` | fonts (@fontsource) awaited before frame 1; size and fps from TIMING | rarely |
| `src/theme-active.ts` | the active theme: a stub (`THEME = null`, the original palette) or `theme.py emit <id> --format ts` output (Themes) | only via `theme.py emit` |
| `src/kit/*.ts` | reusable pieces (catalogue below); `kit/theme.ts` holds palette, fonts, sizes, safe area | to restyle |
| `src/env.d.ts`, `tsconfig.json`, `package.json` | types for `?scene` imports; pinned deps | no |

The film is ONE continuous scene, so the persistent subject (the graph) never disappears between chapters. A
chapter function waits for its own lines and changes the stage; layouts change only while a chapter card
covers the frame (`CARD[n].coveredAt`), which is where hard cuts belong. Coordinates: design space 1920x1080,
origin at the centre, y down; text stays inside `SAFE` (96 px) and above the caption band (`STAGE_BOTTOM` = 344).

## 3. Timing API (`kit/time.ts`)

Every animation is keyed to a line id from the script; never write a bare number of seconds for *when*
something happens (durations of individual tweens are fine).

| Helper | Meaning |
|---|---|
| `L.p3` | line p3: `{start, voiceAt, voiceDur, think, end, dur, cap, say, chapter}`; an unknown id throws |
| `at(t)` | wait until absolute film time t; if already past it, logs `LATE|<line>@t|secs` (the render script reports these) |
| `when(t, task)` | run `task` at absolute time t; put several in `all(...)` so each beat keeps its own cue |
| `cue('p4', 'seven')` | when the voice says that word, estimated from its character position in `say` (throws if absent) |
| `voiceEnd('q1')` | the voice finishes q1 (a think pause starts here) |
| `CARD[n]` | chapter n's card: `inAt`, `coveredAt` (rearrange here), `outAt`, `clearAt` (stage visible again) |
| `TOTAL`, `FPS`, `LINES`, `CHAPTERS` | from the timing; the film ends with `yield* at(TOTAL)` |
| `onFrame(fn)` / `counter(txt, fmt)` | per-frame updaters (text that follows a signal) |
| `rng(seed)` | deterministic random numbers (never `Math.random`: every worker must draw the same frame) |
| `mark('id')` | logs `TL|id|time` while debugging |

Pattern for a dense line (many beats inside 3 seconds of voice):

```ts
yield* all(
  when(cue('p1', 'four') - 0.1, g.popNodes()),
  when(cue('p1', 'each flight') - 0.2, dec.type(0.06, 0.22)),
  when(voiceEnd('p1') - 0.5, sendAllFlights()),
  when(cue('p2', 'zero') - 0.25, srcBadge.in()),      // the next line's beats can live in the same block
);
```

A sequential chain (`yield* at(a); yield* longAnim(); yield* at(b)`) makes `b` late whenever `longAnim` runs
past it; the stills run prints every LATE cue so you can fix it.

## 4. Kit catalogue (`import {...} from './kit'`)

| Piece | Make it | Key methods |
|---|---|---|
| Stage | `const st = setupStage(view, {kicker: 'LC 787'})`; then `yield st.run()` (no star) | layers `st.world` (camera), `st.fg` (screen panels), `st.fx` (bursts), `st.top`, `st.lower` (above the caption scrim, for lower thirds); `st.cam`; `st.screenPos(node)` |
| Camera | `st.cam` | `to({x, y, zoom, rot}, d)`, `push(x, y, zoom, d)`, `reset(d)`, `set({...})`; a slow drift always runs |
| Captions, HUD, chapter cards | automatic from the timing via `st.run()` | captions show each line's `cap` at its voice; cards wipe in between chapters |
| Title card | `titleCard('Cheapest\nflights.', 'within *k* stops.', 'LEETCODE 787 · GRAPHS')` | `in()`, `out()` |
| Lower third | `st.lower.add(lowerThird('EXAMPLE 1', 'src 0 → dst 3, k = 1'))` (in `st.lower`: under the scrim its orange block measured 3.7:1) | `in()`, `out()` |
| Kinetic headline | `kinetic('k stops → *k + 1* rounds.', {size: 76, y: -318})` | words rise out of masks; marks `*acc*` `~mint~` `!rose!` `^muted^` may span words |
| Labels | `label('CITIES 0 · 1', {x, y})` (mono, uppercase, >= 28 px; default `S.tiny` = 30); `mono(text)`; `bigO('n', 'k+1')` | |
| Graph (subject) | `new Graph({nodes: [{id, x, y}], edges: [{u, v, w, bend}], directed: true})`; `st.world.add(g.root)` | `place(x, y, scale, d)`, `popNodes()`, `drawEdge(u, v)`, `showTag`, `showAll()`, `state(id, 'active'/'good'/'bad'/'dim')`, `ring(id)`, `ripple(id)`, `light(u, v, color)`, `fire(u, v, color)`, `travel(path, color, perEdge, onHop)`, `reject(path, '2 STOPS', color, hold, noteAbove?)` (note above node `noteAbove`, else beside the middle edge), `badge(id, 'SRC')`, `edgeBadge(u, v, 'FLIGHT 1', color, along, off)` (`off` < 0 puts it on the outer side; -134 clears the weight tag), `chip(id, '∞')` + `set(v)`, `showTags(on)`, `focusOn(ids)`, `clear()`, `reset()`, `removeAttachments()`. Tags, badges, chips and notes keep their screen size when the graph is placed small (`place(x, y, 0.5)`), and node labels stay >= 30 px on screen |
| Input decoder | `new Decoder({name: 'flights', items: ['[0, 1, 100]', ...], y: -318, size: 34})` | `type()`, `annotate(i, ['FROM', 'TO', 'PRICE'])`, `mark(i)`, `send(st, i, g.edge(u, v).tag!, '100')`, `unmark()` |
| Question card | `new QuestionCard({n: 1, text: '...?', y: -262})` | `in()`, `think('q1')` (waits for the voice, counts the pause down, resolves on time), `out()` |
| Code panel | `new CodePanel({code: CPP, title: 'solution.cpp'})` (size 30 by default, 30-36 px; keep lines under ~60 columns at 30 px or the panel crowds the graph) | `in()`, `reveal(a, b)`, `revealAll()`, `focus(line, n)` (active-line bar; the other lines turn a quieter colour that stays >= 4.5:1, never low opacity), `unfocus()` |
| Array row / table | `new ArrayRow({label: 'dist', values: [...]})`; `new Table({x, y, cell: 78}).addRow('r = 0', [...])` | `in()`, `set(i, '100')`, `mark(i)`, `copyFrom(other)` |
| Complexity ladder | `new Ladder({rungs: [{name, time: ['n', 'k+1'], space: 'O(k)', cost: 1}]})` | `show(i)`, `pick(i)` |
| Recursion fan | `new Fan({levels: 5, branch: 3, width: 1000})` | `grow()`, `ringRepeats(level, idx)` |
| Effects | `burst(st.fx, '700!', {x, y, size, rays})` (`rays: false` in a crowded frame: the speed lines reach ~1.8x the star), `fly(st, '100', fromNode, toNode)`, `counter(txt, fmt)`, `shake(node)` | |
| Style tokens | `kit/theme.ts`: `C` palette, `F` fonts, `S` sizes (`tiny` 30, `small` 32, `code` 30, `body` and `caption` 40), `W`, `H`, `SAFE`, `STAGE_BOTTOM`; `C.muted` `#B3ADA2` is the dimmest text colour (`C.dim` is never text); orange text uses `inkOf(C.acc)` = `C.accText` `#FF8A5C` (plain `C.acc` text on the dark panels measured under 4.5:1); a registry theme maps all of it (Themes, below) | |

## Themes

The kit's colours all come from `src/kit/theme.ts`. With no theme it uses the original dark editorial palette,
exactly as the starter film was verified. A registry theme (`references/themes.md`, 30 of them) lives in one file:

```bash
python3 $S/vstate.py set theme=<id>                                          # e.g. everforest-light
python3 $S/theme.py emit <id> --format ts --out source/src/theme-active.ts   # re-emit after themes.json changes
```

`src/theme-active.ts` ships as a stub (`export const THEME = null`): that means `original`. To go back, copy the
stub from `$SKILL/assets/template/src/theme-active.ts`. Changing the file re-renders every segment (it is part of
`source/src`). The visuals gate checks that the file carries the current `theme-id: <id>  sha: <fp>` line.

Role mapping (`themed()` in `kit/theme.ts`):

| Kit role | Theme token |
|---|---|
| `C.bg`; backdrop gradient centre/edge | `bg`; the lighter / darker of `bg` and `bg2` |
| `C.panel`, cards, ladder rows, cells, tags, chips, code panel, lower third body | `panel` (opaque) |
| node disc gradient | `panel` / `panel2` |
| `C.ink`, `C.muted` | `text`, `muted` |
| `C.dim` (idle tracks), `C.line` (borders), `C.edge` (idle edges) | `line2`, `line` (`line2` on light themes), `dim` |
| `C.acc`, `C.mint`, `C.rose`, `C.gold`, `C.sky` (fills) | `accent`, `good`, `bad`, `gold`, `cool` |
| text in a hue: `inkOf(c)`, `textOf(c)` (`C.accText`), code syntax | `<hue>Ink`, moved further from the ground (same hue) to 6.3:1 on light themes and 5.5:1 on dark ones: thin mono labels on the drifting stage measured 3.8:1 at the registry's 4.6:1 |
| label on a filled pill, badge, stamp, wipe: `onOf(c)` | `on<Hue>` |
| lines and small shapes in a hue: `lineOf(c)` | the fill if it clears 3:1 on the ground, else `<hue>Ink` |
| glows: `glow(c)`; drop shadows: `drop(a)` | the hue on dark grounds, `shadow` at 0.22 on light ones; `shadow` (x0.35 alpha on light) |
| chapter wipe (`wipeOf(n)`) and the light pool | key light `lights[(n - 1) % 6]` with its `on<Hue>`; the pool switches light under each card |
| vignette, caption scrim | toward `deep` (a gentle 0.85 `deep` edge on light themes, never black) |
| grain | light + dark specks on dark themes; dark `shadow` specks only (multiply-like) on light ones |
| caption text shadow | `shadow` on dark; a `bg` halo on light |
| code syntax (`CODE`) | kw `accentInk`, type `coolInk`, num `goodInk`, str `goldInk`, fn `warmInk` (all moved as above), punct/comments `muted`, gutter `dim` |

New scene code keeps the same rule: text takes `C.ink`, `C.muted`, `textOf(hue)`/`inkOf(hue)` or `onOf(fill)`;
shapes take the fill or `lineOf(hue)`; shadows `drop()`/`glow()`. Never a hex literal in a scene.

## 5. Recipes (all in the demo `film.tsx`)

- **Decode an input**: `dec.type()`, `dec.annotate(0, ['FROM','TO','PRICE'])`, then for each entry
  `all(dec.mark(i), dec.send(st, i, g.edge(u, v).tag!, w), delay(0.25, g.drawEdge(u, v, 0.5, false)), delay(0.66, g.showTag(u, v)))`
  inside `sequence(0.3, ...)`: the numbers fly out of the text into the graph's weight tags.
- **Trace a route with a running cost**: `g.travel([0, 1, 3], C.acc, 0.8, function* (i) { yield* cost(...) })`
  with `const cost = counter(txt, v => \`COST ${Math.round(v)}\`)`; then `g.light(...)` the answer in mint and a
  `burst`.
- **Reject an illegal route**: `g.reject([0, 1, 2, 3], '2 STOPS', C.rose, 0.6, 1)` draws it rose, shakes, crosses it out,
  shows the note above node 1 (clear of the weight tags) and restores whatever was lit before.
- **Think countdown**: `yield* all(when(CARD[3].clearAt - 0.3, q.in()), q.think('q1'))`.
- **DP row update**: `next.copyFrom(dist)` (values travel down), `g.fire(0, 1, C.mint)`, `next.set(1, '100')`.
- **Code walkthrough synced to the voice**: `when(cue('c1', 'round one'), all(code.focus(CL.loop, 2), ...))`;
  keep line numbers in `data.ts` (`CODE_LINES`) so the code and the focus calls stay in step.
- **Camera**: push in on what the line talks about (`st.cam.to({x, y, zoom: 1.1}, 1.4)`), pull back for the
  answer, a slow linear push across a static chapter (`st.cam.to({zoom: 1.05}, chapterLength, linear)`).
- **Rearrange between chapters**: `yield* at(CARD[n].coveredAt)`, remove panels, `g.removeAttachments()`,
  `g.reset()`, `st.cam.set({x: 0, y: 0, zoom: 1})`, then `g.place(...)` for the new layout.

## 6. Rendering (`$S/render_revideo.mjs`)

```bash
node $S/render_revideo.mjs --project . --stills lines --workers 2    # one PNG per line -> stills/ (+ LATE report)
node $S/render_revideo.mjs --project . --stills chapters             # one per chapter; or --stills 12.5,40.2
node $S/render_revideo.mjs --project . --range 40,52                 # a quick MP4 of a span -> build/preview.mp4
node $S/render_revideo.mjs --project . --bench 3                     # steady fps per worker and the ETA
node $S/render_revideo.mjs --project . --workers 4 --max-minutes 100 > build/render.log 2>&1   # the film
```

- Each segment (default 20 s, `--segment`) is one `renderVideo` call with `range`, the FFmpeg exporter
  (`{name: '@revideo/core/ffmpeg', options: {format: 'mp4'}}`), puppeteer `executablePath` + `--no-sandbox`, in
  its own child process with a stall watchdog (`--stall 240`). Done segments are recorded in
  `build/segments/manifest.json` and skipped on re-run; any change under `source/src`, the timing or the
  settings starts them over. Exit 3 = the `--max-minutes` budget ran out: run the same command again.
- At the end the segments are concatenated (stream copy) into `build/silent.mp4`, H.264 yuv420p, CRF 18
  (`--crf`), and the duration is checked against `TIMING.total`. Expect about 3-4 Mbit/s (25 MB a minute) with
  this kit; much more means something full-frame changes every frame (section 7).
- A page error (an exception in the scene) fails the segment at once instead of hanging the render.
- Speed measured here (4 CPUs shared with other jobs, load 40-60, 1080p30, this kit): `--bench 3` reported
  1.0 frame/s per worker after a ~50 s start-up; whole 20 s segments took 650-800 s per worker (0.8-0.9 fps).
  Every still re-runs the scene from the start, so late stills take longer (~15-35 s each).

## 7. Gotchas

| Symptom | Cause and fix |
|---|---|
| Render fails with "Encoder creation error" | the default WebCodecs exporter; the script always passes the FFmpeg exporter |
| Render hangs forever after a scene error | Revideo waits on a dead page; the script runs each segment in a child process and kills it on page errors or no progress |
| "The scene is not available in the current context" | a `Txt` whose `text` is a function of a signal; update text with `onFrame()` or `counter()` instead |
| `!=`, `<=`, `++` drawn as single glyphs | JetBrains Mono ligatures; every code/mono `Txt` needs `letterSpacing: 0.01` (the kit sets it) |
| First frames in a fallback font, wrong text widths | fonts not loaded; `project.ts` imports @fontsource CSS and awaits `document.fonts.load` per weight |
| Logs from the scene appear 3-5 times | Revideo runs the scene function several times per render; keep it free of side effects (`setupStage` resets the per-frame list) |
| Only the first argument of `console.log` shows | puppeteer forwards a JSHandle; log one string (`` `LATE|${id}` ``) |
| Circles inside a layout `Rect` are squashed | layout children shrink; keep drawn shapes outside layout nodes (see `QuestionCard`) |
| `import film from './film?scene'` resolves to the wrong file | two files with the same base name (`exp.ts` + `exp.tsx`); keep scene names unique |
| A cue lands late (`LATE|p2@7.62|1.97`) | an earlier animation in a sequential chain ran long; schedule beats with `when()` inside `all()` |
| Render much slower than expected | full-frame gradients, `compositeOperation` blends, big `shadowBlur`, or images drawn scaled / at fractional offsets (20-30 ms each per frame on the CPU); bake static layers with `kit/textures.ts` and draw them 1:1 at rounded positions (~5 ms) |
| MP4 is 20+ Mbit/s (150 MB a minute) | something full-frame changes every frame, usually grain re-jittered per frame; H.264 cannot predict noise. Keep grain static (`GRAIN_HOLD = 0` in `kit/stage.ts`, 3.3 Mbit/s) or hold each pattern several frames |
| Different frames per worker | `Math.random()` or wall-clock time in a scene; use `rng(seed)` and `now()` |
| `npm install` downloads Chrome or fails on it | set `PUPPETEER_SKIP_DOWNLOAD=1` |
| Telemetry requests at render | the script sets `DISABLE_TELEMETRY=true` |

## 8. Laptop differences

- Chromium: install Chrome or Chromium and run with `CHROMIUM=/path/to/chrome` if it is not found
  automatically (macOS: `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` is tried).
- `--workers` defaults to min(4, CPUs - 2); 8-core laptops can use 6. There is no 2-hour cap, but keep the budget
  flag: it makes a crash cheap.
- A live preview editor is not part of this template (it renders headless only); use `--range a,b` for quick looks.
- Measured in the sandbox (4 busy CPUs, 2 workers): the demo's earlier 62 s cut (1867 frames) rendered in about 24 min,
  1.0-1.5 frames/s overall. A quiet laptop with 6 workers should be several times faster; trust `--bench`.
