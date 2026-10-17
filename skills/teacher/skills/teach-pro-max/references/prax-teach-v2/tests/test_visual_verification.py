#!/usr/bin/env python3
"""Black-box verification of delivered visual bytes and retrieval safety."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "prax_teach.py"
RENDERER = ROOT / "scripts" / "render_markdown.mjs"
FIXED_ENV = {**os.environ, "SOURCE_DATE_EPOCH": "1785844800"}


class VisualVerificationTests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), *arguments],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            env=FIXED_ENV,
        )

    def make_case(
        self,
        base: Path,
        *,
        route: str,
        markdown: str,
        retrieval: bool = True,
        forbidden: list[str] | None = None,
        name: str = "lesson",
    ) -> dict[str, Path]:
        base = base.resolve()
        source = base / f"{name}.md"
        html = base / f"{name}.html"
        route_output = base / f"{name}-route.json"
        rubric = base / f"{name}-rubric.json"
        receipt = base / f"{name}-receipt.json"
        source.write_text(markdown, encoding="utf-8")
        route_command = [
            "visual-route",
            "--job",
            "Verify a bounded learning representation",
            "--force",
            route,
        ]
        if retrieval:
            route_command.append("--retrieval")
        routed = self.run_cli(*route_command)
        self.assertEqual(routed.returncode, 0, routed.stderr)
        route_output.write_text(
            json.dumps(json.loads(routed.stdout), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        rubric.write_text(
            json.dumps(
                {
                    "forbidden_answer_terms": forbidden or [],
                    "retrieval": retrieval,
                    "schema_version": 1,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        rendered = subprocess.run(
            [
                "node",
                str(RENDERER),
                "--trusted-root",
                str(base),
                str(source),
                str(html),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            env=FIXED_ENV,
        )
        self.assertEqual(rendered.returncode, 0, rendered.stderr)
        return {
            "html": html,
            "receipt": receipt,
            "route": route_output,
            "rubric": rubric,
            "source": source,
        }

    def verify(
        self, case: dict[str, Path], *, check: bool = False
    ) -> subprocess.CompletedProcess[str]:
        arguments = [
            "visual-verify",
            "--route-output",
            str(case["route"]),
            "--source",
            str(case["source"]),
            "--html",
            str(case["html"]),
            "--forbidden-answer-file",
            str(case["rubric"]),
            "--receipt",
            str(case["receipt"]),
        ]
        if check:
            arguments.append("--check")
        return self.run_cli(*arguments)

    def test_all_four_routes_verify_fallback_and_packaged_runtime_delivery(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            for route in ("none", "static", "interactive", "motion"):
                with self.subTest(route=route):
                    visual = (
                        ""
                        if route == "none"
                        else (
                            "\n| Case | Learner choice |\n"
                            "| --- | --- |\n"
                            "| A | Compare the evidence |\n"
                        )
                    )
                    case = self.make_case(
                        base,
                        route=route,
                        name=route,
                        forbidden=["hidden solution"],
                        markdown=(
                            f"# {route.title()} route\n\n"
                            "## Your attempt\n\n"
                            "Choose a defensible next step before feedback.\n"
                            f"{visual}"
                        ),
                    )
                    completed = self.verify(case)
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    result = json.loads(completed.stdout)
                    self.assertEqual(result["route"], route)
                    self.assertEqual(
                        result["requested_runtime_applicable"],
                        route in {"interactive", "motion"},
                    )
                    self.assertFalse(result["requested_runtime_verified"])
                    self.assertEqual(
                        result["checks"]["static_fallback_verified"],
                        route != "none",
                    )
                    checked = self.verify(case, check=True)
                    self.assertEqual(checked.returncode, 0, checked.stderr)

    def test_none_and_visual_routes_fail_when_artifact_shape_disagrees(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            wrong_none = self.make_case(
                base,
                route="none",
                name="wrong-none",
                forbidden=["solution"],
                markdown=(
                    "# Wrong none\n\n## Your attempt\n\nTry first.\n\n"
                    "| A | B |\n| --- | --- |\n| 1 | 2 |\n"
                ),
            )
            self.assertNotEqual(self.verify(wrong_none).returncode, 0)

            missing_static = self.make_case(
                base,
                route="static",
                name="missing-static",
                forbidden=["solution"],
                markdown="# Missing static\n\n## Your attempt\n\nTry first.\n",
            )
            self.assertNotEqual(self.verify(missing_static).returncode, 0)

    def test_visual_route_requires_a_validated_substantive_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            rejected_markdown = {
                "bare-figure": (
                    "<figure><figcaption>Choose a path</figcaption></figure>\n"
                ),
                "empty-table": (
                    "<table><thead><tr><th>---</th></tr></thead>"
                    "<tbody><tr><td>...</td></tr></tbody></table>\n"
                ),
            }
            for name, fallback in rejected_markdown.items():
                with self.subTest(case=name):
                    case = self.make_case(
                        base,
                        route="static",
                        retrieval=False,
                        name=name,
                        markdown=f"# Invalid fallback\n\n{fallback}",
                    )
                    rejected = self.verify(case)
                    self.assertNotEqual(rejected.returncode, 0)
                    self.assertIn("static fallback", rejected.stderr.lower())

            fake_png = base / "words.png"
            fake_png.write_text(
                "this filename is not a renderable image\n", encoding="utf-8"
            )
            text_suffixed = self.make_case(
                base,
                route="static",
                retrieval=False,
                name="text-suffixed",
                markdown="# Invalid image\n\n![Prompt diagram](words.png)\n",
            )
            rejected_image = self.verify(text_suffixed)
            self.assertNotEqual(rejected_image.returncode, 0)
            self.assertIn("png", rejected_image.stderr.lower())

            malformed_svg = base / "malformed.svg"
            malformed_svg.write_text(
                "plain text with an svg suffix\n", encoding="utf-8"
            )
            malformed = self.make_case(
                base,
                route="static",
                retrieval=False,
                name="malformed-svg",
                markdown="# Invalid SVG\n\n![Prompt diagram](malformed.svg)\n",
            )
            rejected_svg = self.verify(malformed)
            self.assertNotEqual(rejected_svg.returncode, 0)
            self.assertIn("svg", rejected_svg.stderr.lower())

    def test_valid_static_png_jpeg_svg_and_semantic_table_are_verified(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            (base / "pixel.png").write_bytes(
                base64.b64decode(
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC"
                    "AAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
                )
            )
            (base / "pixel.jpg").write_bytes(
                base64.b64decode(
                    "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////"
                    "////////////////////////////////////////////////2wBDAf//////////////////"
                    "////////////////////////////////////////////////////////////////////wAAR"
                    "CAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAf/xAAUEAEAAAAAAAAAAAAA"
                    "AAAAAAAA/9oADAMBAAIQAxAAAAF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABBQJ/"
                    "/8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAwEBPwF//8QAFBEBAAAAAAAAAAAAAAAAAAAA"
                    "AP/aAAgBAgEBPwF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQAGPwJ//8QAFBABAAAA"
                    "AAAAAAAAAAAAAAAAAP/aAAgBAQABPyF//9oADAMBAAIAAwAAABD/xAAUEQEAAAAAAAAAAAAA"
                    "AAAAAAAA/9oACAEDAQE/EB//xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAECAQE/EB//xAAU"
                    "EAEAAAAAAAAAAAAAAAAAAAAA/9oACAEBAAE/EB//2Q=="
                )
            )
            (base / "diagram.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">'
                '<title>Two choices</title><path d="M1 1h18v18H1z"/></svg>\n',
                encoding="utf-8",
            )
            fallbacks = {
                "png": "![Prompt diagram](pixel.png)",
                "jpeg": "![Prompt diagram](pixel.jpg)",
                "svg": "![Prompt diagram](diagram.svg)",
                "table": "| Choice | Evidence |\n| --- | --- |\n| A | Compare first |",
            }
            for name, fallback in fallbacks.items():
                with self.subTest(case=name):
                    case = self.make_case(
                        base,
                        route="static",
                        retrieval=False,
                        name=f"valid-{name}",
                        markdown=f"# Valid fallback\n\n{fallback}\n",
                    )
                    completed = self.verify(case)
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    result = json.loads(completed.stdout)
                    self.assertTrue(result["checks"]["static_fallback_verified"])
                    self.assertFalse(
                        result["checks"]["raster_semantics_automatically_verified"]
                    )

    def test_leakage_is_rejected_in_raw_hidden_and_encoded_surfaces(self) -> None:
        leaking_fragments = {
            "visible": "The secret answer is shown.",
            "comment": "<!-- secret answer -->",
            "details": "<details><summary>Open</summary>secret answer</details>",
            "default-state": (
                "<details open><summary>Open by default</summary>"
                "secret answer</details>"
            ),
            "entity": "s&#x65;cret answer",
            "unicode": "ＳＥＣＲＥＴ　ＡＮＳＷＥＲ",
        }
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            for name, fragment in leaking_fragments.items():
                with self.subTest(surface=name):
                    case = self.make_case(
                        base,
                        route="none",
                        name=f"leak-{name}",
                        forbidden=["secret answer"],
                        markdown=(
                            "# Retrieval\n\n## Your attempt\n\n"
                            f"Try before feedback.\n\n{fragment}\n"
                        ),
                    )
                    rejected = self.verify(case)
                    self.assertNotEqual(rejected.returncode, 0)
                    self.assertIn("forbidden answer", rejected.stderr.lower())

            caption = self.make_case(
                base,
                route="static",
                name="leak-caption",
                forbidden=["secret answer"],
                markdown=(
                    "# Retrieval\n\n## Your attempt\n\nTry before feedback.\n\n"
                    "<table><caption>secret answer</caption><thead><tr>"
                    "<th>Case</th></tr></thead><tbody><tr><td>A</td></tr>"
                    "</tbody></table>\n"
                ),
            )
            rejected_caption = self.verify(caption)
            self.assertNotEqual(rejected_caption.returncode, 0)
            self.assertIn("forbidden answer", rejected_caption.stderr.lower())

    def test_alt_text_linked_svg_and_opaque_media_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            safe_svg = base / "safe.svg"
            safe_svg.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg"><title>Prompt</title>'
                "<text>Choose one path</text></svg>\n",
                encoding="utf-8",
            )
            alt_leak = self.make_case(
                base,
                route="static",
                name="alt-leak",
                forbidden=["secret answer"],
                markdown=(
                    "# Diagram\n\n## Your attempt\n\nChoose first.\n\n"
                    "![secret answer](safe.svg)\n"
                ),
            )
            rejected_alt = self.verify(alt_leak)
            self.assertNotEqual(rejected_alt.returncode, 0)
            self.assertIn("forbidden answer", rejected_alt.stderr.lower())

            leaking_svg = base / "leak.svg"
            leaking_svg.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg"><title>secret answer</title>'
                "<text>Prompt</text></svg>\n",
                encoding="utf-8",
            )
            asset_leak = self.make_case(
                base,
                route="static",
                name="asset-leak",
                forbidden=["secret answer"],
                markdown=(
                    "# Diagram\n\n## Your attempt\n\nChoose first.\n\n"
                    "![Prompt diagram](leak.svg)\n"
                ),
            )
            rejected_asset = self.verify(asset_leak)
            self.assertNotEqual(rejected_asset.returncode, 0)
            self.assertIn("forbidden answer", rejected_asset.stderr.lower())

            (base / "opaque.png").write_bytes(b"\x89PNG\r\n\x1a\nnot-reviewed")
            opaque = self.make_case(
                base,
                route="static",
                name="opaque",
                forbidden=["secret answer"],
                markdown=(
                    "# Diagram\n\n## Your attempt\n\nChoose first.\n\n"
                    "![Prompt diagram](opaque.png)\n"
                ),
            )
            rejected_opaque = self.verify(opaque)
            self.assertNotEqual(rejected_opaque.returncode, 0)
            self.assertIn("opaque", rejected_opaque.stderr.lower())

    def test_missing_attempt_broken_links_and_stale_evidence_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            no_attempt = self.make_case(
                base,
                route="none",
                name="no-attempt",
                forbidden=["secret answer"],
                markdown="# Retrieval\n\nRead this prompt.\n",
            )
            self.assertNotEqual(self.verify(no_attempt).returncode, 0)

            broken = self.make_case(
                base,
                route="none",
                name="broken",
                forbidden=["secret answer"],
                markdown=(
                    "# Retrieval\n\n## Your attempt\n\n"
                    "[Inspect the missing companion](missing.md).\n"
                ),
            )
            self.assertNotEqual(self.verify(broken).returncode, 0)

            valid = self.make_case(
                base,
                route="none",
                name="stale",
                forbidden=["secret answer"],
                markdown="# Retrieval\n\n## Your attempt\n\nTry first.\n",
            )
            self.assertEqual(self.verify(valid).returncode, 0)
            valid["rubric"].write_text(
                json.dumps(
                    {
                        "forbidden_answer_terms": ["a different answer"],
                        "retrieval": True,
                        "schema_version": 1,
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            stale_receipt = self.verify(valid, check=True)
            self.assertNotEqual(stale_receipt.returncode, 0)

            valid["source"].write_text(
                valid["source"].read_text(encoding="utf-8") + "\nChanged.\n",
                encoding="utf-8",
            )
            stale_html = self.verify(valid)
            self.assertNotEqual(stale_html.returncode, 0)


if __name__ == "__main__":
    unittest.main()
