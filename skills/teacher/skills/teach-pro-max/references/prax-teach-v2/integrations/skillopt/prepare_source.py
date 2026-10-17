#!/usr/bin/env python3
"""Prepare a new, pinned SkillOpt source tree with the Prax Teach adapter."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

EXPECTED_COMMIT = "e4ea6a6771e797ef820cdd8bfea64c57e0481065"
REGISTRY_FILES = ("scripts/eval_only.py", "scripts/train.py")
REGISTRY_ANCHOR = "\n\ndef get_adapter(cfg: dict):"
REGISTRY_BLOCK = """
    try:
        from skillopt.envs.prax_teach.adapter import PraxTeachAdapter
        _ENV_REGISTRY["prax_teach"] = PraxTeachAdapter
    except ImportError:
        pass
"""


class PreparationError(RuntimeError):
    """Raised when the pinned-source preparation cannot fail safely."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head(source: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=source,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise PreparationError("source is not a readable Git checkout")
    return completed.stdout.strip()


def _require_clean_tracked_source(source: Path) -> None:
    completed = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=source,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise PreparationError("could not inspect the source worktree")
    if completed.stdout.strip():
        raise PreparationError(
            "source has tracked or non-ignored untracked changes; "
            "it is not the exact pinned tree"
        )


def _git_blob_oid(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data, usedforsecurity=False).hexdigest()


def _tracked_snapshot(source: Path) -> list[tuple[PurePosixPath, bytes, int]]:
    """Read only regular files from the pinned Git tree and verify every blob.

    `git status` rejects non-ignored untracked material. This snapshot separately
    ensures that even ignored worktree files can never enter the prepared tree.
    """

    completed = subprocess.run(
        ["git", "ls-tree", "-r", "-z", "--full-tree", "HEAD"],
        cwd=source,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise PreparationError("could not enumerate the pinned Git tree")

    snapshot: list[tuple[PurePosixPath, bytes, int]] = []
    for raw_entry in completed.stdout.split(b"\0"):
        if not raw_entry:
            continue
        try:
            metadata, raw_path = raw_entry.split(b"\t", 1)
            mode_text, object_type, object_id = metadata.decode("ascii").split(" ")
            path_text = raw_path.decode("utf-8")
        except (UnicodeDecodeError, ValueError) as exc:
            raise PreparationError("Git tree contains an unsupported entry") from exc
        if object_type != "blob" or mode_text not in {"100644", "100755"}:
            raise PreparationError(
                f"tracked entry {path_text!r} is not a regular non-symlink file"
            )
        relative = PurePosixPath(path_text)
        if (
            relative.is_absolute()
            or not relative.parts
            or any(part in {"", ".", ".."} for part in relative.parts)
        ):
            raise PreparationError(f"unsafe tracked path {path_text!r}")

        worktree_path = source.joinpath(*relative.parts)
        current = source
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise PreparationError(
                    f"tracked path {path_text!r} traverses a worktree symlink"
                )
        try:
            file_stat = worktree_path.stat()
            data = worktree_path.read_bytes()
        except OSError as exc:
            raise PreparationError(
                f"tracked file {path_text!r} cannot be read"
            ) from exc
        if not stat.S_ISREG(file_stat.st_mode):
            raise PreparationError(f"tracked path {path_text!r} is not a regular file")
        if _git_blob_oid(data) != object_id:
            raise PreparationError(
                f"tracked file {path_text!r} does not match its pinned Git blob"
            )
        mode = 0o755 if mode_text == "100755" else 0o644
        snapshot.append((relative, data, mode))

    if not snapshot:
        raise PreparationError("pinned Git tree contains no regular files")
    return snapshot


def _snapshot_fingerprint(
    snapshot: list[tuple[PurePosixPath, bytes, int]],
) -> str:
    digest = hashlib.sha256()
    for relative, data, mode in snapshot:
        digest.update(f"{mode:o} {relative.as_posix()}\0".encode())
        digest.update(hashlib.sha256(data).digest())
    return digest.hexdigest()


def _write_snapshot(
    staging: Path, snapshot: list[tuple[PurePosixPath, bytes, int]]
) -> None:
    for relative, data, mode in snapshot:
        target = staging.joinpath(*relative.parts)
        target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        target.write_bytes(data)
        os.chmod(target, mode)


def _patch_registry(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(REGISTRY_ANCHOR) != 1:
        raise PreparationError(f"stable registry anchor changed in {path.name}")
    if "PraxTeachAdapter" in text or '_ENV_REGISTRY["prax_teach"]' in text:
        raise PreparationError(f"prax_teach registry already exists in {path.name}")
    patched = text.replace(REGISTRY_ANCHOR, REGISTRY_BLOCK + REGISTRY_ANCHOR, 1)
    path.write_text(patched, encoding="utf-8")


def prepare(source: Path, destination: Path) -> dict[str, object]:
    source = source.expanduser().resolve(strict=True)
    destination = destination.expanduser().absolute()
    if not source.is_dir():
        raise PreparationError("source must be a directory")
    if destination.exists() or destination.is_symlink():
        raise PreparationError("destination must not already exist")
    destination_resolved = destination.resolve(strict=False)
    if source == destination_resolved or source in destination_resolved.parents:
        raise PreparationError("destination must not be inside the source checkout")
    if destination_resolved in source.parents:
        raise PreparationError("destination must not contain the source checkout")

    head = _git_head(source)
    if head != EXPECTED_COMMIT:
        raise PreparationError(
            f"source commit mismatch: expected {EXPECTED_COMMIT}, got {head or 'none'}"
        )
    _require_clean_tracked_source(source)
    snapshot = _tracked_snapshot(source)
    snapshot_paths = {relative.as_posix() for relative, _data, _mode in snapshot}
    if not set(REGISTRY_FILES).issubset(snapshot_paths):
        raise PreparationError("pinned source is missing a tracked registry script")
    originals = {relative: _sha256(source / relative) for relative in REGISTRY_FILES}

    integration = Path(__file__).resolve().parent
    adapter_source = integration / "prax_teach_adapter.py"
    init_source = integration / "__init__.py"
    if not adapter_source.is_file() or not init_source.is_file():
        raise PreparationError("integration adapter files are missing")

    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.prepare-", dir=destination.parent)
    )
    try:
        _write_snapshot(staging, snapshot)
        adapter_dir = staging / "skillopt" / "envs" / "prax_teach"
        adapter_dir.mkdir(mode=0o755, parents=True, exist_ok=False)
        shutil.copy2(adapter_source, adapter_dir / "adapter.py")
        shutil.copy2(init_source, adapter_dir / "__init__.py")
        for relative in REGISTRY_FILES:
            _patch_registry(staging / relative)
        for relative, before in originals.items():
            if _sha256(source / relative) != before:
                raise PreparationError(f"source mutation detected in {relative}")
        if _git_head(source) != head:
            raise PreparationError("source commit changed during preparation")
        _require_clean_tracked_source(source)
        os.replace(staging, destination)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise

    receipt: dict[str, object] = {
        "adapter_sha256": _sha256(adapter_source),
        "destination_created": True,
        "registered_in": list(REGISTRY_FILES),
        "source_commit": head,
        "source_mutated": False,
        "tracked_source_file_count": len(snapshot),
        "tracked_tree_sha256": _snapshot_fingerprint(snapshot),
    }
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = prepare(args.source, args.destination)
    except (OSError, PreparationError, subprocess.SubprocessError) as exc:
        print(f"prepare_source: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
