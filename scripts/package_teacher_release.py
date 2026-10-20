#!/usr/bin/env python3
"""Build deterministic teaching ZIPs from committed Git objects, with external receipts."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent.parent


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def package(revision, version, output, candidate=False):
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("version must have three numeric components")
    commit = git("rev-parse", "--verify", revision + "^{commit}").decode().strip()
    if output.exists() and any(output.iterdir()):
        raise ValueError("output must be empty; preserve previous artifacts")
    output.mkdir(parents=True, exist_ok=True)
    trees = {}
    for entry in git("ls-tree", "-rz", commit, "--", "skills/teacher", "skills/teach-pro-max", *(["skills/transcript-pipeline", "examples/teach-visual-candidate/base-rates", "scripts/check_render_receipts.py"] if candidate else [])).split(b"\0"):
        if not entry:
            continue
        meta, raw_path = entry.split(b"\t", 1)
        mode, kind, oid = meta.decode().split()
        path = raw_path.decode()
        if mode not in {"100644", "100755"} or kind != "blob":
            raise ValueError(f"release rejects nonregular Git object: {path}")
        if any(part in {"node_modules", "__pycache__", ".tmp.driveupload"} for part in Path(path).parts):
            continue
        trees[path] = (git("cat-file", "blob", oid), int(mode, 8))
    if not all(f"skills/{name}/SKILL.md" in trees for name in ("teacher", "teach-pro-max")):
        raise ValueError("both public skill entries must be present")
    candidate_notice = ("UNACCEPTED CANDIDATE: Task 8 consecutive playback failed; course consent checker approval pending. Not eligible for stable release or installation: validation incomplete. Historical evidence is not current acceptance.\n\n" if candidate else "")
    start = f"""{candidate_notice}# Prax Teach {version}

The complete teacher and compatible teach-pro-max source trees are in skills/.
Keep every supporting file. Core use is explanation first; practice and
persistent learner state require consent.

Install teacher to an explicit agent folder:

    bash skills/teacher/install.sh --dir /path/to/agent/skills

teach-pro-max can also be copied as one whole folder. It uses teacher when
present and its bundled compatibility engine when installed alone.

Python and Node are needed by build/check scripts. Browser/video work also needs
Playwright, Chromium and ffmpeg. Optional voices/models are separate setup
steps. No dependency downloads or paid services start merely by extracting.

For untrusted executable examples, use the bundled Docker sandbox instructions:
skills/teacher/skills/explorable/references/SANDBOX.md
A Docker daemon and explicitly provisioned image are required for that mode.

Original quality evidence: 52 automated criteria plus 4 human listening
approvals. This patch makes no new claim of learning gains or world-best design.
Source commit: {commit}
""".encode()
    collections = {
        f"prax-teach-v{version}-source.zip": dict(trees),
        "teacher.zip": {p[len("skills/"):]: value for p, value in trees.items() if p.startswith("skills/teacher/")},
        "teach-pro-max.zip": {p[len("skills/"):]: value for p, value in trees.items() if p.startswith("skills/teach-pro-max/")},
    }
    collections[f"prax-teach-v{version}-source.zip"]["START-HERE.md"] = (start, 0o100644)
    for name in ("LICENSE", "docs/teach-pro-max/USAGE-GUIDE.md"):
        collections[f"prax-teach-v{version}-source.zip"][name] = (git("show", f"{commit}:{name}"), 0o100644)
    manifest = {"version": version, "source_commit": commit, "scope": "teacher and teach-pro-max source; no runtime weights or new lessons", "assets": []}
    if candidate:
        collections["transcript-pipeline.zip"] = {p[len("skills/"):]: v for p, v in trees.items() if p.startswith("skills/transcript-pipeline/")}
        for component in ("teacher", "teach-pro-max", "transcript-pipeline"):
            notice = (candidate_notice + f"Source commit: {commit}\n").encode()
            collections[f"{component}.zip"][f"{component}/CANDIDATE-STATUS.txt"] = (notice, 0o100644)
        manifest["status"] = "unaccepted-candidate"
        manifest["scope"] = "committed teacher, teach-pro-max, transcript-pipeline and exemplar source; generated media separate"
    for name, files in collections.items():
        path = output / name
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for relative, (data, mode) in sorted(files.items()):
                info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = mode << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data)
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise ValueError("archive CRC failure")
            for info in archive.infolist():
                if info.filename.startswith("/") or ".." in Path(info.filename).parts or (info.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError("unsafe archive member")
        manifest["assets"].append({"name": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                   "bytes": path.stat().st_size, "files": len(files)})
    (output / "RELEASE-MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (output / "SHA256SUMS").write_text("".join(f"{a['sha256']}  {a['name']}\n" for a in manifest["assets"]))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", default="HEAD")
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate", action="store_true", help="Include transcript/exemplar source and explicit unaccepted labels")
    args = parser.parse_args()
    package(args.revision, args.version, args.output, args.candidate)
