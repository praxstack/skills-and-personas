"""AC-1.1..AC-1.5: `ptk route` against the dev prompt set (tests/data/route-dev.jsonl, 60+ prompts).

The dev set was written independently of the holdout. Each case names a workspace fixture
(created here in a temp dir) and the fields it expects; only the named fields are compared. A case may
also list `accept`: other values a good tutor could defend for a field (the WP1 reviewer's scoring).

route-dev-heldback.jsonl holds 20 adversarial probes that were never used to tune the rules. Its test
only reports accuracy; it does not assert a score, so nobody is tempted to tune on it.
"""
import ast
import json
import re
import shutil
from pathlib import Path

from _util import ptk_cmd
from ptk import host, route

DEV = host.PKG / "tests" / "data" / "route-dev.jsonl"
HELDBACK = host.PKG / "tests" / "data" / "route-dev-heldback.jsonl"
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


def _cases(tag=None, path=DEV):
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return [r for r in rows if tag is None or tag in r["tags"]]


def _ok(case, key, got):
    return got == case["expect"][key] or got in case.get("accept", {}).get(key, [])


def _run(cases):
    """Route each case; return (n, failures)."""
    root, dirs = _workspaces()
    try:
        bad = []
        for c in cases:
            got = route.route(c["request"], workspace_dir=dirs[c["workspace"] or "none"])
            diff = {k: (v, got.get(k)) for k, v in c["expect"].items() if not _ok(c, k, got.get(k))}
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


PRACTICE = {"predict-first", "socratic", "quiz", "exam-drill"}
# Teaching requests with no practice words: none of them may start with a question in any workspace.
PLAIN = ("Teach me pointers", "explain how a for loop works", "i dont get recursion :(",
         "Teach me how a switch falls through as a narrated video", "make a narrated video on how unions share memory",
         "teach me how the stack grows, interactive video pls", "can you make a diagram of how argv is laid out in memory",
         "What does printf(\"%d\", 'A') print?", "explain how a switch statement falls through, with a video")
SAME = ("intent", "mode", "media", "narration", "first_turn", "build_needed", "confidence")


def test_explanation_first_in_every_workspace():
    """AC-1.3 (v1.4): a teaching request gets the same explanation-first route in every workspace,
    whatever AGENTS.md, MISSION.md or NOTES.md say. The first turn is never a question, and a requested
    medium is built and shown with the explanation, not after an attempt."""
    res = _assert_all("contract", 10)
    root, dirs = _workspaces()
    real = [C_WORKSPACE] * (C_WORKSPACE / "AGENTS.md").is_file()  # Prax's real C workspace, read-only
    try:
        for req in PLAIN:
            base = route.route(req, workspace_dir=dirs["none"])
            for ws in [*dirs.values(), *real]:
                got = route.route(req, workspace_dir=ws)
                assert {k: got[k] for k in SAME} == {k: base[k] for k in SAME}, (str(ws), req, got, base)
                assert got["mode"] not in PRACTICE, (str(ws), req, got)
                ft = got["first_turn"]
                assert ft["kind"] != "question" and ft["questions"] == 0 and ft["artifact"] != "after-attempt", (req, ft)
        video = route.route("Teach me how a switch falls through as a narrated video", workspace_dir=dirs["predict"])
        assert video["mode"] == "lesson" and video["media"] == ["video"] and video["build_needed"] is True, video
    finally:
        shutil.rmtree(root)
    for ws in real:
        got = route.route("make a narrated video on how unions share memory", workspace_dir=ws)
        assert got["mode"] == "lesson" and got["media"] == ["video"] and got["narration"] is True, got
        res["real_c_workspace"] = got["mode"]
    table = json.loads(route.RULES_PATH.read_text())
    assert "workspace" not in table["precedence"], "workspace files may not propose a mode"
    return res


def test_workspace_conflict_reported():
    """AC-1.3 (v1.4): when workspace files ask for prediction first, the route carries a
    `workspace_conflict` note naming the file and line, and does not obey it."""
    want = {"predict": ("AGENTS.md", 5), "notes": ("NOTES.md", 3), "socratic": ("MISSION.md", 3)}
    root, dirs = _workspaces()
    out = {}
    try:
        for name, (fname, line) in want.items():
            got = route.route("Teach me how integer promotion works", workspace_dir=dirs[name])
            wc = got["workspace_conflict"]
            assert wc and wc["file"] == fname and wc["line"] == line, (name, got)
            assert f"{fname}:{line}" in wc["where"] and f"{fname}:{line}" in wc["note"], wc
            assert got["mode"] == "explain" and got["first_turn"]["questions"] == 0, got
            out[name] = wc["where"]
        for name in ("none", "explain"):
            got = route.route("Teach me how integer promotion works", workspace_dir=dirs[name])
            assert got["workspace_conflict"] is None, (name, got)
        assert route.route("Teach me pointers", workspace_dir=dirs["explain"])["workspace_contract"]["asks"] == "explain-first", \
            "'without prediction' must not read as predict-first"
        task = route.route("Fix the off-by-one in basics.c", workspace_dir=dirs["predict"])
        assert task["intent"] == "ordinary_task" and task["workspace_conflict"] is None, task
    finally:
        shutil.rmtree(root)
    if (C_WORKSPACE / "AGENTS.md").is_file():  # Prax's real C workspace, read-only
        real = route.route("Teach me how printf %d works as a narrated video", workspace_dir=C_WORKSPACE)
        assert real["mode"] == "lesson" and real["first_turn"]["questions"] == 0, real
        assert real["workspace_conflict"] and any(w.startswith("AGENTS.md:") for w in real["workspace_conflict"]["where"]), real
        out["real_c_workspace"] = real["workspace_conflict"]["where"]
    return out


def test_practice_only_when_asked():
    """AC-1.3 (v1.4): a prediction-first turn happens only when the request asks for a practice mode
    (quiz, exam-drill, Socratic, "let me predict", "test me"), in any workspace."""
    asked = {"quiz me on integer promotion": "quiz", "test me on pointers": "quiz",
             "let me predict what printf(\"%c\", 66) prints": "predict-first",
             "Socratic: walk me through recursion": "socratic",
             "give me a timed GATE-style drill on sizeof": "exam-drill"}
    root, dirs = _workspaces()
    try:
        for ws in dirs:
            for req, mode in asked.items():
                got = route.route(req, workspace_dir=dirs[ws])
                assert got["mode"] == mode and got["first_turn"]["kind"] == "question", (ws, req, got)
        practice_rows = [c for c in _cases() if c["expect"].get("mode") in PRACTICE]
        for c in _cases():
            if c["expect"].get("mode") not in PRACTICE:
                none = route.route(c["request"], workspace_dir=dirs["none"])
                got = route.route(c["request"], workspace_dir=dirs[c["workspace"] or "none"])
                assert none["mode"] not in PRACTICE or got["mode"] == none["mode"], c["id"]
                assert got["mode"] not in PRACTICE or none["mode"] in PRACTICE, (c["id"], "the workspace started practice")
    finally:
        shutil.rmtree(root)
    return {"asked": len(asked), "practice_rows": len(practice_rows)}


def test_answer_now_overrides_practice():
    """AC-1.3 (v1.4): "answer now" or "just explain" ends questioning in any mode, also when the same
    request asks for practice; "build the full course" is an explicit build."""
    res = _assert_all("override", 6)
    reqs = " | ".join(c["request"].lower() for c in _cases("override"))
    for phrase in ("answer now", "just explain", "full course"):
        assert phrase in reqs, f"no override case for {phrase!r}"
    ends = {"quiz me on pointers. actually, answer now: what is a null pointer?": "quick",
            "let me predict what this prints... no, just explain it": "explain",
            "Socratic is fine but answer now: what does static do": "quick",
            "test me on structs, actually just explain padding": "explain"}
    root, dirs = _workspaces()
    try:
        for ws in dirs:
            for req, mode in ends.items():
                got = route.route(req, workspace_dir=dirs[ws])
                assert got["mode"] == mode and got["first_turn"]["questions"] == 0, (ws, req, got)
    finally:
        shutil.rmtree(root)
    res["ends_practice"] = len(ends)
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
    assert {"intent", "mode", "media", "workspace_contract", "workspace_conflict", "first_turn", "build_needed"} <= set(out)
    return {"exit": res.code, "mode": out["mode"]}


def test_modes_route():
    """The explicit teaching modes route by name (quiz, exam-drill, socratic, qa-expand, predict, explain)."""
    out = {}
    for tag in ("quiz", "exam-drill", "socratic", "qa-expand", "predict", "explain", "full"):
        out[tag] = _assert_all(tag, 2)["cases"]
    return out


# ---------------------------------------------------------------- negation, topic words, confidence (WP1 fix)

def _route(req, ws="none"):
    root, dirs = _workspaces()
    try:
        return route.route(req, workspace_dir=dirs[ws])
    finally:
        shutil.rmtree(root)


def test_fresh_and_adversarial_sets():
    """The reviewer's 60 fresh prompts and the 20 tuning adversarial probes all route as labelled."""
    out = {}
    for tag, minimum in (("fresh-wp1-review", 60), ("adversarial", 20)):
        out[tag] = _assert_all(tag, minimum)["cases"]
    return out


def test_negated_medium_is_never_built():
    """P1-1: a medium inside a negated clause is removed, never built, and the route says so (low confidence)."""
    cases = {"I don't want a video, just explain pointers": [], "no video please, explain recursion": [],
             "teach me pointers, not as a video": [], "quiz me, no cards": [], "explain pointers, no diagrams": [],
             "skip the video, give me flashcards on structs": ["cards"],
             "rather than a video, make me a still of the stack frame": ["still"],
             "make a video of bubble sort but dont narrate it": ["video"]}
    for req, media in cases.items():
        got = _route(req)
        assert got["media"] == media and got["build_needed"] is bool(media), (req, got)
        dropped = "narrate" not in req  # a negated narration keeps the video, so nothing was dropped
        assert (got["confidence"] == "low") is dropped, (req, got)
        assert any(r.startswith("negated") for r in got["reasons"]) is dropped, (req, got)
    assert _route("make a video of bubble sort but dont narrate it")["narration"] is False
    return {"cases": len(cases)}


def test_refusal_beats_quiz_and_contract():
    """P1-2 / D20.7: refusing questions never starts a quiz, and natural override phrasing beats predict-first."""
    for ws in ("none", "predict"):
        for req in ("dont ask me questions, what does static do", "explain without the quiz thing",
                    "pls dont quiz me rn, just tell me what volatile does", "instead of quizzing me, just walk me through unions",
                    "give me the answer directly", "I just want the explanation, no back and forth",
                    "stop asking me to predict, just tell me what happens"):
            got = _route(req, ws)
            assert got["mode"] in ("quick", "explain") and not got["build_needed"], (ws, req, got)
    got = _route("no need to ask me, show me the video on pointers", "predict")
    assert got["mode"] == "lesson" and got["media"] == ["video"], got
    assert _route("Don't just tell me the answer, let me guess first: what does this switch print?")["mode"] == "predict-first"
    assert _route("can you predict how long the build takes")["mode"] != "predict-first"
    return {"ok": True}


def test_topic_words_are_not_media():
    """A medium word used as the topic (video codecs, a deck of cards, the interactive mode of gdb) builds nothing."""
    for req in ("teach me about video codecs", "explain how mp4 compression works", "teach me how to animate in CSS",
                "explain how to shuffle a deck of cards in C", "explain the interactive mode of gdb",
                "how do images get stored in memory", "what is the figure of merit",
                "I watched a video on pointers but I'm still confused",
                "in one sentence, what does the diagram in the lesson show"):
        got = _route(req)
        assert got["intent"] == "teach" and got["media"] == [] and not got["build_needed"], (req, got)
    got = _route("can you make an animation where i can drag the slider and see the bits flip")
    assert got["media"] == ["explorer"], "interaction wins over the noun animation"
    return {"ok": True}


def test_tasks_and_rebuilds():
    """P2-2: a task verb at the start of any clause is a task (explain_after when it also asks why);
    re-rendering or repairing an existing build is intent=rebuild, which builds that lesson only."""
    for req in ("check my code for bugs", "make it faster", "test the parser", "do not explain, just fix it"):
        assert _route(req)["intent"] == "ordinary_task", req
    for req in ("fix the bug and explain what was wrong", "run the tests and explain the failure"):
        got = _route(req, "predict")
        assert got["intent"] == "ordinary_task" and got["explain_after"] is True and got["mode"] is None, got
    for req in ("render the video again, the audio is out of sync", "the animation is out of sync, re-render it",
                "the explainer video you made had wrong numbers, fix it"):
        got = _route(req, "predict")
        assert got["intent"] == "rebuild" and got["mode"] is None and got["media"] == ["video"], got
        assert got["build_needed"] is True and got["first_turn"]["kind"] == "rebuild", got
    assert _route("Fix my understanding of pointers")["intent"] == "teach"
    return {"ok": True}


def test_confidence():
    """`confidence` is high when one reading is clear and low (with reasons) when signals conflict."""
    high = ["Teach me how printf %d works as a narrated video", "Quiz me on C integer promotion",
            "Fix the off-by-one in basics.c", "flashcards + a short video on operator precedence, also quiz me after"]
    for req in high:
        got = _route(req)
        assert got["confidence"] == "high" and got["reasons"] == [], (req, got)
    seq = _route("flashcards + a short video on operator precedence, also quiz me after")
    assert seq["mode"] == "lesson" and seq["also"] == ["quiz"], seq
    low = {"I don't want a video, just explain pointers": "negated",
           "teach me about video codecs": "topic",
           "write a function that reverses a linked list and make a video of it running": "also",
           "make it": "weak"}
    for req, reason in low.items():
        got = _route(req)
        assert got["confidence"] == "low" and any(r.startswith(reason) for r in got["reasons"]), (req, got)
    for ws in ("predict", "notes", "socratic"):
        led, plain = _route("lets do a q&a session on pointers", ws), _route("lets do a q&a session on pointers")
        assert (led["mode"], led["media"], led["confidence"]) == (plain["mode"], plain["media"], plain["confidence"]), led
        assert led["mode"] == "qa-expand" and led["media"] == [] and led["workspace_conflict"], led
    return {"high": len(high), "low": len(low)}


def test_heldback_report():
    """20 adversarial probes kept out of tuning: disjoint from the dev set; accuracy reported, not asserted."""
    held = _cases(path=HELDBACK)
    assert len(held) == 20, len(held)
    dev = {c["request"].lower() for c in _cases()}
    assert not [c["id"] for c in held if c["request"].lower() in dev], "held-back probes leaked into the dev set"
    n, bad = _run(held)
    return {"cases": n, "correct": n - len(bad), "misses": [b["id"] for b in bad]}


def test_workspace_negation_without_apostrophe():
    """A workspace line that says "dont ask prediction questions" is explain-first, not predict-first."""
    ws = host.make_tmp("route-ws-neg-")
    try:
        (ws / "NOTES.md").write_text("Teach directly. dont ask prediction questions before explaining.\n")
        got = route.route("Teach me pointers", workspace_dir=ws)
    finally:
        shutil.rmtree(ws)
    assert got["workspace_contract"]["asks"] == "explain-first" and got["mode"] == "explain", got
    return {"mode": got["mode"]}


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
    assert "workspace" not in table["precedence"], "workspace files may not propose a mode (AC-1.3 v1.4)"
    assert table["precedence"].index("override") < table["precedence"].index("attempt") \
        < table["precedence"].index("media") < table["precedence"].index("intent")
    assert {r["medium"] for r in table["medium_rules"]} == set(table["media_order"])
    for stage, rules in table["mode_rules"].items():
        assert stage in table["precedence"], stage
        for r in rules:
            assert r["mode"] in table["first_turn"], r["id"]
            for p in r["any"] + r.get("unless", []) + r.get("all", []):
                re.compile(route._expand(p, table["macros"]))
    return {"max_branches": max(counts.values()), "functions": len(counts)}
