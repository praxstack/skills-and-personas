#!/usr/bin/env python3
"""Bring every bundled skill into skills/ and prove where each one came from.

The teacher is standalone: copy this one folder to any host and every
capability skill comes with it. This script is how those copies are made and
checked, so a bundled skill is never a silent fork.

  python3 scripts/vendor.py verify                      # hashes in VENDOR.json match skills/
  python3 scripts/vendor.py record teach-pro-max --note "added the style section"   # accept a local change
  python3 scripts/vendor.py sync --source video=/path/to/claude-video-skills \
      --source skills=/path/to/skills-and-personas --source snapshot=/path/to/folder \
      --source chesslab=/path/to/ChessLab

`sync` copies each entry from its source root, then rewrites VENDOR.json with
the source commit (when the root is a git checkout) and a tree hash.
Skills authored here (lesson-notebook, explorable, concept-animation,
explain-diagram, visual-qa) are not vendored; they live in skills/ and are
listed as "native". The few files they copy from elsewhere (the notebook's
ink.js and fonts, from ChessLab) are tracked one by one under "files".

A change made here to a vendored skill is recorded, not hidden: `record`
re-hashes the skill and appends the note to its "local_changes" in
VENDOR.json, and `sync` then refuses to overwrite that skill unless
--discard-local is given (port the change upstream first).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
MANIFEST = ROOT / "VENDOR.json"
SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "runs"}
SKIP_FILES = {".DS_Store"}

VIDEO_REPO = "https://github.com/praxstack/claude-video-skills-for-people-who-feel-neglected-by-claude"
SKILLS_REPO = "https://github.com/praxstack/skills-and-personas"

# name -> (source key, path inside the source root, upstream URL, license note)
ENTRIES = {
    **{
        name: ("video", f"skills/{name}", VIDEO_REPO, "same as the video skills repo")
        for name in [
            "explainer-video", "manim-video", "motion-canvas-video", "remotion-video", "revideo-video",
            "hyperframes-video", "gsap-video", "motion-video", "threejs-video", "theatrejs-video",
            "handdrawn-js-video",
        ]
    },
    "techtutor": ("skills", "new-skills/techtutor", SKILLS_REPO, "MIT (repo)"),
    "lecture-alchemist": ("skills", "new-skills/lecture-alchemist", SKILLS_REPO, "MIT (repo)"),
    "concept-cartographer": ("skills", "new-skills/concept-cartographer", SKILLS_REPO, "MIT (repo)"),
    "algo-sensei": ("snapshot", "algo-sensei", "https://github.com/karanb192/algo-sensei", "MIT, see its LICENSE"),
    "eli": ("snapshot", "eli", "Prax's local skill library (16 Oct 2026 snapshot)", "Prax's own"),
}

NATIVE = ["lesson-notebook", "explorable", "concept-animation", "explain-diagram", "visual-qa", "course"]

CHESSLAB_REPO = "https://github.com/praxstack/ChessLab"
# Single files copied byte-for-byte into native skills: dest -> (source key, source path, upstream, licence).
FILES = {
    "lesson-notebook/assets/ink.js": ("chesslab", "site/public/assets/ink.js", CHESSLAB_REPO, "Prax's own (AskTheMove)"),
    **{
        f"lesson-notebook/assets/fonts/{f}": ("chesslab", f"site/public/assets/fonts/{f}", CHESSLAB_REPO, "SIL OFL 1.1, see OFL.txt")
        for f in ["OFL.txt", "vollkorn-var.woff2", "kalam-400.woff2", "kalam-700.woff2", "courier-prime-400.woff2"]
    },
}


def _skipped(path: Path, base: Path) -> bool:
    rel = path.relative_to(base)
    return any(part in SKIP_DIRS for part in rel.parts) or path.name in SKIP_FILES


def files_of(base: Path) -> list[Path]:
    return sorted(p for p in base.rglob("*") if p.is_file() and not p.is_symlink() and not _skipped(p, base))


def tree_hash(base: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    files = files_of(base)
    for path in files:
        digest.update(path.relative_to(base).as_posix().encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).hexdigest().encode())
        digest.update(b"\n")
    return digest.hexdigest(), len(files)


def git_head(root: Path) -> str | None:
    try:
        return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def git_files(root: Path, rel: str) -> list[str] | None:
    """Files git tracks under root/rel, or None when root isn't a git checkout."""
    if git_head(root) is None:
        return None
    out = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z", "--", rel], text=True)
    return sorted(f for f in out.split("\0") if f and (root / f).is_file() and not (root / f).is_symlink())


def git_dirty(root: Path, rel: str) -> bool:
    """True when rel in a git source differs from HEAD: uncommitted, untracked or ignored.

    The manifest attributes the copy to HEAD, so the bytes copied must be HEAD's.
    """
    if git_head(root) is None:
        return False
    out = subprocess.check_output(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all", "--", rel], text=True)
    if out.strip():
        return True
    # An ignored file shows up in neither status nor HEAD, so require it to be tracked.
    return not subprocess.check_output(["git", "-C", str(root), "ls-files", "--", rel], text=True).strip()


NOTE = (
    "Vendored skills are byte copies of their sources. Edit them upstream and re-run "
    "scripts/vendor.py sync; scripts/vendor.py verify fails if a copy drifts. A change made "
    "here is recorded with scripts/vendor.py record NAME --note ... and listed under local_changes."
)


def sync(sources: dict[str, Path], only: list[str] | None, discard_local: bool = False) -> int:
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"skills": {}}

    def kept_local(name: str) -> bool:
        return bool(manifest["skills"].get(name, {}).get("local_changes")) and not discard_local

    # Check every source before touching any copy, so a failure can't leave a
    # copy replaced while VENDOR.json still records its old hash.
    picked = [(n, k, r) for n, (k, r, *_) in ENTRIES.items() if (not only or n in only) and k in sources and not kept_local(n)]
    picked += [(d, k, r) for d, (k, r, *_) in FILES.items() if k in sources]
    for label, key, rel in picked:
        if git_dirty(sources[key], rel):
            print(f"FAIL {label}: {sources[key] / rel} differs from HEAD (uncommitted, untracked or ignored); commit it first", file=sys.stderr)
            return 1
    # A copy edited here but never recorded would be lost without a word.
    for name, *_ in picked:
        here = SKILLS / name
        if name in FILES:  # a single copied file, recorded by its sha256
            entry = manifest.get("files", {}).get(name)
            changed = entry and here.is_file() and hashlib.sha256(here.read_bytes()).hexdigest() != entry["sha256"]
            fix = "make the change upstream"
        else:
            entry = manifest["skills"].get(name)
            changed = entry and here.exists() and tree_hash(here)[0] != entry["tree_sha256"]
            fix = f"record it (vendor.py record {name} --note ...)"
        if changed and not discard_local:
            print(f"FAIL {name}: skills/{name} was changed here and not recorded; {fix} or pass --discard-local", file=sys.stderr)
            return 1
    for name, (key, rel, upstream, license_note) in ENTRIES.items():
        if only and name not in only:
            continue
        if kept_local(name):
            print(f"skip {name}: it has local changes ({len(manifest['skills'][name]['local_changes'])} in VENDOR.json); port them upstream, or pass --discard-local")
            continue
        if key not in sources:
            print(f"skip {name}: no --source {key}=...")
            continue
        src = sources[key] / rel
        if not (src / "SKILL.md").is_file():
            print(f"FAIL {name}: {src}/SKILL.md not found", file=sys.stderr)
            return 1
        dest = SKILLS / name
        if dest.exists():
            shutil.rmtree(dest)
        tracked = git_files(sources[key], rel)
        if tracked is None:
            shutil.copytree(src, dest, ignore=shutil.ignore_patterns(*SKIP_DIRS, *SKIP_FILES), symlinks=False)
        else:
            # A git source: copy only what upstream commits, so a fresh clone hashes the same.
            for f in tracked:
                if _skipped(sources[key] / f, src):
                    continue
                target = dest / Path(f).relative_to(rel)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(sources[key] / f, target)  # keep upstream file modes
        digest, count = tree_hash(dest)
        manifest["skills"][name] = {
            "upstream": upstream,
            "source_path": rel,
            "source_commit": git_head(sources[key]),
            "license": license_note,
            "files": count,
            "tree_sha256": digest,
        }
        print(f"ok   {name}: {count} files")
    for dest, (key, rel, upstream, license_note) in FILES.items():
        if key not in sources:
            continue
        src = sources[key] / rel
        if not src.is_file():
            print(f"FAIL {dest}: {src} not found", file=sys.stderr)
            return 1
        target = SKILLS / dest
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)
        manifest.setdefault("files", {})[dest] = {
            "upstream": upstream,
            "source_path": rel,
            "source_commit": git_head(sources[key]),
            "license": license_note,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        }
        print(f"ok   {dest}")
    manifest["native"] = NATIVE
    manifest["note"] = NOTE
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return 0


def record(name: str, note: str) -> int:
    """Accept the current contents of a vendored skill as a deliberate local change."""
    manifest = json.loads(MANIFEST.read_text())
    entry = manifest["skills"].get(name)
    if entry is None:
        print(f"FAIL {name}: not a vendored skill (known: {', '.join(sorted(manifest['skills']))})", file=sys.stderr)
        return 1
    if not note.strip():
        print("FAIL: say what changed with --note", file=sys.stderr)
        return 1
    if not (SKILLS / name / "SKILL.md").is_file():
        # A missing folder hashes as an empty tree; recording that would make sync skip restoring it.
        print(f"FAIL {name}: skills/{name}/SKILL.md is missing; restore it first (vendor.py sync --source KEY=PATH --only {name})", file=sys.stderr)
        return 1
    digest, count = tree_hash(SKILLS / name)
    if digest == entry["tree_sha256"]:
        print(f"ok   {name}: nothing changed since VENDOR.json")
        return 0
    entry["tree_sha256"], entry["files"] = digest, count
    entry.setdefault("local_changes", []).append(note.strip())
    manifest["note"] = NOTE
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"ok   {name}: recorded ({count} files, {len(entry['local_changes'])} local changes)")
    return 0


def verify() -> int:
    manifest = json.loads(MANIFEST.read_text())
    bad = 0
    for name, entry in sorted(manifest["skills"].items()):
        dest = SKILLS / name
        if not dest.is_dir():
            print(f"FAIL {name}: missing")
            bad += 1
            continue
        digest, count = tree_hash(dest)
        if digest != entry["tree_sha256"]:
            print(f"FAIL {name}: drifted from VENDOR.json ({count} files now, {entry['files']} recorded)")
            bad += 1
    for dest, entry in sorted(manifest.get("files", {}).items()):
        target = SKILLS / dest
        if not target.is_file():
            print(f"FAIL {dest}: missing")
            bad += 1
        elif hashlib.sha256(target.read_bytes()).hexdigest() != entry["sha256"]:
            print(f"FAIL {dest}: drifted from VENDOR.json")
            bad += 1
    for name in manifest.get("native", []):
        if not (SKILLS / name / "SKILL.md").is_file():
            print(f"FAIL native {name}: missing SKILL.md")
            bad += 1
    local = sorted(n for n, e in manifest["skills"].items() if e.get("local_changes"))
    print(f"{len(manifest['skills'])} vendored{f' ({len(local)} with local changes: ' + ', '.join(local) + ')' if local else ''}, "
          f"{len(manifest.get('files', {}))} copied files, {len(manifest.get('native', []))} native, {bad} problems")
    return 1 if bad else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sync")
    s.add_argument("--source", action="append", default=[], help="key=path (video, skills, snapshot, chesslab)")
    s.add_argument("--only", nargs="*")
    s.add_argument("--discard-local", action="store_true", help="overwrite skills that have recorded local changes")
    sub.add_parser("verify")
    r = sub.add_parser("record")
    r.add_argument("name")
    r.add_argument("--note", required=True, help="what was changed here, and why")
    args = parser.parse_args()
    if args.cmd == "verify":
        return verify()
    if args.cmd == "record":
        return record(args.name, args.note)
    sources = {}
    for pair in args.source:
        key, _, path = pair.partition("=")
        sources[key] = Path(path).expanduser().resolve()
    return sync(sources, args.only, args.discard_local)


if __name__ == "__main__":
    raise SystemExit(main())
