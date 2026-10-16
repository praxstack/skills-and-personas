"""Parity tests for the machine-readable evidence event variants."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from praxteach.errors import ValidationError
from praxteach.state import _event_id, validate_event
from validate_workspace import _schema_instance_errors

EVENT_SCHEMA = json.loads(
    (ROOT / "schemas" / "event.schema.json").read_text(encoding="utf-8")
)


def event_with_id(payload: dict[str, Any]) -> dict[str, Any]:
    event = dict(payload)
    event["event_id"] = _event_id(event)
    return event


def observation(*, with_misconception: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "agent_inference": {
            "certainty": 0.62,
            "summary": "The learner can identify the stale write.",
        },
        "attempt_number": 1,
        "concept_id": "lost-update",
        "confidence": {"provenance": "not_reported", "value": None},
        "content_id": "lesson:lost-update",
        "content_version": "sha256:" + "a" * 64,
        "dimension": "transfer",
        "event_type": "observation",
        "hint_level": 0,
        "item_id": "transfer-record-update",
        "item_version": "v1",
        "learner_authored": "I used the final balance as evidence.",
        "model_and_prompt_version": "prax-teach-v2-core-1.0.0",
        "objective_id": "objective:lost-update",
        "response": "The second write used a stale balance and overwrote the first.",
        "response_ref": None,
        "result": {"correct": True, "score": 0.9},
        "rubric": {
            "dimensions": {
                "application": None,
                "discrimination": None,
                "explanation": None,
                "recall": None,
                "recognition": None,
                "transfer": 0.9,
            },
            "score": 0.9,
        },
        "schema_version": "1",
        "session_id": "session-1",
        "source_provenance": [
            {"source_id": "fixture-source", "version_or_date": "2026-08-04"}
        ],
        "timestamp": "2026-08-05T10:00:00Z",
    }
    if with_misconception:
        payload.update(
            {
                "learner_reasoning": "The later stale write erased the first update.",
                "misconception_claim": "The first writer is always the lost update.",
                "misconception_learner_confirmed": False,
                "misconception_provenance": "tutor_inference",
            }
        )
    return event_with_id(payload)


def correction() -> dict[str, Any]:
    return event_with_id(
        {
            "corrected_event_id": "evt-" + "1" * 32,
            "event_type": "correction",
            "reason": "The learner corrected the earlier explanation.",
            "schema_version": "1",
            "timestamp": "2026-08-05T10:01:00Z",
        }
    )


def invalidation() -> dict[str, Any]:
    return event_with_id(
        {
            "event_type": "invalidation",
            "invalidated_event_ids": ["evt-" + "2" * 32],
            "reason": "The source content version was withdrawn.",
            "schema_version": "1",
            "timestamp": "2026-08-05T10:02:00Z",
        }
    )


def misconception_rejection() -> dict[str, Any]:
    return event_with_id(
        {
            "event_type": "misconception_rejection",
            "misconception_event_id": "evt-" + "3" * 32,
            "reason": "The learner rejected the inferred misconception.",
            "schema_version": "1",
            "timestamp": "2026-08-05T10:03:00Z",
        }
    )


def schema_errors(event: dict[str, Any]) -> list[str]:
    return _schema_instance_errors(event, EVENT_SCHEMA, EVENT_SCHEMA, "event")


class EventSchemaVariantTest(unittest.TestCase):
    def test_all_runtime_event_variants_remain_schema_valid(self) -> None:
        canonical_fixture = json.loads(
            (ROOT / "fixtures" / "schema-valid" / "events.jsonl")
            .read_text(encoding="utf-8")
            .strip()
        )
        variants = (
            canonical_fixture,
            observation(),
            observation(with_misconception=True),
            correction(),
            invalidation(),
            misconception_rejection(),
        )

        for event in variants:
            with self.subTest(event_type=event["event_type"], fields=sorted(event)):
                validate_event(event)
                self.assertEqual(schema_errors(event), [])

    def test_schema_rejects_cross_variant_fields_that_runtime_rejects(self) -> None:
        cases = (
            (correction(), "dimension", "application"),
            (observation(), "corrected_event_id", "evt-" + "4" * 32),
            (invalidation(), "misconception_event_id", "evt-" + "5" * 32),
            (
                misconception_rejection(),
                "invalidated_event_ids",
                ["evt-" + "6" * 32],
            ),
        )

        for valid_event, field, value in cases:
            contaminated = {**valid_event, field: value}
            with self.subTest(event_type=valid_event["event_type"], field=field):
                with self.assertRaisesRegex(ValidationError, "unsupported field"):
                    validate_event(contaminated)
                self.assertTrue(
                    schema_errors(contaminated),
                    msg=f"schema accepted {valid_event['event_type']} + {field}",
                )

    def test_observation_misconception_metadata_is_all_or_nothing(self) -> None:
        contaminated = {
            **observation(),
            "learner_reasoning": "Metadata without a misconception claim.",
        }

        with self.assertRaisesRegex(ValidationError, "unsupported field"):
            validate_event(contaminated)
        self.assertTrue(
            schema_errors(contaminated),
            msg="schema accepted orphaned observation misconception metadata",
        )

    def test_learner_reported_confidence_cannot_have_a_null_value(self) -> None:
        contaminated = observation()
        contaminated["confidence"] = {
            "provenance": "learner_reported",
            "value": None,
        }

        with self.assertRaisesRegex(ValidationError, "confidence"):
            validate_event(contaminated)
        self.assertTrue(
            schema_errors(contaminated),
            msg="schema accepted learner_reported provenance with a null value",
        )

    def test_schema_and_runtime_reject_correct_score_disagreement(self) -> None:
        contaminated = observation()
        contaminated["result"] = {"correct": False, "score": 0.9}
        contaminated["event_id"] = _event_id(
            {key: value for key, value in contaminated.items() if key != "event_id"}
        )

        with self.assertRaisesRegex(ValidationError, "score threshold"):
            validate_event(contaminated)
        self.assertTrue(
            schema_errors(contaminated),
            msg="schema accepted correct=false with score at the positive threshold",
        )

    def test_schema_and_runtime_reject_confirmed_tutor_inference(self) -> None:
        contaminated = observation(with_misconception=True)
        contaminated["misconception_learner_confirmed"] = True
        contaminated["event_id"] = _event_id(
            {key: value for key, value in contaminated.items() if key != "event_id"}
        )

        with self.assertRaisesRegex(ValidationError, "learner-confirmed"):
            validate_event(contaminated)
        self.assertTrue(
            schema_errors(contaminated),
            msg="schema accepted learner confirmation of a tutor inference",
        )

    def test_observation_preserves_resume_fidelity_fields_exactly(self) -> None:
        event = observation()
        validate_event(event)
        self.assertEqual(
            event["response"],
            "The second write used a stale balance and overwrote the first.",
        )
        self.assertEqual(event["rubric"]["dimensions"]["transfer"], 0.9)
        self.assertEqual(
            event["learner_authored"], "I used the final balance as evidence."
        )
        self.assertEqual(event["agent_inference"]["certainty"], 0.62)

    def test_observation_requires_exactly_one_response_storage_form(self) -> None:
        contaminated = observation()
        contaminated["response_ref"] = "artifacts/answer.txt"
        contaminated["event_id"] = _event_id(
            {key: value for key, value in contaminated.items() if key != "event_id"}
        )

        with self.assertRaisesRegex(ValidationError, "exactly one"):
            validate_event(contaminated)
        self.assertTrue(
            schema_errors(contaminated),
            msg="schema accepted simultaneous inline response and response_ref",
        )


if __name__ == "__main__":
    unittest.main()
