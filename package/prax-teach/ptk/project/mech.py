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


def _vars_row(c, x, y, xr, sid, idx, size, rid, anchors=None):
    """One frame's variables on one row: the parameter at the left, the result at the right (its slot is the
    landing point of the callee's returned value). Returns the slot's centre (x, y) or None."""
    svg, t = c.svg, c.t
    slot_at = None
    for v in frame_vars(c.lesson, sid, idx):
        if v["kind"] == "param":
            svg.text(x, y, f"{v['name']} = {v['text']}", "mono", size, t["ink_soft"], ("chrome", "frame_var"),
                     inside=rid, extra={"data-var": v["name"]})
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
                     extra={"data-var": name})
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

    def val(self, fid):
        return text.display(self.facts[fid])

    def on(self, fid):
        return fid in self.shown

    def label(self, x, y, key, anchor="start", color=None, inside=None, **kw):
        svg = self.svg
        font, px, weight, caps, spacing = svg.role("label", self.S["label"])
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

    def group(self, fid=None, after=None):
        attrs = {}
        if fid:
            attrs["data_m"] = fid
        if after:
            attrs["data_mstate"] = after
        self.svg.open(**attrs)


# ---------------------------------------------------------------- views

def _views(c, x, y, w):
    svg, t, S, lesson = c.svg, c.t, c.S, c.lesson
    P = lesson.data["figure"]["panel"]
    pid = lesson.data["figure"]["program"]
    src = lesson.program_source(pid).split("\n")
    y0 = y
    v = P["value"]
    lh = S["code"] * 1.6
    # the value: its declaration, then its low byte as eight bit cells and the hex form
    y += S["label"]
    c.label(x, y, "panel_value")
    y += 14
    if v.get("line"):
        y += S["code"] * 1.1
        c.code(x, y, src[v["line"] - 1].strip(), pid, v["line"])
        y += 10
    if c.on(v["bits"]):
        c.group(v["bits"])
        # the byte as a tape: eight digits, each over a bar (note for a 1, rule for a 0), the bars kept clear of
        # the digits so OCR reads the digits alone
        vfont, vpx, vweight, _c, _s = svg.role("value", S["value"] * 1.15)
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
        hx = bx + 8 * (adv + gap) + 24
        if c.on(v["hex"]) and hx + 80 * S["k"] <= x + w:
            c.group(v["hex"])
            c.value(hx, base, v["hex"], color=t["note"])
            svg.close()
        y = base + 30
        c.label(x, y + S["label"] + 2, "panel_byte_note")
        y += S["label"] + 10
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

def _stack(c, x, y, w):
    svg, t, S, lesson = c.svg, c.t, c.S, c.lesson
    st = lesson.state(c.sid)["state"]
    frames = st.get("frames", [])
    pid = st["program"]
    vars_on = bool((lesson.data["figure"]["panel"].get("vars") or {}))
    y0 = y
    y += S["label"]
    c.label(x, y, "stack_label")
    c.label(x + w, y, "stack_top", anchor="end")
    y += 16
    fh = round(S["value"] * (3.5 if vars_on else 2.3))
    gap = 12
    arrow_w = 54 * S["k"]
    bw = w - arrow_w
    # the stack stands on a fixed base sized for the deepest state, so frames never move as others come and go
    depth = max(len(s["state"].get("frames", [])) for s in lesson.data["trace"])
    base = y + depth * (fh + gap)
    n = len(frames)
    boxes = [(frames[idx], idx, base - (n - idx) * (fh + gap)) for idx in range(n - 1, -1, -1)]  # top first
    slots, rets = {}, {}
    for i, (fr, idx, fy) in enumerate(boxes):
        status = fr.get("status", "running" if i == 0 else "waiting")
        returning = status == "returning"
        rid = f"frame-{c.layout}-{c.sid}-{i}"
        c.group(fr.get("ret") if returning else fr.get("call"))
        dash = ' stroke-dasharray="6 5"' if returning else ""
        fill = t["note_tint"] if status == "running" else (t["surface"] if not returning else t["ground"])
        svg.raw(f'<rect id="{rid}" data-role="frame" x="{x:.1f}" y="{fy:.1f}" width="{bw:.1f}" height="{fh}" rx="10" '
                f'fill="{fill}" stroke="{t["note"] if status != "waiting" else t["rule"]}" stroke-width="1.5"{dash}/>')
        ty = fy + (S["value"] * 1.25 if vars_on else fh / 2 + S["value"] * 0.33)
        if fr.get("call"):
            c.value(x + 16, ty, fr["call"], color=t["ink"], size=S["value"] * 0.8, inside=rid, ocr=False)
        else:
            c.code(x + 16, ty, fr["fn"], pid, size=S["value"] * 0.8, inside=rid)
        if returning and fr.get("ret"):
            vw = fonts.width("mono", S["value"], c.val(fr["ret"]))
            c.value(x + bw - 16, ty, fr["ret"], anchor="end", inside=rid, ocr=False)
            c.label(x + bw - 16 - vw - 10, ty - 2, "frame_returns", anchor="end", color=t["note"], inside=rid)
            rets[idx] = (x + bw - 16 - vw / 2, ty - S["value"] * 0.35)
        else:
            c.label(x + bw - 16, ty - 2, "frame_" + status, anchor="end",
                    color=t["note"] if status == "running" else t["label"], inside=rid)
        if vars_on:
            vy = fy + fh - S["value"] * 0.62
            at = _vars_row(c, x + 16, vy, x + bw - 16, c.sid, idx, S["code"], rid)
            if at:
                slots[idx] = at
        svg.close()
    # a returned value flows down into the slot of the frame that called it (or into its frame, without vars)
    for idx, (rx_, ry_) in rets.items():
        if idx - 1 < 0:
            continue
        callee_y = next(fy for fr, j, fy in boxes if j == idx)
        caller_y = next(fy for fr, j, fy in boxes if j == idx - 1)
        ax = x + bw + 6
        if idx - 1 in slots:
            _cx, sy_mid, sx_right, _sy, _sh = slots[idx - 1]
            svg.path(f"M{ax - 2:.1f},{callee_y + fh * 0.3:.1f} C{ax + arrow_w - 10:.1f},{callee_y + fh * 0.3:.1f} "
                     f"{ax + arrow_w - 10:.1f},{sy_mid:.1f} {sx_right + 6:.1f},{sy_mid:.1f}", t["note"], 2.5, marker=True)
        else:
            svg.path(f"M{ax:.1f},{callee_y + fh / 2:.1f} C{ax + arrow_w - 10:.1f},{callee_y + fh / 2:.1f} "
                     f"{ax + arrow_w - 10:.1f},{caller_y + fh / 2:.1f} {ax + 4:.1f},{caller_y + fh / 2:.1f}",
                     t["note"], 2.5, marker=True)
    c.anchors = {"rets": rets, "slots": {k: (v[0], v[1]) for k, v in slots.items()}}
    y = base - gap
    for cid in lesson.data["figure"]["panel"].get("claims", []):
        y = c.note(x, y + S["note"] * 2, cid, w)
    return y - y0 + 10


def _stack_timeline(c, x, y, w, states):
    """Every state's stack side by side (wide: one column per state, stacks standing on a shared base;
    portrait: one row per state, frames left to right from main). Each step is captioned with the line
    the program printed at that step, so the picture pairs every output with the frames that made it."""
    svg, t, S, lesson = c.svg, c.t, c.S, c.lesson
    wide = c.layout == "wide"
    y0 = y
    y += S["label"]
    c.label(x, y, "stack_steps")
    y += 18
    facts = c.facts
    cols = [lesson.state(s) for s in states]
    vfont, _vpx, vweight, _c, _s = svg.role("value", S["value"])
    fsize = 13.5 if wide else 12
    cap = 12.5 if wide else 11.5
    vars_on = bool(lesson.data["figure"]["panel"].get("vars"))
    if wide:
        gap = 12
        cw = (w - gap * (len(cols) - 1)) / len(cols)
        fh, fg = (60 if vars_on else 34), 6
        depth = max(len(s["state"].get("frames", [])) for s in cols)
        base = y + 26 + depth * (fh + fg)
        for k, st in enumerate(cols):
            cx = x + k * (cw + gap)
            new = [f for f in st.get("reveals", []) if f in facts and facts[f]["select"].get("stream") == "stdout"]
            if new:
                svg.text(cx, y + cap, text.display(facts[new[-1]]), "mono", cap, t["value"], ("fact", new[-1]),
                         ocr=None)
            frames = st["state"].get("frames", [])
            for i, fr in enumerate(frames):
                fy = base - (i + 1) * (fh + fg) + fg
                _frame_box(c, cx, fy, cw, fh, fr, f"tl-{c.layout}-{st['id']}-{i}", fsize, i == len(frames) - 1,
                           sid=st["id"], idx=i)
            svg.line(cx, base + 4, cx + cw, base + 4, t["rule"], 1.2)
        return base + 14 - y0
    rh, gap, pad, sep = (64 if vars_on else 30), 14, 8, 3

    def widths(st, size):
        out = []
        for i, fr in enumerate(st["state"].get("frames", [])):
            label = text.display(facts[fr["call"]]) if fr.get("call") else fr["fn"]
            rows = [label] + ([_var_text(c, v) for v in frame_vars(lesson, st["id"], i)] if vars_on else [])
            out.append(max(fonts.width("mono", size, r) for r in rows) + 2 * pad)  # a returning frame's value is its row caption
        return out
    # one size for every row: the largest (at most fsize) at which the widest row fits the width
    widest = max(sum(widths(st, fsize)) + sep * (len(st["state"].get("frames", [])) - 1) for st in cols)
    fsize = round(max(11.0, min(fsize, fsize * w / widest)), 2)
    for k, st in enumerate(cols):
        new = [f for f in st.get("reveals", []) if f in facts and facts[f]["select"].get("stream") == "stdout"]
        if new:
            svg.text(x, y + cap, text.display(facts[new[-1]]), "mono", cap, t["value"], ("fact", new[-1]))
        fy = y + cap + 8
        fx = x
        frames = st["state"].get("frames", [])
        for i, (fr, bw) in enumerate(zip(frames, widths(st, fsize))):
            _frame_box(c, fx, fy, bw, rh, fr, f"tl-{c.layout}-{st['id']}-{i}", fsize, i == len(frames) - 1, pad,
                       show_ret=False, sid=st["id"], idx=i)
            fx += bw + sep
        y = fy + rh + gap
    return y - y0


def _var_text(c, v):
    """The text a variable row is measured by (the slot counts as two characters)."""
    if v["kind"] == "param":
        return f"{v['name']} = {v['text']}"
    if v["kind"] == "unset":
        return f"{v['name']} = ?"
    if v["kind"] == "value":
        return f"{v['name']} = {c.val(v['fact'])}"
    return f"{v['name']} = {v['prefix']} 00".replace("  ", " ")


def _vars_lines(c, x, y, lh, sid, idx, size, rid):
    """A frame's variables, one per row, left-aligned (the step strip, where frames are narrow)."""
    svg, t = c.svg, c.t
    for v in frame_vars(c.lesson, sid, idx):
        name = v["name"]
        if v["kind"] == "param":
            svg.text(x, y, f"{name} = {v['text']}", "mono", size, t["ink_soft"], ("chrome", "frame_var"), inside=rid,
                     extra={"data-var": name})
        elif v["kind"] == "unset":
            svg.text(x, y, f"{name} = ?", "mono", size, t["label"], ("chrome", "frame_var_unset"), inside=rid,
                     extra={"data-var": name})
        elif v["kind"] == "value":
            lab = f"{name} ="
            svg.text(x, y, lab, "mono", size, t["ink_soft"], ("chrome", "frame_var_eq"), inside=rid, extra={"data-var": name})
            c.value(x + fonts.width("mono", size, lab + " "), y, v["fact"], size=size, inside=rid, ocr=False)
        else:
            lab = f"{name} = {v['prefix']}" if v["prefix"] else f"{name} ="
            svg.text(x, y, lab, "mono", size, t["ink_soft"], ("chrome", "frame_var" if v["prefix"] else "frame_var_eq"),
                     inside=rid, extra={"data-var": name})
            sx = x + fonts.width("mono", size, lab + " ")
            sw, sh = size * 1.5, size * 1.35
            got = v.get("got")
            svg.raw(f'<rect data-role="slot" x="{sx:.1f}" y="{y - size * 1.0:.1f}" width="{sw:.1f}" height="{sh:.1f}" '
                    f'rx="3" fill="{t["note_tint"] if got else "none"}" stroke="{t["note"]}" stroke-width="1.2"'
                    f'{"" if got else " stroke-dasharray=\"3 3\""}/>')
            if got:
                c.value(sx + sw / 2, y, got, size=size, anchor="middle", inside=rid, ocr=False, color=t["value"])
        y += lh


def _frame_box(c, x, y, w, h, fr, rid, size, top, pad=9, show_ret=True, sid=None, idx=None):
    """One frame: label (its call fact, or the function name), dashed while returning with its value; with the
    panel's `vars`, the frame's own variables under the label."""
    svg, t = c.svg, c.t
    status = fr.get("status", "running" if top else "waiting")
    returning = status == "returning"
    vars_on = bool(c.lesson.data["figure"]["panel"].get("vars")) and sid is not None
    c.group(fr.get("ret") if returning else fr.get("call"))
    dash = ' stroke-dasharray="5 4"' if returning else ""
    fill = t["note_tint"] if status == "running" else (t["surface"] if not returning else t["ground"])
    svg.raw(f'<rect id="{rid}" data-role="frame" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h}" rx="7" '
            f'fill="{fill}" stroke="{t["note"] if status != "waiting" else t["rule"]}" stroke-width="1.4"{dash}/>')
    ty = y + (size * 1.3 if vars_on else h / 2 + size * 0.36)
    if fr.get("call"):
        c.value(x + pad, ty, fr["call"], color=t["ink"], size=size, inside=rid, weight=400, ocr=False)
    else:
        c.code(x + pad, ty, fr["fn"], c.lesson.state(c.sid)["state"]["program"], size=size, inside=rid)
    if returning and fr.get("ret") and show_ret:
        c.value(x + w - pad, ty, fr["ret"], anchor="end", size=size * 1.15, inside=rid, ocr=False)
    if vars_on:
        vs = max(11.0, round(size * 0.92, 2))
        _vars_lines(c, x + pad, ty + vs * 1.55, vs * 1.45, sid, idx, vs, rid)
    svg.close()


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
    col_h = 300 if wide else None
    big = S["big"]
    tone = lambda fid: t["note"] if number(c.val(fid)) >= 0 else t["correction"]  # noqa: E731
    heights = []

    # ---- multiply
    cx, cy = cols[0]
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
    heights.append(yy - cy)

    # ---- add: the running sum along a number line
    cx, cy = cols[1] if wide else (x, cy + heights[0] + 40)
    if not wide:
        svg.line(x, cy - 20, x + w, cy - 20, t["rule"], 1)
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
    row = S["value"] * 2.1
    by = yy + 30
    for k, (fid, (a, b)) in enumerate(zip(terms, ends)):
        if not all(c.on(f) for f in terms[:k + 1]):  # a bar starts where the one before it ends
            continue
        c.group(fid)
        ry = by + k * row + S["value"]
        col = tone(fid)
        svg.line(X(a), ry, X(b), ry, col, 9, role="path")
        svg.circle(X(a), ry, 5.5, col)
        svg.circle(X(b), ry, 5.5, col)
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
        svg.text(X(v), ay + 22, lab, ffont, fpx, t["label"], ("label", "axis-tick"), anchor="middle")
    yy = ay + 46
    if all(c.on(f) for f in terms):
        # z = t1 t2 b: the sum written out from the terms it adds
        zx = cx + c.code(cx, yy, "z =", pid, size=S["code"]) + 10
        for f in terms:
            c.group(f)
            zx += c.value(zx, yy, f, size=S["code"] * 1.05, color=tone(f), ocr=False) + 10
            svg.close()
        yy += 14
    if c.on(P["sum"]):
        c.group(P["sum"])
        lw = c.label(cx, yy + S["value"] * 0.9, "neuron_sum")
        c.value(cx + lw + 14, yy + S["value"] * 1.1, P["sum"], size=big)
        svg.close()
    yy += big * 1.4
    heights.append(yy - cy)

    # ---- gate: ReLU
    cx, cy = cols[2] if wide else (x, cy + heights[1] + 40)
    if not wide:
        svg.line(x, cy - 20, x + w, cy - 20, t["rule"], 1)
    yy = cy + S["label"]
    c.label(cx, yy, "panel_gate")
    gx0, gx1 = cx + 14, cx + cw - 24
    gy1 = yy + 40          # top of the plot
    gy0 = gy1 + (180 if wide else 112)  # the z axis (a = 0)
    zlo, zhi = -1.0, 1.5
    GX = lambda z: gx0 + (z - zlo) / (zhi - zlo) * (gx1 - gx0)  # noqa: E731
    GY = lambda a: gy0 - a / zhi * (gy0 - gy1)  # noqa: E731
    svg.line(gx0, gy0, gx1, gy0, t["rule"], 1.2)
    svg.line(GX(0), gy0, GX(0), gy1, t["rule"], 1.2)
    svg.path(f"M{GX(zlo):.1f},{gy0:.1f} L{GX(0):.1f},{gy0:.1f} L{GX(zhi):.1f},{GY(zhi):.1f}", t["value"], 3.5)
    for z in (zlo, 0.0, zhi):
        svg.text(GX(z), gy0 + 22, f"{z:g}".replace("-", "−"), ffont, fpx, t["label"], ("label", "axis-tick"),
                 anchor="middle")
    svg.text(gx1 + 6, gy0 + 5, text.ui("axis_z"), "mono", fpx, t["label"], ("chrome", "axis_z"))
    svg.text(GX(0) - 8, gy1 - 6, text.ui("axis_a"), "mono", fpx, t["label"], ("chrome", "axis_a"), anchor="end")
    if c.on(P["sum"]):
        z = number(c.val(P["sum"]))
        a = max(0.0, z)
        c.group(P["out"] if c.on(P["out"]) else P["sum"])
        svg.raw(f'<path data-role="guide" d="M{GX(z):.1f},{gy0:.1f} L{GX(z):.1f},{GY(a):.1f} L{GX(0):.1f},{GY(a):.1f}" '
                f'fill="none" stroke="{t["label"]}" stroke-width="1.2" stroke-dasharray="4 4"/>')
        svg.circle(GX(z), GY(a), 7, t["value"])
        svg.close()
    yy = gy0 + 52
    if P.get("gate"):
        ln = P["gate"]["line"]
        m = re.search(r"fmax\([^;]*\)", src[ln - 1])
        if m:
            c.code(cx, yy, m.group(0), pid, size=S["code"] * 1.05)
            yy += S["code"] * 1.2
    if c.on(P["out"]):
        c.group(P["out"])
        lw = c.label(cx, yy + S["value"] * 0.9, "neuron_output")
        c.value(cx + lw + 14, yy + S["value"] * 1.1, P["out"], size=big)
        svg.close()
    yy += big * 1.4
    heights.append(yy - cy)
    if wide:
        h = max(max(heights), col_h)
        for i in (1, 2):
            dx = cols[i][0] - gap / 2
            svg.line(dx, y + 4, dx, y + h - 4, t["rule"], 1)
        return h
    return yy - y


KINDS = {"views": _views, "stack": _stack, "neuron": _neuron}


def draw(svg, lesson, sid, x, y, w, layout="wide", flow=None, key=True, states=None, notes=True):
    """Draw the lesson's panel at trace state `sid`; returns its height. With `states` (the still), a stack
    panel draws every one of those states side by side instead."""
    P = lesson.data["figure"]["panel"]
    c = Ctx(svg, lesson, sid, layout, flow, notes)
    if key:
        svg.open(data_key="panel", data_state_panel=sid)
    if states and P["kind"] == "stack":
        h = _stack_timeline(c, x, y, w, states)
    else:
        h = KINDS[P["kind"]](c, x, y, w)
    if key:
        svg.close()
    return h


def measure(svg_factory, lesson, sid, w, layout="wide"):
    """Height of the panel at `sid` without keeping its elements."""
    svg = svg_factory()
    return draw(svg, lesson, sid, 0, 0, w, layout)


WIDTHS = {("wide", "side"): 432, ("wide", "hero"): 1072, ("portrait", "side"): 368, ("portrait", "hero"): 368}


def page_place(lesson):
    """Where a page shows the panel of one state: a stack of one state is a column beside the code even when
    the still draws the whole run full width."""
    P = lesson.data["figure"]["panel"]
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


def svg_fragment(lesson, sid, layout, theme, tokens=None, states=None, attrs="", height=None, notes=True, width=None):
    """The panel at `sid` as one standalone <svg> for an HTML page or the video: (markup, fact ids drawn, chars).
    Colours and type come from `theme` (the page shows a light and a dark copy by colour scheme); fonts are the
    page's own @font-face families."""
    from . import still  # still imports this module; the writer class lives there
    tokens = tokens or fonts.tokens()
    svg = still.Svg(theme, tokens)
    svg.tight = False  # pull-in points only for the still's OCR; pages and the film keep plain glyph boxes
    flow = still.Flow(svg, {})
    w = width or (WIDTHS[(layout, page_place(lesson))] if not states else WIDTHS[(layout, lesson.data["figure"]["panel"]["place"])])
    h = draw(svg, lesson, sid, 4, 4, w, layout, flow, key=False, states=states, notes=notes)
    body = "\n".join(svg.els)
    facts = re.findall(r'data-fact="([^"]+)"', body)
    chars = "".join(svg.chars.values())
    defs = (f'<defs><marker id="arrow-{theme}-{layout}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" '
            f'markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{svg.t["note"]}"/></marker></defs>')
    body = body.replace('marker-end="url(#arrow)"', f'marker-end="url(#arrow-{theme}-{layout})"')
    h = max(h, height or 0)
    markup = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w + 8:.0f} {h + 8:.0f}" width="{w + 8:.0f}" '
              f'height="{h + 8:.0f}" role="img" '
              f'data-panel-state="{sid}" data-theme="{theme}" data-layout="{layout}" {attrs}>{defs}{body}</svg>')
    return markup, facts, chars
