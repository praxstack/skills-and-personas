"""Pinned FSRS scheduling with an append-only, replayable learner queue.

Review scheduling is deliberately separate from the concept-evidence projection:
reviews may change what is due next, but they never mutate a mastery claim.  The
queue is reconstructed exclusively from ``state/reviews.jsonl`` so there is no
hidden mutable scheduler database to drift from the learner-visible history.
"""

from __future__ import annotations

import importlib.metadata
from datetime import datetime
from pathlib import Path
from typing import Any

from . import SCHEMA_VERSION
from .errors import PraxTeachError, ValidationError
from .io import append_jsonl, read_jsonl, secure_workspace, workspace_lock
from .review_records import (
    FSRS_VERSION,
    SCHEDULER_EVENT_VERSION,
    derive_rating,
    horizon_scheduler_config,
    observation_input_from_event,
    review_event_id,
    stable_card_id,
    validate_review_record,
    validate_review_sequence,
)
from .state import (
    SAFE_IDENTIFIER_RE,
    _active_observations,
    _validate_workspace_state,
    load_events,
    normalize_timestamp,
)

FSRS_PACKAGE = "fsrs"
REVIEWS_PATH = "state/reviews.jsonl"


class SchedulerDependencyError(PraxTeachError):
    """The exact scheduling dependency is unavailable or has drifted."""

    exit_code = 2


def _load_fsrs() -> tuple[Any, Any, Any]:
    """Load the exact audited FSRS version, with no heuristic fallback."""

    message = f"{FSRS_PACKAGE}=={FSRS_VERSION} is required for review scheduling"
    try:
        installed = importlib.metadata.version(FSRS_PACKAGE)
    except importlib.metadata.PackageNotFoundError as exc:
        raise SchedulerDependencyError(message) from exc
    if installed != FSRS_VERSION:
        raise SchedulerDependencyError(f"{message}; installed version is {installed!r}")
    try:
        from fsrs import Card, Rating, Scheduler
    except (ImportError, ModuleNotFoundError) as exc:
        raise SchedulerDependencyError(message) from exc
    return Card, Rating, Scheduler


def _require_identifier(name: str, value: str) -> str:
    normalized = value.strip()
    if not SAFE_IDENTIFIER_RE.fullmatch(normalized):
        raise ValidationError(
            f"{name} must be a pseudonymous identifier using letters, numbers, '.', '_', ':', or '-'"
        )
    return normalized


def _require_reason(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValidationError("reason must not be empty")
    if len(normalized) > 1000:
        raise ValidationError("reason exceeds the 1000-character limit")
    if "\x00" in normalized:
        raise ValidationError("reason contains a NUL byte")
    return normalized


def _as_datetime(value: str) -> datetime:
    normalized = normalize_timestamp(value)
    return datetime.fromisoformat(normalized.replace("Z", "+00:00"))


def _event_id(record_without_id: dict[str, Any]) -> str:
    return review_event_id(record_without_id)


def _card_id(item_id: str) -> int:
    """Return a stable positive ID instead of FSRS's wall-clock-based default."""

    return stable_card_id(item_id)


def _validate_consent(workspace: Path) -> dict[str, Any]:
    # Every scheduler entrypoint holds the shared workspace lock before calling
    # this function. Recover any durable deletion transaction before reading or
    # appending reviews so a later recovery cannot erase a scheduler event that
    # was appended to a partially rewritten log.
    return _validate_workspace_state(workspace)


def _horizon_scheduler_config(horizon_days: int) -> dict[str, Any]:
    """Map the learner-approved horizon to an explicit FSRS policy.

    A nearer independent-performance horizon uses a higher desired retention
    rate (and therefore denser retrieval), while a longer horizon uses a lower
    but still conservative rate.  The horizon also caps FSRS's maximum
    interval so the next scheduled retrieval cannot silently fall beyond the
    learner's stated target window.
    """

    return horizon_scheduler_config(horizon_days)


def _validate_review_record(record: dict[str, Any]) -> None:
    validate_review_record(record)


def _replay(
    workspace: Path,
) -> tuple[
    dict[str, dict[str, Any]],
    str,
    list[dict[str, Any]],
    dict[str, tuple[str, str]],
]:
    records = read_jsonl(workspace, REVIEWS_PATH)
    validate_review_sequence(records)
    Card, Rating, Scheduler = _load_fsrs()
    cards: dict[str, dict[str, Any]] = {}
    item_bindings: dict[str, tuple[str, str]] = {}
    status = "enabled"
    seen: set[str] = set()
    previous_timestamp: datetime | None = None
    for record in records:
        _validate_review_record(record)
        record_timestamp = _as_datetime(str(record["timestamp"]))
        if previous_timestamp is not None and record_timestamp < previous_timestamp:
            raise ValidationError("review timestamps must be monotonic")
        previous_timestamp = record_timestamp
        event_id = str(record["event_id"])
        if event_id in seen:
            raise ValidationError(f"duplicate review event_id: {event_id}")
        seen.add(event_id)
        event_type = record["event_type"]
        if event_type == "review":
            item_id = str(record["item_id"])
            binding = (str(record["concept_id"]), str(record["dimension"]))
            existing_binding = item_bindings.get(item_id)
            if existing_binding is not None:
                if existing_binding[0] != binding[0]:
                    raise ValidationError(
                        f"review item_id {item_id!r} cannot be reused across concepts"
                    )
                if existing_binding[1] != binding[1]:
                    raise ValidationError(
                        f"review item_id {item_id!r} must preserve its dimension"
                    )
            item_bindings[item_id] = binding
            if item_id in cards:
                try:
                    prior_card = Card.from_dict(cards[item_id])
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValidationError(
                        f"stored FSRS card is invalid for item: {item_id}"
                    ) from exc
            else:
                prior_card = Card(card_id=_card_id(item_id), due=record_timestamp)
            config = record["scheduler_config"]
            scheduler = Scheduler(
                desired_retention=config["desired_retention"],
                enable_fuzzing=False,
                maximum_interval=config["maximum_interval"],
            )
            expected_card, expected_log = scheduler.review_card(
                prior_card,
                getattr(Rating, str(record["rating"])),
                review_datetime=record_timestamp,
            )
            expected_card_output = expected_card.to_dict()
            expected_card_output["due"] = normalize_timestamp(
                expected_card_output["due"]
            )
            expected_card_output["last_review"] = normalize_timestamp(
                expected_card_output["last_review"]
            )
            expected_log_output = expected_log.to_dict()
            expected_log_output["review_datetime"] = normalize_timestamp(
                expected_log_output["review_datetime"]
            )
            if (
                expected_card_output != record["output"]["card"]
                or expected_log_output != record["output"]["review_log"]
            ):
                raise ValidationError(
                    f"stored FSRS transition does not replay for item: {item_id}"
                )
            cards[item_id] = dict(record["output"]["card"])
        elif event_type in {"snooze", "reschedule"}:
            item_id = str(record["item_id"])
            if item_id not in cards:
                raise ValidationError(
                    f"{event_type} references an item with no review history: {item_id}"
                )
            if _as_datetime(str(record["due"])) < _as_datetime(
                str(cards[item_id]["last_review"])
            ):
                raise ValidationError(
                    f"{event_type} due must not precede the item's last_review"
                )
            cards[item_id] = dict(cards[item_id])
            cards[item_id]["due"] = record["due"]
        elif event_type == "review_controls":
            status = str(record["status"])
    return cards, status, records, item_bindings


def _append(
    workspace: Path, records: list[dict[str, Any]], payload: dict[str, Any]
) -> dict[str, Any]:
    payload["event_id"] = _event_id(payload)
    _validate_review_record(payload)
    if records and _as_datetime(str(payload["timestamp"])) < _as_datetime(
        str(records[-1]["timestamp"])
    ):
        raise ValidationError("review timestamps must be monotonic")
    if any(record["event_id"] == payload["event_id"] for record in records):
        raise ValidationError("this exact scheduler event is already present")
    validate_review_sequence([*records, payload])
    append_jsonl(workspace, REVIEWS_PATH, payload)
    return payload


def review_item(
    path: str,
    *,
    observation_event_id: str,
) -> dict[str, Any]:
    """Atomically derive one transparent FSRS transition from an observation."""

    Card, Rating, Scheduler = _load_fsrs()
    observation_id = _require_identifier("observation event", observation_event_id)

    workspace = secure_workspace(path)
    with workspace_lock(workspace):
        learner = _validate_consent(workspace)
        events = load_events(workspace)
        observation = next(
            (
                event
                for event in events
                if event["event_id"] == observation_id
                and event["event_type"] == "observation"
            ),
            None,
        )
        if observation is None:
            raise ValidationError("validated observation event was not found")
        active_observation_ids = {
            str(event["event_id"]) for event in _active_observations(events)
        }
        if observation_id not in active_observation_ids:
            raise ValidationError("observation event is corrected or invalidated")
        evidence_input = observation_input_from_event(observation)
        item = str(evidence_input["item_id"])
        concept = str(evidence_input["concept_id"])
        dimension = str(evidence_input["dimension"])
        score = float(evidence_input["score"])
        hint_level = int(evidence_input["hint_level"])
        normalized_time = str(evidence_input["timestamp"])
        review_time = _as_datetime(normalized_time)
        rating_name, explanation = derive_rating(
            dimension=dimension, score=score, hint_level=hint_level
        )
        cards, review_status, records, item_bindings = _replay(workspace)
        if review_status != "enabled":
            raise ValidationError("reviews are disabled")
        if any(
            record["event_type"] == "review"
            and record["input"]["observation_event_id"] == observation_id
            for record in records
        ):
            raise ValidationError(
                "this observation event already produced an FSRS review"
            )
        if item in item_bindings:
            bound_concept, bound_dimension = item_bindings[item]
            if bound_concept != concept:
                raise ValidationError(
                    f"review item_id {item!r} cannot be reused across concepts"
                )
            if bound_dimension != dimension:
                raise ValidationError(
                    f"review item_id {item!r} must preserve its dimension"
                )
        if item in cards:
            try:
                card = Card.from_dict(cards[item])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValidationError(
                    f"stored FSRS card is invalid for item: {item}"
                ) from exc
        else:
            card = Card(card_id=_card_id(item), due=review_time)
        horizon_days = int(learner["goal"]["retention_horizon_days"])
        scheduler_config = _horizon_scheduler_config(horizon_days)
        scheduler = Scheduler(
            desired_retention=scheduler_config["desired_retention"],
            enable_fuzzing=False,
            maximum_interval=scheduler_config["maximum_interval"],
        )
        rating = getattr(Rating, rating_name)
        updated_card, review_log = scheduler.review_card(
            card, rating, review_datetime=review_time
        )
        card_output = updated_card.to_dict()
        card_output["due"] = normalize_timestamp(card_output["due"])
        card_output["last_review"] = normalize_timestamp(card_output["last_review"])
        log_output = review_log.to_dict()
        log_output["review_datetime"] = normalize_timestamp(
            log_output["review_datetime"]
        )
        payload: dict[str, Any] = {
            "algorithm": "fsrs",
            "algorithm_version": FSRS_VERSION,
            "concept_id": concept,
            "dimension": dimension,
            "event_type": "review",
            "explanation": explanation,
            "input": evidence_input,
            "item_id": item,
            "output": {"card": card_output, "review_log": log_output},
            "rating": rating_name,
            "reason": explanation,
            "scheduler_config": scheduler_config,
            "scheduler_event_version": SCHEDULER_EVENT_VERSION,
            "schema_version": SCHEMA_VERSION,
            "timestamp": normalized_time,
        }
        record = _append(workspace, records, payload)

    return {
        "algorithm": record["algorithm"],
        "algorithm_version": record["algorithm_version"],
        "card": record["output"]["card"],
        "event_id": record["event_id"],
        "explanation": record["explanation"],
        "item_id": item,
        "observation_event_id": observation_id,
        "rating": record["rating"],
        "review_log": record["output"]["review_log"],
        "scheduler_config": record["scheduler_config"],
        "status": "reviewed",
    }


def due_items(path: str, *, at: str) -> dict[str, Any]:
    """Return the replayed due queue at an explicit instant."""

    normalized_at = normalize_timestamp(at)
    instant = _as_datetime(normalized_at)
    workspace = secure_workspace(path)
    with workspace_lock(workspace):
        _validate_consent(workspace)
        cards, status, _, _ = _replay(workspace)
    items: list[dict[str, Any]] = []
    if status == "enabled":
        for item_id, card in cards.items():
            due = _as_datetime(str(card["due"]))
            if due <= instant:
                items.append(
                    {
                        "card": card,
                        "due": normalize_timestamp(str(card["due"])),
                        "item_id": item_id,
                    }
                )
        items.sort(key=lambda entry: (entry["due"], entry["item_id"]))
    return {"at": normalized_at, "items": items, "status": status}


def move_due_date(
    path: str,
    *,
    event_type: str,
    item_id: str,
    until: str,
    reason: str,
    timestamp: str,
) -> dict[str, Any]:
    if event_type not in {"snooze", "reschedule"}:
        raise ValidationError("scheduler due-date operation is invalid")
    item = _require_identifier("item", item_id)
    normalized_due = normalize_timestamp(until)
    normalized_time = normalize_timestamp(timestamp)
    rationale = _require_reason(reason)
    workspace = secure_workspace(path)
    with workspace_lock(workspace):
        _validate_consent(workspace)
        cards, _, records, _ = _replay(workspace)
        if item not in cards:
            raise ValidationError(f"no review history exists for item: {item}")
        if _as_datetime(normalized_due) < _as_datetime(str(cards[item]["last_review"])):
            raise ValidationError(
                f"{event_type} due must not precede the item's last_review"
            )
        payload: dict[str, Any] = {
            "due": normalized_due,
            "event_type": event_type,
            "item_id": item,
            "reason": rationale,
            "scheduler_event_version": SCHEDULER_EVENT_VERSION,
            "schema_version": SCHEMA_VERSION,
            "timestamp": normalized_time,
        }
        record = _append(workspace, records, payload)
    return {
        "due": record["due"],
        "event_id": record["event_id"],
        "item_id": item,
        "reason": rationale,
        "status": event_type + "d",
    }


def set_review_status(
    path: str, *, enabled: bool, reason: str, timestamp: str
) -> dict[str, Any]:
    normalized_time = normalize_timestamp(timestamp)
    rationale = _require_reason(reason)
    status = "enabled" if enabled else "disabled"
    workspace = secure_workspace(path)
    with workspace_lock(workspace):
        _validate_consent(workspace)
        _, current, records, _ = _replay(workspace)
        if current == status:
            raise ValidationError(f"reviews are already {status}")
        payload: dict[str, Any] = {
            "event_type": "review_controls",
            "reason": rationale,
            "scheduler_event_version": SCHEDULER_EVENT_VERSION,
            "schema_version": SCHEMA_VERSION,
            "status": status,
            "timestamp": normalized_time,
        }
        record = _append(workspace, records, payload)
    return {
        "event_id": record["event_id"],
        "reason": rationale,
        "status": status,
    }
