import json,os,subprocess,time
from pathlib import Path
r=Path('/Users/prax/Developer/skills-and-personas-recovery-20261016/.worktrees/teach-finish-20261024');os.chdir(r);out=r/'docs/teach-resume-20261024/cleanup'
env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH='/Users/prax/.cache/uv/archive-v0/ZYsqvPvo6Drakewc',TMPDIR=str(Path.home()),TEACHER_SANDBOX_IMAGE='sha256:c3adc592ed3413a4e7d4e9496911f317e223efb5d86712a18cb2286231c79a6a',TEACHER_SANDBOX_CONTEXT='colima-teach-security',ENRICHMENT_TEST_IMAGE='sha256:6bae2ca9852061ba0abebef8b07f9f3ea96a799c9f7ef4d31f0a6f135ae5ea6c',ENRICHMENT_TEST_CONTEXT='colima-teach-security',TEACHER_BROWSER_TESTS='1',CHROMIUM_PATH='/Users/prax/.local/share/prax-teach/runtime/v3/browsers/chromium_headless_shell-1243/chrome-headless-shell-mac-arm64/chrome-headless-shell',PLAYWRIGHT_MODULE='/Users/prax/.local/share/prax-teach/runtime/v3/node/node_modules/playwright')
py='/Users/prax/.local/share/uv/tools/crawl4ai/bin/python'
commands=[('code-sandbox',[py,'-m','unittest','discover','-s','skills/teacher/skills/explorable/scripts','-p','test_sandbox_code.py','-v']),('transcript-sandbox',[py,'-m','unittest','discover','-s','skills/transcript-pipeline/scripts','-p','test_sandbox_resource_enrichment.py','-v']),('browser-transport',[py,'-m','unittest','discover','-s','skills/transcript-pipeline/scripts','-p','test_browser_transport.py','-v']),('wrapper',[py,'-m','unittest','discover','-s','skills/teacher/skills/course/scripts','-p','test_chromium_wrapper.py','-v']),('caption-browser',['node','skills/teacher/skills/explorable/scripts/test_caption_tail.mjs',str(r/'deliverables/teach-resume-20261024/demo/bundle/lesson.mp4')])]
receipts=[]
for name,cmd in commands:
 start=time.monotonic()
 with (out/(name+'.txt')).open('w') as log:result=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
 row=dict(name=name,command=cmd,returncode=result.returncode,seconds=round(time.monotonic()-start,3));receipts.append(row);print(json.dumps(row),flush=True);print((out/(name+'.txt')).read_text()[-1000:],flush=True)
(out/'container-browser-commands.json').write_text(json.dumps({'environment':{k:v for k,v in env.items() if k.startswith(('TEACHER_','ENRICHMENT_','CHROMIUM_','PLAYWRIGHT_')) or k in ('PYTHONPATH','PYTHONDONTWRITEBYTECODE','TMPDIR')},'runs':receipts},indent=2)+'\n')
