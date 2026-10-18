"""AC-1.1..AC-1.5: `ptk route` against the dev prompt set (tests/data/route-dev.jsonl, 60+ prompts).

The dev set was written independently of the holdout. Each case names a workspace fixture
(created here in a temp dir) and the fields it expects; only the named fields are compared.
"""
import ast
import json
import re
import shutil
from pathlib import Path

from _util import ptk_cmd
from ptk import host, route

DEV = host.PKG / "tests" / "data" / "route-dev.jsonl"
C_WORKSPACE = Path.home() / "Study" / "Actual_Study_Gate2027" / "01-Interview Preperation" / "01-C"

# Fixture workspaces, written for this test (not copied from any real workspace).
FIXTURES = {
    "none": {},
    "predict": {"AGENTS.md": "# Study workspace\n\n## Teaching\n\n- Ask one bounded prediction and wait for the attempt.\n"
                             "- Never reveal the result before the learner tries.\n- Use C for C concepts.\n"},
    "notes": {"NOTES.md": "# Preferences\n\nStart each session with one short output prediction.\n"},
    "socratic": {"MISSION.md": "# Mission\n\nLearn C through Socratic prompts and exact diagrams.\n"},
    "explain": {"AGENTS.md": "# Workspace\n\nDeliver the whole explanation without prediction, quiz or teach-back barriers.\n"},
}


def _workspaces():
    root = host.make_tmp("route-ws-")
    dirs = {}
    for name, files in FIXTURES.items():
        d = root / name
        d.mkdir()
        for fname, text in files.items():
            (d / fname).write_text(text)
        dirs[name] = d
    return root, dirs


def _cases(tag=None):
    rows = [json.loads(line) for line in DEV.read_text().splitlines() if line.strip()]
    return [r for r in rows if tag is None or tag in r["tags"]]


def _run(cases):
    """Route each case; return (n, failures)."""
    root, dirs = _workspaces()
    try:
        bad = []
        for c in cases:
            got = route.route(c["request"], workspace_dir=dirs[c["workspace"] or "none"])
            diff = {k: (v, got.get(k)) for k, v in c["expect"].items() if got.get(k) != v}
            if diff:
                bad.append({"id": c["id"], "request": c["request"], "diff": diff, "rules": got["rules"]})
        return len(cases), bad
    finally:
        shutil.rmtree(root)


def _assert_all(tag, minimum):
    n, bad = _run(_cases(tag))
    assert n >= minimum, f"only {n} {tag!r} cases"
    assert not bad, json.dumps(bad, indent=1)
    return {"cases": n}


def test_dev_set_size_and_accuracy():
    """The dev set has at least 60 prompts and every one routes as labelled."""
    cases = _cases()
    assert len(cases) >= 60, len(cases)
    n, bad = _run(cases)
    assert not bad, f"dev accuracy {n - len(bad)}/{n}: " + json.dumps(bad, indent=1)
    return {"cases": n, "correct": n, "accuracy": 1.0}


def test_medium_words():
    """AC-1.1: every medium word routes to its medium, including M1, M2 and the D20.8 cases."""
    words = {"video": "video", "narrated": "video", "voice over": "video", "animate": "video",
             "interactive video": "ive", "explorer": "explorer", "cards": "cards", "q&a": "qa", "still": "still"}
    texts = " ".join(c["request"].lower() for c in _cases("medium"))
    missing = [w for w in words if w not in texts]
    assert not missing, f"dev set lacks medium words: {missing}"
    for tag in ("M1", "M2", "D20.8"):
        assert _cases(tag), f"dev set lacks {tag} cases"
    narrated = [c for c in _cases("D20.8") if "narrat" in c["request"].lower()]
    assert all(c["expect"]["media"] == ["video"] and c["expect"]["narration"] for c in narrated), \
        "narrated animation must be video plus narration, never audio only"
    return _assert_all("medium", 25)


def test_ordinary_tasks():
    """AC-1.2: fix, rename, write tests (and D20.8 'promo video') give intent=ordinary_task and no teaching."""
    res = _assert_all("ordinary", 15)
    root, dirs = _workspaces()
    try:
        for req in ("Fix the off-by-one in basics.c", "Rename sum to total", "Write tests for the parser"):
            got = route.route(req, workspace_dir=dirs["predict"])
            assert got["intent"] == "ordinary_task" and got["mode"] is None and got["media"] == [], got
            assert got["first_turn"]["kind"] == "task" and got["first_turn"]["questions"] == 0
            assert got["build_needed"] is False
    finally:
        shutil.rmtree(root)
    return res


def test_workspace_contract_wins():
    """AC-1.3: a predict-first workspace gives mode=predict-first and a one-question first turn,
    even when a medium is requested; the artifact comes after the attempt."""
    res = _assert_all("contract", 10)
    root, dirs = _workspaces()
    try:
        got = route.route("Teach me how a switch falls through as a narrated video", workspace_dir=dirs["predict"])
        assert got["mode"] == "predict-first" and got["media"] == ["video"] and got["build_needed"] is True
        ft = got["first_turn"]
        assert ft["kind"] == "question" and ft["questions"] == 1 and ft["end_turn"] is True
        assert ft["artifact"] == "after-attempt"
        wc = got["workspace_contract"]
        assert wc["mode"] == "predict-first" and wc["files"] == ["AGENTS.md"]
        assert any("prediction" in e["text"] for e in wc["evidence"])
        neg = route.route("Teach me pointers", workspace_dir=dirs["explain"])["workspace_contract"]
        assert neg["mode"] == "explain-first", "'without prediction' must not read as predict-first"
    finally:
        shutil.rmtree(root)
    if (C_WORKSPACE / "AGENTS.md").is_file():  # Prax's real C workspace, read-only
        real = route.route("Teach me how printf %d works as a narrated video", workspace_dir=C_WORKSPACE)
        assert real["mode"] == "predict-first" and real["first_turn"]["questions"] == 1, real
        res["real_c_workspace"] = sorted({e["file"] for e in real["workspace_contract"]["evidence"]})
    return res


def test_answer_now_overrides_contract():
    """AC-1.3 / D20.7: an explicit answer now, just explain or build the full course beats predict-first."""
    res = _assert_all("override", 6)
    reqs = " | ".join(c["request"].lower() for c in _cases("override"))
    for phrase in ("answer now", "just explain", "full course"):
        assert phrase in reqs, f"no override case for {phrase!r}"
    return res


def test_quick_no_build():
    """AC-1.4: a direct or quick answer request gives mode=quick, build_needed=false."""
    res = _assert_all("quick", 8)
    res["cli"] = _cli_quick()
    return res


def _cli_quick():
    res = host.run([*ptk_cmd(), "route", "Quick question: what does %zu print?", "--workspace",
                    str(host.make_tmp("route-cli-")), "--json"], timeout=60)
    assert res.code == 0, res.stderr[-800:]
    out = json.loads(res.stdout)
    assert out["mode"] == "quick" and out["build_needed"] is False and out["media"] == []
    assert {"intent", "mode", "media", "workspace_contract", "first_turn", "build_needed"} <= set(out)
    return {"exit": res.code, "mode": out["mode"]}


def test_modes_route():
    """The explicit teaching modes route by name (quiz, exam-drill, socratic, qa-expand, predict, explain)."""
    out = {}
    for tag in ("quiz", "exam-drill", "socratic", "qa-expand", "predict", "explain", "full"):
        out[tag] = _assert_all(tag, 2)["cases"]
    return out


# ---------------------------------------------------------------- AC-1.5

BRANCH_NODES = (ast.If, ast.IfExp, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.match_case)


def _branches(fn):
    """Decision points in one function, nested functions excluded."""
    count, stack = 0, list(ast.iter_child_nodes(fn))
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) and node is not fn:
            continue
        count += isinstance(node, BRANCH_NODES)
        count += len(node.ifs) + 1 if isinstance(node, ast.comprehension) else 0
        count += len(node.values) - 1 if isinstance(node, ast.BoolOp) else 0
        stack.extend(ast.iter_child_nodes(node))
    return count


def _function_branches(src):
    tree = ast.parse(src)
    fns = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))]
    return {getattr(f, "name", f"lambda@{f.lineno}"): _branches(f) for f in fns}


def test_rule_table_and_complexity():
    """AC-1.5: the router is table-driven (route_rules.json) and no route.py function has more than 5 branches."""
    # the counter itself sees each kind of branch
    planted = "def f(x):\n if x:\n  pass\n for i in x:\n  pass\n y = 1 if x else 2\n" \
              " z = [a for a in x if a]\n w = x and y or z\n try:\n  pass\n except ValueError:\n  pass\n"
    assert _function_branches(planted)["f"] == 8, _function_branches(planted)
    src = (host.PKG / "ptk" / "route.py").read_text()
    counts = _function_branches(src)
    over = {k: v for k, v in counts.items() if v > 5}
    assert not over, f"functions over 5 branches: {over}"
    # no routing vocabulary in code: every regex lives in the table
    literals = [n.value for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    vocab = ("video", "voice", "anim", "quiz", "predict", "socratic", "explorer", "promo", "fix", "rename")
    leaked = [s for s in literals if ("\\b" in s or any(v in s.lower() for v in vocab))
              and "\n" not in s and s != route.NEVER]
    assert not leaked, f"routing words in route.py instead of route_rules.json: {leaked}"
    table = json.loads(route.RULES_PATH.read_text())
    for key in ("intent_rules", "medium_rules", "mode_rules", "precedence", "first_turn", "workspace_contract"):
        assert key in table, key
    assert table["precedence"].index("override") < table["precedence"].index("workspace") \
        < table["precedence"].index("media") < table["precedence"].index("intent")
    assert {r["medium"] for r in table["medium_rules"]} == set(table["media_order"])
    for stage, rules in table["mode_rules"].items():
        assert stage in table["precedence"], stage
        for r in rules:
            assert r["mode"] in table["first_turn"], r["id"]
            for p in r["any"] + r.get("unless", []):
                re.compile(route._expand(p, table["macros"]))
    return {"max_branches": max(counts.values()), "functions": len(counts)}
