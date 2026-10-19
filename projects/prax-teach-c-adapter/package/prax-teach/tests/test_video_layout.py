"""AC-10.3 (SPEC v1.4 WP10): video typography and layout at 1080p, and the IVE figure above the fold on a phone.

Measured in the rendered composition (each scene's page seeked like the renderer seeks it) at 25%, 50% and 75% of
every scene and at its settled point, then on the encoded MP4 at 2 frames a second:
  output >= code     every visible output value renders at least as large as the visible code lines, in CSS px at
                     1920 x 1080 (= video px), transforms and zoom included. An output value is an element whose
                     data-fact or data-m is a stdout fact, one inside data-role="output", or any monospace text equal
                     to a captured stdout line or value. A code line is text inside data-key="code" or carrying
                     data-src-line, or any monospace line that is a source line of the lesson or looks like C.
  teaching >= 28 px  claim, misconception and question text, the scene title, data-role="teaching", and any
                     non-monospace prose of 4+ words that is not code or output. Chrome and label marks do not exempt
                     prose.
  mechanism >= 55%   in a mechanism scene, what the visible data-role="mechanism" elements paint covers >= 55% of
                     the frame: shots with and without them, 20 px cells changed by more than 12 levels, one-cell
                     dilation, marks under 0.3 opacity ignored. A mechanism scene is one whose storyboard key_nodes
                     name "panel" or "mechanism", whose root says data-scene-kind="mechanism", or that shows a
                     mechanism. A lesson with no mechanism scene fails.
  no empty > 20%     DOM: the largest rectangle on a 20 px grid that no drawn content touches is <= 20% of the frame
                     (fill-only shapes over 10% of the frame are backgrounds, not content). MP4: every frame at 2 fps,
                     except within 0.5 s of a scene cut, at quarter size, median filtered; a 20 px block is empty when
                     its gray levels span <= 10; the largest empty rectangle must be <= 20%.
  phone fold         the IVE at 390 x 844, light and dark, at load and again after one interaction (Pause and
                     explore, or the first enabled button): a visible data-role="mechanism" lies fully in the first
                     screen, is >= 75% of the viewport wide, and visibly paints >= 30% of its own box.
"""
import json
import re
import shutil

import _b0
from ptk import host

MIN_TEACH_PX = 28.0
MIN_MECH = 0.55
MAX_EMPTY = 0.20
FOLD = (390, 844)
MIN_FOLD_WIDTH = 0.75
MIN_FOLD_PAINT = 0.30
POINTS = (0.25, 0.5, 0.75)
CUT_GUARD = 0.5
MONO_HINT = ("mono", "courier", "menlo", "consolas")
C_LINE = re.compile(r"[;{}]\s*$|^\s*(#include|case\b.*:|default\s*:|switch\s*\(|if\s*\(|for\s*\(|while\s*\(|return\b|"
                    r"(unsigned\s+)?(int|double|char|long|float|void)\s+[\w*]|printf\s*\(|puts\s*\()")


def _visible(it, o=0.5):
    return it.get("o", 1) >= o


def _mono(it):
    return any(h in (it.get("ff") or "").lower() for h in MONO_HINT)


def _is_code(it, ctx):
    """A line of code: marked (data-key="code", data-src-line), or a monospace line that is a source line of the
    lesson or reads as C. An identifier drawn in a figure is a label, not a code line."""
    if it.get("label") in ("line-number", "output-step", "program-file"):
        return False
    if it.get("key") == "code" or it.get("srcline"):
        return True
    t = it["t"].strip()
    return _mono(it) and not it.get("fact") and (t in ctx["source_lines"] or bool(C_LINE.search(t)))


def _is_output(it, ctx):
    if _is_code(it, ctx) or it.get("label") in ("output-step", "axis-tick") or it.get("tick"):
        return False
    if it.get("fact") in ctx["stdout_ids"] or it.get("role") == "output":
        return True
    return _mono(it) and _b0.norm_text(it["t"]) in ctx["outputs"]


def _is_teaching(it, ctx):
    if _is_code(it, ctx) or _is_output(it, ctx):
        return False
    if it.get("claim") or it.get("misc") or it.get("question") or it.get("label") == "scene-title" \
            or it.get("role") == "teaching":
        return True
    words = [w for w in (it.get("block") or "").split() if sum(ch.isalpha() for ch in w) >= 2]
    return len(words) >= 4 and not _mono(it)


def measure_frame(m, ctx, mech_scene):
    """Every AC-10.3 frame measure on one extraction (1920 x 1080). Returns (row, problems)."""
    if not m or m.get("error"):
        return {}, [{"kind": "frame-probe-failed", "error": (m or {}).get("error")}]
    texts = [it for it in m["items"] if it["k"] == "text" and _visible(it)]
    code = [it["px"] for it in texts if _is_code(it, ctx)]
    outs = [it for it in texts if _is_output(it, ctx)]
    teach = [it for it in texts if _is_teaching(it, ctx)]
    small = [{"text": it["t"][:50], "px": it["px"]} for it in teach if it["px"] < MIN_TEACH_PX - 0.05]
    paint = (m.get("diff") or {}).get(_b0.MECH_SEL) or {"coverage": 0.0}
    shows_mech = any(c.get("o", 1) >= _b0.MIN_OPACITY for c in m["mechanisms"])
    is_mech = mech_scene or m.get("scene_kind") == "mechanism" or shows_mech
    empty, rect = _b0.dom_empty_fraction(_b0.ink_boxes(m), m["W"], m["H"])
    row = {"code_px": max(code) if code else None, "output_px_min": min((o["px"] for o in outs), default=None),
           "teaching_px_min": min((t["px"] for t in teach), default=None), "teaching_items": len(teach),
           "mechanism_scene": is_mech, "mechanism_coverage": paint["coverage"],
           "rc1_panel_coverage_info": _b0.panel_coverage(m), "dom_empty": empty, "dom_empty_rect": rect}
    probs = []
    if code and outs and row["output_px_min"] < row["code_px"] - 0.5:
        smaller = sorted(outs, key=lambda o: o["px"])[0]
        probs.append({"kind": "output-smaller-than-code", "output_px": smaller["px"], "output": smaller["t"][:30],
                      "code_px": row["code_px"]})
    if small:
        probs.append({"kind": "teaching-text-small", "items": small[:4], "count": len(small)})
    if is_mech and paint["coverage"] < MIN_MECH:
        probs.append({"kind": "mechanism-coverage", "coverage": paint["coverage"]})
    if empty > MAX_EMPTY:
        probs.append({"kind": "empty-region", "fraction": empty, "rect": rect})
    return row, probs


def _near_cut(t, timing):
    return any(abs(t - s["start"]) < CUT_GUARD or abs(t - s["end"]) < CUT_GUARD for s in timing["scenes"])


def pixel_rows(mp4, timing):
    """{time: (empty fraction, rect)} for every MP4 frame at 2 fps away from scene cuts."""
    tmp = host.make_tmp("b0-mp4-")
    try:
        frames = _b0.mp4_gray_frames(mp4, out=tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return {round(t, 2): _b0.flat_empty_fraction(raw) for t, raw in frames if not _near_cut(t, timing)}


def fold_measure(m, label):
    probs = []
    mechs = [c["b"] for c in m["mechanisms"] if c.get("o", 1) >= _b0.MIN_OPACITY and c["b"][2] > 0 and c["b"][3] > 0]
    ok = [b for b in mechs if b[1] >= -0.5 and b[1] + b[3] <= FOLD[1] + 0.5 and b[2] >= MIN_FOLD_WIDTH * FOLD[0]]
    paint = (m.get("diff") or {}).get(_b0.MECH_SEL)
    panels = [p["b"] for p in m.get("panels", []) if p.get("o", 1) >= 0.05]
    if not ok:
        probs.append({"kind": "figure-below-fold", "at": label, "mechanisms": mechs,
                      "rc1_panel_top_info": [round(p[1]) for p in panels]})
    elif not paint or paint["coverage"] < MIN_FOLD_PAINT:
        probs.append({"kind": "fold-figure-empty", "at": label, "painted": (paint or {}).get("coverage")})
    return {"mechanisms": mechs, "painted": (paint or {}).get("coverage"), "rc1_panel_boxes_info": panels}, probs


CLICK_JS = r"""(() => { const vis = (e) => e && e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden';
  const ex = document.getElementById('explore');
  const b = vis(ex) && !ex.disabled ? ex : [...document.querySelectorAll('button')].find((x) => vis(x) && !x.disabled);
  if (!b) return null; b.click(); return b.id || b.textContent.trim().slice(0, 30); })()"""


def fold_check(url, name, lesson_sha=None):
    """The IVE (or a fixture page) at 390 x 844, both schemes, at load and after one interaction."""
    shots = host.make_tmp(f"b0-{name}-fold-")
    jobs, files = [], {}
    for scheme in ("light", "dark"):
        steps = [{"waitFor": "!window.__ptkReady || window.__ptkReady()", "timeout": 30000}, {"wait": 300},
                 _b0.extract_step({"W": FOLD[0], "H": FOLD[1]}, "load")]
        files[(scheme, "load")] = (shots / f"{scheme}-0a.png", shots / f"{scheme}-0b.png")
        steps += _b0.diff_steps(_b0.MECH_SEL, *files[(scheme, "load")])
        steps += [{"eval": CLICK_JS, "as": "clicked"}, {"wait": 500},
                  _b0.extract_step({"W": FOLD[0], "H": FOLD[1]}, "after")]
        files[(scheme, "after")] = (shots / f"{scheme}-1a.png", shots / f"{scheme}-1b.png")
        steps += _b0.diff_steps(_b0.MECH_SEL, *files[(scheme, "after")])
        jobs.append({"id": scheme, "type": "script", "url": url, "width": FOLD[0], "height": FOLD[1],
                     "scheme": scheme, "steps": steps})
    out, probs = {}, []
    try:
        res = _b0.shoot(jobs, name, lesson_sha)
        for r in res["results"]:
            vals = r.get("values") or {}
            if not r.get("ok"):
                probs.append({"kind": "fold-probe-failed", "scheme": r["id"], "error": (r.get("error") or "")[:300]})
                continue
            out[r["id"]] = {"clicked": vals.get("clicked")}
            for when in ("load", "after"):
                m = vals.get(when)
                if not m:
                    probs.append({"kind": "fold-probe-failed", "scheme": r["id"], "at": when})
                    continue
                # the shots are viewport-sized: only the first screen counts
                a, b = files[(r["id"], when)]
                m["diff"] = {_b0.MECH_SEL: _diff_in_mech(a, b, m)}
                row, p = fold_measure(m, f"{r['id']}:{when}")
                out[r["id"]][when] = row
                probs += p
    finally:
        shutil.rmtree(shots, ignore_errors=True)
    return out, probs


def _diff_in_mech(a, b, m):
    """Painted share of the visible mechanism's own box, clipped to the first screen."""
    boxes = [c["b"] for c in m["mechanisms"] if c.get("o", 1) >= _b0.MIN_OPACITY and c["b"][2] > 0]
    if not boxes:
        return {"coverage": 0.0}
    x0, y0 = min(bx[0] for bx in boxes), min(bx[1] for bx in boxes)
    x1, y1 = max(bx[0] + bx[2] for bx in boxes), max(bx[1] + bx[3] for bx in boxes)
    return _b0.diff_coverage(a, b, region=(max(0, x0), max(0, y0), min(FOLD[0], x1), min(FOLD[1], y1)))


def evaluate_video(video_dir, timing, mech_scenes, ctx, mp4=None, name="video", lesson_sha=None, frames=None):
    """All frame measures for one composition. mech_scenes: scene ids the storyboard marks as mechanism scenes.
    frames: optional {scene id: PNG} used for the pixel check instead of the MP4 (fixtures)."""
    samples = []
    for s in timing["scenes"]:
        pts = {f"p{int(f * 100)}": round(s["duration"] * f, 3) for f in POINTS}
        pts["settled"] = _b0.check_points(s)["settled"]
        samples += [(f"{s['id']}@{k}", s["start"] + v) for k, v in pts.items()]
    got = _b0.probe_video(video_dir, timing, samples, name, lesson_sha, diff_sel=_b0.MECH_SEL)
    rows, probs = {}, []
    for label, _t in samples:
        row, p = measure_frame(got.get(label), ctx, label.split("@")[0] in mech_scenes)
        rows[label] = row
        probs += [{**x, "at": label} for x in p]
    if not any(r.get("mechanism_scene") for r in rows.values()):
        probs.append({"kind": "no-mechanism-scene"})
    if frames:
        tmp = host.make_tmp("b0-fxframe-")
        try:
            pix = {sid: _b0.flat_empty_fraction(_b0.median_gray(png, tmp / f"{sid}.gray")) for sid, png in frames.items()}
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    else:
        pix = pixel_rows(mp4, timing) if mp4 else {}
    for t, (frac, rect) in pix.items():
        if frac > MAX_EMPTY:
            probs.append({"kind": "empty-region-pixels", "at": t, "fraction": frac, "rect": rect})
    return rows, {str(k): v[0] for k, v in pix.items()}, probs


def lesson_ctx(lesson, capture_dir):
    vals, _ = _b0.captured_facts(lesson.data, capture_dir)
    stdout_ids = _b0.stdout_fact_ids(lesson.data)
    outputs = {_b0.norm_text(line) for fid in stdout_ids if vals.get(fid) for line in vals[fid].split("\n") if line.strip()}
    srcs = [lesson.program_source(p["id"]) for p in lesson.data["programs"]]
    return {"stdout_ids": stdout_ids, "outputs": outputs,
            "source_lines": {ln.strip() for s in srcs for ln in s.split("\n") if len(ln.strip()) >= 6}}


# ---------------------------------------------------------------- fixtures

FIX_CTX = {"stdout_ids": {"f.out"}, "outputs": {"a = 0.6"},
           "source_lines": {"double z = t1 + t2;", "double a = fmax(0, z);"}}


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
        rows, pix, probs = evaluate_video(d, timing, set(timing.get("mechanism_scenes", [])), FIX_CTX,
                                          name=f"fx-{name}", frames=frames)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(shots, ignore_errors=True)
    return rows, pix, probs


def test_fixture_good_frame_passes():
    """A frame whose mechanism paints most of it, with large output, 32 px teaching text and no empty region,
    passes in the DOM and on its screenshot."""
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


def test_fixture_unmarked_frame_fails():
    """With no markup at all: monospace output smaller than monospace code, chrome-marked prose at 16 px, a
    full-frame ground-coloured rectangle as the "mechanism", and a 90% fill-only card. Each is still caught."""
    rows, pix, probs = _fixture("video-unmarked")
    kinds = {p["kind"] for p in probs}
    want = {"output-smaller-than-code", "teaching-text-small", "mechanism-coverage", "empty-region"}
    assert want <= kinds, (sorted(kinds), probs)
    return {"kinds": sorted(kinds), "rows": rows}


def test_fixture_text_size_under_transforms():
    """The review's page: text at 40 px under a 0.5 scale, a halving viewBox and zoom 0.5 reads as 20 px, and
    rotated text keeps its 40 px."""
    url = (_b0.FIXTURES / "adversarial" / "text-transforms.html").resolve().as_uri()
    res = _b0.shoot([{"id": "x", "type": "script", "url": url, "width": 1920, "height": 1080,
                      "steps": [_b0.extract_step({"W": 1920, "H": 1080})]}], "xf")
    got = {it["t"]: it["px"] for it in res["results"][0]["values"]["m"]["items"] if it["k"] == "text"}
    want = {"scaled html text forty px": 20, "svg in scaled div": 20, "svg viewbox halves": 20,
            "zoomed half html text": 20, "rotated html text forty px here": 40}
    assert all(abs(got.get(k, 0) - v) < 0.6 for k, v in want.items()), got
    return got


def test_fixture_phone_fold():
    """At 390 x 844 a drawn figure at the top passes; a figure under a tall film fails; a figure that a click pushes
    below the fold fails on the re-measure."""
    _o, good = fold_check((_b0.FIXTURES / "ive-fold-pass.html").resolve().as_uri(), "fold-pass")
    _o, bad = fold_check((_b0.FIXTURES / "ive-fold-fail.html").resolve().as_uri(), "fold-fail")
    _o, moved = fold_check((_b0.FIXTURES / "ive-fold-click-fail.html").resolve().as_uri(), "fold-click")
    assert not good, good
    assert {p["kind"] for p in bad} == {"figure-below-fold"} and len(bad) == 4, bad
    assert [p["at"] for p in moved] == ["light:after", "dark:after"], moved
    return {"fail": len(bad), "click": [p["at"] for p in moved]}


# ---------------------------------------------------------------- the built lessons

def _lesson(slug):
    b = _b0.need(slug, "video/timing.json", "video/composition", "video/lesson.mp4", "ive/index.html", "capture")
    lesson = _b0.load(slug)
    timing = json.loads((b / "video" / "timing.json").read_text())
    mech_scenes = {sc["id"] for sc in lesson.data.get("storyboard", [])
                   if {"panel", "mechanism"} & set(sc.get("key_nodes", []))}
    rows, pix, probs = evaluate_video(b / "video", timing, mech_scenes, lesson_ctx(lesson, b / "capture"),
                                      mp4=b / "video" / "lesson.mp4", name=f"video-{slug}", lesson_sha=lesson.sha256())
    fold, fprobs = fold_check((b / "ive" / "index.html").resolve().as_uri(), f"fold-{slug}", lesson.sha256())
    probs += fprobs
    vals = [r for r in rows.values() if r]
    summary = {
        "frames": len(rows), "mp4_frames": len(pix),
        "min_teaching_px": min((r["teaching_px_min"] for r in vals if r["teaching_px_min"] is not None), default=None),
        "frames_output_smaller_than_code": sum(1 for p in probs if p["kind"] == "output-smaller-than-code"),
        "mechanism_frames": sum(1 for r in vals if r["mechanism_scene"]),
        "max_mechanism_coverage": max((r["mechanism_coverage"] for r in vals), default=0),
        "max_panel_coverage_info": max((r["rc1_panel_coverage_info"] for r in vals), default=0),
        "max_dom_empty": max((r["dom_empty"] for r in vals), default=None),
        "max_pixel_empty": max(pix.values(), default=None),
        "mp4_frames_over": sum(1 for v in pix.values() if v > MAX_EMPTY),
        "fold_ok": not fprobs,
    }
    rec = _b0.record(f"ac10.3-{slug}", {"lesson": slug, "summary": summary, "frames": rows, "pixels": pix,
                                        "fold": fold, "problems": probs})
    counts = {}
    for p in probs:
        counts[p["kind"]] = counts.get(p["kind"], 0) + 1
    assert not probs, json.dumps({"problems": counts, "summary": summary, "record": rec})
    return {"summary": summary, "record": rec}


_b0.lesson_tests(globals(), "AC-10.3 video layout", _lesson)
