#!/usr/bin/env node
// Markdown -> one self-contained HTML companion (AC-8.3). Ported from prax-teach-v2
// .engine/scripts/render_markdown.mjs (renderer 2.2.0) and extended:
//   - inline SVG: a sanitized, static, accessible subset (v2 rejected every <svg>; report 02 V3);
//   - math: $...$ and $$...$$ become MathJax SVG through node/tex2svg.mjs (report 02 V4);
//   - <video controls> with a captions <track>, local files only, no autoplay;
//   - provenance: the source sha256 plus the sha256 of every local asset it references;
//   - a CSP meta with hashes for the two style blocks (no scripts at all);
//   - generated-at comes from SOURCE_DATE_EPOCH (ptk sets it), else from the source hash, never the
//     clock, so --check is stable (report 04 E2);
//   - symlinks are checked only below the trusted root, which is realpath'd first (E16);
//   - CRLF frontmatter is stripped (E24); task lists are glyphs, not form inputs (D20.12, E17);
//   - one module path: $PTK_NODE_PREFIX, else next to this file (E28).
// Kept from v2: trusted-root publication with snapshot checks and atomic write, rejection (never
// silent stripping) of unsupported HTML, URL policy, animated-image policy, byte determinism.
// Usage: render_markdown.mjs [--check] --trusted-root <dir> <source.md> [output.html]

import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { lstat, open, readFile, realpath, rename, unlink } from 'node:fs/promises';
import { createRequire } from 'node:module';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const RENDERER_VERSION = 'prax-teach-markdown/2.3.0';
const TEMPLATE_VERSION = 'prax-teach-lesson/3.1.0';
const HERE = path.dirname(fileURLToPath(import.meta.url));
// v2's AskTheMove presentation, byte for byte (its sha256 is pinned by the ported test).
const PRESENTATION_CSS = `/* AskTheMove teaching presentation. Embedded by render_markdown.mjs. */
:root { color-scheme:light; --paper:#fbfaf4; --ink:#171d29; --blue:#1f48ae; --red:#c92324; --muted:#535965; --line:#c8c7bf; --surface:#f7f3e9; --book:Vollkorn,Georgia,"Times New Roman",serif; --technical:"Courier Prime",ui-monospace,SFMono-Regular,Menlo,monospace; --coach:Kalam,"Segoe Print","Bradley Hand","Comic Sans MS",cursive; }
@media (prefers-color-scheme: dark) { :root { color-scheme:dark; --paper:#171d29; --ink:#fbfaf4; --blue:#a6c1ff; --red:#ffaaa7; --muted:#c1c5ce; --line:#666c79; --surface:#202735; } }
* { box-sizing:border-box; }
html { scroll-behavior:smooth; }
body { margin:0; background:var(--paper); color:var(--ink); font:18px/1.65 var(--book); overflow-wrap:break-word; }
a { color:var(--blue); text-underline-offset:.18em; }
a:focus-visible, [tabindex="0"]:focus-visible, summary:focus-visible { outline:3px solid var(--blue); outline-offset:4px; }
::selection { background:#f3e797; color:#171d29; }
.skip-link { position:fixed; left:1rem; top:.7rem; transform:translateY(-180%); z-index:10; padding:.6rem .85rem; background:var(--ink); color:var(--paper); }
.skip-link:focus { transform:translateY(0); }
header { border-bottom:3px double var(--line); }
header div, main, footer { width:min(840px, calc(100% - 2.5rem)); margin-inline:auto; }
header div { display:flex; flex-wrap:wrap; justify-content:space-between; gap:.5rem 1rem; padding:1rem 0; }
header strong { color:var(--ink); }
main { padding:clamp(2.4rem,7vw,5rem) 0; }
h1,h2,h3,h4,h5,h6 { font-family:var(--book); font-style:normal; line-height:1.15; text-wrap:balance; scroll-margin-top:2rem; }
h1 { max-width:20ch; margin:0 0 1.5rem; font-size:clamp(2.35rem,7vw,4.6rem); letter-spacing:-.025em; }
h2 { margin:3rem 0 1rem; font-size:clamp(1.7rem,4vw,2.4rem); }
h3 { margin:2rem 0 .6rem; font-size:1.4rem; }
p,li { max-width:68ch; }
blockquote { margin:1.4rem 0; padding:.4rem 1.1rem; border-left:2px solid var(--line); font-family:var(--book); }
[role="note"] { margin:1.5rem 0; max-width:48ch; color:var(--blue); font:1.2rem/1.45 var(--coach); }
[role="note"][aria-label="Correction"] { color:var(--red); border-left:2px solid currentColor; padding-left:1rem; }
[role="note"] p { margin:.5rem 0; }
code,kbd,samp { font-family:var(--technical); font-size:.88em; overflow-wrap:anywhere; }
code { padding:.08em .22em; border:1px solid var(--line); }
pre { overflow:auto; padding:1rem 1.1rem; border-block:1px solid var(--line); background:var(--surface); color:var(--ink); }
pre code { overflow-wrap:normal; padding:0; border:0; color:inherit; }
figure { margin:1.7rem 0; }
img { max-width:100%; height:auto; }
figcaption { margin-top:.65rem; font-size:1rem; }
.table-wrap { overflow:auto; margin:1.4rem 0; border-block:1px solid var(--line); }
table { width:100%; border-collapse:collapse; font-size:1rem; font-variant-numeric:lining-nums tabular-nums; }
th,td { padding:.72rem .8rem; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }
th { font-family:var(--technical); font-size:.85rem; }
details { margin:1rem 0; padding:.75rem 0; border-block:1px solid var(--line); }
summary { cursor:pointer; font-weight:700; }
footer { padding:1.2rem 0 2.5rem; border-top:1px solid var(--line); color:var(--muted); font: .8rem/1.65 var(--technical); overflow-wrap:anywhere; }
@media (prefers-contrast:more) { :root { --paper:#fff; --ink:#000; --blue:#123479; --red:#9b1717; --muted:#222; --line:#555; --surface:#fff; } a { text-decoration-thickness:2px; } }
@media (forced-colors:active) { :root { --paper:Canvas; --ink:CanvasText; --blue:LinkText; --red:CanvasText; --muted:CanvasText; --line:CanvasText; --surface:Canvas; } }
@media (prefers-reduced-motion:reduce) { html { scroll-behavior:auto; } *,*::before,*::after { animation-duration:.01ms!important; transition-duration:.01ms!important; } }
@media print { :root { color-scheme:light; --paper:#fff; --ink:#000; --blue:#1f48ae; --red:#c92324; --surface:#fff; --line:#aaa; --muted:#333; } header,.skip-link { display:none; } body { font-size:10.5pt; } main,footer { width:100%; } h1 { max-width:none; font-size:28pt; } pre,table,blockquote,figure { break-inside:avoid; } details > *:not(summary),details::details-content { display:block!important; content-visibility:visible!important; } a[href^="http"]::after { content:" (" attr(href) ")"; font-size:8pt; } }
`;
// v2.1 additions in a second block, so the v2 presentation bytes and hash stay unchanged.
const MEDIA_CSS_BASE = `/* v2.1 media: inline SVG, MathJax SVG, video, task glyphs. */
svg { max-width:100%; height:auto; }
.math { display:inline-block; line-height:0; }
.math svg { overflow:visible; }
.math-display { display:block; margin:1.3rem 0; overflow-x:auto; text-align:center; line-height:0; }
video { display:block; width:100%; max-width:100%; height:auto; margin:1.4rem 0; background:#000; }
.task { display:inline-block; width:1.4em; font-family:var(--technical); }
li:has(> .task) { list-style:none; }
`;

const HTML_TAGS = [
  'a', 'abbr', 'b', 'blockquote', 'br', 'button', 'caption', 'code', 'dd', 'del',
  'details', 'div', 'dl', 'dt', 'em', 'fieldset', 'figcaption', 'figure', 'h1', 'h2',
  'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img', 'input', 'kbd', 'li', 'mark',
  'label', 'legend', 'ol', 'option', 'p', 'pre', 's', 'samp', 'select', 'small',
  'span', 'strong', 'sub', 'summary', 'sup', 'table', 'tbody', 'td', 'textarea',
  'tfoot', 'th', 'thead', 'tr', 'u', 'ul', 'var',
];
const MEDIA_TAGS = ['video', 'source', 'track'];
// Static SVG only: no script, foreignObject, animation, style, filters or external references.
const SVG_TAGS = [
  'svg', 'g', 'defs', 'title', 'desc', 'path', 'rect', 'circle', 'ellipse', 'line', 'polyline',
  'polygon', 'text', 'tspan', 'marker', 'lineargradient', 'radialgradient', 'stop', 'clippath',
  'use', 'symbol',
];
const SVG_MOTION_TAGS = ['animate', 'animatemotion', 'animatetransform', 'set'];
const ALLOWED_TAGS = [...HTML_TAGS, ...MEDIA_TAGS, ...SVG_TAGS];
const GLOBAL_ATTRIBUTES = ['aria-describedby', 'aria-label', 'dir', 'id', 'lang', 'role'];
const SVG_ATTRIBUTES = [
  'aria-hidden', 'aria-labelledby', 'class', 'clip-path', 'clippathunits', 'cx', 'cy', 'd', 'dominant-baseline',
  'dx', 'dy', 'fill', 'fill-opacity', 'fill-rule', 'focusable', 'font-family', 'font-size', 'font-style',
  'font-weight', 'gradienttransform', 'gradientunits', 'height', 'href', 'letter-spacing', 'marker-end',
  'marker-mid', 'marker-start', 'markerheight', 'markerunits', 'markerwidth', 'offset', 'opacity', 'orient',
  'paint-order', 'points', 'preserveaspectratio', 'r', 'refx', 'refy', 'rx', 'ry', 'stop-color', 'stop-opacity',
  'stroke', 'stroke-dasharray', 'stroke-linecap', 'stroke-linejoin', 'stroke-opacity', 'stroke-width',
  'text-anchor', 'transform', 'vector-effect', 'viewbox', 'width', 'x', 'x1', 'x2', 'xlink:href', 'xmlns',
  'xmlns:xlink', 'y', 'y1', 'y2',
];
const ALLOWED_ATTRIBUTES = {
  a: ['href', 'title'],
  code: ['class'],
  details: ['open'],
  img: ['alt', 'height', 'loading', 'src', 'title', 'width'],
  button: ['disabled', 'name', 'type', 'value'],
  fieldset: ['disabled'],
  input: ['checked', 'disabled', 'name', 'type', 'value'],
  label: ['for'],
  ol: ['start'],
  option: ['disabled', 'selected', 'value'],
  select: ['disabled', 'multiple', 'name'],
  td: ['align', 'colspan', 'rowspan'],
  textarea: ['cols', 'name', 'readonly', 'rows'],
  th: ['align', 'colspan', 'rowspan', 'scope'],
  video: ['controls', 'height', 'muted', 'playsinline', 'poster', 'preload', 'src', 'width'],
  source: ['src', 'type'],
  track: ['default', 'kind', 'label', 'src', 'srclang'],
  span: ['class'],
  div: ['class'],
  '*': GLOBAL_ATTRIBUTES,
};
for (const tag of SVG_TAGS) ALLOWED_ATTRIBUTES[tag] = SVG_ATTRIBUTES;
const FORM_CONTROLS = new Set(['input', 'select', 'textarea', 'button']);
const LOCAL_MEDIA = { video: ['.mp4', '.webm'], source: ['.mp4', '.webm'], track: ['.vtt'], poster: ['.png', '.jpg', '.jpeg', '.svg'] };

function usage(message = '') {
  if (message) console.error(message);
  console.error('Usage: render_markdown.mjs [--check] --trusted-root <directory> <source.md> [output.html]');
  process.exit(2);
}

function parseArguments(argv) {
  const positional = [];
  let checkOnly = false;
  let trustedRootValue;
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === '--check') {
      if (checkOnly) usage('--check may be provided only once');
      checkOnly = true;
      continue;
    }
    if (argument === '--trusted-root') {
      if (trustedRootValue !== undefined) usage('--trusted-root may be provided only once');
      const value = argv[index + 1];
      if (!value || value.startsWith('--')) usage('--trusted-root requires a directory');
      trustedRootValue = value;
      index += 1;
      continue;
    }
    if (argument.startsWith('--')) usage(`Unknown argument: ${argument}`);
    positional.push(argument);
  }
  if (trustedRootValue === undefined) usage('--trusted-root is required for a trusted publication boundary');
  if (positional.length < 1 || positional.length > 2 || !positional[0].endsWith('.md')) usage();
  return {
    checkOnly,
    outputPath: path.resolve(positional[1] || positional[0].replace(/\.md$/u, '.html')),
    sourcePath: path.resolve(positional[0]),
    trustedRootLexical: path.resolve(trustedRootValue),
  };
}

const args = parseArguments(process.argv.slice(2));
const { checkOnly, sourcePath } = args;
let trustedRoot;
let outputPath;

function nodeRequire() {
  const prefix = process.env.PTK_NODE_PREFIX;
  return createRequire(prefix ? path.join(prefix, 'package.json') : path.join(HERE, 'package.json'));
}

async function loadModule(name) {
  const req = nodeRequire();
  let resolved;
  try {
    resolved = req.resolve(name);
  } catch (error) {
    throw new Error(`${name} is not installed under $PTK_NODE_PREFIX; run \`ptk host setup --yes\` (${error.code})`);
  }
  return import(pathToFileURL(resolved).href);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function containedPath(root, candidate) {
  const relative = path.relative(root, candidate);
  return relative !== '' && relative !== '..' && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative);
}

// Snapshot of each directory from the (realpath'd) trusted root down to `directory`. Symlinks above
// the trusted root, such as macOS /tmp -> /private/tmp, are the operator's choice; below it they fail.
async function directorySnapshot(directory, root) {
  if (directory !== root && !containedPath(root, directory)) {
    throw new Error(`output must be contained beneath the trusted root: ${root}`);
  }
  const parts = directory === root ? [] : path.relative(root, directory).split(path.sep);
  const snapshots = [];
  let current = root;
  for (const part of ['', ...parts]) {
    if (part) current = path.join(current, part);
    let metadata;
    try {
      metadata = await lstat(current);
    } catch (error) {
      if (error?.code === 'ENOENT') throw new Error(`output ancestor is missing: ${current}`);
      throw error;
    }
    if (metadata.isSymbolicLink()) throw new Error(`output path contains a symlink ancestor: ${current}`);
    if (!metadata.isDirectory()) throw new Error(`output ancestor is not a directory: ${current}`);
    snapshots.push({ device: metadata.dev, inode: metadata.ino, path: current });
  }
  return snapshots;
}

function assertSameDirectorySnapshot(expected, current) {
  if (expected.length !== current.length) throw new Error('output ancestor chain changed before publication');
  for (let index = 0; index < expected.length; index += 1) {
    const before = expected[index];
    const after = current[index];
    if (before.path !== after.path || before.device !== after.device || before.inode !== after.inode) {
      throw new Error(`output ancestor changed before publication: ${before.path}`);
    }
  }
}

async function outputLeafSnapshot(output) {
  try {
    const metadata = await lstat(output);
    if (metadata.isSymbolicLink()) throw new Error(`output leaf must not be a symlink: ${output}`);
    if (!metadata.isFile()) throw new Error(`output leaf must be a regular file when it exists: ${output}`);
    return { device: metadata.dev, inode: metadata.ino };
  } catch (error) {
    if (error?.code === 'ENOENT') return null;
    throw error;
  }
}

function assertSameLeafSnapshot(expected, current, output) {
  if (expected === null && current === null) return;
  if (expected === null || current === null || expected.device !== current.device || expected.inode !== current.inode) {
    throw new Error(`output leaf changed before publication: ${output}`);
  }
}

async function validatePublicationTarget(output, root, expected = undefined) {
  if (root === path.parse(root).root) throw new Error('trusted root must be narrower than the filesystem root');
  if (!containedPath(root, output)) throw new Error(`output must be contained beneath the trusted root: ${root}`);
  const rootSnapshot = await directorySnapshot(root, root);
  const parentSnapshot = await directorySnapshot(path.dirname(output), root);
  const leafSnapshot = await outputLeafSnapshot(output);
  const snapshot = { leafSnapshot, parentSnapshot, rootSnapshot };
  if (expected !== undefined) {
    assertSameDirectorySnapshot(expected.rootSnapshot, rootSnapshot);
    assertSameDirectorySnapshot(expected.parentSnapshot, parentSnapshot);
    assertSameLeafSnapshot(expected.leafSnapshot, leafSnapshot, output);
  }
  return snapshot;
}

function stripFrontmatter(markdown) {
  const text = markdown.replace(/\r\n?/gu, '\n');
  if (!text.startsWith('---\n')) return text;
  const end = text.indexOf('\n---\n', 4);
  return end === -1 ? text : text.slice(end + 5);
}

// SOURCE_DATE_EPOCH when set (ptk sets it from the lesson or source hash), else the same derivation
// from the source hash that ptk/host.py uses. The wall clock is never read.
function generationTimestamp(value, sourceHash) {
  let date;
  if (value) {
    date = /^\d+$/u.test(value) ? new Date(Number(value) * 1000) : new Date(value);
    if (Number.isNaN(date.valueOf())) throw new Error('SOURCE_DATE_EPOCH must be an epoch or ISO-8601 timestamp');
  } else {
    date = new Date((1577836800 + (parseInt(sourceHash.slice(0, 8), 16) % 126230400)) * 1000);
  }
  return date.toISOString();
}

function stripTags(value) {
  return value.replace(/<[^>]+>/g, '').replace(/&[^;]+;/g, ' ').trim();
}

function slug(value) {
  return value.normalize('NFKD').toLowerCase()
    .replace(/[^\p{Letter}\p{Number}\s-]/gu, '')
    .trim().replace(/[\s_-]+/g, '-') || 'section';
}

let decodeHTMLAttribute;

function decodedUrlForPolicy(value) {
  return decodeHTMLAttribute(value).replace(/[\u0000- \u007f]+/gu, '').toLowerCase();
}

function rejectedUrlReason(tag, attribute, rawValue) {
  const value = decodedUrlForPolicy(rawValue);
  if (value.startsWith('//')) return `protocol-relative ${attribute} on <${tag}>`;
  const scheme = value.match(/^([a-z][a-z0-9+.-]*):/u)?.[1];
  if (tag === 'a' && attribute === 'href') {
    if (!scheme || ['http', 'https', 'mailto', 'tel'].includes(scheme)) return null;
    return `unsupported URL scheme ${scheme} on <a>`;
  }
  if (tag === 'img' && attribute === 'src') {
    if (!scheme) return null;
    if (scheme === 'data' && /^data:image\/(?:jpeg|png);base64,[a-z0-9+/=\s]+$/iu.test(value)) return null;
    if (scheme === 'http' || scheme === 'https') return 'remote image asset';
    return `unsupported image URL scheme ${scheme}`;
  }
  if (['video', 'source', 'track'].includes(tag) || attribute === 'poster') {
    if (scheme || value.startsWith('/')) return `media ${attribute} on <${tag}> must be a local relative path`;
    return null;
  }
  if (SVG_TAGS.includes(tag) && (attribute === 'href' || attribute === 'xlink:href')) {
    return /^#[a-z0-9_.:-]+$/iu.test(value) ? null : `SVG ${attribute} on <${tag}> may only point inside the SVG (#id)`;
  }
  return null;
}

function pngContainsAnimation(buffer) {
  const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  if (buffer.length < signature.length || !buffer.subarray(0, 8).equals(signature)) return false;
  let offset = 8;
  while (offset + 12 <= buffer.length) {
    const length = buffer.readUInt32BE(offset);
    const chunkEnd = offset + 12 + length;
    if (chunkEnd > buffer.length) return false;
    if (buffer.toString('ascii', offset + 4, offset + 8) === 'acTL') return true;
    offset = chunkEnd;
  }
  return false;
}

// Resolve a local reference inside the Markdown directory, refusing escapes (also through symlinks).
async function resolveLocal(source, reasons, label) {
  const sourceDirectory = await realpath(path.dirname(sourcePath));
  let localName;
  try {
    localName = decodeURIComponent(decodeHTMLAttribute(source).split(/[?#]/u, 1)[0]);
  } catch {
    reasons.push(`${label} path is not valid URI text`);
    return null;
  }
  if (localName.includes('\0')) {
    reasons.push(`${label} path contains a null byte`);
    return null;
  }
  const unresolved = path.resolve(sourceDirectory, localName);
  if (!containedPath(sourceDirectory, unresolved)) {
    reasons.push(`${label} path escapes the Markdown source directory: ${localName}`);
    return null;
  }
  let inspected;
  try {
    inspected = await realpath(unresolved);
  } catch {
    reasons.push(`local ${label} cannot be inspected: ${localName}`);
    return null;
  }
  if (!containedPath(sourceDirectory, inspected)) {
    reasons.push(`${label} path escapes the Markdown source directory through a symlink: ${localName}`);
    return null;
  }
  return { localName, inspected };
}

const SVG_MOTION_RE = /<(?:animate|animateMotion|animateTransform|set)\b|@keyframes\b|\banimation\s*:/iu;

async function rejectedImageMotionReasons(raw) {
  const reasons = [];
  for (const match of raw.matchAll(/<img\b[^>]*\bsrc\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))/giu)) {
    const source = match[1] ?? match[2] ?? match[3];
    const policyValue = decodedUrlForPolicy(source);
    if (/^data:image\/(?:gif|webp);/u.test(policyValue)) {
      reasons.push('animated-capable data image requires a reviewed static fallback');
      continue;
    }
    if (policyValue.startsWith('data:image/png;base64,')) {
      const decodedSource = decodeHTMLAttribute(source);
      const encoded = decodedSource.slice(decodedSource.indexOf(',') + 1).replace(/\s+/gu, '');
      if (pngContainsAnimation(Buffer.from(encoded, 'base64'))) {
        reasons.push('animated PNG data image requires a reviewed static fallback');
      }
      continue;
    }
    if (/^[a-z][a-z0-9+.-]*:/u.test(policyValue) || policyValue.startsWith('//')) continue;
    const local = await resolveLocal(source, reasons, 'image');
    if (!local) continue;
    const extension = path.extname(local.localName).toLowerCase();
    if (['.gif', '.webp', '.apng'].includes(extension)) {
      reasons.push(`animated-capable local image ${extension} requires a reviewed static fallback`);
      continue;
    }
    if (!['.png', '.svg'].includes(extension)) continue;
    try {
      const bytes = await readFile(local.inspected);
      if (extension === '.png' && pngContainsAnimation(bytes)) reasons.push('animated local PNG requires a reviewed static fallback');
      if (extension === '.svg' && SVG_MOTION_RE.test(bytes.toString('utf8'))) reasons.push('animated SVG requires a reviewed static fallback');
    } catch {
      reasons.push(`local image cannot be inspected: ${local.localName}`);
    }
  }
  return [...new Set(reasons)];
}

function attributeMap(attributeText) {
  const map = new Map();
  for (const a of attributeText.matchAll(/([^\s=/>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/gu)) {
    map.set(a[1].toLowerCase(), a[2] ?? a[3] ?? a[4] ?? '');
  }
  return map;
}

// Inline SVG: static, accessible, self-contained. Every <svg> needs role="img" and a name
// (aria-label, aria-labelledby or a <title>), and any url(...) may only name an id inside it.
function rejectedSvgReasons(raw, { authored }) {
  const reasons = [];
  const lower = raw.toLowerCase();
  for (const tag of SVG_MOTION_TAGS) {
    if (new RegExp(`<${tag}\\b`, 'u').test(lower)) reasons.push('animated SVG requires a reviewed static fallback');
  }
  for (const match of raw.matchAll(/<svg\b([^<>]*)>([\s\S]*?)<\/svg>/giu)) {
    const attrs = attributeMap(match[1]);
    if (authored) {
      if (attrs.get('role') !== 'img') reasons.push('inline <svg> needs role="img"');
      const named = attrs.get('aria-label') || attrs.get('aria-labelledby') || /<title\b[^>]*>\s*\S[\s\S]*?<\/title>/iu.test(match[2]);
      if (!named) reasons.push('inline <svg> needs an accessible name (aria-label or <title>)');
    }
  }
  for (const value of raw.matchAll(/url\(\s*([^)]*)\)/giu)) {
    if (!/^['"]?#[a-z0-9_.:-]+['"]?$/iu.test(value[1].trim())) reasons.push(`SVG url() may only name an id inside the SVG: ${value[1].trim()}`);
  }
  return [...new Set(reasons)];
}

// Media: <video controls> with local files and at least one captions or subtitles track.
async function rejectedVideoReasons(raw) {
  const reasons = [];
  const videos = [...raw.matchAll(/<video\b([^<>]*)>([\s\S]*?)<\/video>/giu)];
  const openings = (raw.match(/<video\b/giu) || []).length;
  if (openings !== videos.length) reasons.push('every <video> needs a closing </video>');
  for (const tag of ['source', 'track']) {
    const outside = raw.replace(/<video\b[\s\S]*?<\/video>/giu, '');
    if (new RegExp(`<${tag}\\b`, 'iu').test(outside)) reasons.push(`<${tag}> is only allowed inside <video>`);
  }
  for (const [, attrText, inner] of videos) {
    const attrs = attributeMap(attrText);
    if (!attrs.has('controls')) reasons.push('<video> needs controls (no autoplay, no hidden playback)');
    const tracks = [...inner.matchAll(/<track\b([^<>]*)>/giu)].map((m) => attributeMap(m[1]));
    if (!tracks.some((t) => ['captions', 'subtitles'].includes((t.get('kind') || 'subtitles').toLowerCase()) && t.get('src'))) {
      reasons.push('<video> needs a captions or subtitles <track> with a src');
    }
    for (const t of tracks) {
      if (!t.get('srclang') || !t.get('label')) reasons.push('<track> needs srclang and label');
    }
    const sources = [...inner.matchAll(/<source\b([^<>]*)>/giu)].map((m) => attributeMap(m[1]));
    if (!attrs.get('src') && !sources.some((s) => s.get('src'))) reasons.push('<video> needs a src or a <source src>');
  }
  return [...new Set(reasons)];
}

// Local media files: contained, the right type, and a WebVTT body for tracks. Returns their hashes.
async function localMediaAssets(raw, reasons) {
  const assets = new Map();
  const refs = [];
  for (const match of raw.matchAll(/<(video|source|track|img)\b([^<>]*)>/giu)) {
    const tag = match[1].toLowerCase();
    const attrs = attributeMap(match[2]);
    if (attrs.get('src')) refs.push([tag, 'src', attrs.get('src')]);
    if (tag === 'video' && attrs.get('poster')) refs.push(['poster', 'poster', attrs.get('poster')]);
  }
  for (const [kind, attribute, value] of refs) {
    const policy = decodedUrlForPolicy(value);
    if (/^[a-z][a-z0-9+.-]*:/u.test(policy) || policy.startsWith('//')) continue;
    const local = await resolveLocal(value, reasons, kind === 'img' ? 'image' : 'media');
    if (!local) continue;
    const extension = path.extname(local.localName).toLowerCase();
    if (LOCAL_MEDIA[kind] && !LOCAL_MEDIA[kind].includes(extension)) {
      reasons.push(`${attribute} on <${kind === 'poster' ? 'video' : kind}> must be one of ${LOCAL_MEDIA[kind].join(', ')}: ${local.localName}`);
      continue;
    }
    const bytes = await readFile(local.inspected);
    if (kind === 'track' && !/^﻿?WEBVTT(?:[ \t]|\r?\n|$)/u.test(bytes.toString('utf8'))) {
      reasons.push(`track is not a WebVTT file: ${local.localName}`);
      continue;
    }
    if (kind === 'poster' && extension === '.svg' && SVG_MOTION_RE.test(bytes.toString('utf8'))) {
      reasons.push('animated SVG poster requires a reviewed static fallback');
    }
    assets.set(local.localName, createHash('sha256').update(bytes).digest('hex'));
  }
  return assets;
}

// A form control needs a name a screen reader can read: aria-label, or an id that a <label for> names.
function rejectedFormControlReasons(raw) {
  const reasons = [];
  const labelled = new Set([...raw.matchAll(/<label\b[^>]*\bfor\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))/giu)]
    .map((m) => m[1] ?? m[2] ?? m[3]));
  for (const match of raw.matchAll(/<(input|select|textarea|button)\b([^<>]*)>/giu)) {
    const attrs = attributeMap(match[2]);
    const tag = match[1].toLowerCase();
    if (attrs.get('aria-label') || (attrs.get('id') && labelled.has(attrs.get('id')))) continue;
    if (tag === 'button' && /<button\b[^>]*>\s*[^<\s]/iu.test(raw.slice(match.index))) continue;
    reasons.push(`<${tag}> needs an accessible name (aria-label or <label for>)`);
  }
  return [...new Set(reasons)];
}

function rejectedRawHtmlReasons(raw) {
  const allowedTags = new Set(ALLOWED_TAGS);
  const reasons = [];
  const tags = [...raw.matchAll(/<\/?([a-z][a-z0-9-]*)\b/giu)].map((match) => match[1].toLowerCase());
  const unsupported = [...new Set(tags.filter((tag) => !allowedTags.has(tag)))].sort();
  if (unsupported.length) reasons.push(`unsupported HTML tag(s): ${unsupported.join(', ')}`);
  for (const match of raw.matchAll(/<([a-z][a-z0-9-]*)\b([^<>]*)>/giu)) {
    const tag = match[1].toLowerCase();
    if (!allowedTags.has(tag)) continue;
    const allowed = new Set([...(ALLOWED_ATTRIBUTES[tag] || []), ...GLOBAL_ATTRIBUTES]);
    const names = [];
    for (const attribute of match[2].matchAll(/([^\s=/>]+)(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'=<>`]+))?/gu)) {
      const name = attribute[1].toLowerCase();
      names.push(name);
      if (!allowed.has(name)) reasons.push(`unsupported attribute ${name} on <${tag}>`);
    }
    const duplicates = [...new Set(names.filter((name, index) => names.indexOf(name) !== index))].sort();
    if (duplicates.length) reasons.push(`duplicate attribute(s) on <${tag}>: ${duplicates.join(', ')}`);
    for (const url of match[2].matchAll(/(?:^|\s)(href|src|poster|xlink:href)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))/giu)) {
      const reason = rejectedUrlReason(tag, url[1].toLowerCase(), url[2] ?? url[3] ?? url[4]);
      if (reason) reasons.push(reason);
    }
    if (tag === 'input') {
      const typeMatch = match[2].match(/\btype\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))/iu);
      const type = (typeMatch?.[1] ?? typeMatch?.[2] ?? typeMatch?.[3] ?? 'text').toLowerCase();
      if (!['checkbox', 'number', 'radio', 'range', 'text'].includes(type)) reasons.push(`unsupported input type ${type}`);
    }
    if (tag === 'th' || tag === 'td') {
      for (const alignment of match[2].matchAll(/\balign\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))/giu)) {
        const value = (alignment[1] ?? alignment[2] ?? alignment[3]).toLowerCase();
        if (!['left', 'center', 'right'].includes(value)) reasons.push(`unsupported align value ${value} on <${tag}>`);
      }
    }
    if ((tag === 'span' || tag === 'div' || tag === 'code') && /\bclass\s*=/iu.test(match[2])) {
      const cls = attributeMap(match[2]).get('class') || '';
      if (tag !== 'code' && !/^(?:task|math|math-display)$/u.test(cls)) reasons.push(`unsupported class ${cls} on <${tag}>`);
    }
  }
  if (/\son[a-z]+\s*=/iu.test(raw)) reasons.push('event-handler attributes');
  if (/\b(?:href|src|poster)\s*=\s*["']?\s*(?:javascript|vbscript):/iu.test(raw)) reasons.push('executable URL scheme');
  if (/<img\b[^>]*\bsrc\s*=\s*["']?\s*(?:https?:)?\/\//iu.test(raw)) reasons.push('remote image asset');
  return [...new Set(reasons)];
}

function urlBearingAttributes(raw) {
  const attributes = [];
  for (const tagMatch of raw.matchAll(/<([a-z][a-z0-9-]*)\b([^<>]*)>/giu)) {
    const tag = tagMatch[1].toLowerCase();
    for (const urlMatch of tagMatch[2].matchAll(/(?:^|\s)(href|src|poster|xlink:href)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))/giu)) {
      attributes.push({ attribute: urlMatch[1].toLowerCase(), tag, value: decodeHTMLAttribute(urlMatch[2] ?? urlMatch[3] ?? urlMatch[4]) });
    }
  }
  return attributes;
}

function rejectedSanitizerUrlRewriteReasons(raw, sanitized) {
  const authored = urlBearingAttributes(raw);
  const emitted = urlBearingAttributes(sanitized);
  if (authored.length !== emitted.length) return ['sanitizer-only URL-bearing attribute removal or insertion'];
  for (let index = 0; index < authored.length; index += 1) {
    const before = authored[index];
    const after = emitted[index];
    if (before.tag !== after.tag || before.attribute !== after.attribute || before.value !== after.value) {
      return [`sanitizer-only URL-bearing rewrite on <${before.tag}> ${before.attribute}`];
    }
  }
  return [];
}

// GFM task items become glyphs with the same accessible names v2 gave its checkboxes, so no form
// input is emitted that nothing can grade (D20.12: v2's renderer/validator checkbox disagreement).
function taskGlyphs(html) {
  return html
    .replace(/<input checked="" disabled="" type="checkbox">\s?/gu,
      '<span class="task" role="img" aria-label="Completed checklist item">☑</span> ')
    .replace(/<input disabled="" type="checkbox">\s?/gu,
      '<span class="task" role="img" aria-label="Incomplete checklist item">☐</span> ');
}

// ---------------------------------------------------------------- math
// $$...$$ (display) and $...$ (inline, pandoc rules: no space inside the delimiters, closing $ not
// followed by a digit). Code spans and fences are left alone; \$ is a literal dollar.
function extractMath(markdown) {
  const items = [];
  const out = [];
  let inFence = null;
  const lines = markdown.split('\n');
  let buffer = [];
  const flush = () => {
    if (buffer.length) out.push(replaceMathInText(buffer.join('\n'), items));
    buffer = [];
  };
  for (const line of lines) {
    const fence = line.match(/^ {0,3}(`{3,}|~{3,})/u);
    if (inFence) {
      out.push(line);
      if (fence && fence[1][0] === inFence[0] && fence[1].length >= inFence.length && /^\s*(`{3,}|~{3,})\s*$/u.test(line)) inFence = null;
      continue;
    }
    if (fence) {
      flush();
      inFence = fence[1];
      out.push(line);
      continue;
    }
    buffer.push(line);
  }
  flush();
  return { text: out.join('\n'), items };
}

function replaceMathInText(text, items) {
  // split on inline code spans so their content is never treated as math
  let result = '';
  const segments = [];
  const re = /(`+)([\s\S]*?[^`])\1(?!`)/gu;
  let last = 0;
  for (const m of text.matchAll(re)) {
    segments.push([false, text.slice(last, m.index)]);
    segments.push([true, m[0]]);
    last = m.index + m[0].length;
  }
  segments.push([false, text.slice(last)]);
  for (const [isCode, seg] of segments) {
    if (isCode) {
      result += seg;
      continue;
    }
    let s = seg.replace(/\$\$([\s\S]+?)\$\$/gu, (all, tex) => {
      items.push({ id: `m${items.length}`, tex: tex.trim(), display: true });
      return `\n\nPTKMATHD${items.length - 1}X\n\n`;
    });
    s = s.replace(/(^|[^\\$])\$(?=\S)([^$\n]*?\S)\$(?!\d)/gu, (all, pre, tex) => {
      items.push({ id: `m${items.length}`, tex, display: false });
      return `${pre}PTKMATHI${items.length - 1}X`;
    });
    result += s.replace(/\\\$/gu, '$');
  }
  return result;
}

function renderMath(items) {
  if (!items.length) return [];
  const tmp = mkdtempSync(path.join(process.env.TMPDIR || os.tmpdir(), 'ptk-math-'));
  try {
    writeFileSync(path.join(tmp, 'items.json'), JSON.stringify(items));
    execFileSync(process.execPath, [path.join(HERE, 'tex2svg.mjs'), path.join(tmp, 'items.json'), path.join(tmp, 'out.json')], {
      env: { ...process.env, PTK_NODE_PREFIX: process.env.PTK_NODE_PREFIX || HERE },
      stdio: ['ignore', 'ignore', 'pipe'],
      timeout: 120000,
    });
    const results = JSON.parse(readFileSync(path.join(tmp, 'out.json'), 'utf8'));
    const bad = results.filter((r) => !r.ok);
    if (bad.length) throw new Error(`TeX did not compile: ${bad.map((r) => `${items.find((i) => i.id === r.id)?.tex} (${r.error})`).join('; ')}`);
    return results;
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
}

// MathJax's own `style="vertical-align"` attribute would need 'unsafe-inline' under the CSP, so it
// becomes a class with a rule in the media style block.
function placeMath(html, items, results) {
  const classes = new Map();
  const reasons = [];
  const svgFor = (index) => {
    const r = results[index];
    let svg = r.svg;
    const va = svg.match(/^<svg style="vertical-align: (-?[\d.]+)(?:ex)?;"/u);
    if (va) {
      const name = `mjx-va${classes.has(va[1]) ? classes.get(va[1]).index : classes.size}`;
      if (!classes.has(va[1])) classes.set(va[1], { index: classes.size, name });
      svg = svg.replace(/^<svg style="vertical-align: (-?[\d.]+)(?:ex)?;"/u, `<svg class="${classes.get(va[1]).name}"`);
    }
    svg = svg.replace(/ data-[a-z-]+="[^"]*"/gu, '');
    reasons.push(...rejectedMathSvgReasons(svg));
    return svg;
  };
  const label = (tex) => escapeHtml(`TeX: ${tex}`);
  html = html.replace(/<p>PTKMATHD(\d+)X<\/p>/gu, (all, n) =>
    `<div class="math-display" role="img" aria-label="${label(items[n].tex)}">${svgFor(Number(n))}</div>`);
  html = html.replace(/PTKMATHD(\d+)X/gu, (all, n) =>
    `<span class="math-display" role="img" aria-label="${label(items[n].tex)}">${svgFor(Number(n))}</span>`);
  html = html.replace(/PTKMATHI(\d+)X/gu, (all, n) =>
    `<span class="math" role="img" aria-label="${label(items[n].tex)}">${svgFor(Number(n))}</span>`);
  const css = [...classes.entries()].map(([value, c]) => `.${c.name} { vertical-align:${value}ex; }`).join('\n');
  return { html, css: css ? `${css}\n` : '', reasons: [...new Set(reasons)] };
}

function rejectedMathSvgReasons(svg) {
  const allowed = new Set(['svg', 'defs', 'g', 'path', 'rect', 'use', 'title', 'text']);
  const reasons = [];
  for (const m of svg.matchAll(/<\/?([a-zA-Z][a-zA-Z0-9-]*)\b/gu)) {
    if (!allowed.has(m[1].toLowerCase())) reasons.push(`MathJax emitted an unexpected <${m[1]}>`);
  }
  if (/\son[a-z]+\s*=|style\s*=|javascript:/iu.test(svg)) reasons.push('MathJax output carried an unsafe attribute');
  for (const m of svg.matchAll(/(?:xlink:)?href="([^"]*)"/gu)) {
    if (!m[1].startsWith('#')) reasons.push('MathJax output referenced an outside resource');
  }
  return reasons;
}

// ---------------------------------------------------------------- page

// Chrome treats every file:// URL as its own origin, so a <track src="captions.vtt"> next to the page
// never loads when the page is opened from disk (D20.9). Each track's WebVTT is embedded as a data: URI;
// the file name stays in data-src-name and in the asset provenance.
async function inlineTracks(html) {
  const sourceDirectory = await realpath(path.dirname(sourcePath));
  const out = [];
  let last = 0;
  for (const m of html.matchAll(/<track\b([^<>]*?)\ssrc="([^"]*)"([^<>]*)>/gu)) {
    const name = decodeURIComponent(decodeHTMLAttribute(m[2]).split(/[?#]/u, 1)[0]);
    const bytes = await readFile(await realpath(path.resolve(sourceDirectory, name)));
    out.push(html.slice(last, m.index), `<track${m[1]} src="data:text/vtt;base64,${bytes.toString('base64')}"${m[3]}>`);
    last = m.index + m[0].length;
  }
  out.push(html.slice(last));
  return out.join('');
}

function enrich(raw) {
  const seen = new Map();
  let html = raw.replace(/<h([1-6])>([\s\S]*?)<\/h\1>/g, (all, level, inner) => {
    const base = slug(stripTags(inner));
    const count = seen.get(base) || 0;
    seen.set(base, count + 1);
    const id = count ? `${base}-${count + 1}` : base;
    return `<h${level} id="${escapeHtml(id)}">${inner}</h${level}>`;
  });
  html = html
    .replace(/href="([^"#?]+)\.md(#[^"]*)?"/g, 'href="$1.html$2"')
    .replace(/\b(href|src)="([^"]*)"/g, (all, attribute, value) => `${attribute}="${value.replace(/&(?!#\d+;|#x[0-9a-f]+;|[a-z][a-z0-9]+;)/gi, '&amp;')}"`)
    .replaceAll('<table>', '<div class="table-wrap" tabindex="0" role="region" aria-label="Scrollable table"><table>')
    .replaceAll('</table>', '</table></div>');
  return html;
}

function sanitizeLessonHtml(sanitizeHtml, raw) {
  return sanitizeHtml(raw, {
    allowedTags: ALLOWED_TAGS,
    allowedAttributes: ALLOWED_ATTRIBUTES,
    allowedSchemes: ['http', 'https', 'mailto', 'tel'],
    allowedSchemesByTag: { a: ['http', 'https', 'mailto', 'tel'], img: ['data'], video: [], source: [], track: [] },
    allowedSchemesAppliedToAttributes: ['href', 'src', 'cite', 'poster', 'xlink:href'],
    allowProtocolRelative: false,
    disallowedTagsMode: 'discard',
    selfClosing: ['img', 'br', 'hr', 'input', 'source', 'track'],
    enforceHtmlBoundary: true,
    nonTextTags: ['script', 'style', 'textarea', 'option', 'noscript'],
    parser: { lowerCaseAttributeNames: true, lowerCaseTags: true, recognizeSelfClosing: true },
    transformTags: {
      img: (tagName, attribs) => ({ tagName, attribs: { ...attribs, alt: attribs.alt || '' } }),
      input: (tagName, attribs) => {
        const allowedTypes = new Set(['checkbox', 'number', 'radio', 'range', 'text']);
        const type = allowedTypes.has((attribs.type || 'text').toLowerCase()) ? (attribs.type || 'text').toLowerCase() : 'text';
        return { tagName, attribs: { ...attribs, type } };
      },
    },
  });
}

async function atomicWrite(output, contents, root, initialSnapshot) {
  const temporary = path.join(
    path.dirname(output),
    `.${path.basename(output)}.${process.pid}.${createHash('sha256').update(contents).digest('hex').slice(0, 16)}.tmp`,
  );
  let handle;
  let temporaryIdentity;
  try {
    handle = await open(temporary, 'wx', 0o600);
    await handle.writeFile(contents, 'utf8');
    await handle.sync();
    const temporaryMetadata = await handle.stat();
    temporaryIdentity = { device: temporaryMetadata.dev, inode: temporaryMetadata.ino };
    await handle.close();
    handle = undefined;
    await validatePublicationTarget(output, root, initialSnapshot);
    const currentTemporary = await lstat(temporary);
    if (currentTemporary.isSymbolicLink() || !currentTemporary.isFile()
      || currentTemporary.dev !== temporaryIdentity.device || currentTemporary.ino !== temporaryIdentity.inode) {
      throw new Error('temporary render artifact changed before publication');
    }
    await rename(temporary, output);
    const published = await lstat(output);
    if (published.isSymbolicLink() || !published.isFile()
      || published.dev !== temporaryIdentity.device || published.ino !== temporaryIdentity.inode) {
      throw new Error('published render artifact failed post-publication validation');
    }
    const publishedSnapshot = await validatePublicationTarget(output, root);
    assertSameDirectorySnapshot(initialSnapshot.rootSnapshot, publishedSnapshot.rootSnapshot);
    assertSameDirectorySnapshot(initialSnapshot.parentSnapshot, publishedSnapshot.parentSnapshot);
    const directory = await open(path.dirname(output), 'r');
    try {
      const directoryMetadata = await directory.stat();
      const expectedParent = initialSnapshot.parentSnapshot.at(-1);
      if (directoryMetadata.dev !== expectedParent.device || directoryMetadata.ino !== expectedParent.inode) {
        throw new Error('output parent changed during publication');
      }
      await directory.sync();
    } finally {
      await directory.close();
    }
  } finally {
    if (handle) await handle.close();
    try {
      const currentSnapshot = await directorySnapshot(path.dirname(temporary), root);
      assertSameDirectorySnapshot(initialSnapshot.parentSnapshot, currentSnapshot);
      await unlink(temporary);
    } catch (error) {
      if (error?.code !== 'ENOENT') throw error;
    }
  }
}

function styleHash(css) {
  return `'sha256-${createHash('sha256').update(css).digest('base64')}'`;
}

async function resolveTrustedRoot() {
  try {
    trustedRoot = await realpath(args.trustedRootLexical);
  } catch {
    throw new Error(`trusted root does not exist: ${args.trustedRootLexical}`);
  }
  // Map the output under the real root when it was given through the lexical (symlinked) root.
  const lexicalRel = path.relative(args.trustedRootLexical, args.outputPath);
  outputPath = !lexicalRel.startsWith('..') && !path.isAbsolute(lexicalRel)
    ? path.join(trustedRoot, lexicalRel)
    : args.outputPath;
}

async function run() {
  await resolveTrustedRoot();
  const publicationSnapshot = await validatePublicationTarget(outputPath, trustedRoot);
  if (outputPath === sourcePath || outputPath === await realpath(sourcePath).catch(() => sourcePath)) {
    throw new Error('output path must not overwrite the Markdown source');
  }
  ({ decodeHTMLAttribute } = await loadModule('entities'));
  const sanitizeHtml = (await loadModule('sanitize-html')).default;
  const { marked } = await loadModule('marked');

  const source = await readFile(sourcePath);
  const hash = createHash('sha256').update(source).digest('hex');
  const markdown = stripFrontmatter(source.toString('utf8'));
  const titleMatch = markdown.match(/^#\s+(.+)$/m);
  const title = titleMatch ? titleMatch[1].replace(/[`*_$]/g, '').trim() : path.basename(sourcePath, '.md');
  const { text, items } = extractMath(markdown);
  marked.setOptions({ gfm: true, breaks: false });
  const parsedHtml = taskGlyphs(await marked.parse(text));
  const sanitizedHtml = sanitizeLessonHtml(sanitizeHtml, parsedHtml);
  const mediaReasons = [];
  const assets = await localMediaAssets(parsedHtml, mediaReasons);
  const rejectedReasons = [
    ...rejectedRawHtmlReasons(parsedHtml),
    ...rejectedFormControlReasons(parsedHtml),
    ...rejectedSvgReasons(parsedHtml, { authored: true }),
    ...await rejectedVideoReasons(parsedHtml),
    ...mediaReasons,
    ...await rejectedImageMotionReasons(parsedHtml),
    ...rejectedSanitizerUrlRewriteReasons(parsedHtml, sanitizedHtml),
  ];
  if (rejectedReasons.length) {
    console.error(`Render rejected unsafe or unsupported input: ${[...new Set(rejectedReasons)].join('; ')}`);
    process.exit(2);
  }
  const math = placeMath(enrich(sanitizedHtml), items, renderMath(items));
  if (math.reasons.length) {
    console.error(`Render rejected unsafe or unsupported input: ${math.reasons.join('; ')}`);
    process.exit(2);
  }
  const content = await inlineTracks(math.html);
  const mediaCss = MEDIA_CSS_BASE + math.css;
  const generatedAt = generationTimestamp(process.env.SOURCE_DATE_EPOCH, hash);
  const sourceName = path.basename(sourcePath);
  const presentation = PRESENTATION_CSS;
  const presentationHash = createHash('sha256').update(presentation).digest('hex');
  // The hashes cover each <style> element's exact text, including the template's newline and indent.
  const csp = `default-src 'none'; style-src ${styleHash(`\n${presentation}  `)} ${styleHash(`\n${mediaCss}  `)}; `
    + "img-src 'self' data:; media-src 'self' data:; font-src data:; base-uri 'none'; form-action 'none'";
  const assetList = [...assets.entries()].sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
  const assetMeta = assetList.map(([name, digest]) => `  <meta name="asset-sha256" content="${escapeHtml(name)} ${digest}">\n`).join('');
  const assetFooter = assetList.map(([name, digest]) => `    Asset ${escapeHtml(name)}: <code>${digest}</code><br>\n`).join('');

  const html = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <meta http-equiv="Content-Security-Policy" content="${csp}">
  <meta name="source-path" content="${escapeHtml(sourceName)}">
  <meta name="source-sha256" content="${hash}">
${assetMeta}  <meta name="generated-at" content="${escapeHtml(generatedAt)}">
  <meta name="renderer-version" content="${RENDERER_VERSION}">
  <meta name="template-version" content="${TEMPLATE_VERSION}">
  <meta name="presentation-sha256" content="${presentationHash}">
  <title>${escapeHtml(title)}</title>
  <style>
${presentation}  </style>
  <style>
${mediaCss}  </style>
</head>
<body>
  <a class="skip-link" href="#main-content">Skip to content</a>
  <header><div><strong>Prax Teach lesson</strong><a href="./${escapeHtml(sourceName)}">Markdown source</a></div></header>
  <main id="main-content">${content}</main>
  <footer>
    Canonical source: <a href="./${escapeHtml(sourceName)}">${escapeHtml(sourceName)}</a><br>
    SHA-256: <code>${hash}</code><br>
${assetFooter}    Generated: ${escapeHtml(generatedAt)}<br>
    Renderer: ${RENDERER_VERSION}<br>
    Template: ${TEMPLATE_VERSION}<br>
    Presentation SHA-256: <code>${presentationHash}</code>
  </footer>
</body>
</html>
`;

  if (checkOnly) {
    let current;
    try {
      current = await readFile(outputPath, 'utf8');
    } catch {
      console.error(`Missing HTML companion: ${outputPath}`);
      process.exit(1);
    }
    if (current !== html) {
      console.error(`Stale or drifted HTML companion: ${outputPath}`);
      process.exit(1);
    }
    console.log(`Fresh: ${outputPath}`);
    process.exit(0);
  }
  await atomicWrite(outputPath, html, trustedRoot, publicationSnapshot);
  console.log(`Rendered ${sourcePath} -> ${outputPath}`);
}

try {
  await run();
} catch (error) {
  console.error(`Render rejected unsafe publication or input: ${error?.message ?? String(error)}`);
  process.exitCode = 2;
}
