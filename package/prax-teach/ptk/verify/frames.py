r"""What the video frame shows at time t, read from the composition itself (review P1-3, AC-5.6).

Each scene's sub-composition is loaded on its own in a 1920 x 1080 page with the same GSAP and
fonts, and its paused timeline is seeked to the frame time, exactly as the renderer seeks it.
The rendered state is then *derived from what is drawn*, not from timing data:

    program   the code card's data-program
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

PROBE_JS = r"""(t) => {
  const root = document.getElementById('root');
  const tl = window.__timelines[root.dataset.compositionId];
  tl.seek(t, false);
  const op = (e) => parseFloat(getComputedStyle(e).opacity);
  const hl = document.getElementById('hl');
  const hb = hl.getBoundingClientRect();
  let line = null, best = 1e9;
  for (const r of document.querySelectorAll('.ln[data-line]')) {
    const b = r.getBoundingClientRect(); const d = Math.abs((b.top + b.bottom) / 2 - (hb.top + hb.bottom) / 2);
    if (d < best) { best = d; line = +r.dataset.line; }
  }
  const dots = [...document.querySelectorAll('.dot')];
  const vals = [...document.querySelectorAll('.out .val')];
  const segs = [...document.querySelectorAll('.seg')].map((s) => parseFloat(getComputedStyle(s).strokeDashoffset) || 0);
  // any tween on the mechanism (code card or output card) still running at t
  const mech = (el) => el && el.closest && el.closest('.code, .outcard');
  const active = tl.getChildren(false, true, true).some((ch) => (ch.data === 'draw' || (ch.targets && ch.targets().some(mech)))
    && ch.startTime() <= t + 1e-6 && t < ch.endTime() - 1e-6);
  const moving = active || best > 1.5 || segs.some((d) => d > 0.002 && d < 0.998)
    || dots.some((d) => op(d) > 0.01 && op(d) < 0.99)
    || vals.some((v) => op(v.parentElement) > 0.01 && op(v.parentElement) < 0.99);
  return { t, program: root.dataset.program, line,
           path: dots.filter((d) => op(d) >= 0.99).map((d) => +d.dataset.line),
           output: vals.filter((v) => op(v.parentElement) >= 0.99).map((v) => v.dataset.fact),
           moving };
}"""

LAYOUT_JS = r"""() => {
  const W = 1920, H = 1080, problems = [];
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
  for (const el of document.querySelectorAll('#root *')) {
    const own = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
    if (!own) continue;
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
  const band = H - lowest;
  return { problems, min_px: minPx, empty_bottom_px: Math.round(band), empty_bottom_frac: +(band / H).toFixed(3),
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


def match_state(lesson, probe):
    if probe.get("moving"):
        return "moving"
    for st in lesson.data["trace"]:
        s = st["state"]
        if (s["program"] == probe["program"] and s["line"] == probe["line"]
                and sorted(s.get("path", [])) == sorted(probe["path"]) and s["output"] == probe["output"]):
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
            if pt.get("state") in (None, "moving", "unknown"):
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


def compare_pauses(cue_list, frame_at, explorer, points):
    """Rows for every pause point; a row is bad when the explorer is not on the cue's state, or the
    frame shows something else (only a transition or answer cue may meet a frame in mid-tween)."""
    rows, bad = [], []
    for c in cue_list:
        for t in points(c):
            fr = frame_at.get(round(t, 3), {})
            row = {"cue": c["cue"], "kind": c["kind"], "t": t, "expected_state": c["state"]["state_id"],
                   "explorer_state": explorer.get((c["cue"], t)), "frame_state": fr.get("state"),
                   "frame": {k: fr.get(k) for k in ("program", "line", "path", "output")}}
            rows.append(row)
            in_tween = c["kind"] in ("transition", "answer") and row["frame_state"] == "moving"
            if row["explorer_state"] != row["expected_state"] or not (in_tween or row["frame_state"] == row["explorer_state"]):
                bad.append(row)
    return rows, bad
