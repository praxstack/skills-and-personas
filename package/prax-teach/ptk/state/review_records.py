"""Strict, dependency-free validation for replayable review records."""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from typing import Any

from . import SCHEMA_VERSION
from .errors import ValidationError

FSRS_VERSION = "6.3.1"
SCHEDULER_EVENT_VERSION = "2"
HORIZON_POLICY_VERSION = "1"
DIMENSIONS = frozenset(
    {
        "recognition",
        "recall",
        "explanation",
        "application",
        "discrimination",
        "transfer",
    }
)
HIGHER_ORDER_DIMENSIONS = frozenset({"application", "discrimination", "transfer"})
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
REVIEW_ID_RE = re.compile(r"^review-[0-9a-f]{32}$")
EVIDENCE_ID_RE = re.compile(r"^evt-[0-9a-f]{32}$")
CONTENT_VERSION_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
RATING_NUMBERS = {"Again": 1, "Hard": 2, "Good": 3, "Easy": 4}


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


def _timestamp(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{label} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValidationError(f"{label} must include a UTC offset")
    return (
        parsed.astimezone(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _timestamp_datetime(value: Any, *, label: str) -> datetime:
    return datetime.fromisoformat(_timestamp(value, label=label).replace("Z", "+00:00"))


def _identifier(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER_RE.fullmatch(value):
        raise ValidationError(f"{label} is not a valid pseudonymous identifier")
    return value


def _reason(value: Any, *, label: str = "review reason") -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 1000:
        raise ValidationError(f"{label} must contain 1 to 1000 characters")
    if "\x00" in value:
        raise ValidationError(f"{label} contains a NUL byte")
    return value.strip()


def _finite_number(value: Any, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{label} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise ValidationError(f"{label} must be a finite number")
    return number


def horizon_scheduler_config(horizon_days: int) -> dict[str, Any]:
    if horizon_days <= 14:
        desired_retention = 0.95
    elif horizon_days <= 45:
        desired_retention = 0.92
    elif horizon_days <= 120:
        desired_retention = 0.90
    elif horizon_days <= 365:
        desired_retention = 0.88
    else:
        desired_retention = 0.85
    return {
        "desired_retention": desired_retention,
        "enable_fuzzing": False,
        "horizon_days": horizon_days,
        "horizon_policy_version": HORIZON_POLICY_VERSION,
        "maximum_interval": horizon_days,
    }


def derive_rating(*, dimension: str, score: float, hint_level: int) -> tuple[str, str]:
    """Derive the only rating and explanation permitted by stored performance."""

    if score < 0.8:
        return (
            "Again",
            "Again was selected because the observed score was below the 0.8 success threshold.",
        )
    if hint_level >= 3:
        return (
            "Hard",
            "Hard was selected because success required hint level 3 or higher.",
        )
    if hint_level == 0 and dimension in HIGHER_ORDER_DIMENSIONS and score >= 0.9:
        return (
            "Easy",
            "Easy was selected because an unassisted higher-order response scored at least 0.9.",
        )
    return (
        "Good",
        "Good was selected because the response succeeded without meeting the strict unassisted higher-order Easy rule.",
    )


def review_event_id(record_without_id: dict[str, Any]) -> str:
    encoded = json.dumps(
        record_without_id,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")
    return "review-" + hashlib.sha256(encoded).hexdigest()[:32]


def stable_card_id(item_id: str) -> int:
    """Return the scheduler's deterministic positive card identifier."""

    return int(hashlib.sha256(item_id.encode("utf-8")).hexdigest()[:15], 16) or 1


def _validate_card(card: Any) -> dict[str, Any]:
    if not isinstance(card, dict):
        raise ValidationError("review card must be an object")
    _exact_fields(
        card,
        {"card_id", "difficulty", "due", "last_review", "stability", "state", "step"},
        label="review card",
    )
    card_id = card["card_id"]
    if isinstance(card_id, bool) or not isinstance(card_id, int) or card_id < 1:
        raise ValidationError("review card_id must be a positive integer")
    difficulty = _finite_number(card["difficulty"], label="review card difficulty")
    if not 1 <= difficulty <= 10:
        raise ValidationError("review card difficulty must be between 1 and 10")
    stability = _finite_number(card["stability"], label="review card stability")
    if stability <= 0:
        raise ValidationError("review card stability must be greater than zero")
    due = _timestamp(card["due"], label="review card due")
    last_review = _timestamp(card["last_review"], label="review card last_review")
    if _timestamp_datetime(due, label="review card due") < _timestamp_datetime(
        last_review, label="review card last_review"
    ):
        raise ValidationError("review card due must not precede last_review")
    state = card["state"]
    if isinstance(state, bool) or not isinstance(state, int) or state not in {1, 2, 3}:
        raise ValidationError("review card state must be 1, 2, or 3")
    step = card["step"]
    if step is not None and (
        isinstance(step, bool) or not isinstance(step, int) or step < 0
    ):
        raise ValidationError("review card step must be a non-negative integer or null")
    return card


def _validate_review_log(review_log: Any) -> dict[str, Any]:
    if not isinstance(review_log, dict):
        raise ValidationError("review log must be an object")
    _exact_fields(
        review_log,
        {"card_id", "rating", "review_datetime", "review_duration"},
        label="review log",
    )
    card_id = review_log["card_id"]
    if isinstance(card_id, bool) or not isinstance(card_id, int) or card_id < 1:
        raise ValidationError("review log card_id must be a positive integer")
    rating = review_log["rating"]
    if (
        isinstance(rating, bool)
        or not isinstance(rating, int)
        or rating not in {1, 2, 3, 4}
    ):
        raise ValidationError("review log rating must be an integer from 1 to 4")
    _timestamp(review_log["review_datetime"], label="review log review_datetime")
    duration = review_log["review_duration"]
    if duration is not None and (
        isinstance(duration, bool) or not isinstance(duration, int) or duration < 0
    ):
        raise ValidationError("review duration must be a non-negative integer or null")
    return review_log


def validate_review_record(record: Any) -> dict[str, Any]:
    """Validate exact schema shape, nested semantics, and content-bound ID."""

    if not isinstance(record, dict):
        raise ValidationError("review record must be an object")
    event_type = record.get("event_type")
    base = {
        "event_id",
        "event_type",
        "scheduler_event_version",
        "schema_version",
        "timestamp",
    }
    if event_type == "review":
        expected = base | {
            "algorithm",
            "algorithm_version",
            "concept_id",
            "dimension",
            "explanation",
            "input",
            "item_id",
            "output",
            "rating",
            "reason",
            "scheduler_config",
        }
    elif event_type in {"snooze", "reschedule"}:
        expected = base | {"due", "item_id", "reason"}
    elif event_type == "review_controls":
        expected = base | {"reason", "status"}
    else:
        raise ValidationError(f"unsupported scheduler event_type: {event_type!r}")
    _exact_fields(record, expected, label="review record")

    if record["schema_version"] != SCHEMA_VERSION:
        raise ValidationError("unsupported review schema_version")
    if record["scheduler_event_version"] != SCHEDULER_EVENT_VERSION:
        raise ValidationError("unsupported scheduler_event_version")
    if not isinstance(record["event_id"], str) or not REVIEW_ID_RE.fullmatch(
        record["event_id"]
    ):
        raise ValidationError("review event_id is invalid")
    record_timestamp = _timestamp(record["timestamp"], label="review timestamp")

    if event_type == "review":
        if record["algorithm"] != "fsrs" or record["algorithm_version"] != FSRS_VERSION:
            raise ValidationError("review must use the pinned fsrs algorithm version")
        concept = _identifier(record["concept_id"], label="review concept_id")
        item = _identifier(record["item_id"], label="review item_id")
        dimension = record["dimension"]
        if dimension not in DIMENSIONS:
            raise ValidationError("review dimension is invalid")
        rating = record["rating"]
        if rating not in RATING_NUMBERS:
            raise ValidationError("review rating is invalid")
        explanation = _reason(record["explanation"], label="review explanation")
        reason = _reason(record["reason"])
        if explanation != reason:
            raise ValidationError("review explanation and reason must match")

        input_record = record["input"]
        if not isinstance(input_record, dict):
            raise ValidationError("review input must be an object")
        _exact_fields(
            input_record,
            {
                "concept_id",
                "content_id",
                "content_version",
                "dimension",
                "hint_level",
                "item_id",
                "item_version",
                "model_and_prompt_version",
                "objective_id",
                "observation_event_id",
                "score",
                "session_id",
                "source_provenance",
                "timestamp",
            },
            label="review input",
        )
        if (
            _identifier(input_record["concept_id"], label="review input concept_id")
            != concept
        ):
            raise ValidationError("review input concept_id does not match the record")
        if _identifier(input_record["item_id"], label="review input item_id") != item:
            raise ValidationError("review input item_id does not match the record")
        if input_record["dimension"] != dimension:
            raise ValidationError("review input dimension does not match the record")
        _identifier(input_record["content_id"], label="review input content_id")
        content_version = input_record["content_version"]
        if (
            not isinstance(content_version, str)
            or CONTENT_VERSION_RE.fullmatch(content_version) is None
        ):
            raise ValidationError("review input content_version is invalid")
        _identifier(input_record["objective_id"], label="review input objective_id")
        _identifier(input_record["item_version"], label="review input item_version")
        _identifier(input_record["session_id"], label="review input session_id")
        observation_event_id = input_record["observation_event_id"]
        if (
            not isinstance(observation_event_id, str)
            or EVIDENCE_ID_RE.fullmatch(observation_event_id) is None
        ):
            raise ValidationError("review input observation_event_id is invalid")
        model_and_prompt_version = input_record["model_and_prompt_version"]
        if (
            not isinstance(model_and_prompt_version, str)
            or not model_and_prompt_version.strip()
            or len(model_and_prompt_version) > 2000
            or "\x00" in model_and_prompt_version
        ):
            raise ValidationError("review input model_and_prompt_version is invalid")
        source_provenance = input_record["source_provenance"]
        if not isinstance(source_provenance, list) or not source_provenance:
            raise ValidationError(
                "review input source_provenance must contain a versioned source"
            )
        source_keys: list[tuple[str, str]] = []
        for source in source_provenance:
            if not isinstance(source, dict):
                raise ValidationError("review input source provenance is invalid")
            _exact_fields(
                source,
                {"source_id", "version_or_date"},
                label="review input source provenance",
            )
            source_id = _identifier(source["source_id"], label="review input source_id")
            source_version = source["version_or_date"]
            if (
                not isinstance(source_version, str)
                or not source_version.strip()
                or len(source_version) > 256
                or "\x00" in source_version
            ):
                raise ValidationError("review input source version is invalid")
            source_keys.append((source_id, source_version))
        if len(source_keys) != len(set(source_keys)):
            raise ValidationError("review input source provenance must be unique")
        hint = input_record["hint_level"]
        if isinstance(hint, bool) or not isinstance(hint, int) or not 0 <= hint <= 4:
            raise ValidationError(
                "review input hint_level must be an integer from 0 to 4"
            )
        score = _finite_number(input_record["score"], label="review input score")
        if not 0 <= score <= 1:
            raise ValidationError("review input score must be between 0 and 1")
        input_timestamp = _timestamp(
            input_record["timestamp"], label="review input timestamp"
        )
        if input_timestamp != record_timestamp:
            raise ValidationError("review input timestamp does not match the record")
        derived_rating, derived_explanation = derive_rating(
            dimension=dimension,
            score=score,
            hint_level=hint,
        )
        if rating != derived_rating:
            raise ValidationError(
                "review rating does not match the rating derived from performance input"
            )
        if explanation != derived_explanation:
            raise ValidationError(
                "review explanation does not match the explanation derived from performance input"
            )

        output = record["output"]
        if not isinstance(output, dict):
            raise ValidationError("review output must be an object")
        _exact_fields(output, {"card", "review_log"}, label="review output")
        card = _validate_card(output["card"])
        review_log = _validate_review_log(output["review_log"])
        if card["card_id"] != stable_card_id(item):
            raise ValidationError("review card_id does not match the item_id")
        if card["card_id"] != review_log["card_id"]:
            raise ValidationError("review card and log card_id values do not match")
        if review_log["rating"] != RATING_NUMBERS[rating]:
            raise ValidationError("review rating does not match the FSRS review log")
        card_timestamp = _timestamp(
            card["last_review"], label="review card last_review"
        )
        log_timestamp = _timestamp(
            review_log["review_datetime"], label="review log review_datetime"
        )
        if card_timestamp != record_timestamp:
            raise ValidationError(
                "review card last_review timestamp does not match the record"
            )
        if log_timestamp != record_timestamp:
            raise ValidationError(
                "review log review_datetime timestamp does not match the record"
            )

        config = record["scheduler_config"]
        if not isinstance(config, dict):
            raise ValidationError("review scheduler_config must be an object")
        _exact_fields(
            config,
            {
                "desired_retention",
                "enable_fuzzing",
                "horizon_days",
                "horizon_policy_version",
                "maximum_interval",
            },
            label="review scheduler_config",
        )
        horizon = config["horizon_days"]
        if (
            isinstance(horizon, bool)
            or not isinstance(horizon, int)
            or not 1 <= horizon <= 3650
        ):
            raise ValidationError("review scheduler horizon is invalid")
        if config != horizon_scheduler_config(horizon):
            raise ValidationError("review scheduler horizon policy is invalid")
    elif event_type in {"snooze", "reschedule"}:
        _identifier(record["item_id"], label="review item_id")
        _timestamp(record["due"], label="review due")
        _reason(record["reason"])
    else:
        if record["status"] not in {"enabled", "disabled"}:
            raise ValidationError("review control status is invalid")
        _reason(record["reason"])

    expected_id_payload = dict(record)
    expected_id_payload.pop("event_id")
    if record["event_id"] != review_event_id(expected_id_payload):
        raise ValidationError("review event_id does not match its record")
    return record


def validate_review_sequence(records: list[dict[str, Any]]) -> None:
    """Validate cross-record ordering, ownership, and control dependencies."""

    seen: set[str] = set()
    previous_timestamp: datetime | None = None
    item_bindings: dict[str, tuple[str, str]] = {}
    last_reviews: dict[str, datetime] = {}
    reviewed_observations: set[str] = set()
    review_status = "enabled"
    for record in records:
        validate_review_record(record)
        timestamp = _timestamp_datetime(record["timestamp"], label="review timestamp")
        if previous_timestamp is not None and timestamp < previous_timestamp:
            raise ValidationError("review timestamps must be monotonic")
        previous_timestamp = timestamp
        event_id = str(record["event_id"])
        if event_id in seen:
            raise ValidationError(f"duplicate review event_id: {event_id}")
        seen.add(event_id)

        event_type = record["event_type"]
        if event_type == "review":
            if review_status != "enabled":
                raise ValidationError(
                    "review record encountered while reviews are disabled"
                )
            item_id = str(record["item_id"])
            observation_event_id = str(record["input"]["observation_event_id"])
            if observation_event_id in reviewed_observations:
                raise ValidationError(
                    "one observation event cannot produce multiple FSRS reviews"
                )
            reviewed_observations.add(observation_event_id)
            binding = (str(record["concept_id"]), str(record["dimension"]))
            existing = item_bindings.get(item_id)
            if existing is not None and existing[0] != binding[0]:
                raise ValidationError(
                    f"review item_id {item_id!r} cannot be reused across concepts"
                )
            if existing is not None and existing[1] != binding[1]:
                raise ValidationError(
                    f"review item_id {item_id!r} must preserve its dimension"
                )
            item_bindings[item_id] = binding
            last_reviews[item_id] = _timestamp_datetime(
                record["output"]["card"]["last_review"],
                label="review card last_review",
            )
        elif event_type in {"snooze", "reschedule"}:
            item_id = str(record["item_id"])
            if item_id not in item_bindings:
                raise ValidationError(
                    f"{event_type} references an item with no earlier review history"
                )
            due = _timestamp_datetime(record["due"], label="review due")
            if due < last_reviews[item_id]:
                raise ValidationError(
                    f"{event_type} due must not precede the item's last_review"
                )
        else:
            next_status = str(record["status"])
            if next_status == review_status:
                raise ValidationError(f"reviews are already {next_status}")
            review_status = next_status


def observation_input_from_event(event: dict[str, Any]) -> dict[str, Any]:
    """Return the exact minimal scheduler input derivable from one observation."""

    return {
        "concept_id": event["concept_id"],
        "content_id": event["content_id"],
        "content_version": event["content_version"],
        "dimension": event["dimension"],
        "hint_level": event["hint_level"],
        "item_id": event["item_id"],
        "item_version": event["item_version"],
        "model_and_prompt_version": event["model_and_prompt_version"],
        "objective_id": event["objective_id"],
        "observation_event_id": event["event_id"],
        "score": event["result"]["score"],
        "session_id": event["session_id"],
        "source_provenance": [dict(source) for source in event["source_provenance"]],
        "timestamp": _timestamp(event["timestamp"], label="observation timestamp"),
    }


def validate_review_evidence_bindings(
    records: list[dict[str, Any]], events: list[dict[str, Any]]
) -> None:
    """Fail closed unless every FSRS row names one active exact observation."""

    by_id = {str(event["event_id"]): event for event in events}
    inactive: set[str] = set()
    for event in events:
        if event["event_type"] == "correction":
            inactive.add(str(event["corrected_event_id"]))
        elif event["event_type"] == "invalidation":
            inactive.update(str(value) for value in event["invalidated_event_ids"])
    for record in records:
        if record["event_type"] != "review":
            continue
        observation_event_id = str(record["input"]["observation_event_id"])
        observation = by_id.get(observation_event_id)
        if observation is None or observation.get("event_type") != "observation":
            raise ValidationError(
                "review references an observation event that does not exist"
            )
        if observation_event_id in inactive:
            raise ValidationError("review references an inactive observation event")
        if record["input"] != observation_input_from_event(observation):
            raise ValidationError(
                "review input does not match its validated observation event"
            )
