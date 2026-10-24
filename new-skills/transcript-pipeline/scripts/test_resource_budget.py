import io
import json

import requests
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



class CountingRaw(io.BytesIO):
    def __init__(self, data):
        super().__init__(data)
        self.consumed = 0

    def read(self, n=-1):
        value = super().read(n)
        self.consumed += len(value)
        return value


class SyntheticAdapter(requests.adapters.BaseAdapter):
    """Real Requests dispatch/redirect machinery; no DNS or socket transport."""
    def __init__(self, responses):
        self.responses = iter(responses)
        self.sent = []

    def send(self, request, **kwargs):
        self.sent.append(request)
        status, headers, raw = next(self.responses)
        response = requests.Response()
        response.request = request
        response.url = request.url
        response.status_code = status
        response.headers.update(headers)
        response.raw = raw
        return response

    def close(self):
        pass


class RealRequestsRedirectBudgetTests(unittest.TestCase):
    def session(self, responses, factory=False):
        session = enrichment._new_session() if factory else requests.Session()
        session.trust_env = False
        adapter = SyntheticAdapter(responses)
        session.mount("https://", adapter)
        self.addCleanup(session.close)
        return session, adapter

    def test_large_redirect_is_never_consumed_and_manual_follow_succeeds(self):
        for factory in (False, True):
            with self.subTest(factory=factory):
                redirect, final = CountingRaw(b"x" * (2 * 1024 * 1024)), CountingRaw(b"ok")
                session, adapter = self.session([
                    (302, {"location": "/end"}, redirect), (200, {}, final)
                ], factory=factory)
                observed = []
                session.hooks["response"].append(lambda response, **kw: observed.append(response.status_code))
                budget = budgets.JobBudget(max_transfer=3)
                with budgets.job_scope(budget):
                    response, body = enrichment.fetch_limited(session, "https://8.8.8.8/start", max_bytes=3)
                self.assertEqual(body, b"ok")
                self.assertEqual(response.url, "https://8.8.8.8/end")
                self.assertEqual(observed, [302, 200])
                self.assertEqual(len(adapter.sent), 2)
                self.assertTrue(redirect.closed)
                self.assertEqual(redirect.consumed, 0)
                self.assertEqual(final.consumed, budget.transfer)
                self.assertEqual(budget.transfer, 2)
                self.assertIsNone(budget.failure)

    def test_redirect_target_is_validated_before_next_send(self):
        for target in ("http://127.0.0.1/private", "https://8.8.4.4/other",
                       "http://8.8.8.8/other", "https://8.8.8.8:8443/other"):
            with self.subTest(target=target):
                raw = CountingRaw(b"x" * (2 * 1024 * 1024))
                session, adapter = self.session([(302, {"location": target}, raw)])
                session._credential_host = "8.8.8.8"
                with self.assertRaises(ValueError):
                    enrichment.fetch_limited(session, "https://8.8.8.8/start", max_bytes=3)
                self.assertEqual(len(adapter.sent), 1)
                self.assertEqual(raw.consumed, 0)
                self.assertTrue(raw.closed)

    def test_normal_body_still_enforces_response_and_aggregate_limits(self):
        for response_limit, transfer_limit, error in ((3, 100, ValueError), (100, 3, budgets.BudgetExceeded)):
            with self.subTest(response_limit=response_limit):
                raw = CountingRaw(b"0123456789")
                session, _ = self.session([(200, {}, raw)])
                budget = budgets.JobBudget(max_transfer=transfer_limit)
                with self.assertRaises(error), budgets.job_scope(budget):
                    enrichment.fetch_limited(session, "https://8.8.8.8/body", max_bytes=response_limit)
                self.assertEqual(raw.consumed, 10)
                self.assertEqual(budget.transfer, raw.consumed)
                self.assertTrue(raw.closed)

    def test_browser_redirect_is_empty_then_final_body_is_charged(self):
        redirect, final = CountingRaw(b"x" * (2 * 1024 * 1024)), CountingRaw(b"ok")
        session, adapter = self.session([(302, {"location": "/end"}, redirect), (200, {}, final)])
        budget = budgets.JobBudget(max_transfer=3)
        callback = self.browser_callback(session, budget)
        route = self.route("https://8.8.8.8/start")
        callback(route)
        route.abort.assert_not_called()
        route.fulfill.assert_called_once_with(status=302, headers={"location": "/end"}, body=b"")
        self.assertEqual(len(adapter.sent), 1)  # browser, not Requests, follows
        self.assertTrue(redirect.closed)
        self.assertEqual(redirect.consumed, 0)
        self.assertEqual(budget.transfer, 0)
        final_route = self.route("https://8.8.8.8/end")
        callback(final_route)
        final_route.fulfill.assert_called_once_with(status=200, headers={}, body=b"ok")
        self.assertEqual(budget.transfer, final.consumed)
        self.assertEqual(budget.transfer, 2)
        self.assertIsNone(budget.failure)

    def browser_callback(self, session, budget):
        context = mock.Mock()
        with mock.patch.object(enrichment, "_new_session", return_value=session), budgets.job_scope(budget):
            enrichment.install_browser_transport(context)
        return context.route.call_args.args[1]

    def route(self, url):
        route = mock.Mock()
        route.request.url = url
        route.request.method = "GET"
        route.request.post_data_buffer = None
        route.request.all_headers.return_value = {}
        return route

    def test_browser_normal_body_over_limits_aborts_and_accounts_consumption(self):
        for response_limit, transfer_limit in ((3, 100), (100, 3)):
            with self.subTest(response_limit=response_limit):
                raw = CountingRaw(b"0123456789")
                session, _ = self.session([(200, {}, raw)])
                budget = budgets.JobBudget(max_transfer=transfer_limit)
                callback = self.browser_callback(session, budget)
                route = self.route("https://8.8.8.8/body")
                with mock.patch.object(enrichment, "MAX_HTTP_BYTES", response_limit):
                    callback(route)
                route.fulfill.assert_not_called()
                route.abort.assert_called_once_with("blockedbyclient")
                self.assertEqual(raw.consumed, 10)
                self.assertEqual(budget.transfer, raw.consumed)
                self.assertTrue(raw.closed)


if __name__ == "__main__":
    unittest.main()
