"""AC-8.2 and AC-8.6: per-host discovery and install/rollback, in throwaway HOMEs under
$PTK_STATE/hosts/<host>/ (D19.3). The real ~/.agents, ~/.claude, ~/.codex, ~/.hermes and ~/.config are
only read, before and after, to prove nothing there changed.

Discovery follows each host's documented rules (ptk/package.py HOSTS). Where the host itself is installed
the test also asks it: Codex through `codex app-server` skills/list with HOME and CODEX_HOME pointed at
the throwaway home, Hermes through its own iter_skill_index_files. OpenCode isn't installed here, and
Claude Code needs a login, so those two use the documented rules only (reported in the result).
"""
import json
import os
import shutil
import sys
from pathlib import Path

from ptk import host, package

REAL_DIRS = [".agents/skills", ".agents/skill-library", ".claude/skills", ".codex/skills", ".hermes/skills",
             ".config/opencode/skills"]
CODEX = shutil.which("codex") or os.path.expanduser("~/.local/bin/codex")
HERMES_AGENT = Path(os.path.expanduser("~/.hermes/hermes-agent"))


def _real_fingerprint():
    """Names, link targets and mtimes of the real host skill dirs (read-only)."""
    home = Path(os.path.expanduser("~"))
    out = {}
    for rel in REAL_DIRS:
        d = home / rel
        if not d.exists():
            out[rel] = None
            continue
        rows = []
        for e in sorted(os.scandir(d), key=lambda e: e.name):
            st = e.stat(follow_symlinks=False)
            rows.append((e.name, os.readlink(e.path) if e.is_symlink() else None, st.st_mtime_ns))
        out[rel] = (os.lstat(d).st_mtime_ns, rows)
    return out


def _tree():
    res = package.build(out=host.state_path("hosts", "tree", "prax-teach"))
    assert res["packaged"], res
    return Path(res["out"])


def _codex_prax(home, cwd):
    """Real Codex: skills it lists for `cwd` with this HOME, kept to prax-teach installs."""
    if not os.access(CODEX, os.X_OK):
        return None
    home = Path(home)
    (home / ".codex").mkdir(exist_ok=True)
    msgs = [{"id": 1, "method": "initialize", "params": {"clientInfo": {"name": "ptk-hosts", "version": "1"},
                                                         "capabilities": {"experimentalApi": True}}},
            {"method": "initialized"},
            {"id": 2, "method": "skills/list", "params": {"cwds": [str(cwd)], "forceReload": True}}]
    env = {"HOME": str(home), "CODEX_HOME": str(home / ".codex"), "PATH": "/usr/bin:/bin", "LANG": "C"}
    replies = host.run_jsonrpc([CODEX, "app-server", "--stdio"], msgs, cwd=str(home), env=env, timeout=120)
    skills = [s for g in replies[2]["result"]["data"] for s in g["skills"]]
    lib = (home / ".agents" / "skill-library").resolve()
    return sorted(s["name"] for s in skills if s["name"].startswith("prax-teach")
                  or Path(s["path"]).resolve().is_relative_to(lib))


def _hermes_prax(home):
    """Real Hermes walker over ~/.hermes/skills of this HOME, kept to prax-teach installs."""
    if not (HERMES_AGENT / "agent" / "skill_utils.py").is_file():
        return None
    code = ("import sys, json; from pathlib import Path; sys.path.insert(0, sys.argv[1]); "
            "from agent.skill_utils import iter_skill_index_files; "
            "print(json.dumps([str(p) for p in iter_skill_index_files(Path(sys.argv[2]), 'SKILL.md')]))")
    env = {"HOME": str(home), "PATH": "/usr/bin:/bin", "LANG": "C", "PYTHONDONTWRITEBYTECODE": "1"}
    res = host.run([sys.executable, "-B", "-I", "-c", code, str(HERMES_AGENT), str(Path(home) / ".hermes" / "skills")],
                   env=env, timeout=120)
    assert res.code == 0, res.stderr[-800:]
    lib = (Path(home) / ".agents" / "skill-library").resolve()
    return sorted(str(Path(p).resolve().relative_to(lib)) for p in json.loads(res.stdout)
                  if Path(p).resolve().is_relative_to(lib))


def _count(name, home, cwd):
    return package.prax_entries(package.discover(name, home, cwd), [Path(home) / ".agents" / "skill-library"])


def test_one_entry_per_host():
    before = _real_fingerprint()
    tree = _tree()
    root = host.state_path("hosts")
    fake_v2 = package.write_fake_v2(root / "v2-fixture")
    result = {}
    for name in package.HOSTS:
        home = package.make_home(root / name / "discovery", fake_v2)
        rec = package.install(tree, home)                       # side by side, not registered (D17.12)
        cwds = {"home": home, "tree-root": Path(rec["installed"]), "tree-inner": Path(rec["installed"]) / "ptk" / "state"}
        side = {k: _count(name, home, c) for k, c in cwds.items()}
        for k, entries in side.items():
            assert len(entries) == 1, (name, "side by side", k, entries)
            assert Path(entries[0]["real"]) == (home / ".agents" / "skill-library" / "prax-teach-v2" / "SKILL.md").resolve()
        package.install(tree, home, flip=True)                 # the acceptance flip, in the throwaway home
        flipped = {k: _count(name, home, c) for k, c in cwds.items()}
        for k, entries in flipped.items():
            assert len(entries) == 1, (name, "flipped", k, entries)
            assert Path(entries[0]["real"]) == (home / package.CANDIDATE / "SKILL.md").resolve()
            assert entries[0]["name"] == "prax-teach"
        # negative control: nested SKILL.md files in the tree are seen by the recursive hosts
        planted = home / package.CANDIDATE
        (planted / "ptk" / "state" / ".engine").mkdir()
        (planted / "ptk" / "state" / ".engine" / "SKILL.md").write_text("---\nname: prax-teach-engine\n---\n")
        (planted / "legacy").mkdir()
        (planted / "legacy" / "SKILL.md").write_text("---\nname: prax-teach-old\ndescription: planted\n---\n")
        seen = len(_count(name, home, home))
        if name == "claude-code":
            assert seen == 1, "Claude Code reads one level only"
        else:
            assert seen > 1, f"{name}: the discovery model missed planted nested SKILL.md files"
        real = None
        if name == "codex":
            real = {"planted": _codex_prax(home, home)}
            shutil.rmtree(planted / "ptk" / "state" / ".engine")
            shutil.rmtree(planted / "legacy")
            if real["planted"] is not None:
                real["clean"] = {k: _codex_prax(home, c) for k, c in cwds.items()}
                for k, names in real["clean"].items():
                    assert names == ["prax-teach"], ("real codex", k, names)
                assert len(real["planted"]) > 1, real
        elif name == "hermes":
            real = {"planted": _hermes_prax(home)}
            shutil.rmtree(planted / "ptk" / "state" / ".engine")
            shutil.rmtree(planted / "legacy")
            if real["planted"] is not None:
                real["clean"] = _hermes_prax(home)
                assert real["clean"] == ["prax-teach-v2.1/SKILL.md"], real
                assert len(real["planted"]) > 1, real
        result[name] = {"side_by_side": {k: [e["name"] for e in v] for k, v in side.items()},
                        "flipped": {k: [e["name"] for e in v] for k, v in flipped.items()},
                        "planted_nested_seen": seen, "real_host": real if real and real.get("planted") is not None
                        else "documented rules only"}
    assert _real_fingerprint() == before, "a real host skill directory changed"
    return result


def test_install_rollback():
    from test_state import digests, hardlink_guard, materialize, v2_cli
    from ptk.state import schema2
    before_real = _real_fingerprint()
    tree = _tree()
    root = host.state_path("hosts")
    fake_v2 = package.write_fake_v2(root / "v2-fixture")
    result = {}
    for name in package.HOSTS:
        home = package.make_home(root / name / "rollback", fake_v2)
        link = home / package.V2_LINK
        target_before = os.readlink(link)
        parent, ws = materialize(f"{name}-")
        try:
            with hardlink_guard():
                learner_before = digests(ws)
                rec = package.install(tree, home, flip=True, learners=[ws], when="2026-10-18T12:00:00Z")
                assert Path(rec["record"]).is_file()
                assert os.readlink(link) == "../skill-library/prax-teach-v2.1"
                on = _count(name, home, home)
                assert len(on) == 1 and on[0]["name"] == "prax-teach", on
                assert json.loads((ws / "state" / "learner.json").read_text())["schema_version"] == "2"
                # learning continues on v2.1: one evidence record and two navigation events after the snapshot
                schema2.append_evidence(str(ws), schema2.make_evidence(
                    session_id="s20", concept_id="switch-fallthrough", observed="predicted the fall-through unaided",
                    gap="none seen", next_action="try a switch with default in the middle", timestamp="2026-10-18T12:10:00Z"))
                schema2.grant_navigation(str(ws), granted_at="2026-10-18T12:11:00Z")
                for i, action in enumerate(("open", "seek")):
                    schema2.append_navigation(str(ws), schema2.make_navigation(
                        session_id="s20", artifact_id="switch-ive", action=action, position=None if i == 0 else 4.0,
                        timestamp=f"2026-10-18T12:1{2 + i}:00Z"))
                printed = []
                out = package.rollback(rec["record"], log=printed.append)
                assert out["link_restored"] and os.readlink(link) == target_before
                assert out["lost_events"] == 3, out
                assert printed == ["rollback: 3 learner event(s) recorded after the snapshot are lost"], printed
                assert digests(ws) == learner_before, "the learner snapshot was not restored byte for byte"
                back = _count(name, home, home)
                assert len(back) == 1 and back[0]["name"] == "prax-teach-v2", back
                v2 = v2_cli("show", str(ws))
                if v2 is not None:
                    assert v2.code == 0, f"v2 can't read the restored learner state: {v2.stderr}"
                result[name] = {"lost_events": out["lost_events"], "v2_reads_restored": v2 is not None}
        finally:
            shutil.rmtree(parent)
    assert _real_fingerprint() == before_real, "a real host skill directory changed"
    return result
