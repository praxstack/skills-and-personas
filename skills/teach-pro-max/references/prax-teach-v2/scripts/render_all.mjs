#!/usr/bin/env node

import { readdir, realpath } from "node:fs/promises";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const SKIP_DIRECTORIES = new Set([
  ".agent",
  ".agents",
  ".git",
  ".mypy_cache",
  ".pytest_cache",
  ".ruff_cache",
  ".venv",
  "__pycache__",
  "attempts",
  "learner-workspaces",
  "node_modules",
  "private-banks",
  "openspec",
  "runtime",
  "runs",
]);

const arguments_ = process.argv.slice(2);
const checkOnly = arguments_[0] === "--check";
if (checkOnly) arguments_.shift();
if (arguments_.length > 1) {
  process.stderr.write("Usage: render_all.mjs [--check] [workspace]\n");
  process.exit(2);
}

const root = await realpath(path.resolve(arguments_[0] || "."));
const renderer = path.join(path.dirname(fileURLToPath(import.meta.url)), "render_markdown.mjs");

async function markdownFiles(directory) {
  const found = [];
  const entries = await readdir(directory, { withFileTypes: true });
  entries.sort((left, right) => left.name.localeCompare(right.name, "en"));
  for (const entry of entries) {
    if (entry.isSymbolicLink()) continue;
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      if (!SKIP_DIRECTORIES.has(entry.name)) found.push(...(await markdownFiles(target)));
    } else if (entry.isFile() && entry.name.endsWith(".md")) {
      found.push(target);
    }
  }
  return found;
}

// One operation-local context validates the pinned historical inventory once.
const contextRun = spawnSync(process.env.PRAX_PYTHON || "python3", [path.join(path.dirname(renderer), "current_evidence.py"), root, "--render-contexts"], { cwd: root, encoding: "utf8", env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" }, timeout: 35000 });
if (contextRun.status !== 0) { process.stderr.write(contextRun.stderr || "evidence context failed\n"); process.exit(1); }
const context = JSON.parse(contextRun.stdout);
const files = await markdownFiles(root);
const failures = [];
for (const markdown of files) {
  const relative = path.relative(root, markdown).split(path.sep).join("/");
  const historical = context.prefixes.some((prefix) => relative.startsWith(prefix));
  if (historical && !context.historical_root) { failures.push({ markdown, stderr: "protected historical companion requires a pinned original context", status: 1 }); continue; }
  // Historical bytes are never rewritten; check using their original renderer.
  const effectiveRoot = historical ? context.historical_root : root;
  const args = [historical ? path.join(effectiveRoot, "scripts/render_markdown.mjs") : renderer];
  if (checkOnly || historical) args.push("--check");
  args.push("--trusted-root", effectiveRoot, path.join(effectiveRoot, relative));
  const completed = spawnSync(process.execPath, args, {
    cwd: root,
    encoding: "utf8",
    env: process.env,
  });
  if (completed.status !== 0) {
    failures.push({ markdown, stderr: completed.stderr.trim(), status: completed.status });
  }
}

if (failures.length) {
  for (const failure of failures) {
    process.stderr.write(`${path.relative(root, failure.markdown)}: ${failure.stderr || `exit ${failure.status}`}\n`);
  }
  process.exit(1);
}

process.stdout.write(`${checkOnly ? "Checked" : "Rendered"} ${files.length} Markdown/HTML pair(s)\n`);
