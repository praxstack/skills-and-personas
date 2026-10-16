"""Deterministic least-cost teaching-mode routing."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
VISUAL_RUNTIME_ENTRYPOINT = Path("runtime/prax-visual-lab/dist/index.html")
VISUAL_RUNTIME_MANIFEST = Path("runtime/prax-visual-lab/dist/manifest.json")
VISUAL_RUNTIME_RECEIPT = Path("evidence/zero-api-visual-runtime/verification.json")
TREE_BINDING_ALGORITHM = "sha256(canonical-json(files[path,bytes,sha256]))"
VISUAL_RUNTIME_LESSON_BINDINGS = {
    "python-floating-point": (
        r"\bpython[- ]floating[- ]point\b",
        r"\bfloating[- ]point\b",
    ),
}

ANSWER_PATTERNS = (
    r"\banswer\s+now\b",
    r"\bjust\s+(?:give|tell|show)\s+me\b",
    r"\bno\s+(?:more\s+)?(?:questions|socratic)\b",
    r"\bskip\s+(?:the\s+)?(?:questions|lesson|ceremony)\b",
)
DEMOTION_PATTERNS = (
    r"\bkeep\s+it\s+(?:brief|concise|short)\b",
    r"\bquick(?:ly)?\b",
    r"\bin\s+(?:one|two|three|five|\d+)\s+minutes?\b",
)
COURSE_PATTERNS = (
    r"\bcourse\b",
    r"\bcurriculum\b",
    r"\bsyllabus\b",
    r"\b(?:multi|cross)[ -]?session\b",
    r"\bacross\s+sessions\b",
    r"\bresum(?:e|ing)\b",
    r"\bcontinue\s+where\s+we\s+(?:left|stopped)\b",
    r"\b(?:two|three|four|five|six|seven|eight|nine|ten|\d+)[ -]weeks?\b",
    r"\bover\s+(?:the\s+next\s+)?(?:week|weeks|month|months)\b",
)
LESSON_PATTERNS = (
    r"\blesson\b",
    r"\bguided\s+practice\b",
    r"\binteractive\s+(?:lesson|tutorial)\b",
    r"\bteach\s+me\s+to\s+(?:do|build|solve|apply)\b",
    r"\bteach\s+me\b.*\b(?:practic(?:al|ally)|debug|modify|transfer|executable)\b",
    r"\btransfer\s+(?:task|practice|exercise)\b",
    r"\btransfer\b.*\b(?:attempt|answer|case|exercise|practice|task)\b",
    r"\bwalk\s+me\s+through\b",
)
ORDINARY_TASK_PATTERNS = (
    r"^(?:(?:please|quickly)\s+)*(?:add|apply|build|change|create|delete|deploy|edit|fix|implement|install|migrate|patch|refactor|remove|rename|run|ship|update|write)\b",
    r"^(?:can|could|would|will)\s+you\s+(?:please\s+)?(?:quickly\s+)?(?:add|apply|build|change|create|delete|deploy|edit|fix|implement|install|migrate|patch|refactor|remove|rename|run|ship|update|write)\b",
    r"\b(?:do|complete|perform)\s+(?:this|the)\s+(?:task|change|work)\b",
)
ENGINEERING_CONTEXT_PATTERNS = (
    r"\b(?:api|bug|cli|code|codebase|command|component|database|file|function|implementation|library|method|migration|module|package|parser|pipeline|renderer|repository|repo|router|routing|scheduler|schema|script|sdk|server|test|tests|tool|type)\b",
    r"\b(?:python|typescript|javascript|swift|rust|go|java|json|yaml|sql)\b",
)
EXPLICIT_TEACHING_INTENT_PATTERNS = (
    r"\bteach\s+me\b",
    r"\bhelp\s+me\s+(?:learn|understand|practice)\b",
    r"\bquiz\s+me\b",
    r"\btutor\s+me\b",
    r"\bi\s+want\s+to\s+learn\b",
    r"\b(?:build|create|make)\s+me\s+(?:(?:a|an|the)\s+)?(?:[\w-]+\s+){0,3}course\b",
)
INTERACTIVE_VISUAL_PATTERNS = (
    r"\bmanipulat(?:e|ion)\b",
    r"\b(?:change|adjust|drag|filter|traverse|scrub|test)\b.*\b(?:value|parameter|state|path|model|result|probe|case)\b",
    r"\bsimulator\b",
    r"\bwhat[- ]if\b",
)
MOTION_VISUAL_PATTERNS = (
    r"\bwatch\b.*\b(?:change|interleave|transform|move|accumulate|synchroni[sz]e)\b",
    r"\b(?:over time|interleav|synchroni[sz]|animation|animate|causal sequence)\b",
)
STATIC_VISUAL_PATTERNS = (
    r"\b(?:compare|comparison|distribution|hierarchy|structure|architecture|diagram|graph|chart|map)\b",
    r"\b(?:show|visuali[sz]e)\b.*\b(?:state|relationship|flow|steps?|layout)\b",
    r"\bsmall multiples\b",
)


def _matches(patterns: tuple[str, ...], request: str) -> bool:
    return any(re.search(pattern, request, flags=re.IGNORECASE) for pattern in patterns)


def _runtime_lesson_binding(job: str) -> str | None:
    for lesson_id, patterns in VISUAL_RUNTIME_LESSON_BINDINGS.items():
        if _matches(patterns, job):
            return lesson_id
    return None


def _assert_no_symlink_components(root: Path, *paths: Path) -> None:
    root = root.absolute()
    root_stat = root.lstat()
    if stat.S_ISLNK(root_stat.st_mode):
        raise OSError(f"runtime binding refuses symlink root: {root}")
    anchor = Path(root.anchor)
    ancestor = root.parent
    while ancestor != anchor:
        ancestor_stat = ancestor.lstat()
        if stat.S_ISLNK(ancestor_stat.st_mode):
            trusted_root_alias = (
                ancestor.parent == anchor
                and ancestor_stat.st_uid == 0
                and anchor.stat().st_uid == 0
                and not stat.S_IMODE(anchor.stat().st_mode) & 0o022
            )
            if not trusted_root_alias:
                raise OSError(
                    f"runtime binding refuses symlink root ancestor: {ancestor}"
                )
        ancestor = ancestor.parent
    for path in paths:
        candidate = path.absolute()
        try:
            relative = candidate.relative_to(root)
        except ValueError as exc:
            raise OSError(f"runtime binding path escapes root: {candidate}") from exc
        current = root
        for component in relative.parts:
            current /= component
            component_stat = current.lstat()
            if stat.S_ISLNK(component_stat.st_mode):
                raise OSError(
                    f"runtime binding refuses symlink path component: {current}"
                )


def _file_records(directory: Path) -> list[dict[str, str | int]]:
    directory_stat = directory.lstat()
    if stat.S_ISLNK(directory_stat.st_mode) or not stat.S_ISDIR(directory_stat.st_mode):
        raise OSError(f"runtime binding directory is not a real directory: {directory}")
    records: list[dict[str, str | int]] = []
    for path in sorted(directory.rglob("*")):
        path_stat = path.lstat()
        if stat.S_ISLNK(path_stat.st_mode):
            raise OSError(f"runtime binding refuses symlink: {path}")
        if stat.S_ISDIR(path_stat.st_mode):
            continue
        if not stat.S_ISREG(path_stat.st_mode):
            raise OSError(f"runtime binding refuses non-regular file: {path}")
        payload = _regular_file_bytes(path, path_stat)
        records.append(
            {
                "path": path.relative_to(directory).as_posix(),
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    return records


def _regular_file_bytes(path: Path, expected: os.stat_result | None = None) -> bytes:
    """Read one stable regular-file generation without following a symlink."""

    before = expected or path.lstat()
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise OSError(f"runtime binding refuses non-regular file: {path}")
    descriptor = os.open(
        path,
        os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0),
    )
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (
            before.st_dev,
            before.st_ino,
        ):
            raise OSError(f"runtime binding file changed while opening: {path}")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        after = path.lstat()
        if stat.S_ISLNK(after.st_mode) or (after.st_dev, after.st_ino) != (
            opened.st_dev,
            opened.st_ino,
        ):
            raise OSError(f"runtime binding file changed while reading: {path}")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _tree_binding(directory: Path) -> dict[str, str | int]:
    records = _file_records(directory)
    encoded = json.dumps(
        records, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode()
    return {
        "algorithm": TREE_BINDING_ALGORITHM,
        "file_count": len(records),
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }


def _file_binding(path: Path, root: Path) -> dict[str, str | int]:
    payload = _regular_file_bytes(path)
    return {
        "algorithm": "sha256",
        "path": path.relative_to(root).as_posix(),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def runtime_bindings(root: Path) -> dict[str, dict[str, str | int]]:
    """Bind every byte that establishes packaged-runtime verification."""

    runtime = root / "runtime" / "prax-visual-lab"
    _assert_no_symlink_components(
        root,
        runtime,
        runtime / "src",
        runtime / "dist",
        runtime / "dist" / "manifest.json",
        runtime / "tests",
        runtime / "contracts",
        runtime / "build.mjs",
        root / "scripts" / "praxteach" / "routing.py",
        root / "scripts" / "verify_visual_runtime.py",
    )
    return {
        "source": _tree_binding(runtime / "src"),
        "dist": _tree_binding(runtime / "dist"),
        "manifest": _file_binding(runtime / "dist" / "manifest.json", root),
        "tests": _tree_binding(runtime / "tests"),
        "contracts": _tree_binding(runtime / "contracts"),
        "build": _file_binding(runtime / "build.mjs", root),
        "routing": _file_binding(root / "scripts" / "praxteach" / "routing.py", root),
        "verifier": _file_binding(root / "scripts" / "verify_visual_runtime.py", root),
    }


def runtime_artifacts_valid(root: Path) -> bool:
    """Check that the built manifest and distributable bytes match source."""

    runtime = root / "runtime" / "prax-visual-lab"
    try:
        _assert_no_symlink_components(
            root,
            runtime,
            runtime / "src",
            runtime / "dist",
            runtime / "dist" / "manifest.json",
        )
        source = _file_records(runtime / "src")
        manifest_path = runtime / "dist" / "manifest.json"
        manifest = json.loads(_regular_file_bytes(manifest_path).decode("utf-8"))
        dist = _file_records(runtime / "dist")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    expected_source_sha256 = hashlib.sha256(
        "".join(
            f"{record['path']}:{record['sha256']}:{record['bytes']}\n"
            for record in source
        ).encode()
    ).hexdigest()
    if (
        manifest.get("schema_version") != "prax.visual-manifest/v1"
        or not isinstance(manifest.get("runtime_version"), str)
        or manifest.get("files") != source
        or manifest.get("source_sha256") != expected_source_sha256
    ):
        return False
    dist_by_path = {record["path"]: record for record in dist}
    if set(dist_by_path) != {record["path"] for record in source} | {"manifest.json"}:
        return False
    return all(dist_by_path[record["path"]] == record for record in source)


def _replay_runtime_verification(root: Path) -> dict[str, Any] | None:
    verifier = root / "scripts" / "verify_visual_runtime.py"
    try:
        _assert_no_symlink_components(root, verifier)
    except OSError:
        return None
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / "verification.json"
        try:
            completed = subprocess.run(
                [sys.executable, str(verifier), "--output", str(output)],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
            result = json.loads(_regular_file_bytes(output).decode("utf-8"))
        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            subprocess.SubprocessError,
        ):
            return None
    if not isinstance(result, dict) or completed.returncode not in {0, 1}:
        return None
    return result


def _visual_runtime(lesson_id: str | None = None) -> dict[str, str] | None:
    """Return a bound runtime only after replaying current verification bytes."""

    if lesson_id not in VISUAL_RUNTIME_LESSON_BINDINGS:
        return None

    try:
        _assert_no_symlink_components(
            ROOT,
            ROOT / VISUAL_RUNTIME_ENTRYPOINT,
            ROOT / VISUAL_RUNTIME_MANIFEST,
            ROOT / VISUAL_RUNTIME_RECEIPT,
        )
        _regular_file_bytes(ROOT / VISUAL_RUNTIME_ENTRYPOINT)
        manifest = json.loads(
            _regular_file_bytes(ROOT / VISUAL_RUNTIME_MANIFEST).decode("utf-8")
        )
        receipt = json.loads(
            _regular_file_bytes(ROOT / VISUAL_RUNTIME_RECEIPT).decode("utf-8")
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not runtime_artifacts_valid(ROOT):
        return None
    verification = _replay_runtime_verification(ROOT)
    if verification is None:
        return None
    if not isinstance(manifest, dict) or not isinstance(receipt, dict):
        return None
    try:
        current_bindings = runtime_bindings(ROOT)
    except OSError:
        return None
    security_fields = (
        "schema_version",
        "status",
        "network_scan",
        "external_human_learning_gates_satisfied",
        "errors",
        "bindings",
    )
    if (
        any(receipt.get(field) != verification.get(field) for field in security_fields)
        or verification.get("status") != "passed"
        or verification.get("network_scan") != "passed"
        or verification.get("external_human_learning_gates_satisfied") is not False
        or verification.get("errors") != []
        or verification.get("bindings") != current_bindings
        or manifest.get("schema_version") != "prax.visual-manifest/v1"
        or not isinstance(manifest.get("runtime_version"), str)
    ):
        return None
    return {
        "id": "prax-visual-lab",
        "version": manifest["runtime_version"],
        "lesson_id": lesson_id,
        "entrypoint": VISUAL_RUNTIME_ENTRYPOINT.as_posix(),
        "manifest": VISUAL_RUNTIME_MANIFEST.as_posix(),
        "verification_receipt": VISUAL_RUNTIME_RECEIPT.as_posix(),
    }


def route_request(
    request: str,
    *,
    answer_now: bool = False,
    demote: bool = False,
    explicit_mode: str | None = None,
) -> dict[str, Any]:
    """Choose the lightest sufficient route with explicit overrides first."""

    normalized = " ".join(request.split())
    if not normalized:
        raise ValueError("request must not be empty")

    if answer_now or _matches(ANSWER_PATTERNS, normalized):
        return {
            "action": "answer_now",
            "mode": "quick",
            "persistence": False,
            "reason": "Explicit Answer-now override; stop questioning and respond directly.",
        }
    if demote:
        return {
            "action": "teach",
            "mode": "quick",
            "persistence": False,
            "reason": "Explicit demotion override; use the briefest direct teaching route.",
        }
    if explicit_mode:
        persistence: bool | str = (
            "consent_required" if explicit_mode == "course" else False
        )
        return {
            "action": "teach",
            "mode": explicit_mode,
            "persistence": persistence,
            "reason": f"Explicit {explicit_mode} mode request.",
        }
    if (
        _matches(ORDINARY_TASK_PATTERNS, normalized)
        and _matches(ENGINEERING_CONTEXT_PATTERNS, normalized)
        and not _matches(EXPLICIT_TEACHING_INTENT_PATTERNS, normalized)
    ):
        return {
            "action": "ordinary_task",
            "mode": None,
            "persistence": False,
            "reason": "Engineering context makes course, curriculum, or lesson terminology part of the task target rather than a tutoring request.",
        }
    if _matches(DEMOTION_PATTERNS, normalized):
        return {
            "action": "teach",
            "mode": "quick",
            "persistence": False,
            "reason": "A short time or cognitive-load budget fits one direct explanation.",
        }
    if _matches(COURSE_PATTERNS, normalized):
        return {
            "action": "teach",
            "mode": "course",
            "persistence": "consent_required",
            "reason": "Explicit multi-session, course, or resume intent requires durable continuity.",
        }
    if _matches(LESSON_PATTERNS, normalized):
        return {
            "action": "teach",
            "mode": "lesson",
            "persistence": False,
            "reason": "Guided practice or transfer needs a bounded lesson sequence.",
        }
    if _matches(ORDINARY_TASK_PATTERNS, normalized):
        return {
            "action": "ordinary_task",
            "mode": None,
            "persistence": False,
            "reason": "The request asks for task completion rather than teaching; do not trigger the tutoring system.",
        }
    return {
        "action": "teach",
        "mode": "quick",
        "persistence": False,
        "reason": "One direct response can plausibly satisfy the request; no course is forced.",
    }


def route_visual(
    job: str,
    *,
    retrieval: bool = False,
    exact_quantitative: bool = False,
    static_sufficient: bool | None = None,
    force: str | None = None,
) -> dict[str, Any]:
    """Choose the smallest representation that serves an explicit learning job."""

    normalized = " ".join(job.split())
    if not normalized:
        raise ValueError("visual job must not be empty")
    if force is not None and force not in {"none", "static", "interactive", "motion"}:
        raise ValueError("forced visual route is invalid")

    if force is not None:
        route = force
        reason = f"Explicit {force} route override; the caller remains responsible for accuracy and accessibility."
    elif _matches(INTERACTIVE_VISUAL_PATTERNS, normalized):
        route = "interactive"
        reason = "The learner benefits from manipulating or testing the representation."
    elif _matches(MOTION_VISUAL_PATTERNS, normalized):
        if static_sufficient is True:
            route = "static"
            reason = "The sequence is material, but labeled static states communicate it with less overhead."
        else:
            route = "motion"
            reason = "Changing state, order, or synchronization is the concept and static states were not declared sufficient."
    elif exact_quantitative or _matches(STATIC_VISUAL_PATTERNS, normalized):
        route = "static"
        reason = "An exact comparison, structure, or state is clearer in a stable representation."
    else:
        route = "none"
        reason = "Prose plus an example is the smallest sufficient representation for the stated job."

    media = {
        "none": "text and one aligned example",
        "static": "semantic table, exact SVG, or diagram-as-code",
        "interactive": "native controls with a deterministic static state",
        "motion": "learner-controlled sequence with captions and transcript",
    }
    fallbacks = {
        "none": "Prose and a worked example.",
        "static": "Text reading order and a complete semantic data table when quantitative.",
        "interactive": "Equivalent static state, instructions, and explanation with scripts disabled.",
        "motion": "Captions, transcript, poster, and ordered static states with reduced motion.",
    }
    retrieval_safety = {
        "required": bool(retrieval),
        "verification_status": "not_run" if retrieval else "not_applicable",
        "checks_performed": False,
        "required_checks": (
            [
                "attempt_before_reveal",
                "accessible_reveal",
                "fallback_preserves_order",
            ]
            if retrieval
            else []
        ),
        "surfaces_to_check": [
            "visible_labels",
            "alt_text",
            "captions",
            "default_state",
            "poster_frame",
            "source_code",
        ],
    }
    bundled_renderer_supported = route in {"none", "static"}
    lesson_id = (
        _runtime_lesson_binding(normalized)
        if route in {"interactive", "motion"}
        else None
    )
    visual_runtime = _visual_runtime(lesson_id)
    visual_runtime_supported = visual_runtime is not None
    delivery_supported = bundled_renderer_supported or visual_runtime_supported
    delivery_route = route if delivery_supported else "static"
    delivery_reason = (
        "The bundled Markdown renderer can deliver this route directly."
        if bundled_renderer_supported
        else "The packaged, verified Prax Visual Lab can deliver this route directly."
        if visual_runtime_supported
        else "The requested rich route is a learning-job recommendation only; deliver the complete static fallback until a separately versioned, tested, and manually reviewed runtime is available."
    )
    delivery_surface = (
        "bundled-static-artifact"
        if bundled_renderer_supported
        else "prax-visual-lab"
        if visual_runtime_supported
        else "host-chat-plus-static-fallback"
    )
    return {
        "route": route,
        "reason": reason,
        "bundled_renderer_supported": bundled_renderer_supported,
        "visual_runtime_supported": visual_runtime_supported,
        "visual_runtime": visual_runtime,
        "delivery_reason": delivery_reason,
        "delivery_route": delivery_route,
        "delivery_surface": delivery_surface,
        "default_medium": media[delivery_route],
        "fallback": fallbacks[route],
        "flint_eligible": bool(route == "static" and exact_quantitative),
        "flint_required": False,
        "retrieval_safety": retrieval_safety,
        "requested_medium": media[route],
        "runtime_requirement": (
            None
            if delivery_supported
            else "separately-versioned-tested-and-manually-reviewed"
        ),
    }
