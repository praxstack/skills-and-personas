# Where the teacher engine lives

This folder, `skills/teacher/` in praxstack/skills-and-personas, is the main copy
of the teacher engine. Make every change here first.

Other repos carry a copy and take it from here:

- praxstack/kai-mori-fanout-sh keeps it at `teacher/`. To bring it up to date,
  copy this folder over that one in a fanout-sh checkout and commit the result
  there:

  ```sh
  rm -rf kai-mori-fanout-sh/teacher
  cp -R skills-and-personas/skills/teacher kai-mori-fanout-sh/teacher
  ```

  Then run fanout-sh's own checks (`npm test`, `npm run test:teacher`,
  `npm run build:courses`) before committing.

  Don't edit fanout-sh's `teacher/` directly. A fix found there gets made here
  first, then copied across, so the two never drift apart again.

Site-specific settings stay out of the engine. The course catalog's brand
defaults to Kai Mori, and `build_course.py --brand` changes it. The narration
cache folder is `NARRATE_CACHE`. Tests that read a site's own files (its
`courses/` or `public/favicon.ico`) run only when the engine sits inside that
site, and skip otherwise.

The vendored skills under `skills/` (the video skills, teach-pro-max and the
rest) have their own upstreams, listed in `VENDOR.json`. Change those upstream
and run `scripts/vendor.py sync`. A change made here is recorded with
`scripts/vendor.py record`.
