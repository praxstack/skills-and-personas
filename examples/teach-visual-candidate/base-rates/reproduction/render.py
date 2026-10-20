#!/usr/bin/env python3
"""Copy immutable input bytes to single-link files; run only the offline sandbox."""
from pathlib import Path
import argparse, shutil, subprocess, tempfile
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--no-video',action='store_true')
p.add_argument('--image', required=True, help='Reviewed local immutable sha256 image ID')
p.add_argument('--docker-context', required=True, help='Explicit Docker context; does not change the global context')
a=p.parse_args()
if Path(a.name).name != a.name or a.name in {'.', '..'}:
    p.error('name must be one new output directory name')
base=Path(__file__).resolve().parents[1];repo=base.parents[2]
with tempfile.TemporaryDirectory(prefix='base-rate-input-') as tmp:
    src=Path(tmp)/'course';shutil.copytree(base/'source',src,ignore=shutil.ignore_patterns('videos') if a.no_video else None)
    subprocess.run(['python3',str(repo/'skills/teacher/skills/course/scripts/sandbox_course.py'),'render',str(src),'--out',str(base/'results'/a.name),'--image',a.image,'--docker-context',a.docker_context,'--timeout','300'],check=True)

subprocess.run(['python3',str(repo/'scripts/check_render_receipts.py'),str(base/'results'/a.name),*(['--no-video'] if a.no_video else [])],check=True)
