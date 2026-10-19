#!/usr/bin/env python3
"""Activate only teacher/teach-pro-max pointers, with exact-source checks and rollback."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,sys,uuid
repo=Path(__file__).resolve().parents[6]
release=Path("/Users/prax/.local/share/prax-teach/releases/v3-0d20ff7")
report=Path(__file__).resolve().parent.parent/"private-evaluation/candidate4-accepted-redacted-report.json"
assert hashlib.sha256(report.read_bytes()).hexdigest()=="1f24117a7e66b957dafc6fa5566bdecc9d433f94cc8581c22f35d6c8c581a1c4"
r=json.loads(report.read_text());assert r["evaluator_release_ready"] and r["release_accepted"] and r["e2e"]["passed"]==56
comparison=Path(__file__).resolve().parent.parent/"clean-install-20261019/source-byte-comparison.json";files=json.loads(comparison.read_text())["files"]
for item in files:
    rel=Path(item["path"]);p=release.joinpath(*rel.parts[1:]);assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==item["sha256"],str(p)
roots={"agents":Path("/Users/prax/.agents/skills"),"codex":Path("/Users/prax/.codex/skills"),"claude":Path("/Users/prax/.claude/skills"),"cursor":Path("/Users/prax/.cursor/skills"),"hermes":Path("/Users/prax/.hermes/skills"),"pi":Path("/Users/prax/.pi/agent/skills"),"opencode":Path("/Users/prax/.config/opencode/skills")}
canonical=roots["agents"];plan=[];seen=set()
for host,root in roots.items():
    assert root.is_dir(),str(root)
    if root.resolve() in seen:continue
    seen.add(root.resolve())
    for name in ["teacher","teach-pro-max"]:
        path=root/name;target=str(release/name if host=="agents" else canonical/name)
        if path.is_symlink():
            old=os.readlink(path)
            if old==target:continue
            before={"kind":"symlink","target":old}
        elif path.exists():raise SystemExit("Refusing an unexpected real file/directory at "+str(path))
        else:before={"kind":"missing"}
        plan.append({"path":str(path),"before":before,"after":{"kind":"symlink","target":target}})
assert plan,"Already active; refusing to manufacture a second activation receipt"
backup=Path("/Users/prax/.local/state/prax-teach")/("activation-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"));backup.mkdir(parents=True)
manifest={"product_source":"0d20ff7722910d12256240af0897070255cfc4f3","source_files_verified":len(files),"accepted_report_sha256":hashlib.sha256(report.read_bytes()).hexdigest(),"human_verdict":"I listened to all four. They sound good.","release_root":str(release),"runtime_env":"/Users/prax/.local/share/prax-teach/runtime/v3/env.sh","changes":plan,"host_roots":{k:str(v) for k,v in roots.items()},"phase":"prepared"}
(backup/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
rollback='#!/usr/bin/env python3\nfrom pathlib import Path\nimport argparse,json,os,uuid\np=argparse.ArgumentParser();p.add_argument("--apply",action="store_true");a=p.parse_args();root=Path(__file__).resolve().parent;m=json.loads((root/"manifest.json").read_text());conflicts=[]\nfor row in reversed(m["changes"]):\n    target=Path(row["path"])\n    if not target.is_symlink() or os.readlink(target)!=row["after"]["target"]:\n        conflicts.append(str(target));continue\n    print(("restore " if a.apply else "would restore ")+str(target))\n    if a.apply:\n        before=row["before"]\n        if before["kind"]=="missing":target.unlink()\n        else:\n            temp=target.with_name("."+target.name+".rollback-"+uuid.uuid4().hex);os.symlink(before["target"],temp);os.replace(temp,target)\nif conflicts:raise SystemExit("Refused changed pointers: "+", ".join(conflicts))\n'
(backup/"rollback.py").write_text(rollback)
applied=[]
try:
    for row in plan:
        path=Path(row["path"]);before=row["before"]
        assert (path.is_symlink() and os.readlink(path)==before.get("target")) if before["kind"]=="symlink" else not (path.exists() or path.is_symlink())
        if before["kind"]=="missing":os.symlink(row["after"]["target"],path)
        else:
            temp=path.with_name("."+path.name+".activate-"+uuid.uuid4().hex);os.symlink(row["after"]["target"],temp);os.replace(temp,path)
        applied.append(row)
    for host,root in roots.items():
        for name in ["teacher","teach-pro-max"]:assert (root/name).resolve()==release/name,(host,name)
except BaseException:
    for row in reversed(applied):
        path=Path(row["path"])
        if path.is_symlink() and os.readlink(path)==row["after"]["target"]:
            path.unlink()
            if row["before"]["kind"]=="symlink":os.symlink(row["before"]["target"],path)
    raise
manifest["phase"]="activated";manifest["host_resolution_verified"]={host:{name:str((root/name).resolve()) for name in ["teacher","teach-pro-max"]} for host,root in roots.items()};(backup/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
receipt={**manifest,"backup":str(backup),"rollback":str(backup/"rollback.py"),"scope":"General teacher and compatible entry only. Existing C pack, unrelated skills and host sessions preserved."};(Path(__file__).resolve().parent/"ACTIVATION.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps({"phase":"activated","pointers_changed":len(plan),"host_views_verified":len(roots),"source_files_verified":len(files),"backup":str(backup)},indent=2))
