#!/usr/bin/env python3
"""Authenticated resource enrichment for transcript session folders.

This script enriches session resources listed in:
  <session>/.pipeline/resource_manifest.json

Supported providers:
  - Notion: authenticated block extraction via unofficial API v3
  - Canva: authenticated browser capture via Playwright storage state
  - Generic HTTP fallback for any URL (HTML title/content snapshot)

It writes:
  - <session>/.resources/resource_enrichment_report.json
  - provider-specific extracted artifacts under <session>/.resources/
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import socket
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection, HTTPSConnection
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool


class PublicConnectionMixin:
    """Resolve once, inspect every answer, then connect to numeric addresses only.

    Keep self.host unchanged for HTTP Host, TLS SNI and certificate verification.
    No process-global resolver hooks and no second hostname lookup at connect.
    """
    def _new_conn(self):
        answers = socket.getaddrinfo(self.host, self.port, type=socket.SOCK_STREAM)
        if not answers or any(not _public_ip(row[4][0]) for row in answers):
            raise ValueError("connection target has a non-public DNS answer")
        last_error = None
        for family, kind, protocol, _, address in answers:
            sock = socket.socket(family, kind, protocol)
            try:
                sock.settimeout(self.timeout)
                for option in self.socket_options or []:
                    sock.setsockopt(*option)
                sock.connect(address)  # numeric sockaddr from the checked result
                return sock
            except OSError as exc:
                sock.close()
                last_error = exc
        raise OSError("could not connect to a validated public address") from last_error


class PublicHTTPConnection(PublicConnectionMixin, HTTPConnection):
    pass


class PublicHTTPSConnection(PublicConnectionMixin, HTTPSConnection):
    pass


class PublicHTTPPool(HTTPConnectionPool):
    ConnectionCls = PublicHTTPConnection


class PublicHTTPSPool(HTTPSConnectionPool):
    ConnectionCls = PublicHTTPSConnection


class PublicNetworkAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        super().init_poolmanager(*args, **kwargs)
        self.poolmanager.pool_classes_by_scheme = {
            "http": PublicHTTPPool, "https": PublicHTTPSPool,
        }

    def proxy_manager_for(self, *args, **kwargs):
        raise ValueError("resource fetching does not allow proxy transports")

    def send(self, request, **kwargs):
        validate_remote_url(request.url, resolve_dns=False)
        if kwargs.get("proxies"):
            raise ValueError("resource fetching does not allow proxy transports")
        return super().send(request, **kwargs)


DEFAULT_ROOT = Path.cwd()
MAX_HTTP_BYTES = 10 * 1024 * 1024
MAX_PDF_BYTES = 25 * 1024 * 1024
MAX_REDIRECTS = 5
MAX_BROWSER_HTML_BYTES = 10 * 1024 * 1024
MAX_BROWSER_PAGE_HEIGHT = 20_000
MAX_BROWSER_ARTIFACT_BYTES = 25 * 1024 * 1024
MAX_NOTION_CHUNK_BYTES = 10 * 1024 * 1024


@dataclass
class ResourceItem:
    name: str
    url: str


@dataclass
class EnrichmentResult:
    name: str
    url: str
    provider: str
    method: str
    authenticated: bool
    status: str
    http_status: int | None
    final_url: str | None
    title: str | None
    output_files: list[str]
    notes: list[str]
    error: str | None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "resource"


def detect_provider(url: str) -> str:
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    if host == "notion.so" or host.endswith(".notion.so"):
        return "notion"
    if host == "canva.com" or host.endswith(".canva.com"):
        return "canva"
    if host in {"drive.google.com", "docs.google.com"}:
        return "google-drive"
    return "generic"


def parse_manifest(session_dir: Path) -> list[ResourceItem]:
    manifest_path = session_dir / ".pipeline" / "resource_manifest.json"
    if not manifest_path.exists():
        return []
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    resources_raw = data.get("resources", [])
    items: list[ResourceItem] = []
    for row in resources_raw:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name", "")).strip()
        url = str(row.get("url", "")).strip()
        if not name or not url:
            continue
        items.append(ResourceItem(name=name, url=url))
    return items


def _new_session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    session.mount("https://", PublicNetworkAdapter())
    session.mount("http://", PublicNetworkAdapter())
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    return session


def load_cookie_sessions(cookies_json: Path) -> dict[str, requests.Session]:
    """Load exact-host cookies into separate sessions.

    A global cookie jar is unsafe because a manifest controls the destination.
    Legacy dictionary-form files have no recipient host and are rejected.
    """
    payload = json.loads(cookies_json.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        raise ValueError("dictionary cookie files are unsafe: every cookie needs an exact domain")
    if not isinstance(payload, list):
        raise ValueError("cookies JSON must be a list of domain-scoped cookie objects")
    sessions: dict[str, requests.Session] = {}
    for row in payload:
        if not isinstance(row, dict):
            raise ValueError("every cookie entry must be an object")
        name = str(row.get("name", "")).strip()
        value = row.get("value")
        domain = str(row.get("domain", "")).strip().lower().rstrip(".")
        path = str(row.get("path", "/"))
        if not name or value is None or not domain or domain.startswith("."):
            raise ValueError("every cookie needs a name, value, and exact domain without a leading dot")
        if "/" in domain or "\\" in domain or ":" in domain:
            raise ValueError(f"invalid cookie domain: {domain}")
        session = sessions.setdefault(domain, _new_session())
        setattr(session, "_credential_host", domain)
        session.cookies.set(name, str(value), domain=domain, path=path, secure=True)
    return sessions


def _public_ip(address: str) -> bool:
    ip = ipaddress.ip_address(address.split("%", 1)[0])
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_remote_url(url: str, *, resolve_dns: bool = True) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("resource URL must use http or https")
    if parsed.username or parsed.password:
        raise ValueError("resource URL must not contain credentials")
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        raise ValueError("resource URL has no host")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        literal = ipaddress.ip_address(host.split("%", 1)[0])
    except ValueError:
        literal = None
    if literal is not None:
        if not _public_ip(str(literal)):
            raise ValueError("resource URL resolves to a non-public address")
    elif resolve_dns:
        answers = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        if not answers:
            raise ValueError("resource host did not resolve")
        addresses = {row[4][0] for row in answers}
        if any(not _public_ip(address) for address in addresses):
            raise ValueError("resource host resolves to a non-public address")
    return parsed.geturl()


def read_limited_body(response: requests.Response, max_bytes: int) -> bytes:
    """Read a streamed, decoded response without crossing the byte budget."""
    length = response.headers.get("content-length")
    if length:
        try:
            declared = int(length)
        except ValueError:
            declared = None
        if declared is not None and declared > max_bytes:
            response.close()
            raise ValueError(f"resource exceeds {max_bytes} bytes")
    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        total += len(chunk)
        if total > max_bytes:
            response.close()
            raise ValueError(f"resource exceeds {max_bytes} bytes")
        chunks.append(chunk)
    return b"".join(chunks)


def fetch_limited(
    session: requests.Session,
    url: str,
    *,
    max_bytes: int = MAX_HTTP_BYTES,
    timeout: int = 40,
) -> tuple[requests.Response, bytes]:
    """Fetch a public resource with manual, revalidated redirects and a decoded-byte budget."""
    current = validate_remote_url(url)
    seen: set[str] = set()
    for _ in range(MAX_REDIRECTS + 1):
        if current in seen:
            raise ValueError("redirect loop")
        seen.add(current)
        credential_host = getattr(session, "_credential_host", None)
        current_parts = urlparse(current)
        if credential_host and (
            (current_parts.hostname or "").lower().rstrip(".") != credential_host
            or current_parts.scheme != "https"
            or (current_parts.port not in {None, 443})
        ):
            raise ValueError("authenticated resource redirected outside its exact HTTPS origin")
        response = session.get(current, timeout=timeout, allow_redirects=False, stream=True)
        if response.is_redirect or response.is_permanent_redirect:
            location = response.headers.get("location")
            response.close()
            if not location:
                raise ValueError("redirect response has no location")
            current = validate_remote_url(urljoin(current, location))
            continue
        body = read_limited_body(response, max_bytes)
        response.url = current
        return response, body
    raise ValueError(f"resource exceeded {MAX_REDIRECTS} redirects")


def response_text(response: requests.Response, body: bytes) -> str:
    encoding = response.encoding or "utf-8"
    return body.decode(encoding, errors="replace")


def sanitize_playwright_state(path: Path, provider: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Playwright storage state must be an object")

    def allowed_host(host: str) -> bool:
        host = host.lower().lstrip(".").rstrip(".")
        return host == provider or host.endswith(f".{provider}")

    cookies = [
        row for row in payload.get("cookies", [])
        if isinstance(row, dict) and allowed_host(str(row.get("domain", "")))
    ]
    origins = []
    for row in payload.get("origins", []):
        if not isinstance(row, dict):
            continue
        host = urlparse(str(row.get("origin", ""))).hostname or ""
        if allowed_host(host):
            origins.append(row)
    return {"cookies": cookies, "origins": origins}


def _browser_request_allowed(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme in {"data", "blob"}:
        return len(url) <= MAX_HTTP_BYTES
    try:
        validate_remote_url(url)
        return True
    except Exception:
        return False


def new_public_browser_context(playwright, state=None, executable_path=None):
    browser = playwright.chromium.launch(headless=True, executable_path=executable_path, args=[
        "--proxy-server=http://127.0.0.1:9", "--proxy-bypass-list=<-loopback>",
        "--host-resolver-rules=MAP * ~NOTFOUND", "--disable-quic",
        "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
    ])
    context = browser.new_context(storage_state=state, service_workers="block",
                                  viewport={"width": 1440, "height": 1200})
    if not hasattr(context, "route_web_socket"):
        browser.close()
        raise RuntimeError("Canva capture requires Playwright WebSocket blocking support")
    # A route with no connect_to_server() is a local sink: no upstream
    # socket is opened. Avoid a synchronous close inside the WS dispatch.
    context.route_web_socket("**/*", lambda ws: ws.on_message(lambda message: None))
    install_browser_transport(context)
    return browser, context


def provider_https_origin(url: str, provider: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    return (parsed.scheme == "https" and parsed.port in {None, 443}
            and (host == provider or host.endswith("." + provider)))


def install_browser_transport(context):
    broker = _new_session()
    remaining = [100 * 1024 * 1024]
    context.on("close", lambda: broker.close())

    def fulfill_public(route):
        try:
            request = route.request
            target = validate_remote_url(request.url)
            if remaining[0] <= 0:
                raise ValueError("browser transfer budget exhausted")
            headers = {k: v for k, v in request.all_headers().items()
                       if k.lower() not in {"host", "connection", "content-length", "accept-encoding"}}
            host = (urlparse(target).hostname or "").lower().rstrip(".")
            if not provider_https_origin(target, "canva.com"):
                headers = {k: v for k, v in headers.items()
                           if k.lower() not in {"cookie", "authorization"}}
            post = request.post_data_buffer
            if post and len(post) > MAX_HTTP_BYTES:
                raise ValueError("browser request body exceeds byte budget")
            # Browser storage owns cookies. Do not let the HTTP broker grow a
            # second jar that can attach cookies after the header filter.
            broker.cookies.clear()
            response = broker.request(request.method, target, headers=headers,
                                      data=post, stream=True,
                                      allow_redirects=False, timeout=30)
            try:
                body = read_limited_body(response, min(MAX_HTTP_BYTES, remaining[0]))
                remaining[0] -= len(body)
                response_headers = {k: v for k, v in response.headers.items()
                                    if k.lower() not in {"content-encoding", "transfer-encoding", "content-length"}}
                route.fulfill(status=response.status_code, headers=response_headers, body=body)
            finally:
                response.close()
        except Exception:
            route.abort("blockedbyclient")

    context.route("**/*", fulfill_public)


def extract_html_title(text: str) -> str | None:
    m = re.search(r"<title[^>]*>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    return " ".join(m.group(1).split())


def save_text(path: Path, text: str, dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", errors="ignore")


def save_bytes(path: Path, blob: bytes, dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(blob)


def to_rel(path: Path, session_dir: Path) -> str:
    return str(path.relative_to(session_dir))


def extract_drive_file_id(url: str) -> str | None:
    m = re.search(r"/d/([A-Za-z0-9_-]+)", url)
    if m:
        return m.group(1)
    m = re.search(r"[?&]id=([A-Za-z0-9_-]+)", url)
    if m:
        return m.group(1)
    return None


def parse_notion_page_id(url: str) -> str | None:
    parsed = urlparse(url)
    candidate = parsed.path.strip("/").split("/")[-1]
    candidate = candidate.split("?")[0]
    candidate = candidate.split("#")[0]

    m_hyphen = re.search(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", candidate)
    if m_hyphen:
        return m_hyphen.group(1).lower()
    m_flat = re.search(r"([0-9a-fA-F]{32})", candidate)
    if not m_flat:
        m_flat = re.search(r"([0-9a-fA-F]{32})", parsed.path)
    if m_flat:
        raw = m_flat.group(1).lower()
        return f"{raw[0:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:32]}"
    return None


def notion_load_page_chunks(
    page_id: str,
    token_v2: str,
    active_user: str,
    timeout: int = 45,
    max_calls: int = 30,
) -> tuple[list[dict[str, Any]], list[str]]:
    endpoint = "https://www.notion.so/api/v3/loadCachedPageChunk"
    headers = {
        "content-type": "application/json",
        "x-notion-active-user-header": active_user,
        "user-agent": "Mozilla/5.0",
    }
    session = _new_session()
    setattr(session, "_credential_host", "www.notion.so")
    session.cookies.set("token_v2", token_v2, domain="www.notion.so", path="/", secure=True)
    cursor: dict[str, Any] = {"stack": []}
    chunks: list[dict[str, Any]] = []
    notes: list[str] = []

    for idx in range(max_calls):
        payload = {
            "page": {"id": page_id},
            "limit": 100,
            "cursor": cursor,
            "chunkNumber": idx,
            "verticalColumns": False,
        }
        resp = session.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=timeout,
            allow_redirects=False,
            stream=True,
        )
        try:
            if resp.is_redirect or resp.is_permanent_redirect:
                raise ValueError("authenticated Notion API redirected; credentials were not forwarded")
            body = read_limited_body(resp, MAX_NOTION_CHUNK_BYTES)
            resp.raise_for_status()
            data = json.loads(body)
        finally:
            resp.close()
        chunks.append(data)

        nxt = data.get("cursor")
        if not nxt or nxt == cursor:
            break
        cursor = nxt
    else:
        notes.append("Reached max_calls while paginating Notion chunks; output may be partial.")

    return chunks, notes


def notion_extract_markdown(chunks: list[dict[str, Any]], page_id: str) -> str:
    blocks: dict[str, dict[str, Any]] = {}
    for c in chunks:
        record_map = c.get("recordMap", {})
        bmap = record_map.get("block", {})
        for bid, payload in bmap.items():
            value = payload.get("value")
            if isinstance(value, dict):
                blocks[bid] = value

    def get_text(block: dict[str, Any]) -> str:
        props = block.get("properties", {})
        title = props.get("title")
        if not isinstance(title, list):
            return ""
        fragments: list[str] = []
        for seg in title:
            if isinstance(seg, list) and seg:
                fragments.append(str(seg[0]))
        return "".join(fragments).strip()

    lines: list[str] = []
    visited: set[str] = set()

    def visit(block_id: str, depth: int) -> None:
        if block_id in visited:
            return
        visited.add(block_id)
        block = blocks.get(block_id)
        if not block:
            return
        txt = get_text(block)
        btype = block.get("type", "text")

        if txt:
            if btype in {"header", "sub_header", "sub_sub_header"}:
                level = {"header": 1, "sub_header": 2, "sub_sub_header": 3}.get(btype, 2)
                lines.append(f"{'#' * level} {txt}")
            elif btype == "numbered_list":
                lines.append(("  " * max(depth - 1, 0)) + f"1. {txt}")
            elif btype == "bulleted_list":
                lines.append(("  " * max(depth - 1, 0)) + f"- {txt}")
            else:
                lines.append(("  " * max(depth - 1, 0)) + txt)

        for child in block.get("content", []) or []:
            visit(str(child), depth + 1)

    root_variants = [page_id, page_id.replace("-", "")]
    root = None
    for rid in root_variants:
        if rid in blocks:
            root = rid
            break

    if root is None and blocks:
        # Fallback: best-effort traversal from first known block.
        root = next(iter(blocks.keys()))

    if root is not None:
        visit(root, 0)

    out = "\n\n".join([ln for ln in lines if ln.strip()])
    return out.strip() + ("\n" if out else "")


def enrich_generic_http(
    session: requests.Session,
    item: ResourceItem,
    session_dir: Path,
    resources_dir: Path,
    dry_run: bool,
    authenticated: bool = False,
) -> EnrichmentResult:
    filename = f"{slug(item.name)}.html"
    out_path = resources_dir / filename
    try:
        resp, body = fetch_limited(session, item.url)
        text = response_text(resp, body)
        title = extract_html_title(text)
        save_text(out_path, text, dry_run=dry_run)
        return EnrichmentResult(
            name=item.name,
            url=item.url,
            provider=detect_provider(item.url),
            method="generic-http-fetch",
            authenticated=authenticated,
            status="ok",
            http_status=resp.status_code,
            final_url=str(resp.url),
            title=title,
            output_files=[to_rel(out_path, session_dir)],
            notes=[],
            error=None,
        )
    except Exception as exc:  # pragma: no cover - runtime/network dependent
        return EnrichmentResult(
            name=item.name,
            url=item.url,
            provider=detect_provider(item.url),
            method="generic-http-fetch",
            authenticated=False,
            status="error",
            http_status=None,
            final_url=None,
            title=None,
            output_files=[],
            notes=[],
            error=str(exc),
        )


def enrich_google_drive(
    session: requests.Session,
    item: ResourceItem,
    session_dir: Path,
    resources_dir: Path,
    dry_run: bool,
) -> EnrichmentResult:
    base = enrich_generic_http(session, item, session_dir, resources_dir, dry_run)
    file_id = extract_drive_file_id(item.url)
    if not file_id:
        return base

    try:
        dl_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        resp, body = fetch_limited(session, dl_url, max_bytes=MAX_PDF_BYTES, timeout=60)
        ctype = resp.headers.get("content-type", "").lower()
        if resp.status_code == 200 and ("pdf" in ctype or body.startswith(b"%PDF")):
            pdf_path = resources_dir / f"{slug(item.name)}.pdf"
            save_bytes(pdf_path, body, dry_run=dry_run)
            base.output_files.append(to_rel(pdf_path, session_dir))
            base.notes.append("Google Drive direct PDF export captured.")
        return base
    except Exception as exc:  # pragma: no cover - runtime/network dependent
        base.notes.append(f"Google Drive PDF export attempt failed: {exc}")
        return base


def enrich_notion(
    session: requests.Session,
    item: ResourceItem,
    session_dir: Path,
    resources_dir: Path,
    token_v2: str | None,
    active_user: str | None,
    dry_run: bool,
) -> EnrichmentResult:
    fallback = enrich_generic_http(session, item, session_dir, resources_dir, dry_run)
    fallback.provider = "notion"

    if not token_v2 or not active_user:
        fallback.notes.append("No NOTION_TOKEN_V2 / NOTION_ACTIVE_USER provided; using public HTML snapshot only.")
        return fallback

    page_id = parse_notion_page_id(item.url)
    if not page_id:
        fallback.notes.append("Could not parse Notion page ID from URL; using public HTML snapshot only.")
        return fallback

    try:
        chunks, notes = notion_load_page_chunks(page_id=page_id, token_v2=token_v2, active_user=active_user)
        md = notion_extract_markdown(chunks, page_id=page_id)
        md_path = resources_dir / f"{slug(item.name)}.notion.md"
        raw_path = resources_dir / f"{slug(item.name)}.notion.raw.json"

        save_text(md_path, md, dry_run=dry_run)
        save_text(raw_path, json.dumps(chunks, ensure_ascii=False, indent=2), dry_run=dry_run)

        fallback.method = "notion-api-v3-loadCachedPageChunk"
        fallback.authenticated = True
        fallback.output_files.extend([to_rel(md_path, session_dir), to_rel(raw_path, session_dir)])
        fallback.notes.extend(notes)
        return fallback
    except Exception as exc:  # pragma: no cover - runtime/network dependent
        fallback.notes.append(f"Authenticated Notion extraction failed: {exc}")
        return fallback


def enrich_canva(
    session: requests.Session,
    item: ResourceItem,
    session_dir: Path,
    resources_dir: Path,
    playwright_storage_state: Path | None,
    dry_run: bool,
) -> EnrichmentResult:
    fallback = enrich_generic_http(session, item, session_dir, resources_dir, dry_run)
    fallback.provider = "canva"

    if playwright_storage_state is None:
        fallback.notes.append("No Playwright storage-state provided; Canva authenticated capture skipped.")
        return fallback
    if not playwright_storage_state.exists():
        fallback.notes.append(f"Playwright storage-state not found: {playwright_storage_state}")
        return fallback

    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        fallback.notes.append(f"Playwright unavailable: {exc}")
        return fallback

    html_path = resources_dir / f"{slug(item.name)}.canva-auth.html"
    png_path = resources_dir / f"{slug(item.name)}.canva-auth.png"
    pdf_path = resources_dir / f"{slug(item.name)}.canva-auth.pdf"

    try:
        if dry_run:
            fallback.method = "playwright-auth-capture"
            fallback.authenticated = True
            fallback.notes.append("Dry-run: skipped browser launch.")
            return fallback

        with sync_playwright() as p:
            # Browser sockets have no usable proxy or DNS route. All HTTP(S)
            # responses are fulfilled by the pinned public-only Python transport.
            state = sanitize_playwright_state(playwright_storage_state, "canva.com")
            browser, context = new_public_browser_context(p, state)
            page = context.new_page()
            target = validate_remote_url(item.url)
            target_host = (urlparse(target).hostname or "").lower().rstrip(".")
            if not provider_https_origin(target, "canva.com"):
                raise ValueError("authenticated Canva capture requires a canva.com HTTPS origin on port 443")
            page.goto(target, wait_until="networkidle", timeout=90000)
            page.wait_for_timeout(2000)

            final_host = (urlparse(page.url).hostname or "").lower().rstrip(".")
            if not provider_https_origin(page.url, "canva.com"):
                raise ValueError("authenticated Canva capture redirected outside canva.com")
            height = page.evaluate("Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)")
            if int(height or 0) > MAX_BROWSER_PAGE_HEIGHT:
                raise ValueError(f"browser page exceeds {MAX_BROWSER_PAGE_HEIGHT}px height")

            html = page.content()
            if len(html.encode("utf-8")) > MAX_BROWSER_HTML_BYTES:
                raise ValueError(f"browser HTML exceeds {MAX_BROWSER_HTML_BYTES} bytes")
            save_text(html_path, html, dry_run=False)
            page.screenshot(path=str(png_path), full_page=False)
            if png_path.stat().st_size > MAX_BROWSER_ARTIFACT_BYTES:
                png_path.unlink(missing_ok=True)
                raise ValueError("browser screenshot exceeded artifact budget")
            fallback.output_files.extend([to_rel(html_path, session_dir), to_rel(png_path, session_dir)])
            fallback.method = "playwright-auth-capture"
            fallback.authenticated = True
            fallback.final_url = page.url
            fallback.title = page.title()

            try:
                page.pdf(path=str(pdf_path), print_background=True)
                if pdf_path.stat().st_size > MAX_BROWSER_ARTIFACT_BYTES:
                    pdf_path.unlink(missing_ok=True)
                    fallback.notes.append("Page PDF exceeded the artifact budget and was removed.")
                else:
                    fallback.output_files.append(to_rel(pdf_path, session_dir))
            except Exception as pdf_exc:
                fallback.notes.append(f"Page PDF generation unavailable: {pdf_exc}")

            context.close()
            browser.close()
        return fallback
    except Exception as exc:  # pragma: no cover - runtime/browser dependent
        fallback.notes.append(f"Authenticated Canva capture failed: {exc}")
        return fallback


def enrich_session(
    session_dir: Path,
    notion_token_v2: str | None,
    notion_active_user: str | None,
    playwright_storage_state: Path | None,
    cookies_json: Path | None,
    dry_run: bool,
) -> dict[str, Any]:
    resources = parse_manifest(session_dir)
    resources_dir = session_dir / ".resources"
    report_path = resources_dir / "resource_enrichment_report.json"

    if not dry_run:
        resources_dir.mkdir(parents=True, exist_ok=True)

    public_session = _new_session()
    cookie_sessions = load_cookie_sessions(cookies_json) if cookies_json else {}

    results: list[EnrichmentResult] = []
    for item in resources:
        # Validate before provider routing. The same policy is reapplied to
        # every redirect inside fetch_limited.
        try:
            target = validate_remote_url(item.url)
        except Exception as exc:
            results.append(EnrichmentResult(
                name=item.name,
                url=item.url,
                provider=detect_provider(item.url),
                method="blocked-before-fetch",
                authenticated=False,
                status="error",
                http_status=None,
                final_url=None,
                title=None,
                output_files=[],
                notes=[],
                error=str(exc),
            ))
            continue
        host = (urlparse(target).hostname or "").lower().rstrip(".")
        session = cookie_sessions.get(host, public_session)
        uses_cookie_session = host in cookie_sessions
        provider = detect_provider(item.url)
        if provider == "notion":
            res = enrich_notion(
                session=session,
                item=item,
                session_dir=session_dir,
                resources_dir=resources_dir,
                token_v2=notion_token_v2,
                active_user=notion_active_user,
                dry_run=dry_run,
            )
        elif provider == "canva":
            res = enrich_canva(
                session=session,
                item=item,
                session_dir=session_dir,
                resources_dir=resources_dir,
                playwright_storage_state=playwright_storage_state,
                dry_run=dry_run,
            )
        elif provider == "google-drive":
            res = enrich_google_drive(
                session=session,
                item=item,
                session_dir=session_dir,
                resources_dir=resources_dir,
                dry_run=dry_run,
            )
        else:
            res = enrich_generic_http(
                session=session,
                item=item,
                session_dir=session_dir,
                resources_dir=resources_dir,
                dry_run=dry_run,
                authenticated=uses_cookie_session,
            )
        results.append(res)

    report = {
        "ts": now_iso(),
        "session_dir": str(session_dir),
        "dry_run": dry_run,
        "resource_count": len(resources),
        "auth": {
            "notion_token_v2": bool(notion_token_v2),
            "notion_active_user": bool(notion_active_user),
            "playwright_storage_state": str(playwright_storage_state) if playwright_storage_state else None,
            "cookies_json": str(cookies_json) if cookies_json else None,
        },
        "results": [asdict(r) for r in results],
    }

    if not dry_run:
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def collect_session_dirs(root: Path, session_dir: Path | None, all_sessions: bool) -> list[Path]:
    if session_dir:
        return [session_dir]
    if not all_sessions:
        raise ValueError("Provide --session-dir or use --all-sessions.")
    dirs: list[Path] = []
    for d in sorted(root.glob("2026-*")):
        if not d.is_dir():
            continue
        if (d / ".pipeline" / "resource_manifest.json").exists():
            dirs.append(d)
    return dirs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Authenticated resource enrichment for session resources.")
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="Zoom root directory")
    parser.add_argument("--session-dir", help="Single session directory to enrich")
    parser.add_argument("--all-sessions", action="store_true", help="Process every session with resource manifest")
    parser.add_argument("--dry-run", action="store_true", help="Do not write artifacts/reports")

    parser.add_argument("--cookies-json", help="Optional cookies JSON for authenticated generic requests")

    parser.add_argument(
        "--notion-token-v2",
        default=os.environ.get("NOTION_TOKEN_V2"),
        help="Notion token_v2 cookie value (or set NOTION_TOKEN_V2)",
    )
    parser.add_argument(
        "--notion-active-user",
        default=os.environ.get("NOTION_ACTIVE_USER"),
        help="Notion active user UUID (or set NOTION_ACTIVE_USER)",
    )
    parser.add_argument(
        "--playwright-storage-state",
        default=os.environ.get("RESOURCE_PLAYWRIGHT_STORAGE_STATE"),
        help="Playwright storage-state JSON for authenticated Canva capture",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    session_dir = Path(args.session_dir).resolve() if args.session_dir else None
    cookies_json = Path(args.cookies_json).resolve() if args.cookies_json else None
    storage_state = Path(args.playwright_storage_state).resolve() if args.playwright_storage_state else None

    try:
        targets = collect_session_dirs(root=root, session_dir=session_dir, all_sessions=args.all_sessions)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    if not targets:
        print("No target sessions found.")
        return 0

    enriched = 0
    for target in targets:
        report = enrich_session(
            session_dir=target,
            notion_token_v2=args.notion_token_v2,
            notion_active_user=args.notion_active_user,
            playwright_storage_state=storage_state,
            cookies_json=cookies_json,
            dry_run=args.dry_run,
        )
        enriched += 1
        print(
            f"[resource-enrichment] {target.name}: "
            f"{report['resource_count']} resources, dry_run={report['dry_run']}"
        )

    print(f"Completed resource enrichment for {enriched} session(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
