// ptk MathJax runner: TeX -> self-contained SVG through MathJax's tex2svg (AC-3.5). No network, no DOM.
// Usage: node tex2svg.mjs <items.json> <results.json>
// items: [{id, tex, display}]  results: [{id, ok, svg, width_ex, height_ex, valign_ex, error}]
// fontCache 'local' keeps the glyph paths inside each <svg>, so each result stands alone.
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync } from 'node:fs';

const prefix = process.env.PTK_NODE_PREFIX;
if (!prefix) { console.error('PTK_NODE_PREFIX not set (run through ptk/node.py)'); process.exit(2); }
const require = createRequire(prefix + '/package.json');
const { mathjax } = require('mathjax-full/js/mathjax.js');
const { TeX } = require('mathjax-full/js/input/tex.js');
const { SVG } = require('mathjax-full/js/output/svg.js');
const { liteAdaptor } = require('mathjax-full/js/adaptors/liteAdaptor.js');
const { RegisterHTMLHandler } = require('mathjax-full/js/handlers/html.js');
const { AllPackages } = require('mathjax-full/js/input/tex/AllPackages.js');

const [itemsPath, outPath] = process.argv.slice(2);
const items = JSON.parse(readFileSync(itemsPath, 'utf8'));
const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);
const tex = new TeX({ packages: AllPackages.filter((p) => p !== 'bussproofs'), formatError: (jax, err) => { throw err; } });
const svg = new SVG({ fontCache: 'local' });
const doc = mathjax.document('', { InputJax: tex, OutputJax: svg });

const ex = (v) => (v == null ? null : parseFloat(String(v).replace('ex', '')));
const results = [];
for (const it of items) {
  try {
    const node = doc.convert(it.tex, { display: !!it.display, em: 16, ex: 8, containerWidth: 1200 });
    const el = adaptor.firstChild(node);
    const style = adaptor.getAttribute(el, 'style') || '';
    const va = style.match(/vertical-align:\s*(-?[\d.]+)ex/);
    results.push({ id: it.id, ok: true, svg: adaptor.outerHTML(el), width_ex: ex(adaptor.getAttribute(el, 'width')),
                   height_ex: ex(adaptor.getAttribute(el, 'height')), valign_ex: va ? parseFloat(va[1]) : 0 });
  } catch (e) {
    results.push({ id: it.id, ok: false, error: String(e && e.message || e) });
  }
}
writeFileSync(outPath, JSON.stringify(results));
