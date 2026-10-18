"""WP6: the interactive video explorer (AC-6.1..6.7), checked in Chrome on the built page opened from
disk. tests/test_ive.mjs drives the browser once per run; each test here asserts one AC from its
results. Build first: `ptk build lessons/switch-fallthrough --only video,ive`."""
import json
import shutil

from _util import SLICE
from selftest_support import NotRun
from ptk import errors, host, model, node, text
from ptk.project import explorer, ive
from ptk.verify import media, visual

IVE = SLICE / "build" / "ive"
_RUN = {}


def _built():
    if not (IVE / "index.html").exists() or not (IVE / "ive-data.js").exists():
        raise NotRun(f"no built IVE at {IVE}; run `ptk build lessons/switch-fallthrough --only video,ive`")
    return json.loads((SLICE / "build" / "video" / "timing.json").read_text()), json.loads((IVE / "cues.json").read_text())


def _spec(lesson, timing, cue_list):
    answers = []
    for c in (c for c in cue_list if c["kind"] == "answer"):
        sc = next(s for s in timing["scenes"] if s["id"] == c["answer_for"])
        words = [w.strip().lower() for w in lesson.fact(sc["question"]["answer_fact"])["value"].split("\n") if w.strip()]
        answers.append({"cue": c["cue"], "start": c["start"], "words": words})
    film = next(c for c in cue_list if c["kind"] == "state" and len(c["state"]["output"]) >= 2)
    live = ive.live_model(lesson)
    counts = {"captions": len(timing["cues"]), "chapters": len(timing["scenes"]), "metadata": len(cue_list)}
    return {"url": (IVE / "index.html").resolve().as_uri(), "drive": str(visual.IVE_DRIVE),
            "boundaries": visual.boundary_seeks(cue_list, timing["fps"]), "answers": answers, "counts": counts,
            "counts_by_kind": counts, "first_caption": timing["cues"][0]["start"], "repeats": 5,
            "film_t": round(film["start"] + 0.5, 3), "film_n": film["state"]["vars"][live["var"]],
            "film_brk": "true" if film["state"]["program"] == live["alt"] else "false",
            "domain": live["domain"], "yours_text": text.ui("ive_yours")}


def _run():
    if "out" in _RUN:
        return _RUN["out"]
    timing, cue_list = _built()
    lesson = model.load(SLICE)
    try:
        node_bin = node.node_bin()
    except errors.HostToolMissing as e:
        raise NotRun(str(e)) from e
    if not (node.tools_dir() / "node_modules" / "playwright").exists():
        raise NotRun("Playwright is not installed under $PTK_STATE/tools/node; run `ptk host setup --yes`")
    tmp = host.make_tmp("ive-test-")
    try:
        sp, op = tmp / "spec.json", tmp / "out.json"
        spec = _spec(lesson, timing, cue_list)
        sp.write_text(json.dumps(spec))
        host.run([node_bin, str(host.PKG / "tests" / "test_ive.mjs"), sp, op], env=node.env(lesson.sha256()),
                 timeout=900, check=True)
        _RUN["out"] = {**json.loads(op.read_text()), "spec": spec, "lesson": lesson, "timing": timing, "cues": cue_list}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return _RUN["out"]


def _check(name):
    out = _run()
    c = out["checks"][name]
    assert c.get("ok"), f"{name} failed in {out['browser']}: {json.dumps(c.get('detail'))[:2500]}"
    return out, c


def test_cue_track():
    """AC-6.1: states.vtt is a metadata track of {scene_id, state_id} cues; every question has an answer
    cue; the page's track is byte-for-byte the shipped file."""
    out, c = _check("cue_track")
    data = (IVE / "ive-data.js").read_text()
    payload = json.loads(data[data.index("=") + 1:].strip().rstrip(";"))
    for k in ("captions", "chapters", "states"):
        assert payload["tracks"][k] == (IVE / f"{k}.vtt").read_text(), f"ive-data.js {k} differs from {k}.vtt"
    for cue in media.parse_vtt(IVE / "states.vtt"):
        p = json.loads(cue["text"])
        assert p["scene"] and p["state"]["state_id"], cue
    return {"browser": out["browser"], **c["detail"]}


def test_pause_state():
    """AC-6.2 / D20.6: seeks at boundary - 1 ms, boundary, + 1 ms, the browser's microsecond-truncated time,
    the frame grid and both edges of the one-frame tolerance all show the expected window, and so does
    every chapter jump."""
    out, c = _check("pause_state")
    d = c["detail"]
    assert d["strict_rule_would_fail"] > 0, "no seek exercised the one-frame tolerance"
    return {"browser": out["browser"], "seeks": d["seeks"], "strict_rule_would_fail": d["strict_rule_would_fail"],
            "sample": [{k: r[k] for k in ("at", "t", "actual_t", "expected", "shown")} for r in d["sample"]]}


def test_no_leak_before_answer():
    """AC-6.3: paused 0.1 s before each answer cue, no answer word in the DOM, alt text or transcript so far
    (the noscript transcript is exempt; test_controls_and_noscript checks its 'contains the answers'
    heading comes first), and the live controls are locked."""
    out, c = _check("no_leak_before_answer")
    return {"browser": out["browser"], "checked": [{k: r[k] for k in ("cue", "hits", "locked", "t")} for r in c["detail"]]}


def test_controls_and_noscript():
    """AC-6.4 and the WP5 flake: captions on/off, chapters, the synced transcript with click-to-seek, and
    the no-JS posters (decoded before asserting) and transcript, five runs in a row."""
    out, c = _check("controls_and_noscript")
    return {"browser": out["browser"], "runs": len(c["detail"]), "all_ok": all(r["ok"] for r in c["detail"])}


def test_film_explore_return():
    """AC-6.6: pause enters EXPLORE at the film's state; edits are marked as the learner's; RETURN resumes at
    the paused time with the film's state, and the next pause starts clean."""
    out, c = _check("film_explore_return")
    return {"browser": out["browser"], "checks": c["detail"]["checks"]}


def test_live_views_match_expect():
    """Every live edit the EXPLORE panel can show equals explorer.expected_view (expect.py, no shared code)."""
    out, c = _check("film_explore_return")
    m = explorer.switch_model(out["lesson"])
    bad = []
    for row in c["live"]:
        exp = explorer.expected_view(m, row["brk"], row["n"])
        if (row["program"], row["path"], row["output"], row["exit"], row["ran"]) != \
                (exp["program"], exp["path"], exp["output"], exp["exit"], exp["ran"]):
            bad.append({"n": row["n"], "brk": row["brk"], "page": row, "expected": {k: exp[k] for k in ("path", "output")}})
    assert len(c["live"]) == 2 * len(m["domain"]) and not bad, bad[:3]
    return {"views": len(c["live"])}


def test_navigation_events_only():
    """AC-6.5 (page side): every event the page records or posts to a host bridge is a schema-2
    navigation record, never an attempt."""
    out, c = _check("film_explore_return")
    schema = json.loads((host.PKG / "schemas" / "state-navigation.schema.json").read_text())
    actions = set(schema["properties"]["action"]["enum"])
    ev = c["events"]
    posted = [e for e in ev["posted"] if isinstance(e, dict) and e.get("artifact_id", "").endswith(":ive")]
    assert ev["nav"] and len(posted) == len(ev["nav"]), (len(ev["nav"]), len(posted))
    bad = [e for e in ev["nav"] + posted if e.get("event_type") != "navigation" or e.get("action") not in actions
           or set(e) != set(schema["required"]) or "attempt" in json.dumps(e)]
    assert not bad, bad[:3]
    return {"events": len(ev["nav"]), "actions": sorted({e["action"] for e in ev["nav"]})}


def test_file_protocol():
    """AC-6.7: opened from file:// in Chrome, the MP4 decodes and every WebVTT track loads."""
    out, c = _check("file_protocol")
    return {"browser": out["browser"], **{k: c["detail"][k] for k in ("tracks", "readyState", "track_src")}}


def test_before_answer_shot_has_no_loading_spinner():
    """Integration pass: Chrome's media-controls loading spinner fades out for about a second after a seek, and the
    before-answer screenshot caught it. The shot is taken once the page has settled: a second shot 2.5 s later
    is pixel-identical (no transient Chrome UI left in the frame)."""
    timing, cue_list = _built()
    ans = next(c for c in cue_list if c["kind"] == "answer")
    work = host.make_tmp("ive-spinner-")
    try:
        a, b = work / "a.png", work / "b.png"
        steps = [{"waitFor": "window.__ptkReady && window.__ptkReady()", "timeout": 30000},
                 {"eval": visual.IVE_DRIVE.read_text(), "as": "drive"},
                 visual._js(f"await D.seek({ans['start'] - 0.1:.3f}); document.getElementById('explore').click(); "
                            "await D.sleep(80); await (D.settled ? D.settled() : D.frame()); return 1;"),
                 {"shot": str(a)}, {"wait": 2500}, {"shot": str(b)}]
        visual.shoot([{"id": "spinner", "type": "script", "url": (IVE / "index.html").resolve().as_uri(),
                       "width": 1440, "height": 1000, "steps": steps}], work / "w")
        # Chrome's PNG encoder is deterministic: identical pixels give identical bytes
        assert a.read_bytes() == b.read_bytes(), "the before-answer frame was still changing (Chrome's loading spinner)"
        return {"cue": ans["cue"], "settled": True}
    finally:
        shutil.rmtree(work, ignore_errors=True)
