# Visualization router

## Contents

1. [Decision rule](#decision-rule)
2. [Production capability routing](#production-capability-routing)
3. [Representation routes](#representation-routes)
4. [Optional Flint chart backend](#optional-flint-chart-backend)
5. [Visual brief](#visual-brief)
6. [Accuracy and source rules](#accuracy-and-source-rules)
7. [Accessibility](#accessibility)
8. [Retrieval safety](#retrieval-safety)
9. [Verification](#verification)

## Decision rule

Ask:

> What must the learner see, compare, predict, manipulate, or watch change that prose plus an example does not communicate as efficiently?

Choose internally:

- `none` when prose, code, or a table is already sufficient;
- `static` for structure, comparison, hierarchy, space, exact labels, or a worked state;
- `interactive` when the learner benefits from changing, testing, filtering, traversing, or predicting;
- `motion` when order, causality, transformation, accumulation, synchronization, or changing state is the concept.

Start with the smallest accurate medium. Media availability is not a reason to use it.

Sequence or causality makes motion *eligible*, not mandatory. First test whether a labeled state table, small multiples, or learner-predicted next step communicates the relationship with less overhead.

`route` records the representation best suited to the learning job. The
executable router separately reports the actual delivery surface. The Markdown
renderer supports `none` and `static`; the packaged, verified Prax Visual Lab
supports interactive controls and learner-controlled state sequences. If that
runtime is absent or invalid, rich routes fail closed to static delivery. A
specialized registry-selected renderer remains an authoring route whose output
must be inspected in the actual lesson environment.

## Production capability routing

Read [LEGACY-VISUALIZATION-ROUTER.md](./LEGACY-VISUALIZATION-ROUTER.md)
completely as the inherited Prax-Teach production handbook. Despite the lineage
filename, its fidelity matrix, 38-tool routing, editable-source rules, scene
graph guidance, progressive disclosure, diagram/chart/image/3D/motion/video
contracts, accessibility, provenance, and render-inspect-revise loop are
normative.

Inspect capabilities exposed by the current harness, then query the portable
registry:

```bash
python3 scripts/find_visualization_tool.py --route interaction
python3 scripts/find_visualization_tool.py --route change-over-time
python3 scripts/find_visualization_tool.py --route mathematics
```

Use the closest authorized equivalent capability; do not require a particular
agent brand or hardcode `codex exec`, `claude -p`, or another provider command.
Prefer the packaged Prax Visual Lab for its supported interaction primitives,
browser-native HTML/SVG/Canvas for exact local work, and the smallest suitable
available specialist for advanced output. Never require a second teaching skill
to restore visualization. If no approved capability can execute the selected
route, say so and deliver the complete static fallback.

### Binding selection policy

- Keep the 38-tool registry in Prax-Teach and query it; do not copy it into a
  course or lesson.
- Build the interactive lesson first. One storyboard may then project to
  standalone HTML, HyperFrames or Manim, captions, transcript, and chapters.
- Use HyperFrames for general browser-native explanatory film and Manim for
  mathematical or algorithmic transformation. Pin `manim==0.21.0` at first use.
  Do not select Motion Canvas or Remotion for new Teach Pro Max work. Retain
  their registry records as historical capability evidence only. Consider
  Canvas Commons later only if a real lesson requires TypeScript generators.
- Put a minimal scene/execution-trace JSON under `assets/data/` only when the
  first lab has a real playback, scrubbing, or synchronized-output consumer.
  Do not scaffold a generic scene contract before then.
- Add Olli when a shipped chart needs a screen-reader twin. Add JSXGraph when a
  lesson requires direct manipulation such as “drag the point and watch the
  gradient.” Add Pyodide only when browser-resident Python is essential; local
  labs otherwise use `uv` and `pytest`. Add MCP Apps only when the target
  OpenCode host supports apps. Add Three.js WebGPU only for required 3D, through
  the HyperFrames Three adapter; do not introduce a second 3D engine.
- For LLM visuals, include exactly one truth label in both lesson `NOTES` and
  `CONTEXT`: `illustration`, `measured`, `correlational`, `intervention`, or
  `hypothesis`. Never say “the model thought.” Link Transformer Explainer,
  BertViz, and Bycroft in the bounded lab. Cite and link VisuAlgo, OpenDSA, and
  AV.org; do not vendor them.

For a mechanism lab, follow the proven Classic Patents composition: let the
learner switch among intuition, primary source, schematic, interactive model,
and split comparison without losing context; bind controls, telemetry,
equations, labels, and explanation to one authored model; preserve source
provenance; and test finite outputs, real 2D/3D rendering, console errors,
overflow, keyboard access, reduced motion, and static alternatives. Atmospheric
lighting and motion may strengthen invitation, but they never outrank exact
labels, truthful state, or the learner action.

## Representation routes

| Semantic job | Preferred representation | Avoid |
|---|---|---|
| Exact comparison | Semantic table; optional verified Flint chart when the table is insufficient | Decorative infographic |
| Hierarchy / grouping | Nested HTML, tree, SVG, diagram-as-code | Unlabeled floating cards |
| Process / decision | Flow diagram, numbered states | Animation when order is already obvious |
| Time / transformation | Learner-controlled state sequence or seekable motion | Autoplay-only video |
| Quantity / distribution | Exact chart with source data, text summary, and data-table equivalent | Image-generated chart, 3D, misleading axes |
| Geometry / equations | Exact SVG, math renderer, deterministic animation | Generated image as source of truth |
| Architecture / dependencies | SVG, D2, Graphviz, Mermaid, C4/Structurizr | Screenshot without editable source |
| Practice / simulation | Prax Visual Lab or another approved deterministic runtime | Unbacked controls that imply grading or persistence |
| Atmosphere / metaphor | Sourced or generated illustration | Treating metaphor as factual evidence |

The bundled Markdown artifact path supports static semantic HTML plus linked,
validated assets. Prax Visual Lab provides the packaged interactive surface.
Inline SVG, Canvas, specialized animation/video, and other custom controls must
use an authorized versioned tool/runtime plus manual browser review.

Do not invent a bespoke visualization DSL or renderer for a single lesson. Reuse the bundled Markdown renderer and native elements; introduce a reusable component only after the learning action genuinely requires it.

## Optional Flint chart backend

After choosing `static`, route an exact comparison, quantity, distribution, or time-series job through [Flint](https://github.com/microsoft/flint-chart) only when:

1. a semantic table is not already clearer;
2. the source values and transformations are verified;
3. a pinned Flint dependency or approved MCP tool is available;
4. the requested chart type is supported by the chosen backend;
5. every compiler/render warning will be inspected;
6. a complete table or extended text equivalent will accompany the chart.

Prefer build-time SVG. Preserve prepared data, the editable `.flint.json`, a render manifest with versions/hashes/warnings, and the generated asset. Treat the MCP live chart view as an authoring preview rather than the durable lesson.

Flint is not a data-wrangling layer. Perform joins, pivots, derived fields, filtering, complex aggregation, and time bucketing upstream, then sanity-check the prepared values before authoring the semantic spec.

Do not install Flint silently, use floating `npx -y` in a deterministic build, assume its SVG is accessible, or fail the lesson when the optional backend is unavailable. Fall back to a semantic table or verified native SVG.

Read [FLINT-CHARTS.md](./FLINT-CHARTS.md) before producing a Flint spec or artifact.

## Visual brief

Before a substantial asset, write:

```text
Learning objective:
Learner action:
Semantic job:
Route: none | static | interactive | motion
Required entities, values, relationships, and states:
Accuracy level:
Source/data provenance:
Editable source format and path:
Fallback and reading order:
Accessibility needs:
Retrieval-answer leakage risk:
Verification method:
```

If the brief cannot name a learner action or cognitive job, choose `none`.

## Accuracy and source rules

- Use exact HTML, SVG, diagram-as-code, data visualization, or compositing for authoritative text, equations, values, counts, geometry, architecture, and technical relationships.
- Use generated imagery only for appearance, atmosphere, scenes, objects, or memorable metaphors.
- Preserve editable semantic sources beside rendered derivatives.
- Separate semantics, layout, and style for complex visuals.
- Record source URL/data, authoring tool, render command, dimensions, attribution/license, verification date, and known limitations.
- Do not imply causality from association.
- For charts, show units, sample size, missingness, uncertainty, assumptions, and a textual/table equivalent when material.
- Do not infer a media license from search-result availability.

## Accessibility

### Static

- Use `<figure>` and a useful `<figcaption>`.
- Give simple images concise alt text.
- Give complex visuals a short alternative plus an extended description or data table.
- Do not encode meaning through color alone.
- Keep text as text in SVG where practical.
- Include SVG `<title>` and `<desc>`, semantic groups, and stable IDs.
- Test clipping, contrast, zoom, mobile reflow, and print.

### Interactive

These requirements apply after the packaged Prax Visual Lab or another approved
interaction runtime boundary has been satisfied. Otherwise use host chat or the
router's static `delivery_route`.

- Use native controls and semantic names.
- Support keyboard operation, logical focus, and visible focus.
- Avoid hover-only information.
- Give one precise learning task, immediate explanatory feedback, and a reset.
- Preserve essential meaning without JavaScript.
- Provide a static state and textual explanation.

### Motion

- Use an explicit timeline, frame, or seekable state when determinism matters.
- Add captions and a transcript.
- Provide pause, replay, and scrubbing when applicable.
- Respect `prefers-reduced-motion` without removing information.
- Provide a poster or static sequence for print, failure, and low bandwidth.
- Avoid ambient motion, gratuitous camera movement, rapid zooms, and decorative transitions.

WCAG 2.2 AA is the minimum web target. Automated checks do not replace keyboard, screen-reader, reduced-motion, zoom, and target-user testing. [WCAG 2.2](https://www.w3.org/TR/WCAG22/)

## Retrieval safety

A visual can leak an answer through:

- labels visible before an attempt;
- alt text or captions containing the solution;
- the default slider/state position;
- source code or developer tools;
- thumbnails, posters, or animation end frames;
- choice length, color, or emphasis;
- a distant legend that highlights the correct path.

When retrieval is the task:

1. show the prompt and neutral representation first;
2. require an attempt;
3. reveal one hint or layer at a time;
4. keep answer content out of pre-attempt alternatives;
5. in static bundled HTML, use only reviewed native disclosure for reveal; use
   Prax Visual Lab or host chat for answer capture and grading;
6. ensure the static/no-script fallback preserves the same attempt-before-answer order.

Do not hide required accessibility information. If an alternative would reveal the assessed construct, offer an equivalent response task instead.

## Verification

For bundled delivery, do not stop at the route JSON. Save the exact
`visual-route` output, canonical Markdown, generated HTML, and a small
forbidden-answer rubric, then run:

```bash
python3 scripts/prax_teach.py visual-verify \
  --route-output /absolute/path/to/route.json \
  --source /absolute/path/to/lesson.md \
  --html /absolute/path/to/lesson.html \
  --forbidden-answer-file /absolute/path/to/forbidden-answer.json \
  --receipt /absolute/path/to/visual-receipt.json
```

The verifier reruns exact Markdown/HTML parity and structural checks, scans the
raw source, generated HTML, and linked textual assets after Unicode, entity,
and percent normalization, rejects scripts/forms/remote assets, and requires a
visible attempt prompt for retrieval. Opaque raster media and animated-capable
media cannot receive this automated answer-leakage receipt. For `interactive`
and `motion`, the command verifies the complete static fallback and reruns the
packaged runtime verifier when Prax Visual Lab is the declared delivery surface.
It does not certify arbitrary external animation/video tools. `--check`
recomputes and byte-compares a frozen receipt.

This scan covers only the declared textual answers. It cannot decide whether
geometry, color, emphasis, spatial layout, or an unlabeled path visually gives
away the answer. The receipt marks semantic visual leakage as requiring human
review; do not promote it into a complete answer-leakage claim.

The package carries a four-case `none`/`static`/`interactive`/`motion` fixture
matrix and adversarial leakage, asset, link, accessibility-structure, stale
HTML, and stale-receipt tests. These are engineering checks, not factual or
human review of a particular lesson.

Before any stronger delivery claim:

- compare required entities, labels, edges, directions, values, and states with the brief;
- render in the actual lesson environment;
- inspect at desktop, narrow viewport, zoom, print, and reduced motion;
- operate every control by keyboard;
- verify source/data transformations;
- for Flint, verify the pinned version, input spec, prepared-data and output hashes, warnings, backend coverage, and table/text equivalent;
- check the fallback with scripts and media disabled;
- inspect representative animation frames as stills;
- verify that no answer is exposed before the attempt;
- retain editable source and provenance.

Automated output and structural checks do not authorize a browser-inspected,
field-accessible, or production claim. A browser-inspected or production claim
requires the real-browser checks above. A field-accessibility claim additionally
requires appropriate assistive-technology and representative learner evidence;
until then EG-03 remains parked.

A polished but incorrect arrow, scale, label, or transition is a factual failure.
