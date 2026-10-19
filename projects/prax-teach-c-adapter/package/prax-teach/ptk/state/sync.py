"""Learner state and Google Drive for desktop (WP11, D23.1 to D23.4; evidence: plan/EVIDENCE-HARDLINKS.md).

Google Drive for desktop can back up whole folders. A local probe observed staging hard links shortly after
file creation; this does not establish when or whether an upload completes. Learner state in a backed-up
folder may be uploaded, and a local staged copy can outlive ptk's workspace deletion.

Detection: a folder is Drive-backed when it or an ancestor holds a ``.tmp.driveupload`` (or ``.tmp.drivedownload``)
directory. Only that directory's own entry is checked (lstat); nothing inside it is listed or read. Drive's
configuration database is not read: opening it is not free of side effects for Drive.

Injection: ``PRAX_TEACH_SYNC_ROOTS`` replaces detection. It is a list of folders joined with ``os.pathsep`` that
count as Drive roots; an empty value means none. The test suite sets it, so tests use fixture folders and never a
real Drive folder.

Surviving copies (AC-11.3): ``find_copies`` looks in the staging folders of the Drive root that holds a workspace
for the same inode or the same bytes as a file ptk deletes or replaces. It reads those folders only to report; it
never deletes or changes anything in them (D23.4). A file that still has another link it cannot locate is reported
too, by count.
"""

from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SYNC_ROOTS_ENV = "PRAX_TEACH_SYNC_ROOTS"
DRIVE_SERVICE = "Google Drive for desktop"
DRIVE_STAGING = (".tmp.driveupload", ".tmp.drivedownload")
FROM_ENV = object()  # detect(): read PRAX_TEACH_SYNC_ROOTS, and walk the filesystem only when it is unset
_READ_LIMIT = 64 * 1024 * 1024  # a staged file larger than this is never hashed (no learner file is that big)


@dataclass(frozen=True)
class SyncedLocation:
    """The Google Drive backup root that holds a path."""

    root: Path
    service: str = DRIVE_SERVICE

    def staging(self) -> list[Path]:
        return [self.root / name for name in DRIVE_STAGING]


def configured_roots() -> list[Path] | None:
    """The injected Drive roots, or None when detection should look at the filesystem."""

    raw = os.environ.get(SYNC_ROOTS_ENV)
    if raw is None:
        return None
    return [Path(os.path.realpath(part)) for part in raw.split(os.pathsep) if part.strip()]


def _is_directory_entry(path: Path) -> bool:
    try:
        return stat.S_ISDIR(os.lstat(path).st_mode)
    except OSError:
        return False


def detect(
    path: str | os.PathLike[str],
    *,
    roots: Any = FROM_ENV,
    stop_at: str | os.PathLike[str] | None = None,
) -> SyncedLocation | None:
    """The Google Drive backup root holding ``path`` (which need not exist yet), or None.

    ``roots`` is a list of Drive roots that replaces detection; the default reads PRAX_TEACH_SYNC_ROOTS, and None
    (or the variable unset) walks the filesystem: ``path`` and each ancestor up to ``stop_at`` (default: the
    filesystem root) is checked for a Drive staging directory.
    """

    target = Path(os.path.realpath(path))
    if roots is FROM_ENV:
        chosen = configured_roots()
    else:
        chosen = None if roots is None else [Path(os.path.realpath(r)) for r in roots]
    if chosen is not None:
        for root in chosen:
            if target == root or root in target.parents:
                return SyncedLocation(root)
        return None
    ceiling = Path(os.path.realpath(stop_at)) if stop_at is not None else None
    for folder in (target, *target.parents):
        if ceiling is not None and folder != ceiling and ceiling not in folder.parents:
            break
        if any(_is_directory_entry(folder / name) for name in DRIVE_STAGING):
            return SyncedLocation(folder)
    return None


def consent_notice(location: SyncedLocation) -> str:
    """What a learner is told before consenting to learner state in a Drive-backed folder (AC-11.2)."""

    staging = location.root / DRIVE_STAGING[0]
    return (
        f"This folder is inside {location.root}, which Google Drive for desktop backs up to the Google account "
        "linked to Drive. Your goal, practice evidence and reviews may be uploaded; upload timing is not verified. "
        "Deleting them here does not delete Google's copy, its version history or its trash, and a local copy can "
        f"remain in {staging}. Export shows only this workspace, not the copies Drive "
        "keeps. To keep learner state off Google Drive, choose a folder Drive does not back up. To store it here "
        "anyway, run init again with --consent --allow-google-drive."
    )


def link_cause(location: SyncedLocation | None) -> str:
    """Why a learner's own state file has an extra hard link, for the HardlinkAccepted warning."""

    if location is not None:
        return f"Google Drive for desktop backs up {location.root} and links new files while it uploads them"
    return "a sync or backup tool, such as Google Drive for desktop, can add them"


def file_target(relative: str, entry: os.stat_result, sha256: str) -> dict[str, Any]:
    return {"dev": entry.st_dev, "ino": entry.st_ino, "nlink": entry.st_nlink, "path": relative,
            "sha256": sha256, "size": entry.st_size}


def _digest(path: Path, size: int) -> str | None:
    if size > _READ_LIMIT:
        return None
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0))
    except OSError:
        return None
    try:
        digest = hashlib.sha256()
        while True:
            chunk = os.read(descriptor, 1 << 20)
            if not chunk:
                return digest.hexdigest()
            digest.update(chunk)
    except OSError:
        return None
    finally:
        os.close(descriptor)


def find_copies(location: SyncedLocation | None, targets: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Copies of ``targets`` (file_target records taken before the files were removed or replaced) that survive
    outside the workspace: {"surviving_copies": [{file, copy, match}], "unlocated_links": [{file, links}]}.

    A copy in the Drive root's staging folders matches by inode ("same inode") or, for a non-empty file, by size
    and SHA-256 ("same content"). A target that had more links than the ones found is listed in unlocated_links.
    """

    located: list[dict[str, Any]] = []
    by_inode = {(t["dev"], t["ino"]): t for t in targets}
    by_size: dict[int, list[dict[str, Any]]] = {}
    for t in targets:
        if t["size"] > 0:
            by_size.setdefault(t["size"], []).append(t)
    for staging in location.staging() if location is not None else []:
        if not _is_directory_entry(staging):
            continue
        for folder, directories, names in os.walk(staging, followlinks=False):
            directories.sort()
            for name in sorted(names):
                path = Path(folder) / name
                try:
                    entry = os.lstat(path)
                except OSError:
                    continue
                if not stat.S_ISREG(entry.st_mode):
                    continue
                same = by_inode.get((entry.st_dev, entry.st_ino))
                if same is not None:
                    located.append({"copy": str(path), "file": same["path"], "match": "same inode"})
                    continue
                candidates = by_size.get(entry.st_size)
                if not candidates:
                    continue
                digest = _digest(path, entry.st_size)
                for t in candidates:
                    if digest is not None and digest == t["sha256"]:
                        located.append({"copy": str(path), "file": t["path"], "match": "same content"})
                        break
    unlocated = []
    for t in targets:
        found = sum(1 for c in located if c["match"] == "same inode" and c["file"] == t["path"])
        extra = t["nlink"] - 1 - found
        if extra > 0:
            unlocated.append({"file": t["path"], "links": extra})
    located.sort(key=lambda c: (c["file"], c["copy"]))
    return {"surviving_copies": located, "unlocated_links": unlocated}


def surviving_copies_warning(location: SyncedLocation | None, found: dict[str, list[dict[str, Any]]]) -> str:
    copies, unlocated = found["surviving_copies"], found["unlocated_links"]
    parts = []
    if copies:
        where = f"Google Drive's upload folder under {location.root}" if location is not None else "another folder"
        parts.append(f"{len(copies)} copy(ies) of deleted learner files remain in {where}; ptk does not delete them")
    if unlocated:
        parts.append(f"{len(unlocated)} file(s) still had another hard link outside the workspace that ptk cannot "
                     "locate, so their data survives")
    tail = (" Google Drive may also keep an uploaded copy, its version history and its trash; delete them in Drive."
            if location is not None else "")
    return "; ".join(parts) + "." + tail if parts else ""
