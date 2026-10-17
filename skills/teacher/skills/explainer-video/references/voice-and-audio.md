# Voice and audio

## Contents
- The rule this file exists for
- The engine ladder
- Kokoro voices
- Edge voices for the person's laptop
- Music and effects
- The mix
- When something really is blocked

## The rule this file exists for

On 2026-10-06 a person asked for an explainer video and was told a natural voice could not be baked into the
file. That was false: Kokoro runs offline in the same sandbox. The person had to push back before getting what
was possible all along, and read the gap as being treated as someone who did not deserve full effort. So:

- Every video ships with a natural voice baked into the MP4. Never a silent video with a "voice toggle", never
  browser `speechSynthesis` (it sounds robotic), never "add your own voice-over".
- Never tell the person a capability is impossible until you have tried the alternatives below and recorded
  them with `vstate.py limit ... --tried ... --tried ...`. The gate makes you name at least two attempts.
- When something is limited by the environment (a blocked host, no GPU), say exactly that, in one sentence, and
  say what you did instead.

## The engine ladder

`voice.py --engine auto` (the default) tries these in order and records what failed in `timing.json.fallbacks`.
An explicit `--voice` is tried first with the engine it belongs to (`en-IN-NeerjaNeural` is edge-tts, `af_heart`
Kokoro, `en_US-lessac-medium` Piper). One engine must voice every line: the voice gate reads each clip's own record,
and a robotic clip left from an `--allow-robotic` run is voiced again, not reused, by a natural run.

| Engine | Where it works | Notes |
|---|---|---|
| **kokoro** (Kokoro-82M, `kokoro-onnx`) | Everywhere, offline, CPU | Downloads `kokoro-v1.0.onnx` (325 MB) and `voices-v1.0.bin` from github.com/thewh1teagle/kokoro-onnx releases (model-files-v1.0) to `~/.cache/kokoro` once. About 0.5 s of compute per spoken second on 4 cores. |
| **edge-tts** (Microsoft neural voices) | Laptops and most networks | Blocked in the cloud sandbox (speech.platform.bing.com). Best voice catalogue, including Indian English. |
| **piper** (`piper-tts`) | Offline once its model is downloaded | Voice model from huggingface.co/rhasspy/piper-voices at tag v1.0.0, checked against the MD5 rhasspy publishes (blocked in Claude Code cloud as of 2026-10-07). Slightly flatter than Kokoro. |
| espeak-ng | Last resort only | Robotic. `voice.py` refuses it without `--allow-robotic`, and the voice gate refuses it unless a `vstate.py limit --kind voice` names two things tried and `vstate.py set allow_robotic=yes` is recorded. |

If `pip install` fails, check the proxy/network message, retry, try `--user`, try a different index only if the
person's environment allows it. If the model download fails, try `curl -L` (voice.py does), then a mirror the
person can reach, copied into `KOKORO_DIR`. voice.py checks both files against SHA-256 values pinned in the script
and refuses any other build; to use one anyway (your own mirror, a newer release), set `KOKORO_ALLOW_UNPINNED=1`,
and say so in NOTES.md. Each attempt goes into `--tried`.

## Kokoro voices

Set in `script.json` `meta.voice` / `meta.speed` (or `--voice/--speed`). The examples use 0.95: at 1.0 to 1.05
with sentences run together, the LC 787 narration measured 4.2 syllables a second (about 189 words a minute on
its short numeric words), faster than a teacher talks. `voice.py` now voices each sentence separately and
joins them with `meta.sentence_pause` (default 0.3 s, `--sentence-pause`); with speed 0.95 that measured 3.9
syllables a second. Judge pace in syllables a second (3.5 to 4.0 for teaching), not words a minute: digits and
one-syllable words inflate wpm.

| Voice | Character | Proven on |
|---|---|---|
| `af_heart` | Warm American female, the best all-rounder | LC 787 in Revideo, HyperFrames, hand-drawn, Three.js |
| `am_michael` | Calm American male | LC 787 in Manim |
| `af_bella`, `af_nicole`, `af_sarah` | Other American female | |
| `am_adam`, `am_eric`, `am_liam` | Other American male | |
| `bf_emma`, `bf_isabella`, `bm_george`, `bm_lewis` | British (lang en-gb chosen automatically) | |
| `hf_alpha`, `hf_beta`, `hm_omega`, `hm_psi` | Kokoro's Hindi voices | Run with `--lang hi` for Hindi narration; they also run on English text (lang en-us). Not yet judged by ear: render a 10 s sample and let the person choose before voicing a whole film. |

Other languages: `--lang es|fr-fr|it|pt-br|ja|cmn` with the matching voice prefix (e, f, i, p, j, z).

Pronunciation: Kokoro reads what you write. Spell symbols and numbers in `say` (script-format.md). If a word
comes out wrong, respell it phonetically in `say` only (`"Dijkstra"` reads fine; `"memoize"` may need
`"memo-ize"`). Re-voice a single line by editing its `say`; the cache re-synthesizes only changed lines.

## Edge voices for the person's laptop

Every delivery includes `edge_voice_swap.py`, `timeline.json` and `bed.m4a` (music + effects without voice), so
the person can re-voice the film with any Microsoft neural voice on a machine where edge-tts works:

```bash
pip install edge-tts
python3 edge_voice_swap.py en-IN-NeerjaNeural          # or en-IN-PrabhatNeural, en-US-AriaNeural, en-GB-SoniaNeural
python3 edge_voice_swap.py en-IN-PrabhatNeural film.mp4  # name the MP4 when the folder has several
```

It voices each line at its original start time, speeds a line up (at most 1.35x) only if it would overlap the
next, mixes it over the bed and writes a new MP4 named after the voice. Mention this in the final message.

## Music and effects

`music.py` synthesizes everything in numpy (no downloads, no licensing questions):

- Moods: `calm` (Cmaj7 to Am7 to Fmaj7 to G6 pad with soft keys and bass, 76 bpm), `piano` (felt piano in D, 72
  bpm), `pulse` (Am F C G pad with an arpeggio, more drive), `none`.
- The bed thins during think pauses and swells at chapter starts; a whoosh lands on every chapter change
  (`--no-whoosh` to drop); `--chime` adds a two-tone chime at every chapter change too.
- Per-line effects from `script.json` (`"sfx": [{"at": 0.4, "kind": "pop"}]`): whoosh, pop, chime, tick, click,
  thud, rise. Use them on visible events: a node appearing (pop), a counter ticking (tick), the answer landing
  (chime), a rejection (thud).

Numpy gotcha: smooth long envelopes with cumulative sums. `np.convolve` with a 0.5 s window over a 6-minute
48 kHz signal effectively hangs.

## The mix

`mix.py` normalizes the voice, ducks the music under it (about 60% while speaking), places the effects, and
muxes with the silent render:

- music -17 dB, effects -12 dB under the voice by default (`--music-db`, `--sfx-db`, `--duck`).
- `loudnorm I=-16:TP=-1.5:LRA=11`, AAC 192k, `yuv420p` (Remotion writes yuvj420p, which some players reject; mix
  re-encodes when needed), `+faststart`.
- Writes `audio/bed.m4a` for the voice swap.

`qa.py` then measures the result: -18 to -14 LUFS, peak at most -0.5 dBFS, and every line's voice found within
0.12 s of its planned time (cross-correlation against its clip).

## When something really is blocked

1. Try every rung of the ladder and every mirror you can reach.
2. Record it: `vstate.py limit "edge-tts blocked" --kind voice --tried "edge-tts: 403 from speech.platform.bing.com"
   --tried "kokoro worked: used instead"` (a limit can record what you did instead).
3. Tell the person in one sentence which limit came from the environment and what the film uses.
