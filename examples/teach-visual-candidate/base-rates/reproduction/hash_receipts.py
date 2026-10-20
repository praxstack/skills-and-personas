#!/usr/bin/env python3
"""Hash source, tools and accepted output separately; receipts never hash themselves."""
from pathlib import Path
import hashlib,json
base=Path(__file__).resolve().parents[1];repo=base.parents[2]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=[base/'source/lesson.lesson.js',base/'source/course.json',*sorted((base/'reproduction').glob('*'))]
tools=[repo/'skills/teacher/skills/course/scripts'/n for n in ['sandbox_course.py','render_course.py','render_course.mjs','test_render_refusal.py','Dockerfile.media','README.sandbox.md']]
output=sorted(p for p in (base/'results/final-verified').rglob('*') if p.is_file())
receipt={'source':{str(p.relative_to(repo)):digest(p) for p in source if p.is_file()},'tools':{str(p.relative_to(repo)):digest(p) for p in tools},'output':{str(p.relative_to(base)):digest(p) for p in output},'output_files':len(output),'output_entries':len(list((base/'results/final-verified').rglob('*'))),'output_bytes':sum(p.stat().st_size for p in output)}
(base/'results/final-verified-hashes.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k.startswith('output_')},indent=2))
