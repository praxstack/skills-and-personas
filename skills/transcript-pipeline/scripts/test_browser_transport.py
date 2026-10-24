"""Real browser control: public response is brokered, local and WS egress blocked."""
import os
import faulthandler
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import resource_enrichment as module
    from playwright.sync_api import sync_playwright
except ImportError:
    raise unittest.SkipTest("requests and Playwright required")


@unittest.skipUnless(os.environ.get("TEACHER_BROWSER_TESTS") == "1", "explicit browser test opt-in")
class BrowserTransport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        faulthandler.dump_traceback_later(45, exit=True)

    @classmethod
    def tearDownClass(cls):
        faulthandler.cancel_dump_traceback_later()

    def test_actual_callback_keeps_job_budget_and_blocks_oversized_response(self):
        body = b"<html><title>Budget control</title></html>"
        for maximum in (1, 1024):
            budget = module.budgets.JobBudget(max_transfer=maximum)
            session = module._new_session()
            def request(*args, **kwargs):
                self.assertIs(module.budgets.CURRENT.get(), budget)
                response = mock.Mock()
                response.status_code = 200
                response.headers = {"content-type": "text/html"}
                response.iter_content.return_value = [body]
                return response
            session.request = request
            # Bind during registration, then leave the context before callbacks.
            # The browser must retain the same job even across Playwright greenlets.
            with sync_playwright() as pw, mock.patch.object(module, "_new_session", return_value=session):
                token = module.budgets.CURRENT.set(budget)
                try:
                    browser, context = module.new_public_browser_context(
                        pw, executable_path=os.environ.get("CHROMIUM_PATH"))
                finally:
                    module.budgets.CURRENT.reset(token)
                try:
                    page = context.new_page()
                    if maximum == 1:
                        with self.assertRaises(Exception):
                            page.goto("https://8.8.8.8/budget", timeout=5000)
                        with self.assertRaises(module.BudgetExceeded):
                            budget.check()
                    else:
                        page.goto("https://8.8.8.8/budget", timeout=5000)
                        self.assertEqual(page.title(), "Budget control")
                        budget.check()
                    self.assertGreaterEqual(budget.transfer, len(body))
                finally:
                    context.close()
                    browser.close()

    def test_public_broker_and_blocked_local_and_websocket(self):
        session = module._new_session()
        seen = []
        def request(method, url, **kwargs):
            seen.append(url)
            response = mock.Mock()
            response.status_code = 200
            response.headers = {"content-type": "text/html"}
            response.iter_content.return_value = [b"<html><title>Public control</title><body>control</body></html>"]
            return response
        session.request = request
        with sync_playwright() as pw, mock.patch.object(module, "_new_session", return_value=session):
            browser, context = module.new_public_browser_context(pw, executable_path=os.environ.get("CHROMIUM_PATH"))
            try:
                page = context.new_page()
                page.goto("https://8.8.8.8/control")
                self.assertEqual(page.title(), "Public control")
                result = page.evaluate("""async () => {
                  try { await fetch('http://127.0.0.1/private'); return 'leaked'; }
                  catch { return 'blocked'; }
                }""")
                self.assertEqual(result, "blocked")
                ws = page.evaluate("""() => new Promise(resolve => {
                  const socket = new WebSocket('wss://8.8.8.8/socket');
                  socket.onclose = () => resolve('blocked');
                  socket.onopen = () => { socket.send('test'); setTimeout(() => {socket.close(); resolve('isolated');}, 100); };
                  socket.onerror = () => resolve('blocked');
                  setTimeout(() => resolve('timeout'), 3000);
                })""")
                self.assertIn(ws, {"blocked", "isolated"})
                self.assertTrue(seen)
                self.assertTrue(all(url.startswith("https://8.8.8.8/") for url in seen))
            finally:
                context.close()
                browser.close()


if __name__ == "__main__":
    unittest.main()
