#!/usr/bin/env python3
"""Build an explorable lesson into one self-contained HTML file.

  python3 build.py path/to/lesson.js -o out.html [--fragment]

The lesson file sets window.LESSON (see ../SKILL.md). The output inlines the
notebook styles and fonts, the ink and pen code and this engine, so it opens
from disk, in a Claude artifact, a Codex or ChatGPT canvas, or any static host.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / "assets" / "engine"
sys.path.insert(0, str(HERE.parent.parent / "lesson-notebook" / "scripts"))
import bundle  # noqa: E402

BODY = """<div id="app">
  <noscript><p>This lesson is interactive and needs JavaScript. The notes are in the lesson file.</p></noscript>
</div>"""


def lesson_field(src: str, name: str) -> str | None:
    m = re.search(rf"""\b{name}\s*:\s*(["'`])(.+?)\1""", src)
    return m.group(2) if m else None


def build(lesson: Path, out: Path, fragment: bool = False, include: list[Path] | None = None) -> Path:
    src = lesson.read_text()
    if "window.LESSON" not in src:
        raise SystemExit(f"{lesson}: expected `window.LESSON = {{...}}`")
    title = lesson_field(src, "title") or lesson.stem
    page = bundle.page(
        title=title,
        description=lesson_field(src, "subtitle") or "",
        css=[bundle.NOTEBOOK_CSS, ENGINE / "explorable.css"],
        modules=[*bundle.NOTEBOOK_MODULES, ENGINE / "code.js", ENGINE / "progress.js", ENGINE / "explorable.js"],
        scripts=[*(include or []), lesson],
        body=BODY,
        fragment=fragment,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lesson", type=Path)
    ap.add_argument("-o", "--out", type=Path)
    ap.add_argument("--fragment", action="store_true", help="omit doctype/html/head/body (for hosts that wrap pages)")
    ap.add_argument("--include", action="append", default=[], type=Path, help="shared scripts (a course's model) loaded before the lesson")
    args = ap.parse_args()
    out = build(args.lesson, args.out or args.lesson.with_suffix(".html"), args.fragment, args.include)
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
