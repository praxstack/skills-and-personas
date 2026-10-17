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
  'gsap/dist/MorphSVGPlugin.min.js': 'MorphSVGPlugin.min.js',
  'gsap/dist/SplitText.min.js': 'SplitText.min.js',
  'gsap/dist/TextPlugin.min.js': 'TextPlugin.min.js',
  'gsap/dist/CustomEase.min.js': 'CustomEase.min.js',
  // Inter 4 variable (wght + opsz axes, full glyph set: arrows, math, check marks). The @fontsource Inter
  // subsets leave out → ∞ ≤, which captions use all the time, so Inter comes from the inter-ui package.
  'inter-ui/variable/InterVariable.woff2': 'fonts/InterVariable.woff2',
  '@fontsource/jetbrains-mono/files/jetbrains-mono-latin-400-normal.woff2': 'fonts/jetbrains-mono-400.woff2',
  '@fontsource/jetbrains-mono/files/jetbrains-mono-latin-600-normal.woff2': 'fonts/jetbrains-mono-600.woff2',
  '@fontsource/jetbrains-mono/files/jetbrains-mono-latin-700-normal.woff2': 'fonts/jetbrains-mono-700.woff2',
  '@fontsource/bangers/files/bangers-latin-400-normal.woff2': 'fonts/bangers-400.woff2',
};
let n = 0;
for (const [from, to] of Object.entries(files)) {
  const src = path.join(nm, from);
  if (!fs.existsSync(src)) { console.error(`missing ${src}: run npm ci first`); process.exit(1); }
  fs.mkdirSync(path.dirname(path.join(out, to)), { recursive: true });
  fs.copyFileSync(src, path.join(out, to));
  n++;
}
const v = JSON.parse(fs.readFileSync(path.join(nm, 'gsap/package.json'), 'utf8')).version;
fs.writeFileSync(path.join(out, 'VERSIONS.txt'), `gsap ${v}\ninter-ui ${JSON.parse(fs.readFileSync(path.join(nm, 'inter-ui/package.json'), 'utf8')).version}\n` +
  `@fontsource/jetbrains-mono ${JSON.parse(fs.readFileSync(path.join(nm, '@fontsource/jetbrains-mono/package.json'), 'utf8')).version}\n` +
  `@fontsource/bangers ${JSON.parse(fs.readFileSync(path.join(nm, '@fontsource/bangers/package.json'), 'utf8')).version}\n`);
console.log(`vendored ${n} files (gsap ${v}) into vendor/`);
