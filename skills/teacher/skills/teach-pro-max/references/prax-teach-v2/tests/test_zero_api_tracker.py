import importlib.util
import os
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/update_zero_api_tracker.py"
SPEC = importlib.util.spec_from_file_location("zero_api_tracker", SCRIPT)
assert SPEC and SPEC.loader
TRACKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TRACKER)


class ZeroApiTrackerTests(unittest.TestCase):
    def test_json_status_cannot_turn_failure_into_verified(self):
        self.assertFalse(TRACKER.json_evidence_usable("ZV-02", {"status": "failed"}))
        self.assertFalse(TRACKER.json_evidence_usable("ZV-02", ["not", "a", "receipt"]))
        self.assertTrue(
            TRACKER.json_evidence_usable("ZV-29", {"status": "prepared-not-run"})
        )

    def test_deferred_lean_decision_remains_pending(self):
        self.assertFalse(
            TRACKER.json_evidence_usable(
                "ZV-25", {"status": "engineering-prepared", "decision": "deferred"}
            )
        )

    def test_tracker_updates_the_repository_catalog_not_a_missing_copy(self):
        self.assertEqual(
            TRACKER.TRACKER,
            ROOT.parents[3]
            / "docs/teach-pro-max/research/09-zero-api-visual-runtime-tracker.json",
        )

    def test_tracker_timestamp_is_source_date_epoch_derived(self):
        with mock.patch.dict(os.environ, {"SOURCE_DATE_EPOCH": "1785844800"}):
            self.assertEqual(TRACKER.tracker_timestamp(), "2026-08-04T12:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
