#!/usr/bin/env python3
"""Check a teaching video before a learner sees it.

  python3 check_video.py clip.mp4 [--sheet sheet.png] [--min-height 720] [--lufs -16] [--json]

Fails on: no video stream, odd dimensions or under --min-height, a frame rate
under 24, long black stretches (over 1.5s), long frozen stretches (over 4s,
which usually means a stalled render), missing captions (a .vtt/.srt next to
the file or a subtitle stream), and for clips with sound: integrated loudness
more than 2 LU away from --lufs, or true peak above -1 dBTP. --sheet writes a
contact sheet of 12 frames so a person (or a model) can eyeball the whole
clip in one image. Needs ffmpeg and ffprobe.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def probe(path: Path) -> dict:
    r = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)])
    if r.returncode:
        raise SystemExit(f"ffprobe failed: {r.stderr.strip()}")
    return json.loads(r.stdout)


class DecodeError(Exception):
    pass


def stretches(path: Path, filt: str, key: str) -> list[float]:
    """Lengths of the stretches the filter reports. Frames ffmpeg can't decode
    raise DecodeError: an empty list must mean "none found", not "not looked at".
    A decoder can hide damage (it conceals the frame and exits 0), so its
    error lines count too."""
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-xerror", "-i", str(path), "-vf", filt, "-an", "-f", "null", "-"])
    bad = [l for l in r.stderr.splitlines() if re.match(r"\[\w+ @ 0x[0-9a-f]+\] .*(error|invalid|corrupt)", l, re.I)]
    if r.returncode or bad:
        raise DecodeError((bad or r.stderr.strip().splitlines() or ["ffmpeg failed"])[-1 if not bad else 0])
    return [float(x) for x in re.findall(rf"{key}:\s*([\d.]+)", r.stderr)]


def loudness(path: Path) -> tuple[float | None, float | None]:
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"])
    summary = r.stderr[r.stderr.rfind("Summary:"):]
    i = re.search(r"I:\s*(-?[\d.]+) LUFS", summary)
    p = re.search(r"Peak:\s*(-?[\d.]+) dBFS", summary)
    return (float(i.group(1)) if i else None, float(p.group(1)) if p else None)


def contact_sheet(path: Path, duration: float, out: Path) -> None:
    n = 12
    step = max(duration / n, 0.04)
    r = run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(path), "-vf", f"fps=1/{step:.3f},scale=480:-1,tile=4x3:padding=6:margin=6:color=white", "-frames:v", "1", str(out)])
    if r.returncode:
        raise SystemExit(f"contact sheet failed: {r.stderr.strip()}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", type=Path)
    ap.add_argument("--sheet", type=Path)
    ap.add_argument("--min-height", type=int, default=720)
    ap.add_argument("--lufs", type=float, default=-16.0)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            raise SystemExit(f"{tool} not found on PATH")
    info = probe(a.video)
    streams = info.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    subs = [s for s in streams if s.get("codec_type") == "subtitle"]
    duration = float(info.get("format", {}).get("duration", 0))
    problems: list[str] = []
    facts: dict = {"duration_s": round(duration, 2)}
    if not video:
        problems.append("no video stream")
    else:
        w, h = int(video["width"]), int(video["height"])
        num, den = (int(x) for x in video.get("avg_frame_rate", "0/1").split("/"))
        fps = num / den if den else 0
        facts.update(size=f"{w}x{h}", fps=round(fps, 2), codec=video.get("codec_name"), pix_fmt=video.get("pix_fmt"))
        if w % 2 or h % 2:
            problems.append(f"odd dimensions {w}x{h} (many players refuse them)")
        if h < a.min_height:
            problems.append(f"height {h} is under {a.min_height}")
        if fps < 24:
            problems.append(f"frame rate {fps:.1f} is under 24")
        if video.get("pix_fmt") not in (None, "yuv420p"):
            problems.append(f"pixel format {video.get('pix_fmt')}: use yuv420p for playback everywhere")
        try:
            black = stretches(a.video, "blackdetect=d=1.5:pix_th=0.10", "black_duration")
            frozen = stretches(a.video, "freezedetect=n=0.001:d=4", "lavfi.freezedetect.freeze_duration")
        except DecodeError as e:
            problems.append(f"the video doesn't decode, so black and frozen stretches weren't checked: {e}")
            black = frozen = None
        if black:
            problems.append(f"black stretches: {', '.join(f'{b:.1f}s' for b in black)}")
        if frozen:
            problems.append(f"frozen stretches over 4s: {', '.join(f'{f:.1f}s' for f in frozen)}")
        facts.update(black=black, frozen=frozen)
    side = [p for p in (a.video.with_suffix(".vtt"), a.video.with_suffix(".srt")) if p.exists()]
    facts["captions"] = [p.name for p in side] + [f"stream {s.get('index')}" for s in subs]
    if not facts["captions"]:
        problems.append("no captions: add a .vtt next to the video or a subtitle stream")
    if audio:
        lufs, peak = loudness(a.video)
        facts.update(lufs=lufs, true_peak=peak)
        # An audio stream that can't be measured (corrupt, or no summary) is a
        # failure, not a pass with the checks skipped.
        if lufs is None:
            problems.append("audio stream present but its loudness couldn't be measured")
        if peak is None:
            problems.append("audio stream present but its true peak couldn't be measured")
        if lufs is not None and abs(lufs - a.lufs) > 2:
            problems.append(f"loudness {lufs} LUFS, target {a.lufs} (±2)")
        if peak is not None and peak > -1:
            problems.append(f"true peak {peak} dBTP is above -1")
    else:
        facts["audio"] = "none"
    if a.sheet and video:
        contact_sheet(a.video, duration, a.sheet)
        facts["sheet"] = str(a.sheet)
    if a.json:
        print(json.dumps({"video": str(a.video), "facts": facts, "problems": problems}, indent=2))
    else:
        for k, v in facts.items():
            print(f"     {k}: {v}")
        for p in problems:
            print(f"FAIL {p}")
        print("clean" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
