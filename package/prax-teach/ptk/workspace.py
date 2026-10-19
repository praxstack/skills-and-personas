"""Read what the learner workspace's AGENTS.md, MISSION.md and NOTES.md ask for (AC-1.3 v1.4).

These files never set the teaching mode: every teaching request gets a complete explanation first,
in every workspace (FREEZE-v2 criterion 5). This module only reports which teaching style the files
ask for, with the lines that say so, so the router can name them in a `workspace_conflict` note
instead of obeying them. The patterns live in route_rules.json under `workspace_contract`.

A line counts as predict-first evidence when a predict-first pattern matches and no negation
pattern does ("without prediction" is explain-first, not predict-first). When some file asks for
prediction first, `asks` is "predict-first" and `evidence` holds those lines, so the conflict note
names every one of them.
"""
import re
from pathlib import Path

from . import errors


def _head(path, max_bytes):
    """At most max_bytes of the file, never the whole file (a huge NOTES.md costs nothing)."""
    with path.open("rb") as fh:
        return fh.read(max_bytes).decode(errors="replace")


def _lines(root, names, max_bytes):
    for name in names:
        path = root / name
        text = _head(path, max_bytes) if path.is_file() else ""
        for no, line in enumerate(text.splitlines(), 1):
            yield name, no, line.strip()


def _any(patterns, text):
    return any(p.search(text) for p in patterns)


def _evidence(lines, hit, limit):
    found = [{"file": f, "line": n, "text": t[:160]} for f, n, t in lines if hit(t.lower())]
    return found[:limit]


def read_contract(directory, spec):
    """Return {dir, files, asks, evidence} for the workspace at `directory`.

    asks is "predict-first", "explain-first" or None (no teaching rule found). It is reported, never obeyed."""
    root = Path(directory).expanduser().resolve()
    if not root.is_dir():
        raise errors.HostError(f"workspace is not a directory: {root}", workspace=str(root))
    pf = [re.compile(p) for p in spec["predict_first"]]
    neg = [re.compile(p) for p in spec["negations"]]
    ef = [re.compile(p) for p in spec["explain_first"]]
    lines = list(_lines(root, spec["files"], spec["max_bytes"]))
    predict = _evidence(lines, lambda t: _any(pf, t) and not _any(neg, t), spec["max_evidence"])
    explain = _evidence(lines, lambda t: _any(ef, t), spec["max_evidence"])
    modes = [m for m, ev in (("predict-first", predict), ("explain-first", explain)) if ev]
    return {
        "dir": str(root),
        "files": [n for n in spec["files"] if (root / n).is_file()],
        "asks": (modes or [None])[0],
        "evidence": predict or explain,
    }
