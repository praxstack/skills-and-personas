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

const files = await markdownFiles(root);
const failures = [];
for (const markdown of files) {
  const args = [renderer];
  if (checkOnly) args.push("--check");
  args.push("--trusted-root", root, markdown);
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
