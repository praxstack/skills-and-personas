import json,os,subprocess,time
from pathlib import Path
r=Path('/Users/prax/Developer/skills-and-personas-recovery-20261016/.worktrees/teach-finish-20261024');os.chdir(r)
out=r/'docs/teach-resume-20261024/cleanup';out.mkdir(exist_ok=True,parents=True)
env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH='/Users/prax/.cache/uv/archive-v0/ZYsqvPvo6Drakewc',TMPDIR=str(Path.home()))
py='/Users/prax/.local/share/uv/tools/headroom-ai/bin/python'
commands=[('teacher',[py,'-W','error::ResourceWarning','skills/teacher/scripts/tests/test_teacher.py','-v']),('teacher-extra',[py,'-m','unittest','discover','-s','skills/teacher/scripts/tests','-p','test_*.py','-v']),('transcript',[py,'-m','unittest','discover','-s','skills/transcript-pipeline/scripts','-p','test_resource*.py','-v']),('safe-output',[py,'-m','unittest','discover','-s','skills/transcript-pipeline/scripts','-p','test_safe_output.py','-v']),('packaging-parity',[py,'-m','unittest','discover','-s','scripts','-p','test_portfolio_repair.py','-v']),('vendor',[py,'skills/teacher/scripts/vendor.py','verify']),('distribution',[py,'skills/teach-pro-max/scripts/verify_distribution.py']),('node',['node','--test','skills/teacher/skills/course/scripts/publish_videos.test.mjs','skills/teacher/skills/explorable/scripts/bundle_templates.test.mjs','skills/teacher/skills/explorable/scripts/report.test.mjs'])]
receipts=[]
for name,cmd in commands:
 start=time.monotonic()
 with (out/(name+'.txt')).open('w') as log: result=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
 row=dict(name=name,command=cmd,returncode=result.returncode,seconds=round(time.monotonic()-start,3));receipts.append(row)
 print(json.dumps(row),flush=True)
 print((out/(name+'.txt')).read_text()[-900:],flush=True)
(out/'host-commands.json').write_text(json.dumps({'environment':{k:env[k] for k in ('PYTHONDONTWRITEBYTECODE','PYTHONPATH','TMPDIR')},'runs':receipts},indent=2)+'\n')
