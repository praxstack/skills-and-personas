#!/usr/bin/env python3
"""stills.py: pull review stills out of a (draft) video at the moments that matter.

Use it when your tool renders whole videos more easily than single frames (Manim, Motion Canvas, Revideo):
render a fast draft, extract stills, look at them, fix, repeat. Page-based tools can render stills directly
with `capture.mjs --stills`.

Usage:
  python3 stills.py --project . --video build/draft.mp4 [--at chapters|lines|busy|12.5,40,61] [--out stills]
    chapters  one frame 45% into every chapter (default)
    lines     one frame 65% into every narration line (the full review set)
    busy      the 8 longest lines (where layouts are most crowded)
Also writes <out>/sheet.png, a contact sheet of the extracted stills.
"""
import argparse
import json
import os
import re
import subprocess


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".")
    ap.add_argument("--video", required=True)
    ap.add_argument("--at", default="chapters")
    ap.add_argument("--out", default="stills")
    ap.add_argument("--scale", type=float, default=1.0, help="draft renders at lower resolution: frames are taken as-is")
    a = ap.parse_args()
    root = os.path.abspath(a.project)
    tm = json.load(open(os.path.join(root, "timing.json")))
    out = a.out if os.path.isabs(a.out) else os.path.join(root, a.out)
    os.makedirs(out, exist_ok=True)
    slug = lambda s: re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")  # noqa: E731
    if a.at == "chapters":
        # 45% into the chapter, moved off a caption swap (both captions faint for ~0.35 s): to just before it, where the
        # previous line rests, or, at the chapter's first line (before it is the chapter card), just after it
        off_swap = lambda t: next(((ln["voiceAt"] + 0.4 if next(x for x in tm["lines"] if x["chapter"] == ln["chapter"]) is ln
                                else ln["voiceAt"] - 0.35) for ln in tm["lines"] if abs(t - ln["voiceAt"]) < 0.3), t)  # noqa: E731
        shots = [(f"ch{c['n']}-{slug(c['name'])}", off_swap(c["start"] + 0.45 * (c["end"] - c["start"]))) for c in tm["chapters"]]
    elif a.at == "lines":
        shots = [(f"{ln['start']:07.1f}-{ln['id']}", ln["voiceAt"] + 0.65 * ln["voiceDur"]) for ln in tm["lines"]]
    elif a.at == "busy":
        shots = [(f"{ln['start']:07.1f}-{ln['id']}", ln["voiceAt"] + 0.8 * ln["voiceDur"])
                 for ln in sorted(tm["lines"], key=lambda x: -x["dur"])[:8]]
    else:
        shots = [(f"t{float(x):07.2f}", float(x)) for x in a.at.split(",")]
    files = []
    for name, t in shots:
        f = os.path.join(out, f"{name}.jpg")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", a.video, "-frames:v", "1", "-q:v", "3", f], check=True)
        files.append(f)
        print("still", name, f"{t:.2f}")
    cols = 4
    rows = (len(files) + cols - 1) // cols
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-pattern_type", "glob", "-i", os.path.join(out, "*.jpg"),
                    "-vf", f"scale=480:-1,tile={cols}x{rows}:padding=4:color=0x111111", "-frames:v", "1",
                    os.path.join(out, "sheet.png")])
    print("sheet", os.path.join(out, "sheet.png"))


if __name__ == "__main__":
    main()
