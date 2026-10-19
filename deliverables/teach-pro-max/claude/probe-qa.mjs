import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
const require = createRequire(process.env.PTK_NODE_PREFIX + '/package.json');
const { chromium } = require('playwright');
const [source, output] = process.argv.slice(2);
const browser = await chromium.launch();
const results = [];
for (const width of [1440, 390]) for (const scheme of ['light', 'dark']) {
  const context = await browser.newContext({viewport:{width,height:900},colorScheme:scheme});
  const page = await context.newPage();
  await page.goto(pathToFileURL(source).href); await page.evaluate(()=>document.fonts.ready);
  const result = await page.evaluate(()=>{
    const core=document.querySelector('.explanation'), question=document.querySelector('[data-question]');
    return {coreParagraphs:core.querySelectorAll('p').length,
      coreVisible:core.getBoundingClientRect().height>0,
      coreBeforeQuestion:!!(core.compareDocumentPosition(question)&Node.DOCUMENT_POSITION_FOLLOWING),
      coreButtons:core.querySelectorAll('button,input').length,
      horizontalOverflow:document.documentElement.scrollWidth>innerWidth};
  });
  await page.screenshot({path:output+`-${width}-${scheme}.png`});
  results.push({width,scheme,...result}); await context.close();
}
const context=await browser.newContext({javaScriptEnabled:false});const page=await context.newPage();
await page.goto(pathToFileURL(source).href);results.push({javascript:false,coreVisible:await page.locator('.explanation').isVisible()});
await context.close();await browser.close();writeFileSync(output+'.json',JSON.stringify(results,null,2));
