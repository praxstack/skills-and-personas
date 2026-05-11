# Stage 3 — Enhance Notes

## When to load this file

Load at the start of Stage 3: after Stage 2 has produced zero-topic-loss synthesized notes. Stage 3 enriches with visualizations, analogies, gap-filling, and cross-links without altering source content.

## Input contract

- `stage2-synthesized.md` — structured notes from Stage 2
- Target audience / skill level (beginner / intermediate / advanced)

## Output contract

Enhanced notes that keep the Stage 2 structure but add:

- **Intuition aids** — analogies, metaphors, mental models (marked clearly as aids, not source content)
- **Diagrams** — Mermaid / ASCII-free / PlantUML for architecture, flows, state machines, data models
- **Gap-filling** — explain prerequisite concepts the speaker assumed the audience already knew
- **Cross-links** — forward/backward references to related topics within the notes
- **Worked examples** — step through at least one example for each major concept
- **Common-misunderstanding callouts** — "this is often confused with..."

## Enhancement rules

- **Preserve Stage 2 structure exactly.** Enhancements are additive, not restructurings.
- **Mark enhancements distinctly.** Use a `> **Intuition:**` blockquote or `> **Analogy:**` prefix so readers can tell source-vs-enhancement.
- **Do not invent source content.** If the speaker didn't cover it and it's essential, say `> **Gap-fill:** The source assumed...` and flag it.
- **Cite cross-links explicitly.** `See [Topic 3 — Caching](#topic-3-caching).`
- **Diagrams must add clarity.** If a prose description is clearer than a diagram, don't force a diagram. Diagrams are tools, not checkboxes.
- **Match the audience level.** Beginner notes need more analogy and gap-fill; advanced notes need more pattern-recognition and trade-off depth.

## Enhancement techniques

### Analogies and metaphors

- Choose analogies from domains the audience knows (cooking, sports, everyday physics).
- State the limit of the analogy: "this breaks down when..."
- Never stretch an analogy past its useful domain.

### Diagrams

- **Architecture** — boxes and arrows (Mermaid `graph` or `flowchart`).
- **Sequence / timing** — Mermaid `sequenceDiagram`.
- **State machines** — Mermaid `stateDiagram-v2`.
- **Data model / entity relationships** — Mermaid `erDiagram`.
- **Decision trees** — Mermaid `graph TD` with diamond decision nodes.
- **Process flows** — numbered list is often clearer than a diagram; choose based on complexity.

### Gap-filling

- Identify places where the speaker said "as you know..." or "obviously..." or skipped foundational context.
- Add one-paragraph primers that close those gaps for the target audience.
- Do not over-explain — if the audience already has the context, gap-filling adds noise.

### Worked examples

- For each major concept, add one concrete example that traces through the reasoning.
- Show intermediate state, not just start and end.
- For code, show what the variables look like at each step.
- For algorithms, trace an input through the algorithm step-by-step.

### Common-misunderstanding callouts

- "This is often confused with X because..." — then clarify the distinction.
- "A common mistake is to assume Y, but actually..." — useful for anti-patterns.
- Source for these: your own domain knowledge, not source material.

## Domain-specific enhancement

| Domain | Enhancement emphasis |
|---|---|
| Technical lecture | Diagrams for architectures/flows, worked examples with traces, gap-fills for prerequisites |
| System design | Decision trees, constraint-tradeoff tables, scaled scenarios (100x this design) |
| Business meeting | Usually minimal enhancement; notes are already actionable |
| Podcast / interview | Analogies to connect interviewee ideas to listener's context; quote-pull cards |
| Tutorial / screencast | Annotated commands, explain each flag, show error-path examples |

## Coverage verification

- Every major Stage 2 topic has at least one enhancement (diagram, analogy, worked example, or gap-fill).
- No enhancement contradicts source content.
- Diagrams render (validate Mermaid syntax).
- Cross-links point at existing sections.

## Hand-off to Stage 4

Stage 4 expects:
- Enhanced notes with clear source-vs-enhancement markers
- All diagrams valid and rendering
- Zero topic loss preserved from Stage 2

Output goes to `stage3-enhanced.md` in the working directory.
