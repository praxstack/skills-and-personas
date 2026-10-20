# Base-rates causal candidate

Seven authored visual stages preserve the original exact frequency model while
showing selections move and the denominator change. This is a separate
candidate; the historical exemplar remains untouched.

Source: `source/lesson.lesson.js`, `source/course.json`. Final local deliverables
are in `results/final-verified/bundle/`: `still.png`/`still.svg`, `explorer.html`, `qa.html`,
`cards.html`, `lesson.mp4`, and `interactive-video.html`. Static full prose and
matching captions/timing accompany them. Generated media/results are ignored
by Git. The worked authoring reference is
`skills/teacher/references/MECHANISM-STORYBOARD-EXAMPLE.md` in the repository.

## Reproduce in a fresh output directory

Run from the repository root after explicitly reviewing/building the media
image described in `skills/teacher/skills/course/scripts/README.sandbox.md`.
Pass your reviewed immutable local image ID and explicit Docker context. The
historical local setup used `colima-teach-security`; a recipient must build and
inspect their own image. No script changes the global context.

```sh
python3 examples/teach-visual-candidate/base-rates/reproduction/render.py render-04 --no-video --image "$MEDIA_IMAGE" --docker-context "$DOCKER_CONTEXT"
python3 examples/teach-visual-candidate/base-rates/reproduction/narrate.py
python3 examples/teach-visual-candidate/base-rates/reproduction/render.py new-candidate --image "$MEDIA_IMAGE" --docker-context "$DOCKER_CONTEXT"
python3 -m unittest discover -s skills/teacher/skills/course/scripts -p test_render_refusal.py -v
```

Output directories must be new. Existing receipts are retained, never
silently overwritten. `render.py` copies source bytes into private single-link
files because this workspace mirrors tracked files through hardlinks. It then
calls the existing sandbox adapter; lesson JavaScript executes only inside
Docker. `narrate.py` reads inert exported scene prose, uses local macOS Samantha
TTS, and assembles container PNGs with native ffmpeg. There is no paid voice
service or runtime network setup.

The fixed render helper targets this seven-scene frequency example and still
step 5; it is not a general course-rendering API. Nine frames per scene provide
sampled causal motion with holds, not fluid full-rate animation. The ordinary
Film tab switches settled states. Whole-course `validate` remains a separate
command and still fails its pre-existing course progress-consent expectation.
Consult the task report and receipts before making a completion claim.

The interactive bundle uses VP9 video plus Opus audio in an MP4 container,
which the reviewed Chromium runtime can actually play. The separate
`source/videos/base-rates-h264.mp4` is an H.264/AAC compatibility download from
the same final frames, narration and timing. The reviewed headless Chromium
does not advertise H.264 support; that does not make the H.264 file invalid.
Both files have complete constant-rate video tracks through the last narrated
hold and pass native decoding. Browser coverage is the reviewed Chromium
runtime; no universal browser-compatibility claim is made.

`render.py` now checks both existing QA return-code receipts and every existing
render check/errors/network receipt. An export exit code alone is insufficient.
These checks do not grant human visual acceptance or full-course acceptance.
Task 8 remains unaccepted: three consecutive narrated playback passes were not
achieved. The completed local audio/video stays available as an unaccepted demo;
macOS `say` narration is platform-specific. CI uses a labelled synthetic codec
fixture with the actual exemplar to exercise runtime behavior, not voice quality.
