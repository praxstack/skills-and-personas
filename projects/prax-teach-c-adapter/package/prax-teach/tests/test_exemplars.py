"""WP9: the exemplar lessons (AC-9.1 to AC-9.4).

The three exemplar tests are agent tests: each needs a full six-media build and the full claims suite of reviewer subagents (the
lesson job, the mutation jobs and their controls, AC-7.1). When the report is not a current `verified` build they rebuild, leave the claims
jobs and stop at claims-pending (AgentPending), like test_slice. test_design_verdicts_recorded is automatic: it
checks the recorded screenshot review (ptk design record) against the current build.
"""
import json

from _util import V21, gate
from selftest_support import AgentPending, NotRun
from ptk import design, expect, host, model
from ptk.project import mech
from ptk.verify import claims

LESSONS = {"one-byte-four-views": "AC-9.1", "factorial-stack": "AC-9.2", "neuron": "AC-9.4"}
SIX = {"still", "explorer", "qa", "cards", "video", "ive"}


def _dir(slug):
    return V21 / "lessons" / slug


def _report(slug):
    p = _dir(slug) / "build" / "build-report.json"
    return json.loads(p.read_text()) if p.exists() else None


def _reviews_current(slug, rep):
    lesson = model.load(_dir(slug))
    items = claims.collect_texts(lesson, _dir(slug) / "build")
    claims.mapping_gate(lesson, items)
    _m, cur = claims.manifest_for(claims._job_body(lesson, items))
    g = gate(rep, "claims.review")
    return bool(g) and g["status"] == "passed" and g["measured"].get("current_manifest_sha256") == cur


def _verified(slug):
    """The current report, after checking it is a verified six-media build whose reviews match the lesson."""
    rep = _report(slug)
    lesson = model.load(_dir(slug))
    if not rep or rep.get("lesson_sha256") != lesson.sha256() or rep["status"] == "claims-pending" \
            or not _reviews_current(slug, rep):
        res = host.run([str(host.PKG / "bin" / "ptk"), "build", str(_dir(slug))], timeout=3600)
        assert res.code == 4, f"build should stop at claims-pending (4), got {res.code}: {res.stdout[-1500:]}"
        jobs = json.loads(res.stdout)["claims_jobs"]
        raise AgentPending(f"run each job in a separate subagent, then `ptk claims check {_dir(slug)}`: {jobs}")
    assert rep["status"] == "verified", rep["status"]
    assert SIX <= set(rep["media"]), rep["media"]
    statuses = {g["id"]: g["status"] for g in rep["gates"]}
    assert all(s == "passed" for s in statuses.values()), {k: v for k, v in statuses.items() if v != "passed"}
    assert not rep["fallbacks"]
    sens = gate(rep, "claims.sensitivity")["measured"]  # the full suite (AC-7.1, D22.1), not a canary
    assert sens["mutations"] >= 1 and sens["meets_thresholds"], sens
    for f in lesson.data["facts"]:  # every fact independent of the run that captured it
        assert "fn" in f["expect"] or f["expect"].get("reviewed"), f["id"]
    assert len([f for f in lesson.data["facts"] if "fn" in f["expect"]]) == len(lesson.data["facts"]), \
        "an exemplar computes every expectation (no reviewed literals)"
    for p in ("video/lesson.mp4", "ive/index.html", "explorer/index.html", "qa/index.html", f"cards/{slug}.apkg",
              f"still/{slug}-wide-dark.png"):
        assert (_dir(slug) / "build" / p).exists(), p
    return rep, lesson, statuses


def test_one_byte():
    """AC-9.1: int a = 66 through %d, %u, %f with a (double) cast and %c; the cast makes a new double and printf
    never reinterprets a's bits (m.samebits and its correction); the UB program compiles and never runs."""
    rep, lesson, statuses = _verified("one-byte-four-views")
    facts = {f["id"]: f for f in lesson.data["facts"]}
    assert facts["f.f"]["value"] == "66.000000" == expect.printf_f(66)
    assert facts["f.dbits"]["value"] == expect.double_bits_hex(66) != facts["f.hex"]["value"]
    mis = {m["id"]: m for m in lesson.data["misconceptions"]}
    assert "m.samebits" in mis and lesson.claim(mis["m.samebits"]["correction"])
    texts = " ".join(c["text"] for c in lesson.data["claims"]).lower()
    assert "never changes the bits" not in texts and "same bits" not in texts.replace("not the bits", "")
    cast = lesson.claim("c.cast")["text"]
    assert "converts" in cast and "not the bits of a" in cast, cast
    ub = next(p for p in lesson.data["programs"] if p["ub"])
    assert ub["run"] is False and rep["capture"]["programs"][ub["id"]]["ran"] is False
    assert any(c["kind"] == "undefined-behaviour" and ub["id"] in c.get("programs", []) for c in lesson.data["claims"])
    assert "format specifies type 'double'" in ub["diagnostics"]["clang"]
    q = next(sc["question"] for sc in lesson.data["storyboard"] if sc.get("question"))
    assert any(o.get("misconception") == "m.samebits" for o in q["options"])
    return {"gates": len(statuses), "status": rep["status"]}


test_one_byte.agent = True


def test_factorial_stack():
    """AC-9.2: frames pushed and popped with their return values, from an instrumented run; expectations from
    expect.factorial_events (no capture code); the stack grows to four frames and unwinds to main."""
    rep, lesson, statuses = _verified("factorial-stack")
    out = rep["capture"]
    lines = [f["value"] for f in sorted((f for f in lesson.data["facts"] if f["kind"] == "stdout-line"),
                                        key=lambda f: f["select"]["line"])]
    assert lines == expect.factorial_events(3), lines
    depths = [len(s["state"].get("frames", [])) for s in lesson.data["trace"]]
    assert depths == [2, 3, 4, 4, 3, 2, 1], depths
    rets = [fr for s in lesson.data["trace"] for fr in s["state"]["frames"] if fr.get("status") == "returning"]
    assert [lesson.fact(fr["ret"])["value"] for fr in rets] == ["1", "2", "6"]
    cues = json.loads((_dir("factorial-stack") / "build" / "ive" / "cues.json").read_text())
    assert any(c["state"].get("panel") for c in cues), "IVE cues carry the stack's values"
    assert "RETURNS" in (_dir("factorial-stack") / "build" / "ive" / "ive-data.js").read_text()  # returning frames drawn
    assert out["programs"]["p1"]["ran"] is True
    return {"gates": len(statuses), "depths": depths}


test_factorial_stack.agent = True


def test_neuron_unrelated_subject():
    """AC-9.4 (P1): the Neuron Atlas lesson (0.8, 0.4; 1.5, -1; bias -0.2; ReLU; output 0.6) builds through v2.1
    in all six media, as a non-C subject whose values still come from a captured C run."""
    rep, lesson, statuses = _verified("neuron")
    assert lesson.data.get("subject") and lesson.data["subject"] != "C"
    assert lesson.data["figure"]["panel"]["kind"] == "neuron"
    v = {f["id"]: f["value"] for f in lesson.data["facts"]}
    assert (v["f.x1"], v["f.x2"], v["f.w1"], v["f.w2"], v["f.b"]) == ("0.8", "0.4", "1.5", "-1", "-0.2")
    assert v["f.z"] == v["f.a"] == "0.6" == expect.neuron_relu([0.8, 0.4], [1.5, -1.0], -0.2)
    drawn = mech.svg_fragment(lesson, "s3", "wide", "dark")[1]
    assert {"f.t1", "f.t2", "f.b", "f.z", "f.a"} <= set(drawn), drawn
    return {"gates": len(statuses)}


test_neuron_unrelated_subject.agent = True


def test_design_verdicts_recorded():
    """AC-9.3: each exemplar's build report records verdicts for the six screenshot-reviewed aesthetics items,
    judged against the accepted Neuron Atlas still, bound to this build's lesson and screenshots."""
    out = {}
    for slug in LESSONS:
        rep = _report(slug)
        if not rep:
            raise NotRun(f"{slug} is not built")
        probs = design.problems(_dir(slug), rep)
        assert not probs, (slug, probs)
        d = rep["design_review"]
        assert "baseline" in d["reference"]["path"], d["reference"]
        out[slug] = {k: i["verdict"] for k, i in d["items"].items()}
    return out
