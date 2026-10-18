"""AC-7.1 to AC-7.4: claims jobs and manifests, stale reviews, whole-sentence mapping, invalid reviews."""
import copy
import hashlib
import json
from pathlib import Path

from _claims_agent import fcast_lesson, slice_lesson
from ptk import host, model
from ptk.verify import claims

HINTS = ("why_false", "planted", '"role"', '"mutation"', '"control"', '"family"', "auto.value", '"expect": "reject"')
JOB_KEYS = {"schema", "job_id", "rubric_version", "rubric_path", "review_path", "instructions", "lesson", "platform",
            "programs", "facts", "claims", "misconceptions", "questions", "trace", "teaching_texts", "inputs",
            "manifest", "manifest_sha256"}


def _tmp_build(prefix):
    return host.make_tmp(f"claims-{prefix}-")


def _review(job, verdict="accept", rubric=None, manifest=None):
    return {"schema": "prax-teach/claims-review@1", "job_id": job["job_id"],
            "manifest_sha256": manifest or job["manifest_sha256"], "rubric_version": rubric or job["rubric_version"],
            "reviewer": {"host": "test", "agent": "synthetic"},
            "claims": [{"id": c["id"], "verdict": verdict, "reason": "synthetic"} for c in job["claims"]],
            "texts": [{"id": t["id"], "verdict": verdict, "reason": "synthetic"} for t in job["teaching_texts"]],
            "overall": verdict}


def _jobs(build):
    return {p.stem: json.loads(p.read_text()) for p in sorted((build / "claims-jobs").glob("*.json"))}


def _write_review(build, job, review):
    (build / "claims-review" / f"{job['job_id']}.json").write_text(
        review if isinstance(review, str) else json.dumps(review))


def _gate(lesson, items, build, gid="claims.review"):
    return next(g for g in claims.check(lesson, build, items) if g["id"] == gid)


# ---------------------------------------------------------------- AC-7.1

def test_jobs_and_manifest():
    """One lesson job, up to 12 mutation jobs each paired with a control; each job carries a manifest of the model,
    every artifact text, the sources and the rubric version; the roles never appear in the job files; only
    teaching sentences are sent, and a job (plus rubric) stays under 30k tokens."""
    out = {}
    sets = {"f-cast": fcast_lesson()}
    if slice_lesson():
        sets["switch-fallthrough"] = slice_lesson()
    for name, (lesson, items) in sets.items():
        build = _tmp_build(name)
        ids = claims.write_jobs(lesson, items, build)
        priv = claims.load_private(build)
        roles = [priv["jobs"][j]["role"] for j in ids]
        n_mut = roles.count("mutation")
        assert roles.count("lesson") == 1 and roles.count("control") == n_mut and 1 <= n_mut <= 12, roles
        jobs = _jobs(build)
        assert set(jobs) == set(ids) and len(set(ids)) == len(ids)
        assert not claims.private_path(build).is_relative_to(build) and not claims.private_path(build).is_relative_to(
            lesson.dir), "the role map must live outside the lesson and build trees"
        assert sorted(p.name for p in (build / "claims-jobs").iterdir()) == sorted(f"{j}.json" for j in ids)
        lesson_body = None
        for jid, job in jobs.items():
            m = job["manifest"]
            for k in ("model_sha256", "body_sha256", "artifact_texts_sha256", "sources_sha256", "rubric_version",
                      "rubric_sha256", "slot"):
                assert k in m, (jid, k)
            assert m["model_sha256"] == lesson.sha256()
            assert m["rubric_version"] == claims.RUBRIC_VERSION == "2"
            assert m["rubric_sha256"] == hashlib.sha256(claims.RUBRIC.read_bytes()).hexdigest()
            assert job["manifest_sha256"] == hashlib.sha256(model.canonical(m).encode()).hexdigest()
            assert jid == "job-" + job["manifest_sha256"][:10]
            assert set(job) == JOB_KEYS, set(job) ^ JOB_KEYS
            raw = json.dumps(job)
            leaks = [h for h in HINTS if h in raw]
            assert not leaks, f"{jid} names its role: {leaks}"
            assert {t["source"] for t in job["teaching_texts"]} <= {"claim", "alt", "narration", "question", "option",
                                                                    "trace", "projector", "misconception", "template",
                                                                    "title", "scene-title"}
            body = {k: v for k, v in job.items() if k not in ("job_id", "review_path", "manifest", "manifest_sha256")}
            if priv["jobs"][jid]["role"] == "lesson":
                lesson_body = body
        for jid, job in jobs.items():
            body = {k: v for k, v in job.items() if k not in ("job_id", "review_path", "manifest", "manifest_sha256")}
            same = body == lesson_body
            assert same == (priv["jobs"][jid]["role"] != "mutation"), (jid, priv["jobs"][jid]["role"])
        sizes = claims.job_sizes(build)
        assert max(s["with_rubric"] for s in sizes.values()) < 30_000, sizes
        out[name] = {"jobs": len(ids), "mutations": n_mut,
                     "max_tokens_with_rubric": max(s["with_rubric"] for s in sizes.values()),
                     "teaching_texts": len(jobs[ids[0]]["teaching_texts"]),
                     "not_sent": jobs[ids[0]]["inputs"]["not_sent"]["count"]}
    return out


# ---------------------------------------------------------------- AC-7.2

def test_stale_review_rejected():
    """Replaying a passing review after the content changed is rejected: an edited claim, an edited artifact text,
    an edited rubric, and a review that echoes another manifest."""
    lesson, items = fcast_lesson()
    build = _tmp_build("stale")
    claims.write_jobs(lesson, items, build, mutations=[])
    job = next(iter(_jobs(build).values()))
    _write_review(build, job, _review(job))
    assert _gate(lesson, items, build)["status"] == "passed"
    out = {}
    # 1. the model changes (one claim's wording)
    edited = type(lesson)(lesson.path, copy.deepcopy(lesson.data))
    edited.data["claims"][0]["text"] += " Then it returns 0."
    g = _gate(edited, items, build)
    assert g["status"] == "failed" and g["measured"]["stale"], g
    out["model"] = g["measured"]["stale"][0]["reason"]
    # 2. an artifact text changes (a projector edits a narration line)
    items2 = copy.deepcopy(items)
    items2[0]["text"] += " Really."
    g = _gate(lesson, items2, build)
    assert g["status"] == "failed" and g["measured"]["stale"], g
    # 3. a non-teaching text changes: still bound by hash although not sent
    items3 = copy.deepcopy(items) + [{"id": "t.999", "kind": "code", "ref": "", "text": "return 0;", "where": ["x"],
                                      "maps_to": []}]
    g = _gate(lesson, items3, build)
    assert g["status"] == "failed" and g["measured"]["stale"], g
    # 4. the rubric changes
    saved = claims.RUBRIC
    alt = _tmp_build("rubric") / "rubric.md"
    alt.write_text(saved.read_text() + "\nOne more rule.\n")
    claims.RUBRIC = alt
    try:
        g = _gate(lesson, items, build)
    finally:
        claims.RUBRIC = saved
    assert g["status"] == "failed" and g["measured"]["stale"], g
    # 5. a review that echoes a different manifest
    _write_review(build, job, _review(job, manifest="0" * 64))
    g = _gate(lesson, items, build)
    assert g["status"] == "failed" and "different manifest" in g["measured"]["stale"][0]["reason"], g
    out["cases"] = 5
    return out


def test_v1_review_rejected_for_v2_job():
    """A rubric v1 review can never satisfy a v2 job: by its version field, and by the manifest, which binds the
    rubric's sha256 (a v1 review echoes a manifest computed with the v1 rubric)."""
    lesson, items = fcast_lesson()
    build = _tmp_build("v1")
    claims.write_jobs(lesson, items, build, mutations=[])
    job = next(iter(_jobs(build).values()))
    _write_review(build, job, _review(job, rubric="1"))
    g = _gate(lesson, items, build)
    assert g["status"] == "failed" and "rubric v1" in g["measured"]["stale"][0]["reason"], g
    v1 = dict(job["manifest"], rubric_version="1",
              rubric_sha256=hashlib.sha256(b"# Claims review rubric, version 1\n").hexdigest())
    v1_sha = hashlib.sha256(model.canonical(v1).encode()).hexdigest()
    _write_review(build, job, _review(job, rubric="1", manifest=v1_sha))
    g = _gate(lesson, items, build)
    assert g["status"] == "failed" and g["measured"]["stale"], g
    return {"rejected": [s["reason"] for s in g["measured"]["stale"]]}


# ---------------------------------------------------------------- AC-7.3

def _map(lesson, kind, ref, t):
    return claims.map_item(lesson, {"kind": kind, "ref": ref, "text": t, "where": ["test"]})


def test_unmapped_sentence():
    """Every teaching sentence maps to a whole claim or narration sentence, or a typed chrome.json string.
    Fragments, dropped words, untagged text and wrong slot values fail with ClaimsUnmapped."""
    lesson, items = fcast_lesson()
    g = claims.mapping_gate(lesson, items)
    assert g["status"] == "passed", g["measured"]["unmapped"]
    out = {"f-cast": g["measured"]["texts"]}
    s = slice_lesson()
    if s:
        g = claims.mapping_gate(*s)
        assert g["status"] == "passed", g["measured"]["unmapped"][:5]
        out["switch-fallthrough"] = {"texts": g["measured"]["texts"], "teaching": g["measured"]["teaching"]}
    cast = lesson.claim("c.cast")["text"]
    bad = [
        ("claim", "c.cast", cast.split(", so ")[0] + "."),                  # a fragment of the claim
        ("claim", "c.cast", cast.replace("converts", "does not convert")),  # a word changed
        ("claim", "c.cast", cast + " It always works."),                    # a sentence added
        ("alt", "", "The cast converts the value."),                       # alt text that is no claim sentence
        ("narration", "sc4.0", "The cast reads the bits."),                 # caption that is not the narration line
        ("chrome", "captions_on", "Captions"),                            # a substring of a chrome string
        ("chrome", "source_link", "Source: programs/other.c"),             # a typed slot with a wrong value
        ("chrome", "kicker", "C · undefined behaviour"),                    # {topic} must be this lesson's topic
        ("fact", "f.f", "66.0"),                                           # a fact shown with another value
        ("unmapped", "", "Casts are free."),                               # untagged text
        ("projector", "c.cast", "A cast is free at run time."),           # a projector sentence no claim says
        ("chrome-claim", "x_unknown|c.cast", "Anything at all."),         # a template that isn't in chrome.json
    ]
    for kind, ref, t in bad:
        maps, problem = _map(lesson, kind, ref, t)
        assert problem, f"{kind} {t!r} should be unmapped"
    good = [("claim", "c.cast", cast), ("projector", "c.cast", cast), ("fact", "f.f", "66.000000"),
            ("chrome", "kicker", "C · PRINTF CONVERSIONS"), ("chrome", "source_link", "Source: lessons/f-cast/programs/ fcast.c"),
            ("narration", "sc4.0", cast)]
    for kind, ref, t in good:
        maps, problem = _map(lesson, kind, ref, t)
        assert not problem, (kind, t, problem)
    probe = items + [{"id": "t.999", "kind": "claim", "ref": "c.cast", "text": cast.split(", so ")[0] + ".",
                      "where": ["still"]}]
    g = claims.mapping_gate(lesson, probe)
    assert g["status"] == "failed" and g["reason"] == "ClaimsUnmapped" and len(g["measured"]["unmapped"]) == 1
    out["rejected_cases"] = len(bad)
    return out


# ---------------------------------------------------------------- AC-7.4

BAD_REVIEWS = {
    "empty": "",
    "refusal": "I'm sorry, but I can't help with reviewing this content.",
    "not-an-object": "[]",
    "missing-keys": json.dumps({"schema": "prax-teach/claims-review@1", "overall": "accept"}),
}


def _bad_variants(job):
    partial = _review(job)
    partial["texts"] = partial["texts"][:-1]
    incoherent = _review(job)
    incoherent["claims"][0]["verdict"] = "reject"
    empty_lists = _review(job)
    empty_lists["claims"], empty_lists["texts"] = [], []
    return dict(BAD_REVIEWS, **{"partial-coverage": json.dumps(partial), "overall-mismatch": json.dumps(incoherent),
                                "empty-verdicts": json.dumps(empty_lists)})


def test_invalid_reviews():
    """A malformed, empty or refusal review gets one retry with a schema reminder (claims-pending), then fails
    with ClaimsReviewInvalid. A valid review on the retry passes."""
    lesson, items = fcast_lesson()
    out = {}
    probe_build = _tmp_build("inv-probe")
    claims.write_jobs(lesson, items, probe_build, mutations=[])
    for name, raw in _bad_variants(next(iter(_jobs(probe_build).values()))).items():
        build = _tmp_build(f"inv-{name}")
        claims.write_jobs(lesson, items, build, mutations=[])
        job = next(iter(_jobs(build).values()))
        _write_review(build, job, raw)
        g = _gate(lesson, items, build)
        assert g["status"] == "pending" and g["measured"]["retrying"], (name, g["status"], g["reason"])
        job2 = json.loads((build / "claims-jobs" / f"{job['job_id']}.json").read_text())
        assert job2["retry"]["attempt"] == 2 and "exactly once" in job2["retry"]["schema_reminder"], name
        assert job2["manifest_sha256"] == job["manifest_sha256"]
        assert (build / "claims-review" / "invalid" / f"{job['job_id']}.attempt1.json").exists()
        assert not (build / "claims-review" / f"{job['job_id']}.json").exists()
        _write_review(build, job, raw)
        g = _gate(lesson, items, build)
        assert g["status"] == "failed" and g["reason"] == "ClaimsReviewInvalid", (name, g)
        out[name] = g["measured"]["invalid"][0]["errors"][0][:60]
    build = _tmp_build("inv-recover")
    claims.write_jobs(lesson, items, build, mutations=[])
    job = next(iter(_jobs(build).values()))
    _write_review(build, job, "")
    assert _gate(lesson, items, build)["status"] == "pending"
    _write_review(build, job, _review(job))
    g = _gate(lesson, items, build)
    assert g["status"] == "passed", g
    out["recovered_after_retry"] = True
    return out


def test_build_report_status_after_retry():
    """The retry keeps the build at claims-pending (exit 4), never verified or failed."""
    from ptk import build as b
    gates = [{"id": "values.expect", "status": "passed"}, {"id": "claims.review", "status": "pending"}]
    assert b.final_status(gates, degraded=False) == "claims-pending"
    return {"status": "claims-pending"}


def test_private_map_not_in_reviewer_reach():
    """Review P2-2: the role map is under $PTK_STATE, keyed by the build path, not beside the jobs."""
    lesson, items = fcast_lesson()
    build = _tmp_build("priv")
    claims.write_jobs(lesson, items, build)
    p = claims.private_path(build)
    assert p.exists() and p.is_relative_to(host.state_dir() / "claims-private")
    assert not any(Path(build).rglob("*private*"))
    return {"private": str(p)}
