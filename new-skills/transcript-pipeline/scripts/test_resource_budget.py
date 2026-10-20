import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock

import resource_budget as budgets
import resource_enrichment as enrichment
from test_resource_enrichment import FakeResponse, FakeSession


class JobBudgetTests(unittest.TestCase):
    def test_failed_streams_still_consume_cumulative_transfer(self):
        budget = budgets.JobBudget(max_transfer=10)
        with self.assertRaises(budgets.BudgetExceeded), budgets.job_scope(budget):
            with self.assertRaises(ValueError):
                enrichment.read_limited_body(FakeResponse(chunks=[b"123456"]), 5)
            self.assertEqual(budget.transfer, 6)
            response = FakeResponse(chunks=[b"12345"])
            try:
                enrichment.read_limited_body(response, 10)
            finally:
                self.assertTrue(response.closed)
        self.assertEqual(budget.transfer, 11)
        with self.assertRaises(budgets.BudgetExceeded):
            budget.check()

    def test_resources_accumulate_across_sessions_before_network(self):
        budget = budgets.JobBudget(max_resources=1)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("first", "second"):
                path = root / name / ".pipeline"
                path.mkdir(parents=True)
                (path / "resource_manifest.json").write_text(json.dumps({
                    "resources": [{"name": "demo", "url": "https://8.8.8.8/"}]
                }))
            with mock.patch.object(enrichment, "_new_session") as factory:
                with mock.patch.object(enrichment, "enrich_generic_http") as provider:
                    provider.return_value = enrichment.EnrichmentResult(
                        "demo", "https://8.8.8.8/", "generic", "test", False,
                        "ok", 200, None, None, [], [], None)
                    with self.assertRaises(budgets.BudgetExceeded), budgets.job_scope(budget):
                        for name in ("first", "second"):
                            enrichment.enrich_session(root / name, None, None, None, None, True)
                    self.assertEqual(factory.call_count, 1)
                    self.assertEqual(provider.call_count, 1)

    def test_output_accounting_includes_overwrites_and_encoded_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.txt"
            budget = budgets.JobBudget(max_output=5)
            with self.assertRaises(budgets.BudgetExceeded), budgets.job_scope(budget):
                enrichment.save_text(path, "é", False)
                enrichment.save_bytes(path, b"1234", False)
            self.assertEqual(path.read_bytes(), "é".encode())

    def test_report_write_is_budgeted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(budgets.BudgetExceeded):
                enrichment.enrich_session(root, None, None, None, None, False,
                                          budget=budgets.JobBudget(max_output=1))
            self.assertFalse((root / ".resources/resource_enrichment_report.json").exists())

    def test_small_control_produces_report_and_restores_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = enrichment.enrich_session(root, None, None, None, None, False)
            self.assertEqual(result["resource_count"], 0)
            self.assertEqual(json.loads((root / ".resources/resource_enrichment_report.json").read_text()),
                             result)
            self.assertIsNone(budgets.CURRENT.get())

    def test_provider_cannot_convert_exhaustion_to_fallback_success(self):
        budget = budgets.JobBudget(max_transfer=1)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(budgets.BudgetExceeded), budgets.job_scope(budget):
                enrichment.enrich_generic_http(
                    FakeSession([FakeResponse(chunks=[b"too big"])]),
                    enrichment.ResourceItem("sample", "https://8.8.8.8/"),
                    Path(tmp), Path(tmp), False)

    def test_manifest_size_and_count_fail_before_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".pipeline"
            path.mkdir()
            manifest = path / "resource_manifest.json"
            for data in (' ' * (1024 * 1024 + 1),
                         json.dumps({"resources": [{}] * 101})):
                manifest.write_text(data)
                with self.assertRaises(ValueError):
                    enrichment.parse_manifest(Path(tmp))

    def test_hard_deadline_interrupts_blocking_operation(self):
        start = time.monotonic()
        with self.assertRaises(budgets.BudgetExceeded):
            with budgets.job_scope(budgets.JobBudget(seconds=0.05), hard_deadline=True):
                time.sleep(5)
        self.assertLess(time.monotonic() - start, 1)
        self.assertIsNone(budgets.CURRENT.get())

    def test_nested_scope_cannot_reset_deadline_or_consumption(self):
        budget = budgets.JobBudget(max_requests=1)
        with self.assertRaises(budgets.BudgetExceeded), budgets.job_scope(budget):
            budgets.charge("requests", 1)
            with budgets.job_scope(budgets.JobBudget(max_requests=100)):
                budgets.charge("requests", 1)


if __name__ == "__main__":
    unittest.main()
