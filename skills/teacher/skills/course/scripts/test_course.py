#!/usr/bin/env python3
"""Smoke-test a whole course: every lesson's code, interactions and looks, then the course page.

  python3 test_course.py courses/segment-tree [--out dir] [--skip-qa]

Per lesson: check_code.mjs (when it shows code), build, test_lesson.mjs, and
check_page.mjs (6 runs, every step, with the lesson's model checks). Then the course page
(map, outline, notes, quiz) gets check_page and a quick click-through. Prints
one line per lesson and exits non-zero if anything failed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parent.parent
EXP = SKILLS / "explorable" / "scripts"
QA = SKILLS / "visual-qa" / "scripts"


def run(cmd: list[str], timeout: int = 900) -> tuple[int, str]:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("course", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--skip-qa", action="store_true", help="skip the 6-run visual QA (faster)")
    ap.add_argument("--trust-authored-code", action="store_true", help="after review, allow lesson and shown code to execute")
    ap.add_argument("--course-checker", choices=("v1", "v2"), default="v2",
                    help="course-consent/v2 (default); v1 reproduces the historical consent-unaware diagnostic")
    a = ap.parse_args()
    sys.path.insert(0, str(HERE))
    if a.out:
        return check(a, a.out)
    # Builds, screenshots and copied videos run to hundreds of MB: without
    # --out they go in a folder that is removed afterwards.
    with tempfile.TemporaryDirectory(prefix="course-") as tmp:
        return check(a, Path(tmp))


def check(a: argparse.Namespace, out: Path) -> int:
    from safe_course import snapshot_course
    import copy
    with snapshot_course(a.course) as snapshot:
        private = copy.copy(a)
        private.course = snapshot
        return check_snapshot(private, out)


def check_snapshot(a: argparse.Namespace, out: Path) -> int:
    import build_course  # noqa: E402

    data = build_course.build_course(a.course, out, trust_authored_code=a.trust_authored_code)
    shared = [str(a.course / s) for s in data.get("shared", [])]
    inc = [x for s in shared for x in ("--include", s)]
    failed = 0
    for lesson in data["lessons"]:
        src = str(a.course / lesson["file"])
        page = str(out / lesson["page"])
        parts = []
        ok = True
        if lesson["hasCode"]:
            code, text = run(["node", str(EXP / "check_code.mjs"), src, *inc, *(["--trust-authored-code"] if a.trust_authored_code else [])])
            m = re.search(r"(\d+) runs match the model, (\d+) problems", text)
            if code == 0 and "no C++ or Python to run" in text:
                parts.append("code shown, not checked")
            else:
                parts.append(f"code {m.group(1)} runs ok" if code == 0 and m and int(m.group(1)) else "code FAIL")
                code = code or not (m and int(m.group(1)))  # C++ or Python shown but none of it ran
            ok &= code == 0
            if code:
                print(text)
        if lesson["kind"] == "explorable":
            code, text = run(["node", str(EXP / "test_lesson.mjs"), page, "--shots", str(out / f"{lesson['id']}-shots")])
            m = re.search(r"(\d+) passed, (\d+) failed", text)
            parts.append(f"interactions {m.group(1)}/{int(m.group(1)) + int(m.group(2))}" if m else "interactions FAIL")
            ok &= code == 0
            if code:
                print("\n".join(l for l in text.splitlines() if l.startswith("FAIL") or "Error" in l)[:3000])
        if not a.skip_qa:
            ev = ["--eval", "window.__explorable.check()", "--all-steps"] if lesson["kind"] == "explorable" else []
            code, text = run(["node", str(QA / "check_page.mjs"), page, "--out", str(out / f"{lesson['id']}-qa"), *ev])
            parts.append("looks clean" if code == 0 else "looks FAIL")
            ok &= code == 0
            if code:
                print(text[:3000])
        stale = build_course.unpublished_change(a.course, data["id"], lesson["id"], build_course.load_manifest(a.course))
        if stale:
            parts.append(f"WARN {stale}")
        if lesson.get("video", "").startswith("https://"):
            parts.append("video on Blob")
        elif lesson.get("video"):
            local = (out / "videos" / f"{lesson['id']}.mp4").exists()
            parts.append("video local" if local else "video FAIL (missing)")
            ok &= local
        else:
            parts.append("no video")
        failed += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {lesson['id']}: {', '.join(parts)}")
    checker = "check_course_page.mjs" if a.course_checker == "v1" else "check_course_page_v2.mjs"
    code, text = run(["node", str(HERE / checker), str(out / "index.html")])
    print(text.strip().splitlines()[-1] if text.strip() else "course page: no output")
    failed += code != 0
    if code:
        print(text[:3000])
    if not a.skip_qa:
        code, text = run(["node", str(QA / "check_page.mjs"), str(out / "index.html"), "--out", str(out / "course-qa")])
        print(f"{'ok  ' if code == 0 else 'FAIL'} course page looks")
        failed += code != 0
        if code:
            print(text[:3000])
    where = f" (outputs in {out})" if a.out else " (pass --out to keep the outputs)"
    print(f"{data['id']}: {len(data['lessons'])} lessons, {'all passed' if not failed else f'{failed} failed'}{where}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
