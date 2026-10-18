r"""Still projector: code-trace figure as SVG (wide 1200 / portrait 400) x (light / dark), plus 2x PNG.

Wide wireframe (viewBox 1200 x H):
+--------------------------------------------------------------------------+
| C · SWITCH STATEMENT                                                     |
| <lesson title>                                    (serif 44)             |
| <figure.title_claim text>                         (serif 19, wrapped)    |
|--------------------------------------------------------------------------|
| THE PROGRAM                                   |  notes (Caveat), each at  |
| ┌────────────────────────────────────────┐    |  the line it explains:    |
| │ 4  int n = 2;              ●           │    |  line 8  -> c.match       |
| │ 5  switch (n) {            ●─╮         │    |  line 10 -> c.labels      |
| │ 6    case 1:        skipped  │         │    |  line 12 -> c.break       |
| │ 8    case 2:     enters here ◀╯        │    |                           |
| │ 9      puts("two");        ●  [no break]    |                           |
| │10    case 3:               ●           │    |                           |
| │11      puts("three");      ●           │    |                           |
| │12      break;   leaves the switch ─╮   │    |                           |
| │16  puts("done");           ◀───────╯   │    |                           |
| └────────────────────────────────────────┘    |                           |
| OUTPUT                    | <compare claim>  mini code + its output      |
| 1 two  2 three  3 done    | 1 two  2 done                                |
| <caption claims>                                                         |
| provenance · source link                                                 |
+--------------------------------------------------------------------------+
Portrait (400 wide) stacks the same parts; notes become numbered badges listed under the code.
Every value comes from facts (data-fact), every sentence from claims (data-claim) or
templates/chrome.json (data-chrome); code text is data-code. Nothing is typed in here.
"""
import re

from .. import fonts, text
from ..text import esc

KEYWORDS = {"int", "switch", "case", "break", "return", "void", "char", "default", "if", "else", "while", "for"}
MONO_ADV = 0.6  # JetBrains Mono advance width per em

LAYOUTS = {
    "wide": dict(W=1200, X0=64, X1=1136, kicker=13, title=44, dek=19, dek_lh=27, code=17, code_lh=31,
                 gutter=84, code_w=680, note=23, note_lh=31, out=26, label=12.5, caption=20, foot=12.5,
                 tag=12.5, cmp_code=16),
    "portrait": dict(W=400, X0=16, X1=384, kicker=12, title=30, dek=16, dek_lh=22, code=13, code_lh=23,
                     gutter=58, code_w=368, note=19, note_lh=25, out=21, label=12, caption=16.5, foot=12,
                     tag=12, cmp_code=13),
}


class Svg:
    def __init__(self, theme_name, tokens):
        self.t = tokens["themes"][theme_name]
        self.theme = theme_name
        self.els = []
        self.chars = {"serif": "", "serif_italic": "", "mono": "", "hand": ""}

    def rect(self, x, y, w, h, fill, rx=0, rid=None, stroke=None, sw=1):
        a = f' id="{rid}"' if rid else ""
        s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        self.els.append(f'<rect{a} x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}"{s}/>')

    def line(self, x1, y1, x2, y2, color, sw=1.5, dash=None, role="rule"):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.els.append(f'<line data-role="{role}" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                        f'stroke="{color}" stroke-width="{sw}"{d} stroke-linecap="round"/>')

    def path(self, d, color, sw=2.0, role="path", marker=False):
        m = ' marker-end="url(#arrow)"' if marker else ""
        self.els.append(f'<path data-role="{role}" d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" '
                        f'stroke-linecap="round" stroke-linejoin="round"{m}/>')

    def circle(self, cx, cy, r, fill):
        self.els.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{fill}"/>')

    def text(self, x, y, s, font, size, color, src, weight=400, anchor="start", inside=None, italic=False,
             ocr=None, spacing=0, raw=None, ocr_group=None):
        """One text element. src is ('claim', id) | ('chrome', key) | ('fact', id) | ('code', pid) | ('label', name)."""
        key = "serif_italic" if (font == "serif" and italic) else font
        self.chars[key] += s
        attrs = [f'x="{x:.1f}"', f'y="{y:.1f}"', f'font-family="{fonts.FAMILY[font]}"', f'font-size="{size}"',
                 f'fill="{color}"', f'data-{src[0]}="{esc(src[1])}"']
        if weight != 400:
            attrs.append(f'font-weight="{weight}"')
        if italic:
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


def _code_spans(line_text, t):
    """Escape a code line into tspans: keywords bold, string literals soft. Returns (raw svg, plain)."""
    out = []
    for tok in re.findall(r'"[^"]*"|[A-Za-z_]\w*|\s+|.', line_text):
        if tok.startswith('"'):
            out.append(f'<tspan fill="{t["soft"]}">{esc(tok)}</tspan>')
        elif tok in KEYWORDS:
            out.append(f'<tspan font-weight="700">{esc(tok)}</tspan>')
        else:
            out.append(esc(tok))
    return "".join(out)


def build_svg(lesson, layout, theme, tokens):
    g = LAYOUTS[layout]
    wide = layout == "wide"
    svg = Svg(theme, tokens)
    t = svg.t
    fig = lesson.data["figure"]
    W, X0, X1 = g["W"], g["X0"], g["X1"]
    claims = lesson.by_id("claims")
    facts = lesson.by_id("facts")

    # ---------- header ----------
    y = 64 if wide else 42
    svg.text(X0, y, text.ui("kicker", topic=lesson.data["topic"]).upper(), "mono", g["kicker"], t["blue"],
             ("chrome", "kicker"), weight=600, spacing=2)
    y += 50 if wide else 38
    m0 = svg.mark()
    for ln in fonts.wrap("serif", g["title"], lesson.data["title"], X1 - X0, bold=True):
        svg.text(X0, y, ln, "serif", g["title"], t["ink"], ("label", "title"), weight=600)
        y += g["title"] * 1.34
    svg.merge(m0)
    y += 2
    dek = claims[fig["title_claim"]]["text"]
    m0 = svg.mark()
    for ln in fonts.wrap("serif", g["dek"], dek, X1 - X0):
        svg.text(X0, y, ln, "serif", g["dek"], t["soft"], ("claim", fig["title_claim"]))
        y += g["dek_lh"]
    svg.merge(m0)
    y += 10
    svg.line(X0, y, X1, y, t["rule"], 1)
    y += 34 if wide else 28

    # ---------- code card ----------
    states = [lesson.state(s) for s in fig["states"]]
    executed = []
    for s in states:
        for ln in s["state"].get("path", []):
            if ln not in executed:
                executed.append(ln)
    src_lines = lesson.program_source(fig["program"]).split("\n")
    first = 3 if wide else 4
    last = max(executed) + (1 if wide else 0)
    shown = list(range(first, min(last, len(src_lines)) + 1))
    svg.text(X0, y, text.ui("code_label").upper(), "mono", g["label"], t["muted"], ("chrome", "code_label"),
             weight=600, spacing=1.5)
    y += 14
    card_x, card_w = X0, g["code_w"]
    pad_top = 22 if wide else 16
    card_h = pad_top * 2 + len(shown) * g["code_lh"] - 8
    svg.rect(card_x, y, card_w, card_h, t["card"], rx=12, rid="code-card", stroke=t["rule"], sw=1)
    rail_x = card_x + g["gutter"] - (12 if wide else 8)
    code_x = card_x + g["gutter"] + (8 if wide else 4)
    charw = g["code"] * MONO_ADV
    ys = {}
    base = y + pad_top + g["code"] * 0.8
    for i, n in enumerate(shown):
        ly = base + i * g["code_lh"]
        ys[n] = ly
        line_txt = src_lines[n - 1]
        indent = len(line_txt) - len(line_txt.lstrip(" "))
        is_exec = n in executed
        if is_exec and line_txt.strip():
            svg.rect(code_x - 6 + indent * charw, ly - g["code"] * 0.95, len(line_txt.strip()) * charw + 12,
                     g["code_lh"] - 4, t["hl"], rx=5)
        svg.text(card_x + (30 if wide else 22), ly, str(n), "mono", max(12, g["code"] - 3), t["faint"],
                 ("label", "line-number"), anchor="end", inside="code-card", ocr=str(n), ocr_group="gutter")
        if line_txt.strip():
            color = t["ink"] if is_exec or n < min(executed) or n > max(executed) else t["muted"]
            svg.text(code_x + indent * charw, ly, line_txt.strip(), "mono", g["code"], color,
                     ("code", fig["program"]), inside="code-card", raw=_code_spans(line_txt.strip(), t))

    # executed path rail: dots on executed lines, straight runs, arcs for jumps
    run = [n for n in executed if n in ys]
    cy = lambda n: ys[n] - g["code"] * 0.33
    for a, b in zip(run, run[1:]):
        if b == a + 1:
            svg.line(rail_x, cy(a), rail_x, cy(b), t["blue"], 2.5, role="path")
        else:
            bulge = rail_x - (20 if wide else 14)
            svg.path(f"M{rail_x:.1f},{cy(a):.1f} C{bulge:.1f},{cy(a):.1f} {bulge:.1f},{cy(b):.1f} "
                     f"{rail_x - 4:.1f},{cy(b):.1f}", t["blue"], 2.5, marker=True)
    for n in run:
        svg.circle(rail_x, cy(n), 4 if wide else 3, t["blue"])

    # tags inside the card, right-aligned
    tag_x = card_x + card_w - (16 if wide else 34)
    enter = next((s["state"]["line"] - 1 for s in states[1:2]), None)
    nobreak_after = None
    for a, b in zip(run, run[1:]):
        if src_lines[b - 1].strip().startswith("case") and b == a + 1:
            nobreak_after = a
            break
    brk = next((n for n in run if src_lines[n - 1].strip() == "break;"), None)
    tags = []
    if wide and enter:
        tags.append((enter, "enter_label", t["blue"]))
    if wide and brk:
        tags.append((brk, "exit_label", t["blue"]))
    if wide:
        for n in shown:
            if n not in executed and min(executed) < n < max(executed) and src_lines[n - 1].strip().startswith("case"):
                tags.append((n, "skipped_label", t["muted"]))
    for n, key, color in tags:
        svg.text(tag_x, ys[n], text.ui(key), "mono", g["tag"], color, ("chrome", key), anchor="end",
                 inside="code-card", italic=False)
    if nobreak_after:
        label = text.ui("no_break")
        tw = fonts.width("mono", g["tag"], label, bold=True) + 16
        ty = ys[nobreak_after] + g["code_lh"] * 0.5 - 1
        rx0 = tag_x - tw
        svg.rect(rx0, ty - g["tag"] * 1.05, tw, g["tag"] * 1.75, t["red_tint"], rx=9, rid="tag-nobreak",
                 stroke=t["red"], sw=1.2)
        svg.text(rx0 + tw / 2, ty + g["tag"] * 0.32, label, "mono", g["tag"], t["red"], ("chrome", "no_break"),
                 weight=700, anchor="middle", inside="tag-nobreak")
    card_bottom = y + card_h

    # ---------- notes ----------
    notes = fig.get("notes", [])
    if wide:
        nx, nw = card_x + card_w + 32, X1 - (card_x + card_w + 32)
        floor = y
        for note in notes:
            lines = fonts.wrap("hand", g["note"], claims[note["claim"]]["text"], nw)
            ny = max(ys.get(note["line"], floor) + 2, floor + g["note"])
            svg.line(nx - 24, ny - g["note"] * 0.3, nx - 8, ny - g["note"] * 0.3, t["blue"], 1.5, role="rule")
            m0 = svg.mark()
            for ln in lines:
                svg.text(nx, ny, ln, "hand", g["note"], t["blue"], ("claim", note["claim"]), weight=600)
                ny += g["note_lh"]
            svg.merge(m0)
            floor = ny + 6
        y = max(card_bottom, floor) + 40
    else:
        for k, note in enumerate(notes, 1):
            ly = ys.get(note["line"])
            if ly is not None:
                svg.rect(card_x + card_w - 24, ly - g["code"] * 0.33 - 10, 20, 20, t["blue"], rx=10, rid=f"badge-c{k}")
                svg.text(card_x + card_w - 14, ly - g["code"] * 0.33 + 4.5, str(k), "mono", 12, t["card"],
                         ("label", "note-badge"), weight=700, anchor="middle", inside=f"badge-c{k}")
        y = card_bottom + 30
        for k, note in enumerate(notes, 1):
            svg.rect(X0, y - 16, 20, 20, t["blue"], rx=10, rid=f"badge-n{k}")
            svg.text(X0 + 10, y - 1.5, str(k), "mono", 12, t["paper"], ("label", "note-badge"), weight=700,
                     anchor="middle", inside=f"badge-n{k}")
            m0 = svg.mark()
            for ln in fonts.wrap("hand", g["note"], claims[note["claim"]]["text"], X1 - X0 - 28):
                svg.text(X0 + 28, y, ln, "hand", g["note"], t["blue"], ("claim", note["claim"]), weight=600)
                y += g["note_lh"]
            svg.merge(m0)
            y += 8
        y += 22

    # ---------- output + compare ----------
    final = states[-1]["state"]["output"]
    cmp = fig.get("compare")
    col_gap = 24
    if wide:
        ow = (X1 - X0 - col_gap) / 2
        boxes = [(X0, ow), (X0 + ow + col_gap, ow)]
    else:
        boxes = [(X0, X1 - X0), (X0, X1 - X0)]
    out_h = 64 + len(final) * (g["out"] + 16)

    def output_box(bx, by, bw, fids, rid, header_src, header_text, header_font):
        lines = fonts.wrap(header_font, g["label"] if header_font == "mono" else g["dek"], header_text, bw - 40)
        h = 40 + len(lines) * (g["dek_lh"] if header_font == "serif" else 18) + len(fids) * (g["out"] + 16) + 8
        svg.rect(bx, by, bw, h, t["card"], rx=12, rid=rid, stroke=t["rule"], sw=1)
        yy = by + 32
        m0 = svg.mark()
        for ln in lines:
            if header_font == "mono":
                svg.text(bx + 20, yy, ln.upper(), "mono", g["label"], t["muted"], header_src, weight=600,
                         spacing=1.5, inside=rid)
                yy += 18
            else:
                svg.text(bx + 20, yy, ln, "serif", g["dek"], t["soft"], header_src, inside=rid)
                yy += g["dek_lh"]
        svg.merge(m0)
        yy += g["out"] * 0.6
        for k, fid in enumerate(fids, 1):
            val = text.display(facts[fid])
            svg.text(bx + 20, yy + g["out"] * 0.35, str(k), "mono", g["label"], t["faint"], ("label", "output-step"),
                     inside=rid)
            svg.text(bx + 48, yy + g["out"] * 0.35, val, "mono", g["out"], t["ink"], ("fact", fid), weight=600,
                     inside=rid, ocr=val, ocr_group=rid)
            yy += g["out"] + 16
        return h

    h1 = output_box(boxes[0][0], y, boxes[0][1], final, "out-card", ("chrome", "output_label"),
                    text.ui("output_label"), "mono")
    if cmp:
        cstate = lesson.state(cmp["state"])
        cy0 = y if wide else y + h1 + 20
        h2 = output_box(boxes[1][0], cy0, boxes[1][1], cstate["state"]["output"], "cmp-card",
                        ("claim", cmp["claim"]), claims[cmp["claim"]]["text"], "serif")
        y = (max(y + h1, cy0 + h2)) + 36
    else:
        y += h1 + 36

    # ---------- caption + provenance ----------
    for cid in fig.get("caption_claims", []):
        m0 = svg.mark()
        for ln in fonts.wrap("serif", g["caption"], claims[cid]["text"], X1 - X0):
            svg.text(X0, y, ln, "serif", g["caption"], t["ink"], ("claim", cid), italic=True)
            y += g["caption"] * 1.35
        svg.merge(m0)
        y += 6
    y += 10
    svg.line(X0, y - 16, X1, y - 16, t["rule"], 1)
    f0 = facts[final[0]]
    compiler = f0["source"]["compiler"].split(" (")[0]
    prov = text.ui("provenance", compiler=compiler, sha=f0["source"]["stdout_sha256"][:12])
    m0 = svg.mark()
    for ln in fonts.wrap("mono", g["foot"], prov, X1 - X0):
        svg.text(X0, y + 4, ln, "mono", g["foot"], t["muted"], ("chrome", "provenance"))
        y += g["foot"] * 1.5
    svg.merge(m0)
    src_path = f"lessons/{lesson.id}/{lesson.program(fig['program'])['path']}"
    svg.els.append(f'<a href="../../{esc(lesson.program(fig["program"])["path"])}" data-role="source">')
    m0 = svg.mark()
    for ln in fonts.wrap_at("mono", g["foot"], text.ui("source_link", path=src_path), X1 - X0, "/"):
        svg.text(X0, y + 4, ln, "mono", g["foot"], t["blue"], ("chrome", "source_link"))
        y += g["foot"] * 1.5
    svg.merge(m0)
    svg.els.append("</a>")
    height = y + (20 if wide else 14)
    return svg, height


def render(lesson, layout, theme, tokens):
    svg, height = build_svg(lesson, layout, theme, tokens)
    t = svg.t
    g = LAYOUTS[layout]
    claims = lesson.by_id("claims")
    facts = lesson.by_id("facts")
    fig = lesson.data["figure"]
    final = lesson.state(fig["states"][-1])["state"]["output"]
    title = lesson.data["title"]
    desc = " ".join([claims[fig["title_claim"]]["text"],
                     text.ui("alt_output", program=lesson.program(fig["program"])["path"],
                             lines=", ".join(text.display(facts[f]) for f in final))]
                    + [claims[c]["text"] for c in fig.get("caption_claims", [])])
    used = {k: v for k, v in svg.chars.items() if v}
    css = fonts.face_css(used)
    css += f"text{{font-variant-numeric:{fonts.tokens()['numeric']};font-feature-settings:'lnum' 1,'tnum' 1}}"
    W = g["W"]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height:.0f}" width="{W}" '
            f'height="{height:.0f}" role="img" aria-labelledby="fig-title fig-desc" data-theme="{theme}" '
            f'data-layout="{layout}" data-lesson="{esc(lesson.id)}" data-lesson-sha256="{lesson.sha256()}">\n'
            f'<title id="fig-title" data-label="title">{esc(title)}</title>\n'
            f'<desc id="fig-desc" data-alt="1">{esc(desc)}</desc>\n'
            f'<defs><style>{css}</style>'
            f'<marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" '
            f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{t["blue"]}"/></marker></defs>\n'
            f'<rect id="frame-bg" x="0" y="0" width="{W}" height="{height:.0f}" fill="{t["paper"]}"/>\n'
            + "\n".join(svg.els) + "\n</svg>\n")


VARIANTS = [("wide", "light"), ("wide", "dark"), ("portrait", "light"), ("portrait", "dark")]


def project(lesson, out_dir):
    """Write the 4 SVG variants and a viewer page; PNGs come from node/shoot.mjs (2x)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    tokens = fonts.tokens()
    files = []
    for layout, theme in VARIANTS:
        name = f"{lesson.id}-{layout}-{theme}.svg"
        (out_dir / name).write_text(render(lesson, layout, theme, tokens))
        files.append(name)
    return files
