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
