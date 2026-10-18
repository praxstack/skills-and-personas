"""AC-2.8, AC-8.7 (subprocess boundary), AC-8.8 (no broad except)."""
import ast
import re

from ptk import host

PTK = host.PKG / "ptk"
BOUNDARY = {"host.py", "node.py"}


def _py():
    return [p for p in PTK.rglob("*.py") if "__pycache__" not in p.parts]


def test_expect_independent():
    tree = ast.parse((PTK / "expect.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert "capture" not in (node.module or ""), "expect.py imports capture code"
            assert node.level == 0 or node.module not in ("capture",), node.module
        if isinstance(node, ast.Import):
            assert not any("capture" in a.name for a in node.names)


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
