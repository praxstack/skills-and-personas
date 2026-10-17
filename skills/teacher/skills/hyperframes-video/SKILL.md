---
name: hyperframes-video
description: Make a finished, narrated explainer MP4 (natural Kokoro voice, music, effects baked in) with HyperFrames (one HTML + GSAP composition rendered frame-exact by the HyperFrames CLI) in a dark editorial look with per-chapter coloured light, a perspective floor, a tilted camera that pushes and pans over one persistent glowing graph with a hopping mascot, comic callout bursts, chapter stings, question cards with a think countdown, a code panel with an active-line highlight and a dry-run table. Use it for LeetCode/DSA walkthroughs and concept explainers when someone asks for a HyperFrames video, an HTML/GSAP motion-graphics explainer, or a polished animated explainer rendered to MP4 (never an interactive page).
---

# HyperFrames explainer videos

HyperFrames (npm `hyperframes`, pinned 0.8.137) renders an HTML page to MP4: it opens `index.html` in headless
Chrome, seeks the GSAP timeline registered as `window.__timelines["main"]` frame by frame and encodes with ffmpeg.
The starter project (`assets/template/`, copied to `<project>/source/`) is a complete 71 s film built from a reusable
kit: one paused GSAP 3.15 timeline whose every tween sits at a line time from the voice (`KIT.L.p3.voiceAt`,
`KIT.cue(L.p4, 'the answer')`), never a hard-coded second; a persistent graph in a tilted, drifting world; coloured
chapter light, a perspective floor, bokeh and grain; chapter stings, captions, question cards, a code panel, tables, a
complexity ladder and comic bursts. A new film replaces two files (`scenes/subject.js`, `scenes/film.js`).
`scripts/render_hyperframes.mjs` wraps the CLI for stills, layout checks, benchmarks and a segmented, resumable render.

Every skill in this family makes the same thing: a finished, narrated MP4 with a natural voice, music and
effects baked in, built through a state machine that survives interruptions and refuses to deliver anything
that has not passed its checks. Only the drawing and rendering steps are specific to HyperFrames.

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
python3 $S/vstate.py init --tool hyperframes --slug <short-name> --format dsa-5part   # or --format general
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
test -d source || cp -r $SKILL/assets/template source
(cd source && test -d node_modules || npm ci --no-audit --no-fund)   # ~10 s; postinstall copies GSAP + fonts into vendor/
python3 $S/voice.py --project . --emit source/timing.js
python3 $S/vstate.py advance
```

Kokoro `af_heart` by default (`meta.voice`/`meta.speed` in the script; `references/voice-and-audio.md` lists
voices, including Hindi ones). Changing a `say` re-voices only that line. The emitted timing file is stamped
with a hash; the visuals gate checks your scene code reads the current one.

## Phase 4: visuals

Write the film in `source/scenes/subject.js` (graph layout, camera shots, input text, the exact compiled code) and
`source/scenes/film.js` (choreography); the demo implements `examples/mini` line by line and is the pattern to copy.
Keep `source/kit/`; change the look in `source/kit/tokens.js`, or pick a registry theme (`source/theme.js`, guide section "Themes"). The guide (`references/hyperframes-guide.md`) has the
timing API, the kit catalogue and recipes (decode an input, trace a route, reject a route, think countdown, DP row
update, code walkthrough, camera moves).

1. Plan first: for every line id, what changes on screen and where the camera looks. The graph stays in the world
   the whole film; panels come and go around it (move the camera to make room instead of hiding the subject).
2. Place every tween at a line time (`L.<id>.voiceAt`, `.voiceEnd`, `.thinkEnd`, `K.cue(L.<id>, 'phrase')`,
   `K.chapter(n).start`), on `KIT.tl`, entrances with the kit helpers (they set the hidden state at build time).
3. Lint, then shoot one still per line (about 1.5 s each; the folder is cleared first, `stills/sheet.jpg` is a contact
   sheet), then the event moments you care about (bursts, stamps, arrows) with `--keep`:

```bash
node $S/render_hyperframes.mjs --project . --lint
node $S/render_hyperframes.mjs --project . --stills lines
node $S/render_hyperframes.mjs --project . --stills 16.4,38.3,48.4 --keep
```

4. Run the layout check (lint + JS errors + overlapping text, text under a panel, overflow, text in the caption band,
   contrast, sampled at every line; about 2 minutes for 14 lines on an idle machine, run it in the background on a
   long film):

```bash
node $S/render_hyperframes.mjs --project . --check
```

   Each finding names the time, the line id and the element. Open that line's still, fix real overlaps (move a tag to
   another side, change the shot), and mark a deliberate one on the text element with `data-layout-allow-overlap`.
   It does not replace looking: it found a tag hidden under the input panel that a contact-sheet glance missed.
5. Preview motion when timing matters: `node $S/render_hyperframes.mjs --project . --range 30,36` writes a draft
   `build/preview.mp4` of that range in about 30 s.

Then open every still (Read the PNGs). Check each against `references/quality-bar.md` ("The review pass"): text
inside the safe area, nothing overlapping or cut off, code glyphs correct, the frame shows what its line says,
and it would sit comfortably next to the reference films. Then measure every text in the stills:

```bash
python3 $S/legibility.py --project .     # size and contrast of every text; marked copies in stills/legibility/
```

It fails any text under 26 px or under 4.5:1 contrast, at every size, with no 3:1 large-text exception; the visuals
gate needs 0 failing texts. Fix and re-render stills until both the review and the measurement pass, then:

```bash
python3 $S/vstate.py attest visuals "Looked at N stills: <what you checked, what you fixed>"
python3 $S/vstate.py advance
```

## Phase 5: render

Benchmark first (renders 6 s from the middle, prints frames/s and the ETA for the whole film), then render in the
background and poll. Segments of 20 s are rendered one `hyperframes render` call each, recorded in
`build/segments/manifest.json`, and joined into `build/silent.mp4` (H.264, yuv420p, exactly `TIMING.total`). Use
`--workers 2` on a shared 4-CPU machine, 4 or more on a laptop.

```bash
node $S/render_hyperframes.mjs --project . --bench 6
mkdir -p build && nohup node $S/render_hyperframes.mjs --project . --workers 2 --max-minutes 100 > build/render.log 2>&1 &
tail -n 3 build/render.log        # poll until it prints "wrote .../build/silent.mp4"
```

If it stops at the budget (exit 3, "stopped at the 100-minute budget") or the job is killed, run the same command
again: finished segments are skipped. A change to the source, the timing or the settings starts the segments over
(`--force` does it on purpose). Measured here with 2 workers at `-q high`: about 4 frames/s on a quiet 4-CPU machine
(8 minutes per minute of film) and 1.7 frames/s when eight jobs shared it (the smoke film's earlier 62 s cut took 18.5 minutes), so
budget up to an hour per 3 minutes of film here and trust the `--bench` ETA.

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

## HyperFrames gotchas

- **Keep the inline registration block in `index.html`.** Lint (`gsap_timeline_not_registered`) wants
  `window.__timelines["main"] = ...` in the same inline script that calls `gsap.timeline`, and segment rendering depends
  on its `segFrom`/`segTo` wrapper.
- **No static `data-duration` on `#root` or the layers.** It fixes the composition length, so a 20 s segment would
  render the whole film. The inline script stamps `data-start`/`data-duration` from the range; lint and render accept it.
- **No `../` in asset paths** (lint `invalid_parent_traversal_in_asset_path`); everything the page loads lives under
  `source/` (`vendor/` is generated by `setup.mjs`).
- **Fonts are local.** Google Fonts is blocked: `@fontsource` Inter, JetBrains Mono and Bangers woff2 are copied into
  `vendor/fonts/` with `font-display: block`. The kit never measures text at build time, so layout does not depend on
  when fonts arrive. JetBrains Mono ligatures are off (`!=`, `<=`, `++` stay as typed): keep code in `.mono`.
- **GSAP plugins are free** since 3.13 and ship in the plain `gsap` npm package (DrawSVG, MotionPath, SplitText,
  Text, CustomEase); `kit/core.js` registers them. Ignore advice about Club plugins or private registries.
- **Seek-safe only.** Every motion goes on `KIT.tl` at an absolute time; no CSS animations, `requestAnimationFrame`,
  `Date.now()` or `Math.random()` (`K.rand(seed)`); values change through `K.stack(...).to(t, html)` or `K.count`,
  never through `onUpdate` writes. Each segment starts from a fresh page seeked to its first frame.
- **Expensive paint halves the speed.** A CSS 3D plane with an animated background cost about half the render time;
  the floor is now a canvas drawn per frame. Avoid `backdrop-filter` and full-frame blur filters.
- **Unknown line ids throw** (`KIT.L.x9: no line "x9"`) and `K.cue` throws when the phrase is not in `say`; the error
  lists what exists. That is deliberate: a silent `NaN` time would drop a whole beat.

## References

| File | Read when |
|---|---|
| `references/hyperframes-guide.md` | Building scenes and rendering with HyperFrames: setup, component catalogue, timing API, recipes |
| `references/quality-bar.md` | Before designing the style, and at every review |
| `references/dsa-five-part-format.md` | Any coding-problem explainer |
| `references/script-format.md` | Writing script.json; reading timing in scene code |
| `references/voice-and-audio.md` | Voices, languages, music moods, mix levels, blocked TTS |
| `references/state-machine.md` | Gates, resume, reopening a phase, long renders |
| `references/environment.md` | Paths, fonts, render speeds, the 2-hour cap, laptop differences |
| `references/lessons-learned.md` | Once per project: why each rule exists |
