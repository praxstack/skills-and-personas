// segmanifest.mjs: check a resumed segment manifest before trusting it.
// A segmented render writes build/segments/manifest.json and, on a re-run with the same key, resumes from it. The
// manifest names the files segments are written to and that ffmpeg concatenates, so a tampered or corrupt one could
// redirect those writes and reads. Only the names the renderer itself derives (seg_0000.mp4, seg_0001.mp4, ...), in
// order, with sane frame ranges, are accepted; anything else means start the segments over. sourceStamp() is the
// part of the resume key that says whether the page's files are still the ones the finished segments show.

import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';

export const segName = (i) => `seg_${String(i).padStart(4, '0')}.mp4`;

/** true when `m` is a manifest the renderer could have written for frames `start` to `nframes`: every segment
 *  in order, each starting where the one before ended, together covering the whole range with no gap. */
export function manifestOk(m, nframes, start = 0) {
  return !!m && Array.isArray(m.segments) && m.segments.length > 0 && m.segments.every((s, i) =>
    !!s && s.i === i && s.file === segName(i) && Number.isInteger(s.a) && Number.isInteger(s.b)
    && s.a === (i === 0 ? start : m.segments[i - 1].b) && s.b > s.a && s.b <= nframes && typeof s.done === 'boolean')
    && m.segments[m.segments.length - 1].b === nframes;
}

/** one line of an ffmpeg concat list; a ' in the path is written as '\'' (the list format's own escape). */
export const concatLine = (p) => `file '${p.replace(/'/g, "'\\''")}'`;

const SKIP = ['node_modules', '.git', 'build', 'segments', 'stills', 'out', 'media', 'qa'];
function digest(p) {
  const h = createHash('sha256'), fd = fs.openSync(p, 'r'), buf = Buffer.alloc(1 << 20);
  try { for (let n; (n = fs.readSync(fd, buf, 0, buf.length, null)) > 0;) h.update(buf.subarray(0, n)); } finally { fs.closeSync(fd); }
  return h.digest('hex');
}
function files(dir, rel, out, seen) {
  const real = fs.realpathSync(dir);
  if (seen.has(real)) return out;   // a linked folder that loops back
  seen.add(real);
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (SKIP.includes(e.name)) continue;
    const p = path.join(dir, e.name), r = rel + '/' + e.name;
    let st;
    try { st = fs.statSync(p); } catch { out.push(`${r} missing`); continue; }   // a link to nothing
    if (st.isDirectory()) files(p, r, out, seen);
    else if (st.isFile()) out.push(`${r} ${st.size} ${digest(p)}`);
  }
  return out;
}
/** The resume stamp of a page folder: every file's path and a digest of its bytes (not its time), so an edit that
 *  keeps the size and time (a generator that restores timestamps, two writes in one millisecond) changes it, as
 *  does a file added, deleted or renamed. Build output and dependencies (SKIP) are left out. */
export const sourceStamp = (root) => createHash('sha256').update(files(root, '', [], new Set()).sort().join('\n')).digest('hex').slice(0, 16);
