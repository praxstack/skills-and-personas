#!/usr/bin/env python3
"""Read-only verification against the controller's private baseline; emit counts only."""
import hashlib,json,pathlib,subprocess,os
root=pathlib.Path(__file__).resolve().parents[3]
b=json.loads((root/'.superpowers/sdd/PLAN/baseline.json').read_text())
installed=pathlib.Path('/Users/prax/.local/share/prax-teach/releases/v3.0.1-33cfd55')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
issues=[]
for p,h in b['installedHashes'].items():
 if sha(installed/p)!=h:issues.append('installed hash mismatch')
for p,target in b['installedLinks'].items():
 if not pathlib.Path(p).is_symlink() or str(pathlib.Path(p).resolve())!=target:issues.append('installed link mismatch')
for p,h in b['frozenCheckHashes'].items():
 if sha(root/p)!=h:issues.append('frozen checker mismatch')
paths=list(b['protectedGitBlobs'])
proc=subprocess.run(['git','hash-object','--stdin-paths'],cwd=root,input='\n'.join(paths)+'\n',text=True,capture_output=True,check=True)
for p,h in zip(paths,proc.stdout.splitlines(),strict=True):
 if h!=b['protectedGitBlobs'][p]:issues.append('protected working file mismatch')
tracked=subprocess.check_output(['git','ls-tree','-rz','HEAD','--',*paths],cwd=root).split(b'\0')
blobs={e.split(b'\t')[1].decode():e.split()[2].decode() for e in tracked if e}
if blobs!=b['protectedGitBlobs']:issues.append('protected committed blob mismatch')
# Verify the old general-teacher builder's identity independently of generated comparison receipts.
builder='teacher/skills/explorable/scripts/build.py'
original=pathlib.Path('/Users/prax/.local/share/prax-teach/releases/v3-0d20ff7')/builder
source=subprocess.check_output(['git','show','0d20ff7:skills/'+builder],cwd=root)
identity={'reference':'0d20ff7','builder_sha256':sha(original),'git_builder_sha256':hashlib.sha256(source).hexdigest(),'equal':source==original.read_bytes(),'historical_dc6a498_e2e':'NOT RUN: different historical baseline; no equivalence or held-out improvement inferred'}
if not identity['equal']:issues.append('original general teacher builder mismatch')
result={'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'installed_files':len(b['installedHashes']),'installed_links':len(b['installedLinks']),'frozen_checkers':len(b['frozenCheckHashes']),'protected_git_blobs':len(paths),'issues':issues,'original_general_teacher':identity,'original':b['original'],'accepted':b['accepted'],'rollback':'Installed links remain at v3.0.1-33cfd55; no activation. Candidate rollback: preserve base 4b30f53; do not alter unrelated work.'}
print(json.dumps(result,indent=2));raise SystemExit(bool(issues))
