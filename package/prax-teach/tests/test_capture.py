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
                 expect={"fn": "sizeof_abi", "args": ["int"]}),
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


# ---------------------------------------------------------------- review WP2 P1-1: the source may not switch off its guard
#
# Each case is a program that, before the fix, got a %f-of-int or an INT_MAX + 1 through capture as a
# clean fact. Capture must refuse each one by name (ModelReferenceError, exit 3, construct named),
# before anything runs. "source" cases are visible in the text, so `ptk validate` refuses them too;
# "cpp" cases are built by macro pasting and only clang's own preprocessor output shows them.

FMT_BODY = 'int main(void) {\n    int a = 66;\n    printf("%f\\n", a);\n    return 0;\n}\n'
UB_FN = ('int bump(int x) {\n    return x + 1;\n}\n'
         'int main(void) {\n    volatile int x = INT_MAX;\n    printf("%d\\n", bump(x));\n    return 0;\n}\n')
HDR = "#include <limits.h>\n#include <stdio.h>\n"

BYPASS_CASES = {
    "pragma_clang_diagnostic": ("source", "pragma-diagnostic",
                                HDR + '#pragma clang diagnostic ignored "-Wformat"\n' + FMT_BODY),
    "pragma_gcc_diagnostic": ("source", "pragma-diagnostic", HDR + '#pragma GCC diagnostic ignored "-Wformat"\n' + FMT_BODY),
    "pragma_operator": ("source", "pragma-operator", HDR + '_Pragma("clang diagnostic ignored \\"-Wformat\\"")\n' + FMT_BODY),
    "pragma_clang_attribute": ("source", "pragma-attribute",
                               HDR + '#pragma clang attribute push (__attribute__((no_sanitize("undefined"))), '
                               'apply_to = function)\n' + UB_FN + "#pragma clang attribute pop\n"),
    "pragma_system_header": ("source", "pragma-system-header", HDR + "#pragma clang system_header\n" + FMT_BODY),
    "gnu_line_marker": ("source", "line-marker", HDR + '# 1 "fake.h" 3\n' + FMT_BODY),
    "line_directive": ("source", "line-directive", HDR + '#line 1 "fake.h"\n' + FMT_BODY),
    "digraph_pragma": ("source", "pragma-diagnostic", HDR + '%:pragma clang diagnostic ignored "-Wformat"\n' + FMT_BODY),
    "spliced_pragma": ("source", "pragma-diagnostic",
                       HDR + '#pra\\\ngma clang diagnostic ignored "-Wformat"\n' + FMT_BODY),
    "trigraph_pragma": ("source", "pragma-diagnostic", HDR + '??=pragma clang diagnostic ignored "-Wformat"\n' + FMT_BODY),
    "no_sanitize_attribute": ("source", "no-sanitize", HDR + UB_FN.replace(
        "int bump", '__attribute__((no_sanitize("undefined"))) int bump')),
    "no_sanitize_address": ("source", "no-sanitize", HDR + "#include <stdlib.h>\n"
                            "__attribute__((no_sanitize_address)) int peek(int *p) {\n    return p[4];\n}\n"
                            "int main(void) {\n    int *p = malloc(4 * sizeof *p);\n    p[0] = 1;\n"
                            '    printf("%d\\n", peek(p) * 0 + 1);\n    free(p);\n    return 0;\n}\n'),
    "c2x_no_sanitize": ("source", "no-sanitize", HDR + UB_FN.replace(
        "int bump", '[[clang::no_sanitize("undefined")]] int bump')),
    "asan_default_options": ("source", "sanitizer-hook", HDR +
                             'const char *__ubsan_default_options(void) {\n    return "halt_on_error=0";\n}\n' + UB_FN),
    "asm_label_hook": ("source", "asm", HDR + 'const char *opts(void) __asm__("___ubsan_default_options");\n'
                       'const char *opts(void) {\n    return "halt_on_error=0";\n}\n' + UB_FN),
    "embed": ("source", "embed", HDR + "static const unsigned char d[] = {\n#embed \"/etc/hosts\"\n, 0};\n" + FMT_BODY),
    "pasted_pragma": ("cpp", "pragma-diagnostic", HDR + "#define CAT(a, b) a##b\n#define P(x) CAT(_Prag, ma)(#x)\n"
                      'P(clang diagnostic ignored "-Wformat")\n' + FMT_BODY),
    "pasted_no_sanitize": ("cpp", "no-sanitize", HDR + "#define CAT(a, b) a##b\n#define NS CAT(no_san, itize)\n"
                           + UB_FN.replace("int bump", '__attribute__((NS("undefined"))) int bump')),
    "pasted_hook": ("cpp", "sanitizer-hook", HDR + "#define CAT(a, b) a##b\n"
                    'const char *CAT(__ubsan_default, _options)(void) {\n    return "halt_on_error=0";\n}\n' + UB_FN),
}


def _bypass_test(name, layer, construct, src):
    def test():
        tmp = kit.make_lesson(f"fx-bypass-{name}-", [kit.program_text("p1", "p1.c", src)],
                              [kit.fact("f.x", "p1", 1)])
        try:
            lesson = model.load(tmp)
            if layer == "source":  # visible in the text: `ptk validate` names it with a pointer
                try:
                    model.validate(lesson)
                except errors.ModelReferenceError as e:
                    hits = [x for x in e.detail["errors"] if x["pointer"] == "/programs/0/path"]
                    assert hits and construct in hits[0]["message"], e.detail["errors"]
                else:
                    raise AssertionError(f"{name}: validate accepted a program that switches off its guard")
            try:  # and capture refuses it on its own, even when validate was skipped
                c_runner.capture_lesson(model.load(tmp))
            except errors.ModelReferenceError as e:
                assert e.exit_code == errors.EXIT_MODEL
                assert e.detail.get("construct") == construct, (name, e.message, e.detail)
                assert e.detail.get("pointer") == "/programs/0/path", e.detail
            else:
                raise AssertionError(f"{name}: capture accepted a program that switches off its guard")
            assert not (tmp / "build" / "capture" / "p1.stdout").exists(), "a refused program produced a fact"
            return {"construct": construct, "layer": layer}
        finally:
            kit.cleanup(tmp)
    test.__name__ = f"test_bypass_{name}"
    test.__doc__ = f"Review WP2 P1-1: {name} ({layer} layer) fails capture as {construct}."
    return test


for _name, (_layer, _construct, _src) in BYPASS_CASES.items():
    globals()[f"test_bypass_{_name}"] = _bypass_test(_name, _layer, _construct, _src)


def test_bypass_control_clean_program_captures():
    """Control for the bypass tests: comments and strings that only mention pragmas, line markers or
    no_sanitize are not constructs, and an allowed `#pragma STDC` passes. The program captures."""
    src = (HDR + "/* #pragma clang diagnostic ignored \"-Wformat\"\n# 1 \"fake.h\" 3 */\n"
           "// __attribute__((no_sanitize(\"undefined\"))) and _Pragma(\"x\")\n"
           "#pragma STDC FP_CONTRACT OFF\n"
           'int main(void) {\n    puts("#pragma clang diagnostic is not run here");\n'
           '    printf("%d\\n", INT_MAX / 2);\n    return 0;\n}\n')
    facts = [kit.fact("f.1", "p1", 1, {"value": "#pragma clang diagnostic is not run here", "reviewed": True}),
             kit.fact("f.2", "p1", 2, {"fn": "printf_d", "args": [1073741823]})]
    tmp = kit.make_lesson("fx-bypass-control-", [kit.program_text("p1", "p1.c", src)], facts)
    try:
        lesson, out = _capture(tmp)
        values.check_expectations(lesson)
        assert out["programs"]["p1"]["sanitizers"] == "no finding", out["programs"]["p1"]
        return out["facts"]
    finally:
        kit.cleanup(tmp)


def test_bypass_override_needs_a_claim_and_a_program_that_never_runs():
    """A construct is allowed only when a claim lists it in `overrides` and lists the program, and the
    program never runs (ub:true or run:false). A running program can never switch its guard off."""
    src = HDR + '#pragma clang diagnostic ignored "-Wformat"\n' + FMT_BODY
    hello = kit.program("p2", "hello.c")
    fact = kit.fact("f.hello", "p2", 1, {"value": "hello", "reviewed": True})
    claim = kit.claim("c.ub", "Passing an int where %f expects a double is undefined behaviour.",
                      kind="undefined-behaviour", programs=["p1"])
    claim["overrides"] = ["pragma-diagnostic"]
    tmp = kit.make_lesson("fx-override-", [kit.program_text("p1", "p1.c", src, ub=True, run=False), hello], [fact],
                          claims=[claim])
    try:
        lesson, out = _capture(tmp)
        assert out["programs"]["p1"]["ran"] is False and out["programs"]["p2"]["ran"] is True, out["programs"]

        running = model.load(tmp)
        running.data["programs"][0].update(ub=False, run=True)
        running.data["claims"][0]["kind"] = "caveat"
        try:
            model.validate(running)
        except errors.ModelReferenceError as e:
            assert "/claims/0/overrides" in [x["pointer"] for x in e.detail["errors"]], e.detail
        else:
            raise AssertionError("an override for a running program validated")
        try:
            c_runner.capture_lesson(running)
        except errors.ModelReferenceError as e:
            assert e.detail.get("construct") == "pragma-diagnostic", e.detail
        else:
            raise AssertionError("capture honoured an override for a running program")
        return {"compile_only": "captured", "running": "refused"}
    finally:
        kit.cleanup(tmp)


# ---------------------------------------------------------------- review WP2 P2-3, P2-4, P2-5

def test_too_few_lines_is_expectation_mismatch():
    """P2-3: a fact that selects a line the run never printed is ExpectationMismatch (exit 1), showing
    the expected value and how many lines the program printed. The model is valid; the run differs."""
    tmp = kit.make_lesson("fx-fewlines-", [kit.program("p1", "hello.c")],
                          [kit.fact("f.l3", "p1", 3, {"value": "three", "reviewed": True})])
    try:
        e = _expect_failure(tmp, errors.ExpectationMismatch)
        assert e.exit_code == errors.EXIT_GATE
        mm = e.detail["mismatches"]
        assert mm[0]["fact"] == "f.l3" and mm[0]["captured"] is None and mm[0]["expected"] == "three", mm
        assert "1 line" in mm[0]["reason"], mm
        return mm
    finally:
        kit.cleanup(tmp)


def test_bad_platform_subkey_is_model_error():
    """P2-4: `sizeof.int128` and `captured.x` fail validation at /facts/i/select/key, and capture's own
    lookup raises a named model error instead of a raw KeyError or TypeError."""
    seen = {}
    for key in ("sizeof.int128", "captured.x", "compilers.tcc", "sizeof"):
        tmp = kit.make_lesson("fx-platkey-", [kit.program("p1", "hello.c")],
                              [kit.fact("f.k", "p1", stream="platform", key=key, expect={"value": "4", "reviewed": True})])
        try:
            lesson = model.load(tmp)
            try:
                model.validate(lesson)
            except errors.ModelReferenceError as e:
                assert "/facts/0/select/key" in [x["pointer"] for x in e.detail["errors"]], e.detail
            else:
                raise AssertionError(f"platform key {key!r} validated")
            try:
                c_runner.capture_lesson(model.load(tmp))
            except errors.ModelReferenceError as e:
                assert e.detail.get("pointer") == "/facts/0/select/key", e.detail
                seen[key] = e.message
            else:
                raise AssertionError(f"capture accepted platform key {key!r}")
        finally:
            kit.cleanup(tmp)
    return seen


def test_sizeof_expectation_is_independent():
    """P2-5: sizeof expectations come from the declared ABI table in expect.py, not from the capture.
    A corrupted platform value and the fact that reads it no longer agree with the expectation."""
    from ptk import expect
    assert expect.evaluate({"fn": "sizeof_abi", "args": ["int"]}) == "4"
    assert expect.evaluate({"fn": "sizeof_abi", "args": ["long", "LLP64"]}) == "4"
    assert "sizeof_from_platform" not in expect.FUNCTIONS, "the self-checking sizeof expectation is still offered"
    facts = [kit.fact("f.int", "p1", stream="platform", key="sizeof.int", expect={"fn": "sizeof_abi", "args": ["int"]}),
             kit.fact("f.ptr", "p1", stream="platform", key="sizeof.void*", expect={"fn": "sizeof_abi", "args": ["void*"]})]
    tmp = kit.make_lesson("fx-sizeof-", [kit.program("p1", "hello.c")], facts)
    try:
        lesson, _out = _capture(tmp)
        values.check_expectations(lesson)
        lesson.data["platform"]["sizeof"]["int"] = 8  # a corrupted capture ...
        lesson.data["facts"][0]["value"] = "8"         # ... and the fact read from it
        try:
            values.check_expectations(lesson)
        except errors.ExpectationMismatch as e:
            assert e.detail["mismatches"] == [{"fact": "f.int", "captured": "8", "expected": "4"}], e.detail
        else:
            raise AssertionError("a corrupted sizeof capture still matched its expectation")
        return {"f.int": "4", "f.ptr": lesson.fact("f.ptr")["value"]}
    finally:
        kit.cleanup(tmp)
