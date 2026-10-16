#!/usr/bin/env python3
"""Generate or check the immutable payload reviewed by independent agents."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

PRUNED_DIRECTORY_NAMES = {
    ".agent",
    ".agents",
    ".git",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "env",
    "hidden-bank",
    "hidden-banks",
    "hidden_bank",
    "hidden_banks",
    "learner-workspace",
    "learner-workspaces",
    "learner_workspace",
    "learner_workspaces",
    "node_modules",
    "private-bank",
    "private-banks",
    "private_bank",
    "private_banks",
    "runs",
    "openspec",
    "venv",
}
REVIEW_PAYLOAD_FILE = "evidence/reviews/payload.json"
REVIEW_RECEIPT_FILES = frozenset(
    {
        "evidence/reviews/architecture-council.json",
        "evidence/reviews/code-standards.json",
        "evidence/reviews/frozen-spec.json",
    }
)
FULL_VERIFICATION_FILE = "evidence/verification/full.json"
EXCLUDED_FILES = frozenset(
    {REVIEW_PAYLOAD_FILE, FULL_VERIFICATION_FILE, *REVIEW_RECEIPT_FILES}
)


class PayloadError(RuntimeError):
    """A payload cannot be represented safely."""


def read_stable_regular(path: Path, expected: os.stat_result | None = None) -> bytes:
    """Read one stable regular-file generation without following symlinks."""
    before = expected or path.lstat()
    if stat.S_ISLNK(before.st_mode):
        raise PayloadError(f"review payload is a symlink: {path}")
    if not stat.S_ISREG(before.st_mode):
        raise PayloadError(f"review payload contains a non-regular file: {path}")
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0),
        )
    except OSError as exc:
        raise PayloadError(
            f"review payload file changed while opening: {path}"
        ) from exc
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (
            before.st_dev,
            before.st_ino,
        ):
            raise PayloadError(f"review payload file changed while opening: {path}")
        contents = bytearray()
        while chunk := os.read(descriptor, 1024 * 1024):
            contents.extend(chunk)
        finished = os.fstat(descriptor)
        after = path.lstat()
        stable_fields = ("st_size", "st_mtime_ns", "st_ctime_ns")
        if (
            stat.S_ISLNK(after.st_mode)
            or (after.st_dev, after.st_ino) != (opened.st_dev, opened.st_ino)
            or any(
                getattr(finished, name) != getattr(opened, name)
                for name in stable_fields
            )
        ):
            raise PayloadError(f"review payload file changed while reading: {path}")
        return bytes(contents)
    finally:
        os.close(descriptor)


def sha256(path: Path, expected: os.stat_result | None = None) -> str:
    """Hash one stable regular-file generation without following symlinks."""

    return hashlib.sha256(read_stable_regular(path, expected)).hexdigest()


def distributable_mode(mode: int) -> str:
    """Normalize host permissions to Git/archive regular-file semantics."""

    return "0755" if stat.S_IMODE(mode) & 0o111 else "0644"


def payload_manifest(root: Path) -> dict[str, Any]:
    files: list[dict[str, str]] = []
    for current, directory_names, file_names in os.walk(root, followlinks=False):
        current_path = Path(current)
        kept: list[str] = []
        for name in sorted(directory_names):
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                raise PayloadError(
                    f"review payload contains a directory symlink: {relative}"
                )
            if name in PRUNED_DIRECTORY_NAMES:
                continue
            kept.append(name)
        directory_names[:] = kept
        for name in sorted(file_names):
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if relative in EXCLUDED_FILES:
                continue
            metadata = path.lstat()
            if not stat.S_ISREG(metadata.st_mode):
                raise PayloadError(
                    f"review payload contains a non-regular file: {relative}"
                )
            files.append(
                {
                    "mode": distributable_mode(metadata.st_mode),
                    "path": relative,
                    "sha256": sha256(path, metadata),
                }
            )
    files.sort(key=lambda item: item["path"])
    canonical = json.dumps(
        files, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return {
        "schema_version": 1,
        "scope": "final-feature-payload",
        "algorithm": "sha256(canonical-json(files[path,mode,sha256]))",
        "excluded": [
            *sorted(EXCLUDED_FILES),
            ".git/",
            "runtime/cache directories",
        ],
        "file_count": len(files),
        "files": files,
        "sha256": hashlib.sha256(canonical).hexdigest(),
    }


def resolve_output(root: Path, relative: str) -> Path:
    parts = PurePosixPath(relative)
    if parts.is_absolute() or ".." in parts.parts:
        raise PayloadError("output must be a safe relative path")
    output = root / relative
    resolved_parent = output.parent.resolve()
    if not resolved_parent.is_relative_to(root):
        raise PayloadError("output parent resolves outside the review root")
    return output


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument(
        "--output",
        default="evidence/reviews/payload.json",
        help="safe path relative to root",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail unless the existing payload matches current bytes",
    )
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        print(f"review root is not a directory: {root}", file=sys.stderr)
        return 2
    try:
        output = resolve_output(root, args.output)
        expected = payload_manifest(root)
        if args.check:
            try:
                actual = json.loads(read_stable_regular(output))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise PayloadError(
                    f"review payload is missing or invalid: {exc}"
                ) from exc
            if actual != expected:
                print("review payload is stale", file=sys.stderr)
                return 1
            print(expected["sha256"])
            return 0
        atomic_write_json(output, expected)
        print(expected["sha256"])
        return 0
    except PayloadError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
