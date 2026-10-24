// Supplemental PR1 product regressions. No governing gate or historical fixture edits.
import {mkdtemp,writeFile,readFile,copyFile,symlink} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createServer} from 'node:http';
import {loadPlaywright,launch} from '../../skills/teacher/skills/visual-qa/scripts/pw.mjs';
import {videoLesson} from '../../skills/teacher/skills/explorable/scripts/bundle_templates.mjs';
const root=process.cwd(), work=await mkdtemp(join(tmpdir(),'teach-pr1-')), checks=[];
const check=(name,ok,actual)=>checks.push({name,ok:!!ok,actual});
const exp=join(root,'skills/teacher/skills/explorable');
let source=await readFile(join(exp,'assets/examples/seasons.lesson.js'),'utf8');
const code={title:'Languages',cpp:'int x = 1;',python:'x = 1',js:'JS_SENTINEL <b>bad()</b>',java:'JAVA_SENTINEL',go:'GO_SENTINEL',rust:'RUST_SENTINEL',javascript:'ALIAS_SENTINEL'};
source+='\nwindow.LESSON.code='+JSON.stringify(code)+';\nwindow.LESSON.steps[0].say="<p>If x &lt; 0 &amp;&amp; y &gt; 2</p><p>π &#8804; &#x221e; &quot;yes&quot; &nbsp; ✓</p>";\n';
await writeFile(join(work,'fixture.js'),source);
execFileSync('python3',[join(exp,'scripts/build.py'),join(work,'fixture.js'),'-o',join(work,'explorer.html')]);
const {chromium}=await loadPlaywright();const browser=await launch(chromium);let server;
try {
 const ctx=await browser.newContext({reducedMotion:'reduce'});const p=await ctx.newPage();const net=[];await ctx.route(/^https?:/,r=>{net.push(r.request().url());return r.abort()});
 const open=async suffix=>{await p.goto(pathToFileURL(join(work,'explorer.html')).href+suffix);await p.waitForFunction(()=>window.__explorable)};
 await open('');check('default full explanation visible',await p.locator('.xp-say').isVisible());
 await open('?practice=1');check('practice explanation initially hidden',!await p.locator('.xp-say').isVisible());
 await p.getByRole('button',{name:'Show me',exact:true}).click();check('Show me reveals explanation',await p.locator('.xp-say').isVisible());
 await open('?practice=1');const ans=await p.evaluate(()=>{let a=window.LESSON.steps[0].ask;return typeof a.answer==='function'?a.answer(window.__explorable.state.params,window.LESSON.model(window.__explorable.state.params)):a.answer});await p.locator(`.xp-option[data-k="${ans}"]`).click();await p.getByRole('button',{name:'Check',exact:true}).click();check('correct practice answer reveals explanation',await p.locator('.xp-say').isVisible());
 await open('?film-export');await p.waitForFunction(()=>window.__filmExport);const say=await p.evaluate(()=>window.__filmExport.scenes[0].say);check('narration decodes operators unicode and paragraph spacing',say==='If x < 0 && y > 2. π ≤ ∞ "yes" ✓',say);const engine=await readFile(join(exp,'assets/engine/explorable.js'),'utf8');const fn=engine.match(/function plainText\(html\) \{[\s\S]*?\n\}/)[0];const inert=await p.evaluate(fn=>{window.BAD=0;const plain=eval('('+fn+')');return {text:plain('<p>&lt;img src=x&gt;</p><img src=https://invalid.example/probe onerror=window.BAD=1>'),bad:window.BAD}},fn);check('HTML decoding treats markup as inert text',inert.text==='<img src=x>'&&!inert.bad,inert);await p.waitForTimeout(100);check('HTML-to-text does not fetch resources',!net.some(u=>u.includes('invalid.example')),net);
 await ctx.close();
 execFileSync('node',[join(exp,'scripts/bundle_lesson.mjs'),join(work,'explorer.html'),'--out',join(work,'bundle')]);
 const data=JSON.parse(await readFile(join(work,'bundle/lesson-data.json'),'utf8'));for(const lang of Object.keys(code).filter(k=>k!=='title'))check(`export preserves ${lang}`,data.code[lang]===code[lang],data.code[lang]);
 const staticHTML=await readFile(join(work,'bundle/static.html'),'utf8');for(const marker of ['JS_SENTINEL','JAVA_SENTINEL','GO_SENTINEL','RUST_SENTINEL','ALIAS_SENTINEL'])check(`static renders ${marker}`,staticHTML.includes(marker));check('static code escapes markup',staticHTML.includes('JS_SENTINEL &lt;b&gt;bad()&lt;/b&gt;'));
 const fallbackCtx=await browser.newContext({javaScriptEnabled:false});const fallbackPage=await fallbackCtx.newPage();for(const filename of ['static.html','explorer.html']){await fallbackPage.goto(pathToFileURL(join(work,'bundle',filename)).href);for(const marker of ['JS_SENTINEL','JAVA_SENTINEL','GO_SENTINEL','RUST_SENTINEL'])check(`${filename} JS-off code ${marker}`,await fallbackPage.locator('pre code').filter({hasText:marker}).isVisible())}await fallbackCtx.close();
 // Use retained genuine video bytes only as a browser transport control; no new media claim.
 await symlink(join(root,'deliverables/teach-resume-20261024/demo-eaa524e/bundle/lesson.mp4'),join(work,'lesson.mp4'));
 const captions='WEBVTT\n\n00:00:00.000 --> 00:00:03.000\nNative caption π < 2\n';
 const vdata={...data,video:{total:3,captions,scenes:[{start:0,dur:3,chapter:'Native',say:'Native caption',step:0,params:{}}]}};
 await writeFile(join(work,'interactive-video.html'),videoLesson(vdata));await writeFile(join(work,'lesson.vtt'),captions);
 server=createServer(async(req,res)=>{try{const url=new URL(req.url,'http://127.0.0.1');const file=resolve(work,'.'+url.pathname);if(!file.startsWith(work+'/'))throw Error('path');const buf=await readFile(file);res.setHeader('Content-Type',file.endsWith('.mp4')?'video/mp4':file.endsWith('.vtt')?'text/vtt':'text/html');res.end(buf)}catch{res.statusCode=404;res.end()}});await new Promise(r=>server.listen(0,'127.0.0.1',r));
 for(const js of [false,true])for(const protocol of ['file','http']){
  const c=await browser.newContext({javaScriptEnabled:js});await c.route(/^https?:/,r=>r.request().url().startsWith(`http://127.0.0.1:${server.address().port}/`)?r.continue():r.abort());const q=await c.newPage();const errors=[];q.on('pageerror',e=>errors.push(e.message));const url=protocol==='file'?pathToFileURL(join(work,'interactive-video.html')).href:`http://127.0.0.1:${server.address().port}/interactive-video.html`;await q.goto(url);await q.evaluate(()=>{let v=document.querySelector('video');v.textTracks[0].mode='showing';v.load()});
  let actual;try{await q.waitForFunction(()=>document.querySelector('video').textTracks[0].cues?.length>0,{timeout:4000},{timeout:4000});actual=await q.evaluate(()=>({source:document.querySelector('track').getAttribute('src').split(':')[0],cues:[...document.querySelector('video').textTracks[0].cues].map(c=>c.text),ready:document.querySelector('track').readyState}));check(`native captions JS${js} ${protocol}`,actual.cues.length===1,actual)}catch(e){check(`native captions JS${js} ${protocol}`,false,String(e.message).slice(0,160))}await q.evaluate(async()=>{const v=document.querySelector('video');v.muted=true;await v.play()});await q.waitForTimeout(300);const time=await q.evaluate(()=>{const v=document.querySelector('video');v.pause();return v.currentTime});check(`native video advances JS${js} ${protocol}`,time>0,time);check(`no runtime errors JS${js} ${protocol}`,errors.length===0,errors);await c.close();
 }
 console.log(JSON.stringify({work,browser:browser.version(),checks},null,2));process.exitCode=checks.every(c=>c.ok)?0:1;
}finally{if(server)await new Promise(r=>server.close(r));await browser.close()}
