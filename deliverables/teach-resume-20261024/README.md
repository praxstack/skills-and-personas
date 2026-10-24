# Prax Teach candidate — 24 October 2026

Current source/package snapshot: `e97fe5b`; demonstrated runtime: `eaa524e`; governing method adoption: `bf0bcf9`.
This is an unaccepted local candidate. Final whole-branch review and release
choices are pending; nothing has been installed, published or activated.

- [Narrated interactive lesson](demo-eaa524e/bundle/interactive-video.html)
- [Complete static lesson](demo-eaa524e/bundle/static.html)
- [Explorer](demo-eaa524e/bundle/explorer.html) · [QA](demo-eaa524e/bundle/qa.html) · [Cards](demo-eaa524e/bundle/cards.html)
- [Original browser-tested VP9/Opus MP4](demo-eaa524e/bundle/lesson.mp4)
- [Historical alternate H264/AAC MP4](demo-eaa524e/lesson-h264.mp4) — same retained generation, no new browser certification
- [Complete source archive](source-e97fe5b/prax-teach-v3.0.2-source.zip)
- [Teacher](source-e97fe5b/teacher.zip) · [Teach Pro Max](source-e97fe5b/teach-pro-max.zip) · [Transcript pipeline](source-e97fe5b/transcript-pipeline.zip)
- [Archive/member hashes and modes](source-e97fe5b/RELEASE-MANIFEST.json) · [SHA256SUMS](source-e97fe5b/SHA256SUMS)

Both `source-e97fe5b/` and `repeat-e97fe5b/` were built from committed Git objects
and are byte-identical. The d8085a4 source archives and `demo/` preserve the
snapshot before the chapter precision repair. The eaa524e archives and
`demo-eaa524e/` contain the chapter-corrected runtime and demonstration; use the
`source-e97fe5b/` paths above for the current package.

The separately named consent-aware evaluator v2 is approved and adopted; its
canonical source is `skills/teacher/skills/course/scripts/check_course_page_v2.mjs`.
The legacy checker, original render assertions and historical receipts remain
unchanged. See [approval and adoption](../../docs/teach-resume-20261024/consent/AUTHORITY.md).

Playback diagnosis reproduced browser foreground pool pressure on the pinned
Chromium145 runtime; reducing that pool preserved the separate audio process at
64 tasks,512MiB,no swap and one CPU. The original real media remains byte-identical.
Readable captions now retain the real final cue during a terminal still, and
chapter lookup uses the browser's microsecond media timeline. No fixture wording,
native cue timing, authored scene metadata, limits or governing assertions changed.

The final original narrated sequence passed three consecutive fresh containers,
each22/22 original checks plus lesson and visual QA. Two disclosed immutable cases
also pass those original checks after repair. Their initial failures remain:
caption-tail, seek readiness and fractional chapter handoff; later replay is
regression evidence, not fresh blind validation. A separate new-fixture setup
reject and repeated chapter failure are retained as well.

- [Source-backed playback evidence](../../docs/teach-resume-20261024/playback/)
- [Preserved independent additional failure](../../docs/teach-resume-20261024/playback/additional-independent-failure.json)
- [Final immutable-case regressions](../../docs/teach-resume-20261024/playback/independent-final-precision-regressions.json)
- [Current cleanup, suites and preservation evidence](../../docs/teach-resume-20261024/cleanup/)

Engineering results do not establish subjective listening quality, human learning
or perfection. Host UI controls use Chromium153 and are distinct from pinned
Docker145 playback. Two teacher tests require an unrelated site fixture and are
explicitly skipped; scoped security suites have no skips. Actual authored Manim
rendering was not run. Explicit external credential paths keep their previous
semantics; manifest/output confinement is not blanket certification of every input.

All1546 installed v3.0.1 files and five resolved links are preserved. Source rollback
is `d246f6f`; installed rollback is
`/Users/prax/.local/share/prax-teach/releases/v3.0.1-33cfd55`.
Divergent portfolio identity/content and destructive history changes remain pending
separate exact ownership decisions. No public history was deleted.

Full regression orchestration and CI setup require the complete exact Git checkout,
including Git metadata, test utilities and the new-skills mirror. They are not
source-ZIP validation commands; the shipped runner and setup refuse an archive
clearly before running tests or provisioning dependencies. Individual included
skill checks and vendor/distribution verification retain their documented scope.
See [validation scope](../../scripts/TEACHER-CANDIDATE.md).
