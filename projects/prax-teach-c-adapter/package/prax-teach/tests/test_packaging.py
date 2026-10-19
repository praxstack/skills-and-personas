"""AC-8.1: `ptk package` builds an install tree of at most 5 MB with no home paths, no __pycache__ and no
SKILL.md below the root. The checks here are written out again rather than calling package.check_tree,
and each one is first shown to catch a planted problem."""
import hashlib
import json
import os
import shutil
import sys

from _util import ptk_cmd
from ptk import host, package

LIMIT = 5 * 1024 * 1024
NEEDLE = ("/" + "Users" + "/").encode()


def _scan(root):
    problems, total = [], 0
    for dirpath, dirs, files in os.walk(root):
        for d in dirs:
            if d == "__pycache__":
                problems.append(f"cache:{os.path.relpath(os.path.join(dirpath, d), root)}")
        for f in files:
            p = os.path.join(dirpath, f)
            rel = os.path.relpath(p, root)
            data = open(p, "rb").read()
            total += len(data)
            if NEEDLE in data:
                problems.append(f"home:{rel}")
            if f.lower() == "skill.md" and rel != "SKILL.md":
                problems.append(f"nested:{rel}")
    if total > LIMIT:
        problems.append(f"size:{total}")
    return problems, total


def test_tree_limits():
    out = host.state_path("package-test", "prax-teach")
    res = host.run([*ptk_cmd(), "package", "--out", str(out)], env=host.child_env(), timeout=600)
    assert res.code == 0, res.stdout[-2000:] + res.stderr[-2000:]
    rep = json.loads(res.stdout)
    assert rep["packaged"] and not rep["problems"], rep["problems"]
    problems, total = _scan(out)
    assert not problems, problems
    assert total <= LIMIT
    # the manifest lists every shipped file with its sha256, and nothing else
    man = json.loads((out / package.MANIFEST).read_text())
    listed = {e["path"]: e["sha256"] for e in man["files"]}
    on_disk = {os.path.relpath(os.path.join(d, f), out): None for d, _, fs in os.walk(out) for f in fs}
    assert set(listed) | {package.MANIFEST} == set(on_disk), sorted(set(listed) ^ set(on_disk))
    for rel, digest in listed.items():
        assert hashlib.sha256((out / rel).read_bytes()).hexdigest() == digest, rel
    assert os.access(out / "bin" / "ptk", os.X_OK)
    for must in ("SKILL.md", "ptk/state/schema2.py", "node/render_markdown.mjs", "registry/tools.json",
                 "assets/fonts/SHA256SUMS", "tests/test_state.py"):
        assert (out / must).is_file(), must
    # reproducible: a second build gives the same tree hash
    again = host.run([*ptk_cmd(), "package", "--out", str(out)], env=host.child_env(), timeout=600)
    assert json.loads(again.stdout)["tree_sha256"] == rep["tree_sha256"]
    # the scanner catches each planted problem (so a clean result means something)
    bad = host.state_path("package-test", "planted")
    if bad.exists():
        shutil.rmtree(bad)
    shutil.copytree(out, bad)
    (bad / "ptk" / "state" / "old").mkdir()
    (bad / "ptk" / "state" / "old" / "SKILL.md").write_text("---\nname: prax-teach-old\n---\n")
    (bad / "ptk" / "__pycache__").mkdir()
    (bad / "references" / "x.md").write_bytes(b"see " + NEEDLE + b"someone/x")
    (bad / "assets" / "big.bin").write_bytes(b"\0" * (LIMIT + 1))
    planted, _ = _scan(bad)
    kinds = {p.split(":")[0] for p in planted}
    assert kinds == {"cache", "home", "nested", "size"}, planted
    assert len(package.check_tree(bad)["problems"]) >= 4
    shutil.rmtree(bad)
    # --dry-run writes nothing; a host directory is refused before anything is written
    dry = host.state_path("package-test", "dry-run-target")
    if dry.exists():
        shutil.rmtree(dry)
    res = host.run([*ptk_cmd(), "package", "--dry-run", "--out", str(dry)], env=host.child_env(), timeout=300)
    assert res.code == 0 and not dry.exists(), res.stderr
    probe = os.path.expanduser("~/.claude/skills/ptk-package-refusal-probe")
    refused = host.run([*ptk_cmd(), "package", "--out", probe], env=host.child_env(), timeout=300)
    assert refused.code != 0 and not os.path.exists(probe), refused.stderr
    # the installed tree runs on its own: probe and one of its own tests, with the package's own code
    env = host.child_env({"PTK_STATE": str(host.state_dir())})
    pr = host.run([out / "bin" / "ptk", "host", "probe", "--artifact", "still"], env=env, timeout=300)
    assert pr.code == 0, pr.stderr[-800:]
    st = host.run([sys.executable, "-B", "-m", "ptk", "selftest", "-k", "test_lint.py::test_no_broad_except"],
                  env=host.child_env({"PYTHONPATH": str(out), "PTK_STATE": str(host.state_dir())}), cwd=out,
                  timeout=300)
    assert st.code == 0, st.stderr[-800:]
    assert not list(out.rglob("__pycache__")), "running the installed tree wrote bytecode into it"
    return {"files": rep["files"], "bytes": total, "tree_sha256": rep["tree_sha256"]}
