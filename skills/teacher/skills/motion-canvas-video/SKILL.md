---
name: motion-canvas-video
description: Make a finished, narrated explainer video (an MP4 with a natural voice, music and effects baked in) with Motion Canvas, built from TypeScript scenes timed to the voice, a persistent animated subject, camera moves, code panels with an active-line highlight, DP tables, complexity ladders and comic callouts. Use for LeetCode/DSA walkthroughs (five-part format), algorithm or system explainers, and any request for a video or animation made with Motion Canvas or code-driven 2D motion graphics. Covers voice (Kokoro, offline), a resumable headless render, mixing, QA and delivery through a state machine that survives interruptions.
---

# Motion Canvas explainer videos

Motion Canvas (3.17.2, pinned) animates a 2D canvas with TypeScript generators and signals: exact, code-driven
motion with a camera, layered depth and real code panels. The starter project in `assets/template/` is a
complete film of `assets/examples/mini/` built from a reusable kit: a persistent graph subject with flying
tokens and firing edges, an input decoder, question cards with countdown rings, a code panel with an
active-line bar, DP tables, a complexity ladder, comic bursts and stamps, chapter cards, captions, a drifting
camera, parallax backdrop and film grain. Motion Canvas has no render CLI, so the template also ships a
headless render page that drives the editor's own renderer (frames checked pixel-identical to the editor's
export); `$S/mc.py` builds it and renders through the shared, resumable `capture.mjs`.

Every skill in this family makes the same thing: a finished, narrated MP4 with a natural voice, music and
effects baked in, built through a state machine that survives interruptions and refuses to deliver anything
that has not passed its checks. Only the drawing and rendering steps are specific to Motion Canvas.

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
python3 $S/vstate.py init --tool motion-canvas --slug <short-name> --format dsa-5part   # or --format general
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
python3 $S/mc.py setup --project .     # copies assets/template to source/ and runs npm ci (about 10 s)
python3 $S/voice.py --project . --emit source/src/timing.ts
python3 $S/vstate.py advance
```

Kokoro `af_heart` by default (`meta.voice`/`meta.speed` in the script; `references/voice-and-audio.md` lists
voices, including Hindi ones). Changing a `say` re-voices only that line. The emitted timing file is stamped
with a hash; the visuals gate checks your scene code reads the current one.

## Phase 4: visuals

Write the film in `source/src/scenes/`; keep `source/src/kit/` (`references/motion-canvas-guide.md` lists every
piece with an example, plus recipes for decoding an input, tracing and rejecting routes, think countdowns, DP
rows and code walkthroughs). The template's scenes are a working example to copy from. If the brief names a theme (`references/themes.md`),
emit it into `source/src/theme-film.ts` first (`references/motion-canvas-guide.md`, section 10, "Themes"); with
none the kit keeps its `original` palette.

1. `scenes/data.ts`: the subject's layout, the input rows, the ladder rungs, the exact code from the brief and
   the line numbers the walkthrough points at.
2. One generator per chapter (`ch1-problem.tsx`, ...). Key every beat to a line id, never to a hard-coded
   second: `yield* waitUntilLine('p3')`, `yield* waitUntilCue('p4', 'The answer')`,
   `yield* q.countdown(line('q1').think)`. Wait with `yield*` only on cues and start each beat's animations
   with `yield all(...)`, so nothing can push the next cue late.
3. `scenes/film.tsx` runs the chapters in order and ends with `yield* waitUntilTime(TOTAL)`.

```bash
python3 $S/mc.py stills --project .     # typecheck + build + one still per line into stills/, overview build/stills-sheet.jpg
```

It lists every `[timing] late` warning and scene error the page printed; fix all of them. For busy moments
between lines add `--at 41.5,43.2 --keep`. On a laptop, `python3 $S/mc.py editor --project .` opens the
Motion Canvas editor with the voice playing.

Then open every still (Read the PNGs). Check each against `references/quality-bar.md` ("The review pass"): text
inside the safe area, nothing overlapping or cut off, code glyphs correct, the frame shows what its line says,
and it would sit comfortably next to the reference films. Run `python3 $S/legibility.py --project .` (every
text at least 26 px and 4.5:1; the gate requires 0 failures) and fix each red box in `stills/legibility/`: the
kit's sizes and colours pass as shipped (motion-canvas-guide.md, "Legibility"), so failures usually come from a
smaller camera zoom, a new colour or text caught mid-fade. Fix and re-render stills until it does, then:

```bash
python3 $S/vstate.py attest visuals "Looked at N stills: <what you checked, what you fixed>"
python3 $S/vstate.py advance
```

## Phase 5: render

```bash
python3 $S/mc.py bench --project .                       # frames/s of one worker and the full-film ETA
python3 $S/mc.py render --project . --max-minutes 100    # build/silent.mp4 from segments in build/segments/
```

If the ETA is over 2 minutes, run the render in the background with a log
(`... --max-minutes 100 > build/render.log 2>&1`) and poll the log. Exit code 3 means the budget ran out:
run the same command again and only unfinished segments render. Do not edit `source/` between resumed runs
(a changed build restarts the segments). `--workers N` defaults to up to 4; use 2 on a shared machine.
Measured here (1080p30, 4 CPUs, 2 workers): the mini film's earlier 62 s cut rendered in 2.4 minutes (about 13 frames/s,
so roughly 2.5 minutes per minute of film); with six other renders sharing the CPUs it fell to 1.0 to 1.4
frames/s in total. Bench first. A normal film is 3 to 8 Mbps; 50+ Mbps means something changes every pixel
every frame (see Gotchas).

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

## Motion Canvas gotchas

- **Spawned tails get cut off.** Motion Canvas cancels a thread's children when it ends, and every argument
  of `all()`/`sequence()`/`delay()` is its own short thread. Use `background(task)` from the kit for
  fire-and-forget effects inside them.
- **Ligatures in code.** JetBrains Mono draws `!=`, `<=`, `++` as single glyphs unless `letterSpacing={0.01}`
  (CodePanel sets it). Check code stills glyph by glyph.
- **Undrawn lines still show arrowheads and round caps** at `end={0}`: keep them at `opacity={0}` until drawn.
- **Spaces vanish in layout text** (`n = 4` becomes `n=4`): Txt in a layout trims spaces; use `'\u00A0'`.
- **Fonts**: `@fontsource/*` imports plus `document.fonts.load(...)` in `project.ts` for every weight used;
  Google Fonts is blocked. Add new weights there, not in scenes.
- **Code focus dimming needs** `makeProject({experimentalFeatures: true})` (set in the template).
- **Pinned versions only**: unpinned `npm i @motion-canvas/...` pulls Vite 7 and the build hangs. Add
  packages with `npm i -E name@x.y.z`.
- **Nothing may change every pixel every frame** (animated grain or noise): x264 cannot compress it, the
  MP4 balloons (432 MB vs 29 MB for the same film (the demo's earlier 62 s cut)) and renders slower. Keep texture static on screen.
- **Never `pkill -f vite`** (it matches your own shell); stop an editor server by its PID. Never
  `Math.random()` in scenes (frames must be deterministic); use `rng(seed)` or `useRandom()`.

## References

| File | Read when |
|---|---|
| `references/motion-canvas-guide.md` | Building scenes and rendering with Motion Canvas: setup, component catalogue, timing API, recipes |
| `references/quality-bar.md` | Before designing the style, and at every review |
| `references/dsa-five-part-format.md` | Any coding-problem explainer |
| `references/script-format.md` | Writing script.json; reading timing in scene code |
| `references/voice-and-audio.md` | Voices, languages, music moods, mix levels, blocked TTS |
| `references/state-machine.md` | Gates, resume, reopening a phase, long renders |
| `references/environment.md` | Paths, fonts, render speeds, the 2-hour cap, laptop differences |
| `references/lessons-learned.md` | Once per project: why each rule exists |
