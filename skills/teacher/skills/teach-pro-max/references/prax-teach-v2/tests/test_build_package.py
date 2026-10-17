#!/usr/bin/env python3
"""Black-box tests for immutable-Git-blob release packaging."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_package.py"
PAYLOAD_BUILDER = ROOT / "scripts" / "review_payload.py"

sys.path.insert(0, str(ROOT / "scripts"))
import build_package as package_builder
import verify as verification_driver
from validate_workspace import _release_file_manifest

REVIEW_ATTESTATION = {
    "cryptographic_authorship_verified": False,
    "orchestration_task_identity_recorded": True,
    "threat_model": (
        "orchestration task identity is structurally recorded; "
        "cryptographic authorship is not verified"
    ),
}
LOG_RETENTION = {
    "full_logs_persisted": False,
    "retained": ["sha256", "tail"],
    "tail_line_limit": 12,
}


@contextmanager
def process_umask(mask: int):
    previous = os.umask(mask)
    try:
        yield
    finally:
        os.umask(previous)


class BuildPackageTest(unittest.TestCase):
    def test_verifier_and_validator_manifest_scopes_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            (workspace / "source.txt").write_text("release\n", encoding="utf-8")
            attempt = workspace / "evidence/forward/attempts/attempt-1"
            attempt.mkdir(parents=True)
            (attempt / "historical.txt").write_text("history\n", encoding="utf-8")
            original_root = verification_driver.ROOT
            try:
                verification_driver.ROOT = workspace
                produced = verification_driver.release_file_manifest()
            finally:
                verification_driver.ROOT = original_root
            self.assertEqual(produced, _release_file_manifest(workspace))

    def git(self, repository: Path, *arguments: str) -> None:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=repository,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def repository(self, path: Path) -> None:
        path.mkdir()
        self.git(path, "init", "--quiet")
        self.git(path, "config", "user.name", "Prax Teach test")
        self.git(path, "config", "user.email", "test@example.invalid")
        self.git(path, "config", "commit.gpgsign", "false")
        (path / "SKILL.md").write_text("# Frozen skill\n", encoding="utf-8")
        scripts = path / "scripts"
        scripts.mkdir()
        tool = scripts / "tool.sh"
        tool.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        tool.chmod(0o755)
        self.git(path, "add", ".")
        self.git(path, "commit", "--quiet", "-m", "reviewed")

    def reviewed_candidate(
        self,
        path: Path,
        *,
        full_status: str = "passed",
        level: str = "full",
        review_status: str = "passed",
        trusted_sandbox: bool = True,
    ) -> None:
        """Create the smallest candidate satisfying the real receipt contracts."""

        path.mkdir()
        self.git(path, "init", "--quiet")
        self.git(path, "config", "user.name", "Prax Teach test")
        self.git(path, "config", "user.email", "test@example.invalid")
        self.git(path, "config", "commit.gpgsign", "false")
        (path / "SKILL.md").write_text(
            "---\n"
            "name: prax-teach-v2\n"
            "description: Candidate release-gate fixture.\n"
            "---\n\n"
            "# Reviewed candidate\n",
            encoding="utf-8",
        )
        scripts = path / "scripts"
        scripts.mkdir()
        verify_script = scripts / "verify.py"
        verify_script.write_text("# fixture verifier\n", encoding="utf-8")
        (path / "reviewed.txt").write_text("reviewed bytes\n", encoding="utf-8")
        attempt = path / "evidence/forward/attempts/attempt-1"
        attempt.mkdir(parents=True)
        (attempt / "history.txt").write_text("reviewed history\n", encoding="utf-8")
        lock_paths = (
            "package-lock.json",
            "uv.lock",
            "integrations/flint/package-lock.json",
            "integrations/skillopt/SOURCE.json",
        )
        for relative in lock_paths:
            lock = path / relative
            lock.parent.mkdir(parents=True, exist_ok=True)
            lock.write_text(f"fixture lock: {relative}\n", encoding="utf-8")

        generated = subprocess.run(
            [
                sys.executable,
                str(PAYLOAD_BUILDER),
                str(path),
                "--output",
                "evidence/reviews/payload.json",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(generated.returncode, 0, generated.stderr)
        payload_path = path / "evidence/reviews/payload.json"
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        payload_file_sha256 = hashlib.sha256(payload_path.read_bytes()).hexdigest()
        for index, review_type in enumerate(
            ("code-standards", "frozen-spec", "architecture-council"), start=1
        ):
            receipt = {
                "schema_version": 2,
                "attestation": REVIEW_ATTESTATION,
                "review_type": review_type,
                "reviewer": {
                    "task": f"/reviewer/{index}",
                    "identity": f"independent reviewer {index}",
                    "independent_from_implementation": True,
                },
                "payload": "evidence/reviews/payload.json",
                "payload_file_sha256": payload_file_sha256,
                "payload_manifest_sha256": payload["sha256"],
                "status": review_status,
                "findings": [],
                "fixes": [],
                "unresolved_actionable": [],
                "recheck": {"status": "passed", "reviewer_confirmed": True},
            }
            if review_type == "architecture-council":
                receipt["panelists"] = [
                    {"task": f"/panel/{panel}", "status": "passed"}
                    for panel in range(1, 4)
                ]
                receipt["chair"] = {"task": "/chair/1", "status": "passed"}
            review_path = path / f"evidence/reviews/{review_type}.json"
            review_path.write_text(
                json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

        gate_names = (
            "html-exact-parity",
            "node-tests",
            "package-validator",
            "python-format",
            "python-lint",
            "python-tests",
            "visual-registry-count",
            "visual-registry-tests",
        )
        full_receipt = {
            "dependencies": {
                "installed": {
                    "fsrs": "fixture",
                    "node": "fixture",
                    "npm": "fixture",
                    "python": "fixture",
                    "python_implementation": "fixture",
                    "ruff": "fixture",
                },
                "locks": {
                    relative: hashlib.sha256((path / relative).read_bytes()).hexdigest()
                    for relative in lock_paths
                },
            },
            "evidence_level": "engineering-verification",
            "external_human_learning_gates_satisfied": False,
            "generated_at": "2026-08-04T12:00:00+00:00",
            "log_retention": LOG_RETENTION,
            "run_id": "fixture-full-verification-run",
            "schema_version": 3,
            "scientific_learning_claim_supported": False,
            "source_date_epoch": "1785844800",
            "status": full_status,
            "level": level,
            "trusted_macos_sandbox_tests_required": trusted_sandbox,
            "root_manifest": _release_file_manifest(path),
            "verification_script_sha256": hashlib.sha256(
                verify_script.read_bytes()
            ).hexdigest(),
            "gates": [
                {
                    "command": ["fixture", name],
                    "exit_code": 0,
                    "name": name,
                    "output_sha256": "0" * 64,
                    "output_tail": [],
                    "policy_failures": [],
                    "status": "passed",
                }
                for name in gate_names
            ],
            "postflight_validation": {
                "command": ["fixture", "postflight"],
                "exit_code": 0,
                "output_sha256": "0" * 64,
                "output_tail": [],
                "status": "passed",
            },
            "skillopt_source": {
                "commit": "e4ea6a6771e797ef820cdd8bfea64c57e0481065",
                "path": "/immutable/fixture/skillopt",
                "tree": "1" * 40,
                "worktree_clean": True,
            },
        }
        full_path = path / "evidence/verification/full.json"
        full_path.parent.mkdir(parents=True)
        full_path.write_text(
            json.dumps(full_receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self.git(path, "add", ".")
        self.git(path, "commit", "--quiet", "-m", "reviewed candidate")

    def build(
        self,
        repository: Path,
        output: Path,
        expected: int = 0,
        *,
        force: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        arguments = [
            sys.executable,
            str(BUILDER),
            str(output),
            "--project-root",
            str(repository),
        ]
        if force:
            arguments.append("--force")
        completed = subprocess.run(
            arguments,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, "SOURCE_DATE_EPOCH": "1785844800"},
        )
        self.assertEqual(
            completed.returncode,
            expected,
            msg=f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )
        return completed

    def test_archive_is_deterministic_and_bound_to_git_blobs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            repository = base / "candidate"
            self.repository(repository)
            outputs = [base / "one.zip", base / "two.zip"]
            receipts = [
                json.loads(self.build(repository, output).stdout) for output in outputs
            ]
            self.assertEqual(outputs[0].read_bytes(), outputs[1].read_bytes())
            self.assertEqual(receipts[0]["source"], "immutable_git_blobs")
            self.assertEqual(
                receipts[0]["archive_sha256"],
                hashlib.sha256(outputs[0].read_bytes()).hexdigest(),
            )
            with zipfile.ZipFile(outputs[0]) as archive:
                manifest = json.loads(
                    archive.read("prax-teach-v2/PACKAGE-MANIFEST.json")
                )
                self.assertEqual(
                    manifest["files"]["SKILL.md"],
                    hashlib.sha256(b"# Frozen skill\n").hexdigest(),
                )
                self.assertEqual(
                    archive.read("prax-teach-v2/SKILL.md"), b"# Frozen skill\n"
                )
                executable_mode = (
                    archive.getinfo("prax-teach-v2/scripts/tool.sh").external_attr >> 16
                ) & 0o777
                self.assertEqual(executable_mode, 0o755)

    def test_reviewed_candidate_archive_binds_the_release_gate_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            repository = base / "candidate"
            self.reviewed_candidate(repository)

            # OpenSpec and agent control files are validated separately from the
            # distributable review payload and must not widen the archive.
            for relative in (
                ".agent/run.md",
                ".agents/skills/local/SKILL.md",
                "openspec/config.yaml",
            ):
                control_file = repository / relative
                control_file.parent.mkdir(parents=True, exist_ok=True)
                control_file.write_text("control plane\n", encoding="utf-8")
            self.git(repository, "add", ".")
            self.git(repository, "commit", "--quiet", "-m", "control metadata")

            completed = self.build(repository, base / "release.zip")
            receipt = json.loads(completed.stdout)
            self.assertEqual(receipt["release_gate"], "passed")
            with zipfile.ZipFile(base / "release.zip") as archive:
                self.assertEqual(
                    archive.read(
                        "prax-teach-v2/evidence/forward/attempts/attempt-1/history.txt"
                    ),
                    b"reviewed history\n",
                )
                manifest = json.loads(
                    archive.read("prax-teach-v2/PACKAGE-MANIFEST.json")
                )
                gate = manifest["release_gate"]
                self.assertEqual(gate["policy"], "prax-teach-v2-reviewed-full")
                self.assertEqual(
                    set(gate["independent_reviews"]),
                    {"architecture-council", "code-standards", "frozen-spec"},
                )
                for evidence in (
                    gate["full_verification"],
                    gate["immutable_review_payload"],
                    *gate["independent_reviews"].values(),
                ):
                    archived = archive.read(f"prax-teach-v2/{evidence['path']}")
                    self.assertEqual(
                        evidence["sha256"], hashlib.sha256(archived).hexdigest()
                    )

    def test_release_gate_validates_the_same_immutable_blobs_it_archives(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            repository = base / "candidate"
            self.reviewed_candidate(repository)
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repository,
                text=True,
                capture_output=True,
                check=True,
            ).stdout.strip()
            frozen = package_builder.frozen_release_files(repository, commit)

            mutable_receipt = repository / "evidence/reviews/code-standards.json"
            document = json.loads(mutable_receipt.read_text())
            document["status"] = "failed"
            mutable_receipt.write_text(json.dumps(document), encoding="utf-8")

            gate = package_builder.candidate_release_gate(repository, frozen)
            self.assertIsNotNone(gate)
            assert gate is not None
            frozen_receipt = next(
                item
                for item in frozen
                if item.name == "evidence/reviews/code-standards.json"
            )
            self.assertEqual(
                gate["independent_reviews"]["code-standards"]["sha256"],
                hashlib.sha256(frozen_receipt.data).hexdigest(),
            )

    def test_unknown_review_inventory_cannot_enter_the_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            repository = base / "candidate"
            self.reviewed_candidate(repository)
            unknown = repository / "evidence/reviews/unreviewed.json"
            unknown.write_text("{}\n", encoding="utf-8")
            full_path = repository / "evidence/verification/full.json"
            full = json.loads(full_path.read_text())
            full["root_manifest"] = _release_file_manifest(repository)
            full_path.write_text(
                json.dumps(full, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            self.git(repository, "add", ".")
            self.git(repository, "commit", "--quiet", "-m", "unknown review entry")

            completed = self.build(repository, base / "release.zip", expected=2)
            self.assertIn("unknown review entry", completed.stderr)
            self.assertFalse((base / "release.zip").exists())

    def test_nonforce_publication_is_atomic_no_clobber(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            temporary = base / ".release.tmp"
            output = base / "release.zip"
            temporary.write_bytes(b"new archive")
            output.write_bytes(b"racing publisher")

            with self.assertRaisesRegex(package_builder.PackageError, "already exists"):
                package_builder._publish_archive(temporary, output, force=False)

            self.assertEqual(output.read_bytes(), b"racing publisher")
            self.assertEqual(temporary.read_bytes(), b"new archive")

    def test_full_receipt_log_retention_and_exact_schema_are_enforced(self) -> None:
        for scenario in ("claims-full-logs", "unknown-field", "unknown-nested"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as temp:
                base = Path(temp)
                repository = base / "candidate"
                self.reviewed_candidate(repository)
                receipt_path = repository / "evidence/verification/full.json"
                receipt = json.loads(receipt_path.read_text())
                if scenario == "claims-full-logs":
                    receipt["log_retention"]["full_logs_persisted"] = True
                else:
                    if scenario == "unknown-field":
                        receipt["self_attested_extension"] = True
                    else:
                        receipt["dependencies"]["unchecked"] = True
                receipt_path.write_text(
                    json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                self.git(repository, "add", str(receipt_path.relative_to(repository)))
                self.git(repository, "commit", "--quiet", "-m", scenario)

                completed = self.build(repository, base / "release.zip", expected=2)
                self.assertIn("release gate failed", completed.stderr)
                self.assertFalse((base / "release.zip").exists())

    def test_candidate_release_gate_fails_closed_before_publication(self) -> None:
        scenarios = ("missing", "failed", "stale", "not-full", "untrusted")
        for scenario in scenarios:
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as temp:
                base = Path(temp)
                repository = base / "candidate"
                if scenario == "missing":
                    self.repository(repository)
                    (repository / "SKILL.md").write_text(
                        "---\nname: prax-teach-v2\n"
                        "description: Missing receipts.\n---\n\n# Candidate\n",
                        encoding="utf-8",
                    )
                    self.git(repository, "add", "SKILL.md")
                    self.git(repository, "commit", "--quiet", "-m", "candidate name")
                else:
                    self.reviewed_candidate(
                        repository,
                        full_status="failed" if scenario == "failed" else "passed",
                        level="core" if scenario == "not-full" else "full",
                        trusted_sandbox=scenario != "untrusted",
                    )
                    if scenario == "stale":
                        (repository / "reviewed.txt").write_text(
                            "changed after review\n", encoding="utf-8"
                        )
                        self.git(repository, "add", "reviewed.txt")
                        self.git(
                            repository,
                            "commit",
                            "--quiet",
                            "-m",
                            "post-review mutation",
                        )

                output = base / "release.zip"
                sentinel = b"previous reviewed release must remain untouched\n"
                output.write_bytes(sentinel)
                completed = self.build(repository, output, expected=2, force=True)
                self.assertIn("release gate failed", completed.stderr)
                self.assertEqual(output.read_bytes(), sentinel)

    def test_dirty_tree_and_tracked_symlink_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            repository = base / "candidate"
            self.repository(repository)
            (repository / "SKILL.md").write_text("# Mutated\n", encoding="utf-8")
            dirty = self.build(repository, base / "dirty.zip", expected=2)
            self.assertIn("must be clean", dirty.stderr)

            self.git(repository, "restore", "SKILL.md")
            (repository / "unsafe-link").symlink_to("SKILL.md")
            self.git(repository, "add", "unsafe-link")
            self.git(repository, "commit", "--quiet", "-m", "tracked symlink")
            linked = self.build(repository, base / "linked.zip", expected=2)
            self.assertIn("not a regular distributable file", linked.stderr)

    def test_nested_output_ancestors_are_private_under_umask_022(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            repository = base / "candidate"
            self.repository(repository)
            first = base / "release-parent"
            second = first / "nested-parent"
            output = second / "release.zip"

            with process_umask(0o022):
                self.build(repository, output)

            self.assertEqual(first.stat().st_mode & 0o777, 0o700)
            self.assertEqual(second.stat().st_mode & 0o777, 0o700)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)

    @unittest.skipIf(not hasattr(os, "symlink"), "symlinks unavailable")
    def test_output_ancestor_symlink_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            repository = base / "candidate"
            self.repository(repository)
            outside = base / "outside"
            outside.mkdir()
            alias = base / "alias"
            alias.symlink_to(outside, target_is_directory=True)

            completed = self.build(
                repository, alias / "nested" / "release.zip", expected=2
            )

            self.assertIn("symlink", completed.stderr.lower())
            self.assertEqual(list(outside.iterdir()), [])

    @unittest.skipIf(not hasattr(os, "symlink"), "symlinks unavailable")
    def test_output_leaf_symlink_never_replaces_its_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            repository = base / "candidate"
            self.repository(repository)
            target = base / "target.zip"
            sentinel = b"must remain untouched\n"
            target.write_bytes(sentinel)
            output = base / "release.zip"
            output.symlink_to(target)

            normal = self.build(repository, output, expected=2)
            self.assertIn("symlink", normal.stderr.lower())
            self.assertEqual(target.read_bytes(), sentinel)
            self.assertTrue(output.is_symlink())

            forced = self.build(repository, output, expected=2, force=True)
            self.assertIn("symlink", forced.stderr.lower())
            self.assertEqual(target.read_bytes(), sentinel)
            self.assertTrue(output.is_symlink())

    @unittest.skipIf(not hasattr(os, "symlink"), "symlinks unavailable")
    def test_dangling_output_leaf_symlink_never_creates_its_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            repository = base / "candidate"
            self.repository(repository)
            target = base / "absent-target.zip"
            output = base / "release.zip"
            output.symlink_to(target)

            for force in (False, True):
                with self.subTest(force=force):
                    completed = self.build(repository, output, expected=2, force=force)
                    self.assertIn("symlink", completed.stderr.lower())
                    self.assertFalse(target.exists())
                    self.assertTrue(output.is_symlink())

    @unittest.skipIf(not hasattr(os, "symlink"), "symlinks unavailable")
    def test_exact_output_inside_candidate_is_rejected_before_leaf_resolution(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            repository = base / "candidate"
            self.repository(repository)
            target = base / "target.zip"
            sentinel = b"must remain untouched\n"
            target.write_bytes(sentinel)
            output = repository / "release.zip"
            output.symlink_to(target)
            (repository / ".git" / "info" / "exclude").write_text(
                "/release.zip\n", encoding="utf-8"
            )

            completed = self.build(repository, output, expected=2, force=True)

            self.assertIn("outside the candidate tree", completed.stderr)
            self.assertEqual(target.read_bytes(), sentinel)
            self.assertTrue(output.is_symlink())

    def test_missing_output_inside_candidate_is_rejected_without_side_effects(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            repository = base / "candidate"
            self.repository(repository)
            rejected_parent = repository / "must-not-exist"

            completed = self.build(
                repository, rejected_parent / "release.zip", expected=2
            )

            self.assertIn("outside the candidate tree", completed.stderr)
            self.assertFalse(rejected_parent.exists())


if __name__ == "__main__":
    unittest.main()
