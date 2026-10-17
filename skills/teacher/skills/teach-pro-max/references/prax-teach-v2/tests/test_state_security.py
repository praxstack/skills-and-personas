#!/usr/bin/env python3
"""Adversarial filesystem and concurrency tests for learner state."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event, Thread
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "prax_teach.py"
sys.path.insert(0, str(ROOT / "scripts"))
from praxteach import scheduler as scheduler_module
from praxteach import state as state_module
from praxteach.errors import SafetyError


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    arguments = list(args)
    if arguments and arguments[0] == "observe":
        concept = arguments[arguments.index("--concept") + 1]
        for flag, value in (
            ("--content-id", concept),
            ("--objective-id", "objective:" + concept),
            ("--model-and-prompt-version", "test-tutor:model:prompt-v1"),
        ):
            if flag not in arguments:
                arguments.extend((flag, value))
    return subprocess.run(
        [sys.executable, str(CLI), *arguments],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class TestStateSecurity(unittest.TestCase):
    def init_workspace(self, workspace: Path) -> None:
        completed = run_cli(
            "init",
            str(workspace),
            "--learner-id",
            "learner-local-1",
            "--goal",
            "Concurrent evidence test",
            "--consent",
            "--timestamp",
            "2026-08-04T10:00:00Z",
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        source = run_cli(
            "source-add",
            str(workspace),
            "--source-id",
            "fixture",
            "--title",
            "Filesystem security fixture source",
            "--url",
            "https://example.invalid/filesystem-security",
            "--author-or-publisher",
            "Prax Teach test suite",
            "--source-type",
            "official-doc",
            "--retrieved-at",
            "2026-08-04",
            "--version-or-date",
            "2026-08-04",
            "--license-or-use-note",
            "Synthetic fixture for security testing.",
            "--supports",
            "concurrency",
            "--limitations",
            "Not real-world instructional evidence.",
        )
        self.assertEqual(source.returncode, 0, source.stderr)

    @unittest.skipIf(not hasattr(os, "symlink"), "symlinks unavailable")
    def test_state_symlink_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            workspace = temp_path / "course"
            outside = temp_path / "outside"
            outside.mkdir()
            self.init_workspace(workspace)
            state = workspace / "state"
            backup = workspace / "state-real"
            state.rename(backup)
            state.symlink_to(outside, target_is_directory=True)

            completed = run_cli("rebuild", str(workspace))
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("symlink", completed.stderr.lower())
            self.assertEqual(list(outside.iterdir()), [])

    @unittest.skipIf(not hasattr(os, "symlink"), "symlinks unavailable")
    def test_workspace_symlink_ancestor_is_rejected_for_every_control(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            real_parent = temp_path / "real"
            real_parent.mkdir()
            workspace = real_parent / "course"
            self.init_workspace(workspace)
            observed = run_cli(
                "observe",
                str(workspace),
                "--response",
                "The workspace ancestor must remain bound.",
                "--session",
                "session-1",
                "--concept",
                "ancestor-safety",
                "--dimension",
                "application",
                "--score",
                "0.9",
                "--hint-level",
                "0",
                "--item",
                "item-1",
                "--item-version",
                "v1",
                "--content-version",
                "sha256:" + "a" * 64,
                "--source-id",
                "fixture",
                "--source-version",
                "2026-08-04",
                "--timestamp",
                "2026-08-04T10:05:00Z",
            )
            self.assertEqual(observed.returncode, 0, observed.stderr)
            event_id = json.loads(observed.stdout)["event_id"]
            alias = temp_path / "alias"
            alias.symlink_to(real_parent, target_is_directory=True)
            aliased_workspace = alias / "course"

            commands = (
                ("show", str(aliased_workspace)),
                (
                    "delete",
                    str(aliased_workspace),
                    "--event-id",
                    event_id,
                    "--dry-run",
                ),
                ("delete", str(aliased_workspace), "--all-state", "--dry-run"),
            )
            for command in commands:
                completed = run_cli(*command)
                self.assertEqual(completed.returncode, 5, completed.stderr)
                self.assertIn("symlink", completed.stderr.lower())
            self.assertTrue(workspace.is_dir())

    @unittest.skipUnless(os.name == "posix", "POSIX permission modes required")
    def test_resumed_workspace_requires_private_state_modes_and_regular_files(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)

            workspace.chmod(0o755)
            exposed_workspace = run_cli("show", str(workspace))
            self.assertEqual(exposed_workspace.returncode, 5)
            self.assertIn("private", exposed_workspace.stderr.lower())
            workspace.chmod(0o700)

            state = workspace / "state"
            state.chmod(0o755)
            exposed_state = run_cli("show", str(workspace))
            self.assertEqual(exposed_state.returncode, 5)
            self.assertIn("private", exposed_state.stderr.lower())
            state.chmod(0o700)

            learner = state / "learner.json"
            learner.chmod(0o644)
            exposed_file = run_cli("show", str(workspace))
            self.assertEqual(exposed_file.returncode, 5)
            self.assertIn("private", exposed_file.stderr.lower())
            learner.chmod(0o600)

            sessions = state / "sessions.jsonl"
            sessions.unlink()
            sessions.mkdir(mode=0o700)
            non_regular = run_cli("show", str(workspace))
            self.assertEqual(non_regular.returncode, 5)
            self.assertIn("regular file", non_regular.stderr.lower())

    @unittest.skipUnless(hasattr(os, "link"), "hardlinks unavailable")
    def test_required_state_hardlink_cannot_cross_learner_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            first = base / "first"
            second = base / "second"
            self.init_workspace(first)
            self.init_workspace(second)
            marker = run_cli(
                "observe",
                str(second),
                "--response",
                "This response belongs only to the second learner.",
                "--session",
                "session-secret",
                "--concept",
                "other-learner-marker",
                "--dimension",
                "recall",
                "--score",
                "0.9",
                "--hint-level",
                "0",
                "--item",
                "other-item",
                "--item-version",
                "v1",
                "--content-version",
                "sha256:" + "d" * 64,
                "--source-id",
                "fixture",
                "--source-version",
                "2026-08-04",
                "--timestamp",
                "2026-08-04T10:05:00Z",
            )
            self.assertEqual(marker.returncode, 0, marker.stderr)
            first_log = first / "state" / "sessions.jsonl"
            first_log.unlink()
            os.link(second / "state" / "sessions.jsonl", first_log)

            shown = run_cli("show", str(first))
            self.assertEqual(shown.returncode, 5)
            self.assertIn("hardlink", shown.stderr.lower())
            export_path = base / "must-not-exist.zip"
            exported = run_cli(
                "export",
                str(first),
                str(export_path),
                "--timestamp",
                "2026-08-04T11:00:00Z",
            )
            self.assertEqual(exported.returncode, 5)
            self.assertFalse(export_path.exists())

    @unittest.skipUnless(hasattr(os, "link"), "hardlinks unavailable")
    def test_workspace_lock_rejects_hardlinks_without_chmodding_the_source(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            workspace = base / "course"
            self.init_workspace(workspace)
            outside = base / "outside-lock-source"
            outside.write_bytes(b"outside")
            outside.chmod(0o644)
            lock_path = workspace / ".prax-teach.lock"
            lock_path.unlink()
            os.link(outside, lock_path)
            before = outside.stat().st_mode

            shown = run_cli("show", str(workspace))
            self.assertEqual(shown.returncode, 5)
            self.assertIn("hardlink", shown.stderr.lower())
            self.assertEqual(outside.stat().st_mode, before)
            self.assertEqual(outside.read_bytes(), b"outside")

    @unittest.skipUnless(os.name == "posix", "POSIX generation locks required")
    def test_workspace_generation_reuse_cannot_redirect_a_blocked_writer(
        self,
    ) -> None:
        import fcntl
        import time

        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            workspace = base / "course"
            parked = base / "old-course"
            self.init_workspace(workspace)
            old_lock_path = workspace / ".prax-teach.lock"
            old_lock = os.open(old_lock_path, os.O_RDWR | os.O_CREAT, 0o600)
            fcntl.flock(old_lock, fcntl.LOCK_EX)
            observe = subprocess.Popen(
                [
                    sys.executable,
                    str(CLI),
                    "observe",
                    str(workspace),
                    "--response",
                    "This write must remain in its original workspace generation.",
                    "--session",
                    "session-stale-writer",
                    "--concept",
                    "must-not-cross-generation",
                    "--dimension",
                    "application",
                    "--score",
                    "0.9",
                    "--hint-level",
                    "0",
                    "--item",
                    "stale-item",
                    "--item-version",
                    "v1",
                    "--content-id",
                    "must-not-cross-generation",
                    "--content-version",
                    "sha256:" + "e" * 64,
                    "--objective-id",
                    "objective:must-not-cross-generation",
                    "--model-and-prompt-version",
                    "test-tutor:model:prompt-v1",
                    "--source-id",
                    "fixture",
                    "--source-version",
                    "2026-08-04",
                    "--timestamp",
                    "2026-08-04T10:05:00Z",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            parent_fd = os.open(base, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            deadline = time.monotonic() + 5
            while True:
                try:
                    fcntl.flock(parent_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    break
                else:
                    fcntl.flock(parent_fd, fcntl.LOCK_UN)
                if observe.poll() is not None or time.monotonic() >= deadline:
                    self.fail("observe did not acquire the parent generation lock")
                time.sleep(0.01)

            workspace.rename(parked)
            initialize = subprocess.Popen(
                [
                    sys.executable,
                    str(CLI),
                    "init",
                    str(workspace),
                    "--learner-id",
                    "learner-new-generation",
                    "--goal",
                    "New generation must stay isolated",
                    "--consent",
                    "--timestamp",
                    "2026-08-04T10:06:00Z",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            fcntl.flock(old_lock, fcntl.LOCK_UN)
            os.close(old_lock)
            observe_stdout, observe_stderr = observe.communicate(timeout=10)
            init_stdout, init_stderr = initialize.communicate(timeout=10)
            os.close(parent_fd)

            self.assertEqual(observe.returncode, 5, observe_stdout + observe_stderr)
            self.assertIn("generation changed", observe_stderr.lower())
            self.assertEqual(initialize.returncode, 0, init_stdout + init_stderr)
            self.assertEqual((workspace / "state" / "sessions.jsonl").read_bytes(), b"")
            self.assertEqual((parked / "state" / "sessions.jsonl").read_bytes(), b"")

    @unittest.skipUnless(os.name == "posix", "POSIX generation locks required")
    def test_writer_waiting_on_parent_lock_rejects_a_replacement_generation(
        self,
    ) -> None:
        import fcntl

        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            workspace = base / "course"
            parked = base / "old-course"
            replacement = base / "replacement"
            self.init_workspace(workspace)
            self.init_workspace(replacement)
            replacement_learner = replacement / "state" / "learner.json"
            replacement_document = json.loads(replacement_learner.read_text())
            replacement_document["consent"]["location"] = str(workspace)
            replacement_learner.write_text(
                json.dumps(replacement_document, indent=2, sort_keys=True) + "\n"
            )
            replacement_learner.chmod(0o600)

            parent_fd = os.open(base, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            fcntl.flock(parent_fd, fcntl.LOCK_EX)
            preflight_complete = Event()
            original_secure = state_module.secure_workspace
            outcome: list[BaseException | dict[str, object]] = []

            def observed_secure(path: str) -> Path:
                resolved = original_secure(path)
                preflight_complete.set()
                return resolved

            event = state_module.make_observation(
                session_id="session-stale-writer",
                concept_id="must-not-cross-generation",
                dimension="application",
                score=0.9,
                hint_level=0,
                item_id="stale-item",
                item_version="v1",
                content_id="must-not-cross-generation",
                content_version="sha256:" + "e" * 64,
                objective_id="objective:must-not-cross-generation",
                model_and_prompt_version="test-tutor:model:prompt-v1",
                source_id="fixture",
                source_version="2026-08-04",
                timestamp="2026-08-04T10:05:00Z",
                response="The stale writer must not cross workspace generations.",
                response_ref=None,
            )

            def write() -> None:
                try:
                    outcome.append(
                        state_module.append_observation(str(workspace), event)
                    )
                except SafetyError as exc:
                    outcome.append(exc)

            with mock.patch.object(
                state_module, "secure_workspace", side_effect=observed_secure
            ):
                thread = Thread(target=write)
                thread.start()
                self.assertTrue(preflight_complete.wait(timeout=5))
                workspace.rename(parked)
                replacement.rename(workspace)
                fcntl.flock(parent_fd, fcntl.LOCK_UN)
                os.close(parent_fd)
                thread.join(timeout=10)

            self.assertFalse(thread.is_alive())
            self.assertEqual(len(outcome), 1)
            self.assertIsInstance(outcome[0], SafetyError)
            self.assertIn("generation changed", str(outcome[0]).lower())
            self.assertEqual((workspace / "state" / "sessions.jsonl").read_bytes(), b"")
            self.assertEqual((parked / "state" / "sessions.jsonl").read_bytes(), b"")

    @unittest.skipUnless(os.name == "posix", "POSIX directory descriptors required")
    def test_state_journal_cleanup_cannot_delete_replacement_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            workspace = base / "course"
            replacement = base / "replacement"
            parked = base / "parked-course"
            self.init_workspace(workspace)
            self.init_workspace(replacement)
            workspace = state_module.secure_workspace(workspace)
            replacement = state_module.secure_workspace(replacement)

            transaction = state_module._state_transaction(workspace, [])
            original_journal = workspace / "state" / state_module.STATE_TRANSACTION_NAME
            replacement_journal = (
                replacement / "state" / state_module.STATE_TRANSACTION_NAME
            )
            state_module.atomic_write_json(original_journal, transaction)
            state_module.atomic_write_json(replacement_journal, transaction)

            original_read_bytes = state_module.read_bytes
            misconception_reads = 0

            def swap_generation_before_journal_cleanup(
                target_workspace: Path, relative: str | Path
            ) -> bytes:
                nonlocal misconception_reads
                payload = original_read_bytes(target_workspace, relative)
                if (
                    target_workspace == workspace
                    and str(relative) == "state/misconceptions.json"
                ):
                    misconception_reads += 1
                    if misconception_reads == 2:
                        workspace.rename(parked)
                        replacement.rename(workspace)
                return payload

            with (
                mock.patch.object(
                    state_module,
                    "read_bytes",
                    side_effect=swap_generation_before_journal_cleanup,
                ),
                self.assertRaisesRegex(SafetyError, "generation changed"),
                state_module.workspace_lock(workspace),
            ):
                state_module._apply_state_transaction(workspace, transaction)

            parked = state_module.secure_workspace(parked)
            self.assertTrue(
                (parked / "state" / state_module.STATE_TRANSACTION_NAME).is_file()
            )
            self.assertTrue(
                (workspace / "state" / state_module.STATE_TRANSACTION_NAME).is_file()
            )

            with state_module.workspace_lock(parked):
                state_module._apply_state_transaction(parked, transaction)
            self.assertFalse(
                (parked / "state" / state_module.STATE_TRANSACTION_NAME).exists()
            )
            self.assertTrue(
                (workspace / "state" / state_module.STATE_TRANSACTION_NAME).is_file()
            )

    @unittest.skipUnless(os.name == "posix", "POSIX directory descriptors required")
    def test_full_delete_swap_preserves_replacement_and_journal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            workspace = base / "course"
            quarantine = base / ".course.prax-teach-deleting"
            displaced = base / "displaced-course"
            replacement = base / "replacement"
            journal = base / ".course.full-delete-transaction.json"
            self.init_workspace(workspace)
            replacement.mkdir(mode=0o700)
            marker = replacement / "must-not-delete.txt"
            marker.write_text("replacement", encoding="utf-8")

            original_remove = state_module._remove_directory_contents
            swapped = False

            def swap_then_remove(descriptor: int) -> None:
                nonlocal swapped
                if not swapped:
                    quarantine.rename(displaced)
                    replacement.rename(quarantine)
                    swapped = True
                original_remove(descriptor)

            with (
                mock.patch.object(
                    state_module,
                    "_remove_directory_contents",
                    side_effect=swap_then_remove,
                ),
                self.assertRaisesRegex(SafetyError, "changed during removal"),
            ):
                state_module.delete_workspace(
                    str(workspace), dry_run=False, confirm=True
                )

            self.assertTrue(swapped)
            self.assertEqual(
                (quarantine / marker.name).read_text(encoding="utf-8"),
                "replacement",
            )
            self.assertTrue(displaced.is_dir())
            self.assertTrue(journal.is_file())

    @unittest.skipUnless(os.name == "posix", "POSIX directory descriptors required")
    def test_full_delete_parent_swap_does_not_rename_replacement_workspace(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            original_parent = root / "original-parent"
            replacement_parent = root / "replacement-parent"
            parked_parent = root / "parked-parent"
            original_parent.mkdir(mode=0o700)
            replacement_parent.mkdir(mode=0o700)
            workspace = original_parent / "course"
            replacement_workspace = replacement_parent / workspace.name
            self.init_workspace(workspace)
            replacement_workspace.mkdir(mode=0o700)
            replacement_marker = replacement_workspace / "must-not-move.txt"
            replacement_marker.write_text("replacement", encoding="utf-8")
            original_learner = (workspace / "state" / "learner.json").read_bytes()
            original_plan = state_module._workspace_deletion_plan
            plan_calls = 0

            def plan_then_swap_parent(target: Path) -> dict[str, object]:
                nonlocal plan_calls
                plan = original_plan(target)
                plan_calls += 1
                if plan_calls == 2:
                    original_parent.rename(parked_parent)
                    replacement_parent.rename(original_parent)
                return plan

            with (
                mock.patch.object(
                    state_module,
                    "_workspace_deletion_plan",
                    side_effect=plan_then_swap_parent,
                ),
                self.assertRaises(SafetyError),
            ):
                state_module.delete_workspace(
                    str(workspace), dry_run=False, confirm=True
                )

            replacement_workspace = original_parent / workspace.name
            quarantine = parked_parent / ".course.prax-teach-deleting"
            journal = parked_parent / ".course.full-delete-transaction.json"
            self.assertEqual(plan_calls, 2)
            self.assertEqual(
                (replacement_workspace / replacement_marker.name).read_text(
                    encoding="utf-8"
                ),
                "replacement",
            )
            self.assertFalse((original_parent / quarantine.name).exists())
            self.assertFalse((parked_parent / workspace.name).exists())
            self.assertEqual(
                (quarantine / "state" / "learner.json").read_bytes(),
                original_learner,
            )
            self.assertTrue(journal.is_file())

    @unittest.skipUnless(os.name == "posix", "POSIX directory descriptors required")
    def test_locked_review_write_rejects_ancestor_swap_redirection(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original_parent = root / "original-parent"
            attacker_parent = root / "attacker-parent"
            parked_parent = root / "parked-parent"
            original_parent.mkdir(mode=0o700)
            attacker_parent.mkdir(mode=0o700)
            workspace = original_parent / "course"
            attacker_workspace = attacker_parent / "course"
            self.init_workspace(workspace)
            self.init_workspace(attacker_workspace)

            attacker_learner = attacker_workspace / "state" / "learner.json"
            attacker_document = json.loads(attacker_learner.read_text())
            attacker_document["consent"]["location"] = str(workspace)
            attacker_learner.write_text(
                json.dumps(attacker_document, indent=2, sort_keys=True) + "\n"
            )
            attacker_learner.chmod(0o600)
            original_reviews = (workspace / "state" / "reviews.jsonl").read_bytes()
            attacker_reviews = (
                attacker_workspace / "state" / "reviews.jsonl"
            ).read_bytes()

            original_validate = scheduler_module._validate_consent
            swapped = False

            def swap_ancestor_then_validate(
                locked_workspace: Path,
            ) -> dict[str, object]:
                nonlocal swapped
                if not swapped:
                    original_parent.rename(parked_parent)
                    original_parent.symlink_to(
                        attacker_parent,
                        target_is_directory=True,
                    )
                    swapped = True
                return original_validate(locked_workspace)

            with (
                mock.patch.object(
                    scheduler_module,
                    "_validate_consent",
                    side_effect=swap_ancestor_then_validate,
                ),
                self.assertRaisesRegex(
                    SafetyError,
                    "symlink|changed after it was validated",
                ),
            ):
                scheduler_module.set_review_status(
                    str(workspace),
                    enabled=False,
                    reason="ancestor swap must not redirect this control",
                    timestamp="2026-08-04T10:10:00Z",
                )

            self.assertTrue(swapped)
            self.assertEqual(
                (parked_parent / "course" / "state" / "reviews.jsonl").read_bytes(),
                original_reviews,
            )
            self.assertEqual(
                (attacker_workspace / "state" / "reviews.jsonl").read_bytes(),
                attacker_reviews,
            )

    def test_concurrent_observations_remain_valid_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)

            def record(index: int) -> subprocess.CompletedProcess[str]:
                return run_cli(
                    "observe",
                    str(workspace),
                    "--response",
                    f"Concurrent response {index}",
                    "--session",
                    f"session-{index % 2}",
                    "--concept",
                    "concurrency",
                    "--dimension",
                    "application",
                    "--score",
                    "0.8",
                    "--hint-level",
                    "0",
                    "--item",
                    f"item-{index}",
                    "--item-version",
                    "v1",
                    "--content-version",
                    "sha256:" + "b" * 64,
                    "--source-id",
                    "fixture",
                    "--source-version",
                    "2026-08-04",
                    "--timestamp",
                    f"2026-08-04T10:{index:02d}:00Z",
                )

            with ThreadPoolExecutor(max_workers=6) as pool:
                results = list(pool.map(record, range(12)))
            for result in results:
                self.assertEqual(result.returncode, 0, result.stderr)

            lines = (workspace / "state" / "sessions.jsonl").read_text().splitlines()
            self.assertEqual(len(lines), 12)
            events = [json.loads(line) for line in lines]
            self.assertEqual(len({event["event_id"] for event in events}), 12)
            self.assertEqual(
                {event["item_id"] for event in events}, {f"item-{i}" for i in range(12)}
            )

            first = run_cli("rebuild", str(workspace))
            self.assertEqual(first.returncode, 0, first.stderr)
            before = (workspace / "state" / "concepts.json").read_bytes()
            second = run_cli("rebuild", str(workspace))
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(
                before, (workspace / "state" / "concepts.json").read_bytes()
            )

    def test_orphan_temp_file_does_not_replace_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            concepts = workspace / "state" / "concepts.json"
            original = concepts.read_bytes()
            (workspace / "state" / ".concepts.json.crashed.tmp").write_text("{broken")
            completed = run_cli("rebuild", str(workspace))
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertNotEqual(concepts.read_bytes(), b"{broken")
            self.assertEqual(json.loads(concepts.read_text())["concepts"], [])
            self.assertEqual(original, concepts.read_bytes())

    def test_orphan_log_temp_cannot_corrupt_the_committed_event_log(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            common = (
                "--concept",
                "atomic-log",
                "--score",
                "0.9",
                "--hint-level",
                "0",
                "--item-version",
                "v1",
                "--content-version",
                "sha256:" + "a" * 64,
                "--source-id",
                "fixture",
                "--source-version",
                "2026-08-04",
            )
            first = run_cli(
                "observe",
                str(workspace),
                "--response",
                "First complete response.",
                "--session",
                "session-1",
                "--dimension",
                "application",
                "--item",
                "item-1",
                "--timestamp",
                "2026-08-04T10:01:00Z",
                *common,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            orphan = workspace / "state" / ".sessions.jsonl.crashed.tmp"
            orphan.write_text('{"partial":', encoding="utf-8")

            second = run_cli(
                "observe",
                str(workspace),
                "--response",
                "Second complete response.",
                "--session",
                "session-2",
                "--dimension",
                "recall",
                "--item",
                "item-2",
                "--timestamp",
                "2026-08-05T10:01:00Z",
                *common,
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            committed = (workspace / "state" / "sessions.jsonl").read_text(
                encoding="utf-8"
            )
            records = [json.loads(line) for line in committed.splitlines()]
            self.assertEqual(len(records), 2)
            self.assertTrue(orphan.is_file())

    def test_event_identifier_is_bound_to_the_complete_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "course"
            self.init_workspace(workspace)
            recorded = run_cli(
                "observe",
                str(workspace),
                "--response",
                "The event identifier must bind this exact response.",
                "--session",
                "session-1",
                "--concept",
                "bound-id",
                "--dimension",
                "application",
                "--score",
                "0.9",
                "--hint-level",
                "0",
                "--item",
                "item-1",
                "--item-version",
                "v1",
                "--content-version",
                "sha256:" + "c" * 64,
                "--source-id",
                "fixture",
                "--source-version",
                "2026-08-04",
                "--timestamp",
                "2026-08-04T10:01:00Z",
            )
            self.assertEqual(recorded.returncode, 0, recorded.stderr)
            log = workspace / "state" / "sessions.jsonl"
            event = json.loads(log.read_text(encoding="utf-8"))
            event["response"] = "A different response with the old event identifier."
            log.write_text(json.dumps(event) + "\n", encoding="utf-8")
            rebuilt = run_cli("rebuild", str(workspace))
            self.assertNotEqual(rebuilt.returncode, 0)
            self.assertIn("event_id does not match", rebuilt.stderr)


if __name__ == "__main__":
    unittest.main()
