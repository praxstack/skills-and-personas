#!/usr/bin/env python3
"""Black-box, round-trip tests for ecosystem exports."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "export_learning.py"


class TestExportsCli(unittest.TestCase):
    def run_cli(
        self, *args: str, expected: int = 0
    ) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            expected,
            msg=f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )
        return completed

    def write_items(self, path: Path) -> None:
        path.write_text(
            json.dumps(
                {
                    "schema_version": "1",
                    "collection_id": "index-retrieval",
                    "title": "Index selection retrieval",
                    "language": "en",
                    "license": "CC BY 4.0",
                    "source": "https://www.postgresql.org/docs/current/indexes.html",
                    "items": [
                        {
                            "id": "idx-001",
                            "prompt": "Which index property supports a left-anchored range scan?",
                            "answer": "Ordered keys",
                            "explanation": "The ordering lets the engine seek and then scan a contiguous range.",
                            "choices": [
                                "Ordered keys",
                                "Random eviction",
                                "Write-through caching",
                            ],
                            "tags": ["indexes", "application"],
                        },
                        {
                            "id": "idx-002",
                            "prompt": "Explain why column order matters in a composite B-tree index.",
                            "answer": "The usable search prefix follows the index's leading columns.",
                            "explanation": "Later columns cannot generally substitute for a missing leading predicate.",
                            "choices": [],
                            "tags": ["indexes", "explanation"],
                        },
                    ],
                },
                indent=2,
            )
            + "\n"
        )

    def test_all_exports_are_deterministic_and_validate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            source = temp_path / "items.json"
            self.write_items(source)
            suffixes = {
                "anki": ".txt",
                "qti": ".zip",
                "liascript": ".md",
                "h5p": ".h5p",
            }
            for format_name, suffix in suffixes.items():
                with self.subTest(format=format_name):
                    first = temp_path / f"first-{format_name}{suffix}"
                    second = temp_path / f"second-{format_name}{suffix}"
                    result = json.loads(
                        self.run_cli(
                            "export",
                            format_name,
                            str(source),
                            str(first),
                            "--epoch",
                            "1785772800",
                        ).stdout
                    )
                    self.assertEqual(result["format"], format_name)
                    self.run_cli(
                        "export",
                        format_name,
                        str(source),
                        str(second),
                        "--epoch",
                        "1785772800",
                    )
                    self.assertEqual(first.read_bytes(), second.read_bytes())
                    checked = json.loads(
                        self.run_cli("validate", format_name, str(first)).stdout
                    )
                    self.assertTrue(checked["valid"], checked)

    def test_anki_text_is_importable_and_does_not_put_answers_on_fronts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            source = temp_path / "items.json"
            output = temp_path / "deck.txt"
            self.write_items(source)
            self.run_cli("export", "anki", str(source), str(output))
            lines = output.read_text().splitlines()
            self.assertEqual(
                lines[:4],
                [
                    "#separator:tab",
                    "#html:true",
                    "#notetype:Prax Teach Retrieval",
                    "#columns:Front\tBack\tTags",
                ],
            )
            first_front, first_back, first_tags = lines[4].split("\t")
            self.assertNotIn("Ordered keys", first_front)
            self.assertIn("Ordered keys", first_back)
            self.assertEqual(first_tags, "application indexes")

    def test_qti_and_h5p_packages_have_required_root_files_and_no_parent_paths(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            source = temp_path / "items.json"
            self.write_items(source)
            for format_name, suffix, required in (
                (
                    "qti",
                    ".zip",
                    {"imsmanifest.xml", "items/idx-001.xml", "items/idx-002.xml"},
                ),
                ("h5p", ".h5p", {"h5p.json", "content/content.json"}),
            ):
                output = temp_path / f"bundle{suffix}"
                self.run_cli(
                    "export",
                    format_name,
                    str(source),
                    str(output),
                    "--epoch",
                    "1785772800",
                )
                with zipfile.ZipFile(output) as package:
                    names = set(package.namelist())
                    self.assertTrue(required.issubset(names))
                    self.assertTrue(
                        all(
                            not name.startswith(("/", "../")) and "/../" not in name
                            for name in names
                        )
                    )
                    self.assertTrue(
                        all(
                            info.date_time == (2026, 8, 3, 0, 0, 0)
                            for info in package.infolist()
                        )
                    )
                    if format_name == "qti":
                        ElementTree.fromstring(package.read("imsmanifest.xml"))
                        ElementTree.fromstring(package.read("items/idx-001.xml"))
                    else:
                        h5p = json.loads(package.read("h5p.json"))
                        self.assertEqual(h5p["mainLibrary"], "H5P.QuestionSet")
                        content = json.loads(package.read("content/content.json"))
                        self.assertEqual(len(content["questions"]), 2)

    def test_liascript_uses_native_quiz_syntax_and_preserves_text_fallback(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            source = temp_path / "items.json"
            output = temp_path / "course.md"
            self.write_items(source)
            self.run_cli("export", "liascript", str(source), str(output))
            text = output.read_text()
            self.assertIn("[(X)] Ordered keys", text)
            self.assertIn("[( )] Random eviction", text)
            self.assertIn(
                "[[The usable search prefix follows the index's leading columns.]]",
                text,
            )
            self.assertIn("Explanation:", text)


if __name__ == "__main__":
    unittest.main()
