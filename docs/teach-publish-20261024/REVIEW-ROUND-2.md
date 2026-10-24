# Publication review round 2

Baseline: primary `d4e2ca1`, exported secondary `9bc6cbdf64eb8da26611cf91d7981c88f5e35880`.
Product and ordinary regression source commit: `8dad15db7ebd684c54070f61bdfc256bab6e7260`.
All three new Codex P2 findings reproduce. The fixes change product behavior and
ordinary regressions only; governing files, schemas, limits, compatibility engine,
original 22 checks and historical receipts remain unchanged.

| Comment | Evidence and repair |
| --- | --- |
| 4367995180 | A demonstrated recall followed by a wrong or aided answer still printed demonstrated and disappeared from future due reviews. The existing reschedule branch now clears the flag. A core regression exercises both outcomes, preserves the earlier qualifying result, checks next-session scheduling and re-earns demonstrated status with a future correct unaided answer. |
| 4367995184 | An isolated exact baseline checkout built the one-lesson index course successfully but left only index.html containing the map. Reserve only index and its case variants for lesson IDs in manifest/snapshot validation and the actual builder path. The fixed command fails without producing index.html. A valid lesson-one course produces byte-identical lesson and landing-page HTML against baseline. Ordinary tests cover validation, CLI refusal, and the builder guard even if upstream validation is bypassed. Course IDs and other valid lesson IDs retain their prior namespace. |
| 4367995188 | Opening the synthetic standalone poster SVG and clicking its javascript reference executed a local DOM marker. Poster preparation now imports the same safeSourceUrl HTTP/HTTPS allowlist used by HTML exports. Rejected source URLs retain inert provenance text; only safe external URLs and authored local summary links become anchors. The fixed standalone click stays inert, and source title escaping remains intact. No private data or network request is used. |

The first baseline build probe loaded a current helper from a subprocess and was
rejected before reaching the old collision. That setup failure is retained. The
successful reproduction then extracted exact baseline teacher Git objects into a
temporary directory so every helper used the same baseline.

## Verification

All commands use `PYTHONDONTWRITEBYTECODE=1`; the Python suite uses cached
Headroom Python 3.13.17. Browser control uses the scoped existing runtime env and
Chromium 153 without new flags or isolation changes.

- `python skills/teacher/scripts/tests/test_teacher.py Scripts.test_later_failed_or_aided_recall_returns_and_can_be_reearned -v`:
  [baseline failures](round-2/recall-red.txt); the full core rerun includes the same assertion.
- `python -m unittest discover -s skills/teacher/skills/course/scripts -p test_safe_course.py -v`:
  [RED](round-2/course-red.txt) / [9 GREEN tests](round-2/course-green.txt).
- Exact Git-object baseline builder probe, fixed CLI refusal and valid-output
  comparison: [receipt](round-2/course-build-red.txt),
  [preserved setup failure](round-2/course-build-red-setup.txt).
- `node docs/teach-publish-20261024/review-round-2-poster.mjs`:
  [RED local marker](round-2/poster-red.json) / [3 GREEN browser controls](round-2/poster-green.json).
- Full existing portable selection plus affected course checks:
  [exact commands and output](round-2/portable-green.json). Vendor verification
  has 0 problems, wrapper distribution matches 759 embedded files, core has 72
  tests with 2 expected primary fixture skips, discovery has 8 tests, Manim
  resolution has 9 tests, safe-course has 9 tests and Node has 21 tests.
- The poster source regression is in the existing Node test selection; recall is
  in the existing core suite. Secondary portable CI also runs safe-course checks.
- `git diff --check` passes for these repairs.

The edited series, course and explorable modules are native teacher code, so no
vendored hash entry requires rewriting. Existing vendor verification passes.
These results establish no fresh narrated-container or subjective learning claim.
The root agent owns release checks and remote operations. Secondary provenance
records the final primary commit outside the exact copied skill trees.
