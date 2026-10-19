"""WP6: the interactive video explorer (AC-6.1..6.7), checked in Chrome on the built page opened from
disk. tests/test_ive.mjs drives the browser once per run; each test here asserts one AC from its
results. Build first: `ptk build lessons/switch-fallthrough --only video,ive`."""
import json
import shutil

from _util import SLICE
from selftest_support import NotRun
from ptk import errors, host, model, node, text
from ptk.project import explorer, ive
from ptk.verify import ive_predict, media, visual

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
            "domain": live["domain"], "yours_text": text.ui("ive_yours"),
            "questions": [{"scene": q["scene"], "pause_at": q["pause_at"], "resume_at": q["resume_at"],
                           "answer_at": q["answer_at"], "options": [o["text"] for o in q["options"]],
                           "wrong": next((k for k, o in enumerate(q["options"]) if not o["correct"]), 0)}
                          for q in ive_predict.page_data(IVE).get("questions") or []],
            "sealed_text": text.ui("ive_chapter_sealed")}


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


def test_explanation_first_default():
    """AC-6.8: by default the film plays through each question and explains: it never enters the prediction stop
    and never pauses, skips the silent think gap, and the answer-stating chapter titles open once the answer has
    played. The practice-mode toggle is visible and off."""
    out, c = _check("explanation_first_default")
    assert out["spec"]["questions"], "the slice IVE has no question to play through"
    return {"browser": out["browser"], "played_through": [{k: r[k] for k in ("scene", "modes", "paused", "t_end")}
                                                          for r in c["detail"]]}


def test_practice_mode_pauses():
    """AC-6.8: with the practice toggle on, the film stops at the question, holds through a wait and a play(), shows
    the storyboard's options and resumes at the answer scene after a pick; turning practice off releases the hold."""
    out, c = _check("practice_mode_pauses")
    return {"browser": out["browser"], "stopped_at": [round(r["stopped"]["t"], 3) for r in c["detail"]],
            "resumed_at": [round(r["picked"]["t"], 3) for r in c["detail"]]}


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


def test_caption_band_clear_of_film():
    """Integration finding (WP9 Part A): at 1440 a caption line sat half under the progress bar, and at 390 the
    caption covered the film. Captions now live in a reserved band under the film: at both widths the band is
    below the video, holds its text, shows the cue being spoken, and the browser draws no captions on the film."""
    timing, _cues = _built()
    cue = timing["cues"][len(timing["cues"]) // 2]
    work = host.make_tmp("ive-capband-")
    try:
        jobs = []
        for w in visual.WIDTHS:
            steps = [{"waitFor": "window.__ptkReady && window.__ptkReady()", "timeout": 30000},
                     {"eval": visual.IVE_DRIVE.read_text(), "as": "drive"},
                     {**visual._js(f"await D.seek({cue['start'] + 0.3:.3f}); await D.sleep(200); const L = D.layout(); "
                                   "const b = document.getElementById('capband').getBoundingClientRect(), "
                                   "f = D.v().getBoundingClientRect(); return {problems: L.problems, band_top: b.top, "
                                   "film_bottom: f.bottom, text: document.getElementById('captext').textContent};"), "as": "m"}]
            jobs.append({"id": f"w{w}", "type": "script", "url": (IVE / "index.html").resolve().as_uri(), "width": w,
                         "height": 900, "steps": steps})
        res = visual.shoot(jobs, work / "w")
        out = {}
        for r in res["results"]:
            m = (r.get("values") or {}).get("m") or {}
            assert r.get("ok"), r.get("error", "")[:500]
            cap = [p for p in m["problems"] if p["kind"].startswith(("caption", "no-caption"))]
            assert not cap, (r["id"], cap)
            assert m["band_top"] >= m["film_bottom"] - 0.5, (r["id"], m)
            assert m["text"] == cue["text"], (r["id"], m["text"], cue["text"])
            out[r["id"]] = {"gap_px": round(m["band_top"] - m["film_bottom"], 1)}
        return out
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _explore_values(origin, cue_list):
    """What the ive-explore script returns on a page that behaves: FILM, EXPLORE, an edit or step back marked with
    `origin`, RETURN to the film, a clean re-pause."""
    c = next(c for c in cue_list if c["kind"] == "state")
    st = c["state"]
    var = next(iter(st["vars"]), "")
    return {"film": {"mode": "film", "origin": "film"},
            "explore": {"mode": "explore", "paused": True, "origin": "film", "cue": c["cue"], "expected_cue": c["cue"],
                        "returnTime": 2.0, "border": "solid", "output": ["a"]},
            "edited": {"origin": origin, "edit": "x", "border": "dashed", "output": ["b"]},
            "returned": {"mode": "film", "paused": False, "return_position": 2.0, "t": 2.1, "origin": "film",
                         "cue": c["cue"], "film_cue": c["cue"], "edits_left": 0},
            "repaused": {"origin": "film", "edit": None, "cue": c["cue"], "n_checked": st["vars"].get(var),
                         "brk_pressed": None}}


def test_explore_mode_is_declared_not_inferred():
    """Round-17 P2-2: the IVE explore check decides the kind of live edit from lesson.json (the switch model, or the
    knob a `figure.explore` declares), never from whether the live model happened to build. The auditor's counterexample:
    drop figure.compare.program from the switch lesson, so its live model fails; a page that only steps back
    used to pass `ive.explore-return`. Now it fails with the model error."""
    import copy
    def built_cues(d):
        p = d / "build" / "ive" / "cues.json"
        if not p.exists():
            raise NotRun(f"no built IVE cues at {p}")
        return json.loads(p.read_text())
    lesson = model.load(SLICE)
    cues = built_cues(SLICE)
    assert "panel" not in lesson.data["figure"], "the switch lesson declares a live edit (no figure.panel)"
    ok, m = visual.explore_checks(lesson, cues, _explore_values("yours", cues))
    assert all(ok.values()) and m["mode"] == "live" and m["live_edit"], ok
    _ok, _m = visual.explore_checks(lesson, cues, _explore_values("step", cues))
    assert not all(_ok.values()), "a live-edit lesson whose page only steps back must fail"
    broken = copy.deepcopy(lesson)
    broken.data["figure"]["compare"].pop("program", None)
    assert ive.live_model(broken) is None, "the counterexample needs a live model that fails"
    bad, bm = visual.explore_checks(broken, cues, _explore_values("step", cues))
    assert bm["mode"] == "live" and not bad["live_model_builds"] and not all(bad.values()), bm
    assert bm["live_model_error"], bm
    # D23.5 (SPEC v1.4 AC-6.6, stricter): a panel lesson needs a live control too. The neuron declares its knob
    # (figure.explore), so its IVE must make a live edit in EXPLORE: a page that only steps back through the film now
    # fails, and a live edit marked as the learner's passes.
    panel = model.load(SLICE.parent / "neuron")
    pcues = built_cues(SLICE.parent / "neuron")
    pok, pm = visual.explore_checks(panel, pcues, _explore_values("yours", pcues))
    assert pm["mode"] == "knob" and pm["live_edit"] and all(pok.values()) and "live_edit_marked_yours" in pok, pok
    pstep, _ = visual.explore_checks(panel, pcues, _explore_values("step", pcues))
    assert not all(pstep.values()), "a panel lesson whose IVE only steps back through the film must fail (D23.5)"
    # a panel lesson that declares no live control at all fails: there is nothing a step-through page can do to pass
    bare = copy.deepcopy(panel)
    bare.data["figure"].pop("explore", None)
    nok, nm = visual.explore_checks(bare, pcues, _explore_values("step", pcues))
    assert nm["mode"] == "missing" and not all(nok.values()), (nm["mode"], nok)
    return {"switch": m["mode"], "broken_switch": bm["live_model_error"][:120], "neuron": pm["mode"],
            "no_knob": nm["mode"]}


def test_caption_toggle_measures_rendered_text():
    """Round-17 P3-2 / Codex 7: the caption control is judged by what is drawn, not by a data attribute. On the built
    slice IVE: captions on, off, on, measured from the caption text's computed style and box after each click, and
    the text at a second cue. Counterexample: a page slip that leaves the caption drawn while the control says off
    (`data-on="false"`); the attributes still toggle and the first cue's text matches, so the old check passed.
    Now it fails."""
    timing, _cues = _built()
    work = host.make_tmp("ive-captoggle-")
    try:
        ready = {"waitFor": "window.__ptkReady && window.__ptkReady()", "timeout": 30000}
        drive = {"eval": visual.IVE_DRIVE.read_text(), "as": "drive"}
        # the slip: the off state neither hides nor clears the caption text, while data-on still toggles
        slip = {"eval": "(() => { const el = document.getElementById('captext'); "
                        "el.style.setProperty('visibility', 'visible', 'important'); "
                        "const d = Object.getOwnPropertyDescriptor(Node.prototype, 'textContent'); "
                        "Object.defineProperty(el, 'textContent', {configurable: true, get() { return d.get.call(this); }, "
                        "set(x) { if (x !== '') d.set.call(this, x); }}); return 1; })()"}
        url = (IVE / "index.html").resolve().as_uri()
        jobs = [{"id": "ok", "type": "script", "url": url, "width": 1440, "height": 900,
                 "steps": [ready, drive, visual.ive_controls_step(timing)]},
                {"id": "slip", "type": "script", "url": url, "width": 1440, "height": 900,
                 "steps": [ready, drive, slip, visual.ive_controls_step(timing)]}]
        res = {r["id"]: r for r in visual.shoot(jobs, work / "w")["results"]}
        good = (res["ok"].get("values") or {}).get("controls") or {}
        slipped = (res["slip"].get("values") or {}).get("controls") or {}
        assert res["ok"].get("ok") and res["slip"].get("ok"), (res["ok"].get("error"), res["slip"].get("error"))
        ok, why = visual.captions_ok(good, timing)
        assert ok, (why, good)
        bad, why_bad = visual.captions_ok(slipped, timing)
        assert not bad and [m.get("data_on") for m in slipped["caption_states"]] == ["true", "false", "true"], slipped
        assert [m["shown"] for m in slipped["caption_states"]] == [True, True, True], slipped["caption_states"]
        return {"ok": [m["shown"] for m in good["caption_states"]], "slip_caught": why_bad}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_live_control_every_lesson():
    """SPEC v1.4 AC-6.6 (D23.5), on all four lessons: in EXPLORE the IVE offers a live control that changes the shown
    state (stepping back through the film does not count), the edit is marked as the learner's, and RETURN resumes the
    film at the paused time with the film's state. Each built lesson's IVE runs the gate's own FILM / EXPLORE /
    RETURN script in Chrome from file://; not-run when a lesson is not built."""
    lessons = sorted(p.parent for p in SLICE.parent.glob("*/lesson.json"))
    built = [d for d in lessons if (d / "build" / "ive" / "cues.json").exists() and (d / "build" / "ive" / "index.html").exists()]
    if len(built) < len(lessons):
        raise NotRun(f"not built: {sorted(d.name for d in lessons if d not in built)}")
    jobs, cues = [], {}
    for d in built:
        cues[d.name] = json.loads((d / "build" / "ive" / "cues.json").read_text())
        jobs.append(visual.explore_flow_job(cues[d.name], (d / "build" / "ive" / "index.html").resolve().as_uri(),
                                            job_id=d.name))
    work = host.make_tmp("ive-live-every-")
    try:
        res = {r["id"]: r for r in visual.shoot(jobs, work / "w")["results"]}
    finally:
        shutil.rmtree(work, ignore_errors=True)
    out, bad = {}, {}
    for d in built:
        r = res.get(d.name) or {}
        checks, m = visual.explore_checks(model.load(d), cues[d.name], r.get("values") or {})
        out[d.name] = {"mode": m["mode"], "edit": (m["edited"] or {}).get("edit"),
                       "output_before": (m["explore"] or {}).get("output"), "output_edited": (m["edited"] or {}).get("output")}
        if not r.get("ok") or not all(checks.values()):
            bad[d.name] = {"error": (r.get("error") or "")[:300], "checks": checks}
    assert not bad, bad
    return out
