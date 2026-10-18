"""AC-2.8, AC-8.7 (subprocess boundary), AC-8.8 (no broad except)."""
import ast
import json
import re
import sys

from ptk import host

PTK = host.PKG / "ptk"
BOUNDARY = {"host.py", "node.py"}


def _py():
    return [p for p in PTK.rglob("*.py") if "__pycache__" not in p.parts]


# expect.py may use these standard-library modules and nothing else: no ptk module at all,
# so neither capture code nor anything that imports it can reach the expectations (D17.5).
EXPECT_ALLOWED_IMPORTS = {"math", "fractions", "decimal", "struct", "inspect", "itertools", "functools", "re"}
DYNAMIC_IMPORTS = {"__import__", "import_module", "exec", "eval", "reload"}


def _expect_import_problems(src):
    problems = []
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.ImportFrom):
            if node.level or (node.module or "").split(".")[0] not in EXPECT_ALLOWED_IMPORTS:
                problems.append(f"line {node.lineno}: from {'.' * node.level}{node.module or ''} import ...")
        elif isinstance(node, ast.Import):
            problems += [f"line {node.lineno}: import {a.name}" for a in node.names
                         if a.name.split(".")[0] not in EXPECT_ALLOWED_IMPORTS]
        elif isinstance(node, ast.Call):
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name in DYNAMIC_IMPORTS:
                problems.append(f"line {node.lineno}: dynamic {name}()")
    return problems


def test_expect_independent():
    """AC-2.8: ptk/expect.py imports nothing from ptk.capture, directly, dynamically or transitively."""
    # the checker itself catches each way of reaching capture code
    for planted in ("from .capture import c_runner", "from ptk.capture.c_runner import select",
                    "import ptk.capture", "from . import host", "import os, subprocess",
                    "import importlib\nm = importlib.import_module('ptk.capture')", "m = __import__('ptk')"):
        assert _expect_import_problems(planted), f"the lint missed: {planted!r}"
    problems = _expect_import_problems((PTK / "expect.py").read_text())
    assert not problems, f"expect.py imports outside its allowlist: {problems}"
    # and at run time, in a fresh interpreter: importing ptk.expect loads no other ptk module
    probe = "import sys, json, ptk.expect; print(json.dumps(sorted(m for m in sys.modules if m.startswith('ptk'))))"
    env = host.child_env({"PYTHONPATH": str(host.PKG), "PYTHONDONTWRITEBYTECODE": "1"})
    res = host.run([sys.executable, "-I", "-c", f"import sys; sys.path.insert(0, {str(host.PKG)!r}); {probe}"],
                   env=env, timeout=60)
    assert res.code == 0, res.stderr[-800:]
    loaded = json.loads(res.stdout)
    assert loaded == ["ptk", "ptk.expect"], f"importing ptk.expect loaded {loaded}"
    return {"loaded": loaded}


def test_no_broad_except():
    bad = []
    for p in _py():
        for node in ast.walk(ast.parse(p.read_text())):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None or (isinstance(node.type, ast.Name) and node.type.id in ("Exception", "BaseException")):
                    bad.append(f"{p.relative_to(host.PKG)}:{node.lineno}")
    assert not bad, bad


def test_subprocess_boundary():
    bad = []
    for p in _py():
        if p.name in BOUNDARY:
            continue
        src = p.read_text()
        if re.search(r"^\s*(import subprocess|from subprocess import)", src, re.M) or "os.system(" in src \
                or "os.popen(" in src:
            bad.append(str(p.relative_to(host.PKG)))
    assert not bad, f"only ptk/host.py and ptk/node.py may call subprocess: {bad}"
