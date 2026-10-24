---
name: course
description: Turn a set of lessons into a course with a map of the whole subject (lessons placed by prerequisite, hand-drawn arrows), each lesson offering Quick explain, Teach me (interactive), Watch (film or narrated video), Read and run the code, Quiz me, and a Learning, Done or Skip status; plus an outline and a notes sheet kept apart from the lessons, and a catalog of courses. Use when a subject needs more than one sitting. Builds static pages in the lesson-notebook look and tests every lesson's code, interactions and looks in one command.
---

# Course

One lesson teaches one idea. A course is a map of ideas, so the learner can see the whole subject, where they are, and choose the next step and the medium they want, as often as they like.

## Layout

```
courses/<id>/
  course.json            id, title, subtitle, level, prereqs (other course ids), shared (model scripts), lessons
  <model>.js             optional shared model, loaded before every lesson (window.Something = ...)
  lessons/*.lesson.js    explorables (see ../explorable/SKILL.md)
  lessons/*.anim.js      concept animations (see ../concept-animation/SKILL.md)
  videos/<lesson-id>.vtt captions of the narrated videos (in git; the .mp4 beside them is not)
courses/videos.json      "<course-id>/<lesson-id>.mp4": Vercel Blob URL of each narrated video
```

Each `lessons[]` entry: `id` (letters, digits, `-` and `_`; it becomes a file name), `file`, `title`, `needs` (ids of lessons it builds on, which place it on the map), `minutes`, `summary` (the plain one- or two-sentence Quick explain).

## Build and test

Course lessons are executable JavaScript. The builder validates every manifest
path first and refuses to execute lesson code unless the caller passes
`--trust-authored-code` after reviewing all lesson and shared files. For third-party courses, use the explicit Docker sandbox below. The trust flag
allows host execution; it does not provide isolation.

```sh
python3 scripts/build_course.py courses/segment-tree -o site/segment-tree --trust-authored-code     # one reviewed course
python3 scripts/build_course.py --catalog courses -o site --trust-authored-code                      # reviewed catalog
python3 scripts/test_course.py courses/segment-tree --trust-authored-code       # reviewed code, interactions and looks, then the course page
```

### Restricted whole-course execution

`scripts/sandbox_course.py` runs the existing public extractor, builder, or full
browser checks in a disposable Docker container. Supply an explicitly reviewed,
locally present image ID (`sha256:…`); runtime execution never pulls or installs
anything. See [sandbox setup](scripts/README.sandbox.md) for the build recipe and
tested image IDs.

```sh
python3 scripts/sandbox_course.py extract courses/segment-tree -o extracted --image "$COURSE_IMAGE" --docker-context colima-teach-security
python3 scripts/sandbox_course.py build courses/segment-tree -o site-segment-tree --image "$COURSE_IMAGE" --docker-context colima-teach-security
python3 scripts/sandbox_course.py validate courses/segment-tree -o validated --image "$COURSE_BROWSER_IMAGE" --docker-context colima-teach-security --timeout 180
```

Each destination must be new and its existing parent must contain no symlink
components. Extraction writes `course.json`; build writes the ordinary relative
static pages; validation runs `test_course.py` including interaction checks and
visual QA screenshots. Validation requires the reviewed Playwright/Chromium
image and fails closed without it. The separately named consent-aware evaluator v2 was approved and adopted on
2026-10-24 (`bf0bcf9`); full validation selects that canonical version. The old
reload-without-consent failure remains historical evidence. The final playback
source `eaa524e` passed three consecutive original narrated fresh-container runs,
each 22/22 plus lesson/visual QA and zero phase PID-limit events. Both disclosed
independent cases pass later regression; their earlier failures remain retained.
Current delivery and exact scope: `deliverables/teach-resume-20261024/README.md`
in the full checkout. These results do not imply a stable release or activation.
Course input is limited to 128 lessons and
64 MiB, including local videos; output to 1,024 entries and 64 MiB. Local MP4/VTT
files and a `videos.json` beside a linked course keep their existing behavior.

The container has no network or host credentials, uses a non-root UID, read-only
root/input/tools, 512 MiB memory, one CPU, 64 PIDs/threads, and bounded temporary
storage. The default wall timeout is 90 seconds (maximum 300). The supervisor
waits for the authored process, kills and reaps its descendants (including
`setsid` children), then streams output. The host validates the bounded archive
and publishes it only after clean container exit. No writable host output is
mounted into authored code. Failures remove the container and publish no result;
a host disk error during final publication can leave a partial new private
folder, which is reported.

This adapter handles one course per invocation. Catalog generation, narration,
remote fetches, video publication, and opening generated pages on the host are
outside its supported modes. Browser code runs only in the container during
`validate`; generated pages still contain authored JavaScript and should be
reviewed before opening outside the sandbox.

`--fragment` builds pages for hosts that wrap them (Claude artifacts). Pages are single files and work from disk. For a web host, pass `--base /courses/` (the URL path the output folder is served at): links become root-absolute, so they still work when the host serves `/courses/ai-math/` as `/courses/ai-math` (clean URLs, no trailing slash, as on Vercel).

The catalog page carries a brand name over its heading and in its title. It defaults to Kai Mori; `--brand "Your Name"` changes it and `--brand ""` drops it.

## Narrated videos on Vercel Blob

`scripts/narrate_course.py` writes `videos/<lesson-id>.mp4` and its `.vtt`. The MP4s are kept out of git (`.gitignore`); the captions are committed. When building, a lesson's video is the local MP4 if it exists (copied beside the pages, for previews), else its URL in `courses/videos.json`, else the lesson gets no video button. Captions are always served from beside the page, so a video on Blob still gets same-origin captions; the `<video>` has no `crossorigin` attribute, so Blob needs no CORS for it.

Publish the MP4s and write their URLs into the manifest:

```sh
node scripts/publish_videos.mjs [videos-root] --dry-run                        # list what would be uploaded, no token needed
VIDEOS_BLOB_TOKEN=... node scripts/publish_videos.mjs [videos-root]            # upload, then commit courses/videos.json
```

The token is the Blob store's read-write token. `KAI_MORI_VIDEOS_BLOB_TOKEN` also works, for sites that already use that name.

`videos-root` is a folder laid out like `courses/` (`<course>/videos/<lesson-id>.mp4`), `courses/` by default. Each lesson listed in a `course.json` goes to `courses/<course-id>/<lesson-id>.<sha8>.mp4`, where `<sha8>` is the start of the file's sha256: public, `video/mp4`, cached for a year. The name is content-addressed, so a re-rendered video gets a new URL (no stale copies in browsers or CDNs) and the long cache is safe. A video is skipped only when its manifest URL already carries the same digest, and the manifest is saved after each upload. `narrate_course.py` skips lessons that already have a manifest URL unless `--force`. `test_course.py` reports each lesson as `video local`, `video on Blob` or `no video`, and the course page check fails if a lesson offers a video button without a video.

## What the course page does

- **Map**: lessons left to right by prerequisite (top to bottom on phones), arrows drawn by the pen. Click a lesson to open its panel.
- **Panel**: Learning / Done / Skip (remembered in the browser), Quick explain, Why it mattered, and the same idea in every medium: Teach me, Watch (the narrated video when there is one, else the lesson's film), Read and run the code, Quiz me, Notes. "Can you say it back?" shows the lesson's explain-back question.
- **Quiz me**: the lesson's questions, answers resolved from its model at build time, options in a shuffled order; try first, then see why. Questions marked `needsFigure: true` (they ask about values only the figure shows) stay in the lesson. The score is a clue, not a finish line: a miss links back to its step.
- **Outline** and **Notes**: separate views. Notes gather every lesson's margin notes, mix-ups and deeper questions on one sheet for review.

Patterns from roadmap.sh, Educative and Brilliant (see `teacher/references/DESIGN-INSPIRATION.md`).
