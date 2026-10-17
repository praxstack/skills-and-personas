"""Fail-closed filesystem primitives for learner state.

The module deliberately uses only the Python standard library.  Mutable files
are protected by a process lock, opened without following symlinks where the
platform exposes ``O_NOFOLLOW``, and replaced atomically after an fsync.
"""

from __future__ import annotations

import contextlib
import errno
import hashlib
import json
import os
import stat
import uuid
from collections.abc import Iterator
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Any, BinaryIO

from .errors import SafetyError, StateNotFound, ValidationError

PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600
LOCK_NAME = ".prax-teach.lock"
REQUIRED_STATE_FILES = (
    "concepts.json",
    "learner.json",
    "misconceptions.json",
    "reviews.jsonl",
    "sessions.jsonl",
    "sources.json",
)


def canonical_json_bytes(value: Any) -> bytes:
    """Return the canonical, human-inspectable JSON representation."""

    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_json_line(value: Any) -> bytes:
    """Return one deterministic JSONL record."""

    return (
        json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _contains_parent_reference(path: Path) -> bool:
    return any(part == ".." for part in PurePath(path).parts)


def _absolute_unresolved_path(path: str | os.PathLike[str]) -> Path:
    """Return an absolute path while retaining the caller's unresolved leaf."""

    raw = Path(path).expanduser()
    if _contains_parent_reference(raw):
        raise SafetyError("path traversal ('..') is not allowed")
    absolute = raw if raw.is_absolute() else Path.cwd() / raw
    if not absolute.name:
        raise SafetyError("path must name a leaf below an existing filesystem root")
    return absolute


def _normalize_trusted_root_alias(absolute: Path) -> Path:
    """Expand an OS-owned root alias such as macOS ``/var`` exactly once.

    User-controlled symlinks remain forbidden. A direct child of the filesystem
    root is trusted only when both the link and its non-writable parent are owned
    by root. This preserves normal macOS absolute paths without accepting an
    arbitrary alias deeper in the requested path.
    """

    if os.name != "posix" or absolute.anchor != os.sep or len(absolute.parts) < 2:
        return absolute
    first = Path(absolute.anchor) / absolute.parts[1]
    try:
        first_stat = first.lstat()
    except FileNotFoundError:
        return absolute
    if not stat.S_ISLNK(first_stat.st_mode):
        return absolute
    root_stat = Path(absolute.anchor).stat()
    if (
        first_stat.st_uid != 0
        or root_stat.st_uid != 0
        or stat.S_IMODE(root_stat.st_mode) & 0o022
    ):
        raise SafetyError("path contains an untrusted root-level symlink")
    try:
        resolved = first.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise SafetyError("trusted root alias cannot be resolved safely") from exc
    if not resolved.is_dir():
        raise SafetyError("trusted root alias does not resolve to a directory")
    return resolved.joinpath(*absolute.parts[2:])


def _directory_open_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )


def _supports_secure_parent_walk() -> bool:
    return (
        os.name == "posix"
        and os.open in os.supports_dir_fd
        and os.mkdir in os.supports_dir_fd
        and hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
    )


def _supports_secure_directory_fds() -> bool:
    """Return whether POSIX can complete an anchored atomic replacement."""

    return (
        _supports_secure_parent_walk()
        and os.stat in os.supports_dir_fd
        and os.rename in os.supports_dir_fd
        and os.unlink in os.supports_dir_fd
    )


def _raise_unsafe_component(path: Path, exc: OSError) -> None:
    if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
        raise SafetyError(
            f"path ancestor is a symlink or not a directory: {path}"
        ) from exc
    raise exc


def _prepare_parent_posix(parent: Path, *, create_missing: bool) -> Path:
    """Walk ``parent`` by directory descriptor, optionally creating components."""

    flags = _directory_open_flags()
    current_path = Path(parent.anchor)
    current_fd = os.open(current_path, flags)
    parts = parent.parts[1:]
    try:
        for index, part in enumerate(parts):
            component = current_path / part
            try:
                child_fd = os.open(part, flags, dir_fd=current_fd)
            except FileNotFoundError:
                if not create_missing:
                    return current_path.joinpath(*parts[index:])
                try:
                    os.mkdir(part, PRIVATE_DIR_MODE, dir_fd=current_fd)
                except FileExistsError as race:
                    raise SafetyError(
                        f"path ancestor changed while it was being created: {component}"
                    ) from race
                except OSError as mkdir_error:
                    _raise_unsafe_component(component, mkdir_error)
                    raise AssertionError("unreachable") from mkdir_error
                try:
                    child_fd = os.open(part, flags, dir_fd=current_fd)
                except FileNotFoundError as race:
                    raise SafetyError(
                        f"new path ancestor disappeared during creation: {component}"
                    ) from race
                except OSError as open_error:
                    _raise_unsafe_component(component, open_error)
                    raise AssertionError("unreachable") from open_error
                os.fsync(current_fd)
            except OSError as open_error:
                _raise_unsafe_component(component, open_error)
                raise AssertionError("unreachable") from open_error

            try:
                opened_stat = os.fstat(child_fd)
                entry_stat = os.stat(part, dir_fd=current_fd, follow_symlinks=False)
                if not stat.S_ISDIR(opened_stat.st_mode) or stat.S_ISLNK(
                    entry_stat.st_mode
                ):
                    raise SafetyError(
                        f"path ancestor is a symlink or not a directory: {component}"
                    )
                if (opened_stat.st_dev, opened_stat.st_ino) != (
                    entry_stat.st_dev,
                    entry_stat.st_ino,
                ):
                    raise SafetyError(
                        f"path ancestor changed during validation: {component}"
                    )
            except Exception:
                os.close(child_fd)
                raise
            os.close(current_fd)
            current_fd = child_fd
            current_path = component
        return current_path
    finally:
        os.close(current_fd)


def _prepare_parent_fallback(parent: Path, *, create_missing: bool) -> Path:
    """Fail-closed component walk for platforms without POSIX directory FDs."""

    current = Path(parent.anchor)
    parts = parent.parts[1:]
    for index, part in enumerate(parts):
        component = current / part
        try:
            component_stat = component.lstat()
        except FileNotFoundError:
            if not create_missing:
                return current.joinpath(*parts[index:])
            try:
                component.mkdir(mode=PRIVATE_DIR_MODE)
            except FileExistsError as exc:
                raise SafetyError(
                    f"path ancestor changed while it was being created: {component}"
                ) from exc
            component_stat = component.lstat()
            if stat.S_ISLNK(component_stat.st_mode):
                raise SafetyError(f"new path ancestor became a symlink: {component}")
        if stat.S_ISLNK(component_stat.st_mode) or not stat.S_ISDIR(
            component_stat.st_mode
        ):
            raise SafetyError(
                f"path ancestor is a symlink or not a directory: {component}"
            )
        current = component
    return current


def _open_verified_directory_descriptor(
    directory: Path, *, create_missing: bool = False
) -> int:
    """Open or create ``directory`` without releasing its verified generation."""

    if not _supports_secure_parent_walk():
        raise SafetyError("secure directory-descriptor traversal is unavailable")
    flags = _directory_open_flags()
    current_path = Path(directory.anchor)
    current_fd = os.open(current_path, flags)
    try:
        for part in directory.parts[1:]:
            component = current_path / part
            try:
                child_fd = os.open(part, flags, dir_fd=current_fd)
            except FileNotFoundError as exc:
                if not create_missing:
                    raise SafetyError(
                        f"path ancestor disappeared during validation: {component}"
                    ) from exc
                try:
                    os.mkdir(part, PRIVATE_DIR_MODE, dir_fd=current_fd)
                except FileExistsError as race:
                    raise SafetyError(
                        f"path ancestor changed while it was being created: {component}"
                    ) from race
                except OSError as mkdir_error:
                    _raise_unsafe_component(component, mkdir_error)
                    raise AssertionError("unreachable") from mkdir_error
                try:
                    child_fd = os.open(part, flags, dir_fd=current_fd)
                except FileNotFoundError as race:
                    raise SafetyError(
                        f"new path ancestor disappeared during creation: {component}"
                    ) from race
                except OSError as open_error:
                    _raise_unsafe_component(component, open_error)
                    raise AssertionError("unreachable") from open_error
                os.fsync(current_fd)
            except OSError as exc:
                _raise_unsafe_component(component, exc)
                raise AssertionError("unreachable") from exc
            try:
                opened_stat = os.fstat(child_fd)
                entry_stat = os.stat(part, dir_fd=current_fd, follow_symlinks=False)
                if not stat.S_ISDIR(opened_stat.st_mode) or stat.S_ISLNK(
                    entry_stat.st_mode
                ):
                    raise SafetyError(
                        f"path ancestor is a symlink or not a directory: {component}"
                    )
                if (opened_stat.st_dev, opened_stat.st_ino) != (
                    entry_stat.st_dev,
                    entry_stat.st_ino,
                ):
                    raise SafetyError(
                        f"path ancestor changed during validation: {component}"
                    )
            except Exception:
                os.close(child_fd)
                raise
            os.close(current_fd)
            current_fd = child_fd
            current_path = component
        return current_fd
    except Exception:
        os.close(current_fd)
        raise


def prepare_private_parent(
    path: str | os.PathLike[str], *, create_missing: bool = True
) -> Path:
    """Return ``path`` with a validated parent and an unresolved leaf.

    Missing ancestors are created one component at a time with private modes.
    Existing ancestors are never chmodded, and symlink ancestors are rejected.
    Set ``create_missing`` to false for a read-only preflight.
    """

    absolute = _normalize_trusted_root_alias(_absolute_unresolved_path(path))
    parent = absolute.parent
    if _supports_secure_parent_walk():
        prepared_parent = _prepare_parent_posix(parent, create_missing=create_missing)
    else:
        prepared_parent = _prepare_parent_fallback(
            parent, create_missing=create_missing
        )
    return prepared_parent / absolute.name


@dataclass(frozen=True)
class AnchoredFileTarget:
    """A file name bound to the verified directory generation that contains it."""

    path: Path
    parent_descriptor: int | None
    parent_device: int
    parent_inode: int


@dataclass(frozen=True)
class WorkspaceIoAnchor:
    """Held workspace generations used by state I/O during one lock scope."""

    workspace: Path
    workspace_descriptor: int
    workspace_device: int
    workspace_inode: int
    state_descriptor: int
    state_device: int
    state_inode: int


_ACTIVE_WORKSPACE_IO: ContextVar[WorkspaceIoAnchor | None] = ContextVar(
    "prax_teach_active_workspace_io",
    default=None,
)


def _active_target_for_path(path: str | os.PathLike[str]) -> AnchoredFileTarget | None:
    """Bind a direct workspace/state child to the lock-held directory generation."""

    anchor = _ACTIVE_WORKSPACE_IO.get()
    if anchor is None:
        return None
    absolute = _normalize_trusted_root_alias(_absolute_unresolved_path(path))
    try:
        relative = absolute.relative_to(anchor.workspace)
    except ValueError:
        return None
    if len(relative.parts) == 1:
        return AnchoredFileTarget(
            path=absolute,
            parent_descriptor=anchor.workspace_descriptor,
            parent_device=anchor.workspace_device,
            parent_inode=anchor.workspace_inode,
        )
    if len(relative.parts) == 2 and relative.parts[0] == "state":
        return AnchoredFileTarget(
            path=absolute,
            parent_descriptor=anchor.state_descriptor,
            parent_device=anchor.state_device,
            parent_inode=anchor.state_inode,
        )
    raise SafetyError(
        "locked learner-state I/O supports only direct workspace or state children"
    )


def _active_target_for_workspace_relative(
    workspace: Path,
    relative: str | Path,
) -> AnchoredFileTarget | None:
    """Return the lock-held target for one safe workspace-relative file."""

    rel = Path(relative)
    if rel.is_absolute() or _contains_parent_reference(rel):
        raise SafetyError("state path traversal is not allowed")
    anchor = _ACTIVE_WORKSPACE_IO.get()
    if anchor is None:
        return None
    absolute_workspace = _normalize_trusted_root_alias(
        _absolute_unresolved_path(workspace)
    )
    if absolute_workspace != anchor.workspace:
        return None
    return _active_target_for_path(absolute_workspace / rel)


@contextlib.contextmanager
def anchored_file_target(
    path: str | os.PathLike[str], *, create_missing: bool = True
) -> Iterator[AnchoredFileTarget]:
    """Hold the output parent generation across a later atomic replacement.

    POSIX output writes require descriptor-relative open, rename, and unlink.
    Native Windows retains the existing path-based contract, with parent
    identity checks before and after replacement because Python does not expose
    a portable directory-relative replacement there. Other platforms fail
    closed instead of silently reopening a previously validated pathname.
    """

    absolute = _normalize_trusted_root_alias(_absolute_unresolved_path(path))
    if os.name == "posix":
        if not _supports_secure_directory_fds():
            raise SafetyError(
                "descriptor-relative output writes are unavailable on this platform"
            )
        descriptor = _open_verified_directory_descriptor(
            absolute.parent, create_missing=create_missing
        )
        try:
            parent_stat = os.fstat(descriptor)
            yield AnchoredFileTarget(
                path=absolute,
                parent_descriptor=descriptor,
                parent_device=parent_stat.st_dev,
                parent_inode=parent_stat.st_ino,
            )
        finally:
            os.close(descriptor)
        return

    if os.name != "nt":
        raise SafetyError(
            "descriptor-relative output writes are unavailable on this platform"
        )
    prepared = prepare_private_parent(absolute, create_missing=create_missing)
    parent_stat = prepared.parent.lstat()
    if stat.S_ISLNK(parent_stat.st_mode) or not stat.S_ISDIR(parent_stat.st_mode):
        raise SafetyError("output parent is a symlink or not a directory")
    yield AnchoredFileTarget(
        path=prepared,
        parent_descriptor=None,
        parent_device=parent_stat.st_dev,
        parent_inode=parent_stat.st_ino,
    )


def prepare_new_workspace(path: str | os.PathLike[str]) -> Path:
    """Resolve a not-yet-created workspace without following its leaf."""

    workspace = prepare_private_parent(path)
    try:
        workspace_stat = workspace.lstat()
    except FileNotFoundError:
        return workspace
    if stat.S_ISLNK(workspace_stat.st_mode):
        raise SafetyError("workspace path must not be a symlink")
    raise ValidationError("workspace already exists; refusing to overwrite it")


def secure_workspace(path: str | os.PathLike[str]) -> Path:
    """Resolve and validate an initialized learner workspace."""

    # Reuse the no-follow ancestor walk used for creation and export. Resolving
    # the whole caller-provided path here would silently accept a user-owned
    # symlink in any ancestor and make destructive controls act on its target.
    absolute = prepare_private_parent(path, create_missing=False)
    try:
        leaf_stat = absolute.lstat()
    except FileNotFoundError as exc:
        raise StateNotFound("learner workspace does not exist") from exc
    if stat.S_ISLNK(leaf_stat.st_mode):
        raise SafetyError("learner workspace must not be a symlink")
    if not stat.S_ISDIR(leaf_stat.st_mode):
        raise SafetyError("learner workspace is not a directory")
    if stat.S_IMODE(leaf_stat.st_mode) & 0o077:
        raise SafetyError("learner workspace must have a private permission mode")
    workspace = absolute
    state = workspace / "state"
    try:
        state_stat = state.lstat()
    except FileNotFoundError as exc:
        raise StateNotFound("learner workspace has no state directory") from exc
    if stat.S_ISLNK(state_stat.st_mode):
        raise SafetyError("state directory is a symlink; refusing filesystem access")
    if not stat.S_ISDIR(state_stat.st_mode):
        raise SafetyError("state path is not a directory")
    if stat.S_IMODE(state_stat.st_mode) & 0o077:
        raise SafetyError("state directory must have a private permission mode")
    if state.resolve(strict=True).parent != workspace:
        raise SafetyError("state directory escapes the learner workspace")
    for name in REQUIRED_STATE_FILES:
        required = state / name
        try:
            required_stat = required.lstat()
        except FileNotFoundError as exc:
            raise StateNotFound(
                f"required state file is missing: state/{name}"
            ) from exc
        if stat.S_ISLNK(required_stat.st_mode) or not stat.S_ISREG(
            required_stat.st_mode
        ):
            raise SafetyError(
                f"required state path is not a regular file: state/{name}"
            )
        if required_stat.st_nlink != 1:
            raise SafetyError(
                f"required state file must not be a hardlink: state/{name}"
            )
        if stat.S_IMODE(required_stat.st_mode) & 0o077:
            raise SafetyError(
                f"required state file must have a private permission mode: state/{name}"
            )
    return workspace


def contained_path(
    workspace: Path, relative: str | Path, *, must_exist: bool = False
) -> Path:
    """Return a non-symlink path lexically and physically contained by workspace."""

    rel = Path(relative)
    if rel.is_absolute() or _contains_parent_reference(rel):
        raise SafetyError("state path traversal is not allowed")
    candidate = workspace / rel
    root = workspace.resolve(strict=True)
    current = root
    for part in rel.parts:
        current = current / part
        try:
            current_stat = current.lstat()
        except FileNotFoundError:
            if must_exist:
                raise StateNotFound(f"required state path is missing: {rel.as_posix()}")
            break
        if stat.S_ISLNK(current_stat.st_mode):
            raise SafetyError(f"state path contains a symlink: {rel.as_posix()}")
    parent = candidate.parent.resolve(strict=True)
    try:
        parent.relative_to(root)
    except ValueError as exc:
        raise SafetyError("state path escapes the learner workspace") from exc
    return candidate


def _open_flags(flags: int) -> int:
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    cloexec = getattr(os, "O_CLOEXEC", 0)
    return flags | nofollow | cloexec


def _open_binary(path: Path, flags: int, mode: int = PRIVATE_FILE_MODE) -> BinaryIO:
    try:
        descriptor = os.open(path, _open_flags(flags), mode)
    except OSError as exc:
        if path.is_symlink():
            raise SafetyError(f"refusing to follow symlink: {path.name}") from exc
        raise
    return os.fdopen(
        descriptor,
        "rb" if not flags & (os.O_WRONLY | os.O_RDWR) else "r+b",
        buffering=0,
    )


def read_bytes(workspace: Path, relative: str | Path) -> bytes:
    anchored = _active_target_for_workspace_relative(workspace, relative)
    if anchored is not None:
        _validate_anchored_parent(anchored)
        expected = _validate_anchored_destination(anchored)
        if expected is None:
            raise StateNotFound(
                f"required state path is missing: {Path(relative).as_posix()}"
            )
        if expected.st_nlink != 1:
            raise SafetyError(
                f"state file must not be a hardlink: {Path(relative).as_posix()}"
            )
        descriptor = os.open(
            anchored.path.name,
            _open_flags(os.O_RDONLY),
            dir_fd=anchored.parent_descriptor,
        )
        try:
            opened = os.fstat(descriptor)
            if (opened.st_dev, opened.st_ino) != (
                expected.st_dev,
                expected.st_ino,
            ):
                raise SafetyError("state file changed during descriptor-relative open")
            with os.fdopen(descriptor, "rb", closefd=False) as handle:
                data = handle.read()
        finally:
            os.close(descriptor)
        _validate_anchored_parent(anchored)
        return data
    path = contained_path(workspace, relative, must_exist=True)
    with _open_binary(path, os.O_RDONLY) as handle:
        return handle.read()


def read_json(workspace: Path, relative: str | Path) -> Any:
    path = Path(relative)
    try:
        return json.loads(read_bytes(workspace, path).decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise ValidationError(f"state file is not UTF-8: {path.as_posix()}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"state file is not valid JSON: {path.as_posix()} at line {exc.lineno}"
        ) from exc


def read_jsonl(workspace: Path, relative: str | Path) -> list[dict[str, Any]]:
    path = Path(relative)
    raw = read_bytes(workspace, path)
    records: list[dict[str, Any]] = []
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError(f"state log is not UTF-8: {path.as_posix()}") from exc
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            raise ValidationError(
                f"blank JSONL record in {path.as_posix()} at line {line_number}"
            )
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValidationError(
                f"invalid JSONL in {path.as_posix()} at line {line_number}"
            ) from exc
        if not isinstance(record, dict):
            raise ValidationError(
                f"JSONL record in {path.as_posix()} at line {line_number} must be an object"
            )
        records.append(record)
    return records


def fsync_directory(directory: Path) -> None:
    """Persist directory-entry changes when supported by the platform."""

    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(directory, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_write(path: Path, data: bytes, *, mode: int = PRIVATE_FILE_MODE) -> None:
    """Atomically replace ``path`` with fully flushed bytes."""

    anchored = _active_target_for_path(path)
    if anchored is not None:
        atomic_write_anchored(anchored, data, mode=mode)
        return
    parent = path.parent
    if path.is_symlink():
        raise SafetyError(f"refusing to replace symlink: {path.name}")
    temp = parent / f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    descriptor: int | None = None
    try:
        descriptor = os.open(
            temp,
            _open_flags(os.O_WRONLY | os.O_CREAT | os.O_EXCL),
            mode,
        )
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short write while persisting state")
            view = view[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.replace(temp, path)
        os.chmod(path, mode, follow_symlinks=False)
        fsync_directory(parent)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def _validate_anchored_parent(target: AnchoredFileTarget) -> None:
    expected = (target.parent_device, target.parent_inode)
    if target.parent_descriptor is not None:
        opened = os.fstat(target.parent_descriptor)
        if (opened.st_dev, opened.st_ino) != expected:
            raise SafetyError("held output-parent descriptor changed unexpectedly")
        reopened_descriptor = _open_verified_directory_descriptor(target.path.parent)
        try:
            reopened = os.fstat(reopened_descriptor)
        finally:
            os.close(reopened_descriptor)
        if (reopened.st_dev, reopened.st_ino) != expected:
            raise SafetyError("output parent changed after it was validated")
        return

    try:
        current = target.path.parent.lstat()
    except FileNotFoundError as exc:
        raise SafetyError("output parent disappeared after it was validated") from exc
    if stat.S_ISLNK(current.st_mode) or not stat.S_ISDIR(current.st_mode):
        raise SafetyError("output parent changed into a symlink or non-directory")
    if (current.st_dev, current.st_ino) != expected:
        raise SafetyError("output parent changed after it was validated")


def _validate_anchored_destination(target: AnchoredFileTarget) -> os.stat_result | None:
    try:
        if target.parent_descriptor is not None:
            target_stat = os.stat(
                target.path.name,
                dir_fd=target.parent_descriptor,
                follow_symlinks=False,
            )
        else:
            target_stat = target.path.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(target_stat.st_mode):
        raise SafetyError(f"refusing to replace symlink: {target.path.name}")
    if not stat.S_ISREG(target_stat.st_mode):
        raise ValidationError("output target exists and is not a regular file")
    return target_stat


def atomic_write_anchored(
    target: AnchoredFileTarget,
    data: bytes,
    *,
    mode: int = PRIVATE_FILE_MODE,
) -> None:
    """Atomically replace a file without reopening its POSIX parent by name."""

    _validate_anchored_parent(target)
    _validate_anchored_destination(target)
    if target.parent_descriptor is None:
        # Guarded native-Windows compatibility path; see ``anchored_file_target``.
        atomic_write(target.path, data, mode=mode)
        _validate_anchored_parent(target)
        return

    temporary_name = f".{target.path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    descriptor: int | None = None
    try:
        descriptor = os.open(
            temporary_name,
            _open_flags(os.O_WRONLY | os.O_CREAT | os.O_EXCL),
            mode,
            dir_fd=target.parent_descriptor,
        )
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short write while persisting output")
            view = view[written:]
        os.fchmod(descriptor, mode)
        os.fsync(descriptor)

        # Detect a pathname-generation swap before publishing. The replacement
        # itself remains descriptor-relative, so even a subsequent race cannot
        # redirect bytes through a symlink into learner state.
        _validate_anchored_parent(target)
        _validate_anchored_destination(target)
        written_stat = os.fstat(descriptor)
        os.rename(
            temporary_name,
            target.path.name,
            src_dir_fd=target.parent_descriptor,
            dst_dir_fd=target.parent_descriptor,
        )
        published_stat = os.stat(
            target.path.name,
            dir_fd=target.parent_descriptor,
            follow_symlinks=False,
        )
        if (published_stat.st_dev, published_stat.st_ino) != (
            written_stat.st_dev,
            written_stat.st_ino,
        ):
            raise SafetyError("output target changed during atomic replacement")
        os.fsync(target.parent_descriptor)
        _validate_anchored_parent(target)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            os.unlink(temporary_name, dir_fd=target.parent_descriptor)
        except FileNotFoundError:
            pass


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write(path, canonical_json_bytes(value))


def append_jsonl(workspace: Path, relative: str | Path, value: Any) -> None:
    """Atomically extend one durable log. Callers must hold ``workspace_lock``.

    Replacing the complete validated byte stream means a crash or short write
    can leave only an orphan temporary file. The last committed JSONL log stays
    intact rather than ending in a truncated record.
    """

    path = contained_path(workspace, relative, must_exist=True)
    data = canonical_json_line(value)
    committed = read_bytes(workspace, relative)
    if committed and not committed.endswith(b"\n"):
        raise ValidationError(
            f"state log has an uncommitted tail: {Path(relative).as_posix()}"
        )
    atomic_write(path, committed + data)


@contextlib.contextmanager
def workspace_generation_lock(workspace: Path) -> Iterator[None]:
    """Serialize reuse of one workspace pathname at its parent generation."""

    if os.name == "posix":
        descriptor = os.open(workspace.parent, _directory_open_flags())
        try:
            try:
                import fcntl  # type: ignore[import-not-found]
            except ImportError as exc:
                raise SafetyError(
                    "parent-generation locking is unavailable on this platform"
                ) from exc
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)
        return

    # Windows cannot portably lock a directory descriptor. Use one private,
    # name-derived sibling lock and apply the same anti-link checks as the
    # workspace lock itself.
    digest = hashlib.sha256(workspace.name.encode("utf-8")).hexdigest()[:16]
    namespace_path = workspace.parent / f".prax-teach-{digest}.namespace.lock"
    descriptor = os.open(
        namespace_path,
        _open_flags(os.O_RDWR | os.O_CREAT),
        PRIVATE_FILE_MODE,
    )
    try:
        opened_stat = os.fstat(descriptor)
        entry_stat = namespace_path.lstat()
        if (
            not stat.S_ISREG(opened_stat.st_mode)
            or stat.S_ISLNK(entry_stat.st_mode)
            or opened_stat.st_nlink != 1
            or entry_stat.st_nlink != 1
            or (opened_stat.st_dev, opened_stat.st_ino)
            != (entry_stat.st_dev, entry_stat.st_ino)
            or stat.S_IMODE(opened_stat.st_mode) & 0o077
        ):
            raise SafetyError("workspace namespace lock is unsafe")
        try:
            import msvcrt  # type: ignore[import-not-found]
        except ImportError as exc:
            raise SafetyError(
                "parent-generation locking is unavailable on this platform"
            ) from exc
        if opened_stat.st_size == 0:
            os.write(descriptor, b"0")
            os.fsync(descriptor)
        os.lseek(descriptor, 0, os.SEEK_SET)
        msvcrt.locking(descriptor, msvcrt.LK_LOCK, 1)
        try:
            yield
        finally:
            os.lseek(descriptor, 0, os.SEEK_SET)
            msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
    finally:
        os.close(descriptor)


@contextlib.contextmanager
def _workspace_inode_lock(
    workspace: Path,
    *,
    expected_workspace: os.stat_result,
    expected_state: os.stat_result,
) -> Iterator[None]:
    """Lock and revalidate one already generation-locked workspace."""

    lock_path = contained_path(workspace, LOCK_NAME)
    try:
        lock_stat = lock_path.lstat()
    except FileNotFoundError:
        lock_stat = None
    if lock_stat is not None:
        if stat.S_ISLNK(lock_stat.st_mode) or not stat.S_ISREG(lock_stat.st_mode):
            raise SafetyError("workspace lock must be a regular non-symlink file")
        if lock_stat.st_nlink != 1:
            raise SafetyError("workspace lock must not be a hardlink")
        if stat.S_IMODE(lock_stat.st_mode) & 0o077:
            raise SafetyError("workspace lock must have a private permission mode")
    descriptor = os.open(
        lock_path,
        _open_flags(os.O_RDWR | os.O_CREAT),
        PRIVATE_FILE_MODE,
    )
    try:
        opened_stat = os.fstat(descriptor)
        entry_stat = lock_path.lstat()
        if not stat.S_ISREG(opened_stat.st_mode) or stat.S_ISLNK(entry_stat.st_mode):
            raise SafetyError("workspace lock must be a regular non-symlink file")
        if opened_stat.st_nlink != 1 or entry_stat.st_nlink != 1:
            raise SafetyError("workspace lock must not be a hardlink")
        if (opened_stat.st_dev, opened_stat.st_ino) != (
            entry_stat.st_dev,
            entry_stat.st_ino,
        ):
            raise SafetyError("workspace lock changed during validation")
        if stat.S_IMODE(opened_stat.st_mode) & 0o077:
            raise SafetyError("workspace lock must have a private permission mode")
    except Exception:
        os.close(descriptor)
        raise
    unlock = None
    try:
        try:
            import fcntl  # type: ignore[import-not-found]

            fcntl.flock(descriptor, fcntl.LOCK_EX)
            unlock = lambda: fcntl.flock(descriptor, fcntl.LOCK_UN)
        except ImportError:
            if os.name != "nt":
                raise SafetyError(
                    "portable state locking is unavailable on this platform"
                )
            try:
                import msvcrt  # type: ignore[import-not-found]

                if os.fstat(descriptor).st_size == 0:
                    os.write(descriptor, b"0")
                    os.fsync(descriptor)
                os.lseek(descriptor, 0, os.SEEK_SET)
                msvcrt.locking(descriptor, msvcrt.LK_LOCK, 1)
                unlock = lambda: (
                    os.lseek(descriptor, 0, os.SEEK_SET),
                    msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1),
                )
            except ImportError as exc:
                raise SafetyError(
                    "portable state locking is unavailable on this platform"
                ) from exc
        try:
            current_workspace = workspace.lstat()
            current_state = (workspace / "state").lstat()
        except FileNotFoundError as exc:
            raise SafetyError(
                "learner workspace generation changed while acquiring its lock"
            ) from exc
        if (current_workspace.st_dev, current_workspace.st_ino) != (
            expected_workspace.st_dev,
            expected_workspace.st_ino,
        ) or (current_state.st_dev, current_state.st_ino) != (
            expected_state.st_dev,
            expected_state.st_ino,
        ):
            raise SafetyError(
                "learner workspace generation changed while acquiring its lock"
            )
        yield
    finally:
        if unlock is not None:
            unlock()
        os.close(descriptor)


@contextlib.contextmanager
def workspace_lock(workspace: Path) -> Iterator[None]:
    """Hold parent-generation and workspace locks for one complete operation."""

    try:
        expected_workspace = workspace.lstat()
        expected_state = (workspace / "state").lstat()
    except FileNotFoundError as exc:
        raise SafetyError(
            "learner workspace generation changed before acquiring its lock"
        ) from exc

    with workspace_generation_lock(workspace):
        try:
            current_workspace = workspace.lstat()
            current_state = (workspace / "state").lstat()
        except FileNotFoundError as exc:
            raise SafetyError(
                "learner workspace generation changed while acquiring its lock"
            ) from exc
        if (current_workspace.st_dev, current_workspace.st_ino) != (
            expected_workspace.st_dev,
            expected_workspace.st_ino,
        ) or (current_state.st_dev, current_state.st_ino) != (
            expected_state.st_dev,
            expected_state.st_ino,
        ):
            raise SafetyError(
                "learner workspace generation changed while acquiring its lock"
            )
        with _workspace_inode_lock(
            workspace,
            expected_workspace=expected_workspace,
            expected_state=expected_state,
        ):
            if os.name != "posix" or not _supports_secure_directory_fds():
                yield
                return
            workspace_descriptor = _open_verified_directory_descriptor(workspace)
            state_descriptor: int | None = None
            token = None
            try:
                state_descriptor = _open_verified_directory_descriptor(
                    workspace / "state"
                )
                opened_workspace = os.fstat(workspace_descriptor)
                opened_state = os.fstat(state_descriptor)
                if (opened_workspace.st_dev, opened_workspace.st_ino) != (
                    expected_workspace.st_dev,
                    expected_workspace.st_ino,
                ) or (opened_state.st_dev, opened_state.st_ino) != (
                    expected_state.st_dev,
                    expected_state.st_ino,
                ):
                    raise SafetyError(
                        "learner workspace generation changed while anchoring state I/O"
                    )
                token = _ACTIVE_WORKSPACE_IO.set(
                    WorkspaceIoAnchor(
                        workspace=workspace,
                        workspace_descriptor=workspace_descriptor,
                        workspace_device=opened_workspace.st_dev,
                        workspace_inode=opened_workspace.st_ino,
                        state_descriptor=state_descriptor,
                        state_device=opened_state.st_dev,
                        state_inode=opened_state.st_ino,
                    )
                )
                yield
            finally:
                if token is not None:
                    _ACTIVE_WORKSPACE_IO.reset(token)
                if state_descriptor is not None:
                    os.close(state_descriptor)
                os.close(workspace_descriptor)


def make_private_directory(path: Path) -> None:
    path.mkdir(mode=PRIVATE_DIR_MODE)
    os.chmod(path, PRIVATE_DIR_MODE)


def make_private_file(path: Path, data: bytes = b"") -> None:
    descriptor = os.open(
        path,
        _open_flags(os.O_WRONLY | os.O_CREAT | os.O_EXCL),
        PRIVATE_FILE_MODE,
    )
    try:
        if data:
            view = memoryview(data)
            while view:
                written = os.write(descriptor, view)
                view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.chmod(path, PRIVATE_FILE_MODE, follow_symlinks=False)
