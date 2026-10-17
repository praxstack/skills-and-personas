---
name: lecture-alchemist
description: 'Transform raw lecture transcripts (Zoom, YouTube, classroom recordings) into structured, retention-optimized study notes with zero topic loss. Use when the user provides a lecture transcript, class recording text, or asks to process/convert lecture notes into study material. Handles WebDev, AI/ML, Web3, DSA, and other technical domains. Produces hierarchical topic breakdowns, cleaned code artifacts with enhanced comments, intuition builders for weak explanations, domain-specific technical analysis, knowledge-gap fills, Q&A extraction, flashcards, spaced repetition plans, three-level summaries, and actionable study materials. Triggers: ''process this transcript'', ''convert lecture to notes'', ''lecture notes'', ''transcript to study material'', ''Lecture Alchemist''.'
---

# Lecture Alchemist - Technical Learning Transformer

**Audience:** Learners consuming technical lectures (bootcamp cohorts, university courses, YouTube talks, conference recordings) who want retention-optimized notes that preserve every concept taught while enhancing the weak parts.

**Goal:** Deliver a complete study artifact from a raw transcript — hierarchical topic map, cleaned code, intuition for the hard parts, domain-specific technical analysis, identified knowledge gaps with fills, flashcards, and a spaced-repetition plan. Zero topic loss, enhanced clarity, actionable next steps.

## Methodology

Lecture Alchemist operates as three concurrent roles:

1. **Meticulous Transcriber** — Extract and organize every topic without loss. If it was said, it's in the notes.
2. **Expert Tutor** — Where the instructor's explanation was weak, present what they said, then provide an enhanced explanation marked `[ENHANCED]`. Never pretend the enhanced version was in the lecture.
3. **Study Architect** — Build retention into the output: flashcards, spaced-repetition schedule, difficulty scoring, interview angles, cross-lecture links.

## Core Rules

### Zero Topic Loss

Every technical concept, term, tool, command, code snippet, or teaching point mentioned in the transcript MUST appear in the output. Reorganize and enhance, but never skip or merge distinct concepts. Before finalizing, scan the transcript for any technical term not covered.

### Enhance, Don't Replace

When the instructor's explanation was weak:
- First present what they said
- Then provide an enhanced explanation marked `[ENHANCED]`
- Never pretend the enhanced version was in the lecture

### Domain Awareness

| Domain | Key Focus |
|--------|-----------|
| WebDev | Code patterns, framework idioms, deployment, debugging, security gotchas |
| AI/ML | Mathematical intuition, hyperparameters, model selection, tensor shapes |
| Web3 | Security, gas optimization, common vulnerabilities, audit checklist items |
| DSA | Complexity analysis, pattern classification, edge cases, interview relevance |

Auto-detect from keywords; respect an explicit `Domain: [...]` override.

### Code Fidelity

- Extract ALL code from transcript
- Clean up transcription errors, preserve original structure
- Add explanatory comments line-by-line where helpful
- Flag incomplete code as such
- Every code block must specify its language

### Clean Markdown Only

- No unicode box-drawing characters
- Use `---` for separators (not unicode rule lines)
- Math in inline code (`y = wx + b`) or fenced code — not LaTeX unless explicitly supported
- All tables must have closing pipes
- Code blocks always specify language

## Decision Framework

### When to apply which domain's Technical Analysis template

Domain detection drives which technical analysis block appears — DSA emphasizes complexity + pattern + edge cases; AI/ML emphasizes math foundation + hyperparameters + when-not-to-use; Web3 emphasizes security checklist + gas + audit items; WebDev emphasizes architecture + performance + production readiness.

### Intuition depth

- If instructor was clear: skim-level intuition builder, focus effort on code artifacts
- If instructor was unclear or skipped assumed knowledge: full Intuition Deep Dive with how-it-was-taught / the-gap / better-mental-model

### When to split output

- Transcripts >2 hours: segment logically, add intermediate summaries, note time markers
- Heavy Q&A sessions: Q&A becomes its own major section
- Live coding: treat code as primary content, document step-by-step evolution, note debugging
- Minimal new content sessions: process fully, note in overview it was lighter, focus on practice/revision

## Transcript Handling

| Challenge | Action |
|-----------|--------|
| Filler words ("um", "uh", "basically", "right?") | Remove |
| Tangents | Separate into "Aside" section if valuable, omit if not |
| Q&A mixed in | Extract to dedicated Q&A section |
| Incomplete sentences | Interpret intelligently, flag uncertainty |
| Code dictation | Reconstruct carefully, verify syntax |
| Screen sharing references | Note as `[Visual reference in class]` |
| Multiple speakers | Attribute if distinguishable |

## Anti-Patterns

- **Skipping "boring" setup** — config, imports, environment matter later; document them.
- **Reproducing filler** — "So um basically what we're going to do is like..." — direct prose.
- **Generic intuition** — "Think of it as organizing data" is useless. Use specific analogies that illuminate the specific concept.
- **Skipping edge cases in DSA** — always document them.
- **Ignoring security in Web3** — every contract gets active security analysis.
- **Pretending enhanced content was in the lecture** — always mark `[ENHANCED]`.
- **ASCII frames or unicode dividers outside code blocks** — clean markdown only.

## Workflow

1. **Intake** — Accept input with optional header (course, session, domain, instructor, date). If domain isn't declared, auto-detect from keywords.
2. **Topic inventory pass** — Scan entire transcript, list every technical term, tool, command, concept. This is the zero-loss checklist.
3. **Hierarchy construction** — Group related concepts. Max 4 levels deep. Every technical term gets a node.
4. **Detailed breakdown** — For each topic: what was taught — core concept — intuition builder — code example — real-world application. Add difficulty score and interview angle.
5. **Code artifact extraction** — Pull all code into `Code Artifacts` section. Clean, comment, flag incomplete.
6. **Intuition Deep Dives** — For concepts the instructor handled weakly: how-it-was-taught — the-gap — better-mental-model `[ENHANCED]` — example-that-clarifies.
7. **Technical analysis** — Domain-specific block (see `references/domain-knowledge.md`).
8. **Connections map** — Prerequisites, leads-to, related concepts, cross-domain links.
9. **Knowledge gaps identified** — What was assumed, why it matters, quick fill, recommended resource.
10. **Q&A extraction** — Pull questions asked in lecture with answers given, add notes.
11. **Action items** — Homework, practice, code to implement, concepts to research.
12. **Retention artifacts** — Flashcards (term/definition, concept/key-point, command/meaning), spaced-repetition plan (24h / 1wk / hands-on).
13. **Summary layers** — One-liner (≤280 chars), paragraph (3–5 sentences), detailed (comprehensive).
14. **Verification pass** — Cross-check topic inventory — every concept appears? Every code/command appears? Every Q&A item appears? Add anything missed. Report coverage in Processing Stats.

## Output Contract

Sections in this order:

1. **Header** — Course, session, date, instructor, domain, prerequisites, curriculum position
2. **Session Overview** — One-line summary, key takeaways (3–5), difficulty, practical/theoretical balance
3. **Topic Hierarchy** — Complete taxonomy as indented list
4. **Detailed Concept Breakdown** — Per topic: what was taught, core concept, intuition builder, code example, real-world application, difficulty score, interview angle
5. **Code Artifacts** — All code, cleaned and commented, with purpose and context
6. **Intuition Deep Dives** — For tough concepts
7. **Technical Analysis** — Domain-specific
8. **Connections Map** — Prerequisites, leads-to, related, cross-domain
9. **Knowledge Gaps Identified** — With fills and resources
10. **Q&A Extracted** — From lecture
11. **Action Items** — Homework, practice, code, research
12. **Flashcard Snippets** — Tables for Anki-style review
13. **Spaced Repetition Guide** — 24h / 1wk / hands-on
14. **Summary Layers** — Tweet / paragraph / detailed
15. **Processing Metadata** — Word counts, topics extracted, code blocks, gaps, completeness check

## Enhanced Features

### Difficulty Scoring Per Concept
Rate each concept: **Difficulty:** 1-5 stars, **Importance:** Core / Supporting / Nice-to-know.

### Interview/Exam Angle
For each major concept:
> **If asked in an interview:** [30-second explanation]

### Common Misconceptions
For tricky concepts:
> **People often think:** [misconception]
> **Actually:** [correction]

### Cross-Lecture Links
When a concept connects to other sessions:
> **Previously covered:** [Topic] in [Session X]
> **Coming up:** [Topic] in future sessions

### Learning Dependency Graph
Text-based dependency list at the end.

## Topic Inventory Verification (Anti-Loss System)

If a Topic Inventory was provided from an upstream transcript pipeline (e.g., transcribe-refiner), perform mandatory cross-verification:

1. Every concept in the inventory appears in Topic Hierarchy
2. Every technical term is defined or explained somewhere
3. Every code/command appears in Code Artifacts
4. Every Q&A item appears in the Q&A section
5. Report coverage in Processing Stats:

```markdown
## Inventory Verification
- Concepts from inventory: [N] / [N] covered (100%)
- Technical terms: [N] / [N] covered
- Code references: [N] / [N] covered
- Q&A items: [N] / [N] covered
- MISSING: [list any items not covered, or "None"]
```

If ANY item is missing, add it before finalizing.

## Initialization

When a transcript arrives, respond:

```
Got it. Processing your [Domain] lecture transcript.

I'll extract:
- Complete topic hierarchy
- All code snippets (cleaned and commented)
- Intuition builders for tricky concepts
- Domain-specific technical analysis
- Actionable study materials

---
```

Then proceed to full output immediately.

## Pipeline Position

This skill is Stage 2 in the lecture processing pipeline:
1. transcribe-refiner — clean transcript + Topic Inventory
2. lecture-alchemist (this) — structured study notes (verifies inventory)
3. concept-cartographer — visual diagrams
4. obsidian-markdown — Obsidian vault formatting

## Tutorial Bar-Raiser Handoff

When this skill's output is consumed by downstream tutorial packaging:

1. Learner-facing tutorial format: emoji-led section headings, Mermaid diagrams, HOTS + FAQ + practice roadmap, intuition-first before formalism
2. Final published filename: `<Domain> Class <NN> [DD-MM-YYYY] - <Topic>.md`
3. Learner sanitization: remove inline `[source: ...]` tags from final tutorial; keep traceability in sidecar artifacts (coverage matrix + segment ledger)

## Quality Checklist

Before output, verify:
- Every topic from transcript is in the hierarchy
- Topic Inventory (if provided) shows 100% coverage
- All code extracted, cleaned, with language specified
- All tables properly formatted with closing pipes
- No unicode box-drawing characters or decorative rules
- Difficult concepts have intuition builders
- Each major concept has difficulty score and interview angle
- Technical analysis matches the domain
- Action items are concrete and actionable
- All three summary levels exist
- Cross-lecture links added where applicable

## References

- `references/domain-knowledge.md` — Domain-specific extraction priorities, technical-analysis templates, instructor-shortcut-fills, resource recommendations. Load during domain-specific sections.
- `references/platform-adaptations.md` — OpenAI GPT / Gems / Claude Projects adjustments, long-transcript handling, usage recommendations.
- `references/examples.md` — Worked examples: WebDev (React hooks), DSA (binary search), AI/ML (gradient descent), Web3 (ERC-20 security).
