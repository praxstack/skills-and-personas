"""Read the learner workspace contract (D17.6, AC-1.3).

The workspace's AGENTS.md, MISSION.md and NOTES.md are read first, and their teaching rules beat
the skill's defaults. This module only reads them and reports which teaching mode they require,
with the lines that say so. The patterns live in route_rules.json under `workspace_contract`.

A line counts as predict-first evidence when a predict-first pattern matches and no negation
pattern does ("without prediction" is explain-first, not predict-first). When files disagree,
predict-first wins and `conflict` is set: one question is cheap to skip with "answer now".
"""
import re
from pathlib import Path

from . import errors


def _lines(root, names, max_bytes):
    for name in names:
        path = root / name
        text = path.read_text(errors="replace")[:max_bytes] if path.is_file() else ""
        for no, line in enumerate(text.splitlines(), 1):
            yield name, no, line.strip()


def _any(patterns, text):
    return any(p.search(text) for p in patterns)


def _evidence(lines, hit, limit):
    found = [{"file": f, "line": n, "text": t[:160]} for f, n, t in lines if hit(t.lower())]
    return found[:limit]


def read_contract(directory, spec):
    """Return {dir, files, mode, evidence, conflict} for the workspace at `directory`.

    mode is "predict-first", "explain-first" or None (no teaching rule found)."""
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
        "mode": (modes or [None])[0],
        "evidence": predict or explain,
        "conflict": len(modes) > 1,
    }
