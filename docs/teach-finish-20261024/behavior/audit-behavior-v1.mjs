#!/usr/bin/env node
// Supplemental observation only. Does not replace or certify any frozen gate.
import {mkdtemp, mkdir, copyFile, writeFile, readFile, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {resolve, join, dirname} from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {execFileSync, spawnSync} from 'node:child_process';
import {loadPlaywright, launch} from '../../../skills/teacher/skills/visual-qa/scripts/pw.mjs';

if (!process.argv.includes('--trust-repository-fixture')) throw Error('Review the first-party seasons.lesson.js, then pass --trust-repository-fixture.');
const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '../../..');
const out = resolve(process.argv[process.argv.indexOf('--out') + 1] || here);
if (!process.argv.includes('--out')) throw Error('--out requires a new evidence directory');
await mkdir(out); // Refuse to overwrite historical evidence.
const work = await mkdtemp(join(tmpdir(), 'teach-behavior-v1-'));
const checks = [], errors = [], network = [], observations = {};
const check = (name, ok, observed = null) => checks.push({name, ok: Boolean(ok), observed});
const sha = async path => createHash('sha256').update(await readFile(path)).digest('hex');
let browser;
try {
  const scripts = join(root, 'skills/teacher/skills/course/scripts');
  const exp = join(root, 'skills/teacher/skills/explorable/scripts');
  const fixture = join(root, 'skills/teacher/skills/explorable/assets/examples/seasons.lesson.js');
  const course = join(work, 'course'), site = join(work, 'site'), bundle = join(work, 'bundle');
  await mkdir(course);
  await copyFile(fixture, join(course, 'seasons.lesson.js'));
  await writeFile(join(course, 'course.json'), JSON.stringify({id:'synthetic-behavior-v1', title:'Synthetic behavior audit', lessons:[{id:'seasons',file:'seasons.lesson.js',title:'Why seasons happen',minutes:5}]}));
  execFileSync('python3', [join(scripts, 'build_course.py'), course, '-o', site, '--trust-authored-code']);
  execFileSync('node', [join(exp, 'bundle_lesson.mjs'), join(site, 'seasons.html'), '--out', bundle]);
  observations.hashes = {};
  for (const p of [fixture, join(exp,'../assets/engine/explorable.js'), fileURLToPath(import.meta.url), join(course,'course.json'), join(site,'index.html'), join(site,'seasons.html'), join(bundle,'explorer.html'), join(bundle,'static.html'), join(scripts,'check_course_page.mjs')]) observations.hashes[p.startsWith(root) ? p.slice(root.length+1) : p.slice(work.length+1)] = await sha(p);
  const {chromium} = await loadPlaywright();
  browser = await launch(chromium);
  observations.browser = browser.version();
  async function open(file, suffix = '', options = {}) {
    const ctx = await browser.newContext({viewport:{width:1280,height:900}, reducedMotion:'reduce', offline:true, ...options});
    await ctx.route(/^https?:/, route => {network.push(route.request().url()); return route.abort();});
    const page = await ctx.newPage();
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(pathToFileURL(file).href + suffix);
    return {ctx,page};
  }
  const storage = page => page.evaluate(() => ({local:{...localStorage}, session:{...sessionStorage}}));
  const empty = s => Object.keys(s.local).length === 0 && Object.keys(s.session).length === 0;
  const ready = page => page.waitForFunction(() => window.__explorable || window.__course);
  const progress = page => page.locator('.cs-head .nb-print').first().textContent();
  {
    const {ctx,page} = await open(join(site,'index.html')); await ready(page);
    check('course consent defaults declined', !await page.locator('#cs-remember').isChecked());
    await page.locator('.cs-drawer .cs-chip', {hasText:'Done'}).click();
    check('course no-consent Done works in session', /1 of/.test(await progress(page)));
    observations.courseDeclined = await storage(page);
    check('course declined writes neither local nor session storage', empty(observations.courseDeclined));
    await page.reload(); await ready(page);
    check('course declined progress resets after reload', /^0 of/.test(await progress(page)));
    await page.locator('#cs-remember').check();
    await page.locator('.cs-drawer .cs-chip', {hasText:'Done'}).click();
    observations.courseGranted = await storage(page);
    check('course grant writes consent and progress', observations.courseGranted.local['course:synthetic-behavior-v1:consent'] === 'yes' && JSON.parse(observations.courseGranted.local['course:synthetic-behavior-v1']).status.seasons === 'done');
    await page.reload(); await ready(page);
    check('course granted progress resumes after reload', /1 of/.test(await progress(page)) && await page.locator('#cs-remember').isChecked());
    await page.locator('#cs-remember').uncheck();
    observations.courseWithdrawn = await storage(page);
    check('course withdrawal removes progress and consent', empty(observations.courseWithdrawn));
    await page.reload(); await ready(page);
    check('course withdrawn progress does not resume', /^0 of/.test(await progress(page)));
    await ctx.close();
  }
  {
    const {ctx,page} = await open(join(bundle,'explorer.html')); await ready(page);
    check('explorer defaults explanation-first with declined consent', await page.evaluate(() => document.documentElement.dataset.teachingStyle === 'visual-explain') && !await page.locator('#xp-remember').isChecked());
    const count = await page.evaluate(() => window.LESSON.steps.length);
    const walked = [];
    for (let i=0;i<count;i++) {
      const obs = await page.evaluate(() => {
        const article=document.querySelector('.xp-step'), why=article.querySelector('.xp-explanation'), optional=article.querySelector('details.xp-optional-practice');
        return {step:window.__explorable.state.step, explained:!!why && !!why.textContent.trim(), practiceClosed:!!optional && !optional.open, before:!!why && !!optional && Boolean(why.compareDocumentPosition(optional)&Node.DOCUMENT_POSITION_FOLLOWING), answers:window.__explorable.state.attempts, nextDisabled:article.querySelector('.xp-next').disabled};
      });
      walked.push(obs);
      check(`explanation step ${i+1} precedes closed optional check; navigation open`, obs.step===i && obs.explained && obs.practiceClosed && obs.before && !obs.nextDisabled);
      if(i===0) await page.screenshot({path:join(out,'explanation-first.png'),fullPage:true});
      await page.locator('.xp-next').click();
    }
    observations.explanationWalk = walked;
    await page.getByRole('button',{name:"I've got it. I'm done with this.",exact:true}).click();
    observations.closureReport = await page.locator('.xp-report').inputValue();
    check('default closure accepts satisfaction without answers', observations.closureReport.includes("Next: I've got it. I'm done with this.") && !Object.values(await page.evaluate(()=>window.__explorable.state.attempts)).some(a=>a.length));
    check('unattempted closure fabricates no correctness claims', !/right first time|^- (?:Same light|Why the noon|It isn.t distance|Switch the tilt|Longer days)/m.test(observations.closureReport),observations.closureReport);
    await page.getByRole('tab',{name:'Lesson',exact:true}).click();
    await page.locator('.xp-notes-box').fill('SYNTHETIC DECLINED NOTE'); await page.locator('.xp-notes-box').blur();
    observations.explorerDeclined = await storage(page);
    check('explorer declined notes and viewed steps write no storage', empty(observations.explorerDeclined));
    await page.reload(); await ready(page);
    check('explorer declined note and location reset', await page.locator('.xp-notes-box').inputValue()==='' && await page.evaluate(()=>window.__explorable.state.step===0));
    await page.locator('#xp-remember').check();
    await page.locator('.xp-notes-box').fill('SYNTHETIC CONSENTED NOTE'); await page.locator('.xp-notes-box').blur();
    await page.locator('.xp-next').click();
    observations.explorerGranted = await storage(page);
    await page.reload(); await ready(page);
    check('explorer granted note, location and consent resume', await page.locator('.xp-notes-box').inputValue()==='SYNTHETIC CONSENTED NOTE' && await page.evaluate(()=>window.__explorable.state.step===1) && await page.locator('#xp-remember').isChecked());
    await page.locator('#xp-remember').uncheck();
    observations.explorerWithdrawn = await storage(page);
    check('explorer withdrawal removes progress and consent', empty(observations.explorerWithdrawn));
    await page.reload(); await ready(page);
    check('explorer withdrawn note and location reset', await page.locator('.xp-notes-box').inputValue()==='' && await page.evaluate(()=>window.__explorable.state.step===0));
    await ctx.close();
  }
  {
    const {ctx,page} = await open(join(bundle,'explorer.html'),'?practice=1'); await ready(page);
    // Actual fixture answers: step 1 is option 2; step 2 is option 1.
    await page.locator('.xp-option[data-k="2"]').click();
    await page.getByRole('button',{name:'Check',exact:true}).click();
    await page.locator('.xp-next').click();
    await page.locator('.xp-option[data-k="0"]').click();
    await page.getByRole('button',{name:'Check',exact:true}).click();
    await page.locator('.xp-option[data-k="1"]').click();
    await page.getByRole('button',{name:'Check',exact:true}).click();
    observations.answeredReport = await page.evaluate(()=>({text:window.__explorable.report(),attempts:window.__explorable.state.attempts}));
    check('actual correct first try is reported accurately', observations.answeredReport.text.includes('- Same light, more ground: right first time') && observations.answeredReport.attempts[0].length===1 && observations.answeredReport.attempts[0][0].right,observations.answeredReport);
    check('actual previously missed answer is not reported correct first try', observations.answeredReport.text.includes('- Why the noon sun moves: 1 miss') && !observations.answeredReport.text.includes('- Why the noon sun moves: right first time') && observations.answeredReport.attempts[1].map(a=>a.right).join(',')==='false,true');
    await ctx.close();
  }
  {
    const {ctx,page} = await open(join(bundle,'explorer.html'),'?practice=1'); await ready(page);
    check('explicit practice requests attempt-first navigation', await page.locator('.xp-next').isDisabled() && await page.evaluate(()=>document.documentElement.dataset.teachingStyle==='practice-first'));
    check('requested practice answer initially unrevealed', await page.locator('.xp-why').count()===0);
    await page.getByRole('button',{name:'Show me',exact:true}).click();
    check('Show me answers immediately without attempt', await page.locator('.xp-why').isVisible() && !await page.locator('.xp-next').isDisabled());
    await page.getByRole('link',{name:'Read the complete explanation instead'}).click(); await ready(page);
    check('exit practice restores explanation-first without quiz barrier', await page.evaluate(()=>document.documentElement.dataset.teachingStyle==='visual-explain') && !await page.locator('.xp-next').isDisabled());
    check('practice actions without consent remain ephemeral', empty(await storage(page)));
    await ctx.close();
  }
  {
    const {ctx,page} = await open(join(bundle,'explorer.html'),'',{javaScriptEnabled:false});
    const text = await page.locator('body').innerText();
    check('JS-disabled explorer has complete static fallback', ['Same light, more ground','Why the noon sun moves',"It isn't distance",'Switch the tilt off','Longer days add up'].every(t=>text.includes(t)) && text.includes('No tilt, no seasons.'));
    await page.screenshot({path:join(out,'static-fallback.png'),fullPage:true});
    await page.getByRole('link',{name:'Read the complete static lesson',exact:true}).click();
    check('offline static navigation retains explanation', (await page.locator('body').innerText()).includes('No tilt, no seasons.'));
    await ctx.close();
  }
  await browser.close(); browser=null;
  // Both checker invocations are diagnostic comparisons, never acceptance.
  for(const [label,path] of [['frozen',join(scripts,'check_course_page.mjs')],['unapprovedProposal',join(here,'check-course-consent-v2.proposed.mjs')]]) {
    const r=spawnSync('node',[path,join(site,'index.html')],{encoding:'utf8',timeout:60000});
    observations[label]={exit:r.status,stdout:r.stdout,stderr:r.stderr,error:r.error?.message};
  }
  check('frozen checker reproduces only historical no-consent reload failure', observations.frozen.exit===1 && observations.frozen.stdout.match(/^FAIL /gm)?.length===1 && observations.frozen.stdout.includes('FAIL status survives a reload'));
  check('unapproved proposed checker executes consent-aware branches diagnostically', observations.unapprovedProposal.exit===0);
  check('offline browser observed no HTTP requests', network.length===0,network);
  check('no browser page errors', errors.length===0,errors);
} finally {
  if(browser)await browser.close();
  await writeFile(join(out,'observations.json'),JSON.stringify({schema:'supplemental-behavior-observation/v1',authority:'non-governing; proposal unapproved',observedAt:new Date().toISOString(),checks,observations,errors,network,limits:['Only reviewed first-party seasons fixture and Chromium were exercised.','Page behavior does not prove live-chat instruction adherence or human learning.','No narrated media acceptance; no sandbox repeatability claim.','No learner journal created; only synthetic temporary browser state.']},null,2)+'\n');
  await rm(work,{recursive:true,force:true});
}
console.log(`${checks.filter(c=>c.ok).length}/${checks.length} supplemental observations passed; proposal remains unapproved`);
if(checks.some(c=>!c.ok)) {console.error(JSON.stringify(checks.filter(c=>!c.ok),null,2));process.exitCode=1;}
