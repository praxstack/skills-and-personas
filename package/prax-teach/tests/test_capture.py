"""WP2 capture: AC-2.2 (happy path), AC-2.3 (warnings and sanitizers, E19), AC-2.4 (nondeterminism).

Every test captures a throwaway lesson built from tests/fixtures/capture/*.c through the real
runner: clang with the lesson flags under sandbox-exec, gcc-16 for diagnostics, two runs.
"""
import hashlib
import time

from fixtures.capture import kit
from ptk import errors, model
from ptk.capture import c_runner
from ptk.verify import values

LESSON_FLAGS = ("-std=c17", "-Wall", "-Wextra", "-Wformat=2", "-fsanitize=undefined,address")


def _capture(tmp):
    lesson = model.load(tmp)
    model.validate(lesson)
    return lesson, c_runner.capture_lesson(lesson)


def _expect_failure(tmp, error_class):
    lesson = model.load(tmp)
    model.validate(lesson)
    try:
        c_runner.capture_lesson(lesson)
    except error_class as e:
        return e
    raise AssertionError(f"capture did not raise {error_class.__name__}")


def test_happy_capture():
    facts = [
        kit.fact("f.d", "p1", 1, {"fn": "printf_d", "args": [66]}),
        kit.fact("f.c", "p1", 2, {"fn": "printf_c", "args": [66]}),
        kit.fact("f.u", "p1", 3, {"fn": "printf_u", "args": [66]}),
        kit.fact("f.f", "p1", 4, {"fn": "printf_f", "args": [66]}),
        kit.fact("f.sum", "p1", 5, {"fn": "sum", "args": [[1, 2, 3, 4]]}),
        kit.fact("f.int", "p1", stream="platform", key="sizeof.int",
                 expect={"fn": "sizeof_from_platform", "args": ["int"]}),
        kit.fact("f.signed", "p1", stream="platform", key="char_signed", expect={"value": "true", "reviewed": True}),
    ]
    tmp = kit.make_lesson("fx-happy-", [kit.program("p1", "happy.c")], facts)
    try:
        lesson, out = _capture(tmp)
        got = {f["id"]: f["value"] for f in lesson.data["facts"]}
        assert got["f.d"] == "66" and got["f.c"] == "B" and got["f.u"] == "66", got
        assert got["f.f"] == "66.000000" and got["f.sum"] == "10" and got["f.int"] == "4", got
        values.check_expectations(lesson)  # captured == independent expect, for every fact

        stdout = (tmp / "build" / "capture" / "p1.stdout").read_bytes()
        assert stdout == b"66\nB\n66\n66.000000\n10\n", stdout
        src = lesson.data["facts"][0]["source"]
        assert src["stdout_sha256"] == hashlib.sha256(stdout).hexdigest(), "stdout sha256 does not match the bytes"
        assert src["runs"] == 2, f"ran {src['runs']} time(s), not twice"
        assert all(flag in src["cmd"] for flag in LESSON_FLAGS), src["cmd"]
        assert "sandbox-exec" in src["sandbox"]

        plat = lesson.data["platform"]
        assert plat["captured"] is True
        assert set(plat["sizeof"]) >= {"char", "short", "int", "long", "long long", "float", "double", "void*"}
        assert isinstance(plat["char_signed"], bool) and plat["endianness"] in ("little", "big")
        assert plat["libc"] and plat["compilers"]["clang"] and plat["compilers"]["gcc-16"], plat

        prog = out["programs"]["p1"]
        assert prog["ran"] is True and prog["sanitizers"] == "no finding", prog
        # gcc-16 is diagnostics only: its -Wimplicit-fallthrough warning is recorded and blocks nothing
        assert "fall through" in prog["diagnostics"]["gcc-16"], prog["diagnostics"]
        assert prog["diagnostics"]["clang"] == "", prog["diagnostics"]
        assert lesson.data["programs"][0]["source_sha256"] == hashlib.sha256(
            (tmp / "programs" / "happy.c").read_bytes()).hexdigest()
        return {"facts": got, "stdout_sha256": src["stdout_sha256"]}
    finally:
        kit.cleanup(tmp)


def test_format_warning_fixture():
    """E19 fixture 1: printf("%f", int) is caught by -Wformat and blocks the fact."""
    tmp = kit.make_lesson("fx-wformat-", [kit.program("p1", "format_warning.c")], [kit.fact("f.x", "p1", 1)])
    try:
        e = _expect_failure(tmp, errors.SanitizerFinding)
        assert "-Wformat" in e.detail["stderr"], e.detail
        assert e.exit_code == errors.EXIT_GATE
        assert not (tmp / "build" / "capture" / "p1.stdout").exists(), "a blocked program produced a fact"
        return {"error": e.message}
    finally:
        kit.cleanup(tmp)


def test_asan_fixture():
    """E19 fixture 2: a heap overflow is reported by ASan at run time and blocks the fact."""
    tmp = kit.make_lesson("fx-asan-", [kit.program("p1", "asan_heap.c")], [kit.fact("f.x", "p1", 1)])
    try:
        e = _expect_failure(tmp, errors.SanitizerFinding)
        assert "AddressSanitizer" in e.detail["stderr"] and "heap-buffer-overflow" in e.detail["stderr"], e.detail
        return {"error": e.message}
    finally:
        kit.cleanup(tmp)


def test_ubsan_fixture():
    """E19 fixture 3: signed overflow is reported by UBSan at run time and blocks the fact."""
    tmp = kit.make_lesson("fx-ubsan-", [kit.program("p1", "ubsan_overflow.c")], [kit.fact("f.x", "p1", 1)])
    try:
        e = _expect_failure(tmp, errors.SanitizerFinding)
        assert "signed integer overflow" in e.detail["stderr"], e.detail
        return {"error": e.message}
    finally:
        kit.cleanup(tmp)


def test_ub_program_not_run():
    """A ub:true program covered by an undefined-behaviour claim compiles (warning recorded) and never runs.

    The fixture never terminates, so a run would end in RunTimeout. Without the covering claim the
    model is rejected before anything compiles.
    """
    programs = [kit.program("p1", "ub_never_run.c", ub=True, run=False), kit.program("p2", "hello.c")]
    facts = [kit.fact("f.hello", "p2", 1, {"value": "hello", "reviewed": True})]
    ub_claim = kit.claim("c.ub", "Passing an int where %f expects a double is undefined behaviour.",
                         kind="undefined-behaviour", programs=["p1"])
    tmp = kit.make_lesson("fx-ub-", programs, facts, claims=[ub_claim])
    try:
        t0 = time.monotonic()
        lesson, out = _capture(tmp)
        took = time.monotonic() - t0
        assert out["programs"]["p1"]["ran"] is False, out["programs"]["p1"]
        assert out["programs"]["p1"]["sanitizers"] == "not run (ub)", out["programs"]["p1"]
        assert "-Wformat" in out["programs"]["p1"]["diagnostics"]["clang"], "the UB warning was not recorded"
        assert not (tmp / "build" / "capture" / "p1.stdout").exists()
        assert out["programs"]["p2"]["ran"] is True and lesson.fact("f.hello")["value"] == "hello"
        assert took < c_runner.RUN_TIMEOUT * 2, f"capture took {took:.1f}s; did the ub program run?"

        uncovered = model.load(tmp)
        uncovered.data["claims"][0]["kind"] = "caveat"
        try:
            model.validate(uncovered)
        except errors.ModelReferenceError as e:
            assert any(x["pointer"] == "/programs/0/ub" for x in e.detail["errors"]), e.detail
        else:
            raise AssertionError("a ub:true program with no undefined-behaviour claim validated")
        return {"seconds": round(took, 1)}
    finally:
        kit.cleanup(tmp)


def test_nondeterminism():
    """AC-2.4: two runs that print different bytes fail, and the error shows both outputs."""
    tmp = kit.make_lesson("fx-nondet-", [kit.program("p1", "nondet.c")], [kit.fact("f.x", "p1", 1)])
    try:
        e = _expect_failure(tmp, errors.NondeterministicOutput)
        r1, r2 = e.detail["run1"], e.detail["run2"]
        assert r1.startswith("pid ") and r2.startswith("pid ") and r1 != r2, e.detail
        return {"run1": r1.strip(), "run2": r2.strip()}
    finally:
        kit.cleanup(tmp)
