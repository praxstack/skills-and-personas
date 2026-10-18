"""Capture `run` profile (D17.10, E24, review P1-4): deny-default.

A probe program, built with the lesson flags (ASan + UBSan), tries one thing per run under
sandbox-exec MODE=run. Each forbidden action must be denied inside the sandbox, and the same
binary run outside the sandbox must succeed at it, so the denial is the sandbox's doing.
Mach probes only look services up; nothing is sent, and no app is launched.
"""
import shutil
from pathlib import Path

from ptk import host
from ptk.capture import c_runner

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
