---
name: revideo-video
description: Make a finished, narrated explainer MP4 (natural Kokoro voice, music and effects baked in) with Revideo, the Motion Canvas fork with a headless render API, as one continuous TypeScript scene rendered in headless Chromium and encoded with FFmpeg in resumable segments. The look is a dark, warm, cinematic stage with a light pool, parallax dot grid, grain and vignette, a persistent glowing graph under a moving camera, decoded input that flies into the graph, question cards with a countdown ring, a code panel with an active-line highlight, dry-run tables, a complexity ladder, orange chapter wipes and comic callout bursts, all keyed to the voice timing. Use it when someone asks for a Revideo or Motion Canvas style video, a TypeScript/canvas animation rendered headless, or a LeetCode or DSA walkthrough in this style, even if they only say "make a video of this problem". It runs the eight-phase resumable pipeline and delivers the MP4.
---

# Revideo explainer video

Revideo (version 0.11.0, a Motion Canvas fork) draws the film as one continuous TypeScript scene: generator functions animate signals, and `renderVideo` renders it in headless Chromium and encodes it with FFmpeg. The starter project (`assets/template/`) is a complete 71-second demo film with a kit of reusable pieces: a persistent weighted graph under a camera, an input decoder, question cards with a countdown, a code panel, dry-run tables, a complexity ladder, chapter wipes, captions and comic bursts. A new film replaces two files, `src/data.ts` and the chapter functions in `src/film.tsx`; every beat in them waits for its narration line.

Every skill in this family makes the same thing: a finished, narrated MP4 with a natural voice, music and
effects baked in, built through a state machine that survives interruptions and refuses to deliver anything
that has not passed its checks. Only the drawing and rendering steps are specific to Revideo.

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
python3 $S/vstate.py init --tool revideo --slug <short-name> --format dsa-5part   # or --format general
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
[ -d source ] || cp -r "$SKILL/assets/template" source          # the starter project (demo film + kit)
(cd source && [ -d node_modules ] || PUPPETEER_SKIP_DOWNLOAD=1 npm ci --no-audit --no-fund)   # pinned 0.11.0, ~20 s
python3 $S/voice.py --project . --emit source/src/timing.ts
python3 $S/vstate.py advance
```

Kokoro `af_heart` by default (`meta.voice`/`meta.speed` in the script; `references/voice-and-audio.md` lists
voices, including Hindi ones). Changing a `say` re-voices only that line. The emitted timing file is stamped
with a hash; the visuals gate checks your scene code reads the current one.

## Phase 4: visuals

Build the film in `source/src/` (`references/revideo-guide.md` has the kit catalogue, timing API and recipes):

0. Theme (only if the brief names one): `python3 $S/theme.py emit <id> --format ts --out source/src/theme-active.ts`
   (`references/revideo-guide.md`, Themes; with no theme the stub there keeps the original palette).
1. `data.ts`: the facts from brief.md (the subject's nodes and edges, the input as text, the code exactly as
   compiled, the dry-run rows, the approaches with time and space).
2. `film.tsx`: one generator per chapter. Every beat waits for its line: `at(L.p3.voiceAt)`,
   `at(cue('p4', 'seven'))`, `when(t, task)` inside `all(...)` for dense lines; never a bare number of seconds.
   Rearrange the stage only at `CARD[n].coveredAt` (the chapter wipe covers the frame). For the mini example
   (`assets/examples/mini`) the template's demo film is already complete: go straight to the stills.

```bash
(cd source && npx tsc --noEmit -p .)                                        # typecheck; silent when fine
node $S/render_revideo.mjs --project . --stills lines --workers 2           # one PNG per line -> stills/
node $S/render_revideo.mjs --project . --stills chapters --workers 2        # one per chapter
```

Each still takes 15-30 s per worker (the scene re-runs from the start). The stills run ends with a list of
LATE cues (`p2@7.62 +1.97s`: an animation ran past the cue of line p2); fix every one, usually by scheduling the
beats with `when()` inside `all()` instead of one after another. For a quick moving look at a span:
`node $S/render_revideo.mjs --project . --range 40,52` writes `build/preview.mp4`.

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

```bash
node $S/render_revideo.mjs --project . --bench 3      # steady fps per worker and the ETA for the whole film
mkdir -p build && node $S/render_revideo.mjs --project . --workers 4 --max-minutes 100 > build/render.log 2>&1
```

Run the second command in the background and poll `build/render.log` (progress, fps and ETA every 20 s). Use
`--workers 2` on a shared or small machine. It renders 20-second segments in child processes, records them in
`build/segments/manifest.json`, skips finished ones on a re-run, and concatenates them into `build/silent.mp4`
(H.264, yuv420p, CRF 18) with the exact length of the voice timing. Exit code 3 means the `--max-minutes` budget
ran out: run the same command again. Any change to `source/src` or the timing starts the segments over, so
finish the visuals first. Speed: about 1 frame/s per worker on a busy 4-CPU sandbox (the demo's earlier 62 s cut took 24 min
with 2 workers); a laptop with 6 workers is several times faster. Trust the `--bench` ETA over these numbers.

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

## Revideo gotchas

- **Exporter**: Revideo's default WebCodecs exporter fails headless ("Encoder creation error"); the render script
  always passes `exporter: {name: '@revideo/core/ffmpeg', options: {format: 'mp4'}}`, a local Chromium
  (`CHROMIUM=/path` to override; `/opt/pw-browsers/chromium` here) and `--no-sandbox`. Install with
  `PUPPETEER_SKIP_DOWNLOAD=1`. `@revideo/ui` must be installed even headless.
- **Hangs**: a scene exception makes `renderVideo` wait forever. The script renders each segment in a child
  process and kills it on a page error or after `--stall` seconds without progress; read the `page:` line it prints.
- **Text bound to a signal** (`text: () => ...`) throws "The scene is not available in the current context".
  Update text from `onFrame()` or use `counter()`.
- **Ligatures**: JetBrains Mono turns `!=`, `<=`, `++` into single glyphs; every code or mono `Txt` needs
  `letterSpacing: 0.01` (the kit's `CodePanel`, `mono()` and `label()` set it).
- **Fonts** come from `@fontsource` (Google Fonts is blocked here) and `project.ts` awaits each weight before
  frame 1; a new font needs the same two lines there.
- **Determinism**: the scene function runs several times per render and on every worker; no `Math.random()`,
  no wall-clock time, no side effects outside the scene (use `rng(seed)`).
- **Speed**: rendering is CPU-only here. A full-frame gradient or an image drawn scaled or at a fractional
  offset costs 20-30 ms per frame; the same image drawn 1:1 at whole pixels ~5 ms. The kit bakes the backdrop,
  light pool, vignette, caption scrim and grain into textures (`kit/textures.ts`) and rounds their positions;
  do the same for any new full-frame layer, and avoid `compositeOperation` blends and big shadow blurs.
- **File size**: anything that changes every frame across the whole picture is noise to H.264. Grain re-jittered
  each frame made the MP4 22 Mbit/s (165 MB a minute); static grain gives 3.3 Mbit/s. The kit's grain is static
  (`GRAIN_HOLD = 0` in `kit/stage.ts`); keep full-frame noise and flicker effects still.
- **Legibility** (`legibility.py` fails the visuals gate): de-emphasise with colour (`C.muted`, the code panel's
  quiet colours), never with opacity under ~0.6; orange text is `inkOf(C.acc)`. The vignette darkens only the
  backdrop and the caption scrim darkens everything under it, so a lower third goes in `st.lower` (above the scrim).
- **Layout** squashes drawn shapes inside a `layout: true` Rect; keep circles and lines outside layout nodes.
- **Scene file names** must be unique by base name (`film.ts` next to `film.tsx` breaks the `?scene` import).
- **Debug logs** reach the terminal only as a single string argument (`console.log('TL|' + id)`; see `mark()`).
- **Digits in Bangers**: its 7 reads as a 1, so a "700!" burst read "100!". `burst()` sets any text with digits
  in Inter Display 800 italic; keep numbers that matter out of the comic font.

## References

| File | Read when |
|---|---|
| `references/revideo-guide.md` | Building scenes and rendering with Revideo: setup, component catalogue, timing API, recipes |
| `references/quality-bar.md` | Before designing the style, and at every review |
| `references/dsa-five-part-format.md` | Any coding-problem explainer |
| `references/script-format.md` | Writing script.json; reading timing in scene code |
| `references/voice-and-audio.md` | Voices, languages, music moods, mix levels, blocked TTS |
| `references/state-machine.md` | Gates, resume, reopening a phase, long renders |
| `references/environment.md` | Paths, fonts, render speeds, the 2-hour cap, laptop differences |
| `references/lessons-learned.md` | Once per project: why each rule exists |
