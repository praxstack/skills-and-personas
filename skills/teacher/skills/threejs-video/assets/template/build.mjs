// build.mjs: bundle src/main.js (three.js, the kit, the scenes, fonts as data URLs) into dist/film.js.
// src/timing.js is NOT bundled: index.html loads it directly, so re-voicing never needs a rebuild.
// The bundle is written only when its bytes change, so a rebuild does not invalidate finished render segments.
//   node build.mjs            build once
//   node build.mjs --watch    rebuild on save (preview: any static server in this folder, open index.html?q=draft)
import * as esbuild from 'esbuild';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.dirname(fileURLToPath(import.meta.url));
const out = path.join(root, 'dist', 'film.js');
const opts = {
  absWorkingDir: root, entryPoints: ['src/main.js'], bundle: true, format: 'iife', target: 'chrome120',
  loader: { '.woff2': 'dataurl', '.css': 'text' }, write: false, minify: false, legalComments: 'none', logLevel: 'warning',
};
function save(result) {
  const code = result.outputFiles[0].contents;
  fs.mkdirSync(path.dirname(out), { recursive: true });
  if (fs.existsSync(out) && Buffer.compare(fs.readFileSync(out), Buffer.from(code)) === 0) { console.log('dist/film.js unchanged'); return; }
  fs.writeFileSync(out, code);
  console.log(`dist/film.js written (${(code.length / 1e6).toFixed(2)} MB)`);
}
if (process.argv.includes('--watch')) {
  const ctx = await esbuild.context({ ...opts, plugins: [{ name: 'save', setup(b) { b.onEnd((r) => { if (!r.errors.length) save(r); }); } }] });
  await ctx.watch(); console.log('watching src/ ...');
} else {
  save(await esbuild.build(opts));
}
