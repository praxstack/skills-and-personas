# Ported from prax-teach-v2 .engine/tests/test_continuity_security.py (accepted bytes). Changes: paths, imports
# (praxteach -> ptk.state), and the schema-2 adjustments listed in plan/PROTECTED-MAP.md.
"""Fail-closed optional state, bounded schema and existing anchored I/O."""

from __future__ import annotations

import copy
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent  # ported to v2.1: tests/ported_v2
PKG = ROOT.parents[1]
sys.path.insert(0, str(PKG))
import test_continuity_cli as cli_test
from ptk.state.continuity import validate_continuity_document
from ptk.state.errors import ValidationError


class ContinuitySecurityTest(unittest.TestCase):
    setUp = cli_test.ContinuityCliTest.setUp
    call = cli_test.ContinuityCliTest.call
    grant = cli_test.ContinuityCliTest.grant
    update = cli_test.ContinuityCliTest.update

    def test_unsafe_optional_records_fail_all_controls(self):
        outside = self.directory / "private.json"
        outside.write_text("{}")
        outside.chmod(0o600)
        target = self.workspace / "state/continuity.json"
        for attack in ("symlink", "hardlink", "world-readable"):
            with self.subTest(attack=attack):
                if attack == "symlink":
                    target.symlink_to(outside)
                elif attack == "hardlink":
                    os.link(outside, target)
                else:
                    self.grant()
                    target.chmod(0o644)
                for command, arguments in (
                    ("continuity-show", ()),
                    ("continuity-resume", ()),
                    ("show", ()),
                    ("continuity-grant", ("--consent", "--expected-revision", "0")),
                    (
                        "continuity-reset",
                        ("--expected-revision", "0", "--all", "--confirm"),
                    ),
                    ("export", (str(self.directory / "unsafe.zip"),)),
                    ("delete", ("--all", "--dry-run")),
                ):
                    self.call(command, *arguments, expected=5)
                target.unlink()
                self.assertEqual(outside.read_text(), "{}")

    def test_corrupt_optional_record_is_not_absence(self):
        target = self.workspace / "state/continuity.json"
        for raw in (b"{bad", b"\xff", b"null", b"{}", b'{"schema_version":1}'):
            with self.subTest(raw=raw):
                target.write_bytes(raw)
                target.chmod(0o600)
                before = target.read_bytes()
                for command, arguments in (
                    ("continuity-show", ()),
                    ("continuity-resume", ()),
                    ("show", ()),
                    (
                        "continuity-reset",
                        ("--expected-revision", "0", "--all", "--confirm"),
                    ),
                    ("export", (str(self.directory / "corrupt.zip"),)),
                    ("delete", ("--all", "--dry-run")),
                ):
                    self.call(command, *arguments, expected=6)
                self.assertEqual(target.read_bytes(), before)

    def test_unknown_types_provenance_and_bounds_rejected_without_write(self):
        self.grant()
        target = self.workspace / "state/continuity.json"
        original = target.read_bytes()
        cases = [
            {"extra": "no"},
            {"revision": 3},
            {},
            [],
            {
                "preferences": {
                    "inferred_learning_style": {
                        "value": "visual",
                        "provenance": "user-stated",
                    }
                }
            },
            {"preferences": {"medium": {"value": "visual", "provenance": "inferred"}}},
            {
                "preferences": {
                    "medium": {"value": "x" * 513, "provenance": "user-stated"}
                }
            },
            {"preferences": {"medium": {"value": True, "provenance": "user-stated"}}},
            {"covered_topics": ["x"] * 101},
            {"covered_topics": ["x" * 257]},
            {"covered_topics": "fractions"},
            {"covered_topics": [False]},
            {"last_lesson": {"id": "x", "position": "x", "score": 1}},
            {"agent_summary": {"text": "x" * 2049, "provenance": "agent-authored"}},
            {"agent_summary": {"text": "x", "provenance": "learner-authored"}},
            {"next_topic": {"value": "x", "provenance": "agent-authored"}},
        ]
        for data in cases:
            with self.subTest(data=str(data)[:100]):
                self.update(data, expected=6)
                self.assertEqual(target.read_bytes(), original)
        source = self.directory / "bad.json"
        for raw in (b"{bad", b"\xff", b"x" * 262145):
            source.write_bytes(raw)
            self.call(
                "continuity-update",
                "--data",
                str(source),
                "--expected-revision",
                "1",
                expected=6,
            )
            self.assertEqual(target.read_bytes(), original)

    def test_revisions_are_exact_bounded_integers(self):
        record = self.grant()
        for field in ("revision", "schema_version"):
            for value in (True, False, 1.0, "1", -1, 9007199254740992):
                candidate = copy.deepcopy(record)
                candidate[field] = value
                with (
                    self.subTest(field=field, value=value),
                    self.assertRaises(ValidationError),
                ):
                    validate_continuity_document(candidate)
        self.call("continuity-withdraw", "--expected-revision", "-1", expected=6)
        self.call(
            "continuity-reset",
            "--expected-revision",
            "9007199254740992",
            "--all",
            "--dry-run",
            expected=6,
        )

    def test_reset_after_extension_withdrawal_keeps_withdrawal_and_evidence(self):
        self.grant()
        self.update(
            {"preferences": {"detail": {"value": "deep", "provenance": "user-stated"}}}
        )
        evidence = (self.workspace / "state/sessions.jsonl").read_bytes()
        self.call("continuity-withdraw", "--expected-revision", "2")
        result = self.call(
            "continuity-reset",
            "--expected-revision",
            "3",
            "--preferences-only",
            "--confirm",
        )
        self.assertEqual(result["consent"]["status"], "withdrawn")
        self.assertEqual(result["preferences"], {})
        self.call("continuity-resume", expected=3)
        self.assertEqual(
            (self.workspace / "state/sessions.jsonl").read_bytes(), evidence
        )


if __name__ == "__main__":
    unittest.main()
