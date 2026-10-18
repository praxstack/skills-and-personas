# Where the teacher engine lives

The main copy of this engine is `skills/teacher/` in praxstack/skills-and-personas.
Make every change there first. If you're reading this file anywhere else, you're
in a copy: change the main copy, then sync.

## Copies

- praxstack/kai-mori-fanout-sh keeps a copy at `teacher/`. Don't edit it
  directly. A fix found there gets made in the main copy first, then synced.

To sync, run this from the folder that holds both checkouts. It copies the
committed engine, so local edits and untracked files in skills-and-personas
don't come along:

```sh
git -C skills-and-personas status --porcelain skills/teacher   # should print nothing
rm -rf kai-mori-fanout-sh/teacher && mkdir kai-mori-fanout-sh/teacher
git -C skills-and-personas archive HEAD skills/teacher | tar -x --strip-components=2 -C kai-mori-fanout-sh/teacher
```

Then run fanout-sh's own checks before committing there: `npm test`,
`npm run test:teacher`, `npm run build:courses`, `npm run test:browser` and
`npm run test:courses`.

## Site settings

Nothing site-specific is fixed in the engine:

- The course catalog's brand defaults to Kai Mori. `build_course.py --brand`
  changes it, and `--brand ""` drops it.
- `publish_videos.mjs` reads the Blob token from `VIDEOS_BLOB_TOKEN`, or from
  `KAI_MORI_VIDEOS_BLOB_TOKEN` when that isn't set.
- Narration clips are cached in `~/.cache/kai-mori-voice`. Set `NARRATE_CACHE`
  to use another folder, and `KOKORO_DIR` for the voice model files.
- The few tests that read a site's own files (its `courses/` or
  `public/favicon.ico`) run only when the engine sits inside that site.

## Vendored skills

The skills listed in `VENDOR.json` (the video skills, teach-pro-max and the
rest) have their own upstreams. Change them upstream and run
`scripts/vendor.py sync`. If one has to change here, record it with
`scripts/vendor.py record NAME --note ...`. `eli` carries one recorded local
change, because its upstream is a local snapshot.
