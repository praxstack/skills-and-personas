#!/usr/bin/env node
// Upload the courses' narrated videos to Vercel Blob and record their URLs in
// courses/videos.json, which build_course.py reads when an MP4 isn't on disk.
//
//   VIDEOS_BLOB_TOKEN=... node publish_videos.mjs [videos-root] [--courses courses] [--dry-run]
//
// The token is the Blob store's read-write token. KAI_MORI_VIDEOS_BLOB_TOKEN
// (the name kai-mori-fanout-sh uses) is read when VIDEOS_BLOB_TOKEN isn't set.
//
// videos-root is laid out like courses/ (<course>/videos/<lesson-id>.mp4) and
// defaults to the courses folder itself. Only lessons listed in a course.json
// are uploaded. Uploads are content-addressed: the pathname carries a short
// sha256 of the file, courses/<course-id>/<lesson-id>.<sha8>.mp4, so a
// re-rendered video gets a new URL and a year of caching is safe. A video is
// skipped only when its manifest URL already ends in that same digest. The
// manifest is rewritten after every upload, so an interrupted run keeps what
// it finished. --dry-run lists what would be uploaded and needs no token.

import { readFile, writeFile, rename, stat, readdir, open, realpath } from "node:fs/promises";
import { existsSync, realpathSync, constants } from "node:fs";
import { createHash } from "node:crypto";
import { join, resolve, dirname, relative, isAbsolute } from "node:path";
import { fileURLToPath } from "node:url";

// The site's courses/: the one beside the engine when it sits at <site>/teacher/,
// so the folder this runs from doesn't matter; else the one in the current folder.
const SITE = resolve(dirname(fileURLToPath(import.meta.url)), "../../../..");
const DEFAULT_COURSES = existsSync(join(SITE, "courses")) ? join(SITE, "courses") : resolve("courses");
const YEAR = 365 * 24 * 60 * 60;

export function parseArgs(argv) {
  const a = { dryRun: false, courses: DEFAULT_COURSES, root: null };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--dry-run") a.dryRun = true;
    else if (argv[i] === "--courses") a.courses = resolve(argv[++i]);
    else if (argv[i] === "-h" || argv[i] === "--help") a.help = true;
    else if (!argv[i].startsWith("-") && !a.root) a.root = resolve(argv[i]);
    else throw new Error(`unknown argument ${argv[i]}`);
  }
  a.root ??= a.courses;
  return a;
}

const SAFE_ID = /^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?$/;

export function requireSafeId(value, label) {
  if (typeof value !== "string" || !SAFE_ID.test(value) || value.includes("..")) {
    throw new Error(`${label} must be a portable identifier (letters, digits, dot, dash or underscore)`);
  }
  return value;
}

function requireInside(root, target, label) {
  const rel = relative(root, target);
  if (!rel || rel === ".." || rel.startsWith(`..${process.platform === "win32" ? "\\" : "/"}`) || isAbsolute(rel)) {
    throw new Error(`${label} escapes its declared root`);
  }
}

async function openBoundRegularFile(root, file) {
  const canonical = await realpath(file);
  requireInside(root, canonical, "video file");
  const noFollow = constants.O_NOFOLLOW || 0;
  const handle = await open(file, constants.O_RDONLY | noFollow);
  try {
    const [opened, named] = await Promise.all([handle.stat(), stat(canonical)]);
    if (!opened.isFile()) throw new Error("video input must be a regular file");
    if (opened.nlink !== 1) throw new Error("video input must not be a hard link");
    if (opened.dev !== named.dev || opened.ino !== named.ino) {
      throw new Error("video input changed while it was being validated");
    }
    return { handle, size: opened.size };
  } catch (error) {
    await handle.close();
    throw error;
  }
}

export async function sha8(handle) {
  const h = createHash("sha256");
  for await (const chunk of handle.createReadStream({ start: 0, autoClose: false })) h.update(chunk);
  return h.digest("hex").slice(0, 8);
}

// Is the manifest URL for this video the upload of these exact bytes?
export function isCurrent(url, v) {
  try {
    return new URL(url).pathname.endsWith(`/${v.pathname}`);
  } catch {
    return false; // empty or not a URL
  }
}

// Every lesson video found under root: { key, pathname, file, size, digest }.
export async function findVideos(coursesDir, root) {
  const out = [];
  const coursesRoot = await realpath(coursesDir);
  const videosRoot = await realpath(root);
  try {
    for (const entry of (await readdir(coursesDir, { withFileTypes: true })).filter((d) => d.isDirectory()).sort((a, b) => a.name.localeCompare(b.name))) {
      const dir = requireSafeId(entry.name, "course directory");
      const courseDir = await realpath(join(coursesDir, dir));
      requireInside(coursesRoot, courseDir, "course directory");
      const meta = join(courseDir, "course.json");
      if (!existsSync(meta)) continue;
      const course = JSON.parse(await readFile(meta, "utf8"));
      const courseId = requireSafeId(course.id, "course id");
      if (!Array.isArray(course.lessons)) throw new Error(`course ${courseId} must have a lessons array`);
      for (const lesson of course.lessons) {
        const lessonId = requireSafeId(lesson?.id, `lesson id in ${courseId}`);
        const file = join(videosRoot, dir, "videos", `${lessonId}.mp4`);
        if (!existsSync(file)) continue;
        const { handle, size } = await openBoundRegularFile(videosRoot, file);
        const digest = await sha8(handle);
        out.push({
          key: `${courseId}/${lessonId}.mp4`,
          pathname: `courses/${courseId}/${lessonId}.${digest}.mp4`,
          file,
          handle,
          size,
          digest,
        });
      }
    }
    return out;
  } catch (error) {
    await Promise.allSettled(out.map((video) => video.handle.close()));
    throw error;
  }
}

async function main() {
  const a = parseArgs(process.argv.slice(2));
  if (a.help) {
    console.log(usage());
    return 0;
  }
  const manifestFile = join(a.courses, "videos.json");
  const manifest = existsSync(manifestFile) ? JSON.parse(await readFile(manifestFile, "utf8")) : {};
  const videos = await findVideos(a.courses, a.root);
  if (!videos.length) {
    console.error(`no lesson videos under ${a.root} (expected <course>/videos/<lesson-id>.mp4)`);
    return 1;
  }
  const token = process.env.VIDEOS_BLOB_TOKEN || process.env.KAI_MORI_VIDEOS_BLOB_TOKEN;
  if (!a.dryRun && !token) {
    console.error("set VIDEOS_BLOB_TOKEN or KAI_MORI_VIDEOS_BLOB_TOKEN (the Blob store's read-write token), or pass --dry-run");
    return 1;
  }
  const put = a.dryRun ? null : (await import("@vercel/blob")).put;
  // Written beside it and renamed over it, so a crash mid-write can't leave
  // half a videos.json (the rename is atomic on one file system).
  const save = async () => {
    const tmp = `${manifestFile}.${process.pid}.tmp`;
    await writeFile(tmp, JSON.stringify(Object.fromEntries(Object.entries(manifest).sort()), null, 2) + "\n");
    await rename(tmp, manifestFile);
  };
  let uploaded = 0;
  let skipped = 0;
  let bytes = 0;
  try {
    for (const v of videos) {
      const mb = (v.size / 1e6).toFixed(1);
      if (isCurrent(manifest[v.key], v)) {
        console.log(`skip   ${v.key} (${mb} MB, ${v.digest} already on Blob)`);
        skipped++;
        continue;
      }
      if (a.dryRun) {
        console.log(`upload ${v.key} (${mb} MB) -> ${v.pathname}`);
        uploaded++;
        bytes += v.size;
        continue;
      }
      const blob = await put(v.pathname, v.handle.createReadStream({ start: 0, autoClose: false }), {
        access: "public",
        addRandomSuffix: false,
        allowOverwrite: true,
        contentType: "video/mp4",
        cacheControlMaxAge: YEAR,
        multipart: v.size > 50e6,
        token,
      });
      manifest[v.key] = blob.url;
      await save();
      console.log(`ok     ${v.key} (${mb} MB) ${blob.url}`);
      uploaded++;
      bytes += v.size;
    }
  } finally {
    await Promise.allSettled(videos.map((video) => video.handle.close()));
  }
  if (!a.dryRun) await save();
  const verb = a.dryRun ? "would upload" : "uploaded";
  console.log(`${verb} ${uploaded} (${(bytes / 1e6).toFixed(1)} MB), skipped ${skipped}${a.dryRun ? "" : `; manifest ${manifestFile}`}`);
  return 0;
}

function usage() {
  return "usage: VIDEOS_BLOB_TOKEN=... node publish_videos.mjs [videos-root] [--courses courses] [--dry-run]";
}

// Compare real paths: run through a link (install.sh makes them), argv[1] is the link.
const isMain = () => {
  try {
    return realpathSync(process.argv[1]) === realpathSync(fileURLToPath(import.meta.url));
  } catch {
    return false;
  }
};
if (process.argv[1] && isMain()) {
  main().then(
    (code) => process.exit(code),
    (e) => {
      console.error(e.message || e);
      process.exit(1);
    },
  );
}
