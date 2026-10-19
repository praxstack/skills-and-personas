# Portable lesson exports

Use one authored lesson and its normal builder. The exporter evaluates the built page in Chromium, runs its actual model, and captures the real mechanism figure for every step. There is no topic-specific renderer and no second implementation of the model.

```sh
python3 skills/teacher/skills/explorable/scripts/build.py lesson.js -o explorer.html
node skills/teacher/skills/explorable/scripts/bundle_lesson.mjs explorer.html --out lesson-bundle
```

Requirements: Node.js, the existing Playwright loader and Chromium. Set `PLAYWRIGHT_MODULE` and `CHROMIUM_PATH` when these are provisioned outside the project. Source pages must be self-contained; export blocks remote network requests. Output belongs in the project’s deliverables directory, never in a skill directory.

The command writes:

| Artifact | What it contains |
| --- | --- |
| `explorer.html` | The source lesson’s actual executable model and controls, plus a visible static link and the complete static explanation in `noscript`. Practice stays optional and storage consent stays off by default. |
| `still.svg`, `still.png` | An editable 1440 × 900 landscape mechanism figure and its real Chromium PNG render. The first step is the default; choose another with `--still-step 2` (one-based), or `LESSON.stillStep: 1` (zero-based). |
| `still.html` | The figure, evaluated readouts, its explanation and sources. |
| `qa.html` | Native disclosure sections that open explanations immediately. No answer is required. Alternate explanations include their own evaluated figure when they change parameters. |
| `cards.html`, `cards.tsv` | Optional review cards. Each carries lesson title, step context, explanation and source provenance. The HTML reveals answers only on request; TSV has HTML fields and Anki import directives. |
| `static.html` | The complete explanation, every step figure, readouts, questions with answers, alternate explanations, notes, authored code, limitations and sources. Works with JavaScript disabled. |
| `figures/*.svg` | Editable desktop and authored mobile snapshots of each evaluated step and parameter-changing alternate explanation. |
| `lesson-data.json`, `bundle-manifest.json` | Serializable display content, evaluated parameters/state and provenance. Functions stay in the real explorer; they are not serialized as executable substitutes. The manifest hashes the original built source. |

## Sources and boundaries

Author `LESSON.sources` as an array of `{title, url, note}` records; `locator` is also accepted. Step-specific `sources` are combined with lesson sources. `LESSON.limits` accepts a string or array of strings and is visible in every HTML format. The still carries numbered, clickable source credits linked to their full URLs and to the complete companion reference list. Poster titles and footers use measured SVG text bounds; an unfit display title/note fails explicitly instead of being silently clipped. `poster-layout.json` records those bounds and the reserved mechanism region. Include the assumptions and domain limits needed to interpret the model accurately. Author a narrow figure layout (`viewBox(narrow)` and `kit.narrow`) when the mechanism needs one: the exporter captures that actual 390 px layout for responsive pages and cards. It does not invent a new layout or certify a wide-only figure as readable on a phone.

Missing external references are disclosed visibly and in the manifest; the original lesson link identifies provenance, not independent fact verification. An export is not a factual audit or proof that someone learned the concept. Inspect the actual desktop/mobile renders and the explanation quality before delivery.

## Real interactive video

First render narrated media through the existing narration pipeline. Then export its matching MP4, VTT and timing sidecar:

```sh
python3 skills/teacher/skills/explorable/scripts/narrate.py explorer.html -o lesson.mp4
node skills/teacher/skills/explorable/scripts/bundle_lesson.mjs explorer.html \
  --out lesson-bundle --video lesson.mp4 --timing lesson.timing.json
```

`lesson.vtt` must sit beside the supplied MP4. The exporter validates the MP4 with `ffprobe`, checks duration, cue timings and scene count, and reads the source page’s actual `__filmExport.scenes` and `sceneStates`. A step can produce several narrated scenes. Timing is never inferred from the number of lesson steps.

These inputs add `interactive-video.html`, `lesson.mp4`, `lesson.vtt` and `lesson.timing.json`. Without them, the command explicitly reports that interactive video was not exported. It does not fabricate media or a video-completion claim.

The interactive page provides native video controls, captions, chapters, transcript, replay, speed and pause/resume. “Explore this moment” pauses without seeking and sends the selected scene’s parameters to the original explorer through its `teach:set-params` message interface. Resuming keeps the video playhead. The copied explorer scrolls its own viewport to the genuine figure after a scene message, so the model and controls are immediately available inside the iframe. The copied explorer keeps the same model and genuine controls. No prediction gate or progress-consent flag is added.

All assets are relative local files. Captions use the supplied VTT text through a local Blob URL to avoid Chromium’s `file://` caption-origin restriction. Iframe communication uses `postMessage` rather than cross-origin DOM access. Native playback and the complete static lesson remain available when the interactive features cannot run.
