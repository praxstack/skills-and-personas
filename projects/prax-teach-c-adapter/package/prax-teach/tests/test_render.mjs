// AC-8.3: the ported renderer (node/render_markdown.mjs). Run by tests/test_render.py under Node 22
// and Node 24 with PTK_NODE_PREFIX set by ptk/node.py.
//
// Part 1 is v2's render_markdown.test.mjs (tests 2 to 22), ported: paths, the version strings, and the
// copied-renderer test now copies tex2svg.mjs instead of linking node_modules (one module path, E28).
// v2's test 1 (render_all.mjs bulk rendering of evidence snapshots) is removed: see plan/PROTECTED-MAP.md.
// Part 2 is new: test_svg_math_video and the v2.1 fixes (E2, E16, E24, D20.9, D20.12).
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import {
  mkdir,
  mkdtemp,
  readFile,
  realpath,
  stat,
  symlink,
  writeFile,
} from "node:fs/promises";
import { createRequire } from "node:module";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const NODE_DIR = path.join(ROOT, "node");
const RENDERER = path.join(NODE_DIR, "render_markdown.mjs");
const TMP = process.env.PTK_TEST_TMP || os.tmpdir();
assert.ok(process.env.PTK_NODE_PREFIX, "run through tests/test_render.py (PTK_NODE_PREFIX)");

function runRaw(args, expected = 0, env = {}) {
  const completed = spawnSync(process.execPath, [RENDERER, ...args], {
    cwd: ROOT,
    encoding: "utf8",
    env: { ...process.env, SOURCE_DATE_EPOCH: "1785844800", ...env },
  });
  assert.equal(
    completed.status,
    expected,
    `stdout:\n${completed.stdout}\nstderr:\n${completed.stderr}`,
  );
  return completed;
}

function run(args, expected = 0, trustedRoot = undefined, env = {}) {
  const source = args.find((argument) => argument.endsWith(".md"));
  assert.ok(source, "test invocation must identify its Markdown source");
  return runRaw(
    ["--trusted-root", trustedRoot || path.dirname(source), ...args],
    expected,
    env,
  );
}

async function temporaryDirectory(prefix) {
  return realpath(await mkdtemp(path.join(TMP, prefix)));
}

// ---------------------------------------------------------------- part 1: v2's tests, ported

test("renderer requires an explicit trusted root", async () => {
  const directory = await temporaryDirectory("prax-render-root-required-");
  const markdown = path.join(directory, "lesson.md");
  const htmlPath = path.join(directory, "lesson.html");
  await writeFile(markdown, "# Explicit root\n", "utf8");

  const rejected = runRaw([markdown, htmlPath], 2);
  assert.match(rejected.stderr, /trusted-root.*required|requires.*trusted root/i);
  await assert.rejects(stat(htmlPath));
});

test("renderer confines publication and rejects symlink leaves and ancestors", async () => {
  const directory = await temporaryDirectory("prax-render-paths-");
  const markdown = path.join(directory, "lesson.md");
  await writeFile(markdown, "# Contained publication\n", "utf8");

  const outside = await temporaryDirectory("prax-render-outside-");
  const outsideOutput = path.join(outside, "lesson.html");
  const escaped = run([markdown, outsideOutput], 2, directory);
  assert.match(escaped.stderr, /outside.*trusted root|contained.*trusted root/i);
  await assert.rejects(stat(outsideOutput));

  const protectedTarget = path.join(directory, "protected.txt");
  await writeFile(protectedTarget, "do not replace\n", "utf8");
  const linkedLeaf = path.join(directory, "linked.html");
  await symlink(protectedTarget, linkedLeaf);
  const existingLink = run([markdown, linkedLeaf], 2, directory);
  assert.match(existingLink.stderr, /symlink.*leaf|leaf.*symlink/i);
  assert.equal(await readFile(protectedTarget, "utf8"), "do not replace\n");

  const danglingLeaf = path.join(directory, "dangling.html");
  await symlink(path.join(directory, "missing-target.html"), danglingLeaf);
  const dangling = run([markdown, danglingLeaf], 2, directory);
  assert.match(dangling.stderr, /symlink.*leaf|leaf.*symlink/i);

  const realAncestor = path.join(directory, "real-output");
  const linkedAncestor = path.join(directory, "linked-output");
  await mkdir(realAncestor);
  await symlink(realAncestor, linkedAncestor);
  const throughAncestor = run(
    [markdown, path.join(linkedAncestor, "lesson.html")],
    2,
    directory,
  );
  assert.match(throughAncestor.stderr, /symlink.*ancestor|ancestor.*symlink/i);
  await assert.rejects(stat(path.join(realAncestor, "lesson.html")));
});

test("renderer rejects hostile HTML instead of silently omitting it", async () => {
  const directory = await temporaryDirectory("prax-render-hostile-");
  const markdown = path.join(directory, "lesson.md");
  const htmlPath = path.join(directory, "lesson.html");
  const source = `# Safe lesson

<script>alert("owned")</script>
<iframe src="https://example.invalid/tracker"></iframe>
<img src="https://example.invalid/pixel.png" onerror="alert(1)" alt="Remote pixel">
<a href="javascript:alert(1)" onclick="alert(2)">unsafe link</a>

`;
  await writeFile(markdown, source, "utf8");
  const rejected = run([markdown, htmlPath], 2);
  assert.match(rejected.stderr, /rejected.*unsupported|unsafe/iu);
  await assert.rejects(stat(htmlPath));
});

test("renderer preserves safe native teaching semantics and fallbacks", async () => {
  const directory = await temporaryDirectory("prax-render-safe-");
  const markdown = path.join(directory, "lesson.md");
  const htmlPath = path.join(directory, "lesson.html");
  const source = `# Safe lesson

<details>
<summary>Hint 1</summary>

Compare the two cases before revealing the rule.

</details>

| Case | Move |
| --- | --- |
| A | Predict |

[Official source](https://example.com/reference)
`;
  await writeFile(markdown, source, "utf8");
  run([markdown, htmlPath]);
  const html = await readFile(htmlPath, "utf8");
  assert.match(html, /<details>/);
  assert.match(html, /<summary>Hint 1<\/summary>/);
  assert.match(html, /href="https:\/\/example\.com\/reference"/);
  assert.match(html, /class="table-wrap" tabindex="0" role="region"/);
  assert.match(html, /@media \(prefers-reduced-motion:reduce\)/);
  assert.match(html, /@media print/);
  assert.match(html, /details::details-content \{ display:block!important/);
  assert.match(html, /<header>/);
  assert.match(html, /<main id="main-content">/);
  assert.match(html, /<footer>/);
  assert.match(html, /renderer-version" content="prax-teach-markdown\/2\.3\.0"/);
  assert.match(html, /template-version" content="prax-teach-lesson\/3\.1\.0"/);
  assert.match(html, /generated-at" content="2026-08-04T12:00:00\.000Z"/);
});

test("renderer preserves bounded GFM table alignment", async () => {
  const directory = await temporaryDirectory("prax-render-alignment-");
  const markdown = path.join(directory, "lesson.md");
  const htmlPath = path.join(directory, "lesson.html");
  await writeFile(
    markdown,
    "# Trace\n\n| Step | Value |\n| ---: | :--- |\n| 1 | start |\n",
    "utf8",
  );
  run([markdown, htmlPath]);
  const html = await readFile(htmlPath, "utf8");
  assert.match(html, /<th align="right">Step<\/th>/);
  assert.match(html, /<th align="left">Value<\/th>/);
  assert.match(html, /<td align="right">1<\/td>/);
});

test("renderer rejects table alignment values outside the bounded set", async () => {
  const directory = await temporaryDirectory("prax-render-bad-alignment-");
  const markdown = path.join(directory, "lesson.md");
  const htmlPath = path.join(directory, "lesson.html");
  await writeFile(
    markdown,
    '# Trace\n\n<table><tr><th align="justify">Step</th></tr></table>\n',
    "utf8",
  );
  const rejected = run([markdown, htmlPath], 2);
  assert.match(rejected.stderr, /unsupported align value justify on <th>/i);
  await assert.rejects(stat(htmlPath));
});

test("renderer rejects unsupported attributes instead of silently stripping them", async () => {
  const directory = await temporaryDirectory("prax-render-attribute-");
  const markdown = path.join(directory, "lesson.md");
  const htmlPath = path.join(directory, "lesson.html");
  await writeFile(markdown, '# Lesson\n\n<p style="display:none">Hidden meaning</p>\n', "utf8");
  const rejected = run([markdown, htmlPath], 2);
  assert.match(rejected.stderr, /unsupported attribute style on <p>/i);
  await assert.rejects(stat(htmlPath));
});

test("renderer rejects encoded or sanitizer-only URL and control rewrites", async () => {
  const directory = await temporaryDirectory("prax-render-policy-");
  for (const [name, fragment] of [
    ["encoded-scheme", '<a href="jav&#x61;script:alert(1)">unsafe</a>'],
    ["named-entity-scheme", '<a href="java&Tab;script&colon;alert(1)">unsafe</a>'],
    ["named-protocol-relative", '<img src="&sol;&sol;example.invalid/a.png" alt="unsafe">'],
    ["protocol-relative", '<a href="//example.invalid/path">ambiguous</a>'],
    ["unsafe-data-image", '<img src="data:image/svg+xml;base64,PHN2Zz4=" alt="unsafe">'],
    ["rewritten-input", '<input aria-label="Secret" type="password">'],
  ]) {
    const markdown = path.join(directory, `${name}.md`);
    const htmlPath = path.join(directory, `${name}.html`);
    await writeFile(markdown, `# Policy\n\n${fragment}\n`, "utf8");
    const rejected = run([markdown, htmlPath], 2);
    assert.match(rejected.stderr, /rejected.*(?:scheme|protocol|image|input)/iu);
    await assert.rejects(stat(htmlPath));
  }
});

test("renderer rejects animated-capable images without a reviewed static fallback", async () => {
  const directory = await temporaryDirectory("prax-render-motion-");
  const gif = path.join(directory, "moving.gif");
  await writeFile(gif, Buffer.from("GIF89a", "ascii"));

  const cases = [
    ["local-gif", "![Changing state](./moving.gif)"],
    [
      "data-gif",
      "![Changing state](data:image/gif;base64,R0lGODlhAQABAAAAACw=)",
    ],
  ];
  for (const [name, fragment] of cases) {
    const markdown = path.join(directory, `${name}.md`);
    const htmlPath = path.join(directory, `${name}.html`);
    await writeFile(markdown, `# Motion policy\n\n${fragment}\n`, "utf8");
    const rejected = run([markdown, htmlPath], 2);
    assert.match(rejected.stderr, /animated-capable|static fallback/iu);
    await assert.rejects(stat(htmlPath));
  }
});

test("renderer confines decoded local image inspection to the Markdown directory", async () => {
  const directory = await temporaryDirectory("prax-render-local-image-");
  const sourceDirectory = path.join(directory, "source");
  await mkdir(sourceDirectory);
  const outsidePng = path.join(directory, "outside.png");
  await writeFile(outsidePng, Buffer.from("not an animated PNG", "utf8"));

  for (const [name, reference] of [
    ["percent-escape", "%2e%2e/outside.png"],
    ["entity-escape", "&period;&period;&sol;outside.png"],
  ]) {
    const markdown = path.join(sourceDirectory, `${name}.md`);
    const htmlPath = path.join(sourceDirectory, `${name}.html`);
    await writeFile(markdown, `# Local image\n\n![Prompt](${reference})\n`, "utf8");
    const rejected = run([markdown, htmlPath], 2, sourceDirectory);
    assert.match(rejected.stderr, /image.*(?:escapes|outside).*source directory/i);
    await assert.rejects(stat(htmlPath));
  }

  const outsideSvg = path.join(directory, "outside.svg");
  await writeFile(
    outsideSvg,
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><path d="M0 0h10v10z"/></svg>\n',
    "utf8",
  );
  const linkedSvg = path.join(sourceDirectory, "linked.svg");
  await symlink(outsideSvg, linkedSvg);
  const markdown = path.join(sourceDirectory, "symlink-image.md");
  const htmlPath = path.join(sourceDirectory, "symlink-image.html");
  await writeFile(markdown, "# Local image\n\n![Prompt](linked.svg)\n", "utf8");
  const rejected = run([markdown, htmlPath], 2, sourceDirectory);
  assert.match(rejected.stderr, /image.*(?:escapes|symlink|outside).*source directory/i);
  await assert.rejects(stat(htmlPath));
});

test("rendering is byte deterministic and check detects any drift, not only stale source hash", async () => {
  const directory = await temporaryDirectory("prax-render-deterministic-");
  const markdown = path.join(directory, "lesson.md");
  const one = path.join(directory, "one.html");
  const two = path.join(directory, "two.html");
  const source = "# Deterministic lesson\n\n## Attempt\n\nTry first.\n";
  await writeFile(markdown, source, "utf8");
  run([markdown, one]);
  run([markdown, two]);
  assert.deepEqual(await readFile(one), await readFile(two));
  const digest = createHash("sha256").update(source).digest("hex");
  assert.match(await readFile(one, "utf8"), new RegExp(`source-sha256" content="${digest}`));
  run(["--check", markdown, one]);

  const tampered = (await readFile(one, "utf8")).replace("Try first.", "Skip the attempt.");
  await writeFile(one, tampered, "utf8");
  const failed = run(["--check", markdown, one], 1);
  assert.match(failed.stderr, /drift|stale|mismatch/i);
});

test("frontmatter is excluded and Markdown links become local HTML companion links", async () => {
  const directory = await temporaryDirectory("prax-render-links-");
  const markdown = path.join(directory, "lesson.md");
  const htmlPath = path.join(directory, "lesson.html");
  await writeFile(
    markdown,
    "---\nname: hidden-frontmatter\ndescription: Hidden metadata.\n---\n\n# Visible lesson\n\n[Next](./next.md#attempt)\n",
    "utf8",
  );
  run([markdown, htmlPath]);
  const html = await readFile(htmlPath, "utf8");
  assert.doesNotMatch(html, /hidden-frontmatter/);
  assert.match(html, /href="\.\/next\.html#attempt"/);
  assert.match(html, /<title>Visible lesson<\/title>/);
});

test("native form controls preserve explicit accessible labels", async () => {
  const directory = await temporaryDirectory("prax-render-controls-");
  const markdown = path.join(directory, "lesson.md");
  const htmlPath = path.join(directory, "lesson.html");
  await writeFile(
    markdown,
    '# Practice\n\n<label for="prediction">Your prediction</label>\n<input id="prediction" name="prediction" type="text" value="">\n',
    "utf8",
  );
  run([markdown, htmlPath]);
  const html = await readFile(htmlPath, "utf8");
  assert.match(html, /<label for="prediction">Your prediction<\/label>/);
  assert.match(html, /<input id="prediction" name="prediction" type="text" \/>/);
});

test("generated task-list checkboxes receive accessible state labels", async () => {
  const directory = await temporaryDirectory("prax-render-tasks-");
  const markdown = path.join(directory, "lesson.md");
  const htmlPath = path.join(directory, "lesson.html");
  await writeFile(markdown, "# Checklist\n\n- [ ] Retrieve it\n- [x] Explain it\n", "utf8");
  run([markdown, htmlPath]);
  const html = await readFile(htmlPath, "utf8");
  assert.match(html, /aria-label="Incomplete checklist item"/);
  assert.match(html, /aria-label="Completed checklist item"/);
});


test("AskTheMove presentation is embedded, portable and preserves semantic voices", async () => {
  const directory = await temporaryDirectory("prax-render-coach-");
  const markdown = path.join(directory, "ratios.md");
  const htmlPath = path.join(directory, "ratios.html");
  const source = `# Ratios

The ratio stays constant when both quantities double.

> A quoted definition stays in the book voice.

<div role="note" aria-label="Coach note"><p>Coach note: compare the same two objects.</p></div>
<div role="note" aria-label="Correction"><p>Correction: changing only one quantity changes the ratio.</p></div>

\`a / b\` remains exact technical text.

| State | A | B |
| --- | --- | --- |
| Start | 2 | 3 |
| Both doubled | 4 | 6 |
`;
  await writeFile(markdown, source, "utf8");
  run([markdown, htmlPath]);
  const html = await readFile(htmlPath, "utf8");
  const css = html.match(/<style>\n([\s\S]*?)  <\/style>/)?.[1];
  assert.ok(css, "standalone output embeds the complete presentation");
  const cssHash = createHash("sha256").update(css).digest("hex");
  assert.equal(cssHash, "f7673d0d7da7396446955dcb087de0e23be6793d681731a5c3ef75bdbb45f241", "portable renderer retains the exact reviewed CSS bytes");
  assert.ok(html.includes(`name="presentation-sha256" content="${cssHash}"`));
  assert.ok(html.includes(`Presentation SHA-256: <code>${cssHash}</code>`));
  for (const color of ["#fbfaf4", "#171d29", "#1f48ae", "#c92324"]) {
    assert.ok(html.includes(color), `default semantic color ${color} is present`);
  }
  assert.match(html, /font:18px\/1\.65 var\(--book\)/);
  assert.match(html, /\[role="note"\] \{[^}]*color:var\(--blue\)[^}]*var\(--coach\)/);
  assert.match(html, /\[role="note"\]\[aria-label="Correction"\] \{[^}]*color:var\(--red\)/);
  assert.match(html, /blockquote \{[^}]*font-family:var\(--book\)/);
  assert.match(html, /code,kbd,samp \{[^}]*font-family:var\(--technical\)/);
  assert.match(html, /<div role="note" aria-label="Coach note">/);
  assert.match(html, /<div role="note" aria-label="Correction">/);
  assert.match(html, /<code>a \/ b<\/code>/);
  assert.match(html, /source-sha256" content="[a-f0-9]{64}"/);
  assert.match(html, /prefers-color-scheme: dark/);
  assert.match(html, /prefers-contrast:more/);
  assert.match(html, /forced-colors:active/);
  assert.match(html, /prefers-reduced-motion:reduce/);
  assert.doesNotMatch(html, /<script|<link|@import|url\(/i);
  const moved = await temporaryDirectory("prax-render-moved-");
  await writeFile(path.join(moved, "ratios.md"), source, "utf8");
  await writeFile(path.join(moved, "ratios.html"), html, "utf8");
  run(["--check", path.join(moved, "ratios.md"), path.join(moved, "ratios.html")]);
});


test("copied renderer publishes current HTML without companion asset directories", async () => {
  const directory = await temporaryDirectory("prax-render-copy-");
  const scripts = path.join(directory, "scripts");
  await mkdir(scripts);
  const copiedRenderer = path.join(scripts, "render_markdown.mjs");
  await writeFile(copiedRenderer, await readFile(RENDERER));
  await writeFile(path.join(scripts, "tex2svg.mjs"), await readFile(path.join(NODE_DIR, "tex2svg.mjs")));
  const source = path.join(directory, "lesson.md");
  await writeFile(source, "# Portable current lesson\n\nBoth quantities double.\n");
  const args = [copiedRenderer, "--trusted-root", directory, source];
  for (const check of [false, true]) {
    const completed = spawnSync(process.execPath, check ? [args[0], "--check", ...args.slice(1)] : args, {
      cwd: directory,
      encoding: "utf8",
      env: { ...process.env, SOURCE_DATE_EPOCH: "1785844800" },
    });
    assert.equal(completed.status, 0, completed.stderr);
  }
  const html = await readFile(path.join(directory, "lesson.html"), "utf8");
  assert.match(html, /presentation-sha256" content="f7673d0d7da7396446955dcb087de0e23be6793d681731a5c3ef75bdbb45f241"/);
  await assert.rejects(stat(path.join(directory, "assets")));
});

// ---------------------------------------------------------------- part 2: v2.1 (AC-8.3)

const VTT = "WEBVTT\n\n00:00.000 --> 00:01.500\nThe switch jumps to case 2.\n\n00:01.500 --> 00:03.000\nWithout break it falls through.\n";
const SVG = '<svg role="img" viewBox="0 0 120 40" xmlns="http://www.w3.org/2000/svg"><title>The byte 0x42 as bits</title>'
  + '<defs><marker id="arrow" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="currentColor"/></marker></defs>'
  + '<rect x="2" y="2" width="116" height="20" fill="none" stroke="currentColor"/>'
  + '<line x1="10" y1="32" x2="70" y2="32" stroke="currentColor" marker-end="url(#arrow)"/>'
  + '<text x="60" y="16" text-anchor="middle" font-size="10">0100 0010</text></svg>';

function sha(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

async function mediaLesson(prefix) {
  const directory = await temporaryDirectory(prefix);
  // a tiny but real MP4 is not needed for the HTML contract; the browser test below uses one when present
  await writeFile(path.join(directory, "clip.mp4"), Buffer.from("not decoded by the HTML checks"));
  await writeFile(path.join(directory, "captions.vtt"), VTT, "utf8");
  const source = `# Two to the $n$

Each extra bit doubles the range: $2^{n+1} = 2 \\cdot 2^n$. A dollar stays a dollar: \\$5, and \`$x$\` stays code.

$$\\sum_{i=0}^{n-1} 2^i = 2^n - 1$$

${SVG}

<video controls width="640" src="clip.mp4"><track kind="captions" src="captions.vtt" srclang="en" label="English" default></video>

- [ ] Predict the output
- [x] Run it
`;
  const markdown = path.join(directory, "lesson.md");
  await writeFile(markdown, source, "utf8");
  return { directory, markdown, html: path.join(directory, "lesson.html"), source };
}

test("test_svg_math_video", async () => {
  const { directory, markdown, html: htmlPath, source } = await mediaLesson("ptk-render-media-");
  run([markdown, htmlPath]);
  const html = await readFile(htmlPath, "utf8");
  // inline SVG survives, static and named
  assert.match(html, /<svg role="img" viewbox="0 0 120 40"[^>]*><title>The byte 0x42 as bits<\/title>/);
  assert.match(html, /marker-end="url\(#arrow\)"/);
  // MathJax SVG for both inline and display math, with the TeX as the accessible name
  const inline = [...html.matchAll(/<span class="math" role="img" aria-label="TeX: ([^"]*)"><svg class="mjx-va\d+"/g)].map((m) => m[1]);
  assert.deepEqual(inline, ["n", "2^{n+1} = 2 \\cdot 2^n"]);
  assert.match(html, /<div class="math-display" role="img" aria-label="TeX: \\sum_\{i=0\}\^\{n-1\} 2\^i = 2\^n - 1"><svg/);
  assert.match(html, /\.mjx-va\d+ \{ vertical-align:-?[\d.]+ex; \}/);
  assert.match(html, /\$5/);
  assert.match(html, /<code>\$x\$<\/code>/, "math inside a code span stays code");
  // no inline style attribute anywhere: the CSP has no 'unsafe-inline'
  assert.doesNotMatch(html.replace(/<style>[\s\S]*?<\/style>/g, ""), /\sstyle=/);
  assert.doesNotMatch(html, /<script/i);
  const csp = html.match(/http-equiv="Content-Security-Policy" content="([^"]*)"/)[1];
  assert.match(csp, /default-src 'none'/);
  assert.doesNotMatch(csp, /unsafe-inline|script-src/);
  const blocks = [...html.matchAll(/<style>([\s\S]*?)<\/style>/g)].map((m) => `'sha256-${createHash("sha256").update(m[1]).digest("base64")}'`);
  assert.equal(blocks.length, 2);
  for (const b of blocks) assert.ok(csp.includes(b), `CSP misses the hash of a style block: ${b}`);
  // video with controls and an embedded captions track (file:// can't load a sibling .vtt)
  assert.match(html, /<video controls width="640" src="clip\.mp4"><track kind="captions" src="data:text\/vtt;base64,[A-Za-z0-9+/=]+" srclang="en" label="English" default \/><\/video>/);
  const embedded = Buffer.from(html.match(/data:text\/vtt;base64,([A-Za-z0-9+/=]+)/)[1], "base64").toString("utf8");
  assert.equal(embedded, VTT);
  // provenance: source and every local asset by sha256
  assert.ok(html.includes(`<meta name="source-sha256" content="${sha(source)}">`));
  assert.ok(html.includes(`<meta name="asset-sha256" content="captions.vtt ${sha(VTT)}">`));
  assert.ok(html.includes(`<meta name="asset-sha256" content="clip.mp4 ${sha(await readFile(path.join(directory, "clip.mp4")))}">`));
  // task lists are glyphs with v2's accessible names, not form inputs (D20.12)
  assert.match(html, /<span class="task" role="img" aria-label="Incomplete checklist item">☐<\/span>/);
  assert.match(html, /<span class="task" role="img" aria-label="Completed checklist item">☑<\/span>/);
  assert.doesNotMatch(html, /type="checkbox"/);
  // deterministic, and --check notices a changed asset as well as a changed source
  const again = path.join(directory, "again.html");
  run([markdown, again]);
  assert.deepEqual(await readFile(again), await readFile(htmlPath));
  run(["--check", markdown, htmlPath]);
  await writeFile(path.join(directory, "captions.vtt"), VTT.replace("case 2", "case 3"), "utf8");
  const drift = run(["--check", markdown, htmlPath], 1);
  assert.match(drift.stderr, /drifted/);
});

test("svg, math and video inputs that would mislead or escape are rejected, not stripped", async () => {
  const directory = await temporaryDirectory("ptk-render-reject-");
  await writeFile(path.join(directory, "captions.vtt"), VTT, "utf8");
  await writeFile(path.join(directory, "notes.vtt"), "1\n00:00:00,000 --> 00:00:01,000\nSRT, not WebVTT\n", "utf8");
  await writeFile(path.join(directory, "clip.mp4"), Buffer.from("x"));
  const named = '<svg role="img" viewBox="0 0 10 10" xmlns="http://www.w3.org/2000/svg"><title>t</title>';
  const cases = [
    ["svg-script", `${named}<script>alert(1)</script></svg>`, /unsupported HTML tag\(s\): script/],
    ["svg-foreign", `${named}<foreignObject><p>x</p></foreignObject></svg>`, /unsupported HTML tag\(s\): foreignobject/],
    ["svg-animate", `${named}<rect width="5" height="5"><animate attributeName="x" to="5" dur="1s"/></rect></svg>`, /animated SVG/],
    ["svg-unnamed", '<svg viewBox="0 0 10 10" xmlns="http://www.w3.org/2000/svg"><rect width="5" height="5"/></svg>', /needs role="img"/],
    ["svg-no-title", '<svg role="img" viewBox="0 0 10 10" xmlns="http://www.w3.org/2000/svg"><rect width="5" height="5"/></svg>', /accessible name/],
    ["svg-remote-use", `${named}<use href="https://example.invalid/sprite.svg#a"/></svg>`, /may only point inside the SVG/],
    ["svg-remote-url", `${named}<rect width="5" height="5" fill="url(https://example.invalid/p.svg#g)"/></svg>`, /url\(\) may only name an id/],
    ["svg-style", `${named}<rect width="5" height="5" style="fill:red"/></svg>`, /unsupported attribute style on <rect>/],
    ["svg-onload", `${named}<rect width="5" height="5" onload="alert(1)"/></svg>`, /event-handler|unsupported attribute onload/],
    ["video-no-track", '<video controls src="clip.mp4"></video>', /captions or subtitles <track>/],
    ["video-autoplay", '<video controls autoplay src="clip.mp4"><track kind="captions" src="captions.vtt" srclang="en" label="English"></video>', /unsupported attribute autoplay/],
    ["video-no-controls", '<video src="clip.mp4"><track kind="captions" src="captions.vtt" srclang="en" label="English"></video>', /needs controls/],
    ["video-remote", '<video controls src="https://example.invalid/a.mp4"><track kind="captions" src="captions.vtt" srclang="en" label="English"></video>', /local relative path/],
    ["video-escape", '<video controls src="../clip.mp4"><track kind="captions" src="captions.vtt" srclang="en" label="English"></video>', /escapes the Markdown source directory/],
    ["track-not-vtt", '<video controls src="clip.mp4"><track kind="captions" src="notes.vtt" srclang="en" label="English"></video>', /not a WebVTT file/],
    ["track-no-label", '<video controls src="clip.mp4"><track kind="captions" src="captions.vtt"></video>', /srclang and label/],
    ["bad-tex", "Broken: $\\frac{1}{$ here.", /TeX did not compile/],
    ["unlabelled-input", '<input type="text" name="guess">', /needs an accessible name/],
  ];
  for (const [name, fragment, pattern] of cases) {
    const markdown = path.join(directory, `${name}.md`);
    const htmlPath = path.join(directory, `${name}.html`);
    await writeFile(markdown, `# Case\n\n${fragment}\n`, "utf8");
    const rejected = run([markdown, htmlPath], 2);
    assert.match(rejected.stderr, pattern, name);
    await assert.rejects(stat(htmlPath), `${name} published an artifact`);
  }
});

test("generated-at never reads the clock, CRLF frontmatter is stripped, a symlinked trusted root works", async () => {
  const directory = await temporaryDirectory("ptk-render-fixes-");
  const markdown = path.join(directory, "lesson.md");
  const source = "---\r\ntitle: secret-frontmatter\r\n---\r\n\r\n# Visible\r\n\r\nBody.\r\n";
  await writeFile(markdown, source, "utf8");
  // E2: without SOURCE_DATE_EPOCH the stamp comes from the source hash, so --check passes later too
  const env = { SOURCE_DATE_EPOCH: "" };
  run([markdown], 0, undefined, env);
  const first = await readFile(path.join(directory, "lesson.html"), "utf8");
  await new Promise((resolve) => setTimeout(resolve, 1100));
  run(["--check", markdown], 0, undefined, env);
  const digest = createHash("sha256").update(source).digest("hex");
  const expected = new Date((1577836800 + (parseInt(digest.slice(0, 8), 16) % 126230400)) * 1000).toISOString();
  assert.ok(first.includes(`<meta name="generated-at" content="${expected}">`));
  // E24: CRLF frontmatter does not leak
  assert.doesNotMatch(first, /secret-frontmatter/);
  assert.match(first, /<title>Visible<\/title>/);
  // E16: a trusted root reached through a symlink (macOS /tmp is one) is accepted; links below it are not
  const alias = path.join(await temporaryDirectory("ptk-render-alias-"), "root-link");
  await symlink(directory, alias);
  run([path.join(alias, "lesson.md"), path.join(alias, "via-alias.html")], 0, alias);
  await stat(path.join(directory, "via-alias.html"));
});

test("the page works opened from disk: styles apply under the CSP, captions load, SVG and math have size", async () => {
  const require = createRequire(path.join(process.env.PTK_NODE_PREFIX, "package.json"));
  const { chromium } = require("playwright");
  const { directory, markdown, html: htmlPath } = await mediaLesson("ptk-render-browser-");
  if (process.env.PTK_TEST_MP4) {
    await writeFile(path.join(directory, "clip.mp4"), await readFile(process.env.PTK_TEST_MP4));
  }
  run([markdown, htmlPath]);
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 900 } });
    const problems = [];
    page.on("console", (m) => { if (m.type() === "error") problems.push(m.text()); });
    page.on("request", (r) => { if (!/^(file:|data:)/.test(r.url())) problems.push(`outbound: ${r.url()}`); });
    await page.goto(pathToFileURL(htmlPath).href);
    const r = await page.evaluate(async () => {
      const track = document.querySelector("video").textTracks[0];
      track.mode = "hidden";
      for (let i = 0; i < 50 && !(track.cues && track.cues.length); i += 1) await new Promise((res) => setTimeout(res, 50));
      const box = (el) => { const b = el.getBoundingClientRect(); return [b.width, b.height]; };
      return {
        cues: track.cues ? track.cues.length : 0,
        firstCue: track.cues && track.cues[0] ? track.cues[0].text : null,
        figure: box(document.querySelector("svg[role=img]:not([class])")),
        math: [...document.querySelectorAll(".math svg, .math-display svg")].map(box),
        mathAlign: getComputedStyle(document.querySelector(".math-display svg")).verticalAlign,
        background: getComputedStyle(document.body).backgroundColor,
        overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      };
    });
    assert.deepEqual(problems, [], "console errors or outbound requests (a CSP violation shows up here)");
    assert.equal(r.cues, 2);
    assert.equal(r.firstCue, "The switch jumps to case 2.");
    assert.ok(r.figure[0] > 50 && r.figure[1] > 10, `figure size ${r.figure}`);
    assert.equal(r.math.length, 3);
    for (const [w, h] of r.math) assert.ok(w > 5 && h > 5, `math size ${w}x${h}`);
    assert.notEqual(r.mathAlign, "baseline", "the MathJax vertical-align class did not apply");
    assert.equal(r.background, "rgb(251, 250, 244)", "the presentation style block was blocked");
    assert.ok(r.overflow <= 0, `page scrolls sideways at 390 px by ${r.overflow}px`);
  } finally {
    await browser.close();
  }
});
