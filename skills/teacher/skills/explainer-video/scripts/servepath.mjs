// servepath.mjs: map a request path onto a file inside a served folder, or nothing.
// The lexical check alone was not enough: "/..%2Fsibling/x" passed a prefix test, and a symlink inside the folder
// could point anywhere, so both the folder and the file are resolved to their real paths before comparing.
import fs from 'node:fs';
import path from 'node:path';

/** The real path of the file that `urlPath` names inside `root`, or null when it is outside, missing, a directory,
 *  or reached through a symlink that leaves the folder. */
export function resolveUnder(root, urlPath) {
  let p;
  try { p = path.join(root, decodeURIComponent(new URL(urlPath, 'http://x').pathname)); } catch { return null; }
  let realRoot, real;
  try { realRoot = fs.realpathSync(root); real = fs.realpathSync(p); } catch { return null; }
  const rel = path.relative(realRoot, real);
  if (rel === '' || rel.startsWith('..') || path.isAbsolute(rel)) return null;
  try { if (fs.statSync(real).isDirectory()) return null; } catch { return null; }
  return real;
}

// The type each file is served with, by its extension in any case: a module script (.js, .mjs, main.JS) that came back
// as octet-stream would be refused by the browser. The renderer and the kits' checkers serve with this one table.
const TYPES = { '.html': 'text/html', '.htm': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript',
  '.cjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.csv': 'text/csv', '.txt': 'text/plain',
  '.woff2': 'font/woff2', '.woff': 'font/woff', '.ttf': 'font/ttf', '.otf': 'font/otf', '.png': 'image/png', '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.gif': 'image/gif', '.svg': 'image/svg+xml', '.wav': 'audio/wav',
  '.mp3': 'audio/mpeg', '.m4a': 'audio/mp4', '.mp4': 'video/mp4', '.webm': 'video/webm', '.mov': 'video/quicktime',
  '.glb': 'model/gltf-binary', '.gltf': 'model/gltf+json', '.hdr': 'application/octet-stream', '.wasm': 'application/wasm' };
export const contentType = (p) => TYPES[path.extname(p).toLowerCase()] || 'application/octet-stream';
