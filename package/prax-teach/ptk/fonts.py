"""Bundled OFL fonts: text measurement for layout, per-artifact subsetting, @font-face CSS.

Only assets/fonts/*.woff2 are ever used (AC-3.2). Measurement reads advance widths
from the font itself, so wrapped lines fit before the browser gate measures them again.
"""
import base64
import io
import json
from functools import lru_cache

from . import host

TOKENS = host.PKG / "ptk" / "templates" / "tokens.json"


@lru_cache(maxsize=1)
def tokens():
    return json.loads(TOKENS.read_text())


@lru_cache(maxsize=8)
def _font(key):
    from fontTools.ttLib import TTFont
    spec = tokens()["fonts"][key]
    return TTFont(str(host.FONTS_DIR / spec["file"]))


@lru_cache(maxsize=8)
def _metrics(key):
    f = _font(key)
    cmap = f.getBestCmap()
    hmtx = f["hmtx"].metrics
    upm = f["head"].unitsPerEm
    return cmap, hmtx, upm


def width(key, size, s, bold=False):
    """Advance width of s at size px (default instance; bold adds 4%, a safe overestimate)."""
    cmap, hmtx, upm = _metrics(key)
    total = 0
    for ch in s:
        g = cmap.get(ord(ch))
        total += hmtx[g][0] if g in hmtx else upm * 0.6
    w = total * size / upm
    return w * 1.04 if bold else w


def wrap(key, size, s, max_w, bold=False):
    words, lines, cur = s.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if cur and width(key, size, trial, bold) > max_w:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def wrap_at(key, size, s, max_w, sep):
    """Greedy wrap that may break after `sep` (for paths) as well as at spaces."""
    import re
    parts = re.findall(r"[^ " + re.escape(sep) + r"]*(?:" + re.escape(sep) + r"| |$)", s)
    lines, cur = [], ""
    for part in [p for p in parts if p]:
        if cur and width(key, size, (cur + part).rstrip()) > max_w:
            lines.append(cur.rstrip())
            cur = part
        else:
            cur += part
    if cur.strip():
        lines.append(cur.rstrip())
    return lines


def subset_woff2(key, text):
    from fontTools import subset
    from fontTools.ttLib import TTFont
    f = TTFont(str(host.FONTS_DIR / tokens()["fonts"][key]["file"]), recalcTimestamp=False)  # reproducible bytes
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["*"]
    opts.name_IDs = ["*"]
    opts.notdef_outline = True
    sub = subset.Subsetter(options=opts)
    sub.populate(text=text + "0123456789 ")
    sub.subset(f)
    buf = io.BytesIO()
    f.flavor = "woff2"
    f.save(buf)
    return buf.getvalue()


def face_css(text_by_key):
    """@font-face rules with data: URIs holding only the glyphs this artifact uses."""
    rules = []
    for key, text in text_by_key.items():
        spec = tokens()["fonts"][key]
        data = base64.b64encode(subset_woff2(key, text)).decode()
        rules.append(f"@font-face{{font-family:'{spec['family']}';src:url(data:font/woff2;base64,{data}) format('woff2');"
                     f"font-weight:{spec['weight']};font-style:{spec['style']};font-display:block}}")
    return "".join(rules)


def full_face_css(keys):
    rules = []
    for key in keys:
        spec = tokens()["fonts"][key]
        data = base64.b64encode((host.FONTS_DIR / spec["file"]).read_bytes()).decode()
        rules.append(f"@font-face{{font-family:'{spec['family']}';src:url(data:font/woff2;base64,{data}) format('woff2');"
                     f"font-weight:{spec['weight']};font-style:{spec['style']};font-display:block}}")
    return "".join(rules)


FAMILY = {"serif": "'Source Serif 4'", "mono": "'JetBrains Mono'", "hand": "'Caveat'"}
