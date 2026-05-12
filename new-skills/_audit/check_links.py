#!/usr/bin/env python3
"""
Detect broken internal links across new-skills/ portfolio.

Scans every SKILL.md and references/*.md under new-skills/ for:
- Relative markdown links to non-existent files
- Backtick-quoted paths to non-existent files (references/*.md, scripts/*, assets/*)
- Anchor links (#heading) where the heading doesn't exist in that file
- Same-directory markdown links

Writes _audit/link-report.json and returns exit code 0/1.

Deterministic: no network, no LLM. stdlib + yaml only.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path("/Users/praxlannister/Documents/workspace/skills-and-personas/new-skills")

# [text](url) — capture url only. Exclude URLs with http/https/mailto/pure anchor.
MD_LINK_RE = re.compile(r'\[[^\]]*\]\(((?!https?://|mailto:|#)[^)\s]+)(?:\s+"[^"]*")?\)')
# Anchor-only links: [text](#heading)
ANCHOR_LINK_RE = re.compile(r'\[[^\]]*\]\(#([^)\s]+)\)')
# Backtick-quoted relative paths for references/, scripts/, assets/
BACKTICK_PATH_RE = re.compile(r'`((?:references/|scripts/|assets/)[A-Za-z0-9_\-./]+)`')
# ATX headings: # Heading, ## Heading, etc.
HEADING_RE = re.compile(r'^(#{1,6})\s+(.+?)\s*#*\s*$')

# Heading-to-anchor slugifier (GitHub-style)
def slugify_heading(text: str) -> str:
    text = text.strip().lower()
    # Strip markdown emphasis/code
    text = re.sub(r'[`*_~]+', '', text)
    # Drop anything not alnum/space/hyphen
    text = re.sub(r'[^\w\s\-]', '', text, flags=re.UNICODE)
    text = re.sub(r'\s+', '-', text)
    return text.strip('-')


def strip_code_blocks(text: str) -> str:
    """Remove fenced code blocks so we don't report links inside code examples."""
    out = []
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append("")  # preserve line number
            continue
        if in_fence:
            out.append("")
        else:
            out.append(line)
    return "\n".join(out)


def collect_headings(text: str) -> set:
    """Collect slugified heading anchors from a markdown document (outside code blocks)."""
    stripped = strip_code_blocks(text)
    anchors = set()
    for line in stripped.split("\n"):
        m = HEADING_RE.match(line)
        if m:
            anchors.add(slugify_heading(m.group(2)))
    return anchors


def scan_file(md_path: Path, skill_dir: Path) -> list:
    """
    Scan a single markdown file for broken links.
    Returns list of dicts: {link, type, resolved, exists, line_hint}.
    """
    raw = md_path.read_text()
    # Strip frontmatter before scanning
    body = raw
    if body.startswith("---\n"):
        end = body.find("\n---\n", 4)
        if end != -1:
            body = body[end + 5:]
    body_clean = strip_code_blocks(body)
    headings = collect_headings(body)

    findings = []
    base_dir = md_path.parent

    # 1. Markdown relative links [text](path)
    for m in MD_LINK_RE.finditer(body_clean):
        url = m.group(1).strip()
        # Split off any fragment
        if "#" in url:
            url_path, fragment = url.split("#", 1)
        else:
            url_path, fragment = url, None

        if not url_path:
            # pure anchor, handled separately
            continue

        # Resolve relative to file's directory
        try:
            resolved = (base_dir / url_path).resolve()
        except Exception:
            findings.append({
                "link": url, "type": "md_link", "resolved": None,
                "exists": False, "reason": "unresolvable"
            })
            continue

        exists = resolved.exists()
        finding = {
            "link": url,
            "type": "md_link",
            "resolved": str(resolved),
            "exists": exists,
        }
        if exists and fragment:
            # Check fragment in the target file (only if markdown)
            if resolved.suffix == ".md":
                try:
                    target_text = resolved.read_text()
                    target_anchors = collect_headings(target_text)
                    if slugify_heading(fragment) not in target_anchors:
                        finding["exists"] = False
                        finding["reason"] = f"anchor #{fragment} missing in target"
                except Exception:
                    pass
        if not finding["exists"]:
            findings.append(finding)

    # 2. Anchor-only links [text](#heading) — same file
    for m in ANCHOR_LINK_RE.finditer(body_clean):
        anchor = m.group(1).strip()
        slug = slugify_heading(anchor)
        if slug not in headings:
            findings.append({
                "link": f"#{anchor}",
                "type": "anchor",
                "resolved": str(md_path),
                "exists": False,
                "reason": "heading not found",
            })

    # 3. Backtick-quoted relative paths (references/, scripts/, assets/)
    for m in BACKTICK_PATH_RE.finditer(body_clean):
        rel = m.group(1).strip()
        # Resolve against the skill dir (where references/ lives)
        candidate = (skill_dir / rel).resolve()
        if not candidate.exists():
            findings.append({
                "link": rel,
                "type": "backtick_path",
                "resolved": str(candidate),
                "exists": False,
            })

    return findings


def scan_skill(skill_dir: Path) -> dict:
    """Scan SKILL.md + all references/*.md. Returns {file_rel_path: [findings]}."""
    out = {}
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        findings = scan_file(skill_md, skill_dir)
        if findings:
            out[str(skill_md.relative_to(ROOT))] = findings

    refs_dir = skill_dir / "references"
    if refs_dir.is_dir():
        for ref_md in sorted(refs_dir.rglob("*.md")):
            findings = scan_file(ref_md, skill_dir)
            if findings:
                out[str(ref_md.relative_to(ROOT))] = findings
    return out


def main():
    results = {}
    total_broken = 0
    skills_scanned = 0
    files_scanned = 0
    links_scanned = 0  # approximate

    for skill_dir in sorted(ROOT.iterdir()):
        if not skill_dir.is_dir():
            continue
        if skill_dir.name.startswith("_") or skill_dir.name.startswith("."):
            continue
        skills_scanned += 1

        # Count files scanned
        if (skill_dir / "SKILL.md").exists():
            files_scanned += 1
        refs_dir = skill_dir / "references"
        if refs_dir.is_dir():
            files_scanned += sum(1 for _ in refs_dir.rglob("*.md"))

        skill_findings = scan_skill(skill_dir)
        if skill_findings:
            results[skill_dir.name] = skill_findings
            for file_findings in skill_findings.values():
                total_broken += len(file_findings)

    # Approximate links scanned by re-counting across all files (cheap second pass)
    for skill_dir in sorted(ROOT.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("_") or skill_dir.name.startswith("."):
            continue
        skill_md = skill_dir / "SKILL.md"
        targets = []
        if skill_md.exists():
            targets.append(skill_md)
        refs_dir = skill_dir / "references"
        if refs_dir.is_dir():
            targets.extend(sorted(refs_dir.rglob("*.md")))
        for t in targets:
            try:
                text = t.read_text()
            except Exception:
                continue
            if text.startswith("---\n"):
                end = text.find("\n---\n", 4)
                if end != -1:
                    text = text[end + 5:]
            text = strip_code_blocks(text)
            links_scanned += len(MD_LINK_RE.findall(text))
            links_scanned += len(ANCHOR_LINK_RE.findall(text))
            links_scanned += len(BACKTICK_PATH_RE.findall(text))

    report = {
        "summary": {
            "skills_scanned": skills_scanned,
            "files_scanned": files_scanned,
            "links_scanned": links_scanned,
            "total_broken": total_broken,
            "passed": total_broken == 0,
        },
        "broken": results,
    }

    out_path = ROOT / "_audit" / "link-report.json"
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True))

    print(f"Skills: {skills_scanned}  Files: {files_scanned}  Links: {links_scanned}  Broken: {total_broken}")
    if total_broken:
        for slug, files in sorted(results.items()):
            print(f"\n[{slug}]")
            for fpath, findings in sorted(files.items()):
                print(f"  {fpath}")
                for f in findings:
                    extra = f" ({f.get('reason')})" if f.get("reason") else ""
                    print(f"    - [{f['type']}] {f['link']}{extra}")

    return 0 if total_broken == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
