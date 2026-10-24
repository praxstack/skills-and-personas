// First-party local verification. Does not load remote resources or modify installed engines.
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {mkdir,writeFile} from 'node:fs/promises';
const {loadPlaywright,launch}=await import(pathToFileURL(resolve('skills/teacher/skills/visual-qa/scripts/pw.mjs')));
const {chromium}=await loadPlaywright(), browser=await launch(chromium),results=[];
if(!process.argv.includes('--out'))throw Error('--out requires a new evidence directory');
const out=process.argv[process.argv.indexOf('--out')+1];await mkdir(out);
for(const name of ['merge-sort-stability','momentum','installed-v3.0.1-merge','original-accepted-merge']){
 const path=(name.startsWith('installed')||name.startsWith('original'))?`.superpowers/sdd/PLAN/task-3-evidence/${name}.html`:`examples/teach-visual-candidate/${name}/bundle/explorer.html`;
 for(const width of [1280,390]){
  const context=await browser.newContext({viewport:{width,height:900},reducedMotion:'reduce'}),page=await context.newPage(),remote=[];
  await context.route(/^https?:/,r=>{remote.push(r.request().url());return r.abort();});
  await page.goto(pathToFileURL(resolve(path)).href);await page.waitForFunction(()=>window.__explorable);
  const checks=await page.evaluate(()=>window.__explorable.check());if(checks.some(x=>!x.ok))throw Error('model failed');
  await page.evaluate(()=>window.__explorable.goStep(1));
  const before=await page.evaluate(()=>JSON.stringify(window.__explorable.state.params));
  const slider=page.locator('.xp-control input[type=range]').first();
  const target=await slider.evaluate(el=>el.value===el.max?el.min:el.max);await slider.fill(target);
  const params=await page.evaluate(()=>window.__explorable.state.params);
  if(JSON.stringify(params)===before)throw Error('slider did not change model parameters');
  const storage=await page.evaluate(()=>({local:Object.keys(localStorage),session:Object.keys(sessionStorage)}));
  if(storage.local.length||storage.session.length)throw Error('declined consent wrote browser storage');
  await page.locator('.xp-figure').screenshot({path:`${out}/${name}-${width}.png`});
  results.push({name,width,checks,params,remote,storage});
  if(remote.length)throw Error('offline page requested network');await context.close();
 }
 if(!name.startsWith('installed')&&!name.startsWith('original')){
  const c=await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:844}}),p=await c.newPage();
  await p.goto(pathToFileURL(resolve(`examples/teach-visual-candidate/${name}/bundle/static.html`)).href);
  const text=await p.textContent('body');if(!text.includes('Sources')||await p.locator('picture img').count()<4)throw Error('incomplete static fallback');
  await p.screenshot({path:`${out}/${name}-static-phone.png`,fullPage:true});results.push({name,staticNoJavaScript:true,figures:await p.locator('picture img').count()});await c.close();
 }
}
await browser.close();await writeFile(`${out}/results.json`,JSON.stringify(results,null,2));console.log(`${results.length} offline desktop/mobile/static checks passed; zero remote requests`);
