#!/usr/bin/env python3
"""Frozen visual-route matrix validation regressions."""

from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_workspace as validator
from current_evidence import export_original

from tests import test_review_receipts as review_test_helpers


class VisualFixtureMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original_temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.original_temp.cleanup)
        base = Path(cls.original_temp.name).resolve()
        cls.original = base / "original"
        export_original(ROOT, cls.original, base / "inventory.json")
        shutil.copytree(ROOT / "node_modules", cls.original / "node_modules")
        cls.current = base / "mutable-current-fixture"
        cls.current.mkdir()
        review_test_helpers.ReviewReceiptTests().install_visual_verification_fixture(
            cls.current
        )

    def manifest(self) -> dict[str, object]:
        return json.loads(
            (ROOT / validator.VISUAL_VERIFICATION_FIXTURE).read_text(encoding="utf-8")
        )

    def test_validator_recomputes_all_four_frozen_route_receipts(self) -> None:
        count, errors = validator.validate_visual_verification_fixture(self.original)
        self.assertEqual(count, 4)
        self.assertEqual(errors, [])

    def test_missing_or_duplicate_route_cannot_pass_as_a_complete_matrix(self) -> None:
        missing = self.manifest()
        missing["cases"] = missing["cases"][:-1]
        with patch.object(validator, "_load_json_if_present", return_value=missing):
            count, errors = validator.validate_visual_verification_fixture(
                self.original
            )
        self.assertEqual(count, 3)
        self.assertTrue(any("exactly four" in error for error in errors))
        self.assertTrue(any("incomplete" in error for error in errors))

        duplicate = copy.deepcopy(self.manifest())
        duplicate["cases"][3]["expected_route"] = "interactive"
        with patch.object(validator, "_load_json_if_present", return_value=duplicate):
            count, errors = validator.validate_visual_verification_fixture(
                self.original
            )
        self.assertLess(count, 4)
        self.assertTrue(any("duplicate expected route" in error for error in errors))
        self.assertTrue(any("incomplete" in error for error in errors))

    def test_current_implementation_replays_newly_bound_four_route_fixture(
        self,
    ) -> None:
        count, errors = validator.validate_visual_verification_fixture(self.current)
        self.assertEqual((count, errors), (4, []))

    def test_current_implementation_rejects_missing_and_duplicate_route(self) -> None:
        manifest = json.loads(
            (self.current / validator.VISUAL_VERIFICATION_FIXTURE).read_text()
        )
        missing = copy.deepcopy(manifest)
        missing["cases"].pop()
        with patch.object(validator, "_load_json_if_present", return_value=missing):
            count, errors = validator.validate_visual_verification_fixture(self.current)
        self.assertEqual(count, 3)
        self.assertTrue(any("exactly four" in error for error in errors))
        self.assertTrue(any("incomplete" in error for error in errors))
        duplicate = copy.deepcopy(manifest)
        duplicate["cases"][3]["expected_route"] = "interactive"
        with patch.object(validator, "_load_json_if_present", return_value=duplicate):
            count, errors = validator.validate_visual_verification_fixture(self.current)
        self.assertLess(count, 4)
        self.assertTrue(any("duplicate expected route" in error for error in errors))
        self.assertTrue(any("incomplete" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
