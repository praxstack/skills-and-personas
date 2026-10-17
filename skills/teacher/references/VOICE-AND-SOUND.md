# Voice and sound

What a lesson sounds like, why, and how each choice was checked. Decided in
October 2026; recheck the voice rankings when a new open model makes noise.

## The rule

Never a robotic voice. The browser's `speechSynthesis` is out everywhere,
including film tabs: if there's no natural voice, there's no voice, and the
captions carry the words. Every narrated video is voiced offline by a neural
model, and the pen sounds are real recordings.

## Voice: Kokoro by default, Chatterbox on a GPU

`narrate.py --engine auto` (the default) picks the engine for the machine.

| Engine | Licence | Human preference | Speed here (CPU) | Use |
| --- | --- | --- | --- | --- |
| Kokoro-82M (`af_heart`, speed 0.95) | Apache 2.0 | about 1,060 Elo on public TTS arenas, the top small open model | about real time (8.7 s for 10.4 s of speech) | default everywhere |
| Chatterbox (Resemble AI, 0.5B) | MIT | about 1,020 Elo on Speech Arena; beat ElevenLabs 65% to 25% in its maker's blind test; has an emotion dial | 285 s for 6.7 s of speech (about 40 times slower than real time) | picked automatically when it's installed and a GPU is present |
| Step Audio EditX | Apache 2.0 | about 1,100 Elo | needs a large GPU | worth trying for a studio render |
| F5-TTS, XTTS v2, Fish Speech | weights not for commercial use | strong | | not used |
| Breeze TTS 2 | not for commercial use | top of one board | | not used |
| edge-tts | online Microsoft voices | good | network | fallback ladder in `explainer-video` |
| Piper | MIT | fair | very fast | last resort offline |

Why Kokoro wins by default: it ranks above Chatterbox with human listeners,
it's permissively licensed, it runs faster than real time on any laptop CPU,
and its model files are pinned by SHA-256. Chatterbox is more expressive and
the better choice when a GPU makes it practical, so `auto` upgrades to it
there.

How it's checked: `visual-qa/scripts/check_speech.py` listens to each video
with Whisper and checks that the caption words are actually heard near
their cue. The first segment tree videos scored 99%. Nobody on this project
has listened to the voices yet: the ranking comes from published
human-preference tests, and the check proves intelligibility, not charm.

## Pen sounds: off by default

The first listener found the pen sound annoying and out of sync, so it is
off everywhere by default: videos are voice only (`narrate.py --pen` brings
it back), and in lessons the Sound button turns it on. The video pen track is
placed by an estimate of when strokes draw, which is why it drifts; sync it
to the real stroke times before turning it back on by default.

## Pen sounds: real recordings, cut into grains

| Board | Recording | Licence |
| --- | --- | --- |
| chalkboard (dark mode) | two takes of chalk drawing on a board, OpenGameArt | CC0 |
| paper (light mode) | graphite pencil writing on paper, Freesound via OpenGameArt | CC0 |

Sources and processing are in `skills/lesson-notebook/assets/sounds/SOUNDS.md`.
The three files come to 21 KB and are embedded in every lesson, so a lesson
stays one file that works offline.

Each stroke plays short overlapping grains (85 ms, Hann-like fade) cut from
where a recording is loudest, at random offsets and levels. The stroke
shapes them:

- direction: horizontal strokes play a touch higher, vertical ones lower
- position: panned by where the stroke is on screen
- speed: faster strokes are louder and brighter
- chalk also taps when it lands

The board picks the sound automatically, the same way it picks the look:
an explicit Board choice first, then the page theme, then the system's dark
mode. Chalk sounds go with the chalkboard and pencil with paper.

Measured from the recordings, real pen sound is impulsive, not smooth hiss:
crest factor 9 to 14, broadband (pencil 0.7 to 11.6 kHz, chalk 1.9 to 7.4
kHz), pulsing about every 20 ms as the tip catches and slips. That's the
stick-slip friction that the research on scraping and rubbing describes as
a train of small impacts. Until the recordings decode (or if a browser
can't decode MP3), a friction synth stands in, built to those numbers:
sparse clicks over broadband hiss with a 20 ms pulse.

## The video mix

- voice normalised to its peak
- no pen by default; with `--pen`, it sits 17 dB under the voice on paper, 15 dB on chalk
- a faint room tone 42 dB under the voice, so pauses sound like a quiet room instead of a dropout
- `loudnorm` to -16 LUFS, then a limiter at -2.5 dBFS so true peak stays under -1 dBTP after AAC
- `check_video.py` checks loudness, peak, frames and captions; `check_speech.py` checks the words

## Sources

- TTS arena rankings and licences: Artificial Analysis Speech Arena, the Hugging Face TTS Arena, and each model's own card (checked October 2026).
- Chatterbox: https://github.com/resemble-ai/chatterbox and Resemble AI's published blind test against ElevenLabs.
- Kokoro: https://huggingface.co/hexgrad/Kokoro-82M, run through https://github.com/thewh1teagle/kokoro-onnx.
- Chalk: https://opengameart.org/content/drawing-with-chalk (CC0).
- Pencil: https://opengameart.org/node/132692 (CC0), from https://freesound.org/people/NachtmahrTV/sounds/571800/ (CC0).
- Friction as impacts: "Intuitive Control of Scraping and Rubbing Through Audio-tactile Synthesis", https://arxiv.org/abs/2401.05757.
