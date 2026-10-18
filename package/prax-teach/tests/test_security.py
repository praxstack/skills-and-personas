"""Capture sandbox and resource limits (AC-2.5, AC-2.6, D17.10, E24, review P1-4).

A probe program, built with the lesson flags (ASan + UBSan), tries one thing per run under
sandbox-exec MODE=run. Each forbidden action must be denied inside the sandbox, and the same
binary run outside the sandbox must succeed at it, so the denial is the sandbox's doing.
Mach probes only look services up; nothing is sent, and no app is launched.

The named AC-2.5 tests go through the real `capture_lesson` path with throwaway lessons
(tests/fixtures/capture/kit.py), so they test what an author's program meets, not a helper.
"""
import json
import os
import secrets
import shutil
from pathlib import Path

from fixtures.capture import kit
from ptk import errors, host, model
from ptk.capture import c_runner
from _util import ptk_cmd

PROBE = host.PKG / "tests" / "fixtures" / "sandbox-probe" / "probe.c"
MACH = ("mach-nsurlsessiond", "mach-lsd-open", "mach-launchservicesd", "mach-appleevents", "mach-pasteboard")


def _home_file():
    for name in (".zshrc", ".zprofile", ".bash_profile", ".profile", ".gitconfig"):
        p = Path.home() / name
        if p.is_file():
            return p
    raise AssertionError("no readable file in $HOME to probe with")


def _build(tmp):
    src = tmp / "probe.c"
    shutil.copyfile(PROBE, src)
    exe, _warn, _cmd = c_runner.compile_program(src, tmp, "probe")
    return exe


def _run_raw(exe, tmp, args):
    env = host.program_env(c_runner.SAN_ENV)
    return host.run_limited(host.sandboxed([exe, *args], "run", tmp=tmp), cwd=tmp, timeout=10, max_output=1 << 16,
                            max_rss_kb=512 * 1024, env=env)


def _run(exe, tmp, args, sandbox):
    env = host.program_env({**c_runner.SAN_ENV, "PROBE_HOME_FILE": str(_home_file())})
    cmd = [exe, *args]
    if sandbox:
        cmd = host.sandboxed(cmd, "run", tmp=tmp)
    res = host.run_limited(cmd, cwd=tmp, timeout=10, max_output=1 << 16, max_rss_kb=512 * 1024, env=env)
    return (res.stdout.strip().splitlines() or [f"NO-OUTPUT code={res.code} {res.stderr.strip()[-300:]}"])[-1]


def test_run_profile_denies_escapes():
    tmp = host.make_tmp("security-")
    outside = host.make_tmp("security-outside-")
    try:
        exe = _build(tmp)
        allowed = {a: _run(exe, tmp, [a, *x], True) for a, x in (("hello", []), ("write-tmp", [str(tmp / "ok.txt")]))}
        for a, line in allowed.items():
            assert line.startswith("ALLOWED"), f"sandboxed program cannot even do {a}: {line}"
        for action in ("heap-overflow", "ub-shift"):
            res = _run_raw(exe, tmp, [action])
            assert any(m in res.stderr for m in c_runner.SAN_MARKERS), \
                f"the sanitizer report for {action} did not survive the sandbox: {res.stderr[-400:]}"
        probes = [("read-home", []), ("write-outside", [str(outside / "escape.txt")]), ("connect", []),
                  ("fork", []), ("posix-spawn", []), *[(m, []) for m in MACH]]
        seen, leaks, weak = {}, [], []
        for action, extra in probes:
            inside = _run(exe, tmp, [action, *extra], True)
            outside_run = _run(exe, tmp, [action, *[e.replace("escape", "control") for e in extra]], False)
            seen[action] = {"sandbox": inside, "control": outside_run}
            if not inside.startswith("DENIED"):
                leaks.append(f"{action}: {inside}")
            if action != "connect" and not outside_run.startswith("ALLOWED"):
                weak.append(f"{action}: control {outside_run}")
        assert not leaks, f"MODE=run let the program do: {leaks}"
        assert not weak, f"controls failed outside the sandbox, so the denial proves nothing: {weak}"
        assert not (outside / "escape.txt").exists(), "the write outside TMP landed"
        return seen
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(outside, ignore_errors=True)


# ---------------------------------------------------------------- AC-2.5 / AC-2.6, through capture_lesson

def _capture_probe(prefix, runs):
    """Capture a lesson with one probe program per (id, args); return {id: first stdout line}."""
    programs = [kit.program(pid, kit.PROBE, args=args) for pid, args in runs]
    facts = [kit.fact(f"f.{pid}", pid, 1) for pid, _ in runs]
    tmp = kit.make_lesson(prefix, programs, facts)
    try:
        lesson = model.load(tmp)
        model.validate(lesson)
        c_runner.capture_lesson(lesson)
        return {pid: lesson.fact(f"f.{pid}")["value"] for pid, _ in runs}
    finally:
        kit.cleanup(tmp)


def _control(args):
    """The same probe, outside the sandbox: proves the action works when nothing denies it."""
    tmp = host.make_tmp("security-control-")
    try:
        return _run(_build(tmp), tmp, args, False)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_capture_denies_network():
    got = _capture_probe("sec-net-", [("p1", ["connect"])])
    assert got["p1"].startswith("DENIED connect"), f"a lesson program connected out: {got}"
    return got


def test_denies_outside_write():
    outside = host.make_tmp("security-outside-")
    try:
        got = _capture_probe("sec-write-", [("p1", ["write-outside", str(outside / "escape.txt")]),
                                            ("p2", ["write-tmp", "inside.txt"])])
        assert got["p1"].startswith("DENIED write-outside"), got
        assert not (outside / "escape.txt").exists(), "the write outside the temp dir landed"
        assert got["p2"] == "ALLOWED write-tmp", f"writes inside its own temp dir must work: {got}"
        control = _control(["write-outside", str(outside / "control.txt")])
        assert control.startswith("ALLOWED"), f"control failed outside the sandbox, so the denial proves nothing: {control}"
        return {**got, "control": control}
    finally:
        shutil.rmtree(outside, ignore_errors=True)


def test_denies_fork():
    got = _capture_probe("sec-fork-", [("p1", ["fork"]), ("p2", ["posix-spawn"])])
    assert got["p1"].startswith("DENIED fork") and got["p2"].startswith("DENIED posix-spawn"), got
    control = _control(["fork"])
    assert control.startswith("ALLOWED"), control
    return {**got, "control": control}


def _expect(tmp, error_class):
    lesson = model.load(tmp)
    model.validate(lesson)
    try:
        c_runner.capture_lesson(lesson)
    except error_class as e:
        return e
    raise AssertionError(f"capture did not raise {error_class.__name__}")


def test_output_cap():
    """2 MB on stdout, then on stderr: each is killed at the 1 MB cap and fails (truncation is a failure)."""
    seen = {}
    for stream, args in (("stdout", None), ("stderr", ["err"])):
        tmp = kit.make_lesson(f"sec-cap-{stream}-", [kit.program("p1", "flood.c", args=args)],
                              [kit.fact("f.x", "p1", 1)])
        try:
            e = _expect(tmp, errors.OutputLimitExceeded)
            seen[stream] = e.message
            assert not (tmp / "build" / "capture" / "p1.stdout").exists()
        finally:
            kit.cleanup(tmp)
    assert c_runner.MAX_OUTPUT == 1 << 20
    return seen


def _cap_dirs():
    return {p.name for p in host.state_path("tmp").glob("cap-*")}


def _survivors(token):
    res = host.run(["/bin/ps", "-A", "-o", "pid=,pgid=,command="], timeout=30)
    return [line for line in res.stdout.splitlines() if token in line]


def test_cleanup_after_kill():
    """After a timeout and after an RSS watchdog kill, no process of the program survives and the
    capture temp dir is gone."""
    saved = (c_runner.RUN_TIMEOUT, c_runner.MAX_RSS_KB)
    seen = {}
    try:
        c_runner.RUN_TIMEOUT, c_runner.MAX_RSS_KB = 2.0, 192 * 1024
        for fixture, error_class in (("spin.c", errors.RunTimeout), ("hog.c", errors.MemoryLimitExceeded)):
            token = f"{Path(fixture).stem}-{secrets.token_hex(4)}"
            before = _cap_dirs()
            tmp = kit.make_lesson(f"sec-kill-{Path(fixture).stem}-", [kit.program(token, fixture)],
                                  [kit.fact("f.x", token, 1)])
            try:
                e = _expect(tmp, error_class)
                left = _survivors(token)
                assert not left, f"{fixture}: processes survived the kill: {left}"
                new_dirs = _cap_dirs() - before
                assert not new_dirs, f"{fixture}: capture temp dirs left behind: {new_dirs}"
                seen[fixture] = {"error": e.kind, **{k: v for k, v in e.detail.items() if k != "stderr"}}
            finally:
                kit.cleanup(tmp)
        assert seen["hog.c"]["peak_rss_kb"] > 192 * 1024, seen
        return seen
    finally:
        c_runner.RUN_TIMEOUT, c_runner.MAX_RSS_KB = saved


def test_refuse_without_sandbox():
    """AC-2.6: no sandbox-exec, no capture. Exit 2, SandboxUnavailable, and nothing ran or was written."""
    tmp = kit.make_lesson("sec-nosandbox-", [kit.program("p1", "hello.c")],
                          [kit.fact("f.x", "p1", 1, {"value": "hello", "reviewed": True})])
    calls = []
    real_run, real_limited = host.run, host.run_limited
    old_env = os.environ.get("PTK_SANDBOX_EXEC")
    try:
        before = (tmp / "lesson.json").read_bytes()
        os.environ["PTK_SANDBOX_EXEC"] = str(tmp / "no-such-sandbox-exec")
        host.run = lambda *a, **k: calls.append(("run", a)) or real_run(*a, **k)
        host.run_limited = lambda *a, **k: calls.append(("run_limited", a)) or real_limited(*a, **k)
        lesson = model.load(tmp)
        try:
            c_runner.capture_lesson(lesson)
        except errors.SandboxUnavailable as e:
            assert e.exit_code == errors.EXIT_HOST
        else:
            raise AssertionError("capture ran without sandbox-exec")
        finally:
            host.run, host.run_limited = real_run, real_limited
            if old_env is None:
                os.environ.pop("PTK_SANDBOX_EXEC", None)
            else:
                os.environ["PTK_SANDBOX_EXEC"] = old_env
        assert not calls, f"capture started processes before refusing: {calls}"
        assert (tmp / "lesson.json").read_bytes() == before, "lesson.json changed"
        assert not (tmp / "build").exists(), "capture wrote a build dir"

        env = host.child_env({"PTK_SANDBOX_EXEC": str(tmp / "no-such-sandbox-exec")})
        res = host.run([*ptk_cmd(), "capture", str(tmp)], env=env, timeout=120)
        assert res.code == errors.EXIT_HOST, f"ptk capture exited {res.code}: {res.stderr[-400:]}"
        assert json.loads(res.stderr)["error"] == "SandboxUnavailable", res.stderr
        assert (tmp / "lesson.json").read_bytes() == before and not (tmp / "build").exists()
        return {"exit": res.code}
    finally:
        kit.cleanup(tmp)


def _secret(prefix="security-secret-", text=None):
    """A secret file outside every dir the compile profile may read (the capture temp dir, the
    toolchain). It lives in its own $PTK_STATE/tmp dir, never inside the lesson or the capture dir."""
    secret_dir = host.make_tmp(prefix)
    token = f"SECRET-{secrets.token_hex(8)}"
    secret = secret_dir / "secret.txt"
    secret.write_text(text.replace("@TOKEN@", token) if text else token + "\n")
    return secret_dir, secret.resolve(), token


def _unsandboxed_control(src, token):
    """The same source compiled and run outside the sandbox does read the secret."""
    control_dir = host.make_tmp("security-embed-control-")
    try:
        shutil.copyfile(src, control_dir / "c.c")
        built = host.run(["/usr/bin/clang", "-std=c17", "-Wno-c23-extensions", "-o", "c", "c.c"], cwd=control_dir,
                         timeout=120, env=c_runner.compile_env(control_dir))
        assert built.code == 0, f"control compile failed, so the denial proves nothing: {built.stderr[-400:]}"
        ran = host.run([str(control_dir / "c")], cwd=control_dir, timeout=30, env=host.program_env())
        assert token in ran.stdout, f"control did not read the secret: {ran.stdout[:200]!r}"
        return "read"
    finally:
        shutil.rmtree(control_dir, ignore_errors=True)


def test_compile_cannot_include_outside_files():
    """Rereview P2-A, through capture: compile mode reads file contents only from the program's temp dir
    and the toolchain. The program `#include`s a secret that is a valid C string literal (no warning,
    no pragma, plain C17). Under the sandbox it fails to compile and the token appears nowhere."""
    secret_dir, secret, token = _secret(text='"@TOKEN@"\n')
    work = host.make_tmp("security-include-src-")
    try:
        src = work / "inc.c"
        src.write_text('#include <stdio.h>\nstatic const char s[] =\n#include "' + str(secret) + '"\n;\n'
                       'int main(void) {\n    puts(s);\n    return 0;\n}\n')
        tmp = kit.make_lesson("sec-include-", [kit.program("p1", src)], [kit.fact("f.x", "p1", 1)])
        try:
            e = _expect(tmp, errors.CompileError)
            assert "not permitted" in e.detail["stderr"] or "not found" in e.detail["stderr"], e.detail
            assert token not in json.dumps(e.as_dict(), default=str), "the secret leaked into the error"
            assert not (tmp / "build" / "capture" / "p1.stdout").exists()
        finally:
            kit.cleanup(tmp)
        return {"sandboxed": e.kind, "control": _unsandboxed_control(src, token)}
    finally:
        shutil.rmtree(secret_dir, ignore_errors=True)
        shutil.rmtree(work, ignore_errors=True)


def test_compile_cannot_embed_outside_files():
    """The sandbox layer under the source guard: capture refuses `#embed` by name before compiling
    (test_capture.py::test_bypass_embed), so this drives the compile step directly with no pragma.
    clang's C23-extension warning is just recorded there; the sandboxed read must still fail."""
    secret_dir, secret, token = _secret()
    tmp = host.make_tmp("security-embed-")
    try:
        src = tmp / "embed.c"
        src.write_text((kit.HERE / "embed.c.in").read_text().replace("@SECRET@", str(secret)))
        assert "#pragma" not in src.read_text(), "the embed fixture must not silence anything"
        try:
            c_runner.compile_program(src, tmp, "embed")
        except errors.CompileError as e:
            assert "not permitted" in e.detail["stderr"] or "not found" in e.detail["stderr"], e.detail
            assert token not in json.dumps(e.as_dict(), default=str), "the secret leaked into the error"
        else:
            raise AssertionError("the sandboxed compile embedded a file outside its dirs")
        return {"sandboxed": "CompileError", "control": _unsandboxed_control(src, token)}
    finally:
        shutil.rmtree(secret_dir, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- review WP2 P1-2: symlinks and stderr

def test_symlinked_program_refused():
    """P1-2: programs/p1.c as a symlink to a secret, and programs/ itself as a symlink to a dir holding
    one, are refused by validate (pointer) and by capture (no symlink is ever followed). The secret's
    bytes appear in no error, no stdout/stderr of `ptk build`, and not in build/build-report.json."""
    secret_dir, secret, token = _secret(text="@TOKEN@ is not C at all\nline two of the secret\n")
    seen = {}
    try:
        for variant in ("file", "dir"):
            tmp = kit.make_lesson(f"sec-symlink-{variant}-", [kit.program("p1", "hello.c")],
                                  [kit.fact("f.x", "p1", 1, {"value": "hello", "reviewed": True})])
            try:
                if variant == "file":
                    (tmp / "programs" / "hello.c").unlink()
                    (tmp / "programs" / "hello.c").symlink_to(secret)
                else:
                    shutil.rmtree(tmp / "programs")
                    (secret.parent / "hello.c").symlink_to(secret)
                    (tmp / "programs").symlink_to(secret.parent)
                try:
                    model.validate(model.load(tmp))
                except errors.ModelReferenceError as e:
                    assert "/programs/0/path" in [x["pointer"] for x in e.detail["errors"]], e.detail
                    assert token not in json.dumps(e.as_dict(), default=str)
                else:
                    raise AssertionError(f"validate accepted a symlinked program ({variant})")
                try:
                    c_runner.capture_lesson(model.load(tmp))
                except errors.ModelReferenceError as e:
                    assert e.detail.get("pointer") == "/programs/0/path", e.detail
                    assert token not in json.dumps(e.as_dict(), default=str), "the secret leaked into the error"
                else:
                    raise AssertionError(f"capture followed a symlinked program ({variant})")
                res = host.run([*ptk_cmd(), "build", str(tmp), "--only", "still"], timeout=300)
                assert res.code == errors.EXIT_MODEL, f"build exited {res.code}: {res.stderr[-400:]}"
                assert token not in res.stdout + res.stderr, "the secret leaked into ptk build output"
                rep = (tmp / "build" / "build-report.json").read_text()
                assert token not in rep and "line two of the secret" not in rep, "the secret leaked into the report"
                seen[variant] = json.loads(rep)["error"]["message"][:120]
            finally:
                if variant == "dir":
                    (secret.parent / "hello.c").unlink(missing_ok=True)
                kit.cleanup(tmp)
        return seen
    finally:
        shutil.rmtree(secret_dir, ignore_errors=True)


def test_compile_stderr_keeps_only_lesson_files():
    """P1-2: compiler stderr that reaches a report keeps diagnostics about the lesson's own file only.
    A readable system file that is not C (/usr/share/dict/words) quoted by clang is redacted."""
    words = Path("/usr/share/dict/words")
    if not words.is_file():
        from ptk.selftest import NotRun
        raise NotRun("no /usr/share/dict/words on this host")
    src = '#include <stdio.h>\nint main(void) {\n    return undeclared_name;\n}\n#include "/usr/share/dict/words"\n'
    tmp = kit.make_lesson("sec-redact-", [kit.program_text("p1", "p1.c", src)], [kit.fact("f.x", "p1", 1)])
    try:
        e = _expect(tmp, errors.CompileError)
        err = e.detail["stderr"]
        assert "p1.c:3:" in err and "undeclared_name" in err, f"the lesson's own diagnostic was dropped: {err[:600]}"
        assert "/usr/share/dict/words:" not in err, f"a diagnostic about another file was kept: {err[:800]}"
        assert "redacted" in err, err[-400:]
        return {"kept": [ln for ln in err.splitlines() if ln.startswith("p1.c:")][:3]}
    finally:
        kit.cleanup(tmp)


# ---------------------------------------------------------------- review WP2 P2-1, P2-2: compile limits and env

def test_compile_memory_cap():
    """P2-1: the compile runs under the process-group RSS watchdog. A source that makes clang allocate
    gigabytes is killed at a low cap, nothing of it survives, and the temp dir is gone."""
    saved = c_runner.COMPILE_MAX_RSS_KB
    token = f"heavy{secrets.token_hex(4)}"
    try:
        c_runner.COMPILE_MAX_RSS_KB = 256 * 1024
        before = _cap_dirs()
        tmp = kit.make_lesson("sec-heavy-", [kit.program_text(token, f"{token}.c",
                                                               (kit.HERE / "heavy_compile.c").read_text())],
                              [kit.fact("f.x", token, 1)])
        try:
            e = _expect(tmp, errors.MemoryLimitExceeded)
            assert e.detail["peak_rss_kb"] > 256 * 1024, e.detail
            assert not _survivors(token), f"compiler processes survived: {_survivors(token)}"
            assert not (_cap_dirs() - before), "capture temp dirs left behind"
            return {"error": e.kind, "peak_rss_kb": e.detail["peak_rss_kb"]}
        finally:
            kit.cleanup(tmp)
    finally:
        c_runner.COMPILE_MAX_RSS_KB = saved


HOSTILE_ENV = {"CCC_OVERRIDE_OPTIONS": "x-fsanitize=undefined,address +-Wno-format +-w",
               "CPATH": "/nonexistent-cpath", "C_INCLUDE_PATH": "/nonexistent", "LIBRARY_PATH": "/nonexistent",
               "MallocNanoZone": "1", "SDKROOT": "/nonexistent-sdk", "CCC_ADD_ARGS": "-w"}


def test_compile_env_is_an_allowlist():
    """P2-2: the compiler gets an allowlist env. With CCC_OVERRIDE_OPTIONS set to strip the sanitizers
    and silence warnings, the ASan and -Wformat fixtures are still blocked; the driver check itself
    also catches the override when it is handed a hostile env directly."""
    saved = {k: os.environ.get(k) for k in HOSTILE_ENV}
    seen = {}
    try:
        os.environ.update(HOSTILE_ENV)
        env = c_runner.compile_env(host.state_path("tmp"))
        assert not set(env) & set(HOSTILE_ENV), f"hostile vars reached the compiler: {set(env) & set(HOSTILE_ENV)}"
        assert set(env) <= {"PATH", "TMPDIR", "LANG", "LC_ALL", "HOME"}, sorted(env)
        for fixture, needle in (("asan_heap.c", "AddressSanitizer"), ("format_warning.c", "-Wformat")):
            tmp = kit.make_lesson("sec-env-", [kit.program("p1", fixture)], [kit.fact("f.x", "p1", 1)])
            try:
                e = _expect(tmp, errors.SanitizerFinding)
                assert needle in e.detail["stderr"], e.detail
                seen[fixture] = e.kind
            finally:
                kit.cleanup(tmp)
        problems = c_runner.driver_problems({**env, "CCC_OVERRIDE_OPTIONS": HOSTILE_ENV["CCC_OVERRIDE_OPTIONS"]})
        assert problems, "the driver check did not notice CCC_OVERRIDE_OPTIONS stripping the sanitizers"
        assert not c_runner.driver_problems(env), c_runner.driver_problems(env)
        seen["driver_check_with_override"] = problems[:3]
        return seen
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_kill_group_eperm_only_ignored_after_reap():
    """host._kill_group ignores macOS's zombie-group EPERM only once the leader is reaped. With a live
    leader, EPERM means the kill failed, and it must still raise."""
    import types
    real = os.killpg

    def eperm(pid, sig):
        raise PermissionError(1, "Operation not permitted")

    try:
        os.killpg = eperm
        reaped = types.SimpleNamespace(pid=999999, poll=lambda: 0)
        host._kill_group(reaped)  # leader gone: nothing to kill, no error
        alive = types.SimpleNamespace(pid=999999, poll=lambda: None)
        try:
            host._kill_group(alive)
        except PermissionError:
            pass
        else:
            raise AssertionError("EPERM with a live leader was swallowed")
    finally:
        os.killpg = real
    return {"reaped": "ignored", "alive": "raised"}
