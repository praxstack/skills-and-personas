"""WP11 (AC-11.1 to AC-11.4, D23.1 to D23.3): learner state and Google Drive for desktop.

Google Drive for desktop backs up whole folders ("My Computer" roots). About 0.1 to 1.5 s after a file is created
it hard-links the file into <root>/.tmp.driveupload until the upload finishes (plan/EVIDENCE-HARDLINKS.md). These
tests never touch a real Drive folder: each one builds a fixture root with its own empty `.tmp.driveupload` under
$PTK_STATE/tmp and points detection at it with PRAX_TEACH_SYNC_ROOTS. Staged copies are made by the test itself.
"""
import ctypes
import errno
import json
import os
import shutil
import sys
from pathlib import Path

from ptk import host
from selftest_support import NotRun
from test_state import _core_python

SYNC_ENV = "PRAX_TEACH_SYNC_ROOTS"


def _fixture(prefix):
    """A fake Drive backup root: <tmp>/Drive Root with an empty .tmp.driveupload, and a study folder inside it."""
    base = host.make_tmp(prefix)
    os.chmod(base, 0o700)
    root = base / "Drive Root"
    (root / ".tmp.driveupload").mkdir(parents=True)
    (root / "study").mkdir()
    os.chmod(root / "study", 0o700)
    return base, root


def _cli(*args, roots=""):
    env = host.child_env({"PYTHONPATH": str(host.PKG), "PYTHONDONTWRITEBYTECODE": "1", SYNC_ENV: roots})
    return host.run([_core_python(), "-B", "-m", "ptk.state", *args], env=env, timeout=120)


def _init(ws, roots, *extra):
    return _cli("init", str(ws), "--learner-id", "kai", "--goal", "Trace a switch statement", *extra,
                "--timestamp", "2026-08-07T08:00:00Z", roots=roots)


def _evidence(ws, roots, observed="traced case 2 to the end unaided"):
    res = _cli("evidence", str(ws), "--session", "s1", "--concept", "switch-fallthrough", "--observed", observed,
               "--gap", "default placement", "--next-action", "trace a switch with default first",
               "--timestamp", "2026-08-07T09:00:00Z", roots=roots)
    assert res.code == 0, res.stderr
    return res


def test_drive_folder_refused_by_default():
    """AC-11.1: inside a folder Google Drive backs up, init refuses even with --consent and creates nothing (no
    parent folder either). With the explicit opt-in --allow-google-drive it creates the workspace and records the
    opt-in in the consent: the service, the backed-up root and the exact notice shown."""
    base, root = _fixture("drive-refuse-")
    try:
        ws = root / "study" / "new-folder" / "learner"
        plain = _init(ws, str(root), "--consent")
        assert plain.code == 3, (plain.code, plain.stderr)
        assert not ws.parent.exists(), "a refused init created a folder"
        assert "--allow-google-drive" in plain.stderr, plain.stderr
        # the opt-in alone is not consent
        optin_only = _init(ws, str(root), "--allow-google-drive")
        assert optin_only.code == 3 and not ws.parent.exists(), (optin_only.code, optin_only.stderr)
        ok = _init(ws, str(root), "--consent", "--allow-google-drive")
        assert ok.code == 0, ok.stderr
        out = json.loads(ok.stdout)
        learner = json.loads((ws / "state" / "learner.json").read_text())
        synced = learner["consent"]["synced_location"]
        assert synced["service"] == "Google Drive for desktop" and synced["root"] == str(root.resolve()), synced
        assert "Google Drive" in synced["acknowledged_notice"]
        assert out["synced_location"] == synced, out
        # show reads it back, and a folder Drive does not back up needs no opt-in
        shown = _cli("show", str(ws), roots=str(root))
        assert shown.code == 0 and json.loads(shown.stdout)["consent"]["synced_location"] == synced, shown.stderr
        free = base / "free"
        free.mkdir(mode=0o700)
        plain_ok = _init(free / "learner", str(root), "--consent")
        assert plain_ok.code == 0, plain_ok.stderr
        free_learner = json.loads((free / "learner" / "state" / "learner.json").read_text())
        assert "synced_location" not in free_learner["consent"]
        return {"refused": plain.stderr.strip()[:160]}
    finally:
        shutil.rmtree(base)


def test_consent_names_drive():
    """AC-11.2: the consent text names Google Drive when Drive backs up the folder: the prompt before consent, the
    refusal and the recorded notice. A hard-link warning in a Drive-backed workspace says "Google Drive", and no
    learner-state warning anywhere says "macOS backup"."""
    from ptk.state import sync
    base, root = _fixture("drive-names-")
    try:
        ws = root / "study" / "learner"
        prompt = _init(ws, str(root))
        assert prompt.code == 3 and "Google Drive" in prompt.stderr and str(root.resolve()) in prompt.stderr, \
            prompt.stderr
        assert ".tmp.driveupload" in prompt.stderr and "does not delete" in prompt.stderr, prompt.stderr
        no_drive = _init(base / "elsewhere" / "learner", str(root))
        assert no_drive.code == 3 and "Google Drive" not in no_drive.stderr, no_drive.stderr
        assert _init(ws, str(root), "--consent", "--allow-google-drive").code == 0
        os.link(ws / "state" / "sessions.jsonl", root / ".tmp.driveupload" / "1682115")
        shown = _cli("show", str(ws), roots=str(root))
        assert shown.code == 0, shown.stderr
        assert "Google Drive" in shown.stderr and "macOS" not in shown.stderr, shown.stderr
        # the notice is the one function the CLI and the consent record use
        notice = sync.consent_notice(sync.detect(ws, roots=[root]))
        assert notice in prompt.stderr.replace("\n", " ") or notice.split(".")[0] in prompt.stderr, prompt.stderr
        for p in [*(host.PKG / "ptk" / "state").glob("*.py"), host.PKG / "README.md",
                  host.PKG / "references" / "OPERATIONS.md"]:
            assert "macOS backup" not in p.read_text(), f"{p.name} still blames macOS backup"
        return {"prompt": prompt.stderr.strip()[:200], "warning": shown.stderr.strip()[:200]}
    finally:
        shutil.rmtree(base)


def test_detection_walks_ancestors():
    """Detection without injection: an ancestor holding a `.tmp.driveupload` folder is a Drive backup root. Only the
    folder's existence is checked (lstat); nothing inside it is listed or read. stop_at keeps the walk inside the
    fixture."""
    from ptk.state import sync
    base, root = _fixture("drive-walk-")
    try:
        deep = root / "study" / "a" / "b" / "learner"
        found = sync.detect(deep, roots=None, stop_at=base)
        assert found is not None and found.root == root.resolve() and found.service == "Google Drive for desktop"
        assert sync.detect(base / "outside" / "learner", roots=None, stop_at=base) is None
        (root / ".tmp.driveupload").rmdir()
        (root / ".tmp.driveupload").write_text("not a folder")
        assert sync.detect(deep, roots=None, stop_at=base) is None, "a plain file named like the marker counted"
        assert sync.detect(deep, roots=[]) is None, "an empty injected root list must mean no Drive"
        return {"root": str(found.root)}
    finally:
        shutil.rmtree(base)


def test_delete_reports_surviving_copies():
    """AC-11.3: in a Drive-backed probe folder, a full delete reports each copy Drive still holds in the root's
    .tmp.driveupload (one staged by hard link, so the same inode, one with the same bytes on another inode) and does
    not report all_state_deleted. It never deletes or changes those copies. A scoped delete reports the staged copy
    of the old log too. With nothing staged, the full delete reports all_state_deleted (unless a link outside the
    workspace it cannot locate exists, which it then reports instead)."""
    base, root = _fixture("drive-delete-")
    staging = root / ".tmp.driveupload"
    try:
        roots = str(root)
        ws = root / "study" / "learner"
        assert _init(ws, roots, "--consent", "--allow-google-drive").code == 0
        _evidence(ws, roots, "B traced case 2 alone")
        os.link(ws / "state" / "learner.json", staging / "1682115")
        shutil.copyfile(ws / "MISSION.md", staging / "1682105")
        preview = _cli("delete", str(ws), "--all-state", "--dry-run", roots=roots)
        assert preview.code == 0, preview.stderr
        pv = json.loads(preview.stdout)
        assert {c["file"] for c in pv["surviving_copies"]} == {"state/learner.json", "MISSION.md"}, pv
        done = _cli("delete", str(ws), "--all-state", "--confirm", roots=roots)
        assert done.code == 0, done.stderr
        out = json.loads(done.stdout)
        assert out["status"] != "all_state_deleted" and out["status"] == "deleted_with_surviving_copies", out
        got = {(c["file"], c["match"], Path(c["copy"]).name) for c in out["surviving_copies"]}
        assert ("state/learner.json", "same inode", "1682115") in got, got
        assert ("MISSION.md", "same content", "1682105") in got, got
        assert "Google Drive" in out["warning"] and "Google Drive" in done.stderr, (out["warning"], done.stderr)
        assert not ws.exists()
        assert (staging / "1682115").exists() and (staging / "1682105").exists(), "ptk touched Drive's copies"
        assert b"learner_id" in (staging / "1682115").read_bytes() and b"kai" in (staging / "1682115").read_bytes()

        # scoped delete: the staged copy of the old log still holds the deleted event
        ws2 = root / "study" / "learner2"
        assert _init(ws2, roots, "--consent", "--allow-google-drive").code == 0
        ev = json.loads(_evidence(ws2, roots, "a secret attempt").stdout)
        os.link(ws2 / "state" / "sessions.jsonl", staging / "1682200")
        scoped = _cli("delete", str(ws2), "--event-id", ev["event_id"], "--confirm", roots=roots)
        assert scoped.code == 0, scoped.stderr
        so = json.loads(scoped.stdout)
        assert so["status"] == "deleted", so
        assert ("state/sessions.jsonl", "same inode") in {(c["file"], c["match"]) for c in so["surviving_copies"]}, so
        assert b"a secret attempt" in (staging / "1682200").read_bytes()

        # control: a second Drive root with nothing staged (the first one holds a copy with the same MISSION.md bytes)
        root3 = base / "Drive Root 2"
        (root3 / ".tmp.driveupload").mkdir(parents=True)
        os.chmod(root3, 0o700)
        ws3 = root3 / "learner3"
        assert _init(ws3, str(root3), "--consent", "--allow-google-drive").code == 0
        clean = json.loads(_cli("delete", str(ws3), "--all-state", "--confirm", roots=str(root3)).stdout)
        assert not clean.get("surviving_copies"), clean
        assert clean["status"] == ("deleted_with_surviving_copies" if clean.get("unlocated_links") else
                                   "all_state_deleted"), clean
        return {"survivors": sorted(got), "control": clean["status"]}
    finally:
        shutil.rmtree(base)


# ---------------------------------------------------------------- extended attributes, read without side effects

def _libc():
    lib = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
    lib.listxattr.restype = ctypes.c_ssize_t
    lib.listxattr.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_size_t, ctypes.c_int]
    lib.getxattr.restype = ctypes.c_ssize_t
    lib.getxattr.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32,
                             ctypes.c_int]
    lib.removexattr.restype = ctypes.c_int
    lib.removexattr.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    return lib


def _xattrs(path):
    """{name: value} for every extended attribute of path (no symlink following)."""
    if hasattr(os, "listxattr"):
        return {n: os.getxattr(path, n, follow_symlinks=False) for n in os.listxattr(path, follow_symlinks=False)}
    if sys.platform != "darwin":
        raise NotRun("no extended-attribute interface on this platform")
    lib, p = _libc(), os.fsencode(path)
    size = lib.listxattr(p, None, 0, 1)
    if size <= 0:
        return {}
    buf = ctypes.create_string_buffer(size)
    lib.listxattr(p, buf, size, 1)
    out = {}
    for name in buf.raw[:size].split(b"\0"):
        if name:
            vs = lib.getxattr(p, name, None, 0, 0, 1)
            vb = ctypes.create_string_buffer(max(vs, 1))
            lib.getxattr(p, name, vb, max(vs, 1), 0, 1)
            out[name.decode()] = vb.raw[:max(vs, 0)]
    return out


def _strip_binding(path):
    name = "user.praxteach.learner"
    if hasattr(os, "removexattr"):
        try:
            os.removexattr(path, name, follow_symlinks=False)
        except OSError as e:
            if e.errno not in (errno.ENODATA, getattr(errno, "ENOATTR", errno.ENODATA)):
                raise
        return
    if _libc().removexattr(os.fsencode(path), name.encode(), 1) != 0 and ctypes.get_errno() != 93:
        raise OSError(ctypes.get_errno(), os.strerror(ctypes.get_errno()))


def _snapshot(parent):
    """Every entry under parent: kind, bytes digest, inode, mode, mtime and every extended attribute. The link count
    is left out: Google Drive may add a staging link to these files at any moment, and that is not ptk writing."""
    import hashlib
    snap = {}
    for p in sorted([parent, *parent.rglob("*")]):
        st = p.lstat()
        snap[str(p.relative_to(parent))] = (
            "dir" if p.is_dir() else "file", hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None,
            st.st_ino, st.st_mode, st.st_mtime_ns, tuple(sorted(_xattrs(p).items())))
    return snap


def test_read_only_writes_nothing_without_consent():
    """AC-11.4 (D23.3, the D22.3 regression): after persistence consent is withdrawn, show, due, export (the
    workspace side), continuity-show, delete --dry-run and rebind (without --confirm) change nothing in the
    workspace or beside it: no bytes, no new files, no extended attributes. The binding on the state folder and the
    stamps on legacy files are removed first, which is what made the old code write them on read."""
    from ptk.state import io as sio
    base = host.make_tmp("ro-consent-")
    try:
        os.chmod(base, 0o700)
        parent = base / "p"
        parent.mkdir(mode=0o700)
        ws = parent / "learner"
        if not sio.bindings_supported(parent):
            raise NotRun("this filesystem has no extended attributes")
        assert _init(ws, "", "--consent").code == 0
        _evidence(ws, "")
        off = _cli("disable-persistence", str(ws), "--reason", "test", "--timestamp", "2026-08-07T10:00:00Z")
        assert off.code == 0, off.stderr
        for p in [ws / "state", *(ws / "state").iterdir(), ws / "MISSION.md", ws / "RESOURCES.md"]:
            _strip_binding(p)
        assert sio.read_binding(ws / "state") is None and sio.read_binding(ws / "state" / "learner.json") is None
        before = _snapshot(parent)
        exports = base / "exports"
        exports.mkdir(mode=0o700)
        runs = {
            "show": _cli("show", str(ws)),
            "due": _cli("due", str(ws), "--at", "2026-09-01T00:00:00Z"),
            "export": _cli("export", str(ws), str(exports / "out.zip"), "--timestamp", "2026-08-07T11:00:00Z"),
            "continuity-show": _cli("continuity-show", str(ws)),
            "delete-dry-run": _cli("delete", str(ws), "--all-state", "--dry-run"),
            "delete-unconfirmed": _cli("delete", str(ws), "--all-state"),
            "rebind": _cli("rebind", str(ws)),
        }
        codes = {k: v.code for k, v in runs.items()}
        # show and export stay available after withdrawal (v2's controls); due and rebind refuse with exit 3. When an
        # outside tool (Google Drive) has linked an unbound file meanwhile, the v2 rule refuses it with exit 5.
        linked = any(p.is_file() and p.stat().st_nlink > 1 for p in ws.rglob("*"))
        want = {"show": {0}, "export": {0}, "continuity-show": {0}, "delete-dry-run": {0}, "due": {3},
                "delete-unconfirmed": {4}, "rebind": {3}}
        bad = {k: (v.code, v.stderr[-300:]) for k, v in runs.items()
               if v.code not in want[k] | ({5} if linked else set())}
        assert not bad, bad
        after = _snapshot(parent)
        changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        assert not changed, f"read-only commands wrote after consent was withdrawn: {changed}"
        # with consent active, reading may stamp legacy files again (D22.3, approved in D23.2)
        return {"codes": codes}
    finally:
        shutil.rmtree(base)
