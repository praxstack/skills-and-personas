"""Regression tests for chronological state and evidence-bound scheduling."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "bin" / "python"
CLI = ROOT / "scripts" / "prax_teach.py"


class StateSchedulerCausalityTest(unittest.TestCase):
    maxDiff = None

    def run_cli(
        self, *args: str, expected: int = 0
    ) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            [str(PYTHON), str(CLI), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            expected,
            msg=f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )
        return completed

    def initialize(self, workspace: Path) -> None:
        self.run_cli(
            "init",
            str(workspace),
            "--learner-id",
            "causality-learner",
            "--goal",
            "Apply the target concept independently",
            "--consent",
            "--timestamp",
            "2026-08-04T00:00:00Z",
        )
        self.run_cli(
            "source-add",
            str(workspace),
            "--source-id",
            "causal-source",
            "--title",
            "Causal scheduling fixture",
            "--url",
            "https://example.invalid/causal-source",
            "--author-or-publisher",
            "Prax Teach test suite",
            "--source-type",
            "official-doc",
            "--retrieved-at",
            "2026-08-04",
            "--version-or-date",
            "v3",
            "--license-or-use-note",
            "Synthetic fixture only.",
            "--supports",
            "objective:causal-transfer",
            "--limitations",
            "Not human-learning evidence.",
        )

    def observe(
        self,
        workspace: Path,
        *,
        item: str = "causal-item",
        session: str = "causal-session",
        timestamp: str = "2026-08-04T12:00:00Z",
        misconception: bool = False,
    ) -> dict[str, object]:
        command = [
            "observe",
            str(workspace),
            "--response",
            f"Exact response for {item}",
            "--session",
            session,
            "--concept",
            "causal-concept",
            "--dimension",
            "application",
            "--score",
            "0.9",
            "--hint-level",
            "0",
            "--item",
            item,
            "--item-version",
            "item-v3",
            "--content-id",
            "lesson:causal-content",
            "--content-version",
            "sha256:" + "c" * 64,
            "--objective-id",
            "objective:causal-transfer",
            "--model-and-prompt-version",
            "tutor:prax-teach-v2@2.1.0;model:gpt-5;prompt:sha256:" + "d" * 64,
            "--source-id",
            "causal-source",
            "--source-version",
            "v3",
            "--timestamp",
            timestamp,
        ]
        if misconception:
            command.extend(
                (
                    "--misconception-claim",
                    "A later wall-clock spelling is always a later instant",
                    "--learner-reasoning",
                    "I compared the timestamp strings directly.",
                    "--misconception-provenance",
                    "learner_reported",
                    "--confirm-misconception",
                )
            )
        return json.loads(self.run_cli(*command).stdout)

    def review(self, workspace: Path, event_id: str) -> dict[str, object]:
        return json.loads(
            self.run_cli(
                "review",
                str(workspace),
                "--observation-event",
                event_id,
            ).stdout
        )

    def test_explicit_observation_identity_and_versions_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.initialize(workspace)
            observed = self.observe(workspace)

            event = json.loads(
                (workspace / "state" / "sessions.jsonl").read_text(encoding="utf-8")
            )
            self.assertEqual(event["event_id"], observed["event_id"])
            self.assertEqual(event["content_id"], "lesson:causal-content")
            self.assertEqual(event["objective_id"], "objective:causal-transfer")
            self.assertEqual(
                event["model_and_prompt_version"],
                "tutor:prax-teach-v2@2.1.0;model:gpt-5;prompt:sha256:" + "d" * 64,
            )

    def test_projection_uses_instant_order_and_fixed_width_utc(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.initialize(workspace)
            earlier = self.observe(
                workspace,
                item="offset-earlier",
                timestamp="2026-08-04T11:30:00+05:30",
                misconception=True,
            )
            later = self.observe(
                workspace,
                item="fraction-later",
                timestamp="2026-08-04T06:00:00.1Z",
                misconception=True,
            )
            concept = json.loads(
                (workspace / "state" / "concepts.json").read_text(encoding="utf-8")
            )["concepts"][0]
            misconception = json.loads(
                (workspace / "state" / "misconceptions.json").read_text(
                    encoding="utf-8"
                )
            )["misconceptions"][0]
            self.assertEqual(
                concept["dimensions"]["application"]["evidence_ids"],
                [earlier["event_id"], later["event_id"]],
            )
            self.assertEqual(concept["last_updated"], "2026-08-04T06:00:00.100000Z")
            self.assertEqual(
                misconception["last_tested"], "2026-08-04T06:00:00.100000Z"
            )

    def test_review_is_derived_from_one_validated_observation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.initialize(workspace)
            observed = self.observe(workspace)
            result = self.review(workspace, str(observed["event_id"]))

            record = json.loads(
                (workspace / "state" / "reviews.jsonl").read_text(encoding="utf-8")
            )
            evidence = record["input"]
            self.assertEqual(result["observation_event_id"], observed["event_id"])
            self.assertEqual(evidence["observation_event_id"], observed["event_id"])
            self.assertEqual(evidence["session_id"], "causal-session")
            self.assertEqual(evidence["content_id"], "lesson:causal-content")
            self.assertEqual(evidence["content_version"], "sha256:" + "c" * 64)
            self.assertEqual(evidence["objective_id"], "objective:causal-transfer")
            self.assertEqual(evidence["item_version"], "item-v3")
            self.assertEqual(
                evidence["source_provenance"],
                [{"source_id": "causal-source", "version_or_date": "v3"}],
            )
            self.assertEqual(record["scheduler_event_version"], "2")

            duplicate = self.run_cli(
                "review",
                str(workspace),
                "--observation-event",
                str(observed["event_id"]),
                expected=6,
            )
            self.assertIn("already produced", duplicate.stderr.lower())

            before = (workspace / "state" / "reviews.jsonl").read_bytes()
            missing = self.run_cli(
                "review",
                str(workspace),
                "--observation-event",
                "evt-" + "0" * 32,
                expected=6,
            )
            self.assertIn("observation", missing.stderr.lower())
            self.assertEqual(
                before, (workspace / "state" / "reviews.jsonl").read_bytes()
            )

            record["input"]["session_id"] = "forged-session"
            payload = dict(record)
            payload.pop("event_id")
            encoded = json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
                allow_nan=False,
            ).encode("utf-8")
            record["event_id"] = "review-" + hashlib.sha256(encoded).hexdigest()[:32]
            (workspace / "state" / "reviews.jsonl").write_text(
                json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n",
                encoding="utf-8",
            )
            forged = self.run_cli(
                "due",
                str(workspace),
                "--at",
                "2026-08-20T00:00:00Z",
                expected=6,
            )
            self.assertIn("validated observation", forged.stderr.lower())

    def test_inactive_observation_cannot_be_scheduled(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.initialize(workspace)
            observed = self.observe(workspace)
            self.run_cli(
                "correct",
                str(workspace),
                "--event-id",
                str(observed["event_id"]),
                "--reason",
                "The learner corrected this response before scheduling.",
                "--timestamp",
                "2026-08-04T12:01:00Z",
            )
            failed = self.run_cli(
                "review",
                str(workspace),
                "--observation-event",
                str(observed["event_id"]),
                expected=6,
            )
            self.assertIn("corrected or invalidated", failed.stderr.lower())
            self.assertEqual((workspace / "state" / "reviews.jsonl").read_bytes(), b"")

    def test_correction_removes_later_same_item_review_and_due_controls(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.initialize(workspace)
            first = self.observe(
                workspace,
                timestamp="2026-08-04T12:00:00Z",
            )
            self.review(workspace, str(first["event_id"]))
            self.run_cli(
                "snooze",
                str(workspace),
                "--item",
                "causal-item",
                "--until",
                "2026-08-12T00:00:00Z",
                "--reason",
                "Learner requested a pause.",
                "--timestamp",
                "2026-08-04T12:00:30Z",
            )
            second = self.observe(
                workspace,
                timestamp="2026-08-04T12:01:00Z",
                session="causal-session-2",
            )
            self.review(workspace, str(second["event_id"]))

            corrected = json.loads(
                self.run_cli(
                    "correct",
                    str(workspace),
                    "--event-id",
                    str(first["event_id"]),
                    "--reason",
                    "The first observed performance was entered incorrectly.",
                    "--timestamp",
                    "2026-08-04T12:02:00Z",
                ).stdout
            )
            self.assertEqual(corrected["review_events_removed"], 3)
            self.assertEqual((workspace / "state" / "reviews.jsonl").read_bytes(), b"")

    def test_correction_invalidation_and_session_deletion_scrub_reviews(self) -> None:
        operations = ("correct", "invalidate", "delete-session")
        for operation in operations:
            with (
                self.subTest(operation=operation),
                tempfile.TemporaryDirectory() as temp,
            ):
                workspace = Path(temp) / "course"
                self.initialize(workspace)
                observed = self.observe(workspace)
                self.review(workspace, str(observed["event_id"]))

                if operation == "correct":
                    changed = self.run_cli(
                        "correct",
                        str(workspace),
                        "--event-id",
                        str(observed["event_id"]),
                        "--reason",
                        "The learner corrected this evidence.",
                        "--timestamp",
                        "2026-08-04T12:01:00Z",
                    )
                elif operation == "invalidate":
                    changed = self.run_cli(
                        "invalidate",
                        str(workspace),
                        "--event-id",
                        str(observed["event_id"]),
                        "--reason",
                        "This item version is no longer valid.",
                        "--timestamp",
                        "2026-08-04T12:01:00Z",
                    )
                else:
                    changed = self.run_cli(
                        "delete",
                        str(workspace),
                        "--session",
                        "causal-session",
                        "--confirm",
                    )
                receipt = json.loads(changed.stdout)
                self.assertEqual(receipt["review_events_removed"], 1)
                self.assertEqual(
                    (workspace / "state" / "reviews.jsonl").read_bytes(), b""
                )
                first = self.run_cli("rebuild", str(workspace)).stdout
                first_bytes = (workspace / "state" / "concepts.json").read_bytes()
                second = self.run_cli("rebuild", str(workspace)).stdout
                self.assertEqual(first, second)
                self.assertEqual(
                    first_bytes, (workspace / "state" / "concepts.json").read_bytes()
                )


if __name__ == "__main__":
    unittest.main()
