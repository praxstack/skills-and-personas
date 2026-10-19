"""Shared helpers for ptk tests (not a test module)."""
import json
from pathlib import Path

from ptk import host

V21 = host.PKG.parent.parent
SLICE = V21 / "lessons" / "switch-fallthrough"


def report(lesson_dir=SLICE):
    p = lesson_dir / "build" / "build-report.json"
    return json.loads(p.read_text()) if p.exists() else None


def gate(rep, gid):
    return next((g for g in rep["gates"] if g["id"] == gid), None)


def ptk_cmd():
    return [str(host.PKG / "bin" / "ptk")]


def under(path, root):
    return Path(path).resolve().is_relative_to(Path(root).resolve())
