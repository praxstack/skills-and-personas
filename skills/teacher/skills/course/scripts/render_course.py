#!/usr/bin/env python3
"""Fixed offline render job. Invoked only by sandbox_course's container supervisor.

Not a replacement for validate: exports and focused product receipts can exist
when the unchanged whole-course checker fails. All child execution stays inside
its calling container and the same aggregate output/deadline limits apply.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from build_course import build_course
from safe_course import validate_course_manifest

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('course',type=Path)
parser.add_argument('--out',required=True,type=Path)
parser.add_argument('--trust-authored-code',action='store_true')
args=parser.parse_args()
if not args.trust_authored_code:
    parser.error('refusing authored execution without --trust-authored-code; use sandbox_course.py render')
course=args.course; out=args.out
checked=validate_course_manifest(course)
if len(checked.lessons)!=1:
    raise SystemExit('render supports exactly one lesson')
ident=next(iter(checked.lessons))
build_course(course,out/'site',trust_authored_code=True)
page=out/'site'/f'{ident}.html'
scripts=Path(__file__).resolve().parent
explorable=scripts.parent.parent/'explorable'/'scripts'
cmd=['node',str(explorable/'bundle_lesson.mjs'),str(page),'--out',str(out/'bundle'),'--still-step','5']
video=course/'videos'/f'{ident}.mp4'
if video.exists():
    timing=checked.data.get('renderTiming')
    if not isinstance(timing,dict):
        raise SystemExit('render requires matching renderTiming for video')
    timing_path=out/'timing.json'; timing_path.write_text(json.dumps(timing))
    cmd += ['--video',str(video),'--timing',str(timing_path)]
subprocess.run(cmd,check=True)
subprocess.run(['node',str(scripts/'render_course.mjs'),str(page),str(out),'--trust-authored-code'],check=True)
# Existing QA stays unchanged. Preserve its report and exit status separately.
for label,args in [
 ('lesson',['node',str(explorable/'test_lesson.mjs'),str(page)]),
 ('visual',['node',str(scripts.parent.parent/'visual-qa/scripts/check_page.mjs'),str(page),'--out',str(out/'qa'),'--all-steps','--json'])]:
    result=subprocess.run(args,capture_output=True,text=True)
    (out/f'{label}-check.txt').write_text(result.stdout+result.stderr)
    (out/f'{label}-status.json').write_text(json.dumps({'returncode':result.returncode}))
