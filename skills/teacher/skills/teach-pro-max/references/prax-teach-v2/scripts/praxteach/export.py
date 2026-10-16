"""Deterministic, scoped learner-data export."""

from __future__ import annotations

import contextlib
import hashlib
import io
import os
import stat
import zipfile
from collections.abc import Iterator
from pathlib import Path, PurePath
from typing import Any

from . import CORE_VERSION, SCHEMA_VERSION
from .errors import SafetyError, ValidationError
from .io import (
    PRIVATE_FILE_MODE,
    AnchoredFileTarget,
    anchored_file_target,
    atomic_write_anchored,
    canonical_json_bytes,
    prepare_private_parent,
    read_bytes,
    secure_workspace,
    workspace_lock,
)
from .state import (
    _active_observations,
    _validate_workspace_state,
    load_events,
    load_source_library,
    normalize_timestamp,
    project_events,
    source_record_index,
    validate_event_source_resolution,
)

EXPORT_FILES = (
    "MISSION.md",
    "RESOURCES.md",
    "state/concepts.json",
    "state/learner.json",
    "state/misconceptions.json",
    "state/reviews.jsonl",
    "state/sessions.jsonl",
    "state/sources.json",
)
ZIP_DATETIME = (1980, 1, 1, 0, 0, 0)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=ZIP_DATETIME)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | PRIVATE_FILE_MODE) << 16
    info.flag_bits |= 0x800
    return info


@contextlib.contextmanager
def _prepare_output(path: str, workspace: Path) -> Iterator[AnchoredFileTarget]:
    raw = Path(path).expanduser()
    if any(part == ".." for part in PurePath(raw).parts):
        raise SafetyError("export path traversal ('..') is not allowed")
    preflight = prepare_private_parent(raw, create_missing=False)
    try:
        preflight.relative_to(workspace)
    except ValueError:
        pass
    else:
        raise SafetyError("export target must be outside the learner workspace")

    with anchored_file_target(raw) as target:
        resolved = target.path
        if resolved != preflight:
            raise SafetyError("export path changed while its parent was being prepared")
        try:
            if target.parent_descriptor is not None:
                target_stat = os.stat(
                    resolved.name,
                    dir_fd=target.parent_descriptor,
                    follow_symlinks=False,
                )
            else:
                target_stat = resolved.lstat()
        except FileNotFoundError:
            target_stat = None
        if target_stat is not None and stat.S_ISLNK(target_stat.st_mode):
            raise SafetyError("export target must not be a symlink")
        try:
            resolved.relative_to(workspace)
        except ValueError:
            pass
        else:
            raise SafetyError("export target must be outside the learner workspace")
        if target_stat is not None and not stat.S_ISREG(target_stat.st_mode):
            raise ValidationError("export target exists and is not a regular file")
        yield target


def export_workspace(path: str, output: str, *, exported_at: str) -> dict[str, Any]:
    """Write a byte-reproducible ZIP for a fixed timestamp and state."""

    workspace = secure_workspace(path)
    timestamp = normalize_timestamp(exported_at)
    with _prepare_output(output, workspace) as target:
        with workspace_lock(workspace):
            # Export is a learner control, not a persistence operation. In
            # particular, consent withdrawal must not be bypassed by rebuilding and
            # atomically replacing projection files. Validate the source records and
            # derive canonical projections only in memory.
            _validate_workspace_state(workspace, require_active=False)
            events = load_events(workspace)
            source_library = load_source_library(workspace)
            validate_event_source_resolution(events, source_library)
            concepts, misconceptions = project_events(events)
            files = {
                "MISSION.md": read_bytes(workspace, "MISSION.md"),
                "RESOURCES.md": read_bytes(workspace, "RESOURCES.md"),
                "state/concepts.json": canonical_json_bytes(concepts),
                "state/learner.json": read_bytes(workspace, "state/learner.json"),
                "state/misconceptions.json": canonical_json_bytes(misconceptions),
                "state/reviews.jsonl": read_bytes(workspace, "state/reviews.jsonl"),
                "state/sessions.jsonl": read_bytes(workspace, "state/sessions.jsonl"),
                "state/sources.json": read_bytes(workspace, "state/sources.json"),
            }

            source_records = source_record_index(source_library)
            active_bindings: dict[tuple[str, str], set[str]] = {}
            active_reference_count = 0
            for event in _active_observations(events):
                for reference in event["source_provenance"]:
                    key = (
                        str(reference["source_id"]),
                        str(reference["version_or_date"]),
                    )
                    active_bindings.setdefault(key, set()).add(str(event["event_id"]))
                    active_reference_count += 1
            resolved_active_sources = [
                {
                    "source_id": source_id,
                    "source_record_sha256": _sha256(
                        canonical_json_bytes(source_records[(source_id, version)])
                    ),
                    "supporting_event_ids": sorted(
                        active_bindings[(source_id, version)]
                    ),
                    "version_or_date": version,
                }
                for source_id, version in sorted(active_bindings)
            ]

        manifest = {
            "core": {"name": "prax-teach-v2", "version": CORE_VERSION},
            "exported_at": timestamp,
            "files": [
                {
                    "path": name,
                    "sha256": _sha256(files[name]),
                    "size": len(files[name]),
                }
                for name in sorted(files)
            ],
            "format": "prax-teach-learner-export",
            "provenance": {
                "event_source_references": "state/sessions.jsonl#source_provenance",
                "human_readable_resources": "RESOURCES.md",
                "source_library": {
                    "active_reference_count": active_reference_count,
                    "path": "state/sources.json",
                    "resolved_active_source_count": len(resolved_active_sources),
                    "resolved_active_sources": resolved_active_sources,
                    "sha256": _sha256(files["state/sources.json"]),
                },
            },
            "schema_version": SCHEMA_VERSION,
        }
        files["manifest.json"] = canonical_json_bytes(manifest)

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, mode="w", allowZip64=True) as archive:
            archive.comment = b""
            for name in sorted(files):
                archive.writestr(_zip_info(name), files[name])
        payload = buffer.getvalue()
        atomic_write_anchored(target, payload, mode=PRIVATE_FILE_MODE)
    return {
        "file_count": len(files),
        "sha256": _sha256(payload),
        "status": "exported",
    }
