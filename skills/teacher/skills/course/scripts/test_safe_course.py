from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from safe_course import optional_confined_file, validate_course_manifest, read_bound_file, snapshot_course, publish_bound_file


class SafeCourseTests(unittest.TestCase):
    def fixture(self, root: Path) -> Path:
        course = root.resolve() / "course"
        (course / "lessons").mkdir(parents=True)
        (course / "shared.js").write_text("window.MODEL = {};")
        (course / "lessons/a.lesson.js").write_text("window.LESSON = {};")
        (course / "course.json").write_text(json.dumps({
            "id": "course-one",
            "shared": ["shared.js"],
            "lessons": [{"id": "lesson-one", "file": "lessons/a.lesson.js"}],
        }))
        return course

    def test_snapshot_uses_captured_bytes_after_original_is_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            course = self.fixture(Path(tmp))
            with snapshot_course(course) as snapshot:
                lesson = course / "lessons/a.lesson.js"
                lesson.unlink()
                lesson.symlink_to("/etc/passwd")
                self.assertEqual((snapshot / "lessons/a.lesson.js").read_text(), "window.LESSON = {};")

    def test_open_descriptor_does_not_follow_replaced_parent(self):
        from unittest import mock
        import safe_course
        with tempfile.TemporaryDirectory() as tmp:
            course = self.fixture(Path(tmp))
            real_open = os.open
            def swapping_open(path, flags, *args, **kwargs):
                fd = real_open(path, flags, *args, **kwargs)
                if path == "lessons":
                    (course / "lessons").rename(course / "old-lessons")
                    (course / "lessons").symlink_to(Path(tmp))
                return fd
            with mock.patch.object(safe_course.os, "open", side_effect=swapping_open):
                self.assertEqual(read_bound_file(course, "lessons/a.lesson.js"), b"window.LESSON = {};")

    def test_publish_replaces_link_without_modifying_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            output = root / "videos"
            output.mkdir()
            private = root / "private"
            private.write_bytes(b"secret")
            (output / "lesson.mp4").symlink_to(private)
            staged = root / "staged"
            staged.write_bytes(b"render")
            publish_bound_file(output, "lesson.mp4", staged)
            self.assertEqual(private.read_bytes(), b"secret")
            self.assertEqual((output / "lesson.mp4").read_bytes(), b"render")

    def test_linked_course_keeps_manifest_beside_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            course = self.fixture(root)
            catalog = root / "catalog"
            catalog.mkdir()
            (catalog / "alias").symlink_to(course)
            (catalog / "videos.json").write_text('{"course-one/lesson-one.mp4":"https://example.com/video.mp4"}')
            with snapshot_course(catalog / "alias") as snapshot:
                self.assertIn("example.com/video.mp4", (snapshot.parent / "videos.json").read_text())

    def test_reserved_landing_lesson_id_is_rejected_before_build(self):
        import subprocess
        for ident in ("index", "INDEX"):
            with self.subTest(ident=ident), tempfile.TemporaryDirectory() as tmp:
                course = self.fixture(Path(tmp))
                manifest = json.loads((course / "course.json").read_text())
                manifest["lessons"][0]["id"] = ident
                (course / "course.json").write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError, "reserved"):
                    validate_course_manifest(course)
                output = Path(tmp) / "output"
                result = subprocess.run([sys.executable, str(Path(__file__).with_name("build_course.py")), str(course), "-o", str(output), "--trust-authored-code"], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("reserved", result.stderr)
                self.assertFalse((output / "index.html").exists())

    def test_actual_builder_defends_reserved_output_path(self):
        from unittest import mock
        import build_course
        from safe_course import ValidatedCourse
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = {"id": "one", "lessons": [{"id": "index", "kind": "explorable"}]}
            validated = ValidatedCourse(root, data, (), {"index": root / "input.lesson.js"})
            with mock.patch.object(build_course, "validate_course_manifest", return_value=validated), mock.patch.object(build_course, "extract", return_value=data), mock.patch.object(build_course, "load_manifest", return_value={}):
                with self.assertRaisesRegex(SystemExit, "reserved"):
                    build_course.build_course.__wrapped__(root, root / "out", trust_authored_code=True)
            self.assertFalse((root / "out/index.html").exists())

    def test_valid_manifest_resolves_owned_regular_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = validate_course_manifest(self.fixture(Path(tmp)))
            self.assertEqual(set(result.lessons), {"lesson-one"})
            self.assertEqual(len(result.shared), 1)

    def test_traversal_absolute_and_linked_inputs_fail(self):
        for bad in ("../secret.lesson.js", "/tmp/secret.lesson.js"):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                course = self.fixture(root)
                data = json.loads((course / "course.json").read_text())
                data["lessons"][0]["file"] = bad
                (course / "course.json").write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    validate_course_manifest(course)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            course = self.fixture(root)
            secret = root / "secret.lesson.js"
            secret.write_text("secret")
            (course / "lessons/a.lesson.js").unlink()
            (course / "lessons/a.lesson.js").symlink_to(secret)
            with self.assertRaises(ValueError):
                validate_course_manifest(course)

    def test_hard_linked_video_is_not_a_course_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            course = self.fixture(root)
            (course / "videos").mkdir()
            secret = root / "secret.mp4"
            secret.write_bytes(b"secret")
            os.link(secret, course / "videos/lesson-one.mp4")
            with self.assertRaises(ValueError):
                optional_confined_file(course, Path("videos/lesson-one.mp4"), "video")


if __name__ == "__main__":
    unittest.main()
