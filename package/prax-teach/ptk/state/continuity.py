"""Optional directory continuity, independent of learning evidence and schemas.

Loader/validator have no state imports. Operations import state locally and use
its established consent validation and descriptor-anchored workspace lock.
"""

from __future__ import annotations

import json
import stat
from pathlib import Path
from typing import Any

from .errors import (
    ConfirmationRequired,
    ConsentRequired,
    SafetyError,
    StateNotFound,
    ValidationError,
)
from .io import (
    link_count_ok,
    _active_target_for_workspace_relative,
    _validate_anchored_destination,
    _validate_anchored_parent,
    atomic_write_json,
    contained_path,
    read_json,
    secure_workspace,
    workspace_lock,
)

PREFERENCE_KEYS = frozenset(
    {"teaching_style", "delivery", "medium", "detail", "language", "accessibility"}
)
CONTENT_FIELDS = frozenset(
    {"preferences", "covered_topics", "last_lesson", "agent_summary", "next_topic"}
)
FIELDS = CONTENT_FIELDS | {"schema_version", "revision", "consent"}
MAX_REVISION = 9007199254740991


def _object(
    value: Any, fields: set[str] | frozenset[str], label: str
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValidationError(
            f"{label} must contain exactly: {', '.join(sorted(fields))}"
        )
    return value


def _text(value: Any, maximum: int, label: str) -> None:
    if not isinstance(value, str) or not 1 <= len(value) <= maximum:
        raise ValidationError(f"{label} must be text of length 1..{maximum}")


def validate_continuity_document(value: Any) -> dict[str, Any]:
    """Validate exact fields, bounded content and explicit provenance."""
    record = _object(value, FIELDS, "continuity")
    if type(record["schema_version"]) is not int or record["schema_version"] != 1:
        raise ValidationError("continuity schema_version must be integer 1")
    if (
        type(record["revision"]) is not int
        or not 1 <= record["revision"] <= MAX_REVISION
    ):
        raise ValidationError("continuity revision must be a positive bounded integer")
    consent = _object(record["consent"], {"status"}, "continuity consent")
    if consent["status"] not in ("granted", "withdrawn"):
        raise ValidationError("continuity consent status must be granted or withdrawn")
    preferences = record["preferences"]
    if not isinstance(preferences, dict) or not set(preferences) <= PREFERENCE_KEYS:
        raise ValidationError("continuity preferences contain an unsupported key")
    for key, preference in preferences.items():
        _object(preference, {"value", "provenance"}, f"preference {key}")
        _text(preference["value"], 512, f"preference {key} value")
        if preference["provenance"] != "user-stated":
            raise ValidationError("preferences require user-stated provenance")
    topics = record["covered_topics"]
    if not isinstance(topics, list) or len(topics) > 100:
        raise ValidationError(
            "covered_topics must be an exposure-only list of at most 100 topics"
        )
    for topic in topics:
        _text(topic, 256, "covered topic")
    lesson = record["last_lesson"]
    if lesson is not None:
        _object(lesson, {"id", "position"}, "last_lesson")
        _text(lesson["id"], 256, "last_lesson id")
        _text(lesson["position"], 512, "last_lesson position")
    for key, provenance, maximum, text_field in (
        ("agent_summary", "agent-authored", 2048, "text"),
        ("next_topic", "learner-requested", 512, "value"),
    ):
        item = record[key]
        if item is not None:
            _object(item, {text_field, "provenance"}, key)
            _text(item[text_field], maximum, key)
            if item["provenance"] != provenance:
                raise ValidationError(f"{key} requires {provenance} provenance")
    return record


def load_continuity(workspace: Path) -> dict[str, Any] | None:
    """Call under workspace_lock; only genuine absence is optional."""
    target = _active_target_for_workspace_relative(workspace, "state/continuity.json")
    if target is not None:
        _validate_anchored_parent(target)
        entry = _validate_anchored_destination(target)
        if entry is None:
            return None
    else:
        # Existing non-POSIX lock path uses contained no-follow validation.
        try:
            entry = contained_path(
                workspace, "state/continuity.json", must_exist=True
            ).lstat()
        except StateNotFound:
            return None
    if (
        not stat.S_ISREG(entry.st_mode)
        or not link_count_ok(entry, "state/continuity.json")
        or stat.S_IMODE(entry.st_mode) & 0o077
    ):
        raise SafetyError(
            "continuity record must be a private regular file with one link"
        )
    try:
        value = read_json(workspace, "state/continuity.json")
    except StateNotFound as exc:
        raise SafetyError("continuity record disappeared during locked read") from exc
    return validate_continuity_document(value)


def _active(record: dict[str, Any] | None) -> None:
    if record is None or record["consent"]["status"] != "granted":
        raise ConsentRequired(
            "continuity requires an explicit extension grant; use continuity-grant --consent"
        )


def _expected(record: dict[str, Any] | None, revision: int) -> None:
    if type(revision) is not int or not 0 <= revision <= MAX_REVISION:
        raise ValidationError("expected revision must be a nonnegative bounded integer")
    current = record["revision"] if record is not None else 0
    if current != revision:
        raise ValidationError(
            f"stale continuity revision: expected {revision}, current {current}"
        )


def _write(workspace: Path, record: dict[str, Any], revision: int) -> dict[str, Any]:
    record["revision"] = revision + 1
    validate_continuity_document(record)
    atomic_write_json(workspace / "state/continuity.json", record)
    return record


def inspect_continuity(path: str, *, resume: bool = False) -> dict[str, Any] | None:
    from .state import _validate_workspace_state

    workspace = secure_workspace(path)
    with workspace_lock(workspace):
        _validate_workspace_state(workspace, require_active=resume)
        record = load_continuity(workspace)
        # Absence never creates a record, and is a valid legacy resume result.
        if resume and record is not None:
            _active(record)
        return record


def grant_continuity(
    path: str, *, consent: bool, expected_revision: int
) -> dict[str, Any]:
    from .state import _validate_workspace_state

    if not consent:
        raise ConsentRequired(
            "explicit consent is required for user-stated preferences and directory continuity"
        )
    workspace = secure_workspace(path)
    with workspace_lock(workspace):
        _validate_workspace_state(workspace)
        record = load_continuity(workspace)
        _expected(record, expected_revision)
        if record is None:
            record = {
                "schema_version": 1,
                "revision": 1,
                "consent": {"status": "granted"},
                "preferences": {},
                "covered_topics": [],
                "last_lesson": None,
                "agent_summary": None,
                "next_topic": None,
            }
        record["consent"] = {"status": "granted"}
        return _write(workspace, record, expected_revision)


def update_continuity(
    path: str, data: Any, *, expected_revision: int
) -> dict[str, Any]:
    from .state import _validate_workspace_state

    if not isinstance(data, dict) or not data or not set(data) <= CONTENT_FIELDS:
        raise ValidationError(
            "continuity update must contain one or more supported content fields, no metadata"
        )
    workspace = secure_workspace(path)
    with workspace_lock(workspace):
        _validate_workspace_state(workspace)
        record = load_continuity(workspace)
        _expected(record, expected_revision)
        _active(record)
        assert record is not None
        record.update(data)
        return _write(workspace, record, expected_revision)


def read_update_file(path: str) -> Any:
    """Read caller-selected input only; never follow instructions inside it."""
    try:
        with Path(path).open("rb") as handle:
            raw = handle.read(262145)
        # Bounds on the record also apply after parsing; cap input allocation.
        if len(raw) > 262144:
            raise ValidationError("continuity update JSON exceeds 262144 bytes")
        return json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationError("cannot read valid UTF-8 continuity update JSON") from exc


def withdraw_continuity(path: str, *, expected_revision: int) -> dict[str, Any]:
    from .state import _validate_workspace_state

    workspace = secure_workspace(path)
    with workspace_lock(workspace):
        _validate_workspace_state(workspace, require_active=False)
        record = load_continuity(workspace)
        _expected(record, expected_revision)
        if record is None:
            raise ValidationError("no continuity grant exists to withdraw")
        record["consent"] = {"status": "withdrawn"}
        return _write(workspace, record, expected_revision)


def reset_continuity(
    path: str,
    *,
    expected_revision: int,
    preferences_only: bool,
    dry_run: bool,
    confirm: bool,
) -> dict[str, Any] | None:
    from .state import _unlink_state_journal, _validate_workspace_state

    workspace = secure_workspace(path)
    with workspace_lock(workspace):
        _validate_workspace_state(workspace, require_active=False)
        record = load_continuity(workspace)
        _expected(record, expected_revision)
        if dry_run:
            return {
                "status": "preview",
                "revision": expected_revision,
                "scope": "preferences" if preferences_only else "all-continuity",
                "record_present": record is not None,
            }
        if not confirm:
            raise ConfirmationRequired(
                "continuity reset requires --confirm or --dry-run"
            )
        if record is None:
            return None
        if preferences_only:
            record["preferences"] = {}
            return _write(workspace, record, expected_revision)
        _unlink_state_journal(workspace, "continuity.json", label="continuity record")
        return None
