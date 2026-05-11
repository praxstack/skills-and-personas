# Stage 2 — Synthesize Notes

## When to load this file

Load at the start of Stage 2: after Stage 1 has produced a cleaned, speaker-attributed transcript (`stage1-refined.md`). Stage 2 output feeds Stage 3 (enhance).

## Input contract

- `stage1-refined.md` — cleaned paragraph transcript from Stage 1
- Domain hint: lecture / meeting / podcast / interview / tutorial

## Output contract

Structured notes that preserve every topic from the source while converting continuous prose to scannable, retention-optimized structure:

```
# [Lecture / Meeting / Session Title]

## Summary (3-5 sentences)

## Key Takeaways (5-10 bullets, most-important first)

## Topic 1: [descriptive heading]
- Core claim / concept
- Why it matters
- Supporting detail
- [Code block or formula if present]

## Topic 2: ...

## Questions raised / unresolved
- ...

## Action items / homework (if applicable)
- [ ] ...

## Glossary (terms introduced)
- **Term** — definition in context
```

## Synthesis rules

- **Zero topic loss.** Every topic in the source must appear in the notes. Compression happens within topics, not by dropping topics.
- **Preserve exact technical content.** Code, formulas, numeric values, URLs, library names, function signatures — never paraphrase.
- **Lead with the claim.** Each bullet starts with the main idea, not the speaker's preamble.
- **Quote sparingly.** Direct quotes only when the wording itself is load-bearing (aphorism, specific phrase the user will recall).
- **Extract actions and questions explicitly.** Don't leave them buried in prose.
- **Normalize terminology.** If the speaker used "cache" and "caching" interchangeably for the same concept, pick one.

## Retention-optimization techniques

- **3-level hierarchy max.** Topic → sub-topic → detail. Deeper nesting hurts scanability.
- **Parallel structure.** Bullets at the same level should share grammatical shape.
- **Chunking.** Group related bullets under a sub-heading when there are >4 under a parent.
- **Progressive disclosure.** Summary + Key Takeaways at the top give the 30-second version; deeper sections give the full picture.
- **Explicit contrast.** When the source contrasts two approaches, use a comparison table or X vs Y structure.
- **Callouts for "remember this".** Use blockquotes for content the instructor emphasized ("this is on the test", "this is the key insight").

## Domain-specific synthesis

| Domain | Synthesis emphasis |
|---|---|
| Technical lecture | Preserve code verbatim, build a "concepts → definitions" glossary, extract patterns and trade-offs explicitly |
| System design session | Capture every constraint the speaker mentions, build a decision tree from the design choices |
| Business meeting | Lead with decisions made, then actions with owners, then discussion context |
| Podcast / interview | Preserve the arc; questions stay in order; extract the 3-5 most quotable insights |
| Tutorial / screencast | Step-by-step with exact commands and expected output |

## Coverage verification

After synthesis, run a topic-coverage check:

- Every section header from the source appears in the notes (or is absorbed into a clearly-mapped topic)
- Every code block / formula is preserved
- Every named concept has a one-line definition
- Action items are explicit with owners if stated
- Questions raised are captured

If coverage fails, redo Stage 2 with tighter adherence to source structure.

## Hand-off to Stage 3

Stage 3 expects:
- Structured markdown notes
- Zero topic loss
- All technical content intact
- A glossary of terms introduced

Output goes to `stage2-synthesized.md` in the working directory.
