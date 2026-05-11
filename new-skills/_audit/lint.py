#!/usr/bin/env python3
"""
Deterministic skill-linter implementation for new-skills/ portfolio.
Mirrors skill-linter rules from agentskills.io specification:
  - name: 1-64 chars, regex ^[a-z][a-z0-9]*(-[a-z0-9]+)*$, matches dirname, no "claude"/"anthropic"
  - description: 1-1024 chars, non-empty, no XML angle brackets, has routing keywords
  - frontmatter: no extra fields beyond name/description/allowed-tools/license/metadata/compatibility
  - SKILL.md <= 500 lines
  - No README.md at skill top level
  - Only subdirs: scripts/, references/, assets/
  - No "You are a/an/the" persona statements outside fenced code blocks (FAIL)
  - No ASCII box-drawing / arrow chars outside code blocks (WARN)
  - No marketing copy buzzwords in description (WARN)
"""
import re
import sys
import json
import yaml
from pathlib import Path

ROOT = Path("/Users/praxlannister/Documents/workspace/skills-and-personas/new-skills")

NAME_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
ASCII_ART_RE = re.compile(r"[─│┌┐└┘├┤┬┴┼╭╮╯╰═║╔╗╚╝╠╣╦╩╬↑↓←→↔⇒⇐⇔▲▼◄►]")
PERSONA_RE = re.compile(r"(?i)^\s*(You are\s+(a|an|the)\s+[A-Za-z])")
XML_RE = re.compile(r"[<>]")
ALLOWED_FRONTMATTER = {"name", "description", "allowed-tools", "license", "metadata", "compatibility", "when_to_use", "argument-hint", "arguments", "disable-model-invocation", "user-invocable", "model", "effort", "context", "agent", "hooks", "paths", "shell"}
ALLOWED_SUBDIRS = {"scripts", "references", "assets"}
MARKETING_WORDS = {"comprehensive", "powerful", "cutting-edge", "world-class", "premier", "state-of-the-art", "next-generation", "revolutionary"}
RESERVED_NAME_WORDS = {"claude", "anthropic"}


def split_frontmatter(text):
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        end = text.find("\n---", 4)
        if end == -1:
            return None, text
    fm_text = text[4:end]
    body = text[end:].lstrip("-\n")
    return fm_text, body


def strip_code_blocks(text):
    """Remove ``` fenced blocks so we don't flag ASCII art or 'You are' in examples."""
    out = []
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(line)
    return "\n".join(out)


def lint_skill(skill_dir: Path):
    issues = []  # [(severity, code, message)]
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        issues.append(("FAIL", "NO_SKILL_MD", f"{skill_md} missing"))
        return issues

    raw = skill_md.read_text()
    fm_text, body = split_frontmatter(raw)
    if fm_text is None:
        issues.append(("FAIL", "NO_FRONTMATTER", "Missing YAML frontmatter between --- markers"))
        return issues

    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as e:
        issues.append(("FAIL", "INVALID_YAML", f"YAML parse error: {e}"))
        return issues

    # name
    name = fm.get("name", "")
    if not name:
        issues.append(("FAIL", "NO_NAME", "Missing 'name' field"))
    else:
        if not isinstance(name, str):
            issues.append(("FAIL", "NAME_TYPE", f"name must be string, got {type(name).__name__}"))
            name = str(name)
        if len(name) > 64:
            issues.append(("FAIL", "NAME_TOO_LONG", f"name is {len(name)} chars (max 64)"))
        if not NAME_RE.match(name):
            issues.append(("FAIL", "NAME_INVALID", f"name '{name}' doesn't match ^[a-z][a-z0-9]*(-[a-z0-9]+)*$"))
        if any(w in name.lower() for w in RESERVED_NAME_WORDS):
            issues.append(("FAIL", "NAME_RESERVED", f"name '{name}' contains reserved word (claude/anthropic)"))
        if name != skill_dir.name:
            issues.append(("FAIL", "NAME_DIR_MISMATCH", f"name '{name}' != dirname '{skill_dir.name}'"))

    # description
    desc = fm.get("description", "")
    if not desc:
        issues.append(("FAIL", "NO_DESCRIPTION", "Missing 'description' field"))
    else:
        if not isinstance(desc, str):
            issues.append(("FAIL", "DESC_TYPE", f"description must be string"))
            desc = str(desc)
        if len(desc) > 1024:
            issues.append(("FAIL", "DESC_TOO_LONG", f"description is {len(desc)} chars (max 1024)"))
        if len(desc) < 20:
            issues.append(("WARN", "DESC_TOO_SHORT", f"description is only {len(desc)} chars"))
        if XML_RE.search(desc):
            issues.append(("FAIL", "DESC_XML", "description contains XML angle brackets"))
        # routing keywords
        routing_keywords = ["use when", "trigger", "use this", "when the user", "covers", "for"]
        if not any(kw in desc.lower() for kw in routing_keywords):
            issues.append(("WARN", "DESC_NO_ROUTING", "description lacks routing keywords ('use when', 'triggers on', etc.)"))
        # Strip quoted trigger phrases (they're user-language, not marketing copy about the skill).
        desc_for_marketing = re.sub(r'"[^"]*"', "", desc.lower())
        desc_for_marketing = re.sub(r"'[^']*'", "", desc_for_marketing)
        marketing_found = [w for w in MARKETING_WORDS if w in desc_for_marketing]
        if marketing_found:
            issues.append(("WARN", "DESC_MARKETING", f"description contains marketing words: {marketing_found}"))

    # extra frontmatter fields
    extra = set(fm.keys()) - ALLOWED_FRONTMATTER
    if extra:
        issues.append(("WARN", "FRONTMATTER_EXTRA", f"unexpected frontmatter fields: {sorted(extra)}"))

    # line count
    lines = raw.count("\n")
    if lines > 500:
        issues.append(("FAIL", "TOO_LONG", f"SKILL.md is {lines} lines (max 500)"))
    elif lines > 400:
        issues.append(("WARN", "APPROACHING_LIMIT", f"SKILL.md is {lines} lines (approaching 500-line limit)"))

    # No top-level README.md
    for p in skill_dir.iterdir():
        if p.is_file() and p.name.lower() == "readme.md":
            issues.append(("FAIL", "TOP_LEVEL_README", f"README.md at skill top level not allowed: {p}"))

    # Only allowed subdirs
    for p in skill_dir.iterdir():
        if p.is_dir() and p.name not in ALLOWED_SUBDIRS:
            issues.append(("FAIL", "INVALID_SUBDIR", f"subdir '{p.name}' not allowed (only scripts/references/assets)"))

    # Persona statements (check body, stripped of code blocks)
    stripped_body = strip_code_blocks(body)
    for i, line in enumerate(stripped_body.split("\n"), 1):
        if PERSONA_RE.match(line):
            issues.append(("FAIL", "PERSONA_STATEMENT", f"line {i}: persona statement: {line.strip()[:80]}"))

    # ASCII art (strip code blocks first)
    ascii_hits = []
    for i, line in enumerate(stripped_body.split("\n"), 1):
        if ASCII_ART_RE.search(line):
            ascii_hits.append(i)
    if ascii_hits:
        issues.append(("WARN", "ASCII_ART", f"box-drawing/arrow chars on {len(ascii_hits)} lines outside code blocks: {ascii_hits[:5]}"))

    return issues


def audit_portfolio():
    """Produce skill-auditor-style portfolio summary."""
    rows = []
    for d in sorted(ROOT.iterdir()):
        if not d.is_dir() or d.name.startswith("_"):
            continue
        skill_md = d / "SKILL.md"
        if not skill_md.exists():
            continue
        raw = skill_md.read_text()
        lines = raw.count("\n")
        fm_text, _ = split_frontmatter(raw)
        desc_len = 0
        name = d.name
        if fm_text:
            try:
                fm = yaml.safe_load(fm_text) or {}
                desc_len = len(fm.get("description", ""))
                name = fm.get("name", d.name)
            except Exception:
                pass
        status = "OVER" if lines > 500 else "HEAVY" if lines > 300 else "OK"
        refs = 0
        refs_dir = d / "references"
        if refs_dir.exists():
            refs = sum(1 for p in refs_dir.iterdir() if p.is_file() and p.suffix == ".md")
        rows.append({
            "name": name,
            "dir": d.name,
            "lines": lines,
            "desc_chars": desc_len,
            "status": status,
            "refs": refs,
        })
    return rows


def main():
    results = []
    total_fails = 0
    total_warns = 0
    for d in sorted(ROOT.iterdir()):
        if not d.is_dir() or d.name.startswith("_"):
            continue
        if not (d / "SKILL.md").exists():
            continue
        issues = lint_skill(d)
        fails = sum(1 for i in issues if i[0] == "FAIL")
        warns = sum(1 for i in issues if i[0] == "WARN")
        total_fails += fails
        total_warns += warns
        results.append({
            "slug": d.name,
            "fails": fails,
            "warns": warns,
            "issues": [{"severity": s, "code": c, "msg": m} for s, c, m in issues],
        })

    audit = audit_portfolio()

    report = {
        "summary": {
            "skills_linted": len(results),
            "total_fails": total_fails,
            "total_warns": total_warns,
            "passed": total_fails == 0,
        },
        "lint_results": results,
        "portfolio_audit": audit,
    }

    out_path = ROOT / "_audit" / "lint-report.json"
    out_path.write_text(json.dumps(report, indent=2))
    print(f"Wrote {out_path}")
    print(f"Skills: {len(results)}  FAILs: {total_fails}  WARNs: {total_warns}")

    # Human-readable summary
    print("\n=== FAILs ===")
    for r in results:
        if r["fails"] > 0:
            print(f"\n[{r['slug']}]")
            for i in r["issues"]:
                if i["severity"] == "FAIL":
                    print(f"  FAIL {i['code']}: {i['msg']}")

    print("\n=== WARNs (top 20) ===")
    warn_count = 0
    for r in results:
        for i in r["issues"]:
            if i["severity"] == "WARN" and warn_count < 20:
                print(f"  [{r['slug']}] {i['code']}: {i['msg']}")
                warn_count += 1

    print("\n=== Portfolio ===")
    print(f"{'NAME':<40} {'LINES':>6} {'DESC':>6} {'REFS':>5} STATUS")
    for a in sorted(audit, key=lambda x: -x['lines']):
        print(f"{a['name']:<40} {a['lines']:>6} {a['desc_chars']:>6} {a['refs']:>5} {a['status']}")

    return 0 if total_fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
