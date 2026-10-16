"""Regression tests for private, symlink-safe filesystem preparation."""

from __future__ import annotations

import os
import stat
import sys
import tempfile
import unittest
import zipfile
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from praxteach import export as export_module
from praxteach.errors import SafetyError
from praxteach.export import export_workspace
from praxteach.state import initialize_workspace


@contextmanager
def process_umask(mask: int):
    """Temporarily set the process umask for a single-threaded test."""

    previous = os.umask(mask)
    try:
        yield
    finally:
        os.umask(previous)


def permission_bits(path: Path) -> int:
    return stat.S_IMODE(path.stat(follow_symlinks=False).st_mode)


class PrivatePathTest(unittest.TestCase):
    def initialize(self, workspace: Path) -> None:
        initialize_workspace(
            str(workspace),
            learner_id="learner-local-1",
            goal="Private filesystem regression",
            horizon_days=30,
            granted_at="2026-08-04T10:00:00Z",
        )

    def test_nested_workspace_ancestors_are_private_under_umask_022(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            first = base / "workspace-parent"
            second = first / "nested-parent"
            workspace = second / "course"

            with process_umask(0o022):
                self.initialize(workspace)

            self.assertEqual(permission_bits(first), 0o700)
            self.assertEqual(permission_bits(second), 0o700)
            self.assertEqual(permission_bits(workspace), 0o700)

    def test_preexisting_workspace_ancestor_mode_is_not_changed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            existing = base / "shared-parent"
            existing.mkdir(mode=0o755)
            existing.chmod(0o755)

            self.initialize(existing / "private-parent" / "course")

            self.assertEqual(permission_bits(existing), 0o755)
            self.assertEqual(permission_bits(existing / "private-parent"), 0o700)

    def test_nested_export_ancestors_are_private_under_umask_022(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            workspace = base / "course"
            self.initialize(workspace)
            first = base / "export-parent"
            second = first / "nested-parent"
            output = second / "learner-state.zip"

            with process_umask(0o022):
                export_workspace(
                    str(workspace),
                    str(output),
                    exported_at="2026-08-04T11:00:00Z",
                )

            self.assertEqual(permission_bits(first), 0o700)
            self.assertEqual(permission_bits(second), 0o700)
            self.assertEqual(permission_bits(output), 0o600)

    @unittest.skipIf(not hasattr(os, "symlink"), "symlinks unavailable")
    def test_workspace_ancestor_symlink_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            outside = base / "outside"
            outside.mkdir()
            alias = base / "alias"
            alias.symlink_to(outside, target_is_directory=True)

            with self.assertRaises(SafetyError):
                self.initialize(alias / "nested" / "course")

            self.assertEqual(list(outside.iterdir()), [])

    @unittest.skipIf(not hasattr(os, "symlink"), "symlinks unavailable")
    def test_export_ancestor_symlink_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            workspace = base / "course"
            self.initialize(workspace)
            outside = base / "outside"
            outside.mkdir()
            alias = base / "alias"
            alias.symlink_to(outside, target_is_directory=True)

            with self.assertRaises(SafetyError):
                export_workspace(
                    str(workspace),
                    str(alias / "nested" / "learner-state.zip"),
                    exported_at="2026-08-04T11:00:00Z",
                )

            self.assertEqual(list(outside.iterdir()), [])

    def test_export_inside_workspace_does_not_create_rejected_ancestors(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            workspace = base / "course"
            self.initialize(workspace)
            rejected_parent = workspace / "must-not-exist"

            with self.assertRaises(SafetyError):
                export_workspace(
                    str(workspace),
                    str(rejected_parent / "nested" / "learner-state.zip"),
                    exported_at="2026-08-04T11:00:00Z",
                )

            self.assertFalse(rejected_parent.exists())

    @unittest.skipUnless(
        os.name == "posix" and hasattr(os, "symlink"),
        "descriptor-relative POSIX race regression",
    )
    def test_export_parent_swap_cannot_overwrite_workspace_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            workspace = base / "course"
            self.initialize(workspace)
            learner = workspace / "state" / "learner.json"
            learner_before = learner.read_bytes()

            output_parent = base / "exports"
            output_parent.mkdir()
            displaced_parent = base / "exports-displaced"
            output = output_parent / "learner.json"
            original_atomic_write = export_module.atomic_write_anchored

            def swap_parent_then_write(*args, **kwargs):
                output_parent.rename(displaced_parent)
                output_parent.symlink_to(workspace / "state", target_is_directory=True)
                return original_atomic_write(*args, **kwargs)

            with (
                mock.patch.object(
                    export_module,
                    "atomic_write_anchored",
                    side_effect=swap_parent_then_write,
                ),
                self.assertRaises(SafetyError),
            ):
                export_workspace(
                    str(workspace),
                    str(output),
                    exported_at="2026-08-04T11:00:00Z",
                )

            self.assertEqual(learner.read_bytes(), learner_before)
            self.assertTrue(output_parent.is_symlink())
            self.assertFalse((displaced_parent / "learner.json").exists())

    @unittest.skipUnless(
        os.name == "posix" and hasattr(os, "symlink"),
        "descriptor-relative POSIX publish regression",
    )
    def test_export_parent_swap_during_publish_stays_on_held_descriptor(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            workspace = base / "course"
            self.initialize(workspace)
            learner = workspace / "state" / "learner.json"
            learner_before = learner.read_bytes()

            output_parent = base / "exports"
            output_parent.mkdir()
            displaced_parent = base / "exports-displaced"
            output = output_parent / "learner.json"
            original_rename = os.rename
            original_atomic_write = export_module.atomic_write_anchored

            def swap_at_descriptor_rename(source, destination, **kwargs):
                if kwargs.get("src_dir_fd") is not None:
                    original_rename(output_parent, displaced_parent)
                    output_parent.symlink_to(
                        workspace / "state", target_is_directory=True
                    )
                return original_rename(source, destination, **kwargs)

            def write_with_publish_race(*args, **kwargs):
                with mock.patch(
                    "praxteach.io.os.rename", side_effect=swap_at_descriptor_rename
                ):
                    return original_atomic_write(*args, **kwargs)

            with (
                mock.patch.object(
                    export_module,
                    "atomic_write_anchored",
                    side_effect=write_with_publish_race,
                ),
                self.assertRaises(SafetyError),
            ):
                export_workspace(
                    str(workspace),
                    str(output),
                    exported_at="2026-08-04T11:00:00Z",
                )

            self.assertEqual(learner.read_bytes(), learner_before)
            self.assertTrue(output_parent.is_symlink())
            published = displaced_parent / "learner.json"
            self.assertTrue(published.is_file())
            self.assertTrue(zipfile.is_zipfile(published))

    @unittest.skipUnless(os.name == "posix", "POSIX capability contract")
    def test_export_fails_closed_without_descriptor_relative_primitives(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            workspace = base / "course"
            self.initialize(workspace)
            output = base / "exports" / "learner-state.zip"

            with (
                mock.patch(
                    "praxteach.io._supports_secure_directory_fds", return_value=False
                ),
                self.assertRaisesRegex(
                    SafetyError, "descriptor-relative output writes are unavailable"
                ),
            ):
                export_workspace(
                    str(workspace),
                    str(output),
                    exported_at="2026-08-04T11:00:00Z",
                )

            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
