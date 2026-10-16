"""Black-box learner-export provenance coverage."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "prax_teach.py"


class ExportProvenanceTests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> dict[str, object]:
        command_arguments = list(arguments)
        if command_arguments and command_arguments[0] == "observe":
            concept = command_arguments[command_arguments.index("--concept") + 1]
            command_arguments.extend(
                (
                    "--content-id",
                    concept,
                    "--objective-id",
                    "objective:" + concept,
                    "--model-and-prompt-version",
                    "test-tutor:model:prompt-v1",
                )
            )
        completed = subprocess.run(
            [sys.executable, str(CLI), *command_arguments],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def test_export_includes_mission_and_reviewed_source_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            workspace = base / "course"
            output = base / "learner-export.zip"
            self.run_cli(
                "init",
                str(workspace),
                "--learner-id",
                "learner-local",
                "--goal",
                "Explain and transfer lost-update reasoning",
                "--consent",
                "--timestamp",
                "2026-08-04T10:00:00Z",
            )
            resources = (
                "# Resources\n\n"
                "- source_id: database-transactions-primary\n"
                "- title: Database transaction reference\n"
                "- version_or_date: 2026-08-04\n"
            )
            (workspace / "RESOURCES.md").write_text(resources, encoding="utf-8")
            self.run_cli(
                "source-add",
                str(workspace),
                "--source-id",
                "database-transactions-primary",
                "--title",
                "Database transaction reference",
                "--url",
                "https://example.invalid/database-transactions",
                "--author-or-publisher",
                "Database standards fixture",
                "--source-type",
                "official-doc",
                "--retrieved-at",
                "2026-08-04",
                "--version-or-date",
                "2026-08-04",
                "--license-or-use-note",
                "Synthetic export provenance fixture.",
                "--supports",
                "lost-update",
                "--limitations",
                "Not real-world evidence.",
            )
            observed = self.run_cli(
                "observe",
                str(workspace),
                "--response",
                "A stale read followed by a later write can erase an update.",
                "--session",
                "session-1",
                "--concept",
                "lost-update",
                "--dimension",
                "application",
                "--score",
                "0.9",
                "--hint-level",
                "0",
                "--item",
                "lost-update-item",
                "--item-version",
                "v1",
                "--content-version",
                "sha256:" + "a" * 64,
                "--source-id",
                "database-transactions-primary",
                "--source-version",
                "2026-08-04",
                "--timestamp",
                "2026-08-04T10:30:00Z",
            )
            self.run_cli(
                "export",
                str(workspace),
                str(output),
                "--timestamp",
                "2026-08-04T11:00:00Z",
            )

            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
                self.assertIn("MISSION.md", names)
                self.assertIn("RESOURCES.md", names)
                self.assertIn("state/sources.json", names)
                self.assertEqual(archive.read("RESOURCES.md").decode(), resources)
                manifest = json.loads(archive.read("manifest.json"))

            provenance = manifest["provenance"]
            self.assertEqual(
                provenance["event_source_references"],
                "state/sessions.jsonl#source_provenance",
            )
            self.assertEqual(provenance["human_readable_resources"], "RESOURCES.md")
            source_manifest = provenance["source_library"]
            self.assertEqual(source_manifest["path"], "state/sources.json")
            self.assertEqual(source_manifest["active_reference_count"], 1)
            self.assertEqual(source_manifest["resolved_active_source_count"], 1)
            resolved = source_manifest["resolved_active_sources"][0]
            self.assertEqual(resolved["source_id"], "database-transactions-primary")
            self.assertEqual(resolved["version_or_date"], "2026-08-04")
            self.assertEqual(resolved["supporting_event_ids"], [observed["event_id"]])
            self.assertRegex(resolved["source_record_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(source_manifest["sha256"], r"^[0-9a-f]{64}$")
            tracked = {item["path"] for item in manifest["files"]}
            self.assertIn("MISSION.md", tracked)
            self.assertIn("RESOURCES.md", tracked)
            self.assertIn("state/sources.json", tracked)


if __name__ == "__main__":
    unittest.main()
