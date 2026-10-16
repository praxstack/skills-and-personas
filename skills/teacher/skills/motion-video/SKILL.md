---
name: motion-video
description: "Make a short narrated motion-graphics clip (an MP4 with a natural voice, music and burned-in karaoke captions) from one editable film.json of shots and ready-made blocks: titles, statements, steps, compare cards, counters that count up, bar, line and ring charts read from CSV or JSON data, a multiple-choice question with a think countdown and a reveal, a graph that flies routes, code with a focus bar and an array with pointers. Lays out for 16:9, 9:16 (Shorts, Reels, TikTok safe areas), 1:1 and 4:5, ships a browser editor where every word, number, colour and time can be changed, and fills the narration's numbers from the same data. Use it for daily-question Shorts, data or metrics clips, launch and product explainers, social cuts, or when someone asks for a Claude Motion style clip without Motion; for long five-part DSA films prefer the other kits."
---

# Motion-style clips (film.json + blocks)

Claude Motion (beta, Team and Enterprise plans, started with `/motion` in claude.ai) makes animations as
editable code and exports them as MP4. This skill brings the same way of working to any account and to Claude
Code: the clip is **data, not hand-written animation**. `source/film.json` lists shots; each shot starts on a
line of the narration and holds one to three blocks from a tested library; every change inside a block (a
route flown, a count, a reveal) is a cue placed on a spoken phrase. The engine turns that into one paused GSAP
3.15 timeline keyed to the voice, lays the blocks out for the frame's shape and safe areas, lights the backdrop
per shot, burns in karaoke captions, and exposes the page contract `capture.mjs` renders frame by frame.
Changing a word, a number or a colour is a one-line edit (or a field in `source/editor.html`), never a re-animation.

Every skill in this family makes the same thing: a finished, narrated MP4 with a natural voice, music and
effects baked in, built through a state machine that survives interruptions and refuses to deliver anything
that has not passed its checks. Only the drawing and rendering steps are specific to motion-video.

`$SKILL` below means this skill's base directory (the folder this file is in). `$S` is `$SKILL/scripts`.

## Non-negotiables (and why)

1. **A video is an MP4 with the voice in it.** Not an interactive page, not slides, not a silent render with
   "add your own narration". A person once had to ask three times for a video and kept getting click-through
   pages. The editor is a tool for changing the clip; it is never the deliverable.
2. **Natural voice, always tried.** Kokoro runs offline everywhere (`$S/voice.py` installs it). Never tell the
   person a voice, or any capability, is impossible until the alternatives are tried and recorded with
   `vstate.py limit ... --tried ... --tried ...`. A person was once told TTS was impossible when it was not, and
   read it as being treated as less deserving. Say plainly which limits come from the environment.
3. **The picture follows the voice.** Voice first, then place shots and cues on line ids and spoken phrases.
   Never stretch audio to fit, never write a time in seconds.
4. **Hit the quality bar on the first attempt** (`references/quality-bar.md`): one persistent subject carried
   across shots, every line changes something on screen, eased motion, depth and light, music and effects.
5. **Look at your frames.** The visuals and QA phases need a written attestation of what you looked at. Open
   the stills and the contact sheet with the Read tool; describe what you saw and what you fixed.
6. **Numbers come from somewhere.** A data clip reads its numbers from files in `source/data/`, and the
   narration says the same numbers through `motion_fill.py`. Never type a number into film.json or the script
   that a dataset already holds. For a coding question, compile and run the code before writing a word.

## Start or resume

```bash
python3 $S/vstate.py --project <project> status      # always first; prints the next command
```

New project (keep it on local disk, not a synced folder, while rendering). Pick the frame now; it is the
script's `meta.width`/`meta.height` too:

```bash
mkdir -p <project> && cd <project>
python3 $S/vstate.py init --tool motion --slug <short-name> --format general                          # 16:9
python3 $S/vstate.py init --tool motion --slug <short-name> --format general --width 1080 --height 1920   # 9:16
python3 $S/vstate.py set min_minutes=0.5 max_minutes=1.5     # a clip, not a lesson (the default floor is 1 min)
```

Square is 1080x1080 and 4:5 is 1080x1350. After an interruption run `status` and continue from the phase it
names; `references/state-machine.md` explains every phase and gate.

## Phase 1: brief

Ask only what you cannot default (topic, and anything that changes the goal); default the rest and say which.
Write `brief.md` with **Topic**, **Audience**, **Format** (general; frame and length), **Persistent subject**,
**Style** (look `paper` or `ink`, or a registry theme; brand and tag), **Facts** (real outputs, data sources),
**Output**. Examples: `$SKILL/assets/examples/question-short/brief.md` (a 9:16 question Short) and
`$SKILL/assets/examples/data-clip/brief.md` (a 16:9 data clip). Then `vstate.py advance`.

## Phase 2: script

Write `script.json` (`references/script-format.md`): chapters, and per line an `id`, `chapter`, `cap` (on
screen) and `say` (spoken, words only), `think` after a question. A clip is 8 to 14 lines; one line is one
beat on screen. For a data clip write `script.template.json` instead, with a reference in double braces where
each number goes (`set.col:agg`, see `references/motion-guide.md` section 6). Then copy the template (the first
line of Phase 3), put the data in `source/data/`, name it under `"data"` in `source/film.json`, and let
`python3 $S/motion_fill.py --project .` write `script.json`. `vstate.py advance` checks it, and for a data clip
that it still matches the template and the data: edit the template or the CSV, never `script.json` by hand.

## Phase 3: voice

```bash
[ -d source ] || (cp -r $SKILL/assets/template source && cd source && npm ci --no-audit --no-fund && npm run vendor)
python3 $S/voice.py --project . --emit source/timing.js
python3 $S/vstate.py advance
```

`npm run vendor` copies GSAP and the fonts (Inter, Fraunces, JetBrains Mono) from npm into `source/vendor/`,
so nothing is fetched at render time. Kokoro `af_heart` by default (`meta.voice`/`meta.speed`;
`references/voice-and-audio.md` lists voices, including Hindi ones). Changing a `say` re-voices only that line.
When a CSV changes later, `vstate.py status` sends you back to the script: run `motion_fill.py`, `advance`, then
`voice.py` again. Only the lines whose numbers changed are re-spoken, and the bars and counters follow on their own.
In a delivered package, run them in `deliver/source/`, where film.json sits beside the script and the scripts are
in `pipeline/`: `python3 pipeline/motion_fill.py --project .`, then
`python3 pipeline/voice.py --project . --emit timing.js` (the page's timing file is beside it there), then
`cp voice/narration.wav ../voice/narration.wav` so the preview plays the new voice. `motion_fill.py` prints these
commands for the folder it ran in.

## Phase 4: visuals

Write `source/film.json`. Start from the closest starter and read `references/motion-guide.md` (the format,
time references, layout, every block's fields and cues, recipes):

| Starter (`$SKILL/assets/examples/`) | Frame | Shows |
|---|---|---|
| `question-short/` | 9:16 | a carried graph, a question with countdown, pick and reveal, routes, a price array |
| `data-clip/` | 16:9 | CSV datasets, counters, sorted bars lit on the spoken names, steps in two columns, motion_fill |
| `gallery/` | 16:9 | every other block: compare, steps with cues, line + annotate, ring, stat with spark, code focus, array pointers |

Copy its `film.json` (and `data/`) into `source/`, then change it shot by shot. Plan first: for every line id,
what changes on screen. Give the film one subject that is carried across shots (the same block `id` in
consecutive shots glides instead of leaving), and keep its share of the frame the same in every shot it is in
(`split`), or its text shrinks with it.

Theme: the template's `theme.js` stub means the look named in `film.json` (`paper`, light, or `ink`, dark).
For one of the 30 registry themes (`references/themes.md`):
`python3 $S/theme.py emit <id> --format global --out source/theme.js` and `python3 $S/vstate.py set theme=<id>`.
Either way the engine checks every ink against the lit backdrop and darkens (or lightens) any that falls
under 4.6:1; `motion_check` prints what it changed.

Preview while you work (optional): `python3 -m http.server 8765 --bind 127.0.0.1` in the project folder, then
`http://127.0.0.1:8765/source/index.html` (space plays with the narration) or `.../source/editor.html` (every
field editable, preview at 16:9, 9:16, 1:1 or 4:5; "Save film.json" downloads the edited file, which you put
in `source/`). Stop the server when done.

Lint until it prints `ok` with no warning you have not judged:

```bash
node $S/motion_check.mjs --page source/index.html                 # add --aspect 9:16 to preview another frame
```

It fails on a film.json that does not build (every message names the shot, the block and the field), page
errors and missing files; it warns on overlapping tweens (the flicker cause), a line longer than 2.5 s where
nothing changes, a carried block that shrinks, and, at every line and every cue, text off the frame or outside
the safe area, block text in the caption band, text under 26 px and text overlapping across blocks. It prints
the shots with their times and a ready `--stills` list of cue moments. Then shoot stills (W and H are the
script's frame):

```bash
node $S/capture.mjs --page source/index.html --width W --height H --prime 0.25 --stills chapters --timing timing.json --stills-dir stills
node $S/capture.mjs --page source/index.html --width W --height H --prime 0.25 --stills lines --timing timing.json --stills-dir stills
node $S/capture.mjs --page source/index.html --width W --height H --prime 0.25 --stills <the list motion_check printed> --stills-dir stills
python3 $S/legibility.py --project .           # every text 26 px and 4.5:1, measured on the frame's short side
```

A film with a `screen` block (recorded footage) also needs `node $S/capture.mjs --page source/index.html
--footage-map footage-map.json` before qa, so the recording's own small interface text is reported apart from
the film's text (references/motion-guide.md, "screen").

Open every still (Read the images) and check it against `references/quality-bar.md` ("The review pass"): text
inside the safe area (on 9:16, nothing in the bottom 430 px or the right 120 px), nothing overlapping or cut
off, the frame shows what its line says. Fix film.json (not the engine) and re-shoot until it does, then:

```bash
python3 $S/vstate.py attest visuals "Looked at N stills: <what you checked, what you fixed>"
python3 $S/vstate.py advance
```

## Phase 5: render

W, H and FPS are the frame `vstate.py status` shows (the script's meta).

```bash
node $S/capture.mjs --page source/index.html --width W --height H --fps FPS --prime 0.25 --bench 3   # fps and ETA
mkdir -p build
node $S/capture.mjs --page source/index.html --width W --height H --fps FPS --out build/silent.mp4 --prime 0.25 --workers 4 --max-minutes 100 > build/render.log 2>&1
python3 $S/vstate.py advance      # checks codec, size, fps, duration against the voice timing, segments
```

Run the render in the background and poll `tail -n 3 build/render.log`; exit code 3 means the budget ran out,
so run the same command again (finished segments are kept). Measured here (4 CPUs, no GPU): `--bench` gave
11.7 frames/s for one worker on a quiet machine (9:16 Short); the 51 s Short and the 49 s data clip rendered at
the same time with 2 workers each (about 5.5 frames/s per worker) in 2.3 minutes apiece. Editing anything in `source/` voids the segments.

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
python3 $S/vstate.py notes-md > NOTES.md      # fill every (fill in): versions, look, data sources, re-render commands
python3 $S/package.py --project . --to <deliver folder>
python3 $S/vstate.py advance
python3 $S/vstate.py report                   # use this for the final message
```

The final message leads with the video (attach or link the MP4), then in a few lines: length and frame, voice,
look, where the numbers came from, any limit and which part of it came from the environment, any warning, and
that `source/editor.html` changes any word, number or colour (then lint, re-shoot, re-render). Do not claim
anything the report does not show.

## motion-video gotchas

- **Write film.json, not engine code.** A missing block type is the one reason to touch `source/engine/`:
  add it with `M.block(...)` in a new file loaded after `engine/blocks-dsa.js` (the guide's last section shows
  the shape). Edits to the shipped blocks belong in this skill, not in one film.
- **Times are references, never seconds.** `"r3"`, `"r3:seven hundred"`, `"r3@0.6"`, `"r3.end -0.3"`. A phrase
  must be in that line's `say` (not its `cap`): the error quotes the `say` text. Re-voice before chasing a
  phrase error after editing a `say`.
- **A carried block keeps the size it was built at.** Give it the same `split` share in every shot, or the
  engine warns that its text shrinks (the gallery's line chart did, at 56%, until it got the same split).
- **Blocks enter at the start of their shot.** Something that should appear on a later line is either a cue
  (`chips`, `show`, `right`, `reveal`, `count`) or a new shot on that line.
- **9:16 is narrow.** Code lines over about 40 characters do not fit at the 28 px floor on a 1080-wide frame
  (`motion_check --aspect 9:16` warns), and four options read best as a 2x2 grid (short answers do that on
  their own).
- **A superscript is drawn at 28 px at least** (`O(n^(k+1))`), and a lone `*` is just a character
  (`data/*.csv`, `3 * 4`); `*two words*` is a highlight (no space just inside the stars). Captions keep a
  literal `*` and drop the highlight stars.
- **Never read the clock.** Everything that moves is a tween on `M.tl` or a pure function of `t` in
  `M.ambient`; the timeline is padded to exactly the voice's length.

## References

| File | Read when |
|---|---|
| `references/motion-guide.md` | Writing film.json: shots, time references, layout, every block's fields and cues, data, recipes, adding a block |
| `references/quality-bar.md` | Before designing the clip, and at every review |
| `references/script-format.md` | Writing script.json; the timing fields the engine reads |
| `references/themes.md` | Picking a registry theme instead of paper or ink |
| `references/voice-and-audio.md` | Voices, languages, music moods, mix levels, blocked TTS |
| `references/state-machine.md` | Gates, resume, reopening a phase, long renders |
| `references/environment.md` | Paths, fonts, render speeds, the 2-hour cap, laptop differences |
| `references/lessons-learned.md` | Once per project: why each rule exists |
| `references/dsa-five-part-format.md` | Only for a full coding-problem film (a Short asks one question instead) |
