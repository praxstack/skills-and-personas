"""Verify visual-delivery bytes without promoting unverified runtimes."""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import stat
import subprocess
import unicodedata
import zlib
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree

from .errors import SafetyError, ValidationError
from .io import (
    PRIVATE_FILE_MODE,
    anchored_file_target,
    atomic_write_anchored,
    canonical_json_bytes,
    prepare_private_parent,
)

ROOT = Path(__file__).resolve().parents[2]
RENDERER = ROOT / "scripts" / "render_markdown.mjs"
VERIFIER_VERSION = "prax-teach-visual-verifier/1.1.0"
ANIMATED_OR_UNVERIFIABLE_IMAGE_SUFFIXES = {
    ".apng",
    ".avif",
    ".gif",
    ".webp",
}
STATIC_RASTER_SUFFIXES = {".jpeg", ".jpg", ".png"}
MAX_STATIC_IMAGE_BYTES = 25 * 1024 * 1024
MAX_STATIC_IMAGE_DIMENSION = 100_000
MAX_STATIC_IMAGE_PIXELS = 100_000_000


class _DeliveryParser(HTMLParser):
    """Collect the structural facts required by the static-delivery contract."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[str] = []
        self.ids: list[str] = []
        self.hrefs: list[str] = []
        self.heading_levels: list[int] = []
        self.image_alts: list[str | None] = []
        self.has_lang = False
        self.has_charset = False
        self.has_viewport = False
        self.has_skip_link = False
        self.has_title = False
        self.semantic_tables: list[dict[str, list[str]]] = []
        self._in_title = False
        self._title_text: list[str] = []
        self._table_stack: list[dict[str, list[str]]] = []
        self._table_cell: tuple[str, list[str]] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        values = {key.lower(): value or "" for key, value in attrs}
        self.tags.append(tag)
        if tag == "html" and values.get("lang", "").strip():
            self.has_lang = True
        if tag == "meta" and values.get("charset", "").strip():
            self.has_charset = True
        if tag == "meta" and values.get("name", "").lower() == "viewport":
            self.has_viewport = bool(values.get("content", "").strip())
        if tag == "title":
            self._in_title = True
        if tag == "a":
            href = values.get("href", "")
            if href:
                self.hrefs.append(href)
            if "skip-link" in values.get("class", "").split() and href.startswith("#"):
                self.has_skip_link = True
        if "id" in values:
            self.ids.append(values["id"])
        if len(tag) == 2 and tag.startswith("h") and tag[1].isdigit():
            self.heading_levels.append(int(tag[1]))
        if tag == "img":
            self.image_alts.append(values.get("alt"))
        if tag == "table":
            self._table_stack.append({"data": [], "headers": []})
        elif tag in {"th", "td"} and self._table_stack:
            self._table_cell = ("headers" if tag == "th" else "data", [])

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
            self.has_title = bool("".join(self._title_text).strip())
        if tag in {"th", "td"} and self._table_cell and self._table_stack:
            kind, chunks = self._table_cell
            self._table_stack[-1][kind].append("".join(chunks))
            self._table_cell = None
        elif tag == "table" and self._table_stack:
            table = self._table_stack.pop()
            self.semantic_tables.append(table)

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_text.append(data)
        if self._table_cell:
            self._table_cell[1].append(data)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_regular(path: str | Path, *, label: str) -> tuple[Path, bytes]:
    candidate = prepare_private_parent(path, create_missing=False)
    try:
        metadata = candidate.lstat()
    except FileNotFoundError as exc:
        raise ValidationError(f"{label} is missing") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise SafetyError(f"{label} must be a regular non-symlink file")
    try:
        descriptor = os.open(
            candidate,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        )
    except OSError as exc:
        raise SafetyError(f"{label} cannot be opened safely") from exc
    try:
        current = os.fstat(descriptor)
        if (current.st_dev, current.st_ino) != (metadata.st_dev, metadata.st_ino):
            raise SafetyError(f"{label} changed while being opened")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            payload = handle.read()
    finally:
        os.close(descriptor)
    return candidate, payload


def _receipt_path(path: Path) -> str:
    """Return a relocation-stable path for package-owned evidence."""

    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _json_document(payload: bytes, *, label: str) -> dict[str, Any]:
    try:
        document = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"{label} must be valid UTF-8 JSON") from exc
    if not isinstance(document, dict):
        raise ValidationError(f"{label} must contain an object")
    return document


def _normalized(value: str) -> str:
    decoded = html.unescape(unquote(value))
    compatible = unicodedata.normalize("NFKC", decoded).casefold()
    return "".join(character for character in compatible if character.isalnum())


def _forbidden_terms(document: dict[str, Any], *, retrieval: bool) -> list[str]:
    if set(document) != {"forbidden_answer_terms", "retrieval", "schema_version"}:
        raise ValidationError("forbidden-answer rubric has unsupported or missing keys")
    if (
        document.get("schema_version") != 1
        or type(document.get("retrieval")) is not bool
    ):
        raise ValidationError("forbidden-answer rubric contract is invalid")
    if document["retrieval"] is not retrieval:
        raise ValidationError("route and forbidden-answer rubric disagree on retrieval")
    terms = document.get("forbidden_answer_terms")
    if not isinstance(terms, list) or any(
        not isinstance(term, str) or not term.strip() for term in terms
    ):
        raise ValidationError("forbidden_answer_terms must be a string array")
    normalized = [_normalized(term) for term in terms]
    if len(normalized) != len(set(normalized)) or any(
        len(term) < 3 for term in normalized
    ):
        raise ValidationError("forbidden answer terms must be unique and substantive")
    if retrieval and not normalized:
        raise ValidationError("retrieval verification requires forbidden answer terms")
    return normalized


def _route_contract(document: dict[str, Any]) -> tuple[str, str, bool, bool]:
    route = document.get("route")
    delivery = document.get("delivery_route")
    if route not in {"none", "static", "interactive", "motion"}:
        raise ValidationError("route output has an invalid requested route")
    runtime = document.get("visual_runtime")
    runtime_direct = route in {"interactive", "motion"} and (
        document.get("visual_runtime_supported") is True
        and isinstance(runtime, dict)
        and runtime.get("id") == "prax-visual-lab"
        and isinstance(runtime.get("version"), str)
        and runtime.get("entrypoint") == "runtime/prax-visual-lab/dist/index.html"
        and runtime.get("manifest") == "runtime/prax-visual-lab/dist/manifest.json"
        and runtime.get("verification_receipt")
        == "evidence/zero-api-visual-runtime/verification.json"
        and document.get("runtime_requirement") is None
    )
    expected_delivery = (
        route if route in {"none", "static"} or runtime_direct else "static"
    )
    if delivery != expected_delivery:
        raise ValidationError(
            "route output does not fail closed to its supported delivery"
        )
    retrieval = document.get("retrieval_safety")
    if not isinstance(retrieval, dict) or type(retrieval.get("required")) is not bool:
        raise ValidationError("route output lacks retrieval-safety metadata")
    retrieval_required = retrieval["required"]
    expected_status = "not_run" if retrieval_required else "not_applicable"
    if (
        retrieval.get("verification_status") != expected_status
        or retrieval.get("checks_performed") is not False
    ):
        raise ValidationError("route output has pre-claimed retrieval verification")
    expected_checks = (
        {"attempt_before_reveal", "accessible_reveal", "fallback_preserves_order"}
        if retrieval_required
        else set()
    )
    declared_checks = retrieval.get("required_checks")
    if (
        not isinstance(declared_checks, list)
        or any(not isinstance(value, str) for value in declared_checks)
        or set(declared_checks) != expected_checks
    ):
        raise ValidationError("route output has an invalid retrieval-check contract")
    required_surfaces = {
        "visible_labels",
        "alt_text",
        "captions",
        "default_state",
        "poster_frame",
        "source_code",
    }
    declared_surfaces = retrieval.get("surfaces_to_check")
    if (
        not isinstance(declared_surfaces, list)
        or any(not isinstance(value, str) for value in declared_surfaces)
        or set(declared_surfaces) != required_surfaces
    ):
        raise ValidationError("route output has an invalid retrieval surface contract")
    if route in {"interactive", "motion"}:
        fallback_only = (
            not runtime_direct
            and document.get("bundled_renderer_supported") is False
            and document.get("runtime_requirement")
            == "separately-versioned-tested-and-manually-reviewed"
        )
        if document.get("bundled_renderer_supported") is not False or not (
            runtime_direct or fallback_only
        ):
            raise ValidationError(
                "unverified visual runtime was promoted as verified delivery"
            )
    if (
        route in {"none", "static"}
        and document.get("bundled_renderer_supported") is not True
    ):
        raise ValidationError("bundled static route support is inconsistent")
    return route, delivery, retrieval_required, runtime_direct


def _verify_packaged_visual_runtime() -> None:
    completed = subprocess.run(
        [str(ROOT / "scripts/verify_visual_runtime.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ValidationError(
            "packaged visual runtime verifier emitted invalid JSON"
        ) from exc
    if completed.returncode != 0 or result.get("status") != "passed":
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise ValidationError(f"packaged visual runtime verification failed: {detail}")


def _asset_references(markdown: str, generated_html: str) -> list[str]:
    references = [
        match.group(1).strip().strip("<>")
        for match in re.finditer(r"!\[[^\]]*\]\(([^)\s]+)", markdown)
    ]
    references.extend(
        match.group(1) or match.group(2) or match.group(3)
        for match in re.finditer(
            r"\bsrc\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s\"'=<>`]+))",
            generated_html,
            re.IGNORECASE,
        )
    )
    return sorted(set(references))


def _substantive_text(value: str) -> bool:
    return any(character.isalnum() for character in html.unescape(value))


def _bounded_image_dimensions(width: int, height: int) -> str | None:
    if width <= 0 or height <= 0:
        return "image dimensions must be positive"
    if width > MAX_STATIC_IMAGE_DIMENSION or height > MAX_STATIC_IMAGE_DIMENSION:
        return "image dimensions exceed the static verification limit"
    if width * height > MAX_STATIC_IMAGE_PIXELS:
        return "image pixel count exceeds the static verification limit"
    return None


def _validate_static_png(payload: bytes) -> str | None:
    signature = b"\x89PNG\r\n\x1a\n"
    if not payload.startswith(signature):
        return "PNG signature is invalid"
    if len(payload) > MAX_STATIC_IMAGE_BYTES:
        return "PNG exceeds the static verification size limit"
    offset = len(signature)
    saw_header = False
    saw_data = False
    saw_end = False
    bit_depth = 0
    color_type = -1
    interlace = -1
    width = 0
    height = 0
    compressed = bytearray()
    while offset < len(payload):
        if offset + 12 > len(payload):
            return "PNG chunk framing is truncated"
        length = int.from_bytes(payload[offset : offset + 4], "big")
        chunk_type = payload[offset + 4 : offset + 8]
        chunk_end = offset + 12 + length
        if chunk_end > len(payload):
            return "PNG chunk exceeds the file boundary"
        chunk_data = payload[offset + 8 : offset + 8 + length]
        expected_crc = int.from_bytes(payload[offset + 8 + length : chunk_end], "big")
        actual_crc = zlib.crc32(chunk_type)
        actual_crc = zlib.crc32(chunk_data, actual_crc) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            return "PNG chunk checksum is invalid"
        if not saw_header and chunk_type != b"IHDR":
            return "PNG does not begin with IHDR"
        if chunk_type == b"IHDR":
            if saw_header or length != 13:
                return "PNG IHDR is invalid"
            saw_header = True
            width = int.from_bytes(chunk_data[0:4], "big")
            height = int.from_bytes(chunk_data[4:8], "big")
            dimension_error = _bounded_image_dimensions(width, height)
            if dimension_error:
                return f"PNG {dimension_error}"
            bit_depth = chunk_data[8]
            color_type = chunk_data[9]
            interlace = chunk_data[12]
            allowed_depths = {
                0: {1, 2, 4, 8, 16},
                2: {8, 16},
                3: {1, 2, 4, 8},
                4: {8, 16},
                6: {8, 16},
            }
            if (
                bit_depth not in allowed_depths.get(color_type, set())
                or chunk_data[10] != 0
                or chunk_data[11] != 0
                or interlace not in {0, 1}
            ):
                return "PNG IHDR uses unsupported encoding parameters"
        elif chunk_type == b"acTL":
            return "animated PNG is not a static fallback"
        elif chunk_type == b"IDAT":
            saw_data = True
            compressed.extend(chunk_data)
        elif chunk_type == b"IEND":
            if length != 0:
                return "PNG IEND is invalid"
            saw_end = True
            if chunk_end != len(payload):
                return "PNG contains bytes after IEND"
            break
        offset = chunk_end
    if not (saw_header and saw_data and saw_end):
        return "PNG lacks required IHDR, IDAT, or IEND chunks"
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color_type]
    row_bytes = (width * channels * bit_depth + 7) // 8
    maximum_decoded = (row_bytes + 8) * height + 64
    inflater = zlib.decompressobj()
    try:
        decoded = inflater.decompress(bytes(compressed), maximum_decoded + 1)
        remaining = maximum_decoded + 1 - len(decoded)
        if remaining <= 0:
            return "PNG image data exceeds its declared dimensions"
        decoded += inflater.flush(remaining)
    except zlib.error:
        return "PNG image data is not a valid zlib stream"
    if len(decoded) > maximum_decoded or not inflater.eof or inflater.unused_data:
        return "PNG image data exceeds or violates its declared dimensions"
    if interlace == 0 and len(decoded) != (row_bytes + 1) * height:
        return "PNG scanline data does not match its declared dimensions"
    return None


def _validate_static_jpeg(payload: bytes) -> str | None:
    if len(payload) > MAX_STATIC_IMAGE_BYTES:
        return "JPEG exceeds the static verification size limit"
    if len(payload) < 4 or payload[:2] != b"\xff\xd8" or payload[-2:] != b"\xff\xd9":
        return "JPEG start or end marker is invalid"
    offset = 2
    saw_frame = False
    saw_scan = False
    frame_markers = {
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC5,
        0xC6,
        0xC7,
        0xC9,
        0xCA,
        0xCB,
        0xCD,
        0xCE,
        0xCF,
    }
    while offset < len(payload) - 2:
        if payload[offset] != 0xFF:
            return "JPEG marker framing is invalid"
        while offset < len(payload) and payload[offset] == 0xFF:
            offset += 1
        if offset >= len(payload):
            return "JPEG marker is truncated"
        marker = payload[offset]
        offset += 1
        if marker == 0xDA:
            saw_scan = True
            break
        if marker in {0x01, *range(0xD0, 0xDA)}:
            continue
        if offset + 2 > len(payload):
            return "JPEG segment length is truncated"
        length = int.from_bytes(payload[offset : offset + 2], "big")
        if length < 2 or offset + length > len(payload):
            return "JPEG segment exceeds the file boundary"
        if marker in frame_markers:
            if length < 8:
                return "JPEG frame header is invalid"
            height = int.from_bytes(payload[offset + 3 : offset + 5], "big")
            width = int.from_bytes(payload[offset + 5 : offset + 7], "big")
            dimension_error = _bounded_image_dimensions(width, height)
            if dimension_error:
                return f"JPEG {dimension_error}"
            saw_frame = True
        offset += length
    if not saw_frame or not saw_scan:
        return "JPEG lacks a valid frame or scan"
    return None


def _local_xml_name(value: str) -> str:
    return value.rsplit("}", 1)[-1].lower()


def _svg_has_dimensions(root: ElementTree.Element) -> bool:
    view_box = root.attrib.get("viewBox") or root.attrib.get("viewbox")
    if view_box:
        try:
            values = [float(value) for value in re.split(r"[\s,]+", view_box.strip())]
        except ValueError:
            return False
        if len(values) == 4 and values[2] > 0 and values[3] > 0:
            return True

    def positive_length(name: str) -> bool:
        value = root.attrib.get(name, "").strip()
        match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)(?:px|pt|pc|cm|mm|in)?", value)
        return bool(match and float(match.group(1)) > 0)

    return positive_length("width") and positive_length("height")


def _validate_static_svg(payload: bytes) -> tuple[str | None, str | None]:
    if len(payload) > MAX_STATIC_IMAGE_BYTES:
        return None, "SVG exceeds the static verification size limit"
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        return None, "SVG is not well-formed UTF-8 XML"
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        return text, "SVG is not well-formed UTF-8 XML"
    if _local_xml_name(root.tag) != "svg":
        return text, "SVG document root is not <svg>"
    if not _svg_has_dimensions(root):
        return text, "SVG lacks a positive width/height or viewBox"
    renderable_tags = {
        "circle",
        "ellipse",
        "image",
        "line",
        "path",
        "polygon",
        "polyline",
        "rect",
        "text",
        "use",
    }
    found_renderable = False
    forbidden_tags = {
        "animate",
        "animatemotion",
        "animatetransform",
        "foreignobject",
        "script",
        "set",
    }
    for element in root.iter():
        tag = _local_xml_name(element.tag)
        if tag in forbidden_tags:
            return text, "SVG is executable or animated"
        if tag in renderable_tags:
            found_renderable = True
        for raw_name, raw_value in element.attrib.items():
            name = _local_xml_name(raw_name)
            if (
                name.startswith("on")
                or name == "style"
                and re.search(r"@keyframes\b|\banimation\s*:", raw_value, re.IGNORECASE)
            ):
                return text, "SVG is executable or animated"
            if name == "href":
                parsed = urlparse(html.unescape(raw_value))
                if parsed.scheme or parsed.netloc or raw_value.startswith("//"):
                    return text, "SVG contains an external or data reference"
    if not found_renderable:
        return text, "SVG contains no renderable visual element"
    return text, None


def _has_substantive_semantic_table(parser: _DeliveryParser) -> bool:
    return any(
        any(_substantive_text(value) for value in table["headers"])
        and any(_substantive_text(value) for value in table["data"])
        for table in parser.semantic_tables
    )


def _inspect_assets(
    references: list[str], source: Path, forbidden: list[str]
) -> tuple[list[dict[str, str]], set[str], list[str]]:
    assets: list[dict[str, str]] = []
    renderable: set[str] = set()
    errors: list[str] = []
    for reference in references:
        parsed = urlparse(html.unescape(reference))
        if parsed.scheme or parsed.netloc:
            errors.append(f"remote or data visual asset is unverified: {reference}")
            continue
        local_text = unquote(parsed.path)
        relative = Path(local_text)
        if relative.is_absolute() or ".." in relative.parts:
            errors.append(f"visual asset escapes the source directory: {reference}")
            continue
        local = source.parent / relative
        try:
            local.relative_to(source.parent)
        except ValueError:
            errors.append(f"visual asset escapes the source directory: {reference}")
            continue
        suffix = local.suffix.lower()
        if suffix in ANIMATED_OR_UNVERIFIABLE_IMAGE_SUFFIXES:
            errors.append(f"opaque or animated visual asset is unverified: {reference}")
            continue
        if suffix not in STATIC_RASTER_SUFFIXES | {".svg"}:
            errors.append(f"unsupported visual asset type: {reference}")
            continue
        try:
            asset, payload = _read_regular(local, label=f"visual asset {reference}")
        except (SafetyError, ValidationError) as exc:
            errors.append(str(exc))
            continue
        text: str | None = None
        if suffix == ".png":
            validation_error = _validate_static_png(payload)
        elif suffix in {".jpeg", ".jpg"}:
            validation_error = _validate_static_jpeg(payload)
        else:
            text, validation_error = _validate_static_svg(payload)
        if text is not None:
            normalized_asset = _normalized(text)
            if any(term in normalized_asset for term in forbidden):
                errors.append(f"forbidden answer appears in visual asset: {reference}")
        if validation_error:
            errors.append(f"{validation_error}: {reference}")
            continue
        assets.append({"path": _receipt_path(asset), "sha256": _sha256(payload)})
        renderable.add(reference)
    return assets, renderable, errors


def _local_link_errors(
    parser: _DeliveryParser, generated_html: Path, source_root: Path
) -> list[str]:
    errors: list[str] = []
    known_ids = set(parser.ids)
    for href in parser.hrefs:
        parsed = urlparse(html.unescape(href))
        if parsed.scheme or parsed.netloc:
            continue
        if not parsed.path:
            if parsed.fragment and unquote(parsed.fragment) not in known_ids:
                errors.append(f"missing local anchor: {href}")
            continue
        relative = Path(unquote(parsed.path))
        if relative.is_absolute() or ".." in relative.parts:
            errors.append(f"local link escapes the delivery directory: {href}")
            continue
        target = generated_html.parent / relative
        try:
            target.relative_to(source_root)
            opened, _payload = _read_regular(target, label=f"local link {href}")
        except (ValueError, SafetyError, ValidationError) as exc:
            errors.append(str(exc))
            continue
        if parsed.fragment and opened.suffix.lower() == ".html":
            try:
                linked_parser = _DeliveryParser()
                linked_parser.feed(_payload.decode("utf-8"))
                linked_parser.close()
            except (UnicodeDecodeError, ValueError) as exc:
                errors.append(f"local HTML link cannot be inspected: {href}: {exc}")
                continue
            if unquote(parsed.fragment) not in set(linked_parser.ids):
                errors.append(f"missing local anchor: {href}")
    return errors


def _structure_errors(
    generated_html: str, generated_html_path: Path, source: Path, route: str
) -> list[str]:
    parser = _DeliveryParser()
    try:
        parser.feed(generated_html)
        parser.close()
    except ValueError as exc:
        return [f"generated HTML is structurally malformed: {exc}"]

    errors: list[str] = []
    for landmark in ("header", "main", "footer"):
        if landmark not in parser.tags:
            errors.append(f"generated HTML lacks the {landmark} landmark")
    for label, present in (
        ("document language", parser.has_lang),
        ("character encoding", parser.has_charset),
        ("viewport metadata", parser.has_viewport),
        ("non-empty title", parser.has_title),
        ("skip link", parser.has_skip_link),
    ):
        if not present:
            errors.append(f"generated HTML lacks {label}")
    if len(parser.ids) != len(set(parser.ids)):
        errors.append("generated HTML contains duplicate IDs")
    if parser.heading_levels.count(1) != 1:
        errors.append(
            "generated HTML must contain exactly one h1, found "
            f"{parser.heading_levels.count(1)}"
        )
    previous = 0
    for level in parser.heading_levels:
        if previous and level > previous + 1:
            errors.append(f"heading level jumps from h{previous} to h{level}")
        previous = level
    if any(alt is None for alt in parser.image_alts):
        errors.append("generated HTML contains an image without alt text")
    if (
        route != "none"
        and "img" in parser.tags
        and not any(isinstance(alt, str) and alt.strip() for alt in parser.image_alts)
    ):
        errors.append("visual fallback image lacks meaningful alternative text")
    if (
        route != "none"
        and "table" in parser.tags
        and not ("th" in parser.tags and "td" in parser.tags)
    ):
        errors.append("semantic table fallback lacks headers or data cells")
    if (
        route != "none"
        and "svg" in parser.tags
        and not ("title" in parser.tags or "desc" in parser.tags)
    ):
        errors.append("inline SVG fallback lacks a title or description")
    errors.extend(_local_link_errors(parser, generated_html_path, source.parent))
    return errors


def _artifact_errors(
    route: str,
    markdown: str,
    generated_html: str,
    generated_html_path: Path,
    forbidden: list[str],
    source: Path,
    retrieval: bool,
) -> tuple[list[dict[str, str]], bool, list[str]]:
    errors: list[str] = []
    for label, text in (
        ("canonical Markdown", markdown),
        ("generated HTML", generated_html),
    ):
        normalized_text = _normalized(text)
        if any(term in normalized_text for term in forbidden):
            errors.append(f"forbidden answer appears in {label}")
    if re.search(
        r"<\s*(?:script|form|button|input|select|textarea)\b"
        r"|\son[a-z]+\s*=|\b(?:src|poster)\s*=\s*[\"']?\s*(?:https?:)?//",
        generated_html,
        re.IGNORECASE,
    ):
        errors.append(
            "static delivery contains a script, form control, handler, or remote asset"
        )
    visual_markup = bool(
        re.search(r"<\s*(?:figure|img|svg|table)\b", generated_html, re.IGNORECASE)
    )
    if route == "none" and visual_markup:
        errors.append("route none contains a visual artifact")
    if (
        retrieval
        and re.search(
            r"(?im)^#{2,6}\s+(?:(?:your|learner)\s+)?"
            r"(?:attempt|prediction|retrieval|answer|practice)\b",
            markdown,
        )
        is None
    ):
        errors.append("retrieval delivery lacks a visible attempt-before-reveal prompt")
    if "<table" in generated_html.lower() and not (
        "<th" in generated_html.lower() and "<td" in generated_html.lower()
    ):
        errors.append("semantic table fallback lacks headers or data cells")
    errors.extend(_structure_errors(generated_html, generated_html_path, source, route))
    references = _asset_references(markdown, generated_html)
    assets, renderable_assets, asset_errors = _inspect_assets(
        references, source, forbidden
    )
    errors.extend(asset_errors)
    parser = _DeliveryParser()
    try:
        parser.feed(generated_html)
        parser.close()
    except ValueError:
        substantive_table = False
    else:
        substantive_table = _has_substantive_semantic_table(parser)
    static_fallback_verified = route != "none" and bool(
        renderable_assets or substantive_table
    )
    if route != "none" and not static_fallback_verified:
        errors.append(
            "visual route lacks a validated renderable image or substantive semantic table static fallback"
        )
    return assets, static_fallback_verified, errors


def verify_visual_delivery(
    *,
    route_output: str,
    source: str,
    generated_html: str,
    forbidden_answer_file: str,
    receipt: str | None,
    check: bool,
) -> dict[str, Any]:
    route_path, route_bytes = _read_regular(route_output, label="route output")
    source_path, source_bytes = _read_regular(source, label="canonical Markdown")
    html_path, html_bytes = _read_regular(generated_html, label="generated HTML")
    rubric_path, rubric_bytes = _read_regular(
        forbidden_answer_file, label="forbidden-answer rubric"
    )
    route_document = _json_document(route_bytes, label="route output")
    route, delivery, retrieval, runtime_direct = _route_contract(route_document)
    if runtime_direct:
        _verify_packaged_visual_runtime()
    rubric_document = _json_document(rubric_bytes, label="forbidden-answer rubric")
    forbidden = _forbidden_terms(rubric_document, retrieval=retrieval)
    try:
        markdown_text = source_bytes.decode("utf-8")
        html_text = html_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError("visual delivery files must be UTF-8") from exc

    renderer = subprocess.run(
        [
            "node",
            str(RENDERER),
            "--check",
            "--trusted-root",
            str(source_path.parent),
            str(source_path),
            str(html_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={
            **os.environ,
            "SOURCE_DATE_EPOCH": os.environ.get("SOURCE_DATE_EPOCH", "1785844800"),
        },
    )
    if renderer.returncode != 0:
        raise ValidationError(
            "Markdown/HTML exact parity failed: "
            + (renderer.stderr.strip() or renderer.stdout.strip())
        )
    assets, static_fallback_verified, errors = _artifact_errors(
        route,
        markdown_text,
        html_text,
        html_path,
        forbidden,
        source_path,
        retrieval,
    )
    if errors:
        raise ValidationError("; ".join(sorted(set(errors))))
    implementation_path, implementation_bytes = _read_regular(
        Path(__file__), label="visual verifier implementation"
    )
    renderer_path, renderer_bytes = _read_regular(
        RENDERER, label="Markdown renderer implementation"
    )
    result = {
        "schema_version": 1,
        "status": "passed",
        "route": route,
        "delivery_route": delivery,
        "requested_runtime_applicable": route in {"interactive", "motion"},
        "requested_runtime_verified": runtime_direct,
        "checks": {
            "actual_bytes_scanned_for_declared_textual_leakage": True,
            "attempt_before_reveal": "passed" if retrieval else "not_applicable",
            "animated_or_unvalidated_assets_absent": True,
            "linked_textual_assets_scanned": True,
            "markdown_html_exact_parity": True,
            "raster_semantics_automatically_verified": False,
            "semantic_visual_leakage": "manual_review_required",
            "static_fallback_verified": static_fallback_verified,
            "unbundled_runtime_promoted": False,
        },
        "inputs": {
            "forbidden_answer_rubric": {
                "path": _receipt_path(rubric_path),
                "sha256": _sha256(rubric_bytes),
            },
            "generated_html": {
                "path": _receipt_path(html_path),
                "sha256": _sha256(html_bytes),
            },
            "route_output": {
                "path": _receipt_path(route_path),
                "sha256": _sha256(route_bytes),
            },
            "source": {
                "path": _receipt_path(source_path),
                "sha256": _sha256(source_bytes),
            },
        },
        "linked_textual_assets": assets,
        "verifier": {
            "implementation": {
                "path": _receipt_path(implementation_path),
                "sha256": _sha256(implementation_bytes),
            },
            "renderer": {
                "path": _receipt_path(renderer_path),
                "sha256": _sha256(renderer_bytes),
            },
            "version": VERIFIER_VERSION,
        },
        "claim_boundary": (
            "Automated static-delivery bytes passed deterministic structure and declared textual-leakage checks. "
            "Geometry, color, emphasis, and other semantic visual leakage still require human review. "
            "No browser, assistive-technology, field-accessibility, factual-correctness, or human-learning claim is supported."
        ),
    }
    encoded = canonical_json_bytes(result)
    if receipt is not None:
        receipt_path = prepare_private_parent(receipt, create_missing=not check)
        input_paths = {route_path, source_path, html_path, rubric_path}
        if receipt_path in input_paths:
            raise SafetyError("visual verification receipt cannot overwrite an input")
        if check:
            _existing, existing_bytes = _read_regular(
                receipt_path, label="visual verification receipt"
            )
            if existing_bytes != encoded:
                raise ValidationError("visual verification receipt is stale")
        else:
            with anchored_file_target(receipt_path) as target:
                atomic_write_anchored(target, encoded, mode=PRIVATE_FILE_MODE)
    elif check:
        raise ValidationError("--check requires --receipt")
    return result
