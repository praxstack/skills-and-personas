#!/usr/bin/env python3
"""Actual exemplar/browser controls with SYNTHETIC media, not narrated acceptance."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from check_render_receipts import check

ROOT = Path(__file__).resolve().parent.parent
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--image', required=True)
p.add_argument('--docker-context', required=True)
a = p.parse_args()
if not re.fullmatch(r'sha256:[0-9a-f]{64}', a.image): p.error('immutable local image ID required')
subprocess.run(['docker', '--context', a.docker_context, 'image', 'inspect', a.image], check=True, stdout=subprocess.DEVNULL)

def render(source, out):
    subprocess.run([sys.executable, str(ROOT/'skills/teacher/skills/course/scripts/sandbox_course.py'), 'render', str(source), '--out', str(out), '--image', a.image, '--docker-context', a.docker_context, '--timeout', '300'], check=True)

def stamp(t):
    ms = round(t * 1000)
    return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02}.{ms%1000:03}'

with tempfile.TemporaryDirectory(prefix='teacher-media-ci-') as tmp:
    root = Path(tmp)
    source = root/'source'
    shutil.copytree(ROOT/'examples/teach-visual-candidate/base-rates/source', source, ignore=shutil.ignore_patterns('videos'))
    render(source, root/'static')
    check(root/'static', require_video=False)
    meta = json.loads((root/'static/render-evidence.json').read_text())['meta']
    timing = json.loads((source/'course.json').read_text())['renderTiming']
    videos = source/'videos'; videos.mkdir()
    # Generate inert codec fixture inside the same reviewed image, no host authored execution.
    with (videos/'base-rates.mp4').open('wb') as out:
        subprocess.run(['docker', '--context', a.docker_context, 'run', '--rm', '--pull=never', '--network=none', '--read-only', '--cap-drop=ALL', '--security-opt=no-new-privileges', '--pids-limit=64', '--memory=512m', '--cpus=1', '--user=65534:65534', '--entrypoint=ffmpeg', a.image, '-v', 'error', '-f', 'lavfi', '-i', 'color=c=white:s=960x540:r=24', '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000', '-t', str(timing['total']), '-c:v', 'libvpx-vp9', '-deadline', 'realtime', '-cpu-used', '8', '-threads', '2', '-c:a', 'libopus', '-movflags', 'frag_keyframe+empty_moov', '-f', 'mp4', 'pipe:1'], check=True, stdout=out, timeout=300)
    cues = ['WEBVTT', '']
    for i, (scene, time) in enumerate(zip(meta['scenes'], timing['scenes'])):
        cues.extend([str(i+1), f"{stamp(time['voiceAt'])} --> {stamp(time['start']+time['dur'])}", scene['say'], ''])
    (videos/'base-rates.vtt').write_text('\n'.join(cues)+'\n')
    print('SYNTHETIC codec/runtime fixture; not narrated media acceptance', flush=True)
    for index in range(3):
        out = root/f'media-{index}'
        render(source, out)  # Any failed run stops the sequence; never retry or skip.
        print(f'fresh container {index+1}: {check(out)} existing checks; both QA statuses passed', flush=True)
    # Ordinary caption behavior uses the explicit synthetic codec fixture above.
    subprocess.run(['node', str(ROOT/'skills/teacher/skills/explorable/scripts/test_caption_tail.mjs'), str(videos/'base-rates.mp4')], check=True)
