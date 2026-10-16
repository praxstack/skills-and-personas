#!/usr/bin/env python3
"""Fail-closed local checks for the zero-API visual runtime."""

from __future__ import annotations

import argparse
import glob
import json
import re
import subprocess
import sys
from pathlib import Path

from praxteach.io import anchored_file_target, atomic_write_anchored
from praxteach.routing import runtime_artifacts_valid, runtime_bindings

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime" / "prax-visual-lab"
REMOTE = re.compile(
    r"https?://|wss?://|(?:fetch|XMLHttpRequest|WebSocket|sendBeacon)\s*\(",
    re.IGNORECASE,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "evidence" / "zero-api-visual-runtime" / "verification.json",
    )
    args = parser.parse_args()
    files = sorted(path for path in (RUNTIME / "src").rglob("*") if path.is_file())
    errors: list[str] = []
    network_errors: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        if REMOTE.search(text):
            network_errors.append(
                f"forbidden network reference: {path.relative_to(ROOT)}"
            )
    errors.extend(network_errors)
    if not (RUNTIME / "src" / "index.html").exists():
        errors.append("static fallback missing")
    if not (RUNTIME / "src" / "index.mjs").exists():
        errors.append("runtime entry missing")
    build = subprocess.run(
        ["node", "build.mjs"],
        cwd=RUNTIME,
        text=True,
        capture_output=True,
        check=False,
    )
    if build.returncode:
        errors.append(build.stdout + build.stderr)
    test_files = sorted(glob.glob("tests/*.test.mjs", root_dir=RUNTIME))
    completed = subprocess.run(
        ["node", "--test", *test_files],
        cwd=RUNTIME,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        errors.append(completed.stdout + completed.stderr)
    if not runtime_artifacts_valid(ROOT):
        errors.append("runtime source, dist, and manifest are not exact-byte peers")
    try:
        bindings = runtime_bindings(ROOT)
    except OSError as exc:
        bindings = {}
        errors.append(f"runtime binding failed: {exc}")
    result = {
        "schema_version": "prax.zero-api-runtime-verification/v1",
        "status": "passed" if not errors else "failed",
        "source_file_count": len(files),
        "shape_digest": bindings.get("source", {}).get("sha256", ""),
        "network_scan": "passed" if not network_errors else "failed",
        "bindings": bindings,
        "external_human_learning_gates_satisfied": False,
        "limitations": [
            "Automated checks do not establish field accessibility or learning outcomes."
        ],
        "errors": errors,
    }
    encoded = (json.dumps(result, indent=2) + "\n").encode("utf-8")
    with anchored_file_target(args.output) as target:
        atomic_write_anchored(target, encoded, mode=0o644)
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
