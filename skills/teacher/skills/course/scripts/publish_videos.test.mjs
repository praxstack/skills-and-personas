import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, writeFile, symlink, link, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { findVideos, requireSafeId } from "./publish_videos.mjs";

async function fixture() {
  const root = await mkdtemp(join(tmpdir(), "publish-videos-"));
  const courses = join(root, "courses");
  const videos = join(root, "videos");
  await mkdir(join(courses, "course-one"), { recursive: true });
  await mkdir(join(videos, "course-one", "videos"), { recursive: true });
  await writeFile(join(courses, "course-one", "course.json"), JSON.stringify({
    id: "course-one",
    lessons: [{ id: "lesson-one" }],
  }));
  return { root, courses, videos };
}

async function close(videos) {
  await Promise.allSettled(videos.map((video) => video.handle.close()));
}

test("portable identifiers reject traversal and separators", () => {
  for (const value of ["../secret", "a/b", "a\\b", "..", ".", "a..b", " space"])
    assert.throws(() => requireSafeId(value, "id"));
  assert.equal(requireSafeId("lesson-1_a.b", "id"), "lesson-1_a.b");
});

test("a regular in-root video is bound to one descriptor", async (t) => {
  const f = await fixture();
  t.after(() => rm(f.root, { recursive: true, force: true }));
  await writeFile(join(f.videos, "course-one", "videos", "lesson-one.mp4"), "safe video");
  const found = await findVideos(f.courses, f.videos);
  t.after(() => close(found));
  assert.equal(found.length, 1);
  assert.equal(found[0].size, 10);
  assert.match(found[0].pathname, /^courses\/course-one\/lesson-one\.[0-9a-f]{8}\.mp4$/);
});

test("a symlinked video cannot disclose another file", async (t) => {
  const f = await fixture();
  t.after(() => rm(f.root, { recursive: true, force: true }));
  const secret = join(f.root, "secret.txt");
  await writeFile(secret, "do not upload");
  await symlink(secret, join(f.videos, "course-one", "videos", "lesson-one.mp4"));
  await assert.rejects(findVideos(f.courses, f.videos), /escapes|symbolic link|ELOOP/);
});

test("a hard-linked video is rejected", async (t) => {
  const f = await fixture();
  t.after(() => rm(f.root, { recursive: true, force: true }));
  const secret = join(f.root, "secret.txt");
  await writeFile(secret, "do not upload");
  await link(secret, join(f.videos, "course-one", "videos", "lesson-one.mp4"));
  await assert.rejects(findVideos(f.courses, f.videos), /hard link/);
});
