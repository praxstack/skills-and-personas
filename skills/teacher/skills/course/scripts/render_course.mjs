/** Fixed sampled render and inspection inside the existing offline sandbox. */
import {pathToFileURL} from 'node:url';
import {mkdir,writeFile,access,readFile,readdir} from 'node:fs/promises';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
import {loadPlaywright,launch} from '../../visual-qa/scripts/pw.mjs';
if(!process.argv.includes('--trust-authored-code'))throw new Error('Use sandbox_course.py render; authored execution requires --trust-authored-code');
process.env.DEBUG='pw:browser';
const [file,out]=process.argv.slice(2),{chromium}=await loadPlaywright();
const runtime=[];
async function measure(phase){
 const processes=[];
 for(const pid of (await readdir('/proc')).filter(p=>/^\d+$/.test(p))){
  try{const text=await readFile('/proc/'+pid+'/status','utf8'),field=name=>text.match(new RegExp('^'+name+':\\s*(.+)$','m'))?.[1];
   const args=(await readFile('/proc/'+pid+'/cmdline','utf8')).split('\0');
   processes.push({pid:Number(pid),name:field('Name'),state:field('State'),ppid:Number(field('PPid')),threads:Number(field('Threads')),cpuAllowed:field('Cpus_allowed_list'),role:[...args.join(' ').matchAll(/--(?:type|utility-sub-type)=([^\s\0]+)/g)].map(m=>m[0])});
  }catch(e){if(e.code!=='ENOENT'&&e.code!=='ESRCH')throw e;}
 }
 const sample={phase,pids:Number(await readFile('/sys/fs/cgroup/pids.current','utf8')),events:(await readFile('/sys/fs/cgroup/pids.events','utf8')).trim(),processes};
 runtime.push(sample);console.error('RUNTIME '+JSON.stringify(sample));
 return sample;
}
await measure('before-render-browser');
let browser=await launch(chromium);
await measure('after-render-browser-launch');
let ctx=await browser.newContext({viewport:{width:1280,height:720},reducedMotion:'reduce'});
let page=await ctx.newPage();const errors=[],network=[];
async function observe(target){target.on('pageerror',e=>errors.push(e.message));await target.route(/^https?:/,r=>{network.push(r.request().url());return r.abort()});}
await observe(page);
await page.goto(pathToFileURL(file).href);await page.waitForFunction(()=>window.__explorable);
const checks=await page.evaluate(()=>{
 const L=window.LESSON,tests=[];const ok=(name,v)=>tests.push({name,ok:!!v});
 let cases=0,equivalent=true,phaseInvariant=true;
 for(let base=1;base<=50;base++)for(let hit=50;hit<=100;hit++)for(let falseRate=0;falseRate<=20;falseRate++){
  const p={base,hit,falseRate},a=L.model(p),total=10000,defective=total*base/100,sound=total-defective,trueFlags=defective*hit/100,falseFlags=sound*falseRate/100,flagged=trueFlags+falseFlags;
  const b={total,defective,sound,trueFlags,falseFlags,flagged,missed:defective-trueFlags,precision:flagged?trueFlags/flagged:null};
  equivalent&&=JSON.stringify(a)===JSON.stringify(b);
  phaseInvariant&&=JSON.stringify(a)===JSON.stringify(L.model({...p,phase:3.5}));cases++;
 }
 ok(`${cases} original-grid model equivalence`,equivalent);ok('phase is presentation only',phaseInvariant);
 for(const [base,want] of [[1,2/13],[20,9/11],[50,18/19]])ok(`posterior at ${base}%`,Math.abs(L.model({base,hit:90,falseRate:5}).precision-want)<1e-12);
 const z=L.model({base:10,hit:90,falseRate:0});ok('zero false flags retains 100 missed',z.precision===1&&z.missed===100);
 ok('no storage before consent',localStorage.length===0&&sessionStorage.length===0);
 return tests;
});
await measure('after-lesson-model-checks');
// Actual keyboard operation on the first named range; then default Next without answers.
const range=page.locator('input[type=range]').first();await range.focus();const before=await range.inputValue();await page.keyboard.press('ArrowRight');checks.push({name:'keyboard slider changes value',ok:(await range.inputValue())!==before});
const navigation=[];
for(let i=0;i<7;i++){
 navigation.push(await page.evaluate(()=>window.__explorable.state.step));
 if(i<6)await page.getByRole('button',{name:/^Next/}).click();
}
checks.push({name:'all explanation steps reachable without answers',ok:JSON.stringify(navigation)==='[0,1,2,3,4,5,6]'});
await page.goto(pathToFileURL(file).href+'?film-export');await page.waitForFunction(()=>window.__filmExport);await page.evaluate(()=>document.fonts.ready);
const meta=await page.evaluate(()=>({scenes:window.__filmExport.scenes,states:window.__filmExport.sceneStates}));
if(meta.scenes.length!==7)throw new Error(`Expected seven concise scenes; got ${meta.scenes.length}`);
await mkdir(join(out,'frames'),{recursive:true});const receipts=[];
for(let i=0;i<7;i++)for(let j=0;j<=8;j++){
 const settled=j/8,info=await page.evaluate(([i,t])=>window.__filmExport.frame(i,0,t===1?1:0,t),[i,settled]);
 const geometry=await page.evaluate(()=>[...document.querySelectorAll('svg rect[id]')].map(n=>({id:n.id,x:n.getAttribute('x'),y:n.getAttribute('y'),width:n.getAttribute('width')})));
 const filename=`scene-${i}-${j}.png`;await page.screenshot({path:join(out,'frames',filename)});
 receipts.push({scene:i,settled,filename,...info,geometry});
}
checks.push({name:'first three settled geometries distinct',ok:new Set([0,1,2].map(i=>JSON.stringify(receipts.find(r=>r.scene===i&&r.settled===1).geometry))).size===3});
checks.push({name:'captions hidden throughout unsettled transitions',ok:receipts.filter(r=>r.settled<1).every(r=>!r.captionVisible)});
await measure('after-film-frames');
// Exercise exported formats inside the same offline browser boundary.
for(const format of ['qa','cards']){
 await page.goto(pathToFileURL(join(out,'bundle',format+'.html')).href);
 const summary=page.locator('summary').first();await summary.focus();await page.keyboard.press('Enter');
 checks.push({name:format+' keyboard disclosure opens',ok:await page.locator('details').first().evaluate(e=>e.open)});
}
let hasVideo=false;try{await access(join(out,'bundle','interactive-video.html'));hasVideo=true}catch{}
await measure('after-static-formats');
if(hasVideo){
 await ctx.close();await browser.close();await measure('after-static-browser-close');
 browser=await launch(chromium);ctx=await browser.newContext({viewport:{width:1280,height:720},reducedMotion:'reduce'});page=await ctx.newPage();await observe(page);
 await measure('before-video-navigation');
 await page.goto(pathToFileURL(join(out,'bundle','interactive-video.html')).href,{waitUntil:'domcontentloaded'});
 await measure('after-video-navigation');
 checks.push({name:'VP9 MP4 codec advertised',ok:await page.evaluate(()=>!!document.createElement('video').canPlayType('video/mp4; codecs="vp09.00.10.08"'))});
 await measure('before-play');
 await page.locator('#play').click();
 try{await page.waitForFunction(()=>window.__interactiveVideo?.video.readyState>=1,{},{timeout:5000})}catch(e){console.error('Video diagnostic',await page.evaluate(()=>({error:document.querySelector('video')?.error?.message,ready:document.querySelector('video')?.readyState,network:document.querySelector('video')?.networkState,codec:document.createElement('video').canPlayType('video/mp4; codecs="vp09.00.10.08"'),status:document.querySelector('#video-status')?.textContent,api:!!window.__interactiveVideo,source:document.querySelector('video')?.currentSrc})));throw e}
 try{await page.waitForFunction(()=>window.__interactiveVideo.video.currentTime>0.1&&!window.__interactiveVideo.video.paused,{},{timeout:5000})}catch(e){await measure('playback-failure');console.error('Playback diagnostic',await page.evaluate(()=>({state:window.__interactiveVideo.video.readyState,paused:window.__interactiveVideo.video.paused,time:window.__interactiveVideo.video.currentTime,error:window.__interactiveVideo.video.error?.message,status:document.getElementById('video-status').textContent})), 'pids',await readFile('/sys/fs/cgroup/pids.current','utf8'));throw e}
 await measure('after-playback-advance');
 checks.push({name:'actual video playback advances',ok:true});
 await page.waitForFunction(()=>document.getElementById('explorer-loading').hidden);
 await page.locator('.chapters button').nth(5).click();
 await page.locator('#explore').click();
 const iframe=page.frameLocator('#live-explorer');
 await iframe.locator('.xp-figure').waitFor();
 await page.waitForTimeout(200);
 checks.push({name:'interactive video chapter and paused model transfer',ok:await page.evaluate(()=>window.__interactiveVideo.video.paused&&window.__interactiveVideo.current()===5)});
 const params=await page.frames().find(f=>f.url().includes('explorer.html')).evaluate(()=>window.__explorable.state.params);
 checks.push({name:'explorer receives scene parameters',ok:params.base===10&&params.hit===90&&params.falseRate===5&&params.phase===5});
 await iframe.locator('.xp-figure').scrollIntoViewIfNeeded();
 await iframe.locator('.xp-figure').screenshot({path:join(out,'interactive-explorer-visible.png')});
 await page.screenshot({path:join(out,'interactive-explorer-viewport.png')});
 await measure('after-visible-explorer');
 await page.locator('#speed').selectOption('1.5');
 checks.push({name:'video speed control',ok:await page.locator('video').evaluate(v=>v.playbackRate===1.5)});
 await page.locator('#captions').click();
 checks.push({name:'caption toggle',ok:await page.locator('#readable-captions').evaluate(e=>e.hidden)});
 await page.locator('#captions').click();
 await page.evaluate(()=>{const v=window.__interactiveVideo.video;v.currentTime=v.duration-0.5});
 await page.waitForFunction(()=>document.getElementById('readable-captions').textContent.includes('100 defective'),{},{timeout:5000});
 checks.push({name:'seek near end reaches final chapter and captions',ok:await page.evaluate(()=>window.__interactiveVideo.current()===6&&window.__interactiveVideo.video.readyState>=2)});
 await page.screenshot({path:join(out,'interactive-video.png'),fullPage:true});
}
await measure('after-all-browser-checks');
checks.push({name:'no unexpected network requests',ok:network.length===0});checks.push({name:'no browser errors',ok:errors.length===0});
await writeFile(join(out,'render-evidence.json'),JSON.stringify({checks,meta,receipts,errors,network,runtime,mediaBrowserLifetime:'fresh browser after static capture'},null,2));
await browser.close();await measure('after-browser-close');await writeFile(join(out,'runtime-evidence.json'),JSON.stringify(runtime,null,2));if(checks.some(c=>!c.ok))throw new Error(JSON.stringify(checks.filter(c=>!c.ok)));
