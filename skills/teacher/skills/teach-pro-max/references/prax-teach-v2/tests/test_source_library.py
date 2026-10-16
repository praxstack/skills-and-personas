"""Black-box versioned source-library and provenance binding tests."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "prax_teach.py"


class SourceLibraryTest(unittest.TestCase):
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
            [sys.executable, str(CLI), *arguments],
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
            "source-library-learner",
            "--goal",
            "Apply versioned source evidence",
            "--consent",
            "--timestamp",
            "2026-08-05T08:00:00Z",
        )

    def add_source(self, workspace: Path, *, version: str) -> None:
        self.run_cli(
            "source-add",
            str(workspace),
            "--source-id",
            "official-source",
            "--title",
            "Official source fixture",
            "--url",
            "https://example.invalid/official-source",
            "--author-or-publisher",
            "Fixture standards body",
            "--source-type",
            "official-doc",
            "--retrieved-at",
            "2026-08-05",
            "--version-or-date",
            version,
            "--license-or-use-note",
            "Synthetic source fixture.",
            "--supports",
            "source-concept",
            "--limitations",
            "Not real-world instructional evidence.",
        )

    def observe(
        self,
        workspace: Path,
        *,
        version: str,
        item: str = "source-item",
        item_version: str = "v1",
        content_version: str = "sha256:" + "a" * 64,
        expected: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        return self.run_cli(
            "observe",
            str(workspace),
            "--response",
            "This answer is bound to one reviewed source version.",
            "--session",
            f"session-{item_version}",
            "--concept",
            "source-concept",
            "--dimension",
            "application",
            "--score",
            "0.9",
            "--hint-level",
            "0",
            "--item",
            item,
            "--item-version",
            item_version,
            "--content-version",
            content_version,
            "--source-id",
            "official-source",
            "--source-version",
            version,
            "--timestamp",
            "2026-08-05T08:10:00Z" if item_version == "v1" else "2026-08-05T08:11:00Z",
            expected=expected,
        )

    def test_observation_rejects_unknown_source_id_or_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            before = (workspace / "state" / "sessions.jsonl").read_bytes()
            failed = self.observe(workspace, version="missing-version", expected=6)
            self.assertIn("does not resolve", failed.stderr.lower())
            self.assertEqual(
                (workspace / "state" / "sessions.jsonl").read_bytes(), before
            )

            self.add_source(workspace, version="v1")
            wrong_version = self.observe(workspace, version="v2", expected=6)
            self.assertIn("official-source@v2", wrong_version.stderr)
            self.assertEqual(
                (workspace / "state" / "sessions.jsonl").read_bytes(), before
            )

    def test_missing_or_malformed_source_metadata_blocks_resume(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            self.add_source(workspace, version="v1")
            sources_path = workspace / "state" / "sources.json"
            pristine = json.loads(sources_path.read_text(encoding="utf-8"))

            missing = json.loads(json.dumps(pristine))
            missing["sources"][0].pop("limitations")
            sources_path.write_text(json.dumps(missing) + "\n", encoding="utf-8")
            failed_missing = self.run_cli("show", str(workspace), expected=6)
            self.assertIn("missing required field", failed_missing.stderr.lower())

            malformed = json.loads(json.dumps(pristine))
            malformed["sources"][0]["retrieved_at"] = "05/08/2026"
            sources_path.write_text(json.dumps(malformed) + "\n", encoding="utf-8")
            failed_malformed = self.run_cli("show", str(workspace), expected=6)
            self.assertIn("iso-8601 date", failed_malformed.stderr.lower())

    def test_source_invalidation_requires_and_matches_exact_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            self.add_source(workspace, version="v1")
            self.add_source(workspace, version="v2")
            first = json.loads(self.observe(workspace, version="v1").stdout)
            second = json.loads(
                self.observe(
                    workspace,
                    version="v2",
                    item="source-item-v2",
                    item_version="v2",
                    content_version="sha256:" + "b" * 64,
                ).stdout
            )

            unversioned = self.run_cli(
                "invalidate",
                str(workspace),
                "--source-id",
                "official-source",
                "--reason",
                "One exact source version was withdrawn",
                "--timestamp",
                "2026-08-05T08:12:00Z",
                expected=6,
            )
            self.assertIn("source-version is required", unversioned.stderr.lower())

            invalidated = json.loads(
                self.run_cli(
                    "invalidate",
                    str(workspace),
                    "--source-id",
                    "official-source",
                    "--source-version",
                    "v1",
                    "--reason",
                    "Version v1 was withdrawn",
                    "--timestamp",
                    "2026-08-05T08:12:00Z",
                ).stdout
            )
            self.assertEqual(invalidated["invalidated_event_ids"], [first["event_id"]])
            self.assertNotIn(second["event_id"], invalidated["invalidated_event_ids"])

    def test_export_rejects_an_active_event_with_an_unresolved_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            workspace = base / "course"
            output = base / "must-not-export.zip"
            self.init_workspace(workspace)
            self.add_source(workspace, version="v1")
            self.observe(workspace, version="v1")

            sources_path = workspace / "state" / "sources.json"
            sources_path.write_text(
                json.dumps({"schema_version": "1", "sources": []}) + "\n",
                encoding="utf-8",
            )
            failed = self.run_cli(
                "export",
                str(workspace),
                str(output),
                "--timestamp",
                "2026-08-05T08:30:00Z",
                expected=6,
            )
            self.assertIn("official-source@v1", failed.stderr)
            self.assertIn("does not resolve", failed.stderr.lower())
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
