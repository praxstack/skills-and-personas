"""Regression tests for strict state, consent, invalidation, and deletion contracts."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "bin" / "python"
CLI = ROOT / "scripts" / "prax_teach.py"
sys.path.insert(0, str(ROOT / "scripts"))
from praxteach import state as state_module


class StateContractHardeningTest(unittest.TestCase):
    maxDiff = None

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
            [str(PYTHON), str(CLI), *arguments],
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

    def init_workspace(self, workspace: Path) -> None:
        self.run_cli(
            "init",
            str(workspace),
            "--learner-id",
            "learner-contract",
            "--goal",
            "Transfer the idea independently",
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
            "source-shared",
            "--title",
            "Shared state-contract source",
            "--url",
            "https://example.invalid/state-contract-source",
            "--author-or-publisher",
            "Prax Teach test suite",
            "--source-type",
            "official-doc",
            "--retrieved-at",
            "2026-08-04",
            "--version-or-date",
            "2026-08-04",
            "--license-or-use-note",
            "Synthetic fixture for state-contract testing.",
            "--supports",
            "concept-a",
            "--limitations",
            "Not real-world instructional evidence.",
        )

    def observe(
        self,
        workspace: Path,
        *,
        concept: str = "concept-a",
        item: str = "item-a",
        content_version: str = "sha256:" + "a" * 64,
        timestamp: str = "2026-08-04T10:05:00Z",
    ) -> dict[str, object]:
        return json.loads(
            self.run_cli(
                "observe",
                str(workspace),
                "--response",
                f"Learner response for {item}",
                "--session",
                "session-1",
                "--concept",
                concept,
                "--dimension",
                "application",
                "--score",
                "0.9",
                "--hint-level",
                "0",
                "--item",
                item,
                "--item-version",
                "v1",
                "--content-version",
                content_version,
                "--source-id",
                "source-shared",
                "--source-version",
                "2026-08-04",
                "--timestamp",
                timestamp,
            ).stdout
        )

    def review(self, workspace: Path, *, concept: str, item: str) -> dict[str, object]:
        events = [
            json.loads(line)
            for line in (workspace / "state" / "sessions.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        reviewed_observations = {
            json.loads(line)["input"]["observation_event_id"]
            for line in (workspace / "state" / "reviews.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if json.loads(line)["event_type"] == "review"
        }
        candidates = [
            event
            for event in events
            if event["event_type"] == "observation"
            and event["concept_id"] == concept
            and event["item_id"] == item
            and event["event_id"] not in reviewed_observations
        ]
        if not candidates:
            observed = self.observe(workspace, concept=concept, item=item)
            observation_event_id = str(observed["event_id"])
        else:
            observation_event_id = str(candidates[-1]["event_id"])
        return json.loads(
            self.run_cli(
                "review",
                str(workspace),
                "--observation-event",
                observation_event_id,
            ).stdout
        )

    def test_runtime_rejects_unknown_top_level_and_nested_state_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)

            learner_path = workspace / "state" / "learner.json"
            pristine = json.loads(learner_path.read_text(encoding="utf-8"))
            for mutation in (
                lambda value: value.__setitem__("inferred_disability", "ADHD"),
                lambda value: value["goal"].__setitem__("personality", "anxious"),
                lambda value: value["consent"].__setitem__("silent_scope", ["all"]),
            ):
                document = json.loads(json.dumps(pristine))
                mutation(document)
                learner_path.write_text(json.dumps(document) + "\n", encoding="utf-8")
                failed = self.run_cli("show", str(workspace), expected=6)
                self.assertIn("unsupported field", failed.stderr.lower())

            learner_path.write_text(json.dumps(pristine) + "\n", encoding="utf-8")
            observed = self.observe(workspace)
            log = workspace / "state" / "sessions.jsonl"
            event = json.loads(log.read_text(encoding="utf-8"))
            event["result"]["private_trait"] = "never-store-me"
            log.write_text(json.dumps(event) + "\n", encoding="utf-8")
            failed = self.run_cli("rebuild", str(workspace), expected=6)
            self.assertIn("unsupported field", failed.stderr.lower())
            self.assertEqual(observed["status"], "observed")

    def test_observe_preserves_exact_response_reference_and_inference_fields(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            response_ref = "artifacts/session-1/answer 01.txt#exact"
            learner_note = "  This is my own note; preserve its spacing.  "
            self.run_cli(
                "observe",
                str(workspace),
                "--response-ref",
                response_ref,
                "--session",
                "session-1",
                "--concept",
                "resume-fidelity",
                "--dimension",
                "transfer",
                "--score",
                "0.85",
                "--hint-level",
                "0",
                "--item",
                "resume-item",
                "--item-version",
                "v1",
                "--content-version",
                "sha256:" + "d" * 64,
                "--source-id",
                "source-shared",
                "--source-version",
                "2026-08-04",
                "--learner-authored",
                learner_note,
                "--agent-inference-summary",
                "Transfer appears plausible but delayed retrieval is untested.",
                "--agent-inference-certainty",
                "0.61",
                "--timestamp",
                "2026-08-04T10:05:00Z",
            )
            event = json.loads(
                (workspace / "state" / "sessions.jsonl").read_text(encoding="utf-8")
            )
            self.assertIsNone(event["response"])
            self.assertEqual(event["response_ref"], response_ref)
            self.assertEqual(event["learner_authored"], learner_note)
            self.assertEqual(event["agent_inference"]["certainty"], 0.61)
            self.assertEqual(event["rubric"]["score"], 0.85)
            self.assertEqual(event["rubric"]["dimensions"]["transfer"], 0.85)
            self.assertIsNone(event["rubric"]["dimensions"]["recall"])

    def test_workspace_validation_rejects_semantically_invalid_review_records(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            self.review(workspace, concept="concept-a", item="item-a")
            reviews = workspace / "state" / "reviews.jsonl"
            record = json.loads(reviews.read_text(encoding="utf-8"))
            record["input"]["sensitive_profile"] = "forged"
            reviews.write_text(json.dumps(record) + "\n", encoding="utf-8")
            failed = self.run_cli("show", str(workspace), expected=6)
            self.assertIn("unsupported field", failed.stderr.lower())

    def test_invalidation_can_target_one_exact_content_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            old = self.observe(
                workspace,
                item="old-item",
                content_version="sha256:" + "a" * 64,
            )
            new = self.observe(
                workspace,
                item="new-item",
                content_version="sha256:" + "b" * 64,
                timestamp="2026-08-04T10:06:00Z",
            )
            receipt = json.loads(
                self.run_cli(
                    "invalidate-version",
                    str(workspace),
                    "--source-id",
                    "source-shared",
                    "--source-version",
                    "2026-08-04",
                    "--content-version",
                    "sha256:" + "a" * 64,
                    "--reason",
                    "Only the old content version was withdrawn",
                    "--timestamp",
                    "2026-08-04T10:07:00Z",
                ).stdout
            )
            self.assertEqual(receipt["invalidated_event_ids"], [old["event_id"]])
            self.assertNotIn(new["event_id"], receipt["invalidated_event_ids"])

    def test_item_version_invalidation_requires_an_item_identifier(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            self.observe(workspace, item="item-a")
            self.observe(
                workspace,
                item="item-b",
                timestamp="2026-08-04T10:06:00Z",
            )
            before = (workspace / "state" / "sessions.jsonl").read_bytes()
            failed = self.run_cli(
                "invalidate-version",
                str(workspace),
                "--item-version",
                "v1",
                "--reason",
                "A local version label is not globally unique",
                "--timestamp",
                "2026-08-04T10:07:00Z",
                expected=6,
            )
            self.assertIn("--item", failed.stderr)
            self.assertEqual(
                before, (workspace / "state" / "sessions.jsonl").read_bytes()
            )

    def test_observation_item_identity_and_version_binding_make_invalidation_exact(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            first = self.observe(
                workspace,
                concept="concept-a",
                item="shared-item",
                content_version="sha256:" + "a" * 64,
            )
            log = workspace / "state" / "sessions.jsonl"

            invalid_cases = (
                (
                    "concept-b",
                    "application",
                    "v1",
                    "sha256:" + "a" * 64,
                    "concept",
                ),
                (
                    "concept-a",
                    "recall",
                    "v1",
                    "sha256:" + "a" * 64,
                    "dimension",
                ),
                (
                    "concept-a",
                    "application",
                    "v1",
                    "sha256:" + "b" * 64,
                    "content versions",
                ),
            )
            for concept, dimension, version, content_version, error in invalid_cases:
                before = log.read_bytes()
                failed = self.run_cli(
                    "observe",
                    str(workspace),
                    "--response",
                    "Binding validation response.",
                    "--session",
                    "session-2",
                    "--concept",
                    concept,
                    "--dimension",
                    dimension,
                    "--score",
                    "0.9",
                    "--hint-level",
                    "0",
                    "--item",
                    "shared-item",
                    "--item-version",
                    version,
                    "--content-version",
                    content_version,
                    "--source-id",
                    "source-shared",
                    "--source-version",
                    "2026-08-04",
                    "--timestamp",
                    "2026-08-04T10:06:00Z",
                    expected=6,
                )
                self.assertIn(error, failed.stderr.lower())
                self.assertEqual(before, log.read_bytes())

            second = json.loads(
                self.run_cli(
                    "observe",
                    str(workspace),
                    "--response",
                    "Second content-version response.",
                    "--session",
                    "session-2",
                    "--concept",
                    "concept-a",
                    "--dimension",
                    "application",
                    "--score",
                    "0.9",
                    "--hint-level",
                    "0",
                    "--item",
                    "shared-item",
                    "--item-version",
                    "v2",
                    "--content-version",
                    "sha256:" + "b" * 64,
                    "--source-id",
                    "source-shared",
                    "--source-version",
                    "2026-08-04",
                    "--timestamp",
                    "2026-08-04T10:06:00Z",
                ).stdout
            )
            receipt = json.loads(
                self.run_cli(
                    "invalidate-version",
                    str(workspace),
                    "--item",
                    "shared-item",
                    "--item-version",
                    "v1",
                    "--reason",
                    "Withdraw exactly the first item version",
                    "--timestamp",
                    "2026-08-04T10:07:00Z",
                ).stdout
            )
            self.assertEqual(receipt["invalidated_event_ids"], [first["event_id"]])
            self.assertNotIn(second["event_id"], receipt["invalidated_event_ids"])

    def test_deletion_preview_equals_confirmed_event_rewrites_and_review_scrub(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            first = self.observe(workspace, concept="concept-a", item="item-a")
            self.observe(
                workspace,
                concept="concept-b",
                item="item-b",
                timestamp="2026-08-04T10:06:00Z",
            )
            self.review(workspace, concept="concept-a", item="item-a")
            self.review(workspace, concept="concept-b", item="item-b")
            self.run_cli(
                "invalidate",
                str(workspace),
                "--source-id",
                "source-shared",
                "--source-version",
                "2026-08-04",
                "--reason",
                "Shared source needs selective cleanup",
                "--timestamp",
                "2026-08-04T12:01:00Z",
            )

            preview = json.loads(
                self.run_cli(
                    "delete", str(workspace), "--concept", "concept-a", "--dry-run"
                ).stdout
            )
            self.assertEqual(preview["selected_event_ids"], [first["event_id"]])
            self.assertEqual(len(preview["rewritten_events"]), 1)
            self.assertEqual(preview["review_event_ids_removed"], [])

            confirmed = json.loads(
                self.run_cli(
                    "delete", str(workspace), "--concept", "concept-a", "--confirm"
                ).stdout
            )
            self.assertEqual(confirmed["plan"], preview["plan"])
            self.assertNotIn(
                "concept-a", (workspace / "state" / "reviews.jsonl").read_text()
            )
            self.assertEqual((workspace / "state" / "reviews.jsonl").read_bytes(), b"")

    def test_concept_deletion_removes_causally_bound_review_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            review = self.review(
                workspace, concept="review-only-concept", item="review-only-item"
            )
            preview = json.loads(
                self.run_cli(
                    "delete",
                    str(workspace),
                    "--concept",
                    "review-only-concept",
                    "--dry-run",
                ).stdout
            )
            self.assertEqual(len(preview["selected_event_ids"]), 1)
            self.assertEqual(preview["review_event_ids_removed"], [review["event_id"]])
            confirmed = json.loads(
                self.run_cli(
                    "delete",
                    str(workspace),
                    "--concept",
                    "review-only-concept",
                    "--confirm",
                ).stdout
            )
            self.assertEqual(confirmed["plan"], preview["plan"])
            self.assertEqual((workspace / "state" / "reviews.jsonl").read_bytes(), b"")

    def test_item_deletion_removes_only_the_exact_items_evidence_and_reviews(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            first = self.observe(workspace, concept="concept-a", item="item-a")
            second = self.observe(
                workspace,
                concept="concept-a",
                item="item-b",
                timestamp="2026-08-04T10:06:00Z",
            )
            first_review = self.review(workspace, concept="concept-a", item="item-a")
            second_review = self.review(workspace, concept="concept-a", item="item-b")

            preview = json.loads(
                self.run_cli(
                    "delete", str(workspace), "--item", "item-a", "--dry-run"
                ).stdout
            )
            self.assertEqual(preview["selected_event_ids"], [first["event_id"]])
            self.assertEqual(
                preview["review_event_ids_removed"], [first_review["event_id"]]
            )
            self.assertEqual(
                preview["plan"]["review_match_basis"],
                "causal-observation-session-concept-or-item",
            )

            confirmed = json.loads(
                self.run_cli(
                    "delete", str(workspace), "--item", "item-a", "--confirm"
                ).stdout
            )
            self.assertEqual(confirmed["plan"], preview["plan"])
            sessions = (workspace / "state" / "sessions.jsonl").read_text()
            reviews = (workspace / "state" / "reviews.jsonl").read_text()
            self.assertNotIn(str(first["event_id"]), sessions)
            self.assertIn(str(second["event_id"]), sessions)
            self.assertNotIn(str(first_review["event_id"]), reviews)
            self.assertIn(str(second_review["event_id"]), reviews)

    def test_interrupted_delete_recovers_after_persistence_withdrawal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            observed = self.observe(
                workspace, concept="sensitive-concept", item="sensitive-item"
            )
            self.run_cli(
                "disable-persistence",
                str(workspace),
                "--reason",
                "Learner withdrew storage consent",
                "--timestamp",
                "2026-08-04T13:00:00Z",
            )

            original_atomic_write = state_module.atomic_write
            failed_once = False

            def fail_first_projection(
                path: Path, data: bytes, **kwargs: object
            ) -> None:
                nonlocal failed_once
                if path.name == "concepts.json" and not failed_once:
                    failed_once = True
                    raise OSError("injected projection replacement failure")
                original_atomic_write(path, data, **kwargs)

            with (
                mock.patch.object(
                    state_module, "atomic_write", side_effect=fail_first_projection
                ),
                self.assertRaisesRegex(OSError, "injected projection"),
            ):
                state_module.delete_events(
                    str(workspace),
                    event_ids=[str(observed["event_id"])],
                    session_id=None,
                    concept_id=None,
                    item_id=None,
                    dry_run=False,
                    confirm=True,
                )

            journal = workspace / "state" / ".delete-transaction.json"
            self.assertTrue(journal.is_file())
            recovery = state_module.delete_events(
                str(workspace),
                event_ids=[str(observed["event_id"])],
                session_id=None,
                concept_id=None,
                item_id=None,
                dry_run=False,
                confirm=True,
            )
            self.assertEqual(recovery["status"], "deletion_recovered")
            recovered = state_module.show_state(str(workspace))
            self.assertEqual(recovered["evidence_event_count"], 0)
            self.assertEqual(recovered["concepts"]["concepts"], [])
            self.assertFalse(journal.exists())

    def test_interrupted_observation_recovers_before_consent_withdrawal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            event = state_module.make_observation(
                session_id="session-transaction",
                concept_id="transactional-projection",
                dimension="application",
                score=0.9,
                hint_level=0,
                item_id="transaction-item",
                item_version="v1",
                content_id="transactional-projection",
                content_version="sha256:" + "f" * 64,
                objective_id="objective:transactional-projection",
                model_and_prompt_version="test-tutor:model:prompt-v1",
                source_id="source-shared",
                source_version="2026-08-04",
                timestamp="2026-08-04T10:05:00Z",
                response="The evidence log and projections must commit together.",
                response_ref=None,
            )
            original_atomic_write = state_module.atomic_write
            failed_once = False

            def fail_first_projection(
                path: Path, data: bytes, **kwargs: object
            ) -> None:
                nonlocal failed_once
                if path.name == "concepts.json" and not failed_once:
                    failed_once = True
                    raise OSError("injected state projection failure")
                original_atomic_write(path, data, **kwargs)

            with (
                mock.patch.object(
                    state_module, "atomic_write", side_effect=fail_first_projection
                ),
                self.assertRaisesRegex(OSError, "state projection"),
            ):
                state_module.append_observation(str(workspace), event)

            journal = workspace / "state" / ".state-transaction.json"
            self.assertTrue(journal.is_file())
            disabled = state_module.disable_persistence(
                str(workspace),
                reason="Learner withdrew storage consent after the interruption",
                timestamp="2026-08-04T10:06:00Z",
            )
            self.assertEqual(disabled["status"], "persistence_disabled")
            shown = state_module.show_state(str(workspace))
            self.assertEqual(shown["evidence_event_count"], 1)
            self.assertEqual(
                shown["concepts"]["concepts"][0]["concept_id"],
                "transactional-projection",
            )
            self.assertFalse(journal.exists())

    def test_interrupted_state_transaction_refuses_divergent_log(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            event = state_module.make_observation(
                session_id="session-transaction",
                concept_id="transaction-binding",
                dimension="application",
                score=0.9,
                hint_level=0,
                item_id="transaction-item",
                item_version="v1",
                content_id="transaction-binding",
                content_version="sha256:" + "f" * 64,
                objective_id="objective:transaction-binding",
                model_and_prompt_version="test-tutor:model:prompt-v1",
                source_id="source-shared",
                source_version="2026-08-04",
                timestamp="2026-08-04T10:05:00Z",
                response="This exact response is transaction-bound.",
                response_ref=None,
            )
            original_atomic_write = state_module.atomic_write
            failed_once = False

            def fail_first_projection(
                path: Path, data: bytes, **kwargs: object
            ) -> None:
                nonlocal failed_once
                if path.name == "concepts.json" and not failed_once:
                    failed_once = True
                    raise OSError("injected state projection failure")
                original_atomic_write(path, data, **kwargs)

            with (
                mock.patch.object(
                    state_module, "atomic_write", side_effect=fail_first_projection
                ),
                self.assertRaisesRegex(OSError, "state projection"),
            ):
                state_module.append_observation(str(workspace), event)

            sessions = workspace / "state" / "sessions.jsonl"
            divergent = sessions.read_bytes() + b'{"unbound":true}\n'
            sessions.write_bytes(divergent)
            with self.assertRaisesRegex(
                state_module.SafetyError, "divergent sessions.jsonl"
            ):
                state_module.show_state(str(workspace))
            self.assertEqual(sessions.read_bytes(), divergent)

    def test_scheduler_recovers_interrupted_delete_before_appending_review(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            deleted = self.observe(workspace, concept="concept-a", item="item-a")
            self.observe(
                workspace,
                concept="concept-b",
                item="item-b",
                timestamp="2026-08-04T10:06:00Z",
            )
            first_review = self.review(workspace, concept="concept-b", item="item-b")

            original_atomic_write = state_module.atomic_write
            failed_once = False

            def fail_first_projection(
                path: Path, data: bytes, **kwargs: object
            ) -> None:
                nonlocal failed_once
                if path.name == "concepts.json" and not failed_once:
                    failed_once = True
                    raise OSError("injected projection replacement failure")
                original_atomic_write(path, data, **kwargs)

            with (
                mock.patch.object(
                    state_module, "atomic_write", side_effect=fail_first_projection
                ),
                self.assertRaisesRegex(OSError, "injected projection"),
            ):
                state_module.delete_events(
                    str(workspace),
                    event_ids=[str(deleted["event_id"])],
                    session_id=None,
                    concept_id=None,
                    item_id=None,
                    dry_run=False,
                    confirm=True,
                )

            journal = workspace / "state" / ".delete-transaction.json"
            self.assertTrue(journal.is_file())
            second_observation = self.observe(
                workspace,
                concept="concept-b",
                item="item-b",
                timestamp="2026-08-04T13:00:00Z",
            )
            second_review = json.loads(
                self.run_cli(
                    "review",
                    str(workspace),
                    "--observation-event",
                    str(second_observation["event_id"]),
                ).stdout
            )
            self.assertFalse(journal.exists())
            review_ids = {
                json.loads(line)["event_id"]
                for line in (workspace / "state" / "reviews.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            }
            self.assertEqual(
                review_ids,
                {first_review["event_id"], second_review["event_id"]},
            )
            state_module.show_state(str(workspace))
            review_ids_after_replay = {
                json.loads(line)["event_id"]
                for line in (workspace / "state" / "reviews.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            }
            self.assertEqual(review_ids_after_replay, review_ids)

    def test_session_deletion_uses_the_recorded_review_dependency(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            first = self.observe(
                workspace,
                concept="concept-a",
                item="shared-item",
                content_version="sha256:" + "a" * 64,
            )
            self.run_cli(
                "observe",
                str(workspace),
                "--response",
                "A second session response for deletion dependency testing.",
                "--session",
                "session-2",
                "--concept",
                "concept-a",
                "--dimension",
                "application",
                "--score",
                "0.9",
                "--hint-level",
                "0",
                "--item",
                "shared-item",
                "--item-version",
                "v2",
                "--content-version",
                "sha256:" + "b" * 64,
                "--source-id",
                "source-shared",
                "--source-version",
                "2026-08-04",
                "--timestamp",
                "2026-08-04T10:06:00Z",
            )
            review = self.review(workspace, concept="concept-a", item="shared-item")
            preview = json.loads(
                self.run_cli(
                    "delete",
                    str(workspace),
                    "--session",
                    "session-1",
                    "--dry-run",
                ).stdout
            )
            self.assertEqual(preview["selected_event_ids"], [first["event_id"]])
            self.assertEqual(preview["review_event_ids_removed"], [])
            self.assertEqual(
                preview["plan"]["review_match_basis"],
                "causal-observation-session-concept-or-item",
            )
            self.run_cli(
                "delete",
                str(workspace),
                "--session",
                "session-1",
                "--confirm",
            )
            retained_reviews = (workspace / "state" / "reviews.jsonl").read_text(
                encoding="utf-8"
            )
            self.assertIn(str(review["event_id"]), retained_reviews)

    def test_disable_persistence_blocks_future_evidence_but_allows_control_actions(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            workspace = base / "course"
            self.init_workspace(workspace)
            observed = self.observe(workspace)
            disabled = json.loads(
                self.run_cli(
                    "disable-persistence",
                    str(workspace),
                    "--reason",
                    "Learner withdrew consent",
                    "--timestamp",
                    "2026-08-04T13:00:00Z",
                ).stdout
            )
            self.assertEqual(disabled["status"], "persistence_disabled")
            learner = json.loads(
                (workspace / "state" / "learner.json").read_text(encoding="utf-8")
            )
            self.assertFalse(learner["consent"]["persistent_state"])

            self.run_cli("show", str(workspace))
            state_before = {
                path.relative_to(workspace).as_posix(): (
                    path.stat().st_ino,
                    path.stat().st_mtime_ns,
                    path.stat().st_mode,
                    path.read_bytes(),
                )
                for path in sorted((workspace / "state").iterdir())
                if path.is_file()
            }
            inventory_before = sorted(
                path.relative_to(workspace).as_posix() for path in workspace.rglob("*")
            )
            self.run_cli(
                "export",
                str(workspace),
                str(base / "disabled-export.zip"),
                "--timestamp",
                "2026-08-04T13:01:00Z",
            )
            state_after = {
                path.relative_to(workspace).as_posix(): (
                    path.stat().st_ino,
                    path.stat().st_mtime_ns,
                    path.stat().st_mode,
                    path.read_bytes(),
                )
                for path in sorted((workspace / "state").iterdir())
                if path.is_file()
            }
            inventory_after = sorted(
                path.relative_to(workspace).as_posix() for path in workspace.rglob("*")
            )
            self.assertEqual(state_after, state_before)
            self.assertEqual(inventory_after, inventory_before)
            failed_observe = self.run_cli(
                "observe",
                str(workspace),
                "--response",
                "This must be rejected after persistence withdrawal.",
                "--session",
                "session-2",
                "--concept",
                "concept-a",
                "--dimension",
                "recall",
                "--score",
                "1",
                "--hint-level",
                "0",
                "--item",
                "item-new",
                "--item-version",
                "v1",
                "--content-version",
                "sha256:" + "c" * 64,
                "--source-id",
                "source-shared",
                "--source-version",
                "2026-08-04",
                "--timestamp",
                "2026-08-04T13:02:00Z",
                expected=3,
            )
            self.assertIn("persistence consent", failed_observe.stderr.lower())
            failed_review = self.run_cli(
                "review",
                str(workspace),
                "--observation-event",
                "evt-" + "0" * 32,
                expected=3,
            )
            self.assertIn("persistence consent", failed_review.stderr.lower())

            deleted = json.loads(
                self.run_cli(
                    "delete",
                    str(workspace),
                    "--event-id",
                    str(observed["event_id"]),
                    "--confirm",
                ).stdout
            )
            self.assertEqual(deleted["status"], "deleted")

    def test_compensating_events_cannot_predate_their_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            observed = self.observe(workspace)
            before = (workspace / "state" / "sessions.jsonl").read_bytes()
            correction = self.run_cli(
                "correct",
                str(workspace),
                "--event-id",
                str(observed["event_id"]),
                "--reason",
                "Correction cannot happen before observation",
                "--timestamp",
                "2026-08-04T10:04:00Z",
                expected=6,
            )
            self.assertIn("earlier", correction.stderr.lower())
            self.assertEqual(
                before, (workspace / "state" / "sessions.jsonl").read_bytes()
            )
            invalidation = self.run_cli(
                "invalidate",
                str(workspace),
                "--event-id",
                str(observed["event_id"]),
                "--reason",
                "Invalidation cannot happen before observation",
                "--timestamp",
                "2026-08-04T10:04:00Z",
                expected=6,
            )
            self.assertIn("earlier", invalidation.stderr.lower())
            self.assertEqual(
                before, (workspace / "state" / "sessions.jsonl").read_bytes()
            )

    def test_replay_rejects_a_content_bound_but_time_travelling_correction(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            observed = self.observe(workspace)
            self.run_cli(
                "correct",
                str(workspace),
                "--event-id",
                str(observed["event_id"]),
                "--reason",
                "Learner corrected the observation",
                "--timestamp",
                "2026-08-04T10:06:00Z",
            )
            log = workspace / "state" / "sessions.jsonl"
            records = [json.loads(line) for line in log.read_text().splitlines()]
            correction = records[1]
            correction["timestamp"] = "2026-08-04T10:04:00Z"
            without_id = dict(correction)
            without_id.pop("event_id")
            encoded = json.dumps(
                without_id,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
                allow_nan=False,
            ).encode("utf-8")
            correction["event_id"] = "evt-" + hashlib.sha256(encoded).hexdigest()[:32]
            log.write_text(
                "\n".join(json.dumps(record) for record in records) + "\n",
                encoding="utf-8",
            )
            failed = self.run_cli("show", str(workspace), expected=6)
            self.assertIn("earlier", failed.stderr.lower())

    def test_delete_all_state_has_exact_preview_and_removes_only_workspace(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            workspace = base / "course"
            sentinel = base / "keep.txt"
            sentinel.write_text("keep", encoding="utf-8")
            self.init_workspace(workspace)
            self.observe(workspace)
            preview = json.loads(
                self.run_cli(
                    "delete", str(workspace), "--all-state", "--dry-run"
                ).stdout
            )
            self.assertEqual(preview["workspace"], str(workspace.resolve()))
            self.assertGreater(preview["plan"]["file_count"], 0)
            self.run_cli("delete", str(workspace), "--all-state", expected=4)
            receipt = json.loads(
                self.run_cli(
                    "delete", str(workspace), "--all-state", "--confirm"
                ).stdout
            )
            self.assertEqual(receipt["plan"], preview["plan"])
            self.assertFalse(workspace.exists())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_delete_all_state_recovers_after_partial_recursive_removal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            workspace = base / "course"
            sentinel = base / "keep.txt"
            sentinel.write_text("keep", encoding="utf-8")
            self.init_workspace(workspace)
            self.observe(workspace)
            parent_journal = base / ".course.full-delete-transaction.json"
            quarantine = base / ".course.prax-teach-deleting"

            def partially_remove(descriptor: int) -> None:
                os.unlink("state/sessions.jsonl", dir_fd=descriptor)
                raise OSError("injected partial recursive deletion")

            with (
                mock.patch.object(
                    state_module,
                    "_remove_directory_contents",
                    side_effect=partially_remove,
                ),
                self.assertRaisesRegex(OSError, "partial recursive deletion"),
            ):
                state_module.delete_workspace(
                    str(workspace), dry_run=False, confirm=True
                )

            self.assertFalse(workspace.exists())
            self.assertTrue(quarantine.is_dir())
            self.assertTrue(parent_journal.is_file())
            self.assertFalse((quarantine / "state" / "sessions.jsonl").exists())

            recovered = state_module.delete_workspace(
                str(workspace), dry_run=False, confirm=True
            )
            self.assertEqual(recovered["status"], "all_state_deletion_recovered")
            self.assertFalse(workspace.exists())
            self.assertFalse(quarantine.exists())
            self.assertFalse(parent_journal.exists())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_workspace_name_reuse_finishes_confirmed_partial_deletion_first(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            workspace = base / "course"
            self.init_workspace(workspace)
            self.observe(workspace)

            def partially_remove(descriptor: int) -> None:
                os.unlink("state/sessions.jsonl", dir_fd=descriptor)
                raise OSError("injected partial recursive deletion")

            with (
                mock.patch.object(
                    state_module,
                    "_remove_directory_contents",
                    side_effect=partially_remove,
                ),
                self.assertRaisesRegex(OSError, "partial recursive deletion"),
            ):
                state_module.delete_workspace(
                    str(workspace), dry_run=False, confirm=True
                )

            # Initialization holds the same parent-generation lock, completes
            # the prior confirmed deletion, and only then creates a new inode.
            self.init_workspace(workspace)
            shown = state_module.show_state(str(workspace))
            self.assertEqual(shown["evidence_event_count"], 0)
            self.assertFalse((base / ".course.prax-teach-deleting").exists())
            self.assertFalse((base / ".course.full-delete-transaction.json").exists())

    def test_full_delete_retry_rejects_replacement_quarantine_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            workspace = base / "course"
            self.init_workspace(workspace)
            self.observe(workspace)

            def partially_remove(descriptor: int) -> None:
                os.unlink("state/sessions.jsonl", dir_fd=descriptor)
                raise OSError("injected partial recursive deletion")

            with (
                mock.patch.object(
                    state_module,
                    "_remove_directory_contents",
                    side_effect=partially_remove,
                ),
                self.assertRaisesRegex(OSError, "partial recursive deletion"),
            ):
                state_module.delete_workspace(
                    str(workspace), dry_run=False, confirm=True
                )

            quarantine = base / ".course.prax-teach-deleting"
            displaced = base / ".course.displaced-generation"
            quarantine.rename(displaced)
            quarantine.mkdir(mode=0o700)
            marker = quarantine / "must-not-delete.txt"
            marker.write_text("replacement", encoding="utf-8")

            with self.assertRaisesRegex(
                state_module.SafetyError, "generation does not match"
            ):
                state_module.delete_workspace(
                    str(workspace), dry_run=False, confirm=True
                )
            self.assertEqual(marker.read_text(encoding="utf-8"), "replacement")
            self.assertTrue(displaced.is_dir())

    def test_delete_all_state_rejects_any_symlink_inside_the_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            workspace = base / "course"
            outside = base / "outside.txt"
            outside.write_text("untouched", encoding="utf-8")
            self.init_workspace(workspace)
            (workspace / "assets" / "unsafe-link").symlink_to(outside)
            failed = self.run_cli(
                "delete", str(workspace), "--all-state", "--confirm", expected=5
            )
            self.assertIn("unsafe entry", failed.stderr.lower())
            self.assertTrue(workspace.is_dir())
            self.assertEqual(outside.read_text(encoding="utf-8"), "untouched")


if __name__ == "__main__":
    unittest.main()
