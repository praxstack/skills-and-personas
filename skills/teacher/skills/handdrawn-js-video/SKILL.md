---
name: handdrawn-js-video
description: Make a finished, narrated explainer MP4 (natural voice, music, effects) in a hand-drawn style drawn every frame in plain JavaScript on a 2D canvas, with paper cut-outs and hand lettering by default, or chalkboard or blueprint. Wobbly boiling lines, stroke-on edges and letters, squash-and-stretch pops, a paper plane travelling a hand-drawn graph, comic callouts, a code card and a dry-run table filled in by hand. Use it for LeetCode/DSA walkthroughs and concept explainers when someone wants a hand-made, storybook, paper-cut, whiteboard or chalkboard look, a "JS-drawn every frame" short, or the fastest render of the tool family.
---

# Hand-drawn canvas explainer videos

Plain JavaScript draws every frame from scratch on one 2D canvas: `renderFrame(t)` is a pure function of `t`
(no clock, seeded randomness), so `capture.mjs` can render any frame on any worker and the hand-made texture is
controlled: lines boil 8-12 times a second (never every frame), edges and letters draw on stroke by stroke from
real font outlines, cut-outs pop with squash and stretch and jitter like stop motion. The starter film
(`assets/template/`) is a complete 71 s explainer built from a reusable kit: a persistent hand-drawn graph with a
paper plane flying its routes, camera push-ins, torn-paper chapter labels, comic callouts, stamps, an input note
whose values fly into the graph, a code card with a highlighter, a dry-run table and a complexity ladder.
Styles: `paper` (default), `chalk`, `blueprint`, `whiteboard` (the graph draws itself in marker), `papercraft-riso`
(cut-paper pieces printed in halftone riso inks, stop-motion drops), or `watercolor` (layered washes that bloom,
with a brush-pen ink line), switched with one line in `source/style.js`
and recorded with `vstate.py set style=<name>` (guide, "Styles": what each changes, its cost).
Themes: any of the 30 registry themes (`references/themes.md`) recolours it via `source/theme.js` (guide, "Themes").

Every skill in this family makes the same thing: a finished, narrated MP4 with a natural voice, music and
effects baked in, built through a state machine that survives interruptions and refuses to deliver anything
that has not passed its checks. Only the drawing and rendering steps are specific to the hand-drawn canvas.

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
python3 $S/vstate.py init --tool handdrawn --slug <short-name> --format dsa-5part   # or --format general
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
cp -r $SKILL/assets/template source        # the starter film: kit, demo scenes, pinned fonts
(cd source && npm ci --no-audit --no-fund)  # playwright-core for capture.mjs (2 s, no browser download)
python3 $S/voice.py --project . --emit source/timing.js
python3 $S/vstate.py advance
```

Kokoro `af_heart` by default (`meta.voice`/`meta.speed` in the script; `references/voice-and-audio.md` lists
voices, including Hindi ones). Changing a `say` re-voices only that line. The emitted timing file is stamped
with a hash; the visuals gate checks your scene code reads the current one.

## Phase 4: visuals

Read `references/handdrawn-guide.md` (kit catalogue and recipes), then build the film in `source/scenes.js`.
The shipped `scenes.js` is the mini LC 787 film: keep `source/kit/` and replace only the scenes. Declare the
persistent subject once (`graph(...)`, moved between chapters with `g.place`), and key every element to line
ids (`vAt('p3', 0.4)`, `sayAt('p3', 'one stop')`, `lEnd('p3')`), never to raw seconds. Pick the style with
`STYLE_NAME` in `source/style.js` (`paper`, `chalk`, `blueprint`, `whiteboard`, `papercraft-riso` or `watercolor`). Then render stills from the project folder:

```bash
node $S/capture.mjs --page source/index.html --stills lines --timing timing.json --stills-dir stills
node $S/capture.mjs --page source/index.html --stills 16.6,31.2 --stills-dir stills   # e.g. the busiest moments
mkdir -p build && ffmpeg -loglevel error -y -pattern_type glob -i 'stills/*.jpg' \
  -vf "scale=640:-1,tile=3x5:padding=6" -frames:v 1 build/stills-sheet.jpg            # optional overview
```

The stills command stops with `page error: unknown line id ...` if a scene reads an id that is not in the
script, and prints a `console:` line naming ids no scene reads (each of those lines changes nothing on screen:
fix that). Stills take about 0.3 s each, so iterate freely; the overview sheet is for layout, open the full
stills for text.

Then open every still (Read the JPGs). Check each against `references/quality-bar.md` ("The review pass"): text
inside the safe area, nothing overlapping or cut off, code glyphs correct, the frame shows what its line says,
and it would sit comfortably next to the reference films. Then measure every text in the stills:

```bash
python3 $S/legibility.py --project .     # size and contrast of every text; marked copies in stills/legibility/
```

It fails any text under 26 px or under 4.5:1 contrast, at every size, with no 3:1 large-text exception; the visuals gate needs 0 failing texts.
Use the `S.size` tokens and the colour rules in `references/handdrawn-guide.md` ("Text size and colour"); text
caught mid-write in a still should land earlier, not be shrunk or faded. Fix and re-render stills until both
the review and the measurement pass, then:

```bash
python3 $S/vstate.py attest visuals "Looked at N stills: <what you checked, what you fixed>"
python3 $S/vstate.py advance
```

## Phase 5: render

```bash
node $S/capture.mjs --page source/index.html --bench 3     # frames/s per worker and the full-film ETA
mkdir -p build && nohup node $S/capture.mjs --page source/index.html --out build/silent.mp4 \
  --workers 4 --crf 21 --max-minutes 100 > build/render.log 2>&1 &
tail -3 build/render.log      # poll every minute or two; done when it prints "wrote .../build/silent.mp4"
```

Always run it in the background and poll the log; use `--workers 2` on a shared machine. `--crf 21` keeps
the MP4 near 3 Mbit/s with no visible difference on paper textures (the default, 20, makes a larger file). It renders 20 s
segments into `build/segments/` and records them in `manifest.json`. If it prints `stopped at the 100-minute
budget` (or the job was killed), run the same command again: finished segments are skipped. Editing anything
in `source/` restarts the segments, so finish the stills review first.

Measured in the smoke test on 4 CPUs shared with eight other render jobs (load average 25-43), 2 workers: the
mini film's earlier 62 s cut (1867 frames) took 10.1 min (3.1 frames/s); `--bench` gave 6.8-8.2 frames/s for one worker.
On a quiet 4-core machine expect 25-30 frames/s with 4 workers, about a minute per film minute.

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

## Hand-drawn canvas gotchas

- **Never read a clock or `Math.random` in scenes.** Workers render segments independently; anything not
  derived from `t` flickers at segment joins and fails QA's flicker check. Use `rnd(seed, k)`, `noise1`, and
  pass `t` to ink functions so lines boil at `S.boilFps` instead of shimmering every frame.
- **Code only through `codeCard`/`drawMono`.** JetBrains Mono ligatures turn `!=` into `≠` with plain
  `fillText`; the kit draws code one glyph per grid cell.
- **Symbols the hand fonts lack** (`→ ← ∞ ≤ ≥ ≠ ✓ ✗ ★`) are drawn as hand strokes; any other symbol falls back
  to a system font. Add it to `HAND_GLYPHS` in `kit/type.js` or write the word.
- **Texture tiles must wrap**: draw every fibre at +/- the tile size (`wrapDraw`) or seams show when the camera moves.
- **Camera push-ins crop wide boards.** Keep zoom near 1.0 while the code card is up, 1.04-1.07 elsewhere;
  check the still at the end of every push. Text stays inside x 96..1824, y 96..900 (captions own the bottom 180 px).
- **A huge MP4 means full-frame texture changing every frame.** Keep the grain still (`grainBoil: false`), keep
  the backdrop and scenery on the still camera (main.js does), and render with `--crf 21`.
- **Every element needs an exit** (`until`, or `out` in `slideKeys`), or chapters pile up on the board.
- **Previewing via `file://` shows fallback fonts** (the font fetch fails); serve the project with
  `python3 -m http.server` or just use stills.

## References

| File | Read when |
|---|---|
| `references/handdrawn-guide.md` | Building scenes and rendering with the hand-drawn canvas: setup, component catalogue, timing API, recipes |
| `references/quality-bar.md` | Before designing the style, and at every review |
| `references/dsa-five-part-format.md` | Any coding-problem explainer |
| `references/script-format.md` | Writing script.json; reading timing in scene code |
| `references/voice-and-audio.md` | Voices, languages, music moods, mix levels, blocked TTS |
| `references/state-machine.md` | Gates, resume, reopening a phase, long renders |
| `references/environment.md` | Paths, fonts, render speeds, the 2-hour cap, laptop differences |
| `references/lessons-learned.md` | Once per project: why each rule exists |
