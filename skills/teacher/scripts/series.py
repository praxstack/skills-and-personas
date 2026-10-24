#!/usr/bin/env python3
"""A consented learning journal for a series of sessions, in plain files.

Create it only after the learner says yes. It lives in .teacher/ (or --dir):
journal.json for the teacher and JOURNAL.md for the learner, regenerated on
every write. Any host can read both.

  series.py init --learner Prax --goal "implement a transformer from scratch"
  series.py resume                      # starts the next session; prints open threads and due recalls
  series.py status                      # the same summary, without starting a session
  series.py thread add attention --title "What attention computes" --level L1
  series.py log attention --did "explorable: dot-product attention" --missed "why softmax" --tried "analogy: spotlight"
  series.py level attention L2
  series.py recall add attention "softmax turns scores into weights that sum to 1"
  series.py recall result attention 0 --right --unaided
  series.py satisfied attention --note "said: makes sense now"   # only when the learner says so
  series.py reopen attention | park attention
  series.py forget --yes                # delete the journal

Recall is counted in sessions: a point is due 1, 3 and 6 sessions after it's
added. It counts as demonstrated only after a right, unaided answer in a
later session than the one it was taught in; any other result brings it
back the next session and restarts the spacing.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

SPACING = [1, 3, 6]
LEVELS = ["L0", "L1", "L2", "L3", "L4"]
LEVEL_NAMES = {"L0": "intuition", "L1": "mechanism", "L2": "formal model", "L3": "edge cases and limits", "L4": "transfer"}
PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _private_dir(root: Path, *, create: bool) -> int:
    """Open a learner-owned journal directory without following its final link."""
    created = False
    if create:
        try:
            os.mkdir(root, PRIVATE_DIR_MODE)
            created = True
        except FileExistsError:
            pass
    try:
        named = os.lstat(root)
    except FileNotFoundError:
        raise SystemExit(f"no journal in {root}")
    if stat.S_ISLNK(named.st_mode) or not stat.S_ISDIR(named.st_mode):
        raise SystemExit(f"unsafe journal directory: {root} must be a real directory, not a link")
    if hasattr(os, "getuid") and named.st_uid != os.getuid():
        raise SystemExit(f"unsafe journal directory: {root} is owned by another user")
    current_mode = stat.S_IMODE(named.st_mode)
    if current_mode != PRIVATE_DIR_MODE and not (created or root.name == ".teacher"):
        raise SystemExit(
            f"unsafe journal directory: {root} has mode {current_mode:o}; "
            "use a private 0700 directory instead"
        )
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(root, flags)
    opened = os.fstat(fd)
    if (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino):
        os.close(fd)
        raise SystemExit(f"unsafe journal directory: {root} changed while it was opened")
    if stat.S_IMODE(opened.st_mode) != PRIVATE_DIR_MODE:
        os.fchmod(fd, PRIVATE_DIR_MODE)
    return fd


def _read_private(dir_fd: int, name: str) -> str | None:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(name, flags, dir_fd=dir_fd)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise SystemExit(f"unsafe journal file {name}: {exc.strerror}")
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise SystemExit(f"unsafe journal file {name}: expected one private regular file")
        if hasattr(os, "getuid") and info.st_uid != os.getuid():
            raise SystemExit(f"unsafe journal file {name}: owned by another user")
        os.fchmod(fd, PRIVATE_FILE_MODE)
        with os.fdopen(fd, "r", encoding="utf-8", closefd=False) as stream:
            return stream.read()
    finally:
        os.close(fd)


def _write_private(dir_fd: int, name: str, content: str) -> None:
    # Refuse an unsafe existing entry before replacing it. os.replace replaces
    # a link itself, but failing closed exposes workspace tampering to the user.
    _read_private(dir_fd, name)
    temp_name = f".{name}.{os.getpid()}.{secrets.token_hex(8)}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(temp_name, flags, PRIVATE_FILE_MODE, dir_fd=dir_fd)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", closefd=False) as stream:
            stream.write(content)
            stream.flush()
            os.fsync(fd)
        os.replace(temp_name, name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
        os.fsync(dir_fd)
    except BaseException:
        try:
            os.unlink(temp_name, dir_fd=dir_fd)
        except FileNotFoundError:
            pass
        raise
    finally:
        os.close(fd)


class Journal:
    def __init__(self, root: Path):
        self.root = root
        self.file = root / "journal.json"
        try:
            try:
                root_fd = _private_dir(root, create=False)
            except SystemExit:
                if root.exists() or root.is_symlink():
                    raise
                self.data = {}
                return
            try:
                raw = _read_private(root_fd, "journal.json")
            finally:
                os.close(root_fd)
            self.data: dict = json.loads(raw) if raw is not None else {}
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise SystemExit(f"{self.file} can't be read ({e}); fix it, or delete the journal with: series.py forget --yes")

    @property
    def exists(self) -> bool:
        return bool(self.data)

    def need(self) -> None:
        if not self.exists:
            raise SystemExit(f"no journal in {self.root}. Ask the learner first, then run: series.py init --learner NAME --goal GOAL")

    def thread(self, tid: str) -> dict:
        self.need()
        if tid not in self.data["threads"]:
            raise SystemExit(f"no thread '{tid}'. Open threads: {', '.join(self.data['threads']) or 'none'}")
        return self.data["threads"][tid]

    @property
    def session(self) -> int:
        return self.data["session"]

    def save(self) -> None:
        self.data["updated"] = now()
        root_fd = _private_dir(self.root, create=True)
        try:
            _write_private(root_fd, "journal.json", json.dumps(self.data, indent=2, ensure_ascii=False) + "\n")
            _write_private(root_fd, "JOURNAL.md", self.markdown())
        finally:
            os.close(root_fd)

    # ---- views ----
    @staticmethod
    def pending(p: dict) -> list[int]:
        """Due sessions still ahead of the point. Asking it settles every due
        session up to then, so a session that passed unasked doesn't keep it
        due forever: it stays due (overdue) only until it's next asked."""
        last = max(p["asked_in"], default=0)
        return [d for d in p["due"] if d > last]

    def due(self) -> list[tuple[str, int, dict]]:
        out = []
        for tid, t in self.data["threads"].items():
            for i, p in enumerate(t.get("recall", [])):
                if p["demonstrated"]:
                    continue
                nxt = next(iter(self.pending(p)), None)
                if nxt is not None and nxt <= self.session:
                    out.append((tid, i, p))
        return out

    def summary(self) -> str:
        d = self.data
        lines = [f"Session {d['session']} with {d['learner']}. Goal: {d['goal']}"]
        open_threads = [(k, t) for k, t in d["threads"].items() if t["status"] == "open"]
        if open_threads:
            lines.append("Open threads:")
            for k, t in open_threads:
                last = t["log"][-1] if t["log"] else None
                tail = f"; last: {last['did']}" + (f"; still unclear: {last['missed']}" if last and last.get("missed") else "") if last else ""
                tried = sorted({x for e in t["log"] for x in e.get("tried", [])})
                lines.append(f"  - {k}: {t['title']} [{t['level']} {LEVEL_NAMES[t['level']]}]{tail}")
                if tried:
                    lines.append(f"      explanations already tried: {', '.join(tried)}")
        else:
            lines.append("No open threads. Ask what they want to explore next.")
        due = self.due()
        if due:
            lines.append("Recall due this session (ask before reteaching, unaided first):")
            for tid, i, p in due:
                lines.append(f"  - {tid} #{i}: {p['point']}")
        done = [k for k, t in d["threads"].items() if t["status"] == "satisfied"]
        if done:
            lines.append(f"Satisfied (learner's call): {', '.join(done)}")
        parked = [k for k, t in d["threads"].items() if t["status"] == "parked"]
        if parked:
            lines.append(f"Parked: {', '.join(parked)}")
        return "\n".join(lines)

    def markdown(self) -> str:
        d = self.data
        out = [f"# Learning journal: {d['learner']}", "", f"Goal: {d['goal']}", "",
               f"Session {d['session']}. Kept with consent given {d['consent']['given']}. Delete it any time with `series.py forget --yes`.", ""]
        for k, t in d["threads"].items():
            out += [f"## {t['title']} (`{k}`)", "", f"Status: {t['status']}. Depth: {t['level']}, {LEVEL_NAMES[t['level']]}.", ""]
            for e in t["log"]:
                bits = [f"session {e['session']}: {e['did']}"]
                if e.get("missed"):
                    bits.append(f"still unclear: {e['missed']}")
                if e.get("tried"):
                    bits.append(f"tried: {', '.join(e['tried'])}")
                if e.get("note"):
                    bits.append(e["note"])
                out.append("- " + "; ".join(bits))
            if t.get("recall"):
                out += ["", "Recall:"]
                for p in t["recall"]:
                    state = "demonstrated" if p["demonstrated"] else (f"due in sessions {', '.join(str(x) for x in self.pending(p))}" if self.pending(p) else "no more reviews scheduled")
                    out.append(f"- {p['point']} ({state})")
            if t["status"] == "satisfied":
                out += ["", f"Satisfied in session {t['satisfied_session']}: {t.get('satisfied_note') or 'the learner said so'}."]
            out.append("")
        return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", type=Path, default=Path(".teacher"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init")
    p.add_argument("--learner", required=True)
    p.add_argument("--goal", required=True)
    sub.add_parser("resume")
    sub.add_parser("status")
    p = sub.add_parser("thread")
    p.add_argument("action", choices=["add"])
    p.add_argument("id")
    p.add_argument("--title", required=True)
    p.add_argument("--level", choices=LEVELS, default="L0")
    p = sub.add_parser("log")
    p.add_argument("id")
    p.add_argument("--did", required=True)
    p.add_argument("--missed", default="")
    p.add_argument("--tried", action="append", default=[])
    p.add_argument("--note", default="")
    p = sub.add_parser("level")
    p.add_argument("id")
    p.add_argument("level", choices=LEVELS)
    p = sub.add_parser("recall")
    p.add_argument("action", choices=["add", "result"])
    p.add_argument("id")
    p.add_argument("point", help="the point (add) or its index (result)")
    p.add_argument("--right", action="store_true")
    p.add_argument("--wrong", action="store_true")
    p.add_argument("--unaided", action="store_true")
    for name in ("satisfied", "reopen", "park"):
        p = sub.add_parser(name)
        p.add_argument("id")
        p.add_argument("--note", default="")
    p = sub.add_parser("forget")
    p.add_argument("--yes", action="store_true")
    p = sub.add_parser("export")
    a = ap.parse_args()

    if a.cmd == "forget":
        if not a.yes:
            raise SystemExit("this deletes the journal; run again with --yes once the learner has confirmed")
        root_fd = _private_dir(a.dir, create=False)
        try:
            journal = _read_private(root_fd, "journal.json")
            if journal is None:
                raise SystemExit(f"no journal in {a.dir}; nothing deleted")
            try:
                md = _read_private(root_fd, "JOURNAL.md")
            except SystemExit as exc:
                raise SystemExit(f"{exc}; nothing deleted") from None
            ours = bool(md and md.startswith("# Learning journal:"))
            if ours:
                os.unlink("JOURNAL.md", dir_fd=root_fd)
            # journal.json goes last, so an interrupted forget remains retryable.
            os.unlink("journal.json", dir_fd=root_fd)
            os.fsync(root_fd)
        finally:
            os.close(root_fd)
        if a.dir.name == ".teacher":  # only the default folder is ours; a --dir folder belongs to the caller
            try:
                a.dir.rmdir()
            except OSError:
                pass  # the folder holds other files; leave them alone
        print(f"deleted the journal in {a.dir}")
        return 0
    j = Journal(a.dir)
    if a.cmd == "init":
        if j.exists:
            raise SystemExit(f"a journal already exists in {a.dir}; use resume")
        j.data = {"version": 1, "learner": a.learner, "goal": a.goal, "consent": {"given": now()}, "session": 1,
                  "sessions": [{"n": 1, "started": now()}], "threads": {}}
        j.save()
        print(f"journal started in {a.dir} (session 1)")
        return 0
    j.need()
    if a.cmd == "resume":
        j.data["session"] += 1
        j.data["sessions"].append({"n": j.session, "started": now()})
        j.save()
        print(j.summary())
    elif a.cmd == "status":
        print(j.summary())
    elif a.cmd == "export":
        print(j.markdown())
    elif a.cmd == "thread":
        if a.id in j.data["threads"]:
            raise SystemExit(f"thread '{a.id}' already exists")
        j.data["threads"][a.id] = {"title": a.title, "level": a.level, "status": "open", "opened_session": j.session, "log": [], "recall": []}
        j.save()
        print(f"opened {a.id}")
    elif a.cmd == "log":
        t = j.thread(a.id)
        t["log"].append({"session": j.session, "when": now(), "did": a.did, "missed": a.missed, "tried": a.tried, "note": a.note})
        j.save()
        print(f"logged on {a.id}")
    elif a.cmd == "level":
        j.thread(a.id)["level"] = a.level
        j.save()
        print(f"{a.id} is at {a.level} ({LEVEL_NAMES[a.level]})")
    elif a.cmd == "recall":
        t = j.thread(a.id)
        if a.action == "add":
            t["recall"].append({"point": a.point, "taught_session": j.session, "due": [j.session + s for s in SPACING], "asked_in": [], "results": [], "demonstrated": False})
            j.save()
            print(f"recall added to {a.id}, due in sessions {', '.join(str(j.session + s) for s in SPACING)}")
        else:
            if a.right == a.wrong:
                raise SystemExit("give exactly one of --right or --wrong")
            try:
                n = int(a.point)
                if n < 0:  # -1 would quietly pick the last point
                    raise IndexError
                p = t["recall"][n]
            except (ValueError, IndexError):
                raise SystemExit(f"no recall point {a.point} on {a.id} (points are numbered from 0)")
            p["results"].append({"session": j.session, "right": a.right, "unaided": a.unaided})
            if j.session not in p["asked_in"]:
                p["asked_in"].append(j.session)
            if a.right and a.unaided and j.session > p["taught_session"]:
                p["demonstrated"] = True
            else:
                # A miss, or a right answer that needed help (or came in the
                # session it was taught), brings it back next session, then
                # restarts the spacing: it stays due until shown unaided.
                p["demonstrated"] = False
                p["due"] = sorted(set(p["asked_in"]) | {j.session + s for s in SPACING})
            j.save()
            print("demonstrated" if p["demonstrated"] else "recorded")
    elif a.cmd in ("satisfied", "reopen", "park"):
        t = j.thread(a.id)
        t["status"] = {"satisfied": "satisfied", "reopen": "open", "park": "parked"}[a.cmd]
        if a.cmd == "satisfied":
            t["satisfied_session"] = j.session
            t["satisfied_note"] = a.note
        j.save()
        print(f"{a.id}: {t['status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
