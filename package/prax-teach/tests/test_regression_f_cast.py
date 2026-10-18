"""AC-7.6 (CRITICAL, agent-mediated): the real reviewer rejects the "same bits" claim for printf("%f", (double)a).

Two jobs, reviewed blind by separate subagents:
- same-bits: the f-cast fixture written by an author who believes the claim (c.cast says the format string
  only reads the bits, the representation claim is removed, the misconception is not listed);
- control: the corrected fixture, whose c.cast must be accepted, so a reviewer that rejects everything fails.
The rubric does not contain this example (it is held out).
"""
from _claims_agent import SAME_BITS, ensure_jobs, fcast_lesson, run_check, same_bits_lesson, review_of
from selftest_support import AgentPending


def test_same_bits_claim_rejected():
    runs = {"same-bits": same_bits_lesson(), "control": fcast_lesson()}
    pending, out = [], {}
    for name, (lesson, items) in runs.items():
        build = ensure_jobs(f"f-cast-regression/{name}", lesson, items, mutations=[])
        gates, priv, jobs = run_check(lesson, items, build)
        if jobs:
            pending += jobs
            continue
        g = gates["claims.review"]
        assert not g["measured"]["stale"] and not g["measured"]["invalid"], g["measured"]
        job_id = next(iter(priv["jobs"]))
        rev = review_of(build, job_id)
        cast = next(c for c in rev["claims"] if c["id"] == "c.cast")
        out[name] = {"job": job_id, "c.cast": cast["verdict"], "reason": cast["reason"], "overall": rev["overall"]}
    if pending:
        raise AgentPending(f"review each job in a separate subagent (job file + rubric only): {sorted(set(pending))}")
    same = next(c for c in same_bits_lesson()[0].data["claims"] if c["id"] == "c.cast")
    assert same["text"] == SAME_BITS
    assert out["same-bits"]["c.cast"] == "reject" and out["same-bits"]["overall"] == "reject", out["same-bits"]
    assert out["control"]["c.cast"] == "accept", f"the corrected cast claim was rejected: {out['control']}"
    return out


test_same_bits_claim_rejected.agent = True
