import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {writeFile} from 'node:fs/promises';
import {loadPlaywright,launch} from '../../../../skills/teacher/skills/visual-qa/scripts/pw.mjs';
const {chromium}=await loadPlaywright(),browser=await launch(chromium),checks=[];
const base=resolve('deliverables/teach-pro-max/codex');
function check(id,ok,detail=''){checks.push({id,ok,detail});}
try{
 for(const slug of ['voice-and-focus','base-rates','diffusion']){
  const context=await browser.newContext();let errors=[];const p=await context.newPage();p.on('pageerror',e=>errors.push(e.message));
  for(const width of [1440,390])for(const scheme of ['light','dark']){
   await p.setViewportSize({width,height:1000});await p.emulateMedia({colorScheme:scheme});
   for(const name of ['still','explorer','qa','cards','interactive-video','static']){
    await p.goto(pathToFileURL(resolve(base,'lessons',slug,'bundle',name+'.html')).href);await p.evaluate(()=>document.fonts.ready);
    check(`${slug}:${name}:${width}:${scheme}:no-overflow`,await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    check(`${slug}:${name}:${width}:${scheme}:has-explanation`,(await p.locator('body').innerText()).length>200);
   }
  }
  await p.goto(pathToFileURL(resolve(base,'lessons',slug,'bundle','interactive-video.html')).href);
  const video=p.locator('video');await video.evaluate(async v=>{await v.play();v.pause();await new Promise((resolve,reject)=>{const t=setTimeout(()=>reject(new Error('Video seek timed out')),10000);v.addEventListener('seeked',()=>{clearTimeout(t);resolve()},{once:true});v.currentTime=1})});
  check(`${slug}:real-file-video-playable`,await video.evaluate(v=>v.readyState>=2&&v.videoWidth===1280&&v.duration>30));
  check(`${slug}:video-has-caption-track`,await video.locator('track[kind="captions"]').count()===1);
  await video.evaluate(async v=>{await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(new Error('Caption seek timed out')),10000);v.addEventListener('seeked',()=>{clearTimeout(timer);resolve()},{once:true});v.currentTime=2})});
  await p.waitForFunction(()=>document.getElementById('readable-captions').textContent.trim().length>0);
  const captions=p.locator('#readable-captions');
  check(`${slug}:captions-readable-below-video`,await p.evaluate(()=>{const v=document.querySelector('video').getBoundingClientRect(),c=document.getElementById('readable-captions').getBoundingClientRect();return c.top>=v.bottom&&parseFloat(getComputedStyle(document.getElementById('readable-captions')).fontSize)>=16}));
  check(`${slug}:native-overlay-off-by-default`,await video.evaluate(v=>[...v.textTracks].every(t=>t.mode==='hidden')));
  await p.locator('#captions').click();check(`${slug}:caption-hide-works`,await captions.isHidden());
  await p.locator('#captions').click();check(`${slug}:caption-show-works`,await captions.isVisible()&&(await captions.innerText()).trim().length>0);

  check(`${slug}:no-page-errors`,errors.length===0,errors.join(';'));
  await context.close();
  const nojs=await browser.newContext({javaScriptEnabled:false});const q=await nojs.newPage();
  for(const name of ['explorer','static']){
   await q.goto(pathToFileURL(resolve(base,'lessons',slug,'bundle',name+'.html')).href);
   check(`${slug}:${name}:no-js-complete`,await q.locator('h2').count()>=4 && (await q.locator('body').innerText()).length>1200);
  }
  await nojs.close();
 }
 const p=await browser.newPage();await p.goto(pathToFileURL(resolve(base,'index.html')).href);
 for(const width of [1440,390]){await p.setViewportSize({width,height:1000});check(`portal:${width}:no-overflow`,await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));}
 await p.setViewportSize({width:1440,height:1000});await p.screenshot({path:resolve(base,'evidence','review-portal.png'),fullPage:true});
}finally{await browser.close();}
const result={passed:checks.filter(c=>c.ok).length,failed:checks.filter(c=>!c.ok).length,checks,limitations:['Checks content presence, responsive overflow, media playback and static availability. Does not certify factual correctness, aesthetics or human voice quality.']};
await writeFile(resolve(base,'evidence','export-checks.json'),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({passed:result.passed,failed:result.failed,failures:checks.filter(c=>!c.ok)}));process.exitCode=result.failed?1:0;
