#!/usr/bin/env python3
"""
Auto-fix two categories of linter issues:

1. YAML parse errors from colons in unquoted description strings.
   Fix: wrap description in single-quoted YAML string, escape any single quotes inside as ''.

2. Unicode arrow characters (→ ← ↓ ↑ ⇒ etc.) in prose outside code blocks.
   Fix: replace with em-dash (—) or plain word depending on context.

Idempotent. Leaves already-good files untouched.
"""
import re
import sys
from pathlib import Path

ROOT = Path("/Users/praxlannister/Documents/workspace/skills-and-personas/new-skills")

ARROW_MAP = {
    "→": "—",
    "←": "—",
    "⇒": "—",
    "⇐": "—",
    "↔": "—",
    "↑": "^",
    "↓": "v",
    "▲": "^",
    "▼": "v",
    "◄": "<",
    "►": ">",
}
ARROW_RE = re.compile("|".join(re.escape(k) for k in ARROW_MAP.keys()))


def fix_description_yaml(text):
    """
    Replace `description: <anything with colons>` with single-quote-wrapped form.
    Only touches the description line in the frontmatter block.
    """
    if not text.startswith("---\n"):
        return text, False

    end = text.find("\n---\n", 4)
    if end == -1:
        end = text.find("\n---", 4)
        if end == -1:
            return text, False
    fm = text[4:end]
    rest = text[end:]

    # Find description line(s). Could be single-line `description: ...` or already-multi.
    lines = fm.split("\n")
    new_lines = []
    changed = False
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^(description:\s*)(.*)$", line)
        if m and not line.strip().endswith(("|", "|-", ">", ">-")):
            key, value = m.group(1), m.group(2).strip()
            # If already single-quoted and valid, skip.
            if value.startswith("'") and value.endswith("'") and len(value) >= 2:
                new_lines.append(line)
                i += 1
                continue
            # If double-quoted, convert to single by unescaping double quotes and escaping single.
            if value.startswith('"') and value.endswith('"'):
                inner = value[1:-1]
                # unescape \" -> "
                inner = inner.replace('\\"', '"')
                inner_escaped = inner.replace("'", "''")
                new_lines.append(f"{key}'{inner_escaped}'")
                changed = True
                i += 1
                continue
            # Unquoted: wrap in single quotes
            if value:
                inner_escaped = value.replace("'", "''")
                new_lines.append(f"{key}'{inner_escaped}'")
                changed = True
                i += 1
                continue
        new_lines.append(line)
        i += 1

    new_fm = "\n".join(new_lines)
    return "---\n" + new_fm + rest, changed


def strip_code_blocks_to_mask(text):
    """Return a list of (line_idx, is_in_code) tuples — True = inside ``` block."""
    mask = []
    in_fence = False
    for i, line in enumerate(text.split("\n")):
        stripped = line.lstrip()
        if stripped.startswith("```"):
            mask.append((i, True))  # the fence line itself — don't modify
            in_fence = not in_fence
            continue
        mask.append((i, in_fence))
    return mask


def fix_arrows_outside_code(text):
    """Replace unicode arrows with em-dash / word equivalents, but only OUTSIDE fenced code blocks."""
    lines = text.split("\n")
    mask = strip_code_blocks_to_mask(text)
    changed = False
    for i, line in enumerate(lines):
        _, in_code = mask[i]
        if in_code:
            continue
        if ARROW_RE.search(line):
            new_line = ARROW_RE.sub(lambda m: ARROW_MAP[m.group(0)], line)
            if new_line != line:
                lines[i] = new_line
                changed = True
    return "\n".join(lines), changed


def main():
    touched = []
    for d in sorted(ROOT.iterdir()):
        if not d.is_dir() or d.name.startswith("_"):
            continue
        skill_md = d / "SKILL.md"
        if not skill_md.exists():
            continue
        raw = skill_md.read_text()
        original = raw
        raw, yaml_fixed = fix_description_yaml(raw)
        raw, arrows_fixed = fix_arrows_outside_code(raw)
        if raw != original:
            skill_md.write_text(raw)
            touched.append({
                "slug": d.name,
                "yaml_fix": yaml_fixed,
                "arrow_fix": arrows_fixed,
            })
            print(f"  fixed: {d.name}  yaml={yaml_fixed}  arrows={arrows_fixed}")
    print(f"\nTotal files touched: {len(touched)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
