---
name: threejs-video
description: Make a finished, narrated explainer MP4 (natural voice, music, effects) as a 3D Three.js "toy diorama" - rounded toy blocks on a game board on a wooden desk at night, a warm spotlight and a cool rim light, soft shadows, bloom on whatever is active, a city skyline and string lights behind - with the data structure as 3D pillars and glowing arcs, a little mascot token that flies routes, a camera that dollies and orbits on every line, and crisp DOM text on top (captions, chapter banners, question cards with a think countdown, a code panel with an active line, a dry-run table, a complexity ladder, comic bursts). Use it for LeetCode/DSA walkthroughs and concept explainers when someone asks for a Three.js, WebGL or 3D animated video, a "toy world" or diorama look, or a cinematic 3D explainer rendered frame by frame to MP4.
---

# Three.js explainer videos

One web page renders a Three.js scene (WebGL) with a DOM text layer above it. Everything on screen is a pure
function of time: a tiny seekable tween timeline of our own (`source/src/kit/time.js`, no Theatre.js, no GSAP)
places every tween at a line's time from the voice (`at('p3')`, `word('p4', 'The answer')`), and
`window.renderFrame(t)` seeks it, moves the camera rig, renders the scene, and lays out the text. The shared
`capture.mjs` screenshots each frame (WebGL + text together) on parallel workers into a resumable MP4. The
starter film (`assets/template/`) is a complete 71 s explainer built from a reusable kit: a 3D graph that rises
out of a game board, a mascot token, an orbit camera with a `fit()` solver for "graph left, panel right"
shots, and every 2D panel a DSA film needs. On this sandbox WebGL runs on the CPU (SwiftShader), so rendering is
slow but steady (measured speeds in Phase 5); on a laptop with a GPU it is 20-50x faster.

Every skill in this family makes the same thing: a finished, narrated MP4 with a natural voice, music and
effects baked in, built through a state machine that survives interruptions and refuses to deliver anything
that has not passed its checks. Only the drawing and rendering steps are specific to Three.js.

`$SKILL` below means this skill's base directory (the folder this file is in). `$S` is `$SKILL/scripts`.

## Non-negotiables (and why)

1. **A video is an MP4 with the voice in it.** Not an interactive page, not slides, not a silent render with
   "add your own narration". A person once had to ask three times for a video and kept getting click-through
   pages. Extras (a page, a GIF) come after the MP4, never instead of it.
2. **Natural voice, always tried.** Kokoro runs offline everywhere (`$S/voice.py` installs it). Never tell the
   person a voice, or any capability, is impossible until the alternatives are tried and recorded with
   `vstate.py limit ... --tried ... --tried ...`. A person was once told TTS was impossible when it was not, and
   read it as being treated as less deserving. Say plainly which limits come from the environment.
3. **The picture follows the voice.** Voice first, then animate against `timing.json`. Never stretch audio to fit.
4. **Hit the quality bar on the first attempt** (`references/quality-bar.md`): one persistent subject, every
   line changes something on screen, eased motion with camera movement, depth and light, music and effects.
   A second attempt costs the person a day and their trust.
5. **Look at your frames.** The visuals and QA phases need a written attestation of what you looked at. Open
   the stills and the contact sheet with the Read tool; describe what you saw and what you fixed.
6. **For a coding problem, use the five-part format** (`references/dsa-five-part-format.md`): decode the problem
   and every example, brute force, intuition through timed questions, every approach with time and space, final
   C++ with a dry run. Compile and run the code before writing a word of script.

## Start or resume

```bash
python3 $S/vstate.py --project <project> status      # always first; prints the next command
```

New project (keep it on local disk, not a synced folder, while rendering):

```bash
mkdir -p <project> && cd <project>
python3 $S/vstate.py init --tool threejs --slug <short-name> --format dsa-5part   # or --format general
```

After an interruption (crash, context reset, the 2-hour job cap), run `status` and continue from the phase it
names. Finished work is never redone unless its inputs changed; the gates detect that by hash.
`references/state-machine.md` explains every phase and gate.

## Phase 1: brief

Ask the person only what you cannot reasonably default (topic, and anything that changes the goal). Default
the rest and say which defaults you picked. Write `brief.md` with these sections, then `vstate.py advance`:

- **Topic**, **Audience**, **Format** (dsa-5part or general; target length), **Persistent subject** (the one
  thing every chapter acts on), **Style** (a recipe from quality-bar.md with colours and fonts), **Facts**
  (for code: the solution, the compile command, the program's real output for every example), **Output**
  (resolution, fps, where to deliver).

`$SKILL/assets/examples/lc787/brief.md` is a complete example. For this skill the natural Style is the toy
diorama of the template (palette and fonts in `source/src/kit/style.js`); say so in the brief. A registry theme
(`references/themes.md`) is one emit into `source/src/theme.js`: see the guide's Themes section.

## Phase 2: script

Write `script.json` (`references/script-format.md`): chapters, and per line an `id`, `chapter`, `scene`, `cap`
(on screen, symbols welcome) and `say` (spoken, words only), `think` pauses after questions, optional `sfx`.
`vstate.py advance` checks it. Example: `$SKILL/assets/examples/lc787/script.json` (40 lines, ~6 min).

## Phase 3: voice

```bash
cp -r $SKILL/assets/template source && (cd source && npm ci --no-audit --no-fund)
python3 $S/voice.py --project . --emit source/src/timing.js
python3 $S/vstate.py advance
```

Kokoro `af_heart` by default (`meta.voice`/`meta.speed` in the script; `references/voice-and-audio.md` lists
voices, including Hindi ones). Changing a `say` re-voices only that line. The emitted timing file is stamped
with a hash; the visuals gate checks your scene code reads the current one. (`npm ci` takes about 10 s; it
installs three 0.186.1, esbuild 0.28.2 and the font packages from the lockfile.)

## Phase 4: visuals

Write the film in `source/src/film.js`; the demo there implements `examples/mini` line by line and is the
pattern to copy. Keep the kit (`source/src/kit/`) and change the look in `source/src/kit/style.js`. The guide
(`references/threejs-guide.md`) has the kit catalogue and recipes (decode an input, trace a route, reject a
route, think countdown, DP row update, code walkthrough, camera shots).

1. Plan on paper first: for every line id, what changes on screen and where the camera looks. The graph stays
   on the board for the whole film; panels come and go around it. Give every line its own camera move
   (`cam.shot(...)`), and frame panel shots with `cam.fit(g.bounds(), [left, top, right, bottom], {az, el})`
   so the graph lands exactly in the free part of the screen.
2. Place every tween at a line time: `at('p3')`, `at('p3', 0.5)`, `word('p3', 'phrase')`, `start('p3')`,
   `end('p3')`. Never a hard-coded second; never `Date.now()` or `Math.random()` (use `rand(seed)`).
3. Preview (optional, best on a laptop): `(cd source && node build.mjs --watch)` and open
   `source/draft.html?preview&t=40` in a browser (space plays, arrows step a frame, shift+arrows 5 s).
4. Shoot stills (each `film3d.mjs` call rebuilds the bundle first; here about 3 s per draft still and 9 s per
   final one, about 2 minutes for the 28 stills below):

```bash
node $S/film3d.mjs stills chapters --project . --q draft
node $S/film3d.mjs stills lines --project . --q draft
node $S/film3d.mjs stills busy --project . --q final      # the 8 longest lines at the final look (bloom, MSAA)
```

   For a busy moment add exact times: `node $S/film3d.mjs stills 41.2,47.8 --project .`.

Then open every still (Read the images). Check each against `references/quality-bar.md` ("The review pass"): text
inside the safe area, nothing overlapping or cut off, code glyphs correct, the frame shows what its line says,
and it would sit comfortably next to the reference films. Then measure the text:
`python3 $S/legibility.py --project .` (size and contrast of every text; the visuals gate fails until 0 fail) and
open the marked copies in `stills/legibility/`. Fix and re-render stills until both are clean, then:

```bash
python3 $S/vstate.py attest visuals "Looked at N stills: <what you checked, what you fixed>"
python3 $S/vstate.py advance
```

## Phase 5: render

```bash
node $S/film3d.mjs bench --project . --q final        # frames/s for 2 workers and the film's ETA
mkdir -p build
node $S/film3d.mjs render --project . --q final --workers 2 --max-minutes 100 > build/render.log 2>&1
```

Run the render in the background (it takes far longer than a tool call) and poll `tail -n 3 build/render.log`.
Measured on this 4-CPU sandbox with SwiftShader, 2 workers, final quality: 1920x1080 about 0.8 frames/s on a
quiet machine (bench: 0.61 per worker), so a 6-minute film (10,800 frames) takes about 4 hours, three 100-minute
budgeted runs; 1280x720 about 1.8 frames/s quiet (1.32 per worker). Under heavy load from other jobs it drops
2-3x: the demo's earlier 62 s cut at 1280x720 took 51 minutes (0.6 frames/s) with a load average of 20-55. `--q fast` (75%
render scale; the text stays full resolution) is about 1.6x faster (1080p: 0.97 per worker) and is the sensible
choice for a long 1080p film without a GPU; `--q draft` (no bloom, no MSAA, writes `build/draft/draft.mp4`) is a
timing check, never the delivered render. The render is split into 10 s segments in `build/segments/`; exit
code 3 means the `--max-minutes` budget ran out: run the same command again and only unfinished segments are
drawn. Editing anything in `source/` invalidates the segments (the page is stamped), so finish the visuals
first. Done when the log says `wrote build/silent.mp4`.

```bash
python3 $S/vstate.py advance      # checks codec, size, fps, duration against the voice timing, segments
```

## Phase 6: mix

```bash
python3 $S/music.py --project .          # --mood calm|piano|pulse|none (default: script meta.music)
python3 $S/mix.py --project .            # voice + ducked music + effects, loudness -16 LUFS, yuv420p
python3 $S/vstate.py advance
```

## Phase 7: QA

```bash
python3 $S/qa.py --project .
```

It checks format, duration, loudness, voice sync for every line, black frames, frozen shots and single-frame
flicker, and writes `qa/report.md`, `qa/contact-sheet.png` and `qa/stills/`. Open the contact sheet and the
stills. If anything is wrong, `vstate.py reopen visuals --reason "..."`, fix, and come back through render and
mix. When it is right:

```bash
python3 $S/vstate.py attest qa "Contact sheet and N stills: <what you saw>; report: <pass/warnings>"
python3 $S/vstate.py advance
```

## Phase 8: deliver

```bash
python3 $S/vstate.py notes-md > NOTES.md      # fill every (fill in): tool versions, style, re-render commands
python3 $S/package.py --project . --to <deliver folder>   # a new or empty folder; it never empties one it did not make
python3 $S/vstate.py advance
python3 $S/vstate.py report                   # use this for the final message
```

The final message leads with the video (attach or link the MP4), then in a few lines: length, voice used, the
style, any limit and which part of it came from the environment, any warning, and that `edge_voice_swap.py`
re-voices it on a laptop (for example with `en-IN-NeerjaNeural`). Do not claim anything the report does not show.

## Three.js gotchas

- **SwiftShader is slow and fill-bound.** Cost grows with pixels x passes: MSAA, bloom, shadow-map size and
  render scale are the knobs (`?q=draft|fast|final`, or one at a time: `?bloom=0&msaa=0&shadow=1024&scale=0.75`).
  Benchmark before a long render; never start a 1080p final render without an ETA.
- **Every frame must be a pure function of t.** No clock, no `Math.random()`, no `requestAnimationFrame`, no CSS
  transitions or animations: tween on the timeline or compute from `t` in an `apply(t)`. Workers render
  segments out of order, so state that "accumulates" across frames shows up as jumps at segment joins.
- **Ligatures**: JetBrains Mono must load with `featureSettings: '"calt" 0, "liga" 0'` (main.js does, and uses
  the NL cut) or `!=`, `<=`, `->` turn into single glyphs in the code panel.
- **Text is DOM, not WebGL.** Labels that follow 3D things are anchors (`ui.anchor({world: () => g.top(1)})`);
  they are projected after the camera moves, so they never swim. Do not draw text into textures except the
  numbers printed on the blocks (they are part of the toy).
- **Tweening arrays**: arrays of the same length interpolate element by element (targets, colours); a route
  (`tok.p.route`) must change with `tl.set`, never `tl.to`. Two tweens on one property: the later one takes over
  from wherever the earlier one is at that moment, so order them in time, not in code.
- **Panels hide the graph.** Frame with `cam.fit(g.bounds(), box)` for every shot that shares the screen with a
  panel (`g.bounds(null, { flags: [0, 3] })` when nodes carry START/GOAL flags, so they stay above the caption
  band); hand-tuned targets drift as soon as the layout changes.
- **Three.js r186**: `PCFSoftShadowMap` is gone (use `PCFShadowMap` + `light.shadow.radius`); colours are
  sRGB-managed, so pass hex strings and let `THREE.Color` convert.
- **A phrase that is not in the line's `say`** makes `word(id, '...')` throw with the line's text, and an
  unknown line id throws listing the real ids: after editing `say`, re-voice before fixing the scenes.
- **Digits in Bangers**: its 7 reads as a 1, so a "700!" burst read "100!". `Burst` sets any text with digits in
  Inter ExtraBold (slanted); keep numbers that matter out of the comic font.
- **Small or faint text**: the kit's smallest text is 30 px (weight tags and chips 32, table heads 30, code 30,
  tree notes 30) and secondary text is `C.inkSoft`/`C.inkFaint`/`C.comment`, at least 6:1 on a panel; keep a new
  film at or above these. Text still fading in at a still is a timing bug: land it earlier (see the guide's
  "Text that lands before the still" and "Chapter banners").
- **Bursts live about a second**: line stills (taken partway into each line) miss them. Shoot their exact times
  too (`film3d.mjs stills 16.8,41.2`) and check the burst reads.

## References

| File | Read when |
|---|---|
| `references/threejs-guide.md` | Building scenes and rendering with Three.js: setup, component catalogue, timing API, recipes |
| `references/quality-bar.md` | Before designing the style, and at every review |
| `references/dsa-five-part-format.md` | Any coding-problem explainer |
| `references/script-format.md` | Writing script.json; reading timing in scene code |
| `references/voice-and-audio.md` | Voices, languages, music moods, mix levels, blocked TTS |
| `references/state-machine.md` | Gates, resume, reopening a phase, long renders |
| `references/environment.md` | Paths, fonts, render speeds, the 2-hour cap, laptop differences |
| `references/lessons-learned.md` | Once per project: why each rule exists |
