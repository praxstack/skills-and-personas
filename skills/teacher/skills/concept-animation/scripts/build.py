#!/usr/bin/env python3
"""Build a concept animation into one self-contained HTML file.

  python3 build.py path/to/thing.anim.js -o out.html [--fragment] [--include model.js ...]

The animation file sets window.ANIMATION (see ../SKILL.md). Open the result
in any browser to scrub it, or turn it into MP4/GIF with scripts/export.mjs.
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


def build(source: Path, out: Path, fragment: bool = False, include: list[Path] | None = None) -> Path:
    """include: shared scripts (a course's models) loaded before the animation."""
    src = source.read_text()
    if "window.ANIMATION" not in src:
        raise SystemExit(f"{source}: expected `window.ANIMATION = {{...}}`")
    m = re.search(r"""\btitle\s*:\s*(["'`])(.+?)\1""", src)
    page = bundle.page(
        title=m.group(2) if m else source.stem,
        css=[bundle.NOTEBOOK_CSS, ENGINE / "animate.css"],
        modules=[*bundle.NOTEBOOK_MODULES, ENGINE / "animate.js"],
        scripts=[*(include or []), source],
        body='<main id="app"><noscript><p>This animation needs JavaScript. The transcript is in the source file.</p></noscript></main>',
        fragment=fragment,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", type=Path)
    ap.add_argument("-o", "--out", type=Path)
    ap.add_argument("--fragment", action="store_true")
    ap.add_argument("--include", type=Path, action="append", default=[], help="a shared script to load first (repeatable)")
    a = ap.parse_args()
    out = build(a.source, a.out or a.source.with_suffix(".html"), a.fragment, a.include)
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
