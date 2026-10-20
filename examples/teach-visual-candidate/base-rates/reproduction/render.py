#!/usr/bin/env python3
"""Copy immutable input bytes to single-link files; run only the offline sandbox."""
from pathlib import Path
import argparse, shutil, subprocess, tempfile
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--no-video',action='store_true');a=p.parse_args()
base=Path(__file__).resolve().parents[1];repo=base.parents[2]
with tempfile.TemporaryDirectory(prefix='base-rate-input-') as tmp:
    src=Path(tmp)/'course';shutil.copytree(base/'source',src,ignore=shutil.ignore_patterns('videos') if a.no_video else None)
    subprocess.run(['python3',str(repo/'skills/teacher/skills/course/scripts/sandbox_course.py'),'render',str(src),'--out',str(base/'results'/a.name),'--image','sha256:96e50ad889f7fb38c3360c76c7908d3a9b6b26ec590b82cc316993d6eeae520f','--docker-context','colima-teach-security','--timeout','300'],check=True)
