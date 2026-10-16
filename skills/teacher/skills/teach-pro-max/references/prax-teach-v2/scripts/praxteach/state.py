"""Consent, append-only evidence, and deterministic learner projections."""

from __future__ import annotations

import base64
import contextlib
import hashlib
import json
import math
import os
import re
import shutil
import stat
from collections import defaultdict
from collections.abc import Iterable
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from . import CORE_VERSION, SCHEMA_VERSION
from .errors import ConsentRequired, SafetyError, ValidationError
from .io import (
    _ACTIVE_WORKSPACE_IO,
    PRIVATE_DIR_MODE,
    atomic_write,
    atomic_write_json,
    canonical_json_bytes,
    canonical_json_line,
    fsync_directory,
    make_private_directory,
    make_private_file,
    prepare_new_workspace,
    prepare_private_parent,
    read_bytes,
    read_json,
    read_jsonl,
    secure_workspace,
    workspace_generation_lock,
    workspace_lock,
)

DIMENSIONS = (
    "recognition",
    "recall",
    "explanation",
    "application",
    "discrimination",
    "transfer",
)
HIGHER_ORDER_DIMENSIONS = frozenset({"application", "discrimination", "transfer"})
POSITIVE_SCORE = 0.8
CONTRADICTORY_SCORE = 0.6
MAX_HINT_LEVEL = 4
CONTENT_VERSION_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SOURCE_TYPES = (
    "official-doc",
    "primary-study",
    "review",
    "repository",
    "social",
)
DELETE_TRANSACTION_NAME = ".delete-transaction.json"
STATE_TRANSACTION_NAME = ".state-transaction.json"
FULL_DELETE_TRANSACTION_NAME = ".full-delete-transaction.json"
DELETE_TARGET_FILES = (
    "sessions.jsonl",
    "reviews.jsonl",
    "concepts.json",
    "misconceptions.json",
)
STATE_TARGET_FILES = (
    "sessions.jsonl",
    "reviews.jsonl",
    "concepts.json",
    "misconceptions.json",
)


def _exact_fields(value: dict[str, Any], expected: set[str], *, label: str) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    unsupported = sorted(actual - expected)
    if missing:
        raise ValidationError(
            f"{label} is missing required field(s): {', '.join(missing)}"
        )
    if unsupported:
        raise ValidationError(
            f"{label} contains unsupported field(s): {', '.join(unsupported)}"
        )


def normalize_timestamp(value: Any) -> str:
    """Validate an ISO-8601 timestamp and serialize one fixed-width UTC form."""

    if not isinstance(value, str):
        raise ValidationError("timestamp must be a string")
    candidate = value.strip()
    if not candidate:
        raise ValidationError("timestamp must not be empty")
    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"invalid ISO-8601 timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise ValidationError("timestamp must include a UTC offset")
    utc = parsed.astimezone(timezone.utc)
    return utc.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _timestamp_key(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _require_text(name: str, value: Any, *, maximum: int = 2000) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{name} must not be empty")
    if len(normalized) > maximum:
        raise ValidationError(f"{name} exceeds the {maximum}-character limit")
    if "\x00" in normalized:
        raise ValidationError(f"{name} contains a NUL byte")
    return normalized


def _require_preserved_text(name: str, value: Any, *, maximum: int) -> str:
    """Validate learner-authored text without changing its stored bytes."""

    if not isinstance(value, str):
        raise ValidationError(f"{name} must be a string")
    if not value.strip():
        raise ValidationError(f"{name} must not be empty")
    if len(value) > maximum:
        raise ValidationError(f"{name} exceeds the {maximum}-character limit")
    if "\x00" in value:
        raise ValidationError(f"{name} contains a NUL byte")
    return value


def _require_identifier(name: str, value: Any) -> str:
    normalized = _require_text(name, value, maximum=128)
    if not SAFE_IDENTIFIER_RE.fullmatch(normalized):
        raise ValidationError(
            f"{name} must be a pseudonymous identifier using letters, numbers, '.', '_', ':', or '-'"
        )
    return normalized


def _event_id(event_without_id: dict[str, Any]) -> str:
    encoded = json.dumps(
        event_without_id,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")
    return "evt-" + hashlib.sha256(encoded).hexdigest()[:32]


def _empty_concepts() -> dict[str, Any]:
    return {
        "algorithm": {
            "name": "transparent-evidence-projection",
            "version": CORE_VERSION,
        },
        "concepts": [],
        "schema_version": SCHEMA_VERSION,
    }


def _empty_misconceptions() -> dict[str, Any]:
    return {
        "algorithm": {
            "name": "learner-reasoning-misconception-projection",
            "version": CORE_VERSION,
        },
        "misconceptions": [],
        "schema_version": SCHEMA_VERSION,
    }


def initialize_workspace(
    path: str,
    *,
    learner_id: str,
    goal: str,
    horizon_days: int,
    granted_at: str,
) -> tuple[Path, dict[str, Any]]:
    """Create the first durable byte only after the caller has consent."""

    learner = _require_identifier("learner_id", learner_id)
    goal_statement = _require_text("goal", goal)
    if horizon_days < 1 or horizon_days > 3650:
        raise ValidationError("horizon_days must be between 1 and 3650")
    timestamp = normalize_timestamp(granted_at)
    candidate = prepare_private_parent(path)
    with workspace_generation_lock(candidate):
        # A confirmed deletion owns this pathname until its durable parent
        # tombstone is cleared. Finish that generation before allowing reuse.
        _recover_quarantined_workspace_deletion(candidate)
        workspace = prepare_new_workspace(candidate)
        return _create_workspace_locked(
            workspace,
            learner=learner,
            goal_statement=goal_statement,
            horizon_days=horizon_days,
            timestamp=timestamp,
        )


def _create_workspace_locked(
    workspace: Path,
    *,
    learner: str,
    goal_statement: str,
    horizon_days: int,
    timestamp: str,
) -> tuple[Path, dict[str, Any]]:
    """Create workspace contents while the parent generation is locked."""

    created = False
    try:
        workspace.mkdir(mode=PRIVATE_DIR_MODE)
        created = True
        os.chmod(workspace, PRIVATE_DIR_MODE)
        state = workspace / "state"
        make_private_directory(state)
        # Keep the documented course workspace stable from the first consented
        # write. These directories are intentionally empty until reviewed
        # lesson, reference, or asset material is added.
        for directory_name in ("assets", "lessons", "reference"):
            make_private_directory(workspace / directory_name)

        consent = {
            "controls": ["inspect", "correct", "export", "delete"],
            "granted_at": timestamp,
            "location": str(workspace),
            "persistent_state": True,
            "purpose": "Adapt future teaching from the approved goal, practice evidence, and reviews.",
            "scope": ["goal", "practice_evidence", "reviews"],
        }
        learner_document = {
            "consent": consent,
            "goal": {
                "retention_horizon_days": horizon_days,
                "statement": goal_statement,
                "target_performance": goal_statement,
            },
            "learner_id": learner,
            "schema_version": SCHEMA_VERSION,
        }
        mission = (
            "# Learning mission\n\n"
            f"- Goal: {goal_statement}\n"
            f"- Independent-performance horizon: {horizon_days} days\n"
            "- Evidence policy: observed practice only; no inferred traits\n"
        ).encode()
        resources = (
            b"# Resources\n\n"
            b"No source has been approved yet. Add reviewed sources before using them as teaching evidence.\n"
        )

        make_private_file(workspace / "MISSION.md", mission)
        make_private_file(workspace / "RESOURCES.md", resources)
        make_private_file(
            state / "learner.json", canonical_json_bytes(learner_document)
        )
        make_private_file(state / "sessions.jsonl")
        make_private_file(
            state / "concepts.json", canonical_json_bytes(_empty_concepts())
        )
        make_private_file(
            state / "misconceptions.json", canonical_json_bytes(_empty_misconceptions())
        )
        make_private_file(state / "reviews.jsonl")
        make_private_file(
            state / "sources.json",
            canonical_json_bytes({"schema_version": SCHEMA_VERSION, "sources": []}),
        )
        fsync_directory(state)
        for directory_name in ("assets", "lessons", "reference"):
            fsync_directory(workspace / directory_name)
        fsync_directory(workspace)
        return workspace, learner_document
    except Exception:
        if created and workspace.exists() and not workspace.is_symlink():
            shutil.rmtree(workspace)
        raise


def validate_learner_document(
    document: Any, *, require_active: bool = True
) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise ValidationError("learner.json must contain an object")
    _exact_fields(
        document,
        {"consent", "goal", "learner_id", "schema_version"},
        label="learner document",
    )
    if document.get("schema_version") != SCHEMA_VERSION:
        raise ValidationError("unsupported learner schema_version")
    _require_identifier("learner_id", document.get("learner_id"))
    consent = document.get("consent")
    if not isinstance(consent, dict):
        raise ValidationError("learner consent must be an object")
    persistent_state = consent.get("persistent_state")
    consent_fields = {
        "controls",
        "granted_at",
        "location",
        "persistent_state",
        "purpose",
        "scope",
    }
    if persistent_state is False:
        consent_fields |= {"disabled_at", "disable_reason"}
    _exact_fields(consent, consent_fields, label="learner consent")
    if not isinstance(persistent_state, bool):
        raise ValidationError("learner persistence consent must be boolean")
    if persistent_state is False:
        normalize_timestamp(consent.get("disabled_at"))
        _require_text(
            "consent.disable_reason",
            consent.get("disable_reason"),
            maximum=1000,
        )
    if require_active and persistent_state is not True:
        raise ConsentRequired("learner workspace has no active persistence consent")
    required_scope = {"goal", "practice_evidence", "reviews"}
    scope = consent.get("scope")
    if not isinstance(scope, list) or not all(isinstance(item, str) for item in scope):
        raise ValidationError("learner consent scope is incomplete")
    if set(scope) != required_scope or len(scope) != len(set(scope)):
        raise ValidationError("learner consent scope is incomplete")
    normalize_timestamp(consent.get("granted_at"))
    controls = consent.get("controls")
    if not isinstance(controls, list) or not all(
        isinstance(item, str) for item in controls
    ):
        raise ValidationError("learner consent controls are incomplete")
    if (
        not isinstance(controls, list)
        or len(controls) != len(set(controls))
        or set(controls)
        != {
            "inspect",
            "correct",
            "export",
            "delete",
        }
    ):
        raise ValidationError("learner consent controls are incomplete")
    _require_text("consent.location", consent.get("location"), maximum=4096)
    _require_text("consent.purpose", consent.get("purpose"), maximum=2000)
    goal = document.get("goal")
    if not isinstance(goal, dict):
        raise ValidationError("learner goal must be an object")
    _exact_fields(
        goal,
        {"retention_horizon_days", "statement", "target_performance"},
        label="learner goal",
    )
    _require_text("goal.statement", goal.get("statement"))
    _require_text("goal.target_performance", goal.get("target_performance"))
    horizon = goal.get("retention_horizon_days")
    if (
        not isinstance(horizon, int)
        or isinstance(horizon, bool)
        or not 1 <= horizon <= 3650
    ):
        raise ValidationError("learner retention horizon is invalid")
    return document


def _validate_source_record(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValidationError("source record must be an object")
    _exact_fields(
        record,
        {
            "author_or_publisher",
            "license_or_use_note",
            "limitations",
            "retrieved_at",
            "source_id",
            "source_type",
            "supports",
            "title",
            "url",
            "version_or_date",
        },
        label="source record",
    )
    _require_identifier("source_id", record.get("source_id"))
    _require_text("source title", record.get("title"), maximum=1000)
    _require_text(
        "source author_or_publisher",
        record.get("author_or_publisher"),
        maximum=1000,
    )
    if record.get("source_type") not in SOURCE_TYPES:
        raise ValidationError(f"source_type must be one of: {', '.join(SOURCE_TYPES)}")
    retrieved_at = record.get("retrieved_at")
    if not isinstance(retrieved_at, str):
        raise ValidationError("source retrieved_at must be an ISO-8601 date")
    try:
        parsed_date = date.fromisoformat(retrieved_at)
    except ValueError as exc:
        raise ValidationError("source retrieved_at must be an ISO-8601 date") from exc
    if parsed_date.isoformat() != retrieved_at:
        raise ValidationError("source retrieved_at must use canonical YYYY-MM-DD")
    _require_text("source version_or_date", record.get("version_or_date"), maximum=256)
    _require_text(
        "source license_or_use_note",
        record.get("license_or_use_note"),
        maximum=2000,
    )
    _require_text("source limitations", record.get("limitations"), maximum=4000)
    url = _require_text("source url", record.get("url"), maximum=4096)
    parsed_url = urlparse(url)
    if parsed_url.scheme not in {"file", "http", "https", "urn"}:
        raise ValidationError(
            "source url must use an absolute file, http, https, or urn scheme"
        )
    if parsed_url.scheme in {"http", "https"} and not parsed_url.netloc:
        raise ValidationError("source http(s) url must include a host")
    if parsed_url.scheme == "file" and not parsed_url.path.startswith("/"):
        raise ValidationError("source file url must be absolute")
    supports = record.get("supports")
    if (
        not isinstance(supports, list)
        or not supports
        or len(supports) > 256
        or not all(isinstance(item, str) for item in supports)
    ):
        raise ValidationError("source supports must be a non-empty string list")
    normalized_supports = [
        _require_identifier("source supports item", item) for item in supports
    ]
    if len(normalized_supports) != len(set(normalized_supports)):
        raise ValidationError("source supports must contain unique identifiers")
    return record


def validate_source_library(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError("source library must be an object")
    _exact_fields(
        value,
        {"schema_version", "sources"},
        label="source library",
    )
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValidationError("unsupported source library schema_version")
    sources = value.get("sources")
    if not isinstance(sources, list):
        raise ValidationError("source library sources must be an array")
    seen: set[tuple[str, str]] = set()
    ordered: list[tuple[str, str]] = []
    for record in sources:
        validated = _validate_source_record(record)
        key = (str(validated["source_id"]), str(validated["version_or_date"]))
        if key in seen:
            raise ValidationError(
                "source library contains a duplicate source_id/version_or_date"
            )
        seen.add(key)
        ordered.append(key)
    if ordered != sorted(ordered):
        raise ValidationError(
            "source library records must be sorted by source_id and version_or_date"
        )
    return value


def load_source_library(workspace: Path) -> dict[str, Any]:
    return validate_source_library(read_json(workspace, "state/sources.json"))


def source_record_index(
    library: dict[str, Any],
) -> dict[tuple[str, str], dict[str, Any]]:
    validate_source_library(library)
    return {
        (str(record["source_id"]), str(record["version_or_date"])): record
        for record in library["sources"]
    }


def validate_event_source_resolution(
    events: Iterable[dict[str, Any]], library: dict[str, Any]
) -> None:
    known = source_record_index(library)
    unresolved: set[tuple[str, str]] = set()
    for event in events:
        if event.get("event_type") != "observation":
            continue
        for reference in event["source_provenance"]:
            key = (str(reference["source_id"]), str(reference["version_or_date"]))
            if key not in known:
                unresolved.add(key)
    if unresolved:
        labels = ", ".join(
            f"{source_id}@{version}" for source_id, version in sorted(unresolved)
        )
        raise ValidationError(
            f"observation source reference does not resolve: {labels}"
        )


def add_source_record(path: str, record: dict[str, Any]) -> dict[str, Any]:
    workspace = secure_workspace(path)
    validated = _validate_source_record(record)
    with workspace_lock(workspace):
        _validate_workspace_state(workspace)
        library = load_source_library(workspace)
        key = (str(validated["source_id"]), str(validated["version_or_date"]))
        existing = source_record_index(library)
        if key in existing:
            raise ValidationError("this source_id/version_or_date already exists")
        updated = {
            "schema_version": SCHEMA_VERSION,
            "sources": sorted(
                [*library["sources"], validated],
                key=lambda item: (item["source_id"], item["version_or_date"]),
            ),
        }
        validate_source_library(updated)
        atomic_write_json(workspace / "state" / "sources.json", updated)
    return {
        "source_id": validated["source_id"],
        "status": "source_added",
        "version_or_date": validated["version_or_date"],
    }


def _validate_observation(event: dict[str, Any]) -> None:
    _require_identifier("session_id", event.get("session_id"))
    _require_identifier("concept_id", event.get("concept_id"))
    dimension = event.get("dimension")
    if dimension not in DIMENSIONS:
        raise ValidationError(f"dimension must be one of: {', '.join(DIMENSIONS)}")
    _require_identifier("item_id", event.get("item_id"))
    _require_identifier("item_version", event.get("item_version"))
    content_version = event.get("content_version")
    if not isinstance(content_version, str) or not CONTENT_VERSION_RE.fullmatch(
        content_version
    ):
        raise ValidationError(
            "content_version must be sha256 followed by 64 lowercase hex digits"
        )
    result = event.get("result")
    if not isinstance(result, dict):
        raise ValidationError("observation result must be an object")
    _exact_fields(result, {"correct", "score"}, label="observation result")
    score = result.get("score")
    if (
        isinstance(score, bool)
        or not isinstance(score, (int, float))
        or not math.isfinite(score)
    ):
        raise ValidationError("observation score must be a finite number")
    if not 0 <= float(score) <= 1:
        raise ValidationError("observation score must be between 0 and 1")
    if not isinstance(result.get("correct"), bool):
        raise ValidationError("observation result.correct must be boolean")
    response = event.get("response")
    response_ref = event.get("response_ref")
    if (response is None) == (response_ref is None):
        raise ValidationError(
            "observation must contain exactly one of response or response_ref"
        )
    if response is not None:
        _require_preserved_text("response", response, maximum=16000)
    if response_ref is not None:
        _require_preserved_text("response_ref", response_ref, maximum=4096)

    rubric = event.get("rubric")
    if not isinstance(rubric, dict):
        raise ValidationError("observation rubric must be an object")
    _exact_fields(rubric, {"dimensions", "score"}, label="observation rubric")
    rubric_score = rubric.get("score")
    if (
        isinstance(rubric_score, bool)
        or not isinstance(rubric_score, (int, float))
        or not math.isfinite(rubric_score)
        or not 0 <= float(rubric_score) <= 1
    ):
        raise ValidationError("observation rubric score must be between 0 and 1")
    if float(rubric_score) != float(score):
        raise ValidationError("observation rubric score must match result.score")
    rubric_dimensions = rubric.get("dimensions")
    if not isinstance(rubric_dimensions, dict):
        raise ValidationError("observation rubric dimensions must be an object")
    _exact_fields(
        rubric_dimensions,
        set(DIMENSIONS),
        label="observation rubric dimensions",
    )
    for rubric_dimension, dimension_score in rubric_dimensions.items():
        if dimension_score is None:
            continue
        if (
            isinstance(dimension_score, bool)
            or not isinstance(dimension_score, (int, float))
            or not math.isfinite(dimension_score)
            or not 0 <= float(dimension_score) <= 1
        ):
            raise ValidationError(
                f"observation rubric dimension {rubric_dimension} must be null or a number from 0 to 1"
            )
    if rubric_dimensions[dimension] is None or float(
        rubric_dimensions[dimension]
    ) != float(score):
        raise ValidationError(
            "observation primary rubric dimension must match result.score"
        )

    learner_authored = event.get("learner_authored")
    if learner_authored is not None:
        _require_preserved_text("learner_authored", learner_authored, maximum=16000)
    agent_inference = event.get("agent_inference")
    if agent_inference is not None:
        if not isinstance(agent_inference, dict):
            raise ValidationError("agent_inference must be null or an object")
        _exact_fields(
            agent_inference,
            {"certainty", "summary"},
            label="agent_inference",
        )
        _require_text(
            "agent_inference.summary", agent_inference.get("summary"), maximum=2000
        )
        certainty = agent_inference.get("certainty")
        if (
            isinstance(certainty, bool)
            or not isinstance(certainty, (int, float))
            or not math.isfinite(certainty)
            or not 0 <= float(certainty) <= 1
        ):
            raise ValidationError(
                "agent_inference.certainty must be a number from 0 to 1"
            )
    hint = event.get("hint_level")
    if (
        isinstance(hint, bool)
        or not isinstance(hint, int)
        or not 0 <= hint <= MAX_HINT_LEVEL
    ):
        raise ValidationError(
            f"hint_level must be an integer from 0 to {MAX_HINT_LEVEL}"
        )
    provenance = event.get("source_provenance")
    if not isinstance(provenance, list) or not provenance:
        raise ValidationError(
            "source_provenance must contain at least one versioned source reference"
        )
    source_keys: list[tuple[str, str]] = []
    for source in provenance:
        if not isinstance(source, dict):
            raise ValidationError("source_provenance entries must be objects")
        _exact_fields(
            source,
            {"source_id", "version_or_date"},
            label="source_provenance reference",
        )
        source_id = _require_identifier("source_id", source.get("source_id"))
        version = _require_text(
            "source version_or_date", source.get("version_or_date"), maximum=256
        )
        source_keys.append((source_id, version))
    if len(source_keys) != len(set(source_keys)):
        raise ValidationError(
            "source_provenance must contain unique source/version references"
        )
    confidence = event.get("confidence")
    if not isinstance(confidence, dict):
        raise ValidationError("confidence must include a value and provenance")
    _exact_fields(confidence, {"provenance", "value"}, label="observation confidence")
    value = confidence.get("value")
    if value is not None and (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not 0 <= float(value) <= 1
    ):
        raise ValidationError("confidence value must be null or a number from 0 to 1")
    provenance_label = confidence.get("provenance")
    if provenance_label not in {"not_reported", "learner_reported"}:
        raise ValidationError("confidence provenance is invalid")
    if value is None and provenance_label != "not_reported":
        raise ValidationError("missing confidence must use not_reported provenance")
    if value is not None and provenance_label != "learner_reported":
        raise ValidationError("reported confidence must identify learner provenance")
    claim = event.get("misconception_claim")
    reasoning = event.get("learner_reasoning")
    if claim is not None:
        _require_text("misconception_claim", claim, maximum=1000)
        _require_text("learner_reasoning", reasoning, maximum=4000)
        if event.get("misconception_provenance") not in {
            "learner_reported",
            "tutor_inference",
        }:
            raise ValidationError("misconception provenance is invalid")
        confirmed = event.get("misconception_learner_confirmed")
        if not isinstance(confirmed, bool):
            raise ValidationError("misconception learner confirmation must be boolean")
        if confirmed and event["misconception_provenance"] != "learner_reported":
            raise ValidationError(
                "only learner-reported misconception evidence may be learner-confirmed"
            )
    elif any(
        field in event
        for field in (
            "learner_reasoning",
            "misconception_provenance",
            "misconception_learner_confirmed",
        )
    ):
        raise ValidationError("misconception metadata requires a misconception_claim")

    attempt_number = event.get("attempt_number")
    if (
        isinstance(attempt_number, bool)
        or not isinstance(attempt_number, int)
        or attempt_number < 1
    ):
        raise ValidationError("attempt_number must be a positive integer")
    _require_identifier("content_id", event.get("content_id"))
    _require_identifier("objective_id", event.get("objective_id"))
    _require_text(
        "model_and_prompt_version",
        event.get("model_and_prompt_version"),
        maximum=2000,
    )


def validate_event(event: Any) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise ValidationError("evidence event must be an object")
    if event.get("schema_version") != SCHEMA_VERSION:
        raise ValidationError("unsupported evidence schema_version")
    event_id = event.get("event_id")
    if not isinstance(event_id, str) or not re.fullmatch(r"evt-[0-9a-f]{32}", event_id):
        raise ValidationError("event_id is invalid")
    normalize_timestamp(event.get("timestamp"))
    event_type = event.get("event_type")
    if event_type == "observation":
        expected = {
            "agent_inference",
            "attempt_number",
            "concept_id",
            "confidence",
            "content_id",
            "content_version",
            "dimension",
            "event_id",
            "event_type",
            "hint_level",
            "item_id",
            "item_version",
            "learner_authored",
            "model_and_prompt_version",
            "objective_id",
            "response",
            "response_ref",
            "result",
            "rubric",
            "schema_version",
            "session_id",
            "source_provenance",
            "timestamp",
        }
        if "misconception_claim" in event:
            expected |= {
                "learner_reasoning",
                "misconception_claim",
                "misconception_learner_confirmed",
                "misconception_provenance",
            }
        _exact_fields(event, expected, label="observation event")
        _validate_observation(event)
    elif event_type == "correction":
        _exact_fields(
            event,
            {
                "corrected_event_id",
                "event_id",
                "event_type",
                "reason",
                "schema_version",
                "timestamp",
            },
            label="correction event",
        )
        target = event.get("corrected_event_id")
        if not isinstance(target, str) or not re.fullmatch(r"evt-[0-9a-f]{32}", target):
            raise ValidationError("corrected_event_id is invalid")
        _require_text("correction reason", event.get("reason"), maximum=1000)
    elif event_type == "invalidation":
        _exact_fields(
            event,
            {
                "event_id",
                "event_type",
                "invalidated_event_ids",
                "reason",
                "schema_version",
                "timestamp",
            },
            label="invalidation event",
        )
        targets = event.get("invalidated_event_ids")
        if not isinstance(targets, list) or not targets:
            raise ValidationError("invalidation must reference at least one event")
        for target in targets:
            if not isinstance(target, str) or not re.fullmatch(
                r"evt-[0-9a-f]{32}", target
            ):
                raise ValidationError("invalidated event ID is invalid")
        if len(targets) != len(set(targets)):
            raise ValidationError("invalidation targets must be unique")
        _require_text("invalidation reason", event.get("reason"), maximum=1000)
    elif event_type == "misconception_rejection":
        _exact_fields(
            event,
            {
                "event_id",
                "event_type",
                "misconception_event_id",
                "reason",
                "schema_version",
                "timestamp",
            },
            label="misconception rejection event",
        )
        target = event.get("misconception_event_id")
        if not isinstance(target, str) or not re.fullmatch(r"evt-[0-9a-f]{32}", target):
            raise ValidationError("misconception_event_id is invalid")
        _require_text(
            "misconception rejection reason",
            event.get("reason"),
            maximum=1000,
        )
    else:
        raise ValidationError(f"unsupported event_type: {event_type!r}")
    expected = dict(event)
    expected.pop("event_id", None)
    if event_id != _event_id(expected):
        raise ValidationError("event_id does not match its record")
    if event_type == "observation" and event["result"]["correct"] is not (
        float(event["result"]["score"]) >= POSITIVE_SCORE
    ):
        raise ValidationError(
            "observation result.correct does not match the score threshold"
        )
    return event


def validate_event_sequence(events: list[dict[str, Any]]) -> None:
    """Validate one complete evidence sequence without filesystem mutation."""

    seen: set[str] = set()
    by_id: dict[str, dict[str, Any]] = {}
    item_bindings: dict[str, tuple[str, str, str, str]] = {}
    item_version_bindings: dict[tuple[str, str], str] = {}
    for event in events:
        validate_event(event)
        event_id = event["event_id"]
        if event_id in seen:
            raise ValidationError(f"duplicate evidence event_id: {event_id}")
        event_type = event["event_type"]
        if event_type == "observation":
            item_id = str(event["item_id"])
            binding = (
                str(event["concept_id"]),
                str(event["objective_id"]),
                str(event["content_id"]),
                str(event["dimension"]),
            )
            existing_binding = item_bindings.get(item_id)
            if existing_binding is not None and existing_binding != binding:
                raise ValidationError(
                    f"observation item_id {item_id!r} must preserve its concept, objective, content, and dimension"
                )
            item_bindings[item_id] = binding
            version_key = (item_id, str(event["item_version"]))
            content_version = str(event["content_version"])
            existing_version = item_version_bindings.get(version_key)
            if existing_version is not None and existing_version != content_version:
                raise ValidationError(
                    "one item_id/item_version pair cannot identify multiple content versions"
                )
            item_version_bindings[version_key] = content_version
        elif event_type == "correction":
            target = by_id.get(event["corrected_event_id"])
            if target is None or target["event_type"] != "observation":
                raise ValidationError(
                    "correction must reference an earlier observation event"
                )
            if _timestamp_key(event["timestamp"]) < _timestamp_key(target["timestamp"]):
                raise ValidationError(
                    "correction timestamp is earlier than its target observation"
                )
        elif event_type == "invalidation":
            invalid_targets = [
                target
                for target in event["invalidated_event_ids"]
                if target not in by_id or by_id[target]["event_type"] != "observation"
            ]
            if invalid_targets:
                raise ValidationError(
                    "invalidation must reference earlier observation event(s): "
                    + ", ".join(sorted(invalid_targets))
                )
            if any(
                _timestamp_key(event["timestamp"])
                < _timestamp_key(by_id[target]["timestamp"])
                for target in event["invalidated_event_ids"]
            ):
                raise ValidationError(
                    "invalidation timestamp is earlier than a target observation"
                )
        elif event_type == "misconception_rejection":
            target = by_id.get(event["misconception_event_id"])
            if (
                target is None
                or target["event_type"] != "observation"
                or not target.get("misconception_claim")
            ):
                raise ValidationError(
                    "misconception rejection must reference an earlier misconception observation"
                )
            if _timestamp_key(event["timestamp"]) < _timestamp_key(target["timestamp"]):
                raise ValidationError(
                    "misconception rejection timestamp is earlier than its target observation"
                )
        seen.add(event_id)
        by_id[event_id] = event


def load_events(workspace: Path) -> list[dict[str, Any]]:
    events = read_jsonl(workspace, "state/sessions.jsonl")
    validate_event_sequence(events)
    return events


def _active_observations(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    event_list = list(events)
    superseded: set[str] = set()
    for event in event_list:
        if event["event_type"] == "correction":
            superseded.add(event["corrected_event_id"])
        elif event["event_type"] == "invalidation":
            superseded.update(event["invalidated_event_ids"])
    active = [
        event
        for event in event_list
        if event["event_type"] == "observation" and event["event_id"] not in superseded
    ]
    return sorted(
        active,
        key=lambda event: (_timestamp_key(event["timestamp"]), event["event_id"]),
    )


def _scrub_review_dependencies(
    records: list[dict[str, Any]],
    *,
    observation_event_ids: set[str] | None = None,
    review_event_ids: set[str] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Remove a targeted review and the later same-item causal suffix."""

    observation_targets = observation_event_ids or set()
    review_targets = review_event_ids or set()
    affected_from: dict[str, int] = {}
    for index, record in enumerate(records):
        if record["event_type"] != "review":
            continue
        directly_targeted = str(record["event_id"]) in review_targets
        observation_targeted = (
            str(record["input"]["observation_event_id"]) in observation_targets
        )
        if not directly_targeted and not observation_targeted:
            continue
        item_id = str(record["item_id"])
        affected_from[item_id] = min(index, affected_from.get(item_id, index))

    removed: list[str] = []
    retained: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        item_id = record.get("item_id")
        start = affected_from.get(str(item_id)) if item_id is not None else None
        if (
            start is not None
            and index >= start
            and record["event_type"] in {"review", "snooze", "reschedule"}
        ):
            removed.append(str(record["event_id"]))
        else:
            retained.append(record)

    from .review_records import validate_review_sequence

    validate_review_sequence(retained)
    return retained, removed


def _observation_weight(event: dict[str, Any]) -> float:
    independence = max(0.2, 1.0 - 0.2 * int(event["hint_level"]))
    dimension_weight = 1.15 if event["dimension"] in HIGHER_ORDER_DIMENSIONS else 1.0
    return independence * dimension_weight


def _positive_unassisted(event: dict[str, Any]) -> bool:
    return (
        event["hint_level"] == 0 and float(event["result"]["score"]) >= POSITIVE_SCORE
    )


def _derive_status(observations: list[dict[str, Any]]) -> tuple[str, str]:
    independent = [event for event in observations if _positive_unassisted(event)]
    dimensions = {event["dimension"] for event in independent}
    higher = [
        event for event in independent if event["dimension"] in HIGHER_ORDER_DIMENSIONS
    ]
    contradictions = [
        event
        for event in observations
        if float(event["result"]["score"]) < CONTRADICTORY_SCORE
    ]
    later_retrieval = False
    for retrieval in independent:
        if retrieval["dimension"] != "recall":
            continue
        for prior in higher:
            if prior["session_id"] != retrieval["session_id"] and _timestamp_key(
                prior["timestamp"]
            ) < _timestamp_key(retrieval["timestamp"]):
                later_retrieval = True
                break
        if later_retrieval:
            break

    if contradictions:
        return (
            "developing" if independent else "emerging",
            "Contradictory evidence remains visible and blocks a durable claim.",
        )
    if len(dimensions) >= 2 and higher and later_retrieval:
        return (
            "durable",
            "At least two unassisted dimensions include higher-order evidence and later-session recall.",
        )
    if len(dimensions) >= 2 and higher:
        return (
            "provisional",
            "Independent multi-dimensional evidence exists, but later-session recall is still required.",
        )
    if len(dimensions) >= 2:
        return (
            "developing",
            "Independent evidence spans dimensions but lacks an unassisted higher-order item.",
        )
    if independent:
        return (
            "emerging",
            "Only one independently demonstrated dimension is available.",
        )
    return (
        "emerging",
        "Evidence is partial or scaffolded; no independent mastery claim is supported.",
    )


def project_events(
    events: Iterable[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    event_list = list(events)
    active = _active_observations(event_list)
    rejected_misconceptions = {
        event["misconception_event_id"]
        for event in event_list
        if event["event_type"] == "misconception_rejection"
    }
    by_concept: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in active:
        by_concept[event["concept_id"]].append(event)

    concepts: list[dict[str, Any]] = []
    misconceptions: list[dict[str, Any]] = []
    for concept_id in sorted(by_concept):
        observations = by_concept[concept_id]
        dimension_states: dict[str, Any] = {}
        for dimension in DIMENSIONS:
            dimension_events = [
                event for event in observations if event["dimension"] == dimension
            ]
            if dimension_events:
                total_weight = sum(
                    _observation_weight(event) for event in dimension_events
                )
                estimate = (
                    sum(
                        float(event["result"]["score"]) * _observation_weight(event)
                        for event in dimension_events
                    )
                    / total_weight
                )
                dimension_states[dimension] = {
                    "estimate": round(estimate, 6),
                    "evidence_ids": [event["event_id"] for event in dimension_events],
                }
            else:
                dimension_states[dimension] = {"estimate": None, "evidence_ids": []}

        contradictions = [
            {
                "dimension": event["dimension"],
                "evidence_id": event["event_id"],
                "hint_level": event["hint_level"],
                "score": event["result"]["score"],
            }
            for event in observations
            if float(event["result"]["score"]) < CONTRADICTORY_SCORE
        ]
        independent = [event for event in observations if _positive_unassisted(event)]
        status, reason = _derive_status(observations)
        total_weight = sum(_observation_weight(event) for event in observations)
        confidence = (
            sum(
                float(event["result"]["score"]) * _observation_weight(event)
                for event in observations
            )
            / total_weight
        )
        concept = {
            "confidence": round(confidence, 6),
            "concept_id": concept_id,
            "contradictions": contradictions,
            "dimensions": dimension_states,
            "evidence_ids": [event["event_id"] for event in observations],
            "higher_order_evidence_ids": [
                event["event_id"]
                for event in independent
                if event["dimension"] in HIGHER_ORDER_DIMENSIONS
            ],
            "last_updated": normalize_timestamp(
                max(observations, key=lambda event: _timestamp_key(event["timestamp"]))[
                    "timestamp"
                ]
            ),
            "status": status,
            "status_reason": reason,
            "unassisted_dimensions": sorted(
                {event["dimension"] for event in independent}
            ),
        }
        concepts.append(concept)

        claims: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for event in observations:
            claim = event.get("misconception_claim")
            if claim and event["event_id"] not in rejected_misconceptions:
                claims[str(claim)].append(event)
        for claim in sorted(claims):
            claim_events = claims[claim]
            digest = hashlib.sha256(f"{concept_id}\0{claim}".encode()).hexdigest()[:24]
            misconceptions.append(
                {
                    "claim": claim,
                    "concept_id": concept_id,
                    "evidence_ids": [event["event_id"] for event in claim_events],
                    "last_tested": normalize_timestamp(
                        max(
                            claim_events,
                            key=lambda event: _timestamp_key(event["timestamp"]),
                        )["timestamp"]
                    ),
                    "learner_confirmed": any(
                        event["misconception_learner_confirmed"]
                        for event in claim_events
                    ),
                    "misconception_id": "mis-" + digest,
                    "provenance": sorted(
                        {event["misconception_provenance"] for event in claim_events}
                    ),
                    "state": "supported" if len(claim_events) >= 2 else "suspected",
                }
            )

    concept_projection = _empty_concepts()
    concept_projection["concepts"] = concepts
    misconception_projection = _empty_misconceptions()
    misconception_projection["misconceptions"] = sorted(
        misconceptions, key=lambda item: item["misconception_id"]
    )
    return concept_projection, misconception_projection


def _state_transaction(
    workspace: Path,
    events: list[dict[str, Any]],
    reviews: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Bind evidence, causally valid reviews, and projections in one commit."""

    validate_event_sequence(events)
    if reviews is None:
        reviews = read_jsonl(workspace, "state/reviews.jsonl")
    from .review_records import (
        validate_review_evidence_bindings,
        validate_review_sequence,
    )

    validate_review_sequence(reviews)
    validate_review_evidence_bindings(reviews, events)
    concepts, misconceptions = project_events(events)
    payloads = {
        "sessions.jsonl": b"".join(canonical_json_line(event) for event in events),
        "reviews.jsonl": b"".join(canonical_json_line(record) for record in reviews),
        "concepts.json": canonical_json_bytes(concepts),
        "misconceptions.json": canonical_json_bytes(misconceptions),
    }
    before = {
        name: hashlib.sha256(read_bytes(workspace, f"state/{name}")).hexdigest()
        for name in STATE_TARGET_FILES
    }
    targets = {
        name: {
            "data_base64": base64.b64encode(payloads[name]).decode("ascii"),
            "sha256": hashlib.sha256(payloads[name]).hexdigest(),
        }
        for name in STATE_TARGET_FILES
    }
    identity = canonical_json_bytes({"before": before, "targets": targets})
    return {
        "before": before,
        "schema_version": 1,
        "targets": targets,
        "transaction_id": "state-" + hashlib.sha256(identity).hexdigest()[:32],
    }


def _validate_state_transaction(
    transaction: dict[str, Any],
) -> tuple[dict[str, str], dict[str, bytes]]:
    _exact_fields(
        transaction,
        {"before", "schema_version", "targets", "transaction_id"},
        label="state transaction",
    )
    if transaction.get("schema_version") != 1:
        raise ValidationError("unsupported state transaction schema version")
    before = transaction.get("before")
    targets = transaction.get("targets")
    if not isinstance(before, dict) or set(before) != set(STATE_TARGET_FILES):
        raise ValidationError("state transaction preimage set is invalid")
    if not isinstance(targets, dict) or set(targets) != set(STATE_TARGET_FILES):
        raise ValidationError("state transaction target set is invalid")
    for name, digest in before.items():
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ValidationError(
                f"state transaction preimage {name} digest is malformed"
            )
    transaction_id = transaction.get("transaction_id")
    expected_id = (
        "state-"
        + hashlib.sha256(
            canonical_json_bytes({"before": before, "targets": targets})
        ).hexdigest()[:32]
    )
    if transaction_id != expected_id:
        raise ValidationError("state transaction ID does not match its contents")

    decoded: dict[str, bytes] = {}
    for name in STATE_TARGET_FILES:
        target = targets[name]
        if not isinstance(target, dict):
            raise ValidationError(f"state transaction target {name} is invalid")
        _exact_fields(
            target,
            {"data_base64", "sha256"},
            label=f"state transaction target {name}",
        )
        digest = target.get("sha256")
        encoded = target.get("data_base64")
        if (
            not isinstance(digest, str)
            or re.fullmatch(r"[0-9a-f]{64}", digest) is None
            or not isinstance(encoded, str)
        ):
            raise ValidationError(f"state transaction target {name} is malformed")
        try:
            payload = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError) as exc:
            raise ValidationError(
                f"state transaction target {name} has invalid base64"
            ) from exc
        if hashlib.sha256(payload).hexdigest() != digest:
            raise ValidationError(f"state transaction target {name} digest mismatch")
        decoded[name] = payload

    events = _parse_jsonl_payload(decoded["sessions.jsonl"], label="sessions target")
    reviews = _parse_jsonl_payload(decoded["reviews.jsonl"], label="reviews target")
    validate_event_sequence(events)
    from .review_records import (
        validate_review_evidence_bindings,
        validate_review_sequence,
    )

    validate_review_sequence(reviews)
    validate_review_evidence_bindings(reviews, events)
    try:
        concepts = json.loads(decoded["concepts.json"])
        misconceptions = json.loads(decoded["misconceptions.json"])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError("state transaction projection is invalid JSON") from exc
    expected_concepts, expected_misconceptions = project_events(events)
    if concepts != expected_concepts or misconceptions != expected_misconceptions:
        raise ValidationError(
            "state transaction projections do not match its evidence target"
        )
    return before, decoded


def _load_state_transaction(workspace: Path) -> dict[str, Any] | None:
    path = workspace / "state" / STATE_TRANSACTION_NAME
    try:
        path_stat = path.lstat()
    except FileNotFoundError:
        return None
    if (
        stat.S_ISLNK(path_stat.st_mode)
        or not stat.S_ISREG(path_stat.st_mode)
        or path_stat.st_nlink != 1
        or stat.S_IMODE(path_stat.st_mode) & 0o077
    ):
        raise SafetyError("state transaction journal is unsafe")
    value = read_json(workspace, f"state/{STATE_TRANSACTION_NAME}")
    if not isinstance(value, dict):
        raise ValidationError("state transaction journal must be an object")
    _validate_state_transaction(value)
    return value


def _validate_held_workspace_generation(workspace: Path) -> Any:
    anchor = _ACTIVE_WORKSPACE_IO.get()
    if anchor is None or anchor.workspace != workspace:
        raise SafetyError("state journal cleanup requires a held workspace generation")
    try:
        current_workspace = workspace.lstat()
        current_state = (workspace / "state").lstat()
    except FileNotFoundError as exc:
        raise SafetyError(
            "learner workspace generation changed during journal cleanup"
        ) from exc
    if (current_workspace.st_dev, current_workspace.st_ino) != (
        anchor.workspace_device,
        anchor.workspace_inode,
    ) or (current_state.st_dev, current_state.st_ino) != (
        anchor.state_device,
        anchor.state_inode,
    ):
        raise SafetyError("learner workspace generation changed during journal cleanup")
    return anchor


def _validate_journal_entry(
    directory_descriptor: int, name: str, *, label: str
) -> os.stat_result:
    try:
        entry = os.stat(name, dir_fd=directory_descriptor, follow_symlinks=False)
    except FileNotFoundError as exc:
        raise SafetyError(f"{label} disappeared during cleanup") from exc
    if (
        stat.S_ISLNK(entry.st_mode)
        or not stat.S_ISREG(entry.st_mode)
        or entry.st_nlink != 1
        or stat.S_IMODE(entry.st_mode) & 0o077
    ):
        raise SafetyError(f"{label} is unsafe")
    return entry


def _unlink_state_journal(
    workspace: Path, name: str, *, label: str = "state transaction journal"
) -> None:
    anchor = _validate_held_workspace_generation(workspace)
    _validate_journal_entry(anchor.state_descriptor, name, label=label)
    try:
        os.unlink(name, dir_fd=anchor.state_descriptor)
    except FileNotFoundError as exc:
        raise SafetyError(f"{label} disappeared during cleanup") from exc
    os.fsync(anchor.state_descriptor)
    _validate_held_workspace_generation(workspace)


def _apply_state_transaction(workspace: Path, transaction: dict[str, Any]) -> None:
    before, payloads = _validate_state_transaction(transaction)
    state_directory = workspace / "state"
    for name in STATE_TARGET_FILES:
        current = read_bytes(workspace, f"state/{name}")
        current_digest = hashlib.sha256(current).hexdigest()
        target_digest = hashlib.sha256(payloads[name]).hexdigest()
        if current_digest not in {before[name], target_digest}:
            raise SafetyError(
                f"state transaction refuses to overwrite divergent {name}"
            )
    for name in STATE_TARGET_FILES:
        atomic_write(state_directory / name, payloads[name])
    for name in STATE_TARGET_FILES:
        if read_bytes(workspace, f"state/{name}") != payloads[name]:
            raise SafetyError(f"state transaction verification failed for {name}")
    _unlink_state_journal(workspace, STATE_TRANSACTION_NAME)


def _recover_state_transaction(workspace: Path) -> dict[str, Any] | None:
    transaction = _load_state_transaction(workspace)
    if transaction is None:
        return None
    _apply_state_transaction(workspace, transaction)
    return transaction


def _commit_event_sequence_locked(
    workspace: Path,
    events: list[dict[str, Any]],
    *,
    reviews: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    transaction = _state_transaction(workspace, events, reviews)
    atomic_write_json(workspace / "state" / STATE_TRANSACTION_NAME, transaction)
    _apply_state_transaction(workspace, transaction)
    return project_events(events)


def _validate_workspace_state(
    workspace: Path, *, require_active: bool = True
) -> dict[str, Any]:
    _recover_state_transaction(workspace)
    _recover_deletion_transaction(workspace)
    learner = validate_learner_document(
        read_json(workspace, "state/learner.json"), require_active=require_active
    )
    location = Path(str(learner["consent"].get("location", "")))
    if location != workspace:
        raise SafetyError(
            "consent location does not match the resolved learner workspace"
        )
    # This import is intentionally local: review-record validation is
    # dependency-free, while keeping the state and scheduler modules acyclic.
    from .review_records import (
        validate_review_evidence_bindings,
        validate_review_sequence,
    )

    review_records = read_jsonl(workspace, "state/reviews.jsonl")
    validate_review_sequence(review_records)
    source_library = load_source_library(workspace)
    events = load_events(workspace)
    validate_event_source_resolution(events, source_library)
    validate_review_evidence_bindings(review_records, events)
    return learner


def _rebuild_locked(
    workspace: Path, *, require_active: bool = True
) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_workspace_state(workspace, require_active=require_active)
    events = load_events(workspace)
    return _commit_event_sequence_locked(workspace, events)


def rebuild(path: str) -> tuple[dict[str, Any], dict[str, Any]]:
    workspace = secure_workspace(path)
    with workspace_lock(workspace):
        return _rebuild_locked(workspace)


def make_observation(
    *,
    session_id: str,
    concept_id: str,
    dimension: str,
    score: float,
    hint_level: int,
    item_id: str,
    item_version: str,
    content_id: str,
    content_version: str,
    objective_id: str,
    model_and_prompt_version: str,
    source_id: str,
    source_version: str,
    timestamp: str,
    response: str | None,
    response_ref: str | None,
    confidence: float | None = None,
    attempt_number: int = 1,
    rubric_dimensions: dict[str, float | None] | None = None,
    learner_authored: str | None = None,
    agent_inference_summary: str | None = None,
    agent_inference_certainty: float | None = None,
    misconception_claim: str | None = None,
    learner_reasoning: str | None = None,
    misconception_provenance: str | None = None,
    misconception_learner_confirmed: bool = False,
) -> dict[str, Any]:
    if (
        isinstance(score, bool)
        or not isinstance(score, (int, float))
        or not math.isfinite(score)
        or not 0 <= score <= 1
    ):
        raise ValidationError("score must be between 0 and 1")
    if (
        isinstance(hint_level, bool)
        or not isinstance(hint_level, int)
        or not 0 <= hint_level <= MAX_HINT_LEVEL
    ):
        raise ValidationError(f"hint_level must be from 0 to {MAX_HINT_LEVEL}")
    if confidence is not None and (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not math.isfinite(confidence)
        or not 0 <= confidence <= 1
    ):
        raise ValidationError("confidence must be between 0 and 1")
    if (
        isinstance(attempt_number, bool)
        or not isinstance(attempt_number, int)
        or attempt_number < 1
    ):
        raise ValidationError("attempt_number must be at least 1")
    if (response is None) == (response_ref is None):
        raise ValidationError("provide exactly one of response or response_ref")
    preserved_response = (
        _require_preserved_text("response", response, maximum=16000)
        if response is not None
        else None
    )
    preserved_response_ref = (
        _require_preserved_text("response_ref", response_ref, maximum=4096)
        if response_ref is not None
        else None
    )
    if (agent_inference_summary is None) != (agent_inference_certainty is None):
        raise ValidationError(
            "agent inference summary and certainty must be supplied together"
        )
    if agent_inference_certainty is not None and (
        isinstance(agent_inference_certainty, bool)
        or not isinstance(agent_inference_certainty, (int, float))
        or not math.isfinite(agent_inference_certainty)
        or not 0 <= agent_inference_certainty <= 1
    ):
        raise ValidationError("agent inference certainty must be between 0 and 1")
    if dimension not in DIMENSIONS:
        raise ValidationError(f"dimension must be one of: {', '.join(DIMENSIONS)}")
    if rubric_dimensions is None:
        normalized_rubric_dimensions: dict[str, float | None] = {
            name: score if name == dimension else None for name in DIMENSIONS
        }
    else:
        normalized_rubric_dimensions = dict(rubric_dimensions)
    event: dict[str, Any] = {
        "agent_inference": (
            {
                "certainty": agent_inference_certainty,
                "summary": _require_text(
                    "agent_inference_summary",
                    agent_inference_summary,
                    maximum=2000,
                ),
            }
            if agent_inference_summary is not None
            else None
        ),
        "attempt_number": attempt_number,
        "concept_id": _require_identifier("concept", concept_id),
        "confidence": {
            "provenance": "learner_reported"
            if confidence is not None
            else "not_reported",
            "value": confidence,
        },
        "content_id": _require_identifier("content_id", content_id),
        "content_version": _require_text(
            "content_version", content_version, maximum=71
        ),
        "dimension": dimension,
        "event_type": "observation",
        "hint_level": hint_level,
        "item_id": _require_identifier("item", item_id),
        "item_version": _require_identifier("item_version", item_version),
        "learner_authored": (
            _require_preserved_text("learner_authored", learner_authored, maximum=16000)
            if learner_authored is not None
            else None
        ),
        "model_and_prompt_version": _require_text(
            "model_and_prompt_version", model_and_prompt_version, maximum=2000
        ),
        "objective_id": _require_identifier("objective_id", objective_id),
        "response": preserved_response,
        "response_ref": preserved_response_ref,
        "result": {"correct": score >= POSITIVE_SCORE, "score": score},
        "rubric": {
            "dimensions": normalized_rubric_dimensions,
            "score": score,
        },
        "schema_version": SCHEMA_VERSION,
        "session_id": _require_identifier("session", session_id),
        "source_provenance": [
            {
                "source_id": _require_identifier("source_id", source_id),
                "version_or_date": _require_text(
                    "source_version", source_version, maximum=256
                ),
            }
        ],
        "timestamp": normalize_timestamp(timestamp),
    }
    if misconception_claim is not None or learner_reasoning is not None:
        event["misconception_claim"] = _require_text(
            "misconception_claim", misconception_claim or "", maximum=1000
        )
        event["learner_reasoning"] = _require_text(
            "learner_reasoning", learner_reasoning or "", maximum=4000
        )
        if misconception_provenance not in {"learner_reported", "tutor_inference"}:
            raise ValidationError(
                "misconception provenance must be learner_reported or tutor_inference"
            )
        if (
            misconception_learner_confirmed
            and misconception_provenance != "learner_reported"
        ):
            raise ValidationError(
                "only learner-reported misconception evidence may be learner-confirmed"
            )
        event["misconception_provenance"] = misconception_provenance
        event["misconception_learner_confirmed"] = misconception_learner_confirmed
    event["event_id"] = _event_id(event)
    validate_event(event)
    return event


def append_observation(path: str, event: dict[str, Any]) -> dict[str, Any]:
    workspace = secure_workspace(path)
    with workspace_lock(workspace):
        _validate_workspace_state(workspace)
        events = load_events(workspace)
        if any(existing["event_id"] == event["event_id"] for existing in events):
            raise ValidationError("this exact observation is already present")
        updated_events = [*events, event]
        validate_event_sequence(updated_events)
        validate_event_source_resolution(updated_events, load_source_library(workspace))
        concepts, _ = _commit_event_sequence_locked(workspace, updated_events)
    concept = next(
        item
        for item in concepts["concepts"]
        if item["concept_id"] == event["concept_id"]
    )
    return {
        "concept_status": concept["status"],
        "event_id": event["event_id"],
        "status": "observed",
    }


def correct_event(
    path: str, *, event_id: str, reason: str, timestamp: str
) -> dict[str, Any]:
    workspace = secure_workspace(path)
    with workspace_lock(workspace):
        _validate_workspace_state(workspace)
        events = load_events(workspace)
        matches = [event for event in events if event["event_id"] == event_id]
        if not matches:
            raise ValidationError("correction target event was not found")
        if matches[0]["event_type"] != "observation":
            raise ValidationError("only an observation may be corrected")
        if any(
            event["event_type"] == "correction"
            and event["corrected_event_id"] == event_id
            for event in events
        ):
            raise ValidationError("observation already has a correction event")
        correction: dict[str, Any] = {
            "corrected_event_id": event_id,
            "event_type": "correction",
            "reason": _require_text("reason", reason, maximum=1000),
            "schema_version": SCHEMA_VERSION,
            "timestamp": normalize_timestamp(timestamp),
        }
        if _timestamp_key(correction["timestamp"]) < _timestamp_key(
            matches[0]["timestamp"]
        ):
            raise ValidationError(
                "correction timestamp is earlier than its target observation"
            )
        correction["event_id"] = _event_id(correction)
        validate_event(correction)
        updated_events = [*events, correction]
        validate_event_sequence(updated_events)
        reviews = read_jsonl(workspace, "state/reviews.jsonl")
        retained_reviews, removed_review_ids = _scrub_review_dependencies(
            reviews,
            observation_event_ids={event_id},
        )
        _commit_event_sequence_locked(
            workspace,
            updated_events,
            reviews=retained_reviews,
        )
    return {
        "corrected_event_id": event_id,
        "event_id": correction["event_id"],
        "review_event_ids_removed": removed_review_ids,
        "review_events_removed": len(removed_review_ids),
        "status": "corrected",
    }


def reject_misconception(
    path: str, *, event_id: str, reason: str, timestamp: str
) -> dict[str, Any]:
    workspace = secure_workspace(path)
    with workspace_lock(workspace):
        _validate_workspace_state(workspace)
        events = load_events(workspace)
        target = next(
            (event for event in events if event["event_id"] == event_id), None
        )
        if (
            target is None
            or target["event_type"] != "observation"
            or not target.get("misconception_claim")
        ):
            raise ValidationError(
                "misconception rejection target was not a misconception observation"
            )
        if any(
            event["event_type"] == "misconception_rejection"
            and event["misconception_event_id"] == event_id
            for event in events
        ):
            raise ValidationError("misconception observation is already rejected")
        rejection: dict[str, Any] = {
            "event_type": "misconception_rejection",
            "misconception_event_id": event_id,
            "reason": _require_text("reason", reason, maximum=1000),
            "schema_version": SCHEMA_VERSION,
            "timestamp": normalize_timestamp(timestamp),
        }
        if _timestamp_key(rejection["timestamp"]) < _timestamp_key(target["timestamp"]):
            raise ValidationError(
                "misconception rejection timestamp is earlier than its target observation"
            )
        rejection["event_id"] = _event_id(rejection)
        validate_event(rejection)
        updated_events = [*events, rejection]
        validate_event_sequence(updated_events)
        _commit_event_sequence_locked(workspace, updated_events)
    return {
        "event_id": rejection["event_id"],
        "misconception_event_id": event_id,
        "status": "misconception_rejected",
    }


def invalidate_events(
    path: str,
    *,
    event_id: str | None,
    item_id: str | None,
    item_version: str | None,
    content_version: str | None,
    source_id: str | None,
    source_version: str | None,
    reason: str,
    timestamp: str,
) -> dict[str, Any]:
    if event_id is not None and re.fullmatch(r"evt-[0-9a-f]{32}", event_id) is None:
        raise ValidationError("event_id selector is invalid")
    if item_id is not None:
        _require_identifier("item_id selector", item_id)
    if item_version is not None:
        _require_identifier("item_version selector", item_version)
        if item_id is None:
            raise ValidationError(
                "--item-version requires --item to avoid global scope"
            )
    if (
        content_version is not None
        and CONTENT_VERSION_RE.fullmatch(content_version) is None
    ):
        raise ValidationError("content_version selector is invalid")
    if source_id is not None:
        _require_identifier("source_id selector", source_id)
        if source_version is None:
            raise ValidationError(
                "--source-version is required with --source-id to keep invalidation version-bound"
            )
    elif source_version is not None:
        raise ValidationError("--source-version requires --source-id")
    if source_version is not None:
        _require_text("source_version selector", source_version, maximum=256)
    workspace = secure_workspace(path)
    with workspace_lock(workspace):
        _validate_workspace_state(workspace)
        events = load_events(workspace)
        observations = [
            event for event in events if event["event_type"] == "observation"
        ]
        targets: list[str] = []
        for event in observations:
            if event_id is not None and event["event_id"] != event_id:
                continue
            if item_id is not None and event["item_id"] != item_id:
                continue
            if item_version is not None and event["item_version"] != item_version:
                continue
            if (
                content_version is not None
                and event["content_version"] != content_version
            ):
                continue
            if source_id is not None:
                source_reference = {
                    "source_id": source_id,
                    "version_or_date": source_version,
                }
                if source_reference not in event["source_provenance"]:
                    continue
            targets.append(event["event_id"])
        targets = sorted(set(targets))
        if not targets:
            raise ValidationError("no observation matches the invalidation selector")
        already_invalidated = {
            target
            for event in events
            if event["event_type"] == "invalidation"
            for target in event["invalidated_event_ids"]
        }
        targets = [target for target in targets if target not in already_invalidated]
        if not targets:
            raise ValidationError("all matching observations are already invalidated")
        invalidation: dict[str, Any] = {
            "event_type": "invalidation",
            "invalidated_event_ids": targets,
            "reason": _require_text("reason", reason, maximum=1000),
            "schema_version": SCHEMA_VERSION,
            "timestamp": normalize_timestamp(timestamp),
        }
        observation_by_id = {event["event_id"]: event for event in observations}
        if any(
            _timestamp_key(invalidation["timestamp"])
            < _timestamp_key(observation_by_id[target]["timestamp"])
            for target in targets
        ):
            raise ValidationError(
                "invalidation timestamp is earlier than a target observation"
            )
        invalidation["event_id"] = _event_id(invalidation)
        validate_event(invalidation)
        updated_events = [*events, invalidation]
        validate_event_sequence(updated_events)
        reviews = read_jsonl(workspace, "state/reviews.jsonl")
        retained_reviews, removed_review_ids = _scrub_review_dependencies(
            reviews,
            observation_event_ids=set(targets),
        )
        _commit_event_sequence_locked(
            workspace,
            updated_events,
            reviews=retained_reviews,
        )
    return {
        "event_id": invalidation["event_id"],
        "invalidated_event_ids": targets,
        "review_event_ids_removed": removed_review_ids,
        "review_events_removed": len(removed_review_ids),
        "status": "invalidated",
    }


def disable_persistence(path: str, *, reason: str, timestamp: str) -> dict[str, Any]:
    """Persist withdrawal of consent while preserving learner control actions."""

    workspace = secure_workspace(path)
    rationale = _require_text("reason", reason, maximum=1000)
    disabled_at = normalize_timestamp(timestamp)
    with workspace_lock(workspace):
        learner = _validate_workspace_state(workspace, require_active=False)
        if learner["consent"]["persistent_state"] is False:
            raise ValidationError("persistence consent is already disabled")
        updated = json.loads(json.dumps(learner, allow_nan=False))
        updated["consent"]["persistent_state"] = False
        updated["consent"]["disabled_at"] = disabled_at
        updated["consent"]["disable_reason"] = rationale
        validate_learner_document(updated, require_active=False)
        atomic_write_json(workspace / "state" / "learner.json", updated)
    return {
        "disabled_at": disabled_at,
        "reason": rationale,
        "status": "persistence_disabled",
        "workspace": str(workspace),
    }


def _select_deletion_ids(
    events: list[dict[str, Any]],
    *,
    event_ids: list[str],
    session_id: str | None,
    concept_id: str | None,
    item_id: str | None,
) -> list[str]:
    selected: set[str] = set()
    known = {event["event_id"] for event in events}
    for event_id in event_ids:
        if event_id not in known:
            raise ValidationError(f"deletion target event was not found: {event_id}")
        selected.add(event_id)
    for event in events:
        if session_id is not None and event.get("session_id") == session_id:
            selected.add(event["event_id"])
        if concept_id is not None and event.get("concept_id") == concept_id:
            selected.add(event["event_id"])
        if item_id is not None and event.get("item_id") == item_id:
            selected.add(event["event_id"])
    return sorted(selected)


def _build_deletion_plan(
    events: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
    *,
    event_ids: list[str],
    session_id: str | None,
    concept_id: str | None,
    item_id: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    selected = _select_deletion_ids(
        events,
        event_ids=event_ids,
        session_id=session_id,
        concept_id=concept_id,
        item_id=item_id,
    )
    selected_observation_ids = {
        str(event["event_id"])
        for event in events
        if event["event_type"] == "observation" and str(event["event_id"]) in selected
    }
    selected_review_ids = {
        str(record["event_id"])
        for record in reviews
        if record["event_type"] == "review"
        and (
            str(record["input"]["observation_event_id"]) in selected_observation_ids
            or (
                session_id is not None
                and str(record["input"]["session_id"]) == session_id
            )
            or (concept_id is not None and str(record["concept_id"]) == concept_id)
            or (item_id is not None and str(record["item_id"]) == item_id)
        )
    }
    if not selected and not selected_review_ids:
        raise ValidationError("no event or review matches the deletion selector")
    removed: set[str] = set(selected)
    changed = True
    while changed:
        changed = False
        for event in events:
            if event["event_id"] in removed:
                continue
            correction_lost_target = (
                event["event_type"] == "correction"
                and event["corrected_event_id"] in removed
            )
            rejection_lost_target = (
                event["event_type"] == "misconception_rejection"
                and event["misconception_event_id"] in removed
            )
            invalidation_lost_all_targets = (
                event["event_type"] == "invalidation"
                and not set(event["invalidated_event_ids"]) - removed
            )
            if (
                correction_lost_target
                or rejection_lost_target
                or invalidation_lost_all_targets
            ):
                removed.add(event["event_id"])
                changed = True

    retained_events: list[dict[str, Any]] = []
    rewritten_events: list[dict[str, Any]] = []
    for event in events:
        if event["event_id"] in removed:
            continue
        if event["event_type"] == "invalidation":
            remaining_targets = sorted(set(event["invalidated_event_ids"]) - removed)
            if remaining_targets != event["invalidated_event_ids"]:
                replacement = dict(event)
                replacement["invalidated_event_ids"] = remaining_targets
                replacement.pop("event_id", None)
                replacement["event_id"] = _event_id(replacement)
                validate_event(replacement)
                retained_events.append(replacement)
                rewritten_events.append(
                    {
                        "original_event_id": event["event_id"],
                        "replacement_event_id": replacement["event_id"],
                        "remaining_target_event_ids": remaining_targets,
                    }
                )
                continue
        retained_events.append(event)

    retained_reviews, removed_review_ids = _scrub_review_dependencies(
        reviews,
        observation_event_ids=selected_observation_ids,
        review_event_ids=selected_review_ids,
    )
    # The plan is fully validated before either log is replaced. This prevents
    # a semantic failure during rebuild from leaving a partially applied delete.
    from .review_records import (
        validate_review_evidence_bindings,
        validate_review_sequence,
    )

    validate_event_sequence(retained_events)
    validate_review_sequence(retained_reviews)
    validate_review_evidence_bindings(retained_reviews, retained_events)
    project_events(retained_events)
    plan = {
        "dependent_event_ids_removed": sorted(removed - set(selected)),
        "remaining_event_count": len(retained_events),
        "remaining_review_count": len(retained_reviews),
        "review_match_basis": "causal-observation-session-concept-or-item",
        "review_event_ids_removed": removed_review_ids,
        "rewritten_events": rewritten_events,
        "selected_event_ids": selected,
    }
    return plan, retained_events, retained_reviews


def _parse_jsonl_payload(payload: bytes, *, label: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError(f"{label} is not UTF-8") from exc
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValidationError(
                f"{label} line {line_number} is not valid JSON"
            ) from exc
        if not isinstance(value, dict):
            raise ValidationError(f"{label} line {line_number} must be an object")
        records.append(value)
    return records


def _deletion_transaction(
    plan: dict[str, Any],
    retained_events: list[dict[str, Any]],
    retained_reviews: list[dict[str, Any]],
) -> dict[str, Any]:
    concepts, misconceptions = project_events(retained_events)
    payloads = {
        "sessions.jsonl": b"".join(
            canonical_json_line(event) for event in retained_events
        ),
        "reviews.jsonl": b"".join(
            canonical_json_line(record) for record in retained_reviews
        ),
        "concepts.json": canonical_json_bytes(concepts),
        "misconceptions.json": canonical_json_bytes(misconceptions),
    }
    targets = {
        name: {
            "data_base64": base64.b64encode(payloads[name]).decode("ascii"),
            "sha256": hashlib.sha256(payloads[name]).hexdigest(),
        }
        for name in DELETE_TARGET_FILES
    }
    identity_input = canonical_json_bytes({"plan": plan, "targets": targets})
    return {
        "plan": plan,
        "schema_version": 1,
        "targets": targets,
        "transaction_id": "delete-" + hashlib.sha256(identity_input).hexdigest()[:32],
    }


def _validate_deletion_transaction(
    transaction: dict[str, Any],
) -> dict[str, bytes]:
    _exact_fields(
        transaction,
        {"plan", "schema_version", "targets", "transaction_id"},
        label="deletion transaction",
    )
    if transaction.get("schema_version") != 1:
        raise ValidationError("unsupported deletion transaction schema version")
    if not isinstance(transaction.get("plan"), dict):
        raise ValidationError("deletion transaction plan must be an object")
    transaction_id = transaction.get("transaction_id")
    if (
        not isinstance(transaction_id, str)
        or re.fullmatch(r"delete-[0-9a-f]{32}", transaction_id) is None
    ):
        raise ValidationError("deletion transaction has an invalid ID")
    targets = transaction.get("targets")
    if not isinstance(targets, dict) or set(targets) != set(DELETE_TARGET_FILES):
        raise ValidationError("deletion transaction target set is invalid")
    expected_transaction_id = (
        "delete-"
        + hashlib.sha256(
            canonical_json_bytes({"plan": transaction["plan"], "targets": targets})
        ).hexdigest()[:32]
    )
    if transaction_id != expected_transaction_id:
        raise ValidationError("deletion transaction ID does not match its contents")
    decoded: dict[str, bytes] = {}
    for name in DELETE_TARGET_FILES:
        target = targets[name]
        if not isinstance(target, dict):
            raise ValidationError(f"deletion transaction target {name} is invalid")
        _exact_fields(
            target,
            {"data_base64", "sha256"},
            label=f"deletion transaction target {name}",
        )
        digest = target.get("sha256")
        encoded = target.get("data_base64")
        if (
            not isinstance(digest, str)
            or re.fullmatch(r"[0-9a-f]{64}", digest) is None
            or not isinstance(encoded, str)
        ):
            raise ValidationError(f"deletion transaction target {name} is malformed")
        try:
            payload = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError) as exc:
            raise ValidationError(
                f"deletion transaction target {name} has invalid base64"
            ) from exc
        if hashlib.sha256(payload).hexdigest() != digest:
            raise ValidationError(f"deletion transaction target {name} digest mismatch")
        decoded[name] = payload

    events = _parse_jsonl_payload(decoded["sessions.jsonl"], label="sessions target")
    reviews = _parse_jsonl_payload(decoded["reviews.jsonl"], label="reviews target")
    validate_event_sequence(events)
    from .review_records import (
        validate_review_evidence_bindings,
        validate_review_sequence,
    )

    validate_review_sequence(reviews)
    validate_review_evidence_bindings(reviews, events)
    try:
        concepts = json.loads(decoded["concepts.json"])
        misconceptions = json.loads(decoded["misconceptions.json"])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(
            "deletion transaction projection is invalid JSON"
        ) from exc
    expected_concepts, expected_misconceptions = project_events(events)
    if concepts != expected_concepts or misconceptions != expected_misconceptions:
        raise ValidationError(
            "deletion transaction projections do not match retained evidence"
        )
    return decoded


def _load_deletion_transaction(workspace: Path) -> dict[str, Any] | None:
    path = workspace / "state" / DELETE_TRANSACTION_NAME
    try:
        path_stat = path.lstat()
    except FileNotFoundError:
        return None
    if (
        stat.S_ISLNK(path_stat.st_mode)
        or not stat.S_ISREG(path_stat.st_mode)
        or path_stat.st_nlink != 1
        or stat.S_IMODE(path_stat.st_mode) & 0o077
    ):
        raise SafetyError("deletion transaction journal is unsafe")
    value = read_json(workspace, f"state/{DELETE_TRANSACTION_NAME}")
    if not isinstance(value, dict):
        raise ValidationError("deletion transaction journal must be an object")
    _validate_deletion_transaction(value)
    return value


def _apply_deletion_transaction(workspace: Path, transaction: dict[str, Any]) -> None:
    payloads = _validate_deletion_transaction(transaction)
    state_directory = workspace / "state"
    for name in DELETE_TARGET_FILES:
        atomic_write(state_directory / name, payloads[name])
    for name in DELETE_TARGET_FILES:
        if read_bytes(workspace, f"state/{name}") != payloads[name]:
            raise SafetyError(f"deletion transaction verification failed for {name}")
    _unlink_state_journal(
        workspace,
        DELETE_TRANSACTION_NAME,
        label="deletion transaction journal",
    )


def _recover_deletion_transaction(workspace: Path) -> dict[str, Any] | None:
    transaction = _load_deletion_transaction(workspace)
    if transaction is None:
        return None
    _apply_deletion_transaction(workspace, transaction)
    return transaction


def delete_events(
    path: str,
    *,
    event_ids: list[str],
    session_id: str | None,
    concept_id: str | None,
    item_id: str | None,
    dry_run: bool,
    confirm: bool,
) -> dict[str, Any]:
    workspace = secure_workspace(path)
    with workspace_lock(workspace):
        recovered = _recover_deletion_transaction(workspace)
        if recovered is not None:
            recovered_plan = recovered["plan"]
            return {
                "deleted_event_ids": recovered_plan["selected_event_ids"],
                "dependent_events_removed": len(
                    recovered_plan["dependent_event_ids_removed"]
                ),
                "dependent_events_rewritten": len(recovered_plan["rewritten_events"]),
                "remaining_event_count": recovered_plan["remaining_event_count"],
                "plan": recovered_plan,
                "review_events_removed": len(
                    recovered_plan["review_event_ids_removed"]
                ),
                "status": "deletion_recovered",
            }
        _validate_workspace_state(workspace, require_active=False)
        if item_id is not None:
            item_id = _require_identifier("item", item_id)
        events = load_events(workspace)
        reviews = read_jsonl(workspace, "state/reviews.jsonl")
        plan, retained, retained_reviews = _build_deletion_plan(
            events,
            reviews,
            event_ids=event_ids,
            session_id=session_id,
            concept_id=concept_id,
            item_id=item_id,
        )
        if dry_run:
            return {
                "dependent_event_ids_removed": plan["dependent_event_ids_removed"],
                "plan": plan,
                "review_event_ids_removed": plan["review_event_ids_removed"],
                "rewritten_events": plan["rewritten_events"],
                "selected_event_ids": plan["selected_event_ids"],
                "status": "preview",
                "would_delete_event_ids": plan["selected_event_ids"],
            }
        if not confirm:
            from .errors import ConfirmationRequired

            raise ConfirmationRequired(
                "physical deletion requires --confirm; run with --dry-run to preview exact event IDs"
            )

        transaction = _deletion_transaction(plan, retained, retained_reviews)
        atomic_write_json(workspace / "state" / DELETE_TRANSACTION_NAME, transaction)
        _apply_deletion_transaction(workspace, transaction)
    return {
        "deleted_event_ids": plan["selected_event_ids"],
        "dependent_events_removed": len(plan["dependent_event_ids_removed"]),
        "dependent_events_rewritten": len(plan["rewritten_events"]),
        "remaining_event_count": len(retained),
        "plan": plan,
        "review_events_removed": len(plan["review_event_ids_removed"]),
        "status": "deleted",
    }


def _workspace_deletion_plan(
    workspace: Path, *, ignored_paths: frozenset[str] = frozenset()
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    file_count = 0
    directory_count = 0
    for root, directories, files in os.walk(workspace, topdown=True, followlinks=False):
        root_path = Path(root)
        for name in sorted(directories):
            child = root_path / name
            child_stat = child.lstat()
            relative = child.relative_to(workspace).as_posix()
            if stat.S_ISLNK(child_stat.st_mode) or not stat.S_ISDIR(child_stat.st_mode):
                raise SafetyError(
                    f"workspace deletion rejects unsafe entry: {relative}"
                )
            entries.append(
                {
                    "kind": "directory",
                    "mode": stat.S_IMODE(child_stat.st_mode),
                    "path": relative,
                }
            )
            directory_count += 1
        for name in sorted(files):
            child = root_path / name
            child_stat = child.lstat()
            relative = child.relative_to(workspace).as_posix()
            if relative in ignored_paths:
                continue
            if stat.S_ISLNK(child_stat.st_mode) or not stat.S_ISREG(child_stat.st_mode):
                raise SafetyError(
                    f"workspace deletion rejects unsafe entry: {relative}"
                )
            entries.append(
                {
                    "content_sha256": hashlib.sha256(
                        read_bytes(workspace, relative)
                    ).hexdigest(),
                    "kind": "file",
                    "mode": stat.S_IMODE(child_stat.st_mode),
                    "path": relative,
                    "size": child_stat.st_size,
                }
            )
            file_count += 1
    encoded = json.dumps(
        sorted(entries, key=lambda entry: entry["path"]),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")
    return {
        "directory_count": directory_count,
        "file_count": file_count,
        "tree_entries_sha256": hashlib.sha256(encoded).hexdigest(),
    }


def _full_delete_quarantine(workspace: Path) -> Path:
    return workspace.parent / f".{workspace.name}.prax-teach-deleting"


def _full_delete_journal(workspace: Path) -> Path:
    return workspace.parent / f".{workspace.name}{FULL_DELETE_TRANSACTION_NAME}"


def _full_delete_transaction(workspace: Path, plan: dict[str, Any]) -> dict[str, Any]:
    workspace_stat = workspace.lstat()
    body = {
        "original_workspace": str(workspace),
        "plan": plan,
        "quarantine": str(_full_delete_quarantine(workspace)),
        "schema_version": 1,
        "workspace_device": workspace_stat.st_dev,
        "workspace_inode": workspace_stat.st_ino,
    }
    return {
        **body,
        "transaction_id": "full-delete-"
        + hashlib.sha256(canonical_json_bytes(body)).hexdigest()[:32],
    }


def _validate_full_delete_transaction(
    transaction: dict[str, Any], *, expected_workspace: Path
) -> dict[str, Any]:
    _exact_fields(
        transaction,
        {
            "original_workspace",
            "plan",
            "quarantine",
            "schema_version",
            "transaction_id",
            "workspace_device",
            "workspace_inode",
        },
        label="full deletion transaction",
    )
    if transaction.get("schema_version") != 1:
        raise ValidationError("unsupported full deletion transaction schema version")
    if transaction.get("original_workspace") != str(expected_workspace):
        raise SafetyError("full deletion transaction targets a different workspace")
    if transaction.get("quarantine") != str(
        _full_delete_quarantine(expected_workspace)
    ):
        raise SafetyError("full deletion transaction has a different quarantine path")
    for name in ("workspace_device", "workspace_inode"):
        value = transaction.get(name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValidationError(f"full deletion transaction {name} is invalid")
    plan = transaction.get("plan")
    if not isinstance(plan, dict):
        raise ValidationError("full deletion transaction plan must be an object")
    body = {
        "original_workspace": transaction["original_workspace"],
        "plan": plan,
        "quarantine": transaction["quarantine"],
        "schema_version": 1,
        "workspace_device": transaction["workspace_device"],
        "workspace_inode": transaction["workspace_inode"],
    }
    expected_id = (
        "full-delete-" + hashlib.sha256(canonical_json_bytes(body)).hexdigest()[:32]
    )
    if transaction.get("transaction_id") != expected_id:
        raise ValidationError(
            "full deletion transaction ID does not match its contents"
        )
    return plan


@contextlib.contextmanager
def _held_journal_parent(workspace: Path) -> Iterable[int]:
    if not _supports_full_delete_directory_fds():
        raise SafetyError("descriptor-relative journal cleanup is unavailable")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    anchor = _ACTIVE_WORKSPACE_IO.get()
    if anchor is not None and anchor.workspace == workspace:
        try:
            descriptor = os.open("..", flags, dir_fd=anchor.workspace_descriptor)
        except OSError as exc:
            raise SafetyError("workspace parent cannot be held safely") from exc
    else:
        try:
            descriptor = os.open(workspace.parent, flags)
        except OSError as exc:
            raise SafetyError("workspace parent cannot be held safely") from exc
    try:
        yield descriptor
    finally:
        os.close(descriptor)


def _supports_full_delete_directory_fds() -> bool:
    return (
        os.name == "posix"
        and hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
        and os.scandir in os.supports_fd
        and all(
            operation in os.supports_dir_fd
            for operation in (os.open, os.rename, os.rmdir, os.stat, os.unlink)
        )
    )


def _validate_held_journal_parent(workspace: Path, descriptor: int) -> None:
    try:
        parent_stat = workspace.parent.lstat()
    except FileNotFoundError as exc:
        raise SafetyError("workspace parent changed during journal cleanup") from exc
    if stat.S_ISLNK(parent_stat.st_mode) or not stat.S_ISDIR(parent_stat.st_mode):
        raise SafetyError("workspace parent changed into a symlink or non-directory")
    held_stat = os.fstat(descriptor)
    if (held_stat.st_dev, held_stat.st_ino) != (
        parent_stat.st_dev,
        parent_stat.st_ino,
    ):
        raise SafetyError("workspace parent changed during journal cleanup")


def _entry_exists_at(descriptor: int, name: str) -> bool:
    try:
        os.stat(name, dir_fd=descriptor, follow_symlinks=False)
    except FileNotFoundError:
        return False
    return True


def _unlink_parent_journal(workspace: Path, journal: Path, descriptor: int) -> None:
    _validate_held_journal_parent(workspace, descriptor)
    _validate_journal_entry(
        descriptor,
        journal.name,
        label="full deletion transaction journal",
    )
    try:
        os.unlink(journal.name, dir_fd=descriptor)
    except FileNotFoundError as exc:
        raise SafetyError(
            "full deletion transaction journal disappeared during cleanup"
        ) from exc
    os.fsync(descriptor)
    _validate_held_journal_parent(workspace, descriptor)


def _read_parent_delete_journal(
    journal: Path, *, parent_descriptor: int | None = None
) -> Any:
    try:
        if parent_descriptor is None:
            journal_stat = journal.lstat()
        else:
            journal_stat = os.stat(
                journal.name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
    except FileNotFoundError as exc:
        raise SafetyError("recoverable full deletion is missing its journal") from exc
    if (
        stat.S_ISLNK(journal_stat.st_mode)
        or not stat.S_ISREG(journal_stat.st_mode)
        or journal_stat.st_nlink != 1
        or stat.S_IMODE(journal_stat.st_mode) & 0o077
    ):
        raise SafetyError("full deletion transaction journal is unsafe")
    if journal_stat.st_size > 1024 * 1024:
        raise SafetyError("full deletion transaction journal is unexpectedly large")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        if parent_descriptor is None:
            descriptor = os.open(journal, flags)
        else:
            descriptor = os.open(journal.name, flags, dir_fd=parent_descriptor)
    except OSError as exc:
        raise SafetyError(
            "full deletion transaction journal cannot be opened safely"
        ) from exc
    try:
        opened_stat = os.fstat(descriptor)
        if (opened_stat.st_dev, opened_stat.st_ino) != (
            journal_stat.st_dev,
            journal_stat.st_ino,
        ):
            raise SafetyError("full deletion transaction journal changed during open")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            payload = handle.read()
    finally:
        os.close(descriptor)
    try:
        return json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(
            "full deletion transaction journal is invalid JSON"
        ) from exc


def _load_full_delete_transaction(
    expected_workspace: Path, *, parent_descriptor: int | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    transaction = _read_parent_delete_journal(
        _full_delete_journal(expected_workspace),
        parent_descriptor=parent_descriptor,
    )
    if not isinstance(transaction, dict):
        raise ValidationError("full deletion transaction journal must be an object")
    plan = _validate_full_delete_transaction(
        transaction, expected_workspace=expected_workspace
    )
    return transaction, plan


def _validate_full_delete_generation(path: Path, transaction: dict[str, Any]) -> None:
    try:
        path_stat = path.lstat()
    except FileNotFoundError as exc:
        raise SafetyError("full deletion workspace generation disappeared") from exc
    if stat.S_ISLNK(path_stat.st_mode) or not stat.S_ISDIR(path_stat.st_mode):
        raise SafetyError("full deletion target is a symlink or not a directory")
    if stat.S_IMODE(path_stat.st_mode) & 0o077:
        raise SafetyError("full deletion target no longer has a private mode")
    if (path_stat.st_dev, path_stat.st_ino) != (
        transaction["workspace_device"],
        transaction["workspace_inode"],
    ):
        raise SafetyError(
            "full deletion workspace generation does not match its journal"
        )


def _remove_full_delete_quarantine(
    workspace: Path,
    quarantine: Path,
    journal: Path,
    parent_descriptor: int,
    transaction: dict[str, Any],
) -> None:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    try:
        quarantine_descriptor = os.open(
            quarantine.name,
            flags,
            dir_fd=parent_descriptor,
        )
    except OSError as exc:
        raise SafetyError("full deletion quarantine cannot be opened safely") from exc
    try:
        opened_stat = os.fstat(quarantine_descriptor)
        current_stat = os.stat(
            quarantine.name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        expected_generation = (
            transaction["workspace_device"],
            transaction["workspace_inode"],
        )
        if (opened_stat.st_dev, opened_stat.st_ino) != expected_generation or (
            current_stat.st_dev,
            current_stat.st_ino,
        ) != expected_generation:
            raise SafetyError(
                "full deletion workspace generation does not match its journal"
            )
        _remove_directory_contents(quarantine_descriptor)
        current_stat = os.stat(
            quarantine.name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        if (current_stat.st_dev, current_stat.st_ino) != expected_generation:
            raise SafetyError(
                "full deletion workspace generation changed during removal"
            )
        os.rmdir(quarantine.name, dir_fd=parent_descriptor)
    except FileNotFoundError as exc:
        raise SafetyError(
            "full deletion workspace generation changed during removal"
        ) from exc
    finally:
        os.close(quarantine_descriptor)
    os.fsync(parent_descriptor)
    _unlink_parent_journal(workspace, journal, parent_descriptor)


def _remove_directory_contents(directory_descriptor: int) -> None:
    with os.scandir(directory_descriptor) as iterator:
        names = [entry.name for entry in iterator]
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    for name in names:
        try:
            entry_stat = os.stat(
                name,
                dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            continue
        if not stat.S_ISDIR(entry_stat.st_mode):
            try:
                os.unlink(name, dir_fd=directory_descriptor)
            except FileNotFoundError:
                pass
            continue
        try:
            child_descriptor = os.open(
                name,
                flags,
                dir_fd=directory_descriptor,
            )
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise SafetyError(
                "full deletion directory changed during recursive removal"
            ) from exc
        try:
            opened_stat = os.fstat(child_descriptor)
            if (opened_stat.st_dev, opened_stat.st_ino) != (
                entry_stat.st_dev,
                entry_stat.st_ino,
            ):
                raise SafetyError(
                    "full deletion directory changed during recursive removal"
                )
            _remove_directory_contents(child_descriptor)
            current_stat = os.stat(
                name,
                dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
            if (current_stat.st_dev, current_stat.st_ino) != (
                opened_stat.st_dev,
                opened_stat.st_ino,
            ):
                raise SafetyError(
                    "full deletion directory changed during recursive removal"
                )
            os.rmdir(name, dir_fd=directory_descriptor)
        except FileNotFoundError as exc:
            raise SafetyError(
                "full deletion directory changed during recursive removal"
            ) from exc
        finally:
            os.close(child_descriptor)


def _recover_quarantined_workspace_deletion(workspace: Path) -> dict[str, Any] | None:
    """Finish a confirmed deletion, including a partially removed quarantine."""

    with _held_journal_parent(workspace) as parent_descriptor:
        _validate_held_journal_parent(workspace, parent_descriptor)
        quarantine = _full_delete_quarantine(workspace)
        journal = _full_delete_journal(workspace)
        journal_exists = _entry_exists_at(parent_descriptor, journal.name)
        quarantine_exists = _entry_exists_at(parent_descriptor, quarantine.name)
        workspace_exists = _entry_exists_at(parent_descriptor, workspace.name)
        if not journal_exists:
            if quarantine_exists:
                raise SafetyError("full deletion quarantine exists without its journal")
            return None
        transaction, plan = _load_full_delete_transaction(
            workspace,
            parent_descriptor=parent_descriptor,
        )
        if workspace_exists and quarantine_exists:
            raise SafetyError(
                "full deletion found both live and quarantined workspaces"
            )
        if workspace_exists:
            _validate_full_delete_generation(workspace, transaction)
            current_plan = _workspace_deletion_plan(workspace)
            if current_plan != plan:
                raise SafetyError("full deletion live workspace content has diverged")
            os.rename(
                workspace.name,
                quarantine.name,
                src_dir_fd=parent_descriptor,
                dst_dir_fd=parent_descriptor,
            )
            os.fsync(parent_descriptor)
            quarantine_exists = True
        if quarantine_exists:
            _validate_full_delete_generation(quarantine, transaction)
            _remove_full_delete_quarantine(
                workspace,
                quarantine,
                journal,
                parent_descriptor,
                transaction,
            )
        else:
            # The subtree was completely removed before interruption; the durable
            # parent tombstone is deliberately removed last.
            _unlink_parent_journal(workspace, journal, parent_descriptor)
        return {
            "plan": plan,
            "status": "all_state_deletion_recovered",
            "workspace": str(workspace),
        }


def delete_workspace(path: str, *, dry_run: bool, confirm: bool) -> dict[str, Any]:
    """Preview or remove one exact validated learner workspace."""

    from .errors import ConfirmationRequired

    candidate = prepare_private_parent(path, create_missing=False)
    if not candidate.exists() and not candidate.is_symlink():
        with workspace_generation_lock(candidate):
            recovered = _recover_quarantined_workspace_deletion(candidate)
            if recovered is not None:
                return recovered
        # Preserve the ordinary not-found error and its stable CLI mapping.
    workspace = secure_workspace(candidate)
    with workspace_lock(workspace):
        _validate_workspace_state(workspace, require_active=False)
        journal = _full_delete_journal(workspace)
        if journal.exists() or journal.is_symlink():
            recovered = _recover_quarantined_workspace_deletion(workspace)
            if recovered is None:
                raise SafetyError("full deletion journal could not be recovered")
            return recovered
        plan = _workspace_deletion_plan(workspace)
        if dry_run:
            return {
                "plan": plan,
                "status": "preview",
                "workspace": str(workspace),
            }
        if not confirm:
            raise ConfirmationRequired(
                "full workspace deletion requires --confirm; run with --dry-run to preview the exact tree"
            )
        if not _supports_full_delete_directory_fds():
            raise SafetyError("platform lacks symlink-safe recursive deletion")
        quarantine = _full_delete_quarantine(workspace)
        if quarantine.exists() or quarantine.is_symlink():
            raise SafetyError("workspace deletion quarantine path unexpectedly exists")
        transaction = _full_delete_transaction(workspace, plan)
        atomic_write_json(journal, transaction)
        recovered = _recover_quarantined_workspace_deletion(workspace)
        if recovered is None:
            raise SafetyError("confirmed full deletion did not complete")
    return {
        "plan": plan,
        "status": "all_state_deleted",
        "workspace": str(workspace),
    }


def show_state(path: str) -> dict[str, Any]:
    workspace = secure_workspace(path)
    with workspace_lock(workspace):
        _validate_workspace_state(workspace, require_active=False)
        learner = read_json(workspace, "state/learner.json")
        concepts = read_json(workspace, "state/concepts.json")
        misconceptions = read_json(workspace, "state/misconceptions.json")
        events = load_events(workspace)
        expected_concepts, expected_misconceptions = project_events(events)
        if concepts != expected_concepts or misconceptions != expected_misconceptions:
            raise ValidationError(
                "stored learner projections are stale or do not match the evidence log; run rebuild while persistence consent is active"
            )
    return {
        "concepts": concepts,
        "consent": learner["consent"],
        "evidence_event_count": len(events),
        "goal": learner["goal"],
        "learner_id": learner["learner_id"],
        "misconceptions": misconceptions,
        "schema_version": SCHEMA_VERSION,
    }
