import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import {
  mkdir,
  mkdtemp,
  readFile,
  readdir,
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
const ADAPTER = path.join(ROOT, "integrations", "flint", "render_flint.mjs");
const VALID = path.join(ROOT, "fixtures", "flint", "retrieval-by-session.flint.json");
const INVALID = path.join(ROOT, "fixtures", "flint", "invalid-remote-data.flint.json");
const INVALID_SEMANTIC = path.join(
  ROOT,
  "fixtures",
  "flint",
  "invalid-semantic-field.flint.json",
);
const WARNING = path.join(ROOT, "fixtures", "flint", "warning-pyramid.flint.json");

function runRaw(args, expected = 0, env = undefined) {
  const completed = spawnSync(
    process.execPath,
    [ADAPTER, ...args],
    {
      cwd: ROOT,
      encoding: "utf8",
      env: env || { ...process.env, SOURCE_DATE_EPOCH: "1785844800" },
    },
  );
  assert.equal(
    completed.status,
    expected,
    `stdout:\n${completed.stdout}\nstderr:\n${completed.stderr}`,
  );
  return completed;
}

function run(input, outputDirectory, expected = 0, trustedRoot = undefined, env = undefined) {
  return runRaw(
    [
      "--input",
      input,
      "--output-dir",
      outputDirectory,
      "--backend",
      "vegalite",
      "--trusted-root",
      trustedRoot || path.dirname(outputDirectory),
    ],
    expected,
    env,
  );
}

async function temporaryDirectory(prefix) {
  return realpath(await mkdtemp(path.join(os.tmpdir(), prefix)));
}

function sha256(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

test("real pinned Flint renders deterministic SVG, backend spec, table, and receipt", async () => {
  const base = await temporaryDirectory("prax-flint-");
  const outputs = [path.join(base, "one"), path.join(base, "two")];
  const receipts = outputs.map((output) => JSON.parse(run(VALID, output).stdout));

  assert.deepEqual(receipts[0], receipts[1]);
  assert.equal(receipts[0].status, "rendered");
  assert.equal(receipts[0].compiler.package, "flint-chart");
  assert.equal(receipts[0].compiler.version, "0.4.1");
  assert.equal(receipts[0].renderer.package, "flint-chart-mcp");
  assert.equal(receipts[0].renderer.version, "0.4.1");
  assert.equal(receipts[0].backend, "vegalite");
  assert.deepEqual(receipts[0].warnings, []);
  assert.equal(receipts[0].evidence_level, "dependency-exercised");
  assert.equal(receipts[0].chart_correctness_claimed, false);
  assert.equal(receipts[0].generated_at, "2026-08-04T12:00:00.000Z");
  assert.deepEqual(receipts[0].invocation, {
    api: [
      {
        export: "validateInput",
        module: "flint-chart-mcp/render",
        options: { disableFileReference: true, maxDataRows: 100_000 },
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
      "vegalite",
      "--trusted-root",
      "<trusted-root>",
    ],
  });
  assert.deepEqual(receipts[0].known_limitations, [
    "Pinned Flint execution does not establish chart correctness, accessibility, or learner outcomes.",
    "Network isolation was not externally traced; input policy rejection is not network-isolation evidence.",
    "The generated SVG still requires a reviewed accessible lesson wrapper; the table is a data alternative, not an assistive-technology conformance claim.",
  ]);

  const expectedNames = [
    "chart.data.json",
    "chart.semantic-spec.json",
    "chart.source.flint.json",
    "chart.svg",
    "chart.table.html",
    "chart.vega-lite.json",
    "manifest.json",
  ];
  for (const name of expectedNames) {
    assert.ok((await stat(path.join(outputs[0], name))).size > 0, `${name} must be non-empty`);
    assert.deepEqual(
      await readFile(path.join(outputs[0], name)),
      await readFile(path.join(outputs[1], name)),
      `${name} must be deterministic`,
    );
  }

  const svg = await readFile(path.join(outputs[0], "chart.svg"), "utf8");
  assert.match(svg, /<svg\b/);
  const table = await readFile(path.join(outputs[0], "chart.table.html"), "utf8");
  assert.match(table, /<table>/);
  assert.match(table, /<caption>Synthetic independent-retrieval fixture/);
  assert.match(table, /<th scope="col">/);
  assert.match(table, /<th scope="row">Immediate<\/th>/);
  assert.match(table, /not learner-outcome evidence/i);

  const manifestBytes = await readFile(path.join(outputs[0], "manifest.json"));
  const manifest = JSON.parse(manifestBytes);
  for (const [name, digest] of Object.entries(manifest.artifacts)) {
    assert.equal(sha256(await readFile(path.join(outputs[0], name))), digest);
  }
  assert.equal(manifest.input.raw_sha256, sha256(await readFile(VALID)));
  assert.equal(manifest.network_isolation_verified, false);
  assert.equal(manifest.network_references_accepted, false);
  assert.equal(manifest.file_references, false);
  assert.equal(manifest.synthetic_fixture, true);
  assert.equal(
    manifest.editable_inputs.data.sha256,
    sha256(await readFile(path.join(outputs[0], manifest.editable_inputs.data.file))),
  );
  assert.equal(
    manifest.editable_inputs.semantic_spec.sha256,
    sha256(
      await readFile(path.join(outputs[0], manifest.editable_inputs.semantic_spec.file)),
    ),
  );
  assert.equal(manifest.output_sha256, sha256(await readFile(path.join(outputs[0], "chart.svg"))));
});

test("remote data and unresolved semantic failures fail closed without artifacts", async () => {
  const base = await temporaryDirectory("prax-flint-invalid-");
  const output = path.join(base, "blocked");
  const completed = run(INVALID, output, 2);
  assert.match(completed.stderr, /remote|inline|data\.values/i);
  await assert.rejects(stat(path.join(output, "chart.svg")));

  const semanticOutput = path.join(base, "semantic-blocked");
  const semantic = run(INVALID_SEMANTIC, semanticOutput, 2);
  assert.match(semantic.stderr, /encoding field|absent|semantic/i);
  await assert.rejects(stat(path.join(semanticOutput, "manifest.json")));
});

test("adapter requires a reproducible timestamp and explicit trusted root", async () => {
  const base = await temporaryDirectory("prax-flint-required-");
  const withoutRoot = path.join(base, "without-root");
  const missingRoot = runRaw(
    ["--input", VALID, "--output-dir", withoutRoot, "--backend", "vegalite"],
    2,
  );
  assert.match(missingRoot.stderr, /trusted-root.*required|requires.*trusted root/i);
  await assert.rejects(stat(withoutRoot));

  const withoutTimestamp = path.join(base, "without-timestamp");
  const unpinnedEnvironment = { ...process.env };
  delete unpinnedEnvironment.SOURCE_DATE_EPOCH;
  const missingTimestamp = run(
    VALID,
    withoutTimestamp,
    2,
    base,
    unpinnedEnvironment,
  );
  assert.match(missingTimestamp.stderr, /source_date_epoch.*required|reproducible timestamp/i);
  await assert.rejects(stat(withoutTimestamp));
});

test("adapter confines publication and rejects symlink leaves and ancestors", async () => {
  const base = await temporaryDirectory("prax-flint-paths-");
  const outside = await temporaryDirectory("prax-flint-outside-");
  const outsideOutput = path.join(outside, "chart");
  const escaped = run(VALID, outsideOutput, 2, base);
  assert.match(escaped.stderr, /outside.*trusted root|contained.*trusted root/i);
  await assert.rejects(stat(outsideOutput));

  const existingTarget = path.join(base, "existing-target");
  await mkdir(existingTarget);
  const linkedLeaf = path.join(base, "linked-leaf");
  await symlink(existingTarget, linkedLeaf);
  const existingLink = run(VALID, linkedLeaf, 2, base);
  assert.match(existingLink.stderr, /symlink.*leaf|leaf.*symlink/i);
  assert.deepEqual(await readdir(existingTarget), []);

  const danglingLeaf = path.join(base, "dangling-leaf");
  await symlink(path.join(base, "missing-target"), danglingLeaf);
  const dangling = run(VALID, danglingLeaf, 2, base);
  assert.match(dangling.stderr, /symlink.*leaf|leaf.*symlink/i);

  const realAncestor = path.join(base, "real-ancestor");
  const linkedAncestor = path.join(base, "linked-ancestor");
  await mkdir(realAncestor);
  await symlink(realAncestor, linkedAncestor);
  const throughAncestor = run(
    VALID,
    path.join(linkedAncestor, "chart"),
    2,
    base,
  );
  assert.match(throughAncestor.stderr, /symlink.*ancestor|ancestor.*symlink/i);
  await assert.rejects(stat(path.join(realAncestor, "chart")));

  const trustedAlias = path.join(outside, "trusted-alias");
  await symlink(base, trustedAlias);
  const aliasOutput = path.join(trustedAlias, "chart");
  const aliasRoot = run(VALID, aliasOutput, 2, trustedAlias);
  assert.match(aliasRoot.stderr, /symlink.*ancestor|ancestor.*symlink/i);
  await assert.rejects(stat(path.join(base, "chart")));
});

test("genuine pinned Flint warning fails closed without publishing artifacts", async () => {
  const base = await temporaryDirectory("prax-flint-warning-");
  const output = path.join(base, "blocked");
  const completed = run(WARNING, output, 2, base);
  assert.match(completed.stderr, /Flint assembly emitted unresolved warnings/i);
  assert.match(completed.stderr, /too-many-groups-pyramid/i);
  await assert.rejects(stat(output));
});
