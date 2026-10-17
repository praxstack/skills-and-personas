#!/usr/bin/env python3
"""Black-box tests for the Prax Teach learner-state CLI."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "prax_teach.py"
ROUTING_FIXTURES = ROOT / "fixtures" / "routing-cases.json"


class CliTestCase(unittest.TestCase):
    def run_cli(
        self, *args: str, expected: int = 0
    ) -> subprocess.CompletedProcess[str]:
        arguments = list(args)
        if arguments and arguments[0] == "observe":
            concept = arguments[arguments.index("--concept") + 1]
            for flag, value in (
                ("--content-id", concept),
                ("--objective-id", "objective:" + concept),
                ("--model-and-prompt-version", "test-tutor:model:prompt-v1"),
            ):
                if flag not in arguments:
                    arguments.extend((flag, value))
        completed = subprocess.run(
            [sys.executable, str(CLI), *arguments],
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

    def init_workspace(self, workspace: Path) -> dict[str, object]:
        completed = self.run_cli(
            "init",
            str(workspace),
            "--learner-id",
            "learner-local-1",
            "--goal",
            "Apply index-selection principles to unseen workloads",
            "--horizon-days",
            "30",
            "--consent",
            "--timestamp",
            "2026-08-04T10:00:00Z",
        )
        self.run_cli(
            "source-add",
            str(workspace),
            "--source-id",
            "postgres-index-docs",
            "--title",
            "PostgreSQL index documentation",
            "--url",
            "https://www.postgresql.org/docs/current/indexes.html",
            "--author-or-publisher",
            "PostgreSQL Global Development Group",
            "--source-type",
            "official-doc",
            "--retrieved-at",
            "2026-08-04",
            "--version-or-date",
            "2026-08-04",
            "--license-or-use-note",
            "Used as official documentation under its published terms.",
            "--supports",
            "composite-index-prefix",
            "--limitations",
            "Version-specific database behavior still requires verification.",
        )
        return json.loads(completed.stdout)

    def observe(
        self,
        workspace: Path,
        *,
        session: str,
        dimension: str,
        score: str = "0.9",
        hint: str = "0",
        item: str,
        timestamp: str,
    ) -> dict[str, object]:
        completed = self.run_cli(
            "observe",
            str(workspace),
            "--response",
            f"Learner response for {item}",
            "--session",
            session,
            "--concept",
            "composite-index-prefix",
            "--dimension",
            dimension,
            "--score",
            score,
            "--hint-level",
            hint,
            "--item",
            item,
            "--item-version",
            "v1",
            "--content-version",
            "sha256:" + "a" * 64,
            "--source-id",
            "postgres-index-docs",
            "--source-version",
            "2026-08-04",
            "--timestamp",
            timestamp,
        )
        return json.loads(completed.stdout)


class TestConsentAndState(CliTestCase):
    def test_init_without_consent_creates_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            completed = self.run_cli(
                "init",
                str(workspace),
                "--learner-id",
                "learner-local-1",
                "--goal",
                "Learn safely",
                expected=3,
            )
            self.assertIn("explicit consent", completed.stderr.lower())
            self.assertFalse(workspace.exists())

    def test_init_creates_minimal_private_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            result = self.init_workspace(workspace)
            self.assertEqual(result["status"], "initialized")
            expected = {
                "MISSION.md",
                "RESOURCES.md",
                "state/learner.json",
                "state/sessions.jsonl",
                "state/concepts.json",
                "state/misconceptions.json",
                "state/reviews.jsonl",
                "state/sources.json",
            }
            actual = {
                path.relative_to(workspace).as_posix()
                for path in workspace.rglob("*")
                if path.is_file() and path.name != ".prax-teach.lock"
            }
            self.assertTrue(expected.issubset(actual))
            learner = json.loads((workspace / "state" / "learner.json").read_text())
            self.assertTrue(learner["consent"]["persistent_state"])
            self.assertEqual(
                learner["consent"]["scope"],
                [
                    "goal",
                    "practice_evidence",
                    "reviews",
                ],
            )
            self.assertEqual(os.stat(workspace).st_mode & 0o777, 0o700)
            for directory in ("assets", "lessons", "reference", "state"):
                self.assertTrue((workspace / directory).is_dir())
                self.assertEqual(
                    os.stat(workspace / directory).st_mode & 0o777,
                    0o700,
                )
            self.assertEqual(
                os.stat(workspace / "state" / "learner.json").st_mode & 0o777, 0o600
            )

    def test_rebuild_is_deterministic_and_durable_requires_later_session(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)

            first = self.observe(
                workspace,
                session="session-1",
                dimension="explanation",
                item="explain-1",
                timestamp="2026-08-04T10:05:00Z",
            )
            self.assertEqual(first["concept_status"], "emerging")

            second = self.observe(
                workspace,
                session="session-1",
                dimension="transfer",
                item="transfer-1",
                timestamp="2026-08-04T10:10:00Z",
            )
            self.assertEqual(second["concept_status"], "provisional")
            self.assertNotEqual(second["concept_status"], "durable")

            third = self.observe(
                workspace,
                session="session-2",
                dimension="recall",
                item="recall-2",
                timestamp="2026-08-11T10:00:00Z",
            )
            self.assertEqual(third["concept_status"], "durable")

            concepts_path = workspace / "state" / "concepts.json"
            before = concepts_path.read_bytes()
            self.run_cli("rebuild", str(workspace))
            middle = concepts_path.read_bytes()
            self.run_cli("rebuild", str(workspace))
            after = concepts_path.read_bytes()
            self.assertEqual(before, middle)
            self.assertEqual(middle, after)

            projection = json.loads(after)
            concept = projection["concepts"][0]
            self.assertEqual(concept["status"], "durable")
            self.assertEqual(
                set(concept["dimensions"]),
                {
                    "recognition",
                    "recall",
                    "explanation",
                    "application",
                    "discrimination",
                    "transfer",
                },
            )
            self.assertEqual(len(concept["evidence_ids"]), 3)

    def test_heavily_hinted_correct_answer_is_not_mastery(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            for index, dimension in enumerate(("application", "transfer"), start=1):
                result = self.observe(
                    workspace,
                    session=f"session-{index}",
                    dimension=dimension,
                    hint="4",
                    item=f"hinted-{index}",
                    timestamp=f"2026-08-0{index + 4}T10:00:00Z",
                )
            self.assertIn(result["concept_status"], {"emerging", "developing"})

    def test_misconception_provenance_defaults_unconfirmed_and_can_be_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            missing_provenance = self.run_cli(
                "observe",
                str(workspace),
                "--response",
                "I assumed every column order was equivalent.",
                "--session",
                "session-1",
                "--concept",
                "composite-index-prefix",
                "--dimension",
                "explanation",
                "--score",
                "0.4",
                "--hint-level",
                "0",
                "--item",
                "misconception-1",
                "--item-version",
                "v1",
                "--content-version",
                "sha256:" + "a" * 64,
                "--source-id",
                "postgres-index-docs",
                "--source-version",
                "2026-08-04",
                "--misconception-claim",
                "Column order never matters",
                "--learner-reasoning",
                "I used the same columns, so I assumed every order was equivalent",
                "--timestamp",
                "2026-08-04T10:05:00Z",
                expected=6,
            )
            self.assertIn("provenance", missing_provenance.stderr.lower())

            observed = json.loads(
                self.run_cli(
                    "observe",
                    str(workspace),
                    "--response",
                    "I assumed every column order was equivalent.",
                    "--session",
                    "session-1",
                    "--concept",
                    "composite-index-prefix",
                    "--dimension",
                    "explanation",
                    "--score",
                    "0.4",
                    "--hint-level",
                    "0",
                    "--item",
                    "misconception-1",
                    "--item-version",
                    "v1",
                    "--content-version",
                    "sha256:" + "a" * 64,
                    "--source-id",
                    "postgres-index-docs",
                    "--source-version",
                    "2026-08-04",
                    "--misconception-claim",
                    "Column order never matters",
                    "--learner-reasoning",
                    "I used the same columns, so I assumed every order was equivalent",
                    "--misconception-provenance",
                    "tutor_inference",
                    "--timestamp",
                    "2026-08-04T10:05:00Z",
                ).stdout
            )
            projected = json.loads(
                (workspace / "state" / "misconceptions.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertFalse(projected["misconceptions"][0]["learner_confirmed"])
            self.assertEqual(
                projected["misconceptions"][0]["provenance"], ["tutor_inference"]
            )

            rejected = json.loads(
                self.run_cli(
                    "reject-misconception",
                    str(workspace),
                    "--event-id",
                    str(observed["event_id"]),
                    "--reason",
                    "That is not what I believe",
                    "--timestamp",
                    "2026-08-04T10:06:00Z",
                ).stdout
            )
            self.assertEqual(rejected["status"], "misconception_rejected")
            projected = json.loads(
                (workspace / "state" / "misconceptions.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(projected["misconceptions"], [])
            concepts = json.loads(
                (workspace / "state" / "concepts.json").read_text(encoding="utf-8")
            )
            self.assertEqual(len(concepts["concepts"]), 1)

    def test_correction_removes_superseded_evidence_from_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            observed = self.observe(
                workspace,
                session="session-1",
                dimension="application",
                item="application-1",
                timestamp="2026-08-04T10:05:00Z",
            )
            corrected = self.run_cli(
                "correct",
                str(workspace),
                "--event-id",
                str(observed["event_id"]),
                "--reason",
                "The rubric was mapped to the wrong item",
                "--timestamp",
                "2026-08-04T10:06:00Z",
            )
            correction = json.loads(corrected.stdout)
            self.assertEqual(correction["status"], "corrected")
            projection = json.loads((workspace / "state" / "concepts.json").read_text())
            self.assertEqual(projection["concepts"], [])
            events = [
                json.loads(line)
                for line in (workspace / "state" / "sessions.jsonl")
                .read_text()
                .splitlines()
            ]
            self.assertEqual(
                [event["event_type"] for event in events], ["observation", "correction"]
            )

    def test_deletion_is_previewed_confirmed_and_physical(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            observed = self.observe(
                workspace,
                session="session-sensitive",
                dimension="application",
                item="sensitive-item-marker",
                timestamp="2026-08-04T10:05:00Z",
            )
            preview = json.loads(
                self.run_cli(
                    "delete",
                    str(workspace),
                    "--event-id",
                    str(observed["event_id"]),
                    "--dry-run",
                ).stdout
            )
            self.assertEqual(preview["would_delete_event_ids"], [observed["event_id"]])

            self.run_cli(
                "delete",
                str(workspace),
                "--event-id",
                str(observed["event_id"]),
                expected=4,
            )
            receipt = json.loads(
                self.run_cli(
                    "delete",
                    str(workspace),
                    "--event-id",
                    str(observed["event_id"]),
                    "--confirm",
                ).stdout
            )
            self.assertEqual(receipt["deleted_event_ids"], [observed["event_id"]])
            self.assertNotIn(
                "sensitive-item-marker",
                (workspace / "state" / "sessions.jsonl").read_text(),
            )
            projection = json.loads((workspace / "state" / "concepts.json").read_text())
            self.assertEqual(projection["concepts"], [])

    def test_deleting_one_invalidated_observation_keeps_other_targets_invalidated(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            first = self.observe(
                workspace,
                session="session-1",
                dimension="application",
                item="application-1",
                timestamp="2026-08-04T10:05:00Z",
            )
            second = self.observe(
                workspace,
                session="session-1",
                dimension="transfer",
                item="transfer-1",
                timestamp="2026-08-04T10:06:00Z",
            )
            self.run_cli(
                "invalidate",
                str(workspace),
                "--source-id",
                "postgres-index-docs",
                "--source-version",
                "2026-08-04",
                "--reason",
                "The source version was withdrawn",
                "--timestamp",
                "2026-08-04T10:07:00Z",
            )

            deleted = json.loads(
                self.run_cli(
                    "delete",
                    str(workspace),
                    "--event-id",
                    str(first["event_id"]),
                    "--confirm",
                ).stdout
            )
            self.assertEqual(deleted["dependent_events_rewritten"], 1)
            events = [
                json.loads(line)
                for line in (workspace / "state" / "sessions.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertEqual(
                [event["event_type"] for event in events],
                ["observation", "invalidation"],
            )
            self.assertEqual(events[0]["event_id"], second["event_id"])
            self.assertEqual(events[1]["invalidated_event_ids"], [second["event_id"]])
            projection = json.loads(
                (workspace / "state" / "concepts.json").read_text(encoding="utf-8")
            )
            self.assertEqual(projection["concepts"], [])
            self.assertNotIn(str(first["event_id"]), json.dumps(events))

    def test_export_is_scoped_and_versioned(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            workspace = temp_path / "course"
            export_path = temp_path / "learner-export.zip"
            self.init_workspace(workspace)
            self.observe(
                workspace,
                session="session-1",
                dimension="application",
                item="application-1",
                timestamp="2026-08-04T10:05:00Z",
            )
            result = json.loads(
                self.run_cli(
                    "export",
                    str(workspace),
                    str(export_path),
                    "--timestamp",
                    "2026-08-04T11:00:00Z",
                ).stdout
            )
            self.assertEqual(result["status"], "exported")
            self.assertTrue(export_path.is_file())
            self.assertEqual(len(result["sha256"]), 64)


class TestRouting(CliTestCase):
    def test_every_public_mode_fixture_matches_the_cli(self) -> None:
        fixtures = json.loads(ROUTING_FIXTURES.read_text(encoding="utf-8"))
        for case in fixtures["cases"]:
            arguments = ["route", "--request", case["request"]]
            if case.get("answer_now"):
                arguments.append("--answer-now")
            if case.get("demote"):
                arguments.append("--demote")
            result = json.loads(self.run_cli(*arguments).stdout)
            for key, expected in case["expected"].items():
                self.assertEqual(result[key], expected, case["id"])

    def test_route_uses_lightest_mode_and_honors_overrides(self) -> None:
        quick = json.loads(
            self.run_cli(
                "route", "--request", "Explain what a database index is in two minutes"
            ).stdout
        )
        self.assertEqual(quick["mode"], "quick")
        self.assertFalse(quick["persistence"])

        lesson = json.loads(
            self.run_cli(
                "route",
                "--request",
                "Create a focused lesson with guided practice on B-tree indexes",
            ).stdout
        )
        self.assertEqual(lesson["mode"], "lesson")

        course = json.loads(
            self.run_cli(
                "route",
                "--request",
                "Build a six-week course and let me resume it across sessions",
            ).stdout
        )
        self.assertEqual(course["mode"], "course")
        self.assertEqual(course["persistence"], "consent_required")

        resuming = json.loads(
            self.run_cli(
                "route",
                "--request",
                "I am resuming: the state says one heavily hinted application answer",
            ).stdout
        )
        self.assertEqual(resuming["mode"], "course")
        self.assertEqual(resuming["persistence"], "consent_required")

        transfer_lesson = json.loads(
            self.run_cli(
                "route",
                "--request",
                "Teach a two-thread lost update and do not reveal the transfer answer before an attempt",
            ).stdout
        )
        self.assertEqual(transfer_lesson["mode"], "lesson")
        self.assertFalse(transfer_lesson["persistence"])

        answer = json.loads(
            self.run_cli(
                "route",
                "--request",
                "Keep asking me Socratic questions",
                "--answer-now",
            ).stdout
        )
        self.assertEqual(answer["action"], "answer_now")
        self.assertEqual(answer["mode"], "quick")


if __name__ == "__main__":
    unittest.main()
