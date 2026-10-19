"""Fail-closed filesystem primitives for learner state.

The module deliberately uses only the Python standard library.  Mutable files
are protected by a process lock, opened without following symlinks where the
platform exposes ``O_NOFOLLOW``, and replaced atomically after an fsync.
"""

from __future__ import annotations

import contextlib
import ctypes
import errno
import functools
import hashlib
import json
import os
import stat
import sys
import uuid
import warnings
from collections.abc import Callable, Iterator
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Any, BinaryIO

from . import sync
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



class HardlinkAccepted(UserWarning):
    """A state file had more than one hard link and was read because it carries this workspace's binding."""


# Learner binding (D22.3, plan/PROTECTED-MAP.md): learner state binds content, not link counts.
#
# v2 refused any state file with st_nlink != 1. Google Drive for desktop backs up ~/Developer and ~/Study and
# hard-links each new file into <root>/.tmp.driveupload within about 1.5 s while it uploads it
# (plan/EVIDENCE-HARDLINKS.md; see sync.py), so that rule made learner-state writes fail at random. Accepting
# any same-owner link instead (the round-15 integration pass) let learner B's state, hard-linked into learner
# A's workspace, be read and exported as A's.
#
# Now each workspace's state directory carries a random learner binding ("lw-" + 32 hex), and every state
# file the engine writes carries the same binding on its inode, stamped on the fresh temporary file before
# it is renamed into place. Both live in the extended attribute below. A hard link shares its inode, so it
# shares the binding: a staging link to this learner's own file carries this workspace's binding and is read
# with a warning; a link to another learner's file carries the other binding and is refused. Directories
# cannot be hard-linked, so the state directory's binding cannot be aliased the same way.
#
# Migration for files written by older code (no binding): a file with one link is read and stamped on the
# first command that touches it (it has no other name, so it is this workspace's). An unbound file that
# already has an extra link is refused; `python -m ptk.state rebind <workspace> --confirm` copies it onto a
# fresh, bound inode after the learner has seen the list. Where the filesystem has no extended attributes
# (some Linux tmpfs, Windows), nothing is bound and v2's rule applies: any extra link is refused.
BINDING_ATTRIBUTE = "user.praxteach.learner"
_BINDING_PREFIX = "lw-"
_XATTR_NOFOLLOW = 0x0001  # macOS <sys/xattr.h>
_XATTR_CREATE = 0x0002
_XATTR_UNSUPPORTED = {
    code
    for code in (
        getattr(errno, "ENOTSUP", None),
        getattr(errno, "EOPNOTSUPP", None),
        getattr(errno, "ENOSYS", None),
    )
    if code is not None
}
_XATTR_ABSENT = {
    code
    for code in (getattr(errno, "ENODATA", None), getattr(errno, "ENOATTR", None))
    if code is not None
}
_STAMP_DENIED = {errno.EACCES, errno.EPERM, errno.EROFS}
ANY_BINDING = "*"

# D23.3 (AC-11.4): read-only commands write nothing, extended attributes included, when persistence consent is
# absent or withdrawn. The CLI runs those commands inside read_only_access(), which turns this off unless the
# workspace's learner.json shows active consent; ensure_binding, adoption and lock creation then write nothing.
_METADATA_WRITES: ContextVar[bool] = ContextVar("prax_teach_metadata_writes", default=True)
# The Drive root holding the workspace being validated, for the HardlinkAccepted warning (AC-11.2).
_SYNC_LOCATION: ContextVar[sync.SyncedLocation | None] = ContextVar("prax_teach_sync_location", default=None)


def metadata_writes_allowed() -> bool:
    return _METADATA_WRITES.get()


def consent_active(path: str | os.PathLike[str]) -> bool:
    """Whether the workspace's state/learner.json shows active persistence consent. Read only; any doubt is False.

    This only decides whether a read-only command may stamp bindings; secure_workspace still validates everything.
    """

    try:
        descriptor = os.open(
            Path(os.path.abspath(path)) / "state" / "learner.json",
            _open_flags(os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)),
        )
    except OSError:
        return False
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            return False
        data = os.read(descriptor, 1 << 20)
    except OSError:
        return False
    finally:
        os.close(descriptor)
    try:
        consent = json.loads(data.decode("utf-8")).get("consent")
        return isinstance(consent, dict) and consent.get("persistent_state") is True
    except (UnicodeDecodeError, ValueError, AttributeError):
        return False


@contextlib.contextmanager
def read_only_access(path: str | os.PathLike[str]) -> Iterator[None]:
    """Run a read-only command: no binding or lock is written unless persistence consent is active."""

    token = _METADATA_WRITES.set(consent_active(path))
    try:
        yield
    finally:
        _METADATA_WRITES.reset(token)


class _NoExtendedAttributes(Exception):
    """This platform or filesystem cannot store a learner binding."""


@functools.lru_cache(maxsize=1)
def _darwin_libc() -> Any:
    library = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
    for name, result in (
        ("getxattr", ctypes.c_ssize_t),
        ("fgetxattr", ctypes.c_ssize_t),
        ("setxattr", ctypes.c_int),
        ("fsetxattr", ctypes.c_int),
    ):
        function = getattr(library, name)
        function.restype = result
        first = ctypes.c_int if name.startswith("f") else ctypes.c_char_p
        function.argtypes = [
            first,
            ctypes.c_char_p,
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.c_uint32,
            ctypes.c_int,
        ]
    return library


def _xattr_error(exc: OSError) -> None:
    if exc.errno in _XATTR_UNSUPPORTED:
        raise _NoExtendedAttributes(str(exc)) from exc
    raise exc


def _xattr_read(target: int | Path) -> bytes | None:
    """Read the binding attribute of an open descriptor or a no-follow path; None when absent."""

    name = BINDING_ATTRIBUTE.encode()
    try:
        if hasattr(os, "getxattr"):
            if isinstance(target, int):
                return os.getxattr(target, BINDING_ATTRIBUTE)
            return os.getxattr(os.fspath(target), BINDING_ATTRIBUTE, follow_symlinks=False)
        if sys.platform != "darwin":
            raise _NoExtendedAttributes("no extended-attribute interface on this platform")
        library = _darwin_libc()
        buffer = ctypes.create_string_buffer(256)
        if isinstance(target, int):
            size = library.fgetxattr(target, name, buffer, len(buffer), 0, 0)
        else:
            size = library.getxattr(
                os.fsencode(target), name, buffer, len(buffer), 0, _XATTR_NOFOLLOW
            )
        if size < 0:
            code = ctypes.get_errno()
            raise OSError(code, os.strerror(code))
        return buffer.raw[:size]
    except OSError as exc:
        if exc.errno in _XATTR_ABSENT:
            return None
        if exc.errno == errno.ERANGE:
            return b""  # longer than any binding the engine writes: treated as foreign
        _xattr_error(exc)
        raise AssertionError("unreachable") from exc


def _xattr_write(target: int | Path, value: bytes, *, create_only: bool) -> None:
    try:
        if hasattr(os, "setxattr"):
            flags = os.XATTR_CREATE if create_only else 0
            if isinstance(target, int):
                os.setxattr(target, BINDING_ATTRIBUTE, value, flags)
            else:
                os.setxattr(
                    os.fspath(target), BINDING_ATTRIBUTE, value, flags, follow_symlinks=False
                )
            return
        if sys.platform != "darwin":
            raise _NoExtendedAttributes("no extended-attribute interface on this platform")
        library = _darwin_libc()
        name = BINDING_ATTRIBUTE.encode()
        options = _XATTR_CREATE if create_only else 0
        if isinstance(target, int):
            result = library.fsetxattr(target, name, value, len(value), 0, options)
        else:
            result = library.setxattr(
                os.fsencode(target), name, value, len(value), 0, options | _XATTR_NOFOLLOW
            )
        if result != 0:
            code = ctypes.get_errno()
            raise OSError(code, os.strerror(code))
    except OSError as exc:
        _xattr_error(exc)


def read_binding(target: int | str | os.PathLike[str]) -> str | None:
    """The learner binding an inode carries (descriptor, or path without following a symlink)."""

    try:
        raw = _xattr_read(target if isinstance(target, int) else Path(target))
    except _NoExtendedAttributes:
        return None
    if raw is None:
        return None
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError:
        return "foreign"
    return text if text else "foreign"


def bindings_supported(path: str | os.PathLike[str]) -> bool:
    """Whether the filesystem holding ``path`` can carry learner bindings."""

    try:
        _xattr_read(Path(path))
    except _NoExtendedAttributes:
        return False
    return True


def ensure_binding(state_directory: int | Path) -> str | None:
    """Return the state directory's learner binding, creating it once (race-safe) when absent.

    None means the filesystem cannot carry one (or refuses the write), so only single-link files are read.
    """

    current = read_binding(state_directory)
    if current is not None or not _METADATA_WRITES.get():
        return current
    try:
        _xattr_write(
            state_directory,
            (_BINDING_PREFIX + uuid.uuid4().hex).encode("ascii"),
            create_only=True,
        )
    except _NoExtendedAttributes:
        return None
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            return read_binding(state_directory)
        if exc.errno in _STAMP_DENIED:
            return None
        raise
    return read_binding(state_directory)


def stamp_binding(descriptor: int, binding: str | None) -> None:
    """Stamp a freshly created (or single-link) file with this workspace's learner binding."""

    if binding is None or binding == ANY_BINDING:
        return
    try:
        _xattr_write(descriptor, binding.encode("ascii"), create_only=False)
    except _NoExtendedAttributes:
        return
    except OSError as exc:
        if exc.errno not in _STAMP_DENIED:
            raise


def adopt_single_link(descriptor: int, binding: str | None) -> None:
    """Stamp an unbound file written by older code, but only while it has exactly one link."""

    if binding is None or binding == ANY_BINDING or not _METADATA_WRITES.get():
        return
    opened = os.fstat(descriptor)
    if opened.st_nlink == 1 and stat.S_ISREG(opened.st_mode) and read_binding(descriptor) is None:
        stamp_binding(descriptor, binding)


def link_problem(
    entry: os.stat_result,
    label: str,
    *,
    carried: Callable[[], str | None],
    expected: str | None,
) -> str | None:
    """Why ``entry`` must be refused, or None (D22.3; see the comment above BINDING_ATTRIBUTE).

    ``carried`` reads the inode's binding lazily. ``expected`` is the state directory's binding, or
    ANY_BINDING where the content itself names the workspace (the full-deletion journal).
    A single-link file is refused only when it carries another workspace's binding. A file with more
    than one link must be a regular file this user owns that carries this workspace's binding; it is
    then accepted with a HardlinkAccepted warning.
    """

    if entry.st_nlink == 1:
        if not stat.S_ISREG(entry.st_mode) or expected is None or expected == ANY_BINDING:
            return None
        binding = carried()
        if binding is not None and binding != expected:
            return "is bound to another learner workspace"
        return None
    if stat.S_ISLNK(entry.st_mode) or not stat.S_ISREG(entry.st_mode):
        return "is a hardlink and not a regular file"
    geteuid = getattr(os, "geteuid", None)
    if geteuid is None or entry.st_uid != geteuid():
        return "is a hardlink owned by another user"
    if expected is None:
        return (
            "is a hardlink, and this workspace has no learner binding to check it against "
            "(the filesystem cannot store one)"
        )
    binding = carried()
    if binding is None:
        return (
            "is a hardlink that carries no learner binding (written by older code or not by prax-teach); "
            "if it is this learner's own file, run `python -m ptk.state rebind <workspace>` to review and "
            "copy it onto a fresh inode"
        )
    if expected != ANY_BINDING and binding != expected:
        return "is a hardlink bound to another learner workspace"
    warnings.warn(
        f"prax-teach state: {label} has {entry.st_nlink} hard links ({sync.link_cause(_SYNC_LOCATION.get())}); "
        "read because it carries this learner workspace's binding",
        HardlinkAccepted,
        stacklevel=2,
    )
    return None


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

            _ok0 = False
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
                _ok0 = True
            finally:
                if not _ok0:
                    os.close(child_fd)
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
    _ok2 = False
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
            _ok1 = False
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
                _ok1 = True
            finally:
                if not _ok1:
                    os.close(child_fd)
            os.close(current_fd)
            current_fd = child_fd
            current_path = component
        _ok2 = True
        return current_fd
    finally:
        if not _ok2:
            os.close(current_fd)


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
    binding: str | None = None


_ACTIVE_WORKSPACE_IO: ContextVar[WorkspaceIoAnchor | None] = ContextVar(
    "prax_teach_active_workspace_io",
    default=None,
)


def _active_binding() -> str | None:
    """The learner binding of the lock-held workspace, if any."""

    anchor = _ACTIVE_WORKSPACE_IO.get()
    return None if anchor is None else anchor.binding


def _binding_for_parent(target: AnchoredFileTarget) -> str | None:
    """Writes into the lock-held workspace or its state directory carry that workspace's binding."""

    anchor = _ACTIVE_WORKSPACE_IO.get()
    if anchor is None or target.parent_descriptor is None:
        return None
    if target.parent_descriptor in (anchor.workspace_descriptor, anchor.state_descriptor):
        return anchor.binding
    return None


def _binding_for_path(path: Path) -> str | None:
    """Binding for a write outside a lock scope: the state directory's, for a file in it or beside it."""

    anchor = _ACTIVE_WORKSPACE_IO.get()
    if anchor is not None:
        try:
            relative = path.relative_to(anchor.workspace)
        except ValueError:
            relative = None
        if relative is not None and len(relative.parts) in (1, 2):
            return anchor.binding
    for candidate in (path.parent, path.parent / "state"):
        if candidate.name != "state":
            continue
        try:
            candidate_stat = candidate.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISDIR(candidate_stat.st_mode):
            return read_binding(candidate)
    return None


def workspace_binding(workspace: Path) -> str | None:
    """The learner binding of ``workspace``'s state directory (the held one when its lock is active)."""

    anchor = _ACTIVE_WORKSPACE_IO.get()
    if anchor is not None and anchor.workspace == workspace:
        return anchor.binding
    return read_binding(workspace / "state")


def binding_at(directory_descriptor: int, name: str, entry: os.stat_result) -> str | None:
    """Read the binding of the regular file ``name`` in a held directory, checking it is the inode in ``entry``."""

    descriptor = os.open(
        name,
        _open_flags(os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)),
        dir_fd=directory_descriptor,
    )
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (entry.st_dev, entry.st_ino):
            raise SafetyError(f"{name} changed while its learner binding was read")
        return read_binding(descriptor)
    finally:
        os.close(descriptor)


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


def _adopt_by_path(path: Path, entry: os.stat_result, binding: str | None) -> None:
    """Stamp a single-link, unbound regular file found by path (legacy migration; see BINDING_ATTRIBUTE)."""

    if binding is None or entry.st_nlink != 1 or not stat.S_ISREG(entry.st_mode) or not _METADATA_WRITES.get():
        return
    try:
        descriptor = os.open(path, _open_flags(os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)))
    except FileNotFoundError:
        return
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) == (entry.st_dev, entry.st_ino):
            adopt_single_link(descriptor, binding)
    finally:
        os.close(descriptor)


def secure_workspace(path: str | os.PathLike[str], *, check_bindings: bool = True) -> Path:
    """Resolve and validate an initialized learner workspace.

    ``check_bindings=False`` is only for ``rebind``, which reviews every binding problem itself under the lock.
    """

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
    _SYNC_LOCATION.set(sync.detect(workspace))
    binding = ensure_binding(state)
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
        if check_bindings:
            problem = link_problem(
                required_stat,
                f"state/{name}",
                carried=lambda required=required: read_binding(required),
                expected=binding,
            )
            if problem is not None:
                raise SafetyError(f"refusing required state file state/{name}: it {problem}")
        if stat.S_IMODE(required_stat.st_mode) & 0o077:
            raise SafetyError(
                f"required state file must have a private permission mode: state/{name}"
            )
        if check_bindings:
            _adopt_by_path(required, required_stat, binding)
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
        label = Path(relative).as_posix()
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
            binding = _active_binding()
            problem = link_problem(
                opened,
                label,
                carried=lambda: read_binding(descriptor),
                expected=binding,
            )
            if problem is not None:
                raise SafetyError(f"refusing state file {label}: it {problem}")
            adopt_single_link(descriptor, binding)
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


def atomic_write(
    path: Path,
    data: bytes,
    *,
    mode: int = PRIVATE_FILE_MODE,
    binding: str | None = None,
) -> None:
    """Atomically replace ``path`` with fully flushed bytes.

    Every write lands on a fresh inode (exclusive temporary file, fsync, rename over the name), so it never
    goes through a hard link, and the new inode carries the workspace's learner binding before it is published.
    """

    anchored = _active_target_for_path(path)
    if anchored is not None:
        atomic_write_anchored(anchored, data, mode=mode, binding=binding)
        return
    if binding is None:
        binding = _binding_for_path(path)
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
        stamp_binding(descriptor, binding)
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
    binding: str | None = None,
) -> None:
    """Atomically replace a file without reopening its POSIX parent by name (fresh inode, bound; see atomic_write)."""

    _validate_anchored_parent(target)
    _validate_anchored_destination(target)
    if binding is None:
        binding = _binding_for_parent(target)
    if target.parent_descriptor is None:
        # Guarded native-Windows compatibility path; see ``anchored_file_target``.
        atomic_write(target.path, data, mode=mode, binding=binding)
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
        stamp_binding(descriptor, binding)
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


def atomic_write_json(path: Path, value: Any, *, binding: str | None = None) -> None:
    atomic_write(path, canonical_json_bytes(value), binding=binding)


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


def _lock_problem(entry: os.stat_result, *, carried: Callable[[], str | None], binding: str | None) -> None:
    if stat.S_ISLNK(entry.st_mode) or not stat.S_ISREG(entry.st_mode):
        raise SafetyError("workspace lock must be a regular non-symlink file")
    problem = link_problem(entry, "workspace lock", carried=carried, expected=binding)
    if problem is not None:
        raise SafetyError(f"refusing workspace lock: it {problem}")
    if stat.S_IMODE(entry.st_mode) & 0o077:
        raise SafetyError("workspace lock must have a private permission mode")


@contextlib.contextmanager
def _workspace_inode_lock(
    workspace: Path,
    *,
    expected_workspace: os.stat_result,
    expected_state: os.stat_result,
    binding: str | None = None,
) -> Iterator[None]:
    """Lock and revalidate one already generation-locked workspace.

    A missing lock is created exclusively (a fresh inode carrying the learner binding). An existing lock is
    checked by path before it is opened, so a lock hard-linked from elsewhere is never opened, and again on
    the opened descriptor. The lock's bytes are never written on POSIX (flock only).
    """

    lock_path = contained_path(workspace, LOCK_NAME)
    descriptor: int | None = None
    if not _METADATA_WRITES.get():
        try:
            lock_path.lstat()
        except FileNotFoundError:
            # A read-only command without consent never creates the lock; the caller already holds the parent
            # generation lock, which serializes every operation on this workspace.
            yield
            return
    try:
        if not _METADATA_WRITES.get():
            raise FileExistsError(lock_path)
        descriptor = os.open(
            lock_path,
            _open_flags(os.O_RDWR | os.O_CREAT | os.O_EXCL),
            PRIVATE_FILE_MODE,
        )
    except FileExistsError:
        descriptor = None
    if descriptor is not None:
        try:
            stamp_binding(descriptor, binding)
        except OSError:
            os.close(descriptor)
            raise
    else:
        try:
            lock_stat = lock_path.lstat()
        except FileNotFoundError as exc:
            raise SafetyError("workspace lock disappeared during validation") from exc
        if stat.S_IMODE(lock_stat.st_mode) & 0o077 and lock_stat.st_nlink != 1:
            raise SafetyError(
                "workspace lock must have a private permission mode (it is also a hardlink)"
            )
        _lock_problem(lock_stat, carried=lambda: read_binding(lock_path), binding=binding)
        try:
            descriptor = os.open(lock_path, _open_flags(os.O_RDWR | getattr(os, "O_NONBLOCK", 0)))
        except FileNotFoundError as exc:
            raise SafetyError("workspace lock disappeared during validation") from exc
    _ok3 = False
    try:
        opened_stat = os.fstat(descriptor)
        entry_stat = lock_path.lstat()
        if not stat.S_ISREG(opened_stat.st_mode) or stat.S_ISLNK(entry_stat.st_mode):
            raise SafetyError("workspace lock must be a regular non-symlink file")
        if (opened_stat.st_dev, opened_stat.st_ino) != (
            entry_stat.st_dev,
            entry_stat.st_ino,
        ):
            raise SafetyError("workspace lock changed during validation")
        _lock_problem(opened_stat, carried=lambda: read_binding(descriptor), binding=binding)
        adopt_single_link(descriptor, binding)
        _ok3 = True
    finally:
        if not _ok3:
            os.close(descriptor)
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
        binding = ensure_binding(workspace / "state")
        with _workspace_inode_lock(
            workspace,
            expected_workspace=expected_workspace,
            expected_state=expected_state,
            binding=binding,
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
                        binding=read_binding(state_descriptor),
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


def make_private_file(path: Path, data: bytes = b"", *, binding: str | None = None) -> None:
    """Create a new private file exclusively (fresh inode) carrying the workspace's learner binding."""

    if binding is None:
        binding = _binding_for_path(path)
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
        stamp_binding(descriptor, binding)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.chmod(path, PRIVATE_FILE_MODE, follow_symlinks=False)
