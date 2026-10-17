"""Adversarial tests for the exact release criterion ledger."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_workspace as validator

CAPABILITY_IDS = (
    "baseline-provenance",
    "documentation-truth",
    "ecosystem-exports",
    "evaluation-harness",
    "flint-adapter",
    "full-verification",
    "independent-review",
    "learner-state",
    "learner-study-machinery",
    "legacy-assets",
    "markdown-html-artifacts",
    "mode-and-visual-routing",
    "north-star-outcome",
    "package-validation",
    "release-package",
    "review-scheduler",
    "skillopt-adapter",
)


class ReleaseStatusLedgerTest(unittest.TestCase):
    def fixture(self, workspace: Path) -> dict[str, object]:
        evidence = workspace / "criterion-evidence.txt"
        evidence.write_text("release evidence\n", encoding="utf-8")
        digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
        capabilities = [
            {
                "claim_limit": "Fixture claim boundary.",
                "evidence": ["fixture"],
                "id": capability_id,
                "state": (
                    "scientifically-unproven"
                    if capability_id == "north-star-outcome"
                    else "implemented"
                ),
            }
            for capability_id in CAPABILITY_IDS
        ]
        criteria = [
            {
                "capabilities": ["package-validation"],
                "evidence": [
                    {
                        "kind": "path",
                        "path": evidence.name,
                        "sha256": digest,
                    }
                ],
                "id": f"AC-{index:02d}",
                "state": "pending" if index == 25 else "passed",
            }
            for index in range(26)
        ]
        return {
            "capabilities": capabilities,
            "criteria": criteria,
            "external_gates": [
                {
                    "id": f"EG-{index:02d}",
                    "status": "parked",
                    "unblock": f"Supply external evidence for EG-{index:02d}.",
                }
                for index in range(1, 7)
            ],
            "north_star": {
                "design_encoded": True,
                "machinery_implemented": True,
                "scientifically_supported": False,
            },
            "phases": [
                {
                    "capabilities": ["package-validation"],
                    "evidence": ["fixture"],
                    "id": "phase-0",
                    "parked": [],
                    "state": "implemented",
                    "title": "Fixture phase",
                }
            ],
            "release_label": "pre-release",
            "schema_version": 2,
        }

    def validate(
        self, workspace: Path, status: dict[str, object], expected: int
    ) -> list[str]:
        status_path = workspace / "STATUS.json"
        status_path.write_text(
            json.dumps(status, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        errors = validator.release_status_errors(status_path, status, workspace)
        self.assertEqual(
            int(bool(errors)),
            expected,
            msg="\n".join(errors),
        )
        return errors

    def test_exact_pending_ledger_is_valid_but_cannot_claim_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            status = self.fixture(workspace)
            self.assertEqual(self.validate(workspace, status, 0), [])

            promoted = copy.deepcopy(status)
            promoted["release_label"] = "engineering-candidate"
            errors = self.validate(workspace, promoted, 1)
            self.assertIn(
                "engineering-candidate requires every AC-00 through AC-25",
                "\n".join(errors),
            )

            promoted["criteria"][-1]["state"] = "passed"
            self.assertEqual(self.validate(workspace, promoted, 0), [])

    def test_criterion_omission_duplicate_and_unknown_id_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            baseline = self.fixture(workspace)
            mutations = {
                "omit": lambda status: status["criteria"].pop(7),
                "duplicate": lambda status: status["criteria"].__setitem__(
                    7, copy.deepcopy(status["criteria"][6])
                ),
                "unknown": lambda status: status["criteria"][7].__setitem__(
                    "id", "AC-99"
                ),
            }
            expected = {
                "omit": "criteria omit IDs ['AC-07']",
                "duplicate": "duplicates 'AC-06'",
                "unknown": "is unknown: 'AC-99'",
            }
            for name, mutate in mutations.items():
                with self.subTest(name=name):
                    status = copy.deepcopy(baseline)
                    mutate(status)
                    errors = self.validate(workspace, status, 1)
                    self.assertIn(expected[name], "\n".join(errors))

    def test_unsupported_or_unbound_capability_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            status = self.fixture(workspace)
            status["capabilities"][0]["id"] = "invented-capability"
            status["criteria"][0]["capabilities"] = ["invented-capability"]
            joined = "\n".join(self.validate(workspace, status, 1))
            self.assertIn("id is unsupported: 'invented-capability'", joined)
            self.assertIn("contains unsupported IDs ['invented-capability']", joined)
            self.assertIn("capabilities omit supported IDs", joined)

    def test_phase_capability_contract_and_evidence_floor_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            baseline = self.fixture(workspace)

            promoted = copy.deepcopy(baseline)
            promoted["phases"][0]["state"] = "dependency-exercised"
            joined = "\n".join(self.validate(workspace, promoted, 1))
            self.assertIn(
                "state 'dependency-exercised' exceeds referenced capability "
                "evidence floor 'implemented'",
                joined,
            )

            supported = copy.deepcopy(promoted)
            capability = next(
                item
                for item in supported["capabilities"]
                if item["id"] == "package-validation"
            )
            capability["state"] = "dependency-exercised"
            self.assertEqual(self.validate(workspace, supported, 0), [])

            non_promotable = copy.deepcopy(baseline)
            non_promotable["phases"][0]["capabilities"] = ["north-star-outcome"]
            non_promotable["phases"][0]["state"] = "specified"
            joined = "\n".join(self.validate(workspace, non_promotable, 1))
            self.assertIn(
                "cannot be promoted from non-promotable capability states",
                joined,
            )

            mutations = {
                "empty": ([], "must be a non-empty string list"),
                "duplicate": (
                    ["package-validation", "package-validation"],
                    "contains duplicates",
                ),
                "unknown": (
                    ["invented-capability"],
                    "contains unsupported IDs ['invented-capability']",
                ),
            }
            for name, (capabilities, expected) in mutations.items():
                with self.subTest(name=name):
                    status = copy.deepcopy(baseline)
                    status["phases"][0]["capabilities"] = capabilities
                    joined = "\n".join(self.validate(workspace, status, 1))
                    self.assertIn(expected, joined)

    def test_missing_stale_self_and_unsupported_evidence_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            baseline = self.fixture(workspace)
            mutations = {
                "missing": {
                    "kind": "path",
                    "path": "missing.txt",
                    "sha256": "0" * 64,
                },
                "stale": {
                    "kind": "path",
                    "path": "criterion-evidence.txt",
                    "sha256": "0" * 64,
                },
                "self": {
                    "kind": "path",
                    "path": "./STATUS.json",
                    "sha256": "0" * 64,
                },
                "unsupported-receipt": {
                    "kind": "receipt",
                    "path": "evidence/unreviewed-self-assertion.json",
                },
                "missing-receipt": {
                    "kind": "receipt",
                    "path": "evidence/reviews/frozen-spec.json",
                },
            }
            expected = {
                "missing": "missing or unsafe file 'missing.txt'",
                "stale": "digest mismatch for criterion-evidence.txt",
                "self": "cannot self-bind the status ledger",
                "unsupported-receipt": "unsupported receipt",
                "missing-receipt": "missing or unsafe receipt",
            }
            for name, binding in mutations.items():
                with self.subTest(name=name):
                    status = copy.deepcopy(baseline)
                    status["criteria"][0]["evidence"] = [binding]
                    joined = "\n".join(self.validate(workspace, status, 1))
                    self.assertIn(expected[name], joined)

            (workspace / "alias").symlink_to(workspace, target_is_directory=True)
            symlinked = copy.deepcopy(baseline)
            symlinked["criteria"][0]["evidence"] = [
                {
                    "kind": "path",
                    "path": "alias/criterion-evidence.txt",
                    "sha256": hashlib.sha256(
                        (workspace / "criterion-evidence.txt").read_bytes()
                    ).hexdigest(),
                }
            ]
            joined = "\n".join(self.validate(workspace, symlinked, 1))
            self.assertIn("missing or unsafe file", joined)

    def test_parked_criterion_requires_declared_parked_gate_and_unblock(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            baseline = self.fixture(workspace)

            unbound = copy.deepcopy(baseline)
            unbound["criteria"][0]["state"] = "parked"
            joined = "\n".join(self.validate(workspace, unbound, 1))
            self.assertIn("parked criterion is not bound to an external gate", joined)

            no_unblock = copy.deepcopy(baseline)
            del no_unblock["external_gates"][0]["unblock"]
            joined = "\n".join(self.validate(workspace, no_unblock, 1))
            self.assertIn("unblock is required for a parked gate", joined)

            mismatched = copy.deepcopy(baseline)
            mismatched["criteria"][0]["state"] = "parked"
            mismatched["criteria"][0]["evidence"] = [{"kind": "gate", "id": "EG-01"}]
            mismatched["external_gates"][0] = {
                "id": "EG-01",
                "status": "passed",
            }
            joined = "\n".join(self.validate(workspace, mismatched, 1))
            self.assertIn("requires a parked gate with an exact unblock", joined)

            bound = copy.deepcopy(baseline)
            bound["criteria"][0]["state"] = "parked"
            bound["criteria"][0]["evidence"] = [{"kind": "gate", "id": "EG-01"}]
            self.assertEqual(self.validate(workspace, bound, 0), [])


if __name__ == "__main__":
    unittest.main()
