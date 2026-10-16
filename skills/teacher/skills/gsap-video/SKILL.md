---
name: gsap-video
description: Make a finished, narrated explainer MP4 (natural voice, music, effects) from one GSAP-animated web page, in a dark editorial look with coloured chapter lighting, a camera that pushes and pans over a persistent SVG graph (edges drawn on, a paper-plane token flying routes), comic callout bursts, chapter slabs, question cards with a think countdown, a code panel with an active-line highlight and a dry-run table. Use it for LeetCode/DSA walkthroughs and concept explainers when someone asks for a GSAP video, a motion-graphics or kinetic-typography explainer built with web tech (HTML, SVG, CSS), or a polished "Claude-made animation" style film rendered frame by frame to MP4.
---

# GSAP explainer videos

One HTML page (DOM + SVG, plus one small background canvas) is animated by a single paused GSAP 3.15 timeline.
Every tween sits at a line's time from the voice (`L.p3.voiceAt`, `L.p3.at('each flight')`), never at a
hard-coded second, and the timeline is padded to exactly `TIMING.total`. `window.renderFrame(t)` seeks the
timeline, so `capture.mjs` can draw any frame on any worker and screenshot it into an MP4. The starter film
(`assets/template/`) is a complete 71 s explainer built from a reusable kit: a persistent graph in a world that
the camera frames, an input decoder whose values fly into the graph, chapter slabs and a lower third, question
cards, comic bursts and stamps, a code panel, a dry-run table, a complexity ladder and a result card. GSAP, its
plugins and the fonts are vendored from npm into `source/vendor/`, so nothing loads from a CDN at render time.

Every skill in this family makes the same thing: a finished, narrated MP4 with a natural voice, music and
effects baked in, built through a state machine that survives interruptions and refuses to deliver anything
that has not passed its checks. Only the drawing and rendering steps are specific to GSAP.

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
python3 $S/vstate.py init --tool gsap --slug <short-name> --format dsa-5part   # or --format general
python3 $S/vstate.py set min_minutes=3 max_minutes=4    # only if the person asked for a length (default 2 to 8)
```

`init` uses the current folder as the project; every later command takes `--project <project>` or runs there.

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
cp -r $SKILL/assets/template source && (cd source && npm ci --no-audit --no-fund && npm run vendor)   # ~5 s
python3 $S/voice.py --project . --emit source/timing.js
python3 $S/vstate.py advance
```

`npm ci` installs the pinned GSAP, fonts and playwright-core (no browser download); `npm run vendor` copies GSAP,
its plugins and the woff2 fonts into `source/vendor/`, which is what the page loads. Kokoro `af_heart` by
default (`meta.voice`/`meta.speed` in the script; `references/voice-and-audio.md` lists voices, including Hindi
ones). Changing a `say` re-voices only that line. The emitted `source/timing.js` is stamped with a hash; the
visuals gate checks your scene code reads the current one.

## Phase 4: visuals

Write the film in `source/scenes.js`; the demo there implements `examples/mini` line by line and is the
pattern to copy. Keep the kit (`source/kit/`) and change the look in `source/tokens.js`. If the brief names a theme
(`references/themes.md`), emit it with `python3 $S/theme.py emit <id> --format global --out source/theme.js`
(`gsap-guide.md` section 9 has the role mapping). The guide
(`references/gsap-guide.md`) has the kit catalogue and recipes (decode an input, trace a route, reject a route,
think countdown, DP row update, code walkthrough, camera moves, monotonic stack).

1. Plan on paper first: for every line id, what changes on screen and where the camera looks. One persistent
   subject stays in the world for the whole film; panels come and go around it. The kit has two subjects:
   `K.graph` (graphs, routes) and `K.barRow` + `K.stackCol` (arrays, monotonic stacks, two pointers). For any
   other shape (grid, tree, linked list, intervals), write a new component in `source/kit/<name>.js` in the
   same style (world-space SVG in `K.layer.*`, every change a `K.to` at a line time, `K.channel` for values
   that change often), load it with a `<script>` tag after `kit/array.js`, and add its classes to
   `styles.css`. Budget for this: the LC 739 test film's array subject was about 350 lines, the most work in
   the film. Lay the subject out for the busiest chapter first (it must share the frame with the ladder or
   the code panel), then check the others.
2. Place every tween at a line time: `L.<id>.voiceAt`, `.at('phrase')`, `.p(0.5)`, `.vEnd`, `.end`. Use the
   kit (`K.to/K.fromTo/K.set`, never raw `gsap.to`), so tween fights are detected.
3. Preview while you work (optional): from the project folder run
   `python3 -m http.server 8765 --bind 127.0.0.1`, open `http://127.0.0.1:8765/source/index.html` (space plays
   with the narration, arrow keys step one frame, shift+arrow 5 s, `?t=40` opens at 40 s). Stop the server when done.
4. Lint until it prints `ok` with no warning you have not judged:

```bash
node $S/gsap_check.mjs --page source/index.html
```

   It fails on page errors, a missing font or file, or a broken build; it warns on overlapping tweens (the
   flicker cause), a timeline longer than the voice, and, at every line and every comic burst or stamp, text
   off-frame or outside the 96 px safe area, text in the caption band, world text the camera shrinks below
   26 px, and blocks overlapping; and at every chapter card, anything in screen space (panels, notes, bursts,
   the caption, the lower third) visible under the slab. Then `legibility.py` (below) measures every text in
   the stills: 26 px and 4.5:1 at least.
5. Shoot stills (one per chapter and one per line, JPEG, about 30 s for the demo):

```bash
node $S/capture.mjs --page source/index.html --prime 0.25 --stills chapters --timing timing.json --stills-dir stills
node $S/capture.mjs --page source/index.html --prime 0.25 --stills lines --timing timing.json --stills-dir stills
```

   Add exact times for every burst and busy moment: `gsap_check` prints the burst and stamp times as a ready
   list (`bursts/stamps at full size (for capture.mjs --stills): 34.33,37.60,...`); pass it as
   `--stills 34.33,37.60,... --stills-dir stills` (line stills are taken 65% into each line and can miss a
   burst that lives for one second).

Then open every still (Read the images). Check each against `references/quality-bar.md` ("The review pass"): text
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
node $S/capture.mjs --page source/index.html --prime 0.25 --bench 3     # fps per worker and the film's ETA
mkdir -p build
node $S/capture.mjs --page source/index.html --out build/silent.mp4 --prime 0.25 --workers 4 --max-minutes 100 > build/render.log 2>&1
```

Run the render in the background (it takes longer than a tool call) and poll `tail -n 3 build/render.log`.
Use `--workers 2 --segment 10` on a machine shared with other jobs (smaller segments lose less if the job is
killed). Speed measured here (4 CPUs, no GPU): `--bench` gave about 7 frames/s per
worker on a nearly idle machine and 3-5 under heavy load; with eight other renders sharing it, the demo's earlier 62 s cut
(1867 frames) rendered with 2 workers in 4.7-6.2 minutes (6.6-5.2 frames/s at load averages 20-36). A 6-minute
film with 4 workers on a quiet machine needs roughly 10-20 minutes. The render is
split into 20 s segments in `build/segments/`; exit code 3 means the `--max-minutes` budget ran out: run the
same command again and only unfinished segments are drawn. Editing anything in `source/` invalidates the
segments (the page is stamped), so finish the visuals first. Done when the log says `wrote build/silent.mp4`.
Check its bit rate (`ffprobe -v error -show_entries format=bit_rate -of default=nw=1 build/silent.mp4`): the
demo is 3-5 Mbit/s; tens of Mbit/s means something noisy changes every frame (see the gotchas).

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
stills, and grab the frame at each comic burst from the final MP4 (`ffmpeg -ss <t> -i out/<slug>.mp4 -frames:v 1
burst.jpg`): the sheet samples every couple of seconds and misses a burst that lives for one. If anything is
wrong, `vstate.py reopen visuals --reason "..."`, fix, and come back through render and mix. When it is right:

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

## GSAP gotchas

- **Single-frame flicker** comes from two tweens on the same element and property whose time ranges overlap
  (the frame then depends on seek order), and from `from()`/`fromTo()` tweens that render their start state at
  build time. The kit's `K.fromTo` sets `immediateRender: false`, `K.init` sets the pre-film state, and
  `gsap_check.mjs` lists every overlap. Render with `--prime 0.25` so each worker plays up to its segment the way
  a viewer would.
- **Never read the clock.** No `Date.now()`, `requestAnimationFrame` or CSS animations/transitions: anything
  that moves must be a tween on `K.tl` or a pure function of `t` registered with `K.everyFrame(fn)`.
- **Fonts**: the page waits for `document.fonts.load(...)` before building, because text widths are measured.
  JetBrains Mono needs ligatures off (`font-feature-settings: "calt" 0, "liga" 0`, already in `.mono`), or
  `!=`, `->`, `<=` turn into single glyphs. Google Fonts are blocked here; the woff2 files come from npm.
- **SVG filters (blur, drop-shadow) are slow** in a screenshot capture and some blur differently per frame. Glow
  and depth come from radial gradients, stacked strokes and one half-resolution background canvas.
- **Animated grain or noise bloats the file.** Re-randomising grain every frame made the MP4 7x bigger (37
  vs 5 Mbit/s); the template keeps its grain still (that also
  halved render time). Check `ffprobe` on the render: a film like the demo should
  be a few Mbit/s.
- **Full-screen layers cost time.** Every full-screen DOM layer (grain, vignette, light) is composited for
  every frame: those layers cost about 75 ms a frame here. The template draws all atmosphere into one
  half-resolution canvas instead (about 25 ms).
- **A phrase that is not in the line's `say`** makes `L.x.at('...')` throw with the line's text, and an unknown
  line id throws listing the real ids: after editing `say`, re-voice before fixing the scenes.
- **Numbers in display fonts**: Bangers' 7 reads as a 1 and it has capitals only, so `K.callout` sets digits
  and lowercase letters in Inter Black (write comic words in CAPITALS); keep any number that matters in Inter
  or JetBrains Mono.
- **Text in world space shrinks with the camera.** The graph's weights and SRC/DST flags are 36 px and its
  badges 32 px in world space: keep the camera scale at 0.8 or more (they land at 26-29 px) by giving the
  subject a big enough screen box, and narrow the panel beside it rather than shrinking the graph.
  `gsap_check` warns below 26 px; `legibility.py` fails it.
- **Chapter cards cover the left 900 px** from `K.cardIn(n)` (about 0.8 s before the chapter) to
  `K.cardClear(n)` (about 0.56 s into it). Hide the last chapter's left-side panels so they are gone by
  `K.cardIn(n)` and bring the new chapter's in at `K.cardClear(n)` or later; question cards and the first
  caption wait by themselves. The graph too: when it stands in the left half at a chapter change, fade it out
  before the card and back in after it (`G.fade(K.cardIn(n) - 0.35, 0, 0.3); G.fade(K.cardClear(n), 1, 0.45)`)
  and reframe the camera while it is hidden. In the LC 739 test film the chapter 4 card swept out over the ladder that
  chapter was already building and over its first caption.
- **Dimmed text must stay readable.** Code lines outside the focus dim to opacity 0.75 (still at least 4.5:1)
  and question words not yet spoken to 0.5: mark the focus with the bar, colour or weight, never by making the
  rest near-invisible. Something still fading in when a still is taken is a timing problem: land it earlier.
- **GSAP version**: 3.13+ made every plugin free (DrawSVG, MotionPath, MorphSVG, SplitText); the template pins
  3.15.0 and vendors it. Do not swap in a CDN `<script>`: renders must work offline.

## References

| File | Read when |
|---|---|
| `references/gsap-guide.md` | Building scenes and rendering with GSAP: setup, component catalogue, timing API, recipes |
| `references/quality-bar.md` | Before designing the style, and at every review |
| `references/dsa-five-part-format.md` | Any coding-problem explainer |
| `references/script-format.md` | Writing script.json; reading timing in scene code |
| `references/voice-and-audio.md` | Voices, languages, music moods, mix levels, blocked TTS |
| `references/state-machine.md` | Gates, resume, reopening a phase, long renders |
| `references/environment.md` | Paths, fonts, render speeds, the 2-hour cap, laptop differences |
| `references/lessons-learned.md` | Once per project: why each rule exists |
