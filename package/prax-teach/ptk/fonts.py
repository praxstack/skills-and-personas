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


def load_tokens(path=TOKENS):
    """tokens.json with each theme's WP0 colour names (paper, blue, ...) filled in from `aliases`."""
    tk = json.loads(path.read_text())
    for theme in tk["themes"].values():
        for old, role in tk.get("aliases", {}).items():
            theme.setdefault(old, theme[role])
    return tk


@lru_cache(maxsize=1)
def tokens():
    return load_tokens()


@lru_cache(maxsize=8)
def _font(key):
    from fontTools.ttLib import TTFont
    spec = tokens()["fonts"][key]
    return TTFont(str(host.FONTS_DIR / spec["file"]))


@lru_cache(maxsize=64)
def _metrics(key, wght=None, opsz=None):
    """cmap, advance widths and units per em. For a variable font, the advances of the instance the
    browser draws: the given weight, and (auto optical sizing) opsz equal to the font size in px, so a
    wrapped line fits where the browser wraps it."""
    f = _font(key)
    pins = {}
    if "fvar" in f:
        axes = {a.axisTag: a for a in f["fvar"].axes}
        for tag, val in (("wght", wght), ("opsz", opsz)):
            if val is not None and tag in axes:
                pins[tag] = min(max(float(val), axes[tag].minValue), axes[tag].maxValue)
    if pins:
        from fontTools.ttLib import TTFont
        from fontTools.varLib import instancer
        f = instancer.instantiateVariableFont(TTFont(str(host.FONTS_DIR / tokens()["fonts"][key]["file"])), pins,
                                              inplace=False)
    cmap = f.getBestCmap()
    hmtx = f["hmtx"].metrics
    upm = f["head"].unitsPerEm
    return cmap, hmtx, upm


def width(key, size, s, bold=False, weight=None):
    """Advance width of s at size px. weight measures that instance of a variable font; bold (no weight)
    keeps the WP0 rule: default instance plus 4%, a safe overestimate."""
    opsz = round(float(size)) if weight is not None else None
    cmap, hmtx, upm = _metrics(key, weight, opsz)
    total = 0
    for ch in s:
        g = cmap.get(ord(ch))
        total += hmtx[g][0] if g in hmtx else upm * 0.6
    w = total * size / upm
    return w * 1.04 if bold and weight is None else w


def wrap(key, size, s, max_w, bold=False, weight=None):
    words, lines, cur = s.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if cur and width(key, size, trial, bold, weight) > max_w:
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


FAMILY = {"serif": "'Source Serif 4'", "serif_italic": "'Source Serif 4'", "sans": "'Nunito Sans'",
          "mono": "'JetBrains Mono'", "hand": "'Caveat'"}
