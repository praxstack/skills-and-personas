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


def test_compile_cannot_embed_outside_files():
    """Rereview P2-A: compile mode reads file contents only from the program's temp dir and the toolchain.

    The fixture `#embed`s a secret file under $HOME (in $PTK_STATE, outside the capture temp dir) with
    the C23-extension warning silenced, then prints it. Under the sandbox it must fail to compile.
    The same source compiled outside the sandbox does embed and print the secret, so the denial is
    the sandbox's doing.
    """
    secret_dir = host.make_tmp("security-secret-")
    work = host.make_tmp("security-embed-src-")
    try:
        secret = secret_dir / "secret.txt"
        token = f"SECRET-{secrets.token_hex(8)}"
        secret.write_text(token + "\n")
        assert secret.resolve().is_relative_to(Path.home().resolve()), "the secret must live under $HOME"
        src = work / "embed.c"
        src.write_text((kit.HERE / "embed.c.in").read_text().replace("@SECRET@", str(secret.resolve())))

        tmp = kit.make_lesson("sec-embed-", [kit.program("p1", src)], [kit.fact("f.x", "p1", 1)])
        try:
            e = _expect(tmp, errors.CompileError)
            assert "not permitted" in e.detail["stderr"] or "not found" in e.detail["stderr"], e.detail
            assert token not in json.dumps(e.as_dict(), default=str), "the secret leaked into the error"
            assert not (tmp / "build" / "capture" / "p1.stdout").exists()
        finally:
            kit.cleanup(tmp)

        control_dir = host.make_tmp("security-embed-control-")
        try:
            clang = host.which("clang")
            shutil.copyfile(src, control_dir / "embed.c")
            built = host.run([clang, "-std=c17", "-o", "embed", "embed.c"], cwd=control_dir, timeout=120)
            assert built.code == 0, f"control compile failed, so the denial proves nothing: {built.stderr[-400:]}"
            ran = host.run([str(control_dir / "embed")], cwd=control_dir, timeout=30)
            assert ran.stdout.strip() == token, f"control did not embed the secret: {ran.stdout[:200]!r}"
        finally:
            shutil.rmtree(control_dir, ignore_errors=True)
        return {"sandboxed": e.kind, "control": "embedded"}
    finally:
        shutil.rmtree(secret_dir, ignore_errors=True)
        shutil.rmtree(work, ignore_errors=True)
