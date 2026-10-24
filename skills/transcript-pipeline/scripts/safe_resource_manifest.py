"""Descriptor-bound reads for the selected session's resource manifest only."""
import os
from pathlib import Path
import stat


LIMIT = 1024 * 1024


def _identity(info):
    return info.st_dev, info.st_ino


def _version(info):
    return (_identity(info), info.st_mode, info.st_nlink, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def read_manifest(session):
    """Return bounded bytes or None if missing; refuse links and detected swaps.

    Every directory is opened without following links. Kept descriptors bind the
    read, and name-to-descriptor checks detect substitution during the read.
    Explicit external credential files use their separate existing reader.
    """
    if (not all(hasattr(os, flag) for flag in ('O_NOFOLLOW', 'O_DIRECTORY', 'O_NONBLOCK'))
            or os.open not in os.supports_dir_fd or os.stat not in os.supports_dir_fd
            or os.stat not in os.supports_follow_symlinks):
        raise RuntimeError('session manifest requires no-follow descriptor support')
    descriptors = []
    bindings = []
    leaf = None
    try:
        parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        descriptors.append(parent)
        parts = Path(os.path.abspath(session)).parts[1:] + ('.pipeline',)
        for part in parts:
            try:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            except FileNotFoundError:
                _verify(bindings)
                return None
            descriptors.append(child)
            bindings.append((parent, part, child))
            parent = child
        name = 'resource_manifest.json'
        try:
            leaf = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        except FileNotFoundError:
            _verify(bindings)
            return None
        before = os.fstat(leaf)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ValueError('resource manifest must be a single-link regular file')
        if before.st_size > LIMIT:
            raise ValueError('resource manifest exceeds 1 MiB')
        chunks, size = [], 0
        while True:
            chunk = os.read(leaf, min(65536, LIMIT + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            if size > LIMIT:
                raise ValueError('resource manifest exceeds 1 MiB')
        after = os.fstat(leaf)
        named = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if _version(before) != _version(after) or _version(after) != _version(named) or size != after.st_size:
            raise ValueError('resource manifest changed during read')
        _verify(bindings)
        return b''.join(chunks)
    finally:
        if leaf is not None:
            os.close(leaf)
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _verify(bindings):
    for parent, name, descriptor in bindings:
        named = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if not stat.S_ISDIR(named.st_mode) or _identity(named) != _identity(os.fstat(descriptor)):
            raise ValueError('session manifest directory changed during read')
