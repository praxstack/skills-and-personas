#!/usr/bin/env python3
"""Black-box visual-routing contract tests."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "prax_teach.py"
FIXTURES = ROOT / "fixtures" / "routing-cases.json"
sys.path.insert(0, str(ROOT / "scripts"))

from praxteach import routing as routing_module


class VisualRoutingTest(unittest.TestCase):
    def run_cli(self, *args: str) -> dict[str, object]:
        completed = subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def test_public_visual_cases_choose_smallest_semantic_route(self) -> None:
        fixtures = json.loads(FIXTURES.read_text())
        for case in fixtures["visual_cases"]:
            args = ["visual-route", "--job", case["job"]]
            if case.get("exact_quantitative"):
                args.append("--exact-quantitative")
            if "static_sufficient" in case:
                args.extend(
                    ("--static-sufficient", str(case["static_sufficient"]).lower())
                )
            result = self.run_cli(*args)
            self.assertEqual(result["route"], case["expected_route"], case["id"])
            self.assertIn(result["route"], {"none", "static", "interactive", "motion"})
            self.assertTrue(result["reason"])
            if result["route"] != "none":
                self.assertTrue(result["fallback"])

    def test_packaged_visual_runtime_delivers_interaction_and_motion_directly(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate = Path(temporary)
            shutil.copytree(ROOT / "runtime", candidate / "runtime")
            shutil.copytree(ROOT / "examples", candidate / "examples")
            (candidate / "scripts").mkdir()
            shutil.copy2(
                ROOT / "scripts" / "verify_visual_runtime.py",
                candidate / "scripts" / "verify_visual_runtime.py",
            )
            shutil.copytree(
                ROOT / "scripts" / "praxteach",
                candidate / "scripts" / "praxteach",
            )
            build = subprocess.run(
                ["node", "build.mjs"],
                cwd=candidate / "runtime" / "prax-visual-lab",
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(build.returncode, 0, build.stderr)
            receipt = candidate / routing_module.VISUAL_RUNTIME_RECEIPT
            receipt.parent.mkdir(parents=True)
            receipt.write_text(
                json.dumps(
                    {
                        "schema_version": "prax.zero-api-runtime-verification/v1",
                        "status": "passed",
                        "errors": [],
                        "network_scan": "passed",
                        "external_human_learning_gates_satisfied": False,
                        "bindings": routing_module.runtime_bindings(candidate),
                    }
                )
            )
            valid_receipt = json.loads(receipt.read_text())
            with mock.patch.object(routing_module, "ROOT", candidate):
                for requested in ("interactive", "motion"):
                    result = routing_module.route_visual(
                        "Explore Python floating-point rounding: let the learner manipulate state and watch it change",
                        force=requested,
                    )
                    self.assertEqual(result["delivery_route"], requested)
                    self.assertTrue(result["visual_runtime_supported"])

                unbound = routing_module.route_visual(
                    "Manipulate a graph parameter and watch the chart change",
                    force="interactive",
                )
                self.assertEqual(unbound["delivery_route"], "static")
                self.assertFalse(unbound["visual_runtime_supported"])

                for relative in (
                    "runtime/prax-visual-lab/src/core.mjs",
                    "runtime/prax-visual-lab/dist/core.mjs",
                    "runtime/prax-visual-lab/dist/manifest.json",
                    "runtime/prax-visual-lab/tests/core.test.mjs",
                    "runtime/prax-visual-lab/contracts/learning-receipt.schema.json",
                    "runtime/prax-visual-lab/build.mjs",
                    "scripts/praxteach/routing.py",
                    "scripts/verify_visual_runtime.py",
                ):
                    with self.subTest(tampered=relative):
                        target = candidate / relative
                        original = target.read_bytes()
                        target.write_bytes(bytes([original[0] ^ 1]) + original[1:])
                        tampered = routing_module.route_visual(
                            "Explore Python floating-point rounding: let the learner manipulate state and watch it change",
                            force="interactive",
                        )
                        self.assertEqual(tampered["delivery_route"], "static")
                        self.assertFalse(tampered["visual_runtime_supported"])
                        target.write_bytes(original)

                source = candidate / "runtime/prax-visual-lab/src/core.mjs"
                external = candidate.parent / f"{candidate.name}-external-core.mjs"
                external.write_bytes(source.read_bytes())
                source.unlink()
                source.symlink_to(external)
                symlinked = routing_module.route_visual(
                    "Explore Python floating-point rounding: let the learner manipulate state and watch it change",
                    force="interactive",
                )
                self.assertEqual(symlinked["delivery_route"], "static")
                self.assertFalse(symlinked["visual_runtime_supported"])
                source.unlink()
                source.write_bytes(external.read_bytes())
                external.unlink()

                runtime = candidate / "runtime"
                runtime_real = candidate / "runtime-real"
                runtime.rename(runtime_real)
                runtime.symlink_to(runtime_real, target_is_directory=True)
                symlinked_ancestor = routing_module.route_visual(
                    "Explore Python floating-point rounding: let the learner manipulate state and watch it change",
                    force="interactive",
                )
                self.assertEqual(symlinked_ancestor["delivery_route"], "static")
                self.assertFalse(symlinked_ancestor["visual_runtime_supported"])
                runtime.unlink()
                runtime_real.rename(runtime)

                source = candidate / "runtime/prax-visual-lab/src/core.mjs"
                dist_core = candidate / "runtime/prax-visual-lab/dist/core.mjs"
                manifest_path = candidate / "runtime/prax-visual-lab/dist/manifest.json"
                original_source = source.read_bytes()
                original_dist_core = dist_core.read_bytes()
                original_manifest = manifest_path.read_bytes()
                fetched_bytes = b'\nvoid fetch("https://example.invalid");\n'
                source.write_bytes(original_source + fetched_bytes)
                dist_core.write_bytes(original_dist_core + fetched_bytes)
                manifest = json.loads(original_manifest)
                for record in manifest["files"]:
                    if record["path"] == "core.mjs":
                        record["bytes"] = len(original_dist_core + fetched_bytes)
                        record["sha256"] = hashlib.sha256(
                            original_dist_core + fetched_bytes
                        ).hexdigest()
                manifest["source_sha256"] = hashlib.sha256(
                    "".join(
                        f"{record['path']}:{record['sha256']}:{record['bytes']}\n"
                        for record in manifest["files"]
                    ).encode()
                ).hexdigest()
                manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
                forged = json.loads(receipt.read_text())
                forged["bindings"] = routing_module.runtime_bindings(candidate)
                receipt.write_text(json.dumps(forged))
                fetched = routing_module.route_visual(
                    "Explore Python floating-point rounding: let the learner manipulate state and watch it change",
                    force="interactive",
                )
                self.assertEqual(fetched["delivery_route"], "static")
                self.assertFalse(fetched["visual_runtime_supported"])
                source.write_bytes(original_source)
                dist_core.write_bytes(original_dist_core)
                manifest_path.write_bytes(original_manifest)
                receipt.write_text(json.dumps(valid_receipt))

                original_receipt = json.loads(receipt.read_text())
                for field, value in (
                    ("network_scan", "failed"),
                    ("external_human_learning_gates_satisfied", True),
                ):
                    with self.subTest(tampered_receipt=field):
                        receipt.write_text(
                            json.dumps(original_receipt | {field: value})
                        )
                        tampered = routing_module.route_visual(
                            "Explore Python floating-point rounding: let the learner manipulate state and watch it change",
                            force="interactive",
                        )
                        self.assertEqual(tampered["delivery_route"], "static")
                        self.assertFalse(tampered["visual_runtime_supported"])
                receipt.write_text(json.dumps(original_receipt))

    def test_flint_is_optional_only_after_static_quantitative_route(self) -> None:
        result = self.run_cli(
            "visual-route",
            "--job",
            "Compare a distribution across twelve groups where a table alone is hard to scan",
            "--exact-quantitative",
        )
        self.assertEqual(result["route"], "static")
        self.assertTrue(result["flint_eligible"])
        self.assertEqual(result["flint_required"], False)
        self.assertIn("table", result["fallback"].lower())

        prose = self.run_cli(
            "visual-route",
            "--job",
            "Define the term",
            "--exact-quantitative",
            "--static-sufficient",
            "true",
            "--force",
            "none",
        )
        self.assertEqual(prose["route"], "none")
        self.assertFalse(prose["flint_eligible"])

    def test_retrieval_mode_declares_unperformed_checks_for_every_fallback(
        self,
    ) -> None:
        for route in ("static", "interactive", "motion"):
            result = self.run_cli(
                "visual-route",
                "--job",
                "Assess the learner's prediction before revealing the correct state",
                "--retrieval",
                "--force",
                route,
            )
            safety = result["retrieval_safety"]
            self.assertTrue(safety["required"])
            self.assertEqual(safety["verification_status"], "not_run")
            self.assertFalse(safety["checks_performed"])
            self.assertIn("attempt_before_reveal", safety["required_checks"])
            self.assertIn("alt_text", safety["surfaces_to_check"])
            self.assertIn("source_code", safety["surfaces_to_check"])
            self.assertNotIn("checked_surfaces", safety)


if __name__ == "__main__":
    unittest.main()
