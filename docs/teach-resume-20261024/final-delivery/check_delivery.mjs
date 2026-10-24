import assert from 'node:assert/strict';
import {mkdir} from 'node:fs/promises';
import {resolve,join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {loadPlaywright,launch} from '../../../skills/teacher/skills/visual-qa/scripts/pw.mjs';
const demo=resolve(process.argv[2]),shots=resolve(process.argv[3]);await mkdir(shots,{recursive:true});
const {chromium}=await loadPlaywright();const browser=await launch(chromium);const results=[];
try{
 for(const [name,width,height] of [['desktop',1280,900],['mobile',390,844]]){
  for(const file of ['static.html','interactive-video.html']){
   const page=await browser.newPage({viewport:{width,height},reducedMotion:'reduce'});const errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.goto(pathToFileURL(join(demo,'bundle',file)).href);
   assert.ok(await page.locator('h1').count());
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
   if(file==='interactive-video.html'){
    await page.waitForFunction(()=>window.__interactiveVideo?.video.readyState>=1);
    await page.locator('#speed').selectOption('1.25');assert.equal(await page.locator('video').evaluate(v=>v.playbackRate),1.25);
    await page.locator('#captions').click();assert.equal(await page.locator('#readable-captions').isHidden(),true);
    await page.locator('#captions').click();assert.equal(await page.locator('#readable-captions').isVisible(),true);
    await page.locator('.chapters [data-scene="1"]').click();
    await page.waitForFunction(()=>!window.__interactiveVideo.video.seeking&&window.__interactiveVideo.current()===1);
    await page.locator('#explore').click();
    await page.waitForFunction(()=>document.getElementById('video-status').textContent.startsWith('Exploring:'));
    await page.evaluate(()=>scrollTo(0,0));
   }
   assert.deepEqual(errors,[]);await page.screenshot({path:join(shots,`${name}-${file}.png`),fullPage:false});
   results.push({view:name,file,ok:true});await page.close();
  }
 }
 console.log(JSON.stringify({browser:browser.version(),results},null,2));
}finally{await browser.close()}
