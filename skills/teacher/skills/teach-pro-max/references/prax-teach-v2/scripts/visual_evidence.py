#!/usr/bin/env python3
"""Validate a learner-controlled receipt without inferring mastery."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    document = json.loads(args.receipt.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "lesson_id",
        "lesson_version",
        "actions",
        "attempts",
        "highest_hint_level",
        "observations",
        "learner_authored",
        "created_at",
    }
    missing = (
        sorted(required.difference(document))
        if isinstance(document, dict)
        else sorted(required)
    )
    result = {
        "schema_version": "prax.visual-evidence/v1",
        "status": "valid" if not missing else "invalid",
        "receipt_sha256": hashlib.sha256(args.receipt.read_bytes()).hexdigest(),
        "missing": missing,
        "evidence_level": "learner-authored-local-observation",
        "claim_boundary": "This receipt records actions and observations; it does not infer mastery, retention, accessibility, or transfer.",
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
