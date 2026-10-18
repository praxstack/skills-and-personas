#!/usr/bin/env node
// Turn a built concept animation into a video clip, frame by frame.
//
//   node export.mjs anim.html --out clip.mp4 [--gif clip.gif] [--fps 30] [--size 1280x720] [--no-captions] [--poster poster.png]
//
// Each frame is a seek() of the animation's pure timeline, so the clip is
// exact (no screen recording, no dropped frames). Captions are burned in by
// default and always written as a WebVTT file next to the video. Needs
// Playwright and ffmpeg on PATH.

import { pathToFileURL } from "node:url";
import { resolve, dirname, join } from "node:path";
import { mkdtemp, rm, writeFile, mkdir, rename, stat } from "node:fs/promises";
import { tmpdir } from "node:os";
import { spawnSync } from "node:child_process";
import { loadPlaywright, launch } from "../../visual-qa/scripts/pw.mjs";

const args = process.argv.slice(2);
const opt = (n, d) => (args.includes(n) ? args[args.indexOf(n) + 1] : d);
const input = args[0];
if (!input || input.startsWith("--")) {
  console.error("usage: node export.mjs anim.html --out clip.mp4 [--gif clip.gif] [--fps 30] [--size 1280x720] [--no-captions] [--poster p.png]");
  process.exit(2);
}
const out = resolve(opt("--out", input.replace(/\.html$/, ".mp4")));
const gif = opt("--gif");
const poster = opt("--poster");
const fps = Number(opt("--fps", 30));
const [width, height] = opt("--size", "1280x720").split("x").map(Number);
const captions = !args.includes("--no-captions");

if (spawnSync("ffmpeg", ["-version"]).status !== 0) {
  console.error("ffmpeg not found on PATH");
  process.exit(2);
}

const vtt = (keys, duration) => {
  const stamp = (s) => {
    const ms = Math.round(s * 1000);
    const hh = String(Math.floor(ms / 3600000)).padStart(2, "0");
    const mm = String(Math.floor((ms % 3600000) / 60000)).padStart(2, "0");
    const ss = String(Math.floor((ms % 60000) / 1000)).padStart(2, "0");
    return `${hh}:${mm}:${ss}.${String(ms % 1000).padStart(3, "0")}`;
  };
  // Cue text is markup: a bare "<" would start a tag and hide the rest of the line.
  const esc = (t) => t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const said = keys.filter((k) => k.say);
  return "WEBVTT\n\n" + said.map((k, i) => `${i + 1}\n${stamp(k.at)} --> ${stamp(said[i + 1]?.at ?? duration)}\n${esc(k.say)}\n`).join("\n");
};

const { chromium } = await loadPlaywright();
const browser = await launch(chromium);
const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
await page.goto(`${pathToFileURL(resolve(input)).href}?export`);
await page.waitForFunction(() => window.__anim);
await page.evaluate(() => document.fonts.ready);
if (!captions) await page.addStyleTag({ content: ".ca-caption{display:none!important}" });
const { duration, keys } = await page.evaluate(() => ({ duration: window.__anim.duration, keys: window.__anim.keys }));
const frames = Math.round(duration * fps);
const dir = await mkdtemp(join(tmpdir(), "anim-"));
// The frames are removed whatever happens: a failed export must not leave
// hundreds of PNGs in the temp folder.
const t0 = Date.now();
let failed = false;
// Outputs are written under .partial names and renamed over the old ones only
// once everything worked: a failed export keeps the last good one.
const partial = (f) => f.replace(/(\.[^.]+)$/, ".partial$1");
const finals = [out, out.replace(/\.[^.]+$/, ".vtt"), ...(gif ? [resolve(gif)] : []), ...(poster ? [resolve(poster)] : [])];
try {
  for (let i = 0; i <= frames; i++) {
    await page.evaluate((t) => window.__anim.seek(t), i / fps);
    await page.screenshot({ path: join(dir, `${String(i).padStart(6, "0")}.png`), clip: { x: 0, y: 0, width, height } });
  }
  if (poster) {
    const last = keys.at(-1).at + 1.2;
    await page.evaluate((t) => window.__anim.seek(t), Math.min(duration, last));
    await page.screenshot({ path: partial(resolve(poster)), clip: { x: 0, y: 0, width, height } });
  }
  await browser.close();
  if (errors.length) {
    console.error(`page errors: ${errors.join(" | ")}`);
    failed = true;
  } else {
    await mkdir(dirname(out), { recursive: true });
    const ff = (argv) => {
      const r = spawnSync("ffmpeg", ["-loglevel", "error", "-y", ...argv], { stdio: "inherit" });
      if (r.status !== 0) throw new Error(`ffmpeg failed: ${argv.join(" ")}`);
    };
    const done = [[partial(out), out]];
    ff(["-framerate", String(fps), "-i", join(dir, "%06d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart", done[0][0]]);
    const vttFile = out.replace(/\.[^.]+$/, ".vtt");
    await writeFile(partial(vttFile), vtt(keys, duration));
    done.push([partial(vttFile), vttFile]);
    if (gif) {
      const pal = join(dir, "palette.png");
      const g = resolve(gif);
      ff(["-i", done[0][0], "-vf", "fps=12,scale=720:-1:flags=lanczos,palettegen=stats_mode=diff", pal]);
      ff(["-i", done[0][0], "-i", pal, "-lavfi", "fps=12,scale=720:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4", partial(g)]);
      done.push([partial(g), g]);
    }
    if (poster) done.push([partial(resolve(poster)), resolve(poster)]);
    // Check every destination first, so a bad one (say --poster names a folder)
    // fails before any finished file has replaced the old one.
    for (const [, to] of done) if ((await stat(to).catch(() => null))?.isDirectory()) throw new Error(`${to} is a folder; nothing was replaced`);
    for (const [from, to] of done) await rename(from, to);
  }
} finally {
  await browser.close().catch(() => {});
  await rm(dir, { recursive: true, force: true });
  // Any .partial files a failed export left behind.
  for (const f of finals) await rm(partial(f), { force: true });
}
if (failed) process.exit(1);
console.log(`wrote ${out} (${frames + 1} frames at ${fps} fps, ${duration}s, rendered in ${((Date.now() - t0) / 1000).toFixed(1)}s)`);
console.log(`wrote ${out.replace(/\.[^.]+$/, ".vtt")}`);
if (gif) console.log(`wrote ${resolve(gif)}`);
