#!/usr/bin/env python3
"""Embed a portable reading-theme picker in reviewed authored HTML.

This is an injector, not a sanitizer. It neither executes authored code nor
loads/inlines SVG, images or other references. Existing CSP is preserved;
hosts that block inline CSS/scripts continue to block the picker.
"""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re

ASSETS = Path(__file__).resolve().parents[1] / "assets" / "reading-themes"
START = "<!-- reading-themes:start -->"
END = "<!-- reading-themes:end -->"
BLOCK = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)


class _Head(HTMLParser):
    def __init__(self, document: str):
        super().__init__(convert_charrefs=False)
        self.lines = document.splitlines(keepends=True)
        self.head = None
        self.html = None
        self.metadata_end = 0
        self.first_content = None

    def handle_data(self, data):
        content = data.lstrip("\ufeff \t\r\n\f")
        if self.first_content is None and content:
            line, col = self.getpos()
            self.first_content = (sum(map(len, self.lines[:line - 1])) + col
                                  + len(data) - len(content))

    def handle_starttag(self, tag, attrs):
        if self.first_content is None:
            line, col = self.getpos()
            self.first_content = sum(map(len, self.lines[:line - 1])) + col
        values = dict(attrs)
        if tag == "meta" and ("charset" in values or
                values.get("http-equiv", "").lower() == "content-security-policy"):
            line, col = self.getpos()
            self.metadata_end = max(self.metadata_end,
                sum(map(len, self.lines[:line - 1])) + col + len(self.get_starttag_text()))
        if tag in ("head", "html") and getattr(self, tag) is None:
            line, col = self.getpos()
            setattr(self, tag, sum(map(len, self.lines[:line - 1])) + col + len(self.get_starttag_text()))


def _palette_css(palettes: list[dict]) -> str:
    rules = []
    for p in palettes:
        if not re.fullmatch(r"[a-z]+", p["id"]):
            raise ValueError("Unsafe palette ID")
        tokens = {key: p[key] for key in ("bg", "panel", "ink", "muted", "accent", "border")}
        tokens["blue"] = "#adc7e6" if p["group"] == "Night" else "#9ecbff"
        if any(not re.fullmatch(r"#[0-9a-fA-F]{6}", color) for color in tokens.values()):
            raise ValueError("Palette colors must be six-digit hex")
        body = ";".join(f"--rt-{key}:{color} !important" for key, color in tokens.items())
        rules.append(f':root[data-reading-theme="{p["id"]}"]{{{body}}}')
    return "\n".join(rules)


def embed_reading_themes(document: str) -> str:
    """Return reviewed authored HTML with one early, self-contained theme block.

    Re-injection replaces only our marked block. No references are fetched and
    no existing policies, scripts, media, geometry or content are rewritten.
    """
    document = BLOCK.sub("", document)
    data = json.loads((ASSETS / "themes.json").read_text(encoding="utf-8"))
    encoded = json.dumps(data, ensure_ascii=True, separators=(",", ":")).replace("<", "\\u003c")
    css = _palette_css(data["palettes"]) + "\n" + (ASSETS / "themes.css").read_text(encoding="utf-8")
    js = (ASSETS / "themes.js").read_text(encoding="utf-8").replace("</script", "<\\/script")
    block = (START + '\n<style id="reading-themes-style">\n' + css + '</style>\n'
             + '<script id="reading-themes-data" type="application/json">' + encoded + '</script>\n'
             + '<script id="reading-themes-script">\n' + js + '</script>\n' + END)
    parser = _Head(document)
    parser.feed(document)
    if parser.head is not None:
        position = max(parser.head, parser.metadata_end)
        return document[:position] + block + document[position:]
    # A headless document can omit both start tags while retaining its doctype.
    # Insert after the leading prolog, before actual content, to preserve mode.
    position = max(parser.html or 0, parser.metadata_end,
                   parser.first_content if parser.first_content is not None else len(document))
    return document[:position] + "<head>" + block + "</head>" + document[position:]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", required=True, type=Path)
    args = parser.parse_args()
    result = embed_reading_themes(args.input.read_text(encoding="utf-8"))
    args.output.write_text(result, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
