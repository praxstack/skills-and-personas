"""AC-10.3 (SPEC v1.4 WP10): video typography and layout at 1080p, and the IVE figure above the fold on a phone.

Measured in the rendered composition (each scene's page seeked like the renderer seeks it) at every scene's
midpoint and settled point, then cross-checked on the encoded MP4 so the DOM cannot hide an empty frame:
  output >= code     every visible output value (an element whose data-fact or data-m is a stdout fact, or that
                     sits in data-role="output") renders at least as large as the visible code lines
                     ([data-code], code, .src), in CSS px at 1920 x 1080 (= video px).
  teaching >= 28 px  teaching text: claim, misconception and question text, the scene title, data-role="teaching",
                     and any unmarked non-monospace prose of 4+ words that is not chrome or a label.
  mechanism >= 55%   in a mechanism scene, the union of the painted hulls of the visible data-role="mechanism"
                     elements covers >= 55% of the frame. A mechanism scene is one whose storyboard key_nodes name
                     "panel" or "mechanism", whose scene root says data-scene-kind="mechanism", or that shows a
                     mechanism. A lesson with no mechanism scene fails.
  no empty > 20%     the largest rectangle that no drawn content touches (20 px grid) is <= 20% of the frame.
                     Cross-check: the same scene's settled frame from the MP4 at quarter size, where a 20 px
                     block is empty when its gray levels span <= 10 values (flat cards count as empty).
  phone fold         the IVE at 390 x 844, light and dark: a visible data-role="mechanism" element lies fully in
                     the first screen (top >= 0, bottom <= 844) and is >= 75% of the viewport wide. The film
                     itself does not count as the figure.
"""
import json
import shutil

import _b0
from ptk import host

MIN_TEACH_PX = 28.0
MIN_MECH = 0.55
MAX_EMPTY = 0.20
FOLD = (390, 844)
MIN_FOLD_WIDTH = 0.75
MONO_HINT = ("mono", "courier", "menlo", "consolas")


def _visible(it, o=0.5):
    return it.get("o", 1) >= o


def _is_code(it):
    """A line of the code listing: inside data-key="code" or carrying data-src-line (an identifier drawn in a
    figure with data-code is a figure label, not a code line)."""
    return (it.get("key") == "code" or it.get("srcline")) and it.get("label") not in ("line-number", "output-step", "program-file")


def _is_output(it, stdout_ids):
    return not _is_code(it) and ((it.get("fact") in stdout_ids) or it.get("role") == "output") \
        and it.get("label") not in ("output-step",) and not it.get("chrome")


def _is_teaching(it):
    if it.get("claim") or it.get("misc") or it.get("question") or it.get("label") == "scene-title" \
            or it.get("role") == "teaching":
        return not _is_code(it)
    if it.get("chrome") or it.get("label") or _is_code(it) or it.get("fact"):
        return False
    ff = (it.get("ff") or "").lower()
    words = [w for w in (it.get("block") or "").split() if sum(ch.isalpha() for ch in w) >= 2]
    return len(words) >= 4 and not any(h in ff for h in MONO_HINT)


def measure_frame(m, stdout_ids, mech_scene):
    """Every AC-10.3 frame measure on one extraction (1920 x 1080). Returns (row, problems)."""
    if not m or m.get("error"):
        return {}, [{"kind": "frame-probe-failed", "error": (m or {}).get("error")}]
    texts = [it for it in m["items"] if it["k"] == "text" and _visible(it)]
    code = [it["px"] for it in texts if _is_code(it)]
    outs = [it for it in texts if _is_output(it, stdout_ids)]
    teach = [it for it in texts if _is_teaching(it)]
    small = [{"text": it["t"][:50], "px": it["px"]} for it in teach if it["px"] < MIN_TEACH_PX - 0.05]
    mech, _h = _b0.group_coverage(m, "mech")
    shows_mech = any(c.get("o", 1) >= 0.05 for c in m["mechanisms"])
    is_mech = mech_scene or m.get("scene_kind") == "mechanism" or shows_mech
    empty, rect = _b0.dom_empty_fraction(_b0.ink_boxes(m), m["W"], m["H"])
    row = {"code_px": max(code) if code else None, "output_px_min": min((o["px"] for o in outs), default=None),
           "teaching_px_min": min((t["px"] for t in teach), default=None), "teaching_items": len(teach),
           "mechanism_scene": is_mech, "mechanism_coverage": mech,
           "rc1_panel_coverage_info": _b0.panel_coverage(m), "dom_empty": empty, "dom_empty_rect": rect}
    probs = []
    if code and outs and row["output_px_min"] < row["code_px"] - 0.5:
        smaller = sorted(outs, key=lambda o: o["px"])[0]
        probs.append({"kind": "output-smaller-than-code", "output_px": smaller["px"], "output": smaller["t"][:30],
                      "code_px": row["code_px"]})
    if small:
        probs.append({"kind": "teaching-text-small", "items": small[:4], "count": len(small)})
    if is_mech and mech < MIN_MECH:
        probs.append({"kind": "mechanism-coverage", "coverage": mech})
    if empty > MAX_EMPTY:
        probs.append({"kind": "empty-region", "fraction": empty, "rect": rect})
    return row, probs


def pixel_empty(src, t=None):
    tmp = host.make_tmp("b0-frame-")
    try:
        raw = _b0.gray_raw(src, tmp / "f.gray", t)
        return _b0.flat_empty_fraction(raw)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def fold_check(url, name, lesson_sha=None):
    """The IVE (or a fixture page) at 390 x 844 in both schemes: is a mechanism fully in the first screen?"""
    jobs = [{"id": scheme, "type": "script", "url": url, "width": FOLD[0], "height": FOLD[1], "scheme": scheme,
             "steps": [{"waitFor": "!window.__ptkReady || window.__ptkReady()", "timeout": 30000},
                       {"wait": 300}, _b0.extract_step({"W": FOLD[0], "H": FOLD[1]})]}
            for scheme in ("light", "dark")]
    res = _b0.shoot(jobs, name, lesson_sha)
    out, probs = {}, []
    for r in res["results"]:
        m = (r.get("values") or {}).get("m")
        if not r.get("ok") or not m:
            probs.append({"kind": "fold-probe-failed", "scheme": r["id"], "error": (r.get("error") or "")[:300]})
            continue
        mechs = [c["b"] for c in m["mechanisms"] if c.get("o", 1) >= 0.05 and c["b"][2] > 0 and c["b"][3] > 0]
        ok = [b for b in mechs if b[1] >= -0.5 and b[1] + b[3] <= FOLD[1] + 0.5 and b[2] >= MIN_FOLD_WIDTH * FOLD[0]]
        panels = [p["b"] for p in m.get("panels", []) if p.get("o", 1) >= 0.05]
        out[r["id"]] = {"mechanisms": mechs, "rc1_panel_boxes_info": panels}
        if not ok:
            probs.append({"kind": "figure-below-fold", "scheme": r["id"], "mechanisms": mechs,
                          "rc1_panel_top_info": [round(p[1]) for p in panels]})
    return out, probs


def evaluate_video(video_dir, timing, mech_scenes, stdout_ids, mp4=None, name="video", lesson_sha=None, frames=None):
    """All frame measures for one composition. mech_scenes: scene ids the storyboard marks as mechanism scenes.
    frames: optional {scene id: PNG} used for the pixel cross-check instead of the MP4 (fixtures)."""
    samples = []
    for s in timing["scenes"]:
        for point, local in _b0.check_points(s).items():
            samples.append((f"{s['id']}@{point}", s["start"] + local))
    got = _b0.probe_video(video_dir, timing, samples, name, lesson_sha)
    rows, probs = {}, []
    for label, _t in samples:
        sid = label.split("@")[0]
        row, p = measure_frame(got.get(label), stdout_ids, sid in mech_scenes)
        rows[label] = row
        probs += [{**x, "at": label} for x in p]
    if not any(r.get("mechanism_scene") for r in rows.values()):
        probs.append({"kind": "no-mechanism-scene"})
    pix = {}
    for s in timing["scenes"]:
        t = _b0.frame_time(s["start"] + _b0.check_points(s)["settled"], timing.get("fps", 30))
        src = (frames or {}).get(s["id"]) or mp4
        if not src:
            continue
        frac, rect = pixel_empty(src, None if frames else t)
        pix[s["id"]] = {"t": round(t, 3), "pixel_empty": frac, "rect": rect}
        if frac > MAX_EMPTY:
            probs.append({"kind": "empty-region-pixels", "at": f"{s['id']}@settled", "fraction": frac, "rect": rect})
    return rows, pix, probs


# ---------------------------------------------------------------- fixtures

def _fixture(name):
    d = _b0.FIXTURES / name
    timing = json.loads((d / "timing.json").read_text())
    shots = host.make_tmp("b0-vshot-")
    tmp, pages = _b0._harness(d)
    try:
        with _b0.visual.LocalServer(tmp) as srv:
            jobs = [{"id": sid, "type": "script", "url": f"{srv.url}/{page}", "width": 1920, "height": 1080,
                     "steps": [{"waitFor": "window.__timelines && Object.keys(window.__timelines).length > 0"},
                               {"eval": f"{_b0.SEEK_JS}(0.5)", "as": "s"}, {"shot": str(shots / f"{sid}.png")}]}
                    for sid, page in pages.items()]
            _b0.shoot(jobs, "vshot")
        frames = {sid: shots / f"{sid}.png" for sid in pages}
        rows, pix, probs = evaluate_video(d, timing, set(timing.get("mechanism_scenes", [])), {"f.out"},
                                          name=f"fx-{name}", frames=frames)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(shots, ignore_errors=True)
    return rows, pix, probs


def test_fixture_good_frame_passes():
    """A frame with a dominant mechanism, large output, 32 px teaching text and no empty region passes, in the DOM
    and on its screenshot."""
    rows, pix, probs = _fixture("video-pass")
    assert not probs, probs
    return {"rows": rows, "pixels": pix}


def test_fixture_bad_frame_fails():
    """A frame with a small mechanism, 18 px teaching text, output smaller than code and an empty right half fails
    each measure, and the screenshot cross-check sees the empty half too."""
    rows, pix, probs = _fixture("video-fail")
    kinds = {p["kind"] for p in probs}
    want = {"output-smaller-than-code", "teaching-text-small", "mechanism-coverage", "empty-region", "empty-region-pixels"}
    assert want <= kinds, (sorted(kinds), probs)
    return {"kinds": sorted(kinds), "rows": rows, "pixels": pix}


def test_fixture_phone_fold():
    """At 390 x 844 a figure at the top passes; a figure under a tall film fails."""
    _o, good = fold_check((_b0.FIXTURES / "ive-fold-pass.html").resolve().as_uri(), "fold-pass")
    _o, bad = fold_check((_b0.FIXTURES / "ive-fold-fail.html").resolve().as_uri(), "fold-fail")
    assert not good, good
    assert {p["kind"] for p in bad} == {"figure-below-fold"} and len(bad) == 2, bad
    return {"fail": [p["mechanisms"] for p in bad]}


# ---------------------------------------------------------------- the built lessons

def _lesson(slug):
    b = _b0.need(slug, "video/timing.json", "video/composition", "video/lesson.mp4", "ive/index.html")
    lesson = _b0.load(slug)
    timing = json.loads((b / "video" / "timing.json").read_text())
    mech_scenes = {sc["id"] for sc in lesson.data.get("storyboard", [])
                   if {"panel", "mechanism"} & set(sc.get("key_nodes", []))}
    stdout_ids = _b0.stdout_fact_ids(lesson.data)
    rows, pix, probs = evaluate_video(b / "video", timing, mech_scenes, stdout_ids, mp4=b / "video" / "lesson.mp4",
                                      name=f"video-{slug}", lesson_sha=lesson.sha256())
    fold, fprobs = fold_check((b / "ive" / "index.html").resolve().as_uri(), f"fold-{slug}", lesson.sha256())
    probs += fprobs
    vals = [r for r in rows.values() if r]
    summary = {
        "frames": len(rows),
        "min_teaching_px": min((r["teaching_px_min"] for r in vals if r["teaching_px_min"] is not None), default=None),
        "frames_output_smaller_than_code": sum(1 for p in probs if p["kind"] == "output-smaller-than-code"),
        "mechanism_frames": sum(1 for r in vals if r["mechanism_scene"]),
        "max_mechanism_coverage": max((r["mechanism_coverage"] for r in vals), default=0),
        "max_panel_coverage_info": max((r["rc1_panel_coverage_info"] for r in vals), default=0),
        "max_dom_empty": max((r["dom_empty"] for r in vals), default=None),
        "max_pixel_empty": max((p["pixel_empty"] for p in pix.values()), default=None),
        "fold_ok": not fprobs,
    }
    rec = _b0.record(f"ac10.3-{slug}", {"lesson": slug, "summary": summary, "frames": rows, "pixels": pix,
                                        "fold": fold, "problems": probs})
    counts = {}
    for p in probs:
        counts[p["kind"]] = counts.get(p["kind"], 0) + 1
    assert not probs, json.dumps({"summary": summary, "problems": counts, "record": rec})
    return {"summary": summary, "record": rec}


_b0.lesson_tests(globals(), "AC-10.3 video layout", _lesson)
