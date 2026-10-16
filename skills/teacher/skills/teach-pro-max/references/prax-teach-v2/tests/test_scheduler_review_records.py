"""Focused semantic and JSON-Schema checks for scheduler review records."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from praxteach.errors import ValidationError
from praxteach.review_records import (
    review_event_id,
    validate_review_record,
    validate_review_sequence,
)
from validate_workspace import _schema_instance_errors


class SchedulerReviewRecordTest(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        fixture = ROOT / "fixtures" / "schema-valid" / "reviews.jsonl"
        cls.valid_review = json.loads(fixture.read_text(encoding="utf-8"))
        cls.schema = json.loads(
            (ROOT / "schemas" / "reviews.schema.json").read_text(encoding="utf-8")
        )

    def reseal(self, record: dict[str, Any]) -> dict[str, Any]:
        payload = copy.deepcopy(record)
        payload.pop("event_id", None)
        payload["event_id"] = review_event_id(payload)
        return payload

    def mutated(self, mutator: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        record = copy.deepcopy(self.valid_review)
        mutator(record)
        return self.reseal(record)

    def schema_errors(self, value: dict[str, Any]) -> list[str]:
        return _schema_instance_errors(value, self.schema, self.schema, "instance")

    def assert_runtime_rejects(
        self, mutator: Callable[[dict[str, Any]], None], fragment: str
    ) -> None:
        with self.assertRaisesRegex(ValidationError, fragment):
            validate_review_record(self.mutated(mutator))

    def assert_schema_rejects(self, mutator: Callable[[dict[str, Any]], None]) -> None:
        record = self.mutated(mutator)
        self.assertTrue(
            self.schema_errors(record),
            msg=f"schema unexpectedly accepted:\n{json.dumps(record, indent=2)}",
        )

    def test_review_card_requires_fsrs_valid_numeric_ranges(self) -> None:
        cases = (
            (
                lambda value: value["output"]["card"].__setitem__("stability", 0),
                "stability",
            ),
            (
                lambda value: value["output"]["card"].__setitem__("stability", -0.01),
                "stability",
            ),
            (
                lambda value: value["output"]["card"].__setitem__("difficulty", 0.99),
                "difficulty",
            ),
            (
                lambda value: value["output"]["card"].__setitem__("difficulty", 10.01),
                "difficulty",
            ),
            (lambda value: value["output"]["card"].__setitem__("step", -1), "step"),
            (
                lambda value: value["output"]["card"].__setitem__("step", "0"),
                "step",
            ),
        )
        for mutator, fragment in cases:
            with self.subTest(fragment=fragment, mutator=mutator):
                self.assert_runtime_rejects(mutator, fragment)
                self.assert_schema_rejects(mutator)

    def test_review_rating_and_explanation_are_derived_from_stored_input(self) -> None:
        self.assert_runtime_rejects(
            lambda value: value["input"].__setitem__("score", 0.79),
            "derived rating|performance input",
        )

        def replace_explanation(value: dict[str, Any]) -> None:
            value["explanation"] = "Easy was selected for an unrelated reason."
            value["reason"] = value["explanation"]

        self.assert_runtime_rejects(
            replace_explanation,
            "derived explanation|performance input",
        )

    def test_review_input_requires_complete_observation_causality(self) -> None:
        causal_fields = (
            "content_id",
            "content_version",
            "item_version",
            "model_and_prompt_version",
            "objective_id",
            "observation_event_id",
            "session_id",
            "source_provenance",
        )
        for field in causal_fields:
            with self.subTest(field=field):
                self.assert_runtime_rejects(
                    lambda value, field=field: value["input"].pop(field),
                    "missing required field",
                )
                self.assert_schema_rejects(
                    lambda value, field=field: value["input"].pop(field)
                )

    def test_scheduler_event_v1_is_rejected_without_fabricated_migration(self) -> None:
        self.assert_runtime_rejects(
            lambda value: value.__setitem__("scheduler_event_version", "1"),
            "scheduler_event_version",
        )
        self.assert_schema_rejects(
            lambda value: value.__setitem__("scheduler_event_version", "1")
        )

    def test_review_sequence_rejects_reviews_while_scheduling_is_disabled(
        self,
    ) -> None:
        disabled = self.reseal(
            {
                "event_type": "review_controls",
                "reason": "Learner paused review scheduling",
                "scheduler_event_version": "2",
                "schema_version": "1",
                "status": "disabled",
                "timestamp": "2026-08-04T12:01:00Z",
            }
        )
        review = self.mutated(
            lambda value: (
                value.__setitem__("timestamp", "2026-08-04T12:02:00Z"),
                value["input"].__setitem__("timestamp", "2026-08-04T12:02:00Z"),
                value["output"]["card"].__setitem__(
                    "last_review", "2026-08-04T12:02:00+00:00"
                ),
                value["output"]["review_log"].__setitem__(
                    "review_datetime", "2026-08-04T12:02:00+00:00"
                ),
            )
        )

        with self.assertRaisesRegex(ValidationError, "disabled"):
            validate_review_sequence([self.valid_review, disabled, review])

    def test_review_control_sequence_requires_actual_status_transitions(self) -> None:
        disabled = self.reseal(
            {
                "event_type": "review_controls",
                "reason": "Learner paused review scheduling",
                "scheduler_event_version": "2",
                "schema_version": "1",
                "status": "disabled",
                "timestamp": "2026-08-04T12:01:00Z",
            }
        )
        disabled_again = self.reseal(
            {
                **{key: value for key, value in disabled.items() if key != "event_id"},
                "reason": "A duplicate pause must not be accepted",
                "timestamp": "2026-08-04T12:02:00Z",
            }
        )
        with self.assertRaisesRegex(ValidationError, "already disabled"):
            validate_review_sequence([self.valid_review, disabled, disabled_again])

        enabled = self.reseal(
            {
                "event_type": "review_controls",
                "reason": "Learner resumed review scheduling",
                "scheduler_event_version": "2",
                "schema_version": "1",
                "status": "enabled",
                "timestamp": "2026-08-04T12:02:00Z",
            }
        )
        validate_review_sequence([self.valid_review, disabled, enabled])

    def test_review_due_must_not_precede_last_review(self) -> None:
        def make_due_earlier(value: dict[str, Any]) -> None:
            value["output"]["card"]["due"] = "2026-08-04T10:59:59Z"

        self.assert_runtime_rejects(make_due_earlier, "due")

    def test_all_review_timestamps_must_be_the_same_normalized_instant(self) -> None:
        equivalent = self.mutated(
            lambda value: value["input"].__setitem__(
                "timestamp", "2026-08-04T16:30:00+05:30"
            )
        )
        validate_review_record(equivalent)

        timestamp_paths = (
            (
                "input",
                lambda value: value["input"].__setitem__(
                    "timestamp", "2026-08-04T12:00:01Z"
                ),
            ),
            (
                "last_review",
                lambda value: value["output"]["card"].__setitem__(
                    "last_review", "2026-08-04T12:00:01Z"
                ),
            ),
            (
                "review_datetime",
                lambda value: value["output"]["review_log"].__setitem__(
                    "review_datetime", "2026-08-04T12:00:01Z"
                ),
            ),
        )
        for label, mutator in timestamp_paths:
            with self.subTest(label=label):
                self.assert_runtime_rejects(
                    mutator, "timestamp|last_review|review_datetime"
                )

    def test_review_schema_variants_are_exact(self) -> None:
        common = {
            "event_id": "review-" + "0" * 32,
            "scheduler_event_version": "2",
            "schema_version": "1",
            "timestamp": "2026-08-04T12:00:00Z",
        }
        variants = (
            {
                **common,
                "event_type": "snooze",
                "due": "2026-08-05T12:00:00Z",
                "item_id": "item-1",
                "reason": "Learner requested a pause",
            },
            {
                **common,
                "event_type": "reschedule",
                "due": "2026-08-05T12:00:00Z",
                "item_id": "item-1",
                "reason": "Learner requested a new date",
            },
            {
                **common,
                "event_type": "review_controls",
                "reason": "Learner paused review scheduling",
                "status": "disabled",
            },
        )
        known_variant_fields = {
            **self.valid_review,
            "due": "2026-08-05T12:00:00Z",
            "status": "disabled",
        }
        for variant in variants:
            self.assertEqual(self.schema_errors(variant), [])
            disallowed = set(known_variant_fields) - set(variant)
            for field in sorted(disallowed):
                with self.subTest(event_type=variant["event_type"], field=field):
                    contaminated = copy.deepcopy(variant)
                    contaminated[field] = copy.deepcopy(known_variant_fields[field])
                    self.assertTrue(self.schema_errors(contaminated))


if __name__ == "__main__":
    unittest.main()
