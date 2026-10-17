// Copy GSAP and the fonts out of node_modules into vendor/, so the page loads nothing from a CDN and the
// delivered source/ (which leaves node_modules behind) still renders. Run after `npm ci`: npm run vendor
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const nm = path.join(root, 'node_modules');
const out = path.join(root, 'vendor');
const files = {
  'gsap/dist/gsap.min.js': 'gsap.min.js',
  'gsap/dist/DrawSVGPlugin.min.js': 'DrawSVGPlugin.min.js',
  'gsap/dist/MotionPathPlugin.min.js': 'MotionPathPlugin.min.js',
  'gsap/dist/CustomEase.min.js': 'CustomEase.min.js',
  // Inter 4 variable (wght + opsz axes, full glyph set: arrows, math, check marks); the @fontsource subsets
  // leave out → ∞ ≤, which captions use.
  'inter-ui/variable/InterVariable.woff2': 'fonts/InterVariable.woff2',
  // Fraunces variable (wght, opsz, SOFT, WONK axes): the editorial serif for titles and statements
  '@fontsource-variable/fraunces/files/fraunces-latin-full-normal.woff2': 'fonts/Fraunces.woff2',
  '@fontsource-variable/fraunces/files/fraunces-latin-full-italic.woff2': 'fonts/Fraunces-Italic.woff2',
  '@fontsource/jetbrains-mono/files/jetbrains-mono-latin-400-normal.woff2': 'fonts/jetbrains-mono-400.woff2',
  '@fontsource/jetbrains-mono/files/jetbrains-mono-latin-600-normal.woff2': 'fonts/jetbrains-mono-600.woff2',
};
let n = 0;
for (const [from, to] of Object.entries(files)) {
  const src = path.join(nm, from);
  if (!fs.existsSync(src)) { console.error(`missing ${src}: run npm ci first`); process.exit(1); }
  fs.mkdirSync(path.dirname(path.join(out, to)), { recursive: true });
  fs.copyFileSync(src, path.join(out, to));
  n++;
}
const ver = (p) => JSON.parse(fs.readFileSync(path.join(nm, p, 'package.json'), 'utf8')).version;
fs.writeFileSync(path.join(out, 'VERSIONS.txt'), ['gsap', 'inter-ui', '@fontsource-variable/fraunces', '@fontsource/jetbrains-mono']
  .map((p) => `${p} ${ver(p)}`).join('\n') + '\n');
console.log(`vendored ${n} files (gsap ${ver('gsap')}) into vendor/`);
