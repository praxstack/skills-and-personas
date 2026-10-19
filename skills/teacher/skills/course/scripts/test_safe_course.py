from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from safe_course import optional_confined_file, validate_course_manifest


class SafeCourseTests(unittest.TestCase):
    def fixture(self, root: Path) -> Path:
        course = root / "course"
        (course / "lessons").mkdir(parents=True)
        (course / "shared.js").write_text("window.MODEL = {};")
        (course / "lessons/a.lesson.js").write_text("window.LESSON = {};")
        (course / "course.json").write_text(json.dumps({
            "id": "course-one",
            "shared": ["shared.js"],
            "lessons": [{"id": "lesson-one", "file": "lessons/a.lesson.js"}],
        }))
        return course

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
