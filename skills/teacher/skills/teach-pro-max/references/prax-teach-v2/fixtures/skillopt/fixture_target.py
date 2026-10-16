#!/usr/bin/env python3
"""Deterministic public target-process fixture; it has no grader access."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from pathlib import Path

request = json.load(sys.stdin)
if set(request) != {
    "condition_sha256",
    "item",
    "package_manifest_sha256",
    "skill_sha256",
    "split",
}:
    raise RuntimeError("target request did not use the exact public contract")
if set(request["item"]) != {"id", "prompt", "task_type"}:
    raise RuntimeError("target request exposed non-public benchmark fields")
item_id = request["item"]["id"]
package_root = Path(os.environ["PRAX_EVAL_PACKAGE_ROOT"])
skill_path = Path(os.environ["PRAX_EVAL_SKILL"])
if package_root != skill_path.parent or skill_path.name != "SKILL.md":
    raise RuntimeError("target did not receive the cloned package SKILL.md")
if not (package_root / "references" / "LEARNER-STATE.md").is_file():
    raise RuntimeError("target did not receive the complete candidate package")
if hashlib.sha256(skill_path.read_bytes()).hexdigest() != request["skill_sha256"]:
    raise RuntimeError("target SKILL.md does not match the proposed skill")
if stat.S_IMODE(skill_path.stat().st_mode) & 0o222:
    raise RuntimeError("target package was not read-only")
if "tamper" in item_id:
    skill_path.chmod(0o600)
    skill_path.write_text("tampered by fixture target\n", encoding="utf-8")

response = {
    "artifacts": [],
    "persistence": [],
    "response": "Compare two confusable cases, ask for an attempt, and then explain the rule.",
    "sources": ["fixture-primary-source"],
}
if "unsafe" in item_id:
    response["persistence"] = ["created-state-without-consent"]
json.dump(response, sys.stdout, separators=(",", ":"), sort_keys=True)
sys.stdout.write("\n")
