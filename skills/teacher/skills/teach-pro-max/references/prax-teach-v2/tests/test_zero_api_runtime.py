import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from praxteach import routing as routing_module
from validate_workspace import _schema_instance_errors


class ZeroApiRuntimeTests(unittest.TestCase):
    def test_verifier_binds_every_runtime_verification_input(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "verification.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "verify_visual_runtime.py"),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(
                completed.returncode, 0, completed.stdout + completed.stderr
            )
            receipt = json.loads(output.read_text())
        self.assertEqual(receipt["network_scan"], "passed")
        self.assertIs(receipt["external_human_learning_gates_satisfied"], False)
        self.assertEqual(receipt["bindings"], routing_module.runtime_bindings(ROOT))
        self.assertEqual(
            set(receipt["bindings"]),
            {
                "source",
                "dist",
                "manifest",
                "tests",
                "contracts",
                "build",
                "routing",
                "verifier",
            },
        )

    def test_verifier_refuses_to_replace_a_symlink_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            sentinel = directory / "sentinel.json"
            sentinel.write_text("outside\n", encoding="utf-8")
            output = directory / "verification.json"
            output.symlink_to(sentinel)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "verify_visual_runtime.py"),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "outside\n")

    def test_visual_schemas_accept_shipped_lessons_and_generated_receipt(self) -> None:
        lesson_schema = json.loads(
            (
                ROOT / "runtime/prax-visual-lab/contracts/visual-lesson.schema.json"
            ).read_text(encoding="utf-8")
        )
        for path in sorted((ROOT / "examples/visual-lab").glob("*/lesson.json")):
            lesson = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(
                _schema_instance_errors(lesson, lesson_schema, lesson_schema, "lesson"),
                [],
                path,
            )

        generated = subprocess.run(
            [
                "node",
                "--input-type=module",
                "-e",
                """
import { readFile } from "node:fs/promises";
import { createReceipt, createSession } from "./runtime/prax-visual-lab/src/core.mjs";
const lesson = JSON.parse(await readFile("./examples/visual-lab/python-floating-point/lesson.json", "utf8"));
const session = createSession(lesson, { transfer: { item_id: "float-transfer", pass: true } });
process.stdout.write(JSON.stringify(createReceipt(session)));
""",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(generated.returncode, 0, generated.stderr)
        receipt = json.loads(generated.stdout)
        receipt_schema = json.loads(
            (
                ROOT / "runtime/prax-visual-lab/contracts/learning-receipt.schema.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            _schema_instance_errors(receipt, receipt_schema, receipt_schema, "receipt"),
            [],
        )
        self.assertTrue(
            _schema_instance_errors(
                receipt | {"actions": [7]},
                receipt_schema,
                receipt_schema,
                "receipt",
            )
        )
        self.assertTrue(
            _schema_instance_errors(
                receipt | {"attempts": -1},
                receipt_schema,
                receipt_schema,
                "receipt",
            )
        )

    def test_visual_lesson_schema_matches_runtime_shape_boundaries(self) -> None:
        schema = json.loads(
            (
                ROOT / "runtime/prax-visual-lab/contracts/visual-lesson.schema.json"
            ).read_text(encoding="utf-8")
        )
        valid = json.loads(
            (ROOT / "examples/visual-lab/python-floating-point/lesson.json").read_text()
        )
        cases = [
            valid,
            valid | {"script": "forged"},
            valid | {"lesson_id": "x"},
            valid | {"lesson_version": "broken"},
            valid | {"states": []},
            valid | {"static_fallback": []},
            valid | {"hints": [7]},
        ]
        completed = subprocess.run(
            [
                "node",
                "--input-type=module",
                "-e",
                """
import { validateLesson } from "./runtime/prax-visual-lab/src/core.mjs";
const cases = JSON.parse(process.argv[1]);
process.stdout.write(JSON.stringify(cases.map((item) => {
  try { validateLesson(item); return true; } catch { return false; }
})));
""",
                json.dumps(cases),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        runtime_accepts = json.loads(completed.stdout)
        schema_accepts = [
            not _schema_instance_errors(item, schema, schema, "lesson")
            for item in cases
        ]
        self.assertEqual(runtime_accepts, schema_accepts)
        self.assertEqual(
            runtime_accepts, [True, False, False, False, False, False, False]
        )

    def test_browser_inspection_includes_the_visual_runtime(self) -> None:
        receipt = json.loads(
            (ROOT / "evidence/inspection/browser.json").read_text(encoding="utf-8")
        )
        pages = {item["path"] for item in receipt["planned_pages"]}
        self.assertIn("runtime/prax-visual-lab/dist/index.html", pages)


if __name__ == "__main__":
    unittest.main()
