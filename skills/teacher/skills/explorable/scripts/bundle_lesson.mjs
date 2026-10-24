#!/usr/bin/env node
/** Export an already-built executable lesson into portable, explanation-first formats. */
import {pathToFileURL} from 'node:url';
import {resolve,join,dirname,basename,extname} from 'node:path';
import {readFile,writeFile,mkdir,copyFile,stat} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {loadPlaywright,launch} from '../../visual-qa/scripts/pw.mjs';
import {createPoster} from './bundle_poster.mjs';
import {esc,css,page as htmlPage,sources,readouts,answer,figure,staticLesson,qaLesson,cardsLesson,videoLesson} from './bundle_templates.mjs';

const args=process.argv.slice(2);
const option=(key,fallback)=>{const i=args.indexOf(key);if(i<0)return fallback;if(!args[i+1]||args[i+1].startsWith('--'))throw new Error(`${key} requires a value`);return args[i+1]};
const usage='Usage: node bundle_lesson.mjs explorer.html --out DIR [--video lesson.mp4 --timing lesson.timing.json] [--still-step 1]';
let browser;
try{
 const input=args[0];if(!input||input.startsWith('--')||!args.includes('--out'))throw new Error(usage);
 const inputPath=resolve(input),out=resolve(option('--out'));
 if(resolve(out,'explorer.html')===inputPath)throw new Error('Use a separate output directory; the input explorer must remain intact.');
 const videoPath=option('--video'),timingPath=option('--timing');if(Boolean(videoPath)!==Boolean(timingPath))throw new Error('--video and --timing must be supplied together.');
 const inputHTML=await readFile(inputPath,'utf8');
 const {chromium}=await loadPlaywright();browser=await launch(chromium);
 const context=await browser.newContext({viewport:{width:1440,height:1000},deviceScaleFactor:1,colorScheme:'light',reducedMotion:'reduce'});
 const screen=await context.newPage();const errors=[];screen.on('pageerror',e=>errors.push(e.message));
 // Export is offline. Bundled fonts/data URIs and local files remain available.
 await screen.route(/^https?:\/\//,route=>route.abort());
 await screen.goto(pathToFileURL(inputPath).href);await screen.waitForFunction(()=>window.LESSON&&window.__explorable);await screen.evaluate(()=>document.fonts.ready);
 const data=await screen.evaluate(()=>{
  const L=window.LESSON;
  const clean=(input)=>{const t=document.createElement('template');t.innerHTML=String(input??'');for(const bad of t.content.querySelectorAll('script,style,iframe,object,embed,form,input,button,textarea'))bad.remove();for(const n of t.content.querySelectorAll('*'))for(const a of [...n.attributes])if(a.name.startsWith('on')||['srcdoc','style'].includes(a.name)||(['href','src'].includes(a.name)&&/^\s*(javascript|data:text\/html):/i.test(a.value)))n.removeAttribute(a.name);return t.innerHTML};
  const plain=input=>{const t=document.createElement('template');t.innerHTML=String(input??'');return t.content.textContent.replace(/\s+/g,' ').trim()};
  const refs=input=>(Array.isArray(input)?input:input?[input]:[]).map(s=>typeof s==='string'?{title:s}:({title:s.title||s.label||s.name||s.url||s.href||'Source',url:s.url||s.href||'',locator:s.locator||s.note||s.section||''}));
  return {id:L.id||L.title,title:L.title,subtitle:plain(L.subtitle),subject:L.subject||'',limits:(Array.isArray(L.limits)?L.limits:L.limits?[L.limits]:[]).map(plain),level:L.level||'',lang:L.lang||'en',hook:clean(L.hook),stillStep:L.stillStep,params:Object.fromEntries(Object.entries(L.params||{}).map(([k,p])=>[k,{label:p.label||k,value:p.value,min:p.min,max:p.max,step:p.step}])),sources:refs(L.sources||L.references),misconceptions:(L.misconceptions||[]).map(plain),deeper:(L.deeper||[]).map(plain),code:L.code?{title:L.code.title,cpp:L.code.cpp,python:L.code.python,js:L.code.js,javascript:L.code.javascript,java:L.code.java,go:L.code.go,rust:L.code.rust}:null,steps:L.steps.map((s,index)=>({index,id:s.id||`step-${index+1}`,title:plain(s.title),say:clean(s.say),sayText:plain(s.say),lookFor:plain(s.lookFor),note:plain(s.note),sources:refs(s.sources),alts:(s.alts||[]).map(a=>({label:plain(a.label),say:clean(a.say),set:a.set||{}})),ask:s.ask?{kind:s.ask.kind,q:plain(s.ask.q),why:clean(s.ask.why),model:clean(s.ask.model),points:(s.ask.points||[]).map(plain)}:null}))};
 });
 if(!data.title||!data.steps.length)throw new Error('The source must have a title and at least one authored step.');
 await mkdir(join(out,'figures'),{recursive:true});
 // Preserve the executable source, model, fonts, and controls. A full noscript fallback is added below.
 await writeFile(join(out,'explorer.html'),inputHTML);
 const capture=async(index,altIndex=null)=>{
  await screen.evaluate(([i,a])=>{
   const api=window.__explorable;api.goStep(i,{focus:false});
   if(api.setParams)api.setParams(api.paramsAt?api.paramsAt(i):Object.assign({},...Object.entries(window.LESSON.params||{}).map(([k,p])=>({[k]:p.value})),...window.LESSON.steps.slice(0,i+1).map(s=>s.set||{})));
   if(a!==null){const patch=window.LESSON.steps[i].alts[a].set||{};if(!api.setParams&&Object.keys(patch).length)throw new Error('Alternate figure export requires __explorable.setParams');api.setParams?.({...api.state.params,...patch})}
  },[index,altIndex]);
  await screen.waitForTimeout(40);await screen.evaluate(()=>document.fonts.ready);
  return screen.evaluate(i=>{
   const L=window.LESSON,p={...window.__explorable.state.params},state=L.model(p),svg=document.querySelector('.xp-figure svg');
   if(!svg)throw new Error('The explorer did not render its mechanism figure.');
   const clone=svg.cloneNode(true),nodes=[svg,...svg.querySelectorAll('*')],copies=[clone,...clone.querySelectorAll('*')];
   const props=['color','fill','fill-opacity','stroke','stroke-width','stroke-opacity','stroke-dasharray','stroke-dashoffset','stroke-linecap','stroke-linejoin','opacity','font-family','font-size','font-weight','font-style','text-anchor','dominant-baseline','letter-spacing','paint-order','visibility'];
   nodes.forEach((node,j)=>{const cs=getComputedStyle(node);for(const prop of props)copies[j].style.setProperty(prop,cs.getPropertyValue(prop));copies[j].style.animation='none';copies[j].style.transition='none'});
   const vb=(svg.getAttribute('viewBox')||'0 0 640 380').split(/[ ,]+/).map(Number);
   // Reject visibly clipped input instead of exporting a misleading figure.
   // This authoring preflight is not an independent factual/acceptance review.
   const rootMatrix=svg.getCTM(),clipped=[];
   if(!rootMatrix)throw new Error('The figure has no measurable SVG viewport.');
   for(const text of svg.querySelectorAll('text')){
    if(text.closest('defs,symbol,clipPath,mask'))continue;const cs=getComputedStyle(text);if(cs.display==='none'||cs.visibility==='hidden')continue;
    const b=text.getBBox(),matrix=text.getCTM();if(!b.width||!b.height||!matrix)continue;
    const m=rootMatrix.inverse().multiply(matrix);
    const corners=[[b.x,b.y],[b.x+b.width,b.y],[b.x,b.y+b.height],[b.x+b.width,b.y+b.height]].map(([x,y])=>new DOMPoint(x,y).matrixTransform(m));
    if(corners.some(q=>q.x<vb[0]-1||q.y<vb[1]-1||q.x>vb[0]+vb[2]+1||q.y>vb[1]+vb[3]+1))clipped.push(text.textContent.trim());
   }
   if(clipped.length)throw new Error(`Step ${i+1} has clipped SVG text: ${clipped.slice(0,5).join(' | ')}. Wrap or reposition the source labels and export again.`);

   clone.setAttribute('xmlns','http://www.w3.org/2000/svg');clone.setAttribute('width',String(vb[2]));clone.setAttribute('height',String(vb[3]));
   const defs=document.createElementNS('http://www.w3.org/2000/svg','defs'),style=document.createElementNS('http://www.w3.org/2000/svg','style');
   // Preserve embedded local fonts for editable SVGs; no remote font URLs.
   style.textContent=[...document.querySelectorAll('style')].map(s=>s.textContent).join('\n').match(/@font-face\s*\{[^}]*\}/g)?.filter(s=>!s.includes('https:')&&!s.includes('http:')).join('\n')||'';defs.append(style);clone.prepend(defs);
   const a=L.steps[i].ask;let ans=a?.answer;if(typeof ans==='function')ans=ans(p,state);let answerText='';
   if(a?.kind==='choice'&&Number.isInteger(ans))answerText=String(a.options[ans]??'');else if(a?.kind==='number'&&ans!==undefined)answerText=String(ans)+(a.unit?' '+a.unit:'');
   return {svg:new XMLSerializer().serializeToString(clone),figureWidth:vb[2],figureHeight:vb[3],figureLabel:svg.querySelector('title')?.textContent||L.title,params:p,state:JSON.parse(JSON.stringify(state)),readouts:L.readouts?L.readouts(state,p).map(r=>[String(r[0]),String(r[1])]):[],answerText};
  },index);
 };
 for(const step of data.steps){
  const snap=await capture(step.index);Object.assign(step,snap);if(step.ask)step.ask.answerText=snap.answerText;
  await writeFile(join(out,'figures',`step-${step.index+1}.svg`),snap.svg);
  for(let a=0;a<step.alts.length;a++)if(Object.keys(step.alts[a].set).length){const alternate=await capture(step.index,a);const file=`figures/step-${step.index+1}-alt-${a+1}.svg`;await writeFile(join(out,file),alternate.svg);Object.assign(step.alts[a],{figure:file,figureLabel:alternate.figureLabel,params:alternate.params,state:alternate.state});}
 }
 // Capture the authored mobile layout through the same live renderer, not a scaled-down substitute.
 await screen.setViewportSize({width:390,height:1000});await screen.waitForTimeout(100);
 for(const step of data.steps){
  const snap=await capture(step.index);step.narrowFigure=`figures/step-${step.index+1}-narrow.svg`;step.narrowWidth=snap.figureWidth;step.narrowHeight=snap.figureHeight;
  await writeFile(join(out,step.narrowFigure),snap.svg);
  for(let a=0;a<step.alts.length;a++)if(step.alts[a].figure){const alt=await capture(step.index,a);const file=`figures/step-${step.index+1}-alt-${a+1}-narrow.svg`;await writeFile(join(out,file),alt.svg);step.alts[a].narrowFigure=file;}
 }
 if(errors.length)throw new Error(`Source runtime errors: ${errors.join(' | ')}`);
 let video;
 if(videoPath){
  const timing=JSON.parse(await readFile(resolve(timingPath),'utf8'));
  const film=await context.newPage();await film.route(/^https?:\/\//,route=>route.abort());await film.goto(pathToFileURL(inputPath).href+'?film-export');await film.waitForFunction(()=>window.__filmExport);
  const meta=await film.evaluate(()=>({scenes:window.__filmExport.scenes,states:window.__filmExport.sceneStates}));
  if(!meta.states||meta.states.length!==meta.scenes.length)throw new Error('Interactive video requires __filmExport.sceneStates aligned with exported narration scenes.');
  if(!Array.isArray(timing.scenes)||timing.scenes.length!==meta.scenes.length)throw new Error(`Timing has ${timing.scenes?.length??0} scenes; the source film has ${meta.scenes.length}. Use matching narration outputs.`);
  let end=0;
  for(const [i,s] of timing.scenes.entries()){if(!Number.isFinite(s.start)||!Number.isFinite(s.dur)||s.start<end-.05||s.dur<=0)throw new Error(`Invalid/overlapping timing at scene ${i+1}`);end=s.start+s.dur;}
  const vttPath=resolve(videoPath).replace(/\.[^.]+$/,'.vtt'),vtt=await readFile(vttPath,'utf8');
  if(!/^WEBVTT(?:\s|$)/.test(vtt)||!vtt.includes('-->'))throw new Error('A genuine adjacent WebVTT caption file is required.');
  const videoStat=await stat(resolve(videoPath));if(videoStat.size<32)throw new Error('The MP4 file is empty or invalid.');
  let probe;try{probe=JSON.parse(execFileSync('ffprobe',['-v','error','-show_entries','format=duration:stream=codec_type,width,height','-of','json',resolve(videoPath)],{encoding:'utf8'}))}catch{throw new Error('ffprobe could not validate the supplied MP4. Install ffmpeg and supply a playable video.')}
  if(!probe.streams?.some(s=>s.codec_type==='video'))throw new Error('The supplied MP4 has no video stream.');
  if(!Number.isFinite(Number(probe.format?.duration))||Math.abs(Number(probe.format?.duration)-(timing.total??end))>.2)throw new Error('Video duration does not match the timing sidecar (tolerance 0.2 s).');
  const stamps=[...vtt.matchAll(/(\d{2}):(\d{2}):(\d{2})[.,](\d{3})\s+-->\s+(\d{2}):(\d{2}):(\d{2})[.,](\d{3})/g)];
  const sec=(a)=>Number(a[0])*3600+Number(a[1])*60+Number(a[2])+Number(a[3])/1000;
  if(stamps.length!==timing.scenes.length)throw new Error('VTT cue count does not match the source narration scenes.');
  for(let i=0;i<stamps.length;i++){const sc=timing.scenes[i],a=sec(stamps[i].slice(1,5)),b=sec(stamps[i].slice(5,9));if(Math.abs(a-(sc.voiceAt??sc.start))>.06||Math.abs(b-(sc.start+sc.dur))>.06)throw new Error('VTT cue '+(i+1)+' does not align with the timing sidecar.');}

  const scenes=meta.scenes.map((s,i)=>{
   const params=meta.states[i];
   let step=data.steps.findIndex(t=>t.title===s.chapter);
   if(step<0)step=data.steps.findIndex(t=>JSON.stringify(t.params)===JSON.stringify(params));
   return {...s,...timing.scenes[i],params,step:step>=0?step:0};
  });
  video={scenes,total:timing.total??end,captions:vtt};data.video=video;
  await copyFile(resolve(videoPath),join(out,'lesson.mp4'));await writeFile(join(out,'lesson.vtt'),vtt);await copyFile(resolve(timingPath),join(out,'lesson.timing.json'));
  await film.close();
 }
 const chosen=Number(option('--still-step',String((data.stillStep??0)+1)))-1;
 if(!Number.isInteger(chosen)||!data.steps[chosen])throw new Error('--still-step is a one-based existing step number.');
 const selected=data.steps[chosen];
 const {svg:poster,layout:posterLayout}=await createPoster(screen,data,selected);
 await writeFile(join(out,'poster-layout.json'),JSON.stringify(posterLayout,null,2)+'\n');
 await writeFile(join(out,'still.svg'),poster);
 await screen.setViewportSize({width:1440,height:900});await screen.goto(pathToFileURL(join(out,'still.svg')).href);await screen.evaluate(()=>document.fonts.ready);await screen.screenshot({path:join(out,'still.png'),animations:'disabled'});
 await writeFile(join(out,'still.html'),htmlPage(data,'Mechanism figure',`<figure class="landscape-poster"><img src="still.svg" width="1440" height="900" alt="${esc(selected.figureLabel)}"><figcaption>${esc(selected.lookFor||selected.figureLabel)}</figcaption></figure><div class="mobile-figure">${figure(selected)}</div><p><a href="still.svg" download>Editable SVG</a> · <a href="still.png" download>1440 × 900 PNG</a></p><h2>${esc(selected.title)}</h2>${readouts(selected)}${selected.say}${selected.ask?`<h3>${esc(selected.ask.q)}</h3>${answer(selected)}`:''}${sources(data,selected,'references')}`));
 const staticHTML=staticLesson(data);await writeFile(join(out,'static.html'),staticHTML);
 const staticBody=staticHTML.match(/<body>([\s\S]*?)<\/body>/)[1];
 const fallback='<noscript><style>'+css+'</style>'+staticBody+'</noscript>';
 let bundledExplorer=inputHTML.replace(/<noscript\b[^>]*>[\s\S]*?<\/noscript>/i,fallback);
 if(bundledExplorer===inputHTML)bundledExplorer=inputHTML.replace(/<body\b[^>]*>/i,m=>m+fallback);
 bundledExplorer=bundledExplorer.replace(/<body\b[^>]*>/i,m=>m+'<p class="bundle-static-link" style="margin:12px 24px;font:16px/1.5 sans-serif"><a href="static.html">Read the complete static lesson</a></p>');
 const viewportAdapter='<script>if(window.parent!==window)window.addEventListener("message",event=>{if(event.source!==window.parent||event.data?.type!=="teach:set-params")return;requestAnimationFrame(()=>{const figure=document.querySelector(".xp-figure");if(figure)window.scrollTo({top:Math.max(0,figure.getBoundingClientRect().top+window.scrollY-14),behavior:"instant"})})});</script>';
 bundledExplorer=bundledExplorer.replace(/<\/body>/i,viewportAdapter+'</body>');
 await writeFile(join(out,'explorer.html'),bundledExplorer);await writeFile(join(out,'qa.html'),qaLesson(data));const cards=cardsLesson(data);await writeFile(join(out,'cards.html'),cards.html);await writeFile(join(out,'cards.tsv'),cards.tsv);
 if(video)await writeFile(join(out,'interactive-video.html'),videoLesson(data));
 const exported={...data,steps:data.steps.map(({svg,...s})=>s)};await writeFile(join(out,'lesson-data.json'),JSON.stringify(exported,null,2)+'\n');
 await writeFile(join(out,'bundle-manifest.json'),JSON.stringify({schema:'explorable-bundle/v1',title:data.title,input:basename(inputPath),sourceSha256:createHash('sha256').update(inputHTML).digest('hex'),steps:data.steps.length,still:{step:chosen+1,width:1440,height:900,editable:true},video:video?{scenes:video.scenes.length,total:video.total}:null,formats:['explorer.html','still.svg','still.png','still.html','static.html','qa.html','cards.html','cards.tsv',...(video?['interactive-video.html','lesson.mp4','lesson.vtt','lesson.timing.json']:[])],warnings:data.sources.length?[]:['No external factual references supplied; provenance identifies the source artifact only.']},null,2)+'\n');
 await browser.close();browser=null;
 console.log(`Exported ${data.steps.length} evaluated steps to ${out}${video?`; ${video.scenes.length} real video scenes`:''}.`);
 if(!video)console.log('Interactive video was not exported: supply matching --video and --timing with an adjacent .vtt.');
}catch(error){console.error(error.stack||error.message);if(browser)await browser.close();process.exitCode=1;}
