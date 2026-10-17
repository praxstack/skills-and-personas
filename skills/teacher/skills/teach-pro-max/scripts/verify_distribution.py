#!/usr/bin/env python3
"""Verify that the embedded teaching engine matches its committed manifest."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "references" / "prax-teach-v2"
MANIFEST = ROOT / "references" / "ENGINE-MANIFEST.json"
CACHE_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache", ".venv", "node_modules"}
CONTROL_DIRS = {".agent", ".agents", "openspec"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    if not MANIFEST.is_file():
        fail(f"missing manifest: {MANIFEST}")
    if not ENGINE.is_dir() or ENGINE.is_symlink():
        fail(f"embedded engine is missing or unsafe: {ENGINE}")

    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "teach-pro-max.engine-manifest/v1":
        fail("unsupported manifest schema")
    entries = payload.get("files")
    if not isinstance(entries, list) or not entries:
        fail("manifest files must be a non-empty list")

    expected: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            fail("manifest entry must be an object")
        relative = entry.get("path")
        expected_hash = entry.get("sha256")
        if not isinstance(relative, str) or not relative or relative.startswith("/"):
            fail(f"unsafe manifest path: {relative!r}")
        path = ENGINE / relative
        try:
            path.resolve().relative_to(ENGINE.resolve())
        except ValueError:
            fail(f"manifest path escapes the engine: {relative}")
        if relative in expected:
            fail(f"duplicate manifest path: {relative}")
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            fail(f"invalid hash for {relative}")
        expected[relative] = expected_hash

    actual: dict[str, Path] = {}
    for path in ENGINE.rglob("*"):
        relative = path.relative_to(ENGINE)
        if any(part in CACHE_DIRS | CONTROL_DIRS for part in relative.parts):
            continue
        if path.is_symlink():
            fail(f"symlink is not allowed in embedded engine: {path}")
        if path.is_file():
            actual[relative.as_posix()] = path

    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    mismatched = sorted(
        relative
        for relative in set(expected) & set(actual)
        if sha256(actual[relative]) != expected[relative]
    )
    if missing or extra or mismatched:
        fail(
            "engine drift detected: "
            f"missing={missing[:8]}, extra={extra[:8]}, mismatched={mismatched[:8]}"
        )

    wrapper = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    embedded = (ENGINE / "SKILL.md").read_text(encoding="utf-8")
    if "\nname: teach-pro-max\n" not in wrapper:
        fail("wrapper skill name is not teach-pro-max")
    if "\nname: prax-teach-v2\n" not in embedded:
        fail("embedded engine identity changed unexpectedly")

    print(
        "PASS: teach-pro-max wrapper and "
        f"{len(actual)} embedded engine files match {payload['source']['git_head']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
