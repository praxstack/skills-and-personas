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


def safe_lesson_id(value: object, label: str = "lesson id") -> str:
    text = safe_id(value, label)
    if text.casefold() == "index":
        raise ValueError(f"{label} {text!r} is reserved for the course landing page")
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
        lesson_id = safe_lesson_id(row.get("id"), f"lesson id in {course_id}")
        if lesson_id in lessons:
            raise ValueError(f"duplicate lesson id: {lesson_id}")
        lessons[lesson_id] = confined_file(root, row.get("file"), f"lesson file {lesson_id}", (".lesson.js", ".anim.js"))
    return ValidatedCourse(root=root, data=data, shared=shared, lessons=lessons)


def open_directory(root: Path) -> int:
    """Anchor each absolute component, rejecting links at every level."""
    if not root.is_absolute():
        root = Path.cwd() / root
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for part in root.parts[1:]:
            if part in {".", ".."}:
                raise ValueError("directory must be canonical")
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def read_bound_file(root: Path, relative: str, *, limit: int = 64 * 1024 * 1024) -> bytes:
    """Read through no-follow directory descriptors; never reopen a checked path."""
    parts = Path(relative).parts
    if not parts or Path(relative).is_absolute() or any(p in {".", ".."} for p in parts):
        raise ValueError("input must be a confined relative path without dot segments")
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
    directory = open_directory(root)
    try:
        for part in parts[:-1]:
            child = os.open(part, flags | os.O_DIRECTORY, dir_fd=directory)
            os.close(directory)
            directory = child
        fd = os.open(parts[-1], flags | os.O_NONBLOCK, dir_fd=directory)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_uid != os.getuid():
                raise ValueError("input must be an owned regular file with one link")
            if before.st_size > limit:
                raise ValueError("course input exceeds its byte budget")
            chunks, total = [], 0
            while True:
                chunk = os.read(fd, min(1024 * 1024, limit + 1 - total))
                if not chunk:
                    break
                total += len(chunk)
                if total > limit:
                    raise ValueError("course input exceeds its byte budget")
                chunks.append(chunk)
            after = os.fstat(fd)
            if (before.st_size, before.st_mtime_ns, before.st_ctime_ns, before.st_nlink) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns, after.st_nlink):
                raise ValueError("course input changed while being read")
            return b"".join(chunks)
        finally:
            os.close(fd)
    finally:
        os.close(directory)


from contextlib import contextmanager
from functools import wraps
import tempfile


@contextmanager
def snapshot_course(course_dir: Path):
    """All downstream consumers use the same private copy of validated bytes."""
    # Preserve the manifest beside a linked course, as the public builder does.
    base = Path.cwd()
    pwd = os.environ.get("PWD", "")
    if pwd and os.path.isabs(pwd):
        try:
            if os.path.samefile(pwd, base):
                base = Path(pwd)
        except OSError:
            pass
    logical = Path(os.path.abspath(base / course_dir))
    manifest_parent = logical.parent.resolve(strict=True)
    original = course_dir.resolve(strict=True)
    manifest = read_bound_file(original, "course.json")
    with tempfile.TemporaryDirectory(prefix="teacher-course-") as temp:
        root = Path(temp) / "course"
        root.mkdir(mode=0o700)
        (root / "course.json").write_bytes(manifest)
        data = json.loads(manifest)
        safe_id(data.get("id"), "course id")
        inputs = list(data.get("shared", []))
        lessons = data.get("lessons", [])
        if not isinstance(lessons, list) or not lessons:
            raise ValueError("course needs lessons")
        for lesson in lessons:
            ident = safe_lesson_id(lesson.get("id"), "lesson id")
            inputs.append(lesson.get("file"))
            for suffix in ("mp4", "vtt"):
                relative = f"videos/{ident}.{suffix}"
                try:
                    contents = read_bound_file(original, relative, limit=512 * 1024 * 1024)
                except FileNotFoundError:
                    continue
                target = root / relative
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                target.write_bytes(contents)
        for relative in inputs:
            if not isinstance(relative, str) or not relative.endswith((".js",)):
                raise ValueError("course source must be JavaScript")
            contents = read_bound_file(original, relative)
            target = root / relative
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            target.write_bytes(contents)
        try:
            parent_manifest = read_bound_file(manifest_parent, "videos.json")
        except FileNotFoundError:
            pass
        else:
            (root.parent / "videos.json").write_bytes(parent_manifest)
        validate_course_manifest(root)
        yield root


def private_course_inputs(function):
    @wraps(function)
    def wrapped(course_dir, *args, **kwargs):
        with snapshot_course(course_dir) as private:
            return function(private, *args, **kwargs)
    return wrapped


def publish_bound_file(root: Path, name: str, source: Path) -> None:
    """Publish a staged render via an opened output-directory descriptor."""
    import secrets
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,200}", name):
        raise ValueError("unsafe output filename")
    if Path(name).name != name:
        raise ValueError("output name must have no directory components")
    fd = open_directory(root)
    temporary = f".teacher-{secrets.token_hex(16)}"
    try:
        out = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        with os.fdopen(out, "wb") as dest, source.open("rb") as src:
            import shutil
            shutil.copyfileobj(src, dest)
            dest.flush()
            os.fsync(dest.fileno())
        os.replace(temporary, name, src_dir_fd=fd, dst_dir_fd=fd)
    finally:
        try:
            os.unlink(temporary, dir_fd=fd)
        except FileNotFoundError:
            pass
        os.close(fd)


if __name__ == "__main__":
    import sys
    # Used by the direct Node extractor so it never validates then reopens.
    with snapshot_course(Path(sys.argv[1])) as root:
        validated = validate_course_manifest(root)
        print(json.dumps({"course": validated.data,
                          "shared": [p.read_text() for p in validated.shared],
                          "lessons": {k: p.read_text() for k, p in validated.lessons.items()}}))
