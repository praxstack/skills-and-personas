#!/usr/bin/env python3
"""Bundle notebook-styled pages into one self-contained HTML file.

No build tools and no network: CSS files are inlined with their fonts as
data URIs, and ES modules are joined into one inline module (single-line
imports dropped, `export` keywords stripped). Duplicate top-level names
across modules fail the build, so joining can't silently shadow anything.

Used by explorable/scripts/build.py and concept-animation/scripts/build.py,
and directly:

  python3 bundle.py --title "Why seasons happen" --css a.css --module b.js \
      --script lesson.js --body body.html -o out.html [--fragment]

--fragment leaves out <!doctype>, <html>, <head> and <body>, for hosts that
wrap the page themselves (Claude artifacts do).
"""

from __future__ import annotations

import argparse
import base64
import html
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
NOTEBOOK_CSS = ASSETS / "notebook.css"
INK_JS = ASSETS / "ink.js"
PEN_JS = ASSETS / "pen.js"
SOUND_JS = ASSETS / "sound.js"
PEN_SAMPLES_JS = ASSETS / "pen-samples.js"
BOARD_JS = ASSETS / "board.js"
# The notebook's modules in dependency order: put these before any engine.
NOTEBOOK_MODULES = [INK_JS, PEN_SAMPLES_JS, SOUND_JS, BOARD_JS, PEN_JS]

FONT_URL = re.compile(r"""url\(["']?([^"')]+\.woff2)["']?\)""")
IMPORT_LINE = re.compile(r"^\s*import\s[^;]*;\s*$", re.M)
EXPORT_KW = re.compile(r"^export\s+(?=(async\s+)?function|class|const|let|var)", re.M)
TOP_DECL = re.compile(r"^(?:export\s+)?(?:async\s+)?(?:function\*?|class|const|let|var)\s+([A-Za-z_$][\w$]*)", re.M)


def inline_css(path: Path) -> str:
    text = path.read_text()

    def repl(m: re.Match) -> str:
        font = (path.parent / m.group(1)).resolve()
        if not font.is_file():
            raise SystemExit(f"bundle: font not found: {font}")
        data = base64.b64encode(font.read_bytes()).decode()
        return f'url("data:font/woff2;base64,{data}")'

    return FONT_URL.sub(repl, text)


def join_modules(paths: list[Path]) -> str:
    seen: dict[str, Path] = {}
    parts = []
    for path in paths:
        src = path.read_text()
        for name in TOP_DECL.findall(src):
            if name in seen:
                raise SystemExit(f"bundle: '{name}' is declared in both {seen[name].name} and {path.name}")
            seen[name] = path
        src = IMPORT_LINE.sub("", src)
        src = EXPORT_KW.sub("", src)
        parts.append(f"// ---- {path.name} ----\n{src}")
    return "\n".join(parts)


def safe_script(js: str) -> str:
    # A literal "</script" inside inline JS would end the element early.
    return re.sub(r"</(script)", r"<\\/\1", js, flags=re.I)


def page(*, title: str, css: list[Path], modules: list[Path], scripts: list[Path] = (), body: str, fragment: bool = False,
         lang: str = "en", description: str = "") -> str:
    style = "\n".join(inline_css(p) for p in css)
    classic = "\n".join(f"<script>\n{safe_script(p.read_text())}\n</script>" for p in scripts)
    module = f'<script type="module">\n{safe_script(join_modules(modules))}\n</script>' if modules else ""
    head = (
        f"<title>{html.escape(title)}</title>\n"
        '<meta name="claude:viewport-fit-sides" content="cover">\n'
        + (f'<meta name="description" content="{html.escape(description)}">\n' if description else "")
        + f"<style>\n{style}\n</style>\n"
    )
    if fragment:
        return f"{head}{body}\n{classic}\n{module}\n"
    return (
        f'<!doctype html>\n<html lang="{lang}">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        f"{head}</head>\n<body>\n{body}\n{classic}\n{module}\n</body>\n</html>\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--title", required=True)
    ap.add_argument("--css", action="append", default=[], type=Path, help="extra CSS after notebook.css")
    ap.add_argument("--module", action="append", default=[], type=Path, help="ES modules after ink.js and pen.js")
    ap.add_argument("--script", action="append", default=[], type=Path, help="classic scripts, run before the modules")
    ap.add_argument("--body", type=Path, help="HTML for the body")
    ap.add_argument("--fragment", action="store_true")
    ap.add_argument("-o", "--out", type=Path, required=True)
    args = ap.parse_args()
    body = args.body.read_text() if args.body else '<main id="app"></main>'
    out = page(title=args.title, css=[NOTEBOOK_CSS, *args.css], modules=[*NOTEBOOK_MODULES, *args.module], scripts=args.script,
               body=body, fragment=args.fragment)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(out)
    print(f"wrote {args.out} ({len(out) // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
