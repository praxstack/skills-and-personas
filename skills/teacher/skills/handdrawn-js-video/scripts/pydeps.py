#!/usr/bin/env python3
"""pydeps.py: install the pipeline's Python packages on any machine, including ones where pip says no.

Plain `pip install` fails on many laptops. Homebrew's Python and Debian/Ubuntu's mark themselves "externally
managed" (PEP 668) and refuse both system and --user installs, and kokoro-onnx has no build for Python 3.14
(it needs 3.10 to 3.13). When pip refuses, the pipeline makes one virtual environment of its own, from a Python
the packages support, and runs the calling script again inside it. Later scripts switch to that environment
before importing anything (ensure), so every step shares one set of packages.

  environment: $VIDEO_SKILLS_VENV, else ~/.cache/video-skills/venv (delete it to start over)

Usage, from a script that lives next to this file:
  import pydeps
  np = pydeps.need("numpy", "numpy>=1.24")     # import, installing once if missing
  pydeps.ensure("numpy", "soundfile")          # before module-level imports: switch to the environment if needed
"""
import importlib
import importlib.util
import os
import shutil
import subprocess
import sys

VENV = os.environ.get("VIDEO_SKILLS_VENV") or os.path.join(
    os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"), "video-skills", "venv")
# the Python versions every package the pipeline installs supports (kokoro-onnx 0.6.1: >=3.10, <3.14)
SUPPORTED = ((3, 10), (3, 13))
_MARK = "VIDEO_SKILLS_PYDEPS_SWITCHED"  # set before re-running in the environment, so a failure there cannot loop


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def venv_python():
    return os.path.join(VENV, "bin", "python")


def in_venv():
    return os.path.realpath(sys.prefix) == os.path.realpath(VENV)


def _version(exe):
    try:
        out = subprocess.run([exe, "-c", "import sys; print(*sys.version_info[:2])"], capture_output=True, text=True,
                             timeout=30).stdout.split()
        return tuple(int(x) for x in out[:2]) if len(out) >= 2 else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def _supported(v):
    return v is not None and SUPPORTED[0] <= v[:2] <= SUPPORTED[1]


def base_python():
    """The Python to build the environment from: this one if every package supports it, else the newest
    supported python3.X on PATH, else this one anyway (the packages that do support it still install)."""
    if _supported(sys.version_info):
        return sys.executable
    for minor in range(SUPPORTED[1][1], SUPPORTED[0][1] - 1, -1):
        exe = shutil.which(f"python3.{minor}")
        if exe and _supported(_version(exe)):
            return exe
    return sys.executable


def _pip(python, pkg, user=False):
    cmd = [python, "-m", "pip", "install", "-q", "--disable-pip-version-check"] + (["--user"] if user else []) + [pkg]
    # a user install cannot land in a virtual environment, so PIP_USER or a pip.conf user = true is off there
    env = dict(os.environ, PIP_USER="0") if sys.prefix != sys.base_prefix else None
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return None if r.returncode == 0 else (r.stderr or r.stdout).strip()


def _make_venv():
    if os.path.exists(venv_python()):
        return
    base = base_python()
    log(f"pip cannot install into {sys.executable}; making a private environment at {VENV} from {base}")
    r = subprocess.run([base, "-m", "venv", VENV], capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(venv_python()):
        shutil.rmtree(VENV, ignore_errors=True)
        raise RuntimeError(f"could not create {VENV} with {base} -m venv: {(r.stderr or r.stdout).strip()[-300:]}. "
                           "On Debian/Ubuntu install python3-venv; elsewhere use a Python from python.org or "
                           "Homebrew, or set VIDEO_SKILLS_VENV to an environment you made yourself.")


def _switch(why):
    """Re-run the current script inside the environment. Returns only if that is not possible."""
    here = os.path.dirname(os.path.realpath(__file__))
    script = os.path.realpath(sys.argv[0]) if sys.argv and sys.argv[0] else ""
    if in_venv() or os.environ.get(_MARK) or os.path.dirname(script) != here:
        return  # already there, already tried, or not a pipeline script (e.g. imported by a test)
    _make_venv()
    vpy = venv_python()
    log(f"{why}; running {os.path.basename(sys.argv[0])} again with {vpy}")
    env = dict(os.environ, **{_MARK: "1"})
    sys.stdout.flush()
    sys.stderr.flush()
    os.execve(vpy, [vpy, os.path.abspath(sys.argv[0])] + sys.argv[1:], env)


def _add_user_site():
    """pip installs into the user site folder with --user, and also on its own when site-packages is read-only and
    the system allows it (break-system-packages, as on GitHub's Ubuntu runners). A folder made during this run is
    not on sys.path yet."""
    import site
    if in_venv() or sys.prefix != sys.base_prefix or not site.ENABLE_USER_SITE:
        return
    us = site.getusersitepackages()
    if os.path.isdir(us) and us not in sys.path:
        site.addsitedir(us)


def need(mod, pip_name=None):
    """Import a module, installing it with pip once if it is missing (in the environment if pip refuses here)."""
    try:
        return importlib.import_module(mod)
    except ImportError:
        pass
    pkg = pip_name or mod
    log(f"installing {pkg} ...")
    err = _pip(sys.executable, pkg)
    if err is not None and not in_venv() and sys.prefix == sys.base_prefix:
        err = _pip(sys.executable, pkg, user=True)  # a system Python without write access to site-packages
    if err is None:
        _add_user_site()
        importlib.invalidate_caches()
        return importlib.import_module(mod)
    # pip refused (externally managed, missing, or no build for this Python): use the environment if it would help
    if ("externally-managed-environment" in err or "No module named pip" in err or base_python() != sys.executable
            or os.path.exists(venv_python())):
        _switch(f"pip install {pkg} failed here")
    hint = ""
    if not _supported(sys.version_info):
        hint = (f" (this is Python {sys.version_info[0]}.{sys.version_info[1]}; the pipeline's packages support "
                f"{SUPPORTED[0][0]}.{SUPPORTED[0][1]} to {SUPPORTED[1][0]}.{SUPPORTED[1][1]}: install python3.13, "
                f"delete {VENV} and run again)")
    raise RuntimeError(f"pip install {pkg} failed{hint}: {err[-300:]}")  # the hint first: callers may cut the message


def ensure(*mods):
    """Make the modules importable before a script's module-level imports: switch to the environment if it
    exists and this Python lacks one of them, otherwise install what is missing."""
    missing = [m for m in mods if importlib.util.find_spec(m) is None]
    if not missing:
        return
    if os.path.exists(venv_python()):
        _switch(f"{', '.join(missing)} not installed for {sys.executable}")
    for m in missing:
        need(m, PINS.get(m))


# pins for modules the pipeline imports at module level (voice.py pins the voice engines itself)
PINS = {"numpy": "numpy>=1.24", "soundfile": "soundfile==0.14.0"}
