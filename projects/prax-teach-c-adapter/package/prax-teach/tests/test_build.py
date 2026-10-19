"""Build status and crash reporting (D18.1, D19.5; review P1-1 and P1-2)."""
import json
import shutil

from _util import SLICE, ptk_cmd
from ptk import build, errors, host, model
from ptk.verify import values


def _g(gid, status):
    return {"id": gid, "medium": "all", "status": status, "measured": {}}


def test_pending_claims_beat_degraded():
    """A fallback build whose claims are unreviewed is claims-pending (4), never degraded (6), in any gate order."""
    pending_first = [_g("claims.review", "pending"), _g("values.expect", "passed")]
    pending_last = [_g("values.expect", "passed"), _g("claims.review", "pending")]
    for gates in (pending_first, pending_last):
        st = build.final_status(gates, degraded=True)
        assert st == "claims-pending", f"degraded build with pending claims gave {st}"
        assert build.exit_code({"status": st}) == errors.EXIT_CLAIMS_PENDING


def test_degraded_only_after_claims_pass():
    """Build (pending) then claims check (passed): only the second step may reach degraded (6)."""
    at_build = build.final_status([_g("values.expect", "passed"), _g("claims.review", "pending")], degraded=True)
    status = model.advance("projected", at_build)
    after = build.final_status([_g("values.expect", "passed"), _g("claims.review", "passed")], degraded=True)
    status = model.advance(status, after)
    assert (at_build, status) == ("claims-pending", "degraded")
    assert build.exit_code({"status": status}) == errors.EXIT_DEGRADED
    # failed and not-run still outrank both
    assert build.final_status([_g("a", "pending"), _g("b", "failed")], True) == "failed"
    assert build.final_status([_g("a", "pending"), _g("b", "not-run")], True) == "incomplete"


def _copy_slice(name):
    tmp = host.make_tmp(name)
    dst = tmp / "switch-fallthrough"
    shutil.copytree(SLICE, dst, ignore=shutil.ignore_patterns("build"))
    stale = {"schema": "prax-teach/build-report@1", "lesson": "switch-fallthrough", "status": "verified",
             "started": "2026-10-18T00:00:00+0000", "media": ["still"], "gates": [], "fallbacks": [], "tools": {},
             "artifacts": [], "transitions": ["draft", "verified"], "error": None}
    (dst / "build").mkdir()
    (dst / "build" / "build-report.json").write_text(json.dumps(stale))
    return tmp, dst


def _report_cli(lesson_dir):
    res = host.run([*ptk_cmd(), "report", str(lesson_dir), "--json"], timeout=120)
    return res.code, json.loads(res.stdout)


def test_unknown_expect_fn_leaves_failed_report():
    """An unknown expect.fn must not leave the previous verified report behind (ptk report shows failed)."""
    tmp, lesson_dir = _copy_slice("crash-expect-")
    try:
        data = json.loads((lesson_dir / "lesson.json").read_text())
        data["facts"][0]["expect"] = {"fn": "no_such_fn", "args": []}
        (lesson_dir / "lesson.json").write_text(json.dumps(data, indent=2))
        res = host.run([*ptk_cmd(), "build", str(lesson_dir), "--only", "still"], timeout=600)
        assert res.code != 0, "build with an unknown expect.fn exited 0"
        code, rep = _report_cli(lesson_dir)
        assert rep["status"] == "failed", f"ptk report still says {rep['status']}"
        assert code != 0
        assert "no_such_fn" in json.dumps(rep["error"]), rep["error"]
        # caught at validate time with a JSON pointer, not as a crash after capture
        assert res.code == errors.EXIT_MODEL and "/facts/0/expect/fn" in json.dumps(rep["error"]), rep["error"]
        return {"build_exit": res.code, "report_exit": code, "error": rep["error"]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_internal_crash_leaves_failed_report():
    """Any exception, not only PtkError, ends in a failed report naming the error class and message."""
    tmp, lesson_dir = _copy_slice("crash-internal-")
    original = values.check_expectations

    def boom(lesson):
        raise KeyError("synthetic crash after capture")

    values.check_expectations = boom
    crashed = None
    try:
        try:
            build.build(lesson_dir, only=["still"])
        except KeyError as e:
            crashed = e
        assert crashed is not None, "the synthetic crash did not propagate"
        code, rep = _report_cli(lesson_dir)
        assert rep["status"] == "failed", f"ptk report still says {rep['status']}"
        assert code != 0
        assert rep["error"]["error"] == "KeyError" and "synthetic crash" in rep["error"]["message"], rep["error"]
        assert rep["transitions"][-1] == "failed"
        return {"report_exit": code, "error": rep["error"]}
    finally:
        values.check_expectations = original
        shutil.rmtree(tmp, ignore_errors=True)


def test_hyperframes_check_missing_count_fails():
    """Review P2-8: a missing section or count is not zero."""
    full = {"ok": True, **{k: {"errorCount": 0, "warningCount": 0} for k in build.HF_SECTIONS}}
    assert build.hf_check_clean(full)[0]
    no_section = {k: v for k, v in full.items() if k != "motion"}
    renamed = {**full, "lint": {"errors": 0, "warningCount": 0}}
    empty = {"ok": True}
    for bad in (no_section, renamed, empty):
        clean, _counts, why = build.hf_check_clean(bad)
        assert not clean and "missing" in why, bad
    assert not build.hf_check_clean({**full, "layout": {"errorCount": 0, "warningCount": 2}})[0]


def test_only_keeps_other_media():
    """WP5 (open bug from WP3): `--only x` clears and rebuilds x only. Other media's outputs and the
    claims reviews stay; `--only video` and `--only ive` rebuild both, since the IVE plays the video."""
    assert build.rebuilt_media(["still"]) == ["still"]
    assert build.rebuilt_media(["video"]) == ["ive", "video"] == build.rebuilt_media(["ive"])
    tmp = host.make_tmp("only-unit-")
    try:
        b = tmp / "build"
        for rel in ("still", "video", "ive", "work/ive", "work/other", "explorer", "qa", "cards", "claims-jobs",
                    "claims-review", "shots"):
            (b / rel).mkdir(parents=True)
            (b / rel / "x").write_text("x")
        removed = build.clear_outputs(b, ["still"])
        assert sorted(removed) == ["claims-jobs", "still"], removed
        assert all((b / r / "x").exists() for r in ("video", "ive", "explorer", "qa", "cards", "claims-review", "shots"))
        removed = build.clear_outputs(b, ["video"])
        assert sorted(removed) == ["ive", "video", "work/ive"], removed
        assert (b / "work" / "other" / "x").exists() and (b / "explorer" / "x").exists()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # end to end through the CLI on a copy of the slice
    tmp, lesson_dir = _copy_slice("only-e2e-")
    try:
        keep = {}
        for rel in ("ive", "explorer", "qa", "video", "claims-review"):
            (lesson_dir / "build" / rel).mkdir(parents=True, exist_ok=True)
            (lesson_dir / "build" / rel / "marker.txt").write_text(rel)
            keep[rel] = lesson_dir / "build" / rel / "marker.txt"
        res = host.run([*ptk_cmd(), "build", str(lesson_dir), "--only", "cards"], timeout=900)
        assert res.code in (errors.EXIT_CLAIMS_PENDING, errors.EXIT_OK, errors.EXIT_INCOMPLETE), res.stderr[-1500:]
        gone = [r for r, p in keep.items() if not p.exists()]
        assert not gone, f"--only cards deleted {gone}"
        assert (lesson_dir / "build" / "cards").is_dir()
        rep = json.loads((lesson_dir / "build" / "build-report.json").read_text())
        assert rep["media"] == ["cards"], rep["media"]
        assert set(rep["cleared"]) <= {"cards", "claims-jobs"}, rep["cleared"]
        return {"exit": res.code, "kept": sorted(keep), "cleared": rep["cleared"]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _rep(media, sha, gates, artifacts=(), fallbacks=(), code="P1", tools=None):
    return {"schema": "prax-teach/build-report@1", "lesson": "x", "lesson_sha256": sha, "status": "claims-pending",
            "started": "t", "media": list(media), "gates": list(gates), "fallbacks": list(fallbacks),
            "tools": dict(tools or {"ffmpeg": "8"}), "artifacts": list(artifacts), "transitions": ["draft"],
            "error": None, "ptk": {"version": "v", "code_sha256": code}}


def _art(path, sha="h"):
    return {"path": path, "bytes": 1, "sha256": sha}


def test_only_merges_previous_report():
    """Integration pass: `--only x` keeps the other media's gates, artifacts and fallbacks from the previous report
    when the lesson is unchanged, so the report always describes every medium on disk. A changed lesson carries
    nothing (those outputs are stale) and marks them not-run; a full build replaces everything."""
    arts = [_art("video/lesson.mp4"), _art("ive/index.html")]
    prev = _rep(["video", "ive"], "s1",
                [_g("values.expect", "passed"), {"id": "video.media", "medium": "video", "status": "passed",
                                                 "measured": {}}, {"id": "ive.layout", "medium": "ive",
                                                                   "status": "passed", "measured": {}},
                 {"id": "claims.review", "medium": "all", "status": "passed", "measured": {}}],
                artifacts=arts, fallbacks=[{"what": "tts", "engine": "say"}])
    prev["video"], prev["tts"] = {"theme": "dark"}, {"engine": "say"}
    new = _rep(["still"], "s1", [{"id": "values.still", "medium": "still", "status": "passed", "measured": {}}],
               artifacts=[_art("still/a.svg")])
    now = [_art("still/a.svg")] + arts
    out = build.merge_previous(prev, new, rebuilt=["still"], on_disk=["still", "video", "ive"], current_artifacts=now)
    assert out["media"] == ["still", "video", "ive"], out["media"]
    ids = [g["id"] for g in out["gates"]]
    assert "video.media" in ids and "ive.layout" in ids and "values.still" in ids, ids
    assert "claims.review" not in ids and ids.count("values.expect") == 0, "medium 'all' gates are always recomputed"
    assert {a["path"] for a in out["artifacts"]} == {"still/a.svg", "video/lesson.mp4", "ive/index.html"}
    assert out["fallbacks"] == [{"what": "tts", "engine": "say"}] and out["video"] == {"theme": "dark"}
    assert out["merged_from_previous"] == ["video", "ive"]
    # the lesson changed: nothing carried, the stale media are named and their gates are not-run
    new2 = _rep(["still"], "s2", [{"id": "values.still", "medium": "still", "status": "passed", "measured": {}}])
    out2 = build.merge_previous(prev, new2, rebuilt=["still"], on_disk=["still", "video", "ive"], current_artifacts=now)
    assert out2["media"] == ["still"] and out2["uncovered_media"] == ["ive", "video"], out2
    assert not out2["fallbacks"] and "video.media" not in [g["id"] for g in out2["gates"]]
    assert {g["medium"]: g["status"] for g in out2["gates"] if g["id"].startswith("carry.")} == \
        {"video": "not-run", "ive": "not-run"}, out2["gates"]
    # no previous report (or a failed one): nothing carried
    out3 = build.merge_previous(None, _rep(["still"], "s1", []), rebuilt=["still"], on_disk=["still"],
                                current_artifacts=[_art("still/a.svg")])
    assert out3["media"] == ["still"] and not out3.get("uncovered_media")
    failed = dict(prev, status="failed")
    out4 = build.merge_previous(failed, _rep(["still"], "s1", []), rebuilt=["still"], on_disk=["still", "video"],
                                current_artifacts=now)
    assert out4["media"] == ["still"] and out4["uncovered_media"] == ["video"], out4
    return {"merged": out["media"], "stale": out2["uncovered_media"]}


def test_only_carries_nothing_over_changed_artifacts_or_ptk():
    """D22.2 (round-17 P1-1): a carried medium needs every recorded artifact on disk with the recorded sha256, no
    new file under it, and the same ptk code fingerprint and tool versions. Otherwise its old gates are dropped
    and the medium is marked not-run, so a tampered still can never ride along as `passed`."""
    still_gates = [{"id": "visual.still.contrast", "medium": "still", "status": "passed", "measured": {}},
                   {"id": "values.still", "medium": "still", "status": "passed", "measured": {}}]
    prev = _rep(["still", "qa"], "s1", still_gates, artifacts=[_art("still/a.svg", "orig"), _art("still/a.png", "p")])
    new = _rep(["qa"], "s1", [{"id": "qa.layout", "medium": "qa", "status": "passed", "measured": {}}],
               artifacts=[_art("qa/index.html")])
    good = [_art("qa/index.html"), _art("still/a.svg", "orig"), _art("still/a.png", "p")]
    cases = {
        "tampered svg": (prev, new, [_art("qa/index.html"), _art("still/a.svg", "TAMPERED"), _art("still/a.png", "p")]),
        "file gone": (prev, new, [_art("qa/index.html"), _art("still/a.svg", "orig")]),
        "new file": (prev, new, good + [_art("still/b.svg", "x")]),
        "ptk changed": (prev, _rep(["qa"], "s1", new["gates"], code="P2"), good),
        "tools changed": (prev, _rep(["qa"], "s1", new["gates"], tools={"ffmpeg": "9"}), good),
        "old report without fingerprint": ({k: v for k, v in prev.items() if k != "ptk"}, new, good),
        "no inventory given": (prev, new, None),
    }
    out = {}
    for name, (p, n, now) in cases.items():
        r = build.merge_previous(p, n, rebuilt=["qa"], on_disk=["still", "qa"], current_artifacts=now)
        still = [g for g in r["gates"] if g["medium"] == "still"]
        assert not any(g["status"] == "passed" for g in still), (name, still)
        assert [g["status"] for g in still] == ["not-run"], (name, still)
        assert "still" not in r["merged_from_previous"] and r["uncovered_media"] == ["still"], (name, r)
        assert build.final_status(r["gates"], False) == "incomplete", name
        out[name] = r["carry_refused"]["still"]
    ok = build.merge_previous(prev, new, rebuilt=["qa"], on_disk=["still", "qa"], current_artifacts=good)
    assert ok["merged_from_previous"] == ["still"] and not ok["uncovered_media"], ok
    assert {g["id"] for g in ok["gates"]} == {"qa.layout", "visual.still.contrast", "values.still"}
    assert [a for a in ok["artifacts"] if a["path"].startswith("still/")] == prev["artifacts"], \
        "carried artifacts come from the verified previous inventory"
    return out


def test_only_qa_after_tampered_still_is_not_passed():
    """D22.2 end to end, the auditor's counterexample: copy the slice with its build, paint the output value `three`
    in the page colour in both light SVGs, run `ptk build --only qa`. No still gate may be `passed`."""
    from selftest_support import NotRun
    if not (SLICE / "build" / "still" / "switch-fallthrough-wide-light.svg").exists():
        raise NotRun("the slice has no still build to tamper with")
    tmp = host.make_tmp("only-tamper-")
    dst = tmp / "switch-fallthrough"
    try:
        shutil.copytree(SLICE, dst, ignore=shutil.ignore_patterns("work", "renders", "snapshots", ".hyperframes"))
        hit = 0
        for name in ("switch-fallthrough-wide-light.svg", "switch-fallthrough-portrait-light.svg"):
            svg = dst / "build" / "still" / name
            s = svg.read_text()
            import re
            t, n = re.subn(r'(<text[^>]*data-fact="f\.p1\.l2"[^>]*fill=")[^"]*(")', r"\g<1>#fbfaf6\g<2>", s)
            if n == 0:
                t, n = re.subn(r'(<text[^>]*fill=")[^"]*("[^>]*data-fact="f\.p1\.l2")', r"\g<1>#fbfaf6\g<2>", s)
            hit += n
            svg.write_text(t)
        assert hit, "the tamper found no f.p1.l2 text to repaint"
        res = host.run([*ptk_cmd(), "build", str(dst), "--only", "qa"], timeout=1800)
        rep = json.loads((dst / "build" / "build-report.json").read_text())
        still = {g["id"]: g["status"] for g in rep["gates"] if g["medium"] == "still"}
        assert still and "passed" not in still.values(), still
        assert "still" not in rep.get("merged_from_previous", []) and "still" in rep.get("uncovered_media", []), rep
        assert rep["status"] not in ("verified", "canary-verified", "claims-pending"), rep["status"]
        return {"exit": res.code, "status": rep["status"], "still": still, "tampered_texts": hit,
                "why": rep["carry_refused"]["still"]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_only_carry_refused_for_a_tampered_still_from_the_same_ptk():
    """D22.2 end to end with the same ptk on both builds, so only the artifact hashes can refuse the carry:
    `--only still`, then `--only qa` carries the still (control), then paint `three` invisible in the light SVGs and
    `--only qa` again: the still is refused because its artifacts differ, and no still gate is passed."""
    from selftest_support import NotRun
    import re
    if not (SLICE / "build" / "still").exists():
        raise NotRun("the slice has no build to start from")
    tmp = host.make_tmp("only-tamper2-")
    dst = tmp / "switch-fallthrough"
    try:
        shutil.copytree(SLICE, dst, ignore=shutil.ignore_patterns("work", "renders", "snapshots", ".hyperframes"))
        first = host.run([*ptk_cmd(), "build", str(dst), "--only", "still"], timeout=1800)
        if first.code not in (errors.EXIT_CLAIMS_PENDING, errors.EXIT_INCOMPLETE):
            # a still that fails its own gates leaves a failed report, which is never carried: no control possible
            raise NotRun(f"the slice's still does not build clean now (exit {first.code}), so there is no carry "
                         f"to refuse: {first.stdout[-400:]}")
        control = host.run([*ptk_cmd(), "build", str(dst), "--only", "qa"], timeout=1800)
        rep = json.loads((dst / "build" / "build-report.json").read_text())
        assert "still" in rep["merged_from_previous"], ("control: an untouched still is carried", control.code,
                                                         rep.get("carry_refused"))
        hit = 0
        for svg in (dst / "build" / "still").glob("*-light.svg"):
            t, n = re.subn(r'(<text[^>]*data-fact="f\.p1\.l2"[^>]*fill=")[^"]*(")', r"\g<1>#fbfaf6\g<2>", svg.read_text())
            if n == 0:
                t, n = re.subn(r'(<text[^>]*fill=")[^"]*("[^>]*data-fact="f\.p1\.l2")', r"\g<1>#fbfaf6\g<2>",
                               svg.read_text())
            hit += n
            svg.write_text(t)
        assert hit, "the tamper found no f.p1.l2 text"
        host.run([*ptk_cmd(), "build", str(dst), "--only", "qa"], timeout=1800)
        rep = json.loads((dst / "build" / "build-report.json").read_text())
        still = {g["id"]: g["status"] for g in rep["gates"] if g["medium"] == "still"}
        assert still == {"carry.still": "not-run"}, still
        assert rep["carry_refused"]["still"].startswith("artifacts differ"), rep["carry_refused"]
        return {"control_carried": True, "refused": rep["carry_refused"]["still"][:120], "status": rep["status"]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_only_still_after_video_keeps_video_and_ive():
    """End to end on a copy of the slice with its real video build: `ptk build --only still` leaves build/video and
    build/ive in place, and the report accounts for them: carried with their gates, or marked not-run (D22.2)."""
    from selftest_support import NotRun
    prev = json.loads((SLICE / "build" / "build-report.json").read_text()) \
        if (SLICE / "build" / "build-report.json").exists() else None
    if not prev or "video" not in prev.get("media", []) or not (SLICE / "build" / "video" / "lesson.mp4").exists() \
            or prev.get("lesson_sha256") != model.load(SLICE).sha256() or prev.get("status") == "failed":
        raise NotRun("the slice has no current video build to start from; run `ptk build lessons/switch-fallthrough`")
    tmp = host.make_tmp("only-merge-")
    dst = tmp / "switch-fallthrough"
    try:
        shutil.copytree(SLICE, dst, ignore=shutil.ignore_patterns("work", "renders", "snapshots", ".hyperframes"))
        res = host.run([*ptk_cmd(), "build", str(dst), "--only", "still"], timeout=1800)
        assert res.code in (errors.EXIT_CLAIMS_PENDING, errors.EXIT_INCOMPLETE), (res.code, res.stderr[-1500:])
        for p in ("video/lesson.mp4", "video/captions.vtt", "ive/index.html", "ive/states.vtt"):
            assert (dst / "build" / p).exists(), f"--only still deleted {p}"
        assert any((dst / "build" / "still").glob("*.png")), "no still PNGs"
        rep = json.loads((dst / "build" / "build-report.json").read_text())
        ids = {g["id"]: g["status"] for g in rep["gates"]}
        assert "values.still" in ids, ids
        # D22.2: video and ive keep their gates only when the previous report's inventory, ptk code and tools match;
        # otherwise they are named and marked not-run, never silently dropped or carried
        for m, gid in (("video", "video.media"), ("ive", "ive.layout")):
            if m in rep["merged_from_previous"]:
                assert gid in ids and m in rep["media"], (m, ids)
            else:
                assert ids.get(f"carry.{m}") == "not-run" and m in rep["uncovered_media"], (m, rep["carry_refused"])
        return {"exit": res.code, "media": rep["media"], "carried": rep["merged_from_previous"],
                "refused": rep["carry_refused"]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
