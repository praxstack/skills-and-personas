"""Security boundary for course manifests and their local input files."""

from __future__ import annotations

import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path


SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")


@dataclass(frozen=True)
class ValidatedCourse:
    root: Path
    data: dict
    shared: tuple[Path, ...]
    lessons: dict[str, Path]


def safe_id(value: object, label: str) -> str:
    text = str(value) if value is not None else ""
    if not SAFE_ID.fullmatch(text):
        raise ValueError(f"{label} must use only letters, digits, dash, and underscore")
    return text


def _no_link_components(root: Path, candidate: Path) -> None:
    rel = candidate.relative_to(root)
    current = root
    for part in rel.parts:
        current /= part
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise ValueError(f"course input must not contain links: {rel}")


def confined_file(root: Path, relative: object, label: str, suffixes: tuple[str, ...] = ()) -> Path:
    if not isinstance(relative, str) or not relative or "\x00" in relative:
        raise ValueError(f"{label} must be a non-empty relative path")
    logical = Path(relative)
    if logical.is_absolute():
        raise ValueError(f"{label} must be relative to the course")
    root = root.resolve(strict=True)
    candidate = root / logical
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, RuntimeError, ValueError):
        raise ValueError(f"{label} escapes the course or does not exist: {relative}")
    _no_link_components(root, candidate)
    info = resolved.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError(f"{label} must be one regular, unlinked file: {relative}")
    if hasattr(os, "getuid") and info.st_uid != os.getuid():
        raise ValueError(f"{label} is owned by another user: {relative}")
    if suffixes and not any(resolved.name.endswith(suffix) for suffix in suffixes):
        raise ValueError(f"{label} has an unsupported file type: {relative}")
    return resolved


def optional_confined_file(root: Path, relative: Path, label: str) -> Path | None:
    logical = root / relative
    if not logical.exists() and not logical.is_symlink():
        return None
    return confined_file(root, relative.as_posix(), label)


def validate_course_manifest(course_dir: Path) -> ValidatedCourse:
    root = course_dir.resolve(strict=True)
    manifest = confined_file(root, "course.json", "course manifest", (".json",))
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("course manifest must be an object")
    course_id = safe_id(data.get("id"), "course id")
    shared_raw = data.get("shared", [])
    lessons_raw = data.get("lessons")
    if not isinstance(shared_raw, list) or not all(isinstance(item, str) for item in shared_raw):
        raise ValueError("course shared must be an array of paths")
    if not isinstance(lessons_raw, list) or not lessons_raw:
        raise ValueError("course lessons must be a non-empty array")

    shared = tuple(confined_file(root, item, "shared file", (".js",)) for item in shared_raw)
    lessons: dict[str, Path] = {}
    for row in lessons_raw:
        if not isinstance(row, dict):
            raise ValueError("every lesson must be an object")
        lesson_id = safe_id(row.get("id"), f"lesson id in {course_id}")
        if lesson_id in lessons:
            raise ValueError(f"duplicate lesson id: {lesson_id}")
        lessons[lesson_id] = confined_file(root, row.get("file"), f"lesson file {lesson_id}", (".lesson.js", ".anim.js"))
    return ValidatedCourse(root=root, data=data, shared=shared, lessons=lessons)
