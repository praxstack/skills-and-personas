#!/usr/bin/env python3
"""Make a narrated video for every lesson in a course (skips ones already made).

  <python with kokoro-onnx> narrate_course.py courses/segment-tree [--force] [--only id ...] [--board paper|chalk]

Builds each explorable lesson, runs explorable/scripts/narrate.py on it and
writes courses/<id>/videos/<lesson-id>.mp4 with its .vtt captions (and a
.sheet.png contact sheet to look at, which .gitignore keeps out of git). The
MP4s stay out of git too: publish_videos.mjs puts them on Vercel Blob and
records their URLs in courses/videos.json, and a lesson with a URL there
counts as made. The course page links them as "Watch the narrated video".
Run it with a Python that has kokoro-onnx, soundfile and numpy installed.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parent.parent / "explorable" / "scripts"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("course", type=Path)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--board", choices=["paper", "chalk"], default="paper")
    ap.add_argument("--remux", action="store_true", help="remake only the sound of every existing video, keeping its picture (no --force needed)")
    a = ap.parse_args()
    meta = json.loads((a.course / "course.json").read_text())
    shared = [x for s in meta.get("shared", []) for x in ("--include", str(a.course / s))]
    out_dir = a.course / "videos"
    out_dir.mkdir(exist_ok=True)
    manifest_file = a.course.resolve().parent / "videos.json"
    published = json.loads(manifest_file.read_text()) if manifest_file.exists() else {}
    bad = 0
    for lesson in meta["lessons"]:
        if a.only and lesson["id"] not in a.only:
            continue
        if not lesson["file"].endswith(".lesson.js"):
            continue
        mp4 = out_dir / f"{lesson['id']}.mp4"
        # --remux works on the videos that exist (it keeps their picture), so it
        # implies --force for them and skips lessons that have no video yet.
        if a.remux and not mp4.exists():
            print(f"skip {lesson['id']}: no video to remux")
            continue
        if mp4.exists() and not (a.force or a.remux):
            print(f"skip {lesson['id']}: already made")
            continue
        # A published video is made, but --remux still remakes its sound.
        if published.get(f"{meta['id']}/{lesson['id']}.mp4") and not (a.force or a.remux):
            print(f"skip {lesson['id']}: already on Blob (courses/videos.json); --force makes it again")
            continue
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / f"{lesson['id']}.html"
            r = subprocess.run([sys.executable, str(EXP / "build.py"), str(a.course / lesson["file"]), *shared, "-o", str(page)], capture_output=True, text=True)
            if r.returncode:
                print(f"FAIL {lesson['id']}: build\n{r.stderr}")
                bad += 1
                continue
            r = subprocess.run([sys.executable, str(EXP / "narrate.py"), str(page), "-o", str(mp4), "--board", a.board, *(["--remux"] if a.remux else [])], capture_output=True, text=True)
            tail = (r.stdout + r.stderr).strip().splitlines()
            print(f"{'ok  ' if r.returncode == 0 else 'FAIL'} {lesson['id']}: {' | '.join(l.strip() for l in tail if 'duration' in l or 'lufs' in l or 'speech' in l or 'FAIL' in l or l.strip() in ('clean',))}")
            bad += r.returncode != 0
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
