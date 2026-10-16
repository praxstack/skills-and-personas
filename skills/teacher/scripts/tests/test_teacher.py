#!/usr/bin/env python3
"""Fast checks for the teacher package. Standard library only.

  python3 scripts/tests/test_teacher.py -v

Browser and video checks live in run_all.sh, which calls this first.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "skills"
NATIVE = ["lesson-notebook", "explorable", "concept-animation", "explain-diagram", "visual-qa"]
PY = sys.executable


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([PY, *args], capture_output=True, text=True, cwd=cwd)


def frontmatter(path: Path) -> dict:
    text = path.read_text()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, f"{path}: no frontmatter"
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip().strip("'\"")
    return out


def strip_code(text: str) -> str:
    return re.sub(r"```.*?```", "", text, flags=re.S)


class SkillFormat(unittest.TestCase):
    def skill_dirs(self):
        return [ROOT] + [SKILLS / n for n in NATIVE]

    def test_frontmatter(self):
        for d in self.skill_dirs():
            fm = frontmatter(d / "SKILL.md")
            self.assertEqual(fm.get("name"), d.name, d)
            desc = fm.get("description", "")
            self.assertTrue(1 <= len(desc) <= 1024, f"{d.name}: description is {len(desc)} chars")
            self.assertNotRegex(desc, r"[<>]", d.name)
            self.assertLessEqual(set(fm), {"name", "description"}, d.name)

    def test_length_and_layout(self):
        for d in self.skill_dirs():
            self.assertLessEqual(len((d / "SKILL.md").read_text().splitlines()), 500, d.name)
            self.assertFalse((d / "README.md").exists(), f"{d.name}: README.md at the top level")
            allowed = {"scripts", "references", "assets"} | ({"skills"} if d == ROOT else set())
            extra = {p.name for p in d.iterdir() if p.is_dir()} - allowed
            self.assertFalse(extra, f"{d.name}: unexpected folders {extra}")

    def test_no_persona_statements(self):
        files = [ROOT / "SKILL.md", *ROOT.glob("references/*.md")] + [f for n in NATIVE for f in (SKILLS / n).rglob("*.md")]
        for f in files:
            self.assertIsNone(re.search(r"(?im)^\s*You are\s+(a|an|the)\s", strip_code(f.read_text())), f)

    def test_no_em_dashes_in_our_prose(self):
        files = [ROOT / "SKILL.md", *ROOT.glob("references/*.md")] + [f for n in NATIVE for f in (SKILLS / n).rglob("*.md")]
        for f in files:
            self.assertNotIn("—", f.read_text(), f)

    def test_relative_links_resolve(self):
        files = [ROOT / "SKILL.md", *ROOT.glob("references/*.md")] + [SKILLS / n / "SKILL.md" for n in NATIVE]
        for f in files:
            for target in re.findall(r"\]\(([^)#]+)\)", f.read_text()):
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                self.assertTrue((f.parent / target).exists(), f"{f.relative_to(ROOT)} links to missing {target}")

    def test_repo_lint_on_native_skills(self):
        lint_dir = ROOT.parents[1] / "new-skills" / "_audit"
        if not (lint_dir / "lint.py").exists():
            self.skipTest("repo lint not present (standalone copy)")
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("pyyaml not installed")
        sys.path.insert(0, str(lint_dir))
        import lint  # type: ignore

        for n in NATIVE:
            fails = [i for i in lint.lint_skill(SKILLS / n) if i[0] == "FAIL"]
            self.assertEqual(fails, [], n)


class Registry(unittest.TestCase):
    def setUp(self):
        self.reg = json.loads((ROOT / "assets" / "registry.json").read_text())

    def test_shape(self):
        ids = [t["id"] for t in self.reg["tools"]]
        self.assertEqual(len(ids), len(set(ids)), "duplicate ids")
        for t in self.reg["tools"]:
            self.assertTrue(set(t["jobs"]) <= set(self.reg["jobs"]), t["id"])
            self.assertTrue(t["media"] and set(t["media"]) <= set(self.reg["media"]), t["id"])
            self.assertTrue(set(t.get("probe", {})) <= {"bins", "py", "node", "mcp", "net"}, t["id"])
            self.assertIn("how", t, t["id"])

    def test_skill_paths_exist(self):
        for t in self.reg["tools"]:
            skill = t["how"].get("skill")
            if skill:
                self.assertTrue((ROOT / skill).is_file(), f"{t['id']}: {skill}")

    def test_refs_point_into_teach_pro_max_registry(self):
        tpm = json.loads((SKILLS / "teach-pro-max/references/prax-teach-v2/references/visualization-tool-registry.json").read_text())
        known = {t["id"] for t in tpm["tools"]}
        for t in self.reg["tools"]:
            if "ref" in t:
                self.assertIn(t["ref"], known, t["id"])

    def test_cdn_urls_are_pinned_and_allowed(self):
        for t in self.reg["tools"]:
            url = t["how"].get("cdn")
            if not url:
                continue
            self.assertRegex(url, r"^https://(cdnjs\.cloudflare\.com/ajax/libs/|cdn\.jsdelivr\.net/npm/|unpkg\.com/)", t["id"])
            self.assertRegex(url, r"\d+\.\d+\.\d+", f"{t['id']}: not pinned")


class Scripts(unittest.TestCase):
    def test_vendor_verify(self):
        r = run(str(ROOT / "scripts/vendor.py"), "verify")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_find_tool_ranks_bundled_first(self):
        r = run(str(ROOT / "scripts/find_tool.py"), "--job", "cause", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        rows = json.loads(r.stdout)
        self.assertEqual(rows[0]["id"], "explorable")
        r = run(str(ROOT / "scripts/find_tool.py"), "--job", "structure", "--medium", "still", "--offline", "--json")
        self.assertTrue(all(row["id"] not in ("mermaid", "kroki") for row in json.loads(r.stdout)), "offline filter")

    def test_series_flow(self):
        s = str(ROOT / "scripts/series.py")
        with tempfile.TemporaryDirectory() as tmp:
            self.assertNotEqual(run(s, "status", cwd=Path(tmp)).returncode, 0, "status without consent must refuse")
            for args in (["init", "--learner", "L", "--goal", "g"], ["thread", "add", "t", "--title", "T", "--level", "L1"],
                         ["log", "t", "--did", "x", "--missed", "y", "--tried", "analogy"], ["recall", "add", "t", "point one"],
                         ["recall", "result", "t", "0", "--right", "--unaided"]):
                r = run(s, *args, cwd=Path(tmp))
                self.assertEqual(r.returncode, 0, r.stderr)
            j = json.loads((Path(tmp) / ".teacher/journal.json").read_text())
            self.assertFalse(j["threads"]["t"]["recall"][0]["demonstrated"], "same-session answers don't count")
            out = run(s, "resume", cwd=Path(tmp)).stdout
            self.assertIn("point one", out)
            self.assertIn("analogy", out)
            run(s, "recall", "result", "t", "0", "--right", "--unaided", cwd=Path(tmp))
            run(s, "satisfied", "t", cwd=Path(tmp))
            j = json.loads((Path(tmp) / ".teacher/journal.json").read_text())
            self.assertTrue(j["threads"]["t"]["recall"][0]["demonstrated"])
            self.assertEqual(j["threads"]["t"]["status"], "satisfied")
            self.assertIn("Satisfied in session 2", (Path(tmp) / ".teacher/JOURNAL.md").read_text())
            self.assertNotEqual(run(s, "forget", cwd=Path(tmp)).returncode, 0, "forget needs --yes")
            run(s, "forget", "--yes", cwd=Path(tmp))
            self.assertFalse((Path(tmp) / ".teacher").exists())


class Builds(unittest.TestCase):
    def check_single_file(self, html: str):
        self.assertNotRegex(html, r"<script[^>]+src=", "external script")
        self.assertNotRegex(html, r"<link[^>]+stylesheet", "external stylesheet")
        self.assertNotRegex(html, r"\bimport\s.*\bfrom\s", "a module import survived bundling")
        self.assertIn("data:font/woff2;base64,", html)
        self.assertLess(len(html), 1_000_000)

    def test_explorable_builds(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "s.html"
            r = run(str(SKILLS / "explorable/scripts/build.py"), str(SKILLS / "explorable/assets/examples/seasons.lesson.js"), "-o", str(out))
            self.assertEqual(r.returncode, 0, r.stderr)
            html = out.read_text()
            self.check_single_file(html)
            self.assertTrue(html.startswith("<!doctype html>"))
            r = run(str(SKILLS / "explorable/scripts/build.py"), str(SKILLS / "explorable/assets/examples/seasons.lesson.js"), "-o", str(out), "--fragment")
            self.assertFalse(out.read_text().lstrip().startswith("<!doctype"), "fragment has no document skeleton")

    def test_animation_builds(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "n.html"
            r = run(str(SKILLS / "concept-animation/scripts/build.py"), str(SKILLS / "concept-animation/assets/examples/neuron.anim.js"), "-o", str(out))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.check_single_file(out.read_text())

    def test_bundler_refuses_name_clash(self):
        sys.path.insert(0, str(SKILLS / "lesson-notebook/scripts"))
        import bundle  # type: ignore

        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.js", Path(tmp) / "b.js"
            a.write_text("export function twice() {}\n")
            b.write_text("const twice = 1;\n")
            with self.assertRaises(SystemExit):
                bundle.join_modules([a, b])

    def test_diagram_page_needs_a_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            svg = Path(tmp) / "x.svg"
            svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100" viewBox="0 0 200 100"><script>alert(1)</script><rect width="200" height="100" onclick="x()"/></svg>')
            r = run(str(SKILLS / "explain-diagram/scripts/render.py"), str(svg), "--page", str(Path(tmp) / "x.html"), "--offline")
            self.assertNotEqual(r.returncode, 0, "a page without a claim must be refused")
            r = run(str(SKILLS / "explain-diagram/scripts/render.py"), str(svg), "--page", str(Path(tmp) / "x.html"), "--offline", "--claim", "A box", "--why", "w", "--how", "h", "--look-for", "l")
            self.assertEqual(r.returncode, 0, r.stderr)
            page = (Path(tmp) / "x.html").read_text()
            self.assertNotIn("alert(1)", page)
            self.assertNotIn("onclick", page)
            self.assertIn('aria-label="A box"', page)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg not installed")
class VideoChecker(unittest.TestCase):
    def test_flags_missing_captions_then_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            clip = Path(tmp) / "c.mp4"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30:duration=3", "-pix_fmt", "yuv420p", str(clip)], check=True)
            chk = str(SKILLS / "visual-qa/scripts/check_video.py")
            r = run(chk, str(clip), "--json")
            self.assertEqual(r.returncode, 1)
            self.assertTrue(any("captions" in p for p in json.loads(r.stdout)["problems"]))
            clip.with_suffix(".vtt").write_text("WEBVTT\n\n1\n00:00:00.000 --> 00:00:03.000\nhello\n")
            r = run(chk, str(clip), "--sheet", str(Path(tmp) / "s.png"))
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertTrue((Path(tmp) / "s.png").exists())

    def test_flags_black_and_small(self):
        with tempfile.TemporaryDirectory() as tmp:
            clip = Path(tmp) / "b.mp4"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "color=black:size=640x360:rate=30:duration=3", "-pix_fmt", "yuv420p", str(clip)], check=True)
            r = run(str(SKILLS / "visual-qa/scripts/check_video.py"), str(clip), "--json")
            problems = " ".join(json.loads(r.stdout)["problems"])
            self.assertIn("black", problems)
            self.assertIn("under 720", problems)


if __name__ == "__main__":
    unittest.main()
