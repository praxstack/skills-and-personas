#!/usr/bin/env python3
"""Frozen visual-route matrix validation regressions."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_workspace as validator


class VisualFixtureMatrixTests(unittest.TestCase):
    def manifest(self) -> dict[str, object]:
        return json.loads(
            (ROOT / validator.VISUAL_VERIFICATION_FIXTURE).read_text(encoding="utf-8")
        )

    def test_validator_recomputes_all_four_frozen_route_receipts(self) -> None:
        count, errors = validator.validate_visual_verification_fixture(ROOT)
        self.assertEqual(count, 4)
        self.assertEqual(errors, [])

    def test_missing_or_duplicate_route_cannot_pass_as_a_complete_matrix(self) -> None:
        missing = self.manifest()
        missing["cases"] = missing["cases"][:-1]
        with patch.object(validator, "_load_json_if_present", return_value=missing):
            count, errors = validator.validate_visual_verification_fixture(ROOT)
        self.assertEqual(count, 3)
        self.assertTrue(any("exactly four" in error for error in errors))
        self.assertTrue(any("incomplete" in error for error in errors))

        duplicate = copy.deepcopy(self.manifest())
        duplicate["cases"][3]["expected_route"] = "interactive"
        with patch.object(validator, "_load_json_if_present", return_value=duplicate):
            count, errors = validator.validate_visual_verification_fixture(ROOT)
        self.assertLess(count, 4)
        self.assertTrue(any("duplicate expected route" in error for error in errors))
        self.assertTrue(any("incomplete" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
