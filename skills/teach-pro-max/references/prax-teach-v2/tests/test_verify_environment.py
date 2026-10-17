"""Gate subprocess isolation must not hide candidate identity from real checks."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import verify


class VerificationEnvironmentTests(unittest.TestCase):
    def test_independent_fixture_gates_drop_only_candidate_context(self) -> None:
        environment = {
            **os.environ,
            "PRAX_CURRENT_EVIDENCE": "/candidate/selection.json",
            "PRAX_CURRENT_EVIDENCE_SHA256": "a" * 64,
            "PRAX_ACTIVE_VERIFICATION_RUN_ID": "candidate-run",
            "PRAX_FIXTURE_ENVIRONMENT_SENTINEL": "preserved",
            "PRAX_RUN_MACOS_SANDBOX_TESTS": "0",
        }
        before = dict(environment)
        script = """
import os
assert 'PRAX_CURRENT_EVIDENCE' not in os.environ
assert 'PRAX_CURRENT_EVIDENCE_SHA256' not in os.environ
assert 'PRAX_ACTIVE_VERIFICATION_RUN_ID' not in os.environ
assert os.environ['PRAX_FIXTURE_ENVIRONMENT_SENTINEL'] == 'preserved'
assert os.environ['PATH']
"""
        for gate in ("python-tests", "node-tests"):
            with self.subTest(gate=gate):
                result = verify.run_gate(
                    gate, [sys.executable, "-c", script], environment
                )
                self.assertEqual(result["status"], "passed", result)
                self.assertEqual(environment, before)

    def test_candidate_checks_keep_selection_and_active_run(self) -> None:
        environment = {
            **os.environ,
            "PRAX_CURRENT_EVIDENCE": "/candidate/selection.json",
            "PRAX_CURRENT_EVIDENCE_SHA256": "a" * 64,
            "PRAX_ACTIVE_VERIFICATION_RUN_ID": "candidate-run",
        }
        script = """
import os
assert os.environ['PRAX_CURRENT_EVIDENCE'] == '/candidate/selection.json'
assert os.environ['PRAX_CURRENT_EVIDENCE_SHA256'] == 'a' * 64
assert os.environ['PRAX_ACTIVE_VERIFICATION_RUN_ID'] == 'candidate-run'
"""
        for gate in ("package-validator", "html-exact-parity"):
            with self.subTest(gate=gate):
                result = verify.run_gate(
                    gate, [sys.executable, "-c", script], environment
                )
                self.assertEqual(result["status"], "passed", result)


if __name__ == "__main__":
    unittest.main()
