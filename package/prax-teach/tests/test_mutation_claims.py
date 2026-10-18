"""AC-7.5: the claims mutation suite with controls (E22). Spec name tests/test_mutation.py::test_real_reviewer_rates;
WP3 owns tests/test_mutation.py, so this suite lives here.

Automatic: the planted errors are real changes, avoid the listed misconceptions, cover the families, and the
rate maths counts schema rejections apart. Agent-mediated: the real reviewer's catch and control rates.
"""
from _claims_agent import ensure_jobs, fcast_lesson, run_check, slice_lesson, slice_snapshot
from selftest_support import AgentPending
from ptk import text
from ptk.verify import claims, mutation_claims as mc


def _lessons():
    out = {"f-cast": fcast_lesson()}
    s = slice_lesson()
    if s:
        out["switch-fallthrough"] = s
    return out


def test_mutations_are_real_and_not_misconceptions():
    seen = {}
    for name, (lesson, items) in _lessons().items():
        claims.mapping_gate(lesson, items)
        muts = mc.select(lesson)
        assert 1 <= len(muts) <= mc.MAX_MUTATIONS, (name, len(muts))
        base = claims._job_body(lesson, items)
        for m in muts:
            body, changed = mc.apply(base, m)
            assert body["claims"] != base["claims"] or body["teaching_texts"] != base["teaching_texts"], m["id"]
            for c in body["claims"]:
                assert mc.misconception_overlap(c["text"], lesson) < 0.5, (m["id"], c["text"])
            if m["kind"] == "value-swap":
                facts = {text.display(f) for f in lesson.data["facts"]}
                assert m["replace"] != m["find"] and m["find"] in facts and changed, m
        fams = {mc.family(m["kind"]) for m in muts}
        kinds = {m["kind"] for m in muts}
        assert fams == {"value", "claim"}, (name, fams)
        seen[name] = {"mutations": len(muts), "kinds": sorted(kinds)}
    allkinds = set().union(*[set(v["kinds"]) for v in seen.values()])
    for k in ("value-swap", "false-mechanism", "overbroad", "dropped-caveat", "wrong-citation"):
        assert k in allkinds, f"no {k} mutation in the suite"
    return seen


def test_anchor_gone_is_reported_not_counted():
    lesson, items = fcast_lesson()
    claims.mapping_gate(lesson, items)
    m = {"id": "x", "kind": "overbroad", "target": "c.cast", "find": "no such words", "replace": "y"}
    try:
        mc.apply(claims._job_body(lesson, items), m)
    except ValueError as e:
        return {"reported": str(e)}
    raise AssertionError("a mutation that changes nothing was accepted")


def test_rates_count_schema_rejections_separately():
    rows = [{"role": "mutation", "family": "value", "overall": "reject", "planted_claim": "c.a",
             "rejected_claims": [{"id": "c.a"}], "rejected_texts": [], "changed_texts": []},
            {"role": "mutation", "family": "claim", "overall": "reject", "planted_claim": "c.b",
             "rejected_claims": [], "rejected_texts": [{"id": "t.002"}], "changed_texts": ["t.002"]},
            {"role": "mutation", "family": "claim", "overall": "reject", "planted_claim": "c.c",
             "rejected_claims": [{"id": "c.z"}], "rejected_texts": [], "changed_texts": ["t.009"]},
            {"role": "mutation", "family": "claim", "schema_invalid": True, "overall": None, "planted_claim": "c.d"},
            {"role": "control", "overall": "accept"}, {"role": "control", "overall": "reject"},
            {"role": "control", "schema_invalid": True, "overall": None}]
    r = mc.rates(rows)
    assert r["value"] == {"n": 1, "caught": 1, "schema_rejections": 0, "rate": 1.0}
    # rejecting some other claim is not a catch; a schema rejection is neither a catch nor hidden
    assert r["claim"]["caught"] == 1 and r["claim"]["schema_rejections"] == 1 and r["claim"]["n"] == 3
    assert r["control"]["accepted"] == 1 and r["control"]["schema_rejections"] == 1
    assert r["meets_thresholds"] is False
    return r


def test_real_reviewer_rates():
    """Calibration mode (`--calibrate`, D21.1). Against real reviewer subagents: 100% of value mutations, >= 90% of claim mutations caught,
    >= 95% of controls accepted, pooled over the f-cast fixture and a frozen snapshot of the switch slice;
    schema rejections reported apart."""
    lessons = {"f-cast": fcast_lesson(), "switch-fallthrough": slice_snapshot()}
    pending, rows, per = [], [], {}
    for name, (lesson, items) in lessons.items():
        build = ensure_jobs(f"rates/{name}", lesson, items, calibrate=True)  # D21.1: AC-7.5 is a calibration run
        gates, priv, jobs = run_check(lesson, items, build)
        if jobs:
            pending += jobs
            continue
        st = gates["claims.review"]["measured"]
        assert not st["stale"], st["stale"]
        assert not st["missing"], st["missing"]
        sens = gates["claims.sensitivity"]["measured"]
        per[name] = {k: sens[k] for k in ("value", "claim", "control")}
        per[name]["lesson_job"] = gates["claims.review"]["status"]
        rows += [dict(r, lesson=name) for r in _rows(lesson, items, build)]
    if pending:
        raise AgentPending(f"review each job in a separate subagent (job file + rubric only): {sorted(pending)}")
    pooled = mc.rates(rows)
    missed = [(r["lesson"], r.get("mutation")) for r in rows if r["role"] == "mutation" and not mc.caught(r)]
    rejected_controls = [(r["lesson"], r["job"]) for r in rows if r["role"] == "control" and r.get("overall") != "accept"]
    assert pooled["value"]["rate"] == 1.0, (pooled["value"], missed)
    assert pooled["claim"]["rate"] >= 0.90, (pooled["claim"], missed)
    assert pooled["control"]["rate"] >= 0.95, (pooled["control"], rejected_controls)
    return {"pooled": pooled, "per_lesson": per, "missed": missed, "rejected_controls": rejected_controls}


def _rows(lesson, items, build):
    """Re-derive the per-job rows that check() scored (claims.sensitivity carries a summary only)."""
    import json
    priv = claims.load_private(build)
    out = []
    for job_id, meta in priv["jobs"].items():
        if meta["role"] == "lesson":
            continue
        raw = (build / "claims-review" / f"{job_id}.json").read_text()
        job = json.loads((build / "claims-jobs" / f"{job_id}.json").read_text())
        row = {"job": job_id, "role": meta["role"], "family": meta.get("family"),
               "planted_claim": meta.get("planted_claim"), "changed_texts": meta.get("changed_texts", []),
               "mutation": (meta.get("mutation") or {}).get("id")}
        if claims.review_problems(job, raw):
            out.append(dict(row, schema_invalid=True, overall=None))
            continue
        rev = json.loads(raw)
        out.append(dict(row, overall=rev["overall"],
                        rejected_claims=[c for c in rev["claims"] if c["verdict"] == "reject"],
                        rejected_texts=[t for t in rev["texts"] if t["verdict"] == "reject"]))
    return out


test_real_reviewer_rates.agent = True
