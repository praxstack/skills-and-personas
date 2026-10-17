#!/usr/bin/env python3
"""Black-box tests for validator security and structured receipts."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_workspace.py"
RENDERER = ROOT / "scripts" / "render_markdown.mjs"
sys.path.insert(0, str(ROOT / "scripts"))
import validate_workspace as validator


class ValidatorCliTest(unittest.TestCase):
    def render(self, markdown: Path) -> Path:
        html = markdown.with_suffix(".html")
        trusted_root = markdown.parent.resolve()
        completed = subprocess.run(
            [
                "node",
                str(RENDERER),
                "--trusted-root",
                str(trusted_root),
                str(markdown.resolve()),
                str(trusted_root / html.name),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, "SOURCE_DATE_EPOCH": "1785844800"},
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return html

    def validate(self, workspace: Path, expected: int) -> dict[str, object]:
        completed = subprocess.run(
            [
                sys.executable,
                str(VALIDATOR),
                "--artifact-only",
                "--json",
                str(workspace),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, "SOURCE_DATE_EPOCH": "1785844800"},
        )
        self.assertEqual(
            completed.returncode,
            expected,
            msg=f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )
        return json.loads(completed.stdout)

    def test_artifact_only_emits_structured_clean_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            markdown = workspace / "lesson.md"
            markdown.write_text(
                "# Safe lesson\n\n## Attempt\n\nTry it.\n\n<details>\n<summary>Hint</summary>\n\nCompare cases.\n\n</details>\n",
                encoding="utf-8",
            )
            self.render(markdown)
            report = self.validate(workspace, 0)
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["mode"], "artifact-only")
            self.assertEqual(report["counts"]["markdown_html_pairs"], 1)
            self.assertEqual(report["errors"], [])
            self.assertEqual(report["security"]["dangerous_tags"], 0)
            self.assertEqual(report["security"]["event_attributes"], 0)
            self.assertEqual(report["security"]["unsafe_urls"], 0)

    def test_status_claim_parser_rejects_accessible_renderer_overclaim(self) -> None:
        self.assertEqual(
            validator._status_claims(
                {"evidence": "An accessible deterministic renderer is implemented."}
            ),
            (False, True),
        )
        self.assertEqual(
            validator._status_claims(
                {
                    "evidence": (
                        "A deterministic renderer with automated "
                        "accessibility-structure checks is implemented."
                    )
                }
            ),
            (False, False),
        )

    def test_portability_adapted_legacy_assets_are_explicitly_bound(self) -> None:
        count, errors = validator.validate_legacy_asset_provenance(ROOT)
        self.assertEqual(count, 1)
        self.assertEqual(errors, [])
        manifest = json.loads(
            (ROOT / "evidence/provenance/legacy-assets.json").read_text(
                encoding="utf-8"
            )
        )
        adapted = {
            item["target"]: item
            for item in manifest["assets"]
            if item.get("relation") == "portability-adapted"
        }
        self.assertEqual(
            set(adapted),
            {
                "assets/visualization-router.png",
                "assets/visualization-router.svg",
                "references/LEGACY-VISUALIZATION-ROUTER.md",
                "references/VISUALIZATION-TOOL-REGISTRY.md",
                "references/visualization-tool-registry.json",
                "scripts/find_visualization_tool.py",
                "scripts/test_visualization_registry.py",
            },
        )
        self.assertTrue(all(item.get("adaptation") for item in adapted.values()))

    def test_manually_injected_script_event_handler_and_unsafe_url_fail_closed(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            markdown = workspace / "lesson.md"
            markdown.write_text("# Safe lesson\n\nTry it.\n", encoding="utf-8")
            html_path = self.render(markdown)
            html = html_path.read_text(encoding="utf-8")
            html = html.replace(
                "</main>",
                '<script>alert(1)</script><a href="javascript:alert(2)" onclick="alert(3)">x</a></main>',
            )
            html_path.write_text(html, encoding="utf-8")
            report = self.validate(workspace, 1)
            self.assertEqual(report["status"], "failed")
            joined = "\n".join(report["errors"]).lower()
            self.assertIn("dangerous tag", joined)
            self.assertIn("event attribute", joined)
            self.assertIn("unsafe url", joined)
            self.assertGreater(report["security"]["dangerous_tags"], 0)

    def test_stale_hash_heading_jump_duplicate_id_and_external_asset_are_reported(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            markdown = workspace / "lesson.md"
            markdown.write_text("# Lesson\n\n## Step\n\nText.\n", encoding="utf-8")
            html_path = self.render(markdown)
            html = html_path.read_text(encoding="utf-8")
            html = html.replace('<h2 id="step">', '<h4 id="step"><span id="step">')
            html = html.replace("</h2>", "</span></h4>")
            html = html.replace(
                "</main>",
                '<img src="https://example.invalid/a.png" alt="external"></main>',
            )
            html_path.write_text(html, encoding="utf-8")
            markdown.write_text("# Lesson changed\n", encoding="utf-8")
            report = self.validate(workspace, 1)
            joined = "\n".join(report["errors"]).lower()
            self.assertIn("stale source hash", joined)
            self.assertIn("duplicate", joined)
            self.assertIn("heading level jumps", joined)
            self.assertIn("external asset", joined)

    def test_unlabelled_native_control_fails_accessibility_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            markdown = workspace / "lesson.md"
            markdown.write_text("# Practice\n", encoding="utf-8")
            html_path = self.render(markdown)
            html = html_path.read_text(encoding="utf-8").replace(
                "</main>", '<input id="answer" type="text"></main>'
            )
            html_path.write_text(html, encoding="utf-8")
            report = self.validate(workspace, 1)
            self.assertIn(
                "control has no accessible label", "\n".join(report["errors"])
            )

    def test_labelled_form_control_fails_closed_without_a_versioned_runtime(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            markdown = workspace / "lesson.md"
            markdown.write_text("# Practice\n", encoding="utf-8")
            html_path = self.render(markdown)
            html = html_path.read_text(encoding="utf-8").replace(
                "</main>",
                '<label for="answer">Answer</label><input id="answer" type="text"></main>',
            )
            html_path.write_text(html, encoding="utf-8")
            report = self.validate(workspace, 1)
            self.assertIn(
                "bundled renderer has no form-grading runtime",
                "\n".join(report["errors"]),
            )

    def test_missing_renderer_version_metadata_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            markdown = workspace / "lesson.md"
            markdown.write_text("# Practice\n", encoding="utf-8")
            html_path = self.render(markdown)
            html_path.write_text(
                html_path.read_text(encoding="utf-8").replace(
                    '  <meta name="renderer-version" content="prax-teach-markdown/2.2.0">\n',
                    "",
                ),
                encoding="utf-8",
            )
            report = self.validate(workspace, 1)
            self.assertIn(
                "expected exactly one renderer-version meta",
                "\n".join(report["errors"]),
            )

    def test_full_validation_accepts_the_release_status_ledger(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(VALIDATOR), "--json", str(ROOT)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, "SOURCE_DATE_EPOCH": "1785844800"},
        )
        self.assertEqual(completed.returncode, 0, completed.stdout)
        report = json.loads(completed.stdout)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["counts"]["release_status_ledgers"], 1)
        self.assertEqual(report["counts"]["browser_inspection_receipts"], 1)
        self.assertEqual(report["counts"]["package_contracts"], 1)
        self.assertEqual(report["counts"]["json_schemas"], 10)
        self.assertEqual(report["counts"]["schema_instances"], 10)
        self.assertEqual(report["counts"]["state_invariant_sets"], 1)
        self.assertEqual(report["counts"]["integration_manifests"], 3)
        self.assertEqual(report["counts"]["legacy_asset_manifests"], 1)
        self.assertEqual(report["counts"]["forward_behavior_receipts"], 1)
        self.assertEqual(report["counts"]["independent_review_receipts"], 3)
        self.assertEqual(report["counts"]["verification_receipts"], 1)

    def test_full_validation_replays_state_fixture_and_rejects_forged_event(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "candidate"
            shutil.copytree(
                ROOT,
                workspace,
                ignore=shutil.ignore_patterns(
                    ".ruff_cache", ".venv", "__pycache__", "node_modules"
                ),
            )
            events = workspace / "fixtures/schema-valid/events.jsonl"
            event = json.loads(events.read_text(encoding="utf-8"))
            event["response"] = "Forged response that retains the old event ID."
            events.write_text(json.dumps(event) + "\n", encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(VALIDATOR), "--json", str(workspace)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 1, completed.stdout)
            joined = "\n".join(json.loads(completed.stdout)["errors"])
            self.assertIn("event_id does not match its record", joined)

    def test_full_validation_rejects_stale_forward_behavior_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "candidate"
            shutil.copytree(
                ROOT,
                workspace,
                ignore=shutil.ignore_patterns(
                    ".ruff_cache", ".venv", "__pycache__", "node_modules"
                ),
            )
            output = workspace / "evidence/forward/outputs/quick-bounded-explanation.md"
            output.write_text(
                output.read_text(encoding="utf-8") + "\nmutated after scoring\n",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [sys.executable, str(VALIDATOR), "--json", str(workspace)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 1, completed.stdout)
            joined = "\n".join(json.loads(completed.stdout)["errors"])
            self.assertIn("forward behavior evidence output: digest mismatch", joined)

    def test_forward_receipt_rejects_mutated_bound_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "candidate"
            shutil.copytree(
                ROOT,
                workspace,
                ignore=shutil.ignore_patterns(
                    ".ruff_cache", ".venv", "__pycache__", "node_modules"
                ),
            )
            context = workspace / "evidence/forward/context/resume-hinted.json"
            context.write_text(
                context.read_text(encoding="utf-8") + "\n",
                encoding="utf-8",
            )

            _count, errors = validator.validate_forward_behavior_receipt(workspace)

            self.assertIn(
                "forward behavior evidence context: digest mismatch",
                "\n".join(errors),
            )

    def test_forward_receipt_rejects_unsafe_context_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "candidate"
            shutil.copytree(
                ROOT,
                workspace,
                ignore=shutil.ignore_patterns(
                    ".ruff_cache", ".venv", "__pycache__", "node_modules"
                ),
            )
            run_path = workspace / "evidence/forward/run.json"
            run = json.loads(run_path.read_text(encoding="utf-8"))
            resume_case = next(
                case
                for case in run["cases"]
                if case["case_id"] == "resume-hinted-evidence"
            )
            resume_case["context"] = "../resume-hinted.json"
            run_path.write_text(json.dumps(run), encoding="utf-8")

            _count, errors = validator.validate_forward_behavior_receipt(workspace)

            self.assertIn(
                "forward behavior evidence context: unsafe path",
                "\n".join(errors),
            )

    def test_forward_receipt_requires_resume_case_context_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "candidate"
            shutil.copytree(
                ROOT,
                workspace,
                ignore=shutil.ignore_patterns(
                    ".ruff_cache", ".venv", "__pycache__", "node_modules"
                ),
            )
            run_path = workspace / "evidence/forward/run.json"
            run = json.loads(run_path.read_text(encoding="utf-8"))
            resume_case = next(
                case
                for case in run["cases"]
                if case["case_id"] == "resume-hinted-evidence"
            )
            del resume_case["context"]
            del resume_case["context_sha256"]
            run_path.write_text(json.dumps(run), encoding="utf-8")

            receipt_path = workspace / "evidence/forward/receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["run_sha256"] = validator.sha256(run_path)
            receipt["hash_verification"]["context_count"] = 0
            receipt["hash_verification"]["checked_count"] -= 1
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

            _count, errors = validator.validate_forward_behavior_receipt(workspace)

            self.assertIn(
                "forward behavior evidence: resume-hinted-evidence must bind its public context",
                errors,
            )

    def test_forward_receipt_rejects_forged_hash_binding_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "candidate"
            shutil.copytree(
                ROOT,
                workspace,
                ignore=shutil.ignore_patterns(
                    ".ruff_cache", ".venv", "__pycache__", "node_modules"
                ),
            )
            receipt_path = workspace / "evidence/forward/receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            for field, forged_value in (
                ("rubric_count", 0),
                ("run_count", 0),
                ("source_count", 0),
                ("context_count", 0),
                ("output_count", 0),
                ("checked_count", 0),
                ("rubric_count", True),
            ):
                with self.subTest(field=field, forged_value=forged_value):
                    forged = json.loads(json.dumps(receipt))
                    forged["hash_verification"][field] = forged_value
                    receipt_path.write_text(json.dumps(forged), encoding="utf-8")

                    _count, errors = validator.validate_forward_behavior_receipt(
                        workspace
                    )

                    self.assertIn(
                        "forward behavior evidence: hash binding counts do not match",
                        errors,
                    )

    def test_forward_receipt_rejects_blank_reviewer_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "candidate"
            shutil.copytree(
                ROOT,
                workspace,
                ignore=shutil.ignore_patterns(
                    ".ruff_cache", ".venv", "__pycache__", "node_modules"
                ),
            )
            receipt_path = workspace / "evidence/forward/receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["reviewer"]["identity"] = "   "
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

            _count, errors = validator.validate_forward_behavior_receipt(workspace)

            self.assertIn(
                "forward behavior evidence: reviewer is not independently identified",
                errors,
            )

    def test_forward_receipt_rejects_runner_task_as_reviewer_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "candidate"
            shutil.copytree(
                ROOT,
                workspace,
                ignore=shutil.ignore_patterns(
                    ".ruff_cache", ".venv", "__pycache__", "node_modules"
                ),
            )
            run = json.loads(
                (workspace / "evidence/forward/run.json").read_text(encoding="utf-8")
            )
            receipt_path = workspace / "evidence/forward/receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["reviewer"]["identity"] = run["cases"][0]["fresh_task"]
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

            _count, errors = validator.validate_forward_behavior_receipt(workspace)

            self.assertIn(
                "forward behavior evidence: reviewer is not independently identified",
                errors,
            )

    def test_full_validation_rejects_a_promoted_scientific_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            (workspace / "STATUS.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "release_label": "scientifically-supported",
                        "north_star": {
                            "design_encoded": True,
                            "machinery_implemented": True,
                            "scientifically_supported": False,
                        },
                        "phases": [],
                        "capabilities": [],
                        "external_gates": [],
                    }
                ),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [sys.executable, str(VALIDATOR), "--json", str(workspace)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
                env={**os.environ, "SOURCE_DATE_EPOCH": "1785844800"},
            )
            self.assertEqual(completed.returncode, 1, completed.stdout)
            report = json.loads(completed.stdout)
            self.assertIn(
                "STATUS.json: release_label cannot exceed the North Star evidence",
                report["errors"],
            )

    def test_scientific_status_cannot_be_self_asserted_while_gates_are_parked(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            (workspace / "STATUS.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "release_label": "scientifically-supported",
                        "north_star": {
                            "design_encoded": True,
                            "machinery_implemented": True,
                            "scientifically_supported": True,
                        },
                        "phases": [
                            {
                                "id": "phase-0",
                                "state": "implemented",
                                "evidence": ["fixture"],
                                "parked": [],
                            }
                        ],
                        "capabilities": [
                            {
                                "id": "north-star-outcome",
                                "state": "scientifically-supported",
                                "evidence": ["self assertion"],
                                "claim_limit": "none",
                            }
                        ],
                        "external_gates": [
                            {"id": gate, "status": "parked", "unblock": "real study"}
                            for gate in ("EG-04", "EG-05", "EG-06")
                        ],
                    }
                ),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [sys.executable, str(VALIDATOR), "--json", str(workspace)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 1, completed.stdout)
            joined = "\n".join(json.loads(completed.stdout)["errors"])
            self.assertIn("requires EG-04, EG-05, and EG-06 to pass", joined)

    def test_blocked_browser_receipt_is_valid_only_at_the_parked_claim_boundary(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            page = workspace / "lesson.html"
            page.write_text("<!doctype html><title>Lesson</title>", encoding="utf-8")
            status = {
                "external_gates": [
                    {"id": "EG-03", "status": "parked", "unblock": "manual review"}
                ],
                "capabilities": [
                    {
                        "id": "markdown-html-artifacts",
                        "state": "implemented",
                        "evidence": ["automated structural checks"],
                        "claim_limit": "Real-browser and field evidence remain unverified.",
                    }
                ],
            }
            receipt = self.browser_receipt(page, status="blocked")
            self.write_browser_receipt(workspace, receipt)
            count, errors = validator.validate_browser_inspection_receipt(
                workspace, status
            )
            self.assertEqual(count, 1)
            self.assertEqual(errors, [])

    def test_blocked_browser_receipt_rejects_observation_checks_claims_and_extra_keys(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            page = workspace / "lesson.html"
            page.write_text("<!doctype html><title>Lesson</title>", encoding="utf-8")
            status = {
                "external_gates": [
                    {"id": "EG-03", "status": "failed", "unblock": "manual review"}
                ],
                "capabilities": [
                    {
                        "id": "markdown-html-artifacts",
                        "state": "manually-inspected",
                        "evidence": ["real-browser inspection passed"],
                        "claim_limit": "The package is field-accessible.",
                    }
                ],
            }
            receipt = self.browser_receipt(page, status="blocked")
            receipt["observed_runtime_pages"] = 1
            receipt["console_checked"] = True
            receipt["supports_field_accessibility_claim"] = True
            receipt["unexpected"] = "not allowed"
            self.write_browser_receipt(workspace, receipt)
            _count, errors = validator.validate_browser_inspection_receipt(
                workspace, status
            )
            joined = "\n".join(errors)
            self.assertIn("unexpected keys", joined)
            self.assertIn(
                "blocked receipt requires zero observed runtime pages", joined
            )
            self.assertIn(
                "blocked receipt requires all browser checks to be false", joined
            )
            self.assertIn("supports_field_accessibility_claim must be false", joined)
            self.assertIn(
                "blocked receipt requires STATUS.json EG-03 to be parked", joined
            )
            self.assertIn(
                "manual browser-inspection claim requires a passed receipt", joined
            )
            self.assertIn(
                "field-accessibility claim requires STATUS.json EG-03 to pass", joined
            )

    def test_passed_browser_receipt_supports_manual_inspection_not_field_evidence(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            page = workspace / "lesson.html"
            page.write_text("<!doctype html><title>Lesson</title>", encoding="utf-8")
            status = {
                "external_gates": [
                    {"id": "EG-03", "status": "parked", "unblock": "field work"}
                ],
                "capabilities": [
                    {
                        "id": "markdown-html-artifacts",
                        "state": "manually-inspected",
                        "evidence": ["real-browser inspection passed"],
                        "claim_limit": "Representative field accessibility is unverified.",
                    }
                ],
            }
            receipt = self.browser_receipt(page, status="passed")
            self.write_browser_receipt(workspace, receipt)
            count, errors = validator.validate_browser_inspection_receipt(
                workspace, status
            )
            self.assertEqual(count, 1)
            self.assertEqual(errors, [])

            status["capabilities"][0]["claim_limit"] = (
                "Representative field accessibility validated."
            )
            _count, errors = validator.validate_browser_inspection_receipt(
                workspace, status
            )
            self.assertIn(
                "field-accessibility claim requires STATUS.json EG-03 to pass",
                "\n".join(errors),
            )

    def test_browser_receipt_rejects_stale_or_unsafe_planned_page(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            page = workspace / "lesson.html"
            page.write_text("<!doctype html><title>Lesson</title>", encoding="utf-8")
            status = {
                "external_gates": [{"id": "EG-03", "status": "parked"}],
                "capabilities": [],
            }
            receipt = self.browser_receipt(page, status="blocked")
            receipt["planned_pages"][0]["path"] = "../lesson.html"
            receipt["planned_pages"][0]["sha256"] = "0" * 64
            self.write_browser_receipt(workspace, receipt)
            _count, errors = validator.validate_browser_inspection_receipt(
                workspace, status
            )
            joined = "\n".join(errors)
            self.assertIn("unsafe planned page path", joined)

    @staticmethod
    def browser_receipt(page: Path, *, status: str) -> dict[str, object]:
        import hashlib

        passed = status == "passed"
        return {
            "schema_version": 1,
            "attempted_at": "2026-08-04T20:15:00Z",
            "surface": "test browser",
            "status": status,
            "reason": "completed" if passed else "browser policy blocked navigation",
            "planned_pages": [
                {
                    "path": page.name,
                    "sha256": hashlib.sha256(page.read_bytes()).hexdigest(),
                }
            ],
            "observed_runtime_pages": 1 if passed else 0,
            "console_checked": passed,
            "responsive_viewports_checked": passed,
            "accessibility_tree_checked": passed,
            "manual_assistive_technology_checked": False,
            "supports_field_accessibility_claim": False,
            "claim_boundary": (
                "Manual browser inspection only; representative field evidence remains unverified."
            ),
        }

    @staticmethod
    def write_browser_receipt(workspace: Path, receipt: dict[str, object]) -> None:
        destination = workspace / "evidence/inspection/browser.json"
        destination.parent.mkdir(parents=True)
        destination.write_text(json.dumps(receipt), encoding="utf-8")

    def test_full_validation_rejects_broken_skill_and_schema_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            (workspace / "SKILL.md").write_text(
                "---\nname: wrong-name\ndescription: x\n---\n\n# Skill\n",
                encoding="utf-8",
            )
            schemas = workspace / "schemas"
            schemas.mkdir()
            (schemas / "broken.schema.json").write_text(
                json.dumps(
                    {
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "$id": "https://example.invalid/broken.schema.json",
                        "title": "Broken",
                        "type": "object",
                        "properties": {},
                        "required": ["missing"],
                    }
                ),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [sys.executable, str(VALIDATOR), "--json", str(workspace)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 1, completed.stdout)
            report = json.loads(completed.stdout)
            joined = "\n".join(report["errors"])
            self.assertIn("SKILL.md: name must be 'prax-teach-v2'", joined)
            self.assertIn("required property 'missing' has no schema", joined)
            self.assertIn("package requires exactly one release-status ledger", joined)


if __name__ == "__main__":
    unittest.main()
