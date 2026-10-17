#!/usr/bin/env python3
"""Check that a narrated video says what its captions say.

  python3 check_speech.py clip.mp4 [--vtt clip.vtt] [--model base.en] [--min-recall 0.85] [--json]

Listens to the clip with Whisper (faster-whisper, offline after the first
model download) and, cue by cue, checks how many of the caption's words were
actually heard near that cue's time. Catches a voice that skips, slurs or
mangles words, mispronounces a symbol, or drifts out of sync with the
captions: things nobody can hear in a frame-by-frame check. Fails when
fewer than --min-recall of all caption words are heard, or when any cue
drops below half. Short and very common words are ignored, and numbers
count whether heard as digits or as words.

Needs: pip install faster-whisper (in the same Python as this script) and ffmpeg.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SMALL = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
         "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty"]
TENS = {"thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
SKIP = set("the and for that this with you are its it's was were but not then than into from have has had what when".split())


def stamp(t: str) -> float:
    h, m, s = ([0] + t.split(":"))[-3:]
    return int(h) * 3600 + int(m) * 60 + float(s.replace(",", "."))


def cues(vtt: Path) -> list[tuple[float, float, str]]:
    out = []
    for block in re.split(r"\n\s*\n", vtt.read_text()):
        m = re.search(r"([\d:.,]+)\s*-->\s*([\d:.,]+)[^\n]*\n(.+)", block, re.S)
        if m:
            out.append((stamp(m.group(1)), stamp(m.group(2)), re.sub(r"<[^>]+>", "", m.group(3)).strip()))
    return out


def words(text: str) -> list[str]:
    """Lower-case words, with numbers as digits (twenty one, 21 and 21.0 all become 21)."""
    t = text.lower()
    t = re.sub(r"(?<=[a-z0-9])-(?=[a-z0-9])", "", t).replace("-", " ")  # hand-made, 2-D -> handmade, 2d
    t = re.sub(r"(?<=[a-z]{2})our(s?)\b", r"or\1", t)  # British spelling: neighbours -> neighbors
    t = re.sub(r"(?<=[a-z]{3})is(e|ed|es|ing)\b", r"iz\1", t)  # minimise -> minimize
    toks = re.findall(r"[a-z]+|\d+(?:\.\d+)?", t)
    out: list[str] = []
    for w in toks:
        if w in SMALL:
            w = str(SMALL.index(w))
        elif w in TENS:
            w = str(TENS[w])
        if out and w.isdigit() and out[-1].isdigit() and int(out[-1]) % 10 == 0 and 20 <= int(out[-1]) < 100 and int(w) < 10:
            out[-1] = str(int(out[-1]) + int(w))  # "twenty one" -> 21
            continue
        out.append(w.rstrip("0").rstrip(".") if "." in w else w)
    return out


def keep(w: str) -> bool:
    return w.isdigit() or (len(w) >= 3 and w not in SKIP)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clip", type=Path)
    ap.add_argument("--vtt", type=Path)
    ap.add_argument("--model", default="base.en")
    ap.add_argument("--min-recall", type=float, default=0.85)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    vtt = a.vtt or a.clip.with_suffix(".vtt")
    if not vtt.exists():
        raise SystemExit(f"no captions at {vtt}")
    try:
        import numpy as np
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit("faster-whisper isn't installed: pip install faster-whisper")

    # Decode with ffmpeg rather than faster-whisper's PyAV, whose API shifts between versions.
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(a.clip), "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True)
    if raw.returncode or not raw.stdout:
        raise SystemExit(f"ffmpeg couldn't read the audio: {raw.stderr.decode()[-500:]}")
    audio = np.frombuffer(raw.stdout, dtype=np.float32)
    model = WhisperModel(a.model, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio, beam_size=1, word_timestamps=True, vad_filter=False)
    heard = [(w.start, w.end, ww) for s in segments for w in (s.words or []) for ww in words(w.word)]

    rows = []
    total = got = 0
    for start, end, text in cues(vtt):
        want = [w for w in words(text) if keep(w)]
        window = [w for t0, t1, w in heard if t1 >= start - 2.5 and t0 <= end + 2.5]
        # A compound may be heard as two or three words ("cross entropy", "winner takes all").
        near = set(window) | {a + b for a, b in zip(window, window[1:])} | {a + b + c for a, b, c in zip(window, window[1:], window[2:])}
        # Whisper splits decimals ("0" then ".693"); join neighbouring numbers back up.
        near |= {f"{a}.{b}".rstrip("0").rstrip(".") for a, b in zip(window, window[1:]) if a.isdigit() and b.replace(".", "").isdigit()}
        hit = [w for w in want if w in near]
        total += len(want)
        got += len(hit)
        rows.append({"start": round(start, 2), "text": text, "recall": round(len(hit) / len(want), 2) if want else 1.0,
                     "missing": [w for w in want if w not in near]})
    recall = got / total if total else 1.0
    weak = [r for r in rows if r["recall"] < 0.5]
    ok = recall >= a.min_recall and not weak
    if a.json:
        print(json.dumps({"ok": ok, "recall": round(recall, 3), "cues": rows}, indent=1))
    else:
        print(f"{'ok  ' if ok else 'FAIL'} speech: {got}/{total} caption words heard ({recall:.0%}), {len(weak)} weak cues")
        for r in sorted(rows, key=lambda r: r["recall"])[:5]:
            if r["missing"]:
                print(f"  {r['start']:7.1f}s {r['recall']:.0%} missing {', '.join(r['missing'][:8])}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
