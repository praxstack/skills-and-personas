"""AC-1.9: the loader path is at most 4,000 tokens (characters / 4).

The loader path is everything an agent must read before its first teaching word:
- SKILL.md (the whole file: the host loads it whole);
- every references/*.md the pre-teaching part of SKILL.md (before the first "## Build" heading)
  tells the agent to read;
- the largest `ptk route --json` output over the dev prompt set, because the agent reads it too.
"""
import json
import re
import shutil
from pathlib import Path

from ptk import host, route

BUDGET_TOKENS = 4000
SKILL = host.PKG / "SKILL.md"
DEV = host.PKG / "tests" / "data" / "route-dev.jsonl"
C_WORKSPACE = Path.home() / "Study" / "Actual_Study_Gate2027" / "01-Interview Preperation" / "01-C"


def tokens(text):
    return len(text) / 4


def loader_files(skill_text):
    """SKILL.md plus the reference files its pre-teaching part names."""
    pre = skill_text.split("\n## Build", 1)[0]
    refs = sorted(set(re.findall(r"references/[\w.-]+\.md", pre)))
    return [SKILL, *(host.PKG / r for r in refs)]


def _largest_route_json():
    """Largest route output over the dev set, against a one-line fixture workspace and, when present,
    Prax's real C workspace (read-only), whose four evidence lines make the output longer."""
    ws = host.make_tmp("budget-ws-")
    (ws / "AGENTS.md").write_text("Ask one bounded prediction and wait for the attempt.\n")
    workspaces = [ws] + [C_WORKSPACE] * (C_WORKSPACE / "AGENTS.md").is_file()
    try:
        rows = [json.loads(line) for line in DEV.read_text().splitlines() if line.strip()]
        return max(len(json.dumps(route.route(r["request"], workspace_dir=w), indent=2)) for r in rows for w in workspaces)
    finally:
        shutil.rmtree(ws)


def test_loader_budget():
    text = SKILL.read_text()
    files = loader_files(text)
    names = [str(f.relative_to(host.PKG)) for f in files]
    assert "references/TEACHING.md" in names, f"SKILL.md must send the agent to TEACHING.md before teaching: {names}"
    assert "references/LESSON-MODEL.md" not in names, "LESSON-MODEL.md is build-time, not pre-teaching"
    assert all(f.is_file() for f in files), names
    assert "ptk route" in text.split("\n## Build", 1)[0], "SKILL.md must call ptk route before teaching"
    # the measure itself fails an over-budget path
    assert tokens("x" * (BUDGET_TOKENS * 4 + 4)) > BUDGET_TOKENS
    chars = {n: len(f.read_text()) for n, f in zip(names, files)}
    chars["route --json (largest)"] = _largest_route_json()
    total = sum(chars.values()) / 4
    assert total <= BUDGET_TOKENS, f"loader path is {total:.0f} tokens (> {BUDGET_TOKENS}): {chars}"
    return {"tokens": round(total), "budget": BUDGET_TOKENS, "chars": chars}
