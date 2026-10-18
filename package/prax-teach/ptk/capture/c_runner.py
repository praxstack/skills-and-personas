"""Sandboxed C capture (AC-2.2..2.6, E19, E24).

For each program:
  1. refuse unless sandbox-exec exists (SandboxUnavailable, exit 2, nothing runs);
     read every program with no symlink followed and refuse any construct that switches off the
     guard (capture/guard.py, review WP2 P1-1/P1-2), before anything compiles;
  2. clang -std=c17 -Wall -Wextra -Wformat=2 -fsanitize=undefined,address under the
     sandbox `compile` profile (file contents readable only from the temp dir and the toolchain,
     so `#embed "~/secret"` fails); any warning blocks unless an undefined-behaviour claim that
     lists the program in `programs` covers it (and such a program is `ub: true`);
     Compiles get an allowlist env (no CCC_OVERRIDE_OPTIONS, CPATH, SDKROOT ...), --no-default-config,
     pinned compiler paths, an RSS watchdog over the process group, an output cap and a 30 s timeout;
     a `clang -###` check proves the sanitizer and warning flags reach cc1. clang -E output of the
     program file is scanned again, so a construct pasted together by a macro is refused too.
     Compiler stderr in errors and records keeps diagnostics about the program file only;
  3. gcc-16 -c (object discarded) with the same warnings: diagnostics only, recorded, never run;
  4. ub:true programs compile but never run;
  5. run twice under the `run` profile (no network, no fork, writes only in its temp dir),
     1 MB output cap, RSS watchdog over the process group, 5 s timeout;
  6. both runs must match byte for byte; stdout sha256 and the selected lines become facts.
Platform facts come from a probe program run the same way.

A clean run is recorded as "no finding", never as "no UB" (E19): sanitizers see one execution.
"""
import hashlib
import os
import platform as pyplatform
import shlex
import shutil
from pathlib import Path

from .. import errors, expect, host, model
from . import guard

CLANG_FLAGS = ["-std=c17", "-Wall", "-Wextra", "-Wformat=2", "-fsanitize=undefined,address", "-g", "-O0"]
GCC_FLAGS = ["-std=c17", "-Wall", "-Wextra", "-Wformat=2", "-c"]
# Hardening flags on every clang compile. Not part of `cmd` in fact provenance, which names the
# lesson flags; the capture report lists them per program under `guard`.
GUARD_FLAGS = ["--no-default-config"]
COMPILE_TIMEOUT = 30.0
COMPILE_MAX_RSS_KB = 2 * 1024 * 1024
COMPILE_MAX_OUTPUT = 8 << 20      # stderr/stdout in memory, and RLIMIT_FSIZE for objects and executables
PREPROCESS_MAX_OUTPUT = 16 << 20
RUN_TIMEOUT = 5.0
MAX_OUTPUT = 1 << 20
MAX_RSS_KB = 512 * 1024
SAN_ENV = {"ASAN_OPTIONS": "halt_on_error=1:abort_on_error=0:detect_leaks=0:symbolize=0",
           "UBSAN_OPTIONS": "halt_on_error=1:print_stacktrace=0"}
SAN_MARKERS = ("runtime error:", "ERROR: AddressSanitizer", "ERROR: UndefinedBehaviorSanitizer")

PLATFORM_C = r"""
#include <limits.h>
#include <stdio.h>
int main(void) {
    union { unsigned int u; unsigned char b[sizeof(unsigned int)]; } e = { 1u };
    printf("char %zu\nshort %zu\nint %zu\nlong %zu\nlong long %zu\nfloat %zu\ndouble %zu\nvoid* %zu\n",
           sizeof(char), sizeof(short), sizeof(int), sizeof(long), sizeof(long long),
           sizeof(float), sizeof(double), sizeof(void *));
    printf("char_signed %d\nendianness %s\n", CHAR_MIN < 0, e.b[0] == 1 ? "little" : "big");
    return 0;
}
"""


def _sha(s):
    return hashlib.sha256(s.encode() if isinstance(s, str) else s).hexdigest()


def ub_covered(lesson, program):
    """True when the program is ub:true and an undefined-behaviour claim lists it in `programs`."""
    return bool(program.get("ub")) and any(
        c["kind"] == "undefined-behaviour" and program["id"] in c.get("programs", []) for c in lesson.data["claims"])


# ---------------------------------------------------------------- compiler, env, limits (review WP2 P2-1, P2-2)

def clang_path():
    """The system clang, never whatever `clang` comes first on the caller's PATH."""
    return "/usr/bin/clang" if os.access("/usr/bin/clang", os.X_OK) else host.which("clang")


def gcc_path():
    for cand in ("/opt/homebrew/bin/gcc-16", "/usr/local/bin/gcc-16"):
        if os.access(cand, os.X_OK):
            return cand
    return host.which("gcc-16")


def compile_env(tmp):
    """Allowlist env for the compilers: nothing from the caller (CCC_OVERRIDE_OPTIONS, CPATH,
    C_INCLUDE_PATH, LIBRARY_PATH, SDKROOT, DEVELOPER_DIR, Malloc*) reaches clang or gcc-16."""
    return {"PATH": "/usr/bin:/bin", "TMPDIR": f"{Path(tmp).resolve()}/", "LANG": "C", "LC_ALL": "C"}


_TOOLCHAIN = {}


def toolchain_params():
    """DEVDIR and GCCROOT for the compile profile's read allowlist, realpath'd and cached."""
    if not _TOOLCHAIN:
        res = host.run(["/usr/bin/xcode-select", "-p"], timeout=30, check=True, env=compile_env(host.state_path("tmp")))
        dev = Path(res.stdout.strip()).resolve()
        if dev.parent.name == "Contents" and dev.parent.parent.suffix == ".app":
            dev = dev.parent.parent
        gcc = Path(gcc_path()).resolve().parent.parent  # <prefix>/bin/gcc-16 -> <prefix>
        if gcc.parent.parent.name == "Cellar":  # Homebrew: cc1 links gmp/mpfr/isl from sibling kegs
            gcc = gcc.parent.parent
        _TOOLCHAIN.update(DEVDIR=str(dev), GCCROOT=str(gcc))
    return dict(_TOOLCHAIN)


def compile_sandboxed(cmd, tmp, max_output=COMPILE_MAX_OUTPUT, what="compile"):
    """Run a compiler under MODE=compile with the allowlist env, the RSS watchdog over its process
    group (driver, cc1, ld), an output cap and a timeout. Scratch files go to the per-call temp dir."""
    sb = host.sandboxed(cmd, "compile", tmp=tmp, proj=tmp)
    sb[1:1] = [x for k, v in toolchain_params().items() for x in ("-D", f"{k}={v}")]
    res = host.run_limited(sb, cwd=tmp, timeout=COMPILE_TIMEOUT, max_output=max_output,
                           max_rss_kb=COMPILE_MAX_RSS_KB, env=compile_env(tmp))
    name = Path(cmd[0]).name
    if res.killed_reason == "memory":
        raise errors.MemoryLimitExceeded(f"{name} {what} exceeded {COMPILE_MAX_RSS_KB // 1024} MB resident; "
                                         "process group killed", peak_rss_kb=res.peak_rss_kb)
    if res.killed_reason == "timeout":
        raise errors.CompileError(f"{name} {what} ran over {COMPILE_TIMEOUT:g}s; process group killed",
                                  seconds=res.seconds)
    if res.killed_reason == "output" or res.truncated:
        raise errors.OutputLimitExceeded(f"{name} {what} wrote more than {max_output} bytes; killed")
    return res


_DRIVER_BASE = []


def _cc1_args(env, flags):
    tmp = host.make_tmp("driver-")
    try:
        (tmp / "x.c").write_text("int main(void) { return 0; }\n")
        res = host.run([clang_path(), "-###", *flags, "-o", "x", "x.c"], cwd=tmp, timeout=60, env=env)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    line = next((ln for ln in res.stderr.splitlines() if '"-cc1"' in ln), None)
    return shlex.split(line) if line else None


def driver_problems(env=None):
    """What stops the lesson flags reaching cc1 under env (default: the compile env). `clang -###`
    prints the cc1 command without compiling. The sanitizers and each warning flag must be there,
    with no -w and no -Wno-X beyond the driver's own defaults (from a bare `-###`, same clean env)."""
    clean = compile_env(host.state_path("tmp"))
    if not _DRIVER_BASE:
        _DRIVER_BASE.append(set(_cc1_args(clean, [*GUARD_FLAGS, "-std=c17", "-c"]) or []))
    args = _cc1_args(env or clean, [*GUARD_FLAGS, *CLANG_FLAGS])
    if args is None:
        return ["clang -### printed no cc1 command"]
    problems = []
    for flag in ("-std=c17", "-Wall", "-Wextra", "-Wformat=2"):
        if flag not in args:
            problems.append(f"{flag} missing from cc1")
    san = ",".join(a.split("=", 1)[1] for a in args if a.startswith("-fsanitize="))
    for group in ("address", "signed-integer-overflow", "shift-exponent", "null"):
        if group not in san.split(","):
            problems.append(f"sanitizer {group} missing from cc1")
    problems += [f"{a} reaches cc1" for a in args
                 if a == "-w" or (a.startswith("-Wno-") and not a.startswith("-Wno-error=") and a not in _DRIVER_BASE[0])]
    return problems


def check_driver():
    problems = driver_problems()
    if problems:
        raise errors.ToolFailed("clang driver check failed: the lesson flags do not reach the compiler as written",
                                problems=problems)


def compile_program(src_path, tmp, name="prog"):
    src = Path(src_path).name
    exe = tmp / name
    res = compile_sandboxed([clang_path(), *GUARD_FLAGS, *CLANG_FLAGS, "-o", exe.name, src], tmp)
    if res.code != 0:
        raise errors.CompileError(f"clang failed on {src}", stderr=guard.filter_stderr(res.stderr, [src]))
    return exe, res.stderr, " ".join(["clang", *CLANG_FLAGS, src])


def preprocessed_findings(src_path, tmp):
    """Constructs in clang's own -E output for the program file (a macro can paste one together)."""
    src = Path(src_path).name
    res = compile_sandboxed([clang_path(), *GUARD_FLAGS, *CLANG_FLAGS, "-E", src], tmp,
                            max_output=PREPROCESS_MAX_OUTPUT, what="preprocess")
    if res.code != 0:
        raise errors.CompileError(f"clang -E failed on {src}", stderr=guard.filter_stderr(res.stderr, [src]))
    return guard.scan_preprocessed(res.stdout, src)


def gcc_diagnostics(src_path, tmp):
    src = Path(src_path).name
    obj = tmp / (Path(src_path).stem + ".gcc.o")
    res = compile_sandboxed([gcc_path(), *GCC_FLAGS, "-o", obj.name, src], tmp)
    if res.code != 0:  # review P3-1: a gcc error is a compile error, not a diagnostic string
        raise errors.CompileError(f"gcc-16 failed on {src}", stderr=guard.filter_stderr(res.stderr, [src]))
    return guard.filter_stderr(res.stderr.strip(), [src])


def run_program(exe, tmp, args=()):
    res = host.run_limited(host.sandboxed([exe, *args], "run", tmp=tmp), cwd=tmp, timeout=RUN_TIMEOUT,
                           max_output=MAX_OUTPUT, max_rss_kb=MAX_RSS_KB, env=host.program_env(SAN_ENV))
    if res.killed_reason == "timeout":
        raise errors.RunTimeout(f"{exe.name} ran over {RUN_TIMEOUT:g}s; process group killed", seconds=res.seconds)
    if res.killed_reason == "memory":
        raise errors.MemoryLimitExceeded(f"{exe.name} exceeded {MAX_RSS_KB // 1024} MB resident; killed",
                                         peak_rss_kb=res.peak_rss_kb)
    if res.killed_reason == "output" or res.truncated:
        raise errors.OutputLimitExceeded(f"{exe.name} wrote more than {MAX_OUTPUT} bytes; killed")
    if any(m in res.stderr for m in SAN_MARKERS):
        raise errors.SanitizerFinding(f"sanitizer report from {exe.name}", stderr=res.stderr[-4000:])
    if res.code != 0:
        raise errors.RunCrashed(f"{exe.name} exited {res.code}", code=res.code, stderr=res.stderr[-4000:])
    return res


def guard_program(lesson, index):
    """Read program `index` safely and refuse source-level constructs (review WP2 P1-1, P1-2).
    Returns (bytes, allowed constructs)."""
    program = lesson.data["programs"][index]
    pointer = f"/programs/{index}/path"
    data = guard.read_program(lesson.dir, program["path"], pointer)
    allowed = guard.allowed_constructs(lesson.data, program)
    err = guard.refusal(guard.scan_source(data.decode("utf-8", "replace")), allowed, program["path"], pointer, "source")
    if err:
        raise err
    return data, allowed


def capture_program(lesson, program, tmp, source=None, allowed=frozenset(), index=None):
    if index is None:
        index = lesson.data["programs"].index(program)
    if source is None:
        source, allowed = guard_program(lesson, index)
    src = tmp / Path(program["path"]).name
    src.write_bytes(source)
    exe, warnings, cmd = compile_program(src, tmp, program["id"])
    err = guard.refusal(preprocessed_findings(src, tmp), allowed, program["path"], f"/programs/{index}/path",
                        "preprocessed")
    if err:
        raise err
    shown = guard.filter_stderr(warnings.strip(), [src.name])
    diags = {"clang": shown}
    diags["gcc-16"] = gcc_diagnostics(src, tmp)
    if "warning:" in warnings and not ub_covered(lesson, program):
        raise errors.SanitizerFinding(f"clang warning in {program['path']} and no undefined-behaviour claim covers it",
                                      stderr=shown, program=program["id"])
    out = {"program": program["id"], "diagnostics": diags, "source_sha256": _sha(source), "ran": False,
           "guard": {"flags": GUARD_FLAGS, "scans": ["source", "preprocessed"], "overrides": sorted(allowed)}}
    if program.get("ub"):
        return {**out, "sanitizers": "not run (ub)"}  # compiled, never run
    if not program.get("run", True):
        return {**out, "sanitizers": "not run"}
    first = run_program(exe, tmp, program.get("args", []))
    second = run_program(exe, tmp, program.get("args", []))
    if first.stdout != second.stdout:
        raise errors.NondeterministicOutput(f"{program['id']}: the two runs differ", run1=first.stdout[:4000],
                                            run2=second.stdout[:4000])
    out.update(ran=True, stdout=first.stdout, stdout_sha256=_sha(first.stdout), runs=2,
               sanitizers="no finding",
               cmd=f"{cmd} && ./{program['id']} (sandbox-exec MODE=run, run twice)")
    return out


def capture_platform(tmp):
    src = tmp / "platform.c"
    src.write_text(PLATFORM_C)
    exe, _w, _cmd = compile_program(src, tmp, "platform")
    res = run_program(exe, tmp)
    sizes, info = {}, {}
    for line in res.stdout.splitlines():
        key, _, val = line.rpartition(" ")
        if key in ("char_signed", "endianness"):
            info[key] = val
        else:
            sizes[key] = int(val)
    mac = pyplatform.mac_ver()[0]
    return {"captured": True, "os": f"macOS {mac}", "arch": pyplatform.machine(), "sizeof": sizes,
            "char_signed": info["char_signed"] == "1", "endianness": info["endianness"],
            "libc": f"libSystem (macOS {mac})",
            "compilers": {"clang": host.tool_version("clang"), "gcc-16": host.tool_version("gcc-16")},
            "sandbox": "sandbox-exec ptk/capture/sandbox.sb"}


class _Missing:
    """A stdout line the run never printed (review WP2 P2-3): an expectation mismatch, not a model error."""

    def __init__(self, reason):
        self.reason = reason


def select(fact, cap, platform, index=0):
    sel = fact["select"]
    if sel["stream"] == "platform":
        pointer = f"/facts/{index}/select/key"
        why = model.platform_key_problem(sel["key"])
        val = platform
        for k in sel["key"].split("."):
            if why or not isinstance(val, dict) or k not in val:
                raise errors.ModelReferenceError(f"fact {fact['id']}: {why or 'no platform value at ' + sel['key']}",
                                                 pointer=pointer)
            val = val[k]
        return str(val).lower() if isinstance(val, bool) else str(val)
    stdout = cap["stdout"]
    if "line" not in sel:
        return stdout
    lines = stdout.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if sel["line"] > len(lines):
        return _Missing(f"{fact['program']} printed {len(lines)} line(s); the fact selects line {sel['line']}")
    line = lines[sel["line"] - 1]
    if "field" not in sel:
        return line
    fields = line.split()
    if sel["field"] > len(fields):
        return _Missing(f"line {sel['line']} of {fact['program']} has {len(fields)} field(s); the fact selects field "
                        f"{sel['field']}")
    return fields[sel["field"] - 1]


def capture_lesson(lesson):
    host.sandbox_exec()  # refuse before anything runs (AC-2.6)
    # Review WP2 P1-1/P1-2/P2-4: refuse unsafe programs and impossible platform keys before any compile.
    sources = {p["id"]: guard_program(lesson, i) for i, p in enumerate(lesson.data["programs"])}
    for i, f in enumerate(lesson.data["facts"]):
        if f["select"]["stream"] == "platform":
            why = model.platform_key_problem(f["select"]["key"])
            if why:
                raise errors.ModelReferenceError(f"fact {f['id']}: {why}", pointer=f"/facts/{i}/select/key")
    check_driver()
    tmp = host.make_tmp("cap-")
    try:
        platform = capture_platform(tmp)
        caps = {}
        for i, prog in enumerate(lesson.data["programs"]):
            ptmp = tmp / prog["id"]
            ptmp.mkdir()
            data, allowed = sources[prog["id"]]
            caps[prog["id"]] = capture_program(lesson, prog, ptmp, data, allowed, i)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    missing = []
    for prog in lesson.data["programs"]:
        c = caps[prog["id"]]
        prog["diagnostics"] = c["diagnostics"]
        prog["source_sha256"] = c["source_sha256"]
    for i, fact in enumerate(lesson.data["facts"]):
        c = caps[fact["program"]]
        if not c["ran"] and fact["select"]["stream"] == "stdout":
            raise errors.ModelReferenceError(f"fact {fact['id']} reads stdout of {fact['program']}, which never runs",
                                             pointer=f"/facts/{i}/select/stream")
        val = select(fact, c, platform, i)
        if isinstance(val, _Missing):
            missing.append({"fact": fact["id"], "captured": None, "expected": expect.evaluate(fact["expect"], platform),
                            "reason": val.reason})
            continue
        fact["value"] = val
        fact["source"] = {"compiler": platform["compilers"]["clang"], "cmd": c.get("cmd", "platform probe"),
                          "stdout_sha256": c.get("stdout_sha256", _sha("")), "runs": c.get("runs", 0),
                          "sandbox": "sandbox-exec MODE=run"}
    if missing:  # nothing is saved: the run differs from what the model expects
        raise errors.ExpectationMismatch(f"{len(missing)} fact(s) select output the program never printed",
                                         mismatches=missing)
    lesson.data["platform"] = platform
    lesson.save()
    out_dir = lesson.build_dir() / "capture"
    out_dir.mkdir(exist_ok=True)
    for pid, c in caps.items():
        if c["ran"]:
            (out_dir / f"{pid}.stdout").write_text(c["stdout"])
    return {"captured": True, "programs": {pid: {"ran": c["ran"], "stdout_sha256": c.get("stdout_sha256"),
                                                 "sanitizers": c["sanitizers"], "diagnostics": c["diagnostics"],
                                                 "guard": c["guard"]}
                                           for pid, c in caps.items()},
            "facts": {f["id"]: f["value"] for f in lesson.data["facts"]}, "platform": platform}
