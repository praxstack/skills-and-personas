"""Descriptor-anchored atomic output; never open a destination for writing."""
from contextlib import contextmanager
from contextvars import ContextVar
import os
from pathlib import Path
import secrets
import stat

CURRENT = ContextVar('resource_output', default=None)
_DIRECTORY = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def _identity(info):
    return info.st_dev, info.st_ino, info.st_mode, info.st_nlink


class OutputDirectory:
    def __init__(self, path, *, parent_fd=None):
        self.path = Path(os.path.abspath(path))
        self.parent_fd = parent_fd
        self.fd = os.open(self.path if parent_fd is None else self.path.name,
                          _DIRECTORY, dir_fd=parent_fd)

    def close(self):
        os.close(self.fd)

    def check(self):
        if self.parent_fd is not None:
            parent = os.stat(self.path.parent, follow_symlinks=False)
            if _identity(parent) != _identity(os.fstat(self.parent_fd)):
                raise ValueError('selected session directory changed during enrichment')
        current = os.stat(self.path if self.parent_fd is None else self.path.name,
                          dir_fd=self.parent_fd, follow_symlinks=False)
        if not stat.S_ISDIR(current.st_mode) or _identity(current) != _identity(os.fstat(self.fd)):
            raise ValueError('resource output directory changed during enrichment')

    def destination(self, name):
        try:
            info = os.stat(name, dir_fd=self.fd, follow_symlinks=False)
        except FileNotFoundError:
            return None
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError('resource output destination must be a regular, unlinked file')
        return _identity(info)

    def write(self, path, blob):
        path = Path(os.path.abspath(path))
        if path.parent != self.path or path.name in {'', '.', '..'}:
            raise ValueError('resource output must be directly inside the selected output directory')
        self.check()
        original = self.destination(path.name)
        temporary = '.resource-' + secrets.token_hex(16) + '.tmp'
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=self.fd)
        try:
            # Retain the descriptor; no path-based reopen, truncation or append.
            with os.fdopen(fd, 'wb') as handle:
                handle.write(blob)
                handle.flush()
            self.check()
            if self.destination(path.name) != original:
                raise ValueError('resource output destination changed during enrichment')
            # Replacement does not follow a last-instant destination link either.
            # Such a link can never redirect these bytes to its target.
            os.replace(temporary, path.name, src_dir_fd=self.fd, dst_dir_fd=self.fd)
            self.check()
        finally:
            try:
                os.unlink(temporary, dir_fd=self.fd)
            except FileNotFoundError:
                pass


@contextmanager
def session_output(session_dir, dry_run):
    if dry_run:
        yield
        return
    session_fd = os.open(session_dir, _DIRECTORY)
    output = None
    token = None
    try:
        try:
            os.mkdir('.resources', mode=0o700, dir_fd=session_fd)
        except FileExistsError:
            pass
        output = OutputDirectory(Path(session_dir) / '.resources', parent_fd=session_fd)
        token = CURRENT.set(output)
        yield
    finally:
        if token is not None:
            CURRENT.reset(token)
        if output is not None:
            output.close()
        os.close(session_fd)


def write_bytes(path, blob):
    output = CURRENT.get()
    if output is not None:
        output.write(path, blob)
    else:
        # Preserve direct helper calls while applying the same no-follow writer.
        output = OutputDirectory(Path(path).parent)
        try:
            output.write(path, blob)
        finally:
            output.close()
