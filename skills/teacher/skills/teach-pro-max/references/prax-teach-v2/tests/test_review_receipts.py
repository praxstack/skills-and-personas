#!/usr/bin/env python3
"""Black-box tests for final independent-review receipts."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_SCRIPT = ROOT / "scripts" / "review_payload.py"
VALIDATOR = ROOT / "scripts" / "validate_workspace.py"
REVIEW_ATTESTATION = {
    "cryptographic_authorship_verified": False,
    "orchestration_task_identity_recorded": True,
    "threat_model": (
        "orchestration task identity is structurally recorded; "
        "cryptographic authorship is not verified"
    ),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReviewReceiptTests(unittest.TestCase):
    def install_visual_verification_fixture(self, workspace: Path) -> None:
        """Install the validator's portable visual-fixture/runtime closure."""

        shutil.copytree(
            ROOT / "fixtures" / "visual-verification",
            workspace / "fixtures" / "visual-verification",
        )
        scripts = workspace / "scripts"
        scripts.mkdir()
        shutil.copy2(ROOT / "scripts" / "prax_teach.py", scripts)
        shutil.copy2(ROOT / "scripts" / "render_markdown.mjs", scripts)
        shutil.copy2(ROOT / "scripts" / "verify_visual_runtime.py", scripts)
        shutil.copytree(
            ROOT / "scripts" / "praxteach",
            scripts / "praxteach",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        shutil.copytree(
            ROOT / "runtime" / "prax-visual-lab",
            workspace / "runtime" / "prax-visual-lab",
            ignore=shutil.ignore_patterns("node_modules"),
        )
        shutil.copytree(
            ROOT / "examples" / "visual-lab",
            workspace / "examples" / "visual-lab",
        )
        # Runtime dependencies are deliberately excluded from the immutable
        # review payload, but the copied renderer still needs its pinned local
        # install when the full validator recomputes the fixture receipts.
        shutil.copytree(ROOT / "node_modules", workspace / "node_modules")

    def create_reviewed_workspace(self, workspace: Path) -> None:
        (workspace / "source.txt").write_text("reviewed bytes\n", encoding="utf-8")
        self.install_visual_verification_fixture(workspace)
        generated = subprocess.run(
            [
                sys.executable,
                str(PAYLOAD_SCRIPT),
                str(workspace),
                "--output",
                "evidence/reviews/payload.json",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(generated.returncode, 0, generated.stderr)
        payload_path = workspace / "evidence/reviews/payload.json"
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        payload_paths = {entry["path"] for entry in payload["files"]}
        self.assertIn(
            "fixtures/visual-verification/manifest.json",
            payload_paths,
        )
        for index, review_type in enumerate(
            ("code-standards", "frozen-spec", "architecture-council"), start=1
        ):
            receipt = {
                "schema_version": 2,
                "attestation": REVIEW_ATTESTATION,
                "review_type": review_type,
                "reviewer": {
                    "task": f"/reviewer/{index}",
                    "identity": f"independent reviewer {index}",
                    "independent_from_implementation": True,
                },
                "payload": "evidence/reviews/payload.json",
                "payload_file_sha256": sha256(payload_path),
                "payload_manifest_sha256": payload["sha256"],
                "status": "passed",
                "findings": [],
                "fixes": [],
                "unresolved_actionable": [],
                "recheck": {"status": "passed", "reviewer_confirmed": True},
            }
            if review_type == "architecture-council":
                receipt["panelists"] = [
                    {"task": f"/panel/{panel}", "status": "passed"}
                    for panel in range(1, 4)
                ]
                receipt["chair"] = {"task": "/chair/1", "status": "passed"}
            (workspace / f"evidence/reviews/{review_type}.json").write_text(
                json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

    def validate(self, workspace: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), "--json", str(workspace)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_three_independent_receipts_validate_current_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            self.create_reviewed_workspace(workspace)
            completed = self.validate(workspace)
            self.assertEqual(completed.returncode, 0, completed.stdout)
            report = json.loads(completed.stdout)
            self.assertEqual(report["counts"]["independent_review_receipts"], 3)

    def test_payload_mutation_after_review_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            self.create_reviewed_workspace(workspace)
            (workspace / "source.txt").write_text("changed later\n", encoding="utf-8")
            completed = self.validate(workspace)
            self.assertEqual(completed.returncode, 1, completed.stdout)
            joined = "\n".join(json.loads(completed.stdout)["errors"])
            self.assertIn("independent review payload is stale", joined)

    def test_unknown_review_entries_and_receipt_fields_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            self.create_reviewed_workspace(workspace)
            unknown = workspace / "evidence/reviews/unbounded-notes.json"
            unknown.write_text("{}\n", encoding="utf-8")
            completed = self.validate(workspace)
            self.assertEqual(completed.returncode, 1, completed.stdout)
            joined = "\n".join(json.loads(completed.stdout)["errors"])
            self.assertIn("unknown review entry", joined)

            unknown.unlink()
            receipt_path = workspace / "evidence/reviews/code-standards.json"
            receipt = json.loads(receipt_path.read_text())
            receipt["unbounded_extension"] = {"trusted": True}
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            completed = self.validate(workspace)
            self.assertEqual(completed.returncode, 1, completed.stdout)
            joined = "\n".join(json.loads(completed.stdout)["errors"])
            self.assertIn("exact schema", joined)

    def test_attestation_cannot_claim_cryptographic_authorship(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            self.create_reviewed_workspace(workspace)
            receipt_path = workspace / "evidence/reviews/frozen-spec.json"
            receipt = json.loads(receipt_path.read_text())
            receipt["attestation"]["cryptographic_authorship_verified"] = True
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

            completed = self.validate(workspace)
            self.assertEqual(completed.returncode, 1, completed.stdout)
            joined = "\n".join(json.loads(completed.stdout)["errors"])
            self.assertIn("cryptographic authorship", joined)


if __name__ == "__main__":
    unittest.main()
