#!/usr/bin/env python3
"""
Smoke test harness for installed skills.

For each skill in ~/.claude/skills/ that we just installed:
 1. SKILL.md parses with valid YAML frontmatter
 2. name field matches directory name
 3. description is present and under 1024 chars
 4. No "You are a/an/the..." persona statements outside code blocks
 5. Every references/*.md file referenced in SKILL.md actually exists
 6. scripts/* files (if any) are executable or have a shebang

Writes JSON report. Exit 0 if all pass; 1 if any FAIL.
"""
import os
import re
import sys
import json
import yaml
from pathlib import Path

SKILLS_DIR = Path.home() / ".claude" / "skills"
NEW_SKILLS_MANIFEST = Path("/Users/praxlannister/Documents/workspace/skills-and-personas/new-skills")

NAME_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
PERSONA_RE = re.compile(r"(?i)^\s*(You are\s+(a|an|the)\s+[A-Za-z])")
REF_LINK_RE = re.compile(r"`references/([a-zA-Z0-9\-_./]+\.md)`|\[[^\]]*\]\(references/([a-zA-Z0-9\-_./]+\.md)\)")


def split_frontmatter(text):
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text
    return text[4:end], text[end + 5:]


def strip_code_blocks(text):
    out = []
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(line)
    return "\n".join(out)


def test_skill(skill_dir: Path):
    result = {"slug": skill_dir.name, "checks": {}, "fails": [], "warns": []}
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.exists():
        result["fails"].append("NO_SKILL_MD")
        return result

    raw = skill_md.read_text()
    fm_text, body = split_frontmatter(raw)

    if fm_text is None:
        result["fails"].append("NO_FRONTMATTER")
        return result
    try:
        fm = yaml.safe_load(fm_text) or {}
        result["checks"]["yaml_parses"] = True
    except yaml.YAMLError as e:
        result["fails"].append(f"YAML_PARSE:{e}")
        return result

    name = fm.get("name", "")
    if name != skill_dir.name:
        result["fails"].append(f"NAME_MISMATCH: name={name} dir={skill_dir.name}")
    if not NAME_RE.match(name):
        result["fails"].append(f"NAME_REGEX: {name}")
    result["checks"]["name_valid"] = name == skill_dir.name and bool(NAME_RE.match(name))

    desc = fm.get("description", "")
    if not desc:
        result["fails"].append("NO_DESCRIPTION")
    elif len(desc) > 1024:
        result["fails"].append(f"DESC_LEN:{len(desc)}")
    result["checks"]["description_valid"] = bool(desc) and len(desc) <= 1024

    stripped = strip_code_blocks(body)
    persona_hits = [i for i, line in enumerate(stripped.split("\n")) if PERSONA_RE.match(line)]
    if persona_hits:
        result["fails"].append(f"PERSONA_LINES:{persona_hits[:3]}")
    result["checks"]["no_personas"] = not persona_hits

    missing_refs = []
    for m in REF_LINK_RE.finditer(body):
        fname = m.group(1) or m.group(2)
        if fname:
            ref_path = skill_dir / "references" / fname
            if not ref_path.exists():
                missing_refs.append(fname)
    if missing_refs:
        result["warns"].append(f"MISSING_REFS: {missing_refs[:5]}")
    result["checks"]["all_refs_resolve"] = not missing_refs

    scripts_dir = skill_dir / "scripts"
    if scripts_dir.exists():
        for script in scripts_dir.iterdir():
            if script.is_file() and script.suffix in (".sh", ".py", ".js"):
                first = script.read_text().split("\n", 1)[0] if script.stat().st_size > 0 else ""
                if not first.startswith("#!") and not os.access(script, os.X_OK):
                    result["warns"].append(f"SCRIPT_NOT_EXECUTABLE: {script.name}")

    return result


def main():
    results = []
    total_fails = 0
    total_warns = 0

    our_slugs = sorted(d.name for d in NEW_SKILLS_MANIFEST.iterdir()
                       if d.is_dir() and not d.name.startswith("_") and not d.name.startswith("."))

    for slug in our_slugs:
        skill_dir = SKILLS_DIR / slug
        if not skill_dir.exists():
            results.append({"slug": slug, "fails": ["NOT_INSTALLED"]})
            total_fails += 1
            continue
        r = test_skill(skill_dir)
        fails = len(r.get("fails", []))
        warns = len(r.get("warns", []))
        total_fails += fails
        total_warns += warns
        results.append(r)

    report = {
        "summary": {
            "skills_tested": len(results),
            "total_fails": total_fails,
            "total_warns": total_warns,
            "passed": total_fails == 0,
        },
        "results": results,
    }

    out_path = NEW_SKILLS_MANIFEST / "_audit" / "smoke-test-report.json"
    out_path.write_text(json.dumps(report, indent=2))

    print(f"Tested: {len(results)}  FAILs: {total_fails}  WARNs: {total_warns}")
    if total_fails > 0:
        for r in results:
            if r.get("fails"):
                print(f"  [{r['slug']}] FAILS: {r['fails']}")
    if total_warns > 0 and total_warns <= 20:
        for r in results:
            if r.get("warns"):
                print(f"  [{r['slug']}] WARNS: {r['warns']}")

    return 0 if total_fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
