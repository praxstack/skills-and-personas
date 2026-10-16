#!/usr/bin/env python3
"""Deterministic public agent-process fixture for evaluator machinery tests."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

request = json.load(sys.stdin)
prompt = request["prompt"]
skill_visible = bool(os.environ.get("PRAX_EVAL_SKILL"))

if "MALICIOUS_PATH_ESCAPE" in prompt:
    artifact = "../escape.txt"
    response = "Attempted an invalid artifact path."
elif "MALICIOUS_PERSIST" in prompt:
    Path("learner-state.json").write_text("silent", encoding="utf-8")
    artifact = "answer.md"
    response = "Compared cases, requested an attempt, then explained the rule."
    Path(artifact).write_text(response, encoding="utf-8")
elif "[POSITIVE]" in prompt and skill_visible:
    artifact = "answer.md"
    response = "Compared cases, requested an attempt, then explained the rule."
    Path(artifact).write_text(response, encoding="utf-8")
else:
    artifact = "answer.md"
    response = "Here is a concise direct answer."
    Path(artifact).write_text(response, encoding="utf-8")

json.dump(
    {
        "artifacts": [artifact],
        "response": response,
        "sources": ["fixture-primary-source"],
        "token_usage": {"input": 100, "output": 40},
    },
    sys.stdout,
    separators=(",", ":"),
    sort_keys=True,
)
sys.stdout.write("\n")
