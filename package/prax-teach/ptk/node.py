"""The single Node boundary (E3): resolve Node >= 22, run ptk's .mjs scripts, npm and HyperFrames.

Every call goes through host.run with host.child_env(node_home=True), so the env contract
(spec §5.5) always applies and HyperFrames never writes to the real ~/.hyperframes or
~/.cache/hyperframes. The global `hyperframes` CLI is never used: only the pinned copy in
$PTK_STATE/tools/node/node_modules.
"""
import os
import shutil
from pathlib import Path

from . import errors, host

NODE_DIR = host.PKG / "node"
MIN_MAJOR = 22


def node_bin():
    path = shutil.which("node")
    if not path:
        raise errors.HostToolMissing("node >= 22 not found on PATH", tool="node")
    res = host.run([path, "--version"], timeout=30)
    major = int(res.stdout.strip().lstrip("v").split(".")[0] or 0)
    if major < MIN_MAJOR:
        raise errors.HostToolMissing(f"node {res.stdout.strip()} is below 22", tool="node")
    return path


def node_version():
    return host.run([node_bin(), "--version"], timeout=30).stdout.strip()


def tools_dir():
    return host.state_path("tools", "node")


def env(lesson_sha256=None, extra=None):
    e = host.child_env(extra=extra, lesson_sha256=lesson_sha256, node_home=True)
    e["PTK_NODE_PREFIX"] = str(tools_dir())
    e["PATH"] = os.pathsep.join([str(Path(node_bin()).parent), e.get("PATH", "")])
    return e


def npm(args, cwd, timeout=1800):
    npm_path = shutil.which("npm")
    if not npm_path:
        raise errors.HostToolMissing("npm not found on PATH", tool="npm")
    return host.run([npm_path, *args], cwd=cwd, env=env(), timeout=timeout, check=True)


def bin_path(name):
    p = tools_dir() / "node_modules" / ".bin" / name
    if not p.exists():
        raise errors.HostToolMissing(f"{name} is not installed under $PTK_STATE/tools/node; run `ptk host setup --yes`",
                                     tool=name)
    return p


def run_node_bin(name, args, cwd=None, timeout=600, lesson_sha256=None):
    return host.run([bin_path(name), *args], cwd=cwd or tools_dir(), env=env(lesson_sha256), timeout=timeout,
                    check=True)


def run_script(script, args, cwd=None, timeout=600, lesson_sha256=None, check=True, extra_env=None):
    """Run one of ptk's own node/*.mjs scripts."""
    return host.run([node_bin(), str(NODE_DIR / script), *[str(a) for a in args]], cwd=cwd or NODE_DIR,
                    env=env(lesson_sha256, extra_env), timeout=timeout, check=check)


def hyperframes(args, cwd, timeout=1800, lesson_sha256=None, sandbox_tmp=None, check=True):
    """Run the pinned HyperFrames CLI. With sandbox_tmp, run under the sandbox render profile."""
    cmd = [str(bin_path("hyperframes")), *args]
    extra = None
    if sandbox_tmp:
        cmd = host.sandboxed(cmd, "render", tmp=sandbox_tmp, proj=cwd, state=host.state_dir())
        extra = {"TMPDIR": str(sandbox_tmp) + "/"}
    return host.run(cmd, cwd=cwd, env=env(lesson_sha256, extra), timeout=timeout, check=check)


def hyperframes_version():
    return host.run([bin_path("hyperframes"), "--version"], env=env(), timeout=60).stdout.strip()


def node_for_major(major):
    """A node binary of this major version: $PTK_NODE<major>, then `mise where node@<major>`, then the
    node on PATH if it matches. None when there is none (the caller decides between not-run and failure)."""
    env_path = os.environ.get(f"PTK_NODE{major}")
    candidates = [Path(env_path)] if env_path else []
    mise = shutil.which("mise")
    if mise:
        res = host.run([mise, "where", f"node@{major}"], timeout=60)
        if res.code == 0 and res.stdout.strip():
            candidates.append(Path(res.stdout.strip()) / "bin" / "node")
    on_path = shutil.which("node")
    if on_path:
        candidates.append(Path(on_path))
    for c in candidates:
        if c.is_file() and os.access(c, os.X_OK):
            v = host.run([c, "--version"], timeout=30).stdout.strip()
            if v.lstrip("v").split(".")[0] == str(major):
                return {"path": str(c), "version": v}
    return None


def render_markdown(source, output=None, trusted_root=None, check=False, node_path=None):
    """Render a Markdown lesson note to its HTML companion with node/render_markdown.mjs (AC-8.3).
    SOURCE_DATE_EPOCH comes from the source's sha256, so the same bytes always give the same page."""
    source = Path(source).resolve()
    digest = host.sha256_file(source)
    args = (["--check"] if check else []) + ["--trusted-root", str(Path(trusted_root or source.parent).resolve()),
                                             str(source)] + ([str(output)] if output else [])
    cmd = [node_path or node_bin(), str(NODE_DIR / "render_markdown.mjs"), *args]
    return host.run(cmd, cwd=NODE_DIR, env=env(lesson_sha256=digest), timeout=300)
