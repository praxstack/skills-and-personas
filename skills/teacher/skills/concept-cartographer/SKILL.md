---
name: concept-cartographer
description: 'Generate visual concept maps, flowcharts, architecture diagrams, and relationship diagrams from structured notes or technical content using Mermaid syntax. Use when the user has lecture notes, study materials, or technical documentation and wants visual diagrams to aid understanding. Produces multiple diagram types: concept hierarchy maps, process flowcharts, architecture diagrams, comparison matrices, timeline diagrams, and mind maps. Trigger phrases: "create diagrams from notes", "visualize concepts", "concept map", "make flowcharts", "diagram this", "visual notes".'
---

# Concept Cartographer — Visual Knowledge Mapper

**Audience:** Agents transforming lecture notes or technical documentation into visual diagrams.
**Goal:** Generate Mermaid diagrams tuned to the content's domain and verified against the source topic inventory — not a syntax dump.

## Diagram Type Selection

Claude already knows Mermaid syntax. The delta this skill provides is **picking the right diagram type for the content** and **verifying coverage**. One illustrative example per type is in `references/mermaid-examples.md`; load it only if a reminder is needed.

| Diagram type | Use when content has | Typical size |
|---|---|---|
| Concept hierarchy (`graph TD`) | Parent-child topic structure, taxonomies | 5–15 nodes |
| Process flowchart (`flowchart LR`) | Algorithms, workflows, decision branches | 5–12 nodes |
| Architecture (`graph LR` + subgraphs) | System components + data flow | 3–4 subgraphs, 10–15 nodes |
| Sequence (`sequenceDiagram`) | Interactions over time, API/protocol flows | 3–6 participants, 8–15 messages |
| State (`stateDiagram-v2`) | Lifecycle, mode transitions | 4–10 states |
| Comparison (`graph TD` with branches) | Alternatives with trade-offs | 2–4 branches, ≤4 leaves each |
| Learning-path (`graph LR` with prerequisites) | Educational content with built-up concepts | 5–12 nodes |
| Quadrant (`quadrantChart`) | Difficulty-vs-importance prioritization | 4–10 points |

## Domain-Specific Focus

| Domain | Priority diagrams | Special elements |
|---|---|---|
| AI/ML | Architecture, process flow, comparison | Layer structures, training loops, model pipelines |
| WebDev | Architecture, sequence, flowchart | Request/response flows, component trees, state |
| Web3 | Sequence, architecture, state | Transaction flows, contract interactions, token flows |
| DSA | Flowchart, state, comparison | Algorithm steps, tree/graph structures, complexity |

## Topic Inventory Verification

If a Topic Inventory was provided from Stage 1 (lecture pipeline), **verify every concept from the inventory appears in at least one diagram**. This is the coverage gate — a diagram missing 30% of topics is worse than no diagram.

Report at the end:

```markdown
## Concept Coverage
- Concepts in diagrams: [N] / [N] from inventory
- Concepts not diagrammed: [list] (reason: "too granular" or "no visual relationship")
```

If no inventory exists, extract topics from the source notes before drawing — treat your own extraction as the inventory and verify against it.

## Output Format

```markdown
# Visual Concept Maps: [Topic]

## Overview Map
[Always include: concept hierarchy — this is the minimum output]

## [Diagram Type 2]
[Most relevant additional diagram, with 1–2 sentence caption]

## [Diagram Type 3]
[Second most relevant, with caption]

## Key Relationships Summary
- [Concept A] depends on [Concept B] because...
- [Concept C] is an alternative to [Concept D] when...

## Concept Coverage
[Verification report]
```

## Rules

1. **Valid Mermaid, verified mentally before output.**
2. **Always include a concept hierarchy** — minimum output.
3. **Pick 2–4 diagram types per note set**; more is noise.
4. **Every diagram gets a 1–2 sentence caption** naming its purpose.
5. **Max 15 nodes per diagram** — split into sub-diagrams with explicit cross-links beyond that.
6. **Use subgraphs** for grouping related concepts.
7. **Match the domain** — use domain-appropriate terminology.
8. **Verify against the topic inventory** before declaring done.

## Anti-Patterns

- **NEVER** use more than one diagram type for the same set of relationships (e.g., a flowchart AND a graph showing the same process). The reader has to mentally merge them, which defeats the diagram's purpose.
- **NEVER** stuff more than 15 nodes into a single diagram — readability collapses. Split into sub-diagrams with explicit cross-links (`see: Diagram 3`).
- **NEVER** skip the verification pass against the source topic inventory. A diagram that silently drops 30% of topics is more misleading than no diagram.
- **NEVER** use Mermaid for data-heavy relationships (10+ columns, dense fact tables, wide ERDs) — prefer a markdown table or a dedicated ERD tool. Mermaid ERDs past ~8 entities become unreadable.
- **NEVER** embed a diagram without a 1–2 sentence caption naming its purpose — visual without verbal context is noise the reader has to decode.
- **NEVER** redraw the same hierarchy as both `graph TD` and `graph LR` "to give options" — pick the one the content needs. Orientation is a decision, not a preference.
- **NEVER** mix abstraction levels in one diagram (e.g., a single flowchart showing both business workflow *and* function call sequence) — promote one to a subgraph or split entirely.

## Pipeline Position

Stage 3 in the lecture processing pipeline:

1. `transcribe-refiner` produces the clean transcript plus Topic Inventory.
2. `lecture-alchemist` produces structured study notes.
3. `concept-cartographer` (this) produces visual diagrams, verified against the inventory.
4. `obsidian-markdown` applies Obsidian vault formatting.

## References

- `references/mermaid-examples.md` — one worked example per diagram type. Load on demand.
