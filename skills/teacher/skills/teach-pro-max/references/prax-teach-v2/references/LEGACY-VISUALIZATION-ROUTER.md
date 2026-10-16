# Visualization Router

Use this reference only when a lesson benefits materially from a visual. Visuals are teaching instruments, not decoration.

## Production Loop

Follow this order:

```text
Learning objective
→ visual brief
→ no visual / static / interactive / motion
→ representation family
→ accuracy, editability, and delivery constraints
→ available renderer or verified fallback
→ editable semantic source
→ render in the lesson environment
→ visual, semantic, accessibility, and provenance QA
→ revise locally
→ lesson placement, static fallback, and retrieval task
```

Do not escalate from prose to SVG, SVG to interaction, or interaction to video unless the extra dimension teaches something the simpler medium cannot.

## Write the Visual Brief

Before creating a substantial visual, record:

- **Learning job:** what the learner must notice, compare, predict, manipulate, or watch change.
- **Message:** the one-sentence takeaway.
- **Entities and relationships:** exact objects, labels, values, directions, states, and invariants.
- **Misconception:** the plausible wrong reading the visual must prevent or correct.
- **Evidence:** authoritative source for every factual, numerical, scientific, medical, historical, or technical claim.
- **Delivery constraints:** target screen, mobile and print behavior, offline use, editability, interaction, audio, and available tools.
- **Fallback:** equivalent prose, table, poster, or static sequence.
- **Retrieval action:** what the learner will predict, identify, repair, trace, change, or recreate.

For formulas, notation, protocols, architecture labels, or recurring entities, maintain a **symbol ledger**. Reuse names, colors, shapes, line styles, and meanings across every scene and lesson.

## Choose the Representation

| Learning need | Default | Alternatives |
|---|---|---|
| No relationship is clarified by a visual | No visual | Compact example or table |
| Appearance, mood, historical scene, or metaphor | Image generation or sourced photography | Illustrated collage |
| Exact labelled object, mechanism, anatomy, or spatial instruction | Accessible SVG | HTML/CSS, Penrose |
| Simple process, hierarchy, lifecycle, or decision tree | Mermaid | D2, Graphviz |
| Informal or provisional mental model | Excalidraw | Sketch-mode D2, wireframe |
| Editable professional handoff | draw.io | Figma, Excalidraw |
| UI hierarchy or product flow | Wireframe or runnable HTML | SVG, Figma |
| UML, sequence, state, or deployment | PlantUML | Mermaid, D2, draw.io |
| Evolving software architecture | Structurizr/C4 | D2, PlantUML, draw.io |
| Comparison, distribution, trend, uncertainty, or relationship | Vega-Lite or domain plot | Observable Plot, ECharts |
| Rich interactive chart or dashboard | ECharts | Observable Plot, Vega, D3 |
| Large graph, map, spatial dataset, or 3D relationship | Canvas/WebGL | deck.gl, Three.js, Sigma.js |
| Nodes the learner must expand, drag, connect, or inspect | React Flow | Cytoscape.js, custom SVG |
| Mathematical geometry or constrained relationship | Penrose or SVG | TikZ, Manim |
| Mathematical or algorithmic transformation over time | Manim 0.21.0 | HyperFrames |
| Animated code, vector, or systems explainer | HyperFrames | Manim |
| Templated, data-driven, or branded video | HyperFrames | Manim when precision math dominates |
| Agent-authored HTML/CSS/JS video | HyperFrames | Static sequence when film adds no learning value |
| Small interactive vector state machine | Rive or dotLottie | Animated SVG |
| Many diagram languages behind one gateway | Kroki | Direct local renderer |

These are routes, not mandatory dependencies. Query the registry after choosing a route:

```bash
python <prax-teach-skill-dir>/scripts/find_visualization_tool.py --route quantity
python <prax-teach-skill-dir>/scripts/find_visualization_tool.py mermaid
```

Inspect tools already available in the workspace before installing anything. Prefer browser-native HTML, CSS, JavaScript, Canvas, and SVG when they solve the problem without a heavy toolchain.

## Decide Required Fidelity

| Fidelity | Preferred family |
|---|---|
| Impressionistic | Image generation |
| Approximate relationships | Excalidraw or wireframe |
| Exact labels, arrows, and geometry | SVG or diagram-as-code |
| Exact quantitative encoding | Vega-Lite, Observable Plot, ECharts, domain plot |
| Exact mathematical transformation | Manim or Penrose |
| Exact frame timing | HyperFrames or Manim |

Never use an image model as the source of truth for text, equations, measurements, ordered steps, object counts, charts, architecture, or precise scientific, medical, legal, safety, or historical claims. Generate illustration separately and composite authoritative labels in SVG or HTML.

## Preserve Semantic and Editable Sources

Prefer `.svg`, `.drawio`, `.excalidraw`, `.mmd`, `.d2`, `.dot`, `.puml`, Structurizr DSL, Vega-Lite JSON, HTML/JS, React/TypeScript, Manim Python, or video composition source. Treat PNG, GIF, and MP4 as rendered derivatives.

For complex work, separate:

1. **Semantics:** entities, values, relationships, hierarchy, and state transitions.
2. **Layout:** positions, grouping, routing, scale, and progressive reveals.
3. **Style:** typography, color, line treatment, animation, and decoration.

Styling changes must not rewrite meaning. When practical, generate several views from one semantic model.

### Advanced patterns

Use only when complexity earns them:

- **Scene-graph intermediate representation:** typed nodes, edges, groups, values, and states before rendering, only when a real playback, scrubbing, or synchronized-output consumer reads it.
- **Constraint-based layout:** alignment, containment, non-overlap, equal spacing, and geometric invariants.
- **Structured edits:** add, remove, reconnect, regroup, or restyle semantic objects rather than blind text replacement.
- **Progressive rendering:** show a clearly labelled coarse result and refine without changing its encoding.
- **First-class annotations:** bind callouts to semantic entities or data values.
- **Golden previews:** retain representative screenshots or keyframes to catch layout drift.
- **Targeted regeneration:** repair the incorrect scene, object, label, or edge instead of regenerating everything.

Treat emerging research systems as optional accelerators, never authorities. Keep the verification loop independent of the generator.

## Progressive Disclosure and Signaling

Introduce complexity in stages:

1. Establish the baseline.
2. Add one entity, rule, or transition.
3. Highlight the relevant path or comparison.
4. Show the complete system.
5. Test an edge case or misconception.

Keep labels beside what they explain. Prefer direct labels over distant legends. Use emphasis sparingly. Follow a major visual with a learner action rather than passive admiration.

## Accurate SVG Contract

SVG is the default for precise, responsive lesson illustrations.

- Set a meaningful `viewBox`; use responsive width and automatic height.
- Keep important text as text rather than paths.
- Include `<title>` and `<desc>`, use `role="img"`, and connect them with `aria-labelledby`.
- Group semantic regions with stable IDs.
- Reuse markers, symbols, gradients, and filters through `<defs>`.
- Define consistent meanings for direction, optionality, inhibition, uncertainty, and grouping.
- Keep typography, stroke widths, corner radii, spacing, and color meanings aligned with course tokens.
- Avoid `foreignObject` when the visual must print or render outside a browser.
- Do not encode meaning through color alone.
- Provide a prose reading order for complex figures and a table for quantitative figures.
- Validate XML and inspect the rendered result for clipping, overlap, fonts, malformed paths, and unreadable labels.

During semantic verification, model the SVG as a graph: compare required nodes, labels, edges, directions, and paths with the visual brief. A beautiful incorrect arrow is still incorrect.

## Diagram Rules

- Use Mermaid for fast, modest diagrams with maintainable text source.
- Use D2 when layout engines, themes, sketch styling, modular imports, or animated SVG are valuable.
- Use Graphviz for trees, dependencies, dense graphs, and state spaces where automatic layout is central.
- Use PlantUML for UML-heavy or sequence-heavy material.
- Use Structurizr/C4 when several architecture views must share one model.
- Use Excalidraw for exploratory or deliberately provisional visuals; preserve scene JSON.
- Use draw.io for manual refinement, layers, pages, rich connectors, metadata, or handoff; preserve XML.
- Use wireframes when hierarchy and interaction matter more than finish.
- Use Kroki when a unified local or remote rendering gateway is more useful than separate runtimes.

Split diagrams larger than one screen into an overview and focused detail views. Avoid crossing edges, unexplained icons, decorative containers, and tiny labels.

## Data Visualization Rules

Begin with the question, not the chart type.

- Identify the comparison, distribution, trend, relationship, composition, flow, or uncertainty.
- Prefer position and length for precise comparison before area, angle, volume, or pictograms.
- Start bar-chart quantitative axes at zero unless an explicit exceptional reason is explained.
- Do not force line charts to zero when it destroys the useful scale; disclose the scale.
- Directly label important values, groups, thresholds, and annotations.
- Show sample size, missingness, uncertainty, assumptions, units, and data provenance when relevant.
- Keep annotations bound to semantic data targets.
- Avoid 3D charts, unexplained dual axes, rainbow scales, chart junk, and obscuring animation.
- Retain source data or reproducible transformations.
- Provide a table or concise textual summary for essential values.
- Test mobile and print; reflow, facet, filter, or create a simpler alternate view instead of uniformly shrinking.

Do not imply causality when evidence shows only association.

## Image Generation and Sourced Media

Use generated imagery for appearance, atmosphere, memorable metaphors, scenes, objects, and illustrative composition.

- Inspect for unsupported detail, spatial contradiction, misleading affordance, accidental labels, cultural bias, and conflict with cited sources.
- Identify synthetic imagery when it could be mistaken for documentary evidence.
- Preserve the prompt or edit instructions when reproducibility matters.

For external media:

- Prefer authoritative, public-domain, Creative Commons, or properly licensed sources.
- Record source URL, creator, licence, required attribution, and retrieval date.
- Confirm that the planned redistribution and editing are permitted.
- Never infer a licence from search-result availability.

## Interactive Visual Rules

Use interaction only when the learner gains by changing, testing, traversing, filtering, comparing, controlling time, or inspecting the model.

- Give it one precise learning task.
- Keep controls minimal and action-labelled.
- Provide immediate explanatory feedback.
- Support keyboard operation, logical focus order, and visible focus states.
- Avoid hover-only information; expose the same content through focus or click.
- Preserve useful learner state and provide a clear reset.
- Separate feedback from the answer so the learner can try first.
- Provide a static fallback and textual explanation.
- Keep the lesson understandable if JavaScript is disabled.

## Motion and Video Rules

Use motion only for order, causality, transformation, accumulation, synchronization, navigation through space, or changing state.

Before implementation, create a storyboard containing:

1. Learning objective
2. One idea per scene
3. Initial and final state of each scene
4. Narration or captions
5. What changes and why
6. Expected duration
7. Retrieval prompt

Choose:

- **Manim 0.21.0:** equations, proofs, geometry, science, and precise algorithms.
- **HyperFrames:** deterministic HTML/CSS/JS visual storytelling with seekable animation.
- **Rive/dotLottie:** small interactive vector animations and state machines.

Motion Canvas and Remotion remain historical registry entries, not default
routes for new Teach Pro Max work. Consider Canvas Commons only if a future
lesson demonstrates a requirement for TypeScript generators.

Use an explicit timeline, frame, or seekable state when determinism matters. Do not rely on wall-clock playback.

- Keep narration and visual action complementary rather than duplicative.
- Add captions and a transcript.
- Include pause, replay, and scrubbing when supported.
- Provide a poster or static sequence for print, low bandwidth, failed playback, and reduced-motion users.
- Respect `prefers-reduced-motion` without removing information.
- Review important keyframes as still images.
- Avoid ambient movement, gratuitous camera motion, rapid zooms, and decorative transitions.

## Embed in the Lesson

- Place media beside the explanation or task it supports.
- Use `<figure>` and `<figcaption>` for meaningful static media.
- Write captions that say what to notice.
- Use `alt` text for simple images; use a short alternative plus extended description or data table for complex ones.
- Cite factual content, data, and external imagery near the figure.
- Keep the lesson understandable when media fails.
- Do not reveal a retrieval answer before the learner attempts it.
- Prefer learner-controlled progressive reveals over autoplay.

## Provenance Contract

For each significant visual, retain nearby metadata containing:

- learning brief or storyboard
- authoring or generation tool
- source documents, data, and URLs
- editable source path
- render command and environment
- output dimensions
- attribution or licence
- last verification date
- known limitations

Use lesson-prefixed paths:

```text
assets/visuals/0004-request-lifecycle.d2
assets/visuals/0004-request-lifecycle.svg
assets/visuals/0004-request-lifecycle.png
assets/video/0007-gradient-descent/STORYBOARD.md
assets/video/0007-gradient-descent/main.py
assets/video/0007-gradient-descent/poster.svg
assets/video/0007-gradient-descent/render.mp4
```

## Render, Inspect, Verify, Revise

Never ship a non-trivial visual merely because its source parses.

1. Generate editable source.
2. Render it in the same environment or browser context used by the lesson.
3. Inspect the rendered image, screenshot, interaction states, or video keyframes.
4. Verify facts and semantics against the visual brief and cited sources.
5. Check labels, node and edge completeness, directions, numeric values, legends, units, and scales.
6. Check clipping, overlap, crossings, contrast, spacing, font loading, mobile behavior, print, and static fallbacks.
7. Test keyboard use, text alternatives, and reduced motion where relevant.
8. Revise the smallest incorrect region and rerender.

Use multimodal inspection when available, but do not rely on self-review alone for high-stakes content. Verify scientific, medical, financial, legal, and safety-critical visuals against authoritative sources and surface uncertainty.

If the preferred renderer cannot be used reliably, step down to the nearest simpler medium that can be rendered and verified. State the verification limit.

## Required Deliverables

Retain:

1. Editable semantic source
2. Rendered derivative when needed
3. Visual brief or storyboard
4. Accessibility text
5. Provenance metadata
6. Captions, transcript, and poster for video

## Anti-patterns

Do not:

- add decorative media with no learning job
- use generated imagery for technical truth
- keep only a raster or video derivative when editable source is feasible
- install an unreviewed skill merely to claim tool support
- choose a renderer before defining the visual question
- create motion merely to feel polished
- separate labels from their targets
- present a dense “spaghetti” diagram to a beginner
- omit retrieval practice after a major visual
- regenerate an entire correct artifact to fix one local defect
- claim an unrendered artifact was visually inspected
