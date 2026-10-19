"""Explicit migration for learner state written before learner bindings (D22.3, plan/PROTECTED-MAP.md).

A file written by older code carries no learner binding. With one link it is adopted on first read. With an
extra link it is refused, because the engine cannot tell a backup link from a link to another learner's file.
`rebind` lists those files; with --confirm it copies each one onto a fresh inode that carries this workspace's
binding. The old inode, and every other name it has, is left untouched. A file that carries another learner
workspace's binding and still has another link is never rebound: the learner must remove that link first.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Any

from .errors import ConfirmationRequired, ConsentRequired, SafetyError
from .io import (
    LOCK_NAME,
    _open_flags,
    atomic_write,
    binding_at,
    ensure_binding,
    metadata_writes_allowed,
    secure_workspace,
    workspace_generation_lock,
    workspace_lock,
)


def _classify(entry: os.stat_result, carried: str | None, binding: str) -> str | None:
    """'rebind', 'refuse', or None (already fine) for one regular file."""

    geteuid = getattr(os, "geteuid", None)
    if geteuid is None or entry.st_uid != geteuid():
        return "refuse"
    if carried == binding:
        return None
    if carried is None:
        return "rebind" if entry.st_nlink != 1 else None  # one link: adopted on read
    return "rebind" if entry.st_nlink == 1 else "refuse"


def _scan(directory_descriptor: int, prefix: str, binding: str) -> tuple[list[str], list[str]]:
    rebind: list[str] = []
    refuse: list[str] = []
    for name in sorted(os.listdir(directory_descriptor)):
        if name.startswith("."):
            continue
        entry = os.stat(name, dir_fd=directory_descriptor, follow_symlinks=False)
        if not stat.S_ISREG(entry.st_mode):
            continue
        verdict = _classify(entry, binding_at(directory_descriptor, name, entry), binding)
        if verdict == "rebind":
            rebind.append(prefix + name)
        elif verdict == "refuse":
            refuse.append(prefix + name)
    return rebind, refuse


def _read_exact(directory_descriptor: int, name: str) -> bytes:
    entry = os.stat(name, dir_fd=directory_descriptor, follow_symlinks=False)
    descriptor = os.open(name, _open_flags(os.O_RDONLY), dir_fd=directory_descriptor)
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (entry.st_dev, entry.st_ino):
            raise SafetyError(f"{name} changed while it was being rebound")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            return handle.read()
    finally:
        os.close(descriptor)


def _lock_needs_rebind(workspace: Path, binding: str) -> bool:
    lock = workspace / LOCK_NAME
    try:
        entry = lock.lstat()
    except FileNotFoundError:
        return False
    if not stat.S_ISREG(entry.st_mode) or entry.st_nlink == 1:
        return False
    parent = os.open(workspace, _open_flags(os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)))
    try:
        return _classify(entry, binding_at(parent, LOCK_NAME, entry), binding) == "rebind"
    finally:
        os.close(parent)


def rebind_workspace(path: str, *, confirm: bool) -> dict[str, Any]:
    workspace = secure_workspace(path, check_bindings=False)
    binding = ensure_binding(workspace / "state")
    if binding is None and not metadata_writes_allowed():
        raise ConsentRequired(
            "this workspace has no learner binding and persistence consent is not active, so rebind cannot "
            "create one; nothing was written"
        )
    if binding is None:
        raise SafetyError(
            "this filesystem cannot store learner bindings; remove the extra hard links instead"
        )
    with workspace_generation_lock(workspace):
        # The lock is never written, so an unbound linked lock is simply replaced: holding the parent
        # generation lock means no other prax-teach process holds the workspace lock.
        lock_rebind = _lock_needs_rebind(workspace, binding)
        if lock_rebind and confirm:
            os.unlink(workspace / LOCK_NAME)
    if lock_rebind and not confirm:
        raise ConfirmationRequired(
            f"rebind would replace: {LOCK_NAME}. Remove other links to it or run with --confirm"
        )
    with workspace_lock(workspace):
        root = os.open(workspace, _open_flags(os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)))
        try:
            root_rebind, root_refuse = _scan(root, "", binding)
            state_fd = os.open("state", _open_flags(os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)), dir_fd=root)
            try:
                state_rebind, state_refuse = _scan(state_fd, "state/", binding)
                targets = root_rebind + state_rebind
                refused = root_refuse + state_refuse
                if refused:
                    raise SafetyError(
                        "not rebinding files that carry another learner workspace's binding and still have "
                        "another link, or that another user owns: " + ", ".join(refused)
                    )
                if targets and not confirm:
                    raise ConfirmationRequired(
                        "these files carry no learner binding and have extra hard links; check they are this "
                        "learner's own, then run with --confirm to copy each onto a fresh inode: "
                        + ", ".join(targets)
                    )
                for relative in targets:
                    directory = state_fd if relative.startswith("state/") else root
                    name = relative.split("/")[-1]
                    atomic_write(workspace / relative, _read_exact(directory, name))
            finally:
                os.close(state_fd)
        finally:
            os.close(root)
    rebound = ([LOCK_NAME] if lock_rebind else []) + targets
    return {
        "rebound": rebound,
        "status": "rebound" if rebound else "nothing to rebind",
        "workspace": str(workspace),
    }
