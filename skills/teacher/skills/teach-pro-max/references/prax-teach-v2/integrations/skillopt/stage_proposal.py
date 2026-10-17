#!/usr/bin/env python3
"""Quarantine a structurally passing SkillOpt proposal for human review.

The score JSON is deliberately treated as self-attested. This helper verifies
its exact shape and byte bindings, but it is not an authentication authority
and cannot make an optimization, held-out, staging-eligibility, or adoption
claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SCORE_RECEIPT_FIELDS = {
    "base_sha256",
    "condition_sha256",
    "cross_model_passed",
    "eligible_for_staging",
    "hard_gates_passed",
    "hidden_hard_gates_passed",
    "proposal_sha256",
    "repeated_trials",
    "runner_sha256",
    "schema_version",
    "selection_delta",
    "selection_sha256",
    "train_sha256",
}
SCORE_HASH_FIELDS = {
    "base_sha256",
    "condition_sha256",
    "proposal_sha256",
    "runner_sha256",
    "selection_sha256",
    "train_sha256",
}
MINIMUM_REPEATED_TRIALS = 3


class StagingError(RuntimeError):
    """Raised before a proposal can be staged safely."""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise StagingError(f"score receipt repeats field {key!r}")
        value[key] = item
    return value


def _read_skill(path: Path, role: str) -> tuple[bytes, dict[str, str]]:
    path = path.expanduser().resolve(strict=True)
    if not path.is_file() or path.name != "SKILL.md":
        raise StagingError(f"{role} must be a regular file named SKILL.md")
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StagingError(f"{role} must be UTF-8") from exc
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise StagingError(f"{role} requires YAML-like frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise StagingError(f"{role} frontmatter is not closed") from exc
    fields: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise StagingError(f"{role} frontmatter contains an invalid line")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if not key or not value or key in fields:
            raise StagingError(
                f"{role} frontmatter fields must be unique and non-empty"
            )
        fields[key] = value
    name = fields.get("name", "")
    description = fields.get("description", "")
    if not NAME_PATTERN.fullmatch(name):
        raise StagingError(f"{role} has an invalid name field")
    if not description:
        raise StagingError(f"{role} requires a description field")
    if not any(line.strip() for line in lines[end + 1 :]):
        raise StagingError(f"{role} body must not be empty")
    return data, fields


def _read_score(path: Path) -> tuple[bytes, dict[str, Any]]:
    path = path.expanduser().resolve(strict=True)
    if not path.is_file():
        raise StagingError("score receipt must be a regular file")
    data = path.read_bytes()
    try:
        receipt = json.loads(
            data.decode("utf-8"), object_pairs_hook=_unique_json_object
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StagingError("score receipt must be valid UTF-8 JSON") from exc
    if not isinstance(receipt, dict):
        raise StagingError("score receipt must be a JSON object")
    actual_fields = set(receipt)
    if actual_fields != SCORE_RECEIPT_FIELDS:
        missing = sorted(SCORE_RECEIPT_FIELDS - actual_fields)
        unexpected = sorted(actual_fields - SCORE_RECEIPT_FIELDS)
        raise StagingError(
            "score receipt must match the exact schema; "
            f"missing={missing}, unexpected={unexpected}"
        )
    if (
        isinstance(receipt["schema_version"], bool)
        or not isinstance(receipt["schema_version"], int)
        or receipt["schema_version"] != 1
    ):
        raise StagingError("score receipt schema_version must equal integer 1")
    for field in SCORE_HASH_FIELDS:
        value = receipt[field]
        if not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value):
            raise StagingError(f"score receipt {field} must be a lowercase SHA-256")
    if receipt["hard_gates_passed"] is not True:
        raise StagingError("hard gates did not pass; proposal cannot be staged")
    if receipt["hidden_hard_gates_passed"] is not True:
        raise StagingError("hidden hard gates did not pass; proposal cannot be staged")
    if receipt["cross_model_passed"] is not True:
        raise StagingError("cross-model gate did not pass; proposal cannot be staged")
    if receipt["eligible_for_staging"] is not True:
        raise StagingError("score receipt is not eligible for staging")
    repeated_trials = receipt["repeated_trials"]
    if (
        isinstance(repeated_trials, bool)
        or not isinstance(repeated_trials, int)
        or repeated_trials < MINIMUM_REPEATED_TRIALS
    ):
        raise StagingError(
            f"repeated_trials must be an integer of at least {MINIMUM_REPEATED_TRIALS}"
        )
    delta = receipt.get("selection_delta")
    if isinstance(delta, bool) or not isinstance(delta, (int, float)):
        raise StagingError("score receipt requires a numeric selection_delta")
    if not math.isfinite(float(delta)) or not 0 < float(delta) <= 1:
        raise StagingError("selection_delta must show a positive bounded improvement")
    return data, receipt


def stage(base: Path, proposal: Path, score: Path, output: Path) -> dict[str, Any]:
    base_data, base_fields = _read_skill(base, "base skill")
    proposal_data, proposal_fields = _read_skill(proposal, "proposal")
    score_data, score_receipt = _read_score(score)
    if base.resolve() == proposal.resolve():
        raise StagingError("proposal must be distinct from the base skill")
    if proposal_fields["name"] != base_fields["name"]:
        raise StagingError("proposal may not change the protected skill name")
    if proposal_data == base_data:
        raise StagingError("proposal must differ from the base skill")
    base_sha256 = _sha256_bytes(base_data)
    proposal_sha256 = _sha256_bytes(proposal_data)
    if score_receipt["base_sha256"] != base_sha256:
        raise StagingError("score receipt base_sha256 is stale or unbound")
    if score_receipt["proposal_sha256"] != proposal_sha256:
        raise StagingError("score receipt proposal_sha256 is stale or unbound")

    output = output.expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise StagingError("output directory must not already exist")
    output_resolved = output.resolve(strict=False)
    for source in (base.resolve(), proposal.resolve(), score.resolve()):
        if output_resolved == source or output_resolved in source.parents:
            raise StagingError("output directory may not contain an input")

    receipt = {
        "adopted": False,
        "base_sha256": base_sha256,
        "condition_sha256": score_receipt["condition_sha256"],
        "cross_model_passed": True,
        "eligible_for_adoption": False,
        "eligible_for_evidence_claims": False,
        "hard_gates_passed": True,
        "hidden_hard_gates_passed": True,
        "optimization_gain_claimed": False,
        "proposal_sha256": proposal_sha256,
        "repeated_trials": score_receipt["repeated_trials"],
        "runner_sha256": score_receipt["runner_sha256"],
        "score_receipt_sha256": _sha256_bytes(score_data),
        "score_receipt_trust": "self-attested-structure-only",
        "selection_delta": float(score_receipt["selection_delta"]),
        "selection_sha256": score_receipt["selection_sha256"],
        "status": "quarantined_for_human_review",
        "structurally_staged": True,
        "trust_boundary": (
            "The supplied score receipt is structurally valid and byte-bound but "
            "unauthenticated. Re-evaluate the proposal through the trusted isolated "
            "adapter/evaluator before any evidence or adoption decision."
        ),
        "train_sha256": score_receipt["train_sha256"],
    }
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.stage-", dir=output.parent))
    try:
        (staging / "SKILL.md").write_bytes(proposal_data)
        (staging / "staging-receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.chmod(staging / "SKILL.md", 0o600)
        os.chmod(staging / "staging-receipt.json", 0o600)
        os.replace(staging, output)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-skill", type=Path, required=True)
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--score-receipt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = stage(
            args.base_skill, args.proposal, args.score_receipt, args.output_dir
        )
    except (OSError, StagingError) as exc:
        print(f"stage_proposal: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
