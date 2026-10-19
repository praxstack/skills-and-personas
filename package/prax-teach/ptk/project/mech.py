r"""Mechanism panels (WP9): the diagram beside or above the program, drawn from facts.

One renderer for every medium. It writes into a still.Svg-like writer (rect, line, path, circle, text,
open/close, role), so the still embeds it at absolute coordinates, and the explorer, the IVE and the
video wrap the same elements in their own <svg viewBox> (light and dark variants for pages, the video
theme for the film).

Every value is a fact (data-fact, checked by verify/values.py against capture and expect.py). Every
sentence is a claim (data-claim) or a chrome.json label. An element appears in a state once its fact is
shown there (the state's output, its reveals, or a token of a printed line), so the same function draws
every trace state and the video fades in exactly what a scene reveals: each fact-bound group carries
data-m="<fact id>".

    views   one value seen through several printf conversions
            ┌ the byte ─────────────────────┐
            │ 0 1 0 0 0 0 1 0     0x42      │   bits and hex facts
            └───────────────────────────────┘
            printf("%d\n", a);      ↳ 66          one lane per conversion: the source line, then its output
            printf("%f\n", (double)a);
                ↳ new double 0x4050800000000000  a lane with `via` shows the converted value first
                ↳ 66.000000
            ub.c  printf("%f\n", a);  undefined     the ub program, compiled and never run (after a state)

    stack   the call stack of the state's `frames`, outermost at the bottom; with `panel.vars` every frame
            shows its own parameter and result variable (round 18, review: "each call gets its own n and r")
            ┌ factorial(1)               returns 1 ┐ ╮  a returning frame is dashed; its value flows down
            │ n = 1                          r = 1 │ │  into the caller's slot
            ┌ factorial(2)                 waiting ┐ │
            │ n = 2                      r = 2 * ▢ │◀╯  the slot: the call that has not returned yet
            ┌ main                         waiting ┐
            │                                r = ▢ │

    neuron  three panels, as in the accepted Neuron Atlas still (D20.1):
            MULTIPLY: input × weight = signed term │ ADD: bars along a number line │ GATE: ReLU graph + output
"""
import re

from .. import fonts, text

MONO_ADV = 0.6
SIZES = {"wide": dict(label=12.5, code=15, value=24, big=32, note=17, chip=12.5, k=1.0),
         "portrait": dict(label=12.5, code=13.5, value=21, big=27, note=16, chip=12, k=0.9)}


def number(s):
    """A displayed value as a float (accepts the minus sign U+2212)."""
    return float(s.replace("−", "-"))


def shown_facts(lesson, sid):
    """Facts visible at trace state `sid`: its output, its reveals, and every token fact of a printed line."""
    st = lesson.state(sid)
    out = set(st["state"].get("output", []))
    for s in lesson.data["trace"]:  # reveals stay shown in later states of the same program
        if s["state"]["program"] == st["state"]["program"]:
            out |= set(s.get("reveals", []))
        if s["id"] == sid:
            break
    facts = lesson.by_id("facts")
    printed = st["state"].get("output", [])
    lines = {(facts[f]["program"], facts[f]["select"].get("line")) for f in printed if f in facts}
    for f in lesson.data["facts"]:  # any fact read from a line already printed (a token of it, or the line)
        sel = f["select"]
        if sel.get("line") and (f["program"], sel.get("line")) in lines:
            out.add(f["id"])
    return out


CALL_ARG = re.compile(r"^\s*([A-Za-z_]\w*)\((-?\d+)\)\s*$")
SLOT = "\u25a2"


def _fn_span(src, fn):
    """(first, last) 1-based lines of function `fn`'s definition (its header to the closing brace)."""
    head = re.compile(r"^[A-Za-z_][\w\s\*]*\b" + re.escape(fn) + r"\s*\(")
    for i, ln in enumerate(src, 1):
        if head.match(ln) and "{" in ln:
            depth = 0
            for j in range(i, len(src) + 1):
                depth += src[j - 1].count("{") - src[j - 1].count("}")
                if depth == 0:
                    return i, j
    return None


def frame_vars(lesson, sid, idx):
    """What frame `idx` (outermost first) of state `sid` shows for the panel's `vars` {param, result}:
    [{"name", "kind", ...}], every value derived from facts and the program source, never typed:

        param   {"kind": "param", "text": "3"}          the argument in the frame's call fact, factorial(3)
        result  {"kind": "unset"}                        the frame has not reached its declaration yet: r = ?
                {"kind": "slot", "prefix": "3 *"}        blocked in the call on its call line: r = 3 * ▢
                {"kind": "slot", "prefix": "3 *", "got": fact}   the call returned: r = 3 * 2
                {"kind": "value", "fact": ret}           a returning frame with no call in its result: r = 1
    """
    P = lesson.data["figure"]["panel"]
    spec = P.get("vars") or {}
    st = lesson.state(sid)["state"]
    frames = st.get("frames", [])
    fr = frames[idx]
    facts = lesson.by_id("facts")
    src = lesson.program_source(st["program"]).split("\n")
    out = []
    param, result = spec.get("param"), spec.get("result")
    arg = None
    if param and fr.get("call"):
        m = CALL_ARG.match(text.display(facts[fr["call"]]))
        if m:
            arg = m.group(2)
            out.append({"name": param, "kind": "param", "text": arg})
    if not result:
        return out
    span = _fn_span(src, fr["fn"])
    lines = range(span[0] + 1, span[1] + 1) if span else range(1, len(src) + 1)
    decl = next((n for n in lines if re.search(r"\b(?:int|long|short|char|double|float|unsigned)\s+" + re.escape(result)
                                               + r"\b", src[n - 1])), None)
    call_rx = re.compile(r"\b" + re.escape(result) + r"\s*=\s*(.*?)\b([A-Za-z_]\w*)\s*\((.*)\)\s*;")
    call = next(((n, call_rx.search(src[n - 1])) for n in lines if call_rx.search(src[n - 1])
                 and call_rx.search(src[n - 1]).group(2) != "printf"), None)
    prefix = None
    if call:
        before = call[1].group(1).strip()
        if arg is not None and param:
            before = re.sub(r"\b" + re.escape(param) + r"\b", arg, before)
        prefix = before
    status = fr.get("status", "running" if idx == len(frames) - 1 else "waiting")
    line = fr.get("line") or (st["line"] if idx == len(frames) - 1 else None)
    if status == "returning" and fr.get("ret") and not fr.get("got"):
        out.append({"name": result, "kind": "value", "fact": fr["ret"]})
    elif fr.get("got") and prefix is not None:
        out.append({"name": result, "kind": "slot", "prefix": prefix, "got": fr["got"]})
    elif status == "waiting" and prefix is not None:
        out.append({"name": result, "kind": "slot", "prefix": prefix})
    elif decl is None or line is None or line <= decl:
        out.append({"name": result, "kind": "unset"})
    return out


def _vars_row(c, x, y, xr, sid, idx, size, rid):
    """One frame's variables on one row: the parameter at the left (data-part n), the result at the right (its slot
    is the landing point of the callee's returned value). Every number drawn is bound: the parameter and the result's
    prefix to the frame's call fact (data-from-fact), a received value to its own fact. Returns the slot's geometry
    (centre x, centre y, right x, top y, height) or None."""
    svg, t = c.svg, c.t
    slot_at = None
    st = c.lesson.state(sid)["state"]
    call = st.get("frames", [])[idx].get("call")
    bound = {"data-from-fact": call} if call else {}
    for v in frame_vars(c.lesson, sid, idx):
        if v["kind"] == "param":
            svg.open(data_part="n")
            svg.text(x, y, f"{v['name']} = {v['text']}", "mono", size, t["ink_soft"], ("chrome", "frame_var"),
                     inside=rid, extra={"data-var": v["name"], **bound})
            svg.close()
            continue
        name = v["name"]
        if v["kind"] == "unset":
            svg.text(xr, y, f"{name} = ?", "mono", size, t["label"], ("chrome", "frame_var_unset"), anchor="end",
                     inside=rid, extra={"data-var": name})
        elif v["kind"] == "value":
            vw = c.value(xr, y, v["fact"], size=size, anchor="end", inside=rid, ocr=False)
            svg.text(xr - vw - size * 0.45, y, f"{name} =", "mono", size, t["ink_soft"], ("chrome", "frame_var_eq"),
                     anchor="end", inside=rid, extra={"data-var": name})
        else:
            sw, sh = size * 1.55, size * 1.45
            sx = xr - sw
            sy = y - size * 1.05
            got = v.get("got")
            svg.raw(f'<rect data-role="slot" x="{sx:.1f}" y="{sy:.1f}" width="{sw:.1f}" height="{sh:.1f}" rx="4" '
                    f'fill="{t["note_tint"] if got else "none"}" stroke="{t["note"]}" stroke-width="1.4"'
                    f'{"" if got else " stroke-dasharray=\"3 3\""}/>')
            if got:
                c.value(sx + sw / 2, y, got, size=size, anchor="middle", inside=rid, ocr=False, color=t["value"])
            label = f"{name} = {v['prefix']}" if v["prefix"] else f"{name} ="
            svg.text(sx - size * 0.45, y, label, "mono", size, t["ink_soft"],
                     ("chrome", "frame_var" if v["prefix"] else "frame_var_eq"), anchor="end", inside=rid,
                     extra={"data-var": name, **(bound if v["prefix"] else {})})
            slot_at = (sx + sw / 2, sy + sh / 2, sx + sw, sy, sh)
    return slot_at


def _after(lesson, sid, after):
    order = [s["id"] for s in lesson.data["trace"]]
    return order.index(sid) >= order.index(after)


class Ctx:
    def __init__(self, svg, lesson, sid, layout, flow=None, notes=True):
        self.svg, self.lesson, self.sid, self.layout = svg, lesson, sid, layout
        self.notes = notes  # the film narrates the panel's claims, so its panel leaves their text out
        self.t = svg.t
        self.S = SIZES[layout]
        self.facts = lesson.by_id("facts")
        self.claims = lesson.by_id("claims")
        self.shown = shown_facts(lesson, sid)
        self.flow = flow
        self.anchors = {}
        self.code_key = False  # the still marks the program text it draws as its "code" key node

    def val(self, fid):
        return text.display(self.facts[fid])

    def on(self, fid):
        return fid in self.shown

    def label(self, x, y, key, anchor="start", color=None, inside=None, keep_case=False, **kw):
        """A chrome label. keep_case: a label that quotes code (%f, (double)a) is never upper-cased, since %F is
        another conversion."""
        svg = self.svg
        font, px, weight, caps, spacing = svg.role("label", self.S["label"])
        caps = caps and not keep_case
        s = text.ui(key, **kw)
        svg.text(x, y, s.upper() if caps else s, font, px, color or self.t["label"], ("chrome", key), weight=weight,
                 spacing=spacing, anchor=anchor, inside=inside)
        return fonts.width(font, px, s.upper() if caps else s, weight=weight) + spacing * len(s)

    def code(self, x, y, s, pid, line=None, size=None, color=None, anchor="start", inside=None):
        size = size or self.S["code"]
        extra = {"data-src-line": line} if line else None
        self.svg.text(x, y, s, "mono", size, color or self.t["ink"], ("code", pid), anchor=anchor, inside=inside,
                      extra=extra)
        return len(s) * size * MONO_ADV

    def value(self, x, y, fid, size=None, color=None, anchor="start", weight=None, inside=None, group=None, ocr=True):
        vfont, vpx, vweight, _c, _s = self.svg.role("value", size or self.S["value"])
        s = self.val(fid)
        col = color or self.t["value"]
        tone = "note" if col == self.t["note"] else ("correction" if col == self.t["correction"] else None)
        self.svg.text(x, y, s, vfont, vpx, col, ("fact", fid), weight=weight or vweight, tone=tone,
                      anchor=anchor, ocr=s if ocr else None, ocr_group=group, inside=inside,
                      raw=text.tight_points(s) if getattr(self.svg, "tight", True) else None)
        return fonts.width(vfont, vpx, s, weight=weight or vweight)

    def note(self, x, y, cid, w, color=None):
        """A claim, wrapped in the note role. Returns the y after it."""
        nfont, npx, nweight, _c, _s = self.svg.role("note", self.S["note"])
        lh = npx * (1.35 if nfont == "hand" else 1.4)
        tone = "correction" if color == self.t["correction"] else "note"
        if self.flow is not None:
            return self.flow.emit(x, y, self.claims[cid]["text"], nfont, npx, lh, color or self.t["note"], ("claim", cid),
                                  w, weight=nweight, tone=tone) - lh
        m0 = self.svg.mark()
        for ln in fonts.wrap(nfont, npx, self.claims[cid]["text"], w, weight=nweight):
            self.svg.text(x, y, ln, nfont, npx, color or self.t["note"], ("claim", cid), weight=nweight, tone=tone)
            y += lh
        self.svg.merge(m0)
        return y - lh

    def note_height(self, cid, w):
        nfont, npx, nweight, _c, _s = self.svg.role("note", self.S["note"])
        lh = npx * (1.35 if nfont == "hand" else 1.4)
        return len(fonts.wrap(nfont, npx, self.claims[cid]["text"], w, weight=nweight)) * lh

    def group(self, fid=None, after=None, implies=None, **extra):
        """A fact-bound group. `implies`: facts its geometry gives away even though it prints no value (a bar
        whose end is the sum); the answer gates treat it like a shown value (round 18). `extra`: more attributes,
        such as the mechanism markup's data_part (AC-10.2)."""
        attrs = dict(extra)
        if fid:
            attrs["data_m"] = fid
        if after:
            attrs["data_mstate"] = after
        if implies:
            attrs["data_implies"] = " ".join(implies)
        self.svg.open(**attrs)


# ---------------------------------------------------------------- views

def _mem_row(c, x, y, w, var, ctype, fids, size_fid, low_offset=None):
    """One object's bytes in memory, lowest address first (AC-10.2 bytes): data-part bytes data-var=<var>, one
    data-part byte cell per byte (data-offset, its captured fact), the least significant byte marked data-low. The
    offsets under the cells ("+0", "+1", ...) are the ticks of an address axis. Returns {"y": the y after the row,
    "top", "bottom": the cells' top and bottom, "right": the x after the last cell}."""
    svg, t, S = c.svg, c.t, c.S
    n = len(fids)
    gap = 6 * S["k"]
    cw = min(72 * S["k"], (w - 7 * gap) / 8)  # one cell width for every row, so offsets line up
    ch = round(cw * 0.95, 1)
    y += S["label"]
    lab = text.ui("mem_row", var=var, ctype=ctype, n=c.val(size_fid))
    font, px, weight, _caps, spacing = svg.role("label", S["label"])
    svg.text(x, y, lab, font, px, t["label"], ("chrome", "mem_row"), weight=weight,  # quotes code: never upper-cased
             spacing=spacing, extra={"data-from-fact": size_fid})
    y += 12
    vfont, vpx, vweight, _c, _s = svg.role("value", min(S["value"], cw * 0.46))
    svg.open(data_part="bytes", data_var=var)
    for k, fid in enumerate(fids):
        cx = x + k * (cw + gap)
        low = k == low_offset
        rid = f"cell-{c.layout}-{re.sub(r'[^a-z0-9]', '', var)}-{k}"
        svg.open(data_part="byte", data_offset=k, **({"data_low": "true"} if low else {}))
        svg.raw(f'<rect id="{rid}" x="{cx:.1f}" y="{y:.1f}" width="{cw:.1f}" height="{ch}" rx="6" '
                f'fill="{t["note_tint"] if low else "none"}" stroke="{t["note"] if low else t["rule"]}" '
                f'stroke-width="{2 if low else 1.2}"/>')
        svg.text(cx + cw / 2, y + ch / 2 + vpx * 0.36, c.val(fid), vfont, vpx, t["note"] if low else t["value"],
                 ("fact", fid), weight=vweight, anchor="middle", inside=rid)
        svg.close()
    svg.close()
    top, bottom = y, y + ch
    y += ch + S["label"] + 6
    ffont, fpx, _w, _c, _s = svg.role("foot", S["label"])
    for k in range(n):
        svg.text(x + k * (cw + gap) + cw / 2, y, text.ui("mem_byte", k=k), ffont, fpx, t["faint"], ("chrome", "mem_byte"),
                 anchor="middle", extra={"data-axis": f"offset-{var}", "data-tick": k})
    return {"y": y + 8, "top": top, "bottom": bottom, "right": x + n * (cw + gap) - gap}


def _low_byte(c, x, y, w, v, label_first=False):
    """The low byte as a tape (eight digits over bars, note for a 1) and its hex form; returns the y after. With
    label_first, its label sits above the tape (beside a's cells); else under it."""
    svg, t, S = c.svg, c.t, c.S
    if label_first:
        y += S["label"]
        c.label(x, y, "panel_byte_note")
        y += 2
    c.group(v["bits"])
    # the byte as a tape: eight digits, each over a bar (note for a 1, rule for a 0), the bars kept clear of
    # the digits so OCR reads the digits alone
    vfont, vpx, vweight, _c, _s = svg.role("value", S["value"] * (1.08 if label_first else 1.15))
    adv = fonts.width(vfont, vpx, "0", weight=vweight)
    gap = round(vpx * 0.22, 1)
    bits = c.val(v["bits"])
    bx, base = x, y + vpx + 8
    spans = "".join(f'<tspan fill="{t["note"] if b == "1" else t["label"]}">{b}</tspan>' for b in bits)
    svg.text(bx, base, bits, vfont, vpx, t["ink"], ("fact", v["bits"]), weight=vweight, ocr=bits, raw=spans,
             extra={"letter-spacing": f"{gap:.2f}"})
    for i, b in enumerate(bits):
        bar_x = bx + i * (adv + gap)
        svg.line(bar_x + 1, base + 20, bar_x + adv - 1, base + 20, t["note"] if b == "1" else t["rule"],
                 4 if b == "1" else 2, role="path")
    svg.close()
    hx = bx + 8 * (adv + gap) + 18
    if c.on(v["hex"]) and hx + 60 * S["k"] <= x + w:
        c.group(v["hex"])
        c.value(hx, base, v["hex"], color=t["note"])
        svg.close()
    y = base + 26
    if not label_first:
        c.label(x, y + S["label"] + 2, "panel_byte_note")
        y += S["label"] + 10
    return y


def _memory(c, x, y, w):
    """The value in memory (shared by the still and the film): its declaration, a's bytes with the low byte marked
    and spelled out as bits and hex (beside the cells when there is room), then the bytes of the new double
    (double)a and the hex they spell when read from the highest address down. Returns the y after."""
    svg, t, S, lesson = c.svg, c.t, c.S, c.lesson
    P = lesson.data["figure"]["panel"]
    v, M = P["value"], P.get("memory") or {}
    pid = lesson.data["figure"]["program"]
    src = lesson.program_source(pid).split("\n")
    endian = _platform_fact(lesson, "endianness")
    little = c.val(endian) == "little" if endian else True
    if v.get("line"):
        y += S["code"] * 1.1
        if c.code_key:
            svg.open(data_key="code")
        c.code(x, y, src[v["line"] - 1].strip(), pid, v["line"])
        if c.code_key:
            svg.close()
        y += 10
    bits_done = False
    if M and all(c.on(f) for f in M["int"]):
        n = len(M["int"])
        row = _mem_row(c, x, y + 8, w, v["var"], "int", M["int"], _size_fact(lesson, "int"),
                       low_offset=0 if little else n - 1)
        if c.on(v["bits"]) and x + w - row["right"] >= 250 * S["k"]:
            _low_byte(c, row["right"] + 30 * S["k"], row["top"] - S["label"] - 14,
                      x + w - row["right"] - 30 * S["k"], v, label_first=True)
            bits_done = True
        y = row["y"]
    if c.on(v["bits"]) and not bits_done:
        y = _low_byte(c, x, y, w, v)
    if M and all(c.on(f) for f in M["double"]):
        row = _mem_row(c, x, y + 22 * S["k"], w, f"(double){v['var']}", "double", M["double"], _size_fact(lesson, "double"))
        y = row["y"]
        dbits = next((ln.get("via") for ln in P.get("lanes", []) if ln.get("via")), None)
        if dbits and c.on(dbits):
            # the reading direction: from the highest address (the last cell) down to the lowest
            cw = (row["right"] - x - 7 * 6 * S["k"]) / 8
            ay = y + 4
            x0_, x1_ = row["right"] - cw / 2, x + cw / 2
            _curve_arrow(c, (x0_, ay), (x0_ - 10, ay), (x1_ + 10, ay), (x1_, ay), t["note"], 2)
            y += 8
            y += S["value"] * 0.9
            lw = c.label(x, y - 3, "mem_read_down")
            vf0, vp0, vw0, _c0, _s0 = svg.role("value", S["value"] * 0.8)
            if x + lw + 12 + fonts.width(vf0, vp0, c.val(dbits), weight=vw0) > x + w:  # no room beside its label
                y += S["value"] * 1.1
                lw = -12
            c.value(x + lw + 12, y, dbits, size=S["value"] * 0.8, color=t["note"], ocr=False)
            y += 8
            fprint = next((ln["fact"] for ln in P.get("lanes", []) if ln.get("via") == dbits), None)
            if fprint and c.on(fprint):  # what %f makes of this double
                y += S["value"] * 1.2
                lw = c.label(x, y - 3, "mem_prints", keep_case=True)
                c.value(x + lw + 12, y, fprint, size=S["value"] * 0.9, ocr=False)
                y += 8
    return y


def _memory_panel(c, x, y, w):
    """The still's mechanism for a views lesson: the value in memory."""
    y0 = y
    y += c.S["label"]
    c.label(x, y, "mem_label")
    y += 6
    return _memory(c, x, y, w) - y0


def _platform_fact(lesson, key):
    return next((f["id"] for f in lesson.data["facts"] if f["select"].get("stream") == "platform"
                 and f["select"].get("key") == key), None)


def _size_fact(lesson, ctype):
    return _platform_fact(lesson, f"sizeof.{ctype}")


def _views(c, x, y, w):
    svg, t, S, lesson = c.svg, c.t, c.S, c.lesson
    P = lesson.data["figure"]["panel"]
    pid = lesson.data["figure"]["program"]
    src = lesson.program_source(pid).split("\n")
    y0 = y
    # the value: its declaration, its bytes in memory, its low byte as eight bit cells and the hex form
    y += S["label"]
    c.label(x, y, "panel_value")
    y += 14
    y = _memory(c, x, y, w)
    # one lane per conversion
    for lane in P["lanes"]:
        if not c.on(lane["fact"]):
            continue
        y += 40
        c.group(lane["fact"])
        svg.line(x, y - 24, x + w, y - 24, t["rule"], 1)
        y += S["code"] * 0.9
        code_w = c.code(x, y, src[lane["line"] - 1].strip(), pid, lane["line"])
        if lane.get("via") and c.on(lane["via"]):
            y += S["value"] * 1.35
            lw = c.label(x + 18, y - 3, "lane_converts")
            vfont0, vpx0, vw0, _c0, _s0 = svg.role("value", S["value"] * 0.8)
            via_w = fonts.width(vfont0, vpx0, c.val(lane["via"]), weight=vw0)
            if x + 18 + lw + 12 + via_w > x + w:  # too wide beside its label (portrait): the value goes under it
                y += S["value"] * 1.05
                c.value(x + 18, y, lane["via"], size=S["value"] * 0.8, color=t["note"], ocr=False)
            else:
                c.value(x + 18 + lw + 12, y, lane["via"], size=S["value"] * 0.8, color=t["note"], ocr=False)
            code_w = None
        vfont, vpx, vweight, _c, _s = svg.role("value", S["value"])
        val_w = fonts.width(vfont, vpx, c.val(lane["fact"]), weight=vweight)
        if code_w is not None and x + code_w + 26 + val_w <= x + w:
            # the output fits on the code line: arrow, then the value
            ax = x + code_w + 8
            svg.text(ax, y, "\u2192", "mono", S["code"], t["label"], ("chrome", "arrow"))
            c.value(x + w, y + 1, lane["fact"], anchor="end", ocr=c.layout == "wide")
        else:
            y += S["value"] * 1.35
            lw = c.label(x + 18, y - 3, "lane_prints")
            c.value(x + 18 + lw + 12, y, lane["fact"], ocr=c.layout == "wide")
        if lane.get("claim") and c.notes:
            y = c.note(x + 18, y + S["note"] * 1.5, lane["claim"], w - 18)
        svg.close()
    ub = P.get("ub")
    if ub and _after(lesson, c.sid, ub["after"]):
        usrc = lesson.program_source(ub["program"]).split("\n")
        y += 44
        c.group(after=ub["after"])
        svg.line(x, y - 24, x + w, y - 24, t["correction"], 1.2)
        fname = lesson.program(ub["program"])["path"].split("/")[-1]
        ffont, fpx, _w, _c, _s = svg.role("foot", S["label"])
        svg.text(x, y + 2, fname, ffont, fpx, t["label"], ("label", "program-file"))
        lw = c.label(x + w, y + 2, "lane_undefined", anchor="end", color=t["correction"])
        del lw
        y += S["code"] * 1.4
        c.code(x, y, usrc[ub["line"] - 1].strip(), ub["program"], ub["line"], color=t["correction"])
        if c.notes:
            y = c.note(x, y + S["note"] * 1.5, ub["claim"], w, color=t["correction"])
        svg.close()
    return y - y0 + 10


# ---------------------------------------------------------------- stack

STACK_GUTTER = 40  # the calls rail at the left of the column, the returns rail at the right


def _stack_geom(c, w):
    """(frame height, gap, call gutter, return gutter, frame width) of a stack column of width w."""
    S = c.S
    vars_on = bool(c.lesson.data["figure"]["panel"].get("vars"))
    fh = round(S["value"] * (3.4 if vars_on else 2.3))
    gl, gr = STACK_GUTTER * S["k"], (STACK_GUTTER + 16) * S["k"]
    return fh, 14, gl, gr, w - gl - gr


def _stack_frame(c, x, fy, bw, fh, fr, idx, sid, status, rid, ret_shown):
    """One frame of the stack column (AC-10.2 stack-column): data-part frame with data-call (its call fact, or main),
    its call, its own n and r, and (ret_shown) a data-part ret with the value it returns. Returns (slot geometry,
    centre of the returned value)."""
    svg, t, S = c.svg, c.t, c.S
    pid = c.lesson.state(sid)["state"]["program"]
    vars_on = bool(c.lesson.data["figure"]["panel"].get("vars"))
    returning = status == "returning"
    c.group(fr.get("ret") if returning else fr.get("call"), data_part="frame", data_call=fr.get("call") or "main")
    dash = ' stroke-dasharray="6 5"' if returning else ""
    fill = t["note_tint"] if status == "running" else (t["surface"] if status in ("waiting", "done") else t["ground"])
    edge = t["rule"] if status in ("waiting", "done") else t["note"]
    svg.raw(f'<rect id="{rid}" data-role="frame" x="{x:.1f}" y="{fy:.1f}" width="{bw:.1f}" height="{fh}" rx="10" '
            f'fill="{fill}" stroke="{edge}" stroke-width="1.5"{dash}/>')
    ty = fy + (S["value"] * 1.25 if vars_on else fh / 2 + S["value"] * 0.33)
    if fr.get("call"):
        c.value(x + 16, ty, fr["call"], color=t["ink"], size=S["value"] * 0.8, inside=rid, ocr=False)
    else:
        c.code(x + 16, ty, fr["fn"], pid, size=S["value"] * 0.8, inside=rid)
    ret_at = None
    if ret_shown and fr.get("ret"):
        svg.open(data_part="ret")
        vw = fonts.width("mono", S["value"], c.val(fr["ret"]))
        c.value(x + bw - 16, ty, fr["ret"], anchor="end", inside=rid, ocr=False)
        c.label(x + bw - 16 - vw - 10, ty - 2, "frame_returns", anchor="end", color=t["note"], inside=rid)
        svg.close()
        ret_at = (x + bw - 16 - vw / 2, ty - S["value"] * 0.35)
    elif status != "done":
        c.label(x + bw - 16, ty - 2, "frame_" + status, anchor="end",
                color=t["note"] if status == "running" else t["label"], inside=rid)
    slot = None
    if vars_on:
        vy = fy + fh - S["value"] * 0.62
        slot = _vars_row(c, x + 16, vy, x + bw - 16, sid, idx, S["code"], rid)
    svg.close()
    return slot, ret_at


def _curve_arrow(c, p0, c1, c2, p1, color, sw):
    """A curved shaft and its arrowhead, drawn as its own small triangle (no SVG marker: the film's layout audit
    takes a marked shaft for an HTML connector). The shaft is the first path, so its ends are the curve's ends."""
    import math
    c.svg.path(f"M{p0[0]:.1f},{p0[1]:.1f} C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p1[0]:.1f},{p1[1]:.1f}",
               color, sw)
    ang = math.atan2(p1[1] - c2[1], p1[0] - c2[0])
    L, W = 4 * sw, 2.2 * sw
    tip = (p1[0] + math.cos(ang) * sw, p1[1] + math.sin(ang) * sw)
    bx, by = tip[0] - math.cos(ang) * L, tip[1] - math.sin(ang) * L
    ox, oy = -math.sin(ang) * W, math.cos(ang) * W
    c.svg.raw(f'<path data-role="path" d="M{tip[0]:.1f},{tip[1]:.1f} L{bx + ox:.1f},{by + oy:.1f} L{bx - ox:.1f},{by - oy:.1f} Z" '
              f'fill="{color}"/>')


def _call_arrow(c, x, y_from, y_to):
    """The call going down the left rail: from the caller's frame to its callee's, one frame lower."""
    k = 18 * c.S["k"]
    _curve_arrow(c, (x, y_from), (x - k, y_from), (x - k, y_to), (x - 6, y_to), c.t["label"], 1.8)


def _return_arrow(c, ax, y_from, slot, caller_y, callee_call, caller_call, gr):
    """A returned value going up the right rail: from the callee's frame to the slot of its caller, one frame higher
    (data-part return, data-from callee, data-to caller). The line starts at the callee and ends higher, at the caller."""
    t = c.t
    c.svg.open(data_part="return", data_from=callee_call, data_to=caller_call or "main")
    if slot:
        _cx, sy, sx_right, _sy, _sh = slot
        _curve_arrow(c, (ax - 2, y_from), (ax + gr - 14, y_from), (ax + gr - 14, sy), (sx_right + 9, sy), t["note"], 2.5)
    else:
        _curve_arrow(c, (ax, y_from), (ax + gr - 14, y_from), (ax + gr - 14, caller_y), (ax + 7, caller_y), t["note"], 2.5)
    c.svg.close()


def _stack_head(c, x, y, w):
    S = c.S
    y += S["label"]
    c.label(x, y, "stack_label")
    font, px, weight, caps, spacing = c.svg.role("label", S["label"])
    need = sum(fonts.width(font, px, text.ui(k).upper(), weight=weight) + spacing * len(text.ui(k))
               for k in ("stack_label", "stack_order")) + 24
    if c.layout != "wide" or need > w:  # no room for both on one line
        y += S["label"] * 1.6
        c.label(x, y, "stack_order")
    else:
        c.label(x + w, y, "stack_order", anchor="end")
    return y + 16


def _stack(c, x, y, w):
    """The call stack at one trace state, as one column: main at the top, each call one frame below its caller.
    Calls go down the left rail; a returning frame's value goes up the right rail into its caller's slot. Frames
    hang from a fixed top, so they never move as others come and go."""
    svg, lesson = c.svg, c.lesson
    st = lesson.state(c.sid)["state"]
    frames = st.get("frames", [])
    y0 = y
    y = _stack_head(c, x, y, w)
    fh, gap, gl, gr, bw = _stack_geom(c, w)
    fx = x + gl
    depth = max(len(s["state"].get("frames", [])) for s in lesson.data["trace"])
    n = len(frames)
    tops = [y + i * (fh + gap) for i in range(n)]
    slots, rets = {}, {}
    for i, fr in enumerate(frames):
        status = fr.get("status", "running" if i == n - 1 else "waiting")
        rid = f"frame-{c.layout}-{c.sid}-{i}"
        slot, ret_at = _stack_frame(c, fx, tops[i], bw, fh, fr, i, c.sid, status, rid, status == "returning")
        if slot:
            slots[i] = slot
        if ret_at:
            rets[i] = ret_at
    for i in range(1, n):
        _call_arrow(c, fx, tops[i - 1] + fh * 0.5, tops[i] + fh * 0.3)
    for i in rets:
        if i == 0:
            continue
        _return_arrow(c, fx + bw + 6, tops[i] + fh * 0.5, slots.get(i - 1), tops[i - 1] + fh / 2,
                      frames[i].get("call"), frames[i - 1].get("call"), gr)
    c.anchors = {"rets": rets, "slots": {k: (v[0], v[1]) for k, v in slots.items()}}
    y += depth * (fh + gap) - gap
    for cid in lesson.data["figure"]["panel"].get("claims", []):
        y = c.note(x, y + c.S["note"] * 2, cid, w)
    return y - y0 + 10


def run_frames(lesson):
    """The whole run as one column (the still and the film's summary): [(frame, state id, index)] from main down to
    the deepest call. Each call is taken at the state where it returns (its n, its r and the value it returns);
    main is taken at the last state, holding what it received."""
    trace = lesson.data["trace"]
    out, seen = [], set()
    deepest = max(trace, key=lambda s: len(s["state"].get("frames", [])))
    for i, fr in enumerate(deepest["state"]["frames"]):
        key = fr.get("call") or "main"
        if key in seen:
            continue
        seen.add(key)
        pick = None
        for s in trace:
            for j, f2 in enumerate(s["state"].get("frames", [])):
                if (f2.get("call") or "main") == key and (f2.get("status") == "returning" if f2.get("call")
                                                          else f2.get("got")):
                    pick = (f2, s["id"], j)
        out.append(pick or (fr, deepest["id"], i))
    return out


def _stack_run(c, x, y, w, fit_h=None):
    """Every call of the run in one column (AC-10.2): main at the top, each call below its caller, each frame with its
    own n, its r and what it returns, and every returned value going up the right rail into its caller's r."""
    svg = c.svg
    y0 = y
    y = _stack_head(c, x, y, w)
    fh, gap, gl, gr, bw = _stack_geom(c, w)
    fx = x + gl
    rows = run_frames(c.lesson)
    foot = c.S["label"] + 14
    if fit_h:  # frames grow to the height of what stands beside the column, within reason
        fh = round(min(fh * 1.3, max(fh, (fit_h - (y - y0) - foot - gap * (len(rows) - 1)) / len(rows))))
    tops = [y + i * (fh + gap) for i in range(len(rows))]
    slots = {}
    for i, (fr, sid, j) in enumerate(rows):
        rid = f"frame-{c.layout}-run-{i}"
        slot, _r = _stack_frame(c, fx, tops[i], bw, fh, fr, j, sid, "done", rid, True)
        slots[i] = slot
    for i in range(1, len(rows)):
        _call_arrow(c, fx, tops[i - 1] + fh * 0.5, tops[i] + fh * 0.3)
        _return_arrow(c, fx + bw + 6, tops[i] + fh * 0.62, slots.get(i - 1), tops[i - 1] + fh / 2,
                      rows[i][0].get("call"), rows[i - 1][0].get("call"), gr)
    y = tops[-1] + fh + c.S["label"] + 10
    c.label(fx - gl + 2, y, "stack_calls", color=c.t["label"])
    c.label(fx + bw + gr, y, "stack_returns", anchor="end", color=c.t["note"])
    return y + 4 - y0


# ---------------------------------------------------------------- control path (switch)

def control_rows(lesson, pid):
    """The switch program as the rows of its path figure (the explorer's parse): [{"kind", "lines", "label"}]. Row
    kinds: head (the declaration and the switch line), case (a label and its statements), break, tail (after the
    switch). Every line of a row is a source line of `pid`."""
    from .explorer import parse_switch
    lay = parse_switch(lesson.program_source(pid), pid)
    rows = [{"kind": "head", "lines": [lay["n_line"], lay["switch_line"]], "label": None}]
    for cs in lay["cases"]:
        rows.append({"kind": "case", "lines": [cs["line"], *cs["stmts"]], "label": cs["line"]})
        if cs["brk"]:
            rows.append({"kind": "break", "lines": [cs["brk_line"]], "label": None})
    rows += [{"kind": "tail", "lines": [tl["line"]], "label": None} for tl in lay["tail"]]
    return rows, lay


def path_marks(lesson, pid, path):
    """Where control enters, falls and leaves on `path` (the explorer's path logic, path.py): enter is the first case
    label on the path, fall every later one, leave the last path line inside the switch body."""
    _rows, lay = control_rows(lesson, pid)
    labels = [cs["line"] for cs in lay["cases"]]
    entered = [n for n in path if n in labels]
    body = [n for n in path if lay["switch_line"] < n < lay["close_line"]]
    left = any(n >= lay["close_line"] for n in path)  # control has gone past the switch
    return {"enter": entered[0] if entered else None, "fall": entered[1:], "leave": body[-1] if body and left else None}


def _control_path(c, x, y, w, only_ran=False, head=True, fit_h=None):
    """The path through the switch at one trace state (AC-10.2 control-path): one row per case (its label and
    statements), the break and the line after the switch, in source order; the path rail with a dot on every row that
    ran, a jump into the case control enters, a straight run through every label it falls past to the line where it
    leaves, and a jump out; each printed value beside the statement that printed it."""
    svg, t, S, lesson = c.svg, c.t, c.S, c.lesson
    st = lesson.state(c.sid)["state"]
    pid = st["program"]
    src = lesson.program_source(pid).split("\n")
    path = st.get("path", [])
    rows, lay = control_rows(lesson, pid)
    if only_ran:  # a comparison: only the rows its path runs through
        rows = [r for r in rows if any(n in path for n in r["lines"])]
    marks = path_marks(lesson, pid, path)
    wide = c.layout == "wide"
    size = round(S["code"] * (1.2 if wide else 0.98), 2)
    rh = round(size * (3.15 if wide else 4.6), 1)
    ch = round(size * 2.0, 1)
    num = max(11.6, round(size * 0.78, 2))
    rail = x + 12
    cx0 = x + 34 * S["k"]
    y0 = y
    if head:
        y += S["label"]
        c.label(x, y, "x_flow_label")
        y += 18
    if fit_h:  # rows spread to the height of what stands beside the figure, within reason
        rh = round(min(size * 4.0, max(rh, (fit_h - (y - y0) - ch - 8) / max(1, len(rows) - 1))), 1)
    tops = [y + i * rh for i in range(len(rows))]
    mid = lambda i: tops[i] + ch / 2  # noqa: E731
    ran = [i for i, r in enumerate(rows) if any(n in path for n in r["lines"])]
    printed = rail_print(src, path, [c.val(f) for f in st.get("output", [])])
    vfont, vpx, vweight, _c, _s = svg.role("value", S["value"] * (0.92 if wide else 0.8))
    out_x = x + w - max([fonts.width(vfont, vpx, c.val(f), weight=vweight) for f in st.get("output", [])] + [0])
    tfont, tpx, tweight, _c2, _s2 = svg.role("tag", max(12, round(size * 0.82, 1)))
    row_of = {n: i for i, r in enumerate(rows) for n in r["lines"]}
    ends = {}
    # the rows: one chip per source line, the first chip of a row numbered with its line
    if c.code_key:
        svg.open(data_key="code")
    for i, r in enumerate(rows):
        on = i in ran
        cx = cx0 + (0 if r["kind"] in ("head", "case", "tail") else 26 * S["k"])
        for k, n in enumerate(r["lines"]):
            s_ = src[n - 1].strip()
            rid = f"cp-{c.layout}-{c.sid}-{n}"
            tw = fonts.width("mono", size, s_) + (fonts.width("mono", num, str(n)) + 10 if k == 0 else 0) + 20
            part = {"data_part": "label", "data_line": n} if r["kind"] == "case" and k == 0 else {}
            svg.open(**part)
            dash = "" if on else ' stroke-dasharray="4 4"'
            svg.raw(f'<rect id="{rid}" x="{cx:.1f}" y="{tops[i]:.1f}" width="{tw:.1f}" height="{ch}" rx="7" '
                    f'fill="{t["highlight"] if on and n in path else "none"}" stroke="{t["note"] if on and n in path else t["rule"]}" '
                    f'stroke-width="1.3"{dash}/>')
            tx = cx + 10
            if k == 0:
                svg.text(tx, mid(i) + num * 0.35, str(n), "mono", num, t["label"], ("label", "line-number"), inside=rid,
                         extra={"data-line": n, "data-axis": "source-line", "data-tick": n})
                tx += fonts.width("mono", num, str(n)) + 10
            svg.text(tx, mid(i) + size * 0.35, s_, "mono", size, t["ink"] if on else t["label"], ("code", pid),
                     inside=rid, extra={"data-src-line": n})
            svg.close()
            cx += tw + 8
        ends[i] = cx
    if c.code_key:
        svg.close()
    # the rail: dots on the rows that ran, jumps in and out, the path from enter to leave
    for i in ran:
        svg.circle(rail, mid(i), 5 if wide else 4, t["note"])
    if marks["enter"]:
        # the path proper: from the label control enters to the line where it leaves (or, mid-run, to where it is)
        a = row_of[marks["enter"]]
        body = [i for i in ran if i >= a and rows[i]["kind"] != "tail"]
        b = row_of[marks["leave"]] if marks["leave"] else max(body)
        svg.open(data_part="path")
        svg.line(rail, mid(a), rail, mid(b), t["note"], 4, role="path")
        svg.close()
        bulge = rail - 18 * S["k"]
        if ran and ran[0] < a:
            _curve_arrow(c, (rail, mid(ran[0])), (bulge, mid(ran[0])), (bulge, mid(a)), (rail - 6, mid(a)), t["note"], 2.5)
        after = [i for i in ran if i > b]
        if after and marks["leave"]:
            _curve_arrow(c, (rail, mid(b)), (bulge, mid(b)), (bulge, mid(after[0])), (rail - 6, mid(after[0])),
                         t["note"], 2.5)

    tag_end, tag_at = {}, {}

    def tag(i, key, part, line, tone):
        col = {"path": t["note"], "warn": t["correction"], "muted": t["label"]}[tone]
        s_ = text.ui(key)
        tw = fonts.width(tfont, tpx, s_, weight=tweight)
        tx, ty = ends[i] + 6, mid(i) + tpx * 0.35
        if tx + tw > out_x - 30:  # no room beside the row (portrait): under its chips
            tx, ty = cx0 + 4, tops[i] + ch + tpx * 1.15
        svg.open(**({"data_part": part, "data_line": line} if part else {}))
        svg.text(tx, ty, s_, tfont, tpx, col, ("chrome", key), weight=tweight,
                 tone={"path": "note", "warn": "correction"}.get(tone))
        svg.close()
        tag_end[i] = tx + tw if ty < tops[i] + ch else ends[i]
        tag_at[i] = (tx + tw, ty - tpx * 0.35)
    if marks["enter"]:
        tag(row_of[marks["enter"]], "enter_label", "enter", marks["enter"], "path")
    for n in marks["fall"]:
        i = row_of[n]
        svg.line(rail, mid(i - 1) + 7, rail, mid(i) - 7, t["correction"], 4, role="path")
        tag(i, "x_tag_fall", "fall", n, "warn")
    if marks["leave"]:
        i = row_of[marks["leave"]]
        leave_break = rows[i]["kind"] == "break"
        tag(i, "exit_label" if leave_break else "x_tag_end", "leave", marks["leave"], "path")
    for i, r in enumerate(rows):
        if r["kind"] == "case" and i not in ran and ran and ran[0] < i < ran[-1]:
            tag(i, "skipped_label", None, None, "muted")
    # what each row printed, in output order: one column just clear of the rows and their tags (wide), or at the
    # right edge (portrait)
    if wide and printed:
        lim = x + w - max([fonts.width(vfont, vpx, c.val(f), weight=vweight) for f in st["output"]] + [0])
        out_x = min(lim, max(tag_end.get(i, ends[i]) for i in [row_of[n] for n in printed if n in row_of]) + 70)
    if st.get("output"):
        svg.open(data_key="output", data_state=c.sid)
        for fid, n in zip(st["output"], printed or []):
            i = row_of.get(n)
            if i is None:
                continue
            svg.text(out_x - 12, mid(i) + size * 0.35, "\u2192", "mono", size, t["label"], ("chrome", "arrow"),
                     anchor="end")
            c.value(out_x, mid(i) + vpx * 0.36, fid, size=S["value"] * (0.92 if wide else 0.8), ocr=c.layout == "wide",
                    group="cp-out")
        svg.close()
    # where a note about a line can put its badge: after the row's tag, else after its chips (still.py draws the
    # badges, outside the mechanism: a note number is not a value)
    c.anchors = {"badge": {n: tag_at.get(i, (ends[i] - 2, mid(i))) for i, r in enumerate(rows) for n in r["lines"]}}
    return tops[-1] + ch + 8 - y0


def rail_print(src, path, outputs):
    from . import path as rail_mod
    return rail_mod.print_lines(src, path, outputs)


# ---------------------------------------------------------------- neuron

def _neuron(c, x, y, w):
    svg, t, S, lesson = c.svg, c.t, c.S, c.lesson
    P = lesson.data["figure"]["panel"]
    pid = lesson.data["figure"]["program"]
    src = lesson.program_source(pid).split("\n")
    wide = c.layout == "wide"
    gap = 48 if wide else 0
    cw = (w - 2 * gap) / 3 if wide else w
    cols = [(x + i * (cw + gap), y) for i in range(3)]
    col_h = 280 if wide else None
    big = S["big"]
    tone = lambda fid: t["note"] if number(c.val(fid)) >= 0 else t["correction"]  # noqa: E731
    heights = []

    # ---- multiply
    cx, cy = cols[0]
    svg.open(data_part="panel", data_panel="multiply")
    yy = cy + S["label"]
    c.label(cx, yy, "panel_multiply")
    yy += 20
    rows = [(i, tm) for i, tm in enumerate(P["terms"], 1)] + [(0, None)]
    for i, tm in rows:
        yy += S["note"] * 1.6
        if tm is None:
            if not c.on(P["bias"]):
                break
            c.group(P["bias"])
            c.label(cx, yy, "neuron_bias")
            c.label(cx, yy + S["code"] * 1.7, "neuron_added")
            c.value(cx + cw, yy + S["code"] * 1.2, P["bias"], size=big, color=tone(P["bias"]), anchor="end")
            svg.close()
        else:
            if not c.on(tm["x"]):
                break
            c.group(tm["x"])
            c.label(cx, yy, "neuron_input", i=i)
            vy = yy + S["code"] * 1.7
            xw = c.value(cx, vy, tm["x"], size=S["value"] * 0.85, color=t["ink"], ocr=False)
            svg.text(cx + xw + 10, vy, text.ui("times"), "mono", S["value"] * 0.85, t["label"], ("chrome", "times"))
            c.value(cx + xw + 12 + S["value"] * 0.85 * MONO_ADV + 10, vy, tm["w"], size=S["value"] * 0.85, color=t["ink"],
                    ocr=False)
            svg.close()
            if c.on(tm["t"]):
                c.group(tm["t"])
                c.value(cx + cw, yy + S["code"] * 1.2, tm["t"], size=big, color=tone(tm["t"]), anchor="end")
                svg.close()
        yy += S["code"] * 1.7 + 18
        svg.line(cx, yy, cx + cw, yy, t["rule"], 1)
    svg.close()
    heights.append(yy - cy)

    # ---- add: the running sum along a number line
    cx, cy = cols[1] if wide else (x, cy + heights[0] + 40)
    if not wide:
        svg.line(x, cy - 20, x + w, cy - 20, t["rule"], 1)
    svg.open(data_part="panel", data_panel="add")
    yy = cy + S["label"]
    c.label(cx, yy, "panel_add")
    terms = [tm["t"] for tm in P["terms"]] + [P["bias"]]
    vals = [number(c.val(f)) for f in terms]
    ends, s = [], 0.0
    for v in vals:
        ends.append((s, s + v))
        s += v
    lo = min(0.0, min(a for e in ends for a in e)) - 0.5
    hi = max(0.0, max(a for e in ends for a in e)) + 0.4
    lo, hi = round(lo * 2) / 2, round(hi * 2) / 2
    X = lambda v: cx + 10 + (v - lo) / (hi - lo) * (cw - 20)  # noqa: E731
    row = S["value"] * 1.9
    by = yy + 30
    for k, (fid, (a, b)) in enumerate(zip(terms, ends)):
        # a bar starts where the one before it ends, and the bars are the adding step: they appear with the sum
        # (round 18: during Multiply they gave the sum away by geometry, ahead of the Add scene)
        if not c.on(P["sum"]) or not all(c.on(f) for f in terms[:k + 1]):
            continue
        c.group(fid, implies=[P["sum"], P["out"]] if k == len(terms) - 1 else None)
        ry = by + k * row + S["value"]
        col = tone(fid)
        svg.line(X(a), ry, X(b), ry, col, 9, role="path")
        # each end is an anchor of the axis: the gates check it sits where the tick scale puts the value the
        # facts give (claims.axis_anchor_problems), so ticks shifted all together cannot pass
        for xx, expr in ((X(a), "+".join(terms[:k]) or "0"), (X(b), "+".join(terms[:k + 1]))):
            svg.raw(f'<circle data-role="path" data-axis-anchor="add" data-anchor="{expr}" cx="{xx:.1f}" cy="{ry:.1f}" '
                    f'r="5.5" fill="{col}"/>')
        lab = text.ui("neuron_term_bias") if k == len(terms) - 1 else text.ui("neuron_term", i=k + 1)
        lw = fonts.width("mono", S["chip"] + 2, lab)
        vw = fonts.width("mono", S["chip"] + 4, c.val(fid))
        total = lw + 10 + vw
        # beside the bar on its left when there is room (clear of the guide from the bar above), else above it
        if X(min(a, b)) - 16 - total >= cx:
            label_x, label_y = X(min(a, b)) - 16 - total, ry + 5
        else:
            label_x, label_y = min(max(X(min(a, b)), cx), cx + cw - total), ry - 14
        svg.text(label_x, label_y, lab, "mono", S["chip"] + 2, col, ("chrome", "neuron_term_bias" if k == len(terms) - 1
                                                                       else "neuron_term"))
        c.value(label_x + lw + 10, label_y, fid, size=S["chip"] + 4, color=col, ocr=False)
        if k:
            svg.raw(f'<line data-role="guide" x1="{X(a):.1f}" y1="{ry - row:.1f}" x2="{X(a):.1f}" y2="{ry:.1f}" '
                    f'stroke="{t["label"]}" stroke-width="1" stroke-dasharray="3 4"/>')
        svg.close()
    ay = by + len(terms) * row + 10
    svg.line(cx + 10, ay, cx + cw - 10, ay, t["rule"], 1.2)
    ffont, fpx, _w, _c, _s = svg.role("foot", S["label"])
    for v in (lo, 0.0, hi):
        svg.line(X(v), ay - 5, X(v), ay + 5, t["rule"], 1.2)
        lab = f"{v:g}".replace("-", "−")
        svg.text(X(v), ay + 22, lab, ffont, fpx, t["label"], ("label", "axis-tick"), anchor="middle",
                 extra={"data-axis": "add", "data-tick": f"{v:g}"})
    yy = ay + 42
    if all(c.on(f) for f in terms) and c.on(P["sum"]):
        # z = t1 t2 b: the sum written out from the terms it adds
        zx = cx + c.code(cx, yy, "z =", pid, size=S["code"]) + 10
        for f in terms:
            c.group(f)
            zx += c.value(zx, yy, f, size=S["code"] * 1.05, color=tone(f), ocr=False) + 10
            svg.close()
        yy += 22
    if c.on(P["sum"]):
        c.group(P["sum"])
        lw = c.label(cx, yy + S["value"] * 0.9, "neuron_sum")
        c.value(cx + lw + 14, yy + S["value"] * 1.1, P["sum"], size=big)
        svg.close()
    yy += big * 1.4
    svg.close()
    heights.append(yy - cy)

    # ---- gate: ReLU
    cx, cy = cols[2] if wide else (x, cy + heights[1] + 40)
    if not wide:
        svg.line(x, cy - 20, x + w, cy - 20, t["rule"], 1)
    svg.open(data_part="panel", data_panel="gate")
    yy = cy + S["label"]
    c.label(cx, yy, "panel_gate")
    gx0, gx1 = cx + 14, cx + cw - 24
    gy1 = yy + 40          # top of the plot
    gy0 = gy1 + (140 if wide else 112)  # the z axis (a = 0)
    zlo, zhi = -1.0, 1.5
    GX = lambda z: gx0 + (z - zlo) / (zhi - zlo) * (gx1 - gx0)  # noqa: E731
    GY = lambda a: gy0 - a / zhi * (gy0 - gy1)  # noqa: E731
    svg.line(gx0, gy0, gx1, gy0, t["rule"], 1.2)
    svg.line(GX(0), gy0, GX(0), gy1, t["rule"], 1.2)
    svg.path(f"M{GX(zlo):.1f},{gy0:.1f} L{GX(0):.1f},{gy0:.1f} L{GX(zhi):.1f},{GY(zhi):.1f}", t["value"], 3.5)
    for z in (zlo, 0.0, zhi):
        svg.text(GX(z), gy0 + 22, f"{z:g}".replace("-", "−"), ffont, fpx, t["label"], ("label", "axis-tick"),
                 extra={"data-axis": "gate-z", "data-tick": f"{z:g}"}, anchor="middle")
    svg.text(gx1 + 6, gy0 + 5, text.ui("axis_z"), "mono", fpx, t["label"], ("chrome", "axis_z"))
    svg.text(GX(0) - 8, gy1 - 6, text.ui("axis_a"), "mono", fpx, t["label"], ("chrome", "axis_a"), anchor="end")
    if c.on(P["sum"]):
        z = number(c.val(P["sum"]))
        a = max(0.0, z)
        c.group(P["out"] if c.on(P["out"]) else P["sum"])
        svg.raw(f'<path data-role="guide" d="M{GX(z):.1f},{gy0:.1f} L{GX(z):.1f},{GY(a):.1f} L{GX(0):.1f},{GY(a):.1f}" '
                f'fill="none" stroke="{t["label"]}" stroke-width="1.2" stroke-dasharray="4 4"/>')
        svg.raw(f'<circle data-role="path" data-axis-anchor="gate-z" data-anchor="{P["sum"]}" cx="{GX(z):.1f}" '
                f'cy="{GY(a):.1f}" r="7" fill="{t["value"]}"/>')
        svg.close()
    yy = gy0 + 44
    if P.get("gate"):
        ln = P["gate"]["line"]
        m = re.search(r"fmax\([^;]*\)", src[ln - 1])
        if m:
            svg.open(data_src_line=ln)  # a part of line `ln`: its numbers are bound to that line (AC-10.2)
            c.code(cx, yy, m.group(0), pid, size=S["code"] * 1.05)
            svg.close()
            yy += S["code"] * 1.2
    if c.on(P["out"]):
        c.group(P["out"])
        lw = c.label(cx, yy + S["value"] * 0.9, "neuron_output")
        c.value(cx + lw + 14, yy + S["value"] * 1.1, P["out"], size=big)
        svg.close()
    yy += big * 1.4
    svg.close()
    heights.append(yy - cy)
    if wide:
        h = max(max(heights), col_h)
        for i in (1, 2):
            dx = cols[i][0] - gap / 2
            svg.line(dx, y + 4, dx, y + h - 4, t["rule"], 1)
        return h
    return yy - y


KINDS = {"views": _views, "stack": _stack, "neuron": _neuron}
# The AC-10.2 mechanism kind each panel draws (data-kind), and the switch's path figure, which has no panel.
MECH_KIND = {"views": "bytes", "stack": "stack-column", "neuron": "neuron", "control-path": "control-path"}


def panel_kind(lesson):
    """The panel a lesson's mechanism figure draws: its figure.panel kind, or control-path for a switch program."""
    fig = lesson.data.get("figure") or {}
    if fig.get("panel"):
        return fig["panel"]["kind"]
    from .. import errors
    try:
        control_rows(lesson, fig.get("program"))
    except errors.ModelReferenceError:  # not a switch program: no path figure
        return None
    return "control-path"


def draw(svg, lesson, sid, x, y, w, layout="wide", flow=None, key=True, states=None, notes=True, mark=False,
         kind=None, code_key=False, only=None, only_ran=False, head=True, fit_h=None):
    """Draw the lesson's panel at trace state `sid`; returns its height. With `states` (the still, the film's
    summary), a stack panel draws the whole run as one column instead. `mark`: wrap it in the AC-10.2 mechanism
    markup (data-role="mechanism" data-kind=...), as the still and the film do."""
    kind = kind or panel_kind(lesson)
    c = Ctx(svg, lesson, sid, layout, flow, notes)
    c.code_key = code_key
    if key:
        svg.open(data_key="panel", data_state_panel=sid)
    if mark:
        svg.open(data_role="mechanism", data_kind=MECH_KIND[kind])
    if kind == "control-path":
        h = _control_path(c, x, y, w, only_ran=only_ran, head=head, fit_h=fit_h)
    elif kind == "views" and only == "memory":
        h = _memory_panel(c, x, y, w)
    elif states and kind == "stack":
        h = _stack_run(c, x, y, w, fit_h=fit_h)
    else:
        h = KINDS[kind](c, x, y, w)
    if mark:
        svg.close()
    if key:
        svg.close()
    svg.mech_anchors = c.anchors
    return h


def measure(svg_factory, lesson, sid, w, layout="wide"):
    """Height of the panel at `sid` without keeping its elements."""
    svg = svg_factory()
    return draw(svg, lesson, sid, 0, 0, w, layout)


WIDTHS = {("wide", "side"): 432, ("wide", "hero"): 1072, ("portrait", "side"): 368, ("portrait", "hero"): 368}


def page_place(lesson):
    """Where a page shows the panel of one state: a stack of one state is a column beside the code even when
    the still draws the whole run full width."""
    P = lesson.data["figure"].get("panel") or {"kind": "control-path", "place": "side"}
    return "side" if P["kind"] == "stack" else P["place"]


def max_height(lesson, layout, notes=True, width=None):
    """The tallest the panel gets over the trace, so every state can share one scale."""
    from . import still
    best = 0
    for st in lesson.data["trace"]:
        svg = still.Svg("light", fonts.tokens())
        w = width or WIDTHS[(layout, page_place(lesson))]
        best = max(best, draw(svg, lesson, st["id"], 4, 4, w, layout, still.Flow(svg, {}), key=False, notes=notes))
    return best


def svg_fragment(lesson, sid, layout, theme, tokens=None, states=None, attrs="", height=None, notes=True, width=None,
                 mark=False, kind=None):
    """The panel at `sid` as one standalone <svg> for an HTML page or the video: (markup, fact ids drawn, chars).
    Colours and type come from `theme` (the page shows a light and a dark copy by colour scheme); fonts are the
    page's own @font-face families."""
    from . import still  # still imports this module; the writer class lives there
    tokens = tokens or fonts.tokens()
    svg = still.Svg(theme, tokens)
    svg.tight = False  # pull-in points only for the still's OCR; pages and the film keep plain glyph boxes
    flow = still.Flow(svg, {})
    kind = kind or panel_kind(lesson)
    w = width or (WIDTHS[(layout, "side")] if kind in ("stack", "control-path") else WIDTHS[(layout, page_place(lesson))])
    h = draw(svg, lesson, sid, 4, 4, w, layout, flow, key=False, states=states, notes=notes, mark=mark, kind=kind)
    body = "\n".join(svg.els)
    facts = re.findall(r'data-fact="([^"]+)"', body)
    chars = "".join(svg.chars.values())
    defs = (f'<defs><marker id="arrow-{theme}-{layout}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" '
            f'markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{svg.t["note"]}"/></marker></defs>')
    body = body.replace('marker-end="url(#arrow)"', f'marker-end="url(#arrow-{theme}-{layout})"')
    h = max(h, height or 0)
    fig_role = ' data-role="figure"' if mark else ""
    markup = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w + 8:.0f} {h + 8:.0f}" width="{w + 8:.0f}" '
              f'height="{h + 8:.0f}" role="img" '
              f'data-panel-state="{sid}" data-theme="{theme}" data-layout="{layout}"{fig_role} {attrs}>{defs}{body}</svg>')
    return markup, facts, chars


# ---------------------------------------------------------------- the return flow (round 18)

def stack_anchors(lesson, sid, layout="wide", width=None):
    """{"rets": {frame idx: (x, y)}, "slots": {frame idx: (x, y)}} of a stack panel at `sid`, in the
    coordinates svg_fragment draws (the panel at 4, 4)."""
    from . import still
    svg = still.Svg("light", fonts.tokens())
    svg.tight = False
    c = Ctx(svg, lesson, sid, layout, still.Flow(svg, {}), notes=False)
    _stack(c, 4, 4, width or WIDTHS[(layout, page_place(lesson))])
    return c.anchors


def flows(lesson, before, sid):
    """The returned values that land between two states: [(frame idx in before, frame idx in sid, fact)] for every
    frame of `sid` that received (`got`) the value a frame of `before` was returning."""
    P = (lesson.data.get("figure") or {}).get("panel") or {}
    if P.get("kind") != "stack" or not before or before == sid:
        return []
    bf = lesson.state(before)["state"].get("frames", [])
    cf = lesson.state(sid)["state"].get("frames", [])
    out = []
    for j, fr in enumerate(cf):
        if not fr.get("got"):
            continue
        i = next((k for k, b in enumerate(bf) if b.get("status") == "returning" and b.get("ret") == fr["got"]), None)
        if i is not None:
            out.append((i, j, fr["got"]))
    return out
