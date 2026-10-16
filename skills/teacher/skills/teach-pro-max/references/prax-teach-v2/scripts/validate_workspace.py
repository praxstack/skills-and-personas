#!/usr/bin/env python3
"""Validate durable Prax Teach artifacts and package invariants."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
import subprocess
import sys
from collections.abc import Iterable
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlparse

from review_payload import PayloadError, distributable_mode, payload_manifest

DANGEROUS_TAGS = {"base", "embed", "iframe", "object", "script"}
URL_ATTRIBUTES = {
    "action",
    "background",
    "cite",
    "data",
    "formaction",
    "href",
    "poster",
    "src",
    "xlink:href",
}
ASSET_ATTRIBUTES = {
    "audio": {"src"},
    "embed": {"src"},
    "iframe": {"src"},
    "img": {"src", "srcset"},
    "input": {"src"},
    "object": {"data"},
    "script": {"src"},
    "source": {"src", "srcset"},
    "track": {"src"},
    "video": {"poster", "src"},
}
ASSET_LINK_RELS = {
    "apple-touch-icon",
    "icon",
    "manifest",
    "modulepreload",
    "preload",
    "stylesheet",
}
SAFE_DATA_IMAGE_RE = re.compile(
    r"^data:image/(?:jpeg|png);base64,[a-z0-9+/=\s]+$", re.IGNORECASE
)
CSS_URL_RE = re.compile(r"url\(\s*([\"']?)(.*?)\1\s*\)", re.IGNORECASE)
REMOTE_CSS_RE = re.compile(r"(?:https?:)?//[^\s\"')]+", re.IGNORECASE)
SECURITY_KEYS = (
    "dangerous_tags",
    "event_attributes",
    "unsafe_urls",
    "external_assets",
    "missing_image_alt",
    "duplicate_ids",
)
EVIDENCE_STATES = {
    "specified",
    "implemented",
    "dependency-exercised",
    "manually-inspected",
    "evaluated",
    "scientifically-supported",
    "scientifically-unproven",
    "parked",
}
# Only positive evidence maturity states participate in aggregate promotion.
# ``scientifically-unproven`` is a claim boundary and ``parked`` is a workflow
# disposition, so neither may provide a floor for a promoted aggregate state.
PROMOTABLE_EVIDENCE_RANK = {
    "specified": 0,
    "implemented": 1,
    "dependency-exercised": 2,
    "manually-inspected": 3,
    "evaluated": 4,
    "scientifically-supported": 5,
}
EXTERNAL_GATE_STATES = {"passed", "failed", "parked"}
RELEASE_LABELS = {
    "pre-release",
    "engineering-candidate",
    "scientifically-supported",
}
CRITERION_STATES = {"passed", "pending", "parked"}
EXPECTED_CRITERION_IDS = tuple(f"AC-{index:02d}" for index in range(26))
EXPECTED_EXTERNAL_GATE_IDS = tuple(f"EG-{index:02d}" for index in range(1, 7))
EXPECTED_CAPABILITY_IDS = {
    "baseline-provenance",
    "documentation-truth",
    "ecosystem-exports",
    "evaluation-harness",
    "flint-adapter",
    "full-verification",
    "independent-review",
    "learner-state",
    "learner-study-machinery",
    "legacy-assets",
    "markdown-html-artifacts",
    "mode-and-visual-routing",
    "north-star-outcome",
    "package-validation",
    "release-package",
    "review-scheduler",
    "skillopt-adapter",
}
SUPPORTED_CRITERION_RECEIPTS = {
    "evidence/forward/receipt.json",
    "evidence/inspection/browser.json",
    "evidence/integrations/evaluator-sandbox/manifest.json",
    "evidence/integrations/flint-smoke/manifest.json",
    "evidence/integrations/skillopt-smoke/adapter-receipt.json",
    "evidence/provenance/legacy-assets.json",
    "evidence/reviews/architecture-council.json",
    "evidence/reviews/code-standards.json",
    "evidence/reviews/frozen-spec.json",
    "evidence/verification/full.json",
    "fixtures/visual-verification/manifest.json",
}
EXPECTED_RENDERER_VERSION = "prax-teach-markdown/2.2.0"
EXPECTED_VISUAL_VERIFIER_VERSION = "prax-teach-visual-verifier/1.1.0"
EXPECTED_TEMPLATE_VERSION = "prax-teach-lesson/2.0.0"
JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
EXPECTED_SCHEMA_FILES = {
    "concepts.schema.json",
    "event.schema.json",
    "learner.schema.json",
    "learning-items.schema.json",
    "misconceptions.schema.json",
    "reviews.schema.json",
    "sources.schema.json",
    "study-protocol.schema.json",
    "study-score.schema.json",
    "study-task-bank.schema.json",
}
SCHEMA_INSTANCE_FILES = {
    "concepts.schema.json": ("fixtures/schema-valid/concepts.json",),
    "event.schema.json": ("fixtures/schema-valid/events.jsonl",),
    "learner.schema.json": ("fixtures/schema-valid/learner.json",),
    "learning-items.schema.json": ("fixtures/schema-valid/learning-items.json",),
    "misconceptions.schema.json": ("fixtures/schema-valid/misconceptions.json",),
    "reviews.schema.json": ("fixtures/schema-valid/reviews.jsonl",),
    "sources.schema.json": ("fixtures/schema-valid/sources.json",),
    "study-protocol.schema.json": ("fixtures/schema-valid/study-protocol.json",),
    "study-score.schema.json": ("fixtures/schema-valid/study-score.jsonl",),
    "study-task-bank.schema.json": ("fixtures/schema-valid/study-task-bank.json",),
}
VERIFICATION_RECEIPT_RELATIVE = "evidence/verification/full.json"
FORWARD_RUBRIC_RELATIVE = "evals/forward-behavior.json"
FORWARD_RUN_RELATIVE = "evidence/forward/run.json"
FORWARD_RECEIPT_RELATIVE = "evidence/forward/receipt.json"
REVIEW_PAYLOAD_RELATIVE = "evidence/reviews/payload.json"
REVIEW_TYPES = ("code-standards", "frozen-spec", "architecture-council")
REVIEW_ATTESTATION = {
    "cryptographic_authorship_verified": False,
    "orchestration_task_identity_recorded": True,
    "threat_model": (
        "orchestration task identity is structurally recorded; "
        "cryptographic authorship is not verified"
    ),
}
REVIEW_COMMON_KEYS = {
    "attestation",
    "findings",
    "fixes",
    "payload",
    "payload_file_sha256",
    "payload_manifest_sha256",
    "recheck",
    "review_type",
    "reviewer",
    "schema_version",
    "status",
    "unresolved_actionable",
}
VERIFICATION_LOG_RETENTION = {
    "full_logs_persisted": False,
    "retained": ["sha256", "tail"],
    "tail_line_limit": 12,
}
VERIFICATION_COMMON_KEYS = {
    "dependencies",
    "evidence_level",
    "external_human_learning_gates_satisfied",
    "gates",
    "generated_at",
    "level",
    "log_retention",
    "root_manifest",
    "run_id",
    "schema_version",
    "scientific_learning_claim_supported",
    "skillopt_source",
    "source_date_epoch",
    "status",
    "trusted_macos_sandbox_tests_required",
    "verification_script_sha256",
}
BROWSER_INSPECTION_RECEIPT_RELATIVE = "evidence/inspection/browser.json"
VISUAL_VERIFICATION_FIXTURE = "fixtures/visual-verification/manifest.json"
VISUAL_RECEIPT_CHECK_KEYS = {
    "actual_bytes_scanned_for_declared_textual_leakage",
    "animated_or_unvalidated_assets_absent",
    "attempt_before_reveal",
    "linked_textual_assets_scanned",
    "markdown_html_exact_parity",
    "raster_semantics_automatically_verified",
    "semantic_visual_leakage",
    "static_fallback_verified",
    "unbundled_runtime_promoted",
}
FLINT_MANIFEST_KEYS = {
    "artifacts",
    "backend",
    "chart_correctness_claimed",
    "compiler",
    "compiler_exercise_note",
    "editable_inputs",
    "evidence_level",
    "file_references",
    "format",
    "generated_at",
    "input",
    "invocation",
    "known_limitations",
    "network_isolation_verified",
    "network_references_accepted",
    "output_sha256",
    "renderer",
    "schema_version",
    "source_date_epoch",
    "status",
    "synthetic_fixture",
    "warnings",
}
FLINT_KNOWN_LIMITATIONS = [
    (
        "Pinned Flint execution does not establish chart correctness, "
        "accessibility, or learner outcomes."
    ),
    (
        "Network isolation was not externally traced; input policy rejection "
        "is not network-isolation evidence."
    ),
    (
        "The generated SVG still requires a reviewed accessible lesson wrapper; "
        "the table is a data alternative, not an assistive-technology "
        "conformance claim."
    ),
]
BROWSER_INSPECTION_KEYS = {
    "schema_version",
    "attempted_at",
    "surface",
    "status",
    "reason",
    "planned_pages",
    "observed_runtime_pages",
    "console_checked",
    "responsive_viewports_checked",
    "accessibility_tree_checked",
    "manual_assistive_technology_checked",
    "supports_field_accessibility_claim",
    "claim_boundary",
}
BROWSER_CHECK_FIELDS = (
    "console_checked",
    "responsive_viewports_checked",
    "accessibility_tree_checked",
    "manual_assistive_technology_checked",
)

# Generated dependencies, immutable failed-attempt archives, transient learner
# data, and private evaluation material are outside current-package validation.
PRUNED_DIRECTORY_NAMES = {
    # OpenSpec control files are deliberately outside the legacy package
    # surface. The separately validated runtime remains in the release tree,
    # while its script boundary is checked by its own verifier below.
    ".agent",
    ".agents",
    ".git",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "attempts",
    "env",
    "hidden-bank",
    "hidden-banks",
    "hidden_bank",
    "hidden_banks",
    "learner-workspace",
    "learner-workspaces",
    "learner_workspace",
    "learner_workspaces",
    "node_modules",
    "private-bank",
    "private-banks",
    "private_bank",
    "private_banks",
    "runs",
    "openspec",
    "venv",
}


def normalized_url(value: str) -> str:
    """Remove characters browsers ignore when interpreting a URL scheme."""

    return re.sub(r"[\x00-\x20\x7f]+", "", value).lower()


def url_is_remote(value: str) -> bool:
    normalized = normalized_url(value)
    return normalized.startswith("//") or urlparse(normalized).scheme in {
        "http",
        "https",
    }


def url_is_unsafe(tag: str, attribute: str, value: str) -> bool:
    normalized = normalized_url(value)
    if not normalized or normalized.startswith(("#", "?")):
        return False
    if normalized.startswith(("javascript:", "vbscript:")):
        return True
    if normalized.startswith("data:"):
        return not (
            tag == "img"
            and attribute == "src"
            and SAFE_DATA_IMAGE_RE.fullmatch(value.strip()) is not None
        )

    scheme = urlparse(normalized).scheme
    if not scheme:
        return False
    if scheme in {"http", "https"}:
        return False
    return not (tag == "a" and attribute == "href" and scheme in {"mailto", "tel"})


def srcset_candidates(value: str) -> list[str]:
    """Return the URL portion of ordinary srcset candidates.

    Data URLs contain a comma and require special handling. Treat the complete
    data value as one candidate; it will then be rejected unless it is a safe
    image source in the narrower ``src`` context.
    """

    if normalized_url(value).startswith("data:"):
        return [value.strip()]
    return [part.strip().split()[0] for part in value.split(",") if part.strip()]


class PageParser(HTMLParser):
    """Collect document, link, accessibility, and security facts."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[str] = []
        self.ids: list[str] = []
        self.hrefs: list[str] = []
        self.asset_refs: list[str] = []
        self.external_assets: list[tuple[str, str, str]] = []
        self.dangerous_tags: list[str] = []
        self.event_attributes: list[tuple[str, str]] = []
        self.unsafe_urls: list[tuple[str, str, str]] = []
        self.missing_image_alt = 0
        self.heading_levels: list[int] = []
        self.has_lang = False
        self.has_charset = False
        self.has_viewport = False
        self.has_skip_link = False
        self.has_title = False
        self.source_hashes: list[str] = []
        self.source_paths: list[str] = []
        self.generated_ats: list[str] = []
        self.renderer_versions: list[str] = []
        self.template_versions: list[str] = []
        self.label_targets: set[str] = set()
        self.form_controls: list[tuple[str, str, str, bool]] = []
        self._label_depth = 0
        self._in_title = False
        self._title_text: list[str] = []
        self._in_style = False

    def _record_url(self, tag: str, attribute: str, value: str, *, asset: bool) -> None:
        candidates = srcset_candidates(value) if attribute == "srcset" else [value]
        for candidate in candidates:
            if not candidate:
                continue
            if url_is_unsafe(tag, attribute, candidate):
                self.unsafe_urls.append((tag, attribute, candidate))
            if asset:
                self.asset_refs.append(candidate)
                if url_is_remote(candidate):
                    self.external_assets.append((tag, attribute, candidate))

    def _record_css(self, css: str, *, attribute: str = "style") -> None:
        embedded_urls: list[str] = []
        for match in CSS_URL_RE.finditer(css):
            value = match.group(2).strip()
            embedded_urls.append(value)
            if url_is_unsafe("style", attribute, value):
                self.unsafe_urls.append(("style", attribute, value))
            if url_is_remote(value):
                self.external_assets.append(("style", attribute, value))
        # Also catch remote @import strings that are not wrapped in url(...).
        for value in REMOTE_CSS_RE.findall(css):
            if value not in embedded_urls:
                self.external_assets.append(("style", attribute, value))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        normalized_attrs = [(key.lower(), value or "") for key, value in attrs]
        values = {key: value for key, value in normalized_attrs}
        self.tags.append(tag)

        if tag in DANGEROUS_TAGS:
            self.dangerous_tags.append(tag)
        for key, _value in normalized_attrs:
            if key.startswith("on"):
                self.event_attributes.append((tag, key))

        if tag == "html" and values.get("lang", "").strip():
            self.has_lang = True
        if tag == "meta" and "charset" in values and values["charset"].strip():
            self.has_charset = True
        if tag == "meta" and values.get("name", "").lower() == "viewport":
            self.has_viewport = bool(values.get("content", "").strip())
        if tag == "meta" and values.get("name", "").lower() == "source-sha256":
            self.source_hashes.append(values.get("content", ""))
        if tag == "meta" and values.get("name", "").lower() == "source-path":
            self.source_paths.append(values.get("content", ""))
        if tag == "meta" and values.get("name", "").lower() == "generated-at":
            self.generated_ats.append(values.get("content", ""))
        if tag == "meta" and values.get("name", "").lower() == "renderer-version":
            self.renderer_versions.append(values.get("content", ""))
        if tag == "meta" and values.get("name", "").lower() == "template-version":
            self.template_versions.append(values.get("content", ""))
        if tag == "title":
            self._in_title = True
        if tag == "style":
            self._in_style = True
        if tag == "label":
            self._label_depth += 1
            target = values.get("for", "").strip()
            if target:
                self.label_targets.add(target)

        if tag == "a":
            href = values.get("href", "")
            if href:
                self.hrefs.append(href)
            classes = set(values.get("class", "").split())
            if "skip-link" in classes and href.startswith("#"):
                self.has_skip_link = True
        if "id" in values:
            self.ids.append(values["id"])
        if len(tag) == 2 and tag.startswith("h") and tag[1].isdigit():
            self.heading_levels.append(int(tag[1]))
        if tag == "img" and "alt" not in values:
            self.missing_image_alt += 1
        if tag in {"button", "input", "select", "textarea"} and not (
            tag == "input" and values.get("type", "").lower() == "hidden"
        ):
            self.form_controls.append(
                (
                    tag,
                    values.get("id", "").strip(),
                    values.get("aria-label", "").strip(),
                    self._label_depth > 0,
                )
            )

        link_is_asset = tag == "link" and bool(
            set(values.get("rel", "").lower().split()).intersection(ASSET_LINK_RELS)
        )
        for key, value in normalized_attrs:
            if key == "style":
                self._record_css(value, attribute="style attribute")
            if key not in URL_ATTRIBUTES and key != "srcset":
                continue
            is_asset = key in ASSET_ATTRIBUTES.get(tag, set()) or (
                link_is_asset and key == "href"
            )
            self._record_url(tag, key, value, asset=is_asset)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
            self.has_title = bool("".join(self._title_text).strip())
        if tag == "style":
            self._in_style = False
        if tag == "label" and self._label_depth:
            self._label_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_text.append(data)
        if self._in_style:
            self._record_css(data, attribute="style block")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def empty_security_counts() -> dict[str, int]:
    return {key: 0 for key in SECURITY_KEYS}


def should_prune_directory(name: str) -> bool:
    lowered = name.lower()
    if lowered in PRUNED_DIRECTORY_NAMES:
        return True
    return lowered.endswith(("_cache", "-cache"))


def iter_workspace_files(root: Path, suffixes: Iterable[str]) -> list[Path]:
    wanted = {suffix.lower() for suffix in suffixes}
    found: list[Path] = []
    for current, directory_names, file_names in os.walk(root, followlinks=False):
        directory_names[:] = sorted(
            name for name in directory_names if not should_prune_directory(name)
        )
        current_path = Path(current)
        for name in sorted(file_names):
            path = current_path / name
            if path.suffix.lower() in wanted:
                found.append(path)
    return sorted(found, key=lambda path: path.relative_to(root).as_posix())


def is_negative_fixture(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    return "fixtures" in {
        part.lower() for part in relative.parts[:-1]
    } and path.name.lower().startswith("invalid-")


def check_heading_order(levels: list[int], *, require_h1: bool = True) -> list[str]:
    errors: list[str] = []
    if require_h1 and levels.count(1) != 1:
        errors.append(f"expected exactly one h1, found {levels.count(1)}")
    previous = 0
    for level in levels:
        if previous and level > previous + 1:
            errors.append(f"heading level jumps from h{previous} to h{level}")
        previous = level
    return errors


def resolve_local_link(page: Path, href: str) -> tuple[Path | None, str | None]:
    parsed = urlparse(href)
    if parsed.scheme or parsed.netloc:
        return None, None
    if href.startswith("#"):
        return page, unquote(parsed.fragment)
    target_text = unquote(parsed.path)
    if not target_text:
        return page, unquote(parsed.fragment) if parsed.fragment else None
    target = (page.parent / target_text).resolve()
    return target, unquote(parsed.fragment) if parsed.fragment else None


def parse_page(path: Path) -> PageParser:
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    return parser


def is_separately_validated_runtime(path: Path, root: Path) -> bool:
    """Identify the zero-API runtime whose script boundary has its own verifier."""

    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    return len(relative.parts) >= 2 and relative.parts[:2] == (
        "runtime",
        "prax-visual-lab",
    )


def validate_companion_metadata(
    markdown: Path, html: Path, parser: PageParser, root: Path
) -> list[str]:
    errors: list[str] = []
    html_rel = html.relative_to(root)
    if len(parser.source_hashes) != 1:
        errors.append(
            f"{html_rel}: expected exactly one source-sha256 meta, "
            f"found {len(parser.source_hashes)}"
        )
    elif not re.fullmatch(r"[0-9a-f]{64}", parser.source_hashes[0]):
        errors.append(f"{html_rel}: malformed source-sha256 meta")
    elif parser.source_hashes[0] != sha256(markdown):
        errors.append(f"{html_rel}: stale source hash")

    if len(parser.source_paths) != 1:
        errors.append(
            f"{html_rel}: expected exactly one source-path meta, "
            f"found {len(parser.source_paths)}"
        )
    elif parser.source_paths[0] != markdown.name:
        errors.append(
            f"{html_rel}: source path points to {parser.source_paths[0]!r}, "
            f"expected {markdown.name!r}"
        )

    for label, actual, expected in (
        ("renderer-version", parser.renderer_versions, EXPECTED_RENDERER_VERSION),
        ("template-version", parser.template_versions, EXPECTED_TEMPLATE_VERSION),
    ):
        if len(actual) != 1:
            errors.append(
                f"{html_rel}: expected exactly one {label} meta, found {len(actual)}"
            )
        elif actual[0] != expected:
            errors.append(
                f"{html_rel}: {label} is {actual[0]!r}, expected {expected!r}"
            )
    if len(parser.generated_ats) != 1:
        errors.append(
            f"{html_rel}: expected exactly one generated-at meta, "
            f"found {len(parser.generated_ats)}"
        )
    else:
        try:
            generated_at = datetime.fromisoformat(
                parser.generated_ats[0].replace("Z", "+00:00")
            )
        except ValueError:
            generated_at = None
        if generated_at is None or generated_at.tzinfo is None:
            errors.append(f"{html_rel}: generated-at must be an ISO-8601 timestamp")
    return errors


def validate_html_document(
    path: Path, parser: PageParser, root: Path, *, require_document_shell: bool
) -> list[str]:
    errors: list[str] = []
    rel = path.relative_to(root)
    if require_document_shell:
        required = {"footer", "header", "main"}
        missing = sorted(required.difference(parser.tags))
        if missing:
            errors.append(f"{rel}: missing landmarks {missing}")
        if not parser.has_lang:
            errors.append(f"{rel}: html lang missing")
        if not parser.has_charset:
            errors.append(f"{rel}: charset missing")
        if not parser.has_viewport:
            errors.append(f"{rel}: viewport missing")
        if not parser.has_title:
            errors.append(f"{rel}: non-empty title missing")
        if not parser.has_skip_link:
            errors.append(f"{rel}: skip link missing")
    if len(parser.ids) != len(set(parser.ids)):
        errors.append(f"{rel}: duplicate IDs")
    for problem in check_heading_order(
        parser.heading_levels, require_h1=require_document_shell
    ):
        errors.append(f"{rel}: {problem}")

    separately_validated_runtime = is_separately_validated_runtime(path, root)
    for tag in parser.dangerous_tags:
        if separately_validated_runtime and tag == "script":
            continue
        errors.append(f"{rel}: dangerous tag <{tag}>")
    for tag, attribute in parser.event_attributes:
        errors.append(f"{rel}: event attribute {attribute!r} on <{tag}>")
    for tag, attribute, value in parser.unsafe_urls:
        errors.append(f"{rel}: unsafe URL {value!r} on <{tag} {attribute}>")
    for tag, attribute, value in parser.external_assets:
        errors.append(f"{rel}: external asset {value!r} on <{tag} {attribute}>")
    if parser.missing_image_alt:
        errors.append(
            f"{rel}: {parser.missing_image_alt} image(s) missing an alt attribute"
        )
    for tag, control_id, aria_label, wrapped in parser.form_controls:
        labelled = bool(
            aria_label or wrapped or (control_id and control_id in parser.label_targets)
        )
        if not labelled:
            errors.append(f"{rel}: <{tag}> control has no accessible label")
        errors.append(
            f"{rel}: bundled renderer has no form-grading runtime; "
            "use host chat, static disclosure, or a separately versioned and tested runtime"
        )
    return errors


def validate_local_links(
    html_files: list[Path], parsers: dict[Path, PageParser], root: Path
) -> list[str]:
    errors: list[str] = []
    for page in html_files:
        parser = parsers[page.resolve()]
        references = parser.hrefs + parser.asset_refs
        for href in references:
            target, fragment = resolve_local_link(page, href)
            if target is None:
                continue
            if not target.is_relative_to(root):
                errors.append(
                    f"{page.relative_to(root)}: local link escapes workspace {href!r}"
                )
                continue
            if not target.exists():
                errors.append(f"{page.relative_to(root)}: broken local link {href!r}")
                continue
            if fragment and target.suffix.lower() == ".html":
                target_parser = parsers.get(target.resolve())
                if target_parser is None:
                    try:
                        target_parser = parse_page(target)
                    except (OSError, UnicodeError) as exc:
                        errors.append(
                            f"{page.relative_to(root)}: cannot inspect local link {href!r}: {exc}"
                        )
                        continue
                    parsers[target.resolve()] = target_parser
                if fragment not in set(target_parser.ids):
                    target_label = (
                        target.relative_to(root)
                        if target.is_relative_to(root)
                        else target
                    )
                    errors.append(
                        f"{page.relative_to(root)}: missing anchor #{fragment} in {target_label}"
                    )
    return errors


def validate_json_files(
    json_files: list[Path], jsonl_files: list[Path], root: Path
) -> list[str]:
    errors: list[str] = []
    for path in json_files:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            if not is_negative_fixture(path, root):
                errors.append(f"{path.relative_to(root)}: invalid JSON: {exc}")
    for path in jsonl_files:
        line_number = 0
        try:
            for line_number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if line.strip():
                    json.loads(line)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            if not is_negative_fixture(path, root):
                errors.append(
                    f"{path.relative_to(root)}:{line_number}: invalid JSONL: {exc}"
                )
    return errors


def public_eval_errors(path: Path, payload: Any, root: Path) -> list[str]:
    errors: list[str] = []
    rel = path.relative_to(root)
    if not isinstance(payload, dict):
        return [f"{rel}: expected an object"]
    if payload.get("skill_name") != "prax-teach-v2":
        errors.append(f"{rel}: skill_name must be 'prax-teach-v2'")
    if payload.get("fixture_visibility") != "public_development_only":
        errors.append(f"{rel}: fixtures must be labeled public_development_only")
    evals = payload.get("evals")
    if not isinstance(evals, list) or not evals:
        errors.append(f"{rel}: evals must be a non-empty list")
        return errors
    seen_ids: set[str] = set()
    for index, item in enumerate(evals):
        label = f"{rel}:evals[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: expected an object")
            continue
        eval_id = item.get("id")
        if not isinstance(eval_id, str) or not eval_id.strip():
            errors.append(f"{label}: id must be a non-empty string")
        elif eval_id in seen_ids:
            errors.append(f"{label}: duplicate id {eval_id!r}")
        else:
            seen_ids.add(eval_id)
        for field in ("prompt", "expected_output"):
            value = item.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{label}: {field} must be a non-empty string")
        assertions = item.get("assertions")
        if (
            not isinstance(assertions, list)
            or not assertions
            or not all(isinstance(value, str) and value.strip() for value in assertions)
        ):
            errors.append(f"{label}: assertions must be a non-empty string list")
    return errors


def validate_public_evals(json_files: list[Path], root: Path) -> list[str]:
    errors: list[str] = []
    for path in json_files:
        if path.name != "evals.json" or path.parent.name != "evals":
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        file_errors = public_eval_errors(path, payload, root)
        if is_negative_fixture(path, root):
            if not file_errors:
                errors.append(
                    f"{path.relative_to(root)}: negative fixture unexpectedly passed validation"
                )
        else:
            errors.extend(file_errors)
    return errors


def flint_spec_errors(path: Path, payload: Any, root: Path) -> list[str]:
    errors: list[str] = []
    rel = path.relative_to(root)
    if not isinstance(payload, dict):
        return [f"{rel}: Flint spec must be an object"]
    data = payload.get("data")
    semantic_types = payload.get("semantic_types")
    chart_spec = payload.get("chart_spec")
    columns: set[str] = set()
    if not isinstance(data, dict) or not isinstance(data.get("values"), list):
        errors.append(f"{rel}: data must contain inline values")
    elif not data["values"] or not isinstance(data["values"][0], dict):
        errors.append(f"{rel}: data.values must contain at least one object")
    else:
        columns = set(data["values"][0])
        if any(
            not isinstance(row, dict) or set(row) != columns for row in data["values"]
        ):
            errors.append(f"{rel}: every data.values row must use the same fields")
    if not isinstance(semantic_types, dict) or not semantic_types:
        errors.append(f"{rel}: semantic_types must be a non-empty object")
    if not isinstance(chart_spec, dict):
        errors.append(f"{rel}: chart_spec must be an object")
        return errors
    if (
        not isinstance(chart_spec.get("chartType"), str)
        or not chart_spec["chartType"].strip()
    ):
        errors.append(f"{rel}: chart_spec.chartType must be a non-empty string")
    if not isinstance(chart_spec.get("encodings"), dict) or not chart_spec["encodings"]:
        errors.append(f"{rel}: chart_spec.encodings must be a non-empty object")
    else:
        encoded_fields: set[str] = set()
        for encoding in chart_spec["encodings"].values():
            if isinstance(encoding, dict) and isinstance(encoding.get("field"), str):
                encoded_fields.add(encoding["field"])
        missing_fields = sorted(encoded_fields - columns)
        if missing_fields:
            errors.append(
                f"{rel}: chart_spec encoding fields are absent from data.values: {missing_fields}"
            )
        display_names = payload.get("field_display_names")
        if not isinstance(display_names, dict):
            errors.append(f"{rel}: field_display_names must be an object")
        for field in sorted(encoded_fields):
            if not isinstance(semantic_types, dict) or not isinstance(
                semantic_types.get(field), str
            ):
                errors.append(f"{rel}: semantic_types.{field} is required")
            if not isinstance(display_names, dict) or not isinstance(
                display_names.get(field), str
            ):
                errors.append(f"{rel}: field_display_names.{field} is required")
    return errors


def validate_flint_specs(json_files: list[Path], root: Path) -> list[str]:
    errors: list[str] = []
    for path in json_files:
        if not path.name.endswith(".flint.json"):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            file_errors = [f"{path.relative_to(root)}: invalid Flint JSON: {exc}"]
        else:
            file_errors = flint_spec_errors(path, payload, root)
        if is_negative_fixture(path, root):
            if not file_errors:
                errors.append(
                    f"{path.relative_to(root)}: negative fixture unexpectedly passed validation"
                )
        else:
            errors.extend(file_errors)
    return errors


def _frontmatter_fields(path: Path, root: Path) -> tuple[dict[str, str], list[str]]:
    rel = path.relative_to(root)
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        return {}, [f"{rel}: cannot read frontmatter: {exc}"]
    if not lines or lines[0] != "---":
        return {}, [f"{rel}: YAML frontmatter must begin on the first line"]
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}, [f"{rel}: YAML frontmatter is not closed"]
    fields: dict[str, str] = {}
    for line_number, line in enumerate(lines[1:end], start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            errors.append(f"{rel}:{line_number}: malformed frontmatter field")
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if not key or not value:
            errors.append(f"{rel}:{line_number}: frontmatter fields must be non-empty")
        elif key in fields:
            errors.append(f"{rel}:{line_number}: duplicate frontmatter field {key!r}")
        else:
            fields[key] = value
    if not any(line.strip() for line in lines[end + 1 :]):
        errors.append(f"{rel}: skill body must not be empty")
    return fields, errors


def _resolve_json_pointer(document: Any, reference: str) -> bool:
    if not reference.startswith("#/"):
        return False
    current = document
    for encoded in reference[2:].split("/"):
        key = encoded.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or key not in current:
            return False
        current = current[key]
    return True


def _walk_schema_references(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        reference = value.get("$ref")
        if isinstance(reference, str):
            yield reference
        for child in value.values():
            yield from _walk_schema_references(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_schema_references(child)


def json_schema_errors(path: Path, payload: Any, root: Path) -> list[str]:
    rel = path.relative_to(root)
    prefix = f"{rel}:"
    if not isinstance(payload, dict):
        return [f"{prefix} schema must be an object"]
    errors: list[str] = []
    if payload.get("$schema") != JSON_SCHEMA_DIALECT:
        errors.append(f"{prefix} $schema must be the 2020-12 dialect")
    identifier = payload.get("$id")
    if not isinstance(identifier, str) or not identifier.startswith(
        ("https://", "urn:")
    ):
        errors.append(f"{prefix} $id must be a stable HTTPS URL or URN")
    if not isinstance(payload.get("title"), str) or not payload["title"].strip():
        errors.append(f"{prefix} title must be a non-empty string")
    if payload.get("type") != "object":
        errors.append(f"{prefix} top-level type must be object")
    properties = payload.get("properties")
    if not isinstance(properties, dict):
        errors.append(f"{prefix} properties must be an object")
        properties = {}
    required = payload.get("required")
    if not isinstance(required, list) or not all(
        isinstance(item, str) and item for item in required
    ):
        errors.append(f"{prefix} required must be a string list")
    else:
        if len(required) != len(set(required)):
            errors.append(f"{prefix} required contains duplicates")
        for name in required:
            if name not in properties:
                errors.append(f"{prefix} required property {name!r} has no schema")
    if payload.get("additionalProperties") not in (False, None) and not isinstance(
        payload.get("additionalProperties"), dict
    ):
        errors.append(f"{prefix} additionalProperties must be false or a schema")
    for reference in _walk_schema_references(payload):
        if not _resolve_json_pointer(payload, reference):
            errors.append(f"{prefix} unresolved or external $ref {reference!r}")
    return errors


def _json_equal(left: Any, right: Any) -> bool:
    """Use JSON type equality, avoiding Python's ``True == 1`` shortcut."""

    if type(left) is not type(right):
        return False
    return left == right


def _schema_type_matches(value: Any, expected: str) -> bool:
    checks = {
        "array": lambda item: isinstance(item, list),
        "boolean": lambda item: type(item) is bool,
        "integer": lambda item: isinstance(item, int) and type(item) is not bool,
        "null": lambda item: item is None,
        "number": lambda item: (
            isinstance(item, (int, float))
            and type(item) is not bool
            and math.isfinite(item)
        ),
        "object": lambda item: isinstance(item, dict),
        "string": lambda item: isinstance(item, str),
    }
    return expected in checks and checks[expected](value)


def _schema_instance_errors(
    value: Any,
    schema: Any,
    root_schema: dict[str, Any],
    location: str,
) -> list[str]:
    """Validate the Draft 2020-12 subset used by this package's schemas."""

    if isinstance(schema, bool):
        return [] if schema else [f"{location}: rejected by false schema"]
    if not isinstance(schema, dict):
        return [f"{location}: schema node is not an object"]
    errors: list[str] = []
    reference = schema.get("$ref")
    if isinstance(reference, str):
        if not _resolve_json_pointer(root_schema, reference):
            return [f"{location}: unresolved schema reference {reference!r}"]
        target: Any = root_schema
        for encoded in reference[2:].split("/"):
            key = encoded.replace("~1", "/").replace("~0", "~")
            target = target[key]
        errors.extend(_schema_instance_errors(value, target, root_schema, location))

    if "const" in schema and not _json_equal(value, schema["const"]):
        errors.append(f"{location}: value does not match const")
    enum = schema.get("enum")
    if isinstance(enum, list) and not any(_json_equal(value, item) for item in enum):
        errors.append(f"{location}: value is not in enum")

    expected_type = schema.get("type")
    if isinstance(expected_type, str):
        expected_types = [expected_type]
    elif (
        isinstance(expected_type, list)
        and expected_type
        and all(isinstance(item, str) for item in expected_type)
    ):
        expected_types = expected_type
    else:
        expected_types = []
    if expected_types and not any(
        _schema_type_matches(value, item) for item in expected_types
    ):
        label = expected_types[0] if len(expected_types) == 1 else repr(expected_types)
        errors.append(f"{location}: expected {label}")
        return errors

    for index, branch in enumerate(schema.get("allOf", [])):
        errors.extend(
            _schema_instance_errors(
                value, branch, root_schema, f"{location}.allOf[{index}]"
            )
        )
    any_of = schema.get("anyOf")
    if isinstance(any_of, list) and not any(
        not _schema_instance_errors(value, branch, root_schema, location)
        for branch in any_of
    ):
        errors.append(f"{location}: no anyOf branch matched")
    one_of = schema.get("oneOf")
    if isinstance(one_of, list):
        matches = sum(
            not _schema_instance_errors(value, branch, root_schema, location)
            for branch in one_of
        )
        if matches != 1:
            errors.append(
                f"{location}: expected exactly one oneOf match; found {matches}"
            )
    negated = schema.get("not")
    if isinstance(negated, (dict, bool)) and not _schema_instance_errors(
        value, negated, root_schema, location
    ):
        errors.append(f"{location}: value matched forbidden not schema")
    condition = schema.get("if")
    if isinstance(condition, (dict, bool)):
        condition_matches = not _schema_instance_errors(
            value, condition, root_schema, location
        )
        branch = schema.get("then" if condition_matches else "else")
        if isinstance(branch, (dict, bool)):
            errors.extend(_schema_instance_errors(value, branch, root_schema, location))

    if isinstance(value, dict):
        required = schema.get("required")
        if isinstance(required, list):
            for name in required:
                if name not in value:
                    errors.append(f"{location}: missing required property {name!r}")
        dependent = schema.get("dependentRequired")
        if isinstance(dependent, dict):
            for trigger, dependencies in dependent.items():
                if trigger in value and isinstance(dependencies, list):
                    for name in dependencies:
                        if name not in value:
                            errors.append(
                                f"{location}: {trigger!r} requires property {name!r}"
                            )
        properties = schema.get("properties")
        property_names = set(properties) if isinstance(properties, dict) else set()
        if isinstance(properties, dict):
            for name, child_schema in properties.items():
                if name in value:
                    errors.extend(
                        _schema_instance_errors(
                            value[name], child_schema, root_schema, f"{location}.{name}"
                        )
                    )
        additional = schema.get("additionalProperties")
        extras = set(value) - property_names
        if additional is False and extras:
            errors.append(f"{location}: unexpected properties {sorted(extras)}")
        elif isinstance(additional, dict):
            for name in extras:
                errors.extend(
                    _schema_instance_errors(
                        value[name], additional, root_schema, f"{location}.{name}"
                    )
                )

    if isinstance(value, list):
        minimum_items = schema.get("minItems")
        if isinstance(minimum_items, int) and len(value) < minimum_items:
            errors.append(f"{location}: has fewer than {minimum_items} items")
        maximum_items = schema.get("maxItems")
        if isinstance(maximum_items, int) and len(value) > maximum_items:
            errors.append(f"{location}: has more than {maximum_items} items")
        if schema.get("uniqueItems") is True:
            encoded = [
                json.dumps(item, sort_keys=True, separators=(",", ":"))
                for item in value
            ]
            if len(encoded) != len(set(encoded)):
                errors.append(f"{location}: array items are not unique")
        item_schema = schema.get("items")
        if isinstance(item_schema, (dict, bool)):
            for index, item in enumerate(value):
                errors.extend(
                    _schema_instance_errors(
                        item, item_schema, root_schema, f"{location}[{index}]"
                    )
                )

    if isinstance(value, str):
        minimum_length = schema.get("minLength")
        if isinstance(minimum_length, int) and len(value) < minimum_length:
            errors.append(f"{location}: string is shorter than {minimum_length}")
        maximum_length = schema.get("maxLength")
        if isinstance(maximum_length, int) and len(value) > maximum_length:
            errors.append(f"{location}: string is longer than {maximum_length}")
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and re.search(pattern, value) is None:
            errors.append(f"{location}: string does not match {pattern!r}")
        if schema.get("format") == "date-time":
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                parsed = None
            if parsed is None or parsed.tzinfo is None:
                errors.append(f"{location}: invalid date-time")

    if isinstance(value, (int, float)) and type(value) is not bool:
        for keyword, comparator, phrase in (
            ("minimum", lambda left, right: left >= right, "below minimum"),
            ("maximum", lambda left, right: left <= right, "above maximum"),
            (
                "exclusiveMinimum",
                lambda left, right: left > right,
                "not above exclusive minimum",
            ),
            (
                "exclusiveMaximum",
                lambda left, right: left < right,
                "not below exclusive maximum",
            ),
        ):
            boundary = schema.get(keyword)
            if isinstance(boundary, (int, float)) and not comparator(value, boundary):
                errors.append(f"{location}: {phrase} {boundary}")
    return errors


def validate_schema_instances(root: Path) -> tuple[int, list[str]]:
    if not (root / "SKILL.md").is_file():
        return 0, []
    errors: list[str] = []
    count = 0
    for schema_name, relative_paths in sorted(SCHEMA_INSTANCE_FILES.items()):
        schema_path = root / "schemas" / schema_name
        schema = _load_json_if_present(schema_path)
        if not isinstance(schema, dict):
            continue
        for relative in relative_paths:
            path = root / relative
            if not path.is_file():
                errors.append(
                    f"{relative}: required schema instance fixture is missing"
                )
                continue
            try:
                if path.suffix == ".jsonl":
                    values = [
                        json.loads(line)
                        for line in path.read_text(encoding="utf-8").splitlines()
                        if line.strip()
                    ]
                else:
                    values = [json.loads(path.read_text(encoding="utf-8"))]
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            for index, value in enumerate(values):
                count += 1
                label = relative if len(values) == 1 else f"{relative}:{index + 1}"
                errors.extend(
                    f"{label}: {message.split(': ', 1)[-1]}"
                    for message in _schema_instance_errors(
                        value, schema, schema, "instance"
                    )
                )
    return count, errors


def validate_state_fixture_invariants(root: Path) -> tuple[int, list[str]]:
    """Replay canonical fixtures through the same public state invariants."""

    if not (root / "SKILL.md").is_file():
        return 0, []
    errors: list[str] = []
    scripts = root / "scripts"
    sys.path.insert(0, str(scripts))
    try:
        from praxexports.core import parse_collection
        from praxteach.scheduler import _validate_review_record
        from praxteach.state import (
            project_events,
            validate_event,
            validate_event_source_resolution,
            validate_learner_document,
            validate_source_library,
        )

        fixture = root / "fixtures/schema-valid"
        learner = json.loads((fixture / "learner.json").read_text(encoding="utf-8"))
        validate_learner_document(learner)
        events = [
            json.loads(line)
            for line in (fixture / "events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        seen: set[str] = set()
        for event in events:
            validate_event(event)
            if event["event_id"] in seen:
                raise ValueError(f"duplicate event_id {event['event_id']}")
            seen.add(event["event_id"])
        source_library = validate_source_library(
            json.loads((fixture / "sources.json").read_text(encoding="utf-8"))
        )
        validate_event_source_resolution(events, source_library)
        concepts, misconceptions = project_events(events)
        expected_concepts = json.loads(
            (fixture / "concepts.json").read_text(encoding="utf-8")
        )
        expected_misconceptions = json.loads(
            (fixture / "misconceptions.json").read_text(encoding="utf-8")
        )
        if concepts != expected_concepts:
            errors.append(
                "fixtures/schema-valid/concepts.json: projection replay mismatch"
            )
        if misconceptions != expected_misconceptions:
            errors.append(
                "fixtures/schema-valid/misconceptions.json: projection replay mismatch"
            )
        reviews = [
            json.loads(line)
            for line in (fixture / "reviews.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        for review in reviews:
            _validate_review_record(review)
        parse_collection(
            json.loads((fixture / "learning-items.json").read_text(encoding="utf-8"))
        )
    except Exception as exc:  # noqa: BLE001 - convert invariant failures to receipt
        errors.append(
            f"fixtures/schema-valid: state invariant validation failed: {type(exc).__name__}: {exc}"
        )
    finally:
        try:
            sys.path.remove(str(scripts))
        except ValueError:
            pass
    return 1, errors


def validate_json_schemas(json_files: list[Path], root: Path) -> tuple[int, list[str]]:
    schemas = [
        path
        for path in json_files
        if path.parent.name == "schemas" and path.name.endswith(".schema.json")
    ]
    errors: list[str] = []
    for path in schemas:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        errors.extend(json_schema_errors(path, payload, root))
    if (root / "SKILL.md").is_file():
        names = {path.name for path in schemas}
        missing = sorted(EXPECTED_SCHEMA_FILES - names)
        unexpected = sorted(names - EXPECTED_SCHEMA_FILES)
        if missing:
            errors.append(f"schemas: missing package schemas {missing}")
        if unexpected:
            errors.append(f"schemas: unexpected package schemas {unexpected}")
    return len(schemas), errors


def _load_json_if_present(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None


def _load_strict_bounded_json(path: Path, *, maximum: int = 2 * 1024 * 1024) -> Any:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate key: {key}")
            value[key] = item
        return value

    try:
        if path.is_symlink() or not path.is_file():
            return None
        data = path.read_bytes()
        if not data or len(data) > maximum:
            return None
        return json.loads(data.decode("utf-8"), object_pairs_hook=reject_duplicates)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return None


def validate_dependency_contract(root: Path) -> list[str]:
    path = root / "DEPENDENCIES.json"
    if not path.is_file():
        return ["DEPENDENCIES.json: required dependency provenance is missing"]
    document = _load_json_if_present(path)
    if not isinstance(document, dict):
        return ["DEPENDENCIES.json: expected a valid object"]
    errors: list[str] = []
    entries: dict[str, dict[str, Any]] = {}
    for group in ("runtime", "optional_integrations"):
        values = document.get(group)
        if not isinstance(values, list):
            errors.append(f"DEPENDENCIES.json: {group} must be an array")
            continue
        for index, value in enumerate(values):
            if not isinstance(value, dict):
                errors.append(f"DEPENDENCIES.json: {group}[{index}] must be an object")
                continue
            name = value.get("name")
            version = value.get("version")
            if not isinstance(name, str) or not name:
                errors.append(f"DEPENDENCIES.json: {group}[{index}].name is required")
                continue
            if name in entries:
                errors.append(f"DEPENDENCIES.json: duplicate dependency {name!r}")
            entries[name] = value
            if not isinstance(version, str) or not version:
                errors.append(f"DEPENDENCIES.json: {name}.version is required")
            if not isinstance(value.get("license"), str) or not value["license"]:
                errors.append(f"DEPENDENCIES.json: {name}.license is required")
            source = value.get("source")
            if not isinstance(source, str) or not source.startswith("https://"):
                errors.append(f"DEPENDENCIES.json: {name}.source must use HTTPS")

    package = _load_json_if_present(root / "package.json")
    flint_package = _load_json_if_present(root / "integrations/flint/package.json")
    expected_versions: dict[str, str] = {"fsrs": "6.3.1", "skillopt": "0.2.0"}
    if isinstance(package, dict) and isinstance(package.get("dependencies"), dict):
        expected_versions.update(package["dependencies"])
    else:
        errors.append("package.json: dependencies object is required")
    if isinstance(flint_package, dict) and isinstance(
        flint_package.get("dependencies"), dict
    ):
        expected_versions.update(flint_package["dependencies"])
    else:
        errors.append(
            "integrations/flint/package.json: dependencies object is required"
        )
    for name, version in sorted(expected_versions.items()):
        if name not in entries:
            errors.append(f"DEPENDENCIES.json: missing dependency {name!r}")
        elif entries[name].get("version") != version:
            errors.append(
                f"DEPENDENCIES.json: {name} version disagrees with the locked manifest"
            )

    source = _load_json_if_present(root / "integrations/skillopt/SOURCE.json")
    skillopt = entries.get("skillopt", {})
    expected_commit = "e4ea6a6771e797ef820cdd8bfea64c57e0481065"
    if not isinstance(source, dict) or source.get("commit") != expected_commit:
        errors.append("integrations/skillopt/SOURCE.json: pinned commit is invalid")
    repository_commit = skillopt.get("repository_commit")
    if (
        not isinstance(repository_commit, str)
        or expected_commit not in repository_commit
    ):
        errors.append("DEPENDENCIES.json: SkillOpt repository commit is inconsistent")
    return errors


def _manifest_artifact_errors(directory: Path, artifacts: Any, label: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(artifacts, dict) or not artifacts:
        return [f"{label}: artifacts must be a non-empty digest map"]
    for name, digest in artifacts.items():
        if (
            not isinstance(name, str)
            or PurePosixPath(name).is_absolute()
            or ".." in PurePosixPath(name).parts
            or len(PurePosixPath(name).parts) != 1
        ):
            errors.append(f"{label}: unsafe artifact path {name!r}")
            continue
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            errors.append(f"{label}: invalid SHA-256 for {name!r}")
            continue
        path = directory / name
        if path.is_symlink() or not path.is_file():
            errors.append(f"{label}: artifact is missing or unsafe: {name}")
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            errors.append(f"{label}: artifact digest mismatch: {name}")
    return errors


def validate_integration_manifests(root: Path) -> tuple[int, list[str]]:
    if not (root / "SKILL.md").is_file():
        return 0, []
    errors: list[str] = []
    count = 0
    directory = root / "evidence/integrations/flint-smoke"
    manifest_path = directory / "manifest.json"
    manifest = _load_json_if_present(manifest_path)
    if not isinstance(manifest, dict):
        errors.append(
            "evidence/integrations/flint-smoke/manifest.json: required Flint receipt is missing"
        )
    else:
        count += 1
        label = "evidence/integrations/flint-smoke/manifest.json"
        if set(manifest) != FLINT_MANIFEST_KEYS:
            errors.append(f"{label}: manifest must use the exact 1.1 schema")
        if manifest.get("schema_version") != "1.1":
            errors.append(f"{label}: schema_version must be 1.1")
        if (
            manifest.get("status") != "rendered"
            or manifest.get("backend") != "vegalite"
            or manifest.get("format") != "svg"
            or manifest.get("evidence_level") != "dependency-exercised"
            or manifest.get("file_references") is not False
            or manifest.get("synthetic_fixture") is not True
        ):
            errors.append(f"{label}: render/evidence boundary is invalid")
        generated_at = manifest.get("generated_at")
        source_date_epoch = manifest.get("source_date_epoch")
        parsed_generated_at: datetime | None = None
        if isinstance(generated_at, str):
            try:
                parsed_generated_at = datetime.fromisoformat(
                    generated_at.replace("Z", "+00:00")
                )
            except ValueError:
                pass
        if (
            parsed_generated_at is None
            or parsed_generated_at.tzinfo is None
            or parsed_generated_at.utcoffset() is None
            or not isinstance(source_date_epoch, str)
            or re.fullmatch(r"(?:0|[1-9][0-9]*)", source_date_epoch) is None
        ):
            errors.append(f"{label}: reproducible timestamps are invalid")
        elif parsed_generated_at.timestamp() != int(source_date_epoch):
            errors.append(f"{label}: generated_at is not bound to source_date_epoch")
        expected_invocation = {
            "api": [
                {
                    "export": "validateInput",
                    "module": "flint-chart-mcp/render",
                    "options": {
                        "disableFileReference": True,
                        "maxDataRows": 100_000,
                    },
                },
                {
                    "export": "assembleForBackend",
                    "module": "flint-chart-mcp/render",
                    "options": {"disableFileReference": True},
                },
                {
                    "export": "renderChart",
                    "module": "flint-chart-mcp/render",
                    "options": {
                        "background": "#ffffff",
                        "disableFileReference": True,
                        "format": "svg",
                        "scale": 1,
                    },
                },
            ],
            "cli": [
                "node",
                "integrations/flint/render_flint.mjs",
                "--input",
                "<input>",
                "--output-dir",
                "<output-dir>",
                "--backend",
                "vegalite",
                "--trusted-root",
                "<trusted-root>",
            ],
        }
        if manifest.get("invocation") != expected_invocation:
            errors.append(f"{label}: invocation/API record is not normalized")
        if manifest.get("known_limitations") != FLINT_KNOWN_LIMITATIONS:
            errors.append(f"{label}: known limitations are incomplete or changed")
        input_receipt = manifest.get("input")
        if (
            not isinstance(input_receipt, dict)
            or set(input_receipt) != {"bytes", "raw_sha256"}
            or not isinstance(input_receipt.get("bytes"), int)
            or isinstance(input_receipt.get("bytes"), bool)
            or input_receipt.get("bytes", 0) <= 0
            or not isinstance(input_receipt.get("raw_sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", input_receipt["raw_sha256"]) is None
        ):
            errors.append(f"{label}: input receipt is invalid")
        errors.extend(
            _manifest_artifact_errors(directory, manifest.get("artifacts"), label)
        )
        artifacts = manifest.get("artifacts")
        if not isinstance(artifacts, dict) or set(artifacts) != {
            "chart.data.json",
            "chart.semantic-spec.json",
            "chart.source.flint.json",
            "chart.svg",
            "chart.table.html",
            "chart.vega-lite.json",
        }:
            errors.append(f"{label}: artifact inventory is incomplete or unexpected")
        if manifest.get("compiler") != {"package": "flint-chart", "version": "0.4.1"}:
            errors.append(f"{label}: compiler provenance must be flint-chart 0.4.1")
        if manifest.get("renderer") != {
            "package": "flint-chart-mcp",
            "version": "0.4.1",
        }:
            errors.append(f"{label}: renderer provenance must be flint-chart-mcp 0.4.1")
        if manifest.get("warnings") != []:
            errors.append(f"{label}: unresolved warnings are not allowed")
        if manifest.get("chart_correctness_claimed") is not False:
            errors.append(f"{label}: compiler exercise cannot claim chart correctness")
        if "network_access" in manifest:
            errors.append(
                f"{label}: network_access must not be asserted without tracing"
            )
        if manifest.get("network_isolation_verified") is not False:
            errors.append(
                f"{label}: network isolation must remain explicitly unverified"
            )
        if manifest.get("network_references_accepted") is not False:
            errors.append(f"{label}: network references must be rejected")
        if (
            not isinstance(manifest.get("compiler_exercise_note"), str)
            or not manifest["compiler_exercise_note"].strip()
        ):
            errors.append(f"{label}: compiler exercise claim boundary is missing")
        editable = manifest.get("editable_inputs")
        if not isinstance(editable, dict) or set(editable) != {
            "data",
            "semantic_spec",
            "source",
        }:
            errors.append(f"{label}: editable input receipts are incomplete")
        else:
            artifacts = manifest.get("artifacts", {})
            for kind, receipt in editable.items():
                if not isinstance(receipt, dict) or set(receipt) != {"file", "sha256"}:
                    errors.append(f"{label}: editable_inputs.{kind} is invalid")
                    continue
                file_name = receipt.get("file")
                digest = receipt.get("sha256")
                if (
                    not isinstance(file_name, str)
                    or not isinstance(digest, str)
                    or not isinstance(artifacts, dict)
                    or artifacts.get(file_name) != digest
                ):
                    errors.append(
                        f"{label}: editable_inputs.{kind} is not bound to an artifact"
                    )
        if isinstance(manifest.get("artifacts"), dict) and manifest.get(
            "output_sha256"
        ) != manifest["artifacts"].get("chart.svg"):
            errors.append(f"{label}: output_sha256 is not bound to chart.svg")

    skillopt_directory = root / "evidence/integrations/skillopt-smoke"
    skillopt_receipt_path = skillopt_directory / "adapter-receipt.json"
    skillopt_status_path = skillopt_directory / "sandbox-e2e-status.json"
    skillopt_receipt = _load_json_if_present(skillopt_receipt_path)
    skillopt_status = _load_json_if_present(skillopt_status_path)
    skillopt_label = "evidence/integrations/skillopt-smoke"
    if not isinstance(skillopt_receipt, dict) or not isinstance(skillopt_status, dict):
        errors.append(
            f"{skillopt_label}: required isolated adapter receipts are missing"
        )
    else:
        count += 1
        expected_dependency = {
            "commit": "e4ea6a6771e797ef820cdd8bfea64c57e0481065",
            "name": "SkillOpt",
            "version": "0.2.0",
        }
        if skillopt_receipt.get("dependency") != expected_dependency:
            errors.append(f"{skillopt_label}: dependency provenance is invalid")
        isolation = skillopt_receipt.get("isolation")
        if (
            not isinstance(isolation, dict)
            or isolation.get("mode") != "builtin_macos_sandbox_exec"
            or isolation.get("held_out_nonexposure") != "measured_per_target_invocation"
            or isolation.get("host_filesystem_control") != "default_deny_measured"
            or isolation.get("network_control") != "default_deny_measured"
            or isolation.get("measurement_count") != 2
        ):
            errors.append(f"{skillopt_label}: isolation measurement is incomplete")
        if (
            skillopt_receipt.get("evidence_level") != "dependency-exercised-isolated"
            or skillopt_receipt.get("eligible_for_held_out_claims") is not True
            or skillopt_receipt.get("eligible_as_held_out_staging_input") is not True
            or skillopt_receipt.get("eligible_for_staging") is not False
            or skillopt_receipt.get("optimization_gain_claimed") is not False
        ):
            errors.append(f"{skillopt_label}: evidence/claim boundary is invalid")
        blockers = skillopt_receipt.get("staging_blockers")
        if blockers != [
            "strict_score_receipt",
            "repeated_trials",
            "cross_model_confirmation",
        ]:
            errors.append(f"{skillopt_label}: staging blockers are incomplete")
        bank_receipts = skillopt_receipt.get("banks")
        if not isinstance(bank_receipts, dict) or set(bank_receipts) != {
            "ood",
            "test",
            "train",
            "valid_seen",
            "valid_unseen",
        }:
            errors.append(f"{skillopt_label}: five-bank receipt is incomplete")
        else:
            bank_hashes = [bank.get("sha256") for bank in bank_receipts.values()]
            if any(
                not isinstance(digest, str)
                or re.fullmatch(r"[0-9a-f]{64}", digest) is None
                for digest in bank_hashes
            ) or len(bank_hashes) != len(set(bank_hashes)):
                errors.append(f"{skillopt_label}: bank hashes are invalid or reused")
        if (
            skillopt_status.get("status") != "passed"
            or skillopt_status.get("isolation_mode") != "builtin_macos_sandbox_exec"
            or skillopt_status.get("measurement_count") != 2
            or skillopt_status.get("adapter_receipt_sha256")
            != sha256(skillopt_receipt_path)
        ):
            errors.append(f"{skillopt_label}: E2E status is stale or invalid")

    evaluator_directory = root / "evidence/integrations/evaluator-sandbox"
    evaluator_manifest = _load_json_if_present(evaluator_directory / "manifest.json")
    evaluator_report = _load_json_if_present(evaluator_directory / "report.json")
    evaluator_summary = _load_json_if_present(
        evaluator_directory / "adversarial-summary.json"
    )
    evaluator_results = evaluator_directory / "results.jsonl"
    evaluator_label = "evidence/integrations/evaluator-sandbox"
    if (
        not all(
            isinstance(document, dict)
            for document in (evaluator_manifest, evaluator_report, evaluator_summary)
        )
        or not evaluator_results.is_file()
    ):
        errors.append(f"{evaluator_label}: required containment receipts are missing")
    else:
        count += 1
        try:
            rows = [
                json.loads(line)
                for line in evaluator_results.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except (OSError, UnicodeError, json.JSONDecodeError):
            rows = []
        expected_scope = "containment_mechanism_fixture"
        if (
            evaluator_manifest.get("results_sha256") != sha256(evaluator_results)
            or evaluator_manifest.get("result_count") != len(rows)
            or len(rows) != 2
        ):
            errors.append(f"{evaluator_label}: results binding is stale")
        for label, document in (
            ("manifest", evaluator_manifest),
            ("report", evaluator_report),
            ("adversarial-summary", evaluator_summary),
        ):
            if (
                document.get("evaluation_scope") != expected_scope
                or document.get("eligible_for_held_out_claims") is not False
                or document.get("supports_candidate_quality_claim") is not False
                or document.get("supports_human_learning_claim") is not False
            ):
                errors.append(
                    f"{evaluator_label}/{label}: containment claim boundary is invalid"
                )
        for row in rows:
            if (
                not isinstance(row, dict)
                or row.get("evaluation_scope") != expected_scope
                or row.get("eligible_for_held_out_claims") is not False
                or row.get("isolation_level") != "builtin_macos_sandbox_exec"
                or row.get("hidden_bank_nonexposure_verified") is not True
                or row.get("network_isolation_verified") is not True
                or row.get("isolation_probes_passed") is not True
                or row.get("workspace_removed") is not True
            ):
                errors.append(f"{evaluator_label}: a containment result is invalid")
                break
        if not all(
            evaluator_summary.get(field) is True
            for field in (
                "candidate_read_blocked",
                "hidden_bank_read_blocked",
                "network_blocked",
                "outside_write_blocked",
                "source_target_read_blocked",
            )
        ):
            errors.append(f"{evaluator_label}: adversarial denials are incomplete")
    return count, errors


def validate_legacy_asset_provenance(root: Path) -> tuple[int, list[str]]:
    """Bind every restored legacy asset to its recorded source and target bytes."""

    if not (root / "SKILL.md").is_file():
        return 0, []
    relative = "evidence/provenance/legacy-assets.json"
    document = _load_json_if_present(root / relative)
    if not isinstance(document, dict):
        return 0, [f"{relative}: required legacy provenance manifest is missing"]
    errors: list[str] = []
    assets = document.get("assets")
    if not isinstance(assets, list) or document.get("asset_count") != len(assets):
        return 1, [f"{relative}: asset_count must match the assets array"]
    expected_targets = {
        "GLOSSARY-FORMAT.md",
        "LEARNING-RECORD-FORMAT.md",
        "MISSION-FORMAT.md",
        "RESOURCES-FORMAT.md",
        "assets/visualization-router.png",
        "assets/visualization-router.svg",
        "references/LEGACY-VISUALIZATION-ROUTER.md",
        "references/VISUALIZATION-RESEARCH.md",
        "references/VISUALIZATION-TOOL-REGISTRY.md",
        "references/visualization-tool-registry.json",
        "scripts/find_visualization_tool.py",
        "scripts/test_visualization_registry.py",
    }
    seen: set[str] = set()
    source_root_text = document.get("source_root")
    source_root = (
        Path(source_root_text)
        if isinstance(source_root_text, str) and source_root_text
        else None
    )
    for index, asset in enumerate(assets):
        label = f"{relative}: assets[{index}]"
        if not isinstance(asset, dict):
            errors.append(f"{label} must be an object")
            continue
        target = asset.get("target")
        source = asset.get("source")
        source_digest = asset.get("source_sha256")
        target_digest = asset.get("target_sha256")
        relation = asset.get("relation")
        if not isinstance(target, str) or not isinstance(source, str):
            errors.append(f"{label} requires source and target paths")
            continue
        target_parts = PurePosixPath(target)
        source_parts = PurePosixPath(source)
        if (
            target_parts.is_absolute()
            or source_parts.is_absolute()
            or ".." in target_parts.parts
            or ".." in source_parts.parts
        ):
            errors.append(f"{label} contains an unsafe path")
            continue
        if target in seen:
            errors.append(f"{label} duplicates target {target!r}")
        seen.add(target)
        if relation not in {
            "byte-identical",
            "renamed-byte-identical",
            "format-only",
            "portability-adapted",
        }:
            errors.append(f"{label} has an unsupported relation")
        for name, digest in (
            ("source_sha256", source_digest),
            ("target_sha256", target_digest),
        ):
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                errors.append(f"{label}.{name} must be a SHA-256")
        target_path = root / target
        if target_path.is_symlink() or not target_path.is_file():
            errors.append(f"{label} target is missing or unsafe: {target}")
        elif sha256(target_path) != target_digest:
            errors.append(f"{label} target digest mismatch: {target}")
        if relation in {"byte-identical", "renamed-byte-identical"} and (
            source_digest != target_digest
        ):
            errors.append(f"{label} claims byte identity but hashes differ")
        if relation in {"format-only", "portability-adapted"} and not asset.get(
            "adaptation"
        ):
            errors.append(f"{label} {relation} relation requires an explanation")
        if relation == "portability-adapted" and source_digest == target_digest:
            errors.append(f"{label} portability adaptation did not change the bytes")
        if source_root is not None and source_root.is_dir():
            source_path = source_root / source
            if source_path.is_symlink() or not source_path.is_file():
                errors.append(f"{label} local source is missing or unsafe: {source}")
            elif sha256(source_path) != source_digest:
                errors.append(f"{label} local source digest mismatch: {source}")
    missing = sorted(expected_targets - seen)
    unexpected = sorted(seen - expected_targets)
    if missing:
        errors.append(f"{relative}: missing restored targets {missing}")
    if unexpected:
        errors.append(f"{relative}: unexpected restored targets {unexpected}")
    registry = document.get("registry")
    registry_document = _load_json_if_present(
        root / "references/visualization-tool-registry.json"
    )
    tools = (
        registry_document.get("tools") if isinstance(registry_document, dict) else None
    )
    if (
        not isinstance(registry, dict)
        or registry.get("expected_tool_count") != 38
        or registry.get("test_count") != 12
        or not isinstance(tools, list)
        or len(tools) != 38
    ):
        errors.append(f"{relative}: registry/test count receipt is invalid")
    return 1, errors


def _release_file_manifest(root: Path) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for current, directory_names, file_names in os.walk(root, followlinks=False):
        current_path = Path(current)
        kept: list[str] = []
        for name in sorted(directory_names):
            if should_prune_directory(name):
                continue
            path = current_path / name
            if path.is_symlink():
                raise ValueError(
                    f"release tree contains a directory symlink: "
                    f"{path.relative_to(root)}"
                )
            kept.append(name)
        directory_names[:] = kept
        for name in sorted(file_names):
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if relative == VERIFICATION_RECEIPT_RELATIVE:
                continue
            metadata = path.lstat()
            if not stat.S_ISREG(metadata.st_mode):
                raise ValueError(
                    f"release tree contains a non-regular file: {relative}"
                )
            files.append(
                {
                    "mode": distributable_mode(metadata.st_mode),
                    "path": relative,
                    "sha256": sha256(path),
                }
            )
    files.sort(key=lambda item: item["path"])
    encoded = json.dumps(
        files, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return {
        "algorithm": "sha256(canonical-json(files[path,mode,sha256]))",
        "excluded": [
            VERIFICATION_RECEIPT_RELATIVE,
            ".git/",
            "runtime/cache directories",
        ],
        "file_count": len(files),
        "files": files,
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }


def _bound_regular_file(
    root: Path,
    relative: Any,
    digest: Any,
    *,
    label: str,
) -> list[str]:
    """Validate a relative regular-file path and its SHA-256 binding."""

    if not isinstance(relative, str) or not relative:
        return [f"{label}: path must be a non-empty string"]
    parts = PurePosixPath(relative)
    if parts.is_absolute() or ".." in parts.parts or parts.as_posix() != relative:
        return [f"{label}: unsafe path {relative!r}"]
    path = root / Path(*parts.parts)
    try:
        root_resolved = root.resolve(strict=True)
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError):
        return [f"{label}: missing or unsafe file {relative!r}"]
    parent = root
    parent_symlink = False
    for part in parts.parts[:-1]:
        parent /= part
        parent_symlink = parent_symlink or parent.is_symlink()
    if (
        parent_symlink
        or path.is_symlink()
        or not resolved.is_relative_to(root_resolved)
        or not resolved.is_file()
    ):
        return [f"{label}: missing or unsafe file {relative!r}"]
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        return [f"{label}: digest must be a SHA-256"]
    if sha256(resolved) != digest:
        return [f"{label}: digest mismatch for {relative}"]
    return []


def validate_forward_behavior_receipt(root: Path) -> tuple[int, list[str]]:
    """Bind fresh-context outputs to the frozen rubric and independent score."""

    rubric_path = root / FORWARD_RUBRIC_RELATIVE
    if not rubric_path.is_file():
        return 0, []
    errors: list[str] = []
    rubric = _load_json_if_present(rubric_path)
    run_path = root / FORWARD_RUN_RELATIVE
    run = _load_json_if_present(run_path)
    receipt_path = root / FORWARD_RECEIPT_RELATIVE
    receipt = _load_json_if_present(receipt_path)
    label = "forward behavior evidence"
    if not isinstance(rubric, dict):
        return 1, [f"{label}: rubric is missing or invalid"]
    if not isinstance(run, dict):
        return 1, [f"{label}: run receipt is missing or invalid"]
    if not isinstance(receipt, dict):
        return 1, [f"{label}: independent review receipt is missing or invalid"]

    rubric_cases = rubric.get("cases")
    evaluation = rubric.get("evaluation")
    if (
        rubric.get("schema_version") != 1
        or rubric.get("rubric_version") != "1.1.0"
        or not isinstance(rubric_cases, list)
        or len(rubric_cases) != 8
        or not isinstance(evaluation, dict)
        or evaluation.get("fresh_context_per_case") is not True
        or evaluation.get("independent_reviewer_required") is not True
        or evaluation.get("minimum_passes") != 8
        or evaluation.get("output_receipt") != FORWARD_RECEIPT_RELATIVE
    ):
        errors.append(f"{label}: frozen rubric contract is invalid")
        rubric_cases = rubric_cases if isinstance(rubric_cases, list) else []
    rubric_by_id: dict[str, dict[str, Any]] = {}
    for case in rubric_cases:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str):
            errors.append(f"{label}: rubric contains an invalid case")
            continue
        case_id = case["id"]
        if case_id in rubric_by_id:
            errors.append(f"{label}: duplicate rubric case {case_id!r}")
        rubric_by_id[case_id] = case

    rubric_digest = sha256(rubric_path)
    if (
        run.get("schema_version") != 1
        or run.get("rubric") != FORWARD_RUBRIC_RELATIVE
        or run.get("rubric_sha256") != rubric_digest
        or run.get("scored_by_runner") is not False
    ):
        errors.append(f"{label}: run is not bound to the frozen rubric")
    fresh_contract = run.get("fresh_context_contract")
    if (
        not isinstance(fresh_contract, dict)
        or fresh_contract.get("fork_turns") != "none"
        or fresh_contract.get("one_child_task_per_case") is not True
        or fresh_contract.get("coordinator_did_not_supply_prior_case_outputs")
        is not True
    ):
        errors.append(f"{label}: fresh-context contract is invalid")

    run_cases = run.get("cases")
    run_by_id: dict[str, dict[str, Any]] = {}
    fresh_tasks: set[str] = set()
    output_binding_count = 0
    context_binding_count = 0
    if not isinstance(run_cases, list) or len(run_cases) != len(rubric_by_id):
        errors.append(f"{label}: run case count does not match the rubric")
        run_cases = run_cases if isinstance(run_cases, list) else []
    for case in run_cases:
        if not isinstance(case, dict) or not isinstance(case.get("case_id"), str):
            errors.append(f"{label}: run contains an invalid case")
            continue
        case_id = case["case_id"]
        if case_id in run_by_id:
            errors.append(f"{label}: duplicate run case {case_id!r}")
        run_by_id[case_id] = case
        task = case.get("fresh_task")
        if not isinstance(task, str) or not task.strip():
            errors.append(f"{label}: {case_id} has no fresh task identity")
        elif task.strip() in fresh_tasks:
            errors.append(f"{label}: fresh task {task!r} is reused")
        else:
            fresh_tasks.add(task.strip())
        output = case.get("output")
        if not isinstance(output, str) or not output.startswith(
            "evidence/forward/outputs/"
        ):
            errors.append(f"{label}: {case_id} output is outside the output directory")
        output_binding_count += 1
        errors.extend(
            _bound_regular_file(
                root,
                output,
                case.get("output_sha256"),
                label=f"{label} output",
            )
        )
        has_context_path = "context" in case
        has_context_digest = "context_sha256" in case
        if case_id == "resume-hinted-evidence" and not (
            has_context_path and has_context_digest
        ):
            errors.append(
                f"{label}: resume-hinted-evidence must bind its public context"
            )
        if has_context_path or has_context_digest:
            context_binding_count += 1
            context = case.get("context")
            if isinstance(context, str) and not context.startswith(
                "evidence/forward/context/"
            ):
                errors.append(
                    f"{label}: {case_id} context is outside the context directory"
                )
            errors.extend(
                _bound_regular_file(
                    root,
                    context,
                    case.get("context_sha256"),
                    label=f"{label} context",
                )
            )
    if set(run_by_id) != set(rubric_by_id):
        errors.append(f"{label}: run case IDs do not match the rubric")

    source_files = run.get("source_files")
    source_binding_count = len(source_files) if isinstance(source_files, dict) else 0
    if not isinstance(source_files, dict) or "SKILL.md" not in source_files:
        errors.append(f"{label}: source bindings must include SKILL.md")
    else:
        for relative, digest in source_files.items():
            errors.extend(
                _bound_regular_file(
                    root,
                    relative,
                    digest,
                    label=f"{label} source",
                )
            )

    execution_files = run.get("execution_files")
    required_execution_files = {
        "evidence/forward/execution/practical_gradient_descent.py",
        "evidence/forward/execution/practical_gradient_descent.stdout",
    }
    execution_binding_count = (
        len(execution_files) if isinstance(execution_files, dict) else 0
    )
    if (
        not isinstance(execution_files, dict)
        or set(execution_files) != required_execution_files
    ):
        errors.append(f"{label}: practical execution bindings are missing or invalid")
    else:
        for relative, digest in execution_files.items():
            errors.extend(
                _bound_regular_file(
                    root,
                    relative,
                    digest,
                    label=f"{label} execution",
                )
            )
    practical_run = run_by_id.get("practical-executable-learning", {})
    if practical_run.get("execution_files") != sorted(required_execution_files):
        errors.append(f"{label}: practical case is not bound to its execution evidence")

    if (
        receipt.get("schema_version") != 1
        or receipt.get("rubric_sha256") != rubric_digest
        or receipt.get("run_sha256") != sha256(run_path)
    ):
        errors.append(f"{label}: review is not bound to the current run and rubric")
    reviewer = receipt.get("reviewer")
    reviewer_task = reviewer.get("task") if isinstance(reviewer, dict) else None
    reviewer_identity = reviewer.get("identity") if isinstance(reviewer, dict) else None
    if (
        not isinstance(reviewer, dict)
        or reviewer.get("independent_from_runner") is not True
        or not isinstance(reviewer_task, str)
        or not reviewer_task.strip()
        or reviewer_task.strip() in fresh_tasks
        or not isinstance(reviewer_identity, str)
        or not reviewer_identity.strip()
        or reviewer_identity.strip() in fresh_tasks
    ):
        errors.append(f"{label}: reviewer is not independently identified")
    hash_verification = receipt.get("hash_verification")
    if (
        not isinstance(hash_verification, dict)
        or hash_verification.get("status") != "passed"
        or hash_verification.get("all_bound_hashes_match") is not True
    ):
        errors.append(f"{label}: reviewer hash verification did not pass")
    expected_hash_counts = {
        "rubric_count": 1,
        "run_count": 1,
        "source_count": source_binding_count,
        "context_count": context_binding_count,
        "output_count": output_binding_count,
        "execution_count": execution_binding_count,
    }
    expected_hash_counts["checked_count"] = sum(expected_hash_counts.values())
    if not isinstance(hash_verification, dict) or any(
        type(hash_verification.get(field)) is not int
        or hash_verification.get(field) != expected
        for field, expected in expected_hash_counts.items()
    ):
        errors.append(f"{label}: hash binding counts do not match")

    scored_cases = receipt.get("cases")
    scored_by_id: dict[str, dict[str, Any]] = {}
    if not isinstance(scored_cases, list) or len(scored_cases) != len(rubric_by_id):
        errors.append(f"{label}: scored case count does not match the rubric")
        scored_cases = scored_cases if isinstance(scored_cases, list) else []
    for score in scored_cases:
        if not isinstance(score, dict) or not isinstance(score.get("case_id"), str):
            errors.append(f"{label}: review contains an invalid scored case")
            continue
        case_id = score["case_id"]
        scored_by_id[case_id] = score
        rubric_case = rubric_by_id.get(case_id)
        run_case = run_by_id.get(case_id)
        if rubric_case is None or run_case is None:
            errors.append(f"{label}: review has unknown case {case_id!r}")
            continue
        if (
            score.get("output") != run_case.get("output")
            or score.get("status") != "passed"
            or score.get("remediation") != []
        ):
            errors.append(f"{label}: {case_id} did not pass its hard gate")
        required = score.get("required")
        forbidden = score.get("forbidden")
        required_items = (
            {item.get("item"): item for item in required if isinstance(item, dict)}
            if isinstance(required, list)
            else {}
        )
        forbidden_items = (
            {item.get("item"): item for item in forbidden if isinstance(item, dict)}
            if isinstance(forbidden, list)
            else {}
        )
        if set(required_items) != set(rubric_case.get("required", [])) or any(
            item.get("verdict") != "pass" or item.get("present") is not True
            for item in required_items.values()
        ):
            errors.append(f"{label}: {case_id} required behaviors did not all pass")
        if set(forbidden_items) != set(rubric_case.get("forbidden", [])) or any(
            item.get("verdict") != "pass" or item.get("present") is not False
            for item in forbidden_items.values()
        ):
            errors.append(f"{label}: {case_id} forbidden behaviors did not all pass")
    if set(scored_by_id) != set(rubric_by_id):
        errors.append(f"{label}: scored case IDs do not match the rubric")

    overall = receipt.get("overall")
    if (
        receipt.get("hard_gate_passed") is not True
        or receipt.get("status") != "passed"
        or receipt.get("remediation") != []
        or receipt.get("supports_candidate_superiority") is not False
        or receipt.get("supports_human_learning_claim") is not False
        or not isinstance(receipt.get("claim_boundary"), str)
        or not receipt["claim_boundary"].strip()
        or overall
        != {
            "case_count": 8,
            "pass_count": 8,
            "fail_count": 0,
            "minimum_passes": 8,
            "status": "passed",
        }
    ):
        errors.append(f"{label}: aggregate hard gate or claim boundary is invalid")
    return 1, errors


def validate_independent_review_receipts(root: Path) -> tuple[int, list[str]]:
    """Require three independent reviews of the exact same final payload."""

    payload_path = root / REVIEW_PAYLOAD_RELATIVE
    required = (root / "SKILL.md").is_file() or payload_path.exists()
    if not required:
        return 0, []
    errors: list[str] = []
    reviews_dir = root / "evidence/reviews"
    allowed_review_names = {
        "payload.json",
        *(f"{review_type}.json" for review_type in REVIEW_TYPES),
    }
    if reviews_dir.is_dir():
        for entry in sorted(reviews_dir.iterdir(), key=lambda item: item.name):
            if entry.name not in allowed_review_names:
                errors.append(f"evidence/reviews/{entry.name}: unknown review entry")
    payload = _load_strict_bounded_json(payload_path)
    if not isinstance(payload, dict):
        return 0, ["independent review payload is missing or invalid"]
    try:
        expected_payload = payload_manifest(root)
    except (OSError, PayloadError) as exc:
        errors.append(f"independent review payload cannot be recomputed: {exc}")
        expected_payload = None
    if payload != expected_payload:
        errors.append("independent review payload is stale")
    payload_file_digest = sha256(payload_path)
    payload_manifest_digest = payload.get("sha256")

    count = 0
    reviewer_tasks: set[str] = set()
    for review_type in REVIEW_TYPES:
        relative = f"evidence/reviews/{review_type}.json"
        path = root / relative
        receipt = _load_strict_bounded_json(path, maximum=256 * 1024)
        label = f"{relative}:"
        if not isinstance(receipt, dict):
            errors.append(f"{label} required review receipt is missing or invalid")
            continue
        count += 1
        expected_keys = set(REVIEW_COMMON_KEYS)
        if review_type == "architecture-council":
            expected_keys.update({"chair", "panelists"})
        if set(receipt) != expected_keys:
            errors.append(f"{label} receipt does not match the exact schema")
        if (
            receipt.get("schema_version") != 2
            or receipt.get("review_type") != review_type
        ):
            errors.append(f"{label} schema or review type is invalid")
        if receipt.get("attestation") != REVIEW_ATTESTATION:
            errors.append(
                f"{label} attestation must state that cryptographic authorship "
                "is not verified"
            )
        try:
            encoded_size = len(
                json.dumps(
                    receipt,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
            )
        except (TypeError, ValueError):
            encoded_size = 256 * 1024 + 1
        if encoded_size > 256 * 1024:
            errors.append(f"{label} receipt exceeds the bounded schema size")
        if (
            receipt.get("payload") != REVIEW_PAYLOAD_RELATIVE
            or receipt.get("payload_file_sha256") != payload_file_digest
            or receipt.get("payload_manifest_sha256") != payload_manifest_digest
        ):
            errors.append(f"{label} receipt is not bound to the current payload")
        reviewer = receipt.get("reviewer")
        task = reviewer.get("task") if isinstance(reviewer, dict) else None
        if (
            not isinstance(reviewer, dict)
            or set(reviewer) != {"identity", "independent_from_implementation", "task"}
            or reviewer.get("independent_from_implementation") is not True
            or not isinstance(reviewer.get("identity"), str)
            or not reviewer["identity"].strip()
            or len(reviewer["identity"]) > 512
            or not isinstance(task, str)
            or not task.strip()
            or len(task) > 512
            or task.strip() in reviewer_tasks
        ):
            errors.append(f"{label} reviewer is not independently identified")
        else:
            reviewer_tasks.add(task.strip())
        if (
            receipt.get("status") != "passed"
            or not isinstance(receipt.get("findings"), list)
            or len(receipt.get("findings", [])) > 100
            or not isinstance(receipt.get("fixes"), list)
            or len(receipt.get("fixes", [])) > 100
            or receipt.get("unresolved_actionable") != []
            or receipt.get("recheck")
            != {"status": "passed", "reviewer_confirmed": True}
        ):
            errors.append(f"{label} actionable findings are not closed and rechecked")
        if review_type == "architecture-council":
            panelists = receipt.get("panelists")
            chair = receipt.get("chair")
            panel_tasks = (
                [
                    item.get("task", "").strip()
                    for item in panelists
                    if isinstance(item, dict) and isinstance(item.get("task"), str)
                ]
                if isinstance(panelists, list)
                else []
            )
            if (
                len(panel_tasks) != 3
                or len(set(panel_tasks)) != 3
                or bool(set(panel_tasks) & reviewer_tasks)
                or any(
                    not isinstance(item, dict)
                    or set(item) != {"status", "task"}
                    or not isinstance(item.get("task"), str)
                    or not item["task"].strip()
                    or len(item["task"]) > 512
                    or item.get("status") != "passed"
                    for item in panelists or []
                )
                or not isinstance(chair, dict)
                or set(chair) != {"status", "task"}
                or not isinstance(chair.get("task"), str)
                or not chair["task"].strip()
                or len(chair["task"]) > 512
                or chair.get("task", "").strip() in set(panel_tasks)
                or chair.get("task", "").strip() in reviewer_tasks
                or chair.get("status") != "passed"
            ):
                errors.append(f"{label} council panel or chair receipt is invalid")
    if count != 3:
        errors.append(f"independent reviews: expected 3 receipts, found {count}")
    return count, errors


def validate_verification_receipt(root: Path) -> tuple[int, list[str]]:
    """Reject a green verification receipt after any durable release byte drifts."""

    if not (root / "SKILL.md").is_file():
        return 0, []
    path = root / VERIFICATION_RECEIPT_RELATIVE
    document = _load_strict_bounded_json(path)
    if not isinstance(document, dict):
        return 0, [f"{VERIFICATION_RECEIPT_RELATIVE}: required receipt is missing"]
    errors: list[str] = []
    expected_document_keys = set(VERIFICATION_COMMON_KEYS)
    if document.get("status") == "passed":
        expected_document_keys.add("postflight_validation")
    if set(document) != expected_document_keys:
        errors.append(
            f"{VERIFICATION_RECEIPT_RELATIVE}: receipt does not match the exact schema"
        )
    if document.get("schema_version") != 3:
        errors.append(f"{VERIFICATION_RECEIPT_RELATIVE}: schema_version must be 3")
    if document.get("log_retention") != VERIFICATION_LOG_RETENTION:
        errors.append(
            f"{VERIFICATION_RECEIPT_RELATIVE}: log retention must state that full "
            "logs are not persisted and only their SHA-256 digest and tail are retained"
        )
    try:
        generated_at = datetime.fromisoformat(
            str(document.get("generated_at", "")).replace("Z", "+00:00")
        )
    except ValueError:
        generated_at = None
    if (
        document.get("evidence_level") != "engineering-verification"
        or document.get("external_human_learning_gates_satisfied") is not False
        or document.get("scientific_learning_claim_supported") is not False
        or not isinstance(document.get("generated_at"), str)
        or len(document.get("generated_at", "")) > 128
        or generated_at is None
        or generated_at.tzinfo is None
        or not isinstance(document.get("run_id"), str)
        or not 1 <= len(document.get("run_id", "")) <= 128
        or not isinstance(document.get("source_date_epoch"), str)
        or not document.get("source_date_epoch", "").isdigit()
        or document.get("level") not in {"core", "full"}
        or type(document.get("trusted_macos_sandbox_tests_required")) is not bool
    ):
        errors.append(
            f"{VERIFICATION_RECEIPT_RELATIVE}: verification metadata is invalid"
        )
    try:
        actual_manifest = _release_file_manifest(root)
    except (OSError, ValueError) as exc:
        errors.append(f"{VERIFICATION_RECEIPT_RELATIVE}: {exc}")
        actual_manifest = None
    if document.get("root_manifest") != actual_manifest:
        errors.append(
            f"{VERIFICATION_RECEIPT_RELATIVE}: release-file manifest is stale or forged"
        )
    script = root / "scripts/verify.py"
    if not script.is_file() or document.get("verification_script_sha256") != sha256(
        script
    ):
        errors.append(
            f"{VERIFICATION_RECEIPT_RELATIVE}: verification script digest is stale"
        )
    status = document.get("status")
    active_run = os.environ.get("PRAX_ACTIVE_VERIFICATION_RUN_ID")
    if status == "running":
        if not active_run or active_run != document.get("run_id"):
            errors.append(
                f"{VERIFICATION_RECEIPT_RELATIVE}: running receipt is not bound "
                "to this active verifier"
            )
    elif status == "passed":
        gates = document.get("gates")
        expected_gates = {
            "html-exact-parity",
            "node-tests",
            "package-validator",
            "python-format",
            "python-lint",
            "python-tests",
            "visual-registry-count",
            "visual-registry-tests",
        }
        if (
            not isinstance(gates, list)
            or len(gates) != len(expected_gates)
            or {gate.get("name") for gate in gates if isinstance(gate, dict)}
            != expected_gates
            or any(
                not isinstance(gate, dict)
                or gate.get("status") != "passed"
                or gate.get("exit_code") != 0
                for gate in gates
            )
        ):
            errors.append(
                f"{VERIFICATION_RECEIPT_RELATIVE}: passed receipt has incomplete gates"
            )
        elif any(
            set(gate)
            != {
                "command",
                "exit_code",
                "name",
                "output_sha256",
                "output_tail",
                "policy_failures",
                "status",
            }
            or not isinstance(gate.get("command"), list)
            or not 1 <= len(gate["command"]) <= 100
            or any(
                not isinstance(argument, str) or not 1 <= len(argument) <= 4096
                for argument in gate["command"]
            )
            or not isinstance(gate.get("output_sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", gate["output_sha256"]) is None
            or not isinstance(gate.get("output_tail"), list)
            or len(gate["output_tail"]) > VERIFICATION_LOG_RETENTION["tail_line_limit"]
            or any(
                not isinstance(line, str) or len(line) > 10_000
                for line in gate["output_tail"]
            )
            or not isinstance(gate.get("policy_failures"), list)
            or len(gate["policy_failures"]) > 100
            or any(
                not isinstance(failure, str) or len(failure) > 10_000
                for failure in gate["policy_failures"]
            )
            for gate in gates
        ):
            errors.append(
                f"{VERIFICATION_RECEIPT_RELATIVE}: gate does not match the exact "
                "bounded schema"
            )
        postflight = document.get("postflight_validation")
        active_preflight = active_run and active_run == document.get("run_id")
        if not active_preflight and (
            not isinstance(postflight, dict)
            or set(postflight)
            != {"command", "exit_code", "output_sha256", "output_tail", "status"}
            or postflight.get("status") != "passed"
            or postflight.get("exit_code") != 0
            or not isinstance(postflight.get("command"), list)
            or not 1 <= len(postflight["command"]) <= 100
            or any(
                not isinstance(argument, str) or not 1 <= len(argument) <= 4096
                for argument in postflight["command"]
            )
            or not isinstance(postflight.get("output_sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", postflight["output_sha256"]) is None
            or not isinstance(postflight.get("output_tail"), list)
            or len(postflight["output_tail"])
            > VERIFICATION_LOG_RETENTION["tail_line_limit"]
            or any(
                not isinstance(line, str) or len(line) > 10_000
                for line in postflight["output_tail"]
            )
        ):
            errors.append(
                f"{VERIFICATION_RECEIPT_RELATIVE}: passed receipt lacks a "
                "successful final validator postflight"
            )
    else:
        errors.append(
            f"{VERIFICATION_RECEIPT_RELATIVE}: status must be passed outside an active run"
        )
    dependencies = document.get("dependencies")
    expected_locks = {
        "integrations/flint/package-lock.json",
        "integrations/skillopt/SOURCE.json",
        "package-lock.json",
        "uv.lock",
    }
    expected_installed = {
        "fsrs",
        "node",
        "npm",
        "python",
        "python_implementation",
        "ruff",
    }
    if (
        not isinstance(dependencies, dict)
        or set(dependencies) != {"installed", "locks"}
        or not isinstance(dependencies.get("installed"), dict)
        or set(dependencies.get("installed", {})) != expected_installed
        or any(
            not isinstance(value, str) or not 1 <= len(value) <= 1024
            for value in dependencies.get("installed", {}).values()
        )
    ):
        errors.append(
            f"{VERIFICATION_RECEIPT_RELATIVE}: runtime dependency receipt is missing"
        )
    else:
        locks = dependencies.get("locks")
        if not isinstance(locks, dict) or set(locks) != expected_locks:
            errors.append(
                f"{VERIFICATION_RECEIPT_RELATIVE}: lockfile receipt is missing"
            )
        else:
            for relative, digest in locks.items():
                lock = root / relative
                if (
                    not isinstance(relative, str)
                    or not isinstance(digest, str)
                    or re.fullmatch(r"[0-9a-f]{64}", digest) is None
                    or PurePosixPath(relative).is_absolute()
                    or PurePosixPath(relative).as_posix() != relative
                    or ".." in PurePosixPath(relative).parts
                    or not lock.is_file()
                    or sha256(lock) != digest
                ):
                    errors.append(
                        f"{VERIFICATION_RECEIPT_RELATIVE}: stale lock digest {relative!r}"
                    )
    skillopt_source = document.get("skillopt_source")
    if (
        not isinstance(skillopt_source, dict)
        or set(skillopt_source) != {"commit", "path", "tree", "worktree_clean"}
        or skillopt_source.get("commit") != "e4ea6a6771e797ef820cdd8bfea64c57e0481065"
        or not isinstance(skillopt_source.get("path"), str)
        or not 1 <= len(skillopt_source.get("path", "")) <= 4096
        or not isinstance(skillopt_source.get("tree"), str)
        or re.fullmatch(r"[0-9a-f]{40}", skillopt_source["tree"]) is None
        or skillopt_source.get("worktree_clean") is not True
    ):
        errors.append(
            f"{VERIFICATION_RECEIPT_RELATIVE}: SkillOpt source provenance is invalid"
        )
    return 1, errors


def validate_package_contract(root: Path) -> tuple[int, list[str]]:
    skill = root / "SKILL.md"
    if not skill.is_file():
        return 0, []
    fields, errors = _frontmatter_fields(skill, root)
    if fields.get("name") != "prax-teach-v2":
        errors.append("SKILL.md: name must be 'prax-teach-v2'")
    description = fields.get("description", "")
    if not description or len(description) > 1024:
        errors.append("SKILL.md: description must contain 1 to 1024 characters")

    agent = root / "agents/openai.yaml"
    try:
        agent_text = agent.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        errors.append(
            "agents/openai.yaml: required UI metadata is missing or unreadable"
        )
    else:
        for field in ("display_name", "short_description", "default_prompt"):
            if not re.search(
                rf"^\s{{2}}{field}:\s+[\"'].+[\"']\s*$",
                agent_text,
                re.MULTILINE,
            ):
                errors.append(f"agents/openai.yaml: {field} is missing or malformed")
        if "$prax-teach-v2" not in agent_text:
            errors.append(
                "agents/openai.yaml: default_prompt must invoke $prax-teach-v2"
            )

    errors.extend(validate_dependency_contract(root))
    return 1, errors


def validate_visual_verification_fixture(root: Path) -> tuple[int, list[str]]:
    """Recompute every frozen visual-route receipt instead of trusting pass flags."""

    manifest_path = root / VISUAL_VERIFICATION_FIXTURE
    if not manifest_path.is_file():
        return 0, [f"{VISUAL_VERIFICATION_FIXTURE}: required fixture is missing"]
    manifest = _load_json_if_present(manifest_path)
    if (
        not isinstance(manifest, dict)
        or set(manifest) != {"cases", "schema_version"}
        or manifest.get("schema_version") != 1
        or not isinstance(manifest.get("cases"), list)
    ):
        return 0, [f"{VISUAL_VERIFICATION_FIXTURE}: fixture contract is invalid"]
    cases = manifest["cases"]
    required_routes = {"none", "static", "interactive", "motion"}
    required_case_keys = {
        "expected_route",
        "forbidden_answer_file",
        "html",
        "id",
        "receipt",
        "route_output",
        "source",
    }
    errors: list[str] = []
    seen_ids: set[str] = set()
    seen_routes: set[str] = set()
    verified = 0
    if len(cases) != len(required_routes):
        errors.append(
            f"{VISUAL_VERIFICATION_FIXTURE}: expected exactly four route cases"
        )
    for index, case in enumerate(cases):
        label = f"{VISUAL_VERIFICATION_FIXTURE}: case {index + 1}"
        if not isinstance(case, dict) or set(case) != required_case_keys:
            errors.append(f"{label} contract is invalid")
            continue
        case_id = case.get("id")
        expected_route = case.get("expected_route")
        if (
            not isinstance(case_id, str)
            or not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", case_id)
            or case_id in seen_ids
        ):
            errors.append(f"{label} has an invalid or duplicate id")
        else:
            seen_ids.add(case_id)
        if expected_route not in required_routes or expected_route in seen_routes:
            errors.append(f"{label} has an invalid or duplicate expected route")
        else:
            seen_routes.add(expected_route)

        arguments: list[str] = []
        unsafe = False
        for option, field in (
            ("--route-output", "route_output"),
            ("--source", "source"),
            ("--html", "html"),
            ("--forbidden-answer-file", "forbidden_answer_file"),
            ("--receipt", "receipt"),
        ):
            relative = case.get(field)
            if (
                not isinstance(relative, str)
                or not relative
                or PurePosixPath(relative).is_absolute()
                or ".." in PurePosixPath(relative).parts
            ):
                errors.append(f"{label} has unsafe {field}")
                unsafe = True
                continue
            arguments.extend((option, str(root / Path(*PurePosixPath(relative).parts))))
        if unsafe:
            continue
        completed = subprocess.run(
            [
                sys.executable,
                str(root / "scripts/prax_teach.py"),
                "visual-verify",
                *arguments,
                "--check",
            ],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            env={
                **os.environ,
                "SOURCE_DATE_EPOCH": os.environ.get("SOURCE_DATE_EPOCH", "1785844800"),
            },
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            errors.append(f"{label} recomputation failed: {detail}")
            continue
        try:
            result = json.loads(completed.stdout)
        except json.JSONDecodeError:
            errors.append(f"{label} emitted a malformed result")
            continue
        if result.get("route") != expected_route or result.get("status") != "passed":
            errors.append(f"{label} result does not match the expected route")
            continue
        verifier = result.get("verifier")
        if (
            not isinstance(verifier, dict)
            or set(verifier) != {"implementation", "renderer", "version"}
            or verifier.get("version") != EXPECTED_VISUAL_VERIFIER_VERSION
        ):
            errors.append(f"{label} uses an invalid visual verifier version")
            continue
        checks = result.get("checks")
        expected_static_fallback = expected_route != "none"
        if (
            not isinstance(checks, dict)
            or set(checks) != VISUAL_RECEIPT_CHECK_KEYS
            or checks.get("actual_bytes_scanned_for_declared_textual_leakage")
            is not True
            or checks.get("animated_or_unvalidated_assets_absent") is not True
            or checks.get("attempt_before_reveal") != "passed"
            or checks.get("linked_textual_assets_scanned") is not True
            or checks.get("markdown_html_exact_parity") is not True
            or checks.get("raster_semantics_automatically_verified") is not False
            or checks.get("semantic_visual_leakage") != "manual_review_required"
            or checks.get("static_fallback_verified") is not expected_static_fallback
            or checks.get("unbundled_runtime_promoted") is not False
        ):
            errors.append(f"{label} visual receipt checks are invalid")
            continue
        verified += 1
    if seen_routes != required_routes:
        errors.append(f"{VISUAL_VERIFICATION_FIXTURE}: route matrix is incomplete")
    return verified, errors


def _criterion_receipt_errors(
    root: Path, relative: str, status_payload: dict[str, Any]
) -> list[str]:
    """Recompute an allowlisted receipt instead of trusting its filename."""

    if relative not in SUPPORTED_CRITERION_RECEIPTS:
        return [f"unsupported receipt {relative!r}"]
    receipt = root / Path(*PurePosixPath(relative).parts)
    if receipt.is_symlink() or not receipt.is_file():
        return [f"missing or unsafe receipt {relative!r}"]

    if relative == "evidence/provenance/legacy-assets.json":
        minimum_count, validator_result = 1, validate_legacy_asset_provenance(root)
    elif relative == FORWARD_RECEIPT_RELATIVE:
        minimum_count, validator_result = 1, validate_forward_behavior_receipt(root)
    elif relative == BROWSER_INSPECTION_RECEIPT_RELATIVE:
        minimum_count = 1
        validator_result = validate_browser_inspection_receipt(root, status_payload)
    elif relative == VISUAL_VERIFICATION_FIXTURE:
        minimum_count, validator_result = 4, validate_visual_verification_fixture(root)
    elif relative.startswith("evidence/integrations/"):
        minimum_count, validator_result = 3, validate_integration_manifests(root)
    elif relative.startswith("evidence/reviews/"):
        minimum_count = 3
        validator_result = validate_independent_review_receipts(root)
    elif relative == VERIFICATION_RECEIPT_RELATIVE:
        minimum_count, validator_result = 1, validate_verification_receipt(root)
    else:  # The allowlist and dispatch must remain in lockstep.
        return [f"receipt validator is not configured for {relative!r}"]

    count, errors = validator_result
    if count < minimum_count:
        errors = [
            f"receipt validator found {count}, expected at least {minimum_count}",
            *errors,
        ]
    return errors


def release_status_errors(path: Path, payload: Any, root: Path) -> list[str]:
    """Validate the exact release ledger without promoting unfinished work."""

    rel = path.relative_to(root)
    prefix = f"{rel}:"
    errors: list[str] = []
    if not isinstance(payload, dict):
        return [f"{prefix} expected an object"]

    expected_top_level = {
        "capabilities",
        "criteria",
        "external_gates",
        "north_star",
        "phases",
        "release_label",
        "schema_version",
    }
    missing_top_level = sorted(expected_top_level - set(payload))
    unknown_top_level = sorted(set(payload) - expected_top_level)
    if missing_top_level:
        errors.append(f"{prefix} missing fields {missing_top_level}")
    if unknown_top_level:
        errors.append(f"{prefix} unsupported fields {unknown_top_level}")
    if payload.get("schema_version") != 2:
        errors.append(f"{prefix} schema_version must be 2")

    release_label = payload.get("release_label")
    if release_label not in RELEASE_LABELS:
        errors.append(f"{prefix} invalid release_label {release_label!r}")

    north_star = payload.get("north_star")
    north_star_fields = {
        "design_encoded",
        "machinery_implemented",
        "scientifically_supported",
    }
    if not isinstance(north_star, dict):
        errors.append(f"{prefix} north_star must be an object")
        scientific_support = False
    else:
        if set(north_star) != north_star_fields:
            errors.append(
                f"{prefix} north_star must contain exactly {sorted(north_star_fields)}"
            )
        for field in sorted(north_star_fields):
            if type(north_star.get(field)) is not bool:
                errors.append(f"{prefix} north_star.{field} must be boolean")
        scientific_support = north_star.get("scientifically_supported") is True
    if release_label == "scientifically-supported" and not scientific_support:
        errors.append(f"{prefix} release_label cannot exceed the North Star evidence")

    phases = payload.get("phases")
    phase_capability_records: list[tuple[str, str, tuple[str, ...]]] = []
    if not isinstance(phases, list) or not phases:
        errors.append(f"{prefix} phases must be a non-empty list")
    else:
        seen_phase_ids: set[str] = set()
        for index, phase in enumerate(phases):
            label = f"{prefix} phases[{index}]"
            if not isinstance(phase, dict):
                errors.append(f"{label} must be an object")
                continue
            expected_phase_fields = {
                "capabilities",
                "evidence",
                "id",
                "parked",
                "state",
                "title",
            }
            if set(phase) != expected_phase_fields:
                errors.append(
                    f"{label} must contain exactly capabilities, evidence, id, "
                    "parked, state, and title"
                )
            phase_id = phase.get("id")
            if not isinstance(phase_id, str) or not phase_id:
                errors.append(f"{label}.id must be a non-empty string")
            elif phase_id in seen_phase_ids:
                errors.append(f"{label}.id duplicates {phase_id!r}")
            else:
                seen_phase_ids.add(phase_id)
            phase_state = phase.get("state")
            if phase_state not in EVIDENCE_STATES:
                errors.append(f"{label}.state is not a recognized evidence state")
            title = phase.get("title")
            if not isinstance(title, str) or not title.strip():
                errors.append(f"{label}.title must be a non-empty string")
            for field in ("evidence", "parked"):
                value = phase.get(field)
                if not isinstance(value, list) or not all(
                    isinstance(item, str) and item.strip() for item in value
                ):
                    errors.append(f"{label}.{field} must be a string list")
            phase_capabilities = phase.get("capabilities")
            if (
                not isinstance(phase_capabilities, list)
                or not phase_capabilities
                or not all(
                    isinstance(item, str) and item.strip()
                    for item in phase_capabilities
                )
            ):
                errors.append(f"{label}.capabilities must be a non-empty string list")
            else:
                if len(set(phase_capabilities)) != len(phase_capabilities):
                    errors.append(f"{label}.capabilities contains duplicates")
                unsupported = sorted(set(phase_capabilities) - EXPECTED_CAPABILITY_IDS)
                if unsupported:
                    errors.append(
                        f"{label}.capabilities contains unsupported IDs {unsupported}"
                    )
                if isinstance(phase_state, str):
                    phase_capability_records.append(
                        (label, phase_state, tuple(phase_capabilities))
                    )

    capabilities = payload.get("capabilities")
    seen_capability_ids: set[str] = set()
    capability_states: dict[str, str] = {}
    if not isinstance(capabilities, list) or not capabilities:
        errors.append(f"{prefix} capabilities must be a non-empty list")
    else:
        for index, capability in enumerate(capabilities):
            label = f"{prefix} capabilities[{index}]"
            if not isinstance(capability, dict):
                errors.append(f"{label} must be an object")
                continue
            if set(capability) != {"claim_limit", "evidence", "id", "state"}:
                errors.append(
                    f"{label} must contain exactly claim_limit, evidence, id, and state"
                )
            capability_id = capability.get("id")
            supported_unique_capability = False
            if not isinstance(capability_id, str) or not capability_id:
                errors.append(f"{label}.id must be a non-empty string")
            elif capability_id in seen_capability_ids:
                errors.append(f"{label}.id duplicates {capability_id!r}")
            else:
                seen_capability_ids.add(capability_id)
                if capability_id not in EXPECTED_CAPABILITY_IDS:
                    errors.append(f"{label}.id is unsupported: {capability_id!r}")
                else:
                    supported_unique_capability = True
            state = capability.get("state")
            if state not in EVIDENCE_STATES:
                errors.append(f"{label}.state is not a recognized evidence state")
            elif supported_unique_capability:
                capability_states[capability_id] = state
            evidence = capability.get("evidence")
            if (
                not isinstance(evidence, list)
                or not evidence
                or not all(isinstance(item, str) and item.strip() for item in evidence)
            ):
                errors.append(f"{label}.evidence must be a non-empty string list")
            if (
                not isinstance(capability.get("claim_limit"), str)
                or not capability["claim_limit"].strip()
            ):
                errors.append(f"{label}.claim_limit must be a non-empty string")
            if state == "scientifically-supported" and not scientific_support:
                errors.append(f"{label}.state exceeds the North Star evidence")
    missing_capabilities = sorted(EXPECTED_CAPABILITY_IDS - seen_capability_ids)
    if missing_capabilities:
        errors.append(
            f"{prefix} capabilities omit supported IDs {missing_capabilities}"
        )
    for label, phase_state, phase_capabilities in phase_capability_records:
        unavailable = sorted(set(phase_capabilities) - capability_states.keys())
        if unavailable:
            errors.append(
                f"{label}.capabilities is not bound to declared capabilities "
                f"{unavailable}"
            )
            continue
        phase_rank = PROMOTABLE_EVIDENCE_RANK.get(phase_state)
        if phase_rank is None:
            continue
        non_promotable = sorted(
            capability_id
            for capability_id in phase_capabilities
            if capability_states[capability_id] not in PROMOTABLE_EVIDENCE_RANK
        )
        if non_promotable:
            details = [
                f"{capability_id}={capability_states[capability_id]!r}"
                for capability_id in non_promotable
            ]
            errors.append(
                f"{label}.state cannot be promoted from non-promotable capability "
                f"states {details}"
            )
            continue
        floor_state = min(
            (capability_states[capability_id] for capability_id in phase_capabilities),
            key=PROMOTABLE_EVIDENCE_RANK.__getitem__,
        )
        if phase_rank > PROMOTABLE_EVIDENCE_RANK[floor_state]:
            floor_capabilities = sorted(
                capability_id
                for capability_id in phase_capabilities
                if capability_states[capability_id] == floor_state
            )
            errors.append(
                f"{label}.state {phase_state!r} exceeds referenced capability "
                f"evidence floor {floor_state!r} from {floor_capabilities}"
            )

    external_gates = payload.get("external_gates")
    gate_statuses: dict[str, str] = {}
    gate_unblocks: dict[str, str] = {}
    seen_gate_ids: set[str] = set()
    ordered_gate_ids: list[str] = []
    if not isinstance(external_gates, list) or not external_gates:
        errors.append(f"{prefix} external_gates must be a non-empty list")
    else:
        for index, gate in enumerate(external_gates):
            label = f"{prefix} external_gates[{index}]"
            if not isinstance(gate, dict):
                errors.append(f"{label} must be an object")
                continue
            gate_id = gate.get("id")
            status = gate.get("status")
            if isinstance(gate_id, str):
                ordered_gate_ids.append(gate_id)
            if not isinstance(gate_id, str) or not gate_id:
                errors.append(f"{label}.id must be a non-empty string")
            elif gate_id in seen_gate_ids:
                errors.append(f"{label}.id duplicates {gate_id!r}")
            else:
                seen_gate_ids.add(gate_id)
                if gate_id not in EXPECTED_EXTERNAL_GATE_IDS:
                    errors.append(f"{label}.id is unknown: {gate_id!r}")
                if isinstance(status, str):
                    gate_statuses[gate_id] = status
            if status not in EXTERNAL_GATE_STATES:
                errors.append(f"{label}.status must be passed, failed, or parked")
            if status == "parked":
                if set(gate) != {"id", "status", "unblock"}:
                    errors.append(
                        f"{label} parked gate must contain exactly id, status, and unblock"
                    )
                unblock = gate.get("unblock")
                if not isinstance(unblock, str) or not unblock.strip():
                    errors.append(f"{label}.unblock is required for a parked gate")
                elif isinstance(gate_id, str):
                    gate_unblocks[gate_id] = unblock
            elif set(gate) != {"id", "status"}:
                errors.append(
                    f"{label} non-parked gate must contain exactly id and status"
                )
    missing_gates = sorted(set(EXPECTED_EXTERNAL_GATE_IDS) - seen_gate_ids)
    if missing_gates:
        errors.append(f"{prefix} external_gates omit IDs {missing_gates}")
    if set(ordered_gate_ids) == set(
        EXPECTED_EXTERNAL_GATE_IDS
    ) and ordered_gate_ids != list(EXPECTED_EXTERNAL_GATE_IDS):
        errors.append(f"{prefix} external_gates must be ordered EG-01 through EG-06")

    criteria = payload.get("criteria")
    seen_criterion_ids: set[str] = set()
    ordered_criterion_ids: list[str] = []
    criterion_statuses: dict[str, str] = {}
    receipt_cache: dict[str, list[str]] = {}
    if not isinstance(criteria, list) or not criteria:
        errors.append(f"{prefix} criteria must be a non-empty list")
    else:
        for index, criterion in enumerate(criteria):
            label = f"{prefix} criteria[{index}]"
            if not isinstance(criterion, dict):
                errors.append(f"{label} must be an object")
                continue
            if set(criterion) != {"capabilities", "evidence", "id", "state"}:
                errors.append(
                    f"{label} must contain exactly capabilities, evidence, id, and state"
                )
            criterion_id = criterion.get("id")
            state = criterion.get("state")
            if isinstance(criterion_id, str):
                ordered_criterion_ids.append(criterion_id)
            if not isinstance(criterion_id, str) or not criterion_id:
                errors.append(f"{label}.id must be a non-empty string")
            elif criterion_id in seen_criterion_ids:
                errors.append(f"{label}.id duplicates {criterion_id!r}")
            else:
                seen_criterion_ids.add(criterion_id)
                if criterion_id not in EXPECTED_CRITERION_IDS:
                    errors.append(f"{label}.id is unknown: {criterion_id!r}")
                if isinstance(state, str):
                    criterion_statuses[criterion_id] = state
            if state not in CRITERION_STATES:
                errors.append(f"{label}.state must be passed, pending, or parked")

            criterion_capabilities = criterion.get("capabilities")
            if (
                not isinstance(criterion_capabilities, list)
                or not criterion_capabilities
                or not all(
                    isinstance(item, str) and item for item in criterion_capabilities
                )
            ):
                errors.append(f"{label}.capabilities must be a non-empty string list")
            else:
                if len(set(criterion_capabilities)) != len(criterion_capabilities):
                    errors.append(f"{label}.capabilities contains duplicates")
                unsupported = sorted(
                    set(criterion_capabilities) - EXPECTED_CAPABILITY_IDS
                )
                unavailable = sorted(set(criterion_capabilities) - seen_capability_ids)
                if unsupported:
                    errors.append(
                        f"{label}.capabilities contains unsupported IDs {unsupported}"
                    )
                if unavailable:
                    errors.append(
                        f"{label}.capabilities is not bound to declared capabilities {unavailable}"
                    )

            evidence = criterion.get("evidence")
            gate_bindings: list[str] = []
            seen_bindings: set[str] = set()
            if not isinstance(evidence, list) or not evidence:
                errors.append(f"{label}.evidence must be a non-empty list")
            else:
                for evidence_index, binding in enumerate(evidence):
                    binding_label = f"{label}.evidence[{evidence_index}]"
                    if not isinstance(binding, dict):
                        errors.append(f"{binding_label} must be an object")
                        continue
                    kind = binding.get("kind")
                    if kind == "path":
                        if set(binding) != {"kind", "path", "sha256"}:
                            errors.append(
                                f"{binding_label} path binding must contain exactly kind, path, and sha256"
                            )
                            continue
                        relative = binding.get("path")
                        if isinstance(relative, str) and PurePosixPath(
                            relative
                        ) == PurePosixPath("STATUS.json"):
                            errors.append(
                                f"{binding_label} cannot self-bind the status ledger"
                            )
                            continue
                        errors.extend(
                            _bound_regular_file(
                                root,
                                relative,
                                binding.get("sha256"),
                                label=binding_label,
                            )
                        )
                        binding_key = f"path:{relative}"
                    elif kind == "receipt":
                        if set(binding) != {"kind", "path"}:
                            errors.append(
                                f"{binding_label} receipt binding must contain exactly kind and path"
                            )
                            continue
                        relative = binding.get("path")
                        if not isinstance(relative, str):
                            errors.append(f"{binding_label}.path must be a string")
                            continue
                        if relative not in receipt_cache:
                            receipt_cache[relative] = _criterion_receipt_errors(
                                root, relative, payload
                            )
                        receipt_errors = receipt_cache[relative]
                        errors.extend(
                            f"{binding_label}: stale or invalid receipt: {error}"
                            for error in receipt_errors
                        )
                        binding_key = f"receipt:{relative}"
                    elif kind == "gate":
                        if set(binding) != {"id", "kind"}:
                            errors.append(
                                f"{binding_label} gate binding must contain exactly id and kind"
                            )
                            continue
                        gate_id = binding.get("id")
                        if not isinstance(gate_id, str) or gate_id not in gate_statuses:
                            errors.append(
                                f"{binding_label} is not bound to a declared external gate"
                            )
                            continue
                        gate_bindings.append(gate_id)
                        binding_key = f"gate:{gate_id}"
                    else:
                        errors.append(
                            f"{binding_label}.kind must be gate, receipt, or path"
                        )
                        continue
                    if binding_key in seen_bindings:
                        errors.append(f"{binding_label} duplicates {binding_key!r}")
                    seen_bindings.add(binding_key)

            if state == "parked":
                if not gate_bindings:
                    errors.append(
                        f"{label} parked criterion is not bound to an external gate"
                    )
                for gate_id in gate_bindings:
                    if gate_statuses.get(gate_id) != "parked" or not gate_unblocks.get(
                        gate_id
                    ):
                        errors.append(
                            f"{label} parked criterion requires a parked gate with an exact unblock: {gate_id}"
                        )
            elif gate_bindings:
                errors.append(
                    f"{label} only a parked criterion may bind an external gate"
                )

    expected_criterion_set = set(EXPECTED_CRITERION_IDS)
    missing_criteria = sorted(expected_criterion_set - seen_criterion_ids)
    unknown_criteria = sorted(seen_criterion_ids - expected_criterion_set)
    if missing_criteria:
        errors.append(f"{prefix} criteria omit IDs {missing_criteria}")
    if unknown_criteria:
        errors.append(f"{prefix} criteria contain unknown IDs {unknown_criteria}")
    if seen_criterion_ids == expected_criterion_set and ordered_criterion_ids != list(
        EXPECTED_CRITERION_IDS
    ):
        errors.append(f"{prefix} criteria must be ordered AC-00 through AC-25")

    pending_criteria = sorted(
        criterion_id
        for criterion_id, state in criterion_statuses.items()
        if state == "pending"
    )
    if release_label in {"engineering-candidate", "scientifically-supported"} and (
        pending_criteria or seen_criterion_ids != expected_criterion_set
    ):
        errors.append(
            f"{prefix} {release_label} requires every AC-00 through AC-25 "
            f"to be passed or externally parked; pending={pending_criteria}"
        )

    scientific_gate_ids = ("EG-04", "EG-05", "EG-06")
    scientific_gates_passed = all(
        gate_statuses.get(gate_id) == "passed" for gate_id in scientific_gate_ids
    )
    north_star_capability_supported = (
        any(
            isinstance(capability, dict)
            and capability.get("id") == "north-star-outcome"
            and capability.get("state") == "scientifically-supported"
            for capability in capabilities
        )
        if isinstance(capabilities, list)
        else False
    )
    if scientific_support and not scientific_gates_passed:
        errors.append(
            f"{prefix} north_star.scientifically_supported requires EG-04, EG-05, and EG-06 to pass"
        )
    if scientific_support and not north_star_capability_supported:
        errors.append(
            f"{prefix} scientific North Star requires north-star-outcome capability support"
        )
    if release_label == "scientifically-supported" and (
        not scientific_gates_passed or not north_star_capability_supported
    ):
        errors.append(
            f"{prefix} scientific release requires passed human, delayed-transfer, and generalization gates"
        )

    return errors


def _string_leaves(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _string_leaves(child)
    elif isinstance(value, list):
        for child in value:
            yield from _string_leaves(child)


def _status_claims(status_payload: Any) -> tuple[bool, bool]:
    """Identify explicit positive browser and field-accessibility claims.

    The status ledger is intentionally free-form inside evidence and claim-limit
    strings, so the validator recognizes a small, conservative vocabulary of
    positive release claims. Statements that say evidence is unverified or a
    future gate is parked do not match these patterns.
    """

    text = "\n".join(_string_leaves(status_payload)).lower()
    manual_browser_patterns = (
        r"\bbrowser[- ]inspected\b",
        (
            r"\b(?:real[- ]browser|browser) inspection "
            r"(?:(?:is|was|has been) )?"
            r"(?:passed|complete(?:d)?|verified|validated)\b"
        ),
        r"\bmanually inspected in (?:a )?real browser\b",
        r"\b(?:tested|checked|verified|validated) in (?:a )?real browser\b",
        r"\breal[- ]browser checks? (?:passed|complete(?:d)?)\b",
    )
    field_accessibility_patterns = (
        r"\baccessible deterministic renderer\b",
        r"\bfield[- ]accessible\b",
        (
            r"\b(?:representative )?field accessibility "
            r"(?:(?:is|was|has been) )?"
            r"(?:passed|complete(?:d)?|verified|validated|supported)\b"
        ),
        (
            r"\brepresentative accessibility (?:evidence )?"
            r"(?:passed|complete(?:d)?|verified|validated|supported)\b"
        ),
        (
            r"\bassistive[- ]technology (?:testing )?"
            r"(?:passed|complete(?:d)?|verified|validated)\b"
        ),
        r"\bwcag(?: 2\.2)?(?: aa)? (?:compliant|conformant|certified)\b",
        r"\b(?:meets|conforms to) wcag(?: 2\.2)?(?: aa)?\b",
    )
    capabilities = (
        status_payload.get("capabilities", [])
        if isinstance(status_payload, dict)
        else []
    )
    structured_manual_claim = any(
        isinstance(capability, dict)
        and capability.get("id") == "markdown-html-artifacts"
        and capability.get("state")
        in {"manually-inspected", "scientifically-supported"}
        for capability in capabilities
    )
    return (
        structured_manual_claim
        or any(re.search(pattern, text) for pattern in manual_browser_patterns),
        any(re.search(pattern, text) for pattern in field_accessibility_patterns),
    )


def _status_gate(status_payload: Any, gate_id: str) -> str | None:
    if not isinstance(status_payload, dict):
        return None
    gates = status_payload.get("external_gates")
    if not isinstance(gates, list):
        return None
    matches = [
        gate.get("status")
        for gate in gates
        if isinstance(gate, dict) and gate.get("id") == gate_id
    ]
    if len(matches) != 1 or not isinstance(matches[0], str):
        return None
    return matches[0]


def validate_browser_inspection_receipt(
    root: Path, status_payload: Any | None = None
) -> tuple[int, list[str]]:
    """Validate browser evidence while keeping field claims behind EG-03.

    A well-formed blocked attempt is valid engineering evidence: it records why
    inspection did not happen without pretending that it did. A passed receipt
    may support only the narrower claim that named pages received manual browser
    inspection. Representative accessibility evidence remains an external gate.
    """

    receipt_path = root / BROWSER_INSPECTION_RECEIPT_RELATIVE
    label = BROWSER_INSPECTION_RECEIPT_RELATIVE
    if receipt_path.is_symlink() or not receipt_path.is_file():
        return 0, [f"{label}: required browser-inspection receipt is missing or unsafe"]
    receipt = _load_json_if_present(receipt_path)
    if not isinstance(receipt, dict):
        return 0, [f"{label}: expected a valid object"]
    errors: list[str] = []
    actual_keys = set(receipt)
    missing_keys = sorted(BROWSER_INSPECTION_KEYS - actual_keys)
    unexpected_keys = sorted(actual_keys - BROWSER_INSPECTION_KEYS)
    if missing_keys:
        errors.append(f"{label}: missing keys {missing_keys}")
    if unexpected_keys:
        errors.append(f"{label}: unexpected keys {unexpected_keys}")

    if receipt.get("schema_version") != 1:
        errors.append(f"{label}: schema_version must be 1")
    attempted_at = receipt.get("attempted_at")
    if isinstance(attempted_at, str):
        try:
            attempted = datetime.fromisoformat(attempted_at.replace("Z", "+00:00"))
        except ValueError:
            attempted = None
    else:
        attempted = None
    if attempted is None or attempted.tzinfo is None:
        errors.append(f"{label}: attempted_at must be an ISO-8601 timestamp")
    for field in ("surface", "reason", "claim_boundary"):
        value = receipt.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{label}: {field} must be a non-empty string")

    receipt_status = receipt.get("status")
    if receipt_status not in {"blocked", "passed"}:
        errors.append(f"{label}: status must be blocked or passed")
    observed_pages = receipt.get("observed_runtime_pages")
    if (
        not isinstance(observed_pages, int)
        or isinstance(observed_pages, bool)
        or observed_pages < 0
    ):
        errors.append(f"{label}: observed_runtime_pages must be a non-negative integer")
    for field in (*BROWSER_CHECK_FIELDS, "supports_field_accessibility_claim"):
        if type(receipt.get(field)) is not bool:
            errors.append(f"{label}: {field} must be boolean")
    if receipt.get("supports_field_accessibility_claim") is not False:
        errors.append(f"{label}: supports_field_accessibility_claim must be false")

    planned_pages = receipt.get("planned_pages")
    if not isinstance(planned_pages, list) or not planned_pages:
        errors.append(f"{label}: planned_pages must be a non-empty array")
    else:
        seen_paths: set[str] = set()
        root_resolved = root.resolve()
        for index, planned in enumerate(planned_pages):
            page_label = f"{label}: planned_pages[{index}]"
            if not isinstance(planned, dict):
                errors.append(f"{page_label} must be an object")
                continue
            if set(planned) != {"path", "sha256"}:
                errors.append(f"{page_label} must contain exactly path and sha256")
            relative = planned.get("path")
            digest = planned.get("sha256")
            if (
                not isinstance(relative, str)
                or not relative
                or PurePosixPath(relative).is_absolute()
                or ".." in PurePosixPath(relative).parts
                or PurePosixPath(relative).suffix.lower() != ".html"
            ):
                errors.append(f"{page_label}: unsafe planned page path {relative!r}")
                continue
            if relative in seen_paths:
                errors.append(f"{page_label}: duplicate planned page path {relative!r}")
            seen_paths.add(relative)
            if (
                not isinstance(digest, str)
                or re.fullmatch(r"[0-9a-f]{64}", digest) is None
            ):
                errors.append(f"{page_label}: invalid SHA-256")
                continue
            page = root / Path(*PurePosixPath(relative).parts)
            try:
                resolved = page.resolve(strict=True)
            except (OSError, RuntimeError):
                errors.append(f"{page_label}: planned page is missing")
                continue
            if (
                not resolved.is_relative_to(root_resolved)
                or page.is_symlink()
                or not resolved.is_file()
            ):
                errors.append(f"{page_label}: planned page is unsafe")
                continue
            if sha256(resolved) != digest:
                errors.append(f"{page_label}: planned page digest mismatch")

    check_values = [receipt.get(field) for field in BROWSER_CHECK_FIELDS]
    if receipt_status == "blocked":
        if observed_pages != 0:
            errors.append(
                f"{label}: blocked receipt requires zero observed runtime pages"
            )
        if any(value is not False for value in check_values):
            errors.append(
                f"{label}: blocked receipt requires all browser checks to be false"
            )
    elif receipt_status == "passed":
        if not isinstance(observed_pages, int) or observed_pages < 1:
            errors.append(
                f"{label}: passed receipt requires at least one observed runtime page"
            )
        for field in BROWSER_CHECK_FIELDS[:3]:
            if receipt.get(field) is not True:
                errors.append(f"{label}: passed receipt requires {field} to be true")

    if status_payload is None:
        status_payload = _load_json_if_present(root / "STATUS.json")
    eg03_status = _status_gate(status_payload, "EG-03")
    if receipt_status == "blocked" and eg03_status != "parked":
        errors.append(
            f"{label}: blocked receipt requires STATUS.json EG-03 to be parked"
        )

    manual_browser_claim, field_accessibility_claim = _status_claims(status_payload)
    receipt_supports_manual_claim = (
        receipt_status == "passed"
        and isinstance(observed_pages, int)
        and not isinstance(observed_pages, bool)
        and observed_pages >= 1
        and all(receipt.get(field) is True for field in BROWSER_CHECK_FIELDS[:3])
        and receipt.get("supports_field_accessibility_claim") is False
        and not errors
    )
    if manual_browser_claim and not receipt_supports_manual_claim:
        errors.append(
            f"{label}: manual browser-inspection claim requires a passed receipt"
        )
    if field_accessibility_claim and eg03_status != "passed":
        errors.append(
            f"{label}: field-accessibility claim requires STATUS.json EG-03 to pass"
        )
    return 1, errors


def validate_release_status(
    json_files: list[Path], root: Path
) -> tuple[int, list[str]]:
    ledgers = [path for path in json_files if path.name == "STATUS.json"]
    errors: list[str] = []
    if (root / "SKILL.md").is_file():
        if len(ledgers) != 1:
            errors.append(
                f"STATUS.json: package requires exactly one release-status ledger; found {len(ledgers)}"
            )
        elif ledgers[0] != root / "STATUS.json":
            errors.append("STATUS.json: release-status ledger must be at package root")
    for path in ledgers:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        errors.extend(release_status_errors(path, payload, root))
    return len(ledgers), errors


def validation_report(root: Path, *, artifact_only: bool) -> dict[str, Any]:
    mode = "artifact-only" if artifact_only else "full"
    security = empty_security_counts()
    counts: dict[str, int] = {
        "browser_inspection_receipts": 0,
        "companion_pages": 0,
        "forward_behavior_receipts": 0,
        "html_pages": 0,
        "independent_review_receipts": 0,
        "integration_manifests": 0,
        "legacy_asset_manifests": 0,
        "json_schemas": 0,
        "schema_instances": 0,
        "state_invariant_sets": 0,
        "json_files": 0,
        "jsonl_files": 0,
        "markdown_files": 0,
        "markdown_html_pairs": 0,
        "negative_fixtures": 0,
        "package_contracts": 0,
        "release_status_ledgers": 0,
        "verification_receipts": 0,
        "visual_verification_receipts": 0,
    }
    errors: list[str] = []
    if not root.is_dir():
        return {
            "counts": counts,
            "errors": [f"not a directory: {root}"],
            "mode": mode,
            "root": str(root),
            "security": security,
            "status": "failed",
        }

    markdown_files = iter_workspace_files(root, {".md"})
    html_files = iter_workspace_files(root, {".html"})
    counts["markdown_files"] = len(markdown_files)
    counts["html_pages"] = len(html_files)
    counts["negative_fixtures"] = sum(
        is_negative_fixture(path, root) for path in markdown_files + html_files
    )

    parsers: dict[Path, PageParser] = {}
    regular_html_files: list[Path] = []
    for path in html_files:
        try:
            page_parser = parse_page(path)
        except (OSError, UnicodeError) as exc:
            page_errors = [f"{path.relative_to(root)}: cannot parse HTML: {exc}"]
            page_parser = PageParser()
        else:
            require_document_shell = (
                path.name == "index.html" or path.with_suffix(".md").exists()
            )
            page_errors = validate_html_document(
                path,
                page_parser,
                root,
                require_document_shell=require_document_shell,
            )
        parsers[path.resolve()] = page_parser

        if is_negative_fixture(path, root):
            if not page_errors:
                errors.append(
                    f"{path.relative_to(root)}: negative fixture unexpectedly passed validation"
                )
            continue
        regular_html_files.append(path)
        errors.extend(page_errors)
        security["dangerous_tags"] += len(page_parser.dangerous_tags)
        security["event_attributes"] += len(page_parser.event_attributes)
        security["unsafe_urls"] += len(page_parser.unsafe_urls)
        security["external_assets"] += len(page_parser.external_assets)
        security["missing_image_alt"] += page_parser.missing_image_alt
        security["duplicate_ids"] += len(page_parser.ids) - len(set(page_parser.ids))

    for path in markdown_files:
        rel = path.relative_to(root)
        html = path.with_suffix(".html")
        pair_errors: list[str] = []
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            pair_errors.append(f"{rel}: cannot read Markdown: {exc}")
            text = ""
        if "[TODO" in text or "TODO:" in text:
            pair_errors.append(f"{rel}: unresolved TODO placeholder")
        if not html.exists():
            pair_errors.append(f"{rel}: missing companion {html.name}")
        else:
            counts["markdown_html_pairs"] += 1
            if html.name != "index.html":
                counts["companion_pages"] += 1
            page_parser = parsers.get(html.resolve())
            if page_parser is not None:
                pair_errors.extend(
                    validate_companion_metadata(path, html, page_parser, root)
                )

        if is_negative_fixture(path, root):
            if not pair_errors:
                errors.append(f"{rel}: negative fixture unexpectedly passed validation")
        else:
            errors.extend(pair_errors)

    errors.extend(validate_local_links(regular_html_files, parsers, root))

    if not artifact_only:
        json_files = iter_workspace_files(root, {".json"})
        jsonl_files = iter_workspace_files(root, {".jsonl"})
        counts["json_files"] = len(json_files)
        counts["jsonl_files"] = len(jsonl_files)
        counts["negative_fixtures"] += sum(
            is_negative_fixture(path, root) for path in json_files + jsonl_files
        )
        errors.extend(validate_json_files(json_files, jsonl_files, root))
        errors.extend(validate_public_evals(json_files, root))
        errors.extend(validate_flint_specs(json_files, root))
        schema_count, schema_errors = validate_json_schemas(json_files, root)
        counts["json_schemas"] = schema_count
        errors.extend(schema_errors)
        instance_count, instance_errors = validate_schema_instances(root)
        counts["schema_instances"] = instance_count
        errors.extend(instance_errors)
        invariant_count, invariant_errors = validate_state_fixture_invariants(root)
        counts["state_invariant_sets"] = invariant_count
        errors.extend(invariant_errors)
        integration_count, integration_errors = validate_integration_manifests(root)
        counts["integration_manifests"] = integration_count
        errors.extend(integration_errors)
        legacy_count, legacy_errors = validate_legacy_asset_provenance(root)
        counts["legacy_asset_manifests"] = legacy_count
        errors.extend(legacy_errors)
        forward_count, forward_errors = validate_forward_behavior_receipt(root)
        counts["forward_behavior_receipts"] = forward_count
        errors.extend(forward_errors)
        review_count, review_errors = validate_independent_review_receipts(root)
        counts["independent_review_receipts"] = review_count
        errors.extend(review_errors)
        verification_count, verification_errors = validate_verification_receipt(root)
        counts["verification_receipts"] = verification_count
        errors.extend(verification_errors)
        package_count, package_errors = validate_package_contract(root)
        counts["package_contracts"] = package_count
        errors.extend(package_errors)
        visual_count, visual_errors = validate_visual_verification_fixture(root)
        counts["visual_verification_receipts"] = visual_count
        errors.extend(visual_errors)
        ledger_count, ledger_errors = validate_release_status(json_files, root)
        counts["release_status_ledgers"] = ledger_count
        errors.extend(ledger_errors)
        if (root / "SKILL.md").is_file():
            status_payload = _load_json_if_present(root / "STATUS.json")
            browser_count, browser_errors = validate_browser_inspection_receipt(
                root, status_payload
            )
            counts["browser_inspection_receipts"] = browser_count
            errors.extend(browser_errors)

    sorted_errors = sorted(set(errors))
    return {
        "counts": counts,
        "errors": sorted_errors,
        "mode": mode,
        "root": str(root),
        "security": security,
        "status": "failed" if sorted_errors else "passed",
    }


def emit_report(report: dict[str, Any], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    errors = report["errors"]
    if errors:
        print(f"FAILED: {len(errors)} problem(s)")
        for error in errors:
            print(f"- {error}")
        return
    counts = report["counts"]
    if report["mode"] == "artifact-only":
        print(
            f"PASS: {counts['markdown_html_pairs']} Markdown/HTML pair(s), "
            f"{counts['html_pages']} HTML page(s), security checks, and local links"
        )
    else:
        print(
            f"PASS: {counts['markdown_html_pairs']} Markdown/HTML pair(s), "
            f"{counts['companion_pages']} companion page(s), JSON/eval/spec checks, "
            "security checks, and local links"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifact-only",
        action="store_true",
        help="validate Markdown/HTML artifacts without package JSON/eval/Flint checks",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="emit one structured JSON receipt on stdout",
    )
    parser.add_argument("workspace", type=Path)
    args = parser.parse_args()
    root = args.workspace.expanduser().resolve()
    try:
        report = validation_report(root, artifact_only=args.artifact_only)
    except Exception as exc:  # noqa: BLE001  # pragma: no cover - receipt boundary
        report = {
            "counts": {
                "companion_pages": 0,
                "forward_behavior_receipts": 0,
                "html_pages": 0,
                "independent_review_receipts": 0,
                "integration_manifests": 0,
                "legacy_asset_manifests": 0,
                "json_schemas": 0,
                "schema_instances": 0,
                "state_invariant_sets": 0,
                "json_files": 0,
                "jsonl_files": 0,
                "markdown_files": 0,
                "markdown_html_pairs": 0,
                "negative_fixtures": 0,
                "package_contracts": 0,
                "release_status_ledgers": 0,
                "verification_receipts": 0,
            },
            "errors": [f"validator internal error: {type(exc).__name__}: {exc}"],
            "mode": "artifact-only" if args.artifact_only else "full",
            "root": str(root),
            "security": empty_security_counts(),
            "status": "failed",
        }
    emit_report(report, json_output=args.json_output)
    if not root.is_dir():
        return 2
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
