# Tutorial Tech Bar-Raiser (Mandatory)

Use this in Stage 3 before finalizing `final_notes.md`.

## Goal

Produce **tutorial-grade study guides**, not summary notes.
The learner should understand:
1. what was taught,
2. why it matters,
3. how to apply it,
4. what to do next.

## Style Contract

1. Use Obsidian-friendly Markdown.
2. Use emoji section headings for visual scanning.
3. Keep language direct, concrete, and tutor-like.
4. Explain intuition first, then formal detail.
5. Avoid shallow placeholders and repetitive filler.

## Required Structure (Emoji Headings)

1. `# 🎓 <Domain> Class <NN> [DD/MM/YYYY] - <Topic>`
2. `## 🧠 Session Focus`
3. `## 🎯 Prerequisites`
4. `## ✅ Learning Outcomes`
5. `## 🧭 Topic Index`
6. `## 🗺️ Conceptual Roadmap` (Mermaid)
7. `## 🏗️ Systems Visualization` (Mermaid)
8. `## 🌆 Skyline Intuition Diagram` (ASCII)
9. `## 📚 Core Concepts (Intuition First)`
10. `## ➗ Mathematical Intuition` (when math is relevant)
11. `## 💻 Coding Walkthroughs`
12. `## 🚀 Advanced Real-World Scenario`
13. `## 🧩 HOTS (High-Order Thinking)`
14. `## ❓ FAQ`
15. `## 🛠️ Practice Roadmap`
16. `## 🔭 Next Improvements`
17. `## 🔗 Related Notes`
18. `## 🧾 Traceability`

## Naming Policy (Mandatory)

1. `final_notes.md` must have frontmatter `title` matching the H1 format.
2. Also create a learner-facing published tutorial filename:
   - `<DomainFile> Class <NN> [DD-MM-YYYY] - <Topic>.md`
3. Domains:
   - `AI/ML` -> `AI-ML` (filename)
   - `WebDev` -> `WebDev`
   - `Web3` -> `Web3`

## Concept-Level Requirements

For each core concept, include:
1. What it is.
2. Why it is needed.
3. Intuition / mental model.
4. Common mistake.
5. Next improvement step.

## Math Policy

If a topic is mathematical:
1. Include the formula in code-style inline format (for example, `y = wx + b`).
2. Explain variables in plain English.
3. Explain intuition behind the formula.
4. Explain failure mode if misunderstood.

If a topic is not mathematical:
1. Do not force formulas.
2. Use operational intuition and causal explanation.

## Example Policy

Each tutorial must include:
1. Beginner example (minimal and runnable).
2. Real-world example (where this appears in production).
3. Advanced extension (scale, failure, optimization, security, or reliability).
4. "What this code is doing" bullets.

## Diagram Policy

Minimum:
1. Two Mermaid diagrams.
2. One ASCII skyline/intuition diagram.

Rules:
1. Diagrams must explain relationships/flow, not decorate.
2. Place diagrams near the concept they explain.
3. Keep labels domain-specific.

## Pedagogy Policy

1. Add HOTS questions that require analysis/synthesis/evaluation.
2. Add practical FAQ from learner perspective.
3. Add explicit practice path (today/this week/next week).
4. Add concrete "next improvements" for deeper mastery.

## Traceability Policy

Learner-facing files can be sanitized for readability.
Deterministic traceability must remain in `.pipeline` artifacts:
1. `segment_ledger.jsonl`
2. `coverage_matrix.json`
3. `validation_report.md`
4. `topic_inventory.json`

## Sanitization Policy (Mandatory)

1. Remove inline `[source: <segment_id>]` tags from learner-facing `final_notes.md`.
2. Keep source-rich traceability in `.pipeline/enhanced_notes.md` and coverage artifacts.
3. Do not remove source data from `.pipeline` files.

## Stage 3 Exit Gate (Bar-Raiser)

Do not finalize Stage 3 unless all checks pass:
1. Emoji heading structure present.
2. Intuition-first concept sections present.
3. Math intuition present where relevant.
4. Mermaid count >= 2.
5. Code walkthrough count >= 2.
6. HOTS + FAQ + practice roadmap present.
7. Final note reads like a tutorial, not a summary list.
8. `final_notes.md` has no inline `[source: ...]` tags.
9. Class naming convention is applied.
