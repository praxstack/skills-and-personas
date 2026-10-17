#!/usr/bin/env python3
"""Run paired teaching-skill evaluations behind an explicit evidence boundary.

Treatment runs receive a read-only clone of the complete, manifest-defined
skill package.  An unconfined subprocess is allowed only when the caller opts
into public-fixture mode; those receipts are permanently ineligible for
held-out claims and do not assert hidden-bank nonexposure.  Self-authored
wrapper contracts are rejected.  On macOS, an internally generated,
deny-by-default sandbox-exec profile can establish claim-eligible isolation
only after same-invocation adversarial probes pass.  No mode is evidence of
human learning.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import random
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA_VERSION = 1
CANDIDATE_ROOT = Path(__file__).resolve().parents[1]
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_ARTIFACT_BYTES = 10 * 1024 * 1024
ALLOWED_CASE_KINDS = {"positive", "negative", "boundary"}
ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
PACKAGE_EXCLUDED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}
PACKAGE_EXCLUDED_NAMES = {".DS_Store"}
MACOS_SANDBOX_EXEC = Path("/usr/bin/sandbox-exec")
MACOS_PYTHON_FRAMEWORK = Path(
    "/Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework"
)
MACOS_PROBE_PYTHON = MACOS_PYTHON_FRAMEWORK / "Versions/3.9/bin/python3.9"
MACOS_SYSTEM_READ_ROOTS = (
    "/System",
    "/usr/lib",
    "/usr/share",
    "/Library/Apple",
    str(MACOS_PYTHON_FRAMEWORK),
    "/Applications/Xcode.app/Contents/Developer/usr/bin",
)
HARD_GATE_ORDER = (
    "artifact_path_escape",
    "source_integrity",
    "silent_persistence",
    "process_exit",
    "answer_leak",
    "input_integrity",
    "output_integrity",
    "workspace_cleanup",
)
RESULT_KEYS = {
    "receipt_version",
    "schema_version",
    "experiment_id",
    "run_id",
    "pair_id",
    "matrix_index",
    "case_id",
    "case_kind",
    "evaluation_scope",
    "trial",
    "arm",
    "spec_sha256",
    "target_package_sha256",
    "target_package_file_count",
    "condition_sha256",
    "prompt_sha256",
    "matrix_sha256",
    "runner_sha256",
    "runner_runtime_closure_sha256",
    "exit_code",
    "timed_out",
    "duration_ms",
    "token_usage",
    "response_sha256",
    "stdout_sha256",
    "stderr_sha256",
    "source_count",
    "sources_sha256",
    "artifact_count",
    "artifact_hashes",
    "failed_hard_gates",
    "hard_gates_passed",
    "soft_score",
    "success",
    "workspace_removed",
    "isolation_level",
    "isolation_contract_sha256",
    "isolation_verification_authority",
    "isolation_verification_evidence_sha256",
    "isolation_executor_sha256",
    "isolation_profile_sha256",
    "isolation_probes_sha256",
    "isolation_probes_passed",
    "hidden_bank_nonexposure_verified",
    "network_isolation_verified",
    "eligible_for_held_out_claims",
}


class ValidationError(Exception):
    """An input failed closed before an evaluation output was created."""


class MacOSSandboxUnavailable(Exception):
    """The built-in sandbox cannot be applied in the current parent sandbox."""


@dataclass(frozen=True)
class BoundFile:
    path: Path
    sha256: str
    identity: tuple[int, int]
    size: int


@dataclass(frozen=True)
class ValidatedSpec:
    document: dict[str, Any]
    path: Path
    file_sha256: str
    file_binding: BoundFile
    target_dir: Path
    skill_path: Path
    skill_bytes: bytes
    package_manifest: tuple[dict[str, Any], ...]
    package_files: dict[str, bytes]
    package_bindings: dict[str, BoundFile]
    package_sha256: str
    cases: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class ValidatedHiddenBank:
    document: dict[str, Any]
    path: Path
    file_sha256: str
    file_binding: BoundFile
    cases: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class IsolationBoundary:
    level: str
    eligible_for_held_out_claims: bool
    hidden_bank_nonexposure_verified: bool
    network_isolation_verified: bool
    contract_sha256: str | None
    verification_authority: str | None
    verification_evidence_sha256: str | None
    executor_path: Path | None
    executor_sha256: str | None


@dataclass(frozen=True)
class RunnerFingerprint:
    sha256: str
    tracked_files: tuple[BoundFile, ...]
    manifest_binding: BoundFile | None
    runtime_closure_sha256: str | None
    runtime_entry_count: int


def _evaluation_scope(spec: ValidatedSpec) -> str:
    eligibility = spec.document["eligibility"]
    if eligibility == "public_development_only":
        return "public_machinery_fixture"
    if eligibility == "containment_mechanism_only":
        return "containment_mechanism_fixture"
    return "candidate_quality_benchmark"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_bound_file(
    path: Path, label: str, *, maximum: int | None = None
) -> tuple[bytes, BoundFile]:
    """Read a regular file through one descriptor and bind its named identity."""

    unresolved = path.expanduser()
    try:
        if unresolved.is_symlink():
            raise ValidationError(f"{label} must be a regular, non-symlink file")
        resolved = unresolved.resolve(strict=True)
        descriptor = os.open(
            resolved,
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
    except (OSError, RuntimeError) as error:
        raise ValidationError(f"{label} does not exist or is unsafe") from error
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ValidationError(f"{label} must be a regular, non-symlink file")
        if maximum is not None and before.st_size > maximum:
            raise ValidationError(f"{label} exceeds the size limit")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            data = handle.read() if maximum is None else handle.read(maximum + 1)
        after = os.fstat(descriptor)
        named = resolved.lstat()
    except OSError as error:
        raise ValidationError(f"cannot read {label}") from error
    finally:
        os.close(descriptor)
    if maximum is not None and len(data) > maximum:
        raise ValidationError(f"{label} exceeds the size limit")
    identity = (before.st_dev, before.st_ino)
    if (
        (after.st_dev, after.st_ino) != identity
        or (named.st_dev, named.st_ino) != identity
        or after.st_size != before.st_size
        or named.st_size != before.st_size
        or not stat.S_ISREG(named.st_mode)
    ):
        raise ValidationError(f"{label} changed identity while it was read")
    return data, BoundFile(
        path=resolved,
        sha256=_sha256_bytes(data),
        identity=identity,
        size=len(data),
    )


def _binding_matches(binding: BoundFile, label: str) -> bool:
    try:
        _data, current = _read_bound_file(binding.path, label, maximum=binding.size)
    except ValidationError:
        return False
    return current == binding


def _reject_cross_aliases(
    left: list[tuple[str, BoundFile]], right: list[tuple[str, BoundFile]]
) -> None:
    for left_label, left_binding in left:
        for right_label, right_binding in right:
            if left_binding.identity == right_binding.identity:
                raise ValidationError(
                    f"{left_label} is a filesystem alias of protected {right_label}"
                )
            if (
                left_binding.size == right_binding.size
                and left_binding.sha256 == right_binding.sha256
            ):
                raise ValidationError(
                    f"{left_label} is a content alias of protected {right_label}"
                )


def _canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode("utf-8")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _decode_json(data: bytes, label: str) -> Any:
    if not data or len(data) > MAX_JSON_BYTES:
        raise ValidationError(f"{label} is empty or exceeds the size limit")
    try:
        return json.loads(
            data.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except UnicodeDecodeError as error:
        raise ValidationError(f"{label} must be UTF-8 JSON") from error
    except json.JSONDecodeError as error:
        raise ValidationError(f"{label} is malformed JSON") from error


def _read_json(path: Path, label: str) -> tuple[Any, bytes, BoundFile]:
    data, binding = _read_bound_file(path, label, maximum=MAX_JSON_BYTES)
    return _decode_json(data, label), data, binding


def _require_exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    missing = expected - value.keys()
    extra = value.keys() - expected
    if missing or extra:
        details: list[str] = []
        if missing:
            details.append("missing " + ", ".join(sorted(missing)))
        if extra:
            details.append("unexpected " + ", ".join(sorted(extra)))
        raise ValidationError(f"{label} has invalid fields ({'; '.join(details)})")


def _require_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
        raise ValidationError(f"{label} must be a stable identifier")
    return value


def _require_nonempty_string(value: Any, label: str, maximum: int = 100_000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValidationError(
            f"{label} must be a non-empty string within its size limit"
        )
    if "\x00" in value:
        raise ValidationError(f"{label} contains a NUL byte")
    return value


def _require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value):
        raise ValidationError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _is_within(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def _frontmatter_name(skill_bytes: bytes) -> str:
    try:
        text = skill_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValidationError("target SKILL.md must be UTF-8") from error
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValidationError("target SKILL.md must have YAML frontmatter")
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip("'\"")
    raise ValidationError("target SKILL.md frontmatter is missing name")


def _validate_json_value(value: Any, label: str, depth: int = 0) -> None:
    if depth > 4:
        raise ValidationError(f"{label} is nested too deeply")
    if value is None or isinstance(value, (bool, int, float, str)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValidationError(f"{label} contains a non-finite number")
        if isinstance(value, str):
            _require_nonempty_string(value, label, maximum=10_000)
        return
    if isinstance(value, list):
        if len(value) > 100:
            raise ValidationError(f"{label} contains too many values")
        for index, item in enumerate(value):
            _validate_json_value(item, f"{label}[{index}]", depth + 1)
        return
    if isinstance(value, dict):
        if len(value) > 100:
            raise ValidationError(f"{label} contains too many fields")
        for key, item in value.items():
            _require_id(key, f"{label} key")
            _validate_json_value(item, f"{label}.{key}", depth + 1)
        return
    raise ValidationError(f"{label} contains an unsupported value")


def _safe_manifest_relative(value: Any, label: str) -> str:
    text = _require_nonempty_string(value, label, 4096)
    try:
        path = PurePosixPath(text)
    except ValueError as error:
        raise ValidationError(f"{label} is not a valid package path") from error
    if (
        path.is_absolute()
        or text != path.as_posix()
        or "." in path.parts
        or ".." in path.parts
        or any("\x00" in part for part in path.parts)
    ):
        raise ValidationError(f"{label} must be a canonical relative package path")
    return text


def _package_path_is_excluded(relative: PurePosixPath) -> bool:
    return bool(
        PACKAGE_EXCLUDED_PARTS.intersection(relative.parts)
        or relative.name in PACKAGE_EXCLUDED_NAMES
        or relative.suffix == ".pyc"
    )


def _scan_package(
    root: Path, *, exclude_runtime: bool
) -> tuple[tuple[dict[str, Any], ...], dict[str, bytes], dict[str, BoundFile]]:
    """Read one immutable package snapshot and its canonical manifest."""

    manifest: list[dict[str, Any]] = []
    files: dict[str, bytes] = {}
    bindings: dict[str, BoundFile] = {}
    total_bytes = 0
    try:
        paths = sorted(
            root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()
        )
    except OSError as error:
        raise ValidationError("cannot enumerate target skill package") from error
    for path in paths:
        relative_path = path.relative_to(root)
        relative = PurePosixPath(relative_path.as_posix())
        if exclude_runtime and _package_path_is_excluded(relative):
            continue
        relative_text = _safe_manifest_relative(
            relative.as_posix(), "target package path"
        )
        try:
            metadata = path.lstat()
        except OSError as error:
            raise ValidationError("cannot stat target skill package") from error
        if stat.S_ISLNK(metadata.st_mode):
            raise ValidationError(
                f"target skill package contains a symlink: {relative_text}"
            )
        if stat.S_ISDIR(metadata.st_mode):
            continue
        if not stat.S_ISREG(metadata.st_mode):
            raise ValidationError(
                f"target skill package contains a special file: {relative_text}"
            )
        data, binding = _read_bound_file(
            path,
            f"target package file {relative_text}",
            maximum=MAX_ARTIFACT_BYTES,
        )
        total_bytes += len(data)
        if len(data) > MAX_ARTIFACT_BYTES or total_bytes > 100 * 1024 * 1024:
            raise ValidationError("target skill package exceeds the size limit")
        files[relative_text] = data
        bindings[relative_text] = binding
        manifest.append(
            {
                "path": relative_text,
                "sha256": _sha256_bytes(data),
                "size": len(data),
                "executable": bool(stat.S_IMODE(metadata.st_mode) & 0o111),
            }
        )
        if len(manifest) > 10_000:
            raise ValidationError("target skill package contains too many files")
    if "SKILL.md" not in files:
        raise ValidationError("target skill package must include SKILL.md")
    return tuple(manifest), files, bindings


def _validate_declared_manifest(value: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list) or not value or len(value) > 10_000:
        raise ValidationError("target_skill.manifest must be a non-empty file list")
    manifest: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, entry in enumerate(value):
        if not isinstance(entry, dict):
            raise ValidationError(f"target_skill.manifest[{index}] must be an object")
        _require_exact_keys(
            entry,
            {"path", "sha256", "size", "executable"},
            f"target_skill.manifest[{index}]",
        )
        relative = _safe_manifest_relative(
            entry["path"], f"target_skill.manifest[{index}].path"
        )
        if _package_path_is_excluded(PurePosixPath(relative)):
            raise ValidationError(
                "target_skill.manifest includes an excluded runtime file"
            )
        if relative in seen:
            raise ValidationError("target_skill.manifest contains a duplicate path")
        seen.add(relative)
        digest = _require_sha256(
            entry["sha256"], f"target_skill.manifest[{index}].sha256"
        )
        size = entry["size"]
        if (
            not isinstance(size, int)
            or isinstance(size, bool)
            or not 0 <= size <= MAX_ARTIFACT_BYTES
        ):
            raise ValidationError(f"target_skill.manifest[{index}].size is invalid")
        executable = entry["executable"]
        if not isinstance(executable, bool):
            raise ValidationError(
                f"target_skill.manifest[{index}].executable must be boolean"
            )
        manifest.append(
            {
                "path": relative,
                "sha256": digest,
                "size": size,
                "executable": executable,
            }
        )
    if [entry["path"] for entry in manifest] != sorted(seen):
        raise ValidationError("target_skill.manifest must be sorted by path")
    return tuple(manifest)


def _package_digest(manifest: tuple[dict[str, Any], ...]) -> str:
    return _sha256_bytes(_canonical_json(list(manifest)))


def _validate_spec(path: Path) -> ValidatedSpec:
    document, raw_bytes, spec_binding = _read_json(path, "experiment spec")
    resolved_path = spec_binding.path
    if not isinstance(document, dict):
        raise ValidationError("experiment spec must be a JSON object")
    _require_exact_keys(
        document,
        {
            "schema_version",
            "experiment_id",
            "eligibility",
            "target_skill",
            "design",
            "conditions",
            "cases",
        },
        "experiment spec",
    )
    if document["schema_version"] != SCHEMA_VERSION:
        raise ValidationError("unsupported experiment schema_version")
    _require_id(document["experiment_id"], "experiment_id")
    if document["eligibility"] not in {
        "public_development_only",
        "containment_mechanism_only",
        "held_out_external_evaluation",
    }:
        raise ValidationError("experiment eligibility is unsupported")

    target = document["target_skill"]
    if not isinstance(target, dict):
        raise ValidationError("target_skill must be an object")
    _require_exact_keys(
        target,
        {"name", "path", "package_sha256", "manifest"},
        "target_skill",
    )
    target_name = _require_id(target["name"], "target_skill.name")
    target_path_text = _require_nonempty_string(
        target["path"], "target_skill.path", 4096
    )
    declared_package_sha = _require_sha256(
        target["package_sha256"], "target_skill.package_sha256"
    )
    declared_manifest = _validate_declared_manifest(target["manifest"])
    unresolved_target = Path(target_path_text).expanduser()
    if not unresolved_target.is_absolute():
        unresolved_target = resolved_path.parent / unresolved_target
    try:
        target_dir = unresolved_target.resolve(strict=True)
    except OSError as error:
        raise ValidationError("target skill path does not exist") from error
    if not target_dir.is_dir() or unresolved_target.is_symlink():
        raise ValidationError("target skill path must be a non-symlink directory")
    actual_manifest, package_files, package_bindings = _scan_package(
        target_dir, exclude_runtime=True
    )
    _reject_cross_aliases(
        [("experiment spec", spec_binding)],
        [
            (f"target package file {relative}", binding)
            for relative, binding in package_bindings.items()
        ],
    )
    if actual_manifest != declared_manifest:
        raise ValidationError(
            "target package manifest does not match the complete package tree"
        )
    actual_package_sha = _package_digest(actual_manifest)
    if actual_package_sha != declared_package_sha:
        raise ValidationError("target package fingerprint does not match the spec")
    skill_path = target_dir / "SKILL.md"
    skill_bytes = package_files["SKILL.md"]
    if _frontmatter_name(skill_bytes) != target_name:
        raise ValidationError("target skill name does not match SKILL.md frontmatter")

    design = document["design"]
    if not isinstance(design, dict):
        raise ValidationError("design must be an object")
    _require_exact_keys(
        design,
        {"bootstrap_samples", "minimum_effect", "seed", "trials_per_arm"},
        "design",
    )
    if (
        not isinstance(design["bootstrap_samples"], int)
        or isinstance(design["bootstrap_samples"], bool)
        or not 100 <= design["bootstrap_samples"] <= 100_000
    ):
        raise ValidationError(
            "design.bootstrap_samples must be an integer from 100 to 100000"
        )
    minimum_effect = design["minimum_effect"]
    if (
        not isinstance(minimum_effect, (int, float))
        or isinstance(minimum_effect, bool)
        or not 0 <= minimum_effect <= 1
    ):
        raise ValidationError("design.minimum_effect must be between zero and one")
    if (
        not isinstance(design["seed"], int)
        or isinstance(design["seed"], bool)
        or not 0 <= design["seed"] <= 2**63 - 1
    ):
        raise ValidationError("design.seed must be a non-negative integer")
    if (
        not isinstance(design["trials_per_arm"], int)
        or isinstance(design["trials_per_arm"], bool)
        or not 1 <= design["trials_per_arm"] <= 50
    ):
        raise ValidationError("design.trials_per_arm must be an integer from 1 to 50")

    conditions = document["conditions"]
    if not isinstance(conditions, dict):
        raise ValidationError("conditions must be an object")
    for required in ("harness", "model", "network"):
        if required not in conditions:
            raise ValidationError(f"conditions is missing {required}")
    _require_nonempty_string(conditions["harness"], "conditions.harness", 1000)
    _require_nonempty_string(conditions["model"], "conditions.model", 1000)
    expected_network = (
        "unrestricted_unverified"
        if document["eligibility"] == "public_development_only"
        else "off"
    )
    if conditions["network"] != expected_network:
        raise ValidationError(
            f"evaluation condition network must be {expected_network} for this eligibility"
        )
    _validate_json_value(conditions, "conditions")

    case_list = document["cases"]
    if not isinstance(case_list, list) or not case_list or len(case_list) > 200:
        raise ValidationError("cases must be a non-empty list with at most 200 entries")
    cases: dict[str, dict[str, Any]] = {}
    for index, case in enumerate(case_list):
        if not isinstance(case, dict):
            raise ValidationError(f"cases[{index}] must be an object")
        _require_exact_keys(case, {"id", "kind", "prompt"}, f"cases[{index}]")
        case_id = _require_id(case["id"], f"cases[{index}].id")
        if case_id in cases:
            raise ValidationError(f"duplicate case id: {case_id}")
        if case["kind"] not in ALLOWED_CASE_KINDS:
            raise ValidationError(f"cases[{index}].kind is unsupported")
        _require_nonempty_string(case["prompt"], f"cases[{index}].prompt")
        cases[case_id] = case

    return ValidatedSpec(
        document=document,
        path=resolved_path,
        file_sha256=_sha256_bytes(raw_bytes),
        file_binding=spec_binding,
        target_dir=target_dir,
        skill_path=skill_path,
        skill_bytes=skill_bytes,
        package_manifest=actual_manifest,
        package_files=package_files,
        package_bindings=package_bindings,
        package_sha256=actual_package_sha,
        cases=cases,
    )


def _validate_string_list(value: Any, label: str, *, allow_empty: bool) -> list[str]:
    if (
        not isinstance(value, list)
        or (not allow_empty and not value)
        or len(value) > 200
    ):
        qualifier = "" if allow_empty else " non-empty"
        raise ValidationError(f"{label} must be a{qualifier} list of strings")
    result: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        text = _require_nonempty_string(item, f"{label}[{index}]", 10_000)
        folded = text.casefold()
        if folded in seen:
            raise ValidationError(f"{label} contains a duplicate value")
        seen.add(folded)
        result.append(text)
    return result


def _validate_hidden_bank(
    path: Path,
    spec: ValidatedSpec,
    output_dir: Path,
    expected_eligibility: str,
) -> ValidatedHiddenBank:
    document, raw_bytes, bank_binding = _read_json(path, "hidden bank")
    resolved_path = bank_binding.path
    output_resolved = output_dir.expanduser().resolve(strict=False)
    if _is_within(resolved_path, spec.target_dir):
        raise ValidationError("hidden bank must be external to the target skill")
    if _is_within(resolved_path, CANDIDATE_ROOT):
        raise ValidationError("hidden bank must be external to the candidate package")
    if _is_within(resolved_path, output_resolved):
        raise ValidationError("hidden bank must be external to the output directory")
    if not isinstance(document, dict):
        raise ValidationError("hidden bank must be a JSON object")
    _require_exact_keys(
        document,
        {"schema_version", "experiment_id", "eligibility", "cases"},
        "hidden bank",
    )
    if document["schema_version"] != SCHEMA_VERSION:
        raise ValidationError("unsupported hidden bank schema_version")
    if document["experiment_id"] != spec.document["experiment_id"]:
        raise ValidationError("hidden bank experiment_id does not match the spec")
    if document["eligibility"] != expected_eligibility:
        raise ValidationError(
            f"grader bank eligibility must be {expected_eligibility} for this mode"
        )
    raw_cases = document["cases"]
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValidationError("hidden bank cases must be a non-empty list")
    cases: dict[str, dict[str, Any]] = {}
    required_fields = {"id", "private_reference", "required_terms", "forbidden_terms"}
    optional_fields = {"required_sources", "forbidden_sources"}
    for index, case in enumerate(raw_cases):
        if not isinstance(case, dict):
            raise ValidationError(f"hidden bank case {index} must be an object")
        missing = required_fields - case.keys()
        extra = case.keys() - required_fields - optional_fields
        if missing or extra:
            raise ValidationError("hidden bank case has invalid fields")
        case_id = _require_id(case["id"], f"hidden cases[{index}].id")
        if case_id in cases:
            raise ValidationError("hidden bank contains duplicate case ids")
        _require_nonempty_string(
            case["private_reference"], f"hidden cases[{index}].private_reference"
        )
        _validate_string_list(
            case["required_terms"],
            f"hidden cases[{index}].required_terms",
            allow_empty=False,
        )
        _validate_string_list(
            case["forbidden_terms"],
            f"hidden cases[{index}].forbidden_terms",
            allow_empty=True,
        )
        for field in optional_fields & case.keys():
            _validate_string_list(
                case[field], f"hidden cases[{index}].{field}", allow_empty=True
            )
        cases[case_id] = case
    if set(cases) != set(spec.cases):
        raise ValidationError(
            "hidden bank case ids must exactly match the experiment cases"
        )
    _reject_cross_aliases(
        [("hidden bank", bank_binding)],
        [
            ("experiment spec", spec.file_binding),
            *(
                (f"target package file {relative}", binding)
                for relative, binding in spec.package_bindings.items()
            ),
        ],
    )
    return ValidatedHiddenBank(
        document=document,
        path=resolved_path,
        file_sha256=_sha256_bytes(raw_bytes),
        file_binding=bank_binding,
        cases=cases,
    )


def _public_fixture_boundary() -> IsolationBoundary:
    return IsolationBoundary(
        level="unconfined_public_fixture",
        eligible_for_held_out_claims=False,
        hidden_bank_nonexposure_verified=False,
        network_isolation_verified=False,
        contract_sha256=None,
        verification_authority=None,
        verification_evidence_sha256=None,
        executor_path=None,
        executor_sha256=None,
    )


def _trusted_macos_boundary() -> IsolationBoundary:
    if platform.system() != "Darwin":
        raise ValidationError("--macos-sandbox requires macOS")
    for path, label in (
        (MACOS_SANDBOX_EXEC, "sandbox-exec"),
        (MACOS_PROBE_PYTHON, "system Python probe runtime"),
    ):
        try:
            metadata = path.lstat()
        except OSError as error:
            raise ValidationError(f"trusted {label} is unavailable") from error
        if (
            path.is_symlink()
            or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != 0
            or stat.S_IMODE(metadata.st_mode) & 0o022
            or not os.access(path, os.X_OK)
        ):
            raise ValidationError(f"trusted {label} failed ownership/mode checks")
    return IsolationBoundary(
        level="builtin_macos_sandbox_exec",
        eligible_for_held_out_claims=True,
        hidden_bank_nonexposure_verified=False,
        network_isolation_verified=False,
        contract_sha256=None,
        verification_authority="builtin-macos-sandbox-exec",
        verification_evidence_sha256=None,
        executor_path=MACOS_SANDBOX_EXEC,
        executor_sha256=_sha256_file(MACOS_SANDBOX_EXEC),
    )


def _condition_sha(spec: ValidatedSpec, arm: str) -> str:
    condition = {
        "arm": arm,
        "conditions": spec.document["conditions"],
        "skill_input": spec.package_sha256 if arm == "treatment" else None,
    }
    return _sha256_bytes(_canonical_json(condition))


def _plan_rows(spec: ValidatedSpec) -> list[dict[str, Any]]:
    seed = spec.document["design"]["seed"]
    trials = spec.document["design"]["trials_per_arm"]
    pairs: list[tuple[str, int, str]] = []
    for case_id in spec.cases:
        for trial in range(1, trials + 1):
            material = f"{spec.document['experiment_id']}|{case_id}|{trial}"
            pair_id = "pair-" + hashlib.sha256(material.encode()).hexdigest()[:20]
            pairs.append((case_id, trial, pair_id))
    pairs.sort(
        key=lambda item: hashlib.sha256(
            f"{seed}|pair-order|{item[2]}".encode()
        ).digest()
    )
    rows: list[dict[str, Any]] = []
    for case_id, trial, pair_id in pairs:
        arm_digest = hashlib.sha256(f"{seed}|arm-order|{pair_id}".encode()).digest()
        arms = (
            ("control", "treatment")
            if arm_digest[0] % 2 == 0
            else ("treatment", "control")
        )
        case = spec.cases[case_id]
        for arm in arms:
            run_material = f"{pair_id}|{arm}|{spec.file_sha256}"
            rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "experiment_id": spec.document["experiment_id"],
                    "run_id": "run-"
                    + hashlib.sha256(run_material.encode()).hexdigest()[:24],
                    "pair_id": pair_id,
                    "matrix_index": len(rows),
                    "case_id": case_id,
                    "case_kind": case["kind"],
                    "trial": trial,
                    "arm": arm,
                    "spec_sha256": spec.file_sha256,
                    "target_package_sha256": spec.package_sha256,
                    "target_package_file_count": len(spec.package_manifest),
                    "condition_sha256": _condition_sha(spec, arm),
                    "prompt_sha256": _sha256_bytes(case["prompt"].encode("utf-8")),
                }
            )
    return rows


def _jsonl(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(_canonical_json(row) for row in rows)


def _atomic_write(path: Path, data: bytes) -> None:
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, path)
        try:
            directory_fd = os.open(parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            pass
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _validate_output_file(path: Path, protected: list[Path]) -> Path:
    unresolved = path.expanduser()
    absolute = unresolved if unresolved.is_absolute() else Path.cwd() / unresolved
    if absolute.is_symlink():
        raise ValidationError("output path must not be a symlink")

    # Resolve only the parent.  Resolving the complete path first would erase the
    # identity of a leaf symlink and make the subsequent atomic replace overwrite
    # the symlink target rather than the exact output path the caller named.
    exact = absolute.parent.resolve(strict=False) / absolute.name
    if exact.is_symlink():
        raise ValidationError("output path must not be a symlink")
    if exact.exists() and exact.is_dir():
        raise ValidationError("output path points to a directory")

    for item in protected:
        protected_path = item.expanduser().resolve(strict=True)
        if exact == protected_path:
            raise ValidationError("output path would overwrite an input")
        if protected_path.is_dir() and _is_within(exact, protected_path):
            raise ValidationError("output path must not be inside an input directory")
        if exact.exists() and protected_path.exists():
            try:
                aliases_input = os.path.samefile(exact, protected_path)
            except OSError:
                aliases_input = False
            if aliases_input:
                raise ValidationError("output path would overwrite an input alias")
    return exact


def _spec_input_paths(spec: ValidatedSpec) -> list[Path]:
    return [
        spec.path,
        spec.target_dir,
        *(spec.target_dir / item["path"] for item in spec.package_manifest),
    ]


def _parse_jsonl(
    path: Path, label: str
) -> tuple[list[dict[str, Any]], bytes, BoundFile]:
    raw, binding = _read_bound_file(path, label, maximum=MAX_JSON_BYTES * 4)
    if not raw or len(raw) > MAX_JSON_BYTES * 4:
        raise ValidationError(f"{label} is empty or too large")
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            raise ValidationError(f"{label} contains a blank line")
        value = _decode_json(line, f"{label} line {line_number}")
        if not isinstance(value, dict):
            raise ValidationError(f"{label} line {line_number} must be an object")
        rows.append(value)
    return rows, raw, binding


def _validate_matrix(
    path: Path, spec: ValidatedSpec
) -> tuple[list[dict[str, Any]], bytes, BoundFile]:
    rows, raw, binding = _parse_jsonl(path, "matrix")
    if rows != _plan_rows(spec):
        raise ValidationError(
            "matrix is incomplete, modified, duplicated, or fingerprint-mismatched"
        )
    return rows, raw, binding


def _validate_runner(
    value: str, spec: ValidatedSpec, bank: ValidatedHiddenBank
) -> list[str]:
    try:
        command = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValidationError("runner-json must be a JSON array") from error
    if (
        not isinstance(command, list)
        or not command
        or len(command) > 100
        or any(
            not isinstance(item, str) or not item or "\x00" in item for item in command
        )
    ):
        raise ValidationError("runner-json must be a non-empty array of safe strings")
    executable = Path(command[0]).expanduser()
    if not executable.is_absolute():
        located = shutil.which(command[0])
        if located is None:
            raise ValidationError("runner executable was not found")
        executable = Path(located)
    try:
        executable = executable.resolve(strict=True)
    except OSError as error:
        raise ValidationError("runner executable was not found") from error
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise ValidationError("runner executable is not an executable file")
    command[0] = str(executable)
    hidden_text = str(bank.path)
    target_text = str(spec.target_dir)
    hidden_values = [hidden_text]
    for case in bank.cases.values():
        hidden_values.append(case["private_reference"])
        for field in (
            "required_terms",
            "forbidden_terms",
            "required_sources",
            "forbidden_sources",
        ):
            hidden_values.extend(case.get(field, []))
    hidden_values_folded = [item.casefold() for item in hidden_values]
    for argument in command:
        folded_argument = argument.casefold()
        if any(value in folded_argument for value in hidden_values_folded):
            raise ValidationError(
                "runner command must not contain hidden bank material"
            )
        if target_text in argument:
            raise ValidationError(
                "runner command must not expose the target skill path"
            )
        candidate = Path(argument).expanduser()
        if candidate.is_absolute():
            resolved = candidate.resolve(strict=False)
            if _is_within(resolved, spec.target_dir):
                raise ValidationError(
                    "runner command must not expose the target skill path"
                )
        if target_text == argument:
            raise ValidationError(
                "runner command must not expose the target skill path"
            )
    return command


def _runner_file_entry(
    path: Path, label: str
) -> tuple[Path, dict[str, Any], BoundFile]:
    data, binding = _read_bound_file(path, label)
    return (
        binding.path,
        {
            "path": str(binding.path),
            "sha256": _sha256_bytes(data),
        },
        binding,
    )


def _controlled_python_runtime_closure() -> tuple[str, int]:
    try:
        root = MACOS_PYTHON_FRAMEWORK.resolve(strict=True)
    except OSError as error:
        raise ValidationError("controlled Python runtime is unavailable") from error
    current = root
    while True:
        metadata = current.lstat()
        mode = stat.S_IMODE(metadata.st_mode)
        # A stock macOS installation makes /Applications root-owned and
        # admin-group writable.  The evaluated process cannot exploit that
        # installer boundary because the generated sandbox grants writes only
        # below its private run root.  Everything at and below Xcode.app must
        # still be root-owned and non-writable, and the complete framework is
        # content-hashed before and after the runs.
        trusted_applications_boundary = (
            current == Path("/Applications")
            and metadata.st_uid == 0
            and not mode & stat.S_IWOTH
        )
        if (
            metadata.st_uid != 0
            or not stat.S_ISDIR(metadata.st_mode)
            or (mode & 0o022 and not trusted_applications_boundary)
        ):
            raise ValidationError(
                "controlled Python runtime has an unsafe owner or ancestor mode"
            )
        if current == Path(current.anchor):
            break
        current = current.parent

    entries: list[dict[str, Any]] = []
    for path in sorted(
        root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()
    ):
        relative = path.relative_to(root).as_posix()
        try:
            metadata = path.lstat()
        except OSError as error:
            raise ValidationError(
                "controlled Python runtime changed during scan"
            ) from error
        if metadata.st_uid != 0:
            raise ValidationError(
                "controlled Python runtime contains an untrusted owner"
            )
        mode = stat.S_IMODE(metadata.st_mode)
        if stat.S_ISLNK(metadata.st_mode):
            try:
                target = os.readlink(path)
                resolved = path.resolve(strict=True)
            except OSError as error:
                raise ValidationError(
                    "controlled Python runtime contains a broken symlink"
                ) from error
            if not _is_within(resolved, root):
                raise ValidationError(
                    "controlled Python runtime symlink escapes its measured root"
                )
            entries.append(
                {
                    "kind": "symlink",
                    "mode": f"{mode:04o}",
                    "path": relative,
                    "target": target,
                }
            )
        elif stat.S_ISDIR(metadata.st_mode):
            if mode & 0o022:
                raise ValidationError(
                    "controlled Python runtime contains a writable directory"
                )
            entries.append(
                {"kind": "directory", "mode": f"{mode:04o}", "path": relative}
            )
        elif stat.S_ISREG(metadata.st_mode):
            if mode & 0o022:
                raise ValidationError(
                    "controlled Python runtime contains a writable file"
                )
            entries.append(
                {
                    "kind": "file",
                    "mode": f"{mode:04o}",
                    "path": relative,
                    "sha256": _sha256_file(path),
                    "size": metadata.st_size,
                }
            )
        else:
            raise ValidationError(
                "controlled Python runtime contains an unsupported special file"
            )
    receipt = {
        "algorithm": "sha256(canonical-json(root-relative kind,mode,size,content/target))",
        "entry_count": len(entries),
        "root": str(root),
        "entries": entries,
    }
    return _sha256_bytes(_canonical_json(receipt)), len(entries)


def _fingerprint_runner(
    command: list[str],
    manifest_value: str | None,
    *,
    require_manifest: bool,
    spec: ValidatedSpec,
    bank: ValidatedHiddenBank,
    output_dir: Path,
) -> RunnerFingerprint:
    manifest_binding: BoundFile | None = None
    runtime_closure_sha256: str | None = None
    runtime_entry_count = 0
    entries: list[dict[str, Any]] = []
    tracked: list[BoundFile] = []
    if manifest_value is None:
        if require_manifest:
            raise ValidationError("held-out evaluation requires --runner-manifest-json")
        inferred_paths: set[Path] = set()
        for argument in command:
            candidate = Path(argument).expanduser()
            if candidate.is_absolute() and candidate.exists() and candidate.is_file():
                resolved, entry, binding = _runner_file_entry(candidate, "runner file")
                inferred_paths.add(resolved)
                if not any(item["path"] == entry["path"] for item in entries):
                    entries.append(entry)
                    tracked.append(binding)
        entries.sort(key=lambda item: item["path"])
    else:
        if require_manifest and (
            len(command) < 4
            or Path(command[0]) != MACOS_PROBE_PYTHON
            or command[1:3] != ["-I", "-S"]
        ):
            raise ValidationError(
                "claim-bearing macOS runner must use the measured system Python "
                "with exact isolated flags -I -S"
            )
        document, _raw_bytes, manifest_binding = _read_json(
            Path(manifest_value), "runner manifest"
        )
        manifest_path = manifest_binding.path
        if not isinstance(document, dict):
            raise ValidationError("runner manifest must be a JSON object")
        _require_exact_keys(document, {"schema_version", "files"}, "runner manifest")
        if document["schema_version"] != SCHEMA_VERSION:
            raise ValidationError("unsupported runner manifest schema_version")
        raw_files = document["files"]
        if not isinstance(raw_files, list) or not raw_files or len(raw_files) > 1000:
            raise ValidationError("runner manifest files must be a non-empty list")
        seen: set[str] = set()
        for index, item in enumerate(raw_files):
            if not isinstance(item, dict):
                raise ValidationError(f"runner manifest file {index} must be an object")
            _require_exact_keys(
                item, {"path", "sha256"}, f"runner manifest file {index}"
            )
            path_text = _require_nonempty_string(
                item["path"], f"runner manifest file {index}.path", 4096
            )
            unresolved = Path(path_text).expanduser()
            if not unresolved.is_absolute():
                raise ValidationError("runner manifest paths must be absolute")
            resolved, actual_entry, binding = _runner_file_entry(
                unresolved, f"runner manifest file {index}"
            )
            declared_sha = _require_sha256(
                item["sha256"], f"runner manifest file {index}.sha256"
            )
            if declared_sha != actual_entry["sha256"]:
                raise ValidationError("runner manifest file fingerprint changed")
            if str(resolved) in seen:
                raise ValidationError("runner manifest contains duplicate files")
            if _is_within(resolved, spec.target_dir) or resolved == bank.path:
                raise ValidationError(
                    "runner manifest exposes protected input material"
                )
            seen.add(str(resolved))
            entries.append({"path": str(resolved), "sha256": declared_sha})
            tracked.append(binding)
        entries.sort(key=lambda item: item["path"])
        if [item["path"] for item in entries] != [item["path"] for item in raw_files]:
            raise ValidationError("runner manifest files must be sorted by path")
        required_files: set[str] = set()
        for argument in command:
            candidate = Path(argument).expanduser()
            if candidate.is_absolute() and candidate.exists() and candidate.is_file():
                required_files.add(str(candidate.resolve(strict=True)))
        if not required_files.issubset(seen):
            raise ValidationError(
                "runner manifest omits an executable or argv-referenced file"
            )
        forbidden_roots = [spec.target_dir, CANDIDATE_ROOT, output_dir]
        if any(_is_within(manifest_path, root) for root in forbidden_roots):
            raise ValidationError(
                "runner manifest must remain outside evaluation surfaces"
            )
        if require_manifest:
            runtime_closure_sha256, runtime_entry_count = (
                _controlled_python_runtime_closure()
            )
    fingerprint = _sha256_bytes(
        _canonical_json(
            {
                "argv": command,
                "files": entries,
                "manifest_sha256": (
                    manifest_binding.sha256 if manifest_binding is not None else None
                ),
                "runtime_closure_sha256": runtime_closure_sha256,
                "runtime_entry_count": runtime_entry_count,
            }
        )
    )
    return RunnerFingerprint(
        sha256=fingerprint,
        tracked_files=tuple(tracked),
        manifest_binding=manifest_binding,
        runtime_closure_sha256=runtime_closure_sha256,
        runtime_entry_count=runtime_entry_count,
    )


def _runner_sources_match(fingerprint: RunnerFingerprint) -> bool:
    for binding in fingerprint.tracked_files:
        if not _binding_matches(binding, "runner file"):
            return False
    if fingerprint.manifest_binding is not None and not _binding_matches(
        fingerprint.manifest_binding, "runner manifest"
    ):
        return False
    if fingerprint.runtime_closure_sha256 is not None:
        try:
            closure_sha256, entry_count = _controlled_python_runtime_closure()
        except ValidationError:
            return False
        if (
            closure_sha256 != fingerprint.runtime_closure_sha256
            or entry_count != fingerprint.runtime_entry_count
        ):
            return False
    return True


def _sandbox_literal(path: Path | str) -> str:
    return json.dumps(str(path), ensure_ascii=False)


def _macos_sandbox_profile(
    run_root: Path,
    runner: list[str],
    runner_fingerprint: RunnerFingerprint,
) -> bytes:
    read_rules = [
        f"    (subpath {_sandbox_literal(path)})"
        for path in MACOS_SYSTEM_READ_ROOTS
        if Path(path).exists()
    ]
    read_rules.extend(
        f"    (literal {_sandbox_literal(path)})"
        for path in (
            MACOS_PROBE_PYTHON,
            Path("/dev/null"),
            Path("/dev/random"),
            Path("/dev/urandom"),
            Path("/dev/zero"),
            Path("/private/etc/localtime"),
        )
        if path.exists()
    )
    read_rules.extend(
        f"    (literal {_sandbox_literal(binding.path)})"
        for binding in runner_fingerprint.tracked_files
    )
    read_rules.append(f"    (subpath {_sandbox_literal(run_root)})")
    executable_rules = sorted(
        {
            f"    (literal {_sandbox_literal(MACOS_PROBE_PYTHON)})",
            f"    (literal {_sandbox_literal(Path(runner[0]))})",
            f"    (subpath {_sandbox_literal(MACOS_PYTHON_FRAMEWORK)})",
        }
    )
    map_rules = [
        f"    (subpath {_sandbox_literal(path)})"
        for path in MACOS_SYSTEM_READ_ROOTS
        if Path(path).exists()
    ]
    map_rules.extend(
        f"    (literal {_sandbox_literal(binding.path)})"
        for binding in runner_fingerprint.tracked_files
    )
    map_rules.extend(executable_rules)
    ancestor_targets = [
        *(Path(path) for path in MACOS_SYSTEM_READ_ROOTS if Path(path).exists()),
        *(binding.path for binding in runner_fingerprint.tracked_files),
        MACOS_PROBE_PYTHON,
        run_root,
    ]
    ancestor_rules = sorted(
        {f"    (path-ancestors {_sandbox_literal(path)})" for path in ancestor_targets}
    )
    profile = "\n".join(
        [
            "(version 1)",
            "(deny default)",
            '(import "dyld-support.sb")',
            "(deny network*)",
            "(allow process-exec",
            *executable_rules,
            ")",
            "(allow sysctl-read)",
            "(allow signal (target self))",
            "(allow file-read-metadata file-test-existence",
            *ancestor_rules,
            ")",
            "(allow file-read* file-test-existence",
            *read_rules,
            ")",
            "(allow file-map-executable",
            *map_rules,
            ")",
            "(allow file-write*",
            f"    (subpath {_sandbox_literal(run_root)})",
            ")",
            "",
        ]
    )
    return profile.encode("utf-8")


SANDBOX_PROBE_CODE = r"""
import errno
import json
import os
from pathlib import Path
import socket
import sys

DENIED = {errno.EACCES, errno.EPERM}

def blocked_read(value):
    try:
        Path(value).read_bytes()
    except OSError as error:
        return error.errno in DENIED
    return False

def blocked_write(value):
    descriptor = None
    try:
        descriptor = os.open(value, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except OSError as error:
        return error.errno in DENIED
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return False

def blocked_network():
    connection = None
    try:
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection.settimeout(0.25)
        connection.connect(("127.0.0.1", 9))
    except OSError as error:
        return error.errno in DENIED
    finally:
        if connection is not None:
            connection.close()
    return False

allowed_input, allowed_output, hidden_bank, source_skill, candidate_skill, outside_write, package_file = sys.argv[1:]
results = {
    "allowed_package_read": Path(package_file).read_bytes() != b"",
    "allowed_workspace_read": Path(allowed_input).read_text(encoding="utf-8") == "probe-input",
    "allowed_workspace_write": False,
    "blocked_candidate_read": blocked_read(candidate_skill),
    "blocked_hidden_read": blocked_read(hidden_bank),
    "blocked_network": blocked_network(),
    "blocked_outside_write": blocked_write(outside_write),
    "blocked_source_read": blocked_read(source_skill),
}
Path(allowed_output).write_text("probe-output", encoding="utf-8")
results["allowed_workspace_write"] = True
json.dump(results, sys.stdout, separators=(",", ":"), sort_keys=True)
sys.stdout.write("\n")
""".strip()


def _run_macos_sandbox_probes(
    boundary: IsolationBoundary,
    profile_bytes: bytes,
    run_root: Path,
    workspace: Path,
    skill_root: Path,
    spec: ValidatedSpec,
    bank: ValidatedHiddenBank,
    treatment: bool,
) -> tuple[dict[str, bool], str]:
    if boundary.executor_path is None:
        raise ValidationError("built-in sandbox executor is unavailable")
    allowed_input = workspace / ".sandbox-probe-input"
    allowed_output = workspace / ".sandbox-probe-output"
    outside_write = run_root.parent / f".{run_root.name}-outside-probe"
    if outside_write.exists():
        raise ValidationError("sandbox probe outside-write sentinel already exists")
    allowed_input.write_text("probe-input", encoding="utf-8")
    allowed_input.chmod(0o400)
    package_file = skill_root / "SKILL.md" if treatment else allowed_input
    candidate_skill = CANDIDATE_ROOT / "SKILL.md"
    command = [
        str(boundary.executor_path),
        "-p",
        profile_bytes.decode("utf-8"),
        str(MACOS_PROBE_PYTHON),
        "-c",
        SANDBOX_PROBE_CODE,
        str(allowed_input),
        str(allowed_output),
        str(bank.path),
        str(spec.skill_path),
        str(candidate_skill),
        str(outside_write),
        str(package_file),
    ]
    environment = {
        "HOME": str(run_root / "home"),
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONNOUSERSITE": "1",
        "TMPDIR": str(run_root / "tmp"),
        "TZ": "UTC",
    }
    try:
        completed = subprocess.run(
            command,
            cwd=workspace,
            env=environment,
            capture_output=True,
            check=False,
            timeout=15,
        )
        if completed.returncode == 71:
            raise MacOSSandboxUnavailable(
                "macOS sandbox-exec cannot be nested in the current parent sandbox"
            )
        if completed.returncode != 0:
            raise ValidationError(
                "built-in macOS sandbox adversarial probes failed "
                f"(probe exit {completed.returncode})"
            )
        decoded = _decode_json(completed.stdout, "sandbox probe output")
        expected_keys = {
            "allowed_package_read",
            "allowed_workspace_read",
            "allowed_workspace_write",
            "blocked_candidate_read",
            "blocked_hidden_read",
            "blocked_network",
            "blocked_outside_write",
            "blocked_source_read",
        }
        if (
            not isinstance(decoded, dict)
            or set(decoded) != expected_keys
            or any(value is not True for value in decoded.values())
            or not allowed_output.is_file()
            or allowed_output.read_text(encoding="utf-8") != "probe-output"
            or outside_write.exists()
        ):
            raise ValidationError("built-in macOS sandbox adversarial probes failed")
        result = {key: True for key in sorted(expected_keys)}
        evidence = {
            "probe_code_sha256": _sha256_bytes(SANDBOX_PROBE_CODE.encode("utf-8")),
            "probe_runtime_sha256": _sha256_file(MACOS_PROBE_PYTHON),
            "results": result,
        }
        return result, _sha256_bytes(_canonical_json(evidence))
    except subprocess.TimeoutExpired as error:
        raise ValidationError(
            "built-in macOS sandbox adversarial probes timed out"
        ) from error
    finally:
        try:
            allowed_input.chmod(0o600)
        except OSError:
            pass
        for path in (allowed_input, allowed_output, outside_write):
            try:
                if path.is_file() and not path.is_symlink():
                    path.unlink()
            except OSError:
                pass


def _snapshot_files(root: Path) -> dict[str, tuple[str, str, str]]:
    snapshot: dict[str, tuple[str, str, str]] = {}
    if not root.exists():
        return snapshot
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        try:
            mode = oct(stat.S_IMODE(path.lstat().st_mode))
            if path.is_symlink():
                snapshot[relative] = ("symlink", os.readlink(path), mode)
            elif path.is_file():
                try:
                    digest = _sha256_file(path)
                except OSError:
                    digest = "unreadable"
                snapshot[relative] = ("file", digest, mode)
            elif path.is_dir():
                snapshot[relative] = ("directory", "", mode)
            elif not path.is_dir():
                snapshot[relative] = ("special", "", mode)
        except OSError:
            snapshot[relative] = ("unreadable", "", "")
    return snapshot


def _safe_artifact_path(root: Path, declared: str) -> Path | None:
    try:
        pure = PurePosixPath(declared)
    except (TypeError, ValueError):
        return None
    if not declared or pure.is_absolute() or "." in pure.parts or ".." in pure.parts:
        return None
    candidate = root.joinpath(*pure.parts)
    try:
        resolved = candidate.resolve(strict=False)
    except (OSError, RuntimeError):
        return None
    if not _is_within(resolved, root.resolve()):
        return None
    return candidate


def _sensitive_bytes(hidden_case: dict[str, Any], hidden_path: Path) -> list[bytes]:
    values = [hidden_case["private_reference"], str(hidden_path)]
    values.extend(hidden_case["forbidden_terms"])
    return [value.casefold().encode("utf-8") for value in values if value]


def _contains_sensitive(data: bytes, needles: list[bytes]) -> bool:
    folded = data.decode("utf-8", errors="ignore").casefold().encode("utf-8")
    return any(needle in folded for needle in needles)


def _gate_list(gates: set[str]) -> list[str]:
    return [gate for gate in HARD_GATE_ORDER if gate in gates]


def _fixed_duration_or_elapsed(started: float, spec: ValidatedSpec) -> int:
    conditions = spec.document["conditions"]
    fixture_boundary = (
        conditions["harness"] == "fixture-agent-v1"
        and conditions["model"] == "deterministic-fixture"
    )
    fixed = os.environ.get("PRAX_EVAL_FIXED_DURATION_MS") if fixture_boundary else None
    if fixed is not None:
        try:
            value = int(fixed)
        except ValueError:
            value = -1
        if 0 <= value <= 86_400_000:
            return value
    return max(0, round((time.monotonic() - started) * 1000))


def _make_tree_writable(root: Path) -> None:
    if not root.exists():
        return
    try:
        root.chmod(0o700)
    except OSError:
        pass
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        try:
            current_path.chmod(0o700)
        except OSError:
            pass
        for name in directories:
            path = current_path / name
            if not path.is_symlink():
                try:
                    path.chmod(0o700)
                except OSError:
                    pass
        for name in files:
            path = current_path / name
            if not path.is_symlink():
                try:
                    path.chmod(0o600)
                except OSError:
                    pass


def _new_private_run_root(spec: ValidatedSpec, bank: ValidatedHiddenBank) -> Path:
    candidates = [Path("/private/tmp"), Path("/tmp"), Path(tempfile.gettempdir())]
    for candidate in candidates:
        try:
            parent = candidate.resolve(strict=True)
        except OSError:
            continue
        if not parent.is_dir() or not os.access(parent, os.W_OK | os.X_OK):
            continue
        if _is_within(parent, spec.target_dir) or _is_within(parent, CANDIDATE_ROOT):
            continue
        run_root = Path(tempfile.mkdtemp(prefix="prax-eval-run-", dir=parent)).resolve()
        if _is_within(bank.path, run_root):
            shutil.rmtree(run_root)
            continue
        run_root.chmod(0o700)
        return run_root
    raise ValidationError("no external private temporary directory is available")


def _materialize_read_only_package(spec: ValidatedSpec, destination: Path) -> None:
    destination.mkdir(mode=0o700)
    directories: set[Path] = {destination}
    for entry in spec.package_manifest:
        relative = PurePosixPath(entry["path"])
        target = destination.joinpath(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        current = target.parent
        while _is_within(current, destination):
            directories.add(current)
            if current == destination:
                break
            current = current.parent
        target.write_bytes(spec.package_files[entry["path"]])
        target.chmod(0o500 if entry["executable"] else 0o400)
    for directory in sorted(
        directories, key=lambda item: len(item.parts), reverse=True
    ):
        directory.chmod(0o500)


def _read_only_package_matches(spec: ValidatedSpec, root: Path) -> bool:
    try:
        actual_manifest, _, _ = _scan_package(root, exclude_runtime=False)
    except ValidationError:
        return False
    if actual_manifest != spec.package_manifest:
        return False
    for path in [root, *(item for item in root.rglob("*") if item.is_dir())]:
        try:
            if stat.S_IMODE(path.lstat().st_mode) & 0o222:
                return False
        except OSError:
            return False
    for entry in spec.package_manifest:
        path = root.joinpath(*PurePosixPath(entry["path"]).parts)
        try:
            if stat.S_IMODE(path.lstat().st_mode) & 0o222:
                return False
        except OSError:
            return False
    return True


def _source_package_matches(spec: ValidatedSpec) -> bool:
    try:
        manifest, files, bindings = _scan_package(spec.target_dir, exclude_runtime=True)
    except ValidationError:
        return False
    return (
        manifest == spec.package_manifest
        and _package_digest(manifest) == spec.package_sha256
        and files == spec.package_files
        and bindings == spec.package_bindings
    )


def _isolation_executor_matches(boundary: IsolationBoundary) -> bool:
    if boundary.executor_path is None:
        return boundary.executor_sha256 is None
    if boundary.executor_sha256 is None:
        return False
    try:
        return (
            boundary.executor_path.is_file()
            and not boundary.executor_path.is_symlink()
            and _sha256_file(boundary.executor_path) == boundary.executor_sha256
        )
    except OSError:
        return False


def _protected_inputs_match(
    spec: ValidatedSpec,
    bank: ValidatedHiddenBank,
    matrix: BoundFile,
    runner: RunnerFingerprint,
) -> bool:
    return (
        _binding_matches(spec.file_binding, "experiment spec")
        and _binding_matches(bank.file_binding, "hidden bank")
        and _binding_matches(matrix, "matrix")
        and _source_package_matches(spec)
        and _runner_sources_match(runner)
    )


def _run_one(
    spec: ValidatedSpec,
    bank: ValidatedHiddenBank,
    matrix_row: dict[str, Any],
    matrix_sha256: str,
    matrix_binding: BoundFile,
    runner: list[str],
    runner_sha256: str,
    runner_fingerprint: RunnerFingerprint,
    timeout_seconds: float,
    boundary: IsolationBoundary,
) -> dict[str, Any]:
    gates: set[str] = set()
    row: dict[str, Any] = {
        "receipt_version": 1,
        **matrix_row,
        "evaluation_scope": _evaluation_scope(spec),
        "matrix_sha256": matrix_sha256,
        "runner_sha256": runner_sha256,
        "runner_runtime_closure_sha256": (runner_fingerprint.runtime_closure_sha256),
        "exit_code": None,
        "timed_out": False,
        "duration_ms": 0,
        "token_usage": {"input": 0, "output": 0, "total": 0},
        "response_sha256": _sha256_bytes(b""),
        "stdout_sha256": _sha256_bytes(b""),
        "stderr_sha256": _sha256_bytes(b""),
        "source_count": 0,
        "sources_sha256": _sha256_bytes(_canonical_json([])),
        "artifact_count": 0,
        "artifact_hashes": [],
        "failed_hard_gates": [],
        "hard_gates_passed": False,
        "soft_score": 0.0,
        "success": False,
        "workspace_removed": False,
        "isolation_level": boundary.level,
        "isolation_contract_sha256": boundary.contract_sha256,
        "isolation_verification_authority": boundary.verification_authority,
        "isolation_verification_evidence_sha256": (
            boundary.verification_evidence_sha256
        ),
        "isolation_executor_sha256": boundary.executor_sha256,
        "isolation_profile_sha256": None,
        "isolation_probes_sha256": None,
        "isolation_probes_passed": False,
        "hidden_bank_nonexposure_verified": (boundary.hidden_bank_nonexposure_verified),
        "network_isolation_verified": boundary.network_isolation_verified,
        "eligible_for_held_out_claims": boundary.eligible_for_held_out_claims,
    }
    run_root = _new_private_run_root(spec, bank)
    workspace = run_root / "workspace"
    home = run_root / "home"
    temporary = run_root / "tmp"
    workspace.mkdir(mode=0o700)
    home.mkdir(mode=0o700)
    temporary.mkdir(mode=0o700)
    skill_root = workspace / ".prax-eval-skill"
    if matrix_row["arm"] == "treatment":
        _materialize_read_only_package(spec, skill_root)

    effective_runner = runner
    if boundary.level == "builtin_macos_sandbox_exec":
        profile_bytes = _macos_sandbox_profile(run_root, runner, runner_fingerprint)
        try:
            _, probes_sha256 = _run_macos_sandbox_probes(
                boundary,
                profile_bytes,
                run_root,
                workspace,
                skill_root,
                spec,
                bank,
                matrix_row["arm"] == "treatment",
            )
        except (ValidationError, MacOSSandboxUnavailable):
            _make_tree_writable(run_root)
            shutil.rmtree(run_root, ignore_errors=True)
            raise
        row["isolation_profile_sha256"] = _sha256_bytes(profile_bytes)
        row["isolation_probes_sha256"] = probes_sha256
        row["isolation_probes_passed"] = True
        row["isolation_verification_evidence_sha256"] = probes_sha256
        row["hidden_bank_nonexposure_verified"] = True
        row["network_isolation_verified"] = True
        effective_runner = [
            str(boundary.executor_path),
            "-p",
            profile_bytes.decode("utf-8"),
            *runner,
        ]

    before = _snapshot_files(run_root)
    case = spec.cases[matrix_row["case_id"]]
    hidden_case = bank.cases[matrix_row["case_id"]]
    request = {
        "schema_version": SCHEMA_VERSION,
        "prompt": case["prompt"],
        "run_metadata": {
            "experiment_id": spec.document["experiment_id"],
            "run_id": matrix_row["run_id"],
            "conditions": spec.document["conditions"],
        },
    }
    child_environment = {
        "HOME": str(home),
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONNOUSERSITE": "1",
        "TMPDIR": str(temporary),
        "TZ": "UTC",
        "XDG_CACHE_HOME": str(home / ".cache"),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_DATA_HOME": str(home / ".local" / "share"),
    }
    source_date_epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if source_date_epoch and source_date_epoch.isdigit():
        child_environment["SOURCE_DATE_EPOCH"] = source_date_epoch
    if matrix_row["arm"] == "treatment":
        child_environment["PRAX_EVAL_SKILL"] = str(skill_root / "SKILL.md")
        child_environment["PRAX_EVAL_SKILL_ROOT"] = str(skill_root)

    started = time.monotonic()
    stdout_bytes = b""
    stderr_bytes = b""
    if not _protected_inputs_match(spec, bank, matrix_binding, runner_fingerprint):
        gates.add("input_integrity")
    else:
        try:
            completed = subprocess.run(
                effective_runner,
                cwd=workspace,
                env=child_environment,
                input=_canonical_json(request),
                capture_output=True,
                check=False,
                timeout=timeout_seconds,
            )
            stdout_bytes = completed.stdout
            stderr_bytes = completed.stderr
            row["exit_code"] = completed.returncode
            if completed.returncode != 0:
                gates.add("process_exit")
        except subprocess.TimeoutExpired as error:
            row["timed_out"] = True
            gates.add("process_exit")
            stdout_bytes = error.stdout or b""
            stderr_bytes = error.stderr or b""
        except OSError:
            gates.add("process_exit")
    if not _protected_inputs_match(spec, bank, matrix_binding, runner_fingerprint):
        gates.add("input_integrity")
    row["duration_ms"] = _fixed_duration_or_elapsed(started, spec)
    row["stdout_sha256"] = _sha256_bytes(stdout_bytes)
    row["stderr_sha256"] = _sha256_bytes(stderr_bytes)

    protocol: dict[str, Any] | None = None
    if len(stdout_bytes) > MAX_JSON_BYTES or len(stderr_bytes) > MAX_JSON_BYTES:
        gates.add("output_integrity")
    else:
        try:
            decoded = _decode_json(stdout_bytes, "runner output")
            if not isinstance(decoded, dict):
                raise ValidationError("runner output must be an object")
            _require_exact_keys(
                decoded,
                {"artifacts", "response", "sources", "token_usage"},
                "runner output",
            )
            protocol = decoded
        except ValidationError:
            gates.add("output_integrity")

    needles = _sensitive_bytes(hidden_case, bank.path)
    emitted_for_scoring: list[str] = []
    declared_paths: list[Path] = []
    declared_relatives: set[str] = set()
    artifact_hashes: list[str] = []
    if protocol is not None:
        response = protocol["response"]
        if (
            not isinstance(response, str)
            or len(response) > MAX_JSON_BYTES
            or "\x00" in response
        ):
            gates.add("output_integrity")
            response = ""
        response_bytes = response.encode("utf-8")
        row["response_sha256"] = _sha256_bytes(response_bytes)
        emitted_for_scoring.append(response)

        sources = protocol["sources"]
        if (
            not isinstance(sources, list)
            or len(sources) > 200
            or any(
                not isinstance(source, str) or not source or len(source) > 10_000
                for source in sources
            )
        ):
            gates.add("source_integrity")
            sources = []
        row["source_count"] = len(sources)
        row["sources_sha256"] = _sha256_bytes(_canonical_json(sources))
        required_sources = hidden_case.get("required_sources", [])
        forbidden_sources = hidden_case.get("forbidden_sources", [])
        source_folded = {source.casefold() for source in sources}
        if any(source.casefold() not in source_folded for source in required_sources):
            gates.add("source_integrity")
        if any(source.casefold() in source_folded for source in forbidden_sources):
            gates.add("source_integrity")

        token_usage = protocol["token_usage"]
        if not isinstance(token_usage, dict) or set(token_usage) - {
            "input",
            "output",
            "total",
        }:
            gates.add("output_integrity")
        else:
            token_values: dict[str, int] = {}
            for key in ("input", "output"):
                value = token_usage.get(key)
                if (
                    not isinstance(value, int)
                    or isinstance(value, bool)
                    or not 0 <= value <= 10**9
                ):
                    gates.add("output_integrity")
                    value = 0
                token_values[key] = value
            total = token_usage.get(
                "total", token_values["input"] + token_values["output"]
            )
            if (
                not isinstance(total, int)
                or isinstance(total, bool)
                or total < token_values["input"] + token_values["output"]
                or total > 2 * 10**9
            ):
                gates.add("output_integrity")
                total = token_values["input"] + token_values["output"]
            row["token_usage"] = {**token_values, "total": total}

        artifacts = protocol["artifacts"]
        if not isinstance(artifacts, list) or len(artifacts) > 200:
            gates.add("output_integrity")
            artifacts = []
        for artifact in artifacts:
            if (
                not isinstance(artifact, str)
                or len(artifact) > 4096
                or "\x00" in artifact
            ):
                gates.add("artifact_path_escape")
                continue
            relative_path = _safe_artifact_path(workspace, artifact)
            if relative_path is None:
                gates.add("artifact_path_escape")
                continue
            relative = relative_path.relative_to(workspace).as_posix()
            if relative in declared_relatives:
                gates.add("output_integrity")
                continue
            declared_relatives.add(relative)
            declared_paths.append(relative_path)

        for artifact_path in declared_paths:
            relative = artifact_path.relative_to(workspace).as_posix()
            root_relative = artifact_path.relative_to(run_root).as_posix()
            try:
                resolved_artifact = artifact_path.resolve(strict=True)
            except (OSError, RuntimeError):
                gates.add("output_integrity")
                continue
            if (
                artifact_path.is_symlink()
                or not resolved_artifact.is_file()
                or not _is_within(resolved_artifact, workspace.resolve())
                or root_relative in before
            ):
                gates.add("artifact_path_escape")
                continue
            try:
                artifact_size = resolved_artifact.stat().st_size
                if artifact_size > MAX_ARTIFACT_BYTES:
                    gates.add("output_integrity")
                    continue
                artifact_data = resolved_artifact.read_bytes()
            except OSError:
                gates.add("output_integrity")
                continue
            artifact_hashes.append(_sha256_bytes(artifact_data))
            emitted_for_scoring.append(artifact_data.decode("utf-8", errors="ignore"))

    after = _snapshot_files(run_root)
    new_files = set(after) - set(before)
    changed_inputs = {
        name for name in set(before) & set(after) if before[name] != after[name]
    }
    removed_inputs = set(before) - set(after)
    declared_root_relatives = {f"workspace/{name}" for name in declared_relatives}
    allowed_created_paths = set(declared_root_relatives)
    for relative in declared_root_relatives:
        parent = PurePosixPath(relative).parent
        while str(parent) not in (".", "workspace"):
            allowed_created_paths.add(str(parent))
            parent = parent.parent
    if new_files - allowed_created_paths:
        gates.add("silent_persistence")
    if changed_inputs or removed_inputs:
        gates.add("input_integrity")
    if matrix_row["arm"] == "treatment" and not _read_only_package_matches(
        spec, skill_root
    ):
        gates.add("input_integrity")

    emitted_bytes = "\n".join(emitted_for_scoring).encode("utf-8")
    path_bytes = "\n".join(declared_relatives).encode("utf-8")
    source_bytes = (
        _canonical_json(protocol["sources"])
        if protocol and isinstance(protocol.get("sources"), list)
        else b""
    )
    if any(
        _contains_sensitive(payload, needles)
        for payload in (
            stdout_bytes,
            stderr_bytes,
            emitted_bytes,
            path_bytes,
            source_bytes,
        )
    ):
        gates.add("answer_leak")

    row["artifact_count"] = len(artifact_hashes)
    row["artifact_hashes"] = sorted(artifact_hashes)
    if not gates:
        score_text = "\n".join(emitted_for_scoring).casefold()
        required_terms = hidden_case["required_terms"]
        matches = sum(term.casefold() in score_text for term in required_terms)
        row["soft_score"] = round(matches / len(required_terms), 6)
        row["success"] = matches == len(required_terms)

    _make_tree_writable(run_root)
    try:
        shutil.rmtree(run_root)
        row["workspace_removed"] = not run_root.exists()
    except OSError:
        gates.add("workspace_cleanup")
        row["workspace_removed"] = False
    if not row["workspace_removed"]:
        gates.add("workspace_cleanup")
    if gates:
        row["soft_score"] = 0.0
        row["success"] = False
    row["failed_hard_gates"] = _gate_list(gates)
    row["hard_gates_passed"] = not gates
    row["eligible_for_held_out_claims"] = (
        boundary.eligible_for_held_out_claims
        and spec.document["eligibility"] == "held_out_external_evaluation"
        and not gates
    )
    return row


def _archive_results(
    output_dir: Path,
    spec: ValidatedSpec,
    hidden_bank_sha256: str,
    rows: list[dict[str, Any]],
    matrix_sha256: str,
    runner_sha256: str,
) -> None:
    if output_dir.exists():
        raise ValidationError("output directory already exists")
    output_parent = output_dir.parent
    output_parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_parent))
    try:
        receipts = staging / "receipts"
        receipts.mkdir(mode=0o700)
        results_bytes = _jsonl(rows)
        _atomic_write(staging / "results.jsonl", results_bytes)
        receipt_index: list[dict[str, str]] = []
        for row in rows:
            receipt_bytes = _canonical_json(row)
            _atomic_write(receipts / f"{row['run_id']}.json", receipt_bytes)
            receipt_index.append(
                {
                    "run_id": row["run_id"],
                    "sha256": _sha256_bytes(receipt_bytes),
                }
            )
        receipt_index.sort(key=lambda item: item["run_id"])
        results_sha256 = _sha256_bytes(results_bytes)
        receipt_set_sha256 = _sha256_bytes(_canonical_json(receipt_index))
        evidence_binding = {
            "authority": "package_owned_same_run",
            "spec_sha256": spec.file_sha256,
            "hidden_bank_sha256": hidden_bank_sha256,
            "target_package_sha256": spec.package_sha256,
            "matrix_sha256": matrix_sha256,
            "runner_sha256": runner_sha256,
            "runner_runtime_closure_sha256": sorted(
                {
                    row["runner_runtime_closure_sha256"]
                    for row in rows
                    if row["runner_runtime_closure_sha256"] is not None
                }
            ),
            "results_sha256": results_sha256,
            "receipt_count": len(receipt_index),
            "receipt_set_sha256": receipt_set_sha256,
            "receipts": receipt_index,
            "isolation_executor_sha256": sorted(
                {
                    row["isolation_executor_sha256"]
                    for row in rows
                    if row["isolation_executor_sha256"] is not None
                }
            ),
            "isolation_profile_sha256": sorted(
                {
                    row["isolation_profile_sha256"]
                    for row in rows
                    if row["isolation_profile_sha256"] is not None
                }
            ),
            "isolation_probes_sha256": sorted(
                {
                    row["isolation_probes_sha256"]
                    for row in rows
                    if row["isolation_probes_sha256"] is not None
                }
            ),
        }
        report_document = _report(
            spec,
            rows,
            results_bytes,
            evidence_binding=evidence_binding,
        )
        report_bytes = _canonical_json(report_document)
        _atomic_write(staging / "report.json", report_bytes)
        isolation_levels = sorted({row["isolation_level"] for row in rows})
        eligible = report_document["eligible_for_held_out_claims"]
        hidden_verified = bool(rows) and all(
            row["hidden_bank_nonexposure_verified"] for row in rows
        )
        scopes = sorted({row["evaluation_scope"] for row in rows})
        if len(scopes) != 1:
            raise ValidationError("results contain mixed evaluation scopes")
        evaluation_scope = scopes[0]
        evidence_level = report_document["evidence_level"]
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "evidence_level": evidence_level,
            "evaluation_scope": evaluation_scope,
            "eligible_for_held_out_claims": eligible,
            "supports_candidate_quality_claim": eligible,
            "supports_human_learning_claim": False,
            "isolation_levels": isolation_levels,
            "hidden_bank_nonexposure_verified": hidden_verified,
            "isolation_verification_evidence_sha256": sorted(
                {
                    row["isolation_verification_evidence_sha256"]
                    for row in rows
                    if row["isolation_verification_evidence_sha256"] is not None
                }
            ),
            "result_count": len(rows),
            "results_sha256": results_sha256,
            "receipt_count": len(receipt_index),
            "receipt_set_sha256": receipt_set_sha256,
            "report_sha256": _sha256_bytes(report_bytes),
            "matrix_sha256": matrix_sha256,
            "runner_sha256": runner_sha256,
            "runner_runtime_closure_sha256": evidence_binding[
                "runner_runtime_closure_sha256"
            ],
            "spec_sha256": spec.file_sha256,
            "hidden_bank_sha256": hidden_bank_sha256,
            "target_package_sha256": spec.package_sha256,
            "evidence_binding": evidence_binding,
            "contains_hidden_bank_material": False,
            "contains_target_workspaces": False,
        }
        _atomic_write(staging / "manifest.json", _canonical_json(manifest))
        os.chmod(staging, 0o700)
        os.replace(staging, output_dir)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _validate_results(
    path: Path, spec: ValidatedSpec
) -> tuple[list[dict[str, Any]], bytes, Path]:
    rows, raw, binding = _parse_jsonl(path, "results")
    expected_rows = _plan_rows(spec)
    if len(rows) != len(expected_rows):
        raise ValidationError("results are incomplete")
    expected_by_run = {row["run_id"]: row for row in expected_rows}
    seen: set[str] = set()
    matrix_digests: set[str] = set()
    runner_digests: set[str] = set()
    for index, row in enumerate(rows):
        _require_exact_keys(row, RESULT_KEYS, f"results row {index}")
        run_id = row["run_id"]
        if run_id in seen:
            raise ValidationError("results contain duplicate run ids")
        seen.add(run_id)
        expected = expected_by_run.get(run_id)
        if expected is None:
            raise ValidationError("results contain an unknown run id")
        for key, value in expected.items():
            if row.get(key) != value:
                raise ValidationError(
                    "results contain mismatched experiment fingerprints"
                )
        if row["receipt_version"] != 1:
            raise ValidationError("unsupported result receipt version")
        expected_scope = _evaluation_scope(spec)
        if row["evaluation_scope"] != expected_scope:
            raise ValidationError("results evaluation scope is inconsistent")
        for field in (
            "matrix_sha256",
            "runner_sha256",
            "response_sha256",
            "stdout_sha256",
            "stderr_sha256",
            "sources_sha256",
        ):
            _require_sha256(row[field], f"results.{field}")
        matrix_digests.add(row["matrix_sha256"])
        runner_digests.add(row["runner_sha256"])
        if not isinstance(row["failed_hard_gates"], list) or any(
            gate not in HARD_GATE_ORDER for gate in row["failed_hard_gates"]
        ):
            raise ValidationError("results contain invalid hard-gate data")
        if row["failed_hard_gates"] != _gate_list(set(row["failed_hard_gates"])):
            raise ValidationError("results hard-gate ordering is invalid")
        if row["hard_gates_passed"] is not (not row["failed_hard_gates"]):
            raise ValidationError("results hard-gate summary is inconsistent")
        isolation_level = row["isolation_level"]
        if isolation_level not in {
            "unconfined_public_fixture",
            "builtin_macos_sandbox_exec",
        }:
            raise ValidationError("results isolation level is invalid")
        for field in (
            "hidden_bank_nonexposure_verified",
            "network_isolation_verified",
            "eligible_for_held_out_claims",
            "isolation_probes_passed",
        ):
            if not isinstance(row[field], bool):
                raise ValidationError(f"results {field} must be boolean")
        isolation_contract_sha = row["isolation_contract_sha256"]
        runtime_closure_sha = row["runner_runtime_closure_sha256"]
        verification_authority = row["isolation_verification_authority"]
        verification_evidence_sha = row["isolation_verification_evidence_sha256"]
        executor_sha = row["isolation_executor_sha256"]
        profile_sha = row["isolation_profile_sha256"]
        probes_sha = row["isolation_probes_sha256"]
        if isolation_level == "unconfined_public_fixture":
            if (
                isolation_contract_sha is not None
                or verification_authority is not None
                or verification_evidence_sha is not None
                or executor_sha is not None
                or profile_sha is not None
                or probes_sha is not None
                or runtime_closure_sha is not None
                or row["isolation_probes_passed"]
                or row["hidden_bank_nonexposure_verified"]
                or row["network_isolation_verified"]
                or row["eligible_for_held_out_claims"]
                or spec.document["eligibility"] != "public_development_only"
            ):
                raise ValidationError(
                    "public-fixture results overstate their isolation or eligibility"
                )
        else:
            _require_sha256(
                runtime_closure_sha, "results.runner_runtime_closure_sha256"
            )
            if isolation_contract_sha is not None:
                raise ValidationError(
                    "built-in isolation cannot cite an external contract"
                )
            if verification_authority != "builtin-macos-sandbox-exec":
                raise ValidationError("built-in isolation authority is invalid")
            for field, value in (
                ("isolation_executor_sha256", executor_sha),
                ("isolation_profile_sha256", profile_sha),
                ("isolation_probes_sha256", probes_sha),
                (
                    "isolation_verification_evidence_sha256",
                    verification_evidence_sha,
                ),
            ):
                _require_sha256(value, f"results.{field}")
            if verification_evidence_sha != probes_sha:
                raise ValidationError(
                    "built-in isolation probe evidence is inconsistent"
                )
            if spec.document["eligibility"] not in {
                "containment_mechanism_only",
                "held_out_external_evaluation",
            }:
                raise ValidationError(
                    "built-in isolation result eligibility is invalid"
                )
            probes_passed = row["isolation_probes_passed"]
            boundary_verified = (
                probes_passed
                and row["hidden_bank_nonexposure_verified"]
                and row["network_isolation_verified"]
            )
            if not boundary_verified and (
                "input_integrity" not in row["failed_hard_gates"]
                or row["eligible_for_held_out_claims"]
            ):
                raise ValidationError("built-in isolation lacks valid probe evidence")
            expected_held_out_eligibility = (
                spec.document["eligibility"] == "held_out_external_evaluation"
                and row["hard_gates_passed"]
            )
            if (
                boundary_verified
                and row["eligible_for_held_out_claims"]
                is not expected_held_out_eligibility
            ):
                raise ValidationError(
                    "built-in isolation eligibility is inconsistent with hard gates"
                )
        if not isinstance(row["workspace_removed"], bool):
            raise ValidationError("results workspace cleanup value is invalid")
        if (not row["workspace_removed"]) is not (
            "workspace_cleanup" in row["failed_hard_gates"]
        ):
            raise ValidationError("results workspace cleanup summary is inconsistent")
        if not isinstance(row["timed_out"], bool):
            raise ValidationError("results timeout value is invalid")
        exit_code = row["exit_code"]
        if exit_code is not None and (
            not isinstance(exit_code, int) or isinstance(exit_code, bool)
        ):
            raise ValidationError("results exit code is invalid")
        process_failed = row["timed_out"] or exit_code is None or exit_code != 0
        if process_failed is not ("process_exit" in row["failed_hard_gates"]):
            raise ValidationError("results process-exit summary is inconsistent")
        if row["failed_hard_gates"] and (
            row["success"] is not False or row["soft_score"] != 0.0
        ):
            raise ValidationError("results applied soft scoring before hard gates")
        if not isinstance(row["success"], bool):
            raise ValidationError("results success must be boolean")
        if (
            not isinstance(row["soft_score"], (int, float))
            or isinstance(row["soft_score"], bool)
            or not 0 <= row["soft_score"] <= 1
        ):
            raise ValidationError("results soft_score is invalid")
        if not row["failed_hard_gates"] and row["success"] is not (
            row["soft_score"] == 1.0
        ):
            raise ValidationError("results success and soft score are inconsistent")
        if not isinstance(row["duration_ms"], int) or row["duration_ms"] < 0:
            raise ValidationError("results duration is invalid")
        if (
            not isinstance(row["source_count"], int)
            or isinstance(row["source_count"], bool)
            or not 0 <= row["source_count"] <= 200
        ):
            raise ValidationError("results source count is invalid")
        token_usage = row["token_usage"]
        if not isinstance(token_usage, dict) or set(token_usage) != {
            "input",
            "output",
            "total",
        }:
            raise ValidationError("results token usage is invalid")
        if (
            any(
                not isinstance(token_usage[key], int)
                or isinstance(token_usage[key], bool)
                or token_usage[key] < 0
                for key in token_usage
            )
            or token_usage["total"] < token_usage["input"] + token_usage["output"]
        ):
            raise ValidationError("results token usage is inconsistent")
        if not isinstance(row["artifact_hashes"], list) or any(
            not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest)
            for digest in row["artifact_hashes"]
        ):
            raise ValidationError("results artifact hashes are invalid")
        if (
            not isinstance(row["artifact_count"], int)
            or isinstance(row["artifact_count"], bool)
            or row["artifact_count"] != len(row["artifact_hashes"])
        ):
            raise ValidationError("results artifact count is inconsistent")
        if row["artifact_hashes"] != sorted(row["artifact_hashes"]):
            raise ValidationError("results artifact hashes are not canonical")
    if seen != set(expected_by_run):
        raise ValidationError("results are incomplete")
    if len(matrix_digests) != 1 or len(runner_digests) != 1:
        raise ValidationError("results contain mismatched run fingerprints")
    return rows, raw, binding.path


def _quantile(values: list[float], probability: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = round((len(ordered) - 1) * probability)
    return ordered[index]


def _stratum_summary(
    rows: list[dict[str, Any]],
    case_ids: list[str],
    seed: int,
    bootstrap_samples: int,
) -> dict[str, Any]:
    relevant = [row for row in rows if row["case_id"] in case_ids]
    by_pair: dict[str, dict[str, dict[str, Any]]] = {}
    for row in relevant:
        by_pair.setdefault(row["case_id"], {}).setdefault(str(row["trial"]), {})[
            row["arm"]
        ] = row
    case_deltas: dict[str, list[float]] = {}
    case_soft_deltas: dict[str, list[float]] = {}
    for case_id in case_ids:
        case_deltas[case_id] = []
        case_soft_deltas[case_id] = []
        for trial in sorted(by_pair[case_id], key=int):
            pair = by_pair[case_id][trial]
            case_deltas[case_id].append(
                float(pair["treatment"]["success"]) - float(pair["control"]["success"])
            )
            case_soft_deltas[case_id].append(
                pair["treatment"]["soft_score"] - pair["control"]["soft_score"]
            )
    control = [float(row["success"]) for row in relevant if row["arm"] == "control"]
    treatment = [float(row["success"]) for row in relevant if row["arm"] == "treatment"]
    control_soft = [row["soft_score"] for row in relevant if row["arm"] == "control"]
    treatment_soft = [
        row["soft_score"] for row in relevant if row["arm"] == "treatment"
    ]
    lift = sum(treatment) / len(treatment) - sum(control) / len(control)
    soft_lift = sum(treatment_soft) / len(treatment_soft) - sum(control_soft) / len(
        control_soft
    )

    generator = random.Random(seed)
    bootstrap: list[float] = []
    for _ in range(bootstrap_samples):
        sampled_cases = [generator.choice(case_ids) for _ in case_ids]
        sampled_deltas: list[float] = []
        for case_id in sampled_cases:
            deltas = case_deltas[case_id]
            sampled_deltas.extend(generator.choice(deltas) for _ in deltas)
        bootstrap.append(sum(sampled_deltas) / len(sampled_deltas))
    return {
        "case_count": len(case_ids),
        "paired_trials": len(control),
        "control_success_rate": round(sum(control) / len(control), 6),
        "treatment_success_rate": round(sum(treatment) / len(treatment), 6),
        "absolute_lift": round(lift, 6),
        "soft_score_lift": round(soft_lift, 6),
        "confidence_interval": {
            "lower": round(_quantile(bootstrap, 0.025), 6),
            "upper": round(_quantile(bootstrap, 0.975), 6),
            "confidence": 0.95,
            "method": "seeded_hierarchical_paired_bootstrap",
            "samples": bootstrap_samples,
        },
    }


def _same_run_binding_matches(
    spec: ValidatedSpec,
    rows: list[dict[str, Any]],
    results_bytes: bytes,
    binding: dict[str, Any] | None,
) -> bool:
    expected_keys = {
        "authority",
        "spec_sha256",
        "hidden_bank_sha256",
        "target_package_sha256",
        "matrix_sha256",
        "runner_sha256",
        "runner_runtime_closure_sha256",
        "results_sha256",
        "receipt_count",
        "receipt_set_sha256",
        "receipts",
        "isolation_executor_sha256",
        "isolation_profile_sha256",
        "isolation_probes_sha256",
    }
    if not isinstance(binding, dict) or set(binding) != expected_keys:
        return False
    matrix_digests = {row["matrix_sha256"] for row in rows}
    runner_digests = {row["runner_sha256"] for row in rows}
    runtime_digests = sorted(
        {
            row["runner_runtime_closure_sha256"]
            for row in rows
            if row["runner_runtime_closure_sha256"] is not None
        }
    )
    receipts = binding["receipts"]
    if (
        binding["authority"] != "package_owned_same_run"
        or binding["spec_sha256"] != spec.file_sha256
        or binding["target_package_sha256"] != spec.package_sha256
        or binding["results_sha256"] != _sha256_bytes(results_bytes)
        or len(matrix_digests) != 1
        or binding["matrix_sha256"] not in matrix_digests
        or len(runner_digests) != 1
        or binding["runner_sha256"] not in runner_digests
        or binding["runner_runtime_closure_sha256"] != runtime_digests
        or not isinstance(binding["hidden_bank_sha256"], str)
        or SHA256_PATTERN.fullmatch(binding["hidden_bank_sha256"]) is None
        or not isinstance(receipts, list)
        or binding["receipt_count"] != len(rows)
        or len(receipts) != len(rows)
    ):
        return False
    if any(
        not isinstance(item, dict)
        or set(item) != {"run_id", "sha256"}
        or not isinstance(item["run_id"], str)
        or not isinstance(item["sha256"], str)
        or SHA256_PATTERN.fullmatch(item["sha256"]) is None
        for item in receipts
    ):
        return False
    if [item["run_id"] for item in receipts] != sorted(row["run_id"] for row in rows):
        return False
    if binding["receipt_set_sha256"] != _sha256_bytes(_canonical_json(receipts)):
        return False
    for field in (
        "isolation_executor_sha256",
        "isolation_profile_sha256",
        "isolation_probes_sha256",
    ):
        expected = sorted({row[field] for row in rows if row[field] is not None})
        if binding[field] != expected:
            return False
    return True


def _report(
    spec: ValidatedSpec,
    rows: list[dict[str, Any]],
    results_bytes: bytes,
    *,
    evidence_binding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    seed = spec.document["design"]["seed"]
    samples = spec.document["design"]["bootstrap_samples"]
    strata: dict[str, Any] = {}
    for kind in sorted({case["kind"] for case in spec.cases.values()}):
        case_ids = sorted(
            case_id for case_id, case in spec.cases.items() if case["kind"] == kind
        )
        stratum_seed = int.from_bytes(
            hashlib.sha256(f"{seed}|{kind}".encode()).digest()[:8], "big"
        )
        strata[kind] = _stratum_summary(rows, case_ids, stratum_seed, samples)
    all_case_ids = sorted(spec.cases)
    overall_seed = int.from_bytes(
        hashlib.sha256(f"{seed}|overall".encode()).digest()[:8], "big"
    )
    overall = _stratum_summary(rows, all_case_ids, overall_seed, samples)
    hard_failure_count = sum(not row["hard_gates_passed"] for row in rows)
    epoch_text = os.environ.get("SOURCE_DATE_EPOCH", "0")
    try:
        epoch = int(epoch_text)
    except ValueError:
        epoch = 0
    generated_at = (
        datetime.fromtimestamp(max(0, epoch), timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )
    isolation_levels = sorted({row["isolation_level"] for row in rows})
    same_run_bound = _same_run_binding_matches(
        spec, rows, results_bytes, evidence_binding
    )
    rows_assert_eligible = bool(rows) and all(
        row["eligible_for_held_out_claims"] for row in rows
    )
    eligible = same_run_bound and rows_assert_eligible
    hidden_verified = bool(rows) and all(
        row["hidden_bank_nonexposure_verified"] for row in rows
    )
    public_fixture = isolation_levels == ["unconfined_public_fixture"]
    evaluation_scope = _evaluation_scope(spec)
    containment_verified = (
        evaluation_scope == "containment_mechanism_fixture"
        and hard_failure_count == 0
        and hidden_verified
        and all(row["network_isolation_verified"] for row in rows)
        and all(row["isolation_probes_passed"] for row in rows)
    )
    if eligible:
        evidence_level = "evaluated_held_out_agent_benchmark"
        claim_boundary = (
            "Built-in sandbox evidence supports an agent benchmark claim only; "
            "it is not human-learning evidence."
        )
    elif containment_verified:
        evidence_level = "evaluated_containment_mechanism_fixture"
        claim_boundary = (
            "Adversarial fixture evidence verifies this sandbox invocation's "
            "containment mechanism only. It does not evaluate candidate quality, "
            "held-out performance, or human learning."
        )
    elif public_fixture:
        evidence_level = "evaluated_public_machinery_fixture"
        claim_boundary = (
            "Unconfined public fixture evaluation validates machinery only."
        )
    else:
        evidence_level = "ineligible_evaluation_integrity_failure"
        claim_boundary = (
            "Built-in isolation was requested, but one or more integrity gates "
            "failed; this run supports no benchmark or human-learning claim."
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": spec.document["experiment_id"],
        "evidence_level": evidence_level,
        "evaluation_scope": evaluation_scope,
        "isolation_levels": isolation_levels,
        "hidden_bank_nonexposure_verified": hidden_verified,
        "isolation_verification_authorities": sorted(
            {
                row["isolation_verification_authority"]
                for row in rows
                if row["isolation_verification_authority"] is not None
            }
        ),
        "isolation_verification_evidence_sha256": sorted(
            {
                row["isolation_verification_evidence_sha256"]
                for row in rows
                if row["isolation_verification_evidence_sha256"] is not None
            }
        ),
        "runner_runtime_closure_sha256": sorted(
            {
                row["runner_runtime_closure_sha256"]
                for row in rows
                if row["runner_runtime_closure_sha256"] is not None
            }
        ),
        "eligible_for_held_out_claims": eligible,
        "supports_candidate_quality_claim": eligible,
        "supports_human_learning_claim": False,
        "claim_boundary": claim_boundary,
        "evidence_binding": (
            evidence_binding
            if same_run_bound
            else {
                "authority": "standalone_untrusted_results",
                "results_sha256": _sha256_bytes(results_bytes),
            }
        ),
        "spec_sha256": spec.file_sha256,
        "target_package_sha256": spec.package_sha256,
        "target_package_file_count": len(spec.package_manifest),
        "results_sha256": _sha256_bytes(results_bytes),
        "generated_at": generated_at,
        "run_count": len(rows),
        "hard_gate_failure_count": hard_failure_count,
        "all_hard_gates_passed": hard_failure_count == 0,
        "minimum_effect": spec.document["design"]["minimum_effect"],
        "meets_predeclared_public_fixture_threshold": (
            public_fixture
            and hard_failure_count == 0
            and overall["absolute_lift"] >= spec.document["design"]["minimum_effect"]
        ),
        "meets_predeclared_held_out_threshold": (
            eligible
            and overall["absolute_lift"] >= spec.document["design"]["minimum_effect"]
        ),
        "strata": strata,
        "overall": overall,
    }


def _command_plan(arguments: argparse.Namespace) -> int:
    spec = _validate_spec(Path(arguments.spec))
    output = _validate_output_file(Path(arguments.output), _spec_input_paths(spec))
    _atomic_write(output, _jsonl(_plan_rows(spec)))
    return 0


def _command_run(arguments: argparse.Namespace) -> int:
    spec = _validate_spec(Path(arguments.spec))
    public_fixture = bool(arguments.public_fixture_unconfined)
    macos_sandbox = bool(arguments.macos_sandbox)
    if arguments.isolation_wrapper_json:
        raise ValidationError(
            "self-authored isolation wrapper contracts cannot establish a trusted "
            "boundary; the external trusted-isolation adapter is not implemented "
            "and remains parked"
        )
    if not public_fixture and not macos_sandbox:
        raise ValidationError(
            "run requires either --public-fixture-unconfined or the built-in "
            "--macos-sandbox executor"
        )
    if public_fixture and spec.document["eligibility"] != "public_development_only":
        raise ValidationError(
            "public-fixture mode rejects specs labeled as held-out evidence"
        )
    if macos_sandbox and spec.document["eligibility"] not in {
        "containment_mechanism_only",
        "held_out_external_evaluation",
    }:
        raise ValidationError(
            "built-in macOS sandbox mode requires containment_mechanism_only or "
            "held_out_external_evaluation eligibility"
        )
    matrix, matrix_bytes, matrix_binding = _validate_matrix(
        Path(arguments.matrix), spec
    )
    output_dir = Path(arguments.output_dir).expanduser().resolve(strict=False)
    if output_dir.exists():
        raise ValidationError("output directory already exists")
    if _is_within(output_dir, spec.target_dir) or _is_within(
        output_dir, CANDIDATE_ROOT
    ):
        raise ValidationError(
            "output directory must be external to the target and candidate"
        )
    if public_fixture:
        expected_bank_eligibility = "public_development_grader"
    elif spec.document["eligibility"] == "containment_mechanism_only":
        expected_bank_eligibility = "adversarial_containment_fixture"
    else:
        expected_bank_eligibility = "hidden_external_test"
    bank = _validate_hidden_bank(
        Path(arguments.hidden_bank),
        spec,
        output_dir,
        expected_bank_eligibility,
    )
    boundary = (
        _public_fixture_boundary() if public_fixture else _trusted_macos_boundary()
    )
    _reject_cross_aliases(
        [("matrix", matrix_binding)],
        [
            ("experiment spec", spec.file_binding),
            ("hidden bank", bank.file_binding),
            *(
                (f"target package file {relative}", binding)
                for relative, binding in spec.package_bindings.items()
            ),
        ],
    )
    runner = _validate_runner(arguments.runner_json, spec, bank)
    runner_fingerprint = _fingerprint_runner(
        runner,
        arguments.runner_manifest_json,
        require_manifest=macos_sandbox,
        spec=spec,
        bank=bank,
        output_dir=output_dir,
    )
    protected_before_runner = [
        ("experiment spec", spec.file_binding),
        ("hidden bank", bank.file_binding),
        ("matrix", matrix_binding),
        *(
            (f"target package file {relative}", binding)
            for relative, binding in spec.package_bindings.items()
        ),
    ]
    if runner_fingerprint.manifest_binding is not None:
        _reject_cross_aliases(
            [("runner manifest", runner_fingerprint.manifest_binding)],
            protected_before_runner,
        )
        protected_before_runner.append(
            ("runner manifest", runner_fingerprint.manifest_binding)
        )
    _reject_cross_aliases(
        [
            (f"runner file {binding.path}", binding)
            for binding in runner_fingerprint.tracked_files
        ],
        protected_before_runner,
    )
    if macos_sandbox and any(
        _is_within(binding.path, CANDIDATE_ROOT)
        or _is_within(binding.path, spec.target_dir)
        for binding in runner_fingerprint.tracked_files
    ):
        raise ValidationError(
            "macOS sandbox runner files must be external to candidate and target sources"
        )
    if not 0.1 <= arguments.timeout <= 3600:
        raise ValidationError("timeout must be between 0.1 and 3600 seconds")
    matrix_sha256 = _sha256_bytes(matrix_bytes)
    runner_sha256 = _sha256_bytes(
        _canonical_json(
            {
                "runner_fingerprint": runner_fingerprint.sha256,
                "isolation_level": boundary.level,
                "isolation_contract_sha256": boundary.contract_sha256,
                "isolation_executor_sha256": boundary.executor_sha256,
            }
        )
    )

    rows = [
        _run_one(
            spec,
            bank,
            matrix_row,
            matrix_sha256,
            matrix_binding,
            runner,
            runner_sha256,
            runner_fingerprint,
            arguments.timeout,
            boundary,
        )
        for matrix_row in matrix
    ]
    runner_sources_intact = _runner_sources_match(runner_fingerprint)
    executor_intact = _isolation_executor_matches(boundary)
    if (
        not _source_package_matches(spec)
        or not runner_sources_intact
        or not executor_intact
        or not _binding_matches(spec.file_binding, "experiment spec")
        or not _binding_matches(bank.file_binding, "hidden bank")
        or not _binding_matches(matrix_binding, "matrix")
    ):
        for row in rows:
            gates = set(row["failed_hard_gates"])
            gates.add("input_integrity")
            row["failed_hard_gates"] = _gate_list(gates)
            row["hard_gates_passed"] = False
            row["soft_score"] = 0.0
            row["success"] = False
            row["eligible_for_held_out_claims"] = False
            if not executor_intact:
                row["hidden_bank_nonexposure_verified"] = False
                row["network_isolation_verified"] = False
                row["isolation_probes_passed"] = False
    _archive_results(
        output_dir,
        spec,
        bank.file_sha256,
        rows,
        matrix_sha256,
        runner_sha256,
    )
    if any(not row["hard_gates_passed"] for row in rows):
        print(
            "evaluation integrity failure: one or more hard gates failed",
            file=sys.stderr,
        )
        return 5
    return 0


def _command_report(arguments: argparse.Namespace) -> int:
    spec = _validate_spec(Path(arguments.spec))
    rows, results_bytes, results_path = _validate_results(Path(arguments.results), spec)
    if spec.document["eligibility"] == "held_out_external_evaluation":
        raise ValidationError(
            "standalone report cannot authenticate held-out results; use the "
            "report.json emitted atomically by the package-owned run command"
        )
    output = _validate_output_file(
        Path(arguments.output), [*_spec_input_paths(spec), results_path]
    )
    report = _report(spec, rows, results_bytes)
    encoded = _canonical_json(report)
    _atomic_write(output, encoded)
    sys.stdout.buffer.write(encoded)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser(
        "plan", help="create a deterministic paired run matrix"
    )
    plan.add_argument("spec")
    plan.add_argument("--output", required=True)
    plan.set_defaults(handler=_command_plan)

    run = subparsers.add_parser(
        "run", help="execute an explicitly claim-bounded evaluation matrix"
    )
    run.add_argument("spec")
    run.add_argument("matrix")
    run.add_argument(
        "--hidden-bank",
        required=True,
        help="external grader bank (must be public_development_grader in runnable mode)",
    )
    run.add_argument("--runner-json", required=True)
    run.add_argument(
        "--runner-manifest-json",
        help="complete runner file manifest; mandatory for held-out evaluation",
    )
    run.add_argument("--output-dir", required=True)
    run.add_argument("--timeout", type=float, default=60.0)
    isolation = run.add_mutually_exclusive_group()
    isolation.add_argument(
        "--isolation-wrapper-json",
        help="reserved; rejected until a trusted external adapter is implemented",
    )
    isolation.add_argument(
        "--public-fixture-unconfined",
        action="store_true",
        help="run an unconfined public fixture; permanently ineligible for held-out claims",
    )
    isolation.add_argument(
        "--macos-sandbox",
        action="store_true",
        help="use the built-in deny-by-default macOS sandbox-exec boundary",
    )
    run.set_defaults(handler=_command_run)

    report = subparsers.add_parser(
        "report", help="validate results and create a paired report"
    )
    report.add_argument("spec")
    report.add_argument("results")
    report.add_argument("--output", required=True)
    report.set_defaults(handler=_command_report)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    arguments = parser.parse_args(argv)
    try:
        return arguments.handler(arguments)
    except ValidationError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except MacOSSandboxUnavailable as error:
        print(f"sandbox unavailable: {error}", file=sys.stderr)
        return 71
    except KeyboardInterrupt:
        print("error: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
