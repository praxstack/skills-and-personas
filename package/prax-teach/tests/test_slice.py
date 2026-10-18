"""AC-0.4 (agent-mediated) and AC-0.5: the switch-fallthrough slice."""
import json
import os
import shutil
from pathlib import Path

from _util import SLICE, gate, ptk_cmd, report
from selftest_support import AgentPending
from ptk import build, host, model
from ptk.verify import claims

REQUIRED_GATES = {"values.expect", "values.still", "visual.still.layout", "visual.still.contrast", "visual.still.ocr",
                  "visual.still.fonts", "visual.still.alt-source", "visual.still.network", "video.hyperframes-check",
                  "video.render-isolation", "values.video", "video.media", "video.sync", "video.no-answer-leak",
                  "values.ive", "ive.pause-state", "ive.no-answer-leak", "ive.controls", "ive.layout", "ive.fonts",
                  "ive.network", "claims.mapping", "claims.review", "claims.sensitivity"}


def _reviews_current(rep):
    lesson = model.load(SLICE)
    items = claims.collect_texts(lesson, SLICE / "build")
    _m, cur = claims.manifest_for(claims._job_body(lesson, items))
    g = gate(rep, "claims.review")
    return g and g["status"] == "passed" and g["measured"].get("current_manifest_sha256") == cur


def test_switch_fallthrough_slice():
    """Build with --only still,video,ive; after the reviewer subagents, the report is verified with no not-run gate.
    If reviews are missing or stale, (re)build, leave the jobs and stop at claims-pending (exit 4)."""
    rep = report()
    if not rep or rep["status"] == "claims-pending" or not _reviews_current(rep):
        res = host.run([*ptk_cmd(), "build", str(SLICE), "--only", "still,video,ive"], timeout=3600)
        assert res.code == 4, f"build should stop at claims-pending (4), got {res.code}: {res.stdout[-1500:]}"
        jobs = json.loads(res.stdout)["claims_jobs"]
        raise AgentPending(f"run each job in a separate subagent, then `ptk claims check {SLICE}`: {jobs}")
    assert rep["status"] == "verified", rep["status"]
    statuses = {g["id"]: g["status"] for g in rep["gates"]}
    assert REQUIRED_GATES <= set(statuses), REQUIRED_GATES - set(statuses)
    assert all(s == "passed" for s in statuses.values()), {k: v for k, v in statuses.items() if v != "passed"}
    assert not rep["fallbacks"]
    assert rep["media"] == ["still", "video", "ive"]
    m = gate(rep, "video.media")["measured"]
    assert abs(m["integrated_lufs"] + 16) <= 1 and m["true_peak_dbtp"] <= -1
    s = gate(rep, "video.sync")["measured"]
    assert s["max_abs_start_delta"] <= 0.5 and s["max_abs_end_delta"] <= 0.5 and s["non_code_wer"] <= 0.10
    sens = gate(rep, "claims.sensitivity")["measured"]
    assert sens["caught"] == sens["mutations"] >= 1
    b = SLICE / "build"
    for p in ("still/switch-fallthrough-wide-light.png", "video/lesson.mp4", "video/captions.vtt",
              "video/chapters.vtt", "ive/index.html", "ive/states.vtt"):
        assert (b / p).exists(), p
    return {"status": rep["status"], "gates": len(statuses)}


test_switch_fallthrough_slice.agent = True


def test_entry_by_direct_path():
    """AC-0.5: the slice came from package/prax-teach/SKILL.md by direct path, with ptk on PATH,
    and no host has the candidate registered (D19.3)."""
    skill = host.PKG / "SKILL.md"
    text = skill.read_text()
    assert len(text) / 4 <= 4000, "SKILL.md over the 4k-token loader budget"
    for cmd in ("ptk validate", "ptk build", "--only", "ptk claims check", "ptk report"):
        assert cmd in text, f"SKILL.md does not tell the agent to run {cmd!r}"
    env = dict(os.environ, PATH=f"{host.PKG / 'bin'}{os.pathsep}{os.environ['PATH']}")
    found = shutil.which("ptk", path=env["PATH"])
    assert found and Path(found).resolve() == (host.PKG / "bin" / "ptk").resolve(), found
    res = host.run(["ptk", "report", str(SLICE), "--json"], env=host.child_env({"PATH": env["PATH"]}), timeout=120)
    rep = json.loads(res.stdout)
    assert rep["entry"]["skill_md"] == str(skill)
    assert rep["entry"]["ptk"] == str(host.PKG / "bin" / "ptk")
    assert rep["lesson"] == "switch-fallthrough" and rep["media"] == ["still", "video", "ive"]
    home = Path.home()
    pkg = host.PKG.resolve()
    hits = []
    for d in (home / ".claude" / "skills", home / ".agents" / "skills", home / ".codex" / "skills",
              home / ".hermes" / "skills", home / ".config" / "opencode" / "skills", home / ".cursor" / "skills"):
        if not d.is_dir():
            continue
        for e in d.iterdir():
            target = e.resolve() if e.is_symlink() or e.is_dir() else e
            if e.name in ("prax-teach-v2.1", "prax-teach") or str(target).startswith(str(pkg)):
                if str(target).startswith(str(pkg)) or e.name == "prax-teach-v2.1":
                    hits.append(str(e))
    assert not hits, f"candidate registered with a host: {hits}"
    return {"skill_md": str(skill), "skill_md_chars": len(text), "ptk": found, "registered": hits}
