#!/usr/bin/env python3
"""Report optional SkillOpt and Flint availability without installing anything."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path


def module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def command_path(name: str) -> str | None:
    return shutil.which(name)


def node_package_available(name: str, cwd: Path) -> bool:
    node = command_path("node")
    if not node:
        return False
    source = (
        f"import({json.dumps(name)}).then(() => process.exit(0))"
        ".catch(() => process.exit(1))"
    )
    try:
        completed = subprocess.run(
            [node, "--input-type=module", "-e", source],
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    args = parser.parse_args()
    project = args.project.expanduser().resolve()

    report = {
        "status": "optional_only",
        "project": str(project),
        "skillopt": {
            "python_module": module_available("skillopt"),
            "sleep_module": module_available("skillopt_sleep"),
            "train_command": command_path("skillopt-train"),
            "eval_command": command_path("skillopt-eval"),
            "sleep_command": command_path("skillopt-sleep"),
        },
        "flint": {
            "node_command": command_path("node"),
            "library_importable": node_package_available("flint-chart", project),
            "mcp_command": command_path("flint-chart-mcp"),
        },
    }

    if args.as_json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    print("Optional integration availability")
    print(f"- SkillOpt Python module: {report['skillopt']['python_module']}")
    print(f"- SkillOpt-Sleep module: {report['skillopt']['sleep_module']}")
    print(f"- Flint library importable: {report['flint']['library_importable']}")
    print(f"- Flint MCP command: {report['flint']['mcp_command'] or 'not found'}")
    print("No packages were installed or changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
