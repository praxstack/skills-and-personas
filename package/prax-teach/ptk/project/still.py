r"""Still projector: one landscape, figure-led picture (AC-10.1) and a portrait for phones, light and dark, plus 2x PNG.

Wide wireframe (viewBox 1200 x H, W >= 1.5 H), both themes, in the Neuron Atlas manner (one calm figure, panels
split by thin rules, no cards):
+--------------------------------------------------------------------------+
| C · SWITCH STATEMENT                                    kicker           |
| <lesson title>                                          display          |
| <figure.title_claim>                                    body             |
|--------------------------------------------------------------------------|
| [data-role="figure"]                                                      |
|  ┌ the mechanism (data-role="mechanism") ┐   output · numbered notes ·    |
|  │ switch: the path through the cases    │   the comparison program       |
|  │ factorial: the stack column           │   (a stack or bytes lesson: the |
|  │ one-byte: the bytes in memory         │   output of the run, the note   |
|  │ neuron: multiply · add · gate (full   │   lines of the program)         |
|  └ width, with a band of code, output and notes under it)                 |
| <caption claims>                                                         |
| source link (provenance lives in <metadata> and the alt text, never on   |
| the picture)                                                             |
+--------------------------------------------------------------------------+
Portrait (400 wide) stacks the same parts, so it draws the same facts.

Mechanism, not metrics (D20.5): each output sits beside the step or frame that produced it.

Sources: every value comes from facts (data-fact, inside a data-state container whose fact order the values gate
checks), every sentence from claims (data-claim) or templates/chrome.json (data-chrome), code text is data-code with
data-src-line, line numbers are data-label with data-line. No more than two program lines stand together, so the
still holds no code block. Colours and type come from tokens.json by role (references/STYLE.md); nothing here names
a hex value or a family. Math in a claim, written \( ... \), goes through MathJax tex2svg into a scaled <g>.
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
    "wide": dict(W=1200, X0=48, X1=1152, kicker=13, title=38, dek=18, label=12.5, caption=17, foot=12.5, note=19,
                 out=24, out_gap=12, code=15, col_gap=56),
    "portrait": dict(W=400, X0=16, X1=384, kicker=12, title=28, dek=16, label=12, caption=15.5, foot=12, note=18,
                     out=21, out_gap=10, code=13, col_gap=0),
}
# the mechanism's share of the wide figure, by panel kind (the rest is the side column)
MECH_W = {"control-path": 680, "stack": 540, "views": 640}


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


def _notes(svg, flow, lesson, notes, x, y, w, g, belief=False):
    """Numbered notes, each with the badge its line carries. With `belief`, the note whose claim corrects the figure's
    misconception sits in a wrong-belief callout under the belief it corrects. Returns the y after them."""
    t = svg.t
    claims = lesson.by_id("claims")
    fig = lesson.data["figure"]
    mis = {m["id"]: m for m in lesson.data.get("misconceptions", [])}.get(fig.get("misconception")) if belief else None
    nfont, npx, nweight, _c, _s = svg.role("note", g["note"])
    nlh = npx * (1.35 if nfont == "hand" else 1.42)
    svg.open(data_key="note")
    y += npx * 0.9
    for k, note in enumerate(notes, 1):
        box = mis and mis["correction"] == note["claim"]
        if box:
            pad = 14
            i0 = svg.mark()
            top = y - npx * 0.9 + 4
            _label(svg, x + pad, top + pad + 10, text.ui("wrong_belief"), g["label"], ("chrome", "wrong_belief"),
                   color=t["correction"], inside="belief-card")
            svg.els[-1] = svg.els[-1].replace("<text ", '<text data-tone="correction" ', 1)
            bfont, bpx, bweight, _c2, _s2 = svg.role("body", g["note"] * 0.95)
            yy = top + pad + 22 + bpx
            m0 = svg.mark()
            for ln in fonts.wrap(bfont, bpx, mis["statement"], w - 2 * pad, weight=bweight):
                svg.text(x + pad, yy, ln, bfont, bpx, t["ink"], ("misconception", mis["id"]), weight=bweight,
                         inside="belief-card")
                yy += bpx * 1.4
            svg.merge(m0)
            y, x_, w_ = yy + 6, x + pad, w - 2 * pad
        else:
            x_, w_ = x, w
        svg.rect(x_, y - 15, 20, 20, t["note"], rx=10, rid=f"badge-n{k}")
        svg.text(x_ + 10, y - 0.5, str(k), "mono", 12, t["surface"], ("label", "note-badge"), weight=700,
                 anchor="middle", inside=f"badge-n{k}")
        y = flow.emit(x_ + 30, y, claims[note["claim"]]["text"], nfont, npx, nlh, t["note"],
                      ("claim", note["claim"]), w_ - 30, weight=nweight, tone="note", inside="belief-card" if box else None) + 8
        if box:
            h = y - nlh + npx * 0.35 + 14 - top
            mark = svg.mark()
            svg.rect(x, top, w, h, t["correction_tint"], rx=12, rid="belief-card", stroke=t["correction"], sw=1.2,
                     role="pill")
            svg.els.insert(i0, svg.els.pop(mark))
            y = top + h + npx * 1.6
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


def _code_strip(svg, lesson, pid, lines, x, y, w, size, badges=None):
    """At most two program lines, each with its line number and (badges) the number of the note that explains it,
    under a small label. Never a listing: AC-10.1 allows no code block. Returns the y after it."""
    t = svg.t
    assert len(lines) <= 2, "a still shows at most two program lines together"
    src = lesson.program_source(pid).split("\n")
    num = max(12, round(size * 0.8, 1))
    lh = round(size * 2.1, 1)
    svg.open(data_key="code")
    y += size
    for n in lines:
        s_ = src[n - 1].strip()
        rid = f"strip-{pid}-{n}"
        nw = fonts.width("mono", num, str(n))
        tw = 14 + nw + 12 + fonts.width("mono", size, s_) + 14
        svg.rect(x, y - size * 1.25, tw, size * 1.9, t["highlight"], rx=6, rid=rid)
        svg.text(x + 14 + nw, y, str(n), "mono", num, t["label"], ("label", "line-number"), anchor="end", inside=rid,
                 extra={"data-line": n})
        svg.text(x + 14 + nw + 12, y, s_, "mono", size, t["ink"], ("code", pid), inside=rid, extra={"data-src-line": n})
        k = next((k for k, ln in (badges or []) if ln == n), None)
        if k is not None and x + tw + 30 <= x + w:
            svg.rect(x + tw + 8, y - size * 0.95, 20, 20, t["note"], rx=10, rid=f"{rid}-badge")
            svg.text(x + tw + 18, y - size * 0.95 + 14.5, str(k), "mono", 12, t["surface"], ("label", "note-badge"),
                     weight=700, anchor="middle", inside=f"{rid}-badge")
        y += lh
    svg.close()
    return y - lh + size * 0.9


def _labelled_outputs(svg, g, lesson, sid, x, y, w):
    """The output of `sid`, numbered, each line labelled with the conversion that printed it (its printf's format and
    argument, both program text). Returns the y after it."""
    t = svg.t
    st = lesson.state(sid)["state"]
    facts = lesson.by_id("facts")
    src = lesson.program_source(st["program"]).split("\n")
    made = rail.print_lines(src, st.get("path", []), [text.display(facts[f]) for f in st["output"]]) or []
    vfont, vpx, vweight, _c, _s = svg.role("value", round(g["out"] * 0.86, 2))
    cs = round(g["code"] * 0.92, 2)
    g = dict(g, out_gap=g["out_gap"] * 0.7)
    lab_w = 0
    rows = []
    for fid, n in zip(st["output"], made):
        m = re.search(r'printf\("([^"]*?)(?:\\n)?"\s*,\s*(.+)\)\s*;', src[n - 1])
        spec = re.findall(r"%[#0-9.]*[a-z]+", m.group(1))[0] if m else ""
        arg = m.group(2).strip() if m else ""
        rows.append((fid, spec, arg, n))
        lab_w = max(lab_w, fonts.width("mono", cs, f"{spec}  {arg}"))
    i_out = svg.mark()
    svg.open(data_key="output", data_state=sid)
    _label(svg, x, y + 16, text.ui("prints_label", file=lesson.program(st["program"])["path"].split("/")[-1]), g["label"],
           ("chrome", "prints_label"), inside="out-card")
    yy = y + 36 + vpx * 0.8
    step = vpx + g["out_gap"]
    vx = x + 28 + lab_w + 46  # room for a note badge between the label and the value
    widest = max(fonts.width(vfont, vpx, text.display(facts[f]), weight=vweight) for f in st["output"])
    if vx + widest > x + w - 4:
        vpx = round(vpx * (x + w - 4 - vx) / widest, 2)
    badge = {n["line"]: k for k, n in enumerate(lesson.data["figure"].get("notes", []), 1)}
    for k, (fid, spec, arg, line) in enumerate(rows, 1):
        val = text.display(facts[fid])
        svg.text(x, yy, str(k), "mono", max(14, g["label"]), t["faint"], ("label", "output-step"), inside="out-card",
                 ocr=str(k), ocr_group="out-steps")
        if spec:
            svg.text(x + 28, yy, spec, "mono", cs, t["note"], ("code", st["program"]), inside="out-card")
            svg.text(x + 28 + fonts.width("mono", cs, spec + "  "), yy, arg, "mono", cs, t["label"], ("code", st["program"]),
                     inside="out-card")
        svg.text(vx, yy, val, vfont, vpx, t["value"], ("fact", fid), weight=vweight, inside="out-card", ocr=val,
                 ocr_group="out", raw=text.tight_points(val))
        if line in badge:  # the note that explains this line of output
            bx = vx - 34
            svg.rect(bx, yy - vpx * 0.78, 20, 20, t["note"], rx=10, rid=f"out-badge{badge[line]}")
            svg.text(bx + 10, yy - vpx * 0.78 + 14.5, str(badge[line]), "mono", 12, t["surface"], ("label", "note-badge"),
                     weight=700, anchor="middle", inside=f"out-badge{badge[line]}")
        yy += step
    svg.close()
    h = yy - step - y + vpx * 0.3 + 6
    _place_panels(svg, [(i_out, x - 6, y, w + 6, "out-card")], [h])
    return y + h


def _caption(svg, flow, lesson, g, x, y, w):
    t = svg.t
    claims = lesson.by_id("claims")
    cfont, cpx, cweight, _c, _s = svg.role("caption", g["caption"])
    for cid in lesson.data["figure"].get("caption_claims", []):
        y = flow.emit(x, y, claims[cid]["text"], cfont, cpx, cpx * 1.38, t["ink_soft"], ("claim", cid), w, weight=cweight)
        y += 4
    return y


def _side(svg, flow, lesson, g, kind, x, y, w, wide):
    """What sits beside the mechanism (wide) or under it (portrait): the output, the notes, the comparison, the
    program lines the notes explain. Returns the y after it."""
    fig = lesson.data["figure"]
    t = svg.t
    final = fig["states"][-1]
    notes = fig.get("notes", [])
    claims = lesson.by_id("claims")
    if kind == "control-path":
        # the output is drawn in the path figure, beside the rows that printed it
        if notes:
            y = _notes(svg, flow, lesson, notes, x, y, w, g) + (26 if wide else 22)
        cmp = fig.get("compare")
        if cmp:
            svg.line(x, y - 12, x + w, y - 12, t["rule"], 1)
            svg.open(data_key="compare")
            fname = lesson.program(cmp["program"])["path"].split("/")[-1]
            _label(svg, x, y + 12, text.ui("compare_label", file=fname), g["label"], ("chrome", "compare_label"))
            bfont, bpx, bweight, _c, _s = svg.role("body", g["dek"] * 0.95)
            y = flow.emit(x, y + 22 + bpx, claims[cmp["claim"]]["text"], bfont, bpx, bpx * 1.4, t["ink_soft"],
                          ("claim", cmp["claim"]), w, weight=bweight) + 4
            # the comparison at a readable size (review B1+B2: its code was 13 px)
            y += mech.draw(svg, lesson, cmp["state"], x, y, w, "portrait", flow, key=False, kind="control-path",
                           only_ran=True, head=False, sizes={"code": 15.5} if wide else None)
            svg.close()
        return y
    if kind == "stack":
        if wide:
            y = _output_grid(svg, dict(g, out=g["out"] * 0.78), lesson, final, x, y, w, by_column=True) + 18
        else:
            y = _output_card_at(svg, g, lesson, final, x, y, w)
    elif kind == "views":
        y = _labelled_outputs(svg, g, lesson, final, x, y, w) + 14
    lines = [n["line"] for n in notes]
    if kind == "stack" and lines:
        y = _code_strip(svg, lesson, fig["program"], lines, x, y + 8, w, g["code"],
                        badges=[(k, n["line"]) for k, n in enumerate(notes, 1)]) + 10
    if notes and kind != "neuron":
        y = _notes(svg, flow, lesson, notes, x, y, w, g, belief=kind == "stack")
    ub = (fig.get("panel") or {}).get("ub")
    if kind == "views" and ub:
        y += 30
        svg.line(x, y - 16, x + w, y - 16, t["correction"], 1.2)
        usrc = lesson.program_source(ub["program"]).split("\n")
        fname = lesson.program(ub["program"])["path"].split("/")[-1]
        ffont, fpx, _w, _c, _s = svg.role("foot", g["label"])
        svg.text(x, y, fname, ffont, fpx, t["label"], ("label", "program-file"))
        lfont, lpx, lweight, caps, spacing = svg.role("label", g["label"])
        lab = text.ui("lane_undefined")
        svg.text(x + w, y, lab.upper() if caps else lab, lfont, lpx, t["correction"], ("chrome", "lane_undefined"),
                 weight=lweight, spacing=spacing, anchor="end", tone="correction")
        y += g["code"] * 1.6
        svg.text(x, y, usrc[ub["line"] - 1].strip(), "mono", g["code"], t["correction"], ("code", ub["program"]),
                 extra={"data-src-line": ub["line"]})
        nfont, npx, nweight, _c, _s = svg.role("note", g["note"] * 0.85)
        y = flow.emit(x, y + npx * 1.5, claims[ub["claim"]]["text"], nfont, npx, npx * 1.4, t["correction"],
                      ("claim", ub["claim"]), w, weight=nweight, tone="correction")
    return y


def _figure_badges(svg, lesson, kind):
    """Note badges on the path figure, beside the row each note is about. They are annotations over the figure, written
    outside the mechanism's group: a note number is not a value of the mechanism (AC-10.2)."""
    if kind != "control-path":
        return
    t = svg.t
    at = (getattr(svg, "mech_anchors", None) or {}).get("badge", {})
    for k, note in enumerate(lesson.data["figure"].get("notes", []), 1):
        if note["line"] not in at:
            continue
        x, y = at[note["line"]]
        rid = f"fig-badge{k}"
        svg.rect(x + 8, y - 10, 20, 20, t["note"], rx=10, rid=rid)
        svg.text(x + 18, y + 4.5, str(k), "mono", 12, t["surface"], ("label", "note-badge"), weight=700, anchor="middle",
                 inside=rid)


def _under_mech(svg, flow, lesson, g, kind, x, y, w):
    """Under a views lesson's memory figure: the claims that read it (prose, not part of the drawn mechanism)."""
    if kind != "views":
        return y
    t = svg.t
    claims = lesson.by_id("claims")
    nfont, npx, nweight, _c, _s = svg.role("note", g["note"] * 0.9)
    for cid in (lesson.data["figure"]["panel"].get("memory") or {}).get("claims", []):
        y = flow.emit(x, y + npx * 1.3, claims[cid]["text"], nfont, npx, npx * 1.4, t["note"], ("claim", cid), w,
                      weight=nweight, tone="note") - npx * 1.4 + 6
    return y


def _output_card_at(svg, g, lesson, sid, x, y, w):
    return y + _output_card(svg, g, lesson, sid, x, y, w) + 18


def _output_grid(svg, g, lesson, sid, x, y, w, cols=2, by_column=False):
    """The output of `sid`, numbered, in `cols` columns, read row by row (a short output under a hero panel) or, with
    by_column, down each column in turn (a long output). Returns the y after it."""
    t = svg.t
    facts = lesson.by_id("facts")
    fids = lesson.state(sid)["state"]["output"]
    vfont, vpx, vweight, _c, _s = svg.role("value", g["out"])
    cw = w / cols
    widest = max(fonts.width(vfont, vpx, text.display(facts[f]), weight=vweight) for f in fids)
    if widest > cw - 40:
        vpx = round(max(13.0, vpx * (cw - 40) / widest), 2)
    i_out = svg.mark()
    svg.open(data_key="output", data_state=sid)
    _label(svg, x, y + 16, text.ui("output_label"), g["label"], ("chrome", "output_label"), inside="out-card")
    yy = y + 36 + vpx * 0.8
    nrows = -(-len(fids) // cols)
    for k, fid in enumerate(fids):
        col, row = (k // nrows, k % nrows) if by_column else (k % cols, k // cols)
        cx = x + col * cw
        val = text.display(facts[fid])
        ry = yy + row * (vpx + g["out_gap"])
        svg.text(cx, ry, str(k + 1), "mono", max(14, g["label"]), t["faint"], ("label", "output-step"), inside="out-card",
                 ocr=str(k + 1), ocr_group=f"out-steps-{col}")
        svg.text(cx + 28, ry, val, vfont, vpx, t["value"], ("fact", fid), weight=vweight, inside="out-card", ocr=val,
                 ocr_group=f"out-{col}", raw=text.tight_points(val))
    svg.close()
    rows = -(-len(fids) // cols)
    h = 36 + vpx * 0.8 + (rows - 1) * (vpx + g["out_gap"]) + vpx * 0.3 + 6
    _place_panels(svg, [(i_out, x, y, w, "out-card")], [h])
    return y + h


def _neuron_band(svg, flow, lesson, g, x, y, w, wide):
    """Under the neuron's three panels: the two program lines the notes explain and the output (left), the notes
    (right); stacked on a phone."""
    fig = lesson.data["figure"]
    notes = fig.get("notes", [])
    final = fig["states"][-1]
    badges = [(k, n["line"]) for k, n in enumerate(notes, 1)]
    if wide:
        lw = (w - g["col_gap"]) * 0.52
        # a slim band (review B1+B2): the three panels carry the picture, the band only names the lines and the output
        y1 = _code_strip(svg, lesson, fig["program"], [n["line"] for n in notes], x, y, lw, g["code"] * 0.9,
                         badges=badges)
        y1 = _output_grid(svg, dict(g, out=g["out"] * 0.8, out_gap=6), lesson, final, x, y1 + 2, lw)
        rx = x + lw + g["col_gap"]
        y2 = _notes(svg, flow, lesson, notes, rx, y - 4, x + w - rx, dict(g, note=g["note"] * 0.9), belief=True)
        svg.close()  # the caption reads the figure from under the output; it is not part of the figure
        y1 = _caption(svg, flow, lesson, dict(g, caption=g["caption"] * 0.92), x, y1 + 24, lw)
        svg.open(data_role="figure")
        return max(y1, y2)
    y = _code_strip(svg, lesson, fig["program"], [n["line"] for n in notes], x, y, w, g["code"], badges=badges) + 14
    y = _output_card_at(svg, g, lesson, final, x, y, w)
    return _notes(svg, flow, lesson, notes, x, y, w, g, belief=True)


def build_svg(lesson, layout, theme, tokens, math=None):
    g = LAYOUTS[layout]
    wide = layout == "wide"
    svg = Svg(theme, tokens)
    t = svg.t
    flow = Flow(svg, math)
    fig = lesson.data["figure"]
    W, X0, X1 = g["W"], g["X0"], g["X1"]
    claims = lesson.by_id("claims")

    # ---------- header ----------
    y = 42 if wide else 42
    font, px, weight, caps, spacing = svg.role("kicker", g["kicker"])
    kicker = text.kicker(lesson)
    svg.text(X0, y, kicker.upper() if caps else kicker, font, px, t["note"], ("chrome", "kicker"), weight=weight,
             spacing=spacing, tone="note")
    font, px, weight, _c, _s = svg.role("display", g["title"])
    y += px * (1.1 if wide else 1.25) + 4
    m0 = svg.mark()
    for ln in fonts.wrap(font, px, lesson.data["title"], X1 - X0, weight=weight):
        svg.text(X0, y, ln, font, px, t["ink"], ("label", "title"), weight=weight)
        y += px * 1.2
    svg.merge(m0)
    font, px, weight, _c, _s = svg.role("body", g["dek"])
    y = flow.emit(X0, y + 2, claims[fig["title_claim"]]["text"], font, px, px * 1.42, t["ink_soft"],
                  ("claim", fig["title_claim"]), X1 - X0, weight=weight)
    y -= 4
    svg.line(X0, y, X1, y, t["rule"], 1)
    y += 26 if wide else 26

    # ---------- the figure: the mechanism, and beside it (wide) or under it (portrait) what it explains ----------
    kind = mech.panel_kind(lesson)
    final = fig["states"][-1]
    svg.open(data_role="figure")
    if kind == "neuron":
        h = mech.draw(svg, lesson, final, X0, y, X1 - X0, layout, flow, states=fig["states"], mark=True,
                      sizes={"other_run": True})
        y += h + (26 if wide else 22)
        svg.line(X0, y - 14, X1, y - 14, t["rule"], 1)
        y = _neuron_band(svg, flow, lesson, g, X0, y + 6, X1 - X0, wide)
    else:
        mw = MECH_W[kind] if wide else X1 - X0
        if wide:
            sx = X0 + mw + g["col_gap"]
            m0 = svg.mark()
            side_end = _side(svg, flow, lesson, g, kind, sx, y, X1 - sx, wide)
            side_els = svg.els[m0:]  # measured first (the figure fits its height), written after it
            del svg.els[m0:]
            h = mech.draw(svg, lesson, final, X0, y, mw, layout, flow, states=fig["states"], mark=True,
                          only="memory" if kind == "views" else None, code_key=kind != "stack",
                          # the path keeps its own row pitch (review B1+B2: rows stretched to fill read as spaced code)
                          fit_h=None if kind == "control-path" else side_end - y,
                          sizes={"code": 16.6} if kind == "control-path" else None)
            h = _under_mech(svg, flow, lesson, g, kind, X0, y + h, mw) - y
            _figure_badges(svg, lesson, kind)
            svg.els += side_els
            svg.line(sx - g["col_gap"] / 2, y, sx - g["col_gap"] / 2, max(y + h, side_end), t["rule"], 1)
            y = max(y + h, side_end)
        else:
            h = mech.draw(svg, lesson, final, X0, y, mw, layout, flow, states=fig["states"], mark=True,
                          only="memory" if kind == "views" else None, code_key=kind != "stack")
            h = _under_mech(svg, flow, lesson, g, kind, X0, y + h, mw) - y
            _figure_badges(svg, lesson, kind)
            y += h + 26
            svg.line(X0, y - 14, X1, y - 14, t["rule"], 1)
            y = _side(svg, flow, lesson, g, kind, X0, y + 6, X1 - X0, wide)
    svg.close()
    y += (8 if kind == "neuron" else 26) if wide else 22

    # ---------- caption and the source link (provenance lives in <metadata>, off the picture) ----------
    if not (wide and kind == "neuron"):  # the neuron's caption sits in its band, under the output
        y = _caption(svg, flow, lesson, g, X0, y, X1 - X0)
    ffont, fpx, _w, _c, _s = svg.role("foot", g["foot"])
    prog = lesson.program(fig["program"])
    src_path = f"lessons/{lesson.id}/{prog['path']}"
    svg.raw(f'<a href="../../{esc(prog["path"])}" data-role="source">')
    m0 = svg.mark()
    for ln in fonts.wrap_at(ffont, g["foot"], text.ui("source_link", path=src_path), X1 - X0, "/"):
        svg.text(X0, y + 4, ln, ffont, g["foot"], t["note"], ("chrome", "source_link"), tone="note")
        y += g["foot"] * 1.5
    svg.merge(m0)
    svg.raw("</a>")
    height = y + (20 if wide else 16)
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
            f'<metadata data-provenance="{esc(text.provenance(lesson))}">{esc(text.provenance(lesson))}</metadata>\n'
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
