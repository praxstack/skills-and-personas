#!/usr/bin/env python3
"""Rank teaching tools for an idea, using what this host can actually run.

  python3 scripts/find_tool.py --job change --job cause            # what fits, best first
  python3 scripts/find_tool.py --job structure --medium still --offline
  python3 scripts/find_tool.py --job story --have mcp:hyperframes  # tell it about host tools
  python3 scripts/find_tool.py --inventory                          # what's installed here
  python3 scripts/find_tool.py --job process --json

Ranking: how many of the asked jobs a tool does, the asked medium, whether
every probe passes on this host (binaries on PATH, Python modules, Node
packages, network hosts with --net, MCP tools named with --have or in
$TEACHER_HOST_TOOLS), then bundled notebook-native tools first. A tool that
can't run here is still listed, last, with what's missing, so the teacher can
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


def probe(tool: dict, *, net: bool, mcp: set[str]) -> tuple[bool, list[str]]:
    p = tool.get("probe", {})
    missing = [f"bin:{b}" for b in p.get("bins", []) if not has_bin(b)]
    missing += [f"py:{m}" for m in p.get("py", []) if not has_py(m)]
    missing += [f"node:{m}" for m in p.get("node", []) if not has_node(m)]
    alts_ok = True
    # mcp and net are alternatives to a local install: any one passing is enough.
    alt = []
    if p.get("mcp"):
        alt.append(any(m in mcp for m in p["mcp"]))
    if p.get("net"):
        alt.append(net and any(has_net(u) for u in p["net"]))
    local_only = not p.get("bins") and not p.get("py") and not p.get("node")
    if alt and (local_only or missing):
        alts_ok = any(alt)
        if alts_ok:
            missing = []
        else:
            missing += [f"mcp:{m}" for m in p.get("mcp", [])] + ([f"net:{p['net'][0]}"] if p.get("net") else [])
    return (not missing and alts_ok), missing


def rank(tools: list[dict], jobs: list[str], media: list[str], *, offline: bool, net: bool, mcp: set[str]) -> list[dict]:
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
        ok, missing = probe(t, net=net, mcp=mcp)
        score = 10 * job_hits + 4 * medium_hit + (8 if ok else 0) + (3 if t.get("notebook") == "native" else 0) + (2 if t["id"] in BUNDLED else 0)
        out.append({**t, "available": ok, "missing": missing, "score": score})
    return sorted(out, key=lambda t: (-t["score"], t["name"]))


BUNDLED = {"explorable", "concept-animation", "explain-diagram", "lesson-notebook", "visual-qa", "explainer-video", "handdrawn-js-video"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    reg = json.loads(REGISTRY.read_text())
    ap.add_argument("--job", action="append", default=[], choices=sorted(reg["jobs"]))
    ap.add_argument("--medium", action="append", default=[], choices=reg["media"])
    ap.add_argument("--offline", action="store_true", help="only tools that work without a network")
    ap.add_argument("--net", action="store_true", help="probe network services (Kroki, CDNs)")
    ap.add_argument("--have", action="append", default=[], help="host tools available, e.g. mcp:excalidraw, mcp:hyperframes, mcp:artifact")
    ap.add_argument("--inventory", action="store_true", help="list every tool with whether it runs here")
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    mcp = host_tools(a.have)
    if a.inventory:
        rows = rank(reg["tools"], [], [], offline=False, net=a.net, mcp=mcp)
        rows.sort(key=lambda t: (not t["available"], t["name"]))
    else:
        if not a.job and not a.medium:
            ap.error("give at least one --job or --medium (or --inventory)")
        rows = rank(reg["tools"], a.job, a.medium, offline=a.offline, net=a.net, mcp=mcp)[: a.top]
    if a.json:
        keep = ("id", "name", "media", "jobs", "available", "missing", "score", "how", "notebook", "best_for", "avoid_when", "output", "ref")
        print(json.dumps([{k: r[k] for k in keep if k in r} for r in rows], indent=2))
        return 0
    if not rows:
        print("nothing matches; drop --offline or a --medium, or write SVG by hand with lesson-notebook")
        return 1
    for r in rows:
        mark = "ready" if r["available"] else "needs " + ", ".join(r["missing"])
        how = r["how"].get("skill") or r["how"].get("command") or r["how"].get("cdn") or r["how"].get("mcp") or r["how"].get("note", "")
        print(f"{r['name']:<44} {mark}")
        if r.get("best_for") and not a.inventory:
            print(f"    for: {r['best_for']}")
        if not a.inventory:
            print(f"    how: {how}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
