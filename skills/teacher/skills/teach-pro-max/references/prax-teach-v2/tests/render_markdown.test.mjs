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
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const RENDERER = path.join(ROOT, "scripts", "render_markdown.mjs");
const RENDER_ALL = path.join(ROOT, "scripts", "render_all.mjs");

function runRaw(args, expected = 0) {
  const completed = spawnSync(process.execPath, [RENDERER, ...args], {
    cwd: ROOT,
    encoding: "utf8",
    env: { ...process.env, SOURCE_DATE_EPOCH: "1785844800" },
  });
  assert.equal(
    completed.status,
    expected,
    `stdout:\n${completed.stdout}\nstderr:\n${completed.stderr}`,
  );
  return completed;
}

function run(args, expected = 0, trustedRoot = undefined) {
  const source = args.find((argument) => argument.endsWith(".md"));
  assert.ok(source, "test invocation must identify its Markdown source");
  return runRaw(
    ["--trusted-root", trustedRoot || path.dirname(source), ...args],
    expected,
  );
}

async function temporaryDirectory(prefix) {
  return realpath(await mkdtemp(path.join(os.tmpdir(), prefix)));
}

test("bulk rendering leaves immutable attempt snapshots untouched", async () => {
  const directory = await temporaryDirectory("prax-render-all-");
  const attempts = path.join(directory, "evidence", "forward", "attempts");
  await mkdir(attempts, { recursive: true });
  await writeFile(path.join(directory, "current.md"), "# Current\n", "utf8");
  await writeFile(path.join(attempts, "snapshot.md"), "# Snapshot\n", "utf8");

  const completed = spawnSync(process.execPath, [RENDER_ALL, directory], {
    cwd: ROOT,
    encoding: "utf8",
    env: { ...process.env, SOURCE_DATE_EPOCH: "1785844800" },
  });
  assert.equal(completed.status, 0, completed.stderr);
  await stat(path.join(directory, "current.html"));
  await assert.rejects(stat(path.join(attempts, "snapshot.html")));
});

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
  assert.match(html, /renderer-version" content="prax-teach-markdown\/2\.2\.0"/);
  assert.match(html, /template-version" content="prax-teach-lesson\/2\.0\.0"/);
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
