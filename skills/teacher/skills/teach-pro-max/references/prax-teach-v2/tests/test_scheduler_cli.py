#!/usr/bin/env python3
"""Black-box contract tests for the pinned FSRS review adapter."""

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


class SchedulerCliTest(unittest.TestCase):
    maxDiff = None

    def run_cli(
        self, *args: str, expected: int = 0, no_site: bool = False
    ) -> subprocess.CompletedProcess[str]:
        command = [str(PYTHON)]
        if no_site:
            command.append("-S")
        command.extend((str(CLI), *args))
        completed = subprocess.run(
            command,
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

    def init_workspace(self, workspace: Path, *, horizon_days: str = "30") -> None:
        self.run_cli(
            "init",
            str(workspace),
            "--learner-id",
            "learner-fsrs",
            "--goal",
            "Retain and transfer the target concepts",
            "--horizon-days",
            horizon_days,
            "--consent",
            "--timestamp",
            "2026-08-04T10:00:00Z",
        )
        self.run_cli(
            "source-add",
            str(workspace),
            "--source-id",
            "scheduler-source",
            "--title",
            "Scheduler test source",
            "--url",
            "https://example.invalid/scheduler-source",
            "--author-or-publisher",
            "Prax Teach test suite",
            "--source-type",
            "official-doc",
            "--retrieved-at",
            "2026-08-04",
            "--version-or-date",
            "v1",
            "--license-or-use-note",
            "Synthetic scheduler fixture.",
            "--supports",
            "scheduler-tests",
            "--limitations",
            "Not learner-outcome evidence.",
        )

    def review(
        self,
        workspace: Path,
        *,
        item: str,
        concept: str = "index-selection",
        dimension: str,
        score: str,
        hint: str,
        timestamp: str = "2026-08-04T12:00:00Z",
        expected: int = 0,
    ) -> dict[str, object]:
        observation_command = [
            str(PYTHON),
            str(CLI),
            "observe",
            str(workspace),
            "--response",
            f"Exact observed response for {item} at {timestamp}",
            "--session",
            "session-"
            + hashlib.sha256(
                f"{item}\0{timestamp}\0{score}\0{hint}".encode()
            ).hexdigest()[:16],
            "--item",
            item,
            "--concept",
            concept,
            "--dimension",
            dimension,
            "--score",
            score,
            "--hint-level",
            hint,
            "--item-version",
            "v1",
            "--content-id",
            "content:" + concept,
            "--content-version",
            "sha256:" + "a" * 64,
            "--objective-id",
            "objective:" + concept,
            "--model-and-prompt-version",
            "test-tutor:model:prompt-v1",
            "--source-id",
            "scheduler-source",
            "--source-version",
            "v1",
            "--timestamp",
            timestamp,
        ]
        observed = subprocess.run(
            observation_command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if observed.returncode != 0:
            self.assertEqual(
                observed.returncode,
                expected,
                msg=f"stdout:\n{observed.stdout}\nstderr:\n{observed.stderr}",
            )
            return {"stderr": observed.stderr}
        observation_event_id = str(json.loads(observed.stdout)["event_id"])
        projection_before_review = (workspace / "state" / "concepts.json").read_bytes()
        completed = self.run_cli(
            "review",
            str(workspace),
            "--observation-event",
            observation_event_id,
            expected=expected,
        )
        self.assertEqual(
            projection_before_review,
            (workspace / "state" / "concepts.json").read_bytes(),
        )
        return (
            json.loads(completed.stdout)
            if expected == 0
            else {"stderr": completed.stderr}
        )

    def test_rating_derivation_and_real_fsrs_golden_vectors(self) -> None:
        vectors = [
            (
                "again",
                "recall",
                "0.2",
                "0",
                "Again",
                "2026-08-04T12:01:00.000000Z",
                0.212,
                6.4133,
            ),
            (
                "hard",
                "application",
                "0.9",
                "3",
                "Hard",
                "2026-08-04T12:05:30.000000Z",
                1.2931,
                5.112170705601056,
            ),
            (
                "good",
                "explanation",
                "0.9",
                "0",
                "Good",
                "2026-08-04T12:10:00.000000Z",
                2.3065,
                2.118103970459016,
            ),
            (
                "easy",
                "transfer",
                "0.95",
                "0",
                "Easy",
                "2026-08-10T12:00:00.000000Z",
                8.2956,
                1.0,
            ),
        ]
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            for (
                item,
                dimension,
                score,
                hint,
                rating,
                due,
                stability,
                difficulty,
            ) in vectors:
                result = self.review(
                    workspace,
                    item=item,
                    dimension=dimension,
                    score=score,
                    hint=hint,
                )
                self.assertEqual(result["rating"], rating)
                self.assertEqual(result["card"]["due"], due)
                self.assertAlmostEqual(
                    result["card"]["stability"], stability, places=10
                )
                self.assertAlmostEqual(
                    result["card"]["difficulty"], difficulty, places=10
                )
                self.assertEqual(result["algorithm"], "fsrs")
                self.assertEqual(result["algorithm_version"], "6.3.1")
                self.assertEqual(result["scheduler_config"]["horizon_days"], 30)
                self.assertEqual(result["scheduler_config"]["desired_retention"], 0.92)
                self.assertIn("because", result["explanation"].lower())

            records = [
                json.loads(line)
                for line in (workspace / "state" / "reviews.jsonl")
                .read_text()
                .splitlines()
            ]
            self.assertEqual(len(records), 4)
            self.assertTrue(all(record["algorithm"] == "fsrs" for record in records))
            self.assertTrue(
                all(record["algorithm_version"] == "6.3.1" for record in records)
            )

    def test_rating_threshold_matches_the_mastery_score_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            cases = (
                ("below-old-boundary", "0.59", "Again"),
                ("at-old-boundary", "0.60", "Again"),
                ("below-success", "0.79", "Again"),
                ("at-success", "0.80", "Good"),
            )
            for item, score, expected_rating in cases:
                result = self.review(
                    workspace,
                    item=item,
                    dimension="recall",
                    score=score,
                    hint="0",
                )
                self.assertEqual(result["rating"], expected_rating)

    def test_replay_due_and_learner_controls_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            workspaces = [base / "one", base / "two"]
            review_logs: list[bytes] = []
            for workspace in workspaces:
                self.init_workspace(workspace)
                self.review(
                    workspace,
                    item="transfer-card",
                    dimension="transfer",
                    score="0.95",
                    hint="0",
                )
                review_logs.append((workspace / "state" / "reviews.jsonl").read_bytes())
            self.assertEqual(review_logs[0], review_logs[1])

            workspace = workspaces[0]
            not_due = json.loads(
                self.run_cli(
                    "due", str(workspace), "--at", "2026-08-05T12:00:00Z"
                ).stdout
            )
            self.assertEqual(not_due["items"], [])
            due = json.loads(
                self.run_cli(
                    "due", str(workspace), "--at", "2026-08-12T12:00:00Z"
                ).stdout
            )
            self.assertEqual(
                [item["item_id"] for item in due["items"]], ["transfer-card"]
            )

            snoozed = json.loads(
                self.run_cli(
                    "snooze",
                    str(workspace),
                    "--item",
                    "transfer-card",
                    "--until",
                    "2026-08-15T12:00:00Z",
                    "--reason",
                    "Learner requested a short pause",
                    "--timestamp",
                    "2026-08-04T12:05:00Z",
                ).stdout
            )
            self.assertEqual(snoozed["due"], "2026-08-15T12:00:00.000000Z")

            rescheduled = json.loads(
                self.run_cli(
                    "reschedule",
                    str(workspace),
                    "--item",
                    "transfer-card",
                    "--until",
                    "2026-08-20T09:00:00Z",
                    "--reason",
                    "Align with the learner horizon",
                    "--timestamp",
                    "2026-08-04T12:06:00Z",
                ).stdout
            )
            self.assertEqual(rescheduled["due"], "2026-08-20T09:00:00.000000Z")

            self.run_cli(
                "disable-reviews",
                str(workspace),
                "--reason",
                "Learner opted out",
                "--timestamp",
                "2026-08-04T12:07:00Z",
            )
            disabled = json.loads(
                self.run_cli(
                    "due", str(workspace), "--at", "2026-09-01T00:00:00Z"
                ).stdout
            )
            self.assertEqual(disabled["status"], "disabled")
            self.assertEqual(disabled["items"], [])
            self.run_cli(
                "enable-reviews",
                str(workspace),
                "--reason",
                "Learner opted back in",
                "--timestamp",
                "2026-08-04T12:08:00Z",
            )
            enabled = json.loads(
                self.run_cli(
                    "due", str(workspace), "--at", "2026-09-01T00:00:00Z"
                ).stdout
            )
            self.assertEqual(enabled["status"], "enabled")
            self.assertEqual(
                [item["item_id"] for item in enabled["items"]], ["transfer-card"]
            )

    def test_missing_fsrs_dependency_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            observed = self.run_cli(
                "observe",
                str(workspace),
                "--response",
                "This observed response requires the pinned dependency.",
                "--session",
                "session-missing-dependency",
                "--concept",
                "index-selection",
                "--dimension",
                "recall",
                "--score",
                "1",
                "--hint-level",
                "0",
                "--item",
                "missing-dependency",
                "--item-version",
                "v1",
                "--content-id",
                "content:index-selection",
                "--content-version",
                "sha256:" + "a" * 64,
                "--objective-id",
                "objective:index-selection",
                "--model-and-prompt-version",
                "test-tutor:model:prompt-v1",
                "--source-id",
                "scheduler-source",
                "--source-version",
                "v1",
                "--timestamp",
                "2026-08-04T12:00:00Z",
            )
            observation_event_id = json.loads(observed.stdout)["event_id"]
            completed = self.run_cli(
                "review",
                str(workspace),
                "--observation-event",
                str(observation_event_id),
                expected=2,
                no_site=True,
            )
            self.assertIn("fsrs", completed.stderr.lower())
            self.assertIn("required", completed.stderr.lower())
            self.assertEqual((workspace / "state" / "reviews.jsonl").read_bytes(), b"")

    def test_learner_horizon_changes_the_explicit_fsrs_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            short = base / "short"
            long = base / "long"
            self.init_workspace(short, horizon_days="7")
            self.init_workspace(long, horizon_days="365")
            short_result = self.review(
                short,
                item="horizon-card",
                dimension="transfer",
                score="0.95",
                hint="0",
            )
            long_result = self.review(
                long,
                item="horizon-card",
                dimension="transfer",
                score="0.95",
                hint="0",
            )
            self.assertEqual(
                short_result["scheduler_config"],
                {
                    "desired_retention": 0.95,
                    "enable_fuzzing": False,
                    "horizon_days": 7,
                    "horizon_policy_version": "1",
                    "maximum_interval": 7,
                },
            )
            self.assertEqual(long_result["scheduler_config"]["desired_retention"], 0.88)
            self.assertEqual(long_result["scheduler_config"]["maximum_interval"], 365)
            self.assertLess(short_result["card"]["due"], long_result["card"]["due"])

    def test_review_log_rejects_non_monotonic_timestamps_without_appending(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            self.review(
                workspace,
                item="first-card",
                dimension="recall",
                score="0.9",
                hint="0",
                timestamp="2026-08-04T12:00:00Z",
            )
            reviews = workspace / "state" / "reviews.jsonl"
            before = reviews.read_bytes()

            for item in ("first-card", "backdated-card"):
                with self.subTest(item=item):
                    failed = self.review(
                        workspace,
                        item=item,
                        dimension="recall",
                        score="0.9",
                        hint="0",
                        timestamp="2026-08-04T11:59:59Z",
                        expected=6,
                    )

                    self.assertIn("timestamp", str(failed["stderr"]).lower())
                    self.assertIn("monotonic", str(failed["stderr"]).lower())
                    self.assertEqual(before, reviews.read_bytes())

    def test_item_identity_keeps_one_concept_and_dimension(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            self.review(
                workspace,
                item="stable-card",
                concept="concept-a",
                dimension="recall",
                score="0.9",
                hint="0",
                timestamp="2026-08-04T12:00:00Z",
            )
            reviews = workspace / "state" / "reviews.jsonl"

            for concept, dimension, timestamp, expected_fragment in (
                ("concept-b", "recall", "2026-08-04T12:01:00Z", "concept"),
                ("concept-a", "application", "2026-08-04T12:02:00Z", "dimension"),
            ):
                before = reviews.read_bytes()
                failed = self.review(
                    workspace,
                    item="stable-card",
                    concept=concept,
                    dimension=dimension,
                    score="0.9",
                    hint="0",
                    timestamp=timestamp,
                    expected=6,
                )
                self.assertIn(expected_fragment, str(failed["stderr"]).lower())
                self.assertEqual(before, reviews.read_bytes())

            accepted = self.review(
                workspace,
                item="stable-card",
                concept="concept-a",
                dimension="recall",
                score="0.9",
                hint="0",
                timestamp="2026-08-04T12:03:00Z",
            )
            self.assertEqual(accepted["status"], "reviewed")

    def test_disabled_reviews_reject_review_without_changing_log(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            self.review(
                workspace,
                item="control-card",
                dimension="recall",
                score="0.9",
                hint="0",
                timestamp="2026-08-04T10:30:00Z",
            )
            self.run_cli(
                "disable-reviews",
                str(workspace),
                "--reason",
                "Learner paused scheduled practice",
                "--timestamp",
                "2026-08-04T11:00:00Z",
            )
            snoozed = json.loads(
                self.run_cli(
                    "snooze",
                    str(workspace),
                    "--item",
                    "control-card",
                    "--until",
                    "2026-08-05T11:30:00Z",
                    "--reason",
                    "Learner changed the due date while reviews were paused",
                    "--timestamp",
                    "2026-08-04T11:30:00Z",
                ).stdout
            )
            self.assertEqual(snoozed["status"], "snoozed")
            reviews = workspace / "state" / "reviews.jsonl"
            before = reviews.read_bytes()

            failed = self.review(
                workspace,
                item="paused-card",
                dimension="recall",
                score="0.9",
                hint="0",
                timestamp="2026-08-04T12:00:00Z",
                expected=6,
            )
            self.assertIn("disabled", str(failed["stderr"]).lower())
            self.assertEqual(before, reviews.read_bytes())

            self.run_cli(
                "enable-reviews",
                str(workspace),
                "--reason",
                "Learner resumed scheduled practice",
                "--timestamp",
                "2026-08-04T12:01:00Z",
            )
            accepted = self.review(
                workspace,
                item="paused-card",
                dimension="recall",
                score="0.9",
                hint="0",
                timestamp="2026-08-04T12:02:00Z",
            )
            self.assertEqual(accepted["status"], "reviewed")

    def test_due_date_controls_cannot_predate_the_items_last_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            self.review(
                workspace,
                item="dated-card",
                dimension="recall",
                score="0.9",
                hint="0",
                timestamp="2026-08-04T12:00:00Z",
            )
            reviews = workspace / "state" / "reviews.jsonl"
            before = reviews.read_bytes()

            failed = self.run_cli(
                "reschedule",
                str(workspace),
                "--item",
                "dated-card",
                "--until",
                "2026-08-04T11:59:59Z",
                "--reason",
                "This invalid date predates the last review",
                "--timestamp",
                "2026-08-04T12:01:00Z",
                expected=6,
            )
            self.assertIn("due", failed.stderr.lower())
            self.assertIn("last_review", failed.stderr.lower())
            self.assertEqual(before, reviews.read_bytes())

    def test_due_rejects_a_resealed_but_forged_fsrs_transition(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            self.review(
                workspace,
                item="forged-card",
                dimension="recall",
                score="0.9",
                hint="0",
            )
            reviews = workspace / "state" / "reviews.jsonl"
            record = json.loads(reviews.read_text(encoding="utf-8"))
            record["output"]["card"]["stability"] += 0.001
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
            reviews.write_text(
                json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n",
                encoding="utf-8",
            )

            failed = self.run_cli(
                "due",
                str(workspace),
                "--at",
                "2026-08-10T12:00:00Z",
                expected=6,
            )
            self.assertIn("transition", failed.stderr.lower())

    def test_due_rejects_a_resealed_score_rating_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            self.review(
                workspace,
                item="forged-score-card",
                dimension="recall",
                score="0.9",
                hint="0",
            )
            reviews = workspace / "state" / "reviews.jsonl"
            record = json.loads(reviews.read_text(encoding="utf-8"))
            record["input"]["score"] = 0.2
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
            reviews.write_text(
                json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n",
                encoding="utf-8",
            )

            failed = self.run_cli(
                "due",
                str(workspace),
                "--at",
                "2026-08-10T12:00:00Z",
                expected=6,
            )
            self.assertIn("derived", failed.stderr.lower())
            self.assertIn("performance input", failed.stderr.lower())

    def test_due_rejects_a_resealed_review_record_while_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            self.review(
                workspace,
                item="disabled-history-card",
                dimension="recall",
                score="0.9",
                hint="0",
                timestamp="2026-08-04T10:30:00Z",
            )
            self.run_cli(
                "disable-reviews",
                str(workspace),
                "--reason",
                "Learner paused review scheduling",
                "--timestamp",
                "2026-08-04T11:00:00Z",
            )
            reviews = workspace / "state" / "reviews.jsonl"
            records = [
                json.loads(line)
                for line in reviews.read_text(encoding="utf-8").splitlines()
            ]
            forged = json.loads(json.dumps(records[0]))
            forged["timestamp"] = "2026-08-04T12:00:00Z"
            forged["input"]["timestamp"] = forged["timestamp"]
            forged["output"]["card"]["last_review"] = "2026-08-04T12:00:00.000000Z"
            forged["output"]["card"]["due"] = "2026-08-10T12:00:00.000000Z"
            forged["output"]["review_log"]["review_datetime"] = (
                "2026-08-04T12:00:00.000000Z"
            )
            payload = dict(forged)
            payload.pop("event_id")
            encoded = json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
                allow_nan=False,
            ).encode("utf-8")
            forged["event_id"] = "review-" + hashlib.sha256(encoded).hexdigest()[:32]
            reviews.write_text(
                "".join(
                    json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n"
                    for record in [*records, forged]
                ),
                encoding="utf-8",
            )

            failed = self.run_cli(
                "due",
                str(workspace),
                "--at",
                "2026-08-10T12:00:00Z",
                expected=6,
            )
            self.assertIn("disabled", failed.stderr.lower())


if __name__ == "__main__":
    unittest.main()
