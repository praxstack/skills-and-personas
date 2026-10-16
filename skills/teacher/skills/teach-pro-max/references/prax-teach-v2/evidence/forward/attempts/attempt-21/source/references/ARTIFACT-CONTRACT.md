# Markdown and HTML artifact contract

## Contents

1. [Canonical source](#canonical-source)
2. [Required HTML](#required-html)
3. [Learning interactions](#learning-interactions)
4. [Accessibility](#accessibility)
5. [Visual and source provenance](#visual-and-source-provenance)
6. [Optional Flint chart artifacts](#optional-flint-chart-artifacts)
7. [Build and parity](#build-and-parity)
8. [Acceptance checklist](#acceptance-checklist)

## Canonical source

Every durable instructional document starts as Markdown. Generate an HTML file with the same basename in the same directory.

```text
lessons/0001-index-prefixes.md
lessons/0001-index-prefixes.html
```

Rules:

- Edit Markdown, then regenerate HTML.
- Prefer `node <skill-dir>/scripts/render_markdown.mjs --trusted-root <workspace> <source.md>` for the bundled self-contained template; set `PRAX_MARKED_PATH` when `marked` is not on the normal Node resolution path.
- Never hand-edit generated teaching content in HTML.
- Put any template/CSS/renderer change in versioned source.
- Record the Markdown source path and SHA-256 in machine-readable HTML metadata and visible page provenance.
- Make regeneration deterministic. Use a fixed timestamp such as `SOURCE_DATE_EPOCH` when byte-for-byte reproducibility matters.
- Fail validation when HTML is missing or the recorded source hash is stale.

## Required HTML

Each standalone page must include:

- `<!doctype html>`, `lang`, UTF-8 charset, viewport, and a specific title;
- a skip link;
- semantic `header`, `nav` when needed, `main`, and `footer` landmarks;
- one `h1`, ordered heading levels, and stable unique anchors;
- readable line length and responsive typography;
- responsive tables or an alternate stacked representation;
- visible focus styles;
- source link, source SHA-256, and generation metadata;
- print styles;
- `prefers-reduced-motion` handling;
- a no-script/static path for essential content;
- no mandatory external CDN, tracking, font, or analytics request.

Optional enhancements require a separately versioned and tested runtime and must
not gate access:

- generated table of contents;
- theme control respecting system preference;
- reading-progress indicator;
- copy buttons for code;
- collapsible supporting detail;
- local search across a course.

Default authoring dialect is GFM plus reviewed static native semantic HTML such
as `<details>`, `<summary>`, figures, and tables. The bundled renderer has no
answer-grading or persistence runtime; its validator rejects form controls as an
unsupported interaction claim even when they are labelled. Do not create a
`::: custom-directive` syntax, a one-off parser, or a bespoke component framework
for a single lesson. If a new semantic block becomes reusable, specify and test
it as a versioned renderer feature before using it in canonical content.

## Learning interactions

The executable boundary is deliberate:

- bundled Markdown-to-HTML provides static content and reviewed native
  disclosure only;
- host chat provides live attempts, answer interpretation, progressive feedback,
  and grading;
- bundled HTML does not grade form answers, maintain stateful components, or
  write learner evidence or persistence;
- compatible richer interaction uses the packaged, separately versioned Prax
  Visual Lab; other rich media require an approved versioned capability,
  independent tests, a complete static fallback, and manual browser review.

Prax Visual Lab is part of this package, not a second teaching skill. Use it for
state stepping, parameter manipulation, representation comparison, progressive
hints, local receipts, and learner-controlled sequences. Use the visualization
registry and current harness capabilities for specialized diagrams, charts,
3D, animation, or video.

Prefer direct reuse of one authoritative executable model across the lesson and
its visual surfaces. Only when direct reuse is impossible and the duplicated
calculation is deliberately small may an executable visual prove parity against
independently specified literal parity vectors. Exercise those vectors through both
implementations and fail verification when either disagrees. A browser self-check
may expose the result for inspection, but it is engineering evidence, not
evidence that a learner understood the model.

Do not add a scene or trace schema until a real consumer uses it for playback,
scrubbing, or synchronized state across two outputs. A future video or adapter
is not a consumer; remove an unused schema instead of preserving speculative
infrastructure.

When no approved interaction runtime is present, an "interactive lesson" means
a live host-chat attempt paired with complete static instructions and data. It
does not create artifact controls. In that branch, review the prompt and static
fallback for completeness and answer leakage, but record host-UI keyboard,
focus, control naming, reduced-motion behavior, and assistive-technology
behavior as unverified. Do not score absent artifact controls as though they had
passed browser accessibility checks.

When that richer runtime is absent, the visual router retains the requested
learning-job `route` but sets `bundled_renderer_supported` to false,
`delivery_route` to `static`, and names `requested_medium`, `delivery_reason`, and
`runtime_requirement` as
`separately-versioned-tested-and-manually-reviewed`. Deliver through host chat or
the declared static fallback; do not describe the bundled HTML as an interactive
exercise merely because a learner can open a disclosure.

The static-fallback and packaged-runtime claims are executable.
`prax_teach.py visual-verify`
must recompute the Markdown/HTML companion, structural shell, local links,
route/fallback agreement, visible retrieval-attempt prompt, and normalized
answer-leakage scan over source, HTML, alternative text, captions, hidden
markup, metadata, and linked textual assets. The content-bound receipt records
the verifier and renderer hashes. For a Prax Visual Lab route it also reruns the
packaged runtime verifier. It never upgrades an arbitrary external runtime,
opaque media, factual correctness, real-browser behavior, or human learning
evidence. Declared textual answers are machine-scanned;
geometry, color, emphasis, and other semantic visual leakage remain a required
human review.

Use semantic block types with stable IDs:

- `diagnostic`;
- `explanation`;
- `worked-example`;
- `guided-practice`;
- `hint-ladder`;
- `retrieval-check`;
- `teach-back`;
- `transfer-task`;
- `reflection`;
- `review`.

For checks implemented by a separately approved interaction runtime:

1. Show the prompt before the solution.
2. Accept a meaningful attempt where practical.
3. Reveal hints progressively.
4. Explain why the response is correct or incorrect.
5. Keep feedback separate from the answer so another attempt remains possible.
6. Provide an equivalent static workflow.
7. Do not infer or persist mastery from browser interaction alone.

For live chat, use a turn boundary: end on the check and wait. For a
self-contained static artifact, a reviewed native `<details>` disclosure may let
the learner reveal an answer, but it does not accept, grade, or persist an
attempt. Ensure the unrevealed answer is not exposed through accessibility text,
metadata, default state, or a no-script shortcut. When that cannot be achieved
accessibly, provide the answer key in a clearly separate section and describe
the artifact as review material rather than measured retrieval.

Native `<details>` is acceptable for supporting explanation, but do not put essential instructions behind undiscoverable disclosure. If `<details>` contains an answer, label it clearly and place it after the attempt prompt.

## Accessibility

Target [WCAG 2.2](https://www.w3.org/TR/WCAG22/) AA and apply [W3C
cognitive-accessibility guidance](https://www.w3.org/TR/coga-usable/) for clear
language, predictable navigation, focus support, and memory aids. Automated
landmark, heading, label, security, print, and reduced-motion checks establish an
engineering structure gate only; they do not establish WCAG conformance or
field accessibility.

Before delivering an artifact as **browser-inspected** or **production-ready**,
inspect representative pages in a real browser with keyboard, zoom/reflow,
reduced motion, print, scripts disabled, console, and accessibility-tree checks.
Before calling it **field-accessible**, additionally complete appropriate
assistive-technology checks and representative disabled and neurodivergent
learner evaluation. A blocked browser receipt is acceptable for an engineering
candidate only when it records zero observations, makes no browser or field
claim, and keeps EG-03 parked.

### Structure and navigation

- Use landmarks and descriptive headings.
- Keep navigation order consistent.
- Identify the current page in a course.
- Use descriptive link text.
- Provide breadcrumbs or a compact course map for multi-page artifacts.

### Keyboard and focus

- All controls operate without a pointer.
- Focus order follows reading order.
- Focus is never hidden or trapped.
- Dynamic updates announce through an appropriate live region when needed.
- Avoid single-key shortcuts unless remappable or active only on focus.

### Perception and reflow

- Use sufficient contrast and never color alone.
- Allow text resize and 400% zoom without two-dimensional scrolling for ordinary content.
- Do not lock orientation.
- Give media alternatives appropriate to its complexity.
- Keep target sizes and spacing usable.

### Cognitive access

- Prefer short sections and explicit transitions.
- State objectives and what to do next.
- Keep labels and instructions near controls.
- Offer examples, memory aids, and a predictable reveal sequence.
- Avoid time limits; when required, make them adjustable.
- Do not animate, autoplay, or change context unexpectedly.

### Motion and media

- Respect reduced motion.
- Provide captions, transcript, and static sequence when motion carries meaning.
- Never remove information in reduced-motion mode.

Automated scanners are only one check. The manual and representative checks
above are required before making the corresponding browser, accessibility, or
production claim.

## Visual and source provenance

For every significant visual or interactive artifact, preserve:

```text
learning objective
semantic brief or storyboard
source documents/data/URLs
authoring or generation tool and version
editable source path
render command/environment
output dimensions
attribution or license
last verification date
known limitations
```

Place factual citations close to the supported claim or figure. Distinguish sourced fact, inference, and illustrative example.

## Optional Flint chart artifacts

When a chart is compiled through Flint, preserve a reproducible set beside the canonical lesson:

```text
chart.source.flint.json
chart.data.json
chart.semantic-spec.json
chart.svg
chart.vega-lite.json
chart.table.html
manifest.json
lesson.md
lesson.html
```

The render manifest records the pinned Flint/backend versions, normalized CLI and exact programmatic APIs/options, data/spec/output SHA-256 values, warnings, a reproducible non-null generation time, and explicit known limitations. Prefer build-time SVG; keep interactive preview tooling out of the essential delivery path.

Embed the chart in a semantic `<figure>` with a useful caption, short alternative, and nearby complete data table or extended description. Verify units, sample size, uncertainty, missingness, axes, domains, baselines, category retention, and color-independent meaning.

Fail closed on unsupported templates, render failure, or unresolved warnings about filtering, truncation, semantics, or backend coverage. If Flint is unavailable, preserve the lesson with a semantic table or verified native SVG rather than introducing a mandatory network dependency.

Read [FLINT-CHARTS.md](./FLINT-CHARTS.md) for the authoring and accessibility contract.

## Build and parity

The bundled static renderer must:

- parse the project’s declared Markdown dialect consistently;
- slug headings deterministically and deduplicate anchors;
- reject unsupported tags, attributes, and unsafe URLs with a diagnostic before writing output; the sanitizer remains defense in depth for the explicitly allowed reviewed HTML subset;
- decode named and numeric HTML entities before URL policy, reject sanitizer-only URL-bearing rewrites, and inspect decoded local image paths only beneath the Markdown source directory;
- require an explicit trusted publication root, reject symlink leaves and ancestors, and revalidate the same directory generation immediately before and after atomic publication;
- preserve code exactly;
- sanitize or block dangerous URLs and event attributes;
- resolve relative links from the source document;
- embed or localize required assets for offline use;
- record the exact renderer and template contract versions in machine-readable metadata and visible provenance;
- produce a source hash from the exact Markdown bytes.

Use the bundled renderer for the default dialect. A custom renderer/runtime is
justified only when a required learner action cannot be expressed with static
content, native disclosure, or host chat; version that boundary, record the
decision, preserve a static fallback, test it independently, and complete manual
browser review before delivery. Do not pass custom-JavaScript or form-grading
artifacts through the bundled static validator.

The validator must check:

- every `.md` has same-basename `.html`;
- every HTML companion names the source and matching SHA-256;
- no placeholder/TODO text remains in production artifacts;
- local links and anchors resolve;
- required metadata and landmarks exist;
- heading levels do not skip unexpectedly;
- duplicate IDs are absent;
- external dependencies are declared and intentional;
- Flint-derived assets, when present, have local data/spec/output files, matching recorded hashes, reviewed warnings, and a table/text alternative;
- learner-state JSON/JSONL remains separate from lesson content.
- default-renderer pages contain no form controls, custom answer grading,
  stateful components, or persistence hooks.

When an HTML renderer cannot safely preserve a construct, fail with a clear diagnostic. Do not silently omit it.

## Acceptance checklist

### Content

- One observable outcome.
- Correct, versioned, nearby sources.
- Attempt before answer when retrieval is intended.
- Explained worked example where useful.
- Progressive hints.
- Specific feedback and next attempt.
- Unseen transfer task.
- Honest evidence/uncertainty statement.
- Next retrieval tied to the retention horizon.

### HTML

- Markdown is canonical and hash matches.
- Semantic structure and stable anchors.
- Keyboard, focus, zoom/reflow, and reduced motion pass.
- Print and no-script paths remain useful.
- Visuals have editable sources, alternatives, and provenance.
- No answer leakage from HTML, CSS, scripts, media, or accessibility text.
- No mandatory external network dependency.

### Delivery

- Regenerate all companions.
- Run `node <skill-dir>/scripts/render_markdown.mjs --check --trusted-root <workspace> <source.md>` for each delivered lesson/reference.
- Run the workspace validator.
- Inspect representative pages in a real browser before claiming
  browser-inspected or production delivery.
- Complete appropriate assistive-technology and representative learner
  checks before claiming field accessibility; otherwise keep EG-03 parked.
- Report what was actually tested, the browser-receipt status, and every
  remaining claim limitation.
