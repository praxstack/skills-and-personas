# Manim guide (Manim Community Edition 0.21.0)

1. Setup
2. Project anatomy
3. Timing API
4. Kit catalogue
5. Recipes
6. Rendering
7. Gotchas
8. Laptop differences

## 1. Setup

```bash
apt-get update && apt-get install -y libpango1.0-dev libcairo2-dev pkg-config   # ~1 min once per machine
cp -r $SKILL/assets/template source                                              # inside <project>
python3 -m venv .venv && .venv/bin/python -m pip install -r source/requirements.txt
```

The pip step took 72 s here with a warm pip cache (expect 2-3 min cold). It installs manim 0.21.0, ManimPango
0.7.0, pycairo 1.29.2, Pygments 2.21.0, numpy 2.5.3 and their dependencies, all pinned in
`source/requirements.txt` and tested on Python 3.13. ffmpeg 6+ must be on PATH (the shared pipeline needs it
anyway).

- **Venv location.** Keep the venv at `<project>/.venv`. `render_manim.py` looks there first (then
  `$MANIM_PYTHON`, then `--python`). Never put it in `source/`: the visuals gate and `package.py` walk that
  folder.
- **No LaTeX.** None is needed and none is installed here. All text is Pango. `Formula(tex, fallback)` returns
  MathTex only when `latex` is on PATH, and otherwise the Rich fallback.
- **Fonts.** The film uses Inter / Inter Display from the system (`fonts-inter` on Ubuntu) and DejaVu Sans Mono,
  which is shipped in `source/fonts/` and registered automatically. A `FONT-MISSING` line on stderr means
  Pango fell back to another face.

Check the install in one command (prints the version and the fonts it sees):

```bash
.venv/bin/python -c "import manim, manimpango; print(manim.__version__, [f for f in manimpango.list_fonts() if 'Inter' in f or 'DejaVu Sans Mono' in f][:4])"
```

## 2. Project anatomy

```
source/
  scenes.py          THE FILM: one FilmScene per chapter. Replace it per film; keep the kit.
  timing.json        written by voice.py --emit source/timing.json (the shipped one is the mini demo's)
  requirements.txt   pinned Python packages
  fonts/             DejaVu Sans Mono (+ any .ttf/.otf you drop in, registered at import)
  kit/
    style.py         palette, fonts, SIZE, px()/fs() unit helpers, Z layers, safe area, drift
    timing.py        TIMING, L, LINES, TOTAL, lines_in(), bounds(): the voice clock
    film.py          FilmScene: until/beat/play_until, camera, HUD pinning, captions, chapter/question cards
    backdrop.py      painted backdrop PNG (cached in source/.cache/) and the world dot grid
    fx.py            glow, halo, soft_shadow, ripple, pulse, roll, conceal/unconceal
    graph.py         WGraph (persistent subject), Token (plane), fly(), reject(), auto_layout()
    cards.py         chapter card + corner tag, question card + think ring, title_block, lower_third
    decoder.py       InputDecoder: raw input text whose entries fly into the graph
    table.py         ArrayRow, DPTable, INF
    ladder.py        complexity Ladder with the pick marked
    code.py          CodePanel (Code + Pygments style in the palette, active line, chunked reveal)
    callout.py       burst() comic starburst, pop()
```

- **Units.** The frame is 14.22 x 8 units at 1920x1080, and 1 unit = 135 px. `px(n)` converts pixels to units.
  `fs(n)` gives the Manim `font_size` for an n-px em: `fs(px) = px / 1.877`. Text helpers take px sizes or
  `SIZE` keys: `T("label", 36)`, `H("Title", "headline")`.
- **Text sizes.** `SIZE`: hero 150, title 96, headline 72, question 50, body 44, caption 42, label 36, code 30,
  small 32. `SIZE["small"]` (32 px) is the kit's floor for tags, chips and headers, and `MIN_TEXT = 32` is
  what the graph keeps its weights and node numbers at when posed small. The quality bar's floor is 26 px, but
  `legibility.py` measures cap height, a 480p draft still reads 1-3 px low, and a lowercase-only word ("new",
  "src") reads at its x-height (75% of the size): set short labels in capitals or 6 px larger.
- **Layers.** Z order comes from `Z`: `grid < glow < edge < node < token < panel < card < callout < hud <
  caption`. Set it with `set_z_index` on the whole family. The kit already does this.
- **The look** lives in `style.py`: the BG/PANEL/INK/MUTED/DIM neutrals, and the AMBER (active), CYAN (start,
  reads), CORAL (cost, illegal), VIOLET (code keywords) and MINT (pick, done) accents. Change colours there,
  never inline. MUTED (`#9DA7C8`, 7:1 on PANEL) is the secondary text colour; DIM (2:1) is for strokes and
  the grid, never for text. Never put text on a filled cell or pill in a colour close to the fill.

## 3. Timing API

`source/timing.json` holds the voice layout. `from kit import *` gives you:

| Name | Meaning |
|---|---|
| `L["p3"]` | a Line: `.start .voiceAt .voiceDur .voiceEnd .end .think .thinkAt .chapter .cap .say` |
| `L["p3"].at(0.5)` | halfway through the spoken part |
| `L["p4"].said("seven hundred", 0.1)` | estimated moment the voice reaches that phrase (+0.1 s); KeyError if absent |
| `TOTAL`, `FPS`, `CHAPTERS`, `lines_in(n)` | film length, chapter list, the lines of chapter n |

Inside a `FilmScene` (one per segment, `chapters = [n]` or `span = ("p1", "p7")`):

| Method | Does |
|---|---|
| `self.beat("p3", offset=0)` | hold (camera breathing) until line p3's voice starts; returns the Line |
| `self.until(t)` | hold until film time t; prints `FILM-OVERRUN` if t has already passed by more than a frame |
| `self.play_until(t, *anims, rate_func=...)` | play so the animations end exactly at t |
| `self.play_at(t, *anims, run_time=0.6)` | wait for t, then play |
| `self.now()`, `self.left(t)`, `self.fit(t, rt)` | current film time; seconds until t; run time clipped to fit before t |
| `self.split(t, n, least=0.3)` | run time for n back-to-back plays that all end by t (whole frames, so n plays never overrun) |
| `self.hold_caption("x1", t)` | keep line x1's caption hidden until t (the chapter card uses it) |
| `self.chapter_card(also=lambda: [...])` | card over the chapter gap: the stage goes out under an opaque shade (0.28 s), the card enters on the empty stage, collapses into the corner tag over 0.45 s from 0.6 s before the first line's voice, playing `also` (your layout moves) under the shade, which lifts in the second half of the collapse (the subject is back 0.15 s before the voice); that line's caption waits for the collapse |
| `self.question("q1", 1)` | question card + countdown ring over the line's `think` seconds; out at the line's end |
| `self.cam(center, zoom=1.2)`, `self.push(mob, zoom, offset)`, `self.home()` | camera animations (play them) |
| `self.hud(mob)` | pin mob to the screen (camera moves do not affect it) |

Never type a number of seconds for *when*; `run_time` is only for *how long*. Each segment starts where the
previous line ends and ends at its last line's end, so the segments tile `[0, TOTAL]`. `FilmScene.finish()`
holds to the segment end automatically, and the frame counting (`frame_of(t) = round(t*fps) - round(t0*fps)`)
matches how the render script cuts segments.

## 4. Kit catalogue

Every method returns a **list of animations**. Unpack it: `self.play(*a, *b, run_time=0.5)`.

**Text**
- `T(s, size, color, weight)`: Inter. `H(...)`: Inter Display headline. `Mono(...)`: DejaVu Sans Mono.
- `Rich("O(n^(k+1))", 44, CORAL, "BOLD")`: MarkupText with superscripts (`^x`, `^(...)`) and subscripts (`_(...)`).
- `Formula(r"O(n^{k+1})", "O(n^(k+1))")`: MathTex when LaTeX exists, Rich otherwise.
- `wrap_lines(s, n)`, `balanced_two(s, n)`, `stack(*mobs)`.

**Light and depth**
- `glow(mob, AMBER)`: wide translucent stroke copies; add them behind mob.
- `halo(center, r, color)`: soft disc light. `soft_shadow(card)`: drop shadow.
- `ripple(mob, CYAN)`: expanding ring (play it). `pulse(mob, color)`: scale + colour flash.
- `roll(old_text, new_text)`: number roll; afterwards replace the reference to the old text in your group.
- `conceal(mob)` / `unconceal(mob)`: hide a mob and restore its exact per-part opacities.

**Subject: graph**
- `WGraph(nodes, edges, pos=None, radius=0.46, bend=None, label_side=None, weight_size=34, node_size=38)`.
  `edges` are `(u, v, w)`. Two-way pairs curve apart, and `pos` defaults to `auto_layout()`. Its parts:
  `g.nodes[u]` (`.disc .ring .lab`), `g.edges[(u, v)]` (an Arrow), `g.weights[(u, v)]`, `g.c(u)` (centre point).
- `g.hide()` then `g.appear()` or `g.appear_nodes()`. `g.grow_edge(u, v)`, `g.show_weight(u, v)`.
- `g.light(u, v, AMBER)` / `g.unlight(u, v)`: the edge stays lit with a glow.
- `g.fire(u, v, CYAN)`: a pulse runs along the edge (one animation).
- `g.mark(u, CYAN, "START")` / `g.unmark(u)`: ring colour, halo, tag. `g.badge(u, "700")` returns a pill to FadeIn.
- `g.beside(u, v, mob)` puts mob next to edge (u, v) on the side away from its weight pill, clear of every pill
  and node; `g.free_point(u, v, w, h)` returns such a spot for a w x h box.
- `g.dim(keep=[(0, 1)])` / `g.undim()`. `g.reset()`: every edge, ring and glow back to rest.
- Size and place the graph with `g.place(center, scale)` (instant) or `g.pose(center, scale)` (one
  `MoveToTarget`, play it), never a plain `g.scale()`: they keep weights and node numbers at `MIN_TEXT` (32 px)
  on screen however small the graph gets (`fit_labels()`), seated next to their edges. `g.pose(..., weights=False)`
  hides the weight pills for a small decorative thumbnail (`True` brings them back). `g.settle(center, scale)`
  also rests every edge, ring and glow in the same move (`back_home()` uses it). A group `.animate` in the same
  `play()` as the graph's own member animations (light, mark, reset) puts the members back as they were.

**Token and routes**
- `Token(scale=1)`: the plane with a warm halo. `fly(scene, g, tok, [0, 1, 3], until=t, color=AMBER,
  on_edge=f)` flies the route, drawing a glowing trail; `on_edge(i, u, v)` returns extra animations per leg.
- `reject(g, u, v, label)` returns `(anims, marks)`: coral fire, a crossed disc (sized with the graph, put where
  it covers no weight or node), a wiggle. Fade `marks` later.

**Cards**
- `title_block(line1, line2, kicker)` (`.line1 .line2 .glow`): the intro hero.
- `lower_third("EXAMPLE 1", "k = 1")`, `chapter_tag(n)`: the scene adds the tag itself.
- `self.chapter_card()` and `self.question(id, n)` (above). `think_ring(center)` returns `(ring, tracker)` for a
  custom countdown.

**Input**
- `InputDecoder("flights", FLIGHTS, fields=("from", "to", "price"), per_row=1, size=32, more=[("k = 1", CORAL)])`.
  The `more` lines are `size + 6` (`more_size=`), so lowercase "src = 0" still reads 26 px or more.
- `.write()` types it. `.send(scene, i, g, (u, v), run_time)`: entry i flashes, its weight flies to the
  edge, the edge grows, the cities ripple. `.show_more(i)` reveals an extra line (src, dst, k).

**State**
- `ArrayRow([0, INF, INF, INF], label="dist", header=["0", "1", "2", "3"])` with `.appear()`,
  `.set(i, v, AMBER)`, `.focus(i, CYAN)` (a ring and a nudge; the cell is never flooded with the colour, which
  left its value at 1.6:1), `.calm()`, `.clone_below("next")` and `.pull(src, i, MINT)` (src's value travels
  into cell i at full opacity: `dist = next`).
- `DPTable(rows, cols, init=INF)` with `.appear()` and `.set(r, c, v)`. `INF` shows as ∞.

**Approaches**
- `Ladder([(name, "O(n^(k+1))", "O(k)", cost 0..1), ...])`, then `.hide()`. Bars are coral (costly) to mint
  (cheap).
- `.show_heads()`, `.reveal(i)`, `.pick(i, "INTERVIEW PICK")`.

**Code**
- `CodePanel(src, language="cpp", size=30, max_width=None, min_size=30)`, then `.hide_lines()`. It never
  scales the code below `min_size` (it prints `CODE-TOO-WIDE` instead): wrap the listing to about 50 columns.
- `.reveal(i, j)`: lines type in, 0-based, inclusive. `.focus(i, j)`: highlight bar, the rest dims to 0.78
  (`DIM_OPACITY`), which keeps comments and line numbers at 4.5:1 or more. `.unfocus()`.
  `.find(line, "dist[u]")` returns glyphs to pulse.

**Callouts**
- `burst("700!", size=80)`: tilted comic starburst. `pop(scene, b, hold_until=t)` scales it in with a wobble.

**Look tokens**
- `BG PANEL PANEL_HI INK MUTED DIM EDGE AMBER CYAN CORAL VIOLET MINT COMIC ACCENT`, `SIZE`, `Z`, `px`, `fs`.
- `ink(AMBER)`: the colour for text or a thin stroke in a hue; `on_fill(AMBER)`: a label on a filled shape.
  See **Themes** below.

### Themes

With no theme file the film keeps the original palette above, pixel for pixel. A registry theme
(`references/themes.md`) is one file, `source/kit/theme.py`, which `style.py` imports when it exists:

```bash
python3 $S/vstate.py set theme=catppuccin-latte
python3 $S/theme.py emit catppuccin-latte --format py --out source/kit/theme.py
rm source/kit/theme.py                     # back to the original palette (and vstate.py set theme=original)
```

The file sits inside `kit/`, so changing the theme changes every segment's key and the next render redoes them.
Re-render the stills and run `legibility.py` after a switch. `style.py` maps the theme tokens onto the kit's roles:

| Kit role | Theme token |
|---|---|
| `BG`, `BG2` (backdrop gradient), `BG_DEEP` (card shade, captions, tag and badge pills) | `bg`, `bg2`, `deep` |
| `PANEL`, `PANEL_HI` (cells, panels, code; question card, node discs, active code line) | `panel`, `panel2` |
| `INK`, `MUTED` | `text`, `muted` |
| `DIM` (grid, strokes, pips to come), `EDGE` (edges at rest) | `line2`; `line2` moved toward `muted` to 3:1 on `bg` |
| `AMBER`, `CYAN`, `CORAL`, `MINT`, `VIOLET`, `COMIC`, `ACCENT` (chapter numbers, card rule, pips) | `warm`, `cool`, `bad`, `good`, `violet`, `gold`, `accent` |
| `ink(hue)`: text and thin strokes (weights, tags, lit edges, rings, ripples, trails, cell outlines) | `<hue>Ink` |
| `on_fill(hue)`: Q badge, INTERVIEW PICK pill | `on<Hue>` |
| `SHADOW`, `COMIC_INK` (burst outline) | `shadow` |
| code: comments, punctuation, line numbers, idle lines / keywords / operators / functions | `muted` / `violetInk` / `badInk` / `accentInk` |
| backdrop key light per chapter / rim light | `lights[chapter % 6]` / `cool` |

- Hues are fills. `T`, `H`, `Mono` and `Rich` turn a hue into its ink by themselves, so `T("START", 32, CYAN)`
  is right in every theme. Write `ink(CYAN)` yourself for thin strokes and for `set_color` on text, and
  `on_fill(CYAN)` for a label on a CYAN shape.
- Light themes (`LIGHT`): the backdrop's vignette fades toward `deep` (never black) and its grain only darkens;
  `glow()` becomes a narrow tint with a soft `shadow` under it, and glows behind text are left out; halos are
  tighter; drop shadows use `shadow` at half strength.
- Code in a theme: idle lines turn `muted` instead of dimming by opacity (a dimmed ink would fall under 4.5:1),
  and the active line sits on `panel2` with the `accent` bar.
- Each chapter's backdrop takes its key light from `lights`. The previous chapter's backdrop stays on as an
  image until the chapter card's shade covers the stage (`play_chapter_card` removes it), so the cut shows no
  jump. A chapter scene without a chapter card keeps the previous light.

## 5. Recipes (all from `assets/template/scenes.py`)

**Decode an input.** The graph starts hidden. The decoder writes itself under the chapter card, then each
entry flies into its edge before the next line:

```python
g = flight_map(hidden=True); dec = InputDecoder("flights", FLIGHTS, more=[("src = 0", CYAN), ("k = 1", CORAL)])
self.chapter_card(also=lambda: [*g.appear_nodes(), *dec.write()])
per = self.split(L["p2"].voiceAt - 0.1, len(FLIGHTS))      # n plays in whole frames, all done by p2
for i, (u, v, w) in enumerate(FLIGHTS):
    dec.send(self, i, g, (u, v), run_time=per)
self.until(L["p2"].said("start")); self.play(*g.mark(0, CYAN, "START"), *dec.show_more(0), run_time=0.5)
```

**Trace a route with a running total.**

```python
def tick(i, u, v):                                   # on_edge: extra animations during leg i
    new = Mono(str(sums[i]), 40, AMBER, weight="BOLD"); out = roll(cost[1], new); cost.submobjects[1] = new
    return out
fly(self, g, Token(), [0, 1, 3], until=L["p4"].said("seven hundred", 0.15), on_edge=tick)
```

**Reject an illegal route.**

```python
fly(self, g, tok, [0, 1, 2, 3], until=L["b4"].at(0.6), color=CORAL)
bad, marks = reject(g, 2, 3, "2 stops > k")
self.play(*bad, run_time=0.5)
self.until(L["b4"].end - 0.4); self.play(FadeOut(marks), FadeOut(tok), *g.reset(), run_time=0.35)
```

**Think countdown.** `self.question("q1", 1)`. Put whatever the viewer should reason about on screen
*before* it: the shade darkens only the backdrop and grid (it sits under the subject), so the subject stays at
full contrast during the think pause. Keep the subject clear of the card (top 3 units of the stage).

**DP row update (read old, write new).**

```python
self.play(g.fire(u, v, AMBER), *dist.focus(u, CYAN), *code.focus(10, 11), run_time=0.3)
self.play(*nxt.set(v, new[v], AMBER), *g.light(u, v, AMBER), run_time=0.3)
self.play(*code.focus(13), *[a for i in changed for a in dist.pull(nxt, i, MINT)], run_time=0.45)   # dist = next
```

**Code walkthrough synced to the voice.** Reveal the panel under the chapter card
(`also=lambda: [*code.reveal(0, 16, lag=0.02)]`), then move the focus with the words:
`self.until(L["c1"].said("round zero")); self.play(*code.focus(5, 7), ...)`. Keep the code at 30 px or more
(the quality bar's 30-36): wrap it to about 50 columns with 2-space indents, and a 17-line function fills the
left 55% of the frame, with the state row and a small graph on the right.

**Camera.**
- Push in on the payoff: `self.play(self.push(g, zoom=1.16, offset=(1, 0.25)), run_time=0.6)`.
- Return with `self.home()`. Holds of 1 s or more breathe by themselves (`drift`; `drift = 0` on the class
  turns it off).
- HUD items (`self.hud(mob)`) stay put while the camera moves. Animate them while the camera is still.

**Split a long chapter.** For a long film, `class Approaches1(FilmScene): span = ("x1", "x4")` and
`class Approaches2(FilmScene): span = ("x5", "x9")`. Short segments render in parallel and resume finer. Only
the segment holding a chapter's first line plays its card.

**Continuity.** End every segment in the HOME pose (`back_home(self, g, extra=[...])`) and start the next one
from it. The cut is then hidden under the chapter card or lands on an identical frame.

## 6. Rendering

| Command | Does |
|---|---|
| `python3 $S/render_manim.py --project . --draft --workers 2` | 854x480 15 fps → `build/draft.mp4` (2-5 min for the demo's earlier 62 s cut) |
| `... --draft --stills lines --from-draft` | the same, plus a still for every line via `stills.py` → `stills/` + `stills/sheet.png` |
| `... --stills chapters` / `--stills 12.5,40` | full-size stills via `manim -s` with `FILM_STOP_AT=t` (~8 s each quiet, up to 50 s under load) |
| `... --bench --workers 2` | renders the shortest segment at 1080p, prints fps per worker and the film ETA |
| `... --workers 4 --max-minutes 100` | the film → `build/silent.mp4`; resumable; exit 3 = budget reached, run again |
| `... --only Problem` / `--force` | re-render named segments / everything |

**What the full render does**
- One process per FilmScene: `python -m manim render -r 1920,1080 --fps 30 --disable_caching --media_dir
  build/segments/media/<Scene> scenes.py <Scene>`. Logs go to `build/segments/logs/<Scene>.log`.
- Checks each segment's frame count. A segment off by a frame is re-timed with ffmpeg.
- Records it in `build/segments/manifest.json` (`id, from, to, frames, key, done, secs`).
- Joins the segments with the concat demuxer and verifies `round(TOTAL*fps)` frames.

**What triggers a re-render.** A segment's key hashes the kit, timing.json, the module-level code of
scenes.py and the class body. Editing one scene re-renders that scene only; editing the kit re-renders all.

**Speed measured here** (4 CPUs)
- 1080p30 on a quiet machine: 10.7-13.7 frames/s per worker; the LC 70 test (3.95 min) rendered in 5.0 min
  with 2 workers. Under heavy load (other renders running): 1.0-3.4 frames/s per worker; the demo's earlier 62 s cut took
  11.9 min with 2 workers at load ~60.
- Draft at 480p15: 1.2-11 frames/s per worker, 1.6-4.6 min for the demo.
- Full-size stills: about 8 s each quiet, up to 50 s under load.
- Bench first; the ETA it prints is from the measured speed.
- Moving-camera shots cost the most, because every mobject redraws on every frame.

Stills from `--stills` stop the scene at the given time, cutting the play in progress at that exact moment
(a half-faded part stays half-faded, a morph stays mid-way). They are true 1080p frames, so use them to judge
text and code. The draft is for motion and overruns. Then run `python3 $S/legibility.py --project .` and open
the marked copies in `stills/legibility/`: the visuals gate fails while any text is under 26 px or under 4.5:1.
Text still fading in at a still's moment fails too: land it earlier (before its word), do not hide it.

## 7. Gotchas (symptom → fix)

- **Z-order jump** when parts animate: `AnimationGroup` (and `LaggedStart`, which is one) over sub-mobjects
  re-adds them on top. Unpack lists into `play()`; give layered parts explicit `set_z_index`.
- **A reset or highlight is undone when the subject moves in the same play**: a group `.animate` restores its
  members' state at the end. Use `g.settle(center, scale)`, or `generate_target()` + edit the target +
  `MoveToTarget` for your own subject.
- **New values in a scaled `ArrayRow` come out full size** (fixed: `ArrayRow.set()` scales them by `row.k()`;
  do the same in your own components: build at the base size, then `.scale(row.k())`).
- **Hidden shapes come back as solid (often red) discs**: `set_opacity(1)` also fills zero-opacity fills. Use
  `conceal`/`unconceal` (the kit's `hide()`/`appear()`).
- **A faded glow reappears later**: FadeOut restores its mobject after removing it. Remove the part from its
  group first, then FadeOut (see `WGraph.reset`).
- **An updater's swapped children never draw**: Manim renders the family captured at `play()` start. Keep the
  children and park the hidden ones (captions in film.py).
- **An updater stops during `wait()`**: waits without time-based updaters are frozen frames. Give the updater
  a `dt` argument.
- **A whole group turns one colour**: you assigned `.color` (a VMobject property). Use another attribute
  name; avoid `.name` too.
- **ValueError or merged glyphs in code**: a ligature font (JetBrains Mono, Fira Code). Use `Mono()`/
  `CodePanel` (DejaVu Sans Mono).
- **Spikes around glowing text**: miter joins on wide strokes. Use `joint_type = LineJointType.ROUND` (set in
  `glow()`, `burst()`).
- **`Tex`/`MathTex` crash**: there is no LaTeX. Use `Rich`/`Formula`.
- **Segment one frame long or short / 60 fps stills**: Manim defaults to 60 fps and `run_time` maps to
  `len(arange(0, rt, 1/fps))` frames. Use `until`/`play_until` and the render script (it passes `--fps`).
- **Random crashes in parallel renders**: a shared text cache. Use one `--media_dir` per process (the render
  script does).
- **`FILM-OVERRUN`**: the scene is late for a line, and everything after it shifts (the segment end is
  trimmed). Shorten motions or move set-up under the chapter card (`also=`). Fix all of them before the full
  render.
- **The chapter card plays in the chapter's first second** (voice.py's `chapter_lead`): it holds until 0.6 s
  before the first line's voice, collapses over 0.45 s, and the stage fades back in during the second half of
  the collapse, so the subject is on screen 0.15 s before the voice (qa.py `chapter-entry` warns when it is
  not). `chapter_card()` returns then: continue right after it (a `beat()` of the first line just waits the
  last 0.15 s), and put whatever the first words point at into `also=` so it is there when they are spoken.
- **Card over content at a chapter change** (the starter film, every card 02-05): the card's text faded in
  while the graph was still at about 70%, so edges and node 3 crossed the title, and a 0.84 shade left the
  graph as a 15% ghost behind the card. `play_chapter_card` now runs stage out, card in, card out, with an
  opaque shade that lifts only in the second half of the card's collapse (its title and glow are gone by then); anything at the callout, HUD or caption layer still draws over it.
- **Weights and node numbers turn tiny when the graph is made small**: a plain `g.scale()` scales the labels
  too (a 0.4 thumbnail had 16 px weights). Use `g.place`/`g.pose`/`g.settle`, which keep them at 32 px.
- **Double image / ghost number / scrambled title at a chapter change** (the LC 70 test, 164-168 s): a glow
  built at the end position while its text slid in, a glow faded in place while its text flew away, and a
  ReplacementTransform between two different strings. Move a glow WITH its text (`UpdateFromAlphaFunc`),
  cross-fade different strings instead of morphing them, and keep the tag's pill under the flying parts
  (`play_chapter_card` does all three).

## 8. Laptop differences

- **System libraries.**
  - macOS: `brew install pango cairo pkg-config ffmpeg`, then the same venv + pip line.
  - Windows: use WSL2 with the Ubuntu commands.
- **Fonts.** Install Inter (`brew install --cask font-inter`) or drop the Inter .otf files into `source/fonts/`.
- **LaTeX.** With a TeX install (MacTeX or `texlive-latex-extra`), `Formula()` switches to MathTex by
  itself, and `HAS_LATEX` in style.py is True. Nothing else changes.
- **Speed.** An 8-10 core laptop renders 1080p30 about 2x faster per worker. Use `--workers` equal to the
  number of performance cores.
- **Preview.** `cd source && ../.venv/bin/manim render -ql -p scenes.py Problem` previews one chapter (480p
  with player).
- **Voice.** `edge_voice_swap.py` re-voices on a laptop where edge-tts is reachable. Re-run `voice.py --emit
  source/timing.json` and the render, because the scenes follow the new timing by themselves.
