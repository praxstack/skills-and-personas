#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { lstat, open, readFile, realpath, rename, unlink } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { decodeHTMLAttribute } from 'entities';
import sanitizeHtml from 'sanitize-html';

const RENDERER_VERSION = 'prax-teach-markdown/2.2.0';
const TEMPLATE_VERSION = 'prax-teach-lesson/2.0.0';
const ALLOWED_TAGS = [
  'a', 'abbr', 'b', 'blockquote', 'br', 'button', 'caption', 'code', 'dd', 'del',
  'details', 'div', 'dl', 'dt', 'em', 'fieldset', 'figcaption', 'figure', 'h1', 'h2',
  'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img', 'input', 'kbd', 'li', 'mark',
  'label', 'legend', 'ol', 'option', 'p', 'pre', 's', 'samp', 'select', 'small',
  'span', 'strong', 'sub', 'summary', 'sup', 'table', 'tbody', 'td', 'textarea',
  'tfoot', 'th', 'thead', 'tr', 'u', 'ul', 'var',
];
const GLOBAL_ATTRIBUTES = [
  'aria-describedby', 'aria-label', 'dir', 'id', 'lang', 'role',
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
  '*': GLOBAL_ATTRIBUTES,
};

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
    trustedRoot: path.resolve(trustedRootValue),
  };
}

const { checkOnly, outputPath, sourcePath, trustedRoot } = parseArguments(process.argv.slice(2));

async function loadMarked() {
  try {
    return (await import('marked')).marked;
  } catch {
    const candidates = [process.env.PRAX_MARKED_PATH].filter(Boolean);
    for (const candidate of candidates) {
      try {
        return (await import(pathToFileURL(candidate).href)).marked;
      } catch {
        // Continue to the next explicitly verified renderer path.
      }
    }
  }
  throw new Error('marked is required at generation time. Install it or set PRAX_MARKED_PATH.');
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

async function directorySnapshot(directory) {
  const parsed = path.parse(directory);
  const snapshots = [];
  let current = parsed.root;
  const parts = directory.slice(parsed.root.length).split(path.sep).filter(Boolean);
  for (const part of ['', ...parts]) {
    if (part) current = path.join(current, part);
    let metadata;
    try {
      metadata = await lstat(current);
    } catch (error) {
      if (error?.code === 'ENOENT') {
        throw new Error(`output ancestor is missing: ${current}`);
      }
      throw error;
    }
    if (metadata.isSymbolicLink()) {
      throw new Error(`output path contains a symlink ancestor: ${current}`);
    }
    if (!metadata.isDirectory()) {
      throw new Error(`output ancestor is not a directory: ${current}`);
    }
    snapshots.push({ device: metadata.dev, inode: metadata.ino, path: current });
  }
  return snapshots;
}

function assertSameDirectorySnapshot(expected, current) {
  if (expected.length !== current.length) {
    throw new Error('output ancestor chain changed before publication');
  }
  for (let index = 0; index < expected.length; index += 1) {
    const before = expected[index];
    const after = current[index];
    if (
      before.path !== after.path
      || before.device !== after.device
      || before.inode !== after.inode
    ) {
      throw new Error(`output ancestor changed before publication: ${before.path}`);
    }
  }
}

async function outputLeafSnapshot(output) {
  try {
    const metadata = await lstat(output);
    if (metadata.isSymbolicLink()) {
      throw new Error(`output leaf must not be a symlink: ${output}`);
    }
    if (!metadata.isFile()) {
      throw new Error(`output leaf must be a regular file when it exists: ${output}`);
    }
    return { device: metadata.dev, inode: metadata.ino };
  } catch (error) {
    if (error?.code === 'ENOENT') return null;
    throw error;
  }
}

function assertSameLeafSnapshot(expected, current, output) {
  if (expected === null && current === null) return;
  if (
    expected === null
    || current === null
    || expected.device !== current.device
    || expected.inode !== current.inode
  ) {
    throw new Error(`output leaf changed before publication: ${output}`);
  }
}

async function validatePublicationTarget(output, root, expected = undefined) {
  if (root === path.parse(root).root) {
    throw new Error('trusted root must be narrower than the filesystem root');
  }
  if (!containedPath(root, output)) {
    throw new Error(`output must be contained beneath the trusted root: ${root}`);
  }
  const rootSnapshot = await directorySnapshot(root);
  const parentSnapshot = await directorySnapshot(path.dirname(output));
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
  if (!markdown.startsWith('---\n')) return markdown;
  const end = markdown.indexOf('\n---\n', 4);
  return end === -1 ? markdown : markdown.slice(end + 5);
}

function generationTimestamp(value) {
  if (!value) return new Date().toISOString();
  const date = /^\d+$/u.test(value) ? new Date(Number(value) * 1000) : new Date(value);
  if (Number.isNaN(date.valueOf())) throw new Error('SOURCE_DATE_EPOCH must be an epoch or ISO-8601 timestamp');
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

function decodedUrlForPolicy(value) {
  return decodeHTMLAttribute(value)
    .replace(/[\u0000-\u0020\u007f]+/gu, '')
    .toLowerCase();
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
    if (scheme === 'data' && /^data:image\/(?:jpeg|png);base64,[a-z0-9+/=\s]+$/iu.test(value)) {
      return null;
    }
    if (scheme === 'http' || scheme === 'https') return 'remote image asset';
    return `unsupported image URL scheme ${scheme}`;
  }
  return null;
}

function pngContainsAnimation(buffer) {
  const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  if (buffer.length < signature.length || !buffer.subarray(0, 8).equals(signature)) {
    return false;
  }
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

async function rejectedImageMotionReasons(raw) {
  const reasons = [];
  const sourceDirectory = await realpath(path.dirname(sourcePath));
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
      try {
        if (pngContainsAnimation(Buffer.from(encoded, 'base64'))) {
          reasons.push('animated PNG data image requires a reviewed static fallback');
        }
      } catch {
        reasons.push('invalid PNG data image');
      }
      continue;
    }
    if (/^[a-z][a-z0-9+.-]*:/u.test(policyValue) || policyValue.startsWith('//')) {
      continue;
    }
    let localName;
    try {
      const decodedSource = decodeHTMLAttribute(source);
      localName = decodeURIComponent(decodedSource.split(/[?#]/u, 1)[0]);
    } catch {
      reasons.push('image path is not valid URI text');
      continue;
    }
    if (localName.includes('\0')) {
      reasons.push('image path contains a null byte');
      continue;
    }
    const unresolvedLocal = path.resolve(sourceDirectory, localName);
    if (!containedPath(sourceDirectory, unresolvedLocal)) {
      reasons.push(`image path escapes the Markdown source directory: ${localName}`);
      continue;
    }
    let inspectedLocal;
    try {
      inspectedLocal = await realpath(unresolvedLocal);
    } catch {
      reasons.push(`local image cannot be inspected: ${localName}`);
      continue;
    }
    if (!containedPath(sourceDirectory, inspectedLocal)) {
      reasons.push(`image path escapes the Markdown source directory through a symlink: ${localName}`);
      continue;
    }
    const extension = path.extname(localName).toLowerCase();
    if (['.gif', '.webp', '.apng'].includes(extension)) {
      reasons.push(`animated-capable local image ${extension} requires a reviewed static fallback`);
      continue;
    }
    if (!['.png', '.svg'].includes(extension)) continue;
    try {
      const bytes = await readFile(inspectedLocal);
      if (extension === '.png' && pngContainsAnimation(bytes)) {
        reasons.push('animated local PNG requires a reviewed static fallback');
      }
      if (
        extension === '.svg'
        && /<(?:animate|animateMotion|animateTransform|set)\b|@keyframes\b|\banimation\s*:/iu.test(bytes.toString('utf8'))
      ) {
        reasons.push('animated SVG requires a reviewed static fallback');
      }
    } catch {
      reasons.push(`local image cannot be inspected: ${localName}`);
    }
  }
  return [...new Set(reasons)];
}

function rejectedRawHtmlReasons(raw) {
  const allowedTags = new Set(ALLOWED_TAGS);
  const reasons = [];
  const tags = [...raw.matchAll(/<\/?([a-z][a-z0-9-]*)\b/giu)].map((match) => match[1].toLowerCase());
  const unsupported = [...new Set(tags.filter((tag) => !allowedTags.has(tag)))].sort();
  if (unsupported.length) reasons.push(`unsupported HTML tag(s): ${unsupported.join(', ')}`);

  // Sanitization is defense in depth, not an implicit authoring transform.
  // Reject attributes that the sanitizer would discard so a meaning-bearing
  // construct can never disappear without a diagnostic.
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
    for (const url of match[2].matchAll(/\b(href|src)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))/giu)) {
      const reason = rejectedUrlReason(tag, url[1].toLowerCase(), url[2] ?? url[3] ?? url[4]);
      if (reason) reasons.push(reason);
    }
    if (tag === 'input') {
      const typeMatch = match[2].match(/\btype\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))/iu);
      const type = (typeMatch?.[1] ?? typeMatch?.[2] ?? typeMatch?.[3] ?? 'text').toLowerCase();
      if (!['checkbox', 'number', 'radio', 'range', 'text'].includes(type)) {
        reasons.push(`unsupported input type ${type}`);
      }
    }
    if (tag === 'th' || tag === 'td') {
      for (const alignment of match[2].matchAll(/\balign\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))/giu)) {
        const value = (alignment[1] ?? alignment[2] ?? alignment[3]).toLowerCase();
        if (!['left', 'center', 'right'].includes(value)) {
          reasons.push(`unsupported align value ${value} on <${tag}>`);
        }
      }
    }
  }
  if (/\son[a-z]+\s*=/iu.test(raw)) reasons.push('event-handler attributes');
  if (/\b(?:href|src)\s*=\s*["']?\s*(?:javascript|vbscript):/iu.test(raw)) {
    reasons.push('executable URL scheme');
  }
  if (/<img\b[^>]*\bsrc\s*=\s*["']?\s*(?:https?:)?\/\//iu.test(raw)) {
    reasons.push('remote image asset');
  }
  return [...new Set(reasons)];
}

function urlBearingAttributes(raw) {
  const attributes = [];
  for (const tagMatch of raw.matchAll(/<([a-z][a-z0-9-]*)\b([^<>]*)>/giu)) {
    const tag = tagMatch[1].toLowerCase();
    for (const urlMatch of tagMatch[2].matchAll(/\b(href|src)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))/giu)) {
      attributes.push({
        attribute: urlMatch[1].toLowerCase(),
        tag,
        value: decodeHTMLAttribute(urlMatch[2] ?? urlMatch[3] ?? urlMatch[4]),
      });
    }
  }
  return attributes;
}

function rejectedSanitizerUrlRewriteReasons(raw, sanitized) {
  const authored = urlBearingAttributes(raw);
  const emitted = urlBearingAttributes(sanitized);
  if (authored.length !== emitted.length) {
    return ['sanitizer-only URL-bearing attribute removal or insertion'];
  }
  for (let index = 0; index < authored.length; index += 1) {
    const before = authored[index];
    const after = emitted[index];
    if (
      before.tag !== after.tag
      || before.attribute !== after.attribute
      || before.value !== after.value
    ) {
      return [`sanitizer-only URL-bearing rewrite on <${before.tag}> ${before.attribute}`];
    }
  }
  return [];
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

function sanitizeLessonHtml(raw) {
  return sanitizeHtml(raw, {
    allowedTags: ALLOWED_TAGS,
    allowedAttributes: ALLOWED_ATTRIBUTES,
    allowedSchemes: ['http', 'https', 'mailto', 'tel'],
    allowedSchemesByTag: {
      a: ['http', 'https', 'mailto', 'tel'],
      img: ['data'],
    },
    allowProtocolRelative: false,
    disallowedTagsMode: 'discard',
    enforceHtmlBoundary: true,
    nonTextTags: ['script', 'style', 'textarea', 'option', 'noscript'],
    parser: { lowerCaseAttributeNames: true, lowerCaseTags: true },
    transformTags: {
      a: (tagName, attribs) => ({ tagName, attribs }),
      img: (tagName, attribs) => ({
        tagName,
        attribs: { ...attribs, alt: attribs.alt || '' },
      }),
      input: (tagName, attribs) => {
        const allowedTypes = new Set(['checkbox', 'number', 'radio', 'range', 'text']);
        const type = allowedTypes.has((attribs.type || 'text').toLowerCase())
          ? (attribs.type || 'text').toLowerCase()
          : 'text';
        const normalized = { ...attribs, type };
        // GFM task-list checkboxes are disabled presentation controls.  Give
        // them an explicit accessible name without masking missing labels on
        // real interactive inputs, which the workspace validator rejects.
        if (type === 'checkbox' && Object.hasOwn(attribs, 'disabled') && !attribs['aria-label']) {
          normalized['aria-label'] = Object.hasOwn(attribs, 'checked')
            ? 'Completed checklist item'
            : 'Incomplete checklist item';
        }
        return { tagName, attribs: normalized };
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
    temporaryIdentity = {
      device: temporaryMetadata.dev,
      inode: temporaryMetadata.ino,
    };
    await handle.close();
    handle = undefined;
    await validatePublicationTarget(output, root, initialSnapshot);
    const currentTemporary = await lstat(temporary);
    if (
      currentTemporary.isSymbolicLink()
      || !currentTemporary.isFile()
      || currentTemporary.dev !== temporaryIdentity.device
      || currentTemporary.ino !== temporaryIdentity.inode
    ) {
      throw new Error('temporary render artifact changed before publication');
    }
    await rename(temporary, output);
    const published = await lstat(output);
    if (
      published.isSymbolicLink()
      || !published.isFile()
      || published.dev !== temporaryIdentity.device
      || published.ino !== temporaryIdentity.inode
    ) {
      throw new Error('published render artifact failed post-publication validation');
    }
    const publishedSnapshot = await validatePublicationTarget(output, root);
    assertSameDirectorySnapshot(initialSnapshot.rootSnapshot, publishedSnapshot.rootSnapshot);
    assertSameDirectorySnapshot(initialSnapshot.parentSnapshot, publishedSnapshot.parentSnapshot);
    const directory = await open(path.dirname(output), 'r');
    try {
      const directoryMetadata = await directory.stat();
      const expectedParent = initialSnapshot.parentSnapshot.at(-1);
      if (
        directoryMetadata.dev !== expectedParent.device
        || directoryMetadata.ino !== expectedParent.inode
      ) {
        throw new Error('output parent changed during publication');
      }
      await directory.sync();
    } finally {
      await directory.close();
    }
  } finally {
    if (handle) await handle.close();
    try {
      const currentSnapshot = await directorySnapshot(path.dirname(temporary));
      assertSameDirectorySnapshot(initialSnapshot.parentSnapshot, currentSnapshot);
      await unlink(temporary);
    } catch (error) {
      if (error?.code !== 'ENOENT') throw error;
    }
  }
}

async function run() {
const publicationSnapshot = await validatePublicationTarget(outputPath, trustedRoot);
if (outputPath === sourcePath) {
  throw new Error('output path must not overwrite the Markdown source');
}
const source = await readFile(sourcePath);
const hash = createHash('sha256').update(source).digest('hex');

const markdown = stripFrontmatter(source.toString('utf8'));
const titleMatch = markdown.match(/^#\s+(.+)$/m);
const title = titleMatch ? titleMatch[1].replace(/[`*_]/g, '').trim() : path.basename(sourcePath, '.md');
const marked = await loadMarked();
marked.setOptions({ gfm: true, breaks: false });
const parsedHtml = await marked.parse(markdown);
const sanitizedHtml = sanitizeLessonHtml(parsedHtml);
const rejectedReasons = [
  ...rejectedRawHtmlReasons(parsedHtml),
  ...await rejectedImageMotionReasons(parsedHtml),
  ...rejectedSanitizerUrlRewriteReasons(parsedHtml, sanitizedHtml),
];
if (rejectedReasons.length) {
  console.error(`Render rejected unsafe or unsupported input: ${rejectedReasons.join('; ')}`);
  process.exit(2);
}
const content = enrich(sanitizedHtml);
const generatedAt = generationTimestamp(process.env.SOURCE_DATE_EPOCH);
const sourceName = path.basename(sourcePath);

const html = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <meta name="source-path" content="${escapeHtml(sourceName)}">
  <meta name="source-sha256" content="${hash}">
  <meta name="generated-at" content="${escapeHtml(generatedAt)}">
  <meta name="renderer-version" content="${RENDERER_VERSION}">
  <meta name="template-version" content="${TEMPLATE_VERSION}">
  <title>${escapeHtml(title)}</title>
  <style>
    :root { color-scheme: light; --paper:#f7f3ea; --ink:#172235; --muted:#5d6674; --accent:#8f3b20; --teal:#176b69; --line:#d7cbb8; --surface:#fffdf8; --code:#1c2837; --code-ink:#f4f1ea; }
    @media (prefers-color-scheme: dark) { :root { color-scheme: dark; --paper:#111923; --ink:#edf2f5; --muted:#b4bdc8; --accent:#f19a72; --teal:#72cbc5; --line:#344355; --surface:#182331; --code:#09111a; --code-ink:#edf2f5; } }
    * { box-sizing:border-box; }
    html { scroll-behavior:smooth; }
    body { margin:0; background:var(--paper); color:var(--ink); font:17px/1.68 ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
    a { color:var(--accent); text-underline-offset:.16em; }
    a:focus-visible, [tabindex="0"]:focus-visible, summary:focus-visible { outline:3px solid var(--teal); outline-offset:3px; }
    .skip-link { position:fixed; left:1rem; top:.7rem; transform:translateY(-180%); z-index:10; padding:.6rem .85rem; border-radius:.4rem; background:var(--ink); color:var(--paper); }
    .skip-link:focus { transform:translateY(0); }
    header { border-bottom:1px solid var(--line); background:var(--surface); }
    header div, main, footer { width:min(840px, calc(100% - 2rem)); margin-inline:auto; }
    header div { display:flex; justify-content:space-between; gap:1rem; padding:1rem 0; }
    header strong { color:var(--teal); letter-spacing:.04em; }
    main { padding:clamp(2.4rem,7vw,5rem) 0; }
    h1,h2,h3,h4 { font-family:ui-serif,Georgia,Cambria,serif; line-height:1.15; text-wrap:balance; scroll-margin-top:2rem; }
    h1 { max-width:16ch; margin:0 0 1.5rem; font-size:clamp(2.5rem,8vw,4.8rem); letter-spacing:-.04em; }
    h2 { margin:3.2rem 0 1rem; font-size:clamp(1.7rem,4vw,2.4rem); }
    h3 { margin:2.1rem 0 .6rem; font-size:1.35rem; }
    p,li { max-width:72ch; }
    blockquote { margin:1.4rem 0; padding:.75rem 1.1rem; border-left:.3rem solid var(--accent); background:var(--surface); }
    code { overflow-wrap:anywhere; padding:.1em .3em; border:1px solid var(--line); border-radius:.3rem; font: .88em/1.4 ui-monospace,SFMono-Regular,Menlo,monospace; }
    pre { overflow:auto; padding:1rem 1.1rem; border-radius:.65rem; background:var(--code); color:var(--code-ink); }
    pre code { overflow-wrap:normal; padding:0; border:0; color:inherit; }
    .table-wrap { overflow:auto; margin:1.4rem 0; border:1px solid var(--line); border-radius:.65rem; }
    table { width:100%; border-collapse:collapse; background:var(--surface); font-size:.92rem; }
    th,td { padding:.72rem .8rem; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }
    th { font-size:.78rem; text-transform:uppercase; letter-spacing:.03em; }
    details { margin:1rem 0; padding:.75rem 1rem; border:1px solid var(--line); border-radius:.6rem; background:var(--surface); }
    summary { cursor:pointer; font-weight:700; }
    footer { padding:1.2rem 0 2.5rem; border-top:1px solid var(--line); color:var(--muted); font-size:.78rem; overflow-wrap:anywhere; }
    @media (prefers-reduced-motion:reduce) { html { scroll-behavior:auto; } *,*::before,*::after { animation-duration:.01ms!important; transition-duration:.01ms!important; } }
    @media print { :root { --paper:#fff; --ink:#000; --surface:#fff; --line:#aaa; } header,.skip-link { display:none; } body { font-size:10.5pt; } main,footer { width:100%; } h1 { max-width:none; font-size:28pt; } pre,table,blockquote { break-inside:avoid; } details > *:not(summary),details::details-content { display:block!important; content-visibility:visible!important; } a[href^="http"]::after { content:" (" attr(href) ")"; font-size:8pt; } }
  </style>
</head>
<body>
  <a class="skip-link" href="#main-content">Skip to content</a>
  <header><div><strong>Prax Teach lesson</strong><a href="./${escapeHtml(sourceName)}">Markdown source</a></div></header>
  <main id="main-content">${content}</main>
  <footer>
    Canonical source: <a href="./${escapeHtml(sourceName)}">${escapeHtml(sourceName)}</a><br>
    SHA-256: <code>${hash}</code><br>
    Generated: ${escapeHtml(generatedAt)}<br>
    Renderer: ${RENDERER_VERSION}<br>
    Template: ${TEMPLATE_VERSION}
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
