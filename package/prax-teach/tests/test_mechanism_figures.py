"""AC-10.2 (SPEC v1.4 WP10): each lesson draws its mechanism, and every drawn value equals its captured fact.

Markup contract (projectors emit it; this test reads the rendered DOM in Playwright):
  container   one element per drawn mechanism: data-role="mechanism" data-kind="<kind>".
  values      every value drawn inside it carries data-fact="<fact id>" on the element whose text is exactly the
              value. The text must equal the value read again from build/capture/<program>.stdout (or the
              captured platform), not from lesson.json.
  parts       data-part="<name>" marks the pieces each kind needs:
    control-path (switch)   label  data-line=L   one per case/default label line of the program, in a column
                            enter  data-line=L   the label control enters at (first label on the final path)
                            fall   data-line=L   every later label on the path that control runs past
                            leave  data-line=L   the last line on the path inside the switch body (the break)
                            path                 the drawn path; it spans from enter to leave
                            and the final state's output facts, drawn inside the mechanism
    stack-column (factorial) frame data-call=<call fact id | main>   one per call in the trace, plus main
                            n      inside each call frame: its parameter (the number in the call)
                            ret    inside each call frame, data-fact=<its return fact>
                            return data-from=<callee call fact> data-to=<caller call fact | main>
                            frames form one column (x overlap >= 50%, no y overlap, ordered by depth); each
                            return lies between its two frames, and the caller frame shows the returned value
    bytes (one-byte)        bytes  data-var="a"          sizeof(int) cells, and data-var="(double)a" 8 cells
                            byte   data-offset=k data-fact=<fact>  text "42", "0x42" or "01000010"
                            exactly one cell of a with data-low="true": the least significant byte
                            the cells, in memory order and the captured endianness, rebuild a (from the trace)
                            and the IEEE-754 bits of (double)a, computed here independently
    neuron                  panel x3 or more, and every fact the lesson's figure.panel names drawn inside
Checked in both themes of the wide still (structure and values) and in the video: at least one scene's settled
frame shows a mechanism of the lesson's kind, and every value any shown mechanism draws equals its capture.
"""
import json
import re
import struct

import _b0

LABEL_RE = re.compile(r"^\s*(case\s+[^:]+|default)\s*:")


def context(data, capture_dir, sources):
    facts, drift = _b0.captured_facts(data, capture_dir)
    trace = {s["id"]: s for s in data.get("trace", [])}
    fig = data.get("figure") or {}
    states = [trace[s]["state"] for s in fig.get("states", []) if s in trace]
    return {"data": data, "facts": facts, "drift": drift, "platform": data.get("platform", {}), "sources": sources,
            "fig": fig, "first": states[0] if states else {}, "final": states[-1] if states else {},
            "trace": [s["state"] for s in data.get("trace", [])]}


def _parts(m, mi):
    parts = m["parts"]

    def chain(j):
        seen = []
        while j is not None and j not in seen:
            seen.append(j)
            j = parts[j].get("parent")
        return seen
    inside = {j: {k for k in range(len(parts)) if j in chain(k)} for j in range(len(parts)) if parts[j].get("mech") == mi}
    return parts, inside


def _items_in(m, inside_set):
    return [it for it in m["items"] if it.get("part") in inside_set]


def _text(items):
    return _b0.norm_text(" ".join(it["t"] for it in items if it["k"] == "text"))


def _center(b):
    return (b[0] + b[2] / 2, b[1] + b[3] / 2)


def check_values(items, ctx):
    """Every drawn value inside the mechanism equals its capture. Returns (checked, problems)."""
    n, bad = 0, []
    for it in items:
        fid = _own_fact(it)
        if it["k"] != "text" or not fid or it.get("o", 1) < 0.05:
            continue
        n += 1
        if fid not in ctx["facts"]:
            bad.append({"kind": "unknown-fact", "fact": fid, "shown": it["t"]})
            continue
        cap = ctx["facts"][fid]
        if cap is None:
            bad.append({"kind": "fact-not-in-capture", "fact": fid})
        elif _b0.norm_text(it["t"]) != _b0.norm_text(cap.rstrip("\n")):
            bad.append({"kind": "value-differs", "fact": fid, "shown": it["t"], "captured": cap.rstrip("\n")})
    return n, bad


def _own_fact(it):
    """The fact an element itself carries (data-fact on the element whose text is the value). A data-fact or
    data-m on an enclosing group does not make every label inside it a value."""
    return (it.get("d") or {}).get("fact")


def _drawn_facts(items):
    return {_own_fact(it) for it in items if it["k"] == "text" and _own_fact(it) and it.get("o", 1) >= 0.05}


# ---------------------------------------------------------------- per kind

def _switch_body(src):
    sw = next((i for i, ln in enumerate(src) if re.search(r"\bswitch\s*\(", ln)), None)
    if sw is None:
        return None, None
    depth, opened = 0, False
    for i in range(sw, len(src)):
        depth += src[i].count("{") - src[i].count("}")
        opened = opened or "{" in src[i]
        if opened and depth <= 0:
            return sw + 1, i + 1  # 1-based: the switch line and its closing brace line
    return sw + 1, len(src)


def check_control_path(m, mi, ctx):
    probs = []
    fig = ctx["fig"]
    src = ctx["sources"].get(fig.get("program"), "").split("\n")
    labels = [i + 1 for i, ln in enumerate(src) if LABEL_RE.match(ln)]
    sw, end = _switch_body(src)
    path = ctx["final"].get("path", [])
    entered = [ln for ln in path if ln in labels]
    in_body = [ln for ln in path if sw and sw < ln < end]
    want = {"enter": entered[0] if entered else None, "fall": entered[1:], "leave": in_body[-1] if in_body else None}
    parts, inside = _parts(m, mi)
    by = {}
    for j in inside:
        by.setdefault(parts[j]["d"].get("part"), []).append(j)

    def line(j):
        try:
            return int(parts[j]["d"].get("line"))
        except (TypeError, ValueError):
            return None
    drawn_labels = {line(j): j for j in by.get("label", [])}
    if set(drawn_labels) != set(labels):
        probs.append({"kind": "labels", "want_lines": labels, "drawn_lines": sorted(k for k in drawn_labels if k)})
    for ln, j in drawn_labels.items():
        if ln in labels:
            want_txt = _b0.norm_text(src[ln - 1].strip().rstrip(":"))
            if want_txt not in _text(_items_in(m, inside[j])):
                probs.append({"kind": "label-text", "line": ln, "want": want_txt, "drawn": _text(_items_in(m, inside[j]))})
    ys = [_center(parts[drawn_labels[ln]]["b"])[1] for ln in sorted(k for k in drawn_labels if k in labels)]
    if any(b <= a for a, b in zip(ys, ys[1:])):
        probs.append({"kind": "labels-not-a-column", "y_centers": [round(y) for y in ys]})
    enter = [line(j) for j in by.get("enter", [])]
    if enter != [want["enter"]]:
        probs.append({"kind": "enter", "want": want["enter"], "drawn": enter})
    falls = sorted(line(j) for j in by.get("fall", []))
    if not set(want["fall"]) <= set(falls):
        probs.append({"kind": "fall", "want": want["fall"], "drawn": falls})
    leave = [line(j) for j in by.get("leave", [])]
    if leave != [want["leave"]]:
        probs.append({"kind": "leave", "want": want["leave"], "drawn": leave})
    if not by.get("path"):
        probs.append({"kind": "no-path"})
    elif enter == [want["enter"]] and leave == [want["leave"]]:
        pb = _b0.hull([(p["b"][0], p["b"][1], p["b"][0] + p["b"][2], p["b"][1] + p["b"][3])
                       for p in (parts[j] for j in by["path"])])
        ye = _center(parts[by["enter"][0]]["b"])[1]
        yl = _center(parts[by["leave"][0]]["b"])[1]
        if not (pb[1] - 6 <= min(ye, yl) and pb[3] + 6 >= max(ye, yl)):
            probs.append({"kind": "path-does-not-span", "path_y": [round(pb[1]), round(pb[3])],
                          "enter_y": round(ye), "leave_y": round(yl)})
    drawn = _drawn_facts([it for it in m["items"] if it.get("mech") == mi])
    missing = [f for f in ctx["final"].get("output", []) if f not in drawn]
    if missing:
        probs.append({"kind": "outputs-missing", "facts": missing})
    return probs, want


def _ret_map(ctx):
    """call text -> return fact id: a derived fact that is the last field of a stdout line "<call> = <value>"."""
    out = {}
    for f in ctx["data"].get("facts", []):
        sel = f.get("select", {})
        if "field" not in sel or sel.get("stream") != "stdout":
            continue
        line = _b0.capture_value({**f, "select": {k: v for k, v in sel.items() if k != "field"}},
                                 ctx["capture_dir"], ctx["platform"]) or ""
        parts = line.split()
        if len(parts) >= 3 and parts[1] == "=" and sel["field"] == len(parts):
            out[parts[0]] = f["id"]
    return out


def check_stack_column(m, mi, ctx):
    probs = []
    calls = []
    for st in ctx["trace"]:
        for fr in st.get("frames", []):
            if fr.get("call") and fr["call"] not in calls:
                calls.append(fr["call"])
    rets = _ret_map(ctx)
    parts, inside = _parts(m, mi)
    frames = {parts[j]["d"].get("call"): j for j in inside if parts[j]["d"].get("part") == "frame"}
    want = ["main"] + calls
    if set(frames) != set(want):
        probs.append({"kind": "frames", "want": want, "drawn": sorted(k for k in frames if k)})
    ret_of = {}
    for c in calls:
        if c not in frames:
            continue
        j = frames[c]
        its = _items_in(m, inside[j])
        call_txt = (ctx["facts"].get(c) or "")
        if c not in _drawn_facts(its):
            probs.append({"kind": "frame-call-not-drawn", "call": c})
        mnum = re.search(r"\((-?\d+)\)", call_txt)
        nparts = [k for k in inside[j] if parts[k]["d"].get("part") == "n"]
        if not nparts or not mnum or not re.search(rf"(?<![\d.]){re.escape(mnum.group(1))}(?![\d.])",
                                                   _text(_items_in(m, set().union(*(inside[k] for k in nparts))))):
            probs.append({"kind": "frame-n", "call": c, "want": mnum.group(1) if mnum else None})
        rf = rets.get(call_txt)
        ret_of[c] = rf
        rparts = [k for k in inside[j] if parts[k]["d"].get("part") == "ret"]
        rfacts = {parts[k]["d"].get("fact") for k in rparts} | _drawn_facts(
            _items_in(m, set().union(*(inside[k] for k in rparts)) if rparts else set()))
        if not rf or rf not in rfacts:
            probs.append({"kind": "frame-ret", "call": c, "want": rf, "drawn": sorted(x for x in rfacts if x)})
    fb = {c: parts[j]["b"] for c, j in frames.items() if c in want}
    names = [c for c in want if c in fb]
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            A, B = fb[a], fb[b]
            ox = min(A[0] + A[2], B[0] + B[2]) - max(A[0], B[0])
            oy = min(A[1] + A[3], B[1] + B[3]) - max(A[1], B[1])
            if ox < 0.5 * min(A[2], B[2]) or oy > 2:
                probs.append({"kind": "frames-not-a-column", "a": a, "b": b, "x_overlap": round(ox), "y_overlap": round(oy)})
    ys = [_center(fb[c])[1] for c in names]
    if len(ys) >= 2 and not (all(b > a for a, b in zip(ys, ys[1:])) or all(b < a for a, b in zip(ys, ys[1:]))):
        probs.append({"kind": "frames-not-in-depth-order", "order": names, "y_centers": [round(y) for y in ys]})
    returns = [parts[j] for j in inside if parts[j]["d"].get("part") == "return"]
    for i, callee in enumerate(calls):
        caller = calls[i - 1] if i else "main"
        hit = [r for r in returns if r["d"].get("from") == callee and r["d"].get("to") == caller]
        if not hit:
            probs.append({"kind": "return-missing", "from": callee, "to": caller})
            continue
        if callee in fb and caller in fb:
            y0, y1 = sorted((_center(fb[callee])[1], _center(fb[caller])[1]))
            rb = hit[0]["b"]
            if rb[1] > y1 or rb[1] + rb[3] < y0:
                probs.append({"kind": "return-not-between-frames", "from": callee, "to": caller})
        if caller in frames and ret_of.get(callee) and ret_of[callee] not in _drawn_facts(_items_in(m, inside[frames[caller]])):
            probs.append({"kind": "return-value-not-in-caller", "from": callee, "to": caller, "fact": ret_of.get(callee)})
    return probs, {"calls": calls, "returns": ret_of}


def _byte(txt):
    t = _b0.norm_text(txt).lower()
    if re.fullmatch(r"(0x)?[0-9a-f]{2}", t):
        return int(t[-2:], 16)
    if re.fullmatch(r"[01]{8}", t):
        return int(t, 2)
    return None


def check_bytes(m, mi, ctx):
    probs = []
    plat = ctx["platform"]
    little = plat.get("endianness", "little") == "little"
    var = ((ctx["fig"].get("panel") or {}).get("value") or {}).get("var") or next(iter(ctx["first"].get("vars", {})), "a")
    try:
        a = int(ctx["first"]["vars"][var])
    except (KeyError, TypeError, ValueError):
        return [{"kind": "no-int-in-trace", "var": var}], {}
    isz, dsz = int(plat.get("sizeof", {}).get("int", 4)), int(plat.get("sizeof", {}).get("double", 8))
    want_int = list((a & (2 ** (8 * isz) - 1)).to_bytes(isz, "little" if little else "big"))
    want_dbl = list(struct.pack("<d" if little else ">d", float(a)))
    parts, inside = _parts(m, mi)
    groups = {parts[j]["d"].get("var"): j for j in inside if parts[j]["d"].get("part") == "bytes"}
    out = {}
    for gname, want, size in ((var, want_int, isz), (f"(double){var}", want_dbl, dsz)):
        if gname not in groups:
            probs.append({"kind": "bytes-group-missing", "var": gname})
            continue
        g = groups[gname]
        cells = [k for k in inside[g] if parts[k]["d"].get("part") == "byte"]
        got = {}
        for k in cells:
            its = _items_in(m, inside[k])
            val = _byte(_text(its))
            try:
                off = int(parts[k]["d"].get("offset"))
            except (TypeError, ValueError):
                off = None
            fid = parts[k]["d"].get("fact") or next(iter(_drawn_facts(its)), None)
            cap = _byte(ctx["facts"].get(fid) or "") if fid else None
            if val is None or off is None:
                probs.append({"kind": "byte-unreadable", "var": gname, "text": _text(its), "offset": parts[k]["d"].get("offset")})
                continue
            if fid is None or fid not in ctx["facts"]:
                probs.append({"kind": "byte-without-fact", "var": gname, "offset": off})
            elif cap != val:
                probs.append({"kind": "byte-differs-from-capture", "var": gname, "offset": off, "drawn": val, "captured": cap})
            got[off] = (val, k)
        drawn = [got[i][0] if i in got else None for i in range(size)]
        out[gname] = {"drawn": drawn, "expected": want}
        if len(cells) != size or drawn != want:
            probs.append({"kind": "bytes-wrong", "var": gname, "cells": len(cells), "size": size,
                          "drawn": drawn, "expected": want})
        ys = [_center(parts[got[i][1]]["b"])[1] for i in sorted(got)]
        if ys and max(ys) - min(ys) > 3:
            probs.append({"kind": "bytes-not-in-a-row", "var": gname})
        if gname == var:
            low = [k for k in cells if parts[k]["d"].get("low") == "true"]
            low_off = 0 if little else isz - 1
            if len(low) != 1 or int(parts[low[0]]["d"].get("offset", -1)) != low_off:
                probs.append({"kind": "low-byte-mark", "marked": [parts[k]["d"].get("offset") for k in low],
                              "want_offset": low_off})
    return probs, out


def check_neuron(m, mi, ctx):
    pan = ctx["fig"].get("panel") or {}
    want = [t[k] for t in pan.get("terms", []) for k in ("x", "w", "t")] + [pan.get(k) for k in ("bias", "sum", "out")]
    want = [w for w in want if w]
    drawn = _drawn_facts([it for it in m["items"] if it.get("mech") == mi])
    probs = []
    if not want:
        probs.append({"kind": "lesson-has-no-neuron-panel"})
    missing = [f for f in want if f not in drawn]
    if missing:
        probs.append({"kind": "panel-facts-missing", "facts": missing})
    parts, inside = _parts(m, mi)
    n = sum(1 for j in inside if parts[j]["d"].get("part") == "panel")
    if n < 3:
        probs.append({"kind": "panels", "drawn": n, "want": 3})
    return probs, {"required_facts": want}


CHECKS = {"control-path": check_control_path, "stack-column": check_stack_column, "bytes": check_bytes,
          "neuron": check_neuron}


def evaluate(m, kind, ctx, structure=True):
    """One rendered artifact: the first visible mechanism of `kind`. Returns a result dict with problems."""
    if not m or m.get("error"):
        return {"problems": [{"kind": "render-failed", "error": (m or {}).get("error")}]}
    vis = [i for i, c in enumerate(m["mechanisms"]) if c.get("o", 1) >= 0.05]
    mine = [i for i in vis if m["mechanisms"][i]["d"].get("kind") == kind]
    res = {"mechanisms_found": [m["mechanisms"][i]["d"].get("kind") for i in vis]}
    if not mine:
        res["problems"] = [{"kind": "no-mechanism", "want": kind, "found": res["mechanisms_found"]}]
        return res
    mi = mine[0]
    n, bad = check_values([it for it in m["items"] if it.get("mech") == mi], ctx)
    probs = list(bad)
    if not n:
        probs.append({"kind": "no-values-drawn"})
    if structure:
        sp, info = CHECKS[kind](m, mi, ctx)
        probs += sp
        res["expected"] = info
    res.update({"values_checked": n, "problems": probs})
    return res


def evaluate_stills(svgs, kind, ctx):
    ext, outbound = _b0.extract_svgs(svgs, "mech")
    out = {str(p.name): evaluate(ext.get(str(p)), kind, ctx) for p in svgs}
    probs = [{**pr, "svg": n} for n, r in out.items() for pr in r["problems"]]
    if outbound:
        probs.append({"kind": "outbound-request", "requests": outbound[:5]})
    if ctx["drift"]:
        probs.append({"kind": "lesson-json-differs-from-capture", "facts": ctx["drift"]})
    return out, probs


# ---------------------------------------------------------------- fixtures

def _fixture(kind):
    d = _b0.FIXTURES / "mech" / kind
    data = json.loads((d / "lesson.json").read_text())
    sources = {p["id"]: (d / p["path"]).read_text() for p in data.get("programs", []) if (d / p["path"]).is_file()}
    ctx = context(data, d / "capture", sources)
    ctx["capture_dir"] = d / "capture"
    return d, ctx


def _fixture_case(kind, name):
    d, ctx = _fixture(kind)
    return evaluate_stills([d / name], kind, ctx)


def test_fixture_good_mechanisms_pass():
    """One fixture per kind that follows the contract with captured values: all pass."""
    got = {}
    for kind in CHECKS:
        out, probs = _fixture_case(kind, "pass.svg")
        assert not probs, (kind, probs)
        got[kind] = next(iter(out.values()))["values_checked"]
    return {"values_checked": got}


FAIL_EXPECT = {
    "control-path": {"enter", "leave", "value-differs"},
    "stack-column": {"frames-not-a-column", "return-missing", "frame-ret"},
    "bytes": {"bytes-wrong", "low-byte-mark", "byte-differs-from-capture"},
    "neuron": {"panel-facts-missing", "panels", "value-differs"},
}


def test_fixture_bad_mechanisms_fail():
    """One broken fixture per kind (wrong entry, arcs instead of a column, a wrong byte, a missing panel value):
    each fails for its own reasons, and a still with no mechanism at all fails too."""
    got = {}
    for kind, want in FAIL_EXPECT.items():
        _out, probs = _fixture_case(kind, "fail.svg")
        kinds = {p["kind"] for p in probs}
        assert want <= kinds, (kind, sorted(kinds), probs)
        got[kind] = sorted(kinds)
    _out, probs = _fixture_case("bytes", "none.svg")
    assert {p["kind"] for p in probs} == {"no-mechanism"}, probs
    return got


# ---------------------------------------------------------------- the built lessons

def lesson_kind(lesson):
    return (lesson.data.get("figure") or {}).get("mechanism") or _b0.MECHANISM_KIND.get(lesson.id)


def _video_values(b, lesson, kind, ctx):
    timing = json.loads((b / "video" / "timing.json").read_text())
    samples = [(f"{s['id']}@settled", s["start"] + _b0.check_points(s)["settled"]) for s in timing["scenes"]]
    frames = _b0.probe_video(b / "video", timing, samples, "mech-video", lesson.sha256())
    rows, probs = {}, []
    for label, m in frames.items():
        if m.get("error"):
            probs.append({"kind": "frame-probe-failed", "at": label, "error": m["error"]})
            continue
        r = evaluate(m, kind, ctx, structure=False)
        rows[label] = {"mechanisms": r.get("mechanisms_found"), "values_checked": r.get("values_checked", 0),
                       "drawn_items": len(m.get("items", [])),
                       "problems": [p for p in r["problems"] if p["kind"] != "no-mechanism"]}
        probs += [{**p, "at": label} for p in rows[label]["problems"]]
    if not any(kind in (r["mechanisms"] or []) for r in rows.values()):
        probs.append({"kind": "video-never-draws-mechanism", "want": kind, "scenes": len(rows)})
    return rows, probs


def _lesson(slug):
    b = _b0.need(slug, "still", "capture", "video/timing.json", "video/composition")
    lesson = _b0.load(slug)
    kind = lesson_kind(lesson)
    if kind not in CHECKS:
        raise _b0.NotRun(f"no mechanism kind defined for {slug}")
    sources = {p["id"]: lesson.program_source(p["id"]) for p in lesson.data["programs"]}
    ctx = context(lesson.data, b / "capture", sources)
    ctx["capture_dir"] = b / "capture"
    svgs = [b / "still" / f"{lesson.id}-wide-{th}.svg" for th in ("light", "dark")]
    missing = [p.name for p in svgs if not p.is_file()]
    if missing:
        raise _b0.NotRun(f"not built: lessons/{slug}/build/still/{missing[0]}")
    still, probs = evaluate_stills(svgs, kind, ctx)
    video, vprobs = _video_values(b, lesson, kind, ctx)
    probs += [{**p, "medium": "video"} for p in vprobs]
    rec = _b0.record(f"ac10.2-{slug}", {"lesson": slug, "kind": kind, "still": still, "video": video, "problems": probs})
    summary = {"kind": kind, "still": {n: {"found": r.get("mechanisms_found"), "values": r.get("values_checked", 0)}
                                       for n, r in still.items()},
               "video_scenes_with_mechanism": sum(1 for r in video.values() if kind in (r["mechanisms"] or []))}
    assert not probs, json.dumps({"summary": summary, "problems": sorted({p["kind"] for p in probs}), "record": rec})
    return {"summary": summary, "record": rec}


_b0.lesson_tests(globals(), "AC-10.2 mechanism figure", _lesson)
