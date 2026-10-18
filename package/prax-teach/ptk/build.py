"""`ptk build` and `ptk claims check`: run the state machine in model.py and write the build report.

build:  validate → capture → expect check → project (--only media) → automatic gates
        → claims jobs → claims-pending (exit 4) | failed (1) | incomplete (5) | degraded (6)
claims check: reviews vs manifests → verified (0) | failed | incomplete | degraded
The report (build/build-report.json) records every gate, measurement, artifact hash and tool version.
"""
import json
import os
import shutil
import sys
import time
from pathlib import Path

from . import errors, host, model, node
from .capture import c_runner
from .verify import claims as claims_gate
from .verify import values

SUPPORTED = ("still", "video", "ive")
REPORT_SCHEMA = host.PKG / "schemas" / "build-report.schema.json"


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def report_path(lesson):
    return lesson.build_dir() / "build-report.json"


def tool_versions():
    v = {t: host.tool_version(t) for t in ("clang", "gcc-16", "ffmpeg", "whisper-cli", "tesseract")}
    v["node"] = node.node_version()
    v["hyperframes"] = node.hyperframes_version()
    pw = host.state_path("tools", "node", "node_modules", "playwright", "package.json")
    v["playwright"] = json.loads(pw.read_text())["version"] if pw.exists() else None
    v["python"] = ".".join(map(str, __import__("sys").version_info[:3]))
    v["sandbox-exec"] = host.sandbox_exec()
    return v


def _entry():
    skill = host.PKG / "SKILL.md"
    return {"skill_md": str(skill), "skill_md_sha256": host.sha256_file(skill) if skill.exists() else None,
            "ptk": str(host.PKG / "bin" / "ptk"), "registration": "none (direct path, D19.3)"}


def save(lesson, rep):
    """Validate, then replace the report atomically (write a sibling, then rename)."""
    import jsonschema
    jsonschema.Draft202012Validator(json.loads(REPORT_SCHEMA.read_text())).validate(rep)
    dst = report_path(lesson)
    part = dst.with_name(dst.name + ".part")
    part.write_text(json.dumps(rep, indent=2, default=str))
    os.replace(part, dst)


def _fail(lesson, rep, err, code, t0):
    rep["error"] = err
    rep["status"] = "failed"
    rep["transitions"].append("failed")
    rep["exit"] = code
    rep["finished"] = _now()
    rep["seconds"] = round(time.monotonic() - t0, 1)
    save(lesson, rep)


def _artifact_list(build):
    out = []
    for sub in ("still", "video", "ive"):
        d = build / sub
        if not d.exists():
            continue
        for p in sorted(d.rglob("*")):
            if p.is_file() and "work" not in p.parts and ".hyperframes" not in p.parts and "renders" not in p.parts \
                    and "snapshots" not in p.parts:
                out.append({"path": str(p.relative_to(build)), "bytes": p.stat().st_size, "sha256": host.sha256_file(p)})
    return out


def final_status(gates, degraded):
    st = [g["status"] for g in gates]
    if "failed" in st:
        return "failed"
    if "not-run" in st:
        return "incomplete"
    if "pending" in st:
        return "claims-pending"  # unreviewed claims outrank a fallback (review P1-1)
    if degraded:
        return "degraded"
    return "verified"


def build(lesson_path, only=None):
    lesson = model.load(lesson_path)
    media = only or [m for m in lesson.data.get("requested_media", []) if m in SUPPORTED]
    t0 = time.monotonic()
    rep = {"schema": "prax-teach/build-report@1", "lesson": None, "lesson_sha256": None, "status": "draft",
           "started": _now(), "finished": None, "media": media, "entry": _entry(), "gates": [], "fallbacks": [],
           "tools": {}, "artifacts": [], "transitions": ["draft"], "error": None}
    build_dir = lesson.dir / "build"
    # Replace any earlier report now, so a killed or crashed build never leaves a stale "verified" (P1-2).
    save(lesson, rep)
    finished = False

    def go(target):
        rep["status"] = model.advance(rep["status"], target)
        rep["transitions"].append(target)

    try:
        unsupported = [m for m in media if m not in SUPPORTED]
        if unsupported:
            raise errors.ModelSchemaError(f"WP0 builds still, video and ive only; asked for {unsupported}",
                                          pointer="/requested_media")
        model.validate(lesson)
        rep["lesson"] = lesson.id
        go("valid")
        for sub in ("still", "ive", "shots", "work", "claims-jobs"):
            shutil.rmtree(build_dir / sub, ignore_errors=True)
        cap = c_runner.capture_lesson(lesson)
        model.validate(lesson, stage="captured")
        rep["lesson_sha256"] = lesson.sha256()
        rep["capture"] = {"programs": cap["programs"], "platform": cap["platform"]}
        go("captured")
        rep["tools"] = tool_versions()
        rep["gates"].append({"id": "values.expect", "medium": "all", "status": "passed",
                             "measured": values.check_expectations(lesson), "reason": ""})
        gates, degraded = _project_and_verify(lesson, build_dir, media, rep, go)
        rep["gates"] += gates
        items = claims_gate.collect_texts(lesson, build_dir)
        rep["gates"].append(claims_gate.mapping_gate(lesson, items))
        jobs = claims_gate.write_jobs(lesson, items, build_dir)
        rep["claims"] = {"jobs": [str(build_dir / "claims-jobs" / f"{j}.json") for j in jobs],
                         "reviews_dir": str(build_dir / "claims-review"), "rubric": str(claims_gate.RUBRIC),
                         "next": "run each job in a separate subagent with only the job file and the rubric, then `ptk claims check`"}
        rep["gates"].append({"id": "claims.review", "medium": "all", "status": "pending", "measured": {},
                             "reason": "waiting for reviewer subagents"})
        if any(json.loads((build_dir / "claims-private.json").read_text())[j]["kind"] == "mutation" for j in jobs):
            rep["gates"].append({"id": "claims.sensitivity", "medium": "all", "status": "pending", "measured": {},
                                 "reason": "waiting for reviewer subagents"})
        st = final_status(rep["gates"], degraded)
        go("claims-pending" if st in ("claims-pending", "verified") else st)
        rep["artifacts"] = _artifact_list(build_dir)
        rep["finished"] = _now()
        rep["seconds"] = round(time.monotonic() - t0, 1)
        save(lesson, rep)
        finished = True
    except errors.PtkError as e:
        _fail(lesson, rep, e.as_dict(), e.exit_code, t0)
        finished = True
        raise
    finally:
        if not finished:
            # Not a PtkError: a ptk bug or an unexpected tool output. Record it, then let it propagate.
            exc = sys.exc_info()[1]
            _fail(lesson, rep, {"error": type(exc).__name__ if exc else "Interrupted",
                                "message": str(exc) if exc else "build stopped before finishing",
                                "internal": True, "exit": errors.EXIT_GATE}, errors.EXIT_GATE, t0)
    return rep


HF_SECTIONS = ("lint", "runtime", "layout", "contrast", "motion")


def hf_check_clean(hf):
    """AC-5.1: all five sections present, each with integer error and warning counts of 0 (review P2-8).
    A missing section or count is a failure, never a zero."""
    counts, missing = {}, []
    for k in HF_SECTIONS:
        sec = hf.get(k)
        if not isinstance(sec, dict):
            missing.append(k)
            continue
        counts[k] = {"errors": sec.get("errorCount"), "warnings": sec.get("warningCount")}
        if not all(isinstance(v, int) and not isinstance(v, bool) for v in counts[k].values()):
            missing.append(f"{k} counts")
    nonzero = [k for k, c in counts.items() if c["errors"] or c["warnings"]]
    clean = hf.get("ok") is True and not missing and not nonzero
    why = "" if clean else "; ".join(filter(None, [f"missing: {missing}" if missing else "",
                                                   f"errors or warnings in {nonzero}" if nonzero else "",
                                                   "" if hf.get("ok") is True else "check not ok"]))
    return clean, counts, why


def _project_and_verify(lesson, build_dir, media, rep, go):
    from .project import ive, still, video
    from .verify import frames, isolation, visual
    from .verify import media as media_gates
    gates, degraded = [], False
    timing = None
    projected = {}
    if "still" in media:
        out = build_dir / "still"
        svgs = still.project(lesson, out)
        pngs, failed, ob = visual.make_pngs(out, svgs, lesson.sha256())
        if failed:
            raise errors.ToolFailed("PNG export failed", jobs=failed)
        projected["still"] = (out, svgs)
    if "video" in media or "ive" in media:
        out = build_dir / "video"
        v = video.project(lesson, out)
        timing = v["timing"]
        if v["degraded"]:
            degraded = True
            rep["fallbacks"].append({"what": "tts", "engine": v["tts"]["engine"]})
        rep["tts"] = {k: val for k, val in v["tts"].items() if k != "segments"}
        tmp = host.make_tmp("canary-")
        canaries = isolation.run_canaries(v["composition"], tmp)
        chk = node.hyperframes(["check", ".", "--json"], cwd=v["composition"], timeout=900,
                               lesson_sha256=lesson.sha256(), sandbox_tmp=host.make_tmp("check-"), check=False)
        projected["video"] = (out, v, canaries, chk)
    go("projected")
    if "still" in projected:
        out, svgs = projected["still"]
        gates.append(values.gate(lesson, "still", [("svg", out / s) for s in svgs]))
        gates += visual.still_gates(lesson, out, svgs)
    if "video" in projected:
        out, v, canaries, chk = projected["video"]
        try:
            hf = json.loads(chk.stdout)
        except json.JSONDecodeError:
            hf = {"ok": False, "raw": (chk.stdout or chk.stderr)[-2000:]}
        clean, counts, why = hf_check_clean(hf)
        gates.append({"id": "video.hyperframes-check", "medium": "video", "status": "passed" if clean else "failed",
                      "measured": {"exit": chk.code, "counts": counts, "sandboxed": True}, "reason": why})
        gates.append(frames.scene_layout_gate(lesson, out, timing, lesson.sha256()))
        render_ok, log = True, ""
        try:
            mp4, log = video.finish(lesson, out, v["composition"])
        except errors.RenderFailed as e:
            render_ok, log = False, e.detail.get("log_tail", "")
        gates.append(isolation.gate(canaries, render_ok, log))
        if render_ok:
            gates.append(values.gate(lesson, "video", [("html", p) for p in sorted(
                (v["composition"] / "compositions").glob("*.html"))]))
            gates.append(media_gates.media_gate(mp4, out, timing))
            gates.append(media_gates.sync_gate(mp4, out, timing, out / "work" / "sync"))
            gates.append(media_gates.leak_gate(lesson, timing, out))
        else:
            for gid in ("values.video", "video.media", "video.sync", "video.no-answer-leak"):
                gates.append({"id": gid, "medium": "video", "status": "not-run", "measured": {},
                              "reason": "render failed"})
    if "ive" in media:
        if "video" not in projected or not (build_dir / "video" / "lesson.mp4").exists():
            gates.append({"id": "ive.all", "medium": "ive", "status": "not-run", "measured": {}, "reason": "no video"})
        else:
            r = ive.project(lesson, build_dir / "ive", build_dir / "video", timing)
            gates.append(values.gate(lesson, "ive", [("vtt", build_dir / "ive" / "states.vtt")]))
            gates += visual.ive_gates(lesson, build_dir / "ive", r["cues"], timing)
    return gates, degraded


def load_report(lesson_path):
    lesson = model.load(lesson_path)
    p = report_path(lesson)
    if not p.exists():
        raise errors.ModelReferenceError(f"no build report at {p}; run `ptk build` first")
    return json.loads(p.read_text())


def claims_check(lesson_path):
    lesson = model.load(lesson_path)
    rep = load_report(lesson_path)
    if rep["status"] not in ("claims-pending", "verified", "incomplete", "failed", "degraded"):
        raise errors.IllegalTransition(f"claims check needs a built lesson; status is {rep['status']}")
    build_dir = lesson.dir / "build"
    items = claims_gate.collect_texts(lesson, build_dir)
    mapping = claims_gate.mapping_gate(lesson, items)
    new = claims_gate.check(lesson, build_dir, items)
    ids = {g["id"] for g in new} | {"claims.mapping"}
    rep["gates"] = [g for g in rep["gates"] if g["id"] not in ids] + [mapping] + new
    if rep.get("lesson_sha256") and rep["lesson_sha256"] != lesson.sha256():
        rep["gates"].append({"id": "claims.lesson-unchanged", "medium": "all", "status": "failed", "measured": {},
                             "reason": "lesson.json changed after the build; rebuild"})
    target = final_status(rep["gates"], bool(rep.get("fallbacks")))
    if rep.get("error"):
        target = "failed"  # the build itself stopped; reviews cannot rescue it
    elif rep["status"] == "claims-pending":
        target = model.advance("claims-pending", target)
    rep["status"] = target
    rep["transitions"].append(rep["status"])
    rep["claims_checked"] = _now()
    save(lesson, rep)
    return rep


def exit_code(rep):
    if rep["status"] == "failed" and rep.get("exit"):
        return rep["exit"]
    return model.FINAL_EXIT.get(rep["status"], errors.EXIT_GATE)


def summary(rep):
    return {"lesson": rep.get("lesson"), "status": rep["status"], "exit": exit_code(rep),
            "gates": {g["id"]: g["status"] for g in rep["gates"]},
            "not_run": [g["id"] for g in rep["gates"] if g["status"] == "not-run"],
            "failed": [{"id": g["id"], "reason": g.get("reason")} for g in rep["gates"] if g["status"] == "failed"],
            "claims_jobs": rep.get("claims", {}).get("jobs", []), "next": rep.get("claims", {}).get("next")
            if rep["status"] == "claims-pending" else None, "error": rep.get("error")}


def render_text(rep):
    lines = [f"lesson {rep.get('lesson')}  status {rep['status']}  exit {exit_code(rep)}",
             f"started {rep['started']}  finished {rep.get('finished')}  ({rep.get('seconds')} s)", ""]
    for g in rep["gates"]:
        lines.append(f"  {g['status']:<8} {g['id']:<28} {g.get('reason') or ''}")
    if rep.get("fallbacks"):
        lines.append(f"fallbacks: {rep['fallbacks']}")
    if rep.get("error"):
        lines.append(f"error: {rep['error'].get('error')}: {rep['error'].get('message')}")
    return "\n".join(lines)
