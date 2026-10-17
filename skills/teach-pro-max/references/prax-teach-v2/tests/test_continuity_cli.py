"""Public continuity lifecycle and optimistic concurrency regressions."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/prax_teach.py"


class ContinuityCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.workspace = self.directory / ".prax-teach"
        self.call(
            "init", "--learner-id", "local", "--goal", "Learn fractions", "--consent"
        )

    def call(self, command, *args, expected=0):
        result = subprocess.run(
            [sys.executable, str(CLI), command, str(self.workspace), *args],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, expected, result.stderr + result.stdout)
        return json.loads(result.stdout) if result.returncode == 0 else result

    def grant(self, revision=0):
        return self.call(
            "continuity-grant", "--consent", "--expected-revision", str(revision)
        )

    def update(self, data, revision=1, expected=0):
        source = self.directory / "update.json"
        source.write_text(json.dumps(data), encoding="utf-8")
        return self.call(
            "continuity-update",
            "--data",
            str(source),
            "--expected-revision",
            str(revision),
            expected=expected,
        )

    def test_absent_legacy_and_explicit_grant(self):
        self.assertIsNone(self.call("continuity-show"))
        self.assertIsNone(self.call("show")["continuity"])
        self.assertIsNone(self.call("continuity-resume"))
        self.assertFalse((self.workspace / "state/continuity.json").exists())
        self.call("continuity-grant", "--expected-revision", "0", expected=3)
        record = self.grant()
        self.assertEqual(record["revision"], 1)
        self.assertEqual(record["consent"]["status"], "granted")
        self.assertEqual(self.call("continuity-resume"), record)

    def test_update_withdraw_regrant_and_controls(self):
        self.grant()
        data = {
            "preferences": {"medium": {"value": "static", "provenance": "user-stated"}},
            "covered_topics": ["fractions"],
            "last_lesson": {"id": "fractions-1", "position": "whole explanation"},
            "agent_summary": {
                "text": "Next explain equivalent fractions.",
                "provenance": "agent-authored",
            },
            "next_topic": {
                "value": "equivalent fractions",
                "provenance": "learner-requested",
            },
        }
        record = self.update(data)
        evidence = (self.workspace / "state/sessions.jsonl").read_bytes()
        self.assertEqual(record["revision"], 2)
        self.call("continuity-withdraw", "--expected-revision", "2")
        self.call("continuity-resume", expected=3)
        self.update({"covered_topics": []}, revision=3, expected=3)
        self.assertEqual(
            self.call("continuity-show")["preferences"], data["preferences"]
        )
        archive = self.directory / "export.zip"
        self.call("export", str(archive))
        with zipfile.ZipFile(archive) as handle:
            self.assertEqual(
                json.loads(handle.read("state/continuity.json"))["consent"]["status"],
                "withdrawn",
            )
        self.assertEqual(self.grant(3)["revision"], 4)
        preview = self.call(
            "continuity-reset",
            "--expected-revision",
            "4",
            "--preferences-only",
            "--dry-run",
        )
        self.assertEqual(preview["status"], "preview")
        self.assertEqual(self.call("continuity-show")["revision"], 4)
        record = self.call(
            "continuity-reset",
            "--expected-revision",
            "4",
            "--preferences-only",
            "--confirm",
        )
        self.assertEqual(record["preferences"], {})
        self.assertEqual(record["covered_topics"], ["fractions"])
        self.assertEqual(record["consent"]["status"], "granted")
        self.assertEqual(
            (self.workspace / "state/sessions.jsonl").read_bytes(), evidence
        )

    def test_base_withdrawal_blocks_personalization_and_writes(self):
        self.grant()
        self.call("disable-persistence", "--reason", "stop")
        self.call("continuity-resume", expected=3)
        self.call(
            "continuity-grant", "--consent", "--expected-revision", "1", expected=3
        )
        self.update({"covered_topics": []}, expected=3)
        self.call("continuity-withdraw", "--expected-revision", "1")
        self.assertEqual(self.call("show")["continuity"]["revision"], 2)
        self.call("continuity-reset", "--expected-revision", "2", "--all", "--confirm")
        self.assertIsNone(self.call("continuity-show"))

    def test_stale_revision_reset_and_sibling_lessons(self):
        self.grant()
        self.update({"covered_topics": ["fractions"]})
        self.update({"covered_topics": ["stale"]}, expected=6)
        self.call(
            "continuity-reset",
            "--expected-revision",
            "1",
            "--all",
            "--confirm",
            expected=6,
        )
        self.call("continuity-reset", "--expected-revision", "2", "--all", expected=2)
        self.call("continuity-reset", "--expected-revision", "2", "--all", "--confirm")
        self.call(
            "continuity-update",
            "--data",
            str(self.directory / "update.json"),
            "--expected-revision",
            "0",
            expected=3,
        )
        lesson = self.directory / "lessons/lesson.md"
        lesson.parent.mkdir()
        lesson.write_text("saved lesson")
        self.grant()
        self.call("delete", "--all", "--confirm")
        self.assertEqual(lesson.read_text(), "saved lesson")
        self.assertFalse(self.workspace.exists())

    def test_full_reset_regrant_starts_new_revision_lifetime(self):
        first = self.grant()
        cached_revision = first["revision"]
        pending_content = {"covered_topics": ["pre-reset queued content"]}
        evidence = (self.workspace / "state/sessions.jsonl").read_bytes()

        self.call(
            "continuity-reset", "--expected-revision", str(cached_revision),
            "--all", "--confirm",
        )
        self.assertFalse((self.workspace / "state/continuity.json").exists())
        self.assertIsNone(self.call("continuity-show"))
        self.assertIsNone(self.call("continuity-resume"))
        self.update(pending_content, revision=cached_revision, expected=6)
        self.assertFalse((self.workspace / "state/continuity.json").exists())

        # Only a new affirmative grant permits content writes again. Numeric
        # revisions repeat; the host must cancel old queued/in-flight updates.
        regranted = self.grant()
        self.assertEqual(regranted["revision"], cached_revision)
        self.assertEqual(regranted["covered_topics"], [])
        self.assertEqual(self.call("continuity-resume"), regranted)
        replayed = self.update(pending_content, revision=cached_revision)
        self.assertEqual(replayed["revision"], cached_revision + 1)
        self.assertEqual(replayed["covered_topics"], pending_content["covered_topics"])
        self.assertEqual(
            (self.workspace / "state/sessions.jsonl").read_bytes(), evidence
        )

    def test_concurrent_updates_reject_stale_writer(self):
        self.grant()
        source = self.directory / "update.json"
        source.write_text(json.dumps({"covered_topics": ["fractions"]}))
        command = [
            sys.executable,
            str(CLI),
            "continuity-update",
            str(self.workspace),
            "--data",
            str(source),
            "--expected-revision",
            "1",
        ]
        processes = [
            subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            for _ in range(2)
        ]
        results = [
            (*process.communicate(), process.returncode) for process in processes
        ]
        self.assertEqual(sorted(result[2] for result in results), [0, 6], results)
        self.assertEqual(self.call("continuity-show")["revision"], 2)


if __name__ == "__main__":
    unittest.main()
