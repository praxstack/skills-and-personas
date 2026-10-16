---
name: manim-video
description: Make a finished, narrated explainer MP4 (natural voice, music and effects baked in) with Manim Community Edition, the Python engine behind 3Blue1Brown / 3b1b style math animation. The starter film has a lit dark stage, a persistent weighted graph with glowing active paths, a travelling plane token, chapter cards, question cards with a think countdown, an input decoder, DP rows, a complexity ladder, a code panel without ligatures and comic callouts, all under a camera that pushes in. Use it when someone asks for a Manim video, a math animation, an "anim video", a 3b1b-style explainer, or a LeetCode/DSA or concept walkthrough as a video file. It runs the shared eight-phase pipeline (brief, script, voice, visuals, render, mix, QA, deliver) and renders chapters in parallel, synced to the voice to the frame.
---

# Manim explainer videos

Manim Community Edition 0.21.0 (Python, Cairo renderer) draws the film as code. There is one `FilmScene` per
chapter in `source/scenes.py`, built from a kit (`source/kit/`) that already carries the look:
- a painted backdrop with a world grid,
- a persistent weighted graph whose active path glows, and a plane token that flies routes,
- chapter cards on an emptied stage (the subject fades out first and back in after the card) that collapse into a
  corner tag, and question cards with a countdown ring,
- an input decoder whose entries fly into the graph,
- DP rows, a complexity ladder, a syntax-coloured code panel (no ligatures) and comic bursts,
- a MovingCameraScene camera that pushes in and breathes during holds.

Every moment waits on the voice (`self.beat("p3")`, `self.until(L["p4"].said("seven hundred"))`). Each scene
lasts exactly its share of `TIMING.total`, so `$S/render_manim.py` renders the chapters in parallel and joins
them frame-exactly. No LaTeX is needed: text is Pango (Text/MarkupText) with real superscripts
(`Rich("O(n^(k+1))")`). `Formula()` uses MathTex only when a LaTeX install exists.

Every skill in this family makes the same thing: a finished, narrated MP4 with a natural voice, music and
effects baked in, built through a state machine that survives interruptions and refuses to deliver anything
that has not passed its checks. Only the drawing and rendering steps are specific to Manim.

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
python3 $S/vstate.py init --tool manim --slug <short-name> --format dsa-5part   # or --format general
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
sudo apt-get update && sudo apt-get install -y libpango1.0-dev libcairo2-dev pkg-config   # once per machine; macOS: brew install pango cairo pkg-config
test -d source || cp -r $SKILL/assets/template source
python3 -m venv .venv && .venv/bin/python -m pip install -r source/requirements.txt   # ~1 min; needs Python 3.12 or 3.13 (else python3.13 -m venv)
python3 $S/voice.py --project . --emit source/timing.json
python3 $S/vstate.py advance
```

The venv lives in `<project>/.venv`, never inside `source/`. The render script finds it there. Kokoro
`af_heart` is the default voice (`meta.voice`/`meta.speed` in the script; `references/voice-and-audio.md` lists
voices, including Hindi ones). Changing a `say` re-voices only that line. The emitted `source/timing.json` is
stamped with a hash; the visuals gate checks that your scene code reads the current one.

## Phase 4: visuals

Write the film in `source/scenes.py`. The demo there implements `examples/mini` line by line; it is the
pattern to copy. Keep `source/kit/`, and change the look in `source/kit/style.py` (a registry theme from the
brief is one file: `python3 $S/theme.py emit <id> --format py --out source/kit/theme.py`; guide, **Themes**). The guide
(`references/manim-guide.md`) has the timing API, the kit catalogue and recipes for these moments:
- decode an input,
- trace a route, or reject an illegal one,
- a think countdown,
- a DP row update,
- a code walkthrough synced to the voice,
- camera moves.

1. Plan first: for every line id, decide what changes on screen and where the camera looks. One persistent
   subject appears in every chapter. Each scene starts and ends in the same HOME pose (`back_home()` in the
   demo), so the cut between two separately rendered chapters is invisible. The kit's subjects are `WGraph`
   (graphs) and `ArrayRow` (arrays, DP rows); for anything else (stairs, a grid, a tree) write a component
   in `source/kit/<name>.py` and give it a `settle()`-style method (see the gotcha on group `.animate` below).
   Budget for it: in the LC 70 test the staircase subject was about 400 lines and half the visuals time.
2. Write one `FilmScene` per chapter (`chapters = [n]`; split a long chapter with `span = ("p1", "p7")`). Put
   the code in `film(self)`, not `construct`. Key every moment to a line:
   - `self.chapter_card()`, `self.beat("p2")`, `self.until(L["p4"].said("seven hundred"))`
   - `self.play_until(L["a1"].voiceEnd, ...)`, `self.question("q1", 1)`
   `run_time=` sets how long a motion takes, never when it happens. Unpack kit animations into `self.play(*a, *b)`.
3. Render a draft (854x480, 15 fps) and pull a still for every line:

```bash
python3 $S/render_manim.py --project . --draft --workers 2 --stills lines --from-draft
```

   This takes 2-5 min for the demo's earlier 62 s cut, depending on machine load. Only segments whose code changed
   re-render. The run prints
   `FILM-OVERRUN <Scene>: 0.40 s late for t=...` whenever an animation runs past the line it belongs to. Fix
   every one: use a shorter `run_time`, fewer steps, or start earlier (for example, under the chapter card's
   collapse with `also=`).
4. Render full-size stills, so you can check crisp text and code glyphs (Manim's last-frame mode, with the
   scene stopped at that film time; about 8 s each on a quiet machine, up to 50 s under load). The draft
   stills miss things: the LC 70 test found a clipped burst and two camera pushes cutting text off only at
   full size:

```bash
python3 $S/render_manim.py --project . --stills chapters --workers 2      # plus --stills 41.2,47.8 for busy moments
```

Then open every still (Read the images, and `stills/sheet.png`). Check each against `references/quality-bar.md`
("The review pass"): text inside the safe area, nothing overlapping or cut off, code glyphs correct, the frame
shows what its line says, and it would sit comfortably next to the reference films. Then measure the text:

```bash
python3 $S/legibility.py --project .      # every text >= 26 px and >= 4.5:1; marked copies in stills/legibility/
```

Open the marked copies. Fix by size and colour, not by hiding: the kit's sizes (`SIZE`, 32 px floor for small
labels, code 30 px) and MUTED secondary text pass; text still fading in at a still's moment means it lands too
late. Size and move the graph with `g.place()`/`g.pose()`/`g.settle()`, never a plain `g.scale()`, which shrinks
its weights. Fix and re-render stills until both the look and the measure pass, then:

```bash
python3 $S/vstate.py attest visuals "Looked at N stills: <what you checked, what you fixed>"
python3 $S/vstate.py advance
```

## Phase 5: render

```bash
uptime                                                          # load average: below 1 means the machine is quiet
python3 $S/render_manim.py --project . --bench --workers 2     # fps per worker + ETA; the benched segment is kept
mkdir -p build && nohup python3 $S/render_manim.py --project . --workers 2 --max-minutes 100 > build/render.log 2>&1 &
tail -n 4 build/render.log                                      # poll until it prints "wrote .../build/silent.mp4"
```

Run the full render in the background. Workers: 2 is a safe default on 4 CPUs; use as many as CPUs only when
the load average is below 1 and nothing else will start, since each worker is one CPU-bound Cairo process. It renders one segment per
FilmScene, each with its own `--media_dir`, and records them in `build/segments/manifest.json`. It skips
segments that are done and unchanged, then joins them into `build/silent.mp4` (H.264, yuv420p, 1920x1080,
30 fps). The join is padded or trimmed to exactly `round(TIMING.total * fps)` frames.

Speed measured here (1080p30, 4 CPUs): 11-14 frames/s per worker on a quiet machine (the LC 70 test, a 3.95 min
film, rendered in 5 min with 2 workers), but 1-3.4 frames/s per worker when other heavy jobs share the CPUs
(the demo's earlier 62 s cut took 12 min). Budget about 1.5 min per film minute with 2 quiet workers, and trust `--bench`. Exit code 3 means the budget was reached: run the same command
again to continue. After editing one scene, the same command re-renders only that scene.

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

For NOTES.md, take the versions from `$SKILL/tool.json`. The re-render commands are the Phase 3 setup lines,
`render_manim.py`, `music.py`, `mix.py`. The final message leads with the video (attach or link the MP4).
Then, in a few lines: length, voice used, the style, any limit and which part of it came from the
environment, and any warning. Say that `edge_voice_swap.py` re-voices it on a laptop (for example with
`en-IN-NeerjaNeural`). Do not claim anything the report does not show.

## Manim gotchas

- **Unpack, never AnimationGroup sub-mobjects.** An AnimationGroup over parts of a group re-adds them on top
  (the z-order jump in the first Manim film). The kit returns lists: `self.play(*g.light(0, 1), *row.set(1, 100))`.
  `LaggedStart` is an AnimationGroup too (it reordered a recursion tree's node labels in the LC 70 test): set
  explicit `set_z_index` on layered parts, or stagger with separate `play` calls / `rate_func` offsets.
- **A group `.animate` undoes member animations in the same `play()`.** `g.animate.scale(...)` snapshots every
  member at its current state and restores it at the end, so `self.play(*g.reset(), g.animate.scale(0.5))`
  leaves the edges lit (reproduced). Put every change on one target: `g.settle(center, scale)` for the graph
  (rest + move); for your own subject, `m.generate_target()`, change `m.target` (state and pose), then
  `MoveToTarget(m)`. Moving a group while animating *other* mobjects in the same play is fine.
- **Hide with `conceal()`/`unconceal()`, not `set_opacity`.** `set_opacity(1)` on something hidden also fills
  shapes whose fill was meant to stay transparent (rings turn into red discs). The kit's
  `hide()`/`appear()`/`reveal()` use conceal. Pass layout animations to `chapter_card(also=lambda: [...])`
  as a lambda, so they are built after the card is up.
- **FadeOut restores what it faded.** A faded part that is still inside a group comes back the next time the
  group draws. Remove the part from its group first (`graph.reset()` does this for glows).
- **Updaters cannot swap children.** Manim draws the family it captured when `play()` started. Keep every
  part in the group and park the invisible ones (captions do this). An updater that must run during
  `wait()` needs a `dt` argument: `def upd(m, dt)`. Without it, a plain wait is a frozen frame.
- **Never name attributes `color` or `name` on a mobject.** `color` is a property, so `rung.color = X`
  recolours the whole group.
- **Ligatures and code fonts.** JetBrains Mono / Fira Code ligate (calt), and Text raises on them. Code uses
  DejaVu Sans Mono (shipped in `source/fonts/`) through `CodePanel`/`Mono()`.
- **Thick strokes spike on glyph corners.** Glows and outlines need `joint_type = LineJointType.ROUND`
  (`glow()` and `burst()` set it).
- **No LaTeX.** `Tex`/`MathTex` fail without a TeX install. Use `Rich("O(n^(k+1))")` (MarkupText `<sup>`) and
  `Formula(tex, fallback)`, which uses MathTex only when `latex` is on PATH.
- **Timing is frames.** `play(run_time=x)` renders `len(arange(0, x, 1/fps))` frames, and Manim's default
  quality is 60 fps. Use `until`/`play_until`/`beat`, which count frames the way the render script cuts
  segments. Always render through `render_manim.py`, which passes `--fps`.
- **Parallel renders need separate `--media_dir`** (the text cache races). `render_manim.py` handles this.
- **Speed.** Cairo is CPU only: about 9 min for a 6-min 1080p30 film with 2 quiet workers, 3 to 5x that under load. A moving camera redraws
  everything on every frame, while holds without camera motion are cheap. Bench first, render in the
  background.

## References

| File | Read when |
|---|---|
| `references/manim-guide.md` | Building scenes and rendering with Manim: setup, component catalogue, timing API, recipes |
| `references/quality-bar.md` | Before designing the style, and at every review |
| `references/dsa-five-part-format.md` | Any coding-problem explainer |
| `references/script-format.md` | Writing script.json; reading timing in scene code |
| `references/voice-and-audio.md` | Voices, languages, music moods, mix levels, blocked TTS |
| `references/state-machine.md` | Gates, resume, reopening a phase, long renders |
| `references/environment.md` | Paths, fonts, render speeds, the 2-hour cap, laptop differences |
| `references/lessons-learned.md` | Once per project: why each rule exists |
