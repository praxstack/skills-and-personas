"""E17 sync fixtures (not a test module): a short narration built from the switch lesson's own
Kokoro segments, then broken on purpose.

    control        three cues, scheduled from their measured durations: must pass the sync gate
    shifted        the same audio starting 0.9 s late: cue starts and ends miss by more than 0.5 s
    truncated      the audio cut halfway through the last cue: its end and its words go missing
    mispronounced  the first cue says "and" where the line says the code token `n`

Each fixture is (audio wav, timing). The timing is always the control's schedule, as a real
build's captions would be.
"""
import json

from _util import SLICE
from ptk import host, model, tts
from ptk.project import video

CUES = ("sc1.0", "sc3.0", "sc3.1")
GAP = 0.8
SHIFT = 0.9
# a code-token misreading: Kokoro or a bad respelling saying "and" for the variable n
MISREAD = "The program sets and to two, and switches on and. Case two has no break."


def _measure(segs, work):
    syn = tts.synthesize([{"id": s["id"], "spoken": s["spoken"]} for s in segs], work / "tts", force_engine="kokoro")
    return tts.trim_and_measure(syn["segments"], work / "tts")


def _timing(segs, measured):
    dur = {m["id"]: m["seconds"] for m in measured}
    t, cues = 0.8, []
    for s in segs:
        start = video._frame(t)
        end = video._frame(start + dur[s["id"]])
        cues.append({**s, "start": start, "end": end, "seconds": dur[s["id"]]})
        t = end + GAP
    return {"fps": video.FPS, "duration": video._frame(t + 0.8), "cues": cues, "scenes": []}


def build(kind, work):
    """Write the fixture's wav under work; return (wav, timing)."""
    lesson = model.load(SLICE)
    segs = [s for s in video.segments_of(lesson) if s["id"] in CUES]
    work.mkdir(parents=True, exist_ok=True)
    measured = _measure(segs, work)
    timing = _timing(segs, measured)
    if kind == "mispronounced":
        bad = _measure([{**segs[0], "spoken": MISREAD}], work / "bad")[0]
        # keep the control's cue times (what the captions say), but play the misread audio,
        # padded or cut to the cue's length so every later cue stays where it was
        c0 = timing["cues"][0]
        fit = work / "bad" / "fit.wav"
        host.run([host.which("ffmpeg"), "-v", "error", "-y", "-i", bad["wav"], "-af",
                  f"apad,atrim=duration={c0['end'] - c0['start']:.4f}", "-c:a", "pcm_s16le", fit], check=True, timeout=60)
        measured = [{**measured[0], "wav": fit}] + measured[1:]
    clean = work / "clean.wav"
    video.assemble_audio(timing, measured, work, clean)
    if kind in ("control", "mispronounced"):
        return clean, timing
    ffmpeg = host.which("ffmpeg")
    out = work / f"{kind}.wav"
    if kind == "shifted":
        af = f"adelay={int(SHIFT * 1000)}:all=1,atrim=duration={timing['duration']:.3f}"
    elif kind == "truncated":
        last = timing["cues"][-1]
        cut = (last["start"] + last["end"]) / 2
        af = f"atrim=duration={cut:.3f},apad=whole_dur={timing['duration']:.3f}"
    else:
        raise ValueError(kind)
    host.run([ffmpeg, "-v", "error", "-y", "-i", clean, "-af", af, "-c:a", "pcm_s16le", out], check=True, timeout=120)
    (work / f"{kind}.json").write_text(json.dumps(timing, default=str))
    return out, timing
