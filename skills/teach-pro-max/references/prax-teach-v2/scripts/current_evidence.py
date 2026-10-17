#!/usr/bin/env python3
"""Explicit external evidence selection; the trusted caller pins its SHA-256.

No discovery by age or receipt status. A pending descriptor is generation-only;
only an active full verifier may consume its unhashed full receipt. Deployment
publishes <root>.current-evidence.json beside the attested source directory.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import tarfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from review_payload import PayloadError, payload_manifest, read_stable_regular

SCHEMA = "prax.current-evidence/v1"
BASELINE_COMMIT = "286a98fc67486fa91bb19f34a9c0be347f5db029"
BASELINE_TREE = "3491a07778364500f494b3e9ef571a055838524a"
ROLES = {
    "runtime": "runtime.json",
    "payload": "payload.json",
    "code-standards": "code-standards.json",
    "frozen-spec": "frozen-spec.json",
    "architecture-council": "architecture-council.json",
    "full": "full.json",
    "browser": "browser.json",
}
TOOLS = (
    "scripts/current_evidence.py",
    "scripts/verify_visual_runtime.py",
    "scripts/prax_teach.py",
    "scripts/verify.py",
    "scripts/validate_workspace.py",
    "scripts/build_package.py",
    "scripts/review_payload.py",
    "scripts/render_all.mjs",
    "scripts/render_markdown.mjs",
    "scripts/praxteach/routing.py",
    "scripts/praxteach/visual_verify.py",
    "scripts/praxteach/io.py",
    "scripts/praxteach/errors.py",
    "scripts/praxteach/__init__.py",
)
HISTORICAL_PREFIXES = ("evidence/", "historical/", "fixtures/visual-verification/")


class EvidenceError(ValueError):
    """Selected evidence is absent, unsafe, stale or untrusted."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_absolute(path: Path) -> Path:
    path = Path(os.path.abspath(path.expanduser()))
    for component in (path, *path.parents):
        if component.is_symlink():
            raise EvidenceError(f"evidence path has a symlink component: {component}")
    return path


def _read(path: Path, *, maximum: int = 16 * 1024 * 1024) -> bytes:
    try:
        return read_stable_regular(_safe_absolute(path), maximum=maximum)
    except (OSError, PayloadError) as exc:
        raise EvidenceError(f"missing or unsafe evidence: {path}: {exc}") from exc


def _mode(path: Path) -> str:
    try:
        metadata = _safe_absolute(path).lstat()
    except OSError as exc:
        raise EvidenceError(f"missing historical file mode: {path}: {exc}") from exc
    return "0755" if metadata.st_mode & 0o111 else "0644"


def _decode_json(data: bytes, path: Path) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise EvidenceError(f"duplicate evidence field: {key}")
            result[key] = value
        return result

    if len(data) > 16 * 1024 * 1024:
        raise EvidenceError("evidence JSON exceeds size bound")
    try:
        return json.loads(data, object_pairs_hook=pairs)
    except (UnicodeError, ValueError) as exc:
        raise EvidenceError(f"malformed evidence: {path}: {exc}") from exc


def _json(path: Path) -> Any:
    return _decode_json(_read(path), path)


def _sha(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _relative(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise EvidenceError("evidence relative path missing")
    parsed = PurePosixPath(value)
    if parsed.is_absolute() or ".." in parsed.parts or parsed.as_posix() != value:
        raise EvidenceError(f"unsafe evidence relative path: {value}")
    return value


def git_inventory_tree(files: list[dict[str, Any]]) -> str:
    """Reconstruct the original Git tree, binding complete paths, modes and blobs."""
    tree: dict[str, Any] = {}
    for item in files:
        parts = PurePosixPath(_relative(item["path"])).parts
        directory = tree
        for part in parts[:-1]:
            child = directory.setdefault(part, {})
            if not isinstance(child, dict):
                raise EvidenceError(
                    "historical inventory has a file/directory collision"
                )
            directory = child
        if parts[-1] in directory:
            raise EvidenceError("historical inventory has duplicate paths")
        directory[parts[-1]] = (
            "100755" if item["mode"] == "0755" else "100644",
            item["git_object"],
        )

    def object_id(directory: dict[str, Any]) -> str:
        records = []
        for name, value in directory.items():
            if isinstance(value, dict):
                records.append((name + "/", "40000", name, object_id(value)))
            else:
                records.append((name, value[0], name, value[1]))
        content = b"".join(
            mode.encode() + b" " + name.encode() + b"\0" + bytes.fromhex(oid)
            for _, mode, name, oid in sorted(records)
        )
        return hashlib.sha1(
            b"tree " + str(len(content)).encode() + b"\0" + content
        ).hexdigest()

    return object_id(tree)


@dataclass(frozen=True)
class CurrentEvidence:
    root: Path
    path: Path
    document: dict[str, Any]
    selection_sha256: str
    allow_pending: bool = False

    def receipt_path(self, role: str) -> Path:
        return self.path.parent / self.document["receipts"][role]["path"]

    def receipt(self, role: str) -> Any:
        record = self.document["receipts"][role]
        path = self.receipt_path(role)
        data = _read(path)
        if record["sha256"] is None:
            if not (
                self.allow_pending
                and role == "full"
                and os.environ.get("PRAX_ACTIVE_VERIFICATION_RUN_ID")
            ):
                raise EvidenceError(
                    f"unhashed {role} receipt cannot establish eligibility"
                )
        elif digest(data) != record["sha256"]:
            raise EvidenceError(f"{role} receipt digest mismatch")
        return _decode_json(data, path)

    def historical_root(self) -> Path:
        history = self.document["historical"]
        root = _safe_absolute(Path(history["root"]))
        inventory_path = self.path.parent / history["inventory"]
        inventory_bytes = _read(inventory_path)
        if digest(inventory_bytes) != history["sha256"]:
            raise EvidenceError("historical inventory digest mismatch")
        inventory = _decode_json(inventory_bytes, inventory_path)
        if (
            not isinstance(inventory, dict)
            or set(inventory) != {"commit", "tree", "files"}
            or inventory.get("commit") != BASELINE_COMMIT
            or inventory.get("tree") != BASELINE_TREE
            or not isinstance(inventory.get("files"), list)
        ):
            raise EvidenceError("historical inventory is not the frozen original")
        seen: set[str] = set()
        for item in inventory["files"]:
            if not isinstance(item, dict) or set(item) != {
                "path",
                "sha256",
                "mode",
                "git_object",
            }:
                raise EvidenceError("malformed historical inventory entry")
            relative = _relative(item["path"])
            if (
                relative in seen
                or not _sha(item["sha256"])
                or item["mode"] not in {"0644", "0755"}
                or not isinstance(item["git_object"], str)
                or re.fullmatch(r"[0-9a-f]{40}", item["git_object"]) is None
            ):
                raise EvidenceError("invalid historical inventory entry")
            seen.add(relative)
            if _mode(root / relative) != item["mode"]:
                raise EvidenceError(f"historical snapshot mode drift: {relative}")
            original_bytes = _read(root / relative)
            blob = hashlib.sha1(
                b"blob " + str(len(original_bytes)).encode() + b"\0" + original_bytes
            ).hexdigest()
            if blob != item["git_object"] or digest(original_bytes) != item["sha256"]:
                raise EvidenceError(f"historical snapshot drift: {relative}")
            if relative.startswith(HISTORICAL_PREFIXES):
                if digest(_read(self.root / relative)) != item["sha256"]:
                    raise EvidenceError(
                        f"protected historical bytes changed: {relative}"
                    )
                if _mode(self.root / relative) != item["mode"]:
                    raise EvidenceError(
                        f"protected historical mode changed: {relative}"
                    )
        if git_inventory_tree(inventory["files"]) != BASELINE_TREE:
            raise EvidenceError(
                "historical inventory differs from independently fixed original Git tree"
            )
        actual_paths: set[str] = set()
        for current_dir, directories, filenames in os.walk(root, followlinks=False):
            directories[:] = [
                name
                for name in directories
                if name
                not in {
                    ".git",
                    "node_modules",
                    ".venv",
                    "__pycache__",
                    ".pytest_cache",
                    ".ruff_cache",
                }
            ]
            for name in directories:
                if (Path(current_dir) / name).is_symlink():
                    raise EvidenceError(
                        "historical snapshot contains a directory symlink"
                    )
            actual_paths.update(
                (Path(current_dir) / name).relative_to(root).as_posix()
                for name in filenames
                if not name.endswith((".pyc", ".pyo"))
            )
        if actual_paths != seen:
            raise EvidenceError(
                "historical snapshot path set differs from original inventory"
            )
        if not set(TOOLS).issubset(seen | {"scripts/current_evidence.py"}):
            raise EvidenceError("historical inventory omits required original tools")
        return root

    def historical_path(self, relative: str) -> bool:
        return relative.startswith(HISTORICAL_PREFIXES)


def resolve_pin(root: Path) -> tuple[Path, str, dict[str, Any]] | None:
    """Bounded trusted metadata only; no source-tree hashing before deadline."""
    root = root.resolve()
    selected = os.environ.get("PRAX_CURRENT_EVIDENCE")
    expected = os.environ.get("PRAX_CURRENT_EVIDENCE_SHA256")
    if selected is None and expected is None:
        pin = root.with_name(root.name + ".current-evidence.json")
        if not pin.exists() and not pin.is_symlink():
            return None
        metadata = pin.lstat()
        parent_metadata = pin.parent.stat()
        if (
            metadata.st_uid != os.getuid()
            or metadata.st_mode & 0o022
            or parent_metadata.st_uid != os.getuid()
            or parent_metadata.st_mode & 0o022
        ):
            raise EvidenceError("deployed evidence pin must be owner-controlled")
        binding = _json(pin)
        if (
            not isinstance(binding, dict)
            or set(binding) != {"schema_version", "path", "sha256"}
            or binding.get("schema_version") != 1
        ):
            raise EvidenceError("malformed deployed evidence pin")
        selected, expected = binding["path"], binding["sha256"]
    if (
        not isinstance(selected, str)
        or not Path(selected).is_absolute()
        or not _sha(expected)
    ):
        raise EvidenceError(
            "current evidence requires an absolute selector and independently expected SHA-256"
        )
    path = _safe_absolute(Path(selected))
    if path.is_relative_to(root):
        raise EvidenceError("current evidence must be outside attested source")
    selection_bytes = _read(path, maximum=256 * 1024)
    if digest(selection_bytes) != expected:
        raise EvidenceError(
            "current selector digest mismatch (wrong or superseded selection)"
        )
    document = _decode_json(selection_bytes, path)
    if not isinstance(document, dict):
        raise EvidenceError("current selector must be an object")
    return path, expected, document


def trusted_route_verifier(root: Path) -> Path | None:
    pin = resolve_pin(root)
    if pin is None:
        return None
    _, _, document = pin
    if document.get("schema_version") != SCHEMA or document.get("state") != "final":
        raise EvidenceError("final current selection required for route eligibility")
    tools = document.get("tools")
    if not isinstance(tools, dict) or set(tools) != set(TOOLS):
        raise EvidenceError("route verification tool identities are incomplete")
    for relative in (
        "scripts/verify_visual_runtime.py",
        "scripts/current_evidence.py",
        "scripts/review_payload.py",
        "scripts/praxteach/routing.py",
        "scripts/praxteach/io.py",
        "scripts/praxteach/errors.py",
        "scripts/praxteach/__init__.py",
    ):
        if tools[relative] != digest(_read(root / relative, maximum=1024 * 1024)):
            raise EvidenceError("route verification tool differs from trusted pin")
    return root / "scripts/verify_visual_runtime.py"


def resolve_current(
    root: Path, *, allow_pending: bool = False
) -> CurrentEvidence | None:
    root = root.resolve()
    pin = resolve_pin(root)
    if pin is None:
        return None
    path, expected, document = pin
    keys = {
        "schema_version",
        "state",
        "source_sha256",
        "tools",
        "receipts",
        "historical",
    }
    if (
        not isinstance(document, dict)
        or set(document) != keys
        or document.get("schema_version") != SCHEMA
    ):
        raise EvidenceError("current selector does not match exact schema")
    if document.get("state") not in {"pending", "final"} or (
        document["state"] != "final" and not allow_pending
    ):
        raise EvidenceError("pending evidence cannot establish eligibility")
    try:
        source = payload_manifest(root)["sha256"]
    except (OSError, PayloadError) as exc:
        raise EvidenceError(f"source inventory cannot be verified: {exc}") from exc
    if document.get("source_sha256") != source:
        raise EvidenceError("selected evidence is for different source bytes")
    expected_tools = {relative: digest(_read(root / relative)) for relative in TOOLS}
    if document.get("tools") != expected_tools:
        raise EvidenceError("selected evidence is for different verification tools")
    receipts = document.get("receipts")
    if not isinstance(receipts, dict) or set(receipts) != set(ROLES):
        raise EvidenceError("selected evidence roles are incomplete")
    for role, filename in ROLES.items():
        record = receipts[role]
        if (
            not isinstance(record, dict)
            or set(record) != {"path", "sha256"}
            or record.get("path") != filename
        ):
            raise EvidenceError(f"invalid {role} receipt selection")
        if not _sha(record.get("sha256")) and not (
            allow_pending
            and document["state"] == "pending"
            and role == "full"
            and record.get("sha256") is None
        ):
            raise EvidenceError(f"{role} receipt needs an independently pinned digest")
    history = document.get("historical")
    if (
        not isinstance(history, dict)
        or set(history) != {"root", "inventory", "sha256", "commit"}
        or history.get("commit") != BASELINE_COMMIT
        or not isinstance(history.get("root"), str)
        or not Path(history["root"]).is_absolute()
        or not _sha(history.get("sha256"))
    ):
        raise EvidenceError("invalid original historical inventory selection")
    _relative(history["inventory"])
    result = CurrentEvidence(root, path, document, expected, allow_pending)
    for role in ROLES:
        if role == "full" and document["state"] == "pending":
            continue
        if not isinstance(result.receipt(role), dict):
            raise EvidenceError(f"{role} receipt must be an object")
    return result


def export_original(
    source_repository: Path, destination: Path, inventory_path: Path
) -> dict[str, Any]:
    """Materialize the fixed original Git tree; never use current worktree bytes."""
    destination = _safe_absolute(destination)
    if destination.exists():
        raise EvidenceError("historical snapshot destination must be new")
    repository = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=source_repository,
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    if repository.returncode:
        raise EvidenceError("original Git repository is unavailable")
    completed = subprocess.run(
        ["git", "archive", "--format=tar", BASELINE_TREE],
        cwd=Path(repository.stdout.strip()),
        capture_output=True,
        check=False,
        timeout=60,
    )
    if completed.returncode:
        raise EvidenceError("original immutable Git tree is unavailable")
    files = []
    with tarfile.open(fileobj=io.BytesIO(completed.stdout)) as archive:
        for member in archive:
            if member.isdir():
                continue
            relative = _relative(member.name)
            if not member.isfile():
                raise EvidenceError("original tree contains a nonregular entry")
            handle = archive.extractfile(member)
            assert handle is not None
            data = handle.read()
            mode = "0755" if member.mode & 0o111 else "0644"
            files.append(
                {
                    "path": relative,
                    "mode": mode,
                    "sha256": digest(data),
                    "git_object": hashlib.sha1(
                        b"blob " + str(len(data)).encode() + b"\0" + data
                    ).hexdigest(),
                }
            )
    if git_inventory_tree(files) != BASELINE_TREE:
        raise EvidenceError("original export does not reproduce the fixed Git tree")
    destination.mkdir(mode=0o700, parents=True)
    with tarfile.open(fileobj=io.BytesIO(completed.stdout)) as archive:
        for member in archive:
            if member.isdir():
                continue
            target = destination / member.name
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            handle = archive.extractfile(member)
            assert handle is not None
            target.write_bytes(handle.read())
            target.chmod(0o755 if member.mode & 0o111 else 0o644)
    document = {
        "commit": BASELINE_COMMIT,
        "tree": BASELINE_TREE,
        "files": sorted(files, key=lambda item: item["path"]),
    }
    from review_payload import atomic_write_json

    atomic_write_json(_safe_absolute(inventory_path), document)
    return document


def write_selection(
    root: Path,
    directory: Path,
    history_root: Path,
    inventory: Path,
    *,
    pending: bool = False,
) -> dict[str, Any]:
    """Generate selection data after source freeze; this never grants acceptance."""
    root = root.resolve()
    directory = _safe_absolute(directory)
    if directory.is_relative_to(root):
        raise EvidenceError("selection directory must be external")
    receipts = {}
    for role, filename in ROLES.items():
        receipt_path = directory / filename
        value = None if pending and role == "full" else digest(_read(receipt_path))
        receipts[role] = {"path": filename, "sha256": value}
    inventory = _safe_absolute(inventory)
    if not inventory.is_relative_to(directory):
        raise EvidenceError("historical inventory must be in selection directory")
    document = {
        "schema_version": SCHEMA,
        "state": "pending" if pending else "final",
        "source_sha256": payload_manifest(root)["sha256"],
        "tools": {relative: digest(_read(root / relative)) for relative in TOOLS},
        "receipts": receipts,
        "historical": {
            "root": str(_safe_absolute(history_root)),
            "inventory": inventory.relative_to(directory).as_posix(),
            "sha256": digest(_read(inventory)),
            "commit": BASELINE_COMMIT,
        },
    }
    from review_payload import atomic_write_json

    target = directory / ("selection-pending.json" if pending else "selection.json")
    atomic_write_json(target, document)
    return {"path": str(target), "sha256": digest(_read(target))}


def add_selection_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--current-evidence", type=Path)
    parser.add_argument("--expected-evidence-sha256")


def apply_selection_arguments(args: argparse.Namespace) -> None:
    if args.current_evidence is not None or args.expected_evidence_sha256 is not None:
        if args.current_evidence is None or args.expected_evidence_sha256 is None:
            raise EvidenceError(
                "both selection path and independently expected digest are required"
            )
        os.environ["PRAX_CURRENT_EVIDENCE"] = str(args.current_evidence)
        os.environ["PRAX_CURRENT_EVIDENCE_SHA256"] = args.expected_evidence_sha256


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--companion-context", type=Path)
    parser.add_argument("--render-contexts", action="store_true")
    parser.add_argument("--write-selection", type=Path)
    parser.add_argument("--export-original", type=Path)
    parser.add_argument("--historical-root", type=Path)
    parser.add_argument("--historical-inventory", type=Path)
    parser.add_argument("--pending", action="store_true")
    args = parser.parse_args()
    try:
        if args.export_original:
            if args.historical_inventory is None:
                parser.error("original export needs --historical-inventory")
            export_original(args.root, args.export_original, args.historical_inventory)
            return 0
        if args.write_selection:
            if args.historical_root is None or args.historical_inventory is None:
                parser.error(
                    "selection generation needs --historical-root and --historical-inventory"
                )
            print(
                json.dumps(
                    write_selection(
                        args.root,
                        args.write_selection,
                        args.historical_root,
                        args.historical_inventory,
                        pending=args.pending,
                    )
                )
            )
            return 0
        current = resolve_current(
            args.root,
            allow_pending=bool(os.environ.get("PRAX_ACTIVE_VERIFICATION_RUN_ID")),
        )
        result: dict[str, Any] = {"current": current is not None}
        if args.render_contexts:
            if current:
                history_root = current.historical_root()
            else:
                history_root_text = os.environ.get("PRAX_HISTORICAL_ROOT")
                inventory_text = os.environ.get("PRAX_HISTORICAL_INVENTORY")
                history_root = None
                if history_root_text is not None or inventory_text is not None:
                    if not history_root_text or not inventory_text:
                        raise EvidenceError(
                            "historical preparation requires both snapshot and inventory paths"
                        )
                    inventory = _safe_absolute(Path(inventory_text))
                    # This is only historical companion preparation, never current
                    # eligibility. The fixed Git tree authenticates every entry.
                    preparation = CurrentEvidence(
                        args.root.resolve(),
                        inventory.parent / "preparation.json",
                        {
                            "historical": {
                                "root": history_root_text,
                                "inventory": inventory.name,
                                "sha256": digest(_read(inventory)),
                            }
                        },
                        "",
                        False,
                    )
                    history_root = preparation.historical_root()
            result.update(
                historical_root=str(history_root) if history_root else None,
                prefixes=HISTORICAL_PREFIXES,
            )
        if args.companion_context:
            relative = (
                args.companion_context.resolve()
                .relative_to(args.root.resolve())
                .as_posix()
            )
            historical = current is not None and current.historical_path(relative)
            context_root = (
                current.historical_root() if historical else args.root.resolve()
            )
            result.update(
                root=str(context_root),
                markdown=str(context_root / relative),
                renderer=str(context_root / "scripts/render_markdown.mjs"),
                historical=historical,
            )
        print(json.dumps(result))
        return 0
    except (EvidenceError, OSError, ValueError) as exc:
        print(str(exc), file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
