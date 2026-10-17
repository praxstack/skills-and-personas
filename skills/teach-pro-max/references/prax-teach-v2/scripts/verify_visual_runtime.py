#!/usr/bin/env python3
"""Fail-closed local checks for the zero-API visual runtime."""

from __future__ import annotations

import argparse
import glob
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

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
        default=None,
    )
    parser.add_argument(
        "--check", action="store_true", help="read-only replay; emit result to stdout"
    )
    parser.add_argument(
        "--route-check", help="bounded caller: resolve a packaged lesson read-only"
    )
    args = parser.parse_args()
    if args.route_check:
        from praxteach.routing import _visual_runtime_check

        print(json.dumps(_visual_runtime_check(args.route_check)))
        return 0
    if args.output is None and not args.check:
        parser.error("choose --check or an external --output")
    if args.output is not None and args.output.absolute().is_relative_to(ROOT):
        parser.error("runtime evidence output must be outside source")
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
    # Runtime tests include a build test. Run the entire closure in staging,
    # never against the published tree. --check only inspects already-built bytes.
    if not args.check:
        with tempfile.TemporaryDirectory(prefix="prax-runtime-replay-") as temporary:
            staged = Path(temporary) / "runtime" / "prax-visual-lab"
            try:
                runtime_bindings(ROOT)  # reject unsafe input trees before copying
                shutil.copytree(RUNTIME, staged)
                shutil.copytree(
                    ROOT / "examples" / "visual-lab",
                    Path(temporary) / "examples" / "visual-lab",
                )
                for command in (
                    ["node", "build.mjs"],
                    [
                        "node",
                        "--test",
                        *sorted(glob.glob("tests/*.test.mjs", root_dir=staged)),
                    ],
                ):
                    completed = subprocess.run(
                        command,
                        cwd=staged,
                        text=True,
                        capture_output=True,
                        check=False,
                        timeout=15,
                    )
                    if completed.returncode:
                        errors.append(completed.stdout + completed.stderr)
                # A successful staged build must produce the exact published bytes.
                from praxteach.routing import _tree_binding

                if _tree_binding(staged / "dist") != _tree_binding(RUNTIME / "dist"):
                    errors.append("staged build differs from published dist")
            except (OSError, subprocess.SubprocessError) as exc:
                errors.append(f"bounded staged replay failed: {exc}")
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
    if args.output is not None:
        with anchored_file_target(args.output) as target:
            atomic_write_anchored(target, encoded, mode=0o644)
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
