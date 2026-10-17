#!/usr/bin/env python3
"""Black-box tests for independently reviewable payload manifests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "review_payload.py"
sys.path.insert(0, str(ROOT / "scripts"))
import review_payload


class ReviewPayloadTests(unittest.TestCase):
    def run_script(
        self, workspace: Path, *extra: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                str(workspace),
                "--output",
                "evidence/reviews/payload.json",
                *extra,
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_manifest_excludes_receipts_and_detects_later_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            (workspace / "source.txt").write_text("review me\n", encoding="utf-8")
            (workspace / "evidence/reviews").mkdir(parents=True)
            (workspace / "evidence/verification").mkdir(parents=True)
            (workspace / "evidence/verification/full.json").write_text(
                "{}\n", encoding="utf-8"
            )
            (workspace / "hidden-bank").mkdir()
            (workspace / "hidden-bank/secret.json").write_text(
                '{"answer":"private"}\n', encoding="utf-8"
            )

            generated = self.run_script(workspace)
            self.assertEqual(generated.returncode, 0, generated.stderr)
            payload = json.loads(
                (workspace / "evidence/reviews/payload.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual([row["path"] for row in payload["files"]], ["source.txt"])
            self.assertEqual(self.run_script(workspace, "--check").returncode, 0)

            (workspace / "source.txt").write_text("drifted\n", encoding="utf-8")
            checked = self.run_script(workspace, "--check")
            self.assertEqual(checked.returncode, 1)
            self.assertIn("stale", checked.stderr.lower())

    def test_only_named_receipts_are_excluded_and_unknown_review_files_drift(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            reviews = workspace / "evidence/reviews"
            reviews.mkdir(parents=True)
            for name in (
                "payload.json",
                "code-standards.json",
                "frozen-spec.json",
                "architecture-council.json",
            ):
                (reviews / name).write_text("{}\n", encoding="utf-8")
            unknown = reviews / "reviewer-notes.md"
            unknown.write_text("reviewed note\n", encoding="utf-8")

            generated = self.run_script(workspace)
            self.assertEqual(generated.returncode, 0, generated.stderr)
            payload = json.loads((reviews / "payload.json").read_text())
            paths = {row["path"] for row in payload["files"]}
            self.assertIn("evidence/reviews/reviewer-notes.md", paths)
            self.assertTrue(
                {
                    "evidence/reviews/payload.json",
                    "evidence/reviews/code-standards.json",
                    "evidence/reviews/frozen-spec.json",
                    "evidence/reviews/architecture-council.json",
                }.isdisjoint(paths)
            )

            unknown.write_text("changed after freeze\n", encoding="utf-8")
            checked = self.run_script(workspace, "--check")
            self.assertEqual(checked.returncode, 1)
            self.assertIn("stale", checked.stderr.lower())

    def test_modes_are_normalized_to_archive_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            regular = workspace / "regular.txt"
            executable = workspace / "tool.sh"
            regular.write_text("regular\n", encoding="utf-8")
            executable.write_text("#!/bin/sh\n", encoding="utf-8")
            os.chmod(regular, 0o600)
            os.chmod(executable, 0o711)

            generated = self.run_script(workspace)
            self.assertEqual(generated.returncode, 0, generated.stderr)
            payload = json.loads(
                (workspace / "evidence/reviews/payload.json").read_text()
            )
            modes = {row["path"]: row["mode"] for row in payload["files"]}
            self.assertEqual(modes["regular.txt"], "0644")
            self.assertEqual(modes["tool.sh"], "0755")

    def test_directory_symlink_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            outside = Path(temp) / "outside"
            outside.mkdir()
            (outside / "secret.txt").write_text("secret\n", encoding="utf-8")
            (workspace / "linked").symlink_to(outside, target_is_directory=True)
            completed = self.run_script(workspace)
            self.assertEqual(completed.returncode, 2)
            self.assertIn("symlink", completed.stderr.lower())

    def test_leaf_swap_to_symlink_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            workspace.mkdir()
            victim = workspace / "reviewed.txt"
            victim.write_text("reviewed\n", encoding="utf-8")
            external = Path(temp) / "external.txt"
            external.write_text("external\n", encoding="utf-8")
            real_open = os.open
            swapped = False

            def swap_before_open(path, flags, *args, **kwargs):
                nonlocal swapped
                if Path(path) == victim and not swapped:
                    victim.unlink()
                    victim.symlink_to(external)
                    swapped = True
                return real_open(path, flags, *args, **kwargs)

            with (
                patch.object(review_payload.os, "open", side_effect=swap_before_open),
                self.assertRaises(review_payload.PayloadError),
            ):
                review_payload.payload_manifest(workspace)

    def test_check_rejects_symlinked_output_leaf(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            workspace.mkdir()
            (workspace / "source.txt").write_text("review me\n", encoding="utf-8")

            generated = self.run_script(workspace)
            self.assertEqual(generated.returncode, 0, generated.stderr)
            output = workspace / "evidence/reviews/payload.json"
            outside = Path(temp) / "outside-payload.json"
            output.replace(outside)
            output.symlink_to(outside)

            checked = self.run_script(workspace, "--check")
            self.assertEqual(checked.returncode, 2)
            self.assertIn("symlink", checked.stderr.lower())


if __name__ == "__main__":
    unittest.main()
