# Visualization Research Notes

Use this reference when changing the router or justifying a non-obvious visual-production rule. It is not a substitute for verifying lesson facts against domain-specific primary sources.

## Core Recommendation

Treat visualization as a routing problem driven by the learning objective. Choose the simplest medium that accurately carries the concept, preserve an editable semantic source, render it in the target environment, inspect the result, and provide an accessible fallback.

## Evidence Incorporated into the Skill

### Semantic and editable output

Recent diagram-generation work evaluates diagrams as graphs of nodes, edges, and paths rather than pictures alone. Editable SVG and mxGraph/draw.io output supports semantic verification, targeted repair, and later refinement.

- [DiagramEval: Evaluating LLM-Generated Diagrams via Graphs](https://aclanthology.org/2025.emnlp-main.640/) — EMNLP 2025.
- [DiagramGPT-Llama3: Editable, High-Fidelity Diagram Generation](https://ojs.aaai.org/index.php/AAAI/article/view/40286) — AAAI 2026.
- [AutoFigure: Editable Scientific Illustrations from Text](https://autofigure.org/) — project and paper artifacts.

### Separate meaning, layout, and style

Semantic models should define entities and relationships; layout systems should place them; visual themes should style them. This supports multiple consistent views and safer structured editing.

- [D2](https://d2lang.com/)
- [Structurizr](https://structurizr.com/)
- [Penrose](https://penrose.cs.cmu.edu/)
- [Kroki](https://docs.kroki.io/kroki/)

### Render, inspect, and revise

Generated SVG, diagram code, and animation source must be rendered before acceptance. Educational-diagram research reports that generated artifacts can remain factually inconsistent and that model self-detection is unreliable. Rendered keyframe inspection and local repair are therefore required.

- [Can We Improve Educational Diagram Generation with In-Context Examples? Not if a Hallucination Spoils the Bunch](https://arxiv.org/abs/2601.20476) — 2026 preprint.
- [ManimAgent: Self-Evolving Multimodal Agents for Visual Education](https://arxiv.org/abs/2606.30296) — 2026 preprint; useful evidence for rendered-keyframe feedback, not yet a mature authority.

### Prefer browser-native delivery for HTML lessons

Because lessons are self-contained HTML, accessible SVG, HTML/CSS/JavaScript, Canvas, and browser-native media minimize integration friction. External tools should normally generate assets consumed by that surface.

- [Mermaid accessibility configuration](https://mermaid.js.org/config/accessibility)
- [Vega-Lite](https://vega.github.io/vega-lite/)
- [Observable Plot](https://observablehq.com/plot/)
- [Excalidraw](https://github.com/excalidraw/excalidraw)
- [draw.io documentation](https://www.drawio.com/doc/)

### Motion must encode temporal meaning

Use animation for causality, transformation, synchronization, navigation, or changing state. Preserve captions, a transcript, poster or static sequence, and reduced-motion behavior.

- [Manim Community documentation](https://docs.manim.community/)
- [Motion Canvas documentation](https://motioncanvas.io/docs/)
- [Remotion documentation](https://www.remotion.dev/docs/)
- [HyperFrames repository](https://github.com/heygen-com/hyperframes)
- [W3C: Animation from Interactions](https://www.w3.org/WAI/WCAG21/Understanding/animation-from-interactions.html)

### Progressive disclosure and spatial contiguity

Segmented concept maps with nearby labels can improve learning, but excessive simultaneous signaling can also hurt. Progressive disclosure must be purposeful rather than maximal.

- [How organization highlighting through signaling, spatial contiguity and segmenting can influence learning with concept maps](https://doi.org/10.1016/j.caeo.2021.100040) — Computers and Education Open, 2021.

### Accessibility belongs in the source

SVG should preserve meaningful text, accessible names and descriptions, and redundant encodings beyond color. Interaction needs keyboard access and visible focus. Motion needs user control and reduced-motion handling.

- [W3C Accessibility Features of SVG](https://www.w3.org/TR/SVG-access/)
- [MDN: prefers-reduced-motion](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion)
- [W3C WCAG technique C39](https://www.w3.org/WAI/WCAG21/Techniques/css/C39)

### Agent integrations require independent trust checks

Agent skills can help when they are focused and compatible, but version-mismatched or overly broad guidance can add overhead or reduce performance. Marketplace presence is not proof of quality or authority.

- [SWE-Skills-Bench: Do Agent Skills Actually Help in Real-World Software Engineering?](https://arxiv.org/abs/2603.15401) — 2026 preprint.
- [SkillsBench: Benchmarking How Well Agent Skills Work Across Diverse Tasks](https://arxiv.org/abs/2602.12670) — 2026 preprint.
- [From Anatomy to Smells: An Empirical Study of SKILL.md in Agent Skills](https://arxiv.org/abs/2607.01456) — 2026 preprint.

## Interpretation Limits

- Tool documentation establishes capability, not pedagogical effectiveness.
- A cited agent skill or MCP establishes availability, not safety or compatibility.
- Preprints are useful directional evidence but should be labelled and not treated as settled consensus.
- A rendered example proves one artifact, not general end-to-end reliability.
- Domain-specific visuals still require domain-specific authoritative sources and, for high-stakes topics, human review.
