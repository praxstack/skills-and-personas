# Readable captions during a terminal still

The readable caption panel now derives text from the actual loaded TextTrack
cues at the video's current time. Normal cues keep their original interval;
prefirst silence and interior gaps stay blank. After the latest-ending cue,
the panel retains that real cue's text through a terminal still. Seek, replay,
track load and media time changes recalculate the panel. Caption toggles retain
their existing behavior. Native VTT contents, cue timing and track mode are
unchanged.

The first caption correction exposed a seek-readiness race in the immutable
regression: the caption wait succeeded before the media had current-frame data.
Its exact source and source-freeze receipt remain retained. The final correction
clears the panel while the media is seeking or readyState is below HAVE_CURRENT_DATA,
then refreshes on seek completion, loaded data and canplay. The focused actual
browser control additionally verifies blank text during every real seeking
event and data-ready state when text is shown. Its 13 branches pass in
`browser-seek-ready.txt`; final hashes are in `source-freeze-seek-ready.json`.

The initial independent holdout failure remains retained. Its diagnosed case
is disclosed, so a later rerun is regression evidence, not a new blind result.
No holdout input was read or changed by the implementer. Source freeze is in
`source-freeze.json`; the controller performs the independent replay separately.

`unit-tests.txt` records 7/7 passing tests, including native intervals, gaps,
terminal retention, seeking back, overlapping cues and unloaded/empty tracks.
`browser-test.txt` records a real Chromium 153.0.8010.12 run against the actual
generated video page, actual Blob-loaded VTT and reviewed real MP4. Its 11
branches cover prefirst silence, active cue, interior gap, final cue, terminal
still, native cue end, seek-back, replay clearing, toggles, unchanged native
cue times/text and page errors. Those ordinary functional tests use synthetic
cue text/times deliberately; they are not narrated acceptance media.

```sh
node --test skills/teacher/skills/explorable/scripts/bundle_templates.test.mjs
source /Users/prax/.local/share/prax-teach/runtime/v3/env.sh
node skills/teacher/skills/explorable/scripts/test_caption_tail.mjs /Users/prax/Developer/prax-teach-candidate-handoff-20261020/staging/media/lesson.mp4
```

The original uninstrumented narrated sequence is repeated with new labels;
the prior three passes remain intact. Both original render executors, both
course checkers and the consent executor remain frozen. The scheduling repair,
limits and isolation are unchanged. No sample wording or timestamp appears in
the product correction.

`baseline-adapter-clarification.json` is an additive metadata correction. The
old baseline receipt's `product` object described checkout hashes; the actual
baseline adapter was an exact bf0bcf9 scratch copy, already identified in its
separate receipt. Neither old receipt is rewritten.

The controller reports that the final immutable regression passed 22/22 original
checks and both lesson/visual QA with zero PID-limit events in 27.418 seconds.
The original frozen clip, metadata and assertions are unchanged. This result
is explicitly regression after disclosure; both earlier failures remain retained.

Three subsequent fresh-container uninstrumented original narrated renders passed
22/22 plus both QA checks in 27.194, 26.235 and 26.459 seconds. Every sampled
phase reports zero PID-limit events. Source MP4/VTT/lesson/timing hashes match
the original fixture, and all frozen method/pool hashes are unchanged. See
`runs.json` and the separate caption-narrated-1/2/3 receipts. Prior receipts
remain byte-identical. No additional full security-suite run was needed for
this caption-only correction; the prior 39/39 controls remain retained.
