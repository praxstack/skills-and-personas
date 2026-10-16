#!/usr/bin/env python3
"""edge_voice_swap.py: re-voice a finished video with a Microsoft neural voice, on your own laptop.

The video already has a natural offline voice (Kokoro) baked in. Use this only if you prefer an edge-tts
voice, for example an Indian English one. Every line starts exactly where the animation expects it. A line the new
voice says too slowly for its slot is spoken again in one breath, up to 25% faster; if one still cannot fit, nothing
is written.

Setup:  pip install edge-tts      (and have ffmpeg on your PATH)
Run, in the folder with the MP4, timeline.json and bed.m4a:
  python edge_voice_swap.py                         -> en-US-AriaNeural
  python edge_voice_swap.py en-IN-NeerjaNeural      (Indian English, female)
  python edge_voice_swap.py en-IN-PrabhatNeural     (Indian English, male)
  python edge_voice_swap.py en-GB-SoniaNeural my-video.mp4
List voices: edge-tts --list-voices
"""
import asyncio
import glob
import json
import atexit
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

import edge_tts

VOICE = sys.argv[1] if len(sys.argv) > 1 else "en-US-AriaNeural"
# the original, not an earlier swap (<name>-<voice>.mp4, every edge voice ends in Neural: en-US-AriaNeural)
mp4s = [f for f in sorted(glob.glob("*.mp4")) if not re.search(r"-[a-z]{2,3}-[A-Z]{2}(-[a-z]+)?-[A-Za-z]+Neural\.mp4$", f)]
VIDEO = sys.argv[2] if len(sys.argv) > 2 else (mp4s[0] if mp4s else sys.exit("no .mp4 here"))
lines = json.load(open("timeline.json", encoding="utf-8"))
tmp = tempfile.mkdtemp()
atexit.register(shutil.rmtree, tmp, ignore_errors=True)  # however the run ends: its mp3s and wavs are large


# the same split voice.py makes: . ? ! (and closing quotes) before a space, or a full-width 。？！
SENTENCE_END = re.compile(r"[.?!][\"'\u201d\u2019)\]]*\s+(?=\S)|[\u3002\uff1f\uff01][\u300d\u300f\u201d\u2019\uff09\"']*\s*(?=\S)")


# a period after these is not a sentence end ("e.g. a list", "Dr. Rao", "J. K."), so the line is not cut there
ABBREV = {"mr", "mrs", "ms", "dr", "prof", "st", "jr", "sr", "vs", "etc", "e.g", "i.e", "cf", "approx", "fig", "eq"}


def _abbrev(text, end):
    word = re.search(r"(\S*)$", text[:end]).group(1).lstrip("\"'\u201c\u2018([")
    return word.lower() in ABBREV or (len(word) == 1 and word.isupper())


def sentences(text):
    out, at = [], 0
    for m in SENTENCE_END.finditer(text):
        if text[m.start()] == "." and _abbrev(text, m.start()):
            continue
        out.append(text[at:m.end()].strip())
        at = m.end()
    out.append(text[at:].strip())
    return [p for p in out if p]


async def tts():
    # one call per sentence, joined by the line's pause, so the pacing matches the film's own voice
    for i, ln in enumerate(lines):
        pause, text = float(ln.get("pause", 0)), (ln.get("say") or ln["text"]).strip()
        parts = sentences(text) if pause > 0 else [text]
        files = [os.path.join(tmp, f"v{i:03d}-{j:02d}.mp3") for j in range(len(parts))]
        for part, f in zip(parts, files):
            await edge_tts.Communicate(part, VOICE).save(f)
        pads = "".join(f"[{j}:a]aresample=48000,aformat=channel_layouts=mono" + (f",apad=pad_dur={pause}" if j < len(files) - 1 else "")
                       + f"[s{j}];" for j in range(len(files)))
        subprocess.run(["ffmpeg", "-y", "-v", "error", *sum((["-i", f] for f in files), []), "-filter_complex",
                        pads + "".join(f"[s{j}]" for j in range(len(files))) + f"concat=n={len(files)}:v=0:a=1",
                        os.path.join(tmp, f"v{i:03d}.wav")], check=True)
        print(f"{i + 1}/{len(lines)}", end="\r", flush=True)
asyncio.run(tts())


def length(f):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]).decode())


TEMPO = 1.35  # the most a spoken line is sped up to fit its slot; faster than this sounds rushed
RATE = 25     # how much faster (percent) the voice itself may speak a line that is still too long


def room(i):
    """The seconds line i has before the next line starts (or the film ends), less a short breath: 0.12 s, or a
    quarter of a slot shorter than that. Never more than the real gap, so a line that cannot fit is found."""
    ln = lines[i]
    gap = max((lines[i + 1]["start"] if i + 1 < len(lines) else ln["start"] + ln["dur"]) - ln["start"], 0.0)
    return gap - min(0.12, gap * 0.25)


def fit(i):
    """How much line i must be sped up to end inside its slot (infinite for a slot with no room at all)."""
    r = room(i)
    return length(os.path.join(tmp, f"v{i:03d}.wav")) / r if r > 0 else math.inf


async def say(i, rate):
    """Line i again, rate percent faster, in one call: its sentences without the added pauses."""
    ln, f = lines[i], os.path.join(tmp, f"v{i:03d}-fast.mp3")
    await edge_tts.Communicate(ln.get("say") or ln["text"], VOICE, rate=f"+{rate}%").save(f)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", f, "-ac", "1", "-ar", "48000", os.path.join(tmp, f"v{i:03d}.wav")], check=True)


# how much each line must be sped up to end before the next one starts. A line that needs more than TEMPO is
# spoken again, faster, by the voice itself; one that still cannot fit stops the swap, since it would overlap the next
need = [fit(i) for i in range(len(lines))]
for i in [i for i, x in enumerate(need) if x > TEMPO]:
    rate = RATE if math.isinf(need[i]) else min(RATE, math.ceil((need[i] / TEMPO - 1) * 100) + 3)
    asyncio.run(say(i, rate))
    need[i] = fit(i)
    if need[i] > TEMPO and rate < RATE:  # leading and trailing silence does not shrink with the rate: try the most allowed
        asyncio.run(say(i, RATE))
        need[i] = fit(i)
tight = [i for i, x in enumerate(need) if x > TEMPO]
if tight:
    sys.exit(f"{VOICE} speaks too slowly for {len(tight)} line(s): even {RATE}% faster and sped up {TEMPO}x they would run "
             "into the next line, so nothing was written. Try a faster voice. "
             + "; ".join(f"line {i + 1} at {lines[i]['start']:.1f} s (\"{(lines[i].get('say') or lines[i]['text'])[:40]}\") "
                         f"takes {length(os.path.join(tmp, f'v{i:03d}.wav')):.1f} s of a {room(i):.2f} s slot" for i in tight))

inputs, filt = ["-i", VIDEO, "-i", "bed.m4a"], []
for i, ln in enumerate(lines):
    f = os.path.join(tmp, f"v{i:03d}.wav")
    inputs += ["-i", f]
    speed = max(1.0, need[i])  # speed up only if a line would run into the next (at most TEMPO, checked above)
    ms = int(ln["start"] * 1000)
    filt.append(f"[{i + 2}:a]atempo={speed:.3f},aresample=48000,adelay={ms}|{ms}[a{i}]")
filt.append("".join(f"[a{i}]" for i in range(len(lines))) + f"amix=inputs={len(lines)}:normalize=0,volume=1.6[v]")
filt.append("[v][1:a]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[out]")
out = os.path.splitext(VIDEO)[0] + f"-{VOICE}.mp4"
if os.path.islink(out) or os.path.isfile(out):  # -y would write through a link left there: replace the entry itself
    os.unlink(out)
subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(filt), "-map", "0:v", "-map", "[out]",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out], check=True)
print("\nwrote", out)
