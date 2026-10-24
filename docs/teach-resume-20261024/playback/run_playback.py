"""Task-local paired observation; production executors remain unmodified."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path.cwd()
SCRIPTS = ROOT / 'skills/teacher/skills/course/scripts'
sys.path.insert(0, str(SCRIPTS))
import sandbox_course as sandbox

IMAGE = 'sha256:96e50ad889f7fb38c3360c76c7908d3a9b6b26ec590b82cc316993d6eeae520f'
MEDIA = Path('/Users/prax/Developer/prax-teach-candidate-handoff-20261020/staging/media')
parser = argparse.ArgumentParser()
parser.add_argument('label')
parser.add_argument('--diagnostic', action='store_true')
parser.add_argument('--baseline', action='store_true')
args = parser.parse_args()
record = ROOT / 'docs/teach-resume-20261024/playback' / args.label
record.mkdir(parents=True, exist_ok=False)
scratch = ROOT / '.superpowers/sdd/RESUME-20261024/playback-scratch' / args.label
scratch.mkdir(parents=True, exist_ok=False)
if args.baseline:
    baseline_path = scratch / 'sandbox_baseline.py'
    baseline_path.write_bytes(subprocess.check_output(['git', 'show', 'bf0bcf9:skills/teacher/skills/course/scripts/sandbox_course.py']))
    spec = importlib.util.spec_from_file_location('sandbox_baseline', baseline_path)
    sandbox = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sandbox)
    # The adapter's trusted tool source stays the frozen/current first-party tree.
    sandbox.HERE = SCRIPTS
    sandbox.SKILLS = SCRIPTS.parent.parent
source = scratch / 'source'
shutil.copytree(ROOT / 'examples/teach-visual-candidate/base-rates/source', source)
(source / 'videos').mkdir(exist_ok=True)
for suffix in ['mp4', 'vtt']:
    (source / 'videos' / f'base-rates.{suffix}').write_bytes((MEDIA / f'lesson.{suffix}').read_bytes())

def hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()}

identity = {'argv': sys.argv, 'image': IMAGE, 'context': 'colima-teach-security',
            'baselineAdapter': args.baseline, 'outerTimeoutSeconds': 180,
            'diagnosticOnly': args.diagnostic, 'source': hashes(source),
            'product': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in [SCRIPTS / n for n in ['sandbox_course.py', 'render_course.mjs', 'render_course.py']]}}
(record / 'command.json').write_text(json.dumps(identity, indent=2) + '\n')
if args.diagnostic:
    original_copy = sandbox.copy_tools
    def copy_observed(tools):
        original_copy(tools)
        path = tools / 'course/scripts/render_course.mjs'
        text = path.read_text()
        text = text.replace("role:[...args.join(' ').matchAll", "argv:args,taskNames:await Promise.all((await readdir('/proc/'+pid+'/task')).map(async tid=>({tid:Number(tid),comm:(await readFile('/proc/'+pid+'/task/'+tid+'/comm','utf8')).trim()}))),role:[...args.join(' ').matchAll")
        text = text.replace('const sample={phase,pids:', "const sample={phase,wallMs:Date.now(),cpuMax:(await readFile('/sys/fs/cgroup/cpu.max','utf8')).trim(),memoryMax:(await readFile('/sys/fs/cgroup/memory.max','utf8')).trim(),swapMax:(await readFile('/sys/fs/cgroup/memory.swap.max','utf8')).trim(),memoryCurrent:(await readFile('/sys/fs/cgroup/memory.current','utf8')).trim(),pids:")
        text = text.replace("let browser=await launch(chromium);", "let browser=await launch(chromium);console.error('BROWSER_VERSION '+JSON.stringify(await (await browser.newBrowserCDPSession()).send('Browser.getVersion')));")
        text = text.replace("await measure('before-video-navigation');", "const media=await ctx.newCDPSession(page);for(const event of ['playerPropertiesChanged','playerEventsAdded','playerMessagesLogged','playerErrorsRaised'])media.on('Media.'+event,data=>console.error('MEDIA '+JSON.stringify({event,data})));await media.send('Media.enable');await measure('before-video-navigation');")
        text = text.replace("await measure('before-play');", "await measure('before-play');let sampling=true;const samples=(async()=>{let last='';while(sampling){const s=await measure('audio-startup-poll');const key=JSON.stringify(s.processes.map(p=>[p.pid,p.threads]));if(key===last)runtime.pop();last=key;await new Promise(r=>setTimeout(r,200))}})();")
        text = text.replace("await measure('after-playback-advance');", "await measure('after-playback-advance');console.error('AUDIO_OBSERVATION '+JSON.stringify(await page.locator('video').evaluate(v=>({time:v.currentTime,audioBytes:v.webkitAudioDecodedByteCount,frames:v.webkitDecodedFrameCount,paused:v.paused,error:v.error?.message}))));await page.waitForFunction(()=>window.__interactiveVideo.video.currentTime>2.5,{},{timeout:5000});console.error('AUDIO_PAST_ONSET '+JSON.stringify(await page.locator('video').evaluate(v=>({time:v.currentTime,audioBytes:v.webkitAudioDecodedByteCount,frames:v.webkitDecodedFrameCount,paused:v.paused,error:v.error?.message}))));await measure('after-narration-onset');")
        text = text.replace("await measure('after-visible-explorer');", "await measure('after-visible-explorer');sampling=false;await samples;")
        path.write_text(text)
        (record / 'observer-render.mjs').write_text(text)
    sandbox.copy_tools = copy_observed

start = time.monotonic()
try:
    sandbox.execute(source, scratch / 'output', IMAGE, mode='render', context='colima-teach-security', timeout=180)
except Exception as exc:
    (record / 'result.json').write_text(json.dumps({'ok': False, 'error': str(exc), 'seconds': time.monotonic()-start}, indent=2)+'\n')
    raise
else:
    output = scratch / 'output'
    for name in ['render-evidence.json', 'runtime-evidence.json', 'lesson-status.json', 'visual-status.json', 'lesson-check.txt', 'visual-check.txt']:
        shutil.copyfile(output / name, record / name)
    (record / 'artifact-sha256.json').write_text(json.dumps(hashes(output), indent=2)+'\n')
    checks = json.loads((output / 'render-evidence.json').read_text())['checks']
    result = {'ok': all(c['ok'] for c in checks), 'checks': len(checks), 'seconds': time.monotonic()-start,
              'lesson': json.loads((output/'lesson-status.json').read_text()),
              'visual': json.loads((output/'visual-status.json').read_text())}
    (record / 'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))
