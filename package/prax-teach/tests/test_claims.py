"""AC-7.1 to AC-7.4: claims jobs and manifests, stale reviews, whole-sentence mapping, invalid reviews."""
import copy
import hashlib
import json
from pathlib import Path

from _claims_agent import fcast_lesson, slice_lesson
from _util import report
from ptk import host, model
from ptk.verify import claims

HINTS = ("why_false", "planted", '"role"', '"mutation"', '"control"', '"family"', "auto.value", '"expect": "reject"')
JOB_KEYS = {"schema", "job_id", "rubric_version", "rubric_path", "review_path", "instructions", "lesson", "platform",
            "programs", "facts", "claims", "misconceptions", "questions", "trace", "teaching_texts", "inputs",
            "manifest", "manifest_sha256", "source_passages", "scenes", "where_legend"}
LESSON_REVIEWERS = 3  # AC-7.8


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


def _first_job(build):
    """The first lesson job; the other two lesson jobs (AC-7.8) get an accepting review, so a test about one review
    sees only that review's effect."""
    jobs = _jobs(build)
    first = next(iter(jobs.values()))
    for job in list(jobs.values())[1:]:
        _write_review(build, job, _review(job))
    return first


def _gate(lesson, items, build, gid="claims.review"):
    return next(g for g in claims.check(lesson, build, items) if g["id"] == gid)


# ---------------------------------------------------------------- AC-7.1

def test_jobs_and_manifest():
    """AC-7.1 (spec v1.4): by default three lesson jobs (one per independent reviewer, AC-7.8), up to 12 mutation jobs
    each paired with a control; each job carries a manifest of the model, the stored source passages (AC-7.7),
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
        assert priv["mode"] == "full", priv.get("mode")
        roles = [priv["jobs"][j]["role"] for j in ids]
        n_mut = roles.count("mutation")
        assert roles.count("lesson") == LESSON_REVIEWERS and roles.count("control") == n_mut and 1 <= n_mut <= 12, roles
        jobs = _jobs(build)
        assert set(jobs) == set(ids) and len(set(ids)) == len(ids)
        assert not claims.private_path(build).is_relative_to(build) and not claims.private_path(build).is_relative_to(
            lesson.dir), "the role map must live outside the lesson and build trees"
        assert sorted(p.name for p in (build / "claims-jobs").iterdir()) == sorted(f"{j}.json" for j in ids)
        lesson_body = None
        for jid, job in jobs.items():
            m = job["manifest"]
            for k in ("model_sha256", "body_sha256", "artifact_texts_sha256", "sources_sha256", "source_excerpts",
                      "rubric_version", "rubric_sha256", "slot"):
                assert k in m, (jid, k)
            assert m["model_sha256"] == lesson.sha256()
            assert m["rubric_version"] == claims.RUBRIC_VERSION == "4"
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


def test_canary_jobs_only_when_asked():
    """D22.1: `--canary` (explicit, cheaper) writes the three lesson jobs (AC-7.8) plus exactly one canary mutation job
    and no controls. The canary is picked deterministically from the lesson's own mutations (same lesson, same canary),
    never names its role, and carries the same manifest fields as every other job. Without it the build writes
    the full suite (test_jobs_and_manifest)."""
    out = {}
    sets = {"f-cast": fcast_lesson()}
    if slice_lesson():
        sets["switch-fallthrough"] = slice_lesson()
    for name, (lesson, items) in sets.items():
        build = _tmp_build(f"canary-{name}")
        ids = claims.write_jobs(lesson, items, build, canary=True)
        priv = claims.load_private(build)
        assert priv["mode"] == "canary", priv.get("mode")
        roles = sorted(priv["jobs"][j]["role"] for j in ids)
        assert roles == ["lesson"] * LESSON_REVIEWERS + ["mutation"], roles
        canary = next(m for m in priv["jobs"].values() if m["role"] == "mutation")["mutation"]["id"]
        candidates = [m["id"] for m in claims.mc.select(lesson)]
        assert canary in candidates, (canary, candidates)
        again = _tmp_build(f"canary2-{name}")
        ids2 = claims.write_jobs(lesson, items, again, canary=True)
        assert sorted(ids2) == sorted(ids), "the canary must be the same for the same lesson"
        for jid, job in _jobs(build).items():
            assert set(job) == JOB_KEYS, set(job) ^ JOB_KEYS
            leaks = [h for h in HINTS if h in json.dumps(job)]
            assert not leaks, f"{jid} names its role: {leaks}"
        cal = _tmp_build(f"canary-cal-{name}")
        cal_ids = claims.write_jobs(lesson, items, cal)
        assert set(ids) <= set(cal_ids), "a canary job is the same job as its full-suite twin, so reviews carry over"
        out[name] = {"jobs": len(ids), "canary": canary, "candidates": len(candidates), "calibration_jobs": len(cal_ids)}
    return out


def test_canary_gate():
    """Canary mode: the lesson job accepted and the canary rejected (caught) passes claims.canary. A canary the
    reviewer accepts fails it; a missing canary review is not-run; the full suite reports claims.sensitivity."""
    lesson, items = fcast_lesson()
    out = {}
    for case in ("caught", "accepted", "missing"):
        build = _tmp_build(f"canary-gate-{case}")
        claims.write_jobs(lesson, items, build, canary=True)
        priv = claims.load_private(build)
        for jid, job in _jobs(build).items():
            meta = priv["jobs"][jid]
            if meta["role"] == "lesson":
                _write_review(build, job, _review(job))
            elif case == "caught":
                rev = _review(job)
                planted = meta["planted_claim"]
                if planted in {c["id"] for c in job["claims"]}:
                    for c in rev["claims"]:
                        if c["id"] == planted:
                            c.update(verdict="reject", reason="planted error")
                else:
                    for t in rev["texts"]:
                        if t["id"] in meta["changed_texts"]:
                            t.update(verdict="reject", reason="planted error")
                rev["overall"] = "reject"
                _write_review(build, job, rev)
            elif case == "accepted":
                _write_review(build, job, _review(job))
        gates = {g["id"]: g for g in claims.check(lesson, build, items)}
        assert "claims.sensitivity" not in gates, "canary mode must not report calibration rates"
        assert gates["claims.review"]["status"] == ("not-run" if case == "missing" else "passed"), gates["claims.review"]
        want = {"caught": "passed", "accepted": "failed", "missing": "not-run"}[case]
        assert gates["claims.canary"]["status"] == want, (case, gates["claims.canary"])
        out[case] = gates["claims.canary"]["status"]
    build = _tmp_build("canary-gate-cal")
    claims.write_jobs(lesson, items, build)
    gates = {g["id"] for g in claims.check(lesson, build, items)}
    assert "claims.sensitivity" in gates and "claims.canary" not in gates, gates
    return out


def test_build_cli_canary_flag():
    """D22.1: `ptk build` writes the full suite by default; `--canary` is the explicit cheaper mode. `--calibrate`
    (D21.1, withdrawn) is gone."""
    from ptk import cli
    try:
        parsed = cli.parser().parse_args(["build", "x", "--canary"])
    except SystemExit as e:
        raise AssertionError("ptk build does not accept --canary") from e
    assert parsed.canary is True
    assert cli.parser().parse_args(["build", "x"]).canary is False
    import inspect
    from ptk import build as b
    params = inspect.signature(b.build).parameters
    assert params["canary"].default is False and "calibrate" not in params, list(params)
    try:
        cli.parser().parse_args(["build", "x", "--calibrate"])
    except SystemExit:
        return {"flag": "--canary"}
    raise AssertionError("--calibrate (D21.1) must be withdrawn")


def test_canary_build_never_verified():
    """D22.1: with every gate passed, a canary-mode build is at best `canary-verified` (exit 6), never `verified`;
    a full-suite build with the same gates is `verified`. The report schema refuses a `verified` canary report."""
    import jsonschema
    from ptk import build as b
    from ptk import model as m
    gates = [{"id": "claims.review", "medium": "all", "status": "passed", "measured": {}},
             {"id": "claims.canary", "medium": "all", "status": "passed", "measured": {}}]
    assert b.final_status(gates, False, mode="canary") == "canary-verified"
    assert b.final_status(gates, False, mode="full") == "verified"
    assert b.final_status(gates, False) == "verified"
    assert b.final_status(gates, True, mode="canary") == "degraded"
    assert m.advance("claims-pending", "canary-verified") == "canary-verified"
    rep = {"schema": "prax-teach/build-report@1", "status": "canary-verified", "started": "x", "media": [],
           "gates": gates, "fallbacks": [], "tools": {}, "artifacts": [], "transitions": [],
           "claims": {"mode": "canary"}}
    assert b.exit_code(rep) == 6, b.exit_code(rep)
    schema = json.loads(b.REPORT_SCHEMA.read_text())
    jsonschema.Draft202012Validator(schema).validate(rep)
    bad = dict(rep, status="verified")
    try:
        jsonschema.Draft202012Validator(schema).validate(bad)
    except jsonschema.ValidationError:
        return {"canary": "canary-verified", "full": "verified"}
    raise AssertionError("the report schema accepted a verified canary-mode report")


# ---------------------------------------------------------------- AC-7.2

def test_stale_review_rejected():
    """Replaying a passing review after the content changed is rejected: an edited claim, an edited artifact text,
    an edited rubric, and a review that echoes another manifest."""
    lesson, items = fcast_lesson()
    build = _tmp_build("stale")
    claims.write_jobs(lesson, items, build, mutations=[])
    job = _first_job(build)
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
    job = _first_job(build)
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
    rep = report()
    if s and rep and rep.get("lesson_sha256") == s[0].sha256():
        g = claims.mapping_gate(*s)
        assert g["status"] == "passed", g["measured"]["unmapped"][:5]
        out["switch-fallthrough"] = {"texts": g["measured"]["texts"], "teaching": g["measured"]["teaching"]}
    else:
        out["switch-fallthrough"] = "skipped: the slice build is older than lesson.json"
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
        job = _first_job(build)
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
    job = _first_job(build)
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


# ---------------------------------------------------------------- AC-7.7

def _fixture_copy(prefix):
    """A throwaway copy of the f-cast fixture (lesson.json, programs, mutations.json, sources) and its lesson."""
    import shutil
    from _claims_agent import F_CAST, _fixture
    d = _tmp_build(prefix) / "f-cast"
    shutil.copytree(F_CAST, d)
    return d, _fixture(d)


def _expect_missing(lesson, why):
    from ptk import errors
    try:
        claims.check_source_excerpts(lesson)
    except errors.SourceExcerptMissing as e:
        assert e.detail.get("problems"), e.detail
        return e.detail["problems"]
    raise AssertionError(f"no SourceExcerptMissing when {why}")


def test_source_excerpts_bound():
    """AC-7.7: every claim source that cites an outside document (a C17 clause, a book section, a manual page) points
    at a passage stored under the lesson's sources/; each passage records its document, clause and where its text
    was taken from; every quote is found in its stored passage. Jobs carry the passage text and the manifest binds each
    passage's sha256, so an edited passage makes the review stale. A missing passage, a source with none, a quote the
    passage doesn't contain, or an unstored passage in a planted citation fails with SourceExcerptMissing, and
    `ptk build` stops on it before capture."""
    from ptk import build as b
    from ptk import errors
    out = {}
    lessons = {"f-cast": fcast_lesson()[0]}
    for d in sorted((host.PKG.parent.parent / "lessons").glob("*/lesson.json")):
        lessons[d.parent.name] = model.load(d.parent)
    for name, lesson in lessons.items():
        refs = claims.check_source_excerpts(lesson)
        assert refs, f"{name}: no stored source passages"
        for rel in refs:
            ex = claims.read_excerpt(lesson.dir, rel)
            for k in ("document", "clause", "taken_from"):
                assert ex["header"].get(k), (name, rel, k)
            assert ex["text"].strip() and ex["sha256"] == hashlib.sha256((lesson.dir / rel).read_bytes()).hexdigest()
        out[name] = len(refs)
    # the rc1 reviewer drift came from sources quoted from memory; the stored passages hold the real wording
    pinned = {("switch-fallthrough", "c.bodyend"): "Except as indicated, statements are executed in sequence",
              ("neuron", "c.mul"): "the conversion is with style f (or F) and precision P − (X + 1)"}
    for (name, cid), words in pinned.items():
        if name not in lessons:
            continue
        lesson = lessons[name]
        texts = [claims.read_excerpt(lesson.dir, r)["text"] for s in lesson.claim(cid)["sources"] for r in s.get("excerpts", [])]
        assert any(claims._squash_quote(words) in claims._squash_quote(t) for t in texts), (name, cid)
    # the job carries the passages and the manifest binds them
    lesson, items = fcast_lesson()
    build = _tmp_build("excerpts")
    claims.write_jobs(lesson, items, build)
    for jid, job in _jobs(build).items():
        cited = {r for c in job["claims"] for s in c["sources"] for r in s.get("excerpts", [])}
        assert cited and cited <= set(job["source_passages"]), (jid, cited - set(job["source_passages"]))
        for rel, p in job["source_passages"].items():
            ex = claims.read_excerpt(lesson.dir, rel)
            assert p["text"] == ex["text"] and p["sha256"] == ex["sha256"] and p["document"] == ex["header"]["document"]
            assert job["manifest"]["source_excerpts"][rel] == ex["sha256"], (jid, rel)
    # an edited passage makes a passing review stale
    d, copy_lesson = _fixture_copy("excerpt-stale")
    cbuild = _tmp_build("excerpt-stale-build")
    claims.write_jobs(copy_lesson, items, cbuild, mutations=[])
    for job in _jobs(cbuild).values():
        _write_review(cbuild, job, _review(job))
    assert _gate(copy_lesson, items, cbuild)["status"] == "passed"
    rel = sorted(claims.check_source_excerpts(copy_lesson))[0]
    (d / rel).write_text((d / rel).read_text() + "One more sentence.\n")
    g = _gate(copy_lesson, items, cbuild)
    assert g["status"] == "failed" and g["measured"]["stale"], g
    # four ways to lose a cited passage
    cases = {}
    d, lesson = _fixture_copy("excerpt-missing-file")
    (d / rel).unlink()
    cases["file deleted"] = _expect_missing(lesson, "a stored passage is deleted")
    d, lesson = _fixture_copy("excerpt-no-field")
    src = next(s for c in lesson.data["claims"] for s in c["sources"] if s.get("excerpts"))
    del src["excerpts"]
    cases["no excerpts field"] = _expect_missing(lesson, "a cited document has no stored passage")
    d, lesson = _fixture_copy("excerpt-quote")
    src = next(s for c in lesson.data["claims"] for s in c["sources"] if s.get("quote") and s.get("excerpts"))
    src["quote"] = src["quote"].replace("the", "no", 1)
    cases["quote not in passage"] = _expect_missing(lesson, "a quote is not in its stored passage")
    d, lesson = _fixture_copy("excerpt-mutation")
    muts = json.loads((d / "mutations.json").read_text())
    for m in muts["mutations"]:
        for s in m.get("sources", []):
            s.pop("excerpts", None)
    (d / "mutations.json").write_text(json.dumps(muts))
    cases["planted citation unstored"] = _expect_missing(lesson, "a wrong-citation mutation cites an unstored passage")
    try:
        claims.write_jobs(lesson, items, _tmp_build("excerpt-mutation-build"))
    except errors.SourceExcerptMissing:
        pass
    else:
        raise AssertionError("write_jobs wrote jobs for a planted citation without a stored passage")
    # `ptk build` fails on it before capturing anything
    d, lesson = _fixture_copy("excerpt-build")
    (d / rel).unlink()
    try:
        b.build(d)
    except errors.SourceExcerptMissing as e:
        rep = json.loads((d / "build" / "build-report.json").read_text())
        assert rep["status"] == "failed" and rep["error"]["error"] == "SourceExcerptMissing", rep["error"]
        assert "captured" not in rep["transitions"], rep["transitions"]
        out["build"] = str(e)[:80]
    else:
        raise AssertionError("ptk build ran with a cited passage missing")
    out["cases"] = {k: v[0][:70] for k, v in cases.items()}
    return out


# ---------------------------------------------------------------- AC-7.8

def _review_by(job, reviewer, rejects=()):
    rev = _review(job)
    rev["reviewer"] = {"host": "test", "agent": reviewer}
    for e in rev["claims"] + rev["texts"]:
        if e["id"] in rejects:
            e.update(verdict="reject", reason=f"{reviewer}: {e['id']} is wrong")
    if rejects:
        rev["overall"] = "reject"
    return rev


def test_three_reviewers_agree():
    """AC-7.8: `ptk build` writes the lesson job three times, for three independent reviewers: distinct job ids, the
    same content. claims.review passes only when all three accept. A split verdict is listed per claim or text with
    each reviewer's finding and fails; three rejects fail; a missing third review is not-run, never passed."""
    from ptk import build as b
    lesson, items = fcast_lesson()
    out = {}
    probe = _tmp_build("three-probe")
    claims.write_jobs(lesson, items, probe, mutations=[])
    priv = claims.load_private(probe)
    lesson_ids = [j for j, m in priv["jobs"].items() if m["role"] == "lesson"]
    assert len(lesson_ids) == LESSON_REVIEWERS == len(set(lesson_ids)), lesson_ids
    jobs = _jobs(probe)
    bodies = [{k: v for k, v in jobs[j].items() if k not in ("job_id", "review_path", "manifest", "manifest_sha256")}
              for j in lesson_ids]
    assert all(x == bodies[0] for x in bodies), "the three lesson jobs must carry the same content"
    assert len({jobs[j]["manifest"]["slot"] for j in lesson_ids}) == LESSON_REVIEWERS
    target = lesson.data["claims"][3]["id"]
    for case, rejects in {"all-accept": [(), (), ()], "split": [(), (target,), ()],
                          "all-reject": [(target,), (target,), (target,)], "missing": [(), (), None]}.items():
        build = _tmp_build(f"three-{case}")
        claims.write_jobs(lesson, items, build, mutations=[])
        ids = [j for j, m in claims.load_private(build)["jobs"].items() if m["role"] == "lesson"]
        jobs = _jobs(build)
        for n, (jid, rej) in enumerate(zip(ids, rejects)):
            if rej is not None:
                _write_review(build, jobs[jid], _review_by(jobs[jid], f"reviewer {n + 1}", rej))
        g = _gate(lesson, items, build)
        m = g["measured"]
        if case == "all-accept":
            assert g["status"] == "passed" and len(m["lesson_jobs"]) == 3 and not m["disagreements"], g
            assert b.final_status([g], False) == "verified"
        elif case == "split":
            assert g["status"] == "failed" and "disagree" in g["reason"], g
            (dis,) = m["disagreements"]
            assert dis["id"] == target and sorted(v["verdict"] for v in dis["verdicts"]) == ["accept", "accept", "reject"]
            rej = next(v for v in dis["verdicts"] if v["verdict"] == "reject")
            assert rej["reason"] == f"reviewer 2: {target} is wrong" and rej["reviewer"]["agent"] == "reviewer 2", dis
            assert {v["job"] for v in dis["verdicts"]} == set(ids)
            assert b.final_status([g], False) == "failed"
        elif case == "all-reject":
            assert g["status"] == "failed" and not m["disagreements"] and m["rejected"], g
            assert {r["id"] for r in m["rejected"]} == {target}, m["rejected"]
        else:
            assert g["status"] == "not-run" and len(m["missing"]) == 1, g
        out[case] = g["status"]
    return out


# ---------------------------------------------------------------- AC-7.9

SENTENCE_CLASSES = {"narration": "Narration and transcript lines", "chapter-title": "Chapter titles",
                    "question": "Question lines", "context": "Context sentences"}


def test_rubric_sentence_classes():
    """AC-7.9: the rubric says how narration/transcript lines, chapter titles, question lines and context sentences are
    judged, each with one worked example, and that a cited source is judged only against its stored passage, never
    against a reviewer's memory of the source. The jobs label each teaching text with its class, give scene-bound texts
    their scene (the job's `scenes` outline), and explain every place a text appears (`where_legend`). The rubric
    version is bumped, so a review written under rubric v3 is stale."""
    import re
    rubric = claims.RUBRIC.read_text()
    assert claims.RUBRIC_VERSION == "4" and rubric.startswith("# Claims review rubric, version 4"), rubric[:60]
    sections = {}
    for title in SENTENCE_CLASSES.values():
        m = re.search(rf"^### {re.escape(title)}\n(.*?)(?=^#{{2,3}} )", rubric, re.S | re.M)
        assert m, f"no rubric section {title!r}"
        body = m.group(1)
        assert "Worked example" in body and re.search(r"\b(accept|reject)\b", body), f"{title}: no worked example"
        sections[title] = len(body)
    low = rubric.lower()
    assert "source_passages" in rubric and "memory" in low and "only against" in low, "no stored-passage rule"
    assert "scenes" in rubric and "where_legend" in rubric
    lesson, items = fcast_lesson()
    sets = {"f-cast": (lesson, items)}
    if slice_lesson():
        sets["switch-fallthrough"] = slice_lesson()
    classes = set()
    for name, (lesson, items) in sets.items():
        build = _tmp_build(f"classes-{name}")
        claims.write_jobs(lesson, items, build, mutations=[])
        job = next(iter(_jobs(build).values()))
        scene_ids = {s["id"] for s in job["scenes"]}
        assert scene_ids == {s["id"] for s in lesson.data["storyboard"]}, name
        for t in job["teaching_texts"]:
            assert t["class"] in claims.TEXT_CLASSES, (name, t)
            classes.add(t["class"])
            if t["class"] in ("narration", "chapter-title", "question", "option"):
                assert t.get("scenes") and set(t["scenes"]) <= scene_ids, (name, t)
            for w in t["where"]:
                assert claims.where_kind(w) in job["where_legend"], (name, w)
        for s in job["scenes"]:
            assert {x["id"] for x in job["teaching_texts"]} >= set(s["narration"]) | ({s["title"]} if s["title"] else set())
        rubric_classes = set(re.findall(r"`class: ([a-z-]+)`", rubric))
        assert claims.TEXT_CLASSES <= rubric_classes, claims.TEXT_CLASSES - rubric_classes
    # a review under rubric v3 is stale for a v4 job
    build = _tmp_build("classes-v3")
    claims.write_jobs(lesson, items, build, mutations=[])
    job = _first_job(build)
    _write_review(build, job, _review(job, rubric="3"))
    g = _gate(lesson, items, build)
    assert g["status"] == "failed" and "rubric v3" in g["measured"]["stale"][0]["reason"], g
    return {"sections": sections, "classes": sorted(classes)}
