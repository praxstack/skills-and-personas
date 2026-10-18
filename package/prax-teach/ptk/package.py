"""`ptk package`: build the install tree and check it (AC-8.1); host discovery as each host documents it
(AC-8.2); side-by-side install, link flip and rollback with the learner-state snapshot (AC-8.6, D17.12).

Nothing here writes to a real host directory. Every install and discovery function takes an explicit
`home`, and refuses the real home unless the caller passes allow_real_home=True (only Prax's own
acceptance step would). Tests use throwaway homes under $PTK_STATE/hosts/<host>/ (D19.3).
"""
import hashlib
import json
import os
import secrets
import shutil
import time
from pathlib import Path

from . import errors, host

MAX_BYTES = 5 * 1024 * 1024
EXCLUDE_DIRS = {"__pycache__", "node_modules", "build", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".git",
                ".venv", "venv"}
EXCLUDE_FILES = {".DS_Store"}
EXCLUDE_SUFFIXES = (".pyc", ".pyo", ".part", ".tmp", ".log")
HOME_MARKER = b"/" + b"Users" + b"/"          # spelled in pieces so this file never contains it whole
MANIFEST = "INSTALL-MANIFEST.json"
V2_LINK = Path(".agents") / "skills" / "prax-teach-v2"


CANDIDATE = Path(".agents") / "skill-library" / "prax-teach-v2.1"


class PackageError(errors.GateError):
    """The install tree or an install step broke a packaging rule (exit 1)."""


# ---------------------------------------------------------------- the install tree (AC-8.1)

def _included(rel):
    parts = rel.parts
    if any(p in EXCLUDE_DIRS for p in parts[:-1]) or parts[-1] in EXCLUDE_FILES:
        return False
    return not parts[-1].endswith(EXCLUDE_SUFFIXES)


def tree_files(src=None):
    """Every file the install ships, relative to the package root, sorted. Symlinks are refused."""
    src = Path(src or host.PKG)
    out = []
    for root, dirs, files in os.walk(src):
        rel_root = Path(root).relative_to(src)
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDE_DIRS)
        for d in dirs:
            if (Path(root) / d).is_symlink():
                raise PackageError(f"symlinked directory in the package: {rel_root / d}")
        for f in sorted(files):
            rel = rel_root / f
            if not _included(rel):
                continue
            if (Path(root) / f).is_symlink():
                raise PackageError(f"symlink in the package: {rel}")
            out.append(rel)
    return sorted(out)


def check_tree(root):
    """The AC-8.1 limits on a built (or source) tree: size, no home paths, no caches, one SKILL.md."""
    root = Path(root)
    problems, total, files = [], 0, 0
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if p.is_symlink():
            problems.append(f"symlink: {rel}")
            continue
        if p.is_dir():
            if p.name == "__pycache__":
                problems.append(f"__pycache__: {rel}")
            continue
        files += 1
        data = p.read_bytes()
        total += len(data)
        if HOME_MARKER in data:
            problems.append(f"home path: {rel}")
        if p.name.lower() == "skill.md" and rel != Path("SKILL.md"):
            problems.append(f"nested SKILL.md: {rel}")
        if p.suffix in (".pyc", ".pyo"):
            problems.append(f"bytecode: {rel}")
    if not (root / "SKILL.md").is_file():
        problems.append("no SKILL.md at the root")
    if total > MAX_BYTES:
        problems.append(f"tree is {total} bytes, over the {MAX_BYTES} byte limit")
    return {"files": files, "bytes": total, "problems": problems}


def _manifest(root, rels):
    entries = []
    for rel in rels:
        data = (root / rel).read_bytes()
        entries.append({"path": rel.as_posix(), "sha256": hashlib.sha256(data).hexdigest(), "size": len(data),
                        "mode": "755" if os.access(root / rel, os.X_OK) else "644"})
    digest = hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()
    return {"schema": "prax-teach/install-manifest@1", "files": entries, "tree_sha256": digest,
            "bytes": sum(e["size"] for e in entries)}


def default_out():
    return host.state_path("package", "prax-teach")


def _refuse_host_dirs(out):
    real_home = Path(os.path.expanduser("~")).resolve()
    for d in (".agents", ".claude", ".codex", ".hermes", ".config"):
        hd = real_home / d
        if out == hd or hd in out.parents:
            raise PackageError(f"ptk package never writes into a host directory: {out}")
    if out == host.PKG or host.PKG in out.parents:
        raise PackageError("the install tree can't live inside the package source")


def build(out=None, dry_run=False):
    """Copy the shipped files to `out` (default $PTK_STATE/package/prax-teach), write the manifest,
    check the AC-8.1 limits and run the host discovery check on the result."""
    rels = tree_files()
    src_check = _manifest(host.PKG, rels)
    out = Path(out).resolve() if out else default_out()
    _refuse_host_dirs(out)
    if dry_run:
        size = src_check["bytes"]
        nested = [r.as_posix() for r in rels if r.name.lower() == "skill.md" and r != Path("SKILL.md")]
        marked = [r.as_posix() for r in rels if HOME_MARKER in (host.PKG / r).read_bytes()]
        problems = ([f"nested SKILL.md: {n}" for n in nested] + [f"home path: {m}" for m in marked]
                    + ([f"tree is {size} bytes, over the {MAX_BYTES} byte limit"] if size > MAX_BYTES else []))
        return {"dry_run": True, "out": str(out), "files": len(rels), "bytes": size,
                "tree_sha256": src_check["tree_sha256"], "problems": problems}
    stage = out.with_name(out.name + f".stage-{os.getpid()}")
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    for rel in rels:
        dest = stage / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(host.PKG / rel, dest)
        os.chmod(dest, 0o755 if os.access(host.PKG / rel, os.X_OK) else 0o644)
    man = _manifest(stage, rels)
    (stage / MANIFEST).write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
    if out.exists():
        shutil.rmtree(out)
    stage.rename(out)
    chk = check_tree(out)
    disc = discovery_check(out)
    ok = not chk["problems"] and disc["ok"]
    return {"packaged": ok, "out": str(out), "files": chk["files"], "bytes": chk["bytes"],
            "tree_sha256": man["tree_sha256"], "problems": chk["problems"], "discovery": disc}


# ---------------------------------------------------------------- host discovery (AC-8.2)

def _frontmatter_name(skill_md):
    text = skill_md.read_text(errors="replace")
    if text.startswith("---"):
        for line in text.split("\n")[1:]:
            if line.strip() == "---":
                break
            if line.startswith("name:"):
                return line.split(":", 1)[1].strip()
    return skill_md.parent.name


def _one_level(root):
    root = Path(root)
    if not root.is_dir():
        return []
    return sorted(p / "SKILL.md" for p in root.iterdir() if (p / "SKILL.md").is_file())


def _walk(root, skip_hidden, excluded=(), support=()):
    root = Path(root)
    if not root.is_dir():
        return []
    found = []
    for r, dirs, files in os.walk(root, followlinks=True):
        has = "SKILL.md" in files
        dirs[:] = [d for d in dirs if not (skip_hidden and d.startswith(".")) and d not in excluded
                   and not (has and d in support)]
        if has:
            found.append(Path(r) / "SKILL.md")
    return sorted(found)


def _ancestors(cwd, stop):
    cwd, stop = Path(cwd).resolve(), Path(stop).resolve()
    out = [cwd]
    while cwd != stop and cwd.parent != cwd:
        cwd = cwd.parent
        out.append(cwd)
    return out


HERMES_EXCLUDED = (".git", ".github", ".hub", ".archive", ".curator_backups", ".locks", ".venv", "venv",
                   "node_modules", "site-packages", "__pycache__", ".tox", ".nox", ".pytest_cache", ".mypy_cache",
                   ".ruff_cache")
HERMES_SUPPORT = ("references", "templates", "assets", "scripts")

# Each host's documented skill locations, relative to HOME, and how it scans them.
HOSTS = {
    "claude-code": {"user": [".claude/skills"], "project": [".claude/skills"], "scan": "one-level",
                    "doc": "~/.claude/skills/<name>/SKILL.md and .claude/skills in the project"},
    "codex": {"user": [".agents/skills", ".codex/skills"], "project": [".agents/skills"], "scan": "recursive-skip-hidden",
              "doc": "~/.agents/skills (and legacy $CODEX_HOME/skills) recursively, hidden dirs skipped; "
                     "repo scope .agents/skills from cwd up to the repo root"},
    "hermes": {"user": [".hermes/skills"], "project": [], "scan": "hermes",
               "doc": "~/.hermes/skills via os.walk(followlinks=True), pruning EXCLUDED_SKILL_DIRS and support dirs"},
    "opencode": {"user": [".config/opencode/skills", ".claude/skills", ".agents/skills"],
                 "project": [".opencode/skills", ".claude/skills", ".agents/skills"], "scan": "recursive",
                 "doc": "global and project skill dirs, glob **/SKILL.md (modelled with hidden dirs included, "
                        "the stricter reading)"},
}


def discover(host_name, home, cwd=None):
    """Every SKILL.md the host would load from this HOME and cwd, as {name, path, real}."""
    spec = HOSTS[host_name]
    home = Path(home)
    roots = [home / r for r in spec["user"]]
    if cwd and spec["project"]:
        for anc in _ancestors(cwd, home if Path(cwd).resolve().is_relative_to(home.resolve()) else "/"):
            roots += [anc / r for r in spec["project"]]
    seen, out = set(), []
    for root in roots:
        if spec["scan"] == "one-level":
            found = _one_level(root)
        elif spec["scan"] == "recursive-skip-hidden":
            found = _walk(root, skip_hidden=True)
        elif spec["scan"] == "hermes":
            found = _walk(root, skip_hidden=False, excluded=HERMES_EXCLUDED, support=HERMES_SUPPORT)
        else:
            found = _walk(root, skip_hidden=False)
        for f in found:
            real = f.resolve()
            if real in seen:
                continue
            seen.add(real)
            out.append({"name": _frontmatter_name(f), "path": str(f), "real": str(real)})
    return out


def prax_entries(entries, install_roots):
    """Entries that load a prax-teach install: by name, or because their file lives inside one."""
    roots = [Path(r).resolve() for r in install_roots]
    return [e for e in entries if e["name"].startswith("prax-teach")
            or any(Path(e["real"]).is_relative_to(r) for r in roots)]


def make_home(home, v2_tree, mirrors=True):
    """A throwaway HOME laid out like this Mac: the v2 install in ~/.agents/skill-library, the canonical
    ~/.agents/skills link to it, and each host's skill dir as a symlink mirror of ~/.agents/skills."""
    home = Path(home)
    if home.exists():
        shutil.rmtree(home)
    lib = home / ".agents" / "skill-library" / "prax-teach-v2"
    shutil.copytree(v2_tree, lib, symlinks=True)
    (home / V2_LINK).parent.mkdir(parents=True)
    (home / V2_LINK).symlink_to(Path("..") / "skill-library" / "prax-teach-v2")
    if mirrors:
        for d in (".claude", ".hermes", ".config/opencode"):
            (home / d).mkdir(parents=True, exist_ok=True)
            (home / d / "skills").symlink_to(home / ".agents" / "skills")
        (home / ".codex").mkdir(exist_ok=True)
    return home


def discovery_check(tree, homes_root=None):
    """For every host: a throwaway HOME with v2 linked and this tree installed side by side (never
    registered, D17.12), from three cwds. Each must see exactly one prax-teach entry."""
    tree = Path(tree)
    homes_root = Path(homes_root) if homes_root else host.state_path("hosts", "package-check")
    fake_v2 = homes_root / "v2-fixture"
    write_fake_v2(fake_v2)
    results, ok = {}, True
    for name in HOSTS:
        home = make_home(homes_root / name, fake_v2)
        dest = home / CANDIDATE
        shutil.copytree(tree, dest)
        per = {}
        for label, cwd in (("home", home), ("tree-root", dest), ("tree-inner", dest / "ptk" / "state")):
            entries = prax_entries(discover(name, home, cwd), [home / ".agents" / "skill-library"])
            per[label] = [e["name"] for e in entries]
            ok = ok and len(entries) == 1
        results[name] = per
    return {"ok": ok, "hosts": results}


def write_fake_v2(path):
    """A minimal stand-in for the installed v2 (its real tree is 212 MB): its root SKILL.md only."""
    path = Path(path)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text("---\nname: prax-teach-v2\ndescription: stand-in for the accepted v2 install\n"
                                   "---\n\n# Prax Teach v2 (test stand-in)\n")
    (path / "VERSION").write_text("v2\n")
    return path


# ---------------------------------------------------------------- install, flip, rollback (AC-8.6)

def _guard_home(home, allow_real_home):
    home = Path(home).resolve()
    if home == Path(os.path.expanduser("~")).resolve() and not allow_real_home:
        raise PackageError("refusing to install into the real HOME; that step is Prax's (D19.1)")
    return home


def install(tree, home, flip=False, learners=(), when=None, allow_real_home=False):
    """Step 2 (and 4 with flip=True) of the rollout: copy the tree to ~/.agents/skill-library/prax-teach-v2.1,
    snapshot each learner workspace, then (flip) migrate it to schema 2 and repoint ~/.agents/skills/prax-teach-v2.
    Returns the rollback record, also written to $PTK_STATE/rollback/."""
    from .state import schema2
    home = _guard_home(home, allow_real_home)
    when = when or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    stamp = when.replace(":", "").replace("-", "")
    dest = home / CANDIDATE
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(tree, dest)
    link = home / V2_LINK
    record = {"home": str(home), "installed": str(dest), "when": when, "flipped": False,
              "link": str(link), "previous_target": os.readlink(link) if link.is_symlink() else None,
              "learners": []}
    for i, ws in enumerate(learners):
        snap = host.state_path("snapshots", f"{Path(ws).name}-{stamp}-{i}-{secrets.token_hex(4)}")
        s = schema2.snapshot(str(ws), str(snap))
        entry = {"workspace": str(ws), "snapshot": s["snapshot"], "schema_before": s["schema_version"]}
        if flip and s["schema_version"] == "1":
            m = schema2.migrate(str(ws), migrated_at=when, snapshot_dest=str(snap) + "-migrate")
            entry["migrated"] = m["to"]
        record["learners"].append(entry)
    if flip:
        if not link.is_symlink():
            raise PackageError(f"{link} is not a symlink; nothing to flip")
        tmp = link.with_name(link.name + f".flip-{os.getpid()}")
        tmp.symlink_to(Path("..") / "skill-library" / dest.name)
        os.replace(tmp, link)
        record["flipped"] = True
    rec_path = host.state_path("rollback", f"{stamp}-{secrets.token_hex(4)}.json")
    rec_path.parent.mkdir(exist_ok=True)
    rec_path.write_text(json.dumps(record, indent=1))
    record["record"] = str(rec_path)
    return record


def rollback(record, log=print):
    """Point ~/.agents/skills/prax-teach-v2 back at its previous target and restore each learner snapshot.
    Prints how many events recorded since the snapshot are lost."""
    from .state import schema2
    if isinstance(record, (str, Path)):
        record = json.loads(Path(record).read_text())
    link = Path(record["link"])
    out = {"link_restored": False, "learners": [], "lost_events": 0}
    if record.get("flipped") and record.get("previous_target"):
        tmp = link.with_name(link.name + f".rollback-{os.getpid()}")
        tmp.symlink_to(record["previous_target"])
        os.replace(tmp, link)
        out["link_restored"] = True
    for entry in record["learners"]:
        r = schema2.rollback(entry["workspace"], entry["snapshot"])
        out["learners"].append({"workspace": entry["workspace"], "lost": r["lost"], "lost_events": r["lost_events"]})
        out["lost_events"] += r["lost_events"]
    log(f"rollback: {out['lost_events']} learner event(s) recorded after the snapshot are lost")
    return out
