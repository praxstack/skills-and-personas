#!/usr/bin/env python3
"""Build a deterministic ZIP from immutable blobs in a reviewed Git commit."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from praxteach.errors import SafetyError, ValidationError
from praxteach.io import prepare_private_parent
from verify import PRUNED_DIRECTORIES

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "learner-workspaces",
    "node_modules",
    "private-banks",
    "runs",
}
# Control-plane files are reviewed and validated separately from the
# distributable candidate.  Keep them out of the immutable release inventory;
# including them would make the archive disagree with evidence/reviews/payload.json.
CONTROL_PLANE_PARTS = {".agent", ".agents", "openspec"}
FORBIDDEN_SUFFIXES = {".log", ".pyc", ".pyo"}
ALLOWED_GIT_MODES = {"100644": 0o644, "100755": 0o755}
REVIEW_PAYLOAD = "evidence/reviews/payload.json"
FULL_VERIFICATION = "evidence/verification/full.json"
REVIEW_TYPES = ("code-standards", "frozen-spec", "architecture-council")


class PackageError(ValueError):
    """Raised when the release tree is unsafe or not review-frozen."""


@dataclass(frozen=True)
class FrozenFile:
    """One immutable Git blob and its archive metadata."""

    data: bytes
    git_object: str
    mode: int
    name: str


def stable_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode()


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def run_git(root: Path, *arguments: str, text: bool = True) -> str | bytes:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        text=text,
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        stderr = completed.stderr if text else completed.stderr.decode(errors="replace")
        raise PackageError(stderr.strip() or f"git {' '.join(arguments)} failed")
    return completed.stdout


def validate_relative_path(relative_text: str) -> PurePosixPath:
    relative = PurePosixPath(relative_text)
    if (
        relative.is_absolute()
        or not relative.parts
        or ".." in relative.parts
        or any(part in {"", "."} for part in relative.parts)
    ):
        raise PackageError(f"unsafe tracked path: {relative_text}")
    if any(part in FORBIDDEN_PARTS for part in relative.parts):
        raise PackageError(f"forbidden tracked runtime path: {relative_text}")
    if relative.suffix in FORBIDDEN_SUFFIXES or relative.name == ".DS_Store":
        raise PackageError(f"forbidden tracked runtime file: {relative_text}")
    return relative


def frozen_release_files(root: Path, commit: str) -> list[FrozenFile]:
    """Read each release byte once from ``commit``, never from the worktree."""

    raw = run_git(root, "ls-tree", "-r", "-z", commit, text=False)
    assert isinstance(raw, bytes)
    files: list[FrozenFile] = []
    seen: set[str] = set()
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            metadata, encoded_path = record.split(b"\t", 1)
            mode_bytes, object_type, object_id = metadata.split(b" ", 2)
            relative_text = encoded_path.decode("utf-8")
            mode_text = mode_bytes.decode("ascii")
            object_text = object_id.decode("ascii")
        except (UnicodeDecodeError, ValueError) as exc:
            raise PackageError("Git tree contains an undecodable entry") from exc
        if any(
            part in CONTROL_PLANE_PARTS for part in PurePosixPath(relative_text).parts
        ):
            continue
        relative = validate_relative_path(relative_text)
        if relative.as_posix() in seen:
            raise PackageError(f"duplicate tracked path: {relative_text}")
        seen.add(relative.as_posix())
        if object_type != b"blob" or mode_text not in ALLOWED_GIT_MODES:
            raise PackageError(
                f"tracked entry is not a regular distributable file: {relative_text}"
            )
        data = run_git(root, "cat-file", "blob", object_text, text=False)
        assert isinstance(data, bytes)
        if (
            hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
            != object_text
        ):
            raise PackageError(f"Git blob verification failed: {relative_text}")
        files.append(
            FrozenFile(
                data=data,
                git_object=object_text,
                mode=ALLOWED_GIT_MODES[mode_text],
                name=relative.as_posix(),
            )
        )
    if not files:
        raise PackageError("Git tree contains no tracked release files")
    return sorted(files, key=lambda item: item.name)


def _release_evidence(files: dict[str, FrozenFile], relative: str) -> dict[str, str]:
    try:
        item = files[relative]
    except KeyError as exc:
        raise PackageError(
            f"prax-teach-v2 release gate failed: missing committed evidence {relative}"
        ) from exc
    return {"path": relative, "sha256": sha256(item.data)}


def _declares_prax_teach_v2(skill: FrozenFile | None) -> bool:
    """Recognize the candidate name inside a closed YAML frontmatter block."""

    if skill is None:
        return False
    try:
        lines = skill.data.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        return False
    if not lines or lines[0] != "---":
        return False
    try:
        end = lines.index("---", 1)
    except ValueError:
        return False
    for line in lines[1:end]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip() == "name" and value.strip().strip("\"'") == "prax-teach-v2":
            return True
    return False


def _verified_manifest_matches_head(document: Any, files: list[FrozenFile]) -> bool:
    """Bind the verifier's worktree manifest to distributable HEAD content."""

    if not isinstance(document, dict) or not isinstance(document.get("files"), list):
        return False
    actual: dict[str, tuple[int, str]] = {}
    for item in document["files"]:
        if not isinstance(item, dict):
            return False
        path = item.get("path")
        digest = item.get("sha256")
        mode_text = item.get("mode")
        if (
            not isinstance(path, str)
            or path in actual
            or not isinstance(digest, str)
            or not isinstance(mode_text, str)
        ):
            return False
        try:
            worktree_mode = int(mode_text, 8)
        except ValueError:
            return False
        git_mode = 0o755 if worktree_mode & 0o111 else 0o644
        actual[path] = (git_mode, digest)
    expected = {
        item.name: (item.mode, sha256(item.data))
        for item in files
        if item.name != FULL_VERIFICATION
        and not any(
            part in PRUNED_DIRECTORIES or part.endswith(("_cache", "-cache"))
            for part in PurePosixPath(item.name).parts[:-1]
        )
    }
    return actual == expected


def candidate_release_gate(
    root: Path, files: list[FrozenFile]
) -> dict[str, Any] | None:
    """Validate release evidence against the immutable commit being archived."""

    frozen_by_name = {item.name: item for item in files}
    if not _declares_prax_teach_v2(frozen_by_name.get("SKILL.md")):
        return None

    # Import the canonical validators, then run them over a private tree made
    # only from the exact Git blobs below.  The mutable worktree is never a
    # source of receipt bytes for this release decision.
    from validate_workspace import (
        _frontmatter_fields,
        validate_independent_review_receipts,
        validate_verification_receipt,
    )

    del root
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="prax-release-validate-") as temporary:
        validation_root = Path(temporary).resolve(strict=True)
        for item in files:
            destination = validation_root.joinpath(*PurePosixPath(item.name).parts)
            destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            destination.write_bytes(item.data)
            destination.chmod(item.mode)
        fields, frontmatter_errors = _frontmatter_fields(
            validation_root / "SKILL.md", validation_root
        )
        errors.extend(frontmatter_errors)
        if fields.get("name") != "prax-teach-v2":
            errors.append("SKILL.md: name must be 'prax-teach-v2'")
        review_count, review_errors = validate_independent_review_receipts(
            validation_root
        )
        verification_count, verification_errors = validate_verification_receipt(
            validation_root
        )
        errors.extend(review_errors)
        errors.extend(verification_errors)
        if review_count != len(REVIEW_TYPES):
            errors.append(
                f"independent reviews: expected {len(REVIEW_TYPES)}, "
                f"found {review_count}"
            )
        if verification_count != 1:
            errors.append(
                f"full verification: expected 1 receipt, found {verification_count}"
            )

    try:
        full_receipt = json.loads(frozen_by_name[FULL_VERIFICATION].data)
    except (KeyError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"{FULL_VERIFICATION}: missing or invalid: {exc}")
        full_receipt = None
    if isinstance(full_receipt, dict):
        if full_receipt.get("status") != "passed":
            errors.append(f"{FULL_VERIFICATION}: status must be passed")
        if full_receipt.get("level") != "full":
            errors.append(f"{FULL_VERIFICATION}: level must be full")
        if full_receipt.get("trusted_macos_sandbox_tests_required") is not True:
            errors.append(
                f"{FULL_VERIFICATION}: trusted macOS sandbox tests must be required"
            )
        if not _verified_manifest_matches_head(
            full_receipt.get("root_manifest"), files
        ):
            errors.append(
                f"{FULL_VERIFICATION}: verified release content is not exact HEAD"
            )

    try:
        review_payload = json.loads(frozen_by_name[REVIEW_PAYLOAD].data)
        reviewed_names = {
            item["path"]
            for item in review_payload["files"]
            if isinstance(item, dict) and isinstance(item.get("path"), str)
        }
    except (KeyError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"{REVIEW_PAYLOAD}: missing or invalid inventory: {exc}")
        reviewed_names = set()
    allowed_additions = {
        REVIEW_PAYLOAD,
        FULL_VERIFICATION,
        *(f"evidence/reviews/{review_type}.json" for review_type in REVIEW_TYPES),
    }
    expected_inventory = reviewed_names | allowed_additions
    actual_inventory = set(frozen_by_name)
    if actual_inventory != expected_inventory:
        missing = sorted(expected_inventory - actual_inventory)
        unexpected = sorted(actual_inventory - expected_inventory)
        errors.append(
            "archive inventory must equal the reviewed payload plus exact review "
            f"and full-verification receipts (missing={missing}, unexpected={unexpected})"
        )

    required_paths = [
        REVIEW_PAYLOAD,
        FULL_VERIFICATION,
        *(f"evidence/reviews/{review_type}.json" for review_type in REVIEW_TYPES),
    ]
    evidence: dict[str, dict[str, str]] = {}
    for relative in required_paths:
        try:
            evidence[relative] = _release_evidence(frozen_by_name, relative)
        except PackageError as exc:
            errors.append(str(exc).removeprefix("prax-teach-v2 release gate failed: "))

    if errors:
        joined = "; ".join(sorted(set(errors)))
        raise PackageError(f"prax-teach-v2 release gate failed: {joined}")

    return {
        "schema_version": 1,
        "policy": "prax-teach-v2-reviewed-full",
        "receipt_validation_source": "immutable_git_blobs",
        "immutable_review_payload": evidence[REVIEW_PAYLOAD],
        "full_verification": evidence[FULL_VERIFICATION],
        "independent_reviews": {
            review_type: evidence[f"evidence/reviews/{review_type}.json"]
            for review_type in REVIEW_TYPES
        },
    }


def zip_timestamp(epoch: str) -> tuple[int, int, int, int, int, int]:
    if not epoch.isdigit():
        raise PackageError("SOURCE_DATE_EPOCH must be a non-negative integer")
    instant = datetime.fromtimestamp(int(epoch), tz=timezone.utc)
    if instant.year < 1980:
        instant = datetime(1980, 1, 1, tzinfo=timezone.utc)
    return (
        instant.year,
        instant.month,
        instant.day,
        instant.hour,
        instant.minute,
        instant.second - instant.second % 2,
    )


def entry(
    name: str, timestamp: tuple[int, int, int, int, int, int], mode: int
) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=timestamp)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (mode & 0xFFFF) << 16
    info.flag_bits |= 0x800
    return info


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _outside_candidate(root: Path, output: Path) -> None:
    """Reject the exact unresolved output leaf when it is inside ``root``."""

    try:
        output.relative_to(root)
    except ValueError:
        return
    raise PackageError("release archive must be outside the candidate tree")


def _prepare_release_output(output: Path, *, create_missing: bool) -> Path:
    absolute = Path(os.path.abspath(output.expanduser()))
    try:
        return prepare_private_parent(absolute, create_missing=create_missing)
    except (SafetyError, ValidationError) as exc:
        raise PackageError(str(exc)) from exc


def _validate_output_leaf(output: Path, *, force: bool) -> None:
    try:
        output_stat = output.lstat()
    except FileNotFoundError:
        return
    if stat.S_ISLNK(output_stat.st_mode):
        raise PackageError("release output must not be a symlink")
    if not stat.S_ISREG(output_stat.st_mode):
        raise PackageError("existing output must be a regular non-symlink file")
    if not force:
        raise PackageError(
            "output already exists; pass --force to replace that exact file"
        )


def _publish_archive(temporary: Path, output: Path, *, force: bool) -> None:
    """Publish atomically; only ``force`` may replace an existing leaf."""

    if force:
        os.replace(temporary, output)
        return
    try:
        os.link(temporary, output, follow_symlinks=False)
    except FileExistsError as exc:
        raise PackageError(
            "output already exists; pass --force to replace that exact file"
        ) from exc
    except OSError as exc:
        raise PackageError("could not atomically publish the release archive") from exc
    try:
        temporary.unlink()
    except OSError as exc:
        # Publication already succeeded.  Report the cleanup failure instead of
        # pretending the temporary name was removed.
        raise PackageError("release published but temporary cleanup failed") from exc


def build_package(
    root: Path, output: Path, *, force: bool, epoch: str
) -> dict[str, Any]:
    root = root.expanduser().resolve(strict=True)
    if not (root / ".git").is_dir():
        raise PackageError(
            "candidate-local Git repository is required before packaging"
        )

    preflight_output = _prepare_release_output(
        output.expanduser(), create_missing=False
    )
    _outside_candidate(root, preflight_output)
    _validate_output_leaf(preflight_output, force=force)

    dirty = run_git(root, "status", "--porcelain=v1", "--untracked-files=all")
    assert isinstance(dirty, str)
    if dirty:
        raise PackageError("candidate Git tree must be clean before packaging")
    commit = run_git(root, "rev-parse", "HEAD")
    assert isinstance(commit, str)
    commit = commit.strip()
    if not re_fullmatch_sha1(commit):
        raise PackageError("could not resolve the reviewed commit")

    timestamp = zip_timestamp(epoch)
    files = frozen_release_files(root, commit)
    release_gate = candidate_release_gate(root, files)
    file_hashes = {item.name: sha256(item.data) for item in files}
    git_objects = {item.name: item.git_object for item in files}
    manifest_document: dict[str, Any] = {
        "commit": commit,
        "files": file_hashes,
        "git_blobs": git_objects,
        "schema_version": 1,
        "source_date_epoch": epoch,
    }
    if release_gate is not None:
        manifest_document["release_gate"] = release_gate
    manifest = stable_json(manifest_document)

    output = _prepare_release_output(output.expanduser(), create_missing=True)
    if output != preflight_output:
        raise PackageError("release output path changed while it was being prepared")
    _outside_candidate(root, output)
    _validate_output_leaf(output, force=force)
    archive_digest: str | None = None
    temporary_identity: tuple[int, int] | None = None
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w+b",
            prefix=f".{output.name}.",
            suffix=".tmp",
            dir=output.parent,
            delete=False,
        ) as temporary_handle:
            temporary_path = Path(temporary_handle.name)
            os.chmod(temporary_path, 0o600)
            temporary_stat = os.fstat(temporary_handle.fileno())
            temporary_identity = (temporary_stat.st_dev, temporary_stat.st_ino)
            with zipfile.ZipFile(
                temporary_handle,
                "w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=9,
                strict_timestamps=True,
            ) as archive:
                for item in files:
                    archive.writestr(
                        entry(f"prax-teach-v2/{item.name}", timestamp, item.mode),
                        item.data,
                    )
                archive.writestr(
                    entry("prax-teach-v2/PACKAGE-MANIFEST.json", timestamp, 0o644),
                    manifest,
                )
            temporary_handle.flush()
            os.fsync(temporary_handle.fileno())
            temporary_handle.seek(0)
            with zipfile.ZipFile(temporary_handle, "r") as archive:
                corrupt = archive.testzip()
                if corrupt:
                    raise PackageError(f"archive CRC verification failed at {corrupt}")
                names = archive.namelist()
                expected_names = [
                    *(f"prax-teach-v2/{item.name}" for item in files),
                    "prax-teach-v2/PACKAGE-MANIFEST.json",
                ]
                if names != expected_names or len(names) != len(set(names)):
                    raise PackageError(
                        "archive inventory does not exactly match frozen Git blobs"
                    )
                if any(".git" in PurePosixPath(name).parts for name in names):
                    raise PackageError("archive unexpectedly contains Git metadata")
                for item in files:
                    archived = archive.read(f"prax-teach-v2/{item.name}")
                    if (
                        archived != item.data
                        or sha256(archived) != file_hashes[item.name]
                    ):
                        raise PackageError(f"archive content mismatch: {item.name}")
                archived_manifest = json.loads(
                    archive.read("prax-teach-v2/PACKAGE-MANIFEST.json")
                )
                if archived_manifest != manifest_document:
                    raise PackageError(
                        "archive manifest does not match frozen Git blobs"
                    )
            temporary_handle.seek(0)
            archive_digest = sha256(temporary_handle.read())

        post_commit = run_git(root, "rev-parse", "HEAD")
        post_dirty = run_git(root, "status", "--porcelain=v1", "--untracked-files=all")
        assert isinstance(post_commit, str) and isinstance(post_dirty, str)
        if post_commit.strip() != commit or post_dirty:
            raise PackageError("Git tree changed while the archive was being built")
        final_output = _prepare_release_output(output, create_missing=False)
        if final_output != output:
            raise PackageError("release output path changed while building the archive")
        _outside_candidate(root, final_output)
        _validate_output_leaf(final_output, force=force)
        assert temporary_path is not None and temporary_identity is not None
        temporary_stat = temporary_path.lstat()
        if (
            not stat.S_ISREG(temporary_stat.st_mode)
            or (
                temporary_stat.st_dev,
                temporary_stat.st_ino,
            )
            != temporary_identity
        ):
            raise PackageError("temporary archive changed before publication")
        _publish_archive(temporary_path, output, force=force)
        temporary_path = None
        _fsync_directory(output.parent)
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass

    assert archive_digest is not None
    result = {
        "archive": str(output),
        "archive_sha256": archive_digest,
        "commit": commit,
        "entries": len(files) + 1,
        "git_metadata_included": False,
        "schema_version": 1,
        "source": "immutable_git_blobs",
        "status": "packaged",
    }
    if release_gate is not None:
        result["release_gate"] = "passed"
    return result


def re_fullmatch_sha1(value: str) -> bool:
    return len(value) == 40 and all(
        character in "0123456789abcdef" for character in value
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--project-root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    payload = build_package(
        args.project_root,
        args.output,
        force=args.force,
        epoch=os.environ.get("SOURCE_DATE_EPOCH", "1785844800"),
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, PackageError) as exc:
        print(f"package error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
