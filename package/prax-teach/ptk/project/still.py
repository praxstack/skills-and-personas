r"""Still projector: a code-trace figure as SVG, wide (1200) and portrait (400), light and dark, plus 2x PNG.

Wide wireframe (viewBox 1200 x H), both themes:
+--------------------------------------------------------------------------+
| C · SWITCH STATEMENT                                    kicker           |
| <lesson title>                                          display          |
| <figure.title_claim>                                    body, wrapped    |
|--------------------------------------------------------------------------|
| THE PROGRAM                           fallthrough.c                      |
| ┌──────────────────────────────────────────┐   notes (note role), each   |
| │ 4  int n = 2;              ●             │   at the line it explains   |
| │ 5  switch (n) {            ●─╮           │   — c.match                 |
| │ 6    case 1:               │ │  skipped  │   — c.labels                |
| │ 8    case 2:               ◀─╯ enters    │   — c.break                 |
| │ 9      puts("two");        ●  [no break] │                             |
| │12      break;              ●─╮ leaves    │                             |
| │16  puts("done");           ◀─╯           │                             |
| └──────────────────────────────────────────┘  data-key="code" / "note"  |
| OUTPUT          │ <compare claim>                                        |
| 1 two           │ ┌ with_break.c ─────────┐   1 two                      |
| 2 three         │ │ 8 case 2: ... 10 break│   2 done                     |
| 3 done          │ │ ... 17 puts("done")   │                              |
|  data-key=output│ └───────────────────────┘   data-key="compare"         |
| <caption claims>                                                         |
| provenance · source link                                                 |
+--------------------------------------------------------------------------+
Portrait (400 wide) stacks the same parts; notes become numbered badges listed under the code.

Mechanism, not metrics (D20.5): each output (a summary) sits next to the path that produced it; the
comparison program shows its own path, not only its output.

Sources: every value comes from facts (data-fact, inside a data-state container whose fact order the
values gate checks), every sentence from claims (data-claim) or templates/chrome.json (data-chrome),
code text is data-code with data-src-line, line numbers are data-label with data-line. Colours and type
come from tokens.json by role (references/STYLE.md); nothing here names a hex value or a family.
Math in a claim, written \( ... \), goes through MathJax tex2svg (node/tex2svg.mjs) into a scaled <g>.
"""
import hashlib
import json
import re
import shutil

from .. import errors, fonts, host, node, text
from . import mech
from . import path as rail
from ..text import esc

KEYWORDS = {"int", "switch", "case", "break", "return", "void", "char", "default", "if", "else", "while", "for"}
MONO_ADV = 0.6  # advance width per em of the bundled mono font
MATH_RE = re.compile(r"\\\((.+?)\\\)", re.S)

LAYOUTS = {
    "wide": dict(W=1200, X0=64, X1=1136, kicker=13, title=44, dek=19, code=17, code_lh=31, gutter=84, code_w=680,
                 code_w_side=600,
                 note=23, out=26, out_gap=16, label=12.5, caption=20, foot=12.5, tag=12.5, mini=15, mini_lh=26,
                 mini_gutter=78, col_gap=40, out_w=300),
    "portrait": dict(W=400, X0=16, X1=384, kicker=12, title=30, dek=16, code=13, code_lh=23, gutter=58, code_w=368,
                     note=19, out=21, out_gap=12, label=12, caption=16.5, foot=12, tag=12, mini=12.5, mini_lh=21,
                     mini_gutter=60, col_gap=0, out_w=368),
}


# ---------------------------------------------------------------- SVG writer

class Svg:
    def __init__(self, theme_name, tokens):
        self.t = tokens["themes"][theme_name]
        self.ty = self.t["type"]
        self.frame = self.t["frame"]
        self.theme = theme_name
        self.els = []
        self.chars = {k: "" for k in tokens["fonts"]}

    def role(self, name, size):
        """(font key, px, weight, caps, spacing) of a type role at a layout size."""
        r = self.ty[name]
        return r["font"], round(size * r.get("scale", 1), 2), r.get("weight", 400), r.get("caps", False), \
            r.get("spacing", 0)

    def raw(self, s):
        self.els.append(s)

    def open(self, **attrs):
        self.els.append("<g " + " ".join(f'{k.replace("_", "-")}="{esc(v)}"' for k, v in attrs.items()) + ">")

    def close(self):
        self.els.append("</g>")

    def rect(self, x, y, w, h, fill, rx=0, rid=None, stroke=None, sw=1, role=None):
        a = f' id="{rid}"' if rid else ""
        r = f' data-role="{role}"' if role else ""
        s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        self.els.append(f'<rect{a}{r} x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
                        f'fill="{fill}"{s}/>')

    def line(self, x1, y1, x2, y2, color, sw=1.5, role="rule"):
        self.els.append(f'<line data-role="{role}" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                        f'stroke="{color}" stroke-width="{sw}" stroke-linecap="round"/>')

    def path(self, d, color, sw=2.0, role="path", marker=False):
        m = ' marker-end="url(#arrow)"' if marker else ""
        self.els.append(f'<path data-role="{role}" d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" '
                        f'stroke-linecap="round" stroke-linejoin="round"{m}/>')

    def circle(self, cx, cy, r, fill, role="path"):
        self.els.append(f'<circle data-role="{role}" cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{fill}"/>')

    def text(self, x, y, s, font, size, color, src, weight=400, anchor="start", inside=None, ocr=None,
             spacing=0, raw=None, ocr_group=None, tone=None, extra=None):
        """One text element. src is ('claim', id) | ('chrome', key) | ('fact', id) | ('code', pid) | ('label', name)."""
        self.chars[font] += s
        attrs = [f'x="{x:.1f}"', f'y="{y:.1f}"', f'font-family="{fonts.FAMILY[font]}"', f'font-size="{size}"',
                 f'fill="{color}"', f'data-{src[0]}="{esc(src[1])}"']
        if weight != 400:
            attrs.append(f'font-weight="{weight}"')
        if font == "serif_italic":
            attrs.append('font-style="italic"')
        if anchor != "start":
            attrs.append(f'text-anchor="{anchor}"')
        if inside:
            attrs.append(f'data-in="{inside}"')
        if ocr is not None:
            attrs.append(f'data-ocr="{esc(ocr)}"')
        if ocr_group:
            attrs.append(f'data-ocr-group="{esc(ocr_group)}"')
        if spacing:
            attrs.append(f'letter-spacing="{spacing}"')
        if tone:
            attrs.append(f'data-tone="{tone}"')
        for k, v in (extra or {}).items():
            attrs.append(f'{k}="{esc(v)}"')
        self.els.append(f'<text {" ".join(attrs)}>{raw if raw is not None else esc(s)}</text>')

    def mark(self):
        return len(self.els)

    def merge(self, i0):
        """Fold the <text> lines written since mark() into one <text> of <tspan> lines, so a wrapped
        sentence stays one element (one claim mapping, one overflow box)."""
        parts = self.els[i0:]
        if len(parts) < 2 or not all(p.startswith("<text ") for p in parts):
            return
        rx = re.compile(r'<text (.*?)>(.*)</text>$', re.S)
        first_attrs = rx.match(parts[0]).group(1)
        spans = []
        for p in parts:
            a, inner = rx.match(p).groups()
            x = re.search(r'\bx="([^"]+)"', a).group(1)
            y = re.search(r'\by="([^"]+)"', a).group(1)
            spans.append(f'<tspan x="{x}" y="{y}">{inner}</tspan>')
        self.els[i0:] = [f'<text {first_attrs}>{"".join(spans)}</text>']


# ---------------------------------------------------------------- math (AC-3.5)

def tex_segments(s):
    return MATH_RE.findall(s)


def render_math(texs, lesson_sha=None):
    """{tex: MathJax result} for every distinct TeX string, in one node process. Raises ModelSchemaError
    on TeX that MathJax rejects (the claim must be fixed, not the figure)."""
    texs = sorted(set(texs))
    if not texs:
        return {}
    work = host.make_tmp("tex2svg-")
    items = [{"id": f"m{i}", "tex": t, "display": False} for i, t in enumerate(texs)]
    try:
        (work / "items.json").write_text(json.dumps(items))
        node.run_script("tex2svg.mjs", [work / "items.json", work / "out.json"], timeout=300,
                        lesson_sha256=lesson_sha)
        res = {r["id"]: r for r in json.loads((work / "out.json").read_text())}
    finally:
        shutil.rmtree(work, ignore_errors=True)
    out = {}
    for it in items:
        r = res[it["id"]]
        if not r["ok"]:
            raise errors.ModelSchemaError(f"MathJax rejected TeX in a claim: {r['error']}", tex_sha256=_sha(it["tex"]))
        out[it["tex"]] = r
    return out


def _sha(s):
    return hashlib.sha256(s.encode()).hexdigest()


TEX_TEXT = {r"\times": "×", r"\cdot": "·", r"\le": "≤", r"\leq": "≤", r"\ge": "≥", r"\geq": "≥", r"\ne": "≠",
            r"\neq": "≠", r"\to": "→", r"\rightarrow": "→", r"\ldots": "…", r"\dots": "…", r"\cdots": "…",
            r"\sum": "sum", r"\prod": "product", r"\pm": "±", r"\infty": "infinity", r"\alpha": "α", r"\beta": "β",
            r"\lambda": "λ", r"\sigma": "σ", r"\pi": "π", r"\theta": "θ", r"\mu": "μ", r"\Delta": "Δ",
            r"\left": "", r"\right": "", r"\,": " ", r"\;": " ", r"\quad": " ", r"\!": "", r"\%": "%",
            r"\{": "{", r"\}": "}", r"\mid": "|", r"\lfloor": "⌊", r"\rfloor": "⌋", r"\lceil": "⌈", r"\rceil": "⌉",
            r"\log": "log", r"\max": "max", r"\min": "min", r"\bmod": "mod", r"\mod": "mod"}


def tex_to_text(tex):
    """A plain reading of TeX for alt text (no raw TeX may reach the output). Unknown macros are a model
    error rather than a guess."""
    s = tex
    for _ in range(8):
        s2 = re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"(\1)/(\2)", s)
        s2 = re.sub(r"\\(?:text|mathrm|mathit|mathbf|operatorname)\{([^{}]*)\}", r"\1", s2)
        s2 = re.sub(r"\\sqrt\{([^{}]*)\}", r"√(\1)", s2)
        if s2 == s:
            break
        s = s2
    for k in sorted(TEX_TEXT, key=len, reverse=True):
        s = re.sub(re.escape(k) + (r"(?![A-Za-z])" if k[-1].isalpha() else ""), TEX_TEXT[k], s)
    left = re.findall(r"\\[A-Za-z]+|\\.", s)
    if left:
        raise errors.ModelSchemaError(f"TeX has no alt-text reading for {sorted(set(left))}", macros=sorted(set(left)))
    s = re.sub(r"\^\{([^{}]*)\}", r"^(\1)", s)
    s = re.sub(r"_\{([^{}]*)\}", r"_(\1)", s)
    s = s.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", s).strip()


def plain(s):
    """A claim's text with each \\( tex \\) replaced by its plain reading."""
    return MATH_RE.sub(lambda m: tex_to_text(m.group(1)), s)


def _x_height(font):
    f = fonts._font(font)
    os2 = f["OS/2"]
    return (getattr(os2, "sxHeight", 0) or 0.48 * f["head"].unitsPerEm) / f["head"].unitsPerEm


def _tokens(s):
    """[(kind, value, space_before)] words and math, from a claim text."""
    out, pos = [], 0
    for m in list(MATH_RE.finditer(s)) + [None]:
        chunk = s[pos:m.start()] if m else s[pos:]
        for w in re.finditer(r"\S+", chunk):
            out.append(("t", w.group(0), w.start() > 0 or bool(out) and chunk[:1].isspace()))
        if m:
            out.append(("m", m.group(1), m.start() > 0 and s[m.start() - 1].isspace()))
            pos = m.end()
    return out


class Flow:
    """Wrapped prose that may hold inline math: one <text> of <tspan> runs plus one scaled <g> per formula."""

    def __init__(self, svg, math):
        self.svg = svg
        self.math = math or {}

    def width_of(self, tok, font, size, weight):
        kind, val, _sp = tok
        if kind == "t":
            return fonts.width(font, size, val, weight=weight)
        return self.math[val]["width_ex"] * size * _x_height(font)

    def lines(self, s, font, size, max_w, weight=400):
        if not MATH_RE.search(s):
            return [[("t", ln, False)] for ln in fonts.wrap(font, size, s, max_w, weight=weight)]
        space = fonts.width(font, size, " ", weight=weight)
        lines, cur, cur_w = [], [], 0.0
        for tok in _tokens(s):
            w = self.width_of(tok, font, size, weight) + (space if cur and tok[2] else 0)
            if cur and cur_w + w > max_w:
                lines.append(cur)
                cur, cur_w = [], 0.0
                w = self.width_of(tok, font, size, weight)
            cur.append(tok)
            cur_w += w
        if cur:
            lines.append(cur)
        return lines

    def emit(self, x, y, s, font, size, lh, color, src, max_w, weight=400, anchor="start", inside=None, tone=None):
        """Write the wrapped text; returns the y after the last line."""
        svg = self.svg
        lines = self.lines(s, font, size, max_w, weight)
        if all(t[0] == "t" for ln in lines for t in ln):
            m0 = svg.mark()
            for ln in lines:
                svg.text(x, y, ln[0][1], font, size, color, src, weight=weight, anchor=anchor, inside=inside,
                         tone=tone)
                y += lh
            svg.merge(m0)
            return y
        space = fonts.width(font, size, " ", weight=weight)
        exh = size * _x_height(font)
        spans, formulas = [], []
        for ln in lines:
            cx, run, run_x = x, [], x
            for k, tok in enumerate(ln):
                gap = space if k and tok[2] else 0
                if tok[0] == "t":
                    if not run:
                        run_x = cx + gap
                        cx += gap
                    else:
                        run.append(" " if gap else "")
                        cx += gap
                    run.append(tok[1])
                    svg.chars[font] += tok[1] + " "
                    cx += fonts.width(font, size, tok[1], weight=weight)
                else:
                    if run:
                        spans.append(f'<tspan x="{run_x:.1f}" y="{y:.1f}">{esc("".join(run))}</tspan>')
                        run = []
                    cx += gap
                    r = self.math[tok[1]]
                    w, h = r["width_ex"] * exh, r["height_ex"] * exh
                    top = y - (r["height_ex"] + r["valign_ex"]) * exh
                    formulas.append((cx, top, w, h, tok[1], r["svg"]))
                    cx += w
            if run:
                spans.append(f'<tspan x="{run_x:.1f}" y="{y:.1f}">{esc("".join(run))}</tspan>')
            y += lh
        attrs = (f'font-family="{fonts.FAMILY[font]}" font-size="{size}" fill="{color}" '
                 f'data-{src[0]}="{esc(src[1])}"' + (f' font-weight="{weight}"' if weight != 400 else "")
                 + (' font-style="italic"' if font == "serif_italic" else "")
                 + (f' data-in="{inside}"' if inside else "") + (f' data-tone="{tone}"' if tone else ""))
        if spans:
            svg.raw(f'<text {attrs}>{"".join(spans)}</text>')
        for fx, ft, fw, fh, tex, body in formulas:
            # MathJax's <svg> becomes a <g> scaled into place: one root <svg> per figure keeps every
            # consumer (PNG export, measurement) unambiguous.
            n = len([e for e in svg.els if "data-tex-sha256" in e])
            vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', body).group(1).split()]
            k = fw / vb[2]
            inner = re.sub(r"^<svg[^>]*>|</svg>$", "", body.strip())
            inner = inner.replace('xlink:href="', 'href="')
            inner = inner.replace('id="', f'id="f{n}-').replace('href="#', f'href="#f{n}-')
            svg.raw(f'<g data-{src[0]}="{esc(src[1])}" data-tex-sha256="{_sha(tex)}" data-math="mathjax-tex2svg" '
                    f'data-box="{fx:.1f} {ft:.1f} {fw:.2f} {fh:.2f}" color="{color}" fill="currentColor" '
                    f'stroke="currentColor" stroke-width="0" '
                    f'transform="translate({fx:.2f} {ft:.2f}) scale({k:.6f}) translate({-vb[0]:.1f} {-vb[1]:.1f})">'
                    f'{inner}</g>')
        return y


# ---------------------------------------------------------------- code panel

def _code_spans(line_text, t):
    """Escape a code line into tspans: keywords bold, string literals soft."""
    out = []
    for tok in re.findall(r'"[^"]*"|[A-Za-z_]\w*|\s+|.', line_text):
        if tok.startswith('"'):
            out.append(f'<tspan fill="{t["ink_soft"]}">{esc(tok)}</tspan>')
        elif tok in KEYWORDS:
            out.append(f'<tspan font-weight="700">{esc(tok)}</tspan>')
        else:
            out.append(esc(tok))
    return "".join(out)


def code_panel(svg, lesson, pid, run, shown, x, y, w, size, lh, gutter, rid, ocr_group, tags_on, wide,
               badges=None, nested=False, arcs=True):
    """A program listing with its executed path. Returns (height, {line: baseline y}). A listing nested in
    a filled panel is inset on the ground colour with no border, so cards never sit inside cards."""
    t = svg.t
    src = lesson.program_source(pid).split("\n")
    pad = 20 if wide else 18  # keeps the first line number's OCR crop clear of the card's rounded corner
    h = pad * 2 + len(shown) * lh - lh * 0.25
    inset = nested and svg.frame["panel_fill"]
    svg.rect(x, y, w, h, t["ground"] if inset else t["surface"], rx=12 if wide else 10, rid=rid,
             stroke=t["rule"] if svg.frame["card_border"] and not inset else None, sw=1)
    rail_x = x + gutter - (12 if wide else 9)
    code_x = x + gutter + (8 if wide else 4)
    charw = size * MONO_ADV
    num_size = max(12, round(size - 3, 1))
    ys = {}
    base = y + pad + size * 0.8
    lo, hi = min(run), max(run)
    ends = {}
    for i, n in enumerate(shown):
        ly = base + i * lh
        ys[n] = ly
        s = src[n - 1]
        indent = len(s) - len(s.lstrip(" "))
        is_exec = n in run
        if is_exec and s.strip():
            svg.rect(code_x - 6 + indent * charw, ly - size * 0.95, len(s.strip()) * charw + 12, lh - 4,
                     t["highlight"], rx=5)
        svg.text(x + (32 if wide else 24), ly, str(n), "mono", num_size, t["faint"], ("label", "line-number"),
                 anchor="end", inside=rid, ocr=str(n), ocr_group=ocr_group, extra={"data-line": n})
        if s.strip():
            color = t["ink"] if is_exec or n < lo or n > hi else t["label"]
            svg.text(code_x + indent * charw, ly, s.strip(), "mono", size, color, ("code", pid), inside=rid,
                     raw=_code_spans(s.strip(), t), extra={"data-src-line": n})
            ends[n] = code_x + (indent + len(s.strip())) * charw
    # the path: dots on executed lines, straight runs, arcs with an arrowhead for jumps
    cy = lambda n: ys[n] - size * 0.33
    vis = [n for n in run if n in ys]
    # a recursive run passes the same lines again and again; its jump arcs only tangle (review round 17), so a
    # path that repeats lines is drawn as dots on the executed lines, and the stack strip carries the order
    for a, b, kind in (rail.segments(vis) if arcs and len(vis) == len(set(vis)) else []):
        if kind == "run":
            svg.line(rail_x, cy(a), rail_x, cy(b), t["note"], 2.5, role="path")
        else:
            bulge = rail_x - (20 if wide else 14)
            svg.path(f"M{rail_x:.1f},{cy(a):.1f} C{bulge:.1f},{cy(a):.1f} {bulge:.1f},{cy(b):.1f} "
                     f"{rail_x - 4:.1f},{cy(b):.1f}", t["note"], 2.5, marker=True)
    for n in vis:
        svg.circle(rail_x, cy(n), 4 if wide else 3, t["note"])
    # badges for notes (portrait), placed just after the code on their line
    for k, n in (badges or []):
        if n in ys:
            bx = ends.get(n, code_x) + 8
            svg.rect(bx, cy(n) - 10, 20, 20, t["note"], rx=10, rid=f"{rid}-badge{k}")
            svg.text(bx + 10, cy(n) + 4.5, str(k), "mono", 12, t["surface"], ("label", "note-badge"), weight=700,
                     anchor="middle", inside=f"{rid}-badge{k}")
            ends[n] = bx + 20
    # tags, right-aligned inside the card, only where they clear the code
    tfont, tsize, tweight, _c, _s = svg.role("tag", max(12, round(size * 0.74, 1)))
    tag_x = x + w - (14 if wide else 10)
    if tags_on:
        for n, key, tone in rail.tags(src, vis, shown):
            label = text.ui(key)
            if ends.get(n, code_x) + 14 > tag_x - fonts.width(tfont, tsize, label, weight=tweight):
                continue
            svg.text(tag_x, ys[n], label, tfont, tsize, t["note"] if tone == "path" else t["label"], ("chrome", key),
                     anchor="end", inside=rid, weight=tweight, tone="note" if tone == "path" else None)
    nb = rail.nobreak_after(src, vis)
    if nb and nb in ys:
        label = text.ui("no_break")
        pw = fonts.width(tfont, tsize, label, weight=700) + 18
        py = ys[nb] + lh * 0.5 - 1
        px = tag_x - pw
        svg.rect(px, py - tsize * 1.05, pw, tsize * 1.75, t["correction_tint"], rx=9, rid=f"{rid}-nobreak",
                 stroke=t["correction"], sw=1.2, role="pill")
        svg.text(px + pw / 2, py + tsize * 0.32, label, tfont, tsize, t["correction"], ("chrome", "no_break"),
                 weight=700, anchor="middle", inside=f"{rid}-nobreak", tone="correction")
    return h, ys


# ---------------------------------------------------------------- figure

def _label(svg, x, y, s, size, src, color=None, anchor="start", inside=None):
    font, px, weight, caps, spacing = svg.role("label", size)
    svg.text(x, y, s.upper() if caps else s, font, px, color or svg.t["label"], src, weight=weight,
             spacing=spacing, anchor=anchor, inside=inside)


def _panel(svg, x, y, w, h, rid):
    """A panel box: filled card (light) or an unfilled region (dark, Atlas-like); the rect is the
    container the overflow check measures either way."""
    t = svg.t
    fill = t["surface"] if svg.frame["panel_fill"] else "none"
    stroke = t["rule"] if svg.frame["card_border"] else None
    svg.rect(x, y, w, h, fill, rx=12, rid=rid, stroke=stroke, sw=1)


def _place_panels(svg, panels, heights):
    """Insert each panel's box before its content, now that the content's height is known (later
    insertions first, so earlier indexes stay valid)."""
    for (idx, x, y, w, rid), h in sorted(zip(panels, heights), key=lambda p: -p[0][0]):
        mark = svg.mark()
        _panel(svg, x, y, w, h, rid)
        box = svg.els.pop(mark)
        svg.els.insert(idx, box)


def _output_list(svg, g, x, y, fids, facts, rid, group, max_w=None):
    """Numbered output values (smaller when a value would not fit max_w). Returns the y after the list."""
    t = svg.t
    vfont, vsize, vweight, _c, _s = svg.role("value", g["out"])
    if max_w:
        widest = max((fonts.width(vfont, vsize, text.display(facts[f]), weight=vweight) for f in fids), default=0)
        if widest > max_w - 30:
            vsize = round(max(13.0, vsize * (max_w - 30) / widest), 2)
    for k, fid in enumerate(fids, 1):
        val = text.display(facts[fid])
        svg.text(x, y, str(k), "mono", max(14, g["label"]), t["faint"], ("label", "output-step"), inside=rid,
                 ocr=str(k), ocr_group=f"{group}-steps")
        svg.text(x + 28, y, val, vfont, vsize, t["value"], ("fact", fid), weight=vweight, inside=rid, ocr=val,
                 ocr_group=group, raw=text.tight_points(val))
        y += vsize + g["out_gap"]
    return y


def _notes(svg, flow, lesson, notes, x, y, w, g):
    """Numbered notes, each with the badge its line carries in the code card. Returns the y after them."""
    t = svg.t
    claims = lesson.by_id("claims")
    nfont, npx, nweight, _c, _s = svg.role("note", g["note"])
    nlh = npx * (1.35 if nfont == "hand" else 1.42)
    svg.open(data_key="note")
    y += npx * 0.9
    for k, note in enumerate(notes, 1):
        svg.rect(x, y - 15, 20, 20, t["note"], rx=10, rid=f"badge-n{k}")
        svg.text(x + 10, y - 0.5, str(k), "mono", 12, t["surface"], ("label", "note-badge"), weight=700,
                 anchor="middle", inside=f"badge-n{k}")
        y = flow.emit(x + 30, y, claims[note["claim"]]["text"], nfont, npx, nlh, t["note"],
                      ("claim", note["claim"]), w - 30, weight=nweight, tone="note") + 8
    svg.close()
    return y - nlh


def _out_size(g, n):
    """Output value size: a long output (six lines or more) uses smaller values so it fits beside the code."""
    return round(g["out"] * (0.78 if n >= 6 else 1), 2)


def _output_height(svg, g, lesson, state_id):
    n = len(lesson.state(state_id)["state"]["output"])
    _vf, vpx, _vw, _c, _s = svg.role("value", _out_size(g, n))
    top = (22 if svg.frame["panel_fill"] else 0) or 6
    return top + 30 + n * (vpx + g["out_gap"]) - g["out_gap"] + vpx * 0.3 + top


def _output_card(svg, g, lesson, state_id, x, y, w):
    """The output values of `state_id`, numbered, in a card (light) or an open panel (dark). Returns its height."""
    facts = lesson.by_id("facts")
    final = lesson.state(state_id)["state"]["output"]
    inset = 22 if svg.frame["panel_fill"] else 0
    top = inset or 6
    g = dict(g, out=_out_size(g, len(final)))
    _vf, vpx, _vw, _c, _s = svg.role("value", g["out"])
    svg.open(data_key="output", data_state=state_id)
    i_out = svg.mark()
    _label(svg, x + inset, y + top + 10, text.ui("output_label"), g["label"], ("chrome", "output_label"),
           inside="out-card")
    end = _output_list(svg, g, x + inset, y + top + 30 + vpx * 0.8, final, facts, "out-card", "out",
                       max_w=w - 2 * inset)
    svg.close()
    h = end - y - g["out_gap"] - vpx * 0.8 + vpx * 0.3 + top
    _place_panels(svg, [(i_out, x, y, w, "out-card")], [h])
    return h


def _compare(svg, flow, lesson, g, wide, cmp, X0, X1, y, code_w=None, col_x=None):
    """The comparison program: its claim, its listing with its own path, and its output. Returns the y after it."""
    t = svg.t
    claims = lesson.by_id("claims")
    facts = lesson.by_id("facts")
    inset = 22 if svg.frame["panel_fill"] else 0
    top = inset or 6
    _vf, vpx, _vw, _c, _s = svg.role("value", g["out"])
    ffont, fpx, _w, _c, _s = svg.role("foot", g["label"])
    cstate_id = cmp["state"]
    cst = lesson.state(cstate_id)["state"]
    crun = cst.get("path", [])
    csrc = lesson.program_source(cmp["program"]).split("\n")
    cfirst = rail.enter_line(csrc, crun) or rail.listing(lesson, cmp["program"])[0]
    # every line the comparison adds is on screen, with the two lines above it for context (round 18: the
    # break added after case 1 sat above the listing, so the learner never saw it)
    import difflib
    base_src = lesson.program_source(lesson.data["figure"]["program"]).split("\n")
    added = [j + 1 for op, _i1, _i2, j1, j2 in difflib.SequenceMatcher(a=base_src, b=csrc, autojunk=False).get_opcodes()
             if op in ("insert", "replace") for j in range(j1, j2)]
    cfirst = max(1, min([cfirst] + [n - 2 for n in added]))
    cshown = list(range(cfirst, max(crun) + 1))
    if svg.frame["panel_divider"]:
        svg.line(X0, y - 14, X1, y - 14, t["rule"], 1)
    cw = X1 - X0
    bfont, bpx, bweight, _c, _s = svg.role("body", g["dek"])
    svg.open(data_key="compare", data_state=cstate_id)
    i_cmp = svg.mark()
    yy = flow.emit(X0 + inset, y + top + bpx * 0.95, claims[cmp["claim"]]["text"], bfont, bpx, bpx * 1.42,
                   t["ink_soft"], ("claim", cmp["claim"]), cw - 2 * inset, weight=bweight, inside="cmp-card")
    yy += 2
    fname2 = lesson.program(cmp["program"])["path"].split("/")[-1]
    svg.text(X0 + inset, yy, fname2, ffont, fpx, t["label"], ("label", "program-file"), inside="cmp-card")
    yy += 10
    mini_w = (code_w or 480) - 2 * inset if wide else cw - 2 * inset
    mh, _ys2 = code_panel(svg, lesson, cmp["program"], crun, cshown, X0 + inset, yy, mini_w, g["mini"],
                          g["mini_lh"], g["mini_gutter"], "cmp-code", "gutter-cmp", True, wide, nested=True)
    # wide: the output sits in the same column as the program's output above, so the two compare by eye
    lx, ly = (col_x or X0 + inset + mini_w + 40, yy + 18) if wide else (X0 + inset, yy + mh + 30)
    _label(svg, lx, ly, text.ui("output_label"), g["label"], ("chrome", "output_label"), inside="cmp-card")
    list_end = _output_list(svg, g, lx, ly + 20 + vpx * 0.8, cst["output"], facts, "cmp-card", "cmp")
    svg.close()
    cmp_h = max(yy + mh, list_end - g["out_gap"] - vpx * 0.8 + vpx * 0.3) + top - y
    _place_panels(svg, [(i_cmp, X0, y, cw, "cmp-card")], [cmp_h])
    return y + cmp_h


def _wrong_belief(svg, flow, lesson, g, wide, mid, X0, X1, y):
    """A callout: the wrong belief in the learner's words, then the claim that corrects it. Returns the y after it."""
    t = svg.t
    m = lesson.by_id("misconceptions")[mid]
    pad = 20 if wide else 14
    i0 = svg.mark()
    _label(svg, X0 + pad, y + pad + 10, text.ui("wrong_belief"), g["label"], ("chrome", "wrong_belief"),
           color=t["correction"], inside="belief-card")
    svg.els[-1] = svg.els[-1].replace("<text ", '<text data-tone="correction" ', 1)
    bfont, bpx, bweight, _c, _s = svg.role("body", g["dek"])
    yy = y + pad + 22 + bpx
    m0 = svg.mark()
    for ln in fonts.wrap(bfont, bpx, m["statement"], X1 - X0 - 2 * pad, weight=bweight):
        svg.text(X0 + pad, yy, ln, bfont, bpx, t["ink"], ("misconception", mid), weight=bweight, inside="belief-card")
        yy += bpx * 1.42
    svg.merge(m0)
    nfont, npx, nweight, _c, _s = svg.role("note", g["note"])
    yy = flow.emit(X0 + pad, yy + 6, lesson.claim(m["correction"])["text"], nfont, npx, npx * 1.38, t["note"],
                   ("claim", m["correction"]), X1 - X0 - 2 * pad, weight=nweight, inside="belief-card", tone="note")
    h = yy - npx * 1.38 + pad + 4 - y
    mark = svg.mark()
    svg.rect(X0, y, X1 - X0, h, t["correction_tint"], rx=12, rid="belief-card", stroke=t["correction"], sw=1.2,
             role="pill")
    box = svg.els.pop(mark)
    svg.els.insert(i0, box)
    return y + h


def build_svg(lesson, layout, theme, tokens, math=None):
    g = LAYOUTS[layout]
    wide = layout == "wide"
    svg = Svg(theme, tokens)
    t = svg.t
    flow = Flow(svg, math)
    fig = lesson.data["figure"]
    W, X0, X1 = g["W"], g["X0"], g["X1"]
    claims = lesson.by_id("claims")
    facts = lesson.by_id("facts")

    # ---------- header ----------
    y = 64 if wide else 42
    font, px, weight, caps, spacing = svg.role("kicker", g["kicker"])
    kicker = text.kicker(lesson)
    svg.text(X0, y, kicker.upper() if caps else kicker, font, px, t["note"], ("chrome", "kicker"), weight=weight,
             spacing=spacing, tone="note")
    font, px, weight, _c, _s = svg.role("display", g["title"])
    y += px * (1.12 if wide else 1.25) + 4
    m0 = svg.mark()
    for ln in fonts.wrap(font, px, lesson.data["title"], X1 - X0, weight=weight):
        svg.text(X0, y, ln, font, px, t["ink"], ("label", "title"), weight=weight)
        y += px * 1.2
    svg.merge(m0)
    font, px, weight, _c, _s = svg.role("body", g["dek"])
    y += 4
    y = flow.emit(X0, y, claims[fig["title_claim"]]["text"], font, px, px * 1.42, t["ink_soft"],
                  ("claim", fig["title_claim"]), X1 - X0, weight=weight)
    y += 8
    svg.line(X0, y, X1, y, t["rule"], 1)
    y += 34 if wide else 28

    # ---------- a hero panel spans the width above the program ----------
    panel = fig.get("panel")
    final_state = fig["states"][-1]
    if panel and panel["place"] == "hero":
        y += mech.draw(svg, lesson, final_state, X0, y, X1 - X0, layout, flow, states=fig["states"]) + (34 if wide else 26)
        svg.line(X0, y - 18, X1, y - 18, t["rule"], 1)
        y += 20 if wide else 16

    # ---------- the program ----------
    states = [lesson.state(s) for s in fig["states"]]
    run = rail.executed(s["state"].get("path", []) for s in states)
    src_lines = lesson.program_source(fig["program"]).split("\n")
    first, last = rail.listing(lesson, fig["program"])
    shown = list(range(first, (last if lesson.program(fig["program"]).get("show") else max(run)) + 1))
    prog = lesson.program(fig["program"])
    side = bool(panel and panel["place"] == "side")
    code_w = (g["code_w_side"] if side else g["code_w"]) if wide else g["code_w"]
    longest = max(len(src_lines[n - 1].rstrip()) for n in shown)
    csize = round(min(g["code"], (code_w - g["gutter"] - (24 if wide else 16)) / (longest * MONO_ADV)), 2)
    clh = round(g["code_lh"] * csize / g["code"], 2)
    _label(svg, X0, y, text.ui("code_label"), g["label"], ("chrome", "code_label"))
    fname = prog["path"].split("/")[-1]
    ffont, fpx, _w, _c, _s = svg.role("foot", g["label"])
    svg.text(X0 + code_w, y, fname, ffont, fpx, t["label"], ("label", "program-file"), anchor="end")
    y += 14
    notes = fig.get("notes", [])
    svg.open(data_key="code")
    recursive = any(len(s["state"].get("path", [])) != len(set(s["state"].get("path", []))) for s in states)
    card_h, ys = code_panel(svg, lesson, fig["program"], run, shown, X0, y, code_w, csize, clh,
                            g["gutter"], "code-card", "gutter", True, wide,
                            badges=[(k, n["line"]) for k, n in enumerate(notes, 1)], arcs=not recursive)
    svg.close()
    card_top, card_bottom = y, y + card_h

    # ---------- beside the program (wide) or under it (portrait): panel, numbered notes, output ----------
    col_x = X0 + code_w + g["col_gap"] if wide else X0
    col_w = X1 - col_x
    col_y = card_top if wide else card_bottom + 30
    if side:
        col_y += mech.draw(svg, lesson, final_state, col_x, col_y, col_w, layout, flow, states=fig["states"]) + (30 if wide else 26)
    if notes:
        col_y = _notes(svg, flow, lesson, notes, col_x, col_y, col_w, g) + (24 if wide else 22)
    out_h = _output_height(svg, g, lesson, final_state)
    in_col = not wide or col_y + out_h <= card_bottom + 40
    out_x, out_y, out_w = (col_x, col_y, col_w) if in_col else (X0, card_bottom + 40, code_w)
    out_h = _output_card(svg, g, lesson, final_state, out_x, out_y, out_w)
    y = max(card_bottom, out_y + out_h) + (44 if wide else 36)
    if not wide:
        y = out_y + out_h + 36

    # ---------- the comparison program, with its own path and output (mechanism, not metrics) ----------
    cmp = fig.get("compare")
    if cmp:
        y = _compare(svg, flow, lesson, g, wide, cmp, X0, X1, y, code_w, col_x + (22 if svg.frame["panel_fill"] else 0)) + 40
    # ---------- a common wrong belief, and the claim that corrects it ----------
    if fig.get("misconception"):
        y = _wrong_belief(svg, flow, lesson, g, wide, fig["misconception"], X0, X1, y) + 34

    # ---------- caption + provenance ----------
    cfont, cpx, cweight, _c, _s = svg.role("caption", g["caption"])
    for cid in fig.get("caption_claims", []):
        y = flow.emit(X0, y, claims[cid]["text"], cfont, cpx, cpx * 1.38, t["ink"], ("claim", cid), X1 - X0,
                      weight=cweight)
        y += 6
    y += 10
    svg.line(X0, y - 16, X1, y - 16, t["rule"], 1)
    prov = text.provenance(lesson)
    m0 = svg.mark()
    for ln in fonts.wrap(ffont, g["foot"], prov, X1 - X0):
        svg.text(X0, y + 4, ln, ffont, g["foot"], t["label"], ("chrome", "provenance"))
        y += g["foot"] * 1.5
    svg.merge(m0)
    src_path = f"lessons/{lesson.id}/{prog['path']}"
    svg.raw(f'<a href="../../{esc(prog["path"])}" data-role="source">')
    m0 = svg.mark()
    for ln in fonts.wrap_at(ffont, g["foot"], text.ui("source_link", path=src_path), X1 - X0, "/"):
        svg.text(X0, y + 4, ln, ffont, g["foot"], t["note"], ("chrome", "source_link"), tone="note")
        y += g["foot"] * 1.5
    svg.merge(m0)
    svg.raw("</a>")
    height = y + (24 if wide else 16)
    return svg, height


def alt_text(lesson):
    claims = lesson.by_id("claims")
    facts = lesson.by_id("facts")
    fig = lesson.data["figure"]
    final = lesson.state(fig["states"][-1])["state"]["output"]
    return " ".join([plain(claims[fig["title_claim"]]["text"]),
                     text.ui("alt_output", program=lesson.program(fig["program"])["path"],
                             lines=", ".join(text.display(facts[f]) for f in final))]
                    + [plain(claims[c]["text"]) for c in fig.get("caption_claims", [])])


def render(lesson, layout, theme, tokens, math=None):
    svg, height = build_svg(lesson, layout, theme, tokens, math)
    t = svg.t
    g = LAYOUTS[layout]
    used = {k: v for k, v in svg.chars.items() if v}
    css = fonts.face_css(used)
    css += f"text{{font-variant-numeric:{tokens['numeric']};font-feature-settings:'lnum' 1,'tnum' 1}}"
    W = g["W"]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height:.0f}" width="{W}" '
            f'height="{height:.0f}" role="img" aria-labelledby="fig-title fig-desc" data-theme="{theme}" '
            f'data-layout="{layout}" data-lesson="{esc(lesson.id)}" data-lesson-sha256="{lesson.sha256()}">\n'
            f'<title id="fig-title" data-label="title">{esc(lesson.data["title"])}</title>\n'
            f'<desc id="fig-desc" data-alt="1">{esc(alt_text(lesson))}</desc>\n'
            f'<defs><style>{css}</style>'
            f'<marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" '
            f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{t["note"]}"/></marker></defs>\n'
            f'<rect id="frame-bg" x="0" y="0" width="{W}" height="{height:.0f}" fill="{t["ground"]}"/>\n'
            + "\n".join(svg.els) + "\n</svg>\n")


VARIANTS = [("wide", "light"), ("wide", "dark"), ("portrait", "light"), ("portrait", "dark")]


def figure_texts(lesson):
    fig = lesson.data["figure"]
    ids = [fig.get("title_claim")] + [n["claim"] for n in fig.get("notes", [])] + fig.get("caption_claims", []) \
        + ([fig["compare"]["claim"]] if fig.get("compare") else [])
    return [lesson.claim(c)["text"] for c in ids if c]


def project(lesson, out_dir, tokens=None):
    """Write the 4 SVG variants; PNGs come from node/shoot.mjs (2x) in verify/visual.make_pngs."""
    out_dir.mkdir(parents=True, exist_ok=True)
    tokens = tokens or fonts.tokens()
    math = render_math([s for x in figure_texts(lesson) for s in tex_segments(x)], lesson.sha256())
    files = []
    for layout, theme in VARIANTS:
        name = f"{lesson.id}-{layout}-{theme}.svg"
        (out_dir / name).write_text(render(lesson, layout, theme, tokens, math))
        files.append(name)
    return files
