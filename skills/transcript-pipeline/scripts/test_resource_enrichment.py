from __future__ import annotations

import importlib.util
import json
import socket
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


HERE = Path(__file__).resolve().parent
try:
    import requests
except ImportError:
    raise unittest.SkipTest("requests is required for transport security tests")

SPEC = importlib.util.spec_from_file_location("resource_enrichment", HERE / "resource_enrichment.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class FakeResponse:
    def __init__(self, *, status=200, headers=None, chunks=(), redirect=False):
        self.status_code = status
        self.headers = headers or {}
        self._chunks = list(chunks)
        self.is_redirect = redirect
        self.is_permanent_redirect = False
        self.encoding = "utf-8"
        self.url = ""
        self.closed = False

    def iter_content(self, chunk_size=0):
        yield from self._chunks

    def close(self):
        self.closed = True

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.urls = []

    def get(self, url, **kwargs):
        self.urls.append((url, kwargs))
        return next(self.responses)


class FakeCookieJar:
    def __init__(self):
        self.values = []

    def set(self, *args, **kwargs):
        self.values.append((args, kwargs))


class FakeNotionSession:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.cookies = FakeCookieJar()
        self.posts = []

    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        return next(self.responses)


class ResourceSecurityTests(unittest.TestCase):
    def test_connection_uses_checked_numeric_address_without_second_lookup(self):
        public = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]
        private = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]
        with mock.patch.object(MODULE.socket, "getaddrinfo", side_effect=[public, private]) as dns:
            with mock.patch.object(MODULE.socket, "socket") as sock:
                connection = MODULE.PublicHTTPSConnection("example.test", port=443, timeout=5)
                connection._new_conn()
                sock.return_value.connect.assert_called_once_with(("8.8.8.8", 443))
                self.assertEqual(dns.call_count, 1)
                self.assertEqual(connection.host, "example.test")

    def test_transport_rejects_rebinding_before_opening_socket(self):
        private = [(socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::1", 443, 0, 0))]
        with mock.patch.object(MODULE.socket, "getaddrinfo", return_value=private):
            with mock.patch.object(MODULE.socket, "socket") as sock:
                with self.assertRaises(ValueError):
                    MODULE.PublicHTTPSConnection("example.test", port=443, timeout=5)._new_conn()
                sock.assert_not_called()

    def test_adapter_used_for_both_schemes_and_no_proxy_bypass(self):
        session = MODULE._new_session()
        for scheme in ("http://", "https://"):
            adapter = session.get_adapter(scheme)
            self.assertIsInstance(adapter, MODULE.PublicNetworkAdapter)
            with self.assertRaises(ValueError):
                adapter.proxy_manager_for("http://localhost:8080")
        self.assertFalse(session.trust_env)

    def test_private_and_active_urls_are_rejected(self):
        for url in (
            "file:///etc/passwd",
            "http://127.0.0.1/admin",
            "http://169.254.169.254/latest/meta-data",
            "http://[::1]/",
            "https://user:pass@example.com/",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    MODULE.validate_remote_url(url)

    def test_dns_answer_set_must_be_entirely_public(self):
        answers = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.7", 443)),
        ]
        with mock.patch.object(MODULE.socket, "getaddrinfo", return_value=answers):
            with self.assertRaises(ValueError):
                MODULE.validate_remote_url("https://example.test/")

    def test_cookie_files_require_exact_domains_and_isolate_sessions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cookies.json"
            path.write_text(json.dumps({"session": "secret"}))
            with self.assertRaises(ValueError):
                MODULE.load_cookie_sessions(path)
            path.write_text(json.dumps([{"name": "session", "value": "secret", "domain": ".example.com"}]))
            with self.assertRaises(ValueError):
                MODULE.load_cookie_sessions(path)
            path.write_text(json.dumps([
                {"name": "session", "value": "a", "domain": "a.example.com"},
                {"name": "session", "value": "b", "domain": "b.example.com"},
            ]))
            sessions = MODULE.load_cookie_sessions(path)
            self.assertEqual(set(sessions), {"a.example.com", "b.example.com"})
            self.assertNotEqual(id(sessions["a.example.com"]), id(sessions["b.example.com"]))

    def test_redirect_is_revalidated_before_following(self):
        first = FakeResponse(status=302, headers={"location": "http://127.0.0.1/private"}, redirect=True)
        session = FakeSession([first])
        with mock.patch.object(MODULE, "validate_remote_url", wraps=MODULE.validate_remote_url):
            with self.assertRaises(ValueError):
                MODULE.fetch_limited(session, "https://8.8.8.8/start")
        self.assertEqual(len(session.urls), 1)
        self.assertTrue(first.closed)

    def test_authenticated_session_cannot_change_origin(self):
        self.assertTrue(MODULE.provider_https_origin("https://www.canva.com/path", "canva.com"))
        self.assertFalse(MODULE.provider_https_origin("http://www.canva.com/path", "canva.com"))
        self.assertFalse(MODULE.provider_https_origin("https://www.canva.com:8443/path", "canva.com"))
        redirect = FakeResponse(status=302, headers={"location": "https://8.8.4.4/other"}, redirect=True)
        session = FakeSession([redirect])
        session._credential_host = "8.8.8.8"
        with self.assertRaises(ValueError):
            MODULE.fetch_limited(session, "https://8.8.8.8/start")
        self.assertEqual(len(session.urls), 1)

    def test_decoded_body_budget_is_enforced(self):
        response = FakeResponse(chunks=[b"1234", b"5678"])
        with self.assertRaises(ValueError):
            MODULE.fetch_limited(FakeSession([response]), "https://8.8.8.8/", max_bytes=7)
        self.assertTrue(response.closed)

    def test_notion_credentials_are_exact_host_and_redirects_are_not_followed(self):
        redirect = FakeResponse(status=302, headers={"location": "https://evil.example/"}, redirect=True)
        session = FakeNotionSession([redirect])
        with mock.patch.object(MODULE, "_new_session", return_value=session):
            with self.assertRaises(ValueError):
                MODULE.notion_load_page_chunks("00000000-0000-0000-0000-000000000000", "secret", "user")
        self.assertEqual(session.cookies.values[0][1]["domain"], "www.notion.so")
        self.assertFalse(session.posts[0][1]["allow_redirects"])
        self.assertTrue(redirect.closed)

    def test_storage_state_keeps_only_provider_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            path.write_text(json.dumps({
                "cookies": [
                    {"name": "c", "value": "1", "domain": ".canva.com"},
                    {"name": "x", "value": "2", "domain": ".private.example"},
                ],
                "origins": [
                    {"origin": "https://www.canva.com", "localStorage": []},
                    {"origin": "https://private.example", "localStorage": [{"name": "token", "value": "x"}]},
                ],
            }))
            state = MODULE.sanitize_playwright_state(path, "canva.com")
            self.assertEqual(len(state["cookies"]), 1)
            self.assertEqual(len(state["origins"]), 1)


if __name__ == "__main__":
    unittest.main()
