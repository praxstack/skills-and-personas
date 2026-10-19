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


@contextlib.contextmanager
def hardlink_guard():
    """Kept for callers: a hard link macOS backup/versioning adds to a learner's own state file is accepted with a
    warning (PROTECTED-MAP, D22.3), so a hard-link refusal is a real failure and is not masked."""
    yield


def state_cli(*args, py=None):
    """Run `python -m ptk.state` in the core venv (fsrs is pinned there)."""
    env = host.child_env({"PYTHONPATH": str(host.PKG), "PYTHONDONTWRITEBYTECODE": "1"})
    return host.run([py or _core_python(), "-B", "-m", "ptk.state", *args], env=env, timeout=120)


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
    assert res.code == 0 and tail and tail[-1].startswith("OK"), res.stderr[-3000:]
    count = int(ran.split()[1])
    assert count == 106, f"expected the 106 ported v2 tests to run, got {count}"
    return {"ran": count}


# ---------------------------------------------------------------- hard links (D22.3, PROTECTED-MAP)
# Learner state binds content, not link counts. Each state file's inode carries its learner workspace binding
# (an extended attribute stamped when the engine writes it), and the state directory carries the workspace's own.
# A same-owner extra link is read, with a warning, only when the two match. Writes always replace onto a fresh inode.


def _need_bindings(path):
    from ptk.state import io as sio
    supported = getattr(sio, "bindings_supported", None)
    if supported is not None and not supported(path):
        raise NotRun("this filesystem has no extended attributes: hard-linked state is refused outright (v2 rule)")


def _learners_parent(prefix):
    root = host.state_path("learners")
    root.mkdir(exist_ok=True)
    os.chmod(root, 0o700)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=root)).resolve()


def _init(ws, learner="kai"):
    res = state_cli("init", str(ws), "--learner-id", learner, "--goal", "Trace a switch statement", "--consent",
                    "--timestamp", "2026-08-07T08:00:00Z")
    assert res.code == 0, res.stderr


def _evidence(ws, observed, minute):
    res = state_cli("evidence", str(ws), "--session", "s1", "--concept", "switch-fallthrough", "--observed",
                    observed, "--gap", "default placement", "--next-action", "trace a switch with default first",
                    "--timestamp", f"2026-08-07T09:{minute:02d}:00Z")
    assert res.code == 0, res.stderr


def test_cross_learner_hardlink_refused():
    """Learner B's sessions.jsonl hard-linked into learner A's workspace (both learners even share a learner id):
    show and export refuse with exit 5, no export file is written, and B's file is unchanged."""
    parent = _learners_parent("xlink-")
    try:
        _need_bindings(parent)
        a, b = parent / "a", parent / "b"
        _init(a)
        _init(b)
        _evidence(b, "B traced case 2 alone: a secret only B's workspace holds", 1)
        before = (b / "state" / "sessions.jsonl").read_bytes()
        (a / "state" / "sessions.jsonl").unlink()
        os.link(b / "state" / "sessions.jsonl", a / "state" / "sessions.jsonl")
        shown = state_cli("show", str(a))
        assert shown.code == 5, (shown.code, shown.stdout[:300], shown.stderr)
        assert "hardlink" in shown.stderr.lower() and "another learner" in shown.stderr, shown.stderr
        assert "secret" not in shown.stdout
        leak = parent / "leak.zip"
        exported = state_cli("export", str(a), str(leak), "--timestamp", "2026-08-07T10:00:00Z")
        assert exported.code == 5, (exported.code, exported.stderr)
        assert not leak.exists(), "learner B's state was exported from learner A's workspace"
        assert (b / "state" / "sessions.jsonl").read_bytes() == before
        # the same holds for the workspace lock: B's lock linked into A is refused before A opens it
        (a / "state" / "sessions.jsonl").unlink()
        shutil.copyfile(b / "state" / "sessions.jsonl", a / "state" / "sessions.jsonl")
        os.chmod(a / "state" / "sessions.jsonl", 0o600)
        (a / ".prax-teach.lock").unlink(missing_ok=True)
        os.link(b / ".prax-teach.lock", a / ".prax-teach.lock")
        locked = state_cli("show", str(a))
        assert locked.code == 5 and "hardlink" in locked.stderr.lower(), (locked.code, locked.stderr)
        return {"show": shown.stderr.strip()[:160], "lock": locked.stderr.strip()[:160]}
    finally:
        shutil.rmtree(parent)


def test_backup_link_to_own_file_reads_with_warning():
    """A backup-style extra link (what macOS backupd/revisiond add) to a learner's own state file and lock is read:
    show succeeds and prints one warning naming the file."""
    parent = _learners_parent("blink-")
    try:
        _need_bindings(parent)
        ws = parent / "learner"
        _init(ws)
        _evidence(ws, "traced case 2 to the end unaided", 1)
        clean = state_cli("show", str(ws))
        assert clean.code == 0, clean.stderr
        os.link(ws / "state" / "sessions.jsonl", parent / "backup-sessions.jsonl")
        os.link(ws / ".prax-teach.lock", parent / "backup-lock")
        shown = state_cli("show", str(ws))
        assert shown.code == 0, shown.stderr
        assert json.loads(shown.stdout) == json.loads(clean.stdout)
        assert "hard link" in shown.stderr.lower() and "sessions.jsonl" in shown.stderr, shown.stderr
        return {"warning": shown.stderr.strip()[:200]}
    finally:
        shutil.rmtree(parent)


def test_write_never_goes_through_an_alias():
    """After a write, an outside alias of the old file still holds the old bytes, and the workspace file is a new
    inode: writes replace onto a fresh inode and never write through a link."""
    parent = _learners_parent("wlink-")
    try:
        _need_bindings(parent)
        ws = parent / "learner"
        _init(ws)
        _evidence(ws, "traced case 2 to the end unaided", 1)
        live = ws / "state" / "sessions.jsonl"
        alias = parent / "alias-sessions.jsonl"
        os.link(live, alias)
        old_bytes, old_inode = alias.read_bytes(), alias.stat().st_ino
        _evidence(ws, "traced case 3 to the end unaided", 2)
        assert alias.read_bytes() == old_bytes, "a state write went through an outside alias"
        assert live.stat().st_ino != old_inode, "the state write reused the aliased inode"
        assert len(live.read_bytes()) > len(old_bytes)
        return {"old_inode": old_inode, "new_inode": live.stat().st_ino}
    finally:
        shutil.rmtree(parent)



def test_backup_link_to_delete_journal_recovers():
    """The full-deletion journal sits beside the workspace, outside every state directory. Its content names the
    exact workspace it deletes, so a backup link to it is read when the engine stamped it: a confirmed deletion
    that was interrupted still finishes when the name is reused."""
    from unittest import mock
    from ptk.state import state as state_module
    parent = _learners_parent("jlink-")
    try:
        _need_bindings(parent)
        ws = parent / "course"
        _init(ws)
        _evidence(ws, "traced case 2 to the end unaided", 1)

        def partially_remove(descriptor):
            os.unlink("state/sessions.jsonl", dir_fd=descriptor)
            raise OSError("injected partial recursive deletion")

        with mock.patch.object(state_module, "_remove_directory_contents", side_effect=partially_remove):
            try:
                state_module.delete_workspace(str(ws), dry_run=False, confirm=True)
            except OSError as e:
                assert "partial recursive deletion" in str(e)
            else:
                raise AssertionError("the injected partial deletion did not fail")
        journal = next(parent.glob(".course*transaction*"))
        os.link(journal, parent / "backup-journal")
        again = state_cli("init", str(ws), "--learner-id", "kai", "--goal", "Trace a switch statement", "--consent",
                          "--timestamp", "2026-08-07T11:00:00Z")
        assert again.code == 0, again.stderr
        assert not journal.exists() and not (parent / ".course.prax-teach-deleting").exists()
        return {"journal": journal.name}
    finally:
        shutil.rmtree(parent)

def test_legacy_unbound_state_migrates():
    """Files written by older code carry no binding. With one link they are read and stamped (adopted) on the first
    command; an unbound file with an extra link is refused until `rebind --confirm` copies it onto a fresh,
    bound inode."""
    parent, ws = materialize("legacy-")
    try:
        _need_bindings(parent)
        g = golden(ws)
        before = digests(ws)
        # (1) adoption: one link, read normally, bytes unchanged; an extra link afterwards is a backup link.
        # Google Drive may already have linked the fresh copies; then the precondition (legacy files with one link)
        # does not hold and the refusal that follows is correct, so the step cannot be run.
        linked = sorted(str(p.relative_to(ws)) for p in ws.rglob("*") if p.is_file() and p.stat().st_nlink > 1)
        if linked:
            raise NotRun(f"an outside tool (Google Drive) linked the legacy fixture before the first command: {linked}")
        first = state_cli("show", str(ws))
        assert first.code == 0, first.stderr
        assert digests(ws) == before, "adopting legacy state changed its bytes"
        os.link(ws / "state" / "sessions.jsonl", parent / "backup-link-sessions.jsonl")
        shown = state_cli("show", str(ws))
        assert shown.code == 0, shown.stderr
        assert json.loads(shown.stdout) == g["show"]
        assert "hard link" in shown.stderr.lower() and "sessions.jsonl" in shown.stderr, shown.stderr
        # (2) an unbound file that already has an extra link is refused, and rebind is the explicit way out
        from ptk.state import io as sio
        concepts = ws / "state" / "concepts.json"
        fresh = concepts.with_name("concepts.fresh")
        shutil.copyfile(concepts, fresh)
        os.chmod(fresh, 0o600)
        os.replace(fresh, concepts)
        assert sio.read_binding(concepts) is None
        os.link(concepts, parent / "old-link-concepts.json")
        # Google Drive for desktop stages a second link to any new file in a folder it backs up (EVIDENCE-HARDLINKS);
        # a sibling link stands in for it, so the test does not depend on Drive's timing
        os.link(concepts, parent / "drive-staging-concepts.json")
        old_inode, old_bytes = concepts.stat().st_ino, concepts.read_bytes()
        refused = state_cli("show", str(ws))
        assert refused.code == 5 and "rebind" in refused.stderr, (refused.code, refused.stderr)
        dry = state_cli("rebind", str(ws))
        assert dry.code == 4 and "state/concepts.json" in dry.stderr, (dry.code, dry.stderr)
        done = state_cli("rebind", str(ws), "--confirm")
        assert done.code == 0, done.stderr
        # MISSION.md and RESOURCES.md are listed too when macOS backup has linked them already
        assert "state/concepts.json" in json.loads(done.stdout)["rebound"], done.stdout
        # rebind copies onto a fresh inode: the old inode (still reachable through both outside links) keeps its
        # bytes and gets no binding, and the workspace file is a different inode. The rc1 check here was
        # st_nlink == 1 on the old link, which Google Drive's staging link breaks at random (A5 item 4).
        old_link = parent / "old-link-concepts.json"
        assert old_link.stat().st_ino == old_inode and concepts.stat().st_ino != old_inode, \
            "rebind wrote through the old link"
        assert old_link.read_bytes() == old_bytes and sio.read_binding(old_link) is None, \
            "rebind changed the old inode"
        assert sio.read_binding(concepts) == sio.read_binding(ws / "state")
        assert digests(ws) == before, "rebind changed state bytes"
        again = state_cli("show", str(ws))
        assert again.code == 0 and json.loads(again.stdout) == g["show"], again.stderr
        return {"refused": refused.stderr.strip()[:200]}
    finally:
        shutil.rmtree(parent)


def test_symlinked_and_foreign_state_refused():
    """Still refused: a symlinked state file, a hard-linked state file owned by someone else (simulated with a
    patched os.geteuid), and a non-regular file. A bound extra link owned by this user is accepted with a warning."""
    import warnings
    from unittest import mock
    from ptk.state import io as sio
    from ptk.state.errors import SafetyError
    out = {}
    parent, ws = materialize("link-neg-")
    try:
        _need_bindings(parent)
        assert sio.secure_workspace(ws) == ws.resolve()  # adopts the one-link legacy files
        target = ws / "state" / "learner.json"
        os.link(target, parent / "other-link")
        real_uid = target.stat().st_uid
        with mock.patch.object(sio.os, "geteuid", return_value=real_uid + 1):
            try:
                sio.secure_workspace(ws)
            except SafetyError as e:
                out["foreign"] = str(e)
            else:
                raise AssertionError("a hard-linked state file owned by another user was accepted")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            assert sio.secure_workspace(ws) == ws.resolve()
        assert any(issubclass(w.category, sio.HardlinkAccepted) for w in caught), [str(w.message) for w in caught]
        moved = parent / "learner.real"
        os.replace(target, moved)
        os.symlink(moved, target)
        try:
            sio.secure_workspace(ws)
        except SafetyError as e:
            out["symlink"] = str(e)
        else:
            raise AssertionError("a symlinked state file was accepted")
        target.unlink()
        os.mkfifo(target, 0o600)
        try:
            sio.secure_workspace(ws)
        except SafetyError as e:
            out["fifo"] = str(e)
        else:
            raise AssertionError("a non-regular state file was accepted")
        return out
    finally:
        shutil.rmtree(parent)
