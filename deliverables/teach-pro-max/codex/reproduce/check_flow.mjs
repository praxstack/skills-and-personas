import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {writeFile,mkdir} from 'node:fs/promises';
import {loadPlaywright,launch} from '../../../../skills/teacher/skills/visual-qa/scripts/pw.mjs';
const base=resolve('deliverables/teach-pro-max/codex');
const {chromium}=await loadPlaywright();const browser=await launch(chromium);
const checks=[];function check(id,ok,detail=''){checks.push({id,ok,detail});}
try{
 for(const name of ['voice-and-focus','base-rates','diffusion']){
  const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
  const p=await context.newPage();let errors=[];p.on('pageerror',e=>errors.push(e.message));
  const url=pathToFileURL(resolve(base,'lessons',name,'explorer.html')).href;
  await p.goto(url);await p.waitForFunction(()=>window.__explorable);
  const n=await p.evaluate(()=>window.LESSON.steps.length);
  for(let i=0;i<n;i++){
   await p.evaluate(i=>window.__explorable.goStep(i),i);
   check(`${name}:default-next-${i}`,await p.locator('.xp-next').isEnabled());
   check(`${name}:complete-explanation-${i}`,await p.locator('.xp-say').isVisible());
  }
  check(`${name}:ephemeral-no-progress-write`,await p.evaluate(()=>Object.keys(localStorage).filter(k=>k.startsWith('explorable:')).length===0));
  await p.reload();await p.waitForFunction(()=>window.__explorable);
  check(`${name}:ephemeral-reload`,await p.evaluate(()=>window.__explorable.state.step===0));
  await p.getByRole('checkbox',{name:'Remember progress on this device'}).check();
  await p.evaluate(()=>window.__explorable.goStep(2));await p.reload();await p.waitForFunction(()=>window.__explorable);
  check(`${name}:consented-resume`,await p.evaluate(()=>window.__explorable.state.step===2));
  await p.getByRole('checkbox',{name:'Remember progress on this device'}).uncheck();
  check(`${name}:withdrawal-removes-local-progress`,await p.evaluate(()=>Object.keys(localStorage).filter(k=>k.startsWith('explorable:')).length===0));
  await p.goto(url+'?practice=1');await p.waitForFunction(()=>window.__explorable);
  check(`${name}:explicit-practice-lock`,await p.locator('.xp-next').isDisabled());
  check(`${name}:exit-practice-link`,await p.getByRole('link',{name:'Read the complete explanation instead'}).count()===1);
  await p.getByRole('link',{name:'Read the complete explanation instead'}).click();await p.waitForFunction(()=>window.__explorable);
  check(`${name}:exit-opens-next`,await p.locator('.xp-next').isEnabled());
  for(const width of [1440,390])for(const colorScheme of ['light','dark']){
   await p.setViewportSize({width,height:1000});await p.emulateMedia({colorScheme});
   check(`${name}:${width}:${colorScheme}:no-overflow`,await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  }
  check(`${name}:no-page-errors`,!errors.length,errors.join(';'));
  await context.close();
 }
 const context=await browser.newContext({viewport:{width:1440,height:1000}});const p=await context.newPage();
 await p.goto(pathToFileURL(resolve(base,'course/site/index.html')).href);await p.waitForFunction(()=>window.__course);
 const ids=await p.evaluate(()=>window.__course.lessons);check('course:two-connected-lessons',ids.length===2);
 await p.evaluate(id=>window.__course.setStatus(id,'done'),ids[0]);
 check('course:no-consent-no-write',await p.evaluate(()=>Object.keys(localStorage).filter(k=>k.startsWith('course:')).length===0));
 await p.reload();await p.waitForFunction(()=>window.__course);
 check('course:no-consent-no-restoration',await p.evaluate(()=>Object.keys(window.__course.state.status).length===0));
 await p.getByRole('checkbox',{name:'Remember progress on this device'}).check();
 await p.evaluate(id=>window.__course.setStatus(id,'done'),ids[0]);await p.reload();await p.waitForFunction(()=>window.__course);
 check('course:consented-resume',await p.evaluate(id=>window.__course.state.status[id]==='done',ids[0]));
 await p.getByRole('checkbox',{name:'Remember progress on this device'}).uncheck();
 check('course:withdrawal-removes-local-state',await p.evaluate(()=>Object.keys(localStorage).filter(k=>k.startsWith('course:')).length===0));
 await context.close();
}finally{await browser.close();}
const result={checks,passed:checks.filter(c=>c.ok).length,failed:checks.filter(c=>!c.ok).length,limitations:['Local browser state only; no assertion about external copies or human learning.']};
await mkdir(resolve(base,'evidence'),{recursive:true});await writeFile(resolve(base,'evidence/flow-checks.json'),JSON.stringify(result,null,2));
console.log(JSON.stringify({passed:result.passed,failed:result.failed,failures:checks.filter(c=>!c.ok)}));process.exitCode=result.failed?1:0;
