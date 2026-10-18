"""Sandboxed C capture (AC-2.2..2.6, E19, E24).

For each program:
  1. refuse unless sandbox-exec exists (SandboxUnavailable, exit 2, nothing runs);
  2. clang -std=c17 -Wall -Wextra -Wformat=2 -fsanitize=undefined,address under the
     sandbox `compile` profile (file contents readable only from the temp dir and the toolchain,
     so `#embed "~/secret"` fails); any warning blocks unless an undefined-behaviour claim that
     lists the program in `programs` covers it (and such a program is `ub: true`);
  3. gcc-16 -c (object discarded) with the same warnings: diagnostics only, recorded, never run;
  4. ub:true programs compile but never run;
  5. run twice under the `run` profile (no network, no fork, writes only in its temp dir),
     1 MB output cap, RSS watchdog over the process group, 5 s timeout;
  6. both runs must match byte for byte; stdout sha256 and the selected lines become facts.
Platform facts come from a probe program run the same way.

A clean run is recorded as "no finding", never as "no UB" (E19): sanitizers see one execution.
"""
import hashlib
import platform as pyplatform
import shutil
from pathlib import Path

from .. import errors, host

CLANG_FLAGS = ["-std=c17", "-Wall", "-Wextra", "-Wformat=2", "-fsanitize=undefined,address", "-g", "-O0"]
GCC_FLAGS = ["-std=c17", "-Wall", "-Wextra", "-Wformat=2", "-c"]
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


_TOOLCHAIN = {}


def toolchain_params():
    """DEVDIR and GCCROOT for the compile profile's read allowlist, realpath'd and cached."""
    if not _TOOLCHAIN:
        dev = Path(host.run(["/usr/bin/xcode-select", "-p"], timeout=30, check=True).stdout.strip()).resolve()
        if dev.parent.name == "Contents" and dev.parent.parent.suffix == ".app":
            dev = dev.parent.parent
        gcc = Path(host.which("gcc-16")).resolve().parent.parent  # <prefix>/bin/gcc-16 -> <prefix>
        if gcc.parent.parent.name == "Cellar":  # Homebrew: cc1 links gmp/mpfr/isl from sibling kegs
            gcc = gcc.parent.parent
        _TOOLCHAIN.update(DEVDIR=str(dev), GCCROOT=str(gcc))
    return dict(_TOOLCHAIN)


def compile_sandboxed(cmd, tmp, timeout=120):
    """Run a compiler under MODE=compile. Its scratch files go to the per-call temp dir."""
    sb = host.sandboxed(cmd, "compile", tmp=tmp, proj=tmp)
    extra = [x for k, v in toolchain_params().items() for x in ("-D", f"{k}={v}")]
    sb[1:1] = extra
    return host.run(sb, cwd=tmp, timeout=timeout, env=host.child_env({"TMPDIR": f"{Path(tmp).resolve()}/"}))


def compile_program(src_path, tmp, name="prog"):
    clang = host.which("clang")
    exe = tmp / name
    cmd = [clang, *CLANG_FLAGS, "-o", exe.name, Path(src_path).name]
    res = compile_sandboxed(cmd, tmp)
    if res.code != 0:
        raise errors.CompileError(f"clang failed on {Path(src_path).name}", stderr=res.stderr[-4000:])
    return exe, res.stderr, " ".join(["clang", *CLANG_FLAGS, Path(src_path).name])


def gcc_diagnostics(src_path, tmp):
    gcc = host.which("gcc-16")
    obj = tmp / (Path(src_path).stem + ".gcc.o")
    res = compile_sandboxed([gcc, *GCC_FLAGS, "-o", obj.name, Path(src_path).name], tmp)
    if res.code != 0:  # review P3-1: a gcc error is a compile error, not a diagnostic string
        raise errors.CompileError(f"gcc-16 failed on {Path(src_path).name}", stderr=res.stderr[-4000:])
    return res.stderr.strip()


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


def capture_program(lesson, program, tmp):
    src = tmp / Path(program["path"]).name
    shutil.copyfile(lesson.dir / program["path"], src)
    exe, warnings, cmd = compile_program(src, tmp, program["id"])
    diags = {"clang": warnings.strip()}
    diags["gcc-16"] = gcc_diagnostics(src, tmp)
    if "warning:" in warnings and not ub_covered(lesson, program):
        raise errors.SanitizerFinding(f"clang warning in {program['path']} and no undefined-behaviour claim covers it",
                                      stderr=warnings[-4000:], program=program["id"])
    out = {"program": program["id"], "diagnostics": diags, "source_sha256": _sha(src.read_bytes()), "ran": False}
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


def select(fact, cap, platform):
    sel = fact["select"]
    if sel["stream"] == "platform":
        val = platform
        for k in sel["key"].split("."):
            val = val[k]
        return str(val).lower() if isinstance(val, bool) else str(val)
    stdout = cap["stdout"]
    if "line" not in sel:
        return stdout
    lines = stdout.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if sel["line"] > len(lines):
        raise errors.ModelReferenceError(f"fact {fact['id']} selects stdout line {sel['line']} but "
                                         f"{fact['program']} printed {len(lines)} line(s)", stdout=stdout)
    return lines[sel["line"] - 1]


def capture_lesson(lesson):
    host.sandbox_exec()  # refuse before anything runs (AC-2.6)
    tmp = host.make_tmp("cap-")
    try:
        platform = capture_platform(tmp)
        caps = {}
        for prog in lesson.data["programs"]:
            ptmp = tmp / prog["id"]
            ptmp.mkdir()
            caps[prog["id"]] = capture_program(lesson, prog, ptmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for prog in lesson.data["programs"]:
        c = caps[prog["id"]]
        prog["diagnostics"] = c["diagnostics"]
        prog["source_sha256"] = c["source_sha256"]
    for fact in lesson.data["facts"]:
        c = caps[fact["program"]]
        if not c["ran"] and fact["select"]["stream"] == "stdout":
            raise errors.ModelReferenceError(f"fact {fact['id']} reads stdout of {fact['program']}, which never runs")
        fact["value"] = select(fact, c, platform)
        fact["source"] = {"compiler": platform["compilers"]["clang"], "cmd": c.get("cmd", "platform probe"),
                          "stdout_sha256": c.get("stdout_sha256", _sha("")), "runs": c.get("runs", 0),
                          "sandbox": "sandbox-exec MODE=run"}
    lesson.data["platform"] = platform
    lesson.save()
    out_dir = lesson.build_dir() / "capture"
    out_dir.mkdir(exist_ok=True)
    for pid, c in caps.items():
        if c["ran"]:
            (out_dir / f"{pid}.stdout").write_text(c["stdout"])
    return {"captured": True, "programs": {pid: {"ran": c["ran"], "stdout_sha256": c.get("stdout_sha256"),
                                                 "sanitizers": c["sanitizers"], "diagnostics": c["diagnostics"]}
                                           for pid, c in caps.items()},
            "facts": {f["id"]: f["value"] for f in lesson.data["facts"]}, "platform": platform}
