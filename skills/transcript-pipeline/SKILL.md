---
name: transcript-pipeline
description: "End-to-end transcript-to-notes pipeline with deterministic ingestion and validation. Use when user asks to process Zoom/class transcripts into high-quality notes with full traceability, strict no-loss accountability, staged execution, uncertainty handling, coverage matrices, and PASS/FAIL hard-gate validation. Works with chunked large transcripts and produces learner outputs plus .pipeline audit artifacts."
---

# Transcript Pipeline

Run a 4-stage transcript processing pipeline with deterministic accountability.

## Use This Skill When

- User asks to process class/lecture transcripts into notes.
- User requires no-loss accountability and source traceability.
- User needs uncertainty-aware correction + deterministic validation.
- User wants one repeatable workflow across Codex/OpenCode/Claude.

## Core Contract

1. Stage order is fixed: Stage 1 -> Stage 2 -> Stage 3 -> Stage 4.
2. Deterministic components are scripts, not LLM judgment.
3. Traceability must be preserved in `.pipeline` artifacts; learner-facing notes can be sanitized for readability.
4. No silent low-confidence correction.
5. Final status is PASS/FAIL from validation script.
6. Stage 3 must pass the Tutorial Tech Bar-Raiser gate.
7. Final learner note naming is mandatory across domains.

## Required Outputs

Learner outputs:

1. `final_notes.md`
2. `<DomainFile> Class <NN> [DD-MM-YYYY] - <Topic>.md`
3. `bootcamp_index.md`

Pipeline outputs:

1. `.pipeline/segment_ledger.jsonl`
2. `.pipeline/segment_manifest.jsonl`
3. `.pipeline/refined_transcript.md`
4. `.pipeline/topic_inventory.json`
5. `.pipeline/corrections_log.csv`
6. `.pipeline/uncertainty_report.json`
7. `.pipeline/structured_notes.md`
8. `.pipeline/coverage_matrix.json`
9. `.pipeline/enhanced_notes.md`
10. `.pipeline/validation_report.md`
11. `.pipeline/exceptions.json` (conditional)
12. `.pipeline/human_review_queue.md` (conditional)

## Stage Workflow

### Stage 1: Ingest + Refine

Run deterministic ingestion first:

```bash
python scripts/ingest_captions.py "<input_path>"
```

Then perform uncertainty-aware refinement guided by:

- `references/stage1-refine-guide.md`
- `references/domain-corrections.md`

Never skip corrections log or uncertainty report.

### Stage 2: Structured Synthesis

Use:

- `references/stage2-synthesize-guide.md`

Produce structured notes and coverage matrix with segment mappings.

### Stage 3: Enhancement + Packaging

Use:

- `references/stage3-enhance-guide.md`
- `references/output-template.md`
- `references/tutorial-tech-bar-raiser.md`

Mark all added pedagogical material using `[ENHANCED: ...]`.
Keep `[source: ...]` only in `.pipeline/enhanced_notes.md`, not in learner-facing `final_notes.md`.

### Stage 4: Deterministic Validation

Run validator:

```bash
python scripts/validate_coverage.py --pipeline-dir .pipeline
```

Validation guidance:

- `references/stage4-validate-guide.md`

Hard gates:

1. Segment accountability
2. Uncertainty retention
3. No orphan claims

### Stage 5: Tutorial Publish + Naming

Run learner-facing publishing step:

```bash
python scripts/publish_tutorial_notes.py --root "<sessions_root>" --session-dir "<session_dir>"
```

This step must:

1. enforce title/H1 class naming convention
2. remove inline source tags from learner-facing notes
3. create published tutorial filename
4. refresh `bootcamp_index.md`

If FAIL, patch earliest failing stage and retry up to 3 times.

## Large Transcript Handling

If transcript is too large for one stage context:

1. Split Stage 1 into chunks.
2. Run Stage 1 per chunk.
3. Merge with:

```bash
python scripts/merge_chunks.py --chunk-dirs <chunkA/.pipeline> <chunkB/.pipeline> --output-dir <session/.pipeline>
```

4. Continue Stage 2-4 on merged artifacts.

## Progressive Disclosure Rules

- Load only stage-specific reference file(s) for the current stage.
- Do not preload all references when not needed.
- Keep stage outputs isolated and explicit.

## Tool-Enabled vs Tool-Restricted

Tool-enabled:

- Write files directly.
- Always run deterministic scripts.

Tool-restricted:

- Run one stage per conversation.
- Emit artifacts in fenced blocks.
- Mark validation as non-deterministic unless script output is provided.

## Execution Checklist

Before completion, verify:

1. All required artifacts exist.
2. Validation script executed.
3. PASS/FAIL status is explicit.
4. Any unresolved uncertainty is listed in review queue.
5. Final notes remain source-traceable.
6. Published tutorial filename exists and bootcamp index points to it.
