---
name: remotion-video
description: Make a finished, narrated explainer video (an MP4 with a natural Kokoro voice, music and effects baked in) with Remotion, where React components are rendered frame by frame in headless Chromium. It gives a polished motion-graphics look with a persistent animated subject, camera push-ins, depth and glow, comic chapter stings and callouts, code panels with an active line, DP tables and a caption band, all keyed to the voice timing. Use it when someone asks for a Remotion video, a React or TypeScript animation, or a LeetCode or DSA walkthrough in a crisp motion-graphics style. It runs the resumable eight-phase pipeline (brief, script, voice, visuals, render, mix, QA, deliver) with segmented renders that survive the 2-hour job cap.
---

# Remotion explainer video

Remotion renders a React component once per frame in headless Chromium and encodes the frames with ffmpeg.
Anything a web page can draw is available, including type, SVG, gradients, shadows and layout, and every frame
is deterministic. That makes it the strongest choice for a crisp motion-graphics look with real typography and
code. The cost is render speed, about 4 to 9 frames per second, so long renders run in the background in
resumable segments. The starter project in `assets/template/` already contains:

- a full kit: graph subject, input decoder, question card with countdown, code panel, DP table, complexity
  ladder, recursion tree, comic bursts, chapter stings, captions and camera
- a director pattern: one file that cues the persistent subject and the camera by line id
- the 71-second mini film, as working demo scenes

Every skill in this family makes the same thing: a finished, narrated MP4 with a natural voice, music and
effects baked in, built through a state machine that survives interruptions and refuses to deliver anything
that has not passed its checks. Only the drawing and rendering steps are specific to Remotion.

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
python3 $S/vstate.py init --tool remotion --slug <short-name> --format dsa-5part   # or --format general
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

`$SKILL/assets/examples/lc787/brief.md` is a complete example.

## Phase 2: script

Write `script.json` (`references/script-format.md`): chapters, and per line an `id`, `chapter`, `scene`, `cap`
(on screen, symbols welcome) and `say` (spoken, words only), `think` pauses after questions, optional `sfx`.
`vstate.py advance` checks it. Example: `$SKILL/assets/examples/lc787/script.json` (40 lines, ~6 min).

## Phase 3: voice

```bash
test -d source || cp -r $SKILL/assets/template source                     # the starter project
test -d source/node_modules || (cd source && npm ci --no-audit --no-fund)  # pinned versions, ~20 s
python3 $S/voice.py --project . --emit source/src/timing.json
python3 $S/vstate.py advance
```

Kokoro `af_heart` by default (`meta.voice`/`meta.speed` in the script; `references/voice-and-audio.md` lists
voices, including Hindi ones). Changing a `say` re-voices only that line. The emitted timing file is stamped
with a hash; the visuals gate checks your scene code reads the current one.

## Phase 4: visuals

`source/` is a Remotion project that already plays the mini film. Keep `src/kit/` (components), `src/lib/`
(clock and motion) and `src/Film.tsx` (layer order). A new film replaces only `src/scenes/`:

1. **`scenes/data.ts`**: the film's facts. The subject's layout (`MAP`: nodes and weighted edges), where it sits
   in each chapter (`PLACE`), the raw input text with tagged entries (`INPUT`), and the compiled code (`CPP`,
   `CODE_LINE`).
2. **`scenes/director.ts`**: the persistent subject and the camera, cue by cue. `graphAt(fr)` decides what
   lights up, `placeAt(fr)` where the subject sits, `cameraAt(fr)` the push-ins and pull-backs.
3. **One file per chapter** (`Problem.tsx`, `Brute.tsx`, `Intuition.tsx`, `Approaches.tsx`, `Code.tsx`). Each
   exports a `...World` part, which moves with the camera, and a `...Hud` part in screen space for cards,
   bursts and chips. `scenes/index.tsx` lists them.

If the brief names a theme (`references/themes.md`), emit it before the stills:
`python3 $S/theme.py emit <id> --format ts --out source/src/kit/theme.ts` (guide section 10 has the role mapping).

Every frame number comes from a line id: `f('p3')` (the voice starts p3), `f('p3', 0.4)`,
`fPhrase('p4', 'seven hundred')`, `fSaid('q1')`, `fThink('q1')`, `fStart`/`fEnd`, `chapterStart(n)`, `sec(0.5)`
for durations. Never type a frame number or a second count. An unknown id or phrase throws, so a script edit
that breaks a cue fails loudly. Plan one visible change per line before coding. `references/remotion-guide.md`
has the kit catalogue and recipes: decode, route, reject, think countdown, DP row, code walkthrough, camera.

Render review stills. The first run bundles the project (~20 s), then two stills render at a time, 3 to 10 s each:

```bash
node $S/render_remotion.mjs --project . --stills lines            # one still per line -> stills/
node $S/render_remotion.mjs --project . --stills 15.9,55.4        # plus the busiest moments, in seconds
```

A scene error prints a stack trace naming the file and line. TypeScript type errors do NOT stop a render, so a
misspelt prop silently does nothing: check the stills.

Then open every still (Read the PNGs). Check each against `references/quality-bar.md` ("The review pass"): text
inside the safe area, nothing overlapping or cut off, code glyphs correct, the frame shows what its line says,
and it would sit comfortably next to the reference films. Fix and re-render stills until it does. Then measure
text size and contrast; the visuals gate needs 0 failing texts (the kit's `SIZE` and `C` already meet the bar,
see `references/remotion-guide.md` section 4):

```bash
python3 $S/legibility.py --project .   # red boxes in stills/legibility/: fix, re-shoot the stills, re-run
python3 $S/vstate.py attest visuals "Looked at N stills: <what you checked, what you fixed>"
python3 $S/vstate.py advance
```

## Phase 5: render

Benchmark first: it renders 3 s from the middle of the film and prints the speed and the full-film estimate.
For `N`, use the CPU core count up to 4 (`nproc`), or 2 when other heavy jobs share the machine.

```bash
node $S/render_remotion.mjs --project . --bench 3 --concurrency N
```

Then run the full render in the background with a log, so a job cap or a lost shell never loses work:

```bash
mkdir -p build && nohup node $S/render_remotion.mjs --project . --concurrency N --max-minutes 100 > build/render.log 2>&1 &
tail -3 build/render.log      # poll every few minutes: each segment prints its fps and the ETA
```

It renders 30-second frame ranges into `build/segments/`. The ranges are recorded in `manifest.json` and
finished ones are skipped. It then concatenates them losslessly into `build/silent.mp4`: H.264 yuv420p,
tv-range bt709, no audio.

- **Done:** the log prints `silent render: build/silent.mp4 ... <frames> frames`.
- **Budget reached:** the log prints `Stopping cleanly` (exit code 3), or the job was killed. Run the same
  command again; it continues from the first unfinished segment.
- **Speed measured here:** 3.9 to 6.5 fps at concurrency 2 on a lightly loaded 4-core machine, and 1.8 to 2.3
  fps under heavy load. The mini film (its earlier 62 s cut; now 71 s) takes 5 to 16 minutes; a 7.4-minute film took about 25 minutes
  at concurrency 4.

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

For NOTES.md:

- **Versions:** Remotion 4.0.533 (remotion, @remotion/cli, @remotion/renderer), React 19.3.0, Node 22, and the
  Chromium headless shell. The exact list is in `$SKILL/tool.json`.
- **Re-render:** the plain command works anywhere, and on a laptop Remotion downloads its own browser:
  `cd source && npm ci && npx remotion render src/index.ts Film ../build/silent.mp4 --color-space=bt709`.
  Then run `music.py`, `mix.py` and `qa.py`. With this skill installed, use the resumable
  `render_remotion.mjs` instead.

The final message leads with the video (attach or link the MP4), then in a few lines: length, voice used, the
style, any limit and which part of it came from the environment, any warning, and that `edge_voice_swap.py`
re-voices it on a laptop (for example with `en-IN-NeerjaNeural`). Do not claim anything the report does not show.

## Remotion gotchas

Each gotcha gives the symptom, then the fix. Details are in the guide's Gotchas section.

- **yuvj420p output.** Remotion writes full-range `yuvj420p` even with `--pixel-format=yuv420p`, which some
  players and the QA gate reject. `--color-space=bt709` fixes it at the source. The render script and
  `remotion.config.ts` both set it, and the script re-encodes once if a concat still comes out `yuvj420p`.
- **Ligatures in code.** With JetBrains Mono, `!=`, `<=`, `->` and `++` turn into single glyphs. Set
  `fontFeatureSettings: '"calt" 0, "liga" 0'`. It is `NO_LIGA` in `kit/tokens.ts`, set on the root by
  `Film.tsx` and again by `CodePanel`. Keep both.
- **Fonts.** Never load fonts from Google Fonts: it is blocked here, and a late font renders the first frames
  in a fallback.
  - Import `@fontsource/*` in `kit/fonts.ts`. `useFontsReady()` holds every frame with `delayRender` until
    `document.fonts.load` has resolved for each face.
  - The npm subsets lack `→`, `∞` and `≤`. `RichText` draws `→` as an SVG arrow; the font stacks fall back to
    DejaVu for the others.
- **TypeScript is stripped, not checked.**
  - Remotion's bundler and Node 22 both strip TS types without type checking. A wrong prop name renders
    nothing, with no error.
  - Node scripts can import `.ts` data files only with erasable syntax: no `enum`, no parameter properties,
    and `import type` for types. A JSON import needs `with {type: 'json'}`.
- **Render time.** A 7.4-minute film took about 25 minutes at concurrency 4. Always bench, render in the
  background with `--max-minutes`, and re-run to resume. Do not use concurrency above the number of cores:
  each worker is a Chromium tab.
- **Camera crops.** A push-in above about 1.1 slides content near the frame edge off-screen. Put screen-anchored
  info (chips, meters, receipts) in a `...Hud` part, and push gently or toward the content.
- **`<Sequence>` resets the frame.** Inside a `<Sequence>`, `useCurrentFrame()` counts from 0, which breaks
  `f('id')`. Use the kit's `<Span from to>` together with `useF()`, which returns absolute frames.
- **Animated grain.** Full-frame noise that changes every frame raised the bitrate to 33 Mbps and slowed
  encoding. Keep the grain static (`Finish`) and animate the light instead.

## References

| File | Read when |
|---|---|
| `references/remotion-guide.md` | Building scenes and rendering with Remotion: setup, component catalogue, timing API, recipes |
| `references/quality-bar.md` | Before designing the style, and at every review |
| `references/dsa-five-part-format.md` | Any coding-problem explainer |
| `references/script-format.md` | Writing script.json; reading timing in scene code |
| `references/voice-and-audio.md` | Voices, languages, music moods, mix levels, blocked TTS |
| `references/state-machine.md` | Gates, resume, reopening a phase, long renders |
| `references/environment.md` | Paths, fonts, render speeds, the 2-hour cap, laptop differences |
| `references/lessons-learned.md` | Once per project: why each rule exists |
