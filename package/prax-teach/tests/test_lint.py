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


BROAD = {"Exception", "BaseException"}


def _broad_problems(src, label="<src>"):
    """Every handler that catches Exception or BaseException: bare, by name, as builtins.X, or inside a tuple."""
    def broad(t):
        if t is None:
            return True
        if isinstance(t, ast.Name):
            return t.id in BROAD
        if isinstance(t, ast.Attribute):
            return t.attr in BROAD
        if isinstance(t, ast.Tuple):
            return any(broad(e) for e in t.elts)
        return False
    return [f"{label}:{n.lineno}" for n in ast.walk(ast.parse(src))
            if isinstance(n, (ast.ExceptHandler,)) and broad(n.type)]


def test_no_broad_except():
    """AC-8.8: no `except Exception`, `except BaseException` or bare `except:` anywhere in ptk/,
    including tuples and `builtins.Exception`. The checker proves it catches each form first."""
    for planted in ("try:\n x()\nexcept:\n pass", "try:\n x()\nexcept Exception:\n pass",
                    "try:\n x()\nexcept (ValueError, Exception) as e:\n pass",
                    "try:\n x()\nexcept builtins.BaseException:\n pass",
                    "try:\n x()\nexcept* Exception:\n pass"):
        assert _broad_problems(planted), f"the lint missed: {planted!r}"
    assert not _broad_problems("try:\n x()\nexcept (ValueError, OSError):\n pass")
    bad = []
    for p in _py():
        bad += _broad_problems(p.read_text(), str(p.relative_to(host.PKG)))
    assert not bad, bad
    return {"files": len(_py())}


SPAWN_MODULES = {"subprocess", "multiprocessing", "pty", "pexpect", "sh", "plumbum", "concurrent.futures.process"}
SPAWN_CALLS = {"system", "popen", "spawnl", "spawnle", "spawnlp", "spawnlpe", "spawnv", "spawnve", "spawnvp",
               "spawnvpe", "execl", "execle", "execlp", "execlpe", "execv", "execve", "execvp", "execvpe", "fork",
               "forkpty", "posix_spawn", "posix_spawnp", "startfile", "create_subprocess_exec",
               "create_subprocess_shell", "ProcessPoolExecutor"}


def _spawn_problems(src, label="<src>"):
    """Any way to start a process: importing a spawning module (directly, from-import or dynamically),
    or calling os.system/popen/spawn*/exec*/fork/posix_spawn, asyncio's subprocess helpers, a process pool."""
    out = []
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Import):
            out += [f"{label}:{n.lineno} import {a.name}" for a in n.names
                    if a.name in SPAWN_MODULES or a.name.split(".")[0] in SPAWN_MODULES]
        elif isinstance(n, ast.ImportFrom):
            mod = n.module or ""
            if mod in SPAWN_MODULES or mod.split(".")[0] in SPAWN_MODULES:
                out.append(f"{label}:{n.lineno} from {mod} import ...")
            out += [f"{label}:{n.lineno} from {mod} import {a.name}" for a in n.names if a.name in SPAWN_CALLS]
        elif isinstance(n, ast.Call):
            f = n.func
            name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
            if name in SPAWN_CALLS:
                out.append(f"{label}:{n.lineno} {name}()")
            if name in ("__import__", "import_module") and n.args and isinstance(n.args[0], ast.Constant) \
                    and str(n.args[0].value).split(".")[0] in SPAWN_MODULES:
                out.append(f"{label}:{n.lineno} dynamic import of {n.args[0].value}")
    return out


def _boundary_env_problems(src, label):
    """In host.py and node.py every subprocess call passes an env built by the contract helper."""
    out = []
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) \
                and n.func.value.id == "subprocess" and n.func.attr in ("Popen", "run", "call", "check_call",
                                                                        "check_output"):
            env = next((k.value for k in n.keywords if k.arg == "env"), None)
            ok = isinstance(env, ast.Call) and getattr(env.func, "id", None) == "contract_env"
            if not ok:
                out.append(f"{label}:{n.lineno} subprocess.{n.func.attr} without env=contract_env(...)")
    return out


def test_subprocess_boundary():
    """AC-8.7: only ptk/host.py and ptk/node.py start processes, and host.py hands every child the
    spec 5.5 env through contract_env(). The checkers prove they catch each planted form first."""
    for planted in ("import subprocess", "from subprocess import run", "import os\nos.system('x')",
                    "import os\nos.posix_spawn('x', [], {})", "os.execvp('x', [])", "from os import popen",
                    "import importlib\nimportlib.import_module('subprocess')", "__import__('subprocess')",
                    "import asyncio\nasyncio.create_subprocess_exec('x')", "import multiprocessing",
                    "from concurrent.futures import ProcessPoolExecutor", "import pty"):
        assert _spawn_problems(planted), f"the lint missed: {planted!r}"
    assert _boundary_env_problems("import subprocess\nsubprocess.run(['x'])", "p")
    assert _boundary_env_problems("import subprocess\nsubprocess.Popen(['x'], env=os.environ)", "p")
    assert not _boundary_env_problems("import subprocess\nsubprocess.run(['x'], env=contract_env(e))", "p")
    bad = []
    for p in _py():
        if p.parent == PTK and p.name in BOUNDARY:
            bad += _boundary_env_problems(p.read_text(), p.name)
            continue
        bad += _spawn_problems(p.read_text(), str(p.relative_to(host.PKG)))
    assert not bad, f"only ptk/host.py and ptk/node.py may start processes, always with the env contract: {bad}"
    node_src = (PTK / "node.py").read_text()
    assert not _spawn_problems(node_src), "node.py goes through host.run, it never spawns directly"
    return {"files": len(_py())}


def test_guard_constructs_match_schema():
    """Review WP2 P1-1: the constructs a claim may declare in `overrides` are exactly the ones the
    source guard refuses, so neither list can drift from the other."""
    from ptk.capture import guard
    schema = json.loads((host.PKG / "schemas" / "lesson.schema.json").read_text())
    enum = schema["$defs"]["claim"]["properties"]["overrides"]["items"]["enum"]
    assert sorted(enum) == sorted(guard.CONSTRUCTS), (sorted(enum), sorted(guard.CONSTRUCTS))
    return {"constructs": len(enum)}
