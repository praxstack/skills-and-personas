# Pen sounds

Real recordings of chalk and pencil, played back in small overlapping grains
so every stroke sounds a little different (sound.js live, narrate.py in
videos). All three are public domain (CC0): no credit needed, but here it is.

| File | What it is | Source | Licence |
| --- | --- | --- | --- |
| `chalk-1.mp3` | chalk drawing on a stone board | "drawing with chalk" by sinny, https://opengameart.org/content/drawing-with-chalk (`chalk_drawing_01.mp3`) | CC0 |
| `chalk-2.mp3` | the same, a second take | same page (`chalk_drawing_02.mp3`) | CC0 |
| `pencil.mp3` | graphite pencil writing on paper | "Pencil Sounds" by AntumDeluge, https://opengameart.org/node/132692 (`pencil_write.flac`), cut from "Writing with pencil" by NachtmahrTV, https://freesound.org/people/NachtmahrTV/sounds/571800/ (CC0 on Freesound too) | CC0 |

Each was trimmed of silence, mixed to mono 44.1 kHz, high-passed at 120 Hz,
normalised to -20 LUFS and encoded as 64 kbps MP3 (21 KB for all three).

After changing a file here, regenerate the embedded copy:

    python3 teacher/skills/lesson-notebook/scripts/make_pen_samples.py

What the recordings taught the synthesis (measured with numpy): real pen
sound is impulsive, not smooth hiss (crest factor 9 to 14 against about 4
for filtered noise), broadband (pencil carries energy from 0.7 to 11.6 kHz,
chalk from 1.9 to 7.4 kHz, centred near 5 kHz) and pulses about every 20 ms
as the tip catches and slips. The procedural fallback copies those numbers.
