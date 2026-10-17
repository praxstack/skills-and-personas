#!/usr/bin/env python3
"""Build-time-only formal receipt validator; never invoked by the learner artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def receipt(source: Path, proof_state: Path) -> dict[str, object]:
    if source.suffix != ".lean":
        raise ValueError("--source must name a Lean source file")
    lean = shutil.which("lean")
    version = "not-installed"
    lean_run: subprocess.CompletedProcess[str] | None = None
    if lean:
        completed = subprocess.run(
            [lean, "--version"], capture_output=True, text=True, check=False
        )
        version = completed.stdout.strip() or completed.stderr.strip() or "unknown"
        lean_run = subprocess.run(
            [lean, str(source)], capture_output=True, text=True, check=False
        )
    state = json.loads(proof_state.read_text(encoding="utf-8"))
    if not isinstance(state, dict):
        state = {}
    source_digest = sha256(source)
    state_matches_source = state.get("source_sha256") == source_digest
    states = state.get("states")
    state_contract_valid = (
        state.get("schema_version") == "prax.formal-proof-state/v1"
        and state.get("status") in {"static-equivalent", "verified"}
        and isinstance(states, list)
        and all(
            isinstance(item, dict)
            and isinstance(item.get("label"), str)
            and bool(item["label"].strip())
            and isinstance(item.get("goal"), str)
            and bool(item["goal"].strip())
            for item in states
        )
    )
    status = (
        "failed"
        if not state_contract_valid or not state_matches_source
        else (
            "unavailable"
            if not lean
            else "verified"
            if lean_run and lean_run.returncode == 0
            else "failed"
        )
    )
    warnings = ["Build-time evidence only; not a runtime theorem prover."]
    if not state_matches_source:
        warnings.append("Proof-state export does not match the Lean source SHA-256.")
    if not state_contract_valid:
        warnings.append("Proof-state export does not satisfy the proof-state contract.")
    return {
        "schema_version": "prax.formal-receipt/v1",
        "status": status,
        "source_sha256": source_digest,
        "proof_state_sha256": sha256(proof_state),
        "toolchain": {"name": "Lean", "version": version},
        "imports": [],
        "proof_states": states if state_contract_valid else [],
        "warnings": warnings,
        "axioms": [],
        "compiler": {
            "exit_code": None if lean_run is None else lean_run.returncode,
            "stdout": "" if lean_run is None else lean_run.stdout,
            "stderr": "" if lean_run is None else lean_run.stderr,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--proof-state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(
        json.dumps(receipt(args.source, args.proof_state), indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
