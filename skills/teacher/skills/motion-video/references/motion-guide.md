# motion-video guide

How a clip is put together, the film.json format, every block, the data path, the editor, and how to add a block.
The three starters in `assets/examples/` are complete, rendered films: copy the closest one and change it.

## 1. The project

```
script.json            the lines: id, chapter, cap (shown), say (spoken), think   (or script.template.json + motion_fill.py)
timing.json            written by voice.py: when every line starts, speaks and ends
voice/narration.wav    the voice
source/
  film.json            THE CLIP: style, data, shots of blocks, cues on spoken phrases     <- you write this
  data/*.csv|json      datasets for charts and counters (data clips)
  footage/<clip>/      a screen recording as JPEG frames f00001.jpg ... (product demos; git-ignored)
  timing.js            voice.py --emit source/timing.js (window.TIMING, stamped with its hash)
  theme.js             window.THEME = null (the look in film.json) or a registry theme from theme.py
  index.html main.js   the page: loads fonts, film.json and data; window.READY / TOTAL / renderFrame(t)
  editor.html          every field editable, frame-size preview, Save film.json
  engine/              look.js (palettes, type scale) core.js (geometry, time refs, tweens, rich text)
                       data.js (datasets) stage.js (shots, layout, backdrop, captions, ink guard)
                       blocks-text.js blocks-data.js blocks-dsa.js (the 13 blocks)
                       blocks-screen.js (screen: recorded footage) screen-sync.js (loaded after main.js)
  styles.css           every block's look, in CSS variables set from the palette
  vendor/              GSAP 3.15 + plugins and the woff2 fonts, copied from npm by `npm run vendor`
```

The engine puts everything on one paused GSAP timeline, `M.tl`. `renderFrame(t)` seeks it and redraws the
backdrop, so any frame can be drawn on any worker in any order: that is what makes the render resumable and
parallel. Nothing reads the clock.

## 2. film.json

```json
{
  "style": { "look": "ink", "brand": "Kai Mori", "mark": "KM", "tag": "LC 787 · daily" },
  "data": { "speeds": "data/render-speed.csv" },
  "shots": [
    { "at": "h1", "blocks": [ { "type": "title", "title": "Cheapest flight, at most *one stop*" } ] },
    { "at": "g1", "split": [1.15, 1], "blocks": [
        { "type": "graph", "id": "map", "nodes": [...], "edges": [...] },
        { "type": "text", "text": "Fly from *0* to *3*" } ] },
    { "at": "q1", "split": [1.15, 1], "blocks": [
        { "type": "graph", "id": "map", "cues": [ { "do": "route", "at": "r1", "path": [0, 1, 2, 3], "tone": "bad" } ] },
        { "type": "question", "prompt": "...", "options": ["400", "700", "600", "No route"], "answer": 1, "trap": 0 } ] }
  ]
}
```

**style**: `look` `paper` (light, warm, the default) or `ink` (dark); `brand` (top left; `false` hides it),
`mark` (two letters in the badge), `tag` (top right), `captions: false` (no burned-in captions),
`karaoke: false` (captions without the spoken word lit).

**shots**: each starts when the voice reaches its line `at` (the first shot names the first line and starts at 0) and lasts until the
next shot. A shot holds one to three `blocks` (more is an error); `split` sets their shares (`[1.2, 1]`), `layout` forces `"row"`
or `"column"` (default: side by side on 16:9, stacked on 9:16, 1:1 and 4:5), `light` picks the backdrop light's
hue (`accent`, `warm`, `good`, `bad`, `cool`, `gold`, `violet`; default: the palette's lights in turn); any
other `layout` or `light` is an error. A shot
of one block can be written flat: `{ "at": "e1", "type": "end", "title": "..." }`.

**blocks**: `type`, the block's fields (section 5), optional `id`, `cues` and `weight`. A block whose `id`
appears in the next shot is **carried**: it glides to its new box and keeps everything already on it (routes
flown, badges, values). In the later shot write only `{ "type": "graph", "id": "map" }` plus any new `cues`; the
fields come from its first shot (it keeps its `type`; other fields set again there are ignored, with a warning).
A carried block must be in consecutive shots, and its box should keep the same share (`split`) in each, or it is
scaled down with all its text (the engine warns below 85%). `split` has one share above 0 per block.

**cues**: `{ "do": "<cue>", "at": "<time reference>", ...params }`. Each block's cues are in section 5. A cue
lands on a line of the shot that lists it (list a carried block's later cues in its later shot), and a block's
cues run in spoken order whatever their order in the list. A `tone` anywhere (a cue's, a delta's, a compare
side's) is one of accent, warm, good, bad, cool, gold, violet; any other value is an error, and leaving it out
gives the default.

## 3. Time references

| Reference | Means |
|---|---|
| `"q2"` | the moment the voice starts line q2 |
| `"q2:seven hundred"` | when the voice says that phrase in q2 (from its position in the `say` text) |
| `"q2@0.6"` | 60% of the way through q2's voice (0 to 1; later is `"q2.vEnd +0.5"` or `"q2.end"`) |
| `"q2.start"` `"q2.vEnd"` `"q2.end"` | the line's slot start, the end of its voice (`.think` too), the slot end |
| `"q2:phrase +0.3"` | any of them with an offset in seconds (a space before the sign) |

The phrase is matched in `say`, lower-cased: write the phrase as spoken ("seven hundred", not "700"). A cue
never fires before its block has landed, so a cue at the line start of the block's own shot waits for the
entrance; if that wait runs past the moment the block leaves (a busy graph in a short shot), the build stops:
give the shot more time or carry the block into the next shot. A cue that plays on (a `route`'s hops and chip, a
`count`, a `think` countdown) must also finish before the block leaves. Errors name the line, list the line ids, and quote the `say` text.

## 4. Frames, layout and safe areas

| Frame | Size | Content area (safe area minus brand row and captions) |
|---|---|---|
| 16:9 | 1920x1080 | 96 px from the sides, 80 top, 72 bottom; captions in a 150 px band |
| 9:16 | 1080x1920 | 72 left, **120 right, 150 top, 430 bottom** (the platform draws its buttons and title there); captions 190 px band |
| 1:1, 4:5 | 1080x1080, 1080x1350 | 72 px sides, 64 top, 60 bottom |

Sizes scale with `--u` (1 at 1080 on the frame's short side), so a block looks the same on every frame; the
margins above are at 1080 and scale too (a 2160x3840 Short keeps 860 px clear at the bottom);
`legibility.py` measures text on the short side too. Every text is at least 28 px; a block that must shrink
its text to fit stops at its floor and warns. The editor and `motion_check --aspect 9:16` preview a film at
another frame; the render size always comes from the script (re-voice after changing `meta.width/height`).

Block weights (how much of a shot a block takes when no `split` is given) are listed with each block: a graph
takes 1.5 to a text's 1 in a column, for example.

## 5. Blocks

A `bool` field takes `true` or `false` without quotes (`"false"` is an error, not off), as do `style.captions`
and `style.karaoke`.

Text fields take rich text: `*marked words*` (a highlighter stroke when the voice says them, or a little before
when they are said at the very end of the block's last shot, so the stroke is drawn before it leaves; no space just inside
the stars, so the stars in `data/*.csv` or `3 * 4` stay characters), `` `code` ``,
`x^2` and `n^(k+1)` (superscripts). A `value` field takes a number or a dataset reference (section 6). `rows`
takes inline rows or `{"from": "set", "x": "col", "y": "col", "sort": "desc", "limit": 6}`.

### title

| Field | Type | |
|---|---|---|
| `kicker` | text | small capitals above, e.g. "DAILY QUESTION · LC 787" |
| `title` (required) | text | the headline; *word* marks a highlight |
| `sub` | text | one line under it |
| `align` | enum: left, center | default left |

No cues. Default weight: row 1, column 0.9.

### text

| Field | Type | |
|---|---|---|
| `text` (required) | text | the statement; *word* marks a highlight |
| `kicker` | text |  |
| `chips` | list | small pills under it, e.g. ["O(k·E) time", "O(n) space"] |
| `font` | enum: serif, sans | default serif |
| `size` | enum: xl, l, m | default l |
| `align` | enum: left, center |  |

Cues: `chips` shows the chips (instead of right after the words); `mark` sweeps the highlighter over the *marked* words (instead of when the voice says the first one). Each needs something to show: chips, or marked words. Default weight: row 1, column 1.

### steps

| Field | Type | |
|---|---|---|
| `items` (required) | list | at least one step, each "Title", "Title \| a short note" (split at the first bar) or `{"title", "note"}` |
| `title` | text | a small heading above the steps |

Cues: `show` reveals the next step and makes it current, once the heading and rail are in (`"n": 3` picks one, counting from 1; a step that does not exist or is already shown is an error). Without `show` cues every step enters at the start, staggered. More than five steps in a wide box flow into two columns. Default weight: row 1.1, column 1.3.

### compare

| Field | Type | |
|---|---|---|
| `left` (required) | json | {"title": "Brute force", "body": "Try every route", "chip": "O(n^(k+1))", "tone": "bad"}; at least one of title, body or chip |
| `right` (required) | json | the same shape |
| `winner` | enum: left, right | gets a stamp on the "winner" cue |
| `stamp` | text | the winner stamp text, default "✓ BETTER" |

Cues: `right` brings in the right card (otherwise both enter together); `winner` stamps the winner (`"side": "left"` or `"right"`, else the block's `winner`) once its card is in, so after `right` when it stamps the right card; one `winner` per block. Default weight: row 1.2, column 1.2.

### end

| Field | Type | |
|---|---|---|
| `title` (required) | text | the last line, e.g. "Try it before tomorrow's answer" |
| `mark` | text | two letters in the badge (default: style.mark) |
| `handle` | text | e.g. "@kaimorihq" |
| `cta` | text | a pill, e.g. "Follow for a question a day" |

No cues. Default weight: row 1, column 1.

### stat

| Field | Type | |
|---|---|---|
| `value` (required) | value | a number, or "=set.column:max" from a dataset |
| `from` | number | count up from this, a number (default 0) |
| `format` | text | int, 0.0, pct, compact, x, money, money:₹, time (a negative value reads -$1,200 or -0:30) |
| `prefix` | text |  |
| `suffix` | text | e.g. " fps" |
| `label` | text | what the number is |
| `kicker` | text |  |
| `delta` | json | {"text": "+12% vs last week", "tone": "good"} |
| `spark` | json | a small trend line, 2 or more numbers: [3, 5, 4, 8] or {"from": "set", "x": "day", "y": "n"} |
| `align` | enum: left, center |  |

Cues: `count` counts up on that phrase, once the number is in (otherwise at entry; `"d": 1.3` seconds, 0.2 to 10, and the count must end before the block leaves); `delta` shows the delta chip (needs the `delta` field: a text, or `{"text": ..., "tone": ...}` with text in it). Default weight: row 1, column 1.

### bars

| Field | Type | |
|---|---|---|
| `rows` (required) | rows | [{"label": "GSAP", "value": 7}] or {"from": "set", "x": "kit", "y": "fps", "sort": "desc"}; values 0 or more (a `line` takes negatives); every label a short text or a number, not blank |
| `title` | text |  |
| `unit` | text | shown after the title, e.g. "frames/s" |
| `format` | text |  |
| `highlight` | text | a label (or "max"/"min") drawn in the accent; the rest go neutral |
| `orient` | enum: auto, h, v |  |
| `max` | number | the scale end, at least the largest value and target (default: the largest value) |
| `target` | json | {"value": 30, "label": "real time"}: a dashed line |

Cues: `highlight` lights one bar and greys the rest (`"label": "max"`, `"min"` or a row label, which must appear once in the rows); `target` draws the target line (needs the `target` field). Default weight: row 1.3, column 1.4.

### line

| Field | Type | |
|---|---|---|
| `rows` (required) | rows | [{"label": "Mon", "value": 3}] or {"from": "set", "x": "day", "y": "n"} |
| `title` | text |  |
| `unit` | text |  |
| `format` | text |  |
| `area` | bool | shade under the line (default true) |
| `min` | number | the scale's bottom, at or below every value (default: 0, or the lowest value if below 0) |
| `max` | number | the scale's top, above `min` and at or above every value (default: a round number over the highest value) |

Cues: `annotate` puts a dot, a stem and a note on one point (`"x": "Fri"`, a label that appears once, `"text": "peak: 6"`, `"tone": "good"`). Default weight: row 1.4, column 1.3.

### ring

| Field | Type | |
|---|---|---|
| `value` (required) | value | a number or "=set.col:agg", from 0 to the total |
| `total` | value | the whole, above 0 (default 100) |
| `label` | text |  |
| `format` | text | default pct of total |
| `tone` | enum: accent, warm, good, bad, cool, gold, violet |  |

No cues. Default weight: row 1, column 1.

### question

| Field | Type | |
|---|---|---|
| `prompt` (required) | text | the question; *word* marks a highlight |
| `options` (required) | list | 2 to 4 answers, each a text or a number |
| `answer` (required) | number | index of the right option, a whole number (0 = first) |
| `trap` | number | index of the tempting wrong option (marked ✗ on reveal); not the answer |
| `notes` | list | one short note per option, shown on reveal (e.g. "2 stops") |
| `letters` | bool | A B C D badges (default true) |

Cues: `pick` borders an option and badges it (`"n": 0`, `"note": "cheapest?"`): the tempting answer (picking the option already picked, with the same note, is an error: it would change nothing on screen; so is a pick after the `reveal`, which would recolour the result); `think` places the countdown, once per question (`"secs": 3`, above 0.4; without `secs` it runs from when the options are in to the end of the cue's line; with no `think` cue it runs in the first `think` pause of its shot that still has time once the options are in, and a shot whose pauses are all too short is an error); `reveal` marks the answer green and the trap red with their notes, once per question and not before the countdown has run out (a reveal during the countdown, or a `think` after the reveal, is an error). Default weight: row 1.2, column 1.25.

### graph

| Field | Type | |
|---|---|---|
| `nodes` (required) | json | [{"id": 0, "x": 0.1, "y": 0.5}, ...] x and y from 0 to 1 inside the block; "label" optional (drawn instead of the id); ids and labels are short texts or numbers; ids unique, no two at one point |
| `edges` (required) | json | [[0, 1, 100], ...] from, to, weight (or {"from", "to", "w"}); a weight is optional, a number when given; one edge per pair (per direction when directed) |
| `directed` | bool | arrowheads (default true) |
| `src` | text | node id flagged FROM (one of the nodes) |
| `dst` | text | node id flagged TO (one of the nodes) |

Cues: `route` flies a token along a path and colours it (`"path": [0, 1, 3]`, `"tone": "good"`, `"hop": 0.5` seconds per edge, 0.25 to 1.2; the whole route and its chip must land before the block leaves, `"note": "✓"`, `"chip": false` to skip the "0 → 1 → 3 = 700" chip under the graph); `focus` rings nodes for `"hold"` seconds (default 2, at least 0.4; the hold and its fade must end before the block leaves), once the graph has drawn (`"nodes": [1, 2]`, at least one; `"tone": "bad"`); `clear` returns every edge to neutral (after a `route`). Default weight: row 1.3, column 1.5.

### code

| Field | Type | |
|---|---|---|
| `code` (required) | code | the code, as one string with \n or a list of lines |
| `title` | text | the file name in the header, e.g. "solution.cpp" |

The code needs at least one line with something on it. Cues: `focus` moves the highlight bar to new lines (`"lines": [5, 7]` for a range, or `"line": 4`; whole line numbers of the code, from 1). Default weight: row 1.4, column 1.5.

### array

| Field | Type | |
|---|---|---|
| `values` (required) | list | the cells, at least one, each a number or a short text (`""` for an empty cell), e.g. [2, 7, 11, 15] |
| `name` | text | shown before the cells, e.g. "nums" |
| `index` | bool | index numbers under the cells (default true) |

Cues: `point` places or moves a named pointer to a new cell (`"name": "i"`, a short text, default "i"; `"index": 0`, `"tone": "warm"`); `range` tints cells `from`..`to` (indexes from 0, `from` not after `to`; it must change some cell's colour); `set` writes a value into a cell with a pop (`"index": 3`, `"value": 700`, both required); `clear` un-tints every cell (after a `range`). Default weight: row 1, column 0.9.


### screen

Real screen recordings of a product, for demos: the footage plays inside a plain rounded screen, a camera
pushes in and pulls back over it, and a pen circles, underlines and writes notes on it. Extract each recording
to JPEG frames first, one folder per clip under `source/footage/`:

```bash
mkdir -p source/footage/review && ffmpeg -i review.mp4 -q:v 2 source/footage/review/f%05d.jpg
ls source/footage/review | wc -l      # the clip's "frames"
```

The frames must be real files inside `source/`: the page server refuses a symlink that points out of it, and
the screen then shows an empty panel.

| Field | Type | |
|---|---|---|
| `clips` (required) | json | every clip the block can show: `{"review": {"dir": "footage/review", "fps": 30, "frames": 1990}}` (a folder inside `source/`) |
| `clip` (required) | text | the clip on screen first |
| `from` | number | its second on screen first (default 0) |
| `view` | json | `[x, y, w]`: the centre and width framed first, in recording px (default the whole recording) |
| `size` | json | `[w, h]` of the recording in px (default `[1920, 1080]`) |

Cues: `play` plays the footage from `from` to `to` (seconds of the clip; `"clip"` switches clips with a 0.3 s
crossfade) until `until` or at `speed` (default 1), and two plays may not overlap; `view` moves the camera to
`"box": [x, y, w]` over `d` seconds (0.2 to 4, default 0.9; `w` at least a fifth of the recording, since a closer
push blurs it); `circle` and `underline` draw a pen stroke around or under `"box": [x, y, w, h]` (`tone`, default
`bad`); `note` writes `text` on a paper slip centred on `"near": [x, y]` that keeps its size as the camera moves
(`tone`, default `accent`; `tilt` in degrees). Marks stay until the shot ends, or until `out` (a time
reference). All boxes are in recording px, so they stay on the footage as the camera moves. Default weight:
row 2.3, column 1.6.

The recording's own interface text is often small. `legibility.py` and qa's moving-text check report it apart
from the film's own text: `screen-sync.js` exposes `window.FOOTAGE()` (where the footage and the notes are on the
frame), `capture.mjs --stills` writes it beside each still, and before qa run
`node $S/capture.mjs --page source/index.html --footage-map footage-map.json` in the project folder. Notes and
everything else the film draws are still held to 26 px and 4.5:1.

## 6. Data

```json
"data": { "speeds": "data/render-speed.csv", "facts": "data/facts.csv", "week": [ {"day": "Mon", "solved": 2} ] }
```

A dataset is a CSV with a header row (quoted fields and commas inside quotes are fine; numbers become
numbers), a JSON array of rows, or rows written inline. Paths are relative to `source/` (no URLs, no `..`, and
not through a link to a file outside it). A chart row or a `stat` whose value is blank, `null` or `true`/`false`
is an error, not a zero; `motion_fill.py` leaves those out of sums too.

| Reference | Value |
|---|---|
| `"=speeds.fps:max"` | the column's max (also `sum avg min first last`, over its numbers; `count` counts rows with any value, so `=kits.name:count` works; default `last`) |
| `"=facts.value[fact=gates]"` | the column in the first row where `fact` is `gates` |

Charts take `rows`: `{"from": "speeds", "x": "kit", "y": "fps", "sort": "desc", "limit": 8}` (`sort` is `asc` or `desc`,
`limit` a whole number above 0).

**The narration follows the data.** Write `script.template.json` with the same references in double braces
and generate `script.json` from it:

```json
{"id": "d4", "cap": "Fastest: Motion Canvas, about {{speeds.fps:max}} frames a second.",
             "say": "The fastest is Motion Canvas, at about {{speeds.fps:max}} frames a second."}
```

```bash
python3 $S/motion_fill.py --project .          # cap gets "10", say gets "ten"; "|0.0", "|int", "|pct" format it
python3 $S/motion_fill.py --project . --check  # exit 1 when script.json is stale against the template or the data
python3 $S/voice.py --project . --emit source/timing.js   # re-speaks only the changed lines
```

In `say` a number is spelled out ("ten thousand eight hundred", "zero point six", "seventy two percent");
`|digits` keeps digits. A sentence that now starts with a number gets its capital back.

## 7. Look, themes and contrast

`engine/look.js` is the one place colours and sizes are decided. `paper` and `ink` carry the same keys as a
registry theme (surfaces `bg bg2 deep panel panel2 line line2`, text `text muted dim`, fills `accent warm good
bad cool gold violet`, inks `accentInk ...`, on-fills `onAccent ...`, `lights`, `shadow`), so
`theme.py emit <id> --format global --out source/theme.js` swaps in any of the 30 themes unchanged.

The backdrop is one half-resolution canvas: a gradient, a soft light per shot (cross-faded over a second at
each shot change), a vignette toward `deep`, and still grain; the content area breathes very slowly. Light
darkens a light ground and brightens a dark one, so at build the engine draws the backdrop for every shot,
finds the worst ground under the content, and pushes any ink under 4.6:1 there toward black or white until it
holds. `motion_check` lists each change (`note accentInk #AA4629 -> #923c24`). Text on cards keeps the
palette's own colours.

## 8. The editor

`source/editor.html` (served from the project folder, so the narration plays) shows the clip with a scrubber
and a panel of every shot and block: each field is an input typed from the block's definition (text, number,
yes/no, a list, JSON for nodes and rows), plus the shot's line, split and layout, and the style. Edits rebuild
the clip within a quarter second; build errors and warnings show at the top of the panel; Undo steps back.
A film.json that fails to build still opens, with its error on top, so it can be fixed here.
The frame buttons preview 16:9, 9:16, 1:1 and 4:5. "Save film.json" downloads the edited file and "Copy JSON"
copies it: put it in `source/film.json`, then lint, re-shoot the stills and re-render. A carried block shows
only its cues (its fields are edited in the shot where it first appears).

## 9. Recipes

**A question Short (9:16, ~50 s)**: hook title (1 line) → the subject carried for two lines while a text block
beside it changes (what the input means, the rule) → the subject + a `question` with `think: 3` on the asking
line → `pick` the tempting option and fly its route in `bad` on the next line, `focus` what makes it wrong, fly
the right route in `good`, `reveal` on "the answer is" → a `text` + `array` (or `code`) shot for why → `end`.
`assets/examples/question-short/`.

**A data clip (16:9, ~50 s)**: `title` + `stat` (count of the dataset) → `text` with chips → `bars` carried
for three lines with `highlight` on the spoken names → a big `stat` → `stat` + `steps` (two columns) → two
`stat`s → `text` → `end`. Every number from `data/`, the narration from `script.template.json`.
`assets/examples/data-clip/`.

**Before and after**: `compare` with `right` on the second option's name and `winner` on the verdict.

**A code walkthrough**: one `code` block, `focus` cues on the phrases that name each line ("copy the row",
"relax every flight"); keep lines under about 60 characters on 16:9 and 40 on 9:16.

**A product demo**: record the app (Playwright `recordVideo`, or the OS screen recorder) in short clips, one per
feature, then one `screen` block carried through most shots: `play` on each line's phrase, `view` to push in on
what the line names, `circle` or `note` on the thing to notice, a `text` beside it for the claim. Title and `end`
around it. Keep the film's own words outside the recording or in notes.

**A weekly metric**: `line` carried from a full-width shot into a `line` + `ring` shot only with the same
`split` in both (`assets/examples/gallery/`).

## 10. Adding a block

When the library lacks a shape (a tree, a grid, a timeline), add a block in a new file, e.g.
`source/engine/blocks-tree.js`, loaded with a `<script>` tag after `engine/blocks-dsa.js`:

```js
(function () {
  const M = window.M;
  if (!M || !M.tl) return;
  M.block('tree', {
    fields: { nodes: { type: 'json', required: true, help: '[{"id": 1, "parent": null}, ...]' } },
    cues: ['visit'],
    weight: { row: 1.3, column: 1.4 },
    build(c) {                          // c: {el, box: {w, h}, props, u, P, shot, leaves, cues, time(), value(), rows(), spoken()}
      const { el, box, props: p, u, P } = c;
      // build DOM/SVG inside el, sized from box; every text >= LOOK.TYPE.min * u
      let landed = 0;
      return {
        enter(t0) { /* M.fromTo(..., { duration: 0.6 }, t0) */ landed = t0 + 0.6; return landed; },  // when it has landed
        cues: { visit: (cue, t1) => { const t = Math.max(t1, landed); /* M.to(..., { duration: 0.4 }, t) */ return { at: t, end: t + 0.4 }; } },
      };
    },
  });
})();
```

`enter()` returns when the entrance has landed, and each cue returns `{ at, end }`: when it really starts and when
what it shows has landed (add `off` when something plays on after that, like a halo that fades later). The stage
refuses an entrance or cue still playing when the block leaves (`c.leaves`, in seconds: time anything that waits
for the voice to finish by then), and `motion_check` takes the cue's still at `end`.
Use `M.to`, `M.fromTo`, `M.set` and `M.init` (never raw `gsap.to`): they record each element and property, so
`motion_check` finds overlapping tweens. Give hidden things `display: none` until they show if they would
otherwise take layout room. Put the styles in `styles.css` under `.blk-tree`. Add it to the editor for free:
the panel is generated from `fields`. If it is good, add it to this skill (and to the gallery) rather than
keeping it in one film.

## 11. When something is wrong

| Symptom | Cause and fix |
|---|---|
| `the phrase "..." is not in its say text` | the phrase must be in `say` as spoken; re-voice after editing `say` |
| `block id "x" reappears after a gap` | a carried block must be in consecutive shots; give the later one a new id |
| `"at": "..." is outside its shot` | move the cue to the shot whose lines it falls on (carry the block there) |
| `waits for the block to finish entering ... but the block leaves` | the block is still entering when its shot ends; give the shot more time or carry the block into the next shot |
| `takes until ... to enter, but it leaves` | the block's entrance (a line chart takes about 2.3 s) outlasts its shot; give the shot more time or carry the block into the next shot |
| `plays until ... but the block leaves` | a cue (a route, count, countdown, focus, card, stamp, highlight or chip row) runs past the block's exit; cue it on an earlier line, make it shorter (`hop`, `d`, `secs`, `hold`), or carry the block into the next shot |
| `"x" is carried into a box 56% of its first one` | same `split` share in every shot it is in |
| `does not fit its box even at 28 px` | shorten the text, or give the block more of the shot (`split`) |
| `outside the safe area` on 9:16 | content stays out of the bottom 430 px and right 120 px (at 1080 wide); shorten lines |
| `overlapping tweens on ...` | two cues change the same thing at once; move one later |
| `nothing on screen changes` on a long line | add a cue on that line, or start a shot there |
| text fails contrast only in a cue still | the still caught a fade; motion_check's cue times wait for motion to settle |
| page shows "film.json could not be read" | open it through `python3 -m http.server`, not `file://` |
