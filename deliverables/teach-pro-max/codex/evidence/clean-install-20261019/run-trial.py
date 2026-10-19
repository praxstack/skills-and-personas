#!/usr/bin/env python3
"""Exercise downloaded sources in an isolated prefix; never modify an active skill root."""
import argparse,hashlib,json,os,subprocess,time
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument("root",type=Path);ap.add_argument("--regression-only",action="store_true");a=ap.parse_args();r=a.root.resolve();src=r/"source/skills/teacher";out=r/"outputs";out.mkdir(exist_ok=True)
assert str(r).startswith("/private/tmp/prax-teach-clean-install-") and src.is_dir()
env=os.environ.copy();env.update({"PATH":str(r/"runtime/venv/bin")+":/opt/homebrew/bin:/usr/bin:/bin","PLAYWRIGHT_MODULE":str(r/"runtime/node/node_modules/playwright"),"PLAYWRIGHT_BROWSERS_PATH":str(r/"runtime/browsers"),"CHROMIUM_PATH":str(r/"runtime/browsers/chromium_headless_shell-1243/chrome-headless-shell-mac-arm64/chrome-headless-shell"),"KOKORO_DIR":str(r/"runtime/models/kokoro"),"NARRATE_CACHE":str(r/"runtime/fresh-voice-cache"),"HF_HUB_CACHE":str(r/"runtime/hfcache"),"HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1","PYTHONDONTWRITEBYTECODE":"1","TEACHER_TEST_OUT":str(out/"regression")})
results=[]
def run(name,argv,timeout=600):
    start=time.time(); log=r/(name+".log")
    with log.open("w") as f:
        p=subprocess.run([str(x) for x in argv],cwd=r,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
    row={"name":name,"argv":[str(x) for x in argv],"exit_code":p.returncode,"seconds":round(time.time()-start,3),"log":log.name};results.append(row);print(json.dumps(row),flush=True)
    (r/("regression-results.json" if a.regression_only else "trial-results.json")).write_text(json.dumps(results,indent=2)+"\n")
    if p.returncode:raise SystemExit(p.returncode)
    return log.read_text()
if a.regression_only:
    run("fresh-regression",["bash",src/"scripts/tests/run_all.sh"],900)
    raise SystemExit(0)
installer=src/"install.sh";prefix=r/"project/.agents/skills";copy=r/"copy-test/skills";foreign=r/"foreign-test/skills";dry=r/"dry-test/skills"
run("install-dry",["bash",installer,"--dir",dry,"--dry-run"]);assert not dry.exists()
run("install-link",["bash",installer,"--dir",prefix]);assert (prefix/"teacher").is_symlink() and (prefix/"teacher").resolve()==src
assert len(list(prefix.glob("*/SKILL.md")))==1
run("install-idempotent",["bash",installer,"--dir",prefix]);assert (prefix/"teacher").resolve()==src
run("install-copy",["bash",installer,"--dir",copy,"--copy"]);assert (copy/"teacher/.installed-by-teacher").exists() and not (copy/"teacher").is_symlink()
run("uninstall-copy",["bash",installer,"--dir",copy,"--uninstall"]);assert not (copy/"teacher").exists()
(foreign/"teacher").mkdir(parents=True);marker=foreign/"teacher/DO-NOT-REPLACE";marker.write_text("foreign content\n")
run("preserve-foreign",["bash",installer,"--dir",foreign]);assert marker.read_text()=="foreign content\n"
run("preserve-foreign-uninstall",["bash",installer,"--dir",foreign,"--uninstall"]);assert marker.read_text()=="foreign content\n"
run("uninstall-link",["bash",installer,"--dir",prefix,"--uninstall"]);assert not (prefix/"teacher").is_symlink()
run("install-for-build",["bash",installer,"--dir",prefix]);installed=prefix/"teacher"
run("vendor-verify",["python3",installed/"scripts/vendor.py","verify"])
for slug in ["voice-and-focus","base-rates","diffusion"]:
    target=out/slug;target.mkdir(exist_ok=True)
    run("build-"+slug,["python3",installed/"skills/explorable/scripts/build.py",r/"review/lessons"/slug/"source/lesson.lesson.js","-o",target/"explorer.html"])
voice=out/"voice-and-focus"
assert not (r/"runtime/fresh-voice-cache").exists(),"Fresh narration cache must start empty"
run("fresh-narration",["python3",installed/"skills/explorable/scripts/narrate.py",voice/"explorer.html","-o",voice/"lesson.mp4","--engine","kokoro","--speed","0.85","--fps","24"],1200)
run("six-format-export",["node",installed/"skills/explorable/scripts/bundle_lesson.mjs",voice/"explorer.html","--out",voice/"bundle","--video",voice/"lesson.mp4","--timing",voice/"lesson.timing.json"])
run("fresh-ive-qa",["node",installed/"skills/visual-qa/scripts/check_page.mjs",voice/"bundle/interactive-video.html","--out",out/"ive-qa"])
print("FRESH INSTALL/BUILD COMMANDS COMPLETE; inspect browser artifacts separately",flush=True)
