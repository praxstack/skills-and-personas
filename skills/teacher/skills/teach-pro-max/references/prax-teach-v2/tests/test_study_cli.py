#!/usr/bin/env python3
"""Black-box tests for the learner-outcome study machinery."""

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
CLI = ROOT / "scripts" / "study.py"
sys.path.insert(0, str(ROOT / "scripts"))
import study as study_module


class TestStudyCli(unittest.TestCase):
    def run_cli(
        self, *args: str, expected: int = 0
    ) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            [sys.executable, str(CLI), *args],
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

    def write_protocol(self, path: Path, *, synthetic: bool = True) -> None:
        task_bank = self.task_bank_for(path)
        task_bank.write_text(
            json.dumps(
                {
                    "schema_version": "1",
                    "study_id": "index-learning-pilot",
                    "tasks": [
                        {
                            "id": "retention-1",
                            "outcome": "delayed_retention",
                            "prompt": "Hidden delayed-retention item.",
                            "rubric_ref": "rubric-retention-v1",
                        },
                        {
                            "id": "transfer-1",
                            "outcome": "novel_transfer",
                            "prompt": "Hidden novel-transfer item.",
                            "rubric_ref": "rubric-transfer-v1",
                        },
                    ],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        path.write_text(
            json.dumps(
                {
                    "schema_version": "1",
                    "study_id": "index-learning-pilot",
                    "design": "parallel_randomized",
                    "seed": 1729,
                    "arms": ["active-control", "teach", "prax-teach-v2"],
                    "primary_outcomes": ["delayed_retention", "novel_transfer"],
                    "delay_window_days": {"minimum": 7, "maximum": 14},
                    "confidence_level": 0.95,
                    "bootstrap_samples": 400,
                    "synthetic": synthetic,
                    "missing_outcome_policy": "baseline_carried_forward_zero_adjusted_change",
                    "competency_claim": "Select and justify an index for an unseen workload",
                    "evidence": "Blind-scored performance on unseen parallel and transfer items",
                    "task_bank_hash": "sha256:"
                    + hashlib.sha256(task_bank.read_bytes()).hexdigest(),
                },
                indent=2,
            )
            + "\n"
        )

    def task_bank_for(self, protocol: Path) -> Path:
        return protocol.with_name(f"{protocol.stem}-task-bank.json")

    def write_participants(self, path: Path) -> None:
        rows = [
            {
                "participant_id": f"learner-{index:02d}",
                "pretest": float(index % 3) / 10,
                "instruction_at": f"2026-08-{1 + (index % 2):02d}T10:00:00Z",
            }
            for index in range(12)
        ]
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))

    def write_blinding_key(self, path: Path, marker: int = 17) -> None:
        path.write_bytes(bytes((marker + index) % 256 for index in range(32)))
        path.chmod(0o600)

    def test_allocation_is_deterministic_balanced_and_blinded(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            protocol = temp_path / "protocol.json"
            participants = temp_path / "participants.jsonl"
            private_a = temp_path / "allocation-a.jsonl"
            blind_a = temp_path / "blind-a.jsonl"
            private_b = temp_path / "allocation-b.jsonl"
            blind_b = temp_path / "blind-b.jsonl"
            blinding_key = temp_path / "blinding.key"
            self.write_protocol(protocol)
            self.write_participants(participants)
            self.write_blinding_key(blinding_key)

            valid = json.loads(self.run_cli("validate", str(protocol)).stdout)
            self.assertTrue(valid["valid"])
            self.run_cli(
                "allocate",
                str(protocol),
                str(participants),
                str(private_a),
                str(blind_a),
                "--task-bank",
                str(self.task_bank_for(protocol)),
                "--blinding-key",
                str(blinding_key),
            )
            self.run_cli(
                "allocate",
                str(protocol),
                str(participants),
                str(private_b),
                str(blind_b),
                "--task-bank",
                str(self.task_bank_for(protocol)),
                "--blinding-key",
                str(blinding_key),
            )
            self.assertEqual(private_a.read_bytes(), private_b.read_bytes())
            self.assertEqual(blind_a.read_bytes(), blind_b.read_bytes())

            allocations = [
                json.loads(line) for line in private_a.read_text().splitlines()
            ]
            counts = {
                arm: sum(row["arm"] == arm for row in allocations)
                for arm in ("active-control", "teach", "prax-teach-v2")
            }
            self.assertEqual(
                counts, {"active-control": 4, "teach": 4, "prax-teach-v2": 4}
            )
            allocation_hmacs = {
                row["allocation_set_hmac_sha256"] for row in allocations
            }
            self.assertEqual(len(allocation_hmacs), 1)
            self.assertTrue(next(iter(allocation_hmacs)).startswith("hmac-sha256:"))
            self.assertTrue(
                all(
                    row["participant_roster_sha256"]
                    == hashlib.sha256(participants.read_bytes()).hexdigest()
                    for row in allocations
                )
            )
            self.assertTrue(
                all(
                    row["task_bank_sha256"]
                    == hashlib.sha256(
                        self.task_bank_for(protocol).read_bytes()
                    ).hexdigest()
                    for row in allocations
                )
            )
            blind = [json.loads(line) for line in blind_a.read_text().splitlines()]
            self.assertEqual(len(blind), 12)
            for row in blind:
                serialized = json.dumps(row).lower()
                self.assertNotIn("active-control", serialized)
                self.assertNotIn("prax-teach-v2", serialized)
                self.assertNotIn('"arm"', serialized)
                self.assertEqual(
                    row["allocation_set_hmac_sha256"], next(iter(allocation_hmacs))
                )
            protocol_payload = json.loads(protocol.read_text())
            public_protocol_hash = hashlib.sha256(
                json.dumps(
                    protocol_payload,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            predictable_ids = {
                "asm-"
                + hashlib.sha256(
                    f"{public_protocol_hash}\0learner-{index:02d}\0assessment".encode()
                ).hexdigest()[:24]
                for index in range(12)
            }
            self.assertTrue(
                predictable_ids.isdisjoint(
                    {row["assessment_id"] for row in allocations}
                )
            )

    def test_analysis_enforces_window_reports_attrition_and_never_claims_human_evidence_for_synthetic_data(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            protocol = temp_path / "protocol.json"
            participants = temp_path / "participants.jsonl"
            allocation = temp_path / "allocation.jsonl"
            blind = temp_path / "blind.jsonl"
            scores = temp_path / "scores.jsonl"
            report = temp_path / "report.json"
            blinding_key = temp_path / "blinding.key"
            self.write_protocol(protocol, synthetic=True)
            self.write_participants(participants)
            self.write_blinding_key(blinding_key)
            self.run_cli(
                "allocate",
                str(protocol),
                str(participants),
                str(allocation),
                str(blind),
                "--task-bank",
                str(self.task_bank_for(protocol)),
                "--blinding-key",
                str(blinding_key),
            )
            assigned = [
                json.loads(line) for line in allocation.read_text().splitlines()
            ]

            score_rows: list[dict[str, object]] = []
            for index, row in enumerate(assigned):
                if index == 0:
                    continue  # one assigned learner has no outcome: attrition
                base = {"active-control": 0.45, "teach": 0.60, "prax-teach-v2": 0.75}[
                    row["arm"]
                ]
                day = int(row["instruction_at"][8:10]) + 8
                for outcome, offset in (
                    ("delayed_retention", 0.0),
                    ("novel_transfer", -0.05),
                ):
                    score_rows.append(
                        {
                            "score_schema_version": 1,
                            "assessment_id": row["assessment_id"],
                            "outcome": outcome,
                            "task_id": (
                                "retention-1"
                                if outcome == "delayed_retention"
                                else "transfer-1"
                            ),
                            "rubric_ref": (
                                "rubric-retention-v1"
                                if outcome == "delayed_retention"
                                else "rubric-transfer-v1"
                            ),
                            "score": base + offset,
                            "measured_at": f"2026-08-{day:02d}T10:00:00Z",
                            "blinded_scorer_id": "scorer-1",
                        }
                    )
            # A unique out-of-window score is counted but excluded.
            score_rows.append(
                {
                    "score_schema_version": 1,
                    "assessment_id": assigned[0]["assessment_id"],
                    "outcome": "delayed_retention",
                    "task_id": "retention-1",
                    "rubric_ref": "rubric-retention-v1",
                    "score": 1.0,
                    "measured_at": "2026-08-03T10:00:00Z",
                    "blinded_scorer_id": "scorer-1",
                }
            )
            scores.write_text("".join(json.dumps(row) + "\n" for row in score_rows))

            self.run_cli(
                "analyze",
                str(protocol),
                str(allocation),
                str(scores),
                str(report),
                "--participants",
                str(participants),
                "--task-bank",
                str(self.task_bank_for(protocol)),
                "--blinding-key",
                str(blinding_key),
            )
            payload = json.loads(report.read_text())
            self.assertEqual(payload["claim_status"], "synthetic_machinery_test_only")
            self.assertFalse(payload["supports_human_learning_claim"])
            self.assertEqual(payload["fidelity"]["out_of_window_scores"], 1)
            self.assertGreater(payload["attrition"]["overall_rate"], 0)
            self.assertIn("prax-teach-v2_vs_active-control", payload["comparisons"])
            self.assertIn("prax-teach-v2_vs_teach", payload["comparisons"])
            self.assertEqual(payload["analysis_unit"], "assigned_learner")
            for comparison_name, comparison in payload["comparisons"].items():
                aggregate = comparison["descriptive_aggregate"]
                # One bootstrap observation per learner, never two correlated
                # outcomes flattened into pseudo-independent samples.
                self.assertIn(
                    "assigned learner", comparison["descriptive_aggregate_method"]
                )
                comparison_arm = comparison_name.removeprefix("prax-teach-v2_vs_")
                self.assertEqual(
                    aggregate["candidate_n"],
                    payload["arm_counts"]["prax-teach-v2"],
                )
                self.assertEqual(
                    aggregate["comparison_n"],
                    payload["arm_counts"][comparison_arm],
                )
                self.assertIn("complete_case_sensitivity_aggregate", comparison)
            self.assertEqual(
                payload["missing_outcome_policy"],
                "baseline_carried_forward_zero_adjusted_change",
            )
            self.assertEqual(
                payload["estimand"],
                "intention_to_treat_adjusted_score_difference",
            )
            evidence = payload["allocation_evidence"]
            self.assertEqual(evidence["authority"], "external_blinding_key_hmac_sha256")
            self.assertEqual(evidence["allocation_count"], len(assigned))
            self.assertTrue(
                evidence["allocation_set_hmac_sha256"].startswith("hmac-sha256:")
            )
            self.assertEqual(
                evidence["task_bank_sha256"],
                hashlib.sha256(self.task_bank_for(protocol).read_bytes()).hexdigest(),
            )
            score_evidence = payload["score_import_evidence"]
            self.assertEqual(score_evidence["score_schema"]["version"], 1)
            self.assertEqual(
                score_evidence["score_schema"]["id"],
                "https://prax.local/prax-teach-v2/study-score.schema.json",
            )
            self.assertEqual(
                score_evidence["score_schema"]["sha256"],
                hashlib.sha256(
                    (ROOT / "schemas" / "study-score.schema.json").read_bytes()
                ).hexdigest(),
            )

            permuted_scores = temp_path / "scores-permuted.jsonl"
            permuted_scores.write_text(
                "".join(json.dumps(row) + "\n" for row in reversed(score_rows)),
                encoding="utf-8",
            )
            permuted_report = temp_path / "report-permuted.json"
            self.run_cli(
                "analyze",
                str(protocol),
                str(allocation),
                str(permuted_scores),
                str(permuted_report),
                "--participants",
                str(participants),
                "--task-bank",
                str(self.task_bank_for(protocol)),
                "--blinding-key",
                str(blinding_key),
            )
            permuted_payload = json.loads(permuted_report.read_text())
            for field in ("comparisons", "attrition", "arm_counts", "fidelity"):
                self.assertEqual(payload[field], permuted_payload[field])
            self.assertEqual(
                payload["score_import_evidence"]["validated_scores_sha256"],
                permuted_payload["score_import_evidence"]["validated_scores_sha256"],
            )
            self.assertNotEqual(
                payload["score_import_evidence"]["source_sha256"],
                permuted_payload["score_import_evidence"]["source_sha256"],
            )

            identical_scores = temp_path / "scores-identical-duplicate.jsonl"
            identical_rows = [*score_rows, dict(score_rows[0])]
            identical_scores.write_text(
                "".join(json.dumps(row) + "\n" for row in identical_rows),
                encoding="utf-8",
            )
            identical_report = temp_path / "report-identical-duplicate.json"
            self.run_cli(
                "analyze",
                str(protocol),
                str(allocation),
                str(identical_scores),
                str(identical_report),
                "--participants",
                str(participants),
                "--task-bank",
                str(self.task_bank_for(protocol)),
                "--blinding-key",
                str(blinding_key),
            )
            identical_payload = json.loads(identical_report.read_text())
            self.assertEqual(identical_payload["fidelity"]["duplicate_scores"], 1)
            self.assertEqual(payload["comparisons"], identical_payload["comparisons"])
            self.assertEqual(
                payload["score_import_evidence"]["validated_scores_sha256"],
                identical_payload["score_import_evidence"]["validated_scores_sha256"],
            )

            conflicting_scores = temp_path / "scores-conflicting.jsonl"
            conflict = dict(score_rows[0])
            conflict["score"] = 0.01 if conflict["score"] != 0.01 else 0.99
            conflicting_scores.write_text(
                "".join(json.dumps(row) + "\n" for row in [*score_rows, conflict]),
                encoding="utf-8",
            )
            conflicting_report = temp_path / "must-not-exist-conflict-report.json"
            conflict_result = self.run_cli(
                "analyze",
                str(protocol),
                str(allocation),
                str(conflicting_scores),
                str(conflicting_report),
                "--participants",
                str(participants),
                "--task-bank",
                str(self.task_bank_for(protocol)),
                "--blinding-key",
                str(blinding_key),
                expected=2,
            )
            self.assertIn("conflicting duplicate score", conflict_result.stderr)
            self.assertFalse(conflicting_report.exists())

    def test_analysis_rejects_forged_allocations_roster_key_and_task_bank(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            protocol = temp_path / "protocol.json"
            participants = temp_path / "participants.jsonl"
            allocation = temp_path / "allocation.jsonl"
            blind = temp_path / "blind.jsonl"
            scores = temp_path / "scores.jsonl"
            blinding_key = temp_path / "blinding.key"
            self.write_protocol(protocol)
            self.write_participants(participants)
            self.write_blinding_key(blinding_key)
            self.run_cli(
                "allocate",
                str(protocol),
                str(participants),
                str(allocation),
                str(blind),
                "--task-bank",
                str(self.task_bank_for(protocol)),
                "--blinding-key",
                str(blinding_key),
            )
            scores.write_bytes(b"")
            authentic_rows = [
                json.loads(line) for line in allocation.read_text().splitlines()
            ]

            for label, mutate in (
                (
                    "arm",
                    lambda rows: rows[0].__setitem__(
                        "arm",
                        "teach" if rows[0]["arm"] != "teach" else "active-control",
                    ),
                ),
                (
                    "pretest",
                    lambda rows: rows[0].__setitem__("pretest", 0.99),
                ),
                (
                    "instruction timestamp",
                    lambda rows: rows[0].__setitem__(
                        "instruction_at", "2026-08-05T10:00:00Z"
                    ),
                ),
                ("allocation deletion", lambda rows: rows.pop()),
            ):
                with self.subTest(forgery=label):
                    forged_rows = [dict(row) for row in authentic_rows]
                    mutate(forged_rows)
                    forged = temp_path / f"forged-{label.replace(' ', '-')}.jsonl"
                    forged.write_text(
                        "".join(json.dumps(row) + "\n" for row in forged_rows),
                        encoding="utf-8",
                    )
                    output = temp_path / f"forged-{label.replace(' ', '-')}.json"
                    rejected = self.run_cli(
                        "analyze",
                        str(protocol),
                        str(forged),
                        str(scores),
                        str(output),
                        "--participants",
                        str(participants),
                        "--task-bank",
                        str(self.task_bank_for(protocol)),
                        "--blinding-key",
                        str(blinding_key),
                        expected=2,
                    )
                    self.assertIn("allocation authentication failed", rejected.stderr)
                    self.assertFalse(output.exists())

            wrong_key = temp_path / "wrong-blinding.key"
            self.write_blinding_key(wrong_key, marker=71)
            wrong_key_output = temp_path / "wrong-key-report.json"
            wrong_key_result = self.run_cli(
                "analyze",
                str(protocol),
                str(allocation),
                str(scores),
                str(wrong_key_output),
                "--participants",
                str(participants),
                "--task-bank",
                str(self.task_bank_for(protocol)),
                "--blinding-key",
                str(wrong_key),
                expected=2,
            )
            self.assertIn("allocation authentication failed", wrong_key_result.stderr)
            self.assertFalse(wrong_key_output.exists())

            altered_participants = temp_path / "altered-participants.jsonl"
            participant_rows = [
                json.loads(line) for line in participants.read_text().splitlines()
            ]
            participant_rows[0]["pretest"] = 0.88
            altered_participants.write_text(
                "".join(json.dumps(row) + "\n" for row in participant_rows),
                encoding="utf-8",
            )
            altered_roster_output = temp_path / "altered-roster-report.json"
            altered_roster_result = self.run_cli(
                "analyze",
                str(protocol),
                str(allocation),
                str(scores),
                str(altered_roster_output),
                "--participants",
                str(altered_participants),
                "--task-bank",
                str(self.task_bank_for(protocol)),
                "--blinding-key",
                str(blinding_key),
                expected=2,
            )
            self.assertIn(
                "allocation authentication failed", altered_roster_result.stderr
            )
            self.assertFalse(altered_roster_output.exists())

            forged_task_bank = temp_path / "forged-task-bank.json"
            forged_task_payload = json.loads(
                self.task_bank_for(protocol).read_text(encoding="utf-8")
            )
            forged_task_payload["tasks"][0]["prompt"] = "Substituted hidden item."
            forged_task_bank.write_text(
                json.dumps(forged_task_payload, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            forged_bank_output = temp_path / "forged-bank-report.json"
            forged_bank_result = self.run_cli(
                "analyze",
                str(protocol),
                str(allocation),
                str(scores),
                str(forged_bank_output),
                "--participants",
                str(participants),
                "--task-bank",
                str(forged_task_bank),
                "--blinding-key",
                str(blinding_key),
                expected=2,
            )
            self.assertIn("task bank digest does not match", forged_bank_result.stderr)
            self.assertFalse(forged_bank_output.exists())

            forged_protocol = temp_path / "forged-protocol.json"
            forged_protocol_payload = json.loads(protocol.read_text())
            forged_protocol_payload["task_bank_hash"] = (
                "sha256:" + hashlib.sha256(forged_task_bank.read_bytes()).hexdigest()
            )
            forged_protocol.write_text(
                json.dumps(forged_protocol_payload), encoding="utf-8"
            )
            forged_protocol_output = temp_path / "forged-protocol-report.json"
            forged_protocol_result = self.run_cli(
                "analyze",
                str(forged_protocol),
                str(allocation),
                str(scores),
                str(forged_protocol_output),
                "--participants",
                str(participants),
                "--task-bank",
                str(forged_task_bank),
                "--blinding-key",
                str(blinding_key),
                expected=2,
            )
            self.assertIn(
                "allocation authentication failed", forged_protocol_result.stderr
            )
            self.assertFalse(forged_protocol_output.exists())

    def test_score_schema_task_and_rubric_bindings_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            protocol = temp_path / "protocol.json"
            participants = temp_path / "participants.jsonl"
            allocation = temp_path / "allocation.jsonl"
            blind = temp_path / "blind.jsonl"
            scores = temp_path / "scores.jsonl"
            key = temp_path / "blinding.key"
            self.write_protocol(protocol)
            self.write_participants(participants)
            self.write_blinding_key(key)
            self.run_cli(
                "allocate",
                str(protocol),
                str(participants),
                str(allocation),
                str(blind),
                "--task-bank",
                str(self.task_bank_for(protocol)),
                "--blinding-key",
                str(key),
            )
            assigned = json.loads(allocation.read_text().splitlines()[0])
            instruction_day = int(assigned["instruction_at"][8:10])
            valid = {
                "score_schema_version": 1,
                "assessment_id": assigned["assessment_id"],
                "outcome": "delayed_retention",
                "task_id": "retention-1",
                "rubric_ref": "rubric-retention-v1",
                "score": 0.75,
                "measured_at": f"2026-08-{instruction_day + 8:02d}T10:00:00Z",
                "blinded_scorer_id": "scorer-1",
            }

            def change(field: str, value: object) -> bytes:
                row = {**valid, field: value}
                return (json.dumps(row) + "\n").encode("utf-8")

            extra = {**valid, "grader_note": "not part of the frozen contract"}
            duplicate_key = (
                (json.dumps(valid) + "\n")
                .encode("utf-8")
                .replace(
                    b'"score_schema_version": 1,',
                    b'"score_schema_version": 1, "score_schema_version": 1,',
                    1,
                )
            )
            for label, payload, expected_text in (
                ("schema-version", change("score_schema_version", 2), "unsupported"),
                ("unknown-task", change("task_id", "unknown"), "unknown task_id"),
                (
                    "wrong-rubric",
                    change("rubric_ref", "rubric-transfer-v1"),
                    "rubric_ref does not match",
                ),
                (
                    "extra-field",
                    (json.dumps(extra) + "\n").encode("utf-8"),
                    "must contain exactly",
                ),
                ("duplicate-json-key", duplicate_key, "duplicate JSON key"),
            ):
                with self.subTest(score=label):
                    scores.write_bytes(payload)
                    report = temp_path / f"must-not-exist-{label}.json"
                    rejected = self.run_cli(
                        "analyze",
                        str(protocol),
                        str(allocation),
                        str(scores),
                        str(report),
                        "--participants",
                        str(participants),
                        "--task-bank",
                        str(self.task_bank_for(protocol)),
                        "--blinding-key",
                        str(key),
                        expected=2,
                    )
                    self.assertIn(expected_text, rejected.stderr)
                    self.assertFalse(report.exists())

    def test_invalid_design_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            protocol = Path(temp) / "protocol.json"
            self.write_protocol(protocol)
            payload = json.loads(protocol.read_text())
            payload["design"] = "crossover"
            protocol.write_text(json.dumps(payload))
            completed = self.run_cli("validate", str(protocol), expected=1)
            result = json.loads(completed.stdout)
            self.assertFalse(result["valid"])
            self.assertTrue(
                any("parallel_randomized" in item for item in result["errors"])
            )

    def test_protocol_rejects_additional_properties_at_every_object_level(
        self,
    ) -> None:
        for label, mutate in (
            (
                "top-level",
                lambda payload: payload.__setitem__("unregistered_analysis", True),
            ),
            (
                "nested-delay-window",
                lambda payload: payload["delay_window_days"].__setitem__(
                    "grace_period", 1
                ),
            ),
        ):
            with self.subTest(level=label), tempfile.TemporaryDirectory() as temp:
                protocol = Path(temp) / "protocol.json"
                self.write_protocol(protocol)
                payload = json.loads(protocol.read_text())
                mutate(payload)
                protocol.write_text(json.dumps(payload), encoding="utf-8")
                completed = self.run_cli("validate", str(protocol), expected=1)
                result = json.loads(completed.stdout)
                self.assertFalse(result["valid"])
                self.assertTrue(
                    any("additional properties" in item for item in result["errors"])
                )

    def test_task_bank_schema_and_required_outcome_coverage_fail_closed(self) -> None:
        def empty_tasks(payload: dict[str, object]) -> None:
            payload["tasks"] = []

        def duplicate_id(payload: dict[str, object]) -> None:
            tasks = payload["tasks"]
            assert isinstance(tasks, list)
            tasks[1]["id"] = tasks[0]["id"]

        def missing_outcome(payload: dict[str, object]) -> None:
            tasks = payload["tasks"]
            assert isinstance(tasks, list)
            payload["tasks"] = [tasks[0]]

        def missing_prompt(payload: dict[str, object]) -> None:
            tasks = payload["tasks"]
            assert isinstance(tasks, list)
            del tasks[0]["prompt"]

        def empty_rubric(payload: dict[str, object]) -> None:
            tasks = payload["tasks"]
            assert isinstance(tasks, list)
            tasks[0]["rubric_ref"] = ""

        def extra_task_property(payload: dict[str, object]) -> None:
            tasks = payload["tasks"]
            assert isinstance(tasks, list)
            tasks[0]["answer"] = "must remain hidden"

        for label, mutate, expected_text in (
            ("empty", empty_tasks, "non-empty"),
            ("duplicate-id", duplicate_id, "duplicate task id"),
            ("missing-outcome", missing_outcome, "missing required"),
            ("missing-prompt", missing_prompt, "contain exactly"),
            ("empty-rubric", empty_rubric, "rubric_ref must be a non-empty"),
            ("extra-property", extra_task_property, "contain exactly"),
        ):
            with self.subTest(task_bank=label), tempfile.TemporaryDirectory() as temp:
                temp_path = Path(temp)
                protocol = temp_path / "protocol.json"
                participants = temp_path / "participants.jsonl"
                allocation = temp_path / "allocation.jsonl"
                blind = temp_path / "blind.jsonl"
                key = temp_path / "blinding.key"
                self.write_protocol(protocol)
                self.write_participants(participants)
                self.write_blinding_key(key)
                task_bank = self.task_bank_for(protocol)
                task_payload = json.loads(task_bank.read_text())
                mutate(task_payload)
                task_bank.write_text(
                    json.dumps(task_payload, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                protocol_payload = json.loads(protocol.read_text())
                protocol_payload["task_bank_hash"] = (
                    "sha256:" + hashlib.sha256(task_bank.read_bytes()).hexdigest()
                )
                protocol.write_text(json.dumps(protocol_payload), encoding="utf-8")
                rejected = self.run_cli(
                    "allocate",
                    str(protocol),
                    str(participants),
                    str(allocation),
                    str(blind),
                    "--task-bank",
                    str(task_bank),
                    "--blinding-key",
                    str(key),
                    expected=2,
                )
                self.assertIn(expected_text, rejected.stderr)
                self.assertFalse(allocation.exists())
                self.assertFalse(blind.exists())

        for label, corrupt in (
            ("malformed-json", lambda raw: b'{"schema_version":"1"'),
            (
                "duplicate-json-key",
                lambda raw: raw.replace(
                    b'"schema_version": "1",',
                    b'"schema_version": "1", "schema_version": "1",',
                    1,
                ),
            ),
        ):
            with self.subTest(task_bank=label), tempfile.TemporaryDirectory() as temp:
                temp_path = Path(temp)
                protocol = temp_path / "protocol.json"
                participants = temp_path / "participants.jsonl"
                allocation = temp_path / "allocation.jsonl"
                blind = temp_path / "blind.jsonl"
                key = temp_path / "blinding.key"
                self.write_protocol(protocol)
                self.write_participants(participants)
                self.write_blinding_key(key)
                task_bank = self.task_bank_for(protocol)
                task_bank.write_bytes(corrupt(task_bank.read_bytes()))
                protocol_payload = json.loads(protocol.read_text())
                protocol_payload["task_bank_hash"] = (
                    "sha256:" + hashlib.sha256(task_bank.read_bytes()).hexdigest()
                )
                protocol.write_text(json.dumps(protocol_payload), encoding="utf-8")
                rejected = self.run_cli(
                    "allocate",
                    str(protocol),
                    str(participants),
                    str(allocation),
                    str(blind),
                    "--task-bank",
                    str(task_bank),
                    "--blinding-key",
                    str(key),
                    expected=2,
                )
                self.assertIn("strict UTF-8 JSON", rejected.stderr)
                self.assertFalse(allocation.exists())
                self.assertFalse(blind.exists())

    def test_allocate_rejects_output_collisions_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            protocol = temp_path / "protocol.json"
            participants = temp_path / "participants.jsonl"
            blinding_key = temp_path / "blinding.key"
            self.write_protocol(protocol)
            self.write_participants(participants)
            self.write_blinding_key(blinding_key)

            same_output = temp_path / "same-output.jsonl"
            completed = self.run_cli(
                "allocate",
                str(protocol),
                str(participants),
                str(same_output),
                str(same_output),
                "--task-bank",
                str(self.task_bank_for(protocol)),
                "--blinding-key",
                str(blinding_key),
                expected=2,
            )
            self.assertIn("output paths", completed.stderr)
            self.assertFalse(same_output.exists())

            original_protocol = protocol.read_bytes()
            blind_output = temp_path / "blind.jsonl"
            completed = self.run_cli(
                "allocate",
                str(protocol),
                str(participants),
                str(protocol),
                str(blind_output),
                "--task-bank",
                str(self.task_bank_for(protocol)),
                "--blinding-key",
                str(blinding_key),
                expected=2,
            )
            self.assertIn("overwrite input", completed.stderr)
            self.assertEqual(protocol.read_bytes(), original_protocol)
            self.assertFalse(blind_output.exists())

            private_alias = temp_path / "private-alias.jsonl"
            blind_alias = temp_path / "blind-alias.jsonl"
            private_alias.write_bytes(b"do-not-overwrite\n")
            os.link(private_alias, blind_alias)
            completed = self.run_cli(
                "allocate",
                str(protocol),
                str(participants),
                str(private_alias),
                str(blind_alias),
                "--task-bank",
                str(self.task_bank_for(protocol)),
                "--blinding-key",
                str(blinding_key),
                expected=2,
            )
            self.assertIn("output paths", completed.stderr)
            self.assertEqual(private_alias.read_bytes(), b"do-not-overwrite\n")
            self.assertEqual(blind_alias.read_bytes(), b"do-not-overwrite\n")

    @unittest.skipUnless(os.name == "posix", "POSIX private-key permission contract")
    def test_blinding_key_rejects_public_mode_and_unsafe_or_symlinked_ancestor(
        self,
    ) -> None:
        for label in ("public-mode", "writable-ancestor", "symlinked-ancestor"):
            with self.subTest(boundary=label), tempfile.TemporaryDirectory() as temp:
                temp_path = Path(temp)
                protocol = temp_path / "protocol.json"
                participants = temp_path / "participants.jsonl"
                allocation = temp_path / "allocation.jsonl"
                blind = temp_path / "blind.jsonl"
                self.write_protocol(protocol)
                self.write_participants(participants)

                if label == "public-mode":
                    key = temp_path / "blinding.key"
                    self.write_blinding_key(key)
                    key.chmod(0o644)
                elif label == "writable-ancestor":
                    unsafe = temp_path / "unsafe"
                    unsafe.mkdir(mode=0o700)
                    key = unsafe / "blinding.key"
                    self.write_blinding_key(key)
                    unsafe.chmod(0o777)
                else:
                    real = temp_path / "real"
                    real.mkdir(mode=0o700)
                    real_key = real / "blinding.key"
                    self.write_blinding_key(real_key)
                    alias = temp_path / "alias"
                    alias.symlink_to(real, target_is_directory=True)
                    key = alias / "blinding.key"

                rejected = self.run_cli(
                    "allocate",
                    str(protocol),
                    str(participants),
                    str(allocation),
                    str(blind),
                    "--task-bank",
                    str(self.task_bank_for(protocol)),
                    "--blinding-key",
                    str(key),
                    expected=2,
                )
                self.assertIn("blinding key", rejected.stderr)
                self.assertFalse(allocation.exists())
                self.assertFalse(blind.exists())

    def test_analyze_rejects_output_input_alias_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            protocol = temp_path / "protocol.json"
            participants = temp_path / "participants.jsonl"
            allocation = temp_path / "allocation.jsonl"
            blind = temp_path / "blind.jsonl"
            scores = temp_path / "scores.jsonl"
            blinding_key = temp_path / "blinding.key"
            self.write_protocol(protocol)
            self.write_participants(participants)
            self.write_blinding_key(blinding_key)
            self.run_cli(
                "allocate",
                str(protocol),
                str(participants),
                str(allocation),
                str(blind),
                "--task-bank",
                str(self.task_bank_for(protocol)),
                "--blinding-key",
                str(blinding_key),
            )
            scores.write_bytes(b"")

            completed = self.run_cli(
                "analyze",
                str(protocol),
                str(allocation),
                str(scores),
                str(scores),
                "--participants",
                str(participants),
                "--task-bank",
                str(self.task_bank_for(protocol)),
                "--blinding-key",
                str(blinding_key),
                expected=2,
            )
            self.assertIn("overwrite input", completed.stderr)
            self.assertEqual(scores.read_bytes(), b"")

    @unittest.skipUnless(
        os.name == "posix" and hasattr(os, "symlink"),
        "descriptor-relative POSIX study publication regression",
    )
    def test_analyze_parent_swap_cannot_redirect_report_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp).resolve()
            protocol = temp_path / "protocol.json"
            participants = temp_path / "participants.jsonl"
            allocation = temp_path / "allocation.jsonl"
            blind = temp_path / "blind.jsonl"
            scores = temp_path / "scores.jsonl"
            key = temp_path / "blinding.key"
            self.write_protocol(protocol)
            self.write_participants(participants)
            self.write_blinding_key(key)
            self.run_cli(
                "allocate",
                str(protocol),
                str(participants),
                str(allocation),
                str(blind),
                "--task-bank",
                str(self.task_bank_for(protocol)),
                "--blinding-key",
                str(key),
            )
            scores.write_bytes(b"")

            output_parent = temp_path / "reports"
            output_parent.mkdir(mode=0o700)
            displaced_parent = temp_path / "reports-displaced"
            protected = temp_path / "protected"
            protected.mkdir(mode=0o700)
            sentinel = protected / "report.json"
            sentinel.write_bytes(b"must-not-change\n")
            output = output_parent / "report.json"
            original_publish = study_module.atomic_write_anchored

            def swap_parent_then_publish(*args, **kwargs):
                output_parent.rename(displaced_parent)
                output_parent.symlink_to(protected, target_is_directory=True)
                return original_publish(*args, **kwargs)

            with mock.patch.object(
                study_module,
                "atomic_write_anchored",
                side_effect=swap_parent_then_publish,
            ):
                result = study_module.main(
                    [
                        "analyze",
                        str(protocol),
                        str(allocation),
                        str(scores),
                        str(output),
                        "--participants",
                        str(participants),
                        "--task-bank",
                        str(self.task_bank_for(protocol)),
                        "--blinding-key",
                        str(key),
                    ]
                )

            self.assertEqual(result, 2)
            self.assertEqual(sentinel.read_bytes(), b"must-not-change\n")
            self.assertTrue(output_parent.is_symlink())
            self.assertFalse((displaced_parent / "report.json").exists())

    def test_delay_window_rejects_non_finite_json_constants(self) -> None:
        replacements = {
            "minimum NaN": ('"minimum": 7', '"minimum": NaN'),
            "minimum negative infinity": ('"minimum": 7', '"minimum": -Infinity'),
            "maximum infinity": ('"maximum": 14', '"maximum": Infinity'),
        }
        for label, (original, replacement) in replacements.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp:
                protocol = Path(temp) / "protocol.json"
                self.write_protocol(protocol)
                protocol.write_text(
                    protocol.read_text(encoding="utf-8").replace(original, replacement),
                    encoding="utf-8",
                )
                completed = self.run_cli("validate", str(protocol), expected=2)
                self.assertIn("non-finite", completed.stderr)


if __name__ == "__main__":
    unittest.main()
