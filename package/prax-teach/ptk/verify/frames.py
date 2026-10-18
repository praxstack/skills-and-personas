r"""What the video frame shows at time t, read from the composition itself (review P1-3, AC-5.6).

Each scene's sub-composition is loaded on its own in a 1920 x 1080 page with the same GSAP and
fonts, and its paused timeline is seeked to the frame time, exactly as the renderer seeks it.
The rendered state is then *derived from what is drawn*, not from timing data:

    program   the program whose source matches the drawn code rows (not a data attribute)
    line      the code row under the highlight bar (its current transform)
    path      the rail dots that are fully opaque
    output    the output values that are fully opaque, in order

and matched against the lesson's trace states. A frame in mid-tween (a segment partly drawn, a
dot or value partly faded, or any tween on the code or output card still running) is "moving". The same pass measures the AC-5.6 layout: every key
node fully inside the frame, no text overflow, no text under 11 px, and no empty band at the
bottom of the frame.

    video time t ──▶ frame k = floor(t * fps) ──▶ scene s with start <= k/fps < end
                 ──▶ tl.seek(k/fps - s.start) ──▶ derive {program, line, path, output} ──▶ state id
"""
import math
import re
import shutil

from . import visual

EOP_JS = r"""const eop = (el) => { let o = 1; for (let e = el; e && e.nodeType === 1 && e !== document.body; e = e.parentElement)
    o *= parseFloat(getComputedStyle(e).opacity); return o; };"""

PROBE_JS = r"""(t) => {
  const root = document.querySelector('[data-composition-id]');
  const tl = window.__timelines[root.dataset.compositionId];
  tl.seek(t, false);
  """ + EOP_JS + r"""
  const op = eop;
  const hl = root.querySelector('.hl');
  const hb = hl.getBoundingClientRect();
  // only rows that are fully visible carry the program's identity (a morph draws two sets)
  const rows = [...root.querySelectorAll('.ln[data-line]')].filter((r) => eop(r) >= 0.99);
  let line = null, best = 1e9;
  for (const r of rows) {
    const b = r.getBoundingClientRect(); const d = Math.abs((b.top + b.bottom) / 2 - (hb.top + hb.bottom) / 2);
    if (d < best) { best = d; line = +r.dataset.line; }
  }
  const dots = [...root.querySelectorAll('.dot')];
  const vals = [...root.querySelectorAll('.out .val')];
  const segs = [...root.querySelectorAll('.seg')].filter((s) => eop(s.parentElement) > 0.01)
    .map((s) => parseFloat(getComputedStyle(s).strokeDashoffset) || 0);
  // any tween on the mechanism (code card or output card) still running at t
  const mech = (el) => el && el.closest && el.closest('.code, .outcard, .mechbox');
  const active = tl.getChildren(false, true, true).some((ch) => (ch.data === 'draw' || (ch.targets && ch.targets().some(mech)))
    && ch.startTime() <= t + 1e-6 && t < ch.endTime() - 1e-6);
  // the mechanism panel: the state of the top layer that is fully shown (a panel lesson draws two layers in a
  // scene that changes state; mid cross-fade is moving)
  const layers = [...root.querySelectorAll('.mlayer')];
  const fullL = layers.filter((l) => eop(l) >= 0.99);
  const panel = layers.length ? (fullL.length ? fullL[fullL.length - 1].dataset.panelState : null) : undefined;
  const moving = active || best > 1.5 || eop(hl) < 0.99 || segs.some((d) => d > 0.002 && d < 0.998)
    || layers.some((l) => eop(l) > 0.01 && eop(l) < 0.99)
    || dots.some((d) => op(d) > 0.01 && op(d) < 0.99)
    || vals.some((v) => op(v) > 0.01 && op(v) < 0.99);
  const code = rows.map((r) => [+r.dataset.line, r.querySelector('.src').textContent]);
  // what the side note and the diff show (WP6: the note waits until the diff is complete)
  const one = (s) => { const e = root.querySelector(s); return e ? +eop(e).toFixed(3) : null; };
  const each = (s) => [...root.querySelectorAll(s)].map((e) => +eop(e).toFixed(3));
  const diff = { file_old: one('.file[data-set="old"]'), file_cur: one('.file[data-set="cur"]'),
                 removed: each('.band.minus'), added: each('.ln.add'), rows_cur: one('.rows[data-set="cur"]') };
  return { t, code, line, note: one('.notecard'), diff, panel: panel === undefined ? 'none' : panel,
           path: dots.filter((d) => op(d) >= 0.99).map((d) => +d.dataset.line),
           output: vals.filter((v) => op(v) >= 0.99).map((v) => v.dataset.fact),
           moving };
}"""

LAYOUT_JS = r"""() => {
  const W = 1920, H = 1080, problems = [];
  const root = document.querySelector('[data-composition-id]');
  """ + EOP_JS + r"""
  const keys = [...document.querySelectorAll('[data-key]')];
  let lowest = 0;
  for (const k of keys) {
    const b = k.getBoundingClientRect();
    lowest = Math.max(lowest, b.bottom);
    if (b.left < -0.5 || b.top < -0.5 || b.right > W + 0.5 || b.bottom > H + 0.5)
      problems.push({ kind: 'key-node-outside-frame', key: k.dataset.key, box: [b.left, b.top, b.right, b.bottom].map(Math.round) });
    if (k.scrollHeight > k.clientHeight + 1 || k.scrollWidth > k.clientWidth + 1)
      problems.push({ kind: 'key-node-inner-overflow', key: k.dataset.key, scroll: [k.scrollWidth, k.scrollHeight], client: [k.clientWidth, k.clientHeight] });
  }
  let minPx = 1e9;
  for (const el of root.querySelectorAll('*')) {
    const own = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
    if (!own || eop(el) < 0.02) continue;  // text nobody can see (faded out) is not on screen
    const st = getComputedStyle(el), b = el.getBoundingClientRect();
    const px = parseFloat(st.fontSize); minPx = Math.min(minPx, px);
    if (px < 11) problems.push({ kind: 'min-size', text: el.textContent.trim().slice(0, 40), px });
    if (b.left < -0.5 || b.right > W + 0.5 || b.top < -0.5 || b.bottom > H + 0.5)
      problems.push({ kind: 'text-outside-frame', text: el.textContent.trim().slice(0, 40) });
    const box = el.closest('[data-key]');
    if (box && box !== el) {
      const c = box.getBoundingClientRect();
      if (b.left < c.left - 0.5 || b.right > c.right + 0.5 || b.top < c.top - 0.5 || b.bottom > c.bottom + 0.5)
        problems.push({ kind: 'text-outside-card', key: box.dataset.key, text: el.textContent.trim().slice(0, 40) });
    }
  }
  // no empty panel: an output card on screen shows at least one value (dimmed values of the previous run count)
  const outcard = root.querySelector('.outcard');
  const outs = [...root.querySelectorAll('.out')];
  if (outcard && eop(outcard) > 0.5 && !outs.some((o) => eop(o) > 0.2))
    problems.push({ kind: 'empty-panel', key: 'output' });
  // D20.5: every output value on screen is paired with its mechanism: the step badge on the code
  // line that printed it, and that line on the drawn path
  const pairs = [];
  for (const o of outs.filter((o) => eop(o) >= 0.99)) {
    const set = o.dataset.set, step = o.dataset.step;
    const badge = [...root.querySelectorAll('.ostep')].find((b) => b.dataset.set === set && b.dataset.step === step && eop(b) >= 0.99);
    if (!badge) { problems.push({ kind: 'summary-without-mechanism', step: +step }); continue; }
    const dot = [...root.querySelectorAll('.dot')].find((d) => d.dataset.set === set && d.dataset.line === badge.dataset.line && eop(d) >= 0.99);
    if (!dot) problems.push({ kind: 'mechanism-not-drawn', step: +step, line: +badge.dataset.line });
    pairs.push({ step: +step, line: +badge.dataset.line, drawn: !!dot });
  }
  const band = H - lowest;
  return { problems, pairs, min_px: minPx, empty_bottom_px: Math.round(band), empty_bottom_frac: +(band / H).toFixed(3),
           key_nodes: keys.map((k) => k.dataset.key) };
}"""

MAX_EMPTY_BOTTOM = 0.12


def harness_pages(comp, out):
    """One standalone page per scene: the template's contents, GSAP and the composition's fonts."""
    out.mkdir(parents=True, exist_ok=True)
    rel = "../../composition/"
    pages = {}
    for f in sorted((comp / "compositions").glob("*.html")):
        src = f.read_text()
        inner = re.search(r"<template>(.*)</template>", src, re.S).group(1)
        page = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><base href="{rel}">'
                f'<script src="vendor/gsap.min.js"></script><style>html,body{{margin:0;width:1920px;height:1080px;'
                f'overflow:hidden;position:relative}}</style></head><body>{inner}</body></html>')
        (out / f.name).write_text(page)
        pages[f.stem] = f.name
    return pages


def frame_time(t, fps):
    """The time of the video frame on screen at t (the frame that started at or before t)."""
    return math.floor(t * fps + 1e-6) / fps


def scene_at(timing, t):
    return next(s for s in timing["scenes"] if s["start"] <= t + 1e-6 < s["end"] or s is timing["scenes"][-1])


def drawn_program(lesson, code):
    """The one program whose source lines are exactly the drawn code rows (review P3-B), else None."""
    hits = [p["id"] for p in lesson.data["programs"] if code and all(
        0 < n <= len(src) and src[n - 1].strip() == txt.strip()
        for src in [lesson.program_source(p["id"]).split("\n")] for n, txt in code)]
    return hits[0] if len(hits) == 1 else None


def match_state(lesson, probe):
    if probe.get("moving"):
        return "moving"
    for st in lesson.data["trace"]:
        s = st["state"]
        if (s["program"] == probe["program"] and s["line"] == probe["line"]
                and sorted(set(s.get("path", []))) == sorted(set(probe["path"])) and s["output"] == probe["output"]
                and probe.get("panel", "none") in ("none", st["id"])):
            return st["id"]
    return "unknown"


def check_points(scene):
    """Local times checked per scene: the midpoint (AC-5.6) and the settled end of its drawing."""
    last = round(scene["duration"] - 1 / 30, 3)
    settled = min(max(round(scene["shown"] - scene["start"] + 0.05, 3), round(scene["duration"] / 2, 3)), last)
    return {"mid": round(scene["duration"] / 2, 3), "settled": settled}


def probe(lesson, video_dir, timing, times, snapshots=None, work_name="frames", lesson_sha=None):
    """Derived frame state at each video time in `times`, plus per scene the derived state, the
    layout and (with `snapshots`, a dir) a PNG at each check point.
    Returns ({t: {...probe, state, scene}}, {scene_id: {point: {state, layout}}})."""
    comp = video_dir / "composition"
    hdir = video_dir / "work" / work_name
    if hdir.exists():
        shutil.rmtree(hdir)
    pages = harness_pages(comp, hdir)
    fps = timing["fps"]
    per_scene = {}
    for t in times:
        ft = frame_time(t, fps)
        sc = scene_at(timing, ft)
        per_scene.setdefault(sc["id"], []).append((t, round(ft - sc["start"], 4)))
    jobs = []
    with visual.LocalServer(video_dir) as srv:
        for sc in timing["scenes"]:
            steps = [{"waitFor": "window.__timelines && Object.keys(window.__timelines).length > 0", "timeout": 20000}]
            for t, local in per_scene.get(sc["id"], []):
                steps.append({"eval": f"({PROBE_JS})({local})", "as": f"t:{t}"})
            for name, local in check_points(sc).items():
                steps += [{"eval": f"({PROBE_JS})({local})", "as": f"p:{name}"}, {"eval": f"({LAYOUT_JS})()", "as": f"l:{name}"}]
                if snapshots:
                    steps.append({"shot": str(snapshots / f"{sc['id']}-{name}.png")})
            jobs.append({"id": f"scene:{sc['id']}", "type": "script", "url": f"{srv.url}/work/{work_name}/{pages[sc['id']]}",
                         "width": 1920, "height": 1080, "steps": steps})
        res = visual.shoot(jobs, video_dir / "work" / f"{work_name}-run", lesson_sha)
    frames, scenes = {}, {}
    for r in res["results"]:
        sid = r["id"].split(":", 1)[1]
        vals = r.get("values", {})
        for k, v in vals.items():
            if isinstance(v, dict) and "code" in v:
                v["program"] = drawn_program(lesson, v.pop("code"))
            if k.startswith("t:"):
                frames[float(k[2:])] = {**v, "scene": sid, "state": match_state(lesson, v)}
        scenes[sid] = {"ok": r.get("ok"), "error": r.get("error", "")[:400],
                       "console": [c for c in r.get("console", []) if "error" in c.lower()]}
        for name in ("mid", "settled"):
            if f"p:{name}" in vals:
                scenes[sid][name] = {"state": match_state(lesson, vals[f"p:{name}"]), "layout": vals.get(f"l:{name}")}
    return frames, scenes


def scene_layout_gate(lesson, video_dir, timing, lesson_sha=None):
    """AC-5.6 for WP0: at each scene's midpoint and settled point, every key node inside the frame,
    no overflow, text >= 11 px, the empty band under the lowest key node under 12% of the frame,
    and a frame that shows a known trace state (the scene's own state once settled)."""
    snaps = video_dir / "work" / "snapshots"
    if snaps.exists():
        shutil.rmtree(snaps)
    _f, scenes = probe(lesson, video_dir, timing, [], snapshots=snaps, work_name="frames-layout", lesson_sha=lesson_sha)
    bad, summary = {}, {}
    for s in timing["scenes"]:
        got = scenes.get(s["id"], {})
        probs = [] if got.get("ok") else [{"kind": "job-failed", "error": got.get("error")}]
        if got.get("console"):
            probs.append({"kind": "console", "messages": got["console"][:5]})
        for name in ("mid", "settled"):
            pt = got.get(name) or {}
            lay = pt.get("layout") or {}
            probs += [{**pr, "at": name} for pr in lay.get("problems", [])]
            if lay.get("empty_bottom_frac", 1) > MAX_EMPTY_BOTTOM:
                probs.append({"kind": "empty-bottom-band", "at": name, "frac": lay.get("empty_bottom_frac")})
            # the midpoint may fall inside the scene's own drawing (a morph is long); it must still
            # pass the layout checks, and the settled point must show the scene's state
            drawing = name == "mid" and s["reveal"] - s["start"] <= s["duration"] / 2 < s["shown"] - s["start"]
            if pt.get("state") in (None, "unknown") or (pt.get("state") == "moving" and not drawing):
                probs.append({"kind": "no-trace-state", "at": name, "shows": pt.get("state")})
        if (got.get("settled") or {}).get("state") != s["state"]:
            probs.append({"kind": "settled-state", "shows": (got.get("settled") or {}).get("state"), "scene_state": s["state"]})
        summary[s["id"]] = {n: {"state": (got.get(n) or {}).get("state"),
                                **{k: ((got.get(n) or {}).get("layout") or {}).get(k)
                                   for k in ("min_px", "empty_bottom_frac", "key_nodes")}} for n in ("mid", "settled")}
        if probs:
            bad[s["id"]] = probs
    measured = {"scenes": summary, "problems": bad, "max_empty_bottom": MAX_EMPTY_BOTTOM,
                "snapshots": sorted(f"video/work/snapshots/{p.name}" for p in snaps.glob("*.png"))}
    return visual.g("video.scene-layout", "video", not bad and len(scenes) == len(timing["scenes"]), measured,
                    "" if not bad else "scene snapshots fail the AC-5.6 layout or show no trace state")


def _tween_ok(cue, nxt, frame):
    """A frame in mid-tween is acceptable only inside a transition or answer cue, drawing the
    explorer's program on a path between the cue's state and the next cue's (review P1-A).
    Across a change of program (the diff morph), the rows on screen are still the explorer's
    program, and the dots drawn belong to one of the two paths."""
    if cue["kind"] not in ("transition", "answer") or frame.get("state") != "moving" or nxt is None:
        return False
    drawn, lo, hi = set(frame.get("path") or []), cue["state"], nxt["state"]
    if lo["program"] != hi["program"]:
        return frame.get("program") == lo["program"] and (drawn <= set(lo["path"]) or drawn <= set(hi["path"]))
    return (frame.get("program") == lo["program"] == hi["program"]
            and set(lo["path"]) <= drawn <= set(hi["path"]))


def compare_pauses(cue_list, frame_at, explorer, points):
    """Rows for every pause point; a row is bad when the explorer is not on the cue's state, or the
    frame shows something else (see _tween_ok for the one allowed mid-tween case)."""
    rows, bad = [], []
    for i, c in enumerate(cue_list):
        nxt = cue_list[i + 1] if i + 1 < len(cue_list) else None
        for t in points(c):
            fr = frame_at.get(round(t, 3), {})
            row = {"cue": c["cue"], "kind": c["kind"], "t": t, "expected_state": c["state"]["state_id"],
                   "explorer_state": explorer.get((c["cue"], t)), "frame_state": fr.get("state"),
                   "frame": {k: fr.get(k) for k in ("program", "line", "path", "output")}}
            rows.append(row)
            if row["explorer_state"] != row["expected_state"] or not (
                    _tween_ok(c, nxt, fr) or row["frame_state"] == row["explorer_state"]):
                bad.append(row)
    return rows, bad


# ---------------------------------------------------------------- the program diff keeps the frame steady (WP9 Part A)

MORPH_JS = r"""(t) => {
  const root = document.querySelector('[data-composition-id]');
  const tl = window.__timelines[root.dataset.compositionId];
  tl.seek(t, false);
  """ + EOP_JS + r"""
  const problems = [];
  const max = (els) => els.reduce((m, e) => Math.max(m, eop(e)), 0);
  // every code row on screen keeps a line number on screen (its own, or the one it is turning into)
  const rows = [...root.querySelectorAll('.code .ln')].filter((r) => eop(r) >= 0.99);
  for (const r of rows) {
    if (max([...r.querySelectorAll('.no')]) < 0.5) problems.push({ kind: 'gutter-number-gone', line: r.dataset.line || r.dataset.to });
  }
  // the file name is always readable
  const files = [...root.querySelectorAll('.file')];
  if (files.length && max(files) < 0.5) problems.push({ kind: 'file-name-gone' });
  // no gap opens in the code: visible rows (old, moved and added) cover the card without a hole
  const tops = [...root.querySelectorAll('.code .ln')].filter((r) => eop(r) >= 0.3)
    .map((r) => { const b = r.getBoundingClientRect(); return [b.top, b.bottom]; }).sort((a, b) => a[0] - b[0]);
  const lh = tops.length ? tops[0][1] - tops[0][0] : 0;
  for (let i = 1; i < tops.length; i++) {
    const gap = tops[i][0] - tops[i - 1][1];
    if (gap > 0.6 * lh) problems.push({ kind: 'code-gap', px: Math.round(gap) });
  }
  return { t, problems, out: [...root.querySelectorAll('.out[data-set="old"]')].map((o) => +eop(o).toFixed(3)),
           notes: max([...root.querySelectorAll('.notecard, .changecard, .qcard')]) };
}"""


def morph_gate(lesson, video_dir, timing, lesson_sha=None):
    """A program change keeps the frame steady (WP9 Part A): through the diff every visible code row keeps a line
    number, the file name stays readable, no gap opens in the code, the output values stay fully shown until the
    new output arrives, and the note column is never empty once the title is in. Sampled every 0.1 s from the
    scene start to `shown`."""
    scenes = [s for s in timing["scenes"] if s.get("morph")]
    if not scenes:
        return visual.g("video.morph-stable", "video", True, {"morph_scenes": 0, "note": "no program change in this lesson"})
    from ..project import video as vproj
    comp = video_dir / "composition"
    hdir = video_dir / "work" / "frames-morph"
    if hdir.exists():
        shutil.rmtree(hdir)
    pages = harness_pages(comp, hdir)
    jobs, plans = [], {}
    with visual.LocalServer(video_dir) as srv:
        for sc in scenes:
            plan = vproj.draw_plan(lesson, sc["before"], sc["state"], budget=vproj.DRAW_BUDGET * (sc["end"] - sc["reveal"]))
            reveal = sc["reveal"] - sc["start"]
            outputs_at = reveal + plan["outputs_at"] * plan["k"]
            end = sc["shown"] - sc["start"]
            ts = [round(x / 10, 2) for x in range(0, int(end * 10) + 1)]
            plans[sc["id"]] = {"outputs_at": round(outputs_at, 3), "times": ts}
            steps = [{"waitFor": "window.__timelines && Object.keys(window.__timelines).length > 0", "timeout": 20000}]
            steps += [{"eval": f"({MORPH_JS})({t})", "as": f"t:{t}"} for t in ts]
            jobs.append({"id": f"morph:{sc['id']}", "type": "script", "url": f"{srv.url}/work/frames-morph/{pages[sc['id']]}",
                         "width": 1920, "height": 1080, "steps": steps})
        res = visual.shoot(jobs, video_dir / "work" / "frames-morph-run", lesson_sha)
    bad, sampled = [], 0
    for r in res["results"]:
        sid = r["id"].split(":", 1)[1]
        if not r.get("ok"):
            bad.append({"scene": sid, "kind": "job-failed", "error": r.get("error", "")[:300]})
            continue
        p = plans[sid]
        for k, v in sorted((r.get("values") or {}).items(), key=lambda kv: float(kv[0][2:])):
            t = float(k[2:])
            sampled += 1
            probs = list(v["problems"])
            if t < p["outputs_at"] and v["out"] and min(v["out"]) < 0.99:
                probs.append({"kind": "output-faded", "opacity": min(v["out"])})
            if t >= 0.45 and v["notes"] < 0.5:
                probs.append({"kind": "note-column-empty", "opacity": v["notes"]})
            bad += [{"scene": sid, "t": t, **pr} for pr in probs]
    return visual.g("video.morph-stable", "video", not bad and sampled > 0,
                    {"morph_scenes": [s["id"] for s in scenes], "frames_sampled": sampled, "problems": bad[:30]},
                    "" if not bad else "the frame loses its gutter, file name, output or note during the program diff")
