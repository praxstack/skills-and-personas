"""`ptk build` and `ptk claims check`: run the state machine in model.py and write the build report.

build:  validate → capture → expect check → project (--only media) → automatic gates
        → claims jobs (lesson + 1 canary; --calibrate: the full mutation suite with controls, D21.1) → claims-pending (exit 4) | failed (1) | incomplete (5) | degraded (6)
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

SUPPORTED = ("still", "video", "ive", "explorer", "qa", "cards")
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
    """What this field can show: the build ran through the package's bin/ptk, next to this SKILL.md.
    It cannot show that an agent loaded SKILL.md (review P2-6); that evidence is the agent session."""
    skill = host.PKG / "SKILL.md"
    return {"skill_md": str(skill), "skill_md_sha256": host.sha256_file(skill) if skill.exists() else None,
            "ptk": str(host.PKG / "bin" / "ptk"), "registration": "none (direct path, D19.3)",
            "shows": "build invoked via bin/ptk; does not show that SKILL.md was loaded"}


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
    for sub in ("still", "video", "ive", "explorer", "qa", "cards"):
        d = build / sub
        if not d.exists():
            continue
        for p in sorted(d.rglob("*")):
            if p.is_file() and "work" not in p.parts and ".hyperframes" not in p.parts and "renders" not in p.parts \
                    and "snapshots" not in p.parts:
                out.append({"path": str(p.relative_to(build)), "bytes": p.stat().st_size, "sha256": host.sha256_file(p)})
    return out


# What each medium writes under build/. `--only` clears exactly these for the media it rebuilds.
MEDIA_OUTPUTS = {"still": ("still",), "video": ("video",), "ive": ("ive", "work/ive"), "explorer": ("explorer",),
                 "qa": ("qa",), "cards": ("cards",)}
# The IVE plays the video and reads its timing: `--only` with either one builds both, so a
# stale IVE never sits next to a new video and no other medium's outputs are deleted.
DEPENDS = {"video": ("ive",), "ive": ("video",)}


def rebuilt_media(media):
    out = set(media)
    for m in media:
        out |= set(DEPENDS.get(m, ()))
    return sorted(out)


def clear_outputs(build_dir, media):
    """Remove the outputs of the media this build rewrites, plus the claims jobs (always rewritten).
    Everything else under build/ (other media, claims reviews, shots of other media) is kept.
    Returns the relative paths removed."""
    removed = []
    for rel in ["claims-jobs"] + [r for m in rebuilt_media(media) for r in MEDIA_OUTPUTS.get(m, ())]:
        d = build_dir / rel
        if d.exists():
            shutil.rmtree(d)
            removed.append(rel)
    return removed


CARRY_FROM = ("claims-pending", "verified", "incomplete", "degraded")  # finished builds only, never failed or crashed
FALLBACK_MEDIUM = {"tts": "video"}


def media_on_disk(build_dir):
    """The media whose output folder under build/ holds anything."""
    return [m for m in SUPPORTED if (build_dir / m).is_dir() and any((build_dir / m).iterdir())]


def _read_previous(lesson):
    p = report_path(lesson)
    try:
        return json.loads(p.read_text()) if p.exists() else None
    except (OSError, json.JSONDecodeError):
        return None


def merge_previous(prev, rep, rebuilt, on_disk):
    """`--only` keeps the other media's results (integration pass). From a previous finished report for the same
    lesson sha256, carry the gates, artifacts and fallbacks of every medium that this build did not rebuild and
    whose outputs are still on disk. Gates with medium "all" (values.expect, claims.*) are always recomputed.
    A changed lesson or a failed previous build carries nothing; media left on disk are listed as uncovered."""
    out = dict(rep)
    keep = []
    if prev and prev.get("status") in CARRY_FROM and prev.get("lesson_sha256") \
            and prev.get("lesson_sha256") == rep.get("lesson_sha256"):
        keep = [m for m in SUPPORTED if m in prev.get("media", []) and m not in rebuilt and m in on_disk]
    out["media"] = [m for m in SUPPORTED if m in rebuilt or m in keep]
    out["gates"] = list(rep["gates"]) + [g for g in prev["gates"] if g.get("medium") in keep] if keep else list(rep["gates"])
    have = {a["path"] for a in rep.get("artifacts", [])}
    out["artifacts"] = list(rep.get("artifacts", [])) + [
        a for a in (prev or {}).get("artifacts", []) if keep and a["path"].split("/", 1)[0] in keep and a["path"] not in have]
    out["fallbacks"] = list(rep.get("fallbacks", [])) + [
        f for f in (prev or {}).get("fallbacks", []) if FALLBACK_MEDIUM.get(f.get("what")) in keep]
    if "video" in keep:
        for k in ("video", "tts"):
            if k in prev and k not in out:
                out[k] = prev[k]
    out["merged_from_previous"] = keep
    out["uncovered_media"] = sorted(m for m in on_disk if m not in out["media"])
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


def build(lesson_path, only=None, video_theme=None, renderer="hyperframes", calibrate=False):
    lesson = model.load(lesson_path)
    media = only or [m for m in lesson.data.get("requested_media", []) if m in SUPPORTED]
    if only and not [m for m in only if m not in SUPPORTED]:
        media = [m for m in SUPPORTED if m in rebuilt_media(only)]  # `--only video` rebuilds the IVE with it
    t0 = time.monotonic()
    rep = {"schema": "prax-teach/build-report@1", "lesson": None, "lesson_sha256": None, "status": "draft",
           "started": _now(), "finished": None, "media": media, "entry": _entry(), "gates": [], "fallbacks": [],
           "tools": {}, "artifacts": [], "transitions": ["draft"], "error": None}
    build_dir = lesson.dir / "build"
    previous = _read_previous(lesson) if only else None  # `--only` merges it; a full build replaces it
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
        rep["cleared"] = clear_outputs(build_dir, media)
        cap = c_runner.capture_lesson(lesson)
        model.validate(lesson, stage="captured")
        rep["lesson_sha256"] = lesson.sha256()
        rep["capture"] = {"programs": cap["programs"], "platform": cap["platform"]}
        go("captured")
        rep["tools"] = tool_versions()
        rep["gates"].append({"id": "values.expect", "medium": "all", "status": "passed",
                             "measured": values.check_expectations(lesson), "reason": ""})
        gates, degraded = _project_and_verify(lesson, build_dir, media, rep, go, video_theme, renderer)
        rep["gates"] += gates
        if only:
            rep.update(merge_previous(previous, rep, rebuilt=media, on_disk=media_on_disk(build_dir)))
            degraded = degraded or bool(rep["fallbacks"])
        items = claims_gate.collect_texts(lesson, build_dir)
        rep["gates"].append(claims_gate.mapping_gate(lesson, items))
        jobs = claims_gate.write_jobs(lesson, items, build_dir, calibrate=calibrate)
        mode = "calibrate" if calibrate else "canary"
        rep["claims"] = {"mode": mode, "jobs": [str(build_dir / "claims-jobs" / f"{j}.json") for j in jobs],
                         "reviews_dir": str(build_dir / "claims-review"), "rubric": str(claims_gate.RUBRIC),
                         "job_tokens": claims_gate.job_sizes(build_dir),
                         "next": "run each job in a separate subagent with only the job file and the rubric, then `ptk claims check`"}
        rep["gates"].append({"id": "claims.review", "medium": "all", "status": "pending", "measured": {},
                             "reason": "waiting for reviewer subagents"})
        if mode == "canary":
            rep["gates"].append({"id": "claims.canary", "medium": "all", "status": "pending", "measured": {},
                                 "reason": "waiting for reviewer subagents (one planted error must be caught, D21.1)"})
        elif claims_gate.mutation_count(build_dir):
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


def _project_and_verify(lesson, build_dir, media, rep, go, video_theme=None, renderer="hyperframes"):
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
        v = video.project(lesson, out, theme=video_theme, renderer=renderer)
        timing = v["timing"]
        rep["video"] = {"theme": timing["theme"], "renderer": timing["renderer"]}
        if v["degraded"]:
            degraded = True
            rep["fallbacks"].append({"what": "tts", "engine": v["tts"]["engine"]})
        rep["tts"] = {k: val for k, val in v["tts"].items() if k != "segments"}
        tmp = host.make_tmp("canary-")
        canaries = isolation.run_canaries(v["composition"], tmp)
        chk = v["renderer"].check(lesson, v["composition"])
        projected["video"] = (out, v, canaries, chk)
    from .project import cards, explorer, qa  # WP4
    for name, mod in (("explorer", explorer), ("qa", qa), ("cards", cards)):
        if name in media:
            projected[name] = mod.project(lesson, build_dir / name)
    go("projected")
    if "explorer" in projected:
        gates += explorer.gates(lesson, build_dir / "explorer", build_dir / "shots")
    if "qa" in projected:
        gates += qa.gates(lesson, build_dir / "qa", build_dir / "shots")
    if "cards" in projected:
        gates.append(cards.gate(lesson, projected["cards"]))
    if "still" in projected:
        out, svgs = projected["still"]
        gates.append(values.gate(lesson, "still", [("svg", out / s) for s in svgs]))
        gates += visual.still_gates(lesson, out, svgs)
    if "video" in projected:
        out, v, canaries, chk = projected["video"]
        per_scene = chk["scenes"] == len(timing["scenes"])
        gates.append({"id": "video.hyperframes-check", "medium": "video",
                      "status": "passed" if chk["clean"] and per_scene else "failed",
                      "measured": {"exit": chk["exit"], "counts": chk["counts"], "sandboxed": True,
                                   "sub_compositions": chk["scenes"], "scenes": len(timing["scenes"])},
                      "reason": chk["reason"] if not chk["clean"] else ("" if per_scene else
                                                                         "not one sub-composition per scene")})
        if v["renderer"].frame_probe():
            gates.append(frames.scene_layout_gate(lesson, out, timing, lesson.sha256()))
            gates.append(frames.morph_gate(lesson, out, timing, lesson.sha256()))
        else:
            for gid in ("video.scene-layout", "video.morph-stable"):
                gates.append({"id": gid, "medium": "video", "status": "not-run", "measured": {},
                              "reason": f"renderer {v['renderer'].name} has no frame probe"})
        render_ok, log = True, ""
        try:
            mp4, log = video.finish(lesson, out, v["composition"], v["renderer"])
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
    changed = [a["path"] for a in rep.get("artifacts", []) if not (build_dir / a["path"]).is_file()
               or host.sha256_file(build_dir / a["path"]) != a["sha256"]]
    rep["gates"] = [g for g in rep["gates"] if g["id"] != "claims.artifacts-unchanged"]
    rep["gates"].append({"id": "claims.artifacts-unchanged", "medium": "all", "status": "failed" if changed else "passed",
                         "measured": {"checked": len(rep.get("artifacts", [])), "changed": changed[:20]},
                         "reason": "artifacts changed after the build; rebuild" if changed else ""})  # review P3-12
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
