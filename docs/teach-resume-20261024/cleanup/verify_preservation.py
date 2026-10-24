import hashlib,json,os,subprocess
from pathlib import Path
r=Path('/Users/prax/Developer/skills-and-personas-recovery-20261016/.worktrees/teach-finish-20261024');out=r/'docs/teach-resume-20261024/cleanup'
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
b=json.loads((r/'.superpowers/sdd/RESUME-20261024/baseline.json').read_text());installed=Path(b['installedRoot'])
actual={str(p.relative_to(installed)):h(p) for p in installed.rglob('*') if p.is_file() and not p.is_symlink()}
assert actual==b['installed'],(len(actual),len(b['installed']))
links={p:str(Path(p).resolve()) for p in b['links']};assert links==b['links']
f=json.loads((r/'.superpowers/sdd/RESUME-20261024/PRODUCT-PHASE-BASELINE.json').read_text())['frozenFiles'];assert all(h(r/p)==sha for p,sha in f.items())
product=json.loads((r/'docs/teach-resume-20261024/playback/caption-narrated-3/command.json').read_text())['product'];assert all(h(r/p)==sha for p,sha in product.items())
assert h(r/'skills/teacher/skills/explorable/scripts/bundle_templates.mjs')=='888559f6c60aab57781c03a62aaac9bad7ace8456fb93186711f677eb968e7b8'
historical=subprocess.check_output(['git','diff','--name-only','d246f6f','--','docs/teach-finish-20261024','docs/teach-resume-20261024/playback','docs/teach-resume-20261024/consent'],cwd=r).decode();assert not historical,historical
v=json.loads((r/'skills/teacher/VENDOR.json').read_text())['skills']['manim-video'];old=json.loads(subprocess.check_output(['git','show','d246f6f:skills/teacher/VENDOR.json'],cwd=r))['skills']['manim-video'];assert all(v[k]==value for k,value in old.items() if k not in {'tree_sha256','files','local_changes'})
(out/'preservation.json').write_text(json.dumps({'installedRoot':str(installed),'installedFilesMatched':len(actual),'links':links,'frozenFiles':f,'passedNarrationRelevantSourceMatched':product,'captionTemplateSha256':h(r/'skills/teacher/skills/explorable/scripts/bundle_templates.mjs'),'historicalTrackedReceiptsChanged':False,'vendorOriginRetained':True,'sourceRollback':'d246f6f','installedRollback':str(installed)},indent=2)+'\n')
print('installed',len(actual),'files, five links, six frozen methods, narration modules, vendor origin and historical receipts unchanged')
