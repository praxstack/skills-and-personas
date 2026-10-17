#!/usr/bin/env python3
"""Render diagram source to SVG, then frame it as an explained figure.

  python3 render.py flow.mmd -o flow.svg                    # just the SVG
  python3 render.py flow.mmd --page flow.html \\
      --claim "A cache answers repeat questions without asking the origin" \\
      --why "The origin is slow and far away; the cache is near and fast." \\
      --how "Check the cache first; only a miss goes to the origin, and its answer is stored." \\
      --look-for "the 'no' branch is the only path that reaches the origin"

Formats by extension: .mmd/.mermaid, .d2, .dot/.gv, .puml/.plantuml,
.vl.json (Vega-Lite), .bpmn, .excalidraw, .svg (already drawn).
Engines, in order: a local CLI if installed (mmdc, d2, dot, plantuml), then
Kroki (https://kroki.io, or $KROKI_URL for a self-hosted one). --offline
forbids the network. The notebook look is the default: Mermaid gets
look=handDrawn, D2 gets sketch mode, and the page uses the lesson-notebook
style. --plain turns the hand-drawn look off.
"""

from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "lesson-notebook" / "scripts"))
import bundle  # noqa: E402

KINDS = {
    ".mmd": "mermaid", ".mermaid": "mermaid", ".d2": "d2", ".dot": "graphviz", ".gv": "graphviz",
    ".puml": "plantuml", ".plantuml": "plantuml", ".bpmn": "bpmn", ".excalidraw": "excalidraw", ".svg": "svg",
}


def kind_of(path: Path) -> str:
    if path.name.endswith(".vl.json"):
        return "vegalite"
    k = KINDS.get(path.suffix.lower())
    if not k:
        raise SystemExit(f"don't know how to render {path.name}; use one of {', '.join(sorted(KINDS))} or .vl.json")
    return k


def hand_mermaid(src: str) -> str:
    if "%%{init" in src or "look:" in src:
        return src
    return '%%{init: {"look": "handDrawn", "theme": "neutral", "fontFamily": "Kalam, Segoe Print, cursive"}}%%\n' + src


def local_render(kind: str, src: str, hand: bool) -> str | None:
    with tempfile.TemporaryDirectory() as tmp:
        inp = Path(tmp) / "in"
        out = Path(tmp) / "out.svg"
        inp.write_text(src)
        cmd = None
        if kind == "graphviz" and shutil.which("dot"):
            cmd = ["dot", "-Tsvg", str(inp), "-o", str(out)]
        elif kind == "d2" and shutil.which("d2"):
            cmd = ["d2", *(["--sketch"] if hand else []), str(inp), str(out)]
        elif kind == "mermaid" and shutil.which("mmdc"):
            mmd = inp.with_suffix(".mmd")
            inp.rename(mmd)
            cmd = ["mmdc", "-i", str(mmd), "-o", str(out), "-b", "transparent"]
        elif kind == "plantuml" and shutil.which("plantuml"):
            res = subprocess.run(["plantuml", "-tsvg", "-pipe"], input=src, capture_output=True, text=True)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout
            print(f"local plantuml failed: {res.stderr.strip()[:300]}", file=sys.stderr)
            return None
        if not cmd:
            return None
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode or not out.exists():
            print(f"local {cmd[0]} failed: {(res.stderr or res.stdout).strip()[:300]}", file=sys.stderr)
            return None  # let Kroki try, unless --offline
        return out.read_text()


def kroki_render(kind: str, src: str, hand: bool) -> str:
    base = os.environ.get("KROKI_URL", "https://kroki.io").rstrip("/")
    url = f"{base}/{kind}/svg" + ("?sketch=true" if kind == "d2" and hand else "")
    req = urllib.request.Request(url, data=src.encode(), headers={"Content-Type": "text/plain", "User-Agent": "teacher-explain-diagram"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read().decode()
    except urllib.error.HTTPError as e:
        raise SystemExit(f"kroki said {e.code}: {e.read().decode(errors='replace')[:400]}")
    except urllib.error.URLError as e:
        raise SystemExit(f"couldn't reach {base} ({e.reason}). Install a local CLI or set KROKI_URL.")


def render(path: Path, *, hand: bool = True, offline: bool = False) -> tuple[str, str]:
    kind = kind_of(path)
    src = path.read_text()
    if kind == "svg":
        return src, "as drawn"
    if kind == "mermaid" and hand:
        src = hand_mermaid(src)
    svg = local_render(kind, src, hand)
    if svg:
        return svg, "local"
    if offline:
        raise SystemExit(f"no local renderer for {kind} and --offline is set")
    return kroki_render(kind, src, hand), "kroki"


# Elements that can run code, load a page or take input. They never belong in a figure.
BLOCKED_TAGS = {"script", "iframe", "frame", "frameset", "object", "embed", "applet", "meta", "link", "base",
                "form", "input", "button", "textarea", "select", "handler", "listener"}
URL_ATTRS = {"href", "xlink:href", "src", "action", "formaction", "data", "poster", "background",
             "to", "from", "by", "values"}
ANIMATE_TAGS = {"set", "animate", "animatetransform", "animatemotion"}
TAG_RE = re.compile(r"""<(/?)([A-Za-z][\w:.-]*)((?:[^<>"']|"[^"]*"|'[^']*')*)>|<""")
ATTR_RE = re.compile(r"""([^\s=/>"']+)(?:\s*=\s*("[^"]*"|'[^']*'|[^\s>]+))?""")


_EXTERNAL_URL = r"url\(\s*(?![\"']?\s*#)[^)]*\)"


def clean_css(css: str) -> str | None:
    """CSS with every outside fetch removed, or None when it hides one we can't strip.

    Inline SVG styles apply to the whole page, and @import, url() and image-set()
    would let a figure make requests of its own. In-figure references (url(#id))
    stay. CSS escapes and HTML entities are decoded only to check what is left.
    """
    css = re.sub(r"@import\b[^;]*;?", "", css, flags=re.I)
    css = re.sub(_EXTERNAL_URL, "none", css, flags=re.I)
    seen = html.unescape(css)
    seen = re.sub(r"\\([0-9a-fA-F]{1,6})\s?", lambda m: chr(min(int(m.group(1), 16), 0x10FFFF)), seen)
    seen = re.sub(r"\\(.)", r"\1", seen, flags=re.S)
    if re.search(r"@import|image-set\(|expression\(|" + _EXTERNAL_URL, seen, flags=re.I):
        return None
    return css


def _unsafe_url(value: str) -> bool:
    v = re.sub(r"[\x00-\x20]", "", html.unescape(value)).lower()
    if v.startswith("data:"):
        return not re.match(r"data:image/(png|jpe?g|gif|webp|avif)[;,]", v)
    return v.startswith(("javascript:", "vbscript:"))


def _clean_tag(m: re.Match) -> str:
    if m.group(2) is None:
        return "&lt;"  # a "<" that doesn't start a well-formed tag stays text, whatever a browser would make of it
    close, name, rest = m.group(1), m.group(2), m.group(3)
    low = name.lower()
    if low in BLOCKED_TAGS:
        return ""
    if close:
        return f"</{name}>"
    kept = []
    for a in ATTR_RE.finditer(rest):
        an, av = a.group(1), a.group(2)
        aln = an.lower()
        raw = av[1:-1] if av and av[0] in "\"'" else (av or "")
        if aln.startswith("on"):
            continue
        if low in ANIMATE_TAGS and aln == "attributename" and html.unescape(raw).strip().lower().endswith("href"):
            return ""  # <set attributeName="href" to="javascript:..."> swaps in a link at run time
        if aln in URL_ATTRS and _unsafe_url(raw):
            continue
        if aln == "style":
            css = clean_css(html.unescape(raw))
            if css is None:
                continue
            kept.append(f' style="{html.escape(css, quote=True)}"')
            continue
        # Re-quote every value, so the browser reads exactly the attributes kept here.
        kept.append(f" {an}" if av is None else f' {an}="{raw.replace(chr(34), "&quot;")}"')
    end = "/" if rest.rstrip().endswith("/") else ""
    return f"<{name}{''.join(kept)}{end}>"


def sanitize_svg(svg: str) -> str:
    """Strip anything in an SVG that can run code before it is inlined into a lesson page.

    Rendered and hand-supplied SVGs are both untrusted: drop comments, script-like
    elements with their content, every on* handler (any quoting), executable URL
    schemes (entity-encoded too) and animations that rewrite a link.
    """
    svg = re.sub(r"<!--.*?(-->|$)", "", svg, flags=re.S)
    # Inline SVG has no raw-text elements: a "<" in CDATA or in CSS would be read
    # as a tag. Turn CDATA into escaped text and escape "<" inside <style>.
    svg = re.sub(r"<!\[CDATA\[(.*?)(\]\]>|$)", lambda m: html.escape(m.group(1), quote=False), svg, flags=re.S)
    svg = re.sub(r"(<style\b(?:[^>\"']|\"[^\"]*\"|'[^']*')*>)(.*?)(?=</style\s*>|$)",
                 lambda m: m.group(1) + html.escape(clean_css(html.unescape(m.group(2))) or "", quote=False), svg, flags=re.S | re.I)
    for tag in ("script", "iframe", "object", "applet", "form", "textarea", "select", "button"):
        svg = re.sub(rf"<{tag}\b(?:[^>\"']|\"[^\"]*\"|'[^']*')*?/>", "", svg, flags=re.I)
        svg = re.sub(rf"<{tag}\b.*?</{tag}\s*>", "", svg, flags=re.S | re.I)
    return TAG_RE.sub(_clean_tag, svg)


def clean_svg(svg: str, title: str) -> str:
    svg = re.sub(r"<\?xml[^>]*>|<!DOCTYPE[^>]*>", "", svg).strip()
    svg = sanitize_svg(svg)
    # Give the figure a text alternative and let it scale with its column.
    svg = re.sub(r"<svg\b", f'<svg role="img" aria-label="{html.escape(title, quote=True)}"', svg, count=1)
    root = re.match(r"\s*<svg\b[^>]*>", svg)
    if root:
        head = re.sub(r'\s(width|height)="[^"]*"', "", root.group(0))
        svg = head + svg[root.end():]
    return svg


PAGE_CSS = """
.xd { max-width: 60rem; margin: 0 auto; padding-block: var(--s-6) var(--s-7); display: grid; gap: var(--s-5); }
.xd-claim { font-size: var(--text-h2); }
.xd-figure { margin: 0; padding: var(--s-4); overflow-x: auto; }
.xd-figure svg { display: block; width: 100%; height: auto; min-width: 32rem; max-width: 100%; }
@media (max-width: 600px) { .xd-figure svg { min-width: 0; } }
.xd.is-hand .xd-figure svg text, .xd.is-hand .xd-figure svg .nodeLabel, .xd.is-hand .xd-figure svg .edgeLabel { font-family: var(--font-hand) !important; }
.xd-grid { display: grid; gap: var(--s-5); grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr)); }
.xd-grid section { display: grid; gap: var(--s-2); align-content: start; }
.xd-look { display: flex; flex-wrap: wrap; gap: var(--s-2) var(--s-3); align-items: baseline; }
.xd-steps { margin: 0; padding-left: 1.4em; display: grid; gap: var(--s-2); }
.xd-src { color: var(--ink-2); font-size: var(--text-small); }
"""


def page(svg: str, *, claim: str, why: str, how: str, look_for: str, steps: list[str], hand: bool, source: str, fragment: bool) -> str:
    esc = html.escape
    parts = [
        f'<main class="xd{" is-hand" if hand else ""}">',
        '<p class="nb-label">Explained figure</p>',
        f'<h1 class="xd-claim">{esc(claim)}</h1>',
        f'<figure class="xd-figure nb-sheet">{svg}</figure>',
    ]
    if look_for:
        parts.append(f'<p class="xd-look"><span class="nb-label">Look for</span> <span class="nb-hand">{esc(look_for)}</span></p>')
    cols = []
    if why:
        cols.append(f'<section><h2 class="nb-label">Why it works</h2><p>{esc(why)}</p></section>')
    if how:
        cols.append(f'<section><h2 class="nb-label">How it works</h2><p>{esc(how)}</p></section>')
    if steps:
        items = "".join(f"<li>{esc(s)}</li>" for s in steps)
        cols.append(f'<section><h2 class="nb-label">Follow it step by step</h2><ol class="xd-steps">{items}</ol></section>')
    if cols:
        parts.append(f'<div class="xd-grid">{"".join(cols)}</div>')
    parts.append(f'<p class="xd-src nb-print">Drawn from {esc(source)}.</p></main>')
    with tempfile.NamedTemporaryFile("w", suffix=".css", delete=False) as f:
        f.write(PAGE_CSS)
        extra = Path(f.name)
    try:
        return bundle.page(title=claim[:80], description=why[:200], css=[bundle.NOTEBOOK_CSS, extra], modules=[], body="\n".join(parts), fragment=fragment)
    finally:
        extra.unlink()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", type=Path)
    ap.add_argument("-o", "--out", type=Path, help="write the SVG here")
    ap.add_argument("--page", type=Path, help="write an explained-figure HTML page here")
    ap.add_argument("--claim", help="the one sentence the figure proves (required with --page)")
    ap.add_argument("--why", default="")
    ap.add_argument("--how", default="")
    ap.add_argument("--look-for", default="")
    ap.add_argument("--step", action="append", default=[], help="a numbered walk-through step (repeatable)")
    ap.add_argument("--plain", action="store_true", help="no hand-drawn look")
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--fragment", action="store_true")
    a = ap.parse_args()
    if not a.out and not a.page:
        ap.error("give -o for the SVG, --page for the explained page, or both")
    if a.page and not a.claim:
        ap.error("--page needs --claim: every figure has to say something")
    svg, engine = render(a.source, hand=not a.plain, offline=a.offline)
    if a.out:
        a.out.write_text(svg)
        print(f"wrote {a.out} ({engine})")
    if a.page:
        body = page(clean_svg(svg, a.claim), claim=a.claim, why=a.why, how=a.how, look_for=a.look_for, steps=a.step,
                    hand=not a.plain, source=f"{a.source.name} via {engine}", fragment=a.fragment)
        a.page.write_text(body)
        print(f"wrote {a.page} ({engine})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
