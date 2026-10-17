import { createHash } from "node:crypto";
import { cp, mkdir, readFile, readdir, rm, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url));
const source = path.join(root, "src");
const output = path.join(root, "dist");
const forbidden = /(?:https?:\/\/|wss?:\/\/|(?:fetch|XMLHttpRequest|WebSocket|sendBeacon)\s*\(|import\s*\(\s*["'`]https?:)/i;
const sha256 = (bytes) => createHash("sha256").update(bytes).digest("hex");
async function files(dir, prefix = "") { const out = []; for (const entry of (await readdir(dir, { withFileTypes: true })).sort((a, b) => a.name.localeCompare(b.name))) { const rel = path.join(prefix, entry.name); if (entry.isDirectory()) out.push(...await files(path.join(dir, entry.name), rel)); else out.push(rel); } return out; }
const names = await files(source);
const records = [];
for (const rel of names) { const bytes = await readFile(path.join(source, rel)); if (forbidden.test(bytes.toString("utf8"))) throw new Error(`remote/runtime network reference rejected in ${rel}`); records.push({ path: rel.replaceAll(path.sep, "/"), sha256: sha256(bytes), bytes: bytes.length }); }
await rm(output, { recursive: true, force: true }); await mkdir(output, { recursive: true });
for (const rel of names) { const destination = path.join(output, rel); await mkdir(path.dirname(destination), { recursive: true }); await cp(path.join(source, rel), destination); }
const sourceBytes = Buffer.from(records.map((record) => `${record.path}:${record.sha256}:${record.bytes}\n`).join(""));
const manifest = { schema_version: "prax.visual-manifest/v1", runtime_version: "prax-visual-lab/0.1.0", source_sha256: sha256(sourceBytes), files: records };
await writeFile(path.join(output, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
console.log(JSON.stringify({ output, files: records.length, source_sha256: manifest.source_sha256 }, null, 2));
