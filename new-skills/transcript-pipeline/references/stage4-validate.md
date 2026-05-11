# Stage 4 — Validate Coverage

## When to load this file

Load at the start of Stage 4: the final quality gate before delivering notes. Validates zero topic loss, technical accuracy, and resource enrichment readiness.

## Input contract

- `stage1-refined.md` — raw-to-clean transcript
- `stage2-synthesized.md` — structured notes
- `stage3-enhanced.md` — enriched notes
- Original source file (captions / transcript)

## Validation checklist

### Coverage — Zero Topic Loss

- [ ] Every section header from the source appears in the final notes
- [ ] Every code block or formula from the source is preserved verbatim
- [ ] Every URL from the source is preserved (clickable in final markdown)
- [ ] Every numeric value is preserved (spot check 10 values)
- [ ] Every named concept introduced has a definition in the notes
- [ ] Every action item stated is extracted and marked
- [ ] Every unresolved question is captured

**Pass criteria:** 100% coverage. Any miss → go back to Stage 2 or 3.

### Technical accuracy

- [ ] Code blocks compile / parse (for the language stated)
- [ ] Formula notation is syntactically correct (LaTeX, Mermaid, etc.)
- [ ] Library and tool names are spelled correctly (use canonical casing — React, Node.js, PostgreSQL)
- [ ] Algorithmic complexity claims match what the source said
- [ ] Nothing invented beyond the source (Stage 3 enhancements clearly marked)

**Pass criteria:** zero technical errors. Any error → correct and re-validate.

### Structure and readability

- [ ] Max 3-level heading hierarchy
- [ ] Paragraphs 2-6 sentences
- [ ] Bullet lists parallel-structured at each level
- [ ] Tables used where the source compares ≥2 items
- [ ] Diagrams render (validate Mermaid, PlantUML)
- [ ] Cross-links resolve

### Enhancement markers

- [ ] Stage 3 enhancements clearly marked with `> **Intuition:**`, `> **Analogy:**`, `> **Gap-fill:**`, or equivalent
- [ ] Source content is visually distinct from enhancement commentary
- [ ] Reader can extract "just the source" or "source + enhancements" easily

### Resource enrichment readiness

If the pipeline feeds a resource-enrichment step (Notion / Canva / Drive links):

- [ ] Each major topic has a placeholder for an enriched link
- [ ] Links are marked clearly (e.g., `🔗 [resource slot: <topic>]`)
- [ ] Any existing URLs from the source are already in the notes (not overwritten)

## Coverage metric (compute and log)

```
coverage = (source topics in notes) / (total source topics)
technical_accuracy = 1 - (errors / technical_claims)
enhancement_clarity = (marked enhancements) / (total enhancements)
```

Target:
- coverage ≥ 0.98 (allow 1-2% loss for fillers/redundant recaps)
- technical_accuracy = 1.0 (no tolerance for errors)
- enhancement_clarity ≥ 0.95

## Common failure modes

| Failure | Cause | Fix |
|---|---|---|
| Topic missing | Stage 2 compression too aggressive | Redo Stage 2 with stricter source-structure adherence |
| Code misquoted | Stage 1 ASR error not caught | Go back to source audio if available; or mark `[unclear: ...]` |
| Enhancement confused with source | Stage 3 markers missing/inconsistent | Re-run Stage 3 with strict marker discipline |
| Diagrams don't render | Invalid Mermaid syntax | Validate each diagram in a Mermaid sandbox |
| Glossary missing terms | Stage 2 didn't build glossary | Extract from Stage 2 notes before closing |

## Sign-off

When all checks pass, produce `final-notes.md` with:
- Stage 2 structure
- Stage 3 enhancements (clearly marked)
- Coverage report appended as frontmatter or final section
- Pipeline metadata (source file, dates, stages run, stage timing)

Deliver `final-notes.md` to the user.
