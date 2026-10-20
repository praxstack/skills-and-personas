#!/usr/bin/env python3
"""Rank teaching tools for an idea, using what this host can actually run.

  python3 scripts/find_tool.py --job change --job cause            # what fits, best first
  python3 scripts/find_tool.py --job structure --medium still --offline
  python3 scripts/find_tool.py --job story --have mcp:hyperframes  # tell it about host tools
  python3 scripts/find_tool.py --inventory                          # what's installed here
  python3 scripts/find_tool.py --job process --json

Ranking: how many of the asked jobs a tool does, the asked medium, whether
prerequisites are detected on this host (binaries on PATH, Python modules, Node
packages, network hosts with --net, MCP tools named with --have or in
$TEACHER_HOST_TOOLS), then bundled notebook-native tools first. A tool with
unverified prerequisites is still listed, last, with what's missing, so the teacher can
offer to install it or pick the next one.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "assets" / "registry.json"


@lru_cache(None)
def has_bin(name: str) -> bool:
    return shutil.which(name) is not None


@lru_cache(None)
def has_py(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


@lru_cache(None)
def has_node(name: str) -> bool:
    if not has_bin("node"):
        return False
    search = [os.getcwd(), str(ROOT)]
    extra = os.environ.get("PLAYWRIGHT_MODULE") if name == "playwright" else None
    if extra and Path(extra).exists():
        return True
    code = f"for (const p of {json.dumps(search)}) {{ try {{ require.resolve({json.dumps(name)}, {{ paths: [p] }}); process.exit(0) }} catch {{}} }} process.exit(1)"
    try:
        r = subprocess.run(["node", "-e", code], capture_output=True, timeout=10)
        if r.returncode == 0:
            return True
        g = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True, timeout=10)
        return g.returncode == 0 and (Path(g.stdout.strip()) / name).exists()
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


@lru_cache(None)
def has_net(url: str) -> bool:
    # Any HTTP answer, even a 4xx, means the host is reachable from here.
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "teacher-find-tool"})
    try:
        with urllib.request.urlopen(req, timeout=8):
            return True
    except urllib.error.HTTPError:
        return True
    except Exception:
        return False


def host_tools(cli: list[str]) -> set[str]:
    names = {x.strip().lower() for x in os.environ.get("TEACHER_HOST_TOOLS", "").split(",") if x.strip()}
    names |= {x.lower() for x in cli}
    return {n.split(":", 1)[-1] for n in names}


def inspect_tool(tool: dict, *, net: bool, mcp: set[str], trusted_runtime_probe: bool = False) -> dict:
    """Detect prerequisites, never claim a render or remote runtime was tested."""
    p = tool.get("probe", {})
    how = tool.get("how", {})
    evidence = []
    missing = []
    skill = how.get("skill")
    if skill:
        if not (ROOT / skill).is_file():
            return {"available": False, "missing": [f"file:{skill}"],
                    "status": "missing", "evidence": []}
        evidence.append(f"bundled instructions present: {skill}")
    if tool.get("id") == "manim":
        if not trusted_runtime_probe:
            # Filesystem/PATH evidence only: do not load the wrapper, inspect
            # project source configuration, or import a workspace module.
            cli = shutil.which("manim")
            if cli:
                evidence.append(f"unverified Manim CLI candidate: {cli}")
            project = Path.cwd()
            candidates = [os.environ.get("MANIM_PYTHON"),
                          str(project / ".venv/bin/python"),
                          str(project / "source/.venv/bin/python"), sys.executable]
            for candidate in dict.fromkeys(candidates):
                if candidate and Path(candidate).is_file():
                    evidence.append(f"unverified Python candidate: {candidate}")
            return {"available": False, "missing": ["runtime:unverified (requires --trusted-runtime-probe)"],
                    "status": "unknown", "evidence": evidence}
        # Use the prescribed wrapper's exact resolver, including actual imports.
        # Discovery runs in the project cwd, as does render_manim.py by default.
        wrapper = ROOT / "skills/manim-video/scripts/render_manim.py"
        spec = importlib.util.spec_from_file_location("teacher_manim_renderer", wrapper)
        renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(renderer)
        project = os.getcwd()
        source = "source"
        try:
            state = json.loads((Path(project) / ".video-state.json").read_text())
            config = state.get("config", {}) if isinstance(state, dict) else {}
            candidate = config.get("source") if isinstance(config, dict) else None
            if isinstance(candidate, str):
                source = candidate
        except (OSError, ValueError):
            pass
        selected = renderer.resolve_python(project, os.path.join(project, source))
        if selected:
            return {"available": True, "missing": [], "status": "detected",
                    "evidence": evidence + [f"Manim import verified with wrapper Python: {selected}"]}
        return {"available": False, "missing": ["py:manim (no wrapper-compatible interpreter)"],
                "status": "missing", "evidence": evidence}
    for key, check, label in (("bins", has_bin, "bin"), ("py", has_py, "py"), ("node", has_node, "node")):
        for name in p.get(key, []):
            (evidence if check(name) else missing).append(f"{label}:{name}")
    local = any(p.get(key) for key in ("bins", "py", "node"))
    # Declared CLI alternatives only look up executable names on PATH. Never
    # execute registry command strings, installers, or shell expressions.
    cli = [name for name in p.get("cli", []) if has_bin(name)]
    if cli:
        evidence.extend(f"CLI on PATH: {name}" for name in cli)
        missing = []
        local = True
    elif p.get("cli") and (not local or missing):
        missing.extend(f"bin:{name} (alternative)" for name in p["cli"])
    declared = [name for name in p.get("mcp", []) if name in mcp]
    if not p and tool.get("id") in mcp:
        declared.append(tool["id"])
    if declared:
        evidence.extend(f"host declared: {name}" for name in declared)
        return {"available": True, "missing": [], "status": "declared", "evidence": evidence}
    if local and not missing:
        return {"available": True, "missing": [], "status": "detected", "evidence": evidence}
    if not p and not how.get("cdn"):
        if skill:
            return {"available": True, "missing": [], "status": "instructions", "evidence": evidence}
        if tool.get("id") == "svg":
            return {"available": True, "missing": [], "status": "authoring",
                    "evidence": ["SVG can be authored directly; viewing is untested"]}
    urls = p.get("net", []) or ([how["cdn"]] if how.get("cdn") else [])
    if urls:
        if net:
            reachable = [url for url in urls if has_net(url)]
            if reachable:
                evidence.extend(f"HTTP host reachable: {url}" for url in reachable)
                return {"available": False, "missing": ["runtime:unverified"],
                        "status": "reachable", "evidence": evidence}
            missing.extend(f"net:{url}" for url in urls)
        else:
            missing.append("network:unverified (use --net to check reachability only)")
    missing.extend(f"host:{name} (declare with --have)" for name in p.get("mcp", []))
    if not missing:
        missing.append(f"host:{tool.get('id', 'unknown')} (unverified; declare with --have)")
    return {"available": False, "missing": missing,
            "status": "missing" if local else "unknown", "evidence": evidence}


def probe(tool: dict, *, net: bool, mcp: set[str], trusted_runtime_probe: bool = False) -> tuple[bool, list[str]]:
    result = inspect_tool(tool, net=net, mcp=mcp, trusted_runtime_probe=trusted_runtime_probe)
    return result["available"], result["missing"]


def rank(tools: list[dict], jobs: list[str], media: list[str], *, offline: bool, net: bool, mcp: set[str], trusted_runtime_probe: bool = False) -> list[dict]:
    out = []
    for t in tools:
        job_hits = len(set(jobs) & set(t.get("jobs", []))) if jobs else 0
        medium_hit = bool(set(media) & set(t.get("media", []))) if media else False
        if jobs and not job_hits:
            continue
        if media and not medium_hit:
            continue
        if offline and not t.get("offline", False):
            continue
        result = inspect_tool(t, net=net and not offline, mcp=mcp, trusted_runtime_probe=trusted_runtime_probe)
        ok = result["available"]
        score = 10 * job_hits + 4 * medium_hit + (8 if ok else 0) + (3 if t.get("notebook") == "native" else 0) + (2 if t["id"] in BUNDLED else 0)
        out.append({**t, **result, "score": score})
    return sorted(out, key=lambda t: (-t["score"], t["name"]))


BUNDLED = {"explorable", "concept-animation", "explain-diagram", "lesson-notebook", "visual-qa", "explainer-video", "handdrawn-js-video"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    reg = json.loads(REGISTRY.read_text())
    ap.add_argument("--job", action="append", default=[], choices=sorted(reg["jobs"]))
    ap.add_argument("--medium", action="append", default=[], choices=reg["media"])
    ap.add_argument("--offline", action="store_true", help="only tools that work without a network")
    ap.add_argument("--net", action="store_true", help="probe network services (Kroki, CDNs)")
    ap.add_argument("--trusted-runtime-probe", action="store_true",
                    help="execute Manim import checks in selected local Python runtimes; trust the workspace, its source config, environments and startup/import code first (not a render test)")
    ap.add_argument("--have", action="append", default=[], help="host tools available, e.g. mcp:excalidraw, mcp:hyperframes, mcp:artifact")
    ap.add_argument("--inventory", action="store_true", help="list tool prerequisite evidence (not render verification)")
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    mcp = host_tools(a.have)
    if a.inventory:
        rows = rank(reg["tools"], [], [], offline=a.offline, net=a.net, mcp=mcp, trusted_runtime_probe=a.trusted_runtime_probe)
        rows.sort(key=lambda t: (not t["available"], t["name"]))
    else:
        if not a.job and not a.medium:
            ap.error("give at least one --job or --medium (or --inventory)")
        rows = rank(reg["tools"], a.job, a.medium, offline=a.offline, net=a.net, mcp=mcp, trusted_runtime_probe=a.trusted_runtime_probe)[: a.top]
    if a.json:
        keep = ("id", "name", "media", "jobs", "available", "missing", "status", "evidence", "score", "how", "notebook", "best_for", "avoid_when", "output", "ref")
        print(json.dumps([{k: r[k] for k in keep if k in r} for r in rows], indent=2))
        return 0
    if not rows:
        print("nothing matches; drop --offline or a --medium, or write SVG by hand with lesson-notebook")
        return 1
    for r in rows:
        mark = r["status"] + ("" if r["available"] else ": " + ", ".join(r["missing"]))
        how = r["how"].get("skill") or r["how"].get("command") or r["how"].get("cdn") or r["how"].get("mcp") or r["how"].get("note", "")
        print(f"{r['name']:<44} {mark}")
        if r.get("best_for") and not a.inventory:
            print(f"    for: {r['best_for']}")
        if not a.inventory:
            print(f"    how: {how}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
