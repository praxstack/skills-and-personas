#!/usr/bin/env python3
"""Fast checks for the teacher package. Standard library only.

  python3 scripts/tests/test_teacher.py -v

Browser and video checks live in run_all.sh, which calls this first.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "skills"
NATIVE = ["lesson-notebook", "explorable", "concept-animation", "explain-diagram", "visual-qa", "course"]
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


def load(path: Path, stub: tuple[str, ...] = ()):
    """Import a script as a module. Names in stub get empty stand-ins, so a
    helper can be tested without the heavy packages its script imports."""
    import importlib
    import importlib.util
    import types

    for name in stub:
        try:
            importlib.import_module(name)
        except ImportError:
            sys.modules[name] = types.ModuleType(name)
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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

    def test_frontmatter_is_valid_yaml(self):
        # Hosts parse the header as YAML: an unquoted ": " in the description breaks it.
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML not installed")
        for d in self.skill_dirs():
            head = (d / "SKILL.md").read_text().split("---")[1]
            try:
                data = yaml.safe_load(head)
            except yaml.YAMLError as e:
                self.fail(f"{d.name}: SKILL.md header is not valid YAML: {str(e).splitlines()[0]}")
            self.assertEqual(data.get("name"), d.name)

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
            self.assertTrue(set(t.get("probe", {})) <= {"bins", "py", "node", "mcp", "net", "cli"}, t["id"])
            self.assertIn("how", t, t["id"])

    def test_skill_paths_exist(self):
        for t in self.reg["tools"]:
            skill = t["how"].get("skill")
            if skill:
                self.assertTrue((ROOT / skill).is_file(), f"{t['id']}: {skill}")

    def test_refs_point_into_teach_pro_max_registry(self):
        tpm = json.loads((ROOT.parent / "teach-pro-max/references/prax-teach-v2/references/visualization-tool-registry.json").read_text())
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

    def test_pen_samples_are_embedded_and_fresh(self):
        r = run(str(SKILLS / "lesson-notebook/scripts/make_pen_samples.py"), "--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        sounds = SKILLS / "lesson-notebook/assets/sounds"
        notes = (sounds / "SOUNDS.md").read_text()
        for f in sorted(sounds.glob("*.mp3")):
            self.assertIn(f"`{f.name}`", notes, f"{f.name} needs a source and licence in SOUNDS.md")
            self.assertLess(f.stat().st_size, 40_000, f"{f.name} is too big to embed in every lesson")

    def test_find_tool_ranks_bundled_first(self):
        r = run(str(ROOT / "scripts/find_tool.py"), "--job", "cause", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        rows = json.loads(r.stdout)
        self.assertEqual(rows[0]["id"], "explorable")
        r = run(str(ROOT / "scripts/find_tool.py"), "--job", "structure", "--medium", "still", "--offline", "--json")
        self.assertTrue(all(row["id"] not in ("mermaid", "kroki") for row in json.loads(r.stdout)), "offline filter")

    def test_explain_practice_reveal_is_not_an_unaided_response(self):
        js = r"""
const src=require('fs').readFileSync(process.argv[1],'utf8');
const fn=src.match(/function explainBox\(step, i\) \{[\s\S]*?\n\}/)[0];
let S,finished; const PRACTICE=true,persist=()=>{},finishStep=()=>{finished=true};
const h=(tag,attrs={},...kids)=>({tag,attrs,children:kids.flat().filter(Boolean),value:'',hidden:attrs.hidden,events:{},addEventListener(k,f){this.events[k]=f},focus(){}});
const put=(node,...kids)=>{node.children=kids};eval(fn);
const walk=n=>typeof n==='object'?[n,...n.children.flatMap(walk)]:[];
const outputs=[];
for(const text of ['', 'short', 'A sufficiently detailed actual response.']){
 S={explained:{},attempts:{}};finished=false;const box=explainBox({ask:{q:'Explain',model:'Model',points:['one']}},0),nodes=walk(box),input=nodes.find(n=>n.tag==='textarea');input.value=text;nodes.find(n=>n.attrs.text==="Compare with the teacher's version").events.click();
 if(text.length<12){if(finished)throw Error('short answer accepted');nodes.find(n=>n.attrs.text==='Show me').events.click();if(!finished||S.explained[0]||S.attempts[0].length!==1||!S.attempts[0][0].asked||S.attempts[0][0].right!==false)throw Error('reveal fabricated response');input.value='edited after seeing model';input.events.change();if(S.explained[0])throw Error('aided edit saved as response')}
 else if(!finished||S.explained[0].text!==text||S.attempts[0].some(a=>a.asked))throw Error('real response lost');outputs.push(text.length);
}console.log(JSON.stringify(outputs));
"""
        result = subprocess.run(["node", "-e", js, str(SKILLS / "explorable/assets/engine/explorable.js")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [0, 5, 40])

    def test_course_layout_supports_prototype_like_lesson_ids(self):
        js = r"""
const src = require('fs').readFileSync(process.argv[1], 'utf8');
const block = src.split('// ---------- order and layout ----------')[1].split('// ---------- header ----------')[0];
const layout = new Function('C', block + ';return {ids:ordered.map(l=>l.id),depths:C.lessons.map(l=>[l.id,typeof layer[l.id],layer[l.id]])}');
console.log(JSON.stringify({prototype:layout({lessons:[{id:'constructor'},{id:'toString',needs:['constructor']},{id:'valueOf',needs:['toString']},{id:'ordinary',needs:['hasOwnProperty']}]}),cycle:layout({lessons:[{id:'a',needs:['b']},{id:'b',needs:['a']}]})}));
"""
        result = subprocess.run(["node", "-e", js, str(SKILLS / "course/assets/engine/course.js")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = json.loads(result.stdout)
        self.assertEqual(out["prototype"]["ids"], ["constructor", "ordinary", "toString", "valueOf"])
        self.assertEqual(out["prototype"]["depths"], [["constructor", "number", 0], ["toString", "number", 1], ["valueOf", "number", 2], ["ordinary", "number", 0]])
        self.assertEqual(out["cycle"]["ids"], ["b", "a"])
        self.assertEqual(out["cycle"]["depths"], [["a", "number", 2], ["b", "number", 1]])

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
            self.assertEqual((Path(tmp) / ".teacher").stat().st_mode & 0o777, 0o700)
            self.assertEqual((Path(tmp) / ".teacher/journal.json").stat().st_mode & 0o777, 0o600)
            self.assertEqual((Path(tmp) / ".teacher/JOURNAL.md").stat().st_mode & 0o777, 0o600)
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

    def test_later_failed_or_aided_recall_returns_and_can_be_reearned(self):
        script = str(ROOT / "scripts/series.py")
        for outcome in (["--wrong", "--unaided"], ["--right"]):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp)
                def cmd(*args):
                    result = run(script, *args, cwd=work)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    return result.stdout
                cmd("init", "--learner", "L", "--goal", "g")
                cmd("thread", "add", "t", "--title", "T", "--level", "L1")
                cmd("recall", "add", "t", "review point")
                cmd("resume")
                cmd("recall", "result", "t", "0", "--right", "--unaided")
                cmd("resume")
                self.assertEqual(cmd("recall", "result", "t", "0", *outcome).strip(), "recorded")
                point = json.loads((work / ".teacher/journal.json").read_text())["threads"]["t"]["recall"][0]
                self.assertFalse(point["demonstrated"])
                self.assertEqual(len(point["results"]), 2)
                self.assertEqual(point["results"][0], {"session": 2, "right": True, "unaided": True})
                self.assertIn("review point", cmd("resume"))
                self.assertEqual(cmd("recall", "result", "t", "0", "--right", "--unaided").strip(), "demonstrated")
                point = json.loads((work / ".teacher/journal.json").read_text())["threads"]["t"]["recall"][0]
                self.assertTrue(point["demonstrated"])
                self.assertEqual(len(point["results"]), 3)

    def test_recall_asked_late_is_no_longer_due(self):
        s = str(ROOT / "scripts/series.py")
        with tempfile.TemporaryDirectory() as tmp:
            run(s, "init", "--learner", "L", "--goal", "g", cwd=Path(tmp))
            run(s, "thread", "add", "t", "--title", "T", "--level", "L1", cwd=Path(tmp))
            run(s, "recall", "add", "t", "late point", cwd=Path(tmp))  # due in 2, 4, 7
            run(s, "resume", cwd=Path(tmp))
            run(s, "resume", cwd=Path(tmp))  # session 3: slot 2 was missed
            run(s, "recall", "result", "t", "0", "--right", cwd=Path(tmp))  # asked, with help
            self.assertNotIn("late point", run(s, "status", cwd=Path(tmp)).stdout, "asked in 3 covers the slot due in 2")
            run(s, "resume", cwd=Path(tmp))  # session 4: the next slot is due
            self.assertIn("late point", run(s, "status", cwd=Path(tmp)).stdout)
            for _ in range(4):
                run(s, "resume", cwd=Path(tmp))  # session 8: every slot (2, 4, 7) has passed
            run(s, "recall", "result", "t", "0", "--right", cwd=Path(tmp))  # asked, with help again
            run(s, "resume", cwd=Path(tmp))
            self.assertIn("late point", run(s, "status", cwd=Path(tmp)).stdout, "not demonstrated yet, so it must come back")

    def test_forget_only_deletes_the_journal(self):
        s = str(ROOT / "scripts/series.py")
        with tempfile.TemporaryDirectory() as tmp:
            keep = Path(tmp) / "notes.txt"
            keep.write_text("mine")
            self.assertNotEqual(run(s, "--dir", ".", "forget", "--yes", cwd=Path(tmp)).returncode, 0, "no journal here")
            self.assertTrue(keep.exists())
            run(s, "--dir", ".", "init", "--learner", "L", "--goal", "g", cwd=Path(tmp))
            self.assertEqual(run(s, "--dir", ".", "forget", "--yes", cwd=Path(tmp)).returncode, 0)
            self.assertFalse((Path(tmp) / "journal.json").exists())
            self.assertFalse((Path(tmp) / "JOURNAL.md").exists())
            self.assertTrue(keep.exists(), "forget must not touch other files")
            own = Path(tmp) / "mine"
            own.mkdir()
            run(s, "--dir", str(own), "init", "--learner", "L", "--goal", "g", cwd=Path(tmp))
            run(s, "--dir", str(own), "forget", "--yes", cwd=Path(tmp))
            self.assertTrue(own.is_dir(), "a --dir folder belongs to the caller")
            run(s, "init", "--learner", "L", "--goal", "g", cwd=Path(tmp))
            run(s, "forget", "--yes", cwd=Path(tmp))
            self.assertFalse((Path(tmp) / ".teacher").exists(), "the default folder goes once empty")

    def test_series_rejects_linked_journal_directory_and_files(self):
        s = str(ROOT / "scripts/series.py")
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            victim = base / "victim"
            victim.mkdir()
            (base / ".teacher").symlink_to(victim, target_is_directory=True)
            r = run(s, "init", "--learner", "L", "--goal", "g", cwd=base)
            self.assertNotEqual(r.returncode, 0)
            self.assertFalse((victim / "journal.json").exists())

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            r = run(s, "init", "--learner", "L", "--goal", "g", cwd=base)
            self.assertEqual(r.returncode, 0, r.stderr)
            victim = base / "victim.json"
            victim.write_text("private")
            journal = base / ".teacher/journal.json"
            journal.unlink()
            journal.symlink_to(victim)
            self.assertNotEqual(run(s, "status", cwd=base).returncode, 0)
            self.assertNotEqual(run(s, "forget", "--yes", cwd=base).returncode, 0)
            self.assertEqual(victim.read_text(), "private")

    def test_series_rejects_hard_linked_state(self):
        s = str(ROOT / "scripts/series.py")
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            state = base / "state.json"
            state.write_text('{"version": 1}')
            journal_dir = base / ".teacher"
            journal_dir.mkdir()
            os.link(state, journal_dir / "journal.json")
            self.assertNotEqual(run(s, "status", cwd=base).returncode, 0)

    def test_series_refuses_to_chmod_a_nonprivate_custom_directory(self):
        s = str(ROOT / "scripts/series.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "shared"
            root.mkdir(mode=0o755)
            before = stat.S_IMODE(root.stat().st_mode)
            r = run(s, "--dir", str(root), "init", "--learner", "P", "--goal", "G")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("use a private 0700 directory", r.stderr)
            self.assertEqual(stat.S_IMODE(root.stat().st_mode), before)

    def test_vendor_sync_keeps_unrecorded_edits(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import vendor  # type: ignore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q", str(root / "up")], check=True)
            (root / "up/s").mkdir()
            (root / "up/s/SKILL.md").write_text("a\n")
            subprocess.run(["git", "-C", str(root / "up"), "add", "."], check=True)
            subprocess.run(["git", "-C", str(root / "up"), "-c", "user.email=t@t", "-c", "user.name=t", "-c", "commit.gpgsign=false", "commit", "-qm", "x"], check=True)
            skills, manifest = root / "skills", root / "VENDOR.json"
            old = (vendor.SKILLS, vendor.MANIFEST, vendor.ENTRIES, vendor.FILES)
            vendor.SKILLS, vendor.MANIFEST, vendor.ENTRIES = skills, manifest, {"s": ("up", "s", "x", "MIT")}
            vendor.FILES = {"n/f.txt": ("up", "s/SKILL.md", "x", "MIT")}
            try:
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(vendor.sync({"up": root / "up"}, None), 0)
                    (skills / "s/SKILL.md").write_text("edited here\n")
                    self.assertEqual(vendor.sync({"up": root / "up"}, None), 1, "an unrecorded edit must stop the sync")
                    self.assertEqual((skills / "s/SKILL.md").read_text(), "edited here\n")
                    self.assertEqual(vendor.sync({"up": root / "up"}, None, discard_local=True), 0)
                    (skills / "n/f.txt").write_text("edited here\n")
                    self.assertEqual(vendor.sync({"up": root / "up"}, None), 1, "a copied file edited here stops the sync too")
                    self.assertEqual((skills / "n/f.txt").read_text(), "edited here\n")
                    self.assertEqual(vendor.sync({"up": root / "up"}, None, discard_local=True), 0)
                    before = manifest.read_text()
                    shutil.rmtree(skills / "s")
                    self.assertEqual(vendor.record("s", "deleted by mistake"), 1, "a missing skill can't be recorded")
                    self.assertEqual(manifest.read_text(), before)
                    self.assertEqual(vendor.sync({"up": root / "up"}, None), 0, "so sync still restores it")
                self.assertEqual((skills / "s/SKILL.md").read_text(), "a\n")
                self.assertEqual((skills / "n/f.txt").read_text(), "a\n")
            finally:
                vendor.SKILLS, vendor.MANIFEST, vendor.ENTRIES, vendor.FILES = old

    def test_vendor_refuses_dirty_git_source(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import vendor  # type: ignore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "s").mkdir()
            (root / "s/SKILL.md").write_text("a\n")
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            subprocess.run(["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t", "-c", "commit.gpgsign=false", "commit", "-qm", "x"], check=True)
            self.assertFalse(vendor.git_dirty(root, "s"))
            (root / "s/SKILL.md").write_text("edited\n")
            self.assertTrue(vendor.git_dirty(root, "s"))
            (root / ".gitignore").write_text("x.txt\n")
            (root / "x.txt").write_text("not in HEAD\n")
            self.assertTrue(vendor.git_dirty(root, "x.txt"), "an ignored file isn't HEAD's")

    @unittest.skipUnless(shutil.which("bash"), "no bash")
    def test_install_leaves_other_links_alone(self):
        sh = str(ROOT / "install.sh")
        with tempfile.TemporaryDirectory() as tmp:
            d, other = Path(tmp) / "skills", Path(tmp) / "elsewhere"
            d.mkdir()
            other.mkdir()
            (d / "teacher").symlink_to(other)
            (d / "explorable").symlink_to(ROOT / "skills" / "explorable")  # ours, from this package
            sub = lambda *x: subprocess.run(["bash", sh, "--dir", str(d), *x], capture_output=True, text=True)
            r = sub("--with-subskills")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(Path(os.readlink(d / "teacher")), other, "a link to another checkout is not ours")
            self.assertIn("skip", r.stdout)
            self.assertEqual(Path(os.readlink(d / "concept-animation")), ROOT / "skills" / "concept-animation")
            r = sub("--with-subskills", "--uninstall")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((d / "teacher").is_symlink(), "uninstall must not remove a link that isn't ours")
            self.assertFalse((d / "explorable").exists() or (d / "explorable").is_symlink())
            self.assertTrue(other.is_dir())

    @unittest.skipUnless(shutil.which("bash"), "no bash")
    def test_install_force_never_replaces_its_own_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills = Path(tmp) / "skills"
            here = skills / "teacher"
            shutil.copytree(ROOT, here, ignore=shutil.ignore_patterns("__pycache__", "*.mp4", "*.zip", "references"))
            (here / "MY_WORK.txt").write_text("keep")
            r = subprocess.run(["bash", str(here / "install.sh"), "--dir", str(skills), "--force"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse(here.is_symlink())
            self.assertEqual((here / "MY_WORK.txt").read_text(), "keep")

    def test_recall_due_moves_on_after_an_overdue_ask(self):
        s = str(ROOT / "scripts/series.py")
        with tempfile.TemporaryDirectory() as tmp:
            for args in (["init", "--learner", "L", "--goal", "g"], ["thread", "add", "t", "--title", "T"], ["recall", "add", "t", "p1"],
                         ["resume"], ["resume"], ["resume"]):
                self.assertEqual(run(s, *args, cwd=Path(tmp)).returncode, 0)
            self.assertIn("p1", run(s, "status", cwd=Path(tmp)).stdout, "due 2 and 4 passed unasked: still due (overdue)")
            run(s, "recall", "result", "t", "0", "--wrong", cwd=Path(tmp))  # in session 4
            self.assertNotIn("Recall due", run(s, "status", cwd=Path(tmp)).stdout, "asked in session 4: not due again in session 4")
            self.assertIn("due in sessions 5, 7, 10", (Path(tmp) / ".teacher/JOURNAL.md").read_text())
            for _ in range(3):
                run(s, "resume", cwd=Path(tmp))
            self.assertIn("p1", run(s, "status", cwd=Path(tmp)).stdout, "due 5 passed unasked: still due in session 7")
            run(s, "recall", "result", "t", "0", "--wrong", cwd=Path(tmp))  # in session 7
            self.assertNotIn("Recall due", run(s, "status", cwd=Path(tmp)).stdout, "asking settles the overdue sessions")
            self.assertIn("due in sessions 8, 10, 13", (Path(tmp) / ".teacher/JOURNAL.md").read_text())

    def test_recall_result_refuses_a_negative_index(self):
        s = str(ROOT / "scripts/series.py")
        with tempfile.TemporaryDirectory() as tmp:
            for args in (["init", "--learner", "L", "--goal", "g"], ["thread", "add", "t", "--title", "T"], ["recall", "add", "t", "p1"]):
                self.assertEqual(run(s, *args, cwd=Path(tmp)).returncode, 0)
            for bad in ("-1", "1", "x"):
                r = run(s, "recall", "result", "t", bad, "--wrong", cwd=Path(tmp))
                self.assertNotEqual(r.returncode, 0, bad)
                self.assertIn("no recall point", r.stderr, bad)
            j = json.loads((Path(tmp) / ".teacher/journal.json").read_text())
            self.assertEqual(j["threads"]["t"]["recall"][0]["results"], [], "nothing recorded")

    def test_recall_stays_due_until_shown_unaided(self):
        s = str(ROOT / "scripts/series.py")
        with tempfile.TemporaryDirectory() as tmp:
            for args in (["init", "--learner", "L", "--goal", "g"], ["thread", "add", "t", "--title", "T"], ["recall", "add", "t", "p1"]):
                self.assertEqual(run(s, *args, cwd=Path(tmp)).returncode, 0)
            # Right but aided at every review (sessions 2, 4 and 7, then on): never demonstrated, so never off the list.
            for session in range(2, 12):
                run(s, "resume", cwd=Path(tmp))
                self.assertIn("p1", run(s, "status", cwd=Path(tmp)).stdout, f"due in session {session}")
                run(s, "recall", "result", "t", "0", "--right", cwd=Path(tmp))
            j = json.loads((Path(tmp) / ".teacher/journal.json").read_text())
            self.assertFalse(j["threads"]["t"]["recall"][0]["demonstrated"])
            run(s, "resume", cwd=Path(tmp))
            run(s, "recall", "result", "t", "0", "--right", "--unaided", cwd=Path(tmp))
            run(s, "resume", cwd=Path(tmp))
            self.assertNotIn("Recall due", run(s, "status", cwd=Path(tmp)).stdout, "shown unaided: done")

    def test_forget_leaves_a_journal_md_it_did_not_write(self):
        s = str(ROOT / "scripts/series.py")
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "journal.json").write_text("{}")
            (d / "JOURNAL.md").write_text("# My own notes\n")
            self.assertEqual(run(s, "--dir", ".", "forget", "--yes", cwd=d).returncode, 0)
            self.assertEqual((d / "JOURNAL.md").read_text(), "# My own notes\n")

    def test_forget_stops_when_journal_md_cannot_be_read(self):
        # A JOURNAL.md that is there but unreadable (here a symlink loop) stops
        # the forget before anything is deleted, rather than half doing it.
        s = str(ROOT / "scripts/series.py")
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "journal.json").write_text("{}")
            (d / "JOURNAL.md").symlink_to("JOURNAL.md")
            r = run(s, "--dir", ".", "forget", "--yes", cwd=d)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("nothing deleted", r.stderr)
            self.assertTrue((d / "journal.json").exists())

    def test_forget_deletes_a_corrupt_journal(self):
        s = str(ROOT / "scripts/series.py")
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / ".teacher"
            d.mkdir()
            (d / "journal.json").write_text("{not json")
            r = run(s, "status", cwd=Path(tmp))
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("forget --yes", r.stderr)
            self.assertNotIn("Traceback", r.stderr)
            r = run(s, "forget", "--yes", cwd=Path(tmp))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse(d.exists())

    def test_forget_keeps_other_files(self):
        # --dir can point at a folder with other things in it: forget removes only the journal.
        s = str(ROOT / "scripts/series.py")
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "notes.txt").write_text("mine")
            (d / "src").mkdir()
            (d / "src" / "main.py").write_text("print(1)")
            self.assertEqual(run(s, "--dir", ".", "init", "--learner", "L", "--goal", "g", cwd=d).returncode, 0)
            self.assertTrue((d / "JOURNAL.md").exists())
            r = run(s, "--dir", ".", "forget", "--yes", cwd=d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse((d / "journal.json").exists())
            self.assertFalse((d / "JOURNAL.md").exists())
            self.assertEqual((d / "notes.txt").read_text(), "mine")
            self.assertTrue((d / "src" / "main.py").exists())


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

    def test_catalog_brand_is_a_setting(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            (src / "one/lessons").mkdir(parents=True)
            shutil.copy(SKILLS / "explorable/assets/examples/seasons.lesson.js", src / "one/lessons/a.lesson.js")
            (src / "one/course.json").write_text(json.dumps({"id": "one", "title": "One", "subtitle": "a <!--<script> b",
                                                            "lessons": [{"id": "one-a", "file": "lessons/a.lesson.js", "title": "A", "needs": []}]}))
            script = str(SKILLS / "course/scripts/build_course.py")
            for i, (args, label, title) in enumerate((([], '<p class="nb-label">Kai Mori</p>', "<title>Kai Mori Courses</title>"),
                                       (["--brand", "Ada & Co"], '<p class="nb-label">Ada &amp; Co</p>', "<title>Ada &amp; Co Courses</title>"),
                                       (["--brand", ""], None, "<title>Courses</title>"))):
                out = Path(tmp) / f"out{i}"
                r = run(script, "--catalog", str(src), "--trust-authored-code", "-o", str(out), *args)
                self.assertEqual(r.returncode, 0, r.stderr)
                page = (out / "index.html").read_text()
                self.assertNotIn("<!--<script>", (out / "one/index.html").read_text(), "course text can't change how the inline script parses")
                self.assertIn(title, page, args)
                if label:
                    self.assertIn(label, page, args)
                else:
                    self.assertNotIn('class="nb-label">', page.split("<h1>Courses</h1>")[0].split('class="cs-head"')[-1], "no brand row")

    def test_course_links_with_and_without_base(self):
        # Relative links for disk and artifacts; --base makes them root-absolute
        # for a host with clean URLs and no trailing slash (Vercel).
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            for cid, prereqs in (("one", []), ("two", ["one"])):
                d = src / cid
                (d / "lessons").mkdir(parents=True)
                shutil.copy(SKILLS / "explorable/assets/examples/seasons.lesson.js", d / "lessons/a.lesson.js")
                (d / "videos").mkdir()
                (d / "videos" / f"{cid}-a.mp4").write_bytes(b"")
                (d / "videos" / f"{cid}-a.vtt").write_text("WEBVTT\n")  # a video needs its captions
                (d / "course.json").write_text(json.dumps({"id": cid, "title": cid.title(), "prereqs": prereqs,
                                                           "lessons": [{"id": f"{cid}-a", "file": "lessons/a.lesson.js", "title": "A", "needs": []}]}))
            script = str(SKILLS / "course/scripts/build_course.py")
            rel, absolute = Path(tmp) / "rel", Path(tmp) / "abs"
            self.assertEqual(run(script, "--catalog", str(src), "--trust-authored-code", "-o", str(rel)).returncode, 0)
            r = run(script, "--catalog", str(src), "--trust-authored-code", "-o", str(absolute), "--base", "/courses")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn('href="two/index.html"', (rel / "index.html").read_text())
            self.assertIn('"video": "videos/two-a.mp4"', (rel / "two/index.html").read_text())
            cat = (absolute / "index.html").read_text()
            self.assertIn('href="/courses/two"', cat)
            self.assertNotIn("index.html", cat)
            page = (absolute / "two/index.html").read_text()
            for frag in ('"base": "/courses/two/"', '"root": "/courses/"', '"video": "/courses/two/videos/two-a.mp4"'):
                self.assertIn(frag, page)
            # links.json adds a card for a standalone lesson page, escaped, after the courses
            (src / "links.json").write_text(json.dumps([{"href": "/lessons/x", "title": "X <b>", "subtitle": "s", "level": "l", "meta": "1 lesson"}]))
            self.assertEqual(run(script, "--catalog", str(src), "--trust-authored-code", "-o", str(absolute), "--base", "/courses").returncode, 0)
            cat = (absolute / "index.html").read_text()
            self.assertIn('<a class="cs-title" href="/lessons/x">X &lt;b&gt;</a>', cat)
            self.assertLess(cat.index('href="/courses/two"'), cat.index('href="/lessons/x"'))
            self.assertFalse((absolute / "links.json").exists())
            for bad in ([{"href": "javascript:alert(1)", "title": "x"}], [{"title": "no href"}], {"href": "/x", "title": "x"},
                        [{"href": "//evil.example/x", "title": "x"}], [{"href": "/\\evil.example", "title": "x"}]):
                (src / "links.json").write_text(json.dumps(bad))
                r = run(script, "--catalog", str(src), "--trust-authored-code", "-o", str(absolute), "--base", "/courses")
                self.assertNotEqual(r.returncode, 0, bad)
                self.assertIn("links.json", r.stderr)
            # links.json alone (no course.json folders) is a whole catalog too
            only = Path(tmp) / "only"
            only.mkdir()
            (only / "links.json").write_text(json.dumps([{"href": "/lessons/x", "title": "X"}]))
            r = run(script, "--catalog", str(only), "--trust-authored-code", "-o", str(Path(tmp) / "only-out"))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn('href="/lessons/x"', (Path(tmp) / "only-out/index.html").read_text())

    def test_video_comes_from_local_file_then_manifest_then_none(self):
        # The MP4s live on Vercel Blob (courses/videos.json); a local file wins
        # for previews, and with neither the lesson offers no video at all.
        sys.path.insert(0, str(SKILLS / "course/scripts"))
        import build_course

        url = "https://abc.public.blob.vercel-storage.com/courses/one/one-a.mp4"
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            d = src / "one"
            (d / "lessons").mkdir(parents=True)
            (d / "videos").mkdir()
            for lid in ("one-a", "one-b", "one-c"):
                shutil.copy(SKILLS / "explorable/assets/examples/seasons.lesson.js", d / f"lessons/{lid}.lesson.js")
            (d / "course.json").write_text(json.dumps({"id": "one", "title": "One", "lessons": [
                {"id": lid, "file": f"lessons/{lid}.lesson.js", "title": lid, "needs": []} for lid in ("one-a", "one-b", "one-c")]}))
            (d / "videos/one-a.vtt").write_text("WEBVTT\n")
            (d / "videos/one-b.vtt").write_text("WEBVTT\n")
            (src / "videos.json").write_text(json.dumps({"one/one-a.mp4": url, "one/one-c.mp4": ""}))
            manifest = build_course.load_manifest(d)
            cwd = os.getcwd()  # run from inside the course folder: "." still finds courses/videos.json
            try:
                os.chdir(d)
                self.assertEqual(build_course.load_manifest(Path(".")), manifest)
            finally:
                os.chdir(cwd)
            # A course folder linked in from elsewhere reads the videos.json beside the link, not beside its target.
            linked = Path(tmp) / "linked"
            linked.mkdir()
            (linked / "one").symlink_to(d)
            (linked / "videos.json").write_text(json.dumps({"one/one-a.mp4": "https://beside-the-link"}))
            self.assertEqual(build_course.load_manifest(linked / "one"), {"one/one-a.mp4": "https://beside-the-link"})
            # Also after cd-ing into the link: os.getcwd() is the real folder, $PWD is the linked one.
            from unittest import mock
            try:
                os.chdir(linked / "one")
                with mock.patch.dict(os.environ, {"PWD": str(linked / "one")}):
                    self.assertEqual(build_course.load_manifest(Path(".")), {"one/one-a.mp4": "https://beside-the-link"})
                with mock.patch.dict(os.environ, {"PWD": str(Path(tmp))}):  # a stale $PWD isn't trusted
                    self.assertEqual(build_course.load_manifest(Path(".")), manifest)
            finally:
                os.chdir(cwd)
            self.assertEqual(build_course.resolve_video(d, "one", "one-a", manifest), ("url", url))
            self.assertIsNone(build_course.resolve_video(d, "one", "one-b", manifest), "no file, no manifest entry")
            self.assertIsNone(build_course.resolve_video(d, "one", "one-c", manifest), "an empty manifest entry is no video")
            self.assertIsNone(build_course.resolve_video(d, "one", "one-a", {"one/one-a.mp4": "http://insecure/x.mp4"}))
            (d / "videos/one-a.mp4").write_bytes(b"")
            self.assertEqual(build_course.resolve_video(d, "one", "one-a", manifest), ("local", (d / "videos/one-a.mp4").resolve()), "the local file wins")
            # A local MP4 that isn't the uploaded one (re-rendered or remuxed, not republished) is flagged.
            self.assertIn("publish:videos", build_course.unpublished_change(d, "one", "one-a", manifest), "the URL has no digest")
            digest = hashlib.sha256(b"").hexdigest()[:8]
            self.assertIsNone(build_course.unpublished_change(d, "one", "one-a", {"one/one-a.mp4": f"https://x.public.blob.vercel-storage.com/courses/one/one-a.{digest}.mp4"}))
            self.assertIn("publish:videos", build_course.unpublished_change(d, "one", "one-a", {"one/one-a.mp4": "https://x.public.blob.vercel-storage.com/courses/one/one-a.0badc0de.mp4"}))
            self.assertIsNone(build_course.unpublished_change(d, "one", "one-b", manifest), "no local file, nothing to compare")

            out = Path(tmp) / "out"
            r = run(str(SKILLS / "course/scripts/build_course.py"), "--catalog", str(src), "--trust-authored-code", "-o", str(out), "--base", "/courses")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((out / "one/videos/one-a.mp4").exists(), "a local MP4 is copied")
            (d / "videos/one-a.mp4").unlink()  # published, so the local file goes
            (d / "videos/one-c.mp4").write_bytes(b"")  # a later lesson fails: a video without captions
            r = run(str(SKILLS / "course/scripts/build_course.py"), "--catalog", str(src), "--trust-authored-code", "-o", str(out), "--base", "/courses")
            self.assertNotEqual(r.returncode, 0)
            self.assertTrue((out / "one/videos/one-a.mp4").exists(), "a failed build keeps what the old index links")
            (d / "videos/one-c.mp4").unlink()
            r = run(str(SKILLS / "course/scripts/build_course.py"), "--catalog", str(src), "--trust-authored-code", "-o", str(out), "--base", "/courses")
            self.assertEqual(r.returncode, 0, r.stderr)
            page = (out / "one/index.html").read_text()
            lessons = {l["id"]: l for l in json.loads(re.search(r"window\.COURSE = (.*?);\n", page).group(1))["lessons"]}
            self.assertEqual(lessons["one-a"]["video"], url)
            self.assertEqual(lessons["one-a"]["captions"], "/courses/one/videos/one-a.vtt", "captions stay same-origin")
            self.assertTrue((out / "one/videos/one-a.vtt").exists())
            self.assertFalse((out / "one/videos/one-a.mp4").exists(), "a rebuild drops the copy once the video is on Blob")
            for lid in ("one-b", "one-c"):
                self.assertNotIn("video", lessons[lid])
                self.assertNotIn("captions", lessons[lid])
            self.assertFalse((out / "one/videos/one-b.vtt").exists(), "captions without a video are not shipped")
            self.assertIn("1 narrated videos", (out / "index.html").read_text())
            # --video-url sends Blob videos through the host's own route; captions don't change.
            routed = Path(tmp) / "routed"
            r = run(str(SKILLS / "course/scripts/build_course.py"), "--catalog", str(src), "--trust-authored-code", "-o", str(routed), "--base", "/courses", "--video-url", "/api/watch?v={course}/{lesson}")
            self.assertEqual(r.returncode, 0, r.stderr)
            page = (routed / "one/index.html").read_text()
            lessons = {l["id"]: l for l in json.loads(re.search(r"window\.COURSE = (.*?);\n", page).group(1))["lessons"]}
            self.assertEqual(lessons["one-a"]["video"], "/api/watch?v=one/one-a")
            self.assertEqual(lessons["one-a"]["captions"], "/courses/one/videos/one-a.vtt")
            self.assertNotIn(url, page, "the Blob URL isn't on the page")
            self.assertNotIn("video", lessons["one-b"])
            # A video without captions fails the build instead of shipping without a track.
            (d / "videos/one-a.vtt").unlink()
            r = run(str(SKILLS / "course/scripts/build_course.py"), "--catalog", str(src), "--trust-authored-code", "-o", str(Path(tmp) / "out2"))
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("one/one-a: the lesson has a video but no safe captions file", r.stderr)

    def test_course_pages_link_the_site_icon(self):
        sys.path.insert(0, str(SKILLS / "course/scripts"))
        import build_course

        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "c").mkdir()
            (d / "index.html").write_text("<!doctype html><html><head><title>x</title></head><body></body></html>")
            (d / "c/l.html").write_text("<html><head></head><body></head></body></html>")
            (d / "own.html").write_text('<html><head><link rel="icon" href="/x.svg"></head></html>')
            (d / "frag.html").write_text("<p>no head</p>")
            self.assertEqual(build_course.add_icon(d, "/favicon.svg"), 2)
            for f in ("index.html", "c/l.html"):
                text = (d / f).read_text()
                self.assertEqual(text.count('<link rel="icon" href="/favicon.svg" type="image/svg+xml">'), 1, f)
                self.assertLess(text.index("favicon"), text.index("</head>"), f)
            self.assertNotIn("favicon", (d / "own.html").read_text() + (d / "frag.html").read_text())
        site_icon = ROOT.parent / "public/favicon.ico"  # only when the engine sits in a site (kai-mori-fanout-sh)
        if site_icon.exists():
            self.assertTrue(site_icon.read_bytes().startswith(b"\0\0\1\0"), "a real .ico for /favicon.ico")

    def test_publish_videos_dry_run_lists_lesson_videos_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            courses, root = Path(tmp) / "courses", Path(tmp) / "copies"
            (courses / "two").mkdir(parents=True)
            (courses / "two/course.json").write_text(json.dumps({"id": "two", "lessons": [{"id": "two-a"}, {"id": "two-b"}]}))
            (courses / "videos.json").write_text("{}\n")
            (root / "two/videos").mkdir(parents=True)
            (root / "two/videos/two-a.mp4").write_bytes(b"x" * 1000)
            (root / "two/videos/stray.mp4").write_bytes(b"x")
            env = {k: v for k, v in os.environ.items() if k not in ("VIDEOS_BLOB_TOKEN", "KAI_MORI_VIDEOS_BLOB_TOKEN")}
            script = str(SKILLS / "course/scripts/publish_videos.mjs")
            r = subprocess.run(["node", script, str(root), "--courses", str(courses), "--dry-run"], capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            digest = hashlib.sha256(b"x" * 1000).hexdigest()[:8]
            self.assertIn(f"upload two/two-a.mp4 (0.0 MB) -> courses/two/two-a.{digest}.mp4", r.stdout)
            self.assertNotIn("stray", r.stdout)
            self.assertIn("would upload 1", r.stdout)
            self.assertEqual((courses / "videos.json").read_text(), "{}\n", "a dry run writes nothing")
            # Inside a site (<site>/teacher/...), the default is that site's courses/, wherever it runs from.
            site = Path(tmp) / "site"
            (site / "teacher/skills/course/scripts").mkdir(parents=True)
            shutil.copy(script, site / "teacher/skills/course/scripts")
            shutil.copytree(courses, site / "courses")
            shutil.copytree(root / "two/videos", site / "courses/two/videos")
            (Path(tmp) / "other/courses").mkdir(parents=True)
            r = subprocess.run(["node", str(site / "teacher/skills/course/scripts/publish_videos.mjs"), "--dry-run"],
                               capture_output=True, text=True, env=env, cwd=Path(tmp) / "other")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("would upload 1", r.stdout, "another courses/ in the current folder isn't used")
            # Run through a link, as install.sh makes them: it still runs.
            (Path(tmp) / "pv.mjs").symlink_to(site / "teacher/skills/course/scripts/publish_videos.mjs")
            r = subprocess.run(["node", str(Path(tmp) / "pv.mjs"), "--dry-run"], capture_output=True, text=True, env=env, cwd=Path(tmp) / "other")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("would upload 1", r.stdout, "a symlinked script must not silently do nothing")
            # Skipped only when the manifest URL is the upload of these exact bytes.
            blob = "https://s.public.blob.vercel-storage.com/courses/two"
            for url, skipped in [(f"{blob}/two-a.{digest}.mp4", True), (f"{blob}/two-a.00000000.mp4", False), (f"{blob}/two-a.mp4", False), ("", False)]:
                (courses / "videos.json").write_text(json.dumps({"two/two-a.mp4": url}))
                r = subprocess.run(["node", script, str(root), "--courses", str(courses), "--dry-run"], capture_output=True, text=True, env=env)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertIn("skipped 1" if skipped else "would upload 1", r.stdout, url)
            (courses / "videos.json").write_text("{}\n")
            r = subprocess.run(["node", script, str(root), "--courses", str(courses)], capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 1)
            self.assertIn("KAI_MORI_VIDEOS_BLOB_TOKEN", r.stderr)

    def test_publish_videos_streams_the_file(self):
        # A stubbed @vercel/blob records what put() was given: a stream, not the whole file in memory.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "scripts").mkdir()
            shutil.copy(SKILLS / "course/scripts/publish_videos.mjs", tmp / "scripts")
            stub = tmp / "node_modules/@vercel/blob"
            stub.mkdir(parents=True)
            (stub / "package.json").write_text('{"name": "@vercel/blob", "type": "module", "main": "index.js"}')
            (stub / "index.js").write_text(
                'import { writeFileSync } from "node:fs";\n'
                'export async function put(name, body) {\n'
                '  let n = 0; for await (const c of body) n += c.length;\n'
                '  writeFileSync(process.env.PUT_LOG, JSON.stringify({ name, stream: typeof body.pipe === "function", n }));\n'
                '  return { url: "https://s.public.blob.vercel-storage.com/" + name };\n}\n')
            courses, root = tmp / "courses", tmp / "copies"
            (courses / "two").mkdir(parents=True)
            (courses / "two/course.json").write_text(json.dumps({"id": "two", "lessons": [{"id": "two-a"}]}))
            (root / "two/videos").mkdir(parents=True)
            (root / "two/videos/two-a.mp4").write_bytes(b"x" * 1000)
            env = {**os.environ, "VIDEOS_BLOB_TOKEN": "test", "PUT_LOG": str(tmp / "put.json")}
            r = subprocess.run(["node", str(tmp / "scripts/publish_videos.mjs"), str(root), "--courses", str(courses)], capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            log = json.loads((tmp / "put.json").read_text())
            self.assertEqual((log["stream"], log["n"]), (True, 1000))
            self.assertIn("two/two-a.mp4", json.loads((courses / "videos.json").read_text()))

    def test_code_check_passes_a_lesson_that_only_shows_other_languages(self):
        with tempfile.TemporaryDirectory() as tmp:
            lesson = Path(tmp) / "x.lesson.js"
            lesson.write_text('window.LESSON = { title: "X", code: { js: "console.log(1)", expect: () => "1" } };\n')
            r = subprocess.run(["node", str(SKILLS / "explorable/scripts/check_code.mjs"), str(lesson)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("UNVERIFIED", r.stdout)

    def test_code_check_does_not_execute_authored_javascript_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "executed"
            lesson = Path(tmp) / "x.lesson.js"
            lesson.write_text(
                "this.constructor.constructor('return process')().mainModule.require('fs')"
                f".writeFileSync({json.dumps(str(marker))}, 'bad');\n"
                "window.LESSON = { title: 'X', code: { python: 'print(1)' } };\n"
            )
            r = subprocess.run(["node", str(SKILLS / "explorable/scripts/check_code.mjs"), str(lesson)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("UNVERIFIED", r.stdout)
            self.assertFalse(marker.exists())

    def test_python_worker_runs_one_job_at_a_time(self):
        # Two runs posted together share one Pyodide: the second must wait for the first.
        js = r"""
const s = require("fs").readFileSync(process.argv[1], "utf8");
const src = s.match(/const WORKER_SRC = `([\s\S]*?)\n`;/)[1].replace(/\\\\n/g, "\\n");
const log = [];
const py = { setStdout() {}, setStderr() {}, globals: { get: () => () => ({ set() {}, destroy() {} }) },
  async runPythonAsync(c) { if (!c.startsWith("import sys")) { log.push("run " + c); await new Promise((r) => setTimeout(r, 20)); } } };
const self = {};
new Function("self", "postMessage", "fetch", "importScripts", "loadPyodide", "URL", "Blob", src)(
  self, (m) => log.push(m.type + " " + m.id), async () => ({ ok: true, text: async () => "" }), () => {}, async () => py,
  { createObjectURL: () => "" }, class {});
self.onmessage({ data: { id: 1, src: "A", stdin: "", limit: 100 } });
self.onmessage({ data: { id: 2, src: "B", stdin: "", limit: 100 } });
setTimeout(() => console.log(log.join("|")), 150);
"""
        r = subprocess.run(["node", "-e", js, str(SKILLS / "explorable/assets/engine/code.js")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        log = r.stdout.strip().split("|")
        self.assertLess(log.index("done 1"), log.index("started 2"), log)
        self.assertLess(log.index("done 1"), log.index("turn 2"), log)

    def test_queued_python_run_waits_for_its_turn_to_time_out(self):
        # A run queued behind another starts its load timer only at its turn, so a
        # slow first load can't time out (and kill) the worker the first run is using.
        js = r"""
const timers = [];
globalThis.setTimeout = (fn, ms) => (timers.push(ms), timers.length);
globalThis.clearTimeout = () => {};
let worker;
globalThis.Worker = class { constructor() { worker = this; this.l = {}; }
  addEventListener(t, f) { (this.l[t] ||= []).push(f); } removeEventListener(t, f) { this.l[t] = (this.l[t] || []).filter((g) => g !== f); }
  postMessage() {} terminate() {} emit(data) { for (const f of this.l.message || []) f({ data }); } };
globalThis.URL = { createObjectURL: () => "blob:", revokeObjectURL() {} };
globalThis.Blob = class {};
const { runPython } = await import(process.argv[1]);
runPython("A", "");
runPython("B", "");
const before = timers.length;
worker.emit({ id: 1, type: "turn" });
console.log(JSON.stringify({ before, after: timers.length }));
"""
        mod = (SKILLS / "explorable/assets/engine/code.js").as_uri()
        r = subprocess.run(["node", "--input-type=module", "-e", js, mod], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), {"before": 0, "after": 1})

    @unittest.skipUnless((ROOT.parent / "courses/ai-math").is_dir(), "needs a site's courses/ (kai-mori-fanout-sh)")
    def test_code_check_fails_when_nothing_can_run(self):
        node = shutil.which("node")
        lesson = ROOT.parent / "courses/ai-math/lessons/01-vectors-dot-product.lesson.js"
        with tempfile.TemporaryDirectory() as tmp:
            os.symlink(node, Path(tmp) / "node")  # a PATH with node but no g++ or python3
            r = subprocess.run([node, str(SKILLS / "explorable/scripts/check_code.mjs"), str(lesson), "--include", str(lesson.parent.parent / "aimath.model.js"), "--trust-authored-code"],
                               capture_output=True, text=True, env={**os.environ, "PATH": tmp})
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("nothing ran", r.stdout)
            self.assertIn("no python3", r.stdout)

    def test_animation_builds(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "n.html"
            r = run(str(SKILLS / "concept-animation/scripts/build.py"), str(SKILLS / "concept-animation/assets/examples/neuron.anim.js"), "-o", str(out))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.check_single_file(out.read_text())

    def test_animation_includes_shared_scripts_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            shared = Path(tmp) / "model.js"
            shared.write_text("window.SHARED_MODEL_MARKER = 1;\n")
            out = Path(tmp) / "n.html"
            r = run(str(SKILLS / "concept-animation/scripts/build.py"), str(SKILLS / "concept-animation/assets/examples/neuron.anim.js"),
                    "-o", str(out), "--include", str(shared))
            self.assertEqual(r.returncode, 0, r.stderr)
            page = out.read_text()
            self.assertIn("SHARED_MODEL_MARKER", page)
            self.assertLess(page.index("SHARED_MODEL_MARKER"), page.index("window.ANIMATION"))

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

    def test_diagram_network_fallback_requires_explicit_opt_in(self):
        from unittest import mock

        sys.path.insert(0, str(SKILLS / "explain-diagram/scripts"))
        import render  # type: ignore

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "x.mmd"
            source.write_text("flowchart LR; A-->B\n")
            with mock.patch.object(render, "local_render", return_value=None), \
                    mock.patch.object(render, "kroki_render", return_value="<svg/>") as kroki:
                with self.assertRaises(SystemExit):
                    render.render(source)
                kroki.assert_not_called()
                self.assertEqual(render.render(source, allow_network=True), ("<svg/>", "kroki"))
                kroki.assert_called_once()

    def test_diagram_sanitizer_strips_active_content(self):
        sys.path.insert(0, str(SKILLS / "explain-diagram/scripts"))
        import render  # type: ignore

        evil = ("<svg onload='a()'><!--><script>b()</script>--><svg/onload=c()>"
                '<image href="x" onerror = "d()"/><a href="java&#x09;script:e()">t</a>'
                "<a xlink:href=javascript:f()>t</a><set attributeName='href' to='javascript:g()'/>"
                '<foreignObject><div><img src="x" onerror="h()"/><iframe src="javascript:i()"></iframe></div></foreignObject>'
                "<SCRIPT>j()</SCRIPT><rect fill='#e33' data-x=\"ok\"/></svg>")
        out = render.sanitize_svg(evil)
        for bad in ("a()", "b()", "c()", "d()", "e()", "f()", "g()", "h()", "i()", "j()", "onload", "onerror", "javascript", "<script", "<iframe", "<set"):
            self.assertNotIn(bad, out.lower() if bad.startswith("<") else out)
        self.assertIn('<rect fill="#e33" data-x="ok"/>', out)
        self.assertIn("<image/>", out, "a relative href would fetch on load")

    def test_diagram_sanitizer_keeps_css_and_raster_data(self):
        sys.path.insert(0, str(SKILLS / "explain-diagram/scripts"))
        import render  # type: ignore

        out = render.sanitize_svg('<svg><style>/* a<b */ .n > rect{}</style><style><img onerror="x()"></style>'
                                  '<![CDATA[<img onerror="y()">]]><image href="data:image/png,abc"/></svg>')
        self.assertIn("/* a&lt;b */ .n &gt; rect{}</style>", out, "a < in CSS must not eat </style>")
        self.assertNotIn("<img", out)
        self.assertIn('<image href="data:image/png,abc"/>', out)

    def test_diagram_sanitizer_blocks_css_fetches(self):
        sys.path.insert(0, str(SKILLS / "explain-diagram/scripts"))
        import render  # type: ignore

        out = render.sanitize_svg('<svg><style>@import url(http://e/a.css); .a{fill:url(#g);background:url("http://e/b")}</style>'
                                  '<style>.b{background:u\\72l(http://e/c)}</style><style>@&#105;mport "d.css";</style>'
                                  '<rect style="fill:red;background:url(//e/f)"/></svg>')
        self.assertNotRegex(out, r"e/[a-f]")
        self.assertIn("fill:url(#g)", out, "in-figure references stay")
        self.assertIn('style="fill:red;background:none"', out)

    def test_diagram_sanitizer_blocks_resource_fetches(self):
        sys.path.insert(0, str(SKILLS / "explain-diagram/scripts"))
        import render  # type: ignore

        out = render.sanitize_svg('<svg><image href="https://e/a.png"/><feImage xlink:href="http://127.0.0.1/b"/><use href="c.svg#n"/>'
                                  '<rect filter="url(http://e/d)"/><rect filter="u\\72l(http://e/d2)"/><rect mask="&#117;rl(http://e/d3)"/><foreignObject><img src="http://e/f"/></foreignObject>'
                                  '<use href="#n"/><rect fill="url(#g)"/><image href="data:image/png;base64,AA"/>'
                                  '<a href="https://ok.example/" ping="https://e/g">a link</a><animate attributeName="fill" values="red;blue"/>'
                                  '<foreignObject><img srcset="data:image/png;base64,AA 1x, https://e/h 2x"/></foreignObject></svg>')
        self.assertNotRegex(out, r"e/[a-h]|127\.0\.0\.1|c\.svg|srcset|ping")
        for kept in ('<use href="#n"/>', '<rect fill="url(#g)"/>', 'data:image/png;base64,AA', 'href="https://ok.example/"', 'values="red;blue"'):
            self.assertIn(kept, out)

    def test_diagram_sanitizer_reads_css_escapes_like_a_browser(self):
        sys.path.insert(0, str(SKILLS / "explain-diagram/scripts"))
        import render  # type: ignore

        # A browser reads CRLF as one newline, so "\\75" + CRLF + "rl(" is url(.
        out = render.sanitize_svg('<svg><style>svg{background:\\75\r\nrl(http://e/a)}</style><style>@\\69\r\nmport "http://e/b.css";</style>'
                                  '<rect style="fill:\\75&#13;&#10;rl(http://e/c)"/><rect fill="\\75&#13;&#10;rl(http://e/d)"/>'
                                  '<rect fill="url(#g)"/></svg>')
        self.assertNotRegex(out, r"e/[a-d]")
        self.assertIn('fill="url(#g)"', out)

    def test_diagram_sanitizer_escapes_markup_in_values(self):
        sys.path.insert(0, str(SKILLS / "explain-diagram/scripts"))
        import render  # type: ignore

        # Inside <foreignObject> an HTML <title> ends at the first </title>, quotes or not.
        out = render.sanitize_svg('<svg><foreignObject><title><p title="</title><img src=x onerror=alert(1)>"></p></title>'
                                  '<noscript><b>x</b></noscript><xmp>y</xmp><plaintext></foreignObject></svg>')
        self.assertNotIn("<img", out)
        self.assertEqual(out.count("</title>"), 1, "the only </title> is the real end tag")
        self.assertNotRegex(out, r"(?i)<(noscript|xmp|plaintext)")


class DiagramSanitizer(unittest.TestCase):
    def test_strips_scripts_handlers_and_bad_links(self):
        render = load(SKILLS / "explain-diagram/scripts/render.py")
        bad = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" onload="alert(1)">'
            "<rect width=10 height=10 onclick=alert(2) ONMOUSEOVER='alert(3)'/>"
            '<a href="javascript:alert(4)"><text>j</text></a>'
            '<a xlink:href=" jav&#x61;script:alert(5)"><text>k</text></a>'
            '<a href="data:text/html,<script>alert(6)</script>"><text>d</text></a>'
            '<image href="data:image/png;base64,AAAA" width="1" height="1"/>'
            '<a href="#node1"><text>ok</text></a><a href="https://example.com/x"><text>web</text></a>'
            '<SCRIPT>alert(7)</SCRIPT><iframe src="x"></iframe><svg/onload=alert(8)>'
            '<set attributeName="href" to="javascript:alert(9)"/>'
            '<foreignObject><div xmlns="http://www.w3.org/1999/xhtml"><span class="nodeLabel">Label &amp; more</span></div></foreignObject>'
            "<style>@import url(evil.css); .n { fill: red; }</style></svg>"
        )
        out = render.sanitize_svg(bad)
        for frag in ("alert(1)", "alert(2)", "alert(3)", "alert(4)", "alert(5)", "alert(6)", "alert(7)", "alert(9)", "<iframe", "@import", "<set"):
            self.assertNotIn(frag, out)
        self.assertNotRegex(out.lower(), r"\son\w+\s*=")
        self.assertNotIn("<svg/onload", out)
        for frag in ('viewBox="0 0 10 10"', 'href="data:image/png;base64,AAAA"', 'href="#node1"', 'href="https://example.com/x"',
                     "<foreignObject>", 'class="nodeLabel"', "Label &amp; more", ".n { fill: red; }"):
            self.assertIn(frag, out)


    def test_only_the_root_svg_loses_its_size(self):
        render = load(SKILLS / "explain-diagram/scripts/render.py")
        out = render.clean_svg('<svg width="100" height="50" role="x"><svg width="10" height="10"/></svg>', "A box")
        self.assertEqual(out, '<svg role="img" aria-label="A box"><svg width="10" height="10"/></svg>')


class Captions(unittest.TestCase):
    def test_vtt_escapes_and_reads_back(self):
        narrate = load(SKILLS / "explorable/scripts/narrate.py", stub=("numpy", "soundfile"))
        speech = load(SKILLS / "visual-qa/scripts/check_speech.py")
        said = ["Past that, det < 0: flipped.", "Tom & Jerry --> y > 0.5"]
        timing = {"scenes": [{"start": 0.4, "dur": 3.0, "voiceAt": 1.1}, {"start": 3.4, "dur": 3.0, "voiceAt": 4.1}]}
        text = narrate.vtt(timing, said)
        self.assertIn("det &lt; 0", text)
        self.assertEqual(text.count("-->"), 2, "an arrow in the text must not look like a timing line")
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "c.vtt"
            f.write_text(text)
            self.assertEqual([c[2] for c in speech.cues(f)], said)

    def test_speech_counts_each_heard_word_once(self):
        speech = load(SKILLS / "visual-qa/scripts/check_speech.py")
        want = [w for w in speech.words("Gradient, gradient, gradient descent at 0.693 with cross-entropy") if speech.keep(w)]
        heard = speech.words("gradient descent at 0 .693 with cross entropy")
        hit, missing = speech.match(want, heard)
        self.assertEqual(missing, ["gradient", "gradient"], "one heard 'gradient' can't cover three")
        heard = speech.words("gradient gradient gradient descent at 0 .693 with cross entropy")
        self.assertEqual(speech.match(want, heard)[1], [], "compounds and split decimals still count")

    def test_speech_credits_a_heard_word_to_one_cue(self):
        speech = load(SKILLS / "visual-qa/scripts/check_speech.py")
        two = [(0.0, 2.0, "Gradient descent"), (2.0, 4.0, "Gradient descent")]
        once = [(1.8, 2.0, "gradient"), (2.0, 2.2, "descent")]
        res = speech.score(two, once, 0.85)
        self.assertFalse(res["ok"], "gradient descent said once across two cues")
        self.assertEqual((res["got"], res["total"]), (2, 4), "two heard words, credited once each")
        twice = [(0.5, 0.8, "gradient"), (0.8, 1.1, "descent"), (2.5, 2.8, "gradient"), (2.8, 3.1, "descent")]
        self.assertTrue(speech.score(two, twice, 0.85)["ok"])
        # Both occurrences are near the first cue: it takes its own, leaving the second.
        apart = [(0.0, 2.0, "Gradient descent"), (3.0, 5.0, "Gradient descent")]
        heard = [(1.0, 1.3, "gradient"), (1.3, 1.6, "descent"), (4.0, 4.3, "gradient"), (4.3, 4.6, "descent")]
        self.assertTrue(speech.score(apart, heard, 0.85)["ok"])
        # A misheard word in one cue doesn't take the next cue's word, said on time.
        cues = [(0.0, 2.0, "gradient tells direction"), (2.0, 4.0, "gradient steps")]
        heard = [(0.2, 0.5, "radiant"), (0.5, 0.8, "tells"), (0.8, 1.2, "direction"), (2.2, 2.5, "gradient"), (2.5, 2.8, "steps")]
        rows = speech.score(cues, heard, 0.85)["rows"]
        self.assertEqual([(r["recall"], r["missing"]) for r in rows], [(0.67, ["gradient"]), (1.0, [])])

    def test_speech_check_fails_with_nothing_to_check(self):
        speech = load(SKILLS / "visual-qa/scripts/check_speech.py")
        with tempfile.TemporaryDirectory() as tmp:
            for name, text in [("empty", ""), ("malformed", "WEBVTT\n\nnot a cue\njust text\n"), ("tiny", "WEBVTT\n\n1\n00:00:00.000 --> 00:00:01.000\nSo it is.\n")]:
                f = Path(tmp) / f"{name}.vtt"
                f.write_text(text)
                res = speech.score(speech.cues(f), [(0.0, 1.0, "so")], 0.85)
                self.assertFalse(res["ok"], name)
                self.assertTrue(res["error"], name)
                r = subprocess.run([sys.executable, str(SKILLS / "visual-qa/scripts/check_speech.py"), str(Path(tmp) / "clip.mp4"), "--vtt", str(f)], capture_output=True, text=True)
                self.assertEqual(r.returncode, 1, name)
                self.assertIn("FAIL speech:", r.stdout, name)
        good = speech.score([(0.0, 2.0, "Gradient descent")], [(0.1, 0.5, "gradient"), (0.6, 1.0, "descent")], 0.85)
        self.assertTrue(good["ok"])
        self.assertIsNone(good["error"])

    def test_narrate_course_remuxes_published_videos(self):
        from unittest import mock

        course = load(SKILLS / "course/scripts/narrate_course.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "c"
            (root / "videos").mkdir(parents=True)
            (root / "course.json").write_text(json.dumps({"id": "c", "lessons": [{"id": "l1", "file": "l1.lesson.js"}]}))
            (root / "l1.lesson.js").write_text("window.LESSON = {};\n")
            (root / "videos" / "l1.mp4").write_bytes(b"")
            (root / "videos" / "l1.vtt").write_text("WEBVTT\n")
            (Path(tmp) / "videos.json").write_text(json.dumps({"c/l1.mp4": "https://example.com/l1.abc.mp4"}))
            for flags, runs in [([], 0), (["--remux"], 2), (["--force"], 2)]:
                ok = subprocess.CompletedProcess([], 0, "", "")
                with mock.patch.object(sys, "argv", ["narrate_course.py", str(root), "--trust-authored-code", *flags]), \
                        mock.patch.object(course.subprocess, "run", return_value=ok) as run, \
                        contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(course.main(), 0)
                self.assertEqual(run.call_count, runs, flags)
                if "--remux" in flags:
                    self.assertIn("--remux", run.call_args.args[0])
            # On Blob with no local MP4 and no captions: an error, not "already made" (or "no video to remux").
            (root / "videos" / "l1.mp4").unlink()
            (root / "videos" / "l1.vtt").unlink()
            for flags in ([], ["--remux"]):
                out = io.StringIO()
                with mock.patch.object(sys, "argv", ["narrate_course.py", str(root), "--trust-authored-code", *flags]), \
                        mock.patch.object(course.subprocess, "run") as run, contextlib.redirect_stdout(out):
                    self.assertEqual(course.main(), 1, flags)
                run.assert_not_called()
                self.assertIn("FAIL l1: the video is made but l1.vtt is missing", out.getvalue(), flags)

    def test_narrate_speed_default_leaves_chatterbox_free(self):
        from unittest import mock

        narrate = load(SKILLS / "explorable/scripts/narrate.py", stub=("numpy", "soundfile"))
        spoke = []
        tts = mock.Mock()
        tts.create.side_effect = lambda s, voice, speed, lang: (spoke.append(speed), ([], narrate.SR))[1]
        model = mock.Mock(sr=narrate.SR)
        for gpu in (True, False):
            with mock.patch.object(narrate, "has_gpu_chatterbox", return_value=gpu), mock.patch.object(narrate, "kokoro", return_value=tts), \
                    mock.patch.object(narrate, "chatterbox", return_value=model):
                name = lambda engine, speed: narrate.make_voice(engine, "af_heart", speed)[0]
                self.assertEqual(name("auto", None), "chatterbox" if gpu else "kokoro|af_heart|0.95", "no --speed: auto may pick Chatterbox")
                self.assertEqual(name("auto", 1.0), "chatterbox" if gpu else "kokoro|af_heart|1.0")
                self.assertEqual(name("auto", 0.9), "kokoro|af_heart|0.9")
                self.assertEqual(name("chatterbox", None), "chatterbox", "--engine chatterbox needs no --speed 1.0")
                self.assertEqual(name("chatterbox", 1.0), "chatterbox")
                with self.assertRaises(SystemExit):
                    name("chatterbox", 0.95)
                self.assertEqual(name("kokoro", None), "kokoro|af_heart|0.95", "same voice cache key as before")
                if not gpu:
                    # speak() wraps the audio with np.asarray; NumPy may be a bare stub here (CI has none).
                    with mock.patch.object(narrate, "np", mock.Mock(asarray=lambda x, dtype=None: x)):
                        narrate.make_voice("kokoro", "af_heart", None)[1]("Hello.")
        self.assertEqual(spoke, [0.95], "Kokoro still speaks at 0.95 by default")

    def test_narrate_removes_its_work_folder_when_a_render_fails(self):
        from unittest import mock

        narrate = load(SKILLS / "explorable/scripts/narrate.py", stub=("numpy", "soundfile"))
        scenes = json.dumps({"title": "T", "scenes": [{"say": "Hello there."}]})

        def fake_run(cmd):
            if "--scenes" in cmd:
                return scenes
            raise SystemExit("film_export failed")  # the frame render

        with tempfile.TemporaryDirectory() as tmp:
            for keep, left in ((False, []), (True, ["narrate-x"])):
                work = Path(tmp) / "narrate-x"
                argv = ["narrate.py", str(Path(tmp) / "l.html"), "-o", str(Path(tmp) / "o.mp4"), *(["--keep"] if keep else [])]
                with mock.patch.object(sys, "argv", argv), mock.patch.object(narrate.shutil, "which", return_value="/bin/true"), \
                        mock.patch.object(narrate, "run", side_effect=fake_run), mock.patch.object(narrate, "make_voice", return_value=("v", None)), \
                        mock.patch.object(narrate, "voice_scene", return_value=[0.0] * 100), \
                        mock.patch.object(narrate.tempfile, "mkdtemp", side_effect=lambda prefix: (work.mkdir(), str(work))[1]), \
                        contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(SystemExit):
                        narrate.main()
                self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), left, f"--keep={keep}")
                shutil.rmtree(work, ignore_errors=True)

    def test_remux_refuses_a_changed_timing(self):
        narrate = load(SKILLS / "explorable/scripts/narrate.py", stub=("numpy", "soundfile"))
        # aimath-02: 296.374 s of timing rendered as ceil(296.374 * 24) = 7113 frames.
        self.assertIsNone(narrate.remux_drift(296.374, 7113 / 24, 24))
        self.assertIsNotNone(narrate.remux_drift(296.374 + 0.5, 7113 / 24, 24))
        self.assertIsNotNone(narrate.remux_drift(296.374 - 0.1, 7113 / 24, 24))
        # Same total, scenes moved: only the per-scene ends catch it, from the sidecar or (older videos) the captions.
        timing = {"scenes": [{"start": 0.0, "dur": 4.0, "voiceAt": 0.5}, {"start": 4.0, "dur": 3661.25, "voiceAt": 4.5}]}
        with tempfile.TemporaryDirectory() as tmp:
            mp4 = Path(tmp) / "l.mp4"
            self.assertIsNone(narrate.picture_scene_ends(mp4), "nothing to check against: --remux refuses")
            mp4.with_suffix(".vtt").write_text(narrate.vtt(timing, ["a --> b", "x > y"]))
            self.assertEqual(narrate.picture_scene_ends(mp4), [4.0, 3665.25])
            mp4.with_suffix(".timing.json").write_text(json.dumps({"scenes": [{"start": 0.0, "dur": 5.0}, {"start": 5.0, "dur": 3660.25}]}))
            self.assertEqual(narrate.picture_scene_ends(mp4), [5.0, 3665.25], "the sidecar wins")

    def test_saved_progress_follows_its_step(self):
        js = r"""
const { stepKeys, restoreProgress } = await import(process.argv[1]);
const a = { title: "A", ask: { kind: "choice", q: "a?" } }, b = { title: "B" }, c = { id: "c", title: "C" };
const old = stepKeys([a, b, c]);
const saved = { steps: old, step: 2, done: [0, 1, 2], attempts: { 0: [{ answer: 1, right: true }], 2: [{ answer: 0, right: false }] }, tried: { 1: ["x"] }, explained: { 0: { text: "t", covered: [] } }, notes: "n", curious: ["q"] };
// A step inserted first, B removed, C renamed (its id keeps it matched).
const now = stepKeys([{ title: "New", ask: { kind: "choice", q: "new?" } }, a, { ...c, title: "C2" }]);
const out = {
  moved: restoreProgress(saved, now),
  legacy: restoreProgress({ step: 1, done: [0, 1], attempts: { 0: [] }, notes: "n" }, now),
  junk: [null, 3, "x", [], { steps: "x", done: "x" }, { steps: old, done: [9, "0"], attempts: { 0: "bad" }, step: "nope" }].map((v) => restoreProgress(v, now)),
  dupes: stepKeys([b, b]),
  // A new step with B's title lands before B: which saved B is which is a guess, so nothing moves.
  grown: restoreProgress({ steps: stepKeys([b]), done: [0], tried: { 0: ["x"] } }, stepKeys([b, b])),
  same: restoreProgress({ steps: stepKeys([b, b]), done: [1] }, stepKeys([a, b, b])),
  nested: restoreProgress({ steps: old, attempts: { 0: [null, 3, { answer: 1 }, { answer: 2, right: false }] }, tried: { 0: ["y", null] }, explained: { 0: { text: "saved" }, 2: { covered: [0] } } }, now),
};
console.log(JSON.stringify(out));
"""
        mod = (SKILLS / "explorable/assets/engine/progress.js").as_uri()
        r = subprocess.run(["node", "--input-type=module", "-e", js, mod], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        moved = out["moved"]
        self.assertEqual(sorted(moved["done"]), [1, 2])  # the new step 0 is not done
        self.assertEqual(moved["attempts"], {"1": [{"answer": 1, "right": True}], "2": [{"answer": 0, "right": False}]})
        self.assertEqual(moved["tried"], {})  # B is gone
        self.assertEqual(list(moved["explained"]), ["1"])
        self.assertEqual((moved["step"], moved["notes"], moved["curious"]), (2, "n", ["q"]))
        legacy = out["legacy"]  # saved before keys: can't be matched, so step state is dropped
        self.assertEqual((legacy["done"], legacy["attempts"], legacy["step"], legacy["notes"]), ([], {}, 0, "n"))
        for j in out["junk"]:
            self.assertEqual((j["step"], j["attempts"], j["tried"], j["explained"]), (0, {}, {}, {}))
        self.assertEqual(out["junk"][-1]["done"], [1])  # "0" (old A) still maps; 9 is out of range
        self.assertEqual(len(set(out["dupes"])), 2)
        self.assertEqual((out["grown"]["done"], out["grown"]["tried"]), ([], {}))
        self.assertEqual(out["same"]["done"], [2])  # the group kept its size, so order still tells them apart
        nested = out["nested"]  # malformed rows inside an entry would crash report()
        self.assertEqual(nested["attempts"], {"1": [{"answer": 2, "right": False}]})
        self.assertEqual(nested["tried"], {"1": ["y"]})
        self.assertEqual(nested["explained"], {"1": {"text": "saved", "covered": []}})

    def test_plain_text_reads_into_a_formula(self):
        js = r"""
const src = require("fs").readFileSync(process.argv[1], "utf8");
eval(src.match(/function plainText\(html\) \{[\s\S]*?\n\}/)[0]);
console.log(plainText(process.argv[2]));
"""
        say = '<p>the set of points with</p><p class="nb-print">w1x1 + b = 0</p><p>That is a <strong>line</strong></p><p>Next</p>'
        r = subprocess.run(["node", "-e", js, str(SKILLS / "explorable/assets/engine/explorable.js"), say], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "the set of points with w1x1 + b = 0. That is a line. Next")

    @unittest.skipUnless((ROOT.parent / "courses").is_dir(), "needs a site's courses/ (kai-mori-fanout-sh)")
    def test_shipped_captions_are_escaped(self):
        for f in sorted((ROOT.parent / "courses").glob("*/videos/*.vtt")):
            for block in f.read_text().split("\n\n")[1:]:
                for line in block.split("\n")[2:]:
                    self.assertNotRegex(line, r"<|>|&(?!amp;|lt;|gt;)", f"{f.name}: {line}")


class VideoCheckerAudio(unittest.TestCase):
    def test_unmeasurable_audio_fails(self):
        from unittest import mock

        chk = load(SKILLS / "visual-qa/scripts/check_video.py")
        info = {"format": {"duration": "3"}, "streams": [
            {"codec_type": "video", "width": 1280, "height": 720, "avg_frame_rate": "30/1", "pix_fmt": "yuv420p"},
            {"codec_type": "audio"}]}
        with tempfile.TemporaryDirectory() as tmp:
            clip = Path(tmp) / "c.mp4"
            clip.with_suffix(".vtt").write_text("WEBVTT\n")
            for measured, ok in [((-16.0, -2.0), True), ((None, -2.0), False), ((-16.0, None), False)]:
                out = io.StringIO()
                with mock.patch.object(sys, "argv", ["check_video.py", str(clip), "--json"]), \
                        mock.patch.object(chk.shutil, "which", return_value="/bin/true"), \
                        mock.patch.object(chk, "probe", return_value=info), mock.patch.object(chk, "stretches", return_value=[]), \
                        mock.patch.object(chk, "loudness", return_value=measured), contextlib.redirect_stdout(out):
                    code = chk.main()
                self.assertEqual(code == 0, ok, (measured, out.getvalue()))
                if not ok:
                    self.assertIn("couldn't be measured", out.getvalue())

    def test_undecodable_frames_fail(self):
        from unittest import mock

        chk = load(SKILLS / "visual-qa/scripts/check_video.py")
        info = {"format": {"duration": "3"}, "streams": [
            {"codec_type": "video", "width": 1280, "height": 720, "avg_frame_rate": "30/1", "pix_fmt": "yuv420p"}]}
        with tempfile.TemporaryDirectory() as tmp:
            clip = Path(tmp) / "c.mp4"
            clip.with_suffix(".vtt").write_text("WEBVTT\n")
            for code, ok in ((0, True), (1, False)):
                done = subprocess.CompletedProcess([], code, "", "" if code == 0 else "Invalid data found when processing input")
                out = io.StringIO()
                with mock.patch.object(sys, "argv", ["check_video.py", str(clip), "--json"]), \
                        mock.patch.object(chk.shutil, "which", return_value="/bin/true"), mock.patch.object(chk, "probe", return_value=info), \
                        mock.patch.object(chk, "run", return_value=done), contextlib.redirect_stdout(out):
                    self.assertEqual(chk.main() == 0, ok, out.getvalue())
                if not ok:
                    self.assertIn("doesn't decode", out.getvalue())
                    self.assertIn("Invalid data", out.getvalue())


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
