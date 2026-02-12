# Stage 3 Guide: Enhancement + Packaging

## Inputs

1. `.pipeline/structured_notes.md`
2. `.pipeline/coverage_matrix.json`
3. `.pipeline/topic_inventory.json`

## Outputs

1. `.pipeline/enhanced_notes.md`
2. `final_notes.md`
3. `bootcamp_index.md`

## Non-Negotiable Rules

1. Do not overwrite original lecture meaning.
2. Mark added pedagogical content with `[ENHANCED: ...]`.
3. Keep source mapping `[source: <segment_id>]`.
4. Preserve major timestamp anchors as `<!-- T:HH:MM:SS -->` when available.

## Required Enhancements

1. Topic intro blurbs
2. Tiny-concept clarifications
3. Better examples
4. Misconceptions and corrections
5. HOTS questions
6. FAQ block
7. Mermaid diagrams (preferred)
8. ASCII diagram fallback (when Mermaid is unsuitable)

## Diagram Policy

- Prefer Mermaid for process/relationship visuals.
- Use ASCII only for terminal-friendly or ultra-simple structures.
- Every diagram section should retain nearby source mapping.

## Packaging Guidance

- `.pipeline/enhanced_notes.md`: full fidelity + pedagogy layer.
- `final_notes.md`: learner-first polished output with traceability intact.
- `bootcamp_index.md`: cross-lecture links and concept navigation.

## Stage 3 Exit Checklist

- All added content is explicitly marked `[ENHANCED]`.
- No unsupported factual additions.
- Mermaid count and enhanced-claim count are reported.
- Final notes remain source-traceable.
