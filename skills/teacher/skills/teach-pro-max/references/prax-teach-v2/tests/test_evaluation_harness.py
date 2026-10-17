#!/usr/bin/env python3
"""Black-box tests for claim-bounded skill-evaluation machinery."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "evaluate.py"
AGENT = ROOT / "fixtures" / "evaluation" / "fixture_agent.py"
SYSTEM_SANDBOX_PYTHON = Path(
    "/Applications/Xcode.app/Contents/Developer/Library/Frameworks/"
    "Python3.framework/Versions/3.9/bin/python3.9"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package_manifest(root: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for path in sorted(
        root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()
    ):
        if path.is_dir():
            continue
        relative = path.relative_to(root).as_posix()
        entries.append(
            {
                "path": relative,
                "sha256": sha256(path),
                "size": path.stat().st_size,
                "executable": bool(path.stat().st_mode & 0o111),
            }
        )
    return entries


def package_sha256(manifest: list[dict[str, object]]) -> str:
    encoded = (
        json.dumps(manifest, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class EvaluationHarnessTest(unittest.TestCase):
    maxDiff = None

    def run_cli(
        self, *args: str, expected: int = 0
    ) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            env={
                **os.environ,
                "SOURCE_DATE_EPOCH": "1785844800",
                "PRAX_EVAL_FIXED_DURATION_MS": "7",
            },
        )
        self.assertEqual(
            completed.returncode,
            expected,
            msg=f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )
        return completed

    def write_experiment(
        self, base: Path, cases: list[dict[str, str]]
    ) -> tuple[Path, Path, Path]:
        skill = base / "target-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text(
            "---\nname: target-skill\ndescription: Test target.\n---\n\n# Test target\n",
            encoding="utf-8",
        )
        (skill / "references").mkdir()
        (skill / "references" / "protocol.md").write_text(
            "Complete-package reference marker.\n", encoding="utf-8"
        )
        (skill / "scripts").mkdir()
        helper = skill / "scripts" / "helper.py"
        helper.write_text("#!/usr/bin/env python3\nVALUE = 1\n", encoding="utf-8")
        helper.chmod(0o755)
        manifest = package_manifest(skill)
        spec = {
            "schema_version": 1,
            "experiment_id": "public-machinery-smoke",
            "eligibility": "public_development_only",
            "target_skill": {
                "name": "target-skill",
                "path": str(skill),
                "package_sha256": package_sha256(manifest),
                "manifest": manifest,
            },
            "design": {
                "bootstrap_samples": 400,
                "minimum_effect": 0.1,
                "seed": 37,
                "trials_per_arm": 2,
            },
            "conditions": {
                "harness": "fixture-agent-v1",
                "model": "deterministic-fixture",
                "network": "unrestricted_unverified",
            },
            "cases": cases,
        }
        spec_path = base / "experiment.json"
        spec_path.write_text(json.dumps(spec), encoding="utf-8")
        hidden = {
            "schema_version": 1,
            "experiment_id": "public-machinery-smoke",
            "eligibility": "public_development_grader",
            "cases": [
                {
                    "id": case["id"],
                    "private_reference": f"NEVER_EXPOSE_{case['id']}",
                    "required_terms": (
                        ["compared", "attempt", "rule"]
                        if case["kind"] == "positive"
                        else ["concise", "direct"]
                    ),
                    "forbidden_terms": ["NEVER_EXPOSE_"],
                }
                for case in cases
            ],
        }
        hidden_path = base / "external-hidden-bank.json"
        hidden_path.write_text(json.dumps(hidden), encoding="utf-8")
        return spec_path, hidden_path, skill

    def test_plan_run_and_report_are_claim_bounded_paired_and_reproducible(
        self,
    ) -> None:
        cases = [
            {
                "id": "positive-1",
                "kind": "positive",
                "prompt": "[POSITIVE] Teach a contrastive transfer strategy.",
            },
            {
                "id": "negative-1",
                "kind": "negative",
                "prompt": "Give a concise direct definition.",
            },
        ]
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            spec, hidden, _ = self.write_experiment(base, cases)
            matrices: list[bytes] = []
            for name in ("matrix-one.jsonl", "matrix-two.jsonl"):
                output = base / name
                self.run_cli("plan", str(spec), "--output", str(output))
                matrices.append(output.read_bytes())
            self.assertEqual(matrices[0], matrices[1])
            rows = [json.loads(line) for line in matrices[0].decode().splitlines()]
            self.assertEqual(len(rows), 8)
            self.assertEqual({row["arm"] for row in rows}, {"control", "treatment"})
            self.assertEqual(len({row["run_id"] for row in rows}), 8)

            output = base / "run-output"
            runner_json = json.dumps([sys.executable, str(AGENT)])
            self.run_cli(
                "run",
                str(spec),
                str(base / "matrix-one.jsonl"),
                "--hidden-bank",
                str(hidden),
                "--runner-json",
                runner_json,
                "--output-dir",
                str(output),
                "--public-fixture-unconfined",
            )
            result_rows = [
                json.loads(line)
                for line in (output / "results.jsonl").read_text().splitlines()
            ]
            self.assertEqual(len(result_rows), 8)
            self.assertTrue(all(row["condition_sha256"] for row in result_rows))
            self.assertTrue(all(row["duration_ms"] == 7 for row in result_rows))
            self.assertTrue(all(row["hard_gates_passed"] for row in result_rows))
            self.assertTrue(all(row["workspace_removed"] for row in result_rows))
            self.assertTrue(
                all(
                    row["isolation_level"] == "unconfined_public_fixture"
                    for row in result_rows
                )
            )
            self.assertTrue(
                all(
                    row["hidden_bank_nonexposure_verified"] is False
                    and row["network_isolation_verified"] is False
                    and row["eligible_for_held_out_claims"] is False
                    and row["isolation_contract_sha256"] is None
                    for row in result_rows
                )
            )
            self.assertEqual(
                sum(
                    row["success"]
                    for row in result_rows
                    if row["case_id"] == "positive-1" and row["arm"] == "treatment"
                ),
                2,
            )
            self.assertEqual(
                sum(
                    row["success"]
                    for row in result_rows
                    if row["case_id"] == "positive-1" and row["arm"] == "control"
                ),
                0,
            )
            visible_receipts = "\n".join(
                path.read_text(encoding="utf-8")
                for path in output.rglob("*")
                if path.is_file()
            )
            self.assertNotIn("NEVER_EXPOSE_", visible_receipts)
            self.assertNotIn(str(hidden), visible_receipts)

            archive_report_path = output / "report.json"
            archive_report = json.loads(archive_report_path.read_text())
            archive_manifest = json.loads((output / "manifest.json").read_text())
            receipt_index = sorted(
                (
                    {
                        "run_id": receipt.stem,
                        "sha256": sha256(receipt),
                    }
                    for receipt in (output / "receipts").glob("*.json")
                ),
                key=lambda item: item["run_id"],
            )
            receipt_set_bytes = (
                json.dumps(
                    receipt_index,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                + "\n"
            ).encode("utf-8")
            self.assertEqual(
                archive_report["evidence_binding"]["authority"],
                "package_owned_same_run",
            )
            self.assertEqual(
                archive_manifest["evidence_binding"],
                archive_report["evidence_binding"],
            )
            self.assertEqual(
                archive_manifest["report_sha256"], sha256(archive_report_path)
            )
            self.assertEqual(
                archive_manifest["receipt_set_sha256"],
                hashlib.sha256(receipt_set_bytes).hexdigest(),
            )
            self.assertEqual(archive_manifest["receipt_count"], len(result_rows))

            report_path = base / "report.json"
            completed = self.run_cli(
                "report",
                str(spec),
                str(output / "results.jsonl"),
                "--output",
                str(report_path),
            )
            report = json.loads(completed.stdout)
            self.assertEqual(report, json.loads(report_path.read_text()))
            self.assertEqual(
                report["evidence_level"], "evaluated_public_machinery_fixture"
            )
            self.assertFalse(report["eligible_for_held_out_claims"])
            self.assertFalse(report["hidden_bank_nonexposure_verified"])
            self.assertFalse(report["supports_human_learning_claim"])
            self.assertEqual(
                report["evidence_binding"]["authority"],
                "standalone_untrusted_results",
            )
            self.assertEqual(report["isolation_levels"], ["unconfined_public_fixture"])
            self.assertEqual(
                report["target_package_sha256"],
                json.loads(spec.read_text())["target_skill"]["package_sha256"],
            )
            self.assertIn("positive", report["strata"])
            self.assertIn("confidence_interval", report["strata"]["positive"])
            self.assertGreater(report["strata"]["positive"]["absolute_lift"], 0)

    def test_structurally_valid_forged_held_out_results_cannot_create_report(
        self,
    ) -> None:
        cases = [
            {
                "id": "forged-held-out",
                "kind": "positive",
                "prompt": "[POSITIVE] Exercise held-out report binding.",
            }
        ]
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            spec, hidden, _ = self.write_experiment(base, cases)
            public_matrix = base / "public-matrix.jsonl"
            self.run_cli("plan", str(spec), "--output", str(public_matrix))
            public_output = base / "public-output"
            self.run_cli(
                "run",
                str(spec),
                str(public_matrix),
                "--hidden-bank",
                str(hidden),
                "--runner-json",
                json.dumps([sys.executable, str(AGENT)]),
                "--output-dir",
                str(public_output),
                "--public-fixture-unconfined",
            )
            templates = [
                json.loads(line)
                for line in (public_output / "results.jsonl").read_text().splitlines()
            ]

            document = json.loads(spec.read_text())
            document["eligibility"] = "held_out_external_evaluation"
            document["conditions"]["network"] = "off"
            spec.write_text(json.dumps(document), encoding="utf-8")
            forged_matrix = base / "forged-held-out-matrix.jsonl"
            self.run_cli("plan", str(spec), "--output", str(forged_matrix))
            planned = [
                json.loads(line) for line in forged_matrix.read_text().splitlines()
            ]
            matrix_digest = sha256(forged_matrix)
            dummy_digest = "a" * 64
            forged_rows: list[dict[str, object]] = []
            for template, expected in zip(templates, planned, strict=True):
                forged = dict(template)
                forged.update(expected)
                forged.update(
                    {
                        "evaluation_scope": "candidate_quality_benchmark",
                        "matrix_sha256": matrix_digest,
                        "runner_sha256": dummy_digest,
                        "runner_runtime_closure_sha256": dummy_digest,
                        "isolation_level": "builtin_macos_sandbox_exec",
                        "isolation_contract_sha256": None,
                        "isolation_verification_authority": (
                            "builtin-macos-sandbox-exec"
                        ),
                        "isolation_verification_evidence_sha256": dummy_digest,
                        "isolation_executor_sha256": dummy_digest,
                        "isolation_profile_sha256": dummy_digest,
                        "isolation_probes_sha256": dummy_digest,
                        "isolation_probes_passed": True,
                        "hidden_bank_nonexposure_verified": True,
                        "network_isolation_verified": True,
                        "eligible_for_held_out_claims": True,
                    }
                )
                forged_rows.append(forged)
            forged_results = base / "forged-held-out-results.jsonl"
            forged_results.write_text(
                "".join(
                    json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n"
                    for row in forged_rows
                ),
                encoding="utf-8",
            )
            forged_report_path = base / "must-not-exist-report.json"
            rejected = self.run_cli(
                "report",
                str(spec),
                str(forged_results),
                "--output",
                str(forged_report_path),
                expected=2,
            )
            self.assertIn("standalone report cannot authenticate", rejected.stderr)
            self.assertIn("package-owned run command", rejected.stderr)
            self.assertFalse(forged_report_path.exists())

    def test_plan_and_report_reject_output_symlinks_and_input_aliases(self) -> None:
        cases = [
            {
                "id": "output-boundary",
                "kind": "positive",
                "prompt": "Teach the output boundary.",
            }
        ]
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            spec, hidden, skill = self.write_experiment(base, cases)
            original_spec = spec.read_bytes()

            plan_sentinel = base / "plan-sentinel.jsonl"
            plan_sentinel.write_bytes(b"do-not-overwrite-plan\n")
            plan_symlink = base / "plan-link.jsonl"
            plan_symlink.symlink_to(plan_sentinel)
            linked_plan = self.run_cli(
                "plan", str(spec), "--output", str(plan_symlink), expected=2
            )
            self.assertIn("symlink", linked_plan.stderr)
            self.assertEqual(plan_sentinel.read_bytes(), b"do-not-overwrite-plan\n")

            plan_hardlink = base / "plan-hardlink.jsonl"
            os.link(spec, plan_hardlink)
            aliased_plan = self.run_cli(
                "plan", str(spec), "--output", str(plan_hardlink), expected=2
            )
            self.assertIn("overwrite an input", aliased_plan.stderr)
            self.assertEqual(spec.read_bytes(), original_spec)

            skill_file = skill / "SKILL.md"
            original_skill = skill_file.read_bytes()
            package_hardlink = base / "package-hardlink.jsonl"
            os.link(skill_file, package_hardlink)
            package_alias = self.run_cli(
                "plan", str(spec), "--output", str(package_hardlink), expected=2
            )
            self.assertIn("overwrite an input", package_alias.stderr)
            self.assertEqual(skill_file.read_bytes(), original_skill)

            inside_skill = self.run_cli(
                "plan",
                str(spec),
                "--output",
                str(skill / "generated-plan.jsonl"),
                expected=2,
            )
            self.assertIn("input directory", inside_skill.stderr)
            self.assertFalse((skill / "generated-plan.jsonl").exists())

            matrix = base / "matrix.jsonl"
            self.run_cli("plan", str(spec), "--output", str(matrix))
            output = base / "run-output"
            self.run_cli(
                "run",
                str(spec),
                str(matrix),
                "--hidden-bank",
                str(hidden),
                "--runner-json",
                json.dumps([sys.executable, str(AGENT)]),
                "--output-dir",
                str(output),
                "--public-fixture-unconfined",
            )
            results = output / "results.jsonl"
            original_results = results.read_bytes()

            report_sentinel = base / "report-sentinel.json"
            report_sentinel.write_bytes(b"do-not-overwrite-report\n")
            report_symlink = base / "report-link.json"
            report_symlink.symlink_to(report_sentinel)
            linked_report = self.run_cli(
                "report",
                str(spec),
                str(results),
                "--output",
                str(report_symlink),
                expected=2,
            )
            self.assertIn("symlink", linked_report.stderr)
            self.assertEqual(report_sentinel.read_bytes(), b"do-not-overwrite-report\n")

            report_hardlink = base / "report-hardlink.json"
            os.link(results, report_hardlink)
            aliased_report = self.run_cli(
                "report",
                str(spec),
                str(results),
                "--output",
                str(report_hardlink),
                expected=2,
            )
            self.assertIn("overwrite an input", aliased_report.stderr)
            self.assertEqual(results.read_bytes(), original_results)

    def test_run_rejects_hardlink_and_content_aliases_across_protected_inputs(
        self,
    ) -> None:
        cases = [
            {
                "id": "cross-alias",
                "kind": "positive",
                "prompt": "Teach protected input isolation.",
            }
        ]
        for alias_kind in ("hidden-hardlink", "runner-content"):
            with (
                self.subTest(alias_kind=alias_kind),
                tempfile.TemporaryDirectory() as temp,
            ):
                base = Path(temp)
                spec, hidden, skill = self.write_experiment(base, cases)
                runner = base / "external-runner.py"
                runner.write_bytes(AGENT.read_bytes())
                if alias_kind == "hidden-hardlink":
                    os.link(hidden, skill / "references/hidden-alias.json")
                else:
                    (skill / "references/runner-copy.py").write_bytes(
                        runner.read_bytes()
                    )
                document = json.loads(spec.read_text())
                manifest = package_manifest(skill)
                document["target_skill"]["manifest"] = manifest
                document["target_skill"]["package_sha256"] = package_sha256(manifest)
                spec.write_text(json.dumps(document), encoding="utf-8")
                matrix = base / "matrix.jsonl"
                self.run_cli("plan", str(spec), "--output", str(matrix))

                rejected = self.run_cli(
                    "run",
                    str(spec),
                    str(matrix),
                    "--hidden-bank",
                    str(hidden),
                    "--runner-json",
                    json.dumps([sys.executable, str(runner)]),
                    "--output-dir",
                    str(base / "must-not-run"),
                    "--public-fixture-unconfined",
                    expected=2,
                )
                self.assertIn("alias", rejected.stderr.lower())
                self.assertFalse((base / "must-not-run").exists())

    def test_runner_identity_replacement_with_same_bytes_fails_integrity(self) -> None:
        cases = [
            {
                "id": "identity-race",
                "kind": "positive",
                "prompt": "Teach input integrity.",
            }
        ]
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            spec, hidden, _skill = self.write_experiment(base, cases)
            matrix = base / "matrix.jsonl"
            self.run_cli("plan", str(spec), "--output", str(matrix))
            runner = base / "identity-replacing-runner.py"
            runner.write_text(
                """#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

json.load(sys.stdin)
source = Path(__file__)
replacement = source.with_name(source.name + ".replacement")
replacement.write_bytes(source.read_bytes())
os.replace(replacement, source)
json.dump({"artifacts": [], "response": "compared attempt rule", "sources": [], "token_usage": {"input": 1, "output": 1}}, sys.stdout)
sys.stdout.write("\\n")
""",
                encoding="utf-8",
            )
            completed = self.run_cli(
                "run",
                str(spec),
                str(matrix),
                "--hidden-bank",
                str(hidden),
                "--runner-json",
                json.dumps([sys.executable, str(runner)]),
                "--output-dir",
                str(base / "run-output"),
                "--public-fixture-unconfined",
                expected=5,
            )
            self.assertIn("integrity failure", completed.stderr.lower())
            rows = [
                json.loads(line)
                for line in (base / "run-output/results.jsonl").read_text().splitlines()
            ]
            self.assertTrue(
                all("input_integrity" in row["failed_hard_gates"] for row in rows)
            )

    def test_path_escape_and_silent_persistence_fail_closed_before_soft_score(
        self,
    ) -> None:
        cases = [
            {
                "id": "malicious-path",
                "kind": "positive",
                "prompt": "MALICIOUS_PATH_ESCAPE",
            },
            {
                "id": "malicious-persist",
                "kind": "positive",
                "prompt": "MALICIOUS_PERSIST",
            },
        ]
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            spec, hidden, _ = self.write_experiment(base, cases)
            matrix = base / "matrix.jsonl"
            self.run_cli("plan", str(spec), "--output", str(matrix))
            output = base / "run-output"
            completed = self.run_cli(
                "run",
                str(spec),
                str(matrix),
                "--hidden-bank",
                str(hidden),
                "--runner-json",
                json.dumps([sys.executable, str(AGENT)]),
                "--output-dir",
                str(output),
                "--public-fixture-unconfined",
                expected=5,
            )
            self.assertIn("integrity", completed.stderr.lower())
            rows = [
                json.loads(line)
                for line in (output / "results.jsonl").read_text().splitlines()
            ]
            self.assertTrue(
                any("artifact_path_escape" in row["failed_hard_gates"] for row in rows)
            )
            self.assertTrue(
                any("silent_persistence" in row["failed_hard_gates"] for row in rows)
            )
            for row in rows:
                if not row["hard_gates_passed"]:
                    self.assertEqual(row["soft_score"], 0.0)
                    self.assertFalse(row["success"])

    def test_hidden_bank_inside_target_or_malformed_matrix_is_rejected(self) -> None:
        cases = [
            {
                "id": "positive-1",
                "kind": "positive",
                "prompt": "[POSITIVE] Teach safely.",
            }
        ]
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            spec, hidden, skill = self.write_experiment(base, cases)
            matrix = base / "matrix.jsonl"
            self.run_cli("plan", str(spec), "--output", str(matrix))
            contaminated = skill / "hidden-bank.json"
            contaminated.write_bytes(hidden.read_bytes())
            rejected = self.run_cli(
                "run",
                str(spec),
                str(matrix),
                "--hidden-bank",
                str(contaminated),
                "--runner-json",
                json.dumps([sys.executable, str(AGENT)]),
                "--output-dir",
                str(base / "blocked"),
                "--public-fixture-unconfined",
                expected=2,
            )
            self.assertTrue(
                "grader bank" in rejected.stderr.lower()
                or "target package" in rejected.stderr.lower()
            )
            self.assertFalse((base / "blocked").exists())

            contaminated.unlink()
            matrix.write_text("{not-json}\n", encoding="utf-8")
            malformed = self.run_cli(
                "run",
                str(spec),
                str(matrix),
                "--hidden-bank",
                str(hidden),
                "--runner-json",
                json.dumps([sys.executable, str(AGENT)]),
                "--output-dir",
                str(base / "malformed"),
                "--public-fixture-unconfined",
                expected=2,
            )
            self.assertIn("matrix", malformed.stderr.lower())
            self.assertFalse((base / "malformed").exists())

    def test_default_run_refuses_without_an_explicit_isolation_boundary(self) -> None:
        cases = [
            {
                "id": "positive-1",
                "kind": "positive",
                "prompt": "[POSITIVE] Teach safely.",
            }
        ]
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            spec, hidden, _ = self.write_experiment(base, cases)
            matrix = base / "matrix.jsonl"
            self.run_cli("plan", str(spec), "--output", str(matrix))
            output = base / "must-not-exist"
            refused = self.run_cli(
                "run",
                str(spec),
                str(matrix),
                "--hidden-bank",
                str(hidden),
                "--runner-json",
                json.dumps([sys.executable, str(AGENT)]),
                "--output-dir",
                str(output),
                expected=2,
            )
            self.assertIn("--public-fixture-unconfined", refused.stderr)
            self.assertIn("--macos-sandbox", refused.stderr)
            self.assertFalse(output.exists())

    def test_complete_package_is_cloned_read_only_and_fingerprinted(self) -> None:
        cases = [
            {
                "id": "package-1",
                "kind": "positive",
                "prompt": "CHECK_COMPLETE_PACKAGE",
            }
        ]
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            spec, hidden, skill = self.write_experiment(base, cases)
            hidden_document = json.loads(hidden.read_text())
            hidden_document["cases"][0]["required_terms"] = [
                "package-complete",
                "read-only",
                "reference-marker",
            ]
            hidden.write_text(json.dumps(hidden_document), encoding="utf-8")
            agent = base / "package_agent.py"
            agent.write_text(
                """#!/usr/bin/env python3
import json, os, pathlib, sys
request = json.load(sys.stdin)
root_text = os.environ.get("PRAX_EVAL_SKILL_ROOT")
ok = False
if root_text:
    root = pathlib.Path(root_text)
    reference = root / "references" / "protocol.md"
    expected = {"SKILL.md", "references/protocol.md", "scripts/helper.py"}
    found = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    readonly = all(not (p.stat().st_mode & 0o222) for p in root.rglob("*"))
    ok = found == expected and readonly and "Complete-package" in reference.read_text()
response = "package-complete read-only reference-marker" if ok else "control"
pathlib.Path("answer.md").write_text(response)
json.dump({"artifacts":["answer.md"],"response":response,"sources":[],"token_usage":{"input":1,"output":1}}, sys.stdout)
sys.stdout.write("\\n")
""",
                encoding="utf-8",
            )
            agent.chmod(0o755)
            matrix = base / "matrix.jsonl"
            self.run_cli("plan", str(spec), "--output", str(matrix))
            output = base / "package-output"
            self.run_cli(
                "run",
                str(spec),
                str(matrix),
                "--hidden-bank",
                str(hidden),
                "--runner-json",
                json.dumps([sys.executable, str(agent)]),
                "--output-dir",
                str(output),
                "--public-fixture-unconfined",
            )
            rows = [
                json.loads(line)
                for line in (output / "results.jsonl").read_text().splitlines()
            ]
            self.assertTrue(
                all(row["success"] for row in rows if row["arm"] == "treatment")
            )
            self.assertTrue(
                all(not row["success"] for row in rows if row["arm"] == "control")
            )
            self.assertTrue(all(row["target_package_file_count"] == 3 for row in rows))
            first_runner_sha = rows[0]["runner_sha256"]
            agent.write_text(
                agent.read_text() + "\n# fingerprint change\n", encoding="utf-8"
            )
            changed_runner_output = base / "changed-runner-output"
            self.run_cli(
                "run",
                str(spec),
                str(matrix),
                "--hidden-bank",
                str(hidden),
                "--runner-json",
                json.dumps([sys.executable, str(agent)]),
                "--output-dir",
                str(changed_runner_output),
                "--public-fixture-unconfined",
            )
            changed_rows = [
                json.loads(line)
                for line in (changed_runner_output / "results.jsonl")
                .read_text()
                .splitlines()
            ]
            self.assertNotEqual(first_runner_sha, changed_rows[0]["runner_sha256"])

            original_spec = json.loads(spec.read_text())
            original_digest = original_spec["target_skill"]["package_sha256"]
            (skill / "references" / "protocol.md").write_text(
                "Changed complete-package reference marker.\n", encoding="utf-8"
            )
            stale = self.run_cli(
                "plan",
                str(spec),
                "--output",
                str(base / "stale-matrix.jsonl"),
                expected=2,
            )
            self.assertIn("package manifest", stale.stderr.lower())
            refreshed_manifest = package_manifest(skill)
            refreshed_digest = package_sha256(refreshed_manifest)
            self.assertNotEqual(original_digest, refreshed_digest)
            original_spec["target_skill"]["manifest"] = refreshed_manifest
            original_spec["target_skill"]["package_sha256"] = refreshed_digest
            spec.write_text(json.dumps(original_spec), encoding="utf-8")
            refreshed_matrix = base / "refreshed-matrix.jsonl"
            self.run_cli("plan", str(spec), "--output", str(refreshed_matrix))
            matrix_rows = [
                json.loads(line) for line in refreshed_matrix.read_text().splitlines()
            ]
            self.assertTrue(
                all(
                    row["target_package_sha256"] == refreshed_digest
                    for row in matrix_rows
                )
            )

    def test_public_fixture_mode_rejects_held_out_labels(self) -> None:
        cases = [
            {
                "id": "positive-1",
                "kind": "positive",
                "prompt": "[POSITIVE] Teach safely.",
            }
        ]
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            spec, hidden, _ = self.write_experiment(base, cases)
            document = json.loads(spec.read_text())
            document["eligibility"] = "held_out_external_evaluation"
            document["conditions"]["network"] = "off"
            spec.write_text(json.dumps(document), encoding="utf-8")
            bank = json.loads(hidden.read_text())
            bank["eligibility"] = "hidden_external_test"
            hidden.write_text(json.dumps(bank), encoding="utf-8")
            matrix = base / "matrix.jsonl"
            self.run_cli("plan", str(spec), "--output", str(matrix))
            refused = self.run_cli(
                "run",
                str(spec),
                str(matrix),
                "--hidden-bank",
                str(hidden),
                "--runner-json",
                json.dumps([sys.executable, str(AGENT)]),
                "--output-dir",
                str(base / "blocked-held-out-label"),
                "--public-fixture-unconfined",
                expected=2,
            )
            self.assertIn("rejects specs labeled as held-out", refused.stderr)

    def test_self_attested_wrapper_cannot_promote_held_out_claims(self) -> None:
        cases = [
            {
                "id": "positive-1",
                "kind": "positive",
                "prompt": "[POSITIVE] Teach safely.",
            }
        ]
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            spec, hidden, _ = self.write_experiment(base, cases)
            spec_document = json.loads(spec.read_text())
            spec_document["eligibility"] = "held_out_external_evaluation"
            spec_document["conditions"]["network"] = "off"
            spec.write_text(json.dumps(spec_document), encoding="utf-8")
            bank = json.loads(hidden.read_text())
            bank["eligibility"] = "hidden_external_test"
            hidden.write_text(json.dumps(bank), encoding="utf-8")

            contract = base / "isolation-contract.json"
            contract.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "isolation_level": "externally_verified_process_sandbox",
                        "authority": "self-asserted-and-untrusted",
                        "hidden_bank_nonexposure_verified": True,
                        "network_isolation_verified": True,
                    }
                ),
                encoding="utf-8",
            )
            matrix = base / "matrix.jsonl"
            self.run_cli("plan", str(spec), "--output", str(matrix))
            output = base / "must-not-run-held-out"
            refused = self.run_cli(
                "run",
                str(spec),
                str(matrix),
                "--hidden-bank",
                str(hidden),
                "--runner-json",
                json.dumps([sys.executable, str(AGENT)]),
                "--output-dir",
                str(output),
                "--isolation-wrapper-json",
                str(contract),
                expected=2,
            )
            self.assertIn("self-authored isolation wrapper", refused.stderr)
            self.assertIn("not implemented", refused.stderr)
            self.assertIn("parked", refused.stderr)
            self.assertFalse(output.exists())
            self.assertNotIn(
                "eligible_for_held_out_claims",
                refused.stdout,
            )

    def test_builtin_macos_sandbox_blocks_adversarial_access(self) -> None:
        if os.environ.get("PRAX_RUN_MACOS_SANDBOX_TESTS") != "1":
            self.skipTest(
                "set PRAX_RUN_MACOS_SANDBOX_TESTS=1 for the required platform gate"
            )
        cases = [
            {
                "id": "sandbox-adversary",
                "kind": "positive",
                "prompt": "Exercise the built-in sandbox boundary.",
            }
        ]
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            spec, hidden, skill = self.write_experiment(base, cases)
            document = json.loads(spec.read_text())
            document["experiment_id"] = "macos-containment-adversary"
            document["eligibility"] = "containment_mechanism_only"
            document["conditions"]["network"] = "off"
            document["design"]["trials_per_arm"] = 1
            spec.write_text(json.dumps(document), encoding="utf-8")
            bank = json.loads(hidden.read_text())
            bank["experiment_id"] = "macos-containment-adversary"
            bank["eligibility"] = "adversarial_containment_fixture"
            bank["cases"][0]["required_terms"] = [
                "hidden-blocked",
                "candidate-blocked",
                "source-blocked",
                "outside-write-blocked",
                "network-blocked",
                "package-readable",
            ]
            hidden.write_text(json.dumps(bank), encoding="utf-8")

            secret = base / "external-secret.txt"
            secret.write_text("EXTERNAL_SECRET_MUST_NOT_BE_READ\n", encoding="utf-8")
            outside_write = base / "outside-write-must-not-exist.txt"
            runner = base / "adversarial_runner.py"
            runner.write_text(
                f"""#!/usr/bin/env python3
import errno
import json
import os
from pathlib import Path
import socket
import sys

DENIED = {{errno.EACCES, errno.EPERM}}

def blocked_read(path):
    try:
        Path(path).read_bytes()
    except OSError as error:
        return error.errno in DENIED
    return False

def blocked_write(path):
    descriptor = None
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except OSError as error:
        return error.errno in DENIED
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return False

def blocked_network():
    connection = None
    try:
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection.settimeout(0.25)
        connection.connect(("127.0.0.1", 9))
    except OSError as error:
        return error.errno in DENIED
    finally:
        if connection is not None:
            connection.close()
    return False

json.load(sys.stdin)
checks = {{
    "candidate-blocked": blocked_read({json.dumps(str(ROOT / "SKILL.md"))}),
    "hidden-blocked": blocked_read({json.dumps(str(hidden))}),
    "network-blocked": blocked_network(),
    "outside-write-blocked": blocked_write({json.dumps(str(outside_write))}),
    "source-blocked": blocked_read({json.dumps(str(skill / "SKILL.md"))}),
}}
skill_root = os.environ.get("PRAX_EVAL_SKILL_ROOT")
checks["package-readable"] = bool(
    skill_root and (Path(skill_root) / "SKILL.md").read_bytes()
)
response = " ".join(key for key, passed in sorted(checks.items()) if passed)
Path("answer.md").write_text(response, encoding="utf-8")
json.dump(
    {{
        "artifacts": ["answer.md"],
        "response": response,
        "sources": [],
        "token_usage": {{"input": 1, "output": 1}},
    }},
    sys.stdout,
    separators=(",", ":"),
    sort_keys=True,
)
sys.stdout.write("\\n")
""",
                encoding="utf-8",
            )
            runner.chmod(0o755)
            runner_files = sorted(
                [SYSTEM_SANDBOX_PYTHON, runner.resolve()], key=lambda path: str(path)
            )
            runner_manifest = base / "runner-manifest.json"
            runner_manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "files": [
                            {"path": str(path), "sha256": sha256(path)}
                            for path in runner_files
                        ],
                    }
                ),
                encoding="utf-8",
            )
            matrix = base / "matrix.jsonl"
            self.run_cli("plan", str(spec), "--output", str(matrix))
            output = base / "sandbox-output"
            command = [
                sys.executable,
                str(CLI),
                "run",
                str(spec),
                str(matrix),
                "--hidden-bank",
                str(hidden),
                "--runner-json",
                json.dumps(
                    [
                        str(SYSTEM_SANDBOX_PYTHON),
                        "-I",
                        "-S",
                        str(runner.resolve()),
                    ]
                ),
                "--runner-manifest-json",
                str(runner_manifest),
                "--output-dir",
                str(output),
                "--macos-sandbox",
            ]
            completed = subprocess.run(
                command,
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
                env={
                    **os.environ,
                    "SOURCE_DATE_EPOCH": "1785844800",
                    "PRAX_EVAL_FIXED_DURATION_MS": "7",
                },
            )
            if completed.returncode == 71:
                self.skipTest(
                    "sandbox-exec cannot nest inside the current parent sandbox (exit 71)"
                )
            self.assertEqual(
                completed.returncode,
                0,
                msg=f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
            )
            self.assertFalse(outside_write.exists())
            rows = [
                json.loads(line)
                for line in (output / "results.jsonl").read_text().splitlines()
            ]
            self.assertEqual(len(rows), 2)
            self.assertTrue(all(row["hard_gates_passed"] for row in rows))
            self.assertTrue(all(row["isolation_probes_passed"] for row in rows))
            self.assertTrue(
                all(
                    row["isolation_level"] == "builtin_macos_sandbox_exec"
                    and row["hidden_bank_nonexposure_verified"]
                    and row["network_isolation_verified"]
                    and not row["eligible_for_held_out_claims"]
                    and row["evaluation_scope"] == "containment_mechanism_fixture"
                    and row["isolation_executor_sha256"]
                    and row["isolation_profile_sha256"]
                    and row["isolation_probes_sha256"]
                    for row in rows
                )
            )
            treatment = next(row for row in rows if row["arm"] == "treatment")
            self.assertTrue(treatment["success"])
            visible_receipts = "\n".join(
                path.read_text(encoding="utf-8")
                for path in output.rglob("*")
                if path.is_file()
            )
            self.assertNotIn("EXTERNAL_SECRET_MUST_NOT_BE_READ", visible_receipts)
            self.assertNotIn(str(hidden), visible_receipts)
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(
                manifest["evidence_level"],
                "evaluated_containment_mechanism_fixture",
            )
            self.assertEqual(
                manifest["evaluation_scope"], "containment_mechanism_fixture"
            )
            self.assertFalse(manifest["eligible_for_held_out_claims"])
            self.assertFalse(manifest["supports_candidate_quality_claim"])
            self.assertFalse(manifest["supports_human_learning_claim"])
            archive_report = json.loads((output / "report.json").read_text())
            self.assertEqual(
                archive_report["evidence_binding"]["authority"],
                "package_owned_same_run",
            )
            self.assertEqual(manifest["report_sha256"], sha256(output / "report.json"))
            self.assertEqual(
                manifest["evidence_binding"], archive_report["evidence_binding"]
            )

            report_path = base / "sandbox-report.json"
            self.run_cli(
                "report",
                str(spec),
                str(output / "results.jsonl"),
                "--output",
                str(report_path),
            )
            report = json.loads(report_path.read_text())
            self.assertEqual(
                report["evidence_level"],
                "evaluated_containment_mechanism_fixture",
            )
            self.assertEqual(
                report["evaluation_scope"], "containment_mechanism_fixture"
            )
            self.assertFalse(report["eligible_for_held_out_claims"])
            self.assertFalse(report["supports_candidate_quality_claim"])
            self.assertFalse(report["supports_human_learning_claim"])
            self.assertFalse(report["meets_predeclared_held_out_threshold"])
            self.assertIn("containment mechanism only", report["claim_boundary"])
            self.assertIn(
                "does not evaluate candidate quality", report["claim_boundary"]
            )

            forged_rows = [dict(row) for row in rows]
            for row in forged_rows:
                row["evaluation_scope"] = "candidate_quality_benchmark"
                row["eligible_for_held_out_claims"] = True
            forged_results = base / "forged-containment-promotion.jsonl"
            forged_results.write_text(
                "".join(
                    json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n"
                    for row in forged_rows
                ),
                encoding="utf-8",
            )
            forged_report = self.run_cli(
                "report",
                str(spec),
                str(forged_results),
                "--output",
                str(base / "forged-report.json"),
                expected=2,
            )
            self.assertIn("evaluation scope is inconsistent", forged_report.stderr)

            held_out_document = dict(document)
            held_out_document["experiment_id"] = "macos-held-out-binding"
            held_out_document["eligibility"] = "held_out_external_evaluation"
            spec.write_text(json.dumps(held_out_document), encoding="utf-8")
            held_out_bank = dict(bank)
            held_out_bank["experiment_id"] = "macos-held-out-binding"
            held_out_bank["eligibility"] = "hidden_external_test"
            hidden.write_text(json.dumps(held_out_bank), encoding="utf-8")
            held_out_matrix = base / "held-out-matrix.jsonl"
            self.run_cli("plan", str(spec), "--output", str(held_out_matrix))
            held_out_output = base / "held-out-output"
            held_out_command = [
                sys.executable,
                str(CLI),
                "run",
                str(spec),
                str(held_out_matrix),
                "--hidden-bank",
                str(hidden),
                "--runner-json",
                json.dumps(
                    [
                        str(SYSTEM_SANDBOX_PYTHON),
                        "-I",
                        "-S",
                        str(runner.resolve()),
                    ]
                ),
                "--runner-manifest-json",
                str(runner_manifest),
                "--output-dir",
                str(held_out_output),
                "--macos-sandbox",
            ]
            held_out_completed = subprocess.run(
                held_out_command,
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
                env={
                    **os.environ,
                    "SOURCE_DATE_EPOCH": "1785844800",
                    "PRAX_EVAL_FIXED_DURATION_MS": "7",
                },
            )
            self.assertEqual(
                held_out_completed.returncode,
                0,
                msg=(
                    f"stdout:\n{held_out_completed.stdout}\n"
                    f"stderr:\n{held_out_completed.stderr}"
                ),
            )
            held_out_report_path = held_out_output / "report.json"
            held_out_report = json.loads(held_out_report_path.read_text())
            held_out_manifest = json.loads(
                (held_out_output / "manifest.json").read_text()
            )
            self.assertEqual(
                held_out_report["evidence_level"],
                "evaluated_held_out_agent_benchmark",
            )
            self.assertTrue(held_out_report["eligible_for_held_out_claims"])
            self.assertTrue(held_out_report["supports_candidate_quality_claim"])
            self.assertFalse(held_out_report["supports_human_learning_claim"])
            self.assertEqual(
                held_out_report["evidence_binding"]["authority"],
                "package_owned_same_run",
            )
            self.assertEqual(
                held_out_manifest["report_sha256"], sha256(held_out_report_path)
            )
            self.assertEqual(
                held_out_manifest["evidence_binding"],
                held_out_report["evidence_binding"],
            )
            rejected_standalone_path = base / "held-out-standalone-must-not-exist.json"
            rejected_standalone = self.run_cli(
                "report",
                str(spec),
                str(held_out_output / "results.jsonl"),
                "--output",
                str(rejected_standalone_path),
                expected=2,
            )
            self.assertIn(
                "standalone report cannot authenticate", rejected_standalone.stderr
            )
            self.assertFalse(rejected_standalone_path.exists())

            undeclared_helper = base / "undeclared_helper.py"
            undeclared_helper.write_text(
                'RESPONSE = "hidden helper must not contribute"\n', encoding="utf-8"
            )
            importing_runner = base / "importing_runner.py"
            importing_runner.write_text(
                """#!/usr/bin/env python3
import json
from pathlib import Path
import sys
from undeclared_helper import RESPONSE

json.load(sys.stdin)
Path("answer.md").write_text(RESPONSE, encoding="utf-8")
json.dump({"artifacts":["answer.md"],"response":RESPONSE,"sources":[],"token_usage":{"input":1,"output":1}}, sys.stdout)
sys.stdout.write("\\n")
""",
                encoding="utf-8",
            )
            importing_runner.chmod(0o755)
            importing_files = sorted(
                [SYSTEM_SANDBOX_PYTHON, importing_runner.resolve()],
                key=lambda path: str(path),
            )
            importing_manifest = base / "importing-runner-manifest.json"
            importing_manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "files": [
                            {"path": str(path), "sha256": sha256(path)}
                            for path in importing_files
                        ],
                    }
                ),
                encoding="utf-8",
            )
            undeclared_output = base / "undeclared-helper-output"
            undeclared_result = self.run_cli(
                "run",
                str(spec),
                str(held_out_matrix),
                "--hidden-bank",
                str(hidden),
                "--runner-json",
                json.dumps(
                    [
                        str(SYSTEM_SANDBOX_PYTHON),
                        "-I",
                        "-S",
                        str(importing_runner),
                    ]
                ),
                "--runner-manifest-json",
                str(importing_manifest),
                "--output-dir",
                str(undeclared_output),
                "--macos-sandbox",
                expected=5,
            )
            self.assertIn("integrity failure", undeclared_result.stderr)
            undeclared_rows = [
                json.loads(line)
                for line in (undeclared_output / "results.jsonl")
                .read_text()
                .splitlines()
            ]
            self.assertTrue(
                all(
                    "process_exit" in row["failed_hard_gates"]
                    for row in undeclared_rows
                )
            )
            undeclared_report = json.loads(
                (undeclared_output / "report.json").read_text()
            )
            self.assertFalse(undeclared_report["supports_candidate_quality_claim"])
            self.assertFalse(undeclared_report["eligible_for_held_out_claims"])
            self.assertTrue(
                all(row["runner_runtime_closure_sha256"] for row in undeclared_rows)
            )
            self.assertNotIn(
                sha256(undeclared_helper),
                json.dumps(undeclared_report, sort_keys=True),
            )

            persist_value = os.environ.get("PRAX_EVAL_SANDBOX_RECEIPT_DIR")
            if persist_value:
                persist = Path(persist_value).expanduser()
                if not persist.is_absolute() or persist.exists():
                    self.fail(
                        "PRAX_EVAL_SANDBOX_RECEIPT_DIR must be an absent absolute path"
                    )
                shutil.copytree(output, persist)
                (persist / "adversarial-summary.json").write_text(
                    json.dumps(
                        {
                            "candidate_read_blocked": True,
                            "eligible_for_held_out_claims": False,
                            "evaluation_scope": "containment_mechanism_fixture",
                            "hidden_bank_read_blocked": True,
                            "network_blocked": True,
                            "outside_write_blocked": True,
                            "source_target_read_blocked": True,
                            "supports_candidate_quality_claim": False,
                            "supports_human_learning_claim": False,
                        },
                        indent=2,
                        sort_keys=True,
                    )
                    + "\n",
                    encoding="utf-8",
                )


if __name__ == "__main__":
    unittest.main()
