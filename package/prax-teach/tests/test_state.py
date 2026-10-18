"""AC-8.4: the ported consent-first state engine (ptk/state) reads v1 state unchanged, migrates to
schema 2 with navigation and evidence kinds, and keeps v2's consent rules.

The v1 fixture (tests/fixtures/state/v1-learner) was written by the real v2 engine, and golden.json is
v2's own `show` and `due` output for it. Learner workspaces for tests live under $PTK_STATE/learners
(D19.1); the C study workspace is never touched.
"""
import contextlib
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from ptk import host
from selftest_support import NotRun

FIXTURE = host.PKG / "tests" / "fixtures" / "state" / "v1-learner"
PORTED = host.PKG / "tests" / "ported_v2"
V2_ENGINE = Path.home() / ".agents" / "skill-library" / "prax-teach-v2" / ".engine"


def _core_python():
    py = host.state_path("venvs", "core", "bin", "python")
    if not py.exists():
        raise NotRun("core venv missing: run `ptk host setup --yes` (fsrs and jsonschema live there)")
    return py


def materialize(prefix="v1-"):
    """Copy the v1 fixture into a fresh private learner workspace and bind consent.location to it."""
    root = host.state_path("learners")
    root.mkdir(exist_ok=True)
    os.chmod(root, 0o700)
    parent = Path(tempfile.mkdtemp(prefix=prefix, dir=root)).resolve()
    ws = parent / "learner"
    shutil.copytree(FIXTURE / "workspace", ws)
    for d in ("assets", "lessons", "reference"):
        (ws / d).mkdir()
    for p in [ws, *ws.rglob("*")]:
        os.chmod(p, 0o700 if p.is_dir() else 0o600)
    learner = ws / "state" / "learner.json"
    learner.write_bytes(learner.read_bytes().replace(b"@WORKSPACE@", str(ws).encode()))
    return parent, ws


def digests(ws):
    return {str(p.relative_to(ws)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(ws.rglob("*")) if p.is_file() and not p.name.startswith(".")}


def golden(ws):
    return json.loads((FIXTURE / "golden.json").read_text().replace("@WORKSPACE@", str(ws)))


HARDLINK = "must not be a hardlink"
HARDLINK_NOTE = ("macOS gave a fresh state file a second hard link (a background process does this to new files "
                 "under ~/Developer at times, see commit 3b89295). The engine refuses hard-linked state on purpose "
                 "(v2's protected cross-learner check), so this run proves nothing either way: rerun")


@contextlib.contextmanager
def hardlink_guard():
    """These tests never plant hard links, so a hard-link refusal is the macOS link flake: not-run, not pass."""
    from ptk.state.errors import SafetyError
    try:
        yield
    except SafetyError as e:
        if HARDLINK in str(e):
            raise NotRun(HARDLINK_NOTE) from e
        raise


def state_cli(*args, py=None):
    """Run `python -m ptk.state` in the core venv (fsrs is pinned there)."""
    env = host.child_env({"PYTHONPATH": str(host.PKG), "PYTHONDONTWRITEBYTECODE": "1"})
    res = host.run([py or _core_python(), "-B", "-m", "ptk.state", *args], env=env, timeout=120)
    if HARDLINK in res.stderr:
        raise NotRun(HARDLINK_NOTE)
    return res


def v2_cli(*args):
    """The installed v2 engine, read-only (-B, no bytecode), or None when v2 isn't installed."""
    py, cli = V2_ENGINE / ".venv" / "bin" / "python", V2_ENGINE / "scripts" / "prax_teach.py"
    if not (py.exists() and cli.exists()):
        return None
    return host.run([py, "-B", cli, *args], env=host.child_env({"PYTHONDONTWRITEBYTECODE": "1"}), timeout=120)


def test_v1_reads():
    parent, ws = materialize()
    try:
        before = digests(ws)
        g = golden(ws)
        show = state_cli("show", str(ws))
        assert show.code == 0, show.stderr
        assert json.loads(show.stdout) == g["show"], "v2.1 shows a v1 workspace differently from v2"
        due = state_cli("due", str(ws), "--at", "2026-09-01T00:00:00Z")
        assert due.code == 0, due.stderr
        assert json.loads(due.stdout) == g["due"], "v2.1 schedules a v1 workspace differently from v2"
        assert digests(ws) == before, "reading a v1 workspace changed its bytes"
        # schema 2 kinds are refused in a v1 workspace until it is migrated
        ev = state_cli("evidence", str(ws), "--session", "s9", "--concept", "switch-fallthrough", "--observed",
                       "traced case 2 to the end unaided", "--gap", "default placement", "--next-action",
                       "trace a switch with default first", "--timestamp", "2026-08-07T09:00:00Z")
        assert ev.code != 0 and "migrat" in ev.stderr, ev.stderr
        nav = state_cli("grant-navigation", str(ws), "--timestamp", "2026-08-07T09:00:00Z")
        assert nav.code != 0 and "migrat" in nav.stderr, nav.stderr
        assert digests(ws) == before
        # the real v2 engine agrees with the golden output on the same bytes (when v2 is installed)
        cross = v2_cli("show", str(ws))
        if cross is not None:
            assert cross.code == 0, cross.stderr
            assert json.loads(cross.stdout) == g["show"]
            assert digests(ws) == before
        return {"events": g["show"]["evidence_event_count"], "v2_cross_check": cross is not None}
    finally:
        shutil.rmtree(parent)


def test_migration():
    parent, ws = materialize("mig-")
    snap = parent / "snapshot"
    try:
        before = digests(ws)
        mig = state_cli("migrate", str(ws), "--snapshot-to", str(snap), "--timestamp", "2026-08-07T08:00:00Z")
        assert mig.code == 0, mig.stderr
        m = json.loads(mig.stdout)
        assert (m["from"], m["to"], m["v1_event_count"]) == ("1", "2", 8), m
        after = digests(ws)
        changed = sorted(k for k in before if before[k] != after.get(k))
        assert changed == ["state/learner.json"], f"migration must rewrite learner.json only, changed: {changed}"
        learner = json.loads((ws / "state" / "learner.json").read_text())
        assert learner["schema_version"] == "2" and learner["migration"]["from"] == "1"
        assert "navigation" not in learner["consent"]["scope"], "migration must not grant navigation consent"
        again = state_cli("migrate", str(ws), "--snapshot-to", str(parent / "snap2"))
        assert again.code != 0 and "already schema 2" in again.stderr
        show = json.loads(state_cli("show", str(ws)).stdout)
        g = golden(ws)["show"]
        for k in ("concepts", "misconceptions", "evidence_event_count", "goal", "learner_id"):
            assert show[k] == g[k], k

        # evidence: independent only, exactly one next action
        ok = state_cli("evidence", str(ws), "--session", "s9", "--concept", "switch-fallthrough", "--observed",
                       "traced case 2 to the end unaided", "--gap", "default placement", "--next-action",
                       "trace a switch with default first", "--timestamp", "2026-08-07T09:00:00Z")
        assert ok.code == 0, ok.stderr
        two = state_cli("evidence", str(ws), "--session", "s9", "--concept", "switch-fallthrough", "--observed",
                        "x", "--gap", "y", "--next-action", "1. trace it 2. write it", "--timestamp",
                        "2026-08-07T09:01:00Z")
        assert two.code != 0 and "exactly one action" in two.stderr, two.stderr
        sys.path.insert(0, str(host.PKG))
        from ptk.state import schema2, state
        from ptk.state.errors import ValidationError
        try:
            schema2.make_evidence(session_id="s9", concept_id="c", observed="watched the video", gap="g",
                                  next_action="a", timestamp="2026-08-07T09:02:00Z", independent=False)
            raise AssertionError("evidence from a watched solution was accepted")
        except ValidationError:
            pass
        # navigation needs its own consent, never lands in sessions.jsonl, never changes projections
        sessions_before = (ws / "state" / "sessions.jsonl").read_bytes()
        concepts_before = (ws / "state" / "concepts.json").read_bytes()
        refused = state_cli("navigate", str(ws), "--session", "s9", "--artifact", "switch-video", "--action", "seek",
                            "--position", "12.5", "--timestamp", "2026-08-07T09:03:00Z")
        assert refused.code != 0 and "consent" in refused.stderr.lower(), refused.stderr
        assert not (ws / "state" / "navigation.jsonl").exists(), "a navigation byte was written without consent"
        assert state_cli("grant-navigation", str(ws), "--timestamp", "2026-08-07T09:04:00Z").code == 0
        for i, (action, pos) in enumerate((("open", None), ("seek", 12.5))):
            args = ["navigate", str(ws), "--session", "s9", "--artifact", "switch-video", "--action", action,
                    "--timestamp", f"2026-08-07T09:0{5 + i}:00Z"]
            if pos is not None:
                args += ["--position", str(pos)]
            res = state_cli(*args)
            assert res.code == 0, res.stderr
        assert (ws / "state" / "sessions.jsonl").read_bytes() == sessions_before
        assert (ws / "state" / "concepts.json").read_bytes() == concepts_before
        nav = [json.loads(ln) for ln in (ws / "state" / "navigation.jsonl").read_text().splitlines()]
        assert [n["action"] for n in nav] == ["open", "seek"]
        try:
            state.validate_event(nav[0])
            raise AssertionError("a navigation record was accepted as an attempt")
        except ValidationError:
            pass
        shown = json.loads(state_cli("show", str(ws)).stdout)
        assert shown["navigation_event_count"] == 2 and len(shown["evidence_records"]) == 1
        # consent withdrawal stops every write, navigation included (v2's rule)
        assert state_cli("disable-persistence", str(ws), "--reason", "test", "--timestamp",
                         "2026-08-07T09:10:00Z").code == 0
        late = state_cli("navigate", str(ws), "--session", "s9", "--artifact", "switch-video", "--action", "close",
                         "--timestamp", "2026-08-07T09:11:00Z")
        assert late.code != 0 and "consent" in late.stderr.lower()
        # rollback restores the v1 bytes and counts what is lost (1 evidence + 2 navigation)
        rb = state_cli("rollback", str(ws), "--snapshot", str(snap))
        assert rb.code == 0, rb.stderr
        r = json.loads(rb.stdout)
        assert r["lost_events"] == 3 and r["lost"] == {"sessions": 1, "reviews": 0, "navigation": 2}, r
        assert "3 event(s)" in rb.stderr
        assert digests(ws) == before, "rollback did not restore the v1 bytes exactly"
        cross = v2_cli("show", str(ws))
        if cross is not None:
            assert cross.code == 0, f"v2 can't read the rolled-back workspace: {cross.stderr}"
        # a tampered snapshot is refused
        (snap / "state" / "sessions.jsonl").write_bytes(b"")
        bad = state_cli("rollback", str(ws), "--snapshot", str(snap))
        assert bad.code != 0 and "changed" in bad.stderr, bad.stderr
        return {"lost_events": r["lost_events"], "v2_reads_rollback": cross is not None}
    finally:
        shutil.rmtree(parent)


def test_ported_v2_suite():
    """The v2 state tests that still apply (plan/PROTECTED-MAP.md), run unchanged in substance against
    ptk/state in the core venv."""
    py = _core_python()
    env = host.child_env({"PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(host.state_path("tmp")) + "/"})
    res = host.run([py, "-B", "-m", "unittest", "discover", "-s", str(PORTED), "-p", "test_*.py"],
                   cwd=PORTED, env=env, timeout=1800)
    tail = res.stderr.strip().splitlines()
    ran = next((ln for ln in tail if ln.startswith("Ran ")), "")
    if res.code != 0:
        blocks = res.stderr.split("=" * 70)[1:]
        failures = [b for b in blocks if b.lstrip().startswith(("FAIL:", "ERROR:"))]
        if failures and all(HARDLINK in b for b in failures):
            raise NotRun(f"{len(failures)} failures, all hard-link refusals. " + HARDLINK_NOTE)
    assert res.code == 0 and tail and tail[-1].startswith("OK"), res.stderr[-3000:]
    count = int(ran.split()[1])
    assert count == 106, f"expected the 106 ported v2 tests to run, got {count}"
    return {"ran": count}
