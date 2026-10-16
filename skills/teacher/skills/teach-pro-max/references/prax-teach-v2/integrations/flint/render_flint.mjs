#!/usr/bin/env node

import { createHash } from "node:crypto";
import {
  lstat,
  mkdir,
  mkdtemp,
  open,
  readFile,
  rename,
  rm,
} from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  assembleForBackend,
  renderChart,
  stripPrivateKeys,
  validateInput,
} from "flint-chart-mcp/render";

const ALLOWED_BACKENDS = new Set(["vegalite", "echarts"]);
const MAX_INPUT_BYTES = 5 * 1024 * 1024;
const MAX_ROWS = 100_000;
const MAX_COLUMNS = 128;
const MAX_TEXT_LENGTH = 16_384;
const MAX_DIMENSION = 4_000;
const MAX_ABSOLUTE_NUMBER = 1e15;
const REFERENCE_KEYS = new Set(["file", "filename", "href", "path", "src", "url"]);
const FORBIDDEN_OBJECT_KEYS = new Set(["__proto__", "constructor", "prototype"]);
const KNOWN_LIMITATIONS = [
  "Pinned Flint execution does not establish chart correctness, accessibility, or learner outcomes.",
  "Network isolation was not externally traced; input policy rejection is not network-isolation evidence.",
  "The generated SVG still requires a reviewed accessible lesson wrapper; the table is a data alternative, not an assistive-technology conformance claim.",
];

function fail(message) {
  throw new Error(message);
}

function parseArguments(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (!argument.startsWith("--")) {
      fail(`unexpected positional argument: ${argument}`);
    }
    if (!["--input", "--output-dir", "--backend", "--trusted-root"].includes(argument)) {
      fail(`unknown argument: ${argument}`);
    }
    const value = argv[index + 1];
    if (!value || value.startsWith("--")) {
      fail(`${argument} requires a value`);
    }
    const key = argument.slice(2);
    if (Object.hasOwn(parsed, key)) {
      fail(`${argument} may be provided only once`);
    }
    parsed[key] = value;
    index += 1;
  }

  for (const key of ["input", "output-dir", "backend", "trusted-root"]) {
    if (!parsed[key]) fail(`--${key} is required`);
  }
  if (!ALLOWED_BACKENDS.has(parsed.backend)) {
    fail(`--backend must be one of: ${[...ALLOWED_BACKENDS].join(", ")}`);
  }
  return {
    backend: parsed.backend,
    inputPath: path.resolve(parsed.input),
    outputDirectory: path.resolve(parsed["output-dir"]),
    trustedRoot: path.resolve(parsed["trusted-root"]),
  };
}

function sha256(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

function stableValue(value) {
  if (Array.isArray(value)) return value.map(stableValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, stableValue(value[key])]),
    );
  }
  return value;
}

function stableJson(value) {
  return `${JSON.stringify(stableValue(value), null, 2)}\n`;
}

function isPlainObject(value) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

function assertNoReferences(value, location = "input") {
  if (Array.isArray(value)) {
    value.forEach((entry, index) => assertNoReferences(entry, `${location}[${index}]`));
    return;
  }
  if (!isPlainObject(value)) return;

  for (const [key, child] of Object.entries(value)) {
    const normalizedKey = key.toLowerCase();
    if (FORBIDDEN_OBJECT_KEYS.has(normalizedKey)) {
      fail(`${location}.${key} uses a forbidden object key`);
    }
    if (REFERENCE_KEYS.has(normalizedKey)) {
      fail(
        `${location}.${key} is a remote or file reference; only inline data.values is allowed`,
      );
    }
    if (
      typeof child === "string" &&
      /(?:https?:\/\/|file:\/\/|(?:^|[\\/])\.\.(?:[\\/]|$))/iu.test(child)
    ) {
      fail(`${location}.${key} contains a remote or file reference`);
    }
    assertNoReferences(child, `${location}.${key}`);
  }
}

function requireReviewedText(metadata, key) {
  const value = metadata[key];
  if (typeof value !== "string" || !value.trim()) {
    fail(`prax_teach.${key} must be a complete non-empty string`);
  }
  if (value.length > MAX_TEXT_LENGTH) {
    fail(`prax_teach.${key} exceeds the ${MAX_TEXT_LENGTH}-character limit`);
  }
  if (/^(?:tbd|todo|placeholder|n\/a)$/iu.test(value.trim())) {
    fail(`prax_teach.${key} is unresolved placeholder text`);
  }
  return value.trim();
}

function encodingFields(encodings) {
  const fields = [];
  const visit = (value) => {
    if (typeof value === "string" && value.trim()) fields.push(value.trim());
    else if (Array.isArray(value)) value.forEach(visit);
    else if (isPlainObject(value) && typeof value.field === "string" && value.field.trim()) {
      fields.push(value.field.trim());
    }
  };
  Object.values(encodings).forEach(visit);
  return [...new Set(fields)];
}

function assertFiniteValue(value, location) {
  if (value === null || typeof value === "boolean") return;
  if (typeof value === "number") {
    if (!Number.isFinite(value) || Math.abs(value) > MAX_ABSOLUTE_NUMBER) {
      fail(`${location} must be a finite bounded number`);
    }
    return;
  }
  if (typeof value === "string") {
    if (value.length > MAX_TEXT_LENGTH) fail(`${location} exceeds the text-size limit`);
    return;
  }
  fail(`${location} must be a scalar JSON value`);
}

function assertBoundedSize(chartSpec, key) {
  const size = chartSpec[key];
  if (!isPlainObject(size)) {
    fail(`chart_spec.${key} is required to bound chart dimensions`);
  }
  for (const dimension of ["width", "height"]) {
    const value = size[dimension];
    if (!Number.isInteger(value) || value <= 0 || value > MAX_DIMENSION) {
      fail(
        `chart_spec.${key}.${dimension} must be a positive integer no greater than ${MAX_DIMENSION}`,
      );
    }
  }
}

function assertBoundedScales(value, location = "chart_spec") {
  if (Array.isArray(value)) {
    value.forEach((entry, index) => assertBoundedScales(entry, `${location}[${index}]`));
    return;
  }
  if (!isPlainObject(value)) return;

  for (const [key, child] of Object.entries(value)) {
    if (["expr", "signal"].includes(key.toLowerCase())) {
      fail(`${location}.${key} is executable or unbounded and is not allowed`);
    }
    if (key.toLowerCase() === "scale") {
      if (!isPlainObject(child)) fail(`${location}.scale must be an object`);
      for (const bound of ["domainMin", "domainMax", "domainMid"]) {
        if (Object.hasOwn(child, bound)) assertFiniteValue(child[bound], `${location}.scale.${bound}`);
      }
      for (const listKey of ["domain", "range"]) {
        if (Object.hasOwn(child, listKey)) {
          const list = child[listKey];
          if (!Array.isArray(list) || list.length === 0 || list.length > 1_024) {
            fail(`${location}.scale.${listKey} must be a non-empty bounded array`);
          }
          list.forEach((entry, index) =>
            assertFiniteValue(entry, `${location}.scale.${listKey}[${index}]`),
          );
        }
      }
    }
    assertBoundedScales(child, `${location}.${key}`);
  }
}

function validatePolicy(input) {
  if (!isPlainObject(input)) fail("input must be a JSON object");
  assertNoReferences(input);

  if (!isPlainObject(input.data) || !Array.isArray(input.data.values)) {
    fail("input must use inline data.values; remote and file data references are forbidden");
  }
  const rows = input.data.values;
  if (rows.length === 0 || rows.length > MAX_ROWS) {
    fail(`data.values must contain between 1 and ${MAX_ROWS} rows`);
  }

  const firstRow = rows[0];
  if (!isPlainObject(firstRow)) fail("data.values[0] must be an object");
  const columns = Object.keys(firstRow);
  if (columns.length === 0 || columns.length > MAX_COLUMNS) {
    fail(`data.values must contain between 1 and ${MAX_COLUMNS} columns`);
  }
  if (columns.some((column) => !column.trim())) fail("data.values field names must be non-empty");

  const columnSet = new Set(columns);
  rows.forEach((row, rowIndex) => {
    if (!isPlainObject(row)) fail(`data.values[${rowIndex}] must be an object`);
    const rowKeys = Object.keys(row);
    if (rowKeys.length !== columns.length || rowKeys.some((key) => !columnSet.has(key))) {
      fail(`data.values[${rowIndex}] must contain the same fields as the first row`);
    }
    columns.forEach((column) =>
      assertFiniteValue(row[column], `data.values[${rowIndex}].${column}`),
    );
  });

  if (!isPlainObject(input.chart_spec) || !isPlainObject(input.chart_spec.encodings)) {
    fail("chart_spec.encodings must be an object");
  }
  const usedFields = encodingFields(input.chart_spec.encodings);
  if (usedFields.length === 0) fail("chart_spec.encodings must bind at least one field");
  for (const field of usedFields) {
    if (!columnSet.has(field)) fail(`chart_spec encoding field \"${field}\" is absent from data.values`);
  }

  for (const semanticMap of ["semantic_types", "field_display_names"]) {
    if (!isPlainObject(input[semanticMap])) fail(`${semanticMap} must be an object`);
    for (const field of usedFields) {
      const label = input[semanticMap][field];
      if (typeof label !== "string" || !label.trim()) {
        fail(`${semanticMap}.${field} must be a complete non-empty string`);
      }
    }
  }

  assertBoundedSize(input.chart_spec, "baseSize");
  assertBoundedSize(input.chart_spec, "canvasSize");
  assertBoundedScales(input.chart_spec);

  if (!isPlainObject(input.prax_teach) || input.prax_teach.reviewed !== true) {
    fail("prax_teach.reviewed must be true before rendering");
  }
  const title = requireReviewedText(input.prax_teach, "title");
  const summary = requireReviewedText(input.prax_teach, "summary");
  const tableCaption = requireReviewedText(input.prax_teach, "table_caption");

  return { columns, rows, summary, tableCaption, title, usedFields };
}

function warningText(warning) {
  if (typeof warning === "string") return warning;
  if (warning && typeof warning === "object") {
    const severity = warning.severity ?? "warning";
    const code = warning.code ? ` ${warning.code}` : "";
    const message = warning.message ?? JSON.stringify(stableValue(warning));
    return `${severity}${code}: ${message}`;
  }
  return String(warning);
}

function rejectUnresolvedWarnings(warnings, phase) {
  if (!Array.isArray(warnings)) fail(`${phase} returned a malformed warnings collection`);
  if (warnings.length > 0) {
    fail(`${phase} emitted unresolved warnings: ${warnings.map(warningText).join("; ")}`);
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function displayValue(value) {
  if (value === null) return "Not available";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

function buildTable(input, policy) {
  const labels = policy.columns.map(
    (column) => input.field_display_names[column]?.trim() || column,
  );
  const lines = [
    `<section aria-label="${escapeHtml(policy.title)}">`,
    `  <h2>${escapeHtml(policy.title)}</h2>`,
    `  <p>${escapeHtml(policy.summary)}</p>`,
    "  <table>",
    `    <caption>${escapeHtml(policy.tableCaption)}</caption>`,
    "    <thead>",
    `      <tr>${labels.map((label) => `<th scope="col">${escapeHtml(label)}</th>`).join("")}</tr>`,
    "    </thead>",
    "    <tbody>",
  ];
  for (const row of policy.rows) {
    const cells = policy.columns.map((column, index) => {
      const tag = index === 0 ? 'th scope="row"' : "td";
      return `<${tag}>${escapeHtml(displayValue(row[column]))}</${index === 0 ? "th" : "td"}>`;
    });
    lines.push(`      <tr>${cells.join("")}</tr>`);
  }
  lines.push("    </tbody>", "  </table>", "</section>", "");
  return lines.join("\n");
}

async function packageVersion(specifier, expectedName) {
  let current = path.dirname(fileURLToPath(import.meta.resolve(specifier)));
  for (let depth = 0; depth < 8; depth += 1) {
    const candidate = path.join(current, "package.json");
    try {
      const metadata = JSON.parse(await readFile(candidate, "utf8"));
      if (metadata.name === expectedName && typeof metadata.version === "string") {
        return metadata.version;
      }
    } catch (error) {
      if (error?.code !== "ENOENT") throw error;
    }
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
  fail(`could not resolve installed ${expectedName} package metadata`);
}

function sourceTimestamp() {
  const raw = process.env.SOURCE_DATE_EPOCH;
  if (raw === undefined) {
    fail("SOURCE_DATE_EPOCH is required for a reproducible timestamp");
  }
  if (!/^(?:0|[1-9]\d*)$/u.test(raw)) {
    fail("SOURCE_DATE_EPOCH must be a non-negative integer number of seconds");
  }
  const milliseconds = Number(raw) * 1_000;
  if (!Number.isSafeInteger(milliseconds)) fail("SOURCE_DATE_EPOCH is outside the safe range");
  const generatedAt = new Date(milliseconds).toISOString();
  return { generatedAt, sourceDateEpoch: raw };
}

function normalizedInvocation(backend) {
  return {
    api: [
      {
        export: "validateInput",
        module: "flint-chart-mcp/render",
        options: { disableFileReference: true, maxDataRows: MAX_ROWS },
      },
      {
        export: "assembleForBackend",
        module: "flint-chart-mcp/render",
        options: { disableFileReference: true },
      },
      {
        export: "renderChart",
        module: "flint-chart-mcp/render",
        options: {
          background: "#ffffff",
          disableFileReference: true,
          format: "svg",
          scale: 1,
        },
      },
    ],
    cli: [
      "node",
      "integrations/flint/render_flint.mjs",
      "--input",
      "<input>",
      "--output-dir",
      "<output-dir>",
      "--backend",
      backend,
      "--trusted-root",
      "<trusted-root>",
    ],
  };
}

function validateDurableManifest(manifest, backend) {
  if (
    typeof manifest.generated_at !== "string"
    || Number.isNaN(Date.parse(manifest.generated_at))
    || typeof manifest.source_date_epoch !== "string"
  ) {
    fail("durable manifest requires a reproducible generated_at timestamp");
  }
  if (
    !Array.isArray(manifest.known_limitations)
    || manifest.known_limitations.length === 0
    || manifest.known_limitations.some(
      (limitation) => typeof limitation !== "string" || !limitation.trim(),
    )
  ) {
    fail("durable manifest requires explicit known_limitations");
  }
  if (stableJson(manifest.invocation) !== stableJson(normalizedInvocation(backend))) {
    fail("durable manifest invocation/API record is not normalized");
  }
}

async function lstatIfPresent(target) {
  try {
    return await lstat(target);
  } catch (error) {
    if (error?.code === "ENOENT") return null;
    throw error;
  }
}

function isContained(root, candidate) {
  const relative = path.relative(root, candidate);
  return relative !== "" && relative !== ".." && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative);
}

async function directorySnapshot(directory) {
  const parsed = path.parse(directory);
  const snapshots = [];
  let current = parsed.root;
  const parts = directory.slice(parsed.root.length).split(path.sep).filter(Boolean);
  for (const part of ["", ...parts]) {
    if (part) current = path.join(current, part);
    const metadata = await lstatIfPresent(current);
    if (!metadata) fail(`output ancestor is missing: ${current}`);
    if (metadata.isSymbolicLink()) fail(`output path contains a symlink ancestor: ${current}`);
    if (!metadata.isDirectory()) fail(`output ancestor is not a directory: ${current}`);
    snapshots.push({ device: metadata.dev, inode: metadata.ino, path: current });
  }
  return snapshots;
}

function assertSameSnapshot(expected, current) {
  if (expected.length !== current.length) fail("output ancestor chain changed before publication");
  for (let index = 0; index < expected.length; index += 1) {
    const before = expected[index];
    const after = current[index];
    if (
      before.path !== after.path
      || before.device !== after.device
      || before.inode !== after.inode
    ) {
      fail(`output ancestor changed before publication: ${before.path}`);
    }
  }
}

async function assertOutputLeafAbsent(outputDirectory) {
  const metadata = await lstatIfPresent(outputDirectory);
  if (!metadata) return;
  if (metadata.isSymbolicLink()) {
    fail(`output leaf must not be a symlink: ${outputDirectory}`);
  }
  fail(`output directory already exists: ${outputDirectory}`);
}

async function preflightPublication(outputDirectory, trustedRoot) {
  if (trustedRoot === path.parse(trustedRoot).root) {
    fail("trusted root must be narrower than the filesystem root");
  }
  if (!isContained(trustedRoot, outputDirectory)) {
    fail(`output must be contained beneath the trusted root: ${trustedRoot}`);
  }
  const rootSnapshot = await directorySnapshot(trustedRoot);
  const expectedAncestors = new Map();
  let current = trustedRoot;
  const parentRelative = path.relative(trustedRoot, path.dirname(outputDirectory));
  const parts = parentRelative === "" ? [] : parentRelative.split(path.sep);
  let missing = false;
  for (const part of parts) {
    current = path.join(current, part);
    if (missing) continue;
    const metadata = await lstatIfPresent(current);
    if (!metadata) {
      missing = true;
      continue;
    }
    if (metadata.isSymbolicLink()) fail(`output path contains a symlink ancestor: ${current}`);
    if (!metadata.isDirectory()) fail(`output ancestor is not a directory: ${current}`);
    expectedAncestors.set(current, { device: metadata.dev, inode: metadata.ino });
  }
  if (!missing) await assertOutputLeafAbsent(outputDirectory);
  return { expectedAncestors, rootSnapshot, trustedRoot };
}

async function preparePublicationParent(outputDirectory, preflight) {
  assertSameSnapshot(preflight.rootSnapshot, await directorySnapshot(preflight.trustedRoot));
  let current = preflight.trustedRoot;
  const parentRelative = path.relative(preflight.trustedRoot, path.dirname(outputDirectory));
  const parts = parentRelative === "" ? [] : parentRelative.split(path.sep);
  for (const part of parts) {
    current = path.join(current, part);
    const expected = preflight.expectedAncestors.get(current);
    if (expected) {
      const metadata = await lstatIfPresent(current);
      if (
        !metadata
        || metadata.isSymbolicLink()
        || !metadata.isDirectory()
        || metadata.dev !== expected.device
        || metadata.ino !== expected.inode
      ) {
        fail(`output ancestor changed before publication: ${current}`);
      }
      continue;
    }
    try {
      await mkdir(current, { mode: 0o700 });
    } catch (error) {
      if (error?.code === "EEXIST") fail(`output ancestor appeared before publication: ${current}`);
      throw error;
    }
    const metadata = await lstat(current);
    if (metadata.isSymbolicLink() || !metadata.isDirectory()) {
      fail(`new output ancestor is unsafe: ${current}`);
    }
  }
  await assertOutputLeafAbsent(outputDirectory);
  return directorySnapshot(path.dirname(outputDirectory));
}

async function writeSynced(target, content) {
  const handle = await open(target, "wx", 0o600);
  try {
    await handle.writeFile(content);
    await handle.sync();
  } finally {
    await handle.close();
  }
}

async function publishAtomically(outputDirectory, files, preflight) {
  const parent = path.dirname(outputDirectory);
  const parentSnapshot = await preparePublicationParent(outputDirectory, preflight);
  const temporary = await mkdtemp(path.join(parent, `.${path.basename(outputDirectory)}.tmp-`));
  const temporaryMetadata = await lstat(temporary);
  const temporaryIdentity = {
    device: temporaryMetadata.dev,
    inode: temporaryMetadata.ino,
  };
  let published = false;
  try {
    for (const [name, content] of Object.entries(files)) {
      await writeSynced(path.join(temporary, name), content);
    }
    assertSameSnapshot(parentSnapshot, await directorySnapshot(parent));
    await assertOutputLeafAbsent(outputDirectory);
    const currentTemporary = await lstat(temporary);
    if (
      currentTemporary.isSymbolicLink()
      || !currentTemporary.isDirectory()
      || currentTemporary.dev !== temporaryIdentity.device
      || currentTemporary.ino !== temporaryIdentity.inode
    ) {
      fail("temporary Flint artifact directory changed before publication");
    }
    await rename(temporary, outputDirectory);
    const publishedMetadata = await lstat(outputDirectory);
    if (
      publishedMetadata.isSymbolicLink()
      || !publishedMetadata.isDirectory()
      || publishedMetadata.dev !== temporaryIdentity.device
      || publishedMetadata.ino !== temporaryIdentity.inode
    ) {
      fail("published Flint artifact directory failed validation");
    }
    assertSameSnapshot(parentSnapshot, await directorySnapshot(parent));
    const parentHandle = await open(parent, "r");
    try {
      const openedParent = await parentHandle.stat();
      const expectedParent = parentSnapshot.at(-1);
      if (
        openedParent.dev !== expectedParent.device
        || openedParent.ino !== expectedParent.inode
      ) {
        fail("output parent changed during Flint publication");
      }
      await parentHandle.sync();
    } finally {
      await parentHandle.close();
    }
    published = true;
  } finally {
    if (!published) {
      try {
        assertSameSnapshot(parentSnapshot, await directorySnapshot(parent));
        const currentTemporary = await lstatIfPresent(temporary);
        if (
          currentTemporary
          && !currentTemporary.isSymbolicLink()
          && currentTemporary.isDirectory()
          && currentTemporary.dev === temporaryIdentity.device
          && currentTemporary.ino === temporaryIdentity.inode
        ) {
          await rm(temporary, { force: true, recursive: true });
        }
      } catch {
        // Leave an unresolvable temporary directory rather than following a changed path.
      }
    }
  }
}

async function run() {
  const { backend, inputPath, outputDirectory, trustedRoot } = parseArguments(
    process.argv.slice(2),
  );
  if (outputDirectory === path.parse(outputDirectory).root) {
    fail("the filesystem root cannot be used as --output-dir");
  }
  const publicationPreflight = await preflightPublication(outputDirectory, trustedRoot);
  const timestamp = sourceTimestamp();

  const inputBytes = await readFile(inputPath);
  if (inputBytes.length === 0 || inputBytes.length > MAX_INPUT_BYTES) {
    fail(`input must contain between 1 and ${MAX_INPUT_BYTES} bytes`);
  }
  let input;
  try {
    input = JSON.parse(inputBytes.toString("utf8"));
  } catch (error) {
    fail(`input is not valid JSON: ${error.message}`);
  }

  const policy = validatePolicy(input);
  validateInput(input, { disableFileReference: true, maxDataRows: MAX_ROWS });

  const assembled = assembleForBackend(backend, input, { disableFileReference: true });
  rejectUnresolvedWarnings(assembled.warnings, "Flint assembly");
  const backendSpec = stripPrivateKeys(structuredClone(assembled.spec));

  const rendered = await renderChart(input, backend, {
    background: "#ffffff",
    disableFileReference: true,
    format: "svg",
    scale: 1,
  });
  rejectUnresolvedWarnings(rendered.warnings, "Flint rendering");
  if (rendered.format !== "svg" || rendered.mimeType !== "image/svg+xml" || !rendered.svg) {
    fail("Flint did not return a non-empty SVG artifact");
  }

  const specName = backend === "vegalite" ? "chart.vega-lite.json" : "chart.echarts.json";
  const sourceName = "chart.source.flint.json";
  const dataName = "chart.data.json";
  const semanticSpecName = "chart.semantic-spec.json";
  const canonicalSource = stableJson(input);
  const canonicalData = stableJson({ data: input.data });
  const canonicalSemanticSpec = stableJson({
    chart_spec: input.chart_spec,
    field_display_names: input.field_display_names,
    prax_teach: input.prax_teach,
    semantic_types: input.semantic_types,
  });
  const artifactFiles = {
    "chart.svg": rendered.svg.endsWith("\n") ? rendered.svg : `${rendered.svg}\n`,
    [specName]: stableJson(backendSpec),
    "chart.table.html": buildTable(input, policy),
    [sourceName]: canonicalSource,
    [dataName]: canonicalData,
    [semanticSpecName]: canonicalSemanticSpec,
  };
  const artifacts = Object.fromEntries(
    Object.entries(artifactFiles)
      .sort(([left], [right]) => (left < right ? -1 : left > right ? 1 : 0))
      .map(([name, bytes]) => [name, sha256(bytes)]),
  );
  const compilerVersion = await packageVersion("flint-chart", "flint-chart");
  const rendererVersion = await packageVersion("flint-chart-mcp/render", "flint-chart-mcp");
  const reviewedText = `${policy.title}\n${policy.summary}\n${policy.tableCaption}`;
  const manifest = {
    artifacts,
    backend,
    chart_correctness_claimed: false,
    compiler: { package: "flint-chart", version: compilerVersion },
    compiler_exercise_note:
      "This receipt proves that the pinned compiler and renderer executed; it does not establish chart correctness or learner-outcome evidence.",
    evidence_level: "dependency-exercised",
    editable_inputs: {
      data: { file: dataName, sha256: sha256(canonicalData) },
      semantic_spec: {
        file: semanticSpecName,
        sha256: sha256(canonicalSemanticSpec),
      },
      source: { file: sourceName, sha256: sha256(canonicalSource) },
    },
    file_references: false,
    format: "svg",
    generated_at: timestamp.generatedAt,
    input: { bytes: inputBytes.length, raw_sha256: sha256(inputBytes) },
    invocation: normalizedInvocation(backend),
    known_limitations: [...KNOWN_LIMITATIONS],
    network_isolation_verified: false,
    network_references_accepted: false,
    output_sha256: artifacts["chart.svg"],
    renderer: { package: "flint-chart-mcp", version: rendererVersion },
    schema_version: "1.1",
    source_date_epoch: timestamp.sourceDateEpoch,
    status: "rendered",
    synthetic_fixture: /\bsynthetic\b/iu.test(reviewedText),
    warnings: [],
  };
  validateDurableManifest(manifest, backend);
  const manifestBytes = stableJson(manifest);
  await publishAtomically(outputDirectory, {
    ...artifactFiles,
    "manifest.json": manifestBytes,
  }, publicationPreflight);
  process.stdout.write(stableJson(manifest));
}

try {
  await run();
} catch (error) {
  process.stderr.write(`Flint adapter rejected input: ${error?.message ?? String(error)}\n`);
  process.exitCode = 2;
}
