/** Focused real-browser readable-panel control; not narrated acceptance. */
import assert from 'node:assert/strict';
import {mkdtemp,readFile,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {videoLesson} from './bundle_templates.mjs';
import {loadPlaywright,launch} from '../../visual-qa/scripts/pw.mjs';

const source=process.argv[2];if(!source)throw Error('Supply the reviewed real MP4 for the ordinary caption control');
const root=await mkdtemp(join(tmpdir(),'teach-caption-tail-'));
let browser;
try{
 const captions='WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nOpening explanation\n\n00:00:04.000 --> 00:00:05.000\nClosing explanation\n';
 const data={title:'Caption control',subject:'Playback',lang:'en',sources:[],video:{captions,scenes:[{start:0,chapter:'Opening',say:'Opening explanation'},{start:3,chapter:'Closing',say:'Closing explanation'}]}};
 await writeFile(join(root,'interactive-video.html'),videoLesson(data));
 await writeFile(join(root,'explorer.html'),'<!doctype html><title>Ordinary caption fixture</title>');
 await writeFile(join(root,'lesson.mp4'),await readFile(source));
 const {chromium}=await loadPlaywright();browser=await launch(chromium);
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(pathToFileURL(join(root,'interactive-video.html')).href);
 await page.waitForFunction(()=>document.querySelector('track').track.cues?.length===2&&document.querySelector('video').readyState>=1);
 const native=()=>page.evaluate(()=>Array.from(document.querySelector('track').track.cues,c=>({start:c.startTime,end:c.endTime,text:c.text})));
 await page.evaluate(()=>{window.captionSeeks=[];document.querySelector('video').addEventListener('seeking',()=>window.captionSeeks.push({text:document.getElementById('readable-captions').textContent,seeking:document.querySelector('video').seeking}))});
 const before=await native();assert.deepEqual(before,[{start:1,end:2,text:'Opening explanation'},{start:4,end:5,text:'Closing explanation'}]);
 async function at(time,text){
  await page.locator('video').evaluate((v,t)=>{v.pause();v.currentTime=t},time);
  await page.waitForFunction(([t,want])=>!document.querySelector('video').seeking&&document.querySelector('video').readyState>=2&&Math.abs(document.querySelector('video').currentTime-t)<0.05&&document.getElementById('readable-captions').textContent===want,[time,text]);
 }
 await at(0.5,'');await at(1.5,'Opening explanation');await at(2.5,'');await at(4.5,'Closing explanation');await at(6,'Closing explanation');
 assert.equal(await page.evaluate(()=>document.querySelector('track').track.activeCues.length),0,'native captions end on time');
 await page.locator('#captions').click();assert.equal(await page.locator('#readable-captions').isHidden(),true);
 await at(0.5,'');await page.locator('#captions').click();assert.equal(await page.locator('#readable-captions').textContent(),'');
 await at(6,'Closing explanation');await page.locator('#replay').click();
 await page.waitForFunction(()=>document.querySelector('video').currentTime>=3&&document.querySelector('video').currentTime<4&&document.getElementById('readable-captions').textContent==='');
 await at(4.5,'Closing explanation');await page.locator('#captions').click();await at(6,'Closing explanation');assert.equal(await page.locator('#readable-captions').isHidden(),true);
 await page.locator('#captions').click();assert.equal(await page.locator('#readable-captions').textContent(),'Closing explanation');
 const seeking=await page.evaluate(()=>window.captionSeeks);assert.ok(seeking.length>=8);assert.ok(seeking.every(s=>s.seeking&&s.text===''),'panel clears while actual media seeks');assert.ok(await page.locator('video').evaluate(v=>!v.seeking&&v.readyState>=2));
 assert.deepEqual(await native(),before);assert.deepEqual(errors,[]);
 console.log(JSON.stringify({ok:true,browser:browser.version(),loadedNativeCues:before,checks:['prefirst','active','interior-gap','final-cue','terminal-still','native-end','seek-back','replay-clear','toggle-retention','native-timing-unchanged','seeking-clear','seeked-data-ready','no-page-errors']}));
}finally{if(browser)await browser.close();await rm(root,{recursive:true,force:true})}
