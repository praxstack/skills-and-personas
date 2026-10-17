import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "integrations/formal/lean/adapter.py"
SOURCE = ROOT / "examples/visual-lab/lean-proof-state/Proof.lean"
PROOF = ROOT / "examples/visual-lab/lean-proof-state/proof-state.json"


class FormalAdapterTests(unittest.TestCase):
    def test_build_time_receipt_is_provenance_bound_and_runtime_free(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "formal-receipt.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ADAPTER),
                    "--source",
                    str(SOURCE),
                    "--proof-state",
                    str(PROOF),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            receipt = json.loads(output.read_text())
            self.assertIn(receipt["status"], {"unavailable", "failed", "verified"})
            self.assertEqual(
                receipt["source_sha256"],
                hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            )
            self.assertEqual(receipt["schema_version"], "prax.formal-receipt/v1")

    def test_lean_exit_status_controls_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            fake_lean = temporary_path / "lean"
            fake_lean.write_text(
                "#!/bin/sh\n"
                'if [ "$1" = "--version" ]; then echo \'Lean 4.test\'; exit 0; fi\n'
                'exit "${FAKE_LEAN_EXIT:-0}"\n'
            )
            fake_lean.chmod(0o755)
            proof = temporary_path / "proof-state.json"
            proof.write_text(
                json.dumps(
                    {
                        "schema_version": "prax.formal-proof-state/v1",
                        "source_sha256": hashlib.sha256(
                            SOURCE.read_bytes()
                        ).hexdigest(),
                        "status": "verified",
                        "states": [{"label": "Closed", "goal": "no goals"}],
                    }
                )
            )
            environment = os.environ | {
                "PATH": f"{temporary_path}:{os.environ.get('PATH', '')}",
                "FAKE_LEAN_EXIT": "0",
            }
            verified = self._run_adapter(
                temporary_path / "verified.json", proof, environment
            )
            self.assertEqual(verified["status"], "verified")

            environment["FAKE_LEAN_EXIT"] = "1"
            failed = self._run_adapter(
                temporary_path / "failed.json", proof, environment
            )
            self.assertEqual(failed["status"], "failed")

    def test_proof_state_must_match_the_lean_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            fake_lean = temporary_path / "lean"
            fake_lean.write_text(
                '#!/bin/sh\nif [ "$1" = "--version" ]; then echo \'Lean 4.test\'; fi\n'
            )
            fake_lean.chmod(0o755)
            proof = temporary_path / "proof-state.json"
            proof.write_text(
                json.dumps(
                    {
                        "schema_version": "prax.formal-proof-state/v1",
                        "source_sha256": "0" * 64,
                        "status": "verified",
                        "states": [],
                    }
                )
            )
            receipt = self._run_adapter(
                temporary_path / "mismatch.json",
                proof,
                os.environ | {"PATH": f"{temporary_path}:{os.environ.get('PATH', '')}"},
            )
            self.assertEqual(receipt["status"], "failed")
            self.assertIn("does not match", " ".join(receipt["warnings"]))

    def test_forged_proof_state_shape_cannot_be_verified(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            fake_lean = temporary_path / "lean"
            fake_lean.write_text(
                '#!/bin/sh\nif [ "$1" = "--version" ]; then echo \'Lean 4.test\'; fi\n'
            )
            fake_lean.chmod(0o755)
            proof = temporary_path / "proof-state.json"
            proof.write_text(
                json.dumps(
                    {
                        "schema_version": "forged",
                        "source_sha256": hashlib.sha256(
                            SOURCE.read_bytes()
                        ).hexdigest(),
                        "status": "verified",
                        "states": "forged",
                    }
                )
            )
            receipt = self._run_adapter(
                temporary_path / "forged.json",
                proof,
                os.environ | {"PATH": f"{temporary_path}:{os.environ.get('PATH', '')}"},
            )
            self.assertEqual(receipt["status"], "failed")
            self.assertEqual(receipt["proof_states"], [])
            self.assertIn("contract", " ".join(receipt["warnings"]))

            proof.write_text("[]")
            non_object = self._run_adapter(
                temporary_path / "non-object.json",
                proof,
                os.environ | {"PATH": f"{temporary_path}:{os.environ.get('PATH', '')}"},
            )
            self.assertEqual(non_object["status"], "failed")
            self.assertEqual(non_object["proof_states"], [])

    def _run_adapter(self, output: Path, proof: Path, environment: dict[str, str]):
        completed = subprocess.run(
            [
                sys.executable,
                str(ADAPTER),
                "--source",
                str(SOURCE),
                "--proof-state",
                str(proof),
                "--output",
                str(output),
            ],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(output.read_text())


if __name__ == "__main__":
    unittest.main()
