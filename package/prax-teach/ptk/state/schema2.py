"""Schema 2 for learner state (D17.12, AC-8.4): navigation kept apart from attempts, an `evidence`
kind, and the snapshot / migrate / rollback steps the install and rollback path uses (AC-8.6).

Consent rules kept from v2, plus two:
- Every write still needs active persistence consent (v2's rule), checked under the workspace lock.
- Navigation is a new kind of data, so it needs its own consent: `grant_navigation` adds "navigation"
  to the consent scope. Without that grant no navigation byte is written. Migration never grants it.
- Evidence records independent work only, with the gap and exactly one next action.

Rollback restores a snapshot byte for byte and reports how many events recorded after it are lost.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from . import RECORD_SCHEMA_V2, WORKSPACE_SCHEMA
from .errors import ConsentRequired, SafetyError, ValidationError
from .io import (
    atomic_write,
    atomic_write_json,
    canonical_json_bytes,
    make_private_directory,
    make_private_file,
    read_bytes,
    read_json,
    read_jsonl,
    secure_workspace,
    workspace_lock,
)
from .state import (
    _event_id,
    _require_identifier,
    _validate_workspace_state,
    load_events,
    normalize_timestamp,
    project_events,
    validate_event,
    validate_event_sequence,
    validate_event_source_resolution,
    load_source_library,
    _commit_event_sequence_locked,
)

NAVIGATION_LOG = "state/navigation.jsonl"
NAVIGATION_ACTIONS = ("open", "seek", "chapter", "replay", "reveal", "flip", "explore", "return", "close")
SNAPSHOT_MANIFEST = "snapshot.json"
SNAPSHOT_FILES = ("MISSION.md", "RESOURCES.md")


# ---------------------------------------------------------------- navigation

def validate_navigation_record(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValidationError("navigation record must be an object")
    expected = {"action", "artifact_id", "event_id", "event_type", "position", "schema_version", "session_id",
                "timestamp"}
    if set(record) != expected:
        raise ValidationError(f"navigation record fields must be exactly: {', '.join(sorted(expected))}")
    if record["event_type"] != "navigation" or record["schema_version"] != RECORD_SCHEMA_V2:
        raise ValidationError("navigation records are schema 2 records of type navigation")
    _require_identifier("session_id", record["session_id"])
    _require_identifier("artifact_id", record["artifact_id"])
    if record["action"] not in NAVIGATION_ACTIONS:
        raise ValidationError(f"navigation action must be one of: {', '.join(NAVIGATION_ACTIONS)}")
    pos = record["position"]
    if pos is not None and (isinstance(pos, bool) or not isinstance(pos, (int, float)) or pos < 0 or pos > 86400):
        raise ValidationError("navigation position is seconds from 0 to 86400, or null")
    normalize_timestamp(record["timestamp"])
    if not isinstance(record["event_id"], str) or not re.fullmatch(r"evt-[0-9a-f]{32}", record["event_id"]):
        raise ValidationError("event_id is invalid")
    body = dict(record)
    body.pop("event_id")
    if record["event_id"] != _event_id(body):
        raise ValidationError("event_id does not match its record")
    return record


def make_navigation(*, session_id: str, artifact_id: str, action: str, position: float | None,
                    timestamp: str) -> dict[str, Any]:
    body = {"action": action, "artifact_id": artifact_id, "event_type": "navigation", "position": position,
            "schema_version": RECORD_SCHEMA_V2, "session_id": session_id, "timestamp": normalize_timestamp(timestamp)}
    record = {**body, "event_id": _event_id(body)}
    return validate_navigation_record(record)


def load_navigation(workspace: Path) -> list[dict[str, Any]]:
    """Navigation records, or [] when the log doesn't exist. Validated on every read."""
    if not (workspace / "state" / "navigation.jsonl").exists():
        return []
    records = read_jsonl(workspace, NAVIGATION_LOG)
    seen: set[str] = set()
    for r in records:
        validate_navigation_record(r)
        if r["event_id"] in seen:
            raise ValidationError(f"duplicate navigation event_id: {r['event_id']}")
        seen.add(r["event_id"])
    return records


def validate_navigation_state(workspace: Path, learner: dict[str, Any]) -> None:
    """Called by _validate_workspace_state: a navigation log needs a schema 2 workspace."""
    present = (workspace / "state" / "navigation.jsonl").exists()
    if present and learner.get("schema_version") != WORKSPACE_SCHEMA:
        raise ValidationError("a schema 1 workspace cannot hold a navigation log")
    if present:
        load_navigation(workspace)


def _require_v2(learner: dict[str, Any]) -> None:
    if learner.get("schema_version") != WORKSPACE_SCHEMA:
        raise ValidationError("this workspace is schema 1; run the migration first")


def grant_navigation(path: str, *, granted_at: str) -> dict[str, Any]:
    """Explicit, separate consent for navigation records. Creates the empty log."""
    workspace = secure_workspace(path)
    timestamp = normalize_timestamp(granted_at)
    with workspace_lock(workspace):
        learner = _validate_workspace_state(workspace)
        _require_v2(learner)
        if "navigation" in learner["consent"]["scope"]:
            raise ValidationError("navigation is already in the consent scope")
        updated = json.loads(json.dumps(learner))
        updated["consent"]["scope"] = [*learner["consent"]["scope"], "navigation"]
        updated["consent"]["navigation_granted_at"] = timestamp
        from .state import validate_learner_document
        validate_learner_document(updated)
        log = workspace / "state" / "navigation.jsonl"
        if not log.exists():
            make_private_file(log)
        atomic_write_json(workspace / "state" / "learner.json", updated)
    return {"status": "navigation_granted", "granted_at": timestamp}


def revoke_navigation(path: str, *, timestamp: str) -> dict[str, Any]:
    """Withdraw navigation consent and delete every navigation record."""
    workspace = secure_workspace(path)
    normalize_timestamp(timestamp)
    with workspace_lock(workspace):
        learner = _validate_workspace_state(workspace, require_active=False)
        _require_v2(learner)
        if "navigation" not in learner["consent"]["scope"]:
            raise ValidationError("navigation is not in the consent scope")
        removed = len(load_navigation(workspace))
        updated = json.loads(json.dumps(learner))
        updated["consent"]["scope"] = [s for s in learner["consent"]["scope"] if s != "navigation"]
        updated["consent"].pop("navigation_granted_at", None)
        atomic_write_json(workspace / "state" / "learner.json", updated)
        log = workspace / "state" / "navigation.jsonl"
        if log.exists():
            os.unlink(log)
    return {"status": "navigation_revoked", "deleted_records": removed}


def append_navigation(path: str, record: dict[str, Any]) -> dict[str, Any]:
    workspace = secure_workspace(path)
    validate_navigation_record(record)
    with workspace_lock(workspace):
        learner = _validate_workspace_state(workspace)
        _require_v2(learner)
        if "navigation" not in learner["consent"]["scope"]:
            raise ConsentRequired("navigation is outside the consent scope; ask before recording it")
        existing = load_navigation(workspace)
        if any(r["event_id"] == record["event_id"] for r in existing):
            raise ValidationError("this exact navigation record is already present")
        from .io import append_jsonl
        append_jsonl(workspace, NAVIGATION_LOG, record)
    return {"status": "navigation_recorded", "event_id": record["event_id"]}


# ---------------------------------------------------------------- evidence

def make_evidence(*, session_id: str, concept_id: str, observed: str, gap: str, next_action: str,
                  timestamp: str, independent: bool = True) -> dict[str, Any]:
    body = {"concept_id": concept_id, "event_type": "evidence", "gap": gap, "independent": independent,
            "next_action": next_action, "observed": observed, "schema_version": RECORD_SCHEMA_V2,
            "session_id": session_id, "timestamp": normalize_timestamp(timestamp)}
    return validate_event({**body, "event_id": _event_id(body)})


def append_evidence(path: str, record: dict[str, Any]) -> dict[str, Any]:
    workspace = secure_workspace(path)
    validate_event(record)
    if record["event_type"] != "evidence":
        raise ValidationError("append_evidence takes evidence records only")
    with workspace_lock(workspace):
        learner = _validate_workspace_state(workspace)
        _require_v2(learner)
        events = load_events(workspace)
        if any(e["event_id"] == record["event_id"] for e in events):
            raise ValidationError("this exact evidence record is already present")
        updated = [*events, record]
        validate_event_sequence(updated)
        validate_event_source_resolution(updated, load_source_library(workspace))
        _commit_event_sequence_locked(workspace, updated)
    return {"status": "evidence_recorded", "event_id": record["event_id"]}


# ---------------------------------------------------------------- snapshot, migrate, rollback

def _state_files(workspace: Path) -> list[str]:
    rel = []
    for name in sorted(os.listdir(workspace / "state")):
        p = workspace / "state" / name
        if name.startswith(".") or p.is_symlink() or not p.is_file():
            continue
        rel.append(f"state/{name}")
    rel += [f for f in SNAPSHOT_FILES if (workspace / f).is_file()]
    return rel


def _manifest_digest(files: dict[str, str]) -> str:
    return hashlib.sha256(canonical_json_bytes(files)).hexdigest()


def snapshot(path: str, dest: str) -> dict[str, Any]:
    """Copy the learner state (every file under state/, MISSION.md, RESOURCES.md) to `dest`, a new
    directory outside the workspace, with a manifest of sha256 per file and the event counts."""
    workspace = secure_workspace(path)
    target = Path(dest).resolve()
    if target.exists():
        raise SafetyError(f"snapshot destination already exists: {target}")
    if target == workspace or workspace in target.parents:
        raise SafetyError("snapshot must live outside the learner workspace")
    with workspace_lock(workspace):
        learner = _validate_workspace_state(workspace, require_active=False)
        files: dict[str, str] = {}
        target.parent.mkdir(parents=True, exist_ok=True)
        make_private_directory(target)
        make_private_directory(target / "state")
        for rel in _state_files(workspace):
            data = read_bytes(workspace, rel)
            make_private_file(target / rel, data)
            files[rel] = hashlib.sha256(data).hexdigest()
        counts = {"sessions": len(load_events(workspace)), "reviews": len(read_jsonl(workspace, "state/reviews.jsonl")),
                  "navigation": len(load_navigation(workspace))}
        manifest = {"learner_id": learner["learner_id"], "schema_version": learner["schema_version"], "files": files,
                    "counts": counts, "files_sha256": _manifest_digest(files)}
        make_private_file(target / SNAPSHOT_MANIFEST, canonical_json_bytes(manifest))
    return {"snapshot": str(target), **manifest}


def _load_snapshot(snap: Path) -> dict[str, Any]:
    manifest = json.loads((snap / SNAPSHOT_MANIFEST).read_bytes())
    files = manifest.get("files")
    if not isinstance(files, dict) or _manifest_digest(files) != manifest.get("files_sha256"):
        raise SafetyError("snapshot manifest does not match its own digest")
    for rel, digest in files.items():
        if rel.startswith("/") or ".." in Path(rel).parts:
            raise SafetyError(f"snapshot path escapes: {rel}")
        p = snap / rel
        if p.is_symlink() or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            raise SafetyError(f"snapshot file is missing or changed: {rel}")
    return manifest


def migrate(path: str, *, migrated_at: str, snapshot_dest: str) -> dict[str, Any]:
    """Schema 1 -> 2. Snapshots first, then rewrites learner.json only: every v1 record keeps its bytes."""
    workspace = secure_workspace(path)
    when = normalize_timestamp(migrated_at)
    with workspace_lock(workspace):
        learner = _validate_workspace_state(workspace)
        if learner["schema_version"] != "1":
            raise ValidationError("workspace is already schema 2")
        events = load_events(workspace)
        concepts, misconceptions = project_events(events)
        if read_json(workspace, "state/concepts.json") != concepts or \
                read_json(workspace, "state/misconceptions.json") != misconceptions:
            raise ValidationError("stored projections are stale; rebuild before migrating")
    snap = snapshot(path, snapshot_dest)
    with workspace_lock(workspace):
        learner = _validate_workspace_state(workspace)
        if learner["schema_version"] != "1":
            raise ValidationError("workspace changed schema during migration")
        current = {rel: hashlib.sha256(read_bytes(workspace, rel)).hexdigest() for rel in snap["files"]}
        if current != snap["files"]:
            raise SafetyError("workspace changed between snapshot and migration; nothing was migrated")
        updated = json.loads(json.dumps(learner))
        updated["schema_version"] = WORKSPACE_SCHEMA
        updated["migration"] = {"from": "1", "migrated_at": when, "snapshot_sha256": snap["files_sha256"],
                                "v1_event_count": snap["counts"]["sessions"]}
        from .state import validate_learner_document
        validate_learner_document(updated)
        atomic_write_json(workspace / "state" / "learner.json", updated)
    return {"status": "migrated", "from": "1", "to": WORKSPACE_SCHEMA, "snapshot": snap["snapshot"],
            "snapshot_sha256": snap["files_sha256"], "v1_event_count": snap["counts"]["sessions"]}


def rollback(path: str, snapshot_dir: str, dry_run: bool = False) -> dict[str, Any]:
    """Restore a snapshot byte for byte. Events, reviews and navigation recorded after the snapshot are
    lost; the result counts them (`lost_events`) so the caller can print the number.
    dry_run: validate and count only; no state file is written."""
    workspace = secure_workspace(path)
    snap = Path(snapshot_dir).resolve()
    manifest = _load_snapshot(snap)
    with workspace_lock(workspace):
        learner = _validate_workspace_state(workspace, require_active=False)
        if learner["learner_id"] != manifest["learner_id"]:
            raise SafetyError("snapshot belongs to another learner")
        snap_events = {json.loads(ln)["event_id"] for ln in (snap / "state" / "sessions.jsonl").read_bytes().splitlines()
                       if ln.strip()}
        snap_reviews = {json.loads(ln)["event_id"] for ln in (snap / "state" / "reviews.jsonl").read_bytes().splitlines()
                        if ln.strip()}
        now_events = load_events(workspace)
        now_reviews = read_jsonl(workspace, "state/reviews.jsonl")
        now_nav = load_navigation(workspace)
        lost = {"sessions": sum(1 for e in now_events if e["event_id"] not in snap_events),
                "reviews": sum(1 for r in now_reviews if r["event_id"] not in snap_reviews),
                "navigation": len(now_nav) if "state/navigation.jsonl" not in manifest["files"] else 0}
        if dry_run:
            return {"status": "dry_run", "schema_version": manifest["schema_version"],
                    "would_restore": sorted(manifest["files"]), "lost": lost, "lost_events": sum(lost.values())}
        restored = []
        for rel in manifest["files"]:
            atomic_write(workspace / rel, (snap / rel).read_bytes())
            restored.append(rel)
        for rel in _state_files(workspace):
            if rel.startswith("state/") and rel not in manifest["files"]:
                os.unlink(workspace / rel)
                restored.append(f"removed {rel}")
        _validate_workspace_state(workspace, require_active=False)
    return {"status": "rolled_back", "schema_version": manifest["schema_version"], "restored": restored,
            "lost": lost, "lost_events": sum(lost.values())}
