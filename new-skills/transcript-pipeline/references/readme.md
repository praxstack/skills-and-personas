# Transcript Pipeline Kit

A provider-agnostic, deterministic transcript-to-tutorial system for Zoom class captions.

## Why This Exists

LLM transformations are probabilistic. This kit guarantees accountability by splitting responsibilities:

- Scripts for deterministic stages (ingest, `validate`, publish).
- Chat providers for language-heavy stages (refine, synthesize, enhance).
- Traceability artifacts in `.pipeline/` for every session.

## System Architecture

```mermaid
flowchart TD
  A[Raw Zoom Captions] --> B[Stage 0: ingest_zoom_captions.py]
  B --> C[.pipeline/segment_ledger.jsonl]
  C --> D[Stage 1 Chat: refine]
  D --> E[Stage 2 Chat: synthesize]
  E --> F[Stage 3 Chat: enhance]
  F --> G[final_notes.md]
  G --> H[Deep Pass Gate (--deep-pass)]
  H --> I[Stage 4: validate_coverage.py]
  I --> J[publish_tutorial_notes.py]
  J --> K[Published tutorial file]
```

## What You Get

Scripts below live in the external transcript-pipeline-kit repo under its own `scripts/` directory, NOT inside this skill. File names are referenced here conceptually so users know what each stage does; the skill does not bundle these files.

- End-to-end run orchestration: **run_chat_pipeline.py**
- Deterministic ingestion: **ingest_zoom_captions.py**
- Deterministic validation: **validate_coverage.py**
- Standardized publishing: **publish_tutorial_notes.py**
- Chunk merge utility: **merge_chunks.py**
- Dedicated Colab explainer pipeline: **run_colab_notebook_pipeline.py**
- Authenticated resource enrichment (Notion/Canva): **resource_enrichment.py**

## Strict Quality Gate (`--deep-pass`)

Enable deep tutorial quality enforcement in the runner.

It hard-fails if `final_notes.md` misses any of these:

- Prerequisite rescue section
- Intuition depth (minimum threshold)
- Mermaid diagram block
- HOTS section (minimum actionable items)
- FAQ section (minimum Q/A entries)
- Practice plan/roadmap section

Reports:

- `.pipeline/deep_pass_report.md`
- `.pipeline/deep_pass_exceptions.json`

## Quick Start

```bash
cd /Users/praxlannister/Documents/Zoom/transcript-pipeline-kit
python3 scripts/run_chat_pipeline.py run "<transcript_or_session_path>" --deep-pass
```

## Colab Code Pipeline (AI/ML)

```bash
cd /Users/praxlannister/Documents/Zoom/transcript-pipeline-kit
python3 scripts/run_colab_notebook_pipeline.py
```

This augments AI/ML notes with official resource links, full notebook code appendices, import/function deep explanations, and line-by-line learning commentary.

## Authenticated Resource Enrichment

```bash
cd /Users/praxlannister/Documents/Zoom/transcript-pipeline-kit
python3 scripts/resource_enrichment.py --all-sessions
```

Optional auth for deeper extraction:

- `NOTION_TOKEN_V2` + `NOTION_ACTIVE_USER` for Notion block extraction.
- `RESOURCE_PLAYWRIGHT_STORAGE_STATE` for authenticated Canva capture.

See: `resource-enrichment-authenticated-flow.md`

## Canonical Docs

- Full usage: `usage-guide.md`
- Colab pipeline spec: `colab-notebook-explainer-pipeline.md`
- Resource enrichment spec: `resource-enrichment-authenticated-flow.md`
- Prompts: `docs/prompts`
- Blueprint: `transcript-intelligence-master-blueprint.md`
- SOP: `multi-agent-contribution-sop.md`

## Repo Layout

```text
transcript-pipeline-kit/
├── SKILL.md
├── references/
│   ├── readme.md
│   ├── usage-guide.md
│   ├── prompts/
│   ├── transcript-intelligence-master-blueprint.md
│   └── multi-agent-contribution-sop.md
└── scripts/
    ├── run_chat_pipeline.py
    ├── run_colab_notebook_pipeline.py
    ├── resource_enrichment.py
    ├── ingest_zoom_captions.py
    ├── validate_coverage.py
    ├── publish_tutorial_notes.py
    └── merge_chunks.py
```
