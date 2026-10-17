"""Behavioral tests for pinned current proof and read-only bounded selection."""

from __future__ import annotations

import concurrent.futures
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import current_evidence as evidence
from praxteach import routing
from review_payload import atomic_write_json, payload_manifest


class CurrentEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original_temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.original_temp.cleanup)
        base = Path(cls.original_temp.name).resolve()
        cls.original = base / "original"
        cls.original_inventory = base / "original-inventory.json"
        evidence.export_original(ROOT, cls.original, cls.original_inventory)

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name).resolve()
        self.root = base / "source"
        shutil.copytree(self.original, self.root)
        for relative in evidence.TOOLS:
            source = ROOT / relative
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        self.directory = base / "proof"
        self.directory.mkdir()
        shutil.copy2(
            self.original_inventory, self.directory / "original-inventory.json"
        )
        for filename in evidence.ROLES.values():
            atomic_write_json(self.directory / filename, {})
        generated = subprocess.run(
            [
                sys.executable,
                "-B",
                str(self.root / "scripts/verify_visual_runtime.py"),
                "--output",
                str(self.directory / "runtime.json"),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(generated.returncode, 0, generated.stdout + generated.stderr)
        self.pin = self.select()
        self.environment = mock.patch.dict(
            os.environ,
            {
                "PRAX_CURRENT_EVIDENCE": self.pin["path"],
                "PRAX_CURRENT_EVIDENCE_SHA256": self.pin["sha256"],
                "PYTHONDONTWRITEBYTECODE": "1",
            },
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def select(self, *, pending: bool = False) -> dict[str, str]:
        return evidence.write_selection(
            self.root,
            self.directory,
            self.original,
            self.directory / "original-inventory.json",
            pending=pending,
        )

    def repin(self, document: dict) -> None:
        path = Path(self.pin["path"])
        atomic_write_json(path, document)
        os.environ["PRAX_CURRENT_EVIDENCE_SHA256"] = evidence.digest(path.read_bytes())

    def snapshot(self) -> dict:
        return {
            str(path.relative_to(self.root)): (
                path.stat().st_mode,
                path.stat().st_mtime_ns,
                path.read_bytes() if path.is_file() else None,
            )
            for path in self.root.rglob("*")
        }

    def test_current_exact_source_and_original_inventory_are_independent(self) -> None:
        selected = evidence.resolve_current(self.root)
        self.assertEqual(selected.historical_root(), self.original)
        self.assertEqual(
            selected.document["source_sha256"], payload_manifest(self.root)["sha256"]
        )
        self.assertEqual(selected.selection_sha256, self.pin["sha256"])
        original_receipt = (
            self.root / "evidence/zero-api-visual-runtime/verification.json"
        )
        self.assertEqual(
            original_receipt.read_bytes(),
            (self.original / original_receipt.relative_to(self.root)).read_bytes(),
        )

    def test_wrong_source_wrong_tool_and_superseded_selection_fail_closed(self) -> None:
        document = json.loads(Path(self.pin["path"]).read_text())
        (self.root / "binary-font.bin").write_bytes(b"new exact bytes\x00")
        with self.assertRaisesRegex(evidence.EvidenceError, "different source"):
            evidence.resolve_current(self.root)
        (self.root / "binary-font.bin").unlink()
        document["tools"]["scripts/verify.py"] = "0" * 64
        self.repin(document)
        with self.assertRaisesRegex(
            evidence.EvidenceError, "different verification tools"
        ):
            evidence.resolve_current(self.root)
        os.environ["PRAX_CURRENT_EVIDENCE_SHA256"] = self.pin["sha256"]
        with self.assertRaisesRegex(evidence.EvidenceError, "superseded"):
            evidence.resolve_current(self.root)

    def test_missing_malformed_duplicate_and_replaced_receipts_reject(self) -> None:
        target = self.directory / "browser.json"
        for data in (None, b"not-json", b'{"x":1,"x":2}', b'{"status":"passed"}'):
            with self.subTest(data=data):
                if data is None:
                    target.unlink()
                else:
                    target.write_bytes(data)
                with self.assertRaises(evidence.EvidenceError):
                    evidence.resolve_current(self.root)
                atomic_write_json(target, {})

    def test_pending_never_establishes_runtime_or_package_eligibility(self) -> None:
        pin = self.select(pending=True)
        os.environ.update(
            PRAX_CURRENT_EVIDENCE=pin["path"],
            PRAX_CURRENT_EVIDENCE_SHA256=pin["sha256"],
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "pending"):
            evidence.resolve_current(self.root)
        selected = evidence.resolve_current(self.root, allow_pending=True)
        with self.assertRaisesRegex(evidence.EvidenceError, "unhashed"):
            selected.receipt("full")
        with mock.patch.dict(os.environ, {"PRAX_ACTIVE_VERIFICATION_RUN_ID": "active"}):
            self.assertEqual(
                evidence.resolve_current(self.root, allow_pending=True).receipt("full"),
                {},
            )
        with mock.patch.object(routing, "ROOT", self.root):
            self.assertIsNone(routing._visual_runtime("python-floating-point"))

    def test_historical_inventory_omission_and_mode_changes_reject(self) -> None:
        selected = evidence.resolve_current(self.root)
        inventory = json.loads((self.directory / "original-inventory.json").read_text())
        inventory["files"].pop()
        atomic_write_json(self.directory / "original-inventory.json", inventory)
        document = selected.document
        document["historical"]["sha256"] = evidence.digest(
            (self.directory / "original-inventory.json").read_bytes()
        )
        self.repin(document)
        with self.assertRaisesRegex(evidence.EvidenceError, "original Git tree"):
            evidence.resolve_current(self.root).historical_root()

    def test_replaced_verifier_is_rejected_before_child_execution(self) -> None:
        verifier = self.root / "scripts/verify_visual_runtime.py"
        verifier.write_text('print("forged runtime")\n', encoding="utf-8")
        with (
            mock.patch.object(routing, "ROOT", self.root),
            mock.patch.object(routing.subprocess, "Popen") as spawn,
        ):
            self.assertIsNone(routing._visual_runtime("python-floating-point"))
        spawn.assert_not_called()

    def test_original_modes_and_complete_snapshot_paths_remain_checked(self) -> None:
        selected = evidence.resolve_current(self.root)
        script = self.original / "scripts/prax_teach.py"
        mode = script.stat().st_mode
        try:
            script.chmod(0o644)
            with self.assertRaisesRegex(evidence.EvidenceError, "mode drift"):
                selected.historical_root()
        finally:
            script.chmod(mode)
        extra = self.original / "unexpected-file.txt"
        try:
            extra.write_text("not original", encoding="utf-8")
            with self.assertRaisesRegex(evidence.EvidenceError, "path set"):
                selected.historical_root()
        finally:
            extra.unlink()

    def test_concurrent_route_and_verifier_checks_preserve_bytes_modes_and_mtimes(
        self,
    ) -> None:
        before = self.snapshot()
        request = "python-floating-point"
        with (
            mock.patch.object(routing, "ROOT", self.root),
            concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool,
        ):
            results = list(pool.map(routing._visual_runtime, [request] * 3))
        self.assertTrue(
            all(result and result["lesson_id"] == request for result in results),
            results,
        )
        self.assertEqual(self.snapshot(), before)

    def test_readonly_route_succeeds_and_cannot_invoke_build(self) -> None:
        # Deny all writes inside source, and intercept build references through
        # a PATH node trap. Route-time inspection requires neither Node nor build.
        trap = self.directory / "bin"
        trap.mkdir()
        marker = self.directory / "node-was-invoked"
        node = trap / "node"
        node.write_text(f'#!/bin/sh\ntouch "{marker}"\nexit 97\n')
        node.chmod(0o755)
        for path in sorted(self.root.rglob("*"), reverse=True):
            path.chmod(0o555 if path.is_dir() or path.stat().st_mode & 0o111 else 0o444)
        self.root.chmod(0o555)
        self.addCleanup(lambda: self.root.chmod(0o755))
        before = self.snapshot()
        with (
            mock.patch.dict(
                os.environ, {"PATH": str(trap) + os.pathsep + os.environ["PATH"]}
            ),
            mock.patch.object(routing, "ROOT", self.root),
        ):
            self.assertIsNotNone(routing._visual_runtime("python-floating-point"))
        self.assertFalse(marker.exists())
        self.assertEqual(self.snapshot(), before)
        for path in self.root.rglob("*"):
            if path.is_dir():
                path.chmod(0o755)

    def test_normal_cli_without_bytecode_flags_preserves_fresh_tree(self) -> None:
        before = self.snapshot()
        environment = dict(os.environ)
        environment.pop("PYTHONDONTWRITEBYTECODE", None)
        completed = subprocess.run(
            [
                sys.executable,
                str(self.root / "scripts/prax_teach.py"),
                "visual-route",
                "--job",
                "Explore Python floating point rounding interactively",
                "--force",
                "interactive",
            ],
            cwd=self.directory,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=40,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(json.loads(completed.stdout)["visual_runtime_supported"])
        self.assertEqual(self.snapshot(), before)

    def test_timeout_cancels_the_whole_verification_process_group(self) -> None:
        process = mock.Mock(pid=12345)
        process.communicate.side_effect = [
            subprocess.TimeoutExpired("verify", 35),
            ("", ""),
        ]
        process.poll.return_value = None
        with (
            mock.patch.object(routing, "ROOT", self.root),
            mock.patch.object(
                routing.subprocess, "Popen", return_value=process
            ) as spawn,
            mock.patch.object(routing.os, "killpg") as kill,
        ):
            self.assertIsNone(routing._visual_runtime("python-floating-point"))
        self.assertTrue(spawn.call_args.kwargs["start_new_session"])
        process.communicate.assert_any_call(timeout=35)
        kill.assert_called_once()

    def test_sibling_pin_is_explicit_and_invalid_pin_cannot_fall_back(self) -> None:
        self.environment.stop()
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PRAX_CURRENT_EVIDENCE", None)
            os.environ.pop("PRAX_CURRENT_EVIDENCE_SHA256", None)
            sibling = self.root.with_name(self.root.name + ".current-evidence.json")
            atomic_write_json(sibling, {"schema_version": 1, **self.pin})
            self.assertIsNotNone(evidence.resolve_current(self.root))
            atomic_write_json(
                sibling,
                {"schema_version": 1, "path": self.pin["path"], "sha256": "0" * 64},
            )
            with self.assertRaises(evidence.EvidenceError):
                evidence.resolve_current(self.root)

    def test_pinned_receipt_is_parsed_from_the_same_buffer_that_was_hashed(
        self,
    ) -> None:
        selected = evidence.resolve_current(self.root)
        original_read = evidence._read
        target = self.directory / "browser.json"
        count = 0

        def replacement(path, **kwargs):
            nonlocal count
            if path == target:
                count += 1
                return b"{}\n" if count == 1 else b'{"untrusted":true}'
            return original_read(path, **kwargs)

        with mock.patch.object(evidence, "_read", side_effect=replacement):
            self.assertEqual(selected.receipt("browser"), {})
        self.assertEqual(count, 1)

    def test_json_read_bound_applies_before_allocation(self) -> None:
        path = self.directory / "too-large.json"
        with path.open("wb") as handle:
            handle.truncate(16 * 1024 * 1024 + 1)
        with self.assertRaisesRegex(evidence.EvidenceError, "read bound"):
            evidence._json(path)


if __name__ == "__main__":
    unittest.main()
