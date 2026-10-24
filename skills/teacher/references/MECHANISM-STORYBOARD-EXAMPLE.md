# Worked example: collecting flags before changing the denominator

The product source and reproduction scripts live in
`examples/teach-visual-candidate/base-rates/`. Generated media stays there,
outside this skill tree and outside Git history. This is an authoring example
under the existing visual-quality requirements, not an additional acceptance gate.

The baseline base-rates film repeated the complete diagram in its first three
scenes. The candidate uses seven stages: populations, true selection, false
selection, collection, denominator expansion, changed prior, and zero false
flags. An explanation step is available without answering practice questions.

## Keep identity while changing geometry

`true-flag-segment` and `false-flag-segment` are semantic SVG identities. At 1%
base rate they represent 90 and 495 items. Collection changes their positions;
rescaling changes their widths. Their counts remain 90 and 495 throughout both
operations. Muted local-denominator reference bars stay behind after collection.
The source labels, direct outcome names and false-flag hatching make color
redundant. Zero false flags has exactly zero width, while the missed defective
count remains outside the selected group.

Each width has a stated denominator: the population strip uses 10,000; the
initial defective detail uses its own defective count; the common count bars
use at least 1,000; the expanded collected bar uses all flags. Never imply that
widths on different scales can be compared directly. Name the change of scale
while it happens, not just after it settles.

## Isolate presentation from arithmetic

The original `flags(p)` function and all three rate ranges/steps/defaults are
retained. A separate numeric `phase` parameter controls visibility and geometry
only. Every authored step and film scene sets all four parameters explicitly.
All controls omit phase. A changing prior or detector rate recomputes the same
model; a moving selection does not create fractional people.

The complete still exports step 5 (one-based): population, both rate
applications, collected denominator and excluded missed items are visible
together. Interactive scene 1 intentionally reveals only the populations.
Fixed narrative prose names its worked-example parameter assumptions; current
slider values are represented by the live figure and readouts.

## Observed export hooks and their limits

`__filmExport.frame(scene, u, captionProgress, settled)` interpolates numeric
parameters. The candidate samples nine frames per scene inside the reviewed
Docker boundary. Counts settle before narration and numerical captions begin.
Native local TTS and ffmpeg assemble those frames with holds into an MP4.
The selected-frame approach stays within the existing 1,024-entry/64 MiB
sandbox output limits; it produces visibly stepped motion rather than claiming
full-rate fluid animation.

The ordinary interactive Film tab changes between settled scenes. It does not
smoothly interpolate this geometry. The narrated MP4 contains the sampled
transformations. The interactive video bundle adds chapters, transcript and a
linked explorer using matching timing and model states.

The fixed `sandbox_course.py render` mode currently serves this one-lesson,
seven-scene example with still step 5 and the `base`/`hit`/`falseRate` model
contract. It is not a general arbitrary-course media service. Use its explicit
local immutable image and context; do not run authored JavaScript on the host.
`validate` remains separate and uses the approved consent-aware evaluator v2.
The earlier consent-checker failure remains historical evidence; current final
source eaa524e passes the three original narrated runs and disclosed-case
regressions. Export receipts do not establish human acceptance of visual quality.
