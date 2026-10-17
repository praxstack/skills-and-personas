"""Pure, deterministic export and validation implementation.

The exporters intentionally use the Python standard library only.  An H5P
archive contains content and dependency declarations, not the H5P JavaScript
runtime; a conforming H5P host must already provide those declared libraries.
"""

from __future__ import annotations

import hashlib
import html
import io
import json
import os
import re
import stat
import tempfile
import uuid
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from xml.etree import ElementTree as ET

MODEL_VERSION = "1"
QTI_VERSION = "2.2"
H5P_QUESTION_SET_VERSION = "1.20"
FORMATS = ("anki", "qti", "liascript", "h5p")
DEFAULT_EPOCH = 315532800  # 1980-01-01T00:00:00Z, the first ZIP date.
MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 10000

SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9_-])?$")
SAFE_TAG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
LANGUAGE = re.compile(r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$")

CP_NS = "http://www.imsglobal.org/xsd/imscp_v1p1"
QTI_NS = "http://www.imsglobal.org/xsd/imsqti_v2p2"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
ET.register_namespace("", CP_NS)
ET.register_namespace("xsi", XSI_NS)


class ExportError(ValueError):
    """An item model or artifact violates the public export contract."""


@dataclass(frozen=True)
class LearningItem:
    item_id: str
    prompt: str
    answer: str
    explanation: str
    choices: tuple[str, ...]
    tags: tuple[str, ...]


@dataclass(frozen=True)
class Collection:
    collection_id: str
    title: str
    language: str
    license: str
    source: str
    items: tuple[LearningItem, ...]


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _non_empty_text(value: Any, field: str, *, maximum: int = 20000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExportError(f"{field} must be a non-empty string")
    if len(value) > maximum:
        raise ExportError(f"{field} exceeds {maximum} characters")
    if "\x00" in value:
        raise ExportError(f"{field} contains a NUL character")
    return value


def _safe_identifier(value: Any, field: str) -> str:
    text = _non_empty_text(value, field, maximum=128)
    if (
        not SAFE_IDENTIFIER.fullmatch(text)
        or ".." in text
        or "/" in text
        or "\\" in text
        or text in {".", ".."}
    ):
        raise ExportError(
            f"{field} is unsafe; use 1-128 ASCII letters, digits, dot, underscore, or hyphen "
            "without path components or '..'"
        )
    return text


def _exact_keys(value: dict[str, Any], *, required: set[str], field: str) -> None:
    missing = sorted(required - value.keys())
    extra = sorted(value.keys() - required)
    if missing:
        raise ExportError(f"{field} is missing required fields: {', '.join(missing)}")
    if extra:
        raise ExportError(f"{field} has unsupported fields: {', '.join(extra)}")


def parse_collection(value: Any) -> Collection:
    if not isinstance(value, dict):
        raise ExportError("learning-item source must be a JSON object")
    root_fields = {
        "schema_version",
        "collection_id",
        "title",
        "language",
        "license",
        "source",
        "items",
    }
    _exact_keys(value, required=root_fields, field="collection")
    if value["schema_version"] != MODEL_VERSION:
        raise ExportError(f"schema_version must be {MODEL_VERSION!r}")
    collection_id = _safe_identifier(value["collection_id"], "collection_id")
    title = _non_empty_text(value["title"], "title")
    language = _non_empty_text(value["language"], "language", maximum=63)
    if not LANGUAGE.fullmatch(language):
        raise ExportError("language must be a BCP-47-style language tag")
    license_text = _non_empty_text(value["license"], "license")
    source = _non_empty_text(value["source"], "source")
    raw_items = value["items"]
    if not isinstance(raw_items, list) or not raw_items:
        raise ExportError("items must be a non-empty array")

    items: list[LearningItem] = []
    seen_ids: set[str] = set()
    item_fields = {"id", "prompt", "answer", "explanation", "choices", "tags"}
    for index, raw in enumerate(raw_items):
        field = f"items[{index}]"
        if not isinstance(raw, dict):
            raise ExportError(f"{field} must be an object")
        _exact_keys(raw, required=item_fields, field=field)
        item_id = _safe_identifier(raw["id"], f"{field}.id")
        if item_id in seen_ids:
            raise ExportError(f"duplicate item id: {item_id}")
        seen_ids.add(item_id)
        prompt = _non_empty_text(raw["prompt"], f"{field}.prompt")
        answer = _non_empty_text(raw["answer"], f"{field}.answer")
        explanation = _non_empty_text(raw["explanation"], f"{field}.explanation")

        raw_choices = raw["choices"]
        if not isinstance(raw_choices, list):
            raise ExportError(f"{field}.choices must be an array")
        choices = tuple(
            _non_empty_text(choice, f"{field}.choices[{choice_index}]")
            for choice_index, choice in enumerate(raw_choices)
        )
        if len(set(choices)) != len(choices):
            raise ExportError(f"{field}.choices must be unique")
        if choices:
            if len(choices) < 2:
                raise ExportError(
                    f"{field}.choices must contain at least two choices or be empty"
                )
            if choices.count(answer) != 1:
                raise ExportError(f"{field}.answer must occur exactly once in choices")

        raw_tags = raw["tags"]
        if not isinstance(raw_tags, list):
            raise ExportError(f"{field}.tags must be an array")
        tags: list[str] = []
        for tag_index, tag in enumerate(raw_tags):
            if not isinstance(tag, str) or not SAFE_TAG.fullmatch(tag):
                raise ExportError(
                    f"{field}.tags[{tag_index}] must contain only letters, digits, underscore, or hyphen"
                )
            tags.append(tag)
        if len(set(tags)) != len(tags):
            raise ExportError(f"{field}.tags must be unique")
        items.append(
            LearningItem(
                item_id, prompt, answer, explanation, choices, tuple(sorted(tags))
            )
        )

    return Collection(
        collection_id, title, language, license_text, source, tuple(items)
    )


def load_collection(path: Path) -> Collection:
    try:
        if path.stat().st_size > MAX_INPUT_BYTES:
            raise ExportError(f"learning-item source exceeds {MAX_INPUT_BYTES} bytes")
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ExportError(f"learning-item source not found: {path}") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise ExportError(
            f"cannot read UTF-8 learning-item source {path}: {exc}"
        ) from exc
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ExportError(
            f"invalid JSON in {path} at line {exc.lineno}: {exc.msg}"
        ) from exc
    return parse_collection(value)


def _html_text(value: str) -> str:
    escaped = html.escape(value, quote=True).replace("\t", "&#9;")
    return escaped.replace("\r\n", "<br>").replace("\r", "<br>").replace("\n", "<br>")


def _markdown_text(value: str) -> str:
    value = value.replace("\\", "\\\\")
    value = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for character in ("`", "*", "_", "[", "]"):
        value = value.replace(character, "\\" + character)
    return value.replace("\r\n", " ").replace("\r", " ").replace("\n", "  \n")


def export_anki(collection: Collection, _epoch: int) -> tuple[bytes, dict[str, Any]]:
    lines = [
        "#separator:tab",
        "#html:true",
        "#notetype:Prax Teach Retrieval",
        "#columns:Front\tBack\tTags",
    ]
    for item in collection.items:
        front = f'<div class="prax-prompt">{_html_text(item.prompt)}</div>'
        back = (
            f'<div class="prax-answer"><strong>Answer:</strong> {_html_text(item.answer)}</div>'
            f'<div class="prax-explanation"><strong>Explanation:</strong> {_html_text(item.explanation)}</div>'
        )
        lines.append("\t".join((front, back, " ".join(item.tags))))
    return ("\n".join(lines) + "\n").encode("utf-8"), {
        "artifact_type": "Anki text import",
        "not_a_fake_apkg": True,
        "item_count": len(collection.items),
    }


def _xml_bytes(element: ET.Element) -> bytes:
    ET.indent(element, space="  ")
    return (
        ET.tostring(
            element, encoding="utf-8", xml_declaration=True, short_empty_elements=True
        )
        + b"\n"
    )


def _qti_item(item: LearningItem) -> bytes:
    root = ET.Element(
        f"{{{QTI_NS}}}assessmentItem",
        {
            "identifier": f"ITEM_{item.item_id}",
            "title": item.prompt,
            "adaptive": "false",
            "timeDependent": "false",
            f"{{{XSI_NS}}}schemaLocation": f"{QTI_NS} imsqti_v2p2.xsd",
        },
    )
    declaration = ET.SubElement(
        root,
        f"{{{QTI_NS}}}responseDeclaration",
        {
            "identifier": "RESPONSE",
            "cardinality": "single",
            "baseType": "identifier" if item.choices else "string",
        },
    )
    correct = ET.SubElement(declaration, f"{{{QTI_NS}}}correctResponse")
    correct_value = ET.SubElement(correct, f"{{{QTI_NS}}}value")
    if item.choices:
        correct_value.text = f"CHOICE_{item.choices.index(item.answer) + 1}"
    else:
        correct_value.text = item.answer
    ET.SubElement(
        root,
        f"{{{QTI_NS}}}outcomeDeclaration",
        {"identifier": "SCORE", "cardinality": "single", "baseType": "float"},
    )
    body = ET.SubElement(root, f"{{{QTI_NS}}}itemBody")
    prompt = ET.SubElement(body, f"{{{QTI_NS}}}p")
    prompt.text = item.prompt
    if item.choices:
        interaction = ET.SubElement(
            body,
            f"{{{QTI_NS}}}choiceInteraction",
            {"responseIdentifier": "RESPONSE", "shuffle": "false", "maxChoices": "1"},
        )
        for index, choice in enumerate(item.choices, start=1):
            option = ET.SubElement(
                interaction,
                f"{{{QTI_NS}}}simpleChoice",
                {"identifier": f"CHOICE_{index}"},
            )
            option.text = choice
    else:
        ET.SubElement(
            body,
            f"{{{QTI_NS}}}extendedTextInteraction",
            {
                "responseIdentifier": "RESPONSE",
                "expectedLength": str(max(80, len(item.answer))),
            },
        )
    rubric = ET.SubElement(body, f"{{{QTI_NS}}}rubricBlock", {"view": "scorer"})
    rubric.text = f"Expected answer: {item.answer}\nExplanation: {item.explanation}"
    ET.SubElement(
        root,
        f"{{{QTI_NS}}}responseProcessing",
        {
            "template": "http://www.imsglobal.org/question/qti_v2p2/rptemplates/match_correct"
        },
    )
    return _xml_bytes(root)


def _qti_manifest(collection: Collection) -> bytes:
    root = ET.Element(
        f"{{{CP_NS}}}manifest",
        {
            "identifier": f"MANIFEST_{collection.collection_id}",
            f"{{{XSI_NS}}}schemaLocation": (
                f"{CP_NS} imscp_v1p1.xsd {QTI_NS} imsqti_v2p2.xsd"
            ),
        },
    )
    metadata = ET.SubElement(root, f"{{{CP_NS}}}metadata")
    schema = ET.SubElement(metadata, f"{{{CP_NS}}}schema")
    schema.text = "IMS Content"
    version = ET.SubElement(metadata, f"{{{CP_NS}}}schemaversion")
    version.text = "1.2.0 / QTI 2.2"
    resources = ET.SubElement(root, f"{{{CP_NS}}}resources")
    for item in collection.items:
        href = f"items/{item.item_id}.xml"
        resource = ET.SubElement(
            resources,
            f"{{{CP_NS}}}resource",
            {
                "identifier": f"RESOURCE_{item.item_id}",
                "type": "imsqti_item_xmlv2p2",
                "href": href,
            },
        )
        ET.SubElement(resource, f"{{{CP_NS}}}file", {"href": href})
    return _xml_bytes(root)


def _zip_date(epoch: int) -> tuple[int, int, int, int, int, int]:
    if isinstance(epoch, bool) or not isinstance(epoch, int):
        raise ExportError("epoch must be an integer Unix timestamp")
    try:
        moment = datetime.fromtimestamp(epoch, timezone.utc)
    except (OverflowError, OSError, ValueError) as exc:
        raise ExportError("epoch is outside the supported timestamp range") from exc
    if not 1980 <= moment.year <= 2107:
        raise ExportError("epoch date must be within ZIP's 1980-2107 range")
    # Archive metadata deliberately uses midnight of the epoch's UTC date.
    # This avoids host-timezone variation while retaining the declared build date.
    return (moment.year, moment.month, moment.day, 0, 0, 0)


def _safe_archive_name(name: str) -> None:
    path = PurePosixPath(name)
    raw_parts = name.split("/")
    if (
        not name
        or "\\" in name
        or name.startswith("/")
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in raw_parts)
    ):
        raise ExportError(f"unsafe archive entry path: {name!r}")


def deterministic_zip(entries: dict[str, bytes], epoch: int) -> bytes:
    timestamp = _zip_date(epoch)
    target = io.BytesIO()
    with zipfile.ZipFile(
        target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for name in sorted(entries):
            _safe_archive_name(name)
            info = zipfile.ZipInfo(name, date_time=timestamp)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.flag_bits |= 0x800
            info.extra = b""
            info.comment = b""
            archive.writestr(info, entries[name])
    return target.getvalue()


def export_qti(collection: Collection, epoch: int) -> tuple[bytes, dict[str, Any]]:
    entries = {"imsmanifest.xml": _qti_manifest(collection)}
    entries.update(
        {f"items/{item.item_id}.xml": _qti_item(item) for item in collection.items}
    )
    return deterministic_zip(entries, epoch), {
        "artifact_type": "IMS Question and Test Interoperability package",
        "qti_version": QTI_VERSION,
        "content_package_version": "1.2.0",
        "item_count": len(collection.items),
    }


def export_liascript(
    collection: Collection, _epoch: int
) -> tuple[bytes, dict[str, Any]]:
    lines = [
        "<!--",
        "author: Prax Teach v2",
        f"title: {_markdown_text(collection.title)}",
        f"language: {_markdown_text(collection.language)}",
        f"version: {MODEL_VERSION}",
        f"license: {_markdown_text(collection.license)}",
        f"source: {_markdown_text(collection.source)}",
        "-->",
        "",
        f"# {_markdown_text(collection.title)}",
        "",
        "> This course is a text-first export. Every quiz retains a readable prompt, answer, and explanation.",
        "",
    ]
    for item in collection.items:
        lines.extend(
            (
                f"## {_markdown_text(item.item_id)}",
                "",
                _markdown_text(item.prompt),
                "",
            )
        )
        if item.choices:
            for choice in item.choices:
                marker = "X" if choice == item.answer else " "
                lines.append(f"[({marker})] {_markdown_text(choice)}")
        else:
            lines.append(f"[[{_markdown_text(item.answer)}]]")
        lines.extend(
            (
                "",
                f"**Explanation:** {_markdown_text(item.explanation)}",
                "",
                f"**Text fallback — expected answer:** {_markdown_text(item.answer)}",
                "",
                f"Tags: {', '.join(_markdown_text(tag) for tag in item.tags) or 'none'}",
                "",
            )
        )
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8"), {
        "artifact_type": "LiaScript Markdown",
        "syntax": "native single-choice and free-text",
        "item_count": len(collection.items),
    }


def _h5p_question(item: LearningItem) -> dict[str, Any]:
    subcontent_id = str(
        uuid.UUID(hashlib.sha256(f"h5p\0{item.item_id}".encode()).hexdigest()[:32])
    )
    if item.choices:
        return {
            "library": "H5P.MultiChoice 1.16",
            "subContentId": subcontent_id,
            "params": {
                "question": f"<p>{_html_text(item.prompt)}</p>",
                "answers": [
                    {
                        "text": f"<div>{_html_text(choice)}</div>",
                        "correct": choice == item.answer,
                        "tipsAndFeedback": {
                            "chosenFeedback": _html_text(item.explanation),
                            "notChosenFeedback": "",
                            "tip": "",
                        },
                    }
                    for choice in item.choices
                ],
                "behaviour": {
                    "enableRetry": True,
                    "enableSolutionsButton": True,
                    "enableCheckButton": True,
                    "type": "auto",
                    "singlePoint": True,
                    "randomAnswers": False,
                    "showSolutionsRequiresInput": True,
                },
                "overallFeedback": [
                    {"from": 0, "to": 100, "feedback": _html_text(item.explanation)}
                ],
            },
        }
    return {
        "library": "H5P.Essay 1.5",
        "subContentId": subcontent_id,
        "params": {
            "taskDescription": f"<p>{_html_text(item.prompt)}</p>",
            "placeholderText": "Type your answer here",
            "solution": {"sample": f"<p>{_html_text(item.answer)}</p>"},
            "keywords": [
                {
                    "keyword": item.answer,
                    "alternatives": [],
                    "options": {"points": 1, "occurrences": 1, "caseSensitive": False},
                }
            ],
            "overallFeedback": [
                {"from": 0, "to": 100, "feedback": _html_text(item.explanation)}
            ],
        },
    }


def _h5p_license(license_text: str) -> tuple[str, str]:
    normalized = " ".join(
        license_text.upper().replace("CREATIVE COMMONS", "CC").split()
    )
    supported = (
        "CC BY-NC-ND",
        "CC BY-NC-SA",
        "CC BY-NC",
        "CC BY-ND",
        "CC BY-SA",
        "CC BY",
    )
    for code in supported:
        if normalized.startswith(code):
            version_match = re.search(r"\b([1-4]\.0)\b", normalized)
            return code, version_match.group(1) if version_match else ""
    if normalized in {"PUBLIC DOMAIN", "PD"}:
        return "PD", ""
    return "U", ""


def export_h5p(collection: Collection, epoch: int) -> tuple[bytes, dict[str, Any]]:
    license_code, license_version = _h5p_license(collection.license)
    has_multiple_choice = any(item.choices for item in collection.items)
    has_essay = any(not item.choices for item in collection.items)
    dependencies = [
        {"machineName": "H5P.QuestionSet", "majorVersion": 1, "minorVersion": 20}
    ]
    required_host_libraries = ["H5P.QuestionSet 1.20"]
    if has_multiple_choice:
        dependencies.append(
            {"machineName": "H5P.MultiChoice", "majorVersion": 1, "minorVersion": 16}
        )
        required_host_libraries.append("H5P.MultiChoice 1.16")
    if has_essay:
        dependencies.append(
            {"machineName": "H5P.Essay", "majorVersion": 1, "minorVersion": 5}
        )
        required_host_libraries.append("H5P.Essay 1.5")
    metadata = {
        "title": collection.title,
        "language": collection.language,
        "license": license_code,
        "licenseVersion": license_version,
        "source": collection.source,
        "mainLibrary": "H5P.QuestionSet",
        "embedTypes": ["div"],
        "preloadedDependencies": dependencies,
    }
    content = {
        "introPage": {"showIntroPage": False},
        "progressType": "textual",
        "passPercentage": 100,
        "questions": [_h5p_question(item) for item in collection.items],
        "texts": {
            "prevButton": "Previous question",
            "nextButton": "Next question",
            "finishButton": "Finish",
            "submitButton": "Submit",
            "textualProgress": "Question @current of @total questions",
        },
    }
    archive = deterministic_zip(
        {
            "content/content.json": canonical_json_bytes(content),
            "h5p.json": canonical_json_bytes(metadata),
        },
        epoch,
    )
    return archive, {
        "artifact_type": "H5P content package",
        "main_library": "H5P.QuestionSet",
        "main_library_version": H5P_QUESTION_SET_VERSION,
        "self_contained_runtime": False,
        "requires_host_libraries": required_host_libraries,
        "item_count": len(collection.items),
    }


EXPORTERS: dict[str, Callable[[Collection, int], tuple[bytes, dict[str, Any]]]] = {
    "anki": export_anki,
    "qti": export_qti,
    "liascript": export_liascript,
    "h5p": export_h5p,
}


def atomic_write(path: Path, data: bytes) -> None:
    if path.exists() and path.is_dir():
        raise ExportError(f"output path is a directory: {path}")
    if path.is_symlink():
        raise ExportError(f"refusing to replace output symlink: {path}")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        parent = path.parent.resolve(strict=True)
    except OSError as exc:
        raise ExportError(f"cannot prepare output directory for {path}: {exc}") from exc
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    except OSError as exc:
        raise ExportError(f"cannot write output {path}: {exc}") from exc
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def export_artifact(
    format_name: str, collection: Collection, epoch: int
) -> tuple[bytes, dict[str, Any]]:
    try:
        exporter = EXPORTERS[format_name]
    except KeyError as exc:
        raise ExportError(f"unsupported export format: {format_name}") from exc
    return exporter(collection, epoch)


def _read_artifact(path: Path) -> bytes:
    try:
        size = path.stat().st_size
        if size > MAX_ARCHIVE_BYTES:
            raise ExportError(f"artifact exceeds {MAX_ARCHIVE_BYTES} bytes")
        return path.read_bytes()
    except FileNotFoundError as exc:
        raise ExportError(f"artifact not found: {path}") from exc
    except OSError as exc:
        raise ExportError(f"cannot read artifact {path}: {exc}") from exc


def _safe_zip(artifact: bytes) -> dict[str, bytes]:
    try:
        with zipfile.ZipFile(io.BytesIO(artifact)) as archive:
            if archive.comment:
                raise ExportError(
                    "archive comment must be empty for deterministic output"
                )
            infos = archive.infolist()
            if len(infos) > MAX_ARCHIVE_ENTRIES:
                raise ExportError("archive contains too many entries")
            if [info.filename for info in infos] != sorted(
                info.filename for info in infos
            ):
                raise ExportError(
                    "archive entries are not in deterministic lexical order"
                )
            names: set[str] = set()
            total = 0
            entries: dict[str, bytes] = {}
            for info in infos:
                _safe_archive_name(info.filename)
                if info.filename in names:
                    raise ExportError(
                        f"archive contains duplicate entry: {info.filename}"
                    )
                names.add(info.filename)
                if info.is_dir():
                    raise ExportError(
                        f"archive contains an unexpected directory entry: {info.filename}"
                    )
                if info.date_time[3:] != (0, 0, 0):
                    raise ExportError(
                        f"archive entry {info.filename} timestamp is not normalized to UTC-day midnight"
                    )
                if (info.external_attr >> 16) & 0o777 != 0o644:
                    raise ExportError(
                        f"archive entry {info.filename} permissions are not normalized to 0644"
                    )
                if info.compress_type != zipfile.ZIP_DEFLATED:
                    raise ExportError(
                        f"archive entry {info.filename} does not use deterministic DEFLATE storage"
                    )
                if info.extra or info.comment:
                    raise ExportError(
                        f"archive entry {info.filename} has non-canonical extra metadata"
                    )
                total += info.file_size
                if total > MAX_ARCHIVE_BYTES:
                    raise ExportError("uncompressed archive exceeds safety limit")
                entries[info.filename] = archive.read(info)
            return entries
    except zipfile.BadZipFile as exc:
        raise ExportError("artifact is not a valid ZIP package") from exc


def _parse_xml(data: bytes, field: str) -> ET.Element:
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ExportError(f"{field} must not contain DTD or entity declarations")
    try:
        return ET.fromstring(data)
    except ET.ParseError as exc:
        raise ExportError(f"invalid XML in {field}: {exc}") from exc


def validate_anki(data: bytes) -> dict[str, Any]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ExportError("Anki text import must be UTF-8") from exc
    lines = text.splitlines()
    expected = [
        "#separator:tab",
        "#html:true",
        "#notetype:Prax Teach Retrieval",
        "#columns:Front\tBack\tTags",
    ]
    if lines[:4] != expected:
        raise ExportError(
            "Anki artifact is missing the required deterministic text-import headers"
        )
    if len(lines) <= 4:
        raise ExportError("Anki artifact contains no cards")
    for number, line in enumerate(lines[4:], start=5):
        columns = line.split("\t")
        if len(columns) != 3 or not columns[0].strip() or not columns[1].strip():
            raise ExportError(
                f"Anki line {number} must contain non-empty Front, Back, and Tags columns"
            )
        if "<script" in line.lower() or re.search(
            r"\bon[a-z]+\s*=", line, re.IGNORECASE
        ):
            raise ExportError(f"Anki line {number} contains executable HTML")
    return {
        "artifact_type": "Anki text import",
        "card_count": len(lines) - 4,
        "not_apkg": True,
    }


def validate_qti(data: bytes) -> dict[str, Any]:
    entries = _safe_zip(data)
    if "imsmanifest.xml" not in entries:
        raise ExportError("QTI package is missing imsmanifest.xml")
    manifest = _parse_xml(entries["imsmanifest.xml"], "imsmanifest.xml")
    if manifest.tag != f"{{{CP_NS}}}manifest":
        raise ExportError("QTI manifest uses an unsupported content-package namespace")
    resources = manifest.findall(f".//{{{CP_NS}}}resource")
    if not resources:
        raise ExportError("QTI manifest contains no item resources")
    expected_paths: set[str] = set()
    for resource in resources:
        href = resource.get("href")
        if not href:
            raise ExportError("QTI resource is missing href")
        _safe_archive_name(href)
        if not href.startswith("items/") or not href.endswith(".xml"):
            raise ExportError(
                f"QTI resource is outside the deterministic items directory: {href}"
            )
        if resource.get("type") != "imsqti_item_xmlv2p2":
            raise ExportError(f"QTI resource {href} does not declare QTI 2.2")
        expected_paths.add(href)
    if len(expected_paths) != len(resources):
        raise ExportError("QTI manifest contains duplicate item resources")
    missing = sorted(expected_paths - entries.keys())
    if missing:
        raise ExportError(
            f"QTI package is missing manifest resources: {', '.join(missing)}"
        )
    unexpected = sorted(entries.keys() - expected_paths - {"imsmanifest.xml"})
    if unexpected:
        raise ExportError(
            f"QTI package contains unmanifested entries: {', '.join(unexpected)}"
        )
    for href in sorted(expected_paths):
        item = _parse_xml(entries[href], href)
        if item.tag != f"{{{QTI_NS}}}assessmentItem":
            raise ExportError(f"{href} is not an IMS QTI 2.2 assessmentItem")
        body = item.find(f"{{{QTI_NS}}}itemBody")
        correct = item.find(f".//{{{QTI_NS}}}correctResponse/{{{QTI_NS}}}value")
        if body is None or correct is None or not (correct.text or "").strip():
            raise ExportError(
                f"{href} lacks accessible body text or a correct response"
            )
    return {
        "artifact_type": "IMS QTI package",
        "qti_version": QTI_VERSION,
        "item_count": len(resources),
    }


def validate_liascript(data: bytes) -> dict[str, Any]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ExportError("LiaScript artifact must be UTF-8") from exc
    if not text.startswith("<!--\n") or "\n-->\n" not in text:
        raise ExportError("LiaScript artifact is missing its metadata comment")
    quizzes = len(re.findall(r"^\[\((?:X| )\)\] ", text, flags=re.MULTILINE))
    free_text = len(re.findall(r"^\[\[.+\]\]$", text, flags=re.MULTILINE))
    if quizzes + free_text == 0:
        raise ExportError("LiaScript artifact contains no native quiz syntax")
    if (
        "**Explanation:**" not in text
        or "**Text fallback — expected answer:**" not in text
    ):
        raise ExportError("LiaScript artifact lacks explanation or text fallback")
    if re.search(r"<(?:script|iframe|object|embed)\b", text, re.IGNORECASE):
        raise ExportError("LiaScript artifact contains unsafe raw HTML")
    return {
        "artifact_type": "LiaScript Markdown",
        "quiz_lines": quizzes,
        "free_text_items": free_text,
    }


def _load_json_member(entries: dict[str, bytes], name: str) -> dict[str, Any]:
    if name not in entries:
        raise ExportError(f"H5P package is missing {name}")
    try:
        value = json.loads(entries[name].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExportError(f"H5P member {name} is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ExportError(f"H5P member {name} must contain a JSON object")
    return value


def validate_h5p(data: bytes) -> dict[str, Any]:
    entries = _safe_zip(data)
    expected_entries = {"h5p.json", "content/content.json"}
    if set(entries) != expected_entries:
        extra = sorted(set(entries) - expected_entries)
        missing = sorted(expected_entries - set(entries))
        details = []
        if missing:
            details.append(f"missing {', '.join(missing)}")
        if extra:
            details.append(f"unexpected {', '.join(extra)}")
        raise ExportError(
            "thin H5P package must contain only its two required JSON files: "
            + "; ".join(details)
        )
    metadata = _load_json_member(entries, "h5p.json")
    content = _load_json_member(entries, "content/content.json")
    if metadata.get("mainLibrary") != "H5P.QuestionSet":
        raise ExportError("H5P mainLibrary must be H5P.QuestionSet")
    dependencies = metadata.get("preloadedDependencies")
    if not isinstance(dependencies, list):
        raise ExportError("H5P package lacks preloadedDependencies")
    dependency_names: set[str] = set()
    for index, dependency in enumerate(dependencies):
        if not isinstance(dependency, dict):
            raise ExportError(f"H5P preloadedDependencies[{index}] must be an object")
        machine_name = dependency.get("machineName")
        if not isinstance(machine_name, str) or not machine_name:
            raise ExportError(f"H5P preloadedDependencies[{index}] lacks machineName")
        if not isinstance(dependency.get("majorVersion"), int) or not isinstance(
            dependency.get("minorVersion"), int
        ):
            raise ExportError(
                f"H5P dependency {machine_name} lacks integer major/minor versions"
            )
        if machine_name in dependency_names:
            raise ExportError(f"H5P dependency is declared twice: {machine_name}")
        dependency_names.add(machine_name)
    if "H5P.QuestionSet" not in dependency_names:
        raise ExportError("H5P package must explicitly depend on H5P.QuestionSet")
    questions = content.get("questions")
    if not isinstance(questions, list) or not questions:
        raise ExportError("H5P content must contain at least one question")
    used_libraries: set[str] = set()
    for index, question in enumerate(questions):
        if not isinstance(question, dict) or not isinstance(
            question.get("library"), str
        ):
            raise ExportError(f"H5P questions[{index}] lacks a library declaration")
        used_library = question["library"].split(" ", 1)[0]
        if used_library not in {"H5P.MultiChoice", "H5P.Essay"}:
            raise ExportError(f"H5P questions[{index}] uses an unsupported library")
        used_libraries.add(used_library)
        try:
            uuid.UUID(str(question.get("subContentId")))
        except (ValueError, AttributeError) as exc:
            raise ExportError(
                f"H5P questions[{index}] has an invalid subContentId UUID"
            ) from exc
        if not isinstance(question.get("params"), dict):
            raise ExportError(f"H5P questions[{index}] lacks params")
    missing_dependencies = sorted(used_libraries - dependency_names)
    if missing_dependencies:
        raise ExportError(
            f"H5P package omits used host libraries: {', '.join(missing_dependencies)}"
        )
    return {
        "artifact_type": "H5P content package",
        "main_library": "H5P.QuestionSet",
        "item_count": len(questions),
        "self_contained_runtime": False,
        "requires_host_library": "H5P.QuestionSet 1.20",
        "runtime_notice": (
            "Valid thin H5P content package; it requires the declared H5P.QuestionSet, "
            "H5P.MultiChoice, and H5P.Essay libraries from the importing host."
        ),
    }


VALIDATORS: dict[str, Callable[[bytes], dict[str, Any]]] = {
    "anki": validate_anki,
    "qti": validate_qti,
    "liascript": validate_liascript,
    "h5p": validate_h5p,
}


def validate_artifact(format_name: str, path: Path) -> tuple[bytes, dict[str, Any]]:
    try:
        validator = VALIDATORS[format_name]
    except KeyError as exc:
        raise ExportError(f"unsupported export format: {format_name}") from exc
    data = _read_artifact(path)
    return data, validator(data)
