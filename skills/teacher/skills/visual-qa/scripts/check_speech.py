#!/usr/bin/env python3
"""Check that a narrated video says what its captions say.

  python3 check_speech.py clip.mp4 [--vtt clip.vtt] [--model base.en] [--min-recall 0.85] [--json]

Listens to the clip with Whisper (faster-whisper, local model cache by default;
TEACHER_ALLOW_NETWORK=1 permits model download) and, cue by cue, checks how many of the caption's words were
actually heard near that cue's time. Catches a voice that skips, slurs or
mangles words, mispronounces a symbol, or drifts out of sync with the
captions: things nobody can hear in a frame-by-frame check. Fails when
fewer than --min-recall of all caption words are heard, or when any cue
drops below half. Short and very common words are ignored, and numbers
count whether heard as digits or as words. Captions that parse to no cues,
or to no checkable words, fail: there is nothing to check them against.

Needs: pip install faster-whisper (in the same Python as this script) and ffmpeg.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
from collections import Counter
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
            out.append((stamp(m.group(1)), stamp(m.group(2)), html.unescape(re.sub(r"<[^>]+>", "", m.group(3))).strip()))
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


def units(heard: list[tuple[float, float, str]], idx: list[int]) -> list[tuple[str, tuple[int, ...]]]:
    """The ways a caption word can be heard in a run of heard words, as
    (word, indices of the heard words it uses)."""
    out = []
    for k, i in enumerate(idx):
        a = heard[i][2]
        out.append((a, (i,)))
        if k + 1 < len(idx):
            j = idx[k + 1]
            b = heard[j][2]
            # A compound may be heard as two or three words ("cross entropy", "winner takes all").
            out.append((a + b, (i, j)))
            if k + 2 < len(idx):
                out.append((a + b + heard[idx[k + 2]][2], (i, j, idx[k + 2])))
            # Whisper splits decimals ("0" then ".693"); join neighbouring numbers back up.
            if a.isdigit() and b.replace(".", "").isdigit():
                out.append((f"{a}.{b}".rstrip("0").rstrip("."), (i, j)))
    return out


def take(want: list[str], heard: list[tuple[float, float, str]], idx: list[int], used: set[int],
         span: tuple[float, float] = (0.0, 0.0)) -> tuple[list[str], list[str]]:
    """Split a cue's words into (heard, missing), using the heard words at idx
    that aren't in used yet, and add the ones it uses to used. Each heard word
    counts once, so a caption that says a word twice needs to be heard saying
    it twice, and a word heard once can't count for two cues. Of several
    matches, the one nearest the cue's time (span) wins."""
    start, end = span
    cands = units(heard, idx)
    hit, missing = [], []
    for w in want:
        best = None
        for tok, ix in cands:
            if tok != w or used.intersection(ix):
                continue
            t = (heard[ix[0]][0] + heard[ix[-1]][1]) / 2
            d = max(0.0, start - t, t - end)
            if best is None or d < best[0]:
                best = (d, ix)
        if best:
            used.update(best[1])
            hit.append(w)
        else:
            missing.append(w)
    return hit, missing


def match(want: list[str], window: list[str]) -> tuple[list[str], list[str]]:
    """take() for a plain list of heard words, all at one time."""
    return take(want, [(0.0, 0.0, w) for w in window], list(range(len(window))), set())


def score(cue_list: list[tuple[float, float, str]], heard: list[tuple[float, float, str]], min_recall: float) -> dict:
    """Compare captions with what was heard. An empty or malformed VTT, or one
    with no checkable words, is a failure with a reason, never a vacuous pass."""
    rows = []
    total = got = 0
    used: set[int] = set()  # heard words already credited to a cue
    wants = [[w for w in words(text) if keep(w)] for _, _, text in cue_list]
    # Two passes, so a cue can't take a word its neighbour said on time (when
    # its own copy was misheard): first each cue takes what was heard inside
    # its own time, then what's left within 2.5 s either side.
    first = []
    for (start, end, _), want in zip(cue_list, wants):
        idx = [i for i, (t0, t1, _) in enumerate(heard) if start <= (t0 + t1) / 2 <= end]
        first.append(take(want, heard, idx, used, (start, end)))
    for (start, end, text), want, (hit, missing) in zip(cue_list, wants, first):
        idx = [i for i, (t0, t1, _) in enumerate(heard) if t1 >= start - 2.5 and t0 <= end + 2.5]
        late, missing = take(missing, heard, idx, used, (start, end))
        hit = hit + late
        total += len(want)
        got += len(hit)
        rows.append({"start": round(start, 2), "text": text, "recall": round(len(hit) / len(want), 2) if want else 1.0,
                     "missing": missing})
    error = None
    if not cue_list:
        error = "no caption cues parsed (the VTT is empty or malformed)"
    elif not total:
        error = f"{len(cue_list)} cues but no checkable caption words"
    recall = got / total if total else 0.0
    weak = [r for r in rows if r["recall"] < 0.5]
    return {"ok": error is None and recall >= min_recall and not weak, "error": error, "recall": recall,
            "got": got, "total": total, "weak": weak, "rows": rows}


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
    cue_list = cues(vtt)
    res = score(cue_list, [], a.min_recall)
    if res["error"]:
        # Nothing to listen for: fail now, before loading Whisper.
        print(json.dumps({"ok": False, "error": res["error"], "recall": 0, "cues": res["rows"]}, indent=1) if a.json
              else f"FAIL speech: {res['error']} in {vtt}")
        return 1
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
    try:
        model = WhisperModel(a.model, device="cpu", compute_type="int8",
                             local_files_only=os.environ.get("TEACHER_ALLOW_NETWORK") != "1")
    except Exception as exc:
        if os.environ.get("TEACHER_ALLOW_NETWORK") != "1":
            raise SystemExit("Whisper could not load a local model. Prepare the model separately or "
                             "explicitly opt in with TEACHER_ALLOW_NETWORK=1. " + str(exc)) from exc
        raise
    segments, _ = model.transcribe(audio, beam_size=1, word_timestamps=True, vad_filter=False)
    heard = [(w.start, w.end, ww) for s in segments for w in (s.words or []) for ww in words(w.word)]

    res = score(cue_list, heard, a.min_recall)
    ok, recall, got, total, rows, weak = res["ok"], res["recall"], res["got"], res["total"], res["rows"], res["weak"]
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
