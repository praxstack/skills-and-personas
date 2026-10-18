"""Host boundary: paths, the child-process env contract, subprocess, probe and setup.

Only this module and ptk/node.py call subprocess (AC-8.7). Everything that touches an
external tool (compilers, sandbox-exec, ffmpeg, whisper-cli, tesseract, the Kokoro venv,
npm, pip) goes through `run()` or `run_limited()` here.

Env contract (spec §5.5), applied by child_env() to every child:
    HYPERFRAMES_SKIP_SKILLS=1  HYPERFRAMES_NO_UPDATE_CHECK=1  HYPERFRAMES_NO_TELEMETRY=1
    DO_NOT_TRACK=1  HYPERFRAMES_NO_AUTO_INSTALL=1  PLAYWRIGHT_BROWSERS_PATH=$PTK_STATE/browsers
    SOURCE_DATE_EPOCH (from the lesson sha256)
plus: secret API keys stripped, npm/pip caches inside $PTK_STATE.
"""
import hashlib
import json
import os
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from . import errors

PKG = Path(__file__).resolve().parent.parent          # package/prax-teach
REGISTRY = PKG / "registry" / "tools.json"
SANDBOX_PROFILE = PKG / "ptk" / "capture" / "sandbox.sb"
FONTS_DIR = PKG / "assets" / "fonts"

SECRET_VARS = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "HEYGEN_API_KEY", "HEYGEN_ACCESS_TOKEN",
               "HYPERFRAMES_API_KEY", "ELEVENLABS_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY",
               "ANTHROPIC_API_KEY", "FIGMA_TOKEN", "GITHUB_TOKEN", "GITHUB_PERSONAL_ACCESS_TOKEN",
               "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "GCS_CREDS", "CURSOR_API_KEY")
CONTRACT = {
    "HYPERFRAMES_SKIP_SKILLS": "1",
    "HYPERFRAMES_NO_UPDATE_CHECK": "1",
    "HYPERFRAMES_NO_TELEMETRY": "1",
    "HYPERFRAMES_NO_AUTO_INSTALL": "1",
    "DO_NOT_TRACK": "1",
}


# ---------------------------------------------------------------- paths

def state_dir():
    """$PTK_STATE, else the dev layout's v2.1/.state, else ~/.local/share/prax-teach."""
    env = os.environ.get("PTK_STATE")
    if env:
        p = Path(env)
    else:
        dev = PKG.parent.parent / ".state"
        p = dev if dev.is_dir() else Path.home() / ".local" / "share" / "prax-teach"
    p.mkdir(parents=True, exist_ok=True)
    return p.resolve()


def state_path(*parts):
    return state_dir().joinpath(*parts)


def registry():
    return json.loads(REGISTRY.read_text())


def source_date_epoch(lesson_sha256):
    """Deterministic epoch inside 2020..2023 taken from the lesson hash."""
    return str(1_577_836_800 + int(lesson_sha256[:8], 16) % 126_230_400)


def child_env(extra=None, lesson_sha256=None, node_home=False):
    env = {k: v for k, v in os.environ.items() if k not in SECRET_VARS}
    env.update(CONTRACT)
    st = state_dir()
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(st / "browsers")
    env["npm_config_cache"] = str(st / "npm-cache")
    env["npm_config_update_notifier"] = "false"
    env["PIP_CACHE_DIR"] = str(st / "pip-cache")
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    env["SOURCE_DATE_EPOCH"] = source_date_epoch(lesson_sha256 or "0" * 64)
    if node_home:
        # HyperFrames writes ~/.hyperframes and ~/.cache/hyperframes: keep both inside $PTK_STATE.
        home = st / "home"
        home.mkdir(exist_ok=True)
        env["HOME"] = str(home)
        env["HYPERFRAMES_FONT_CACHE_DIR"] = str(st / "home" / "fonts")
        chrome = hyperframes_chrome()
        if chrome:
            env["HYPERFRAMES_BROWSER_PATH"] = str(chrome)
        kpy = st / "venvs" / "kokoro" / "bin" / "python"
        if kpy.exists():
            env["HYPERFRAMES_PYTHON"] = str(kpy)
    if extra:
        env.update(extra)
    return env


def program_env(extra=None):
    """Allowlist env for an untrusted lesson program (review P3-3): nothing from the parent leaks in."""
    env = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"}
    env.update(extra or {})
    return env


def hyperframes_chrome():
    reg = registry()["hyperframes_chrome"]
    p = state_path("browsers", "hyperframes", reg["dir"], reg["binary"])
    return p if p.exists() else None


# ---------------------------------------------------------------- subprocess

@dataclass
class Result:
    cmd: list
    code: int
    stdout: str
    stderr: str
    seconds: float
    timed_out: bool = False
    killed_reason: str = ""
    peak_rss_kb: int = 0
    truncated: bool = False
    extra: dict = field(default_factory=dict)


def which(tool, required=True):
    path = shutil.which(tool)
    if not path and required:
        hint = registry().get("install_hints", {}).get(tool, "see `ptk host probe`")
        raise errors.HostToolMissing(f"{tool} not found: {hint}", tool=tool)
    return path


def run(cmd, cwd=None, env=None, timeout=600, input_text=None, check=False):
    """Run a tool to completion with a timeout; kill its whole process group on timeout."""
    cmd = [str(c) for c in cmd]
    t0 = time.monotonic()
    proc = subprocess.Popen(cmd, cwd=cwd, env=env or child_env(), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, stdin=subprocess.PIPE if input_text else subprocess.DEVNULL,
                            text=True, start_new_session=True)
    try:
        out, err = proc.communicate(input_text, timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        _kill_group(proc)
        out, err = proc.communicate()
        timed_out = True
    res = Result(cmd, proc.returncode, out, err, time.monotonic() - t0, timed_out)
    if check and (res.code != 0 or timed_out):
        raise errors.ToolFailed(f"{Path(cmd[0]).name} exited {res.code}", cmd=cmd,
                                stderr=(err or "")[-4000:], stdout=(out or "")[-2000:])
    return res


def _kill_group(proc):
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except PermissionError:
        # macOS: once the leader is reaped, killpg on a group left with only zombies (children
        # reparented to launchd, not yet collected) fails with EPERM. Nothing is left to kill then.
        # With a live leader, EPERM means the kill really failed, so it still raises.
        if proc.poll() is None:
            raise


def _group_rss_kb(pgid):
    """Resident size of every process in the group, in KB (macOS has no RLIMIT_AS)."""
    out = subprocess.run(["/bin/ps", "-A", "-o", "pgid=,rss="], capture_output=True, text=True).stdout
    total = 0
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] == str(pgid):
            total += int(parts[1])
    return total


def run_limited(cmd, cwd, timeout, max_output, max_rss_kb, env=None):
    """Run an untrusted program: output cap, RSS watchdog over the process group, group kill.

    Used by capture/c_runner.py for the sandboxed program run. Returns Result with
    timed_out / killed_reason / truncated set; the caller maps them to error classes.
    """
    import resource

    def limits():
        resource.setrlimit(resource.RLIMIT_CPU, (int(timeout) + 1, int(timeout) + 1))
        resource.setrlimit(resource.RLIMIT_FSIZE, (max_output, max_output))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    cmd = [str(c) for c in cmd]
    t0 = time.monotonic()
    proc = subprocess.Popen(cmd, cwd=cwd, env=env or child_env(), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, start_new_session=True,
                            preexec_fn=limits)
    bufs = {"out": bytearray(), "err": bytearray()}
    state = {"truncated": False, "reason": "", "peak": 0}

    def pump(stream, key):
        while True:
            chunk = stream.read(65536)
            if not chunk:
                return
            room = max_output + 1 - len(bufs[key])
            bufs[key] += chunk[:max(room, 0)]
            if len(bufs[key]) > max_output and not state["truncated"]:
                state["truncated"] = True
                state["reason"] = state["reason"] or "output"
                _kill_group(proc)

    threads = [threading.Thread(target=pump, args=(proc.stdout, "out"), daemon=True),
               threading.Thread(target=pump, args=(proc.stderr, "err"), daemon=True)]
    for t in threads:
        t.start()
    while proc.poll() is None:
        if time.monotonic() - t0 > timeout:
            state["reason"] = state["reason"] or "timeout"
            _kill_group(proc)
            break
        rss = _group_rss_kb(proc.pid)
        state["peak"] = max(state["peak"], rss)
        if rss > max_rss_kb:
            state["reason"] = state["reason"] or "memory"
            _kill_group(proc)
            break
        time.sleep(0.1)
    proc.wait()
    # Cleanup: make sure nothing in the group survives (watchdog or timeout kill).
    _kill_group(proc)
    for t in threads:
        t.join(timeout=2)
    out = bufs["out"][:max_output].decode("utf-8", "replace")
    err = bufs["err"][:max_output].decode("utf-8", "replace")
    return Result(cmd, proc.returncode, out, err, time.monotonic() - t0,
                  timed_out=state["reason"] == "timeout", killed_reason=state["reason"],
                  peak_rss_kb=state["peak"], truncated=state["truncated"])


# ---------------------------------------------------------------- sandbox

def sandbox_exec():
    """Path to sandbox-exec, or SandboxUnavailable. PTK_SANDBOX_EXEC overrides for tests."""
    path = os.environ.get("PTK_SANDBOX_EXEC", "/usr/bin/sandbox-exec")
    if not Path(path).is_file() or not os.access(path, os.X_OK):
        raise errors.SandboxUnavailable(
            f"sandbox-exec not available at {path}; ptk refuses to run untrusted code without it",
            path=path)
    return path


def sandboxed(cmd, mode, tmp, proj=None, state=None):
    """Prefix cmd with sandbox-exec and the ptk profile in the given mode."""
    tmp = Path(tmp).resolve()
    proj = Path(proj).resolve() if proj else tmp
    state = Path(state).resolve() if state else tmp
    extra = []
    if mode == "run":
        extra = ["-D", f"EXE={Path(cmd[0]).resolve()}", "-D", f"RT={sanitizer_runtime_dir()}"]
    return [sandbox_exec(), "-f", str(SANDBOX_PROFILE), "-D", f"MODE={mode}", "-D", f"TMP={tmp}",
            "-D", f"PROJ={proj}", "-D", f"STATE={state}", *extra, *[str(c) for c in cmd]]


_RT = []


def sanitizer_runtime_dir():
    """clang's darwin runtime dir (libclang_rt.asan/ubsan dylibs), realpath'd, cached."""
    if not _RT:
        res = run([which("clang"), "-print-resource-dir"], timeout=30, check=True)
        _RT.append(str((Path(res.stdout.strip()) / "lib" / "darwin").resolve()))
    return _RT[0]


def make_tmp(prefix):
    root = state_path("tmp")
    root.mkdir(exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=root)).resolve()


# ---------------------------------------------------------------- versions and probe

def tool_version(tool):
    reg = registry()["tools"].get(tool, {})
    args = reg.get("version_args", ["--version"])
    path = which(reg.get("binary", tool), required=False)
    if not path:
        return None
    res = run([path, *args], timeout=30)
    text = (res.stdout or res.stderr).strip().splitlines()
    return text[0] if text else ""


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _probe_one(name, spec):
    kind = spec.get("probe", "binary")
    if kind == "binary":
        path = shutil.which(spec.get("binary", name))
        return {"runnable": bool(path), "path": path}
    if kind == "state":
        p = state_path(*spec["path"].split("/"))
        return {"runnable": p.exists(), "path": str(p)}
    if kind == "sandbox":
        try:
            return {"runnable": True, "path": sandbox_exec()}
        except errors.SandboxUnavailable:
            return {"runnable": False, "path": None}
    return {"runnable": False, "path": None, "note": f"unknown probe {kind}"}


def probe():
    reg = registry()
    out = {"state": str(state_dir()), "tools": {}, "artifacts": {}}
    for name, spec in reg["tools"].items():
        out["tools"][name] = {**_probe_one(name, spec), "role": spec.get("role", "")}
    for art, alts in reg.get("artifacts", {}).items():
        ranked = []
        for alt in alts:
            needs = alt.get("needs", [])
            ok = all(out["tools"].get(n, {}).get("runnable") for n in needs)
            ranked.append({"id": alt["id"], "runnable": ok, "needs": needs, "fallback_rank": alt["rank"]})
        out["artifacts"][art] = ranked
    return out


# ---------------------------------------------------------------- setup (AC-0.1)

INVENTORY = "setup-inventory.json"


def setup_plan():
    """Every download with source, size and sha256 (D19.2). Nothing is fetched here."""
    reg = registry()
    plan = []
    for item in reg["downloads"]:
        plan.append({k: item.get(k) for k in ("id", "kind", "url", "size", "sha256", "dest", "note")})
    return plan


def setup(yes=False, log=print):
    plan = setup_plan()
    if not yes:
        return {"fetched": False, "plan": plan}
    reg = registry()
    inv = {"state": str(state_dir()), "items": [], "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    for item in reg["downloads"]:
        log(f"setup: {item['id']}")
        rec = _SETUP[item["kind"]](item)
        inv["items"].append({"id": item["id"], "kind": item["kind"], **rec})
    inv["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    inv["total_bytes"] = sum(i.get("size") or 0 for i in inv["items"])
    state_path(INVENTORY).write_text(json.dumps(inv, indent=2))
    return {"fetched": True, "inventory": str(state_path(INVENTORY)), "items": len(inv["items"]),
            "total_bytes": inv["total_bytes"]}


def _dest(item):
    if item.get("dest_root") == "fonts":
        return FONTS_DIR / item["dest"]
    return state_path(*item["dest"].split("/"))


def _fetch(url, dest, sha, size=None):
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    with urllib.request.urlopen(url, timeout=120) as r, open(part, "wb") as f:
        shutil.copyfileobj(r, f, 1 << 20)
    got = sha256_file(part)
    if got != sha:
        part.unlink()
        raise errors.SetupError(f"sha256 mismatch for {url}", expected=sha, got=got)
    if size and part.stat().st_size != size:
        part.unlink()
        raise errors.SetupError(f"size mismatch for {url}", expected=size, got=part.stat().st_size)
    part.replace(dest)


def _setup_file(item):
    dest = _dest(item)
    source = "present"
    if not (dest.exists() and sha256_file(dest) == item["sha256"]):
        source = item["url"]
        for cand in item.get("copy_from", []):
            c = Path(os.path.expanduser(cand))
            if c.exists() and c.stat().st_size == item.get("size") and sha256_file(c) == item["sha256"]:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(c, dest)
                source = f"copied from {cand} (same sha256 as {item['url']})"
                break
        else:
            _fetch(item["url"], dest, item["sha256"], item.get("size"))
    return {"url": item["url"], "path": str(dest), "size": dest.stat().st_size,
            "sha256": sha256_file(dest), "source": source}


def _setup_venv(item):
    venv = state_path("venvs", item["venv"])
    py = venv / "bin" / "python"
    base = which(item.get("python", "python3"))
    if not py.exists():
        run([base, "-m", "venv", str(venv)], check=True)
    req = PKG / item["requirements"]
    report = state_path("downloads", f"pip-{item['venv']}-report.json")
    report.parent.mkdir(parents=True, exist_ok=True)
    run([py, "-m", "pip", "install", "--quiet", "--require-hashes", "--no-deps", "--only-binary=:all:",
         "--report", str(report), "-r", str(req)], check=True, timeout=1800)
    rep = json.loads(report.read_text()) if report.exists() else {"install": []}
    pkgs = [{"name": i["metadata"]["name"], "version": i["metadata"]["version"],
             "url": i["download_info"]["url"],
             "sha256": i["download_info"].get("archive_info", {}).get("hash", "").split("=")[-1]}
            for i in rep.get("install", [])]
    if item.get("post") == "espeak_short_path":
        _espeak_short_path(venv)
    return {"url": "https://pypi.org/simple/", "path": str(venv), "size": _du(venv),
            "sha256": sha256_file(req), "requirements": str(req), "packages_installed_now": pkgs,
            "source": "pip --require-hashes"}


def _espeak_short_path(venv):
    """Kokoro's espeak data fails under long paths: move it to $PTK_STATE/espeak-ng-data, symlink back."""
    sp = next((venv / "lib").glob("python3.*/site-packages/espeakng_loader"))
    data = sp / "espeak-ng-data"
    short = state_path("espeak-ng-data")
    if data.is_symlink():
        return
    if short.exists():
        shutil.rmtree(short)
    shutil.move(str(data), str(short))
    data.symlink_to(short)


def _setup_npm(item):
    from . import node
    tools = state_path("tools", "node")
    tools.mkdir(parents=True, exist_ok=True)
    for f in ("package.json", "package-lock.json"):
        shutil.copyfile(PKG / "node" / f, tools / f)
    node.npm(["ci", "--no-fund", "--no-audit"], cwd=tools)
    lock = json.loads((tools / "package-lock.json").read_text())
    pkgs = [{"name": k.replace("node_modules/", ""), "version": v.get("version"), "url": v.get("resolved"),
             "integrity": v.get("integrity")} for k, v in lock.get("packages", {}).items() if k]
    return {"url": "https://registry.npmjs.org/", "path": str(tools), "size": _du(tools / "node_modules"),
            "sha256": sha256_file(tools / "package-lock.json"), "packages": len(pkgs),
            "top": [p for p in pkgs if p["name"] in ("hyperframes", "playwright", "playwright-core")],
            "source": "npm ci (package-lock.json)"}


def _setup_playwright(item):
    from . import node
    res = node.run_node_bin("playwright", ["install", "--only-shell", "chromium"], timeout=1800)
    shell = next(state_path("browsers").glob("chromium_headless_shell-*/chrome-headless-shell-mac-arm64/"
                                              "chrome-headless-shell"), None)
    if not shell:
        raise errors.SetupError("playwright chromium headless shell missing after install",
                                stdout=res.stdout[-2000:], stderr=res.stderr[-2000:])
    urls = [w for w in (res.stdout + res.stderr).split() if w.startswith("https://")]
    return {"url": urls[0] if urls else item["url"], "path": str(shell.parent.parent), "size": _du(shell.parent.parent),
            "sha256": sha256_file(shell), "source": "playwright install --only-shell chromium"}


def _setup_hf_chrome(item):
    from . import node
    reg = registry()["hyperframes_chrome"]
    dest = state_path("browsers", "hyperframes", reg["dir"])
    binary = dest / reg["binary"]
    source = "present"
    if not binary.exists():
        cache = Path.home() / ".cache" / "hyperframes" / "chrome" / "chrome-headless-shell" / reg["dir"]
        cbin = cache / reg["binary"]
        if cbin.exists() and sha256_file(cbin) == item["sha256"]:
            dest.parent.mkdir(parents=True, exist_ok=True)
            run(["/bin/cp", "-cR", str(cache), str(dest.parent)], check=True)
            source = f"copied from the HyperFrames cache (same sha256 as {item['url']})"
        else:
            node.hyperframes(["browser", "ensure"], cwd=state_dir(), timeout=1800)
            got = state_path("home", ".cache", "hyperframes", "chrome", "chrome-headless-shell", reg["dir"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(got), str(dest))
            source = "hyperframes browser ensure (HOME=$PTK_STATE/home)"
    got = sha256_file(binary)
    if got != item["sha256"]:
        raise errors.SetupError("hyperframes chrome sha256 mismatch", expected=item["sha256"], got=got)
    return {"url": item["url"], "path": str(dest), "size": _du(dest), "sha256": got, "source": source}


def _setup_font(item):
    """Verify a bundled font against the committed pin (assets/fonts/SHA256SUMS). Setup never writes
    into the package (AC-0.1, review P2-1): the woff2 subsets and licenses ship with it. The upstream
    URL and sha256 stay in the registry as provenance for re-subsetting, which a maintainer does by hand."""
    pins = {}
    for line in (FONTS_DIR / "SHA256SUMS").read_text().splitlines():
        if line.strip():
            digest, name = line.split(None, 1)
            pins[name.strip()] = digest
    out, lic = FONTS_DIR / item["dest"], FONTS_DIR / item["license_dest"]
    for f in (out, lic):
        if not f.is_file() or sha256_file(f) != pins.get(f.name):
            raise errors.SetupError(f"bundled {f.name} is missing or does not match assets/fonts/SHA256SUMS",
                                    path=str(f), pinned=pins.get(f.name))
    if pins.get(lic.name) != item["license_sha256"]:
        raise errors.SetupError(f"{lic.name} pin disagrees with the registry", registry=item["license_sha256"])
    return {"url": item["url"], "path": str(out), "size": out.stat().st_size, "sha256": pins[out.name],
            "upstream_sha256": item["sha256"], "license": str(lic), "license_url": item["license_url"],
            "source": "bundled subset, verified against the committed SHA256SUMS (setup writes nothing here)"}


def _du(path):
    total = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            if not os.path.islink(fp):
                total += os.path.getsize(fp)
    return total


_SETUP = {"file": _setup_file, "venv": _setup_venv, "npm": _setup_npm, "playwright": _setup_playwright,
          "hyperframes_chrome": _setup_hf_chrome, "font": _setup_font}
