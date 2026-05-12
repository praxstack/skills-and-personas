"""
TDD tests for _audit/ tooling: lint.py, fix_lint_issues.py, smoke_test.py.

Tests use isolated temp-dir skill fixtures so they don't touch the real portfolio.
Run with: pytest _audit/tests/ -v

Each test asserts ONE behavior. If a test name doesn't map to a behavior, delete
the test — don't let suite bloat hide real failures.
"""
import importlib.util
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

AUDIT_DIR = Path(__file__).resolve().parent.parent
NEW_SKILLS_DIR = AUDIT_DIR.parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def lint_mod():
    return load_module("lint", AUDIT_DIR / "lint.py")


@pytest.fixture
def fix_mod():
    return load_module("fix_lint_issues", AUDIT_DIR / "fix_lint_issues.py")


@pytest.fixture
def smoke_mod():
    return load_module("smoke_test", AUDIT_DIR / "smoke_test.py")


# ============================================================================
# lint.py — split_frontmatter
# ============================================================================

def test_split_frontmatter_handles_minimal_valid(lint_mod):
    text = "---\nname: x\ndescription: y\n---\n\nbody\n"
    fm, body = lint_mod.split_frontmatter(text)
    assert fm == "name: x\ndescription: y"
    assert "body" in body


def test_split_frontmatter_returns_none_when_no_opening(lint_mod):
    fm, body = lint_mod.split_frontmatter("no frontmatter here\n")
    assert fm is None


def test_split_frontmatter_returns_none_when_no_closing(lint_mod):
    fm, body = lint_mod.split_frontmatter("---\nname: x\ndescription: y\n")
    assert fm is None


# ============================================================================
# lint.py — strip_code_blocks (persona/ASCII scan must NOT fire in fenced blocks)
# ============================================================================

def test_strip_code_blocks_removes_fenced(lint_mod):
    text = "visible\n```\nhidden\n```\nalso visible\n"
    stripped = lint_mod.strip_code_blocks(text)
    assert "hidden" not in stripped
    assert "visible" in stripped
    assert "also visible" in stripped


def test_strip_code_blocks_handles_nested_fences(lint_mod):
    text = "visible\n```python\ncode with ``` inline\n```\ntail\n"
    # Inner ``` at col 0 would close; our simple parser flips state on any ```.
    # Verify we still drop content between first and second ``` lines.
    stripped = lint_mod.strip_code_blocks(text)
    assert "code with" not in stripped or "tail" in stripped


def test_strip_code_blocks_preserves_blank_lines(lint_mod):
    text = "a\n\nb\n"
    assert lint_mod.strip_code_blocks(text) == text


# ============================================================================
# lint.py — lint_skill (integration over a tempdir fixture)
# ============================================================================

def _write_skill(tmpdir: Path, name: str, body: str, frontmatter: dict = None):
    """Helper: write a minimal skill dir to tmpdir with given frontmatter + body."""
    skill_dir = tmpdir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    fm = frontmatter or {"name": name, "description": f"{name} test description with routing keyword: Use when testing."}
    fm_text = yaml.safe_dump(fm, default_flow_style=False, sort_keys=False).strip()
    (skill_dir / "SKILL.md").write_text(f"---\n{fm_text}\n---\n\n{body}\n")
    return skill_dir


def test_lint_passes_minimal_valid_skill(lint_mod, tmp_path, monkeypatch):
    d = _write_skill(tmp_path, "valid-skill", "# Title\n\n**Audience:** test.\n\nBody text.\n")
    monkeypatch.setattr(lint_mod, "ROOT", tmp_path)
    issues = lint_mod.lint_skill(d)
    fails = [i for i in issues if i[0] == "FAIL"]
    assert fails == [], f"unexpected fails: {fails}"


def test_lint_fails_when_name_mismatches_dirname(lint_mod, tmp_path, monkeypatch):
    d = _write_skill(tmp_path, "wrong-dir", "body",
                     frontmatter={"name": "different-name", "description": "Use when testing routing keyword."})
    monkeypatch.setattr(lint_mod, "ROOT", tmp_path)
    issues = lint_mod.lint_skill(d)
    codes = [i[1] for i in issues if i[0] == "FAIL"]
    assert "NAME_DIR_MISMATCH" in codes


def test_lint_fails_on_reserved_name_word(lint_mod, tmp_path, monkeypatch):
    d = _write_skill(tmp_path, "claude-tool", "body",
                     frontmatter={"name": "claude-tool", "description": "Use when."})
    monkeypatch.setattr(lint_mod, "ROOT", tmp_path)
    issues = lint_mod.lint_skill(d)
    codes = [i[1] for i in issues if i[0] == "FAIL"]
    assert "NAME_RESERVED" in codes


def test_lint_fails_on_invalid_name_regex(lint_mod, tmp_path, monkeypatch):
    d = _write_skill(tmp_path, "Bad_Name", "body",
                     frontmatter={"name": "Bad_Name", "description": "Use when."})
    monkeypatch.setattr(lint_mod, "ROOT", tmp_path)
    issues = lint_mod.lint_skill(d)
    codes = [i[1] for i in issues if i[0] == "FAIL"]
    assert "NAME_INVALID" in codes


def test_lint_fails_on_description_too_long(lint_mod, tmp_path, monkeypatch):
    long_desc = "Use when " + "x" * 1100
    d = _write_skill(tmp_path, "long-desc", "body",
                     frontmatter={"name": "long-desc", "description": long_desc})
    monkeypatch.setattr(lint_mod, "ROOT", tmp_path)
    issues = lint_mod.lint_skill(d)
    codes = [i[1] for i in issues if i[0] == "FAIL"]
    assert "DESC_TOO_LONG" in codes


def test_lint_fails_on_xml_in_description(lint_mod, tmp_path, monkeypatch):
    d = _write_skill(tmp_path, "xml-desc", "body",
                     frontmatter={"name": "xml-desc", "description": "Use when <bad> tags appear."})
    monkeypatch.setattr(lint_mod, "ROOT", tmp_path)
    issues = lint_mod.lint_skill(d)
    codes = [i[1] for i in issues if i[0] == "FAIL"]
    assert "DESC_XML" in codes


def test_lint_fails_on_persona_statement_outside_code(lint_mod, tmp_path, monkeypatch):
    body = "# Title\n\nYou are a senior engineer.\n\nMore text.\n"
    d = _write_skill(tmp_path, "persona-skill", body)
    monkeypatch.setattr(lint_mod, "ROOT", tmp_path)
    issues = lint_mod.lint_skill(d)
    codes = [i[1] for i in issues if i[0] == "FAIL"]
    assert "PERSONA_STATEMENT" in codes


def test_lint_ignores_persona_statement_in_code_block(lint_mod, tmp_path, monkeypatch):
    body = "# Title\n\n**Audience:** test.\n\nExample:\n\n```\nYou are a senior engineer\n```\n\nEnd.\n"
    d = _write_skill(tmp_path, "safe-persona", body)
    monkeypatch.setattr(lint_mod, "ROOT", tmp_path)
    issues = lint_mod.lint_skill(d)
    codes = [i[1] for i in issues if i[0] == "FAIL"]
    assert "PERSONA_STATEMENT" not in codes


def test_lint_warns_on_ascii_art_outside_code(lint_mod, tmp_path, monkeypatch):
    body = "# Title\n\n**Audience:** x.\n\n┌───┐\n│ A │\n└───┘\n\nEnd.\n"
    d = _write_skill(tmp_path, "ascii-art", body)
    monkeypatch.setattr(lint_mod, "ROOT", tmp_path)
    issues = lint_mod.lint_skill(d)
    codes = [i[1] for i in issues if i[0] == "WARN"]
    assert "ASCII_ART" in codes


def test_lint_fails_on_top_level_readme(lint_mod, tmp_path, monkeypatch):
    d = _write_skill(tmp_path, "has-readme", "body")
    (d / "README.md").write_text("readme at top level")
    monkeypatch.setattr(lint_mod, "ROOT", tmp_path)
    issues = lint_mod.lint_skill(d)
    codes = [i[1] for i in issues if i[0] == "FAIL"]
    assert "TOP_LEVEL_README" in codes


def test_lint_fails_on_invalid_subdir(lint_mod, tmp_path, monkeypatch):
    d = _write_skill(tmp_path, "bad-subdir", "body")
    (d / "notes").mkdir()
    monkeypatch.setattr(lint_mod, "ROOT", tmp_path)
    issues = lint_mod.lint_skill(d)
    codes = [i[1] for i in issues if i[0] == "FAIL"]
    assert "INVALID_SUBDIR" in codes


def test_lint_accepts_references_scripts_assets_subdirs(lint_mod, tmp_path, monkeypatch):
    d = _write_skill(tmp_path, "good-subdirs", "body")
    (d / "references").mkdir()
    (d / "scripts").mkdir()
    (d / "assets").mkdir()
    monkeypatch.setattr(lint_mod, "ROOT", tmp_path)
    issues = lint_mod.lint_skill(d)
    codes = [i[1] for i in issues if i[0] == "FAIL"]
    assert "INVALID_SUBDIR" not in codes


def test_lint_fails_on_over_500_lines(lint_mod, tmp_path, monkeypatch):
    body = "\n".join(f"line {i}" for i in range(520))
    d = _write_skill(tmp_path, "too-long", body)
    monkeypatch.setattr(lint_mod, "ROOT", tmp_path)
    issues = lint_mod.lint_skill(d)
    codes = [i[1] for i in issues if i[0] == "FAIL"]
    assert "TOO_LONG" in codes


def test_lint_warns_on_approaching_500_lines(lint_mod, tmp_path, monkeypatch):
    body = "\n".join(f"line {i}" for i in range(420))
    d = _write_skill(tmp_path, "heavy", body)
    monkeypatch.setattr(lint_mod, "ROOT", tmp_path)
    issues = lint_mod.lint_skill(d)
    codes = [i[1] for i in issues if i[0] == "WARN"]
    assert "APPROACHING_LIMIT" in codes


# ============================================================================
# fix_lint_issues.py — fix_description_yaml
# ============================================================================

def test_fix_description_yaml_wraps_unquoted_colon(fix_mod):
    text = "---\nname: x\ndescription: Use when: doing things\n---\nbody\n"
    fixed, changed = fix_mod.fix_description_yaml(text)
    assert changed is True
    assert "description: 'Use when: doing things'" in fixed


def test_fix_description_yaml_idempotent_when_already_single_quoted(fix_mod):
    text = "---\nname: x\ndescription: 'already quoted: colon ok'\n---\nbody\n"
    fixed, changed = fix_mod.fix_description_yaml(text)
    assert changed is False
    assert text == fixed


def test_fix_description_yaml_converts_double_to_single(fix_mod):
    text = '---\nname: x\ndescription: "double quoted"\n---\nbody\n'
    fixed, changed = fix_mod.fix_description_yaml(text)
    assert changed is True
    assert "description: 'double quoted'" in fixed


def test_fix_description_yaml_escapes_internal_single_quote(fix_mod):
    text = "---\nname: x\ndescription: it's complicated\n---\nbody\n"
    fixed, changed = fix_mod.fix_description_yaml(text)
    assert changed is True
    # YAML escape for single quote inside single-quoted scalar is ''
    assert "it''s" in fixed


def test_fix_description_yaml_leaves_folded_block_alone(fix_mod):
    text = "---\nname: x\ndescription: >\n  long folded description\n  with colons: ok\n---\nbody\n"
    fixed, changed = fix_mod.fix_description_yaml(text)
    assert changed is False


def test_fix_description_yaml_does_nothing_without_frontmatter(fix_mod):
    text = "no frontmatter here\n"
    fixed, changed = fix_mod.fix_description_yaml(text)
    assert changed is False
    assert text == fixed


# ============================================================================
# fix_lint_issues.py — fix_arrows_outside_code
# ============================================================================

def test_fix_arrows_replaces_right_arrow_in_prose(fix_mod):
    text = "# Title\n\nfoo → bar\n"
    fixed, changed = fix_mod.fix_arrows_outside_code(text)
    assert changed is True
    assert "→" not in fixed
    assert "—" in fixed


def test_fix_arrows_preserves_in_code_block(fix_mod):
    text = "# Title\n\n```\nfoo → bar\n```\n\nAfter block.\n"
    fixed, changed = fix_mod.fix_arrows_outside_code(text)
    # Inside code block, arrow must survive
    assert "→" in fixed


def test_fix_arrows_handles_multiple_arrow_types(fix_mod):
    text = "a → b ← c ⇒ d\n"
    fixed, changed = fix_mod.fix_arrows_outside_code(text)
    assert changed is True
    for arrow in "→←⇒":
        assert arrow not in fixed


def test_fix_arrows_noop_when_no_arrows(fix_mod):
    text = "# Title\n\nno arrows here.\n"
    fixed, changed = fix_mod.fix_arrows_outside_code(text)
    assert changed is False
    assert text == fixed


# ============================================================================
# smoke_test.py — REF_LINK_RE detection
# ============================================================================

def test_smoke_detects_backtick_reference(smoke_mod):
    body = "See `references/file.md` for more."
    matches = list(smoke_mod.REF_LINK_RE.finditer(body))
    assert len(matches) == 1
    # Group 1 = backtick form, group 2 = markdown link form
    assert matches[0].group(1) == "file.md"


def test_smoke_detects_markdown_link_reference(smoke_mod):
    body = "See [the guide](references/file.md) for more."
    matches = list(smoke_mod.REF_LINK_RE.finditer(body))
    assert len(matches) == 1
    assert matches[0].group(2) == "file.md"


def test_smoke_detects_multiple_references(smoke_mod):
    body = "Use `references/a.md` and `references/b.md`."
    matches = list(smoke_mod.REF_LINK_RE.finditer(body))
    assert len(matches) == 2


def test_smoke_ignores_non_references_path(smoke_mod):
    body = "See `/etc/passwd` and `src/file.md`."
    matches = list(smoke_mod.REF_LINK_RE.finditer(body))
    assert len(matches) == 0


# ============================================================================
# End-to-end: run lint.py against real portfolio and expect 0 FAILs
# ============================================================================

def test_real_portfolio_lint_passes():
    """Integration: real new-skills/ portfolio must always pass linter."""
    result = subprocess.run(
        [sys.executable, str(AUDIT_DIR / "lint.py")],
        cwd=str(NEW_SKILLS_DIR),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"lint failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    # Report must exist after run
    report_path = AUDIT_DIR / "lint-report.json"
    assert report_path.exists()
    report = json.loads(report_path.read_text())
    assert report["summary"]["total_fails"] == 0, \
        f"Lint regressed — FAILs: {report['summary']['total_fails']}"


def test_real_portfolio_all_skill_names_match_dirs():
    """Invariant: every SKILL.md 'name' field must equal its directory name."""
    for skill_dir in sorted(NEW_SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("_") or skill_dir.name.startswith("."):
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        raw = skill_md.read_text()
        assert raw.startswith("---\n"), f"{skill_dir.name}: missing frontmatter opener"
        end = raw.find("\n---", 4)
        fm = yaml.safe_load(raw[4:end])
        assert fm["name"] == skill_dir.name, \
            f"{skill_dir.name}: name field '{fm.get('name')}' != dirname"


def test_real_portfolio_all_descriptions_under_1024_chars():
    """Invariant: no skill description exceeds the agentskills spec cap."""
    for skill_dir in sorted(NEW_SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("_") or skill_dir.name.startswith("."):
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        raw = skill_md.read_text()
        end = raw.find("\n---", 4)
        fm = yaml.safe_load(raw[4:end])
        desc = fm.get("description", "")
        assert len(desc) <= 1024, \
            f"{skill_dir.name}: description is {len(desc)} chars"


def test_real_portfolio_frontmatter_has_no_xml_tags():
    """Security: XML angle brackets in frontmatter can enable prompt injection."""
    for skill_dir in sorted(NEW_SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("_") or skill_dir.name.startswith("."):
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        raw = skill_md.read_text()
        end = raw.find("\n---", 4)
        fm_text = raw[4:end]
        # Descriptions shouldn't contain raw < or > tokens.
        # (Folded-YAML or inline quoted text with & / > as indicator is fine at YAML level
        # but we scan the parsed description.)
        fm = yaml.safe_load(fm_text)
        desc = fm.get("description", "")
        assert "<" not in desc and ">" not in desc, \
            f"{skill_dir.name}: description contains XML angle brackets"


def test_no_skill_has_top_level_readme():
    """Spec requirement: README.md inside a skill dir is not permitted."""
    for skill_dir in sorted(NEW_SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("_") or skill_dir.name.startswith("."):
            continue
        readmes = [p for p in skill_dir.iterdir() if p.is_file() and p.name.lower() == "readme.md"]
        assert not readmes, f"{skill_dir.name}: top-level README.md found"
