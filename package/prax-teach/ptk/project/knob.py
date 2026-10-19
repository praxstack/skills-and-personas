r"""The explorer's knob (round 18, review P1: "every explorer was a stepper with nothing to change").

Under the step-through of the captured run, a panel lesson's explorer lets the learner change the one
input the lesson is about (figure.explore). Every value on screen is captured or computed here, in
Python, and written into the page; knob.js only shows the part for the chosen value and, for the neuron,
places the bars and the dot from numbers this module computed.

    values   one captured run per value of a variable (one-byte: a in {66, 200, -1, 321})
             a table, one row per value, every cell a fact (data-fact), the chosen row lit, and the
             claims for that value under it
    calls    one captured run per argument (factorial: n = 1..5), its stdout one fact
             the run replayed line by line: the stack after each printed line, every frame with its own
             n and r, derived from the lines (stack_steps) and checked against expect.factorial_events
    neuron   two sliders (w2, b) over a grid; every point from ptk/expect_neuron.py, never from the page;
             the variant programs in figure.explore.checks are captured runs at three points and must
             print exactly what the grid says there

Gates (gates()): the driver (templates/html/drive.mjs, stepper mode) picks every value, steps every call,
and moves the sliders to the check points and the corners; each record is compared with expected_*().
"""
import json
import re

from .. import expect, expect_neuron, text
from ..text import esc

ENTER = re.compile(r"^enter (\w+)\((-?\d+)\)$")
RESULT = re.compile(r"^(\w+)\((-?\d+)\) = (-?\d+)$")
MAIN = re.compile(r"^main got (-?\d+)$")


GEOM = {"w": 320, "pad": 16, "lo": -1.5, "hi": 3.5, "ticks": [-1, 0, 1, 2, 3], "zlo": -1.0, "zhi": 3.5, "ahi": 3.5,
        "gy0": 118, "gy1": 14, "zticks": [-1, 0, 1, 2, 3]}


def gate_xy(zf, af):
    """Where the gate dot must be for a point (the same mapping knob.js draws with)."""
    G = GEOM
    x = G["pad"] + (zf - G["zlo"]) / (G["zhi"] - G["zlo"]) * (G["w"] - 2 * G["pad"])
    y = G["gy0"] - af / G["ahi"] * (G["gy0"] - G["gy1"])
    return x, y


def spec(lesson):
    return (lesson.data.get("figure") or {}).get("explore")


def _fact_text(lesson, fid):
    return text.display(lesson.fact(fid))


def _prov(lesson, pid):
    sha = next((f["source"]["stdout_sha256"][:12] for f in lesson.data["facts"]
                if f["program"] == pid and f.get("source", {}).get("stdout_sha256")), "")
    return text.ui("x_captured_run", file=lesson.program(pid)["path"].split("/")[-1], sha=sha)


# ---------------------------------------------------------------- calls: the stack after each printed line

def stack_steps(lines):
    """[{"line": k, "printed": [...], "frames": [{"label", "status", "n", "r", "slot", "ret"}]}] after each line,
    main first, each call after its caller (drawn top-down, as the still and the film draw the stack, AC-10.2).
    A frame's r: "r = ?" before its call returns; "r = 3 *" plus an empty slot while it waits
    for the call on its call line; "r = 2 * 1" once the value has landed (one line after the callee printed
    its result, when the callee's frame is gone); the base case shows its result. main waits with "r =" and a
    slot until factorial(n) has returned."""
    frames = [{"label": "main", "n": None, "status": "waiting", "pending": "", "got": None, "ret": None}]
    out, printed = [], []
    for k, ln in enumerate(lines, 1):
        printed.append(ln)
        if frames[-1]["status"] == "returning":
            done = frames.pop()
            frames[-1]["got"] = done["ret"]
        m = ENTER.match(ln)
        if m:
            top = frames[-1]
            if top["label"] != "main":
                top.update(status="waiting", pending=f"{top['n']} *")
            frames.append({"label": f"{m.group(1)}({m.group(2)})", "n": m.group(2), "status": "running", "pending": None,
                           "got": None, "ret": None})
        m = RESULT.match(ln)
        if m:
            frames[-1].update(status="returning", ret=m.group(3))
        if MAIN.match(ln):
            frames[0]["status"] = "running"
        out.append({"line": k, "printed": list(printed), "frames": [_view(f) for f in frames]})
    return out


def _view(f):
    if f["label"] == "main":
        r, slot = ("r = " + f["got"], False) if f["got"] is not None else ("r =", True)
    elif f["pending"] is None:
        r, slot = ("r = " + f["ret"] if f["status"] == "returning" else "r = ?"), False
    elif f["got"] is None:
        r, slot = f"r = {f['pending']}", True
    else:
        r, slot = f"r = {f['pending']} {f['got']}", False
    return {"label": f["label"], "status": f["status"], "n": f["n"], "r": r, "slot": slot, "ret": f["ret"]}


def expected_calls(n):
    """The independent view: stack_steps over the lines expect.py says factorial(n) prints."""
    return stack_steps(expect.factorial_events(int(n)))


# ---------------------------------------------------------------- HTML

def _radios(name, values, first):
    return "".join(f'<label><input type="radio" name="{name}" value="{esc(v)}"{" checked" if v == first else ""}>'
                   f'<span>{esc(v)}</span></label>' for v in values)


def _claims_html(lesson, cids):
    """The knob's fixed sentences. A sentence about captured runs (a claim bound to facts) is marked
    data-captured with those facts (AC-10.4): it describes the runs, not the live setting, and every number in it
    is one of theirs."""
    from .stepper import nobr
    out = []
    for c in cids:
        cl = lesson.claim(c)
        cap = f' data-captured="{" ".join(cl["facts"])}"' if cl.get("facts") else ""
        out.append(f'<p data-claim="{c}"{cap}>{nobr(cl["text"])}</p>')
    return "".join(out)


LIVE_CLAIM, ROUND_CLAIM = "c.kformula", "c.kround"


def live_texts(lesson, T):
    """The neuron knob's live sentences (AC-10.4), rebuilt from the grid row on screen after every slider step:
    {"live": template, "tiny": template or None, "fill": {...}, "claims": {...}}. Every number comes from
    expect_neuron (the row strings, and t1 to 17 significant digits); the page only fills the templates in."""
    P = lesson.data["figure"]["panel"]
    num = lambda fid: float(_fact_text(lesson, fid).replace("−", "-"))  # noqa: E731
    x1, w1 = num(P["terms"][0]["x"]), num(P["terms"][0]["w"])
    t1 = expect_neuron.point(x1, w1, 0.0, 0.0, 0.0)["t1"]
    has_round = any(c["id"] == ROUND_CLAIM for c in lesson.data["claims"])
    return {"live": text.ui("k_live", g_w2="{w2}", g_b="{b}", g_z="{z}", g_a="{a}"),
            "tiny": text.ui("k_tiny", g_z="{z}", g_x1=T["x1"], g_w1=T["w1"], g_x2=T["x2"], d_t1=repr(t1)) if has_round else None,
            "claims": {"live": LIVE_CLAIM, "tiny": ROUND_CLAIM if has_round else None}}


def tiny(row):
    """A nonzero z too small to be anything but rounding (|z| < 1e-9): the page explains it (AC-10.4)."""
    return row["zf"] != 0.0 and abs(row["zf"]) < 1e-9


COLS = (("bits", "k_col_bits"), ("hex", "k_col_hex"), ("d", "k_col_d"), ("u", "k_col_u"), ("f", "k_col_f"),
        ("c", "k_col_c"))


def _values_html(lesson, sp):
    """One column per value (the chosen one lit; at phone width only the chosen one shows), one row per view."""
    vals = sp["values"]
    head = "".join(f'<th scope="col" data-value="{esc(v["value"])}"><code data-code="{v["program"]}">'
                   f'{esc(sp["var"])} = {esc(v["value"])}</code></th>' for v in vals)
    rows = []
    for role, key in COLS:
        cells = []
        for v in vals:
            F = v["facts"]
            if role == "c" and "char" not in F:
                body = (f'<span class="kb" data-chrome="k_byte">{esc(text.ui("k_byte"))}</span> '
                        f'<span data-fact="{F["byte"]}">{esc(_fact_text(lesson, F["byte"]))}</span>')
            else:
                fid = F["char"] if role == "c" else F[role]
                body = f'<span data-fact="{fid}">{esc(_fact_text(lesson, fid))}</span>'
            cells.append(f'<td class="v" data-value="{esc(v["value"])}">{body}</td>')
        rows.append(f'<tr><th scope="row" data-chrome="{key}">{esc(text.ui(key))}</th>{"".join(cells)}</tr>')
    prose = "".join(f'<div class="kprose" data-value="{esc(v["value"])}">{_claims_html(lesson, v.get("claims", []))}'
                    f'<p class="prov" data-chrome="x_captured_run">{esc(_prov(lesson, v["program"]))}</p></div>'
                    for v in vals)
    return (f'<div class="ktable" data-key="knob-table"><table id="k-table"><thead><tr><th scope="col" data-chrome="k_col_var">'
            f'{esc(text.ui("k_col_var"))}</th>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            f'<div class="kprose-all">{prose}</div>')


def _frame_html(f):
    vars_ = []
    if f["n"] is not None:
        vars_.append(f'<span class="kvar" data-chrome="frame_var">n = {esc(f["n"])}</span>')
    slot = f'<span class="kslot" role="img" aria-label="{esc(text.ui("k_slot"))}"></span>' if f["slot"] else ""
    key = "frame_var_unset" if f["r"].endswith("?") else ("frame_var_eq" if f["r"].endswith("=") else "frame_var")
    vars_.append(f'<span class="kvar" data-chrome="{key}">{esc(f["r"])}{slot}</span>')
    status = (f'<span class="lbl" data-chrome="frame_returns">{esc(text.ui("frame_returns"))}</span> '
              f'<b class="kret">{esc(f["ret"])}</b>') if f["status"] == "returning" else \
        f'<span class="lbl" data-chrome="frame_{f["status"]}">{esc(text.ui("frame_" + f["status"]))}</span>'
    return (f'<li class="kframe" data-status="{f["status"]}"><span class="kfl"><code>{esc(f["label"])}</code>{status}</span>'
            f'<span class="kfv">{"".join(vars_)}</span></li>')


def _calls_html(lesson, sp):
    blocks = []
    for v in sp["values"]:
        fid = v["facts"]["out"]
        lines = _fact_text(lesson, fid).split("\n")
        st = stack_steps(lines)
        panes = []
        for s in st:
            outs = "".join(f'<li{" class=\"now\"" if i == len(s["printed"]) - 1 else ""}><span class="k">{i + 1}</span>'
                           f'<span class="val">{esc(t)}</span></li>' for i, t in enumerate(s["printed"]))
            panes.append(f'<div class="kstep" data-step="{s["line"]}"><p class="lbl" data-chrome="s_step">'
                         f'{esc(text.ui("s_step", k=s["line"], n=len(st)))}</p><div class="kgrid">'
                         f'<div class="kstackbox" data-key="knob-stack"><p class="lbl" data-chrome="stack_label">{esc(text.ui("stack_label"))}</p>'
                         f'<ol class="kstack">{"".join(_frame_html(f) for f in s["frames"])}</ol></div>'
                         f'<div><p class="lbl" data-chrome="output_label">{esc(text.ui("output_label"))}</p>'
                         f'<ol class="out kout" data-fact-whole="{fid}">{outs}</ol></div></div></div>')
        blocks.append(f'<div class="kcalls" data-value="{esc(v["value"])}" data-steps="{len(st)}">{"".join(panes)}'
                      f'{_claims_html(lesson, v.get("claims", []))}'
                      f'<p class="prov" data-chrome="x_captured_run">{esc(_prov(lesson, v["program"]))}</p></div>')
    nav = (f'<div class="toggles"><button type="button" class="pill" id="k-prev" data-chrome="prev_state">'
           f'{esc(text.ui("prev_state"))}</button><button type="button" class="pill" id="k-next" data-chrome="next_state">'
           f'{esc(text.ui("next_state"))}</button></div>')
    return nav + "".join(blocks)


def neuron_table(lesson, sp):
    P = lesson.data["figure"]["panel"]
    num = lambda fid: float(_fact_text(lesson, fid).replace("−", "-"))  # noqa: E731
    x1, w1 = num(P["terms"][0]["x"]), num(P["terms"][0]["w"])
    x2 = num(P["terms"][1]["x"])
    sl = {s["var"]: s for s in sp["sliders"]}
    return {"x1": expect_neuron.g(x1), "w1": expect_neuron.g(w1), "x2": expect_neuron.g(x2),
            "w2_0": _fact_text(lesson, P["terms"][1]["w"]), "b_0": expect_neuron.g(num(P["bias"])),
            **expect_neuron.grid(x1, w1, x2, sl)}


def _neuron_html(lesson, sp):
    T = neuron_table(lesson, sp)
    sliders = []
    for s in sp["sliders"]:
        vals = T[s["var"]]
        i0 = vals.index(T[f"{s['var']}_0"])
        sliders.append(f'<label class="kslider"><span class="lbl" data-chrome="k_slider">{esc(text.ui("k_slider", name=s["var"]))}</span>'
                       f'<input type="range" id="k-{s["var"]}" min="0" max="{len(vals) - 1}" step="1" value="{i0}" '
                       f'aria-valuetext="{esc(vals[i0])}"><output class="kout1" id="k-{s["var"]}-v">{esc(vals[i0])}</output></label>')
    return (f'<div class="ksliders">{"".join(sliders)}</div>'
            f'<div class="kneuron" data-key="knob-neuron" id="k-neuron">'
            f'<div class="kn-col"><p class="lbl" data-chrome="panel_multiply">{esc(text.ui("panel_multiply"))}</p>'
            f'<p class="kn-eq"><span id="k-x1">{esc(T["x1"])}</span> × <span id="k-w1">{esc(T["w1"])}</span> = <b id="k-t1"></b></p>'
            f'<p class="kn-eq"><span id="k-x2">{esc(T["x2"])}</span> × <span id="k-w2s"></span> = <b id="k-t2"></b></p>'
            f'<p class="kn-eq"><span data-chrome="neuron_bias">{esc(text.ui("neuron_bias"))}</span> <b id="k-bs"></b></p></div>'
            f'<div class="kn-col"><p class="lbl" data-chrome="panel_add">{esc(text.ui("panel_add"))}</p>'
            f'<svg id="k-add" viewBox="0 0 320 150" role="img" aria-labelledby="k-zl"></svg>'
            f'<p class="kn-eq" id="k-zl"><span data-chrome="axis_z">{esc(text.ui("axis_z"))}</span> = <b id="k-z"></b></p></div>'
            f'<div class="kn-col"><p class="lbl" data-chrome="panel_gate">{esc(text.ui("panel_gate"))}</p>'
            f'<svg id="k-gate" viewBox="0 0 320 150" role="img" aria-labelledby="k-al"></svg>'
            f'<p class="kn-eq" id="k-al"><span data-chrome="axis_a">{esc(text.ui("axis_a"))}</span> = <b id="k-a"></b></p></div></div>'
            f'<div class="klives"><p class="klive" id="k-live" data-chrome="k_live" data-claims="{LIVE_CLAIM}"></p>'
            f'<p class="klive" id="k-tiny" data-chrome="k_tiny" data-claims="{ROUND_CLAIM}" hidden></p></div>'
            f'<div class="kprose-all always">{_claims_html(lesson, sp.get("claims", []))}'
            f'<p class="prov" data-chrome="k_computed">{esc(text.ui("k_computed", count=len(sp.get("checks", []))))}</p></div>')


def section(lesson):
    """The knob's HTML and its page data, or ("", None) when the lesson has no figure.explore."""
    sp = spec(lesson)
    if not sp:
        return "", None
    kind = sp["kind"]
    head = f'<h2 class="sec" id="k-h" data-chrome="x_section">{esc(text.ui("x_section"))}</h2>'
    if kind in ("values", "calls"):
        vals = [v["value"] for v in sp["values"]]
        first = next((v["value"] for v in sp["values"] if v["program"] == lesson.data["figure"]["program"]), vals[0])
        ctl = (f'<fieldset class="seg" id="k-vals"><legend class="lbl" data-chrome="k_var_label">'
               f'{esc(text.ui("k_var_label", var=sp["var"]))}</legend><div class="opts">{_radios("k-val", vals, first)}</div></fieldset>')
        body = _values_html(lesson, sp) if kind == "values" else _calls_html(lesson, sp)
        data = {"kind": kind, "values": vals, "first": first}
        common = _claims_html(lesson, sp.get("claims", [])) if kind == "values" else \
            f'<div class="kprose-all always">{_claims_html(lesson, sp.get("claims", []))}</div>'
        if kind == "values":
            common = f'<div class="kprose-all always">{common}</div>'
        html = f'<section class="knob" id="k" data-kind="{kind}" aria-labelledby="k-h">{head}<div class="js-only">{ctl}</div>{body}{common}</section>'
    else:
        T = neuron_table(lesson, sp)
        data = {"kind": "neuron", "w2": T["w2"], "b": T["b"], "rows": T["rows"], "x1": T["x1"], "x2": T["x2"], "geom": GEOM,
                "labels": [text.ui("neuron_term", i=1), text.ui("neuron_term", i=2), text.ui("neuron_term_bias")],
                "texts": live_texts(lesson, T)}
        html = (f'<section class="knob js-only" id="k" data-kind="neuron" aria-labelledby="k-h">{head}'
                f'{_neuron_html(lesson, sp)}</section>')
    return html, data


def texts(lesson, where):
    """The knob's sentences and labels for texts.json (the claims mapping)."""
    sp = spec(lesson)
    if not sp:
        return []
    items = [{"text": text.ui("x_section"), "claims": [], "source": "chrome:x_section", "where": where}]
    cids = list(sp.get("claims", [])) + [c for v in sp.get("values", []) for c in v.get("claims", [])]
    for c in dict.fromkeys(cids):
        items.append({"text": lesson.claim(c)["text"], "claims": [c], "source": f"claim:{c}", "where": where})
    keys = ["k_var_label"] if sp["kind"] != "neuron" else ["k_slider", "k_computed", "panel_multiply", "panel_add",
                                                            "panel_gate", "neuron_bias", "axis_z", "axis_a"]
    if sp["kind"] == "values":
        keys += ["k_col_var", "k_byte"] + [k for _r, k in COLS]
    if sp["kind"] == "calls":
        keys += ["stack_label", "output_label", "frame_returns", "frame_running", "frame_waiting", "prev_state", "next_state"]
    for k in keys:
        kw = {"var": sp.get("var", "")} if k == "k_var_label" else ({"count": len(sp.get("checks", []))} if k == "k_computed"
                                                                    else ({"name": "w2"} if k == "k_slider" else {}))
        items.append({"text": text.ui(k, **kw), "claims": [], "source": f"chrome:{k}", "where": where})
    for v in sp.get("values", []):
        items.append({"text": _prov(lesson, v["program"]), "claims": [], "source": "chrome:x_captured_run", "where": where})
    if sp["kind"] == "neuron":
        T = neuron_table(lesson, sp)
        L = live_texts(lesson, T)
        for key, tpl in (("live", L["live"]), ("tiny", L["tiny"])):
            if not tpl:
                continue
            k_ = next((k for k, r in T["rows"].items() if tiny(r)), None) if key == "tiny" else f"{T['w2_0']}|{T['b_0']}"
            if k_:
                row, (w2_, b_) = T["rows"][k_], k_.split("|")
                items.append({"text": tpl.format(w2=w2_, b=b_, z=row["z"], a=row["a"]),
                              "claims": [L["claims"][key]], "source": f"chrome:k_{key}", "where": where})
    return items


# ---------------------------------------------------------------- checks

def expected_values(lesson):
    sp = spec(lesson)
    out = {}
    for v in sp["values"]:
        cells = {}
        for role, fid in v["facts"].items():
            f = lesson.fact(fid)
            want = expect.evaluate(f["expect"], lesson.data.get("platform", {})).rstrip("\n")
            cells[fid] = want
        out[v["value"]] = {"facts": cells, "claims": [c for c in v.get("claims", [])]}
    return out


def neuron_problems(lesson):
    """The domain and the spot checks: every grid point finite and inside the drawn axes; at each check point
    the captured program printed exactly the grid's lines; the starting point equals the lesson's facts."""
    sp = spec(lesson)
    probs = []
    T = neuron_table(lesson, sp)
    for key, r in T["rows"].items():
        for k in ("zf", "af", "t1f", "t2f"):
            if r[k] != r[k] or abs(r[k]) > 1e6:
                probs.append(f"{key}: {k} is not finite")
        if not -1.0 <= r["zf"] <= 3.5:
            probs.append(f"{key}: z = {r['z']} is outside the explorer's axes")
    P = lesson.data["figure"]["panel"]
    num = lambda fid: float(_fact_text(lesson, fid).replace("−", "-"))  # noqa: E731
    x1, w1, x2 = num(P["terms"][0]["x"]), num(P["terms"][0]["w"]), num(P["terms"][1]["x"])
    for c in sp.get("checks", []):
        want = expect_neuron.lines(x1, w1, x2, c["at"]["w2"], c["at"]["b"])
        got = [_fact_text(lesson, c["facts"][r]) for r in ("t1", "t2", "z", "a")]
        if got != want:
            probs.append(f"check {c['program']} at {c['at']}: captured {got}, grid {want}")
        key = f"{expect_neuron.g(c['at']['w2'])}|{expect_neuron.g(c['at']['b'])}"
        if key not in T["rows"]:
            probs.append(f"check point {key} is not on the slider grid")
    base = T["rows"].get(f"{T['w2_0']}|{expect_neuron.g(num(P['bias']))}")
    if not base or base["z"] != _fact_text(lesson, P["sum"]) or base["a"] != _fact_text(lesson, P["out"]):
        probs.append("the sliders' starting point does not reproduce the captured run")
    return probs, T


def check(lesson, rec):
    """Problems in the driver's knob record (drive.mjs, stepper mode)."""
    sp = spec(lesson)
    if not sp:
        return [], 0
    k = rec.get("knob")
    if not k:
        return ["the driver recorded no knob"], 0
    probs, n = [], 0
    if sp["kind"] == "values":
        exp = expected_values(lesson)
        for snap in k:
            n += 1
            v = snap["value"]
            if snap.get("selected") != [v]:
                probs.append(f"a = {v}: selected rows {snap.get('selected')}")
            got = {f: t for f, t in snap.get("row", [])}
            if got != exp[v]["facts"]:
                probs.append(f"a = {v}: row shows {got}, expected {exp[v]['facts']}")
            if snap.get("prose") != exp[v]["claims"]:
                probs.append(f"a = {v}: prose {snap.get('prose')}, expected {exp[v]['claims']}")
    elif sp["kind"] == "calls":
        for v in sp["values"]:
            want = expected_calls(v["value"])
            got = [s for s in k if s["value"] == v["value"]]
            if len(got) != len(want):
                probs.append(f"n = {v['value']}: stepped {len(got)} steps, expected {len(want)}")
            for g, w in zip(got, want):
                n += 1
                wf = [{"label": f["label"], "status": f["status"], "vars": ([f"n = {f['n']}"] if f["n"] is not None else [])
                       + [f["r"]], "slot": f["slot"]} for f in w["frames"]]
                if g["frames"] != wf or g["printed"] != w["printed"]:
                    probs.append(f"n = {v['value']} step {w['line']}: page {g['frames']} / {g['printed']}, expected {wf} / {w['printed']}")
                    break
    else:
        lp, T = neuron_problems(lesson)
        probs += lp
        for snap in k:
            n += 1
            row = T["rows"].get(f"{snap['w2']}|{snap['b']}")
            if not row:
                probs.append(f"the page moved to {snap['w2']}|{snap['b']}, not a grid point")
                continue
            want = {"t1": row["t1"], "t2": row["t2"], "b": row["b"], "z": row["z"], "a": row["a"]}
            got = {kk: snap.get("bs" if kk == "b" else kk) for kk in want}
            if got != want:
                probs.append(f"w2 = {snap['w2']}, b = {snap['b']}: page {got}, expected {want}")
            gx, gy = gate_xy(row["zf"], row["af"])
            dot = snap.get("dot") or [None, None]
            if dot[0] is None or abs(dot[0] - gx) > 0.5 or abs(dot[1] - gy) > 0.5:
                probs.append(f"w2 = {snap['w2']}, b = {snap['b']}: the gate dot is at {dot}, expected ({gx:.1f}, {gy:.1f})")
    return probs, n


def driver_job(lesson):
    """What drive.mjs needs to drive the knob."""
    sp = spec(lesson)
    if not sp:
        return None
    if sp["kind"] != "neuron":
        return {"kind": sp["kind"], "values": [v["value"] for v in sp["values"]]}
    T = neuron_table(lesson, sp)
    pts = [(T["w2_0"], T["b_0"]), (T["w2"][0], T["b"][0]), (T["w2"][-1], T["b"][-1]), (T["w2"][0], T["b"][-1]),
           (T["w2"][-1], T["b"][0])]
    pts += [(expect_neuron.g(c["at"]["w2"]), expect_neuron.g(c["at"]["b"])) for c in sp.get("checks", [])]
    return {"kind": "neuron", "points": [{"w2": T["w2"].index(w), "b": T["b"].index(b)} for w, b in dict.fromkeys(pts)]}


def page_chars(lesson):
    sp = spec(lesson)
    if not sp or sp["kind"] != "neuron":
        return ""
    T = neuron_table(lesson, sp)
    return json.dumps(T["rows"])[:0] + "".join(sorted({ch for r in T["rows"].values() for v in r.values()
                                                      if isinstance(v, str) for ch in v}))
