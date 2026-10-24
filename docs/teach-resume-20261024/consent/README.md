# Consent-aware course validation adoption

The whole-course executor now uses `course-consent/v2`. Its declined-consent
branch requires session progress to work without local/session storage writes
and to reset on reload. Its affirmative branch checks progress and consent
resume; its withdrawal branch checks deletion of course keys and reset on reload.
The original map, keyboard, quiz, video-offer, outline, notes and page-error
assertions remain. [AUTHORITY.md](AUTHORITY.md) records approval and source hashes.

Run normal course validation as before:

```sh
python3 skills/teacher/skills/course/scripts/test_course.py REVIEWED_COURSE --trust-authored-code
```

The explicit historical path remains available:

```sh
python3 skills/teacher/skills/course/scripts/test_course.py REVIEWED_COURSE --trust-authored-code --course-checker v1
node skills/teacher/skills/course/scripts/check_course_page.mjs BUILT_COURSE/index.html
```

`--course-checker v2` selects the same method as the default. Restricted Docker
validation copies both checkers using the existing `copy_tools` route and selects
v2 through `test_course.py`; no sandbox limit or supervisor behavior changed.
The prior sandbox README's consent-check limitation is a historical observation
superseded by this separately approved method adoption. Other boundaries still
apply, including review before executing authored code on the host.

The raw receipts here cover a real restricted-image whole-course success, a
deliberate private-snapshot course-page error that fails v2 and prevents
publication, unchanged isolation/cancellation tests, and first-party fixture
comparisons. The historical checker still produces `18 passed, 1 failed` on the
single-lesson fixture. This failure is reproduced, not erased.

The two-lesson fixture exercises Tab/Enter traversal and remote video-offer/
caption routing using blocked placeholder URLs. It creates no narrated media
and supplies no playback, subjective listening or human-learning evidence.
No real learner state, private bank or installed skill was used. Browser state
and temporary fixture directories are discarded. The first fixture script
attempt rejected the legacy output's trailing space; trimming output lines
corrected that assertion. Two later attempts correctly refused a disposable
manifest that had acquired a second hard link. Recreating only the temporary
fixture inputs restored the required one-link boundary. The source of that
extra link was not established. All three failed attempt logs are retained.

Reproduce the first-party comparisons from the repository root:

```sh
source /Users/prax/.local/share/prax-teach/runtime/v3/env.sh
python3 docs/teach-resume-20261024/consent/verify_method.py
```

The script uses only the reviewed repository fixture and creates temporary
inputs beneath the Task 1 plan workspace. Its text outputs and JSON receipt
are written here. Preserve the recorded receipts before rerunning it.

`fixture-receipt.json` preserves exact child output strings, including v1's
trailing space. The matching text files trim line-end whitespace for Git.
