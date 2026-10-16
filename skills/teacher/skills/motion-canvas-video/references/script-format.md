# script.json and the timing it produces

## Contents
- script.json schema
- Writing `cap` and `say`
- The timing model
- timing.json (what the scene code reads)
- Choreographing against the timing

## script.json schema

```json
{
 "meta": {
  "title": "Cheapest Flights Within K Stops",
  "subtitle": "LeetCode 787",
  "format": "dsa-5part",
  "chapters": ["Intro", "The problem", "Brute force", "Intuition", "Every approach", "C++ and dry run"],
  "voice": "af_heart", "speed": 0.95, "music": "calm",
  "fps": 30, "width": 1920, "height": 1080,
  "lead": 0.25, "pad": 0.35, "chapter_gap": 0.8, "chapter_lead": 1.0, "sentence_pause": 0.3
 },
 "lines": [
  {"id": "p3", "chapter": 1, "scene": "inputs",
   "cap": "So [0, 1, 100] means: fly from city 0 to city 1 for 100.",
   "say": "So zero, one, one hundred means: fly from city zero to city one, for one hundred."},
  {"id": "q1", "chapter": 3, "scene": "q1",
   "cap": "Question 1: the limit counts stops. Is there something simpler to count?",
   "say": "Question one. The limit counts stops. Is there something simpler to count?",
   "think": 2.5,
   "sfx": [{"at": 0.0, "kind": "pop"}]}
 ]
}
```

| Field | Meaning |
|---|---|
| `id` | Stable name for the beat; scene code keys animations to it. Up to 32 letters, digits, `_` and `-`, starting with a letter or digit. |
| `chapter` | Index into `meta.chapters`. DSA order: 0 Intro, 1 Problem, 2 Brute force, 3 Intuition, 4 Approaches, 5 Code + dry run. |
| `scene` | Groups consecutive lines that share one composition (optional; defaults to the chapter). |
| `cap` | What appears on screen (captions, labels). Symbols welcome: → ≤ ∞ [0, 1, 100] O(n^(k+1)). |
| `say` | What the voice speaks. Plain words only (the script gate rejects → ≤ ≥ ≠ ∞ ^ [ ] { } \| _ · …). |
| `say_ok` | `true` skips that symbol check for one line, when the engine reads the symbol correctly (say why in the brief). |
| `think` | Seconds of silence after the line so the viewer can try first. Use 2 to 3 s on every intuition question. |
| `min` | Minimum slot length when the picture needs more time than the words (a long route animation). |
| `lead`, `pad` | Per-line overrides of the silence before/after the voice (a line's own `lead` also wins over `chapter_lead`). |
| `sfx` | Optional effect cues relative to the line's voice start: whoosh, pop, chime, tick, click, thud, rise. `music.py` reads them from `script.json`. Any edit to `script.json`, sfx included, marks the voice phase stale (the gate hashes the script), so re-run `voice.py` after it (cached clips make that quick). |
| `meta.voice/speed` | Kokoro voice (af_heart, am_michael, bf_emma, am_adam...) and speed (1.0 to 1.1 reads well). |
| `meta.music` | calm, piano, pulse or none. |

## Writing `cap` and `say`

- One idea per line, 6 to 25 spoken words. A line is a beat: something on screen must change while it plays.
- `cap` can be shorter than `say`, never longer in meaning. Viewers read and listen at the same time; if they
  disagree the viewer trusts neither.
- Spell out what a voice reads badly: `[0,1,100]` -> "zero, one, one hundred"; `n − 1` -> "n minus one";
  `O(k·E)` -> "order k times E"; `dist[u]` -> "dist of u"; `→` -> "to" or a pause; `787` -> "seven eighty seven".
- Code identifiers that are words (`dist`, `next`, `src`) can stay; acronyms that should be spelled get spaces
  or a phonetic form ("B F S" or "breadth first search").
- Questions end with `?` in `cap` and carry `think`. The answer is the next line, never the same line.

## The timing model

`voice.py` voices every line, trims silence, and lays the film out from the real clip lengths:

```
slot(line) = max(lead + spoken + pad + think, min)        chapter change adds chapter_gap
lead       = max(lead, chapter_lead) on a chapter's first line (default 1.0 s: the card plays before the voice)
spoken     = the line's sentences, each trimmed, joined by sentence_pause (default 0.3 s) of silence
voiceAt    = start + lead                                 the moment the voice begins
end        = start + slot
total      = last end + outro_tail
```

The picture follows the voice. Never stretch or speed audio to fit an animation; lengthen the line's `min` or
change the words instead.

## timing.json (what the scene code reads)

```json
{
 "hash": "b814a8b622d2fb90", "engine": "kokoro", "voice": "af_heart", "speed": 1.0,
 "total": 62.231, "fps": 30, "width": 1920, "height": 1080, "title": "...",
 "chapters": [{"n": 1, "name": "The problem", "start": 3.63, "end": 18.03}],
 "scenes":   [{"id": "inputs", "chapter": 1, "start": 3.63, "end": 9.7, "lines": ["p1", "p2"]}],
 "lines":    [{"id": "p1", "chapter": 1, "scene": "inputs", "start": 3.63, "voiceAt": 3.88, "voiceDur": 2.71,
               "think": 0, "end": 6.99, "dur": 3.36, "cap": "...", "say": "..."}]
}
```

`--emit` writes the same object in the format your tool reads, stamped with the hash so the visuals gate can
tell the scenes are timed to the current voice:

| Extension | Content | Used by |
|---|---|---|
| `.json` | the object | Manim (`json.load`), Remotion/Revideo/Motion Canvas (`import timing from './timing.json'`) |
| `.js` | `window.TIMING = {...}` | plain HTML pages (GSAP, hand-drawn canvas, HyperFrames) |
| `.ts` / `.mjs` | `export const TIMING = {...}` | TypeScript projects, bundlers |
| `.py` | `TIMING = json.loads(...)` | Python tools |

## Choreographing against the timing

Key every animation to a line, not to a hard-coded second:

```js
const L = Object.fromEntries(TIMING.lines.map(l => [l.id, l]));
at(L.p8.voiceAt + 0.2)            // the route starts flying just after the voice begins the sentence
at(L.p8.voiceAt + L.p8.voiceDur)  // the result lands as the sentence ends
at(L.q1.voiceAt + L.q1.voiceDur)  // think timer runs for L.q1.think seconds from here
```

When a phrase inside a long line needs a cue, estimate it from the character position
(`voiceAt + voiceDur * say.indexOf(phrase) / say.length`); it lands within a few hundred milliseconds, which
reads as in sync. If it must be exact, split the line in two.
