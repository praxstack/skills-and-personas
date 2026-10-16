---
name: theatrejs-video
description: Make a finished, narrated explainer MP4 (natural voice, music, effects) animated with Theatre.js, where every keyframe is generated from the voice timing so re-voicing re-times the whole film. The default look is a 2.5D motion-design diorama in the DOM and SVG, with parallax depth layers, a Theatre camera that pans, dollies and orbits, depth-of-field blur, and sky moods per chapter. It includes a persistent glowing graph with planes flying routes, comic callout bursts, chapter swipes, question cards with a think countdown, and a code panel with an active-line highlight. Use it for LeetCode/DSA walkthroughs and concept explainers when someone asks for a Theatre.js video, keyframed or 2.5D/parallax motion graphics, or a film they can later hand-tweak in Theatre Studio. A Three.js binding of the same sheet is included for a 3D variant.
---

# Theatre.js explainer videos

Theatre.js is the animation system. Every moving value in the film is a prop on one Theatre sheet: the camera,
sky colours, each graph node and edge, every panel and burst. `src/film/shots.js` writes the keyframes as calls
keyed to narration line ids, for example `s.to('Code', { line: code.find('next[v] =') }, T.word('c1', 'round one'))`.
`npm run build` compiles them into `theatre-state.json`, the same JSON that Theatre Studio exports.
`getProject(id, { state })` plays that file with no Studio at render time. When the voice changes, the next
build moves every keyframe with its line.

`window.renderFrame(t)` sets `sheet.sequence.position = t` and applies the values to a 2.5D layered DOM/SVG
stage, so `capture.mjs` can screenshot any frame on any worker. The starter film (`assets/template/`) is a
complete 71 s explainer built from a reusable kit. Studio, for dragging keyframes by hand, is an optional laptop
step. A Three.js binding of the same sheet is included as a 3D variant.

Every skill in this family makes the same thing: a finished, narrated MP4 with a natural voice, music and
effects baked in. Each one is built through a state machine that survives interruptions and refuses to deliver
anything that has not passed its checks. Only the drawing and rendering steps are specific to Theatre.js.

`$SKILL` below means this skill's base directory (the folder this file is in). `$S` is `$SKILL/scripts`.

## Non-negotiables (and why)

1. **A video is an MP4 with the voice in it.** Not an interactive page, not slides, not a silent render with
   "add your own narration". A person once had to ask three times for a video and kept getting click-through
   pages. Extras (a page, a GIF) come after the MP4, never instead of it.
2. **Natural voice, always tried.** Kokoro runs offline everywhere (`$S/voice.py` installs it). Never tell the
   person a voice, or any other capability, is impossible until you have tried the alternatives and recorded
   them with `vstate.py limit ... --tried ... --tried ...`. A person was once told TTS was impossible when it was
   not, and read it as being treated as less deserving. Say plainly which limits come from the environment.
3. **The picture follows the voice.** Voice first, then animate against `timing.json`. Never stretch audio to fit.
4. **Hit the quality bar on the first attempt** (`references/quality-bar.md`). That means:
   - one persistent subject
   - every line changes something on screen
   - eased motion with camera movement
   - depth and light
   - music and effects

   A second attempt costs the person a day and their trust.
5. **Look at your frames.** The visuals and QA phases need a written attestation of what you looked at. Open
   the stills and the contact sheet with the Read tool; describe what you saw and what you fixed.
6. **For a coding problem, use the five-part format** (`references/dsa-five-part-format.md`):
   1. decode the problem and every example
   2. brute force
   3. intuition through timed questions
   4. every approach with its time and space
   5. final C++ with a dry run

   Compile and run the code before writing a word of script.

## Start or resume

```bash
python3 $S/vstate.py --project <project> status      # always first; prints the next command
```

New project (keep it on local disk, not a synced folder, while rendering):

```bash
mkdir -p <project> && cd <project>
python3 $S/vstate.py init --tool theatre --slug <short-name> --format dsa-5part   # or --format general
```

After an interruption (crash, context reset, the 2-hour job cap), run `status` and continue from the phase it
names. Finished work is never redone unless its inputs changed; the gates detect that by hash.
`references/state-machine.md` explains every phase and gate.

## Phase 1: brief

Ask the person only what you cannot reasonably default (the topic, and anything that changes the goal). Default
the rest and say which defaults you picked. Write `brief.md` with these sections, then run `vstate.py advance`:

- **Topic**
- **Audience**
- **Format**: dsa-5part or general, and the target length.
- **Persistent subject**: the one thing every chapter acts on.
- **Style**: a recipe from quality-bar.md, with colours and fonts.
- **Facts**: for code, the solution, the compile command, and the program's real output for every example.
- **Output**: resolution, fps, and where to deliver.

`$SKILL/assets/examples/lc787/brief.md` is a complete example.

## Phase 2: script

Write `script.json` (`references/script-format.md`). It has chapters, and each line has:

- `id`, `chapter` and `scene`
- `cap`: shown on screen; symbols are welcome
- `say`: spoken; words only
- `think`: a pause after a question
- `sfx`: optional

`vstate.py advance` checks it. Example: `$SKILL/assets/examples/lc787/script.json` (40 lines, about 6 min).

## Phase 3: voice

```bash
test -d source/src || { mkdir -p source && cp -r $SKILL/assets/template/. source/; }   # first time only
test -d source/node_modules || (cd source && npm ci --no-audit --no-fund)          # ~2 s, 8 packages
python3 $S/voice.py --project . --emit source/timing.js
python3 $S/vstate.py advance
```

Kokoro `af_heart` is the default voice. Set `meta.voice` and `meta.speed` in the script to change it;
`references/voice-and-audio.md` lists the voices, including Hindi ones. Changing a `say` re-voices only that
line. The emitted timing file is stamped with a hash, and the visuals gate checks that your scene code reads the
current one. `source/timing.js` is loaded by the page at runtime, and the page recompiles the keyframes if
`theatre-state.json` was built for another timing. A re-voice can never play stale keyframes.

## Phase 4: visuals

A new film rewrites two files and keeps the kit:

- `source/src/film/world.js`: **what** is on screen. Kit components with their data: the graph layout, the
  decoder rows, tables, ladder rungs, and the compiled code.
- `source/src/film/shots.js`: **when** things happen. Every keyframe, keyed to line ids.

The demo implements `examples/mini` line by line and is the pattern to copy. Change the look in
`source/src/kit/tokens.js` (palette, sky moods, fonts); for a registry theme, emit it into
`source/src/kit/theme.js` (guide section 13, Themes). The guide (`references/theatre-guide.md`) has the timing
API, the shot builder, the kit catalogue and the recipes:

- decode an input
- trace a route
- reject a route
- think countdown
- DP row update
- code walkthrough
- camera framing with `R.focus(rect)`

Work through these steps:

1. **Plan on paper first.** For every line id, write down what changes on screen and where the camera looks. One
   persistent subject (usually the graph) stays in the world for the whole film; it moves and shrinks to make
   room for panels, and never leaves.
2. **Time everything from the narration.** Take every time from `T` (`T.at(id, frac)`, `T.word(id, 'phrase')`,
   `T.after`, `T.think`), never from typed seconds. Frame shots with `R.focus(rect)` rather than raw camera
   numbers, so panels stay inside the frame.
3. **Build and shoot stills.** This builds the page, prints the coverage report, and shoots one still per
   chapter and one per line into `stills/`, with contact sheets (under a minute for the demo):

```bash
node $S/theatre_look.mjs                      # add --at 41.2,47.8 for busy moments
```

   Fix every line the report lists under `NOTHING changes during lines`. Judge each one under
   `only the camera moves`.
4. **Preview (optional).** From the project folder, run `python3 -m http.server 8765 --bind 127.0.0.1` and open
   `http://127.0.0.1:8765/source/index.html?play=1` (click to play with the narration). `?t=40` opens one frame
   and `?debug=1` shows the safe area and line ids. Stop the server when you are done.

Then open the `stills/sheet-*.png` overviews and every still (Read the images). Check each against
`references/quality-bar.md` ("The review pass"):

- text is inside the safe area
- nothing overlaps or is cut off
- code glyphs are correct
- the frame shows what its line says
- it would sit comfortably next to the reference films

Then measure the text: `python3 $S/legibility.py --project .` checks every text in the stills (at least 26 px,
4.5:1 contrast) and writes marked copies to `stills/legibility/`. The kit's sizes (`SIZE` and `GRAPH_TEXT` in
`tokens.js`) pass at the demo's framing; if a still fails, frame tighter or enlarge the text, never dim it.

Fix and re-run until it does, then:

```bash
python3 $S/vstate.py attest visuals "Looked at N stills: <what you checked, what you fixed>"
python3 $S/vstate.py advance
```

## Phase 5: render

```bash
(cd source && npm run build)
node $S/capture.mjs --page source/index.html --bench 3      # fps per worker and the film's ETA
mkdir -p build
node $S/capture.mjs --page source/index.html --out build/silent.mp4 --workers 2 --max-minutes 100 > build/render.log 2>&1
```

Run the render in the background, because it takes longer than a tool call, and poll `tail -n 3 build/render.log`.
Use `--workers 2` on a machine shared with other jobs, and up to 4 on your own.

Speed measured here, on a 4-CPU sandbox shared with other jobs: 2 to 4 frames/s per worker in the bench
(it prints yours). The demo's earlier 62 s cut rendered in 9 to 11 minutes with 2 workers. A 6-minute film with 2 workers takes
about 35 to 65 minutes, which fits in one 2-hour job.

The render is split into 20 s segments in `build/segments/`. Exit code 3 means the `--max-minutes` budget ran
out: run the same command again, and only unfinished segments are drawn. Editing anything in `source/`
invalidates the segments, so finish the visuals first. A rebuild with no changes is safe, because it rewrites
nothing. The render is done when the log says `wrote .../build/silent.mp4`.

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

It checks:

- format and duration
- loudness
- voice sync for every line
- black frames, frozen shots and single-frame flicker

It writes `qa/report.md`, `qa/contact-sheet.png` and `qa/stills/`. Open the contact sheet and the stills. If
anything is wrong, run `vstate.py reopen visuals --reason "..."`, fix it, and come back through render and mix.
When it is right:

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

The final message leads with the video (attach or link the MP4), then covers in a few lines:

- the length and the voice used
- the style
- any limit, and which part of it came from the environment
- any warning
- that `edge_voice_swap.py` re-voices it on a laptop (for example with `en-IN-NeerjaNeural`)

Do not claim anything the report does not show.

## Theatre.js gotchas

- **Never hand-edit `theatre-state.json`.** It is generated. Change `shots.js` and run `npm run build`. To keep a
  Studio hand-tweak, port it into shots.js (`node tools/studio-diff.mjs <export.json>` lists each change with its
  line id). To render an export as-is, save it as `source/theatre-state.pinned.json`; it will not follow a
  re-voice.
- **The state must reach `getProject(id, { state })`.** `rig.js` passes it. If the state is missing or its
  object keys differ, every prop silently sits at its default. Theatre normalises `"a/b"` to `"a / b"`, and the
  compiler emits the normalised form.
- **Read values right after seeking.** Use `sheet.sequence.position = t` then `obj.value`, which is synchronous
  and deterministic. `onValuesChange` is driven by the animation frame and lags or skips while seeking, so never
  render from it.
- **Use JetBrains Mono NL for code.** The NL files have no ligatures, and the `.mono` CSS also turns off `calt`
  and `liga`, so `!=` `<=` `++` never merge. Keep both.
- **Keep numbers out of Bangers.** Bangers' 7 reads as a 1, so a "700!" burst read "100!". The kit sets burst
  digits in Inter Black; put any number that matters in Inter or JetBrains Mono.
- **Use full-glyph Inter.** The kit loads Inter from `inter-ui` (full glyph set) because the fontsource subsets
  lack `→ ∞ ≤`.
- **Keep fonts local.** All fonts are bundled as data URLs and awaited before READY; Google Fonts is blocked.
- **Strings and booleans cannot tween.** `s.to` turns them into holds. Use `s.set` for steps, line ids, text and
  routes.
- **Theatre shows the first keyframe's value before it.** The compiler adds a keyframe at 0 holding the default;
  use the `s.*` calls and you never see this.
- **Watch the frame cost.** Large live CSS `filter: blur()` or `backdrop-filter` on moving layers triples the
  frame time. Blur static art once into a canvas, as the stage does for depth of field.
- **Wrap rich text in one span.** Flex containers drop the spaces between inline spans, so wrap rich text in one
  `<span>` (as the caption band does).
- **Build defines `process.env.NODE_ENV`.** Theatre reads it, and without the define the page throws
  `process is not defined`.

## References

| File | Read when |
|---|---|
| `references/theatre-guide.md` | Building scenes and rendering with Theatre.js: setup, component catalogue, timing API, recipes |
| `references/quality-bar.md` | Before designing the style, and at every review |
| `references/dsa-five-part-format.md` | Any coding-problem explainer |
| `references/script-format.md` | Writing script.json; reading timing in scene code |
| `references/voice-and-audio.md` | Voices, languages, music moods, mix levels, blocked TTS |
| `references/state-machine.md` | Gates, resume, reopening a phase, long renders |
| `references/environment.md` | Paths, fonts, render speeds, the 2-hour cap, laptop differences |
| `references/lessons-learned.md` | Once per project: why each rule exists |
