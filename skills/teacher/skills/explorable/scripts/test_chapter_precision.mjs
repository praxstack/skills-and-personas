/** Actual-media chapter selection on fractional boundaries; synthetic metadata. */
import assert from 'node:assert/strict';
import {mkdtemp,readFile,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {videoLesson} from './bundle_templates.mjs';
import {loadPlaywright,launch} from '../../visual-qa/scripts/pw.mjs';
const source=process.argv[2];if(!source)throw Error('Supply explicit existing MP4');
const root=await mkdtemp(join(tmpdir(),'chapter-precision-'));let browser;
const scenes=[{start:0,chapter:'First',say:'First',step:0,params:{value:11}},{start:1.23456789,chapter:'Second',say:'Second',step:1,params:{value:22}},{start:4.3456789123,chapter:'Third',say:'Third',step:2,params:{value:33}}];
try{
 await writeFile(join(root,'interactive-video.html'),videoLesson({title:'Chapter precision',subject:'Synthetic control',lang:'en',sources:[],video:{captions:'WEBVTT\n\n00:00:00.000 --> 00:00:07.000\nControl\n',scenes}}));
 await writeFile(join(root,'explorer.html'),'<!doctype html><title>Transfer receiver</title><script>window.messages=[];addEventListener("message",e=>window.messages.push(e.data))</script>');
 await writeFile(join(root,'lesson.mp4'),await readFile(source));
 const {chromium}=await loadPlaywright();browser=await launch(chromium);const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(pathToFileURL(join(root,'interactive-video.html')).href);
 await page.waitForFunction(()=>window.__interactiveVideo?.video.readyState>=1&&document.getElementById('explorer-loading').hidden);
 await page.evaluate(()=>{const v=window.__interactiveVideo.video;window.settled=[];v.addEventListener('seeked',()=>{v.pause();window.settled.push({time:v.currentTime,index:window.__interactiveVideo.current()})})});
 async function seek(time,index){
  await page.evaluate(t=>{const v=window.__interactiveVideo.video;v.pause();v.currentTime=t},time);
  await page.waitForFunction(()=>!window.__interactiveVideo.video.seeking&&window.__interactiveVideo.video.readyState>=2);
  const result=await page.evaluate(()=>({time:window.__interactiveVideo.video.currentTime,index:window.__interactiveVideo.current()}));assert.equal(result.index,index,JSON.stringify({requested:time,...result}));return result;
 }
 const observations=[];
 for(const [time,index] of [[1.234566,0],[scenes[1].start,1],[1.234569,1],[4.345677,1],[scenes[2].start,2],[4.34568,2],[scenes[1].start,1],[0.5,0]])observations.push(await seek(time,index));
 await seek(scenes[2].start,2);await page.locator('#explore').click();
 const frame=page.frames().find(f=>f.url().includes('explorer.html'));
 await frame.waitForFunction(()=>window.messages.length>0);assert.deepEqual(await frame.evaluate(()=>window.messages.at(-1)),{type:'teach:set-params',step:2,params:{value:33}});
 await page.locator('#replay').click();await page.waitForFunction(()=>window.settled.length>=10&&!window.__interactiveVideo.video.seeking);
 assert.equal(await page.evaluate(()=>window.__interactiveVideo.current()),2);
 await page.locator('.chapters [data-scene="1"]').click();await page.waitForFunction(()=>!window.__interactiveVideo.video.seeking&&window.__interactiveVideo.current()===1);
 await page.locator('#explore').click();await frame.waitForFunction(()=>window.messages.at(-1)?.step===1);
 assert.deepEqual(await frame.evaluate(()=>window.messages.at(-1)),{type:'teach:set-params',step:1,params:{value:22}});
 assert.deepEqual(await page.evaluate(()=>window.__interactiveVideo.scenes),scenes);assert.deepEqual(errors,[]);
 console.log(JSON.stringify({ok:true,browser:browser.version(),observations,checks:['fractional-boundaries','previous-microsecond','next-microsecond','backward-seek','replay','chapter-button','explorer-handoff','unchanged-metadata','no-page-errors']}));
}finally{if(browser)await browser.close();await rm(root,{recursive:true,force:true})}
