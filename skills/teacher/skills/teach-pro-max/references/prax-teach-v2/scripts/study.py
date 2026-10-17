#!/usr/bin/env python3
"""Validate, allocate, and analyze Prax Teach parallel learner studies.

Synthetic fixtures verify this machinery. They never establish a human-learning claim.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import math
import os
import random
import stat
import statistics
import sys
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from praxteach.errors import SafetyError as PraxSafetyError
from praxteach.errors import ValidationError as PraxValidationError
from praxteach.io import anchored_file_target, atomic_write_anchored

SCHEMA_VERSION = "1"
REQUIRED_ARMS = ("active-control", "teach", "prax-teach-v2")
REQUIRED_OUTCOMES = ("delayed_retention", "novel_transfer")
MISSING_OUTCOME_POLICY = "baseline_carried_forward_zero_adjusted_change"
ALLOCATION_RECEIPT_VERSION = 1
ALLOCATION_HMAC_PREFIX = "hmac-sha256:"
SCORE_SCHEMA_VERSION = 1
SCORE_SCHEMA_ID = "https://prax.local/prax-teach-v2/study-score.schema.json"
SCORE_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1] / "schemas" / "study-score.schema.json"
)
PROTOCOL_KEYS = {
    "schema_version",
    "study_id",
    "design",
    "seed",
    "arms",
    "primary_outcomes",
    "delay_window_days",
    "confidence_level",
    "bootstrap_samples",
    "synthetic",
    "missing_outcome_policy",
    "competency_claim",
    "evidence",
    "task_bank_hash",
}
TASK_BANK_KEYS = {"schema_version", "study_id", "tasks"}
TASK_KEYS = {"id", "outcome", "prompt", "rubric_ref"}
SCORE_KEYS = {
    "score_schema_version",
    "assessment_id",
    "outcome",
    "task_id",
    "rubric_ref",
    "score",
    "measured_at",
    "blinded_scorer_id",
}


class StudyError(ValueError):
    """Raised when study inputs violate the executable protocol."""


def _reject_non_finite_constant(value: str) -> Any:
    raise ValueError(f"non-finite JSON constant {value} is not allowed")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r} is not allowed")
        result[key] = value
    return result


def _strict_json_loads(value: str) -> Any:
    return json.loads(
        value,
        parse_constant=_reject_non_finite_constant,
        object_pairs_hook=_reject_duplicate_keys,
    )


def _is_finite_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = _strict_json_loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StudyError(f"file not found: {path}") from exc
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise StudyError(f"invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise StudyError(f"expected a JSON object at {path}")
    return value


def load_jsonl_with_bytes(path: Path) -> tuple[list[dict[str, Any]], bytes]:
    rows: list[dict[str, Any]] = []
    try:
        raw = path.read_bytes()
        lines = raw.decode("utf-8").splitlines()
    except FileNotFoundError as exc:
        raise StudyError(f"file not found: {path}") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise StudyError(f"cannot read {path}: {exc}") from exc
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = _strict_json_loads(line)
        except ValueError as exc:
            raise StudyError(f"invalid JSONL at {path}:{line_number}: {exc}") from exc
        if not isinstance(row, dict):
            raise StudyError(f"expected an object at {path}:{line_number}")
        rows.append(row)
    return rows, raw


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return load_jsonl_with_bytes(path)[0]


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def protocol_hash(protocol: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(protocol).encode("utf-8")).hexdigest()


def content_sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def require_score_schema_evidence() -> dict[str, Any]:
    try:
        payload = SCORE_SCHEMA_PATH.read_bytes()
        decoded = _strict_json_loads(payload.decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise StudyError("study score schema is unavailable or malformed") from exc
    properties = decoded.get("properties") if isinstance(decoded, dict) else None
    required = decoded.get("required") if isinstance(decoded, dict) else None
    version_property = (
        properties.get("score_schema_version") if isinstance(properties, dict) else None
    )
    if (
        not isinstance(properties, dict)
        or not isinstance(required, list)
        or any(not isinstance(field, str) for field in required)
        or not isinstance(version_property, dict)
        or decoded.get("$id") != SCORE_SCHEMA_ID
        or decoded.get("additionalProperties") is not False
        or set(required) != SCORE_KEYS
        or set(properties) != SCORE_KEYS
        or version_property.get("const") != SCORE_SCHEMA_VERSION
    ):
        raise StudyError("study score schema does not match the executable contract")
    return {
        "id": SCORE_SCHEMA_ID,
        "version": SCORE_SCHEMA_VERSION,
        "sha256": content_sha256(payload),
    }


def validate_task_bank(
    task_bank: dict[str, Any], protocol: dict[str, Any]
) -> dict[str, dict[str, str]]:
    if set(task_bank) != TASK_BANK_KEYS:
        raise StudyError(
            "task bank must contain exactly schema_version, study_id, and tasks"
        )
    if task_bank["schema_version"] != SCHEMA_VERSION:
        raise StudyError(f"task bank schema_version must be {SCHEMA_VERSION!r}")
    if task_bank["study_id"] != protocol["study_id"]:
        raise StudyError("task bank study_id does not match the frozen protocol")
    raw_tasks = task_bank["tasks"]
    if not isinstance(raw_tasks, list) or not raw_tasks:
        raise StudyError("task bank tasks must be a non-empty list")
    if len(raw_tasks) > 10_000:
        raise StudyError("task bank exceeds the 10000-task safety limit")
    tasks: dict[str, dict[str, str]] = {}
    coverage: set[str] = set()
    for index, task in enumerate(raw_tasks):
        if not isinstance(task, dict) or set(task) != TASK_KEYS:
            raise StudyError(
                f"task bank tasks[{index}] must contain exactly id, outcome, "
                "prompt, and rubric_ref"
            )
        for field in ("id", "prompt", "rubric_ref"):
            if not isinstance(task[field], str) or not task[field].strip():
                raise StudyError(
                    f"task bank tasks[{index}].{field} must be a non-empty string"
                )
        task_id = task["id"]
        if task_id in tasks:
            raise StudyError(f"task bank contains duplicate task id: {task_id}")
        outcome = task["outcome"]
        if outcome not in REQUIRED_OUTCOMES:
            raise StudyError(f"task bank tasks[{index}].outcome is unsupported")
        tasks[task_id] = {
            "outcome": outcome,
            "rubric_ref": task["rubric_ref"],
        }
        coverage.add(outcome)
    missing = sorted(set(REQUIRED_OUTCOMES) - coverage)
    if missing:
        raise StudyError(
            "task bank is missing required primary-outcome coverage: "
            + ", ".join(missing)
        )
    return tasks


def require_task_bank(
    path: Path, protocol: dict[str, Any]
) -> tuple[str, dict[str, dict[str, str]]]:
    try:
        payload = path.read_bytes()
    except (OSError, RuntimeError) as exc:
        raise StudyError("task bank must be a readable regular file") from exc
    if not payload:
        raise StudyError("task bank must not be empty")
    if len(payload) > 100 * 1024 * 1024:
        raise StudyError("task bank exceeds the 100 MiB safety limit")
    digest = content_sha256(payload)
    if not hmac.compare_digest(protocol["task_bank_hash"], f"sha256:{digest}"):
        raise StudyError("task bank digest does not match the frozen protocol")
    try:
        decoded = _strict_json_loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise StudyError(f"task bank must be strict UTF-8 JSON: {exc}") from exc
    if not isinstance(decoded, dict):
        raise StudyError("task bank must be a JSON object")
    return digest, validate_task_bank(decoded, protocol)


def parse_timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise StudyError(f"{field} must be a non-empty ISO-8601 timestamp")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise StudyError(f"{field} is not a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise StudyError(f"{field} must include a timezone")
    return parsed


def validate_protocol(protocol: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    missing_keys = sorted(PROTOCOL_KEYS - set(protocol))
    extra_keys = sorted(set(protocol) - PROTOCOL_KEYS)
    if missing_keys:
        errors.append(
            "protocol is missing required properties: " + ", ".join(missing_keys)
        )
    if extra_keys:
        errors.append(
            "protocol contains additional properties: " + ", ".join(extra_keys)
        )
    if protocol.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION!r}")
    if (
        not isinstance(protocol.get("study_id"), str)
        or not protocol["study_id"].strip()
    ):
        errors.append("study_id must be a non-empty string")
    if protocol.get("design") != "parallel_randomized":
        errors.append(
            "design must be 'parallel_randomized'; acquired knowledge cannot be washed out"
        )
    if protocol.get("arms") != list(REQUIRED_ARMS):
        errors.append(f"arms must be exactly {list(REQUIRED_ARMS)!r}")
    if protocol.get("primary_outcomes") != list(REQUIRED_OUTCOMES):
        errors.append(f"primary_outcomes must be exactly {list(REQUIRED_OUTCOMES)!r}")
    if not isinstance(protocol.get("seed"), int) or isinstance(
        protocol.get("seed"), bool
    ):
        errors.append("seed must be an integer")
    window = protocol.get("delay_window_days")
    if not isinstance(window, dict):
        errors.append("delay_window_days must be an object")
    else:
        window_keys = {"minimum", "maximum"}
        missing_window = sorted(window_keys - set(window))
        extra_window = sorted(set(window) - window_keys)
        if missing_window:
            errors.append(
                "delay_window_days is missing required properties: "
                + ", ".join(missing_window)
            )
        if extra_window:
            errors.append(
                "delay_window_days contains additional properties: "
                + ", ".join(extra_window)
            )
        minimum = window.get("minimum")
        maximum = window.get("maximum")
        if not _is_finite_number(minimum) or minimum <= 0:
            errors.append("delay_window_days.minimum must be > 0")
        if not _is_finite_number(maximum) or maximum < 1:
            errors.append("delay_window_days.maximum must be >= 1")
        if (
            _is_finite_number(minimum)
            and _is_finite_number(maximum)
            and maximum < minimum
        ):
            errors.append("delay_window_days.maximum must be >= minimum")
    confidence = protocol.get("confidence_level")
    if not _is_finite_number(confidence) or not 0.5 <= confidence < 1:
        errors.append("confidence_level must be from 0.5 (inclusive) to 1 (exclusive)")
    samples = protocol.get("bootstrap_samples")
    if not isinstance(samples, int) or isinstance(samples, bool) or samples < 200:
        errors.append("bootstrap_samples must be an integer >= 200")
    for field in ("competency_claim", "evidence"):
        if not isinstance(protocol.get(field), str) or not protocol[field].strip():
            errors.append(f"{field} must be a non-empty string")
    task_hash = protocol.get("task_bank_hash")
    if (
        not isinstance(task_hash, str)
        or not task_hash.startswith("sha256:")
        or len(task_hash) != 71
    ):
        errors.append("task_bank_hash must be sha256:<64 lowercase hex characters>")
    elif any(character not in "0123456789abcdef" for character in task_hash[7:]):
        errors.append("task_bank_hash must use lowercase hexadecimal")
    if not isinstance(protocol.get("synthetic"), bool):
        errors.append("synthetic must be a boolean")
    if protocol.get("missing_outcome_policy") != MISSING_OUTCOME_POLICY:
        errors.append(f"missing_outcome_policy must be {MISSING_OUTCOME_POLICY!r}")
    return {
        "valid": not errors,
        "errors": errors,
        "protocol_sha256": protocol_hash(protocol),
    }


def require_protocol(path: Path) -> dict[str, Any]:
    protocol = load_json(path)
    validation = validate_protocol(protocol)
    if not validation["valid"]:
        raise StudyError("invalid protocol:\n- " + "\n- ".join(validation["errors"]))
    return protocol


def atomic_write(path: Path, data: bytes) -> None:
    try:
        with anchored_file_target(path) as target:
            atomic_write_anchored(target, data, mode=0o600)
    except (PraxSafetyError, PraxValidationError, OSError) as exc:
        raise StudyError(f"race-safe output publication failed: {exc}") from exc


def preflight_study_paths(
    *, inputs: dict[str, Path], outputs: dict[str, Path]
) -> tuple[dict[str, Path], dict[str, Path]]:
    canonical_inputs: dict[str, Path] = {}
    for label, path in inputs.items():
        unresolved = path.expanduser()
        if unresolved.is_symlink():
            raise StudyError(f"{label} input must not be a symlink")
        try:
            canonical = unresolved.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise StudyError(f"{label} input must be a readable file") from exc
        if not canonical.is_file():
            raise StudyError(f"{label} input must be a regular file")
        canonical_inputs[label] = canonical

    exact_outputs: dict[str, Path] = {}
    for label, path in outputs.items():
        unresolved = path.expanduser()
        absolute = unresolved if unresolved.is_absolute() else Path.cwd() / unresolved
        if absolute.is_symlink():
            raise StudyError(f"{label} output must not be a symlink")
        exact = absolute
        if exact.is_symlink():
            raise StudyError(f"{label} output must not be a symlink")
        if exact.exists() and not exact.is_file():
            raise StudyError(f"{label} output must be a regular file")
        exact_outputs[label] = exact

    output_items = list(exact_outputs.items())
    for index, (left_label, left) in enumerate(output_items):
        for right_label, right in output_items[index + 1 :]:
            aliases = left == right
            if not aliases and left.exists() and right.exists():
                try:
                    aliases = os.path.samefile(left, right)
                except OSError:
                    aliases = False
            if aliases:
                raise StudyError(
                    f"output paths {left_label} and {right_label} must be distinct"
                )

    for output_label, output in output_items:
        for input_label, input_path in canonical_inputs.items():
            aliases = output == input_path
            if not aliases and output.exists():
                try:
                    aliases = os.path.samefile(output, input_path)
                except OSError:
                    aliases = False
            if aliases:
                raise StudyError(
                    f"{output_label} output would overwrite input {input_label}"
                )
    return canonical_inputs, exact_outputs


def jsonl_bytes(rows: Iterable[dict[str, Any]]) -> bytes:
    return ("".join(canonical_json(row) + "\n" for row in rows)).encode("utf-8")


def _private_key_path(path: Path) -> Path:
    raw = path.expanduser()
    absolute = raw if raw.is_absolute() else Path.cwd() / raw
    if ".." in absolute.parts:
        raise StudyError("blinding key path traversal is not allowed")
    if os.name != "posix" or len(absolute.parts) < 2:
        return absolute
    first = Path(absolute.anchor) / absolute.parts[1]
    try:
        first_stat = first.lstat()
    except OSError:
        return absolute
    if not stat.S_ISLNK(first_stat.st_mode):
        return absolute
    root_stat = Path(absolute.anchor).stat()
    if (
        first_stat.st_uid != 0
        or root_stat.st_uid != 0
        or stat.S_IMODE(root_stat.st_mode) & 0o022
    ):
        raise StudyError("blinding key path contains an untrusted root alias")
    try:
        resolved_first = first.resolve(strict=True)
    except OSError as exc:
        raise StudyError("blinding key root alias cannot be resolved safely") from exc
    if not resolved_first.is_dir():
        raise StudyError("blinding key root alias is not a directory")
    return resolved_first.joinpath(*absolute.parts[2:])


def _validate_private_key_ancestors(path: Path, owner_uid: int) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:-1]:
        current /= part
        try:
            metadata = current.lstat()
        except OSError as exc:
            raise StudyError("blinding key ancestor is not safely readable") from exc
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise StudyError("blinding key ancestor must not be a symlink")
        if metadata.st_uid not in {0, owner_uid}:
            raise StudyError("blinding key ancestor has an untrusted owner")
        mode = stat.S_IMODE(metadata.st_mode)
        if mode & 0o022:
            trusted_sticky_root = metadata.st_uid == 0 and bool(mode & stat.S_ISVTX)
            if not trusted_sticky_root:
                raise StudyError(
                    "blinding key ancestor must not be group/world writable"
                )


def load_blinding_key(path: Path) -> bytes:
    unresolved = _private_key_path(path)
    owner_uid = (
        os.geteuid()
        if hasattr(os, "geteuid")
        else os.getuid()
        if hasattr(os, "getuid")
        else 0
    )
    if os.name == "posix":
        _validate_private_key_ancestors(unresolved, owner_uid)
    try:
        metadata = unresolved.lstat()
    except OSError as exc:
        raise StudyError("blinding key must be a readable regular file") from exc
    if stat.S_ISLNK(metadata.st_mode):
        raise StudyError("blinding key must not be a symlink")
    if not stat.S_ISREG(metadata.st_mode):
        raise StudyError("blinding key must be a regular file")
    if os.name == "posix":
        if metadata.st_uid != owner_uid:
            raise StudyError("blinding key must be owned by the current user")
        mode = stat.S_IMODE(metadata.st_mode)
        if mode & 0o077 or not mode & stat.S_IRUSR or mode & 0o111:
            raise StudyError(
                "blinding key must use a private 0600-style permission mode"
            )
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    descriptor: int | None = None
    try:
        descriptor = os.open(unresolved, flags)
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (metadata.st_dev, metadata.st_ino):
            raise StudyError("blinding key changed during validation")
        payload = os.read(descriptor, 4097)
        if os.read(descriptor, 1):
            raise StudyError("blinding key exceeds the 4096-byte safety limit")
    except OSError as exc:
        raise StudyError("blinding key must be a readable regular file") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    if not 32 <= len(payload) <= 4096:
        raise StudyError("blinding key must contain between 32 and 4096 bytes")
    return payload


def build_allocations(
    protocol: dict[str, Any],
    participants: list[dict[str, Any]],
    blinding_key: bytes,
    *,
    participant_roster_sha256: str,
    task_bank_sha256: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not participants:
        raise StudyError("participants must not be empty")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(participants):
        participant_id = row.get("participant_id")
        if not isinstance(participant_id, str) or not participant_id.strip():
            raise StudyError(
                f"participants[{index}].participant_id must be a non-empty string"
            )
        if participant_id in seen:
            raise StudyError(f"duplicate participant_id: {participant_id}")
        seen.add(participant_id)
        pretest = row.get("pretest")
        if not _is_finite_number(pretest) or not 0 <= pretest <= 1:
            raise StudyError(f"participants[{index}].pretest must be from 0 to 1")
        parse_timestamp(
            row.get("instruction_at"), f"participants[{index}].instruction_at"
        )
        normalized.append(
            {
                "participant_id": participant_id,
                "pretest": float(pretest),
                "instruction_at": row["instruction_at"],
            }
        )

    rng = random.Random(protocol["seed"])
    rng.shuffle(normalized)
    allocation_rows: list[dict[str, Any]] = []
    p_hash = protocol_hash(protocol)
    for index, participant in enumerate(normalized):
        arm = REQUIRED_ARMS[index % len(REQUIRED_ARMS)]
        opaque = hmac.new(
            blinding_key,
            f"{p_hash}\0{participant['participant_id']}\0assessment".encode(),
            hashlib.sha256,
        ).hexdigest()[:24]
        assessment_id = f"asm-{opaque}"
        allocation_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "allocation_receipt_version": ALLOCATION_RECEIPT_VERSION,
                "study_id": protocol["study_id"],
                "protocol_sha256": p_hash,
                "participant_roster_sha256": participant_roster_sha256,
                "task_bank_sha256": task_bank_sha256,
                "participant_id": participant["participant_id"],
                "assessment_id": assessment_id,
                "arm": arm,
                "pretest": participant["pretest"],
                "instruction_at": participant["instruction_at"],
            }
        )
    allocation_rows.sort(key=lambda row: row["participant_id"])
    receipt_payload = canonical_json(
        {
            "allocation_receipt_version": ALLOCATION_RECEIPT_VERSION,
            "protocol_sha256": p_hash,
            "participant_roster_sha256": participant_roster_sha256,
            "task_bank_sha256": task_bank_sha256,
            "allocations": allocation_rows,
        }
    ).encode("utf-8")
    allocation_set_hmac = (
        ALLOCATION_HMAC_PREFIX
        + hmac.new(
            blinding_key,
            b"prax-teach-v2-study-allocation-set-v1\0" + receipt_payload,
            hashlib.sha256,
        ).hexdigest()
    )
    allocation_rows = [
        {**row, "allocation_set_hmac_sha256": allocation_set_hmac}
        for row in allocation_rows
    ]
    blind_rows = [
        {
            "schema_version": SCHEMA_VERSION,
            "allocation_receipt_version": ALLOCATION_RECEIPT_VERSION,
            "study_id": protocol["study_id"],
            "assessment_id": row["assessment_id"],
            "primary_outcomes": list(REQUIRED_OUTCOMES),
            "task_bank_sha256": task_bank_sha256,
            "allocation_set_hmac_sha256": allocation_set_hmac,
        }
        for row in allocation_rows
    ]
    blind_rows.sort(key=lambda row: row["assessment_id"])
    return allocation_rows, blind_rows


def authenticate_allocations(
    allocations: list[dict[str, Any]],
    expected_allocations: list[dict[str, Any]],
) -> dict[str, Any]:
    if not expected_allocations:
        raise StudyError("authenticated allocation set must not be empty")
    if not hmac.compare_digest(
        jsonl_bytes(allocations), jsonl_bytes(expected_allocations)
    ):
        raise StudyError(
            "allocation authentication failed: assignments do not match the "
            "keyed participant/protocol/task-bank allocation receipt"
        )
    allocation_set_hmac = expected_allocations[0]["allocation_set_hmac_sha256"]
    if any(
        row.get("allocation_set_hmac_sha256") != allocation_set_hmac
        for row in expected_allocations
    ):
        raise StudyError("allocation authentication failed: mixed receipt HMACs")
    return {
        "authority": "external_blinding_key_hmac_sha256",
        "allocation_receipt_version": ALLOCATION_RECEIPT_VERSION,
        "allocation_set_hmac_sha256": allocation_set_hmac,
        "participant_roster_sha256": expected_allocations[0][
            "participant_roster_sha256"
        ],
        "task_bank_sha256": expected_allocations[0]["task_bank_sha256"],
        "allocation_count": len(expected_allocations),
    }


def quantile(values: list[float], probability: float) -> float:
    if not values:
        return math.nan
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def bootstrap_difference(
    candidate: list[float],
    comparison: list[float],
    *,
    seed: int,
    samples: int,
    confidence: float,
) -> dict[str, float | int | None]:
    if not candidate or not comparison:
        return {
            "estimate": None,
            "lower": None,
            "upper": None,
            "candidate_n": len(candidate),
            "comparison_n": len(comparison),
        }
    estimate = statistics.fmean(candidate) - statistics.fmean(comparison)
    rng = random.Random(seed)
    draws: list[float] = []
    for _ in range(samples):
        c_draw = [rng.choice(candidate) for _ in candidate]
        o_draw = [rng.choice(comparison) for _ in comparison]
        draws.append(statistics.fmean(c_draw) - statistics.fmean(o_draw))
    alpha = 1 - confidence
    return {
        "estimate": estimate,
        "lower": quantile(draws, alpha / 2),
        "upper": quantile(draws, 1 - alpha / 2),
        "candidate_n": len(candidate),
        "comparison_n": len(comparison),
    }


def validate_and_deduplicate_scores(
    scores: list[dict[str, Any]],
    task_bank: dict[str, dict[str, str]],
) -> tuple[list[dict[str, Any]], int]:
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    duplicate_count = 0
    for index, row in enumerate(scores):
        if set(row) != SCORE_KEYS:
            raise StudyError(
                f"scores[{index}] must contain exactly " + ", ".join(sorted(SCORE_KEYS))
            )
        if row["score_schema_version"] != SCORE_SCHEMA_VERSION:
            raise StudyError(f"scores[{index}] has unsupported score_schema_version")
        for field in (
            "assessment_id",
            "outcome",
            "task_id",
            "rubric_ref",
            "measured_at",
            "blinded_scorer_id",
        ):
            if not isinstance(row[field], str) or not row[field].strip():
                raise StudyError(f"scores[{index}].{field} must be non-empty")
        task = task_bank.get(row["task_id"])
        if task is None:
            raise StudyError(f"scores[{index}] cites an unknown task_id")
        if row["outcome"] != task["outcome"]:
            raise StudyError(f"scores[{index}] outcome does not match its task")
        if row["rubric_ref"] != task["rubric_ref"]:
            raise StudyError(f"scores[{index}] rubric_ref does not match its task")
        score = row["score"]
        if not _is_finite_number(score) or not 0 <= score <= 1:
            raise StudyError(f"scores[{index}].score must be from 0 to 1")
        measured = parse_timestamp(row["measured_at"], f"scores[{index}].measured_at")
        measured_utc = (
            measured.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        )
        normalized = {
            "score_schema_version": SCORE_SCHEMA_VERSION,
            "assessment_id": row["assessment_id"],
            "outcome": row["outcome"],
            "task_id": row["task_id"],
            "rubric_ref": row["rubric_ref"],
            "score": float(score),
            "measured_at": measured_utc,
            "blinded_scorer_id": row["blinded_scorer_id"],
        }
        key = (normalized["assessment_id"], normalized["outcome"])
        existing = by_key.get(key)
        if existing is not None:
            if existing != normalized:
                raise StudyError(
                    "conflicting duplicate score for assessment_id/outcome"
                )
            duplicate_count += 1
            continue
        by_key[key] = normalized
    ordered = [by_key[key] for key in sorted(by_key)]
    return ordered, duplicate_count


def analyze(
    protocol: dict[str, Any],
    allocations: list[dict[str, Any]],
    scores: list[dict[str, Any]],
    allocation_evidence: dict[str, Any],
    task_bank: dict[str, dict[str, str]],
    scores_source_sha256: str,
) -> dict[str, Any]:
    p_hash = protocol_hash(protocol)
    score_schema = require_score_schema_evidence()
    by_assessment: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(allocations):
        if row.get("protocol_sha256") != p_hash:
            raise StudyError(f"allocations[{index}] protocol hash does not match")
        assessment_id = row.get("assessment_id")
        if not isinstance(assessment_id, str) or assessment_id in by_assessment:
            raise StudyError(
                f"allocations[{index}] has missing or duplicate assessment_id"
            )
        if row.get("arm") not in REQUIRED_ARMS:
            raise StudyError(f"allocations[{index}] has invalid arm")
        by_assessment[assessment_id] = row

    minimum = float(protocol["delay_window_days"]["minimum"])
    maximum = float(protocol["delay_window_days"]["maximum"])
    validated_scores, duplicate_scores = validate_and_deduplicate_scores(
        scores, task_bank
    )
    accepted: dict[tuple[str, str], float] = {}
    out_of_window = 0
    invalid_scores = 0
    for row in validated_scores:
        assessment_id = row["assessment_id"]
        outcome = row["outcome"]
        if assessment_id not in by_assessment:
            invalid_scores += 1
            continue
        instruction = parse_timestamp(
            by_assessment[assessment_id]["instruction_at"], "instruction_at"
        )
        measured = parse_timestamp(row["measured_at"], "score.measured_at")
        elapsed_days = (measured - instruction).total_seconds() / 86400
        if elapsed_days < minimum or elapsed_days > maximum:
            out_of_window += 1
            continue
        key = (assessment_id, outcome)
        accepted[key] = row["score"]

    adjusted: dict[str, dict[str, list[float]]] = {
        arm: {outcome: [] for outcome in REQUIRED_OUTCOMES} for arm in REQUIRED_ARMS
    }
    intention_to_treat: dict[str, dict[str, list[float]]] = {
        arm: {outcome: [] for outcome in REQUIRED_OUTCOMES} for arm in REQUIRED_ARMS
    }
    # Preserve the randomized learner as the sampling unit.  Outcome-specific
    # analyses use one score per learner; the descriptive aggregate first
    # averages the available adjusted outcomes within each learner and only
    # then bootstraps learners.  Flattening outcomes would incorrectly treat
    # two correlated observations from one learner as independent samples.
    adjusted_by_learner: dict[str, list[float]] = {arm: [] for arm in REQUIRED_ARMS}
    intention_to_treat_by_learner: dict[str, list[float]] = {
        arm: [] for arm in REQUIRED_ARMS
    }
    completed_any: set[str] = set()
    completed_all: set[str] = set()
    for assessment_id, allocation in by_assessment.items():
        available = [
            outcome
            for outcome in REQUIRED_OUTCOMES
            if (assessment_id, outcome) in accepted
        ]
        if available:
            completed_any.add(assessment_id)
        if len(available) == len(REQUIRED_OUTCOMES):
            completed_all.add(assessment_id)
        learner_adjusted: list[float] = []
        learner_itt: list[float] = []
        arm = allocation["arm"]
        pretest = float(allocation["pretest"])
        for outcome in REQUIRED_OUTCOMES:
            value = (
                accepted[(assessment_id, outcome)] - pretest
                if outcome in available
                else 0.0
            )
            intention_to_treat[arm][outcome].append(value)
            learner_itt.append(value)
        for outcome in available:
            value = accepted[(assessment_id, outcome)] - pretest
            adjusted[arm][outcome].append(value)
            learner_adjusted.append(value)
        if learner_adjusted:
            adjusted_by_learner[arm].append(statistics.fmean(learner_adjusted))
        intention_to_treat_by_learner[arm].append(statistics.fmean(learner_itt))

    comparisons: dict[str, Any] = {}
    for comparison_arm in ("active-control", "teach"):
        by_outcome: dict[str, Any] = {}
        for outcome_index, outcome in enumerate(REQUIRED_OUTCOMES):
            candidate = intention_to_treat["prax-teach-v2"][outcome]
            other = intention_to_treat[comparison_arm][outcome]
            by_outcome[outcome] = bootstrap_difference(
                candidate,
                other,
                seed=protocol["seed"] + outcome_index,
                samples=protocol["bootstrap_samples"],
                confidence=protocol["confidence_level"],
            )
        comparisons[f"prax-teach-v2_vs_{comparison_arm}"] = {
            "by_outcome": by_outcome,
            "complete_case_sensitivity_by_outcome": {
                outcome: bootstrap_difference(
                    adjusted["prax-teach-v2"][outcome],
                    adjusted[comparison_arm][outcome],
                    seed=protocol["seed"] + 200 + outcome_index,
                    samples=protocol["bootstrap_samples"],
                    confidence=protocol["confidence_level"],
                )
                for outcome_index, outcome in enumerate(REQUIRED_OUTCOMES)
            },
            "descriptive_aggregate": bootstrap_difference(
                intention_to_treat_by_learner["prax-teach-v2"],
                intention_to_treat_by_learner[comparison_arm],
                seed=protocol["seed"] + 99,
                samples=protocol["bootstrap_samples"],
                confidence=protocol["confidence_level"],
            ),
            "descriptive_aggregate_method": (
                "intention-to-treat mean adjusted primary-outcome score per assigned "
                "learner, with missing outcomes set to zero adjusted change, followed "
                "by a seeded learner-level bootstrap"
            ),
            "complete_case_sensitivity_aggregate": bootstrap_difference(
                adjusted_by_learner["prax-teach-v2"],
                adjusted_by_learner[comparison_arm],
                seed=protocol["seed"] + 299,
                samples=protocol["bootstrap_samples"],
                confidence=protocol["confidence_level"],
            ),
        }

    assigned = len(allocations)
    result = {
        "schema_version": SCHEMA_VERSION,
        "study_id": protocol["study_id"],
        "protocol_sha256": p_hash,
        "analysis_unit": "assigned_learner",
        "estimand": "intention_to_treat_adjusted_score_difference",
        "missing_outcome_policy": MISSING_OUTCOME_POLICY,
        "synthetic": protocol["synthetic"],
        "claim_status": "synthetic_machinery_test_only"
        if protocol["synthetic"]
        else "descriptive_analysis_requires_preregistered_interpretation",
        "supports_human_learning_claim": False,
        "allocation_evidence": allocation_evidence,
        "score_import_evidence": {
            "score_schema": score_schema,
            "source_sha256": scores_source_sha256,
            "source_row_count": len(scores),
            "deduplicated_row_count": len(validated_scores),
            "validated_scores_sha256": content_sha256(jsonl_bytes(validated_scores)),
            "task_bindings": [
                {
                    "task_id": task_id,
                    "outcome": task_bank[task_id]["outcome"],
                    "rubric_ref": task_bank[task_id]["rubric_ref"],
                }
                for task_id in sorted(task_bank)
            ],
        },
        "window_days": {"minimum": minimum, "maximum": maximum},
        "fidelity": {
            "accepted_scores": len(accepted),
            "out_of_window_scores": out_of_window,
            "invalid_scores": invalid_scores,
            "duplicate_scores": duplicate_scores,
        },
        "attrition": {
            "assigned": assigned,
            "with_any_primary_outcome": len(completed_any),
            "with_all_primary_outcomes": len(completed_all),
            "overall_rate": (assigned - len(completed_all)) / assigned
            if assigned
            else None,
        },
        "arm_counts": {
            arm: sum(row["arm"] == arm for row in allocations) for arm in REQUIRED_ARMS
        },
        "comparisons": comparisons,
        "interpretation_warning": "Synthetic/public machinery tests cannot establish immediate, delayed, transfer, accessibility, or generalization claims.",
    }
    return result


def command_validate(args: argparse.Namespace) -> int:
    protocol = load_json(args.protocol)
    result = validate_protocol(protocol)
    print(json.dumps(result, allow_nan=False, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


def command_allocate(args: argparse.Namespace) -> int:
    blinding_key = load_blinding_key(args.blinding_key)
    inputs, outputs = preflight_study_paths(
        inputs={
            "protocol": args.protocol,
            "participants": args.participants,
            "task_bank": args.task_bank,
            "blinding_key": args.blinding_key,
        },
        outputs={
            "private_output": args.private_output,
            "blind_output": args.blind_output,
        },
    )
    protocol = require_protocol(inputs["protocol"])
    participants, participant_bytes = load_jsonl_with_bytes(inputs["participants"])
    task_bank_sha256, _ = require_task_bank(inputs["task_bank"], protocol)
    participant_roster_sha256 = content_sha256(participant_bytes)
    allocations, blind = build_allocations(
        protocol,
        participants,
        blinding_key,
        participant_roster_sha256=participant_roster_sha256,
        task_bank_sha256=task_bank_sha256,
    )
    atomic_write(outputs["private_output"], jsonl_bytes(allocations))
    atomic_write(outputs["blind_output"], jsonl_bytes(blind))
    print(
        json.dumps(
            {
                "status": "allocated",
                "participants": len(allocations),
                "private_output": str(outputs["private_output"]),
                "blind_output": str(outputs["blind_output"]),
                "protocol_sha256": protocol_hash(protocol),
                "participant_roster_sha256": participant_roster_sha256,
                "task_bank_sha256": task_bank_sha256,
                "allocation_set_hmac_sha256": allocations[0][
                    "allocation_set_hmac_sha256"
                ],
                "blinding_scheme": "HMAC-SHA-256 with private external key",
            },
            allow_nan=False,
            sort_keys=True,
        )
    )
    return 0


def command_analyze(args: argparse.Namespace) -> int:
    blinding_key = load_blinding_key(args.blinding_key)
    inputs, outputs = preflight_study_paths(
        inputs={
            "protocol": args.protocol,
            "participants": args.participants,
            "allocations": args.allocations,
            "scores": args.scores,
            "task_bank": args.task_bank,
            "blinding_key": args.blinding_key,
        },
        outputs={"output": args.output},
    )
    protocol = require_protocol(inputs["protocol"])
    participants, participant_bytes = load_jsonl_with_bytes(inputs["participants"])
    task_bank_sha256, task_bank = require_task_bank(inputs["task_bank"], protocol)
    expected_allocations, _ = build_allocations(
        protocol,
        participants,
        blinding_key,
        participant_roster_sha256=content_sha256(participant_bytes),
        task_bank_sha256=task_bank_sha256,
    )
    allocations = load_jsonl(inputs["allocations"])
    allocation_evidence = authenticate_allocations(allocations, expected_allocations)
    scores, scores_bytes = load_jsonl_with_bytes(inputs["scores"])
    report = analyze(
        protocol,
        allocations,
        scores,
        allocation_evidence,
        task_bank,
        content_sha256(scores_bytes),
    )
    atomic_write(
        outputs["output"],
        (json.dumps(report, allow_nan=False, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        ),
    )
    print(
        json.dumps(
            {
                "status": "analyzed",
                "output": str(outputs["output"]),
                "claim_status": report["claim_status"],
            },
            allow_nan=False,
            sort_keys=True,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser(
        "validate", help="validate a frozen study protocol"
    )
    validate.add_argument("protocol", type=Path)
    validate.set_defaults(handler=command_validate)

    allocate = subparsers.add_parser(
        "allocate", help="create private assignments and a blind assessment roster"
    )
    allocate.add_argument("protocol", type=Path)
    allocate.add_argument("participants", type=Path)
    allocate.add_argument("private_output", type=Path)
    allocate.add_argument("blind_output", type=Path)
    allocate.add_argument(
        "--task-bank",
        type=Path,
        required=True,
        help="external hidden assessment-task bank matching protocol.task_bank_hash",
    )
    allocate.add_argument(
        "--blinding-key",
        type=Path,
        required=True,
        help="private external file containing at least 32 random bytes",
    )
    allocate.set_defaults(handler=command_allocate)

    analyze_parser = subparsers.add_parser(
        "analyze", help="analyze blind scores using assigned learners"
    )
    analyze_parser.add_argument("protocol", type=Path)
    analyze_parser.add_argument("allocations", type=Path)
    analyze_parser.add_argument("scores", type=Path)
    analyze_parser.add_argument("output", type=Path)
    analyze_parser.add_argument(
        "--participants",
        type=Path,
        required=True,
        help="exact participant roster used for allocation",
    )
    analyze_parser.add_argument(
        "--task-bank",
        type=Path,
        required=True,
        help="external hidden assessment-task bank matching protocol.task_bank_hash",
    )
    analyze_parser.add_argument(
        "--blinding-key",
        type=Path,
        required=True,
        help="same private external key used for allocation authentication",
    )
    analyze_parser.set_defaults(handler=command_analyze)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except StudyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
