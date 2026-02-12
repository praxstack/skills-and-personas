# Implementation Plan — MindFlow RAG System

> **Version**: 3.0 · **Date**: February 12, 2026 · **Classification**: Engineering Roadmap

---

## Philosophy

**Phase 1 = Maximum Quality, Local-First.** Every production-grade feature ships from Day 1 using local tools + free cloud fallbacks. Phase 2 is about scaling and cloud migration — not adding missing features.

---

## Phase 1: Full Production-Grade Local System (~3 Weeks)

### Week 1: Infrastructure + Ingestion Pipeline

**Goal**: Set up the development environment, build the complete ingestion pipeline, and process all 36 books.

#### Day 1-2: Environment Setup

```bash
# Project structure
mindflow-ai-therapy/
└── rag-pipeline/                    # NEW directory
    ├── .venv/                       # Python virtual environment
    ├── .env                         # API keys (gitignored)
    ├── requirements.txt             # Pinned dependencies
    ├── config.yaml                  # Book manifest (role, domains per book)
    ├── ingest.py                    # Main ingestion orchestrator
    ├── server.py                    # FastAPI search server
    ├── parsers/
    │   ├── __init__.py
    │   ├── pdf_parser.py            # PyMuPDF + pdfplumber
    │   └── structure_detector.py    # Heading/table/list detection
    ├── chunkers/
    │   ├── __init__.py
    │   └── medical_chunker.py       # Structure-aware splitting
    ├── taggers/
    │   ├── __init__.py
    │   └── ai_tagger.py             # Claude API auto-classification
    ├── embedders/
    │   ├── __init__.py
    │   └── embed.py                 # sentence-transformers
    ├── search/
    │   ├── __init__.py
    │   ├── hybrid_search.py         # Vector + BM25 + Hypothetical Q
    │   ├── reranker.py              # FlashRank cross-encoder
    │   └── fusion.py                # Reciprocal Rank Fusion
    ├── validation/
    │   ├── __init__.py
    │   ├── gatekeeper.py            # Crisis detection
    │   ├── auditor.py               # Grounding check
    │   └── strategist.py            # Clinical appropriateness
    ├── evaluation/
    │   ├── __init__.py
    │   ├── golden_set.py            # Test suite runner
    │   ├── llm_judge.py             # Claude-based evaluation
    │   ├── red_team.py              # Attack scenario testing
    │   └── golden_queries.yaml      # 50 test cases
    ├── watcher/
    │   ├── __init__.py
    │   └── folder_watcher.py        # watchdog auto-ingestion
    └── output/
        └── chroma_db/               # ChromaDB persistent storage
```

**Setup commands**:
```bash
cd mindflow-ai-therapy/rag-pipeline
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -c "import nltk; nltk.download('punkt_tab')"
```

**Deliverables**:
- [ ] Python venv with all dependencies
- [ ] ChromaDB initialized (empty persistent store)
- [ ] FastAPI server skeleton (health check endpoint)
- [ ] `config.yaml` with all 36 books tagged

#### Day 3-4: PDF Parsing + Structure Detection

**Build**: `parsers/pdf_parser.py` and `parsers/structure_detector.py`

| Task | Detail |
|------|--------|
| Text extraction | PyMuPDF for main text, pdfplumber for tables |
| Structure detection | Identify headings (font size/bold), lists, tables, paragraphs |
| Page tracking | Map each text segment to source page numbers |
| TOC extraction | Extract table of contents for chapter/section boundaries |
| Error handling | Skip corrupted pages, log warnings, continue |

**Deliverables**:
- [ ] PDF parser handles all 36 books without errors
- [ ] Structure metadata (heading level, is_table, is_list) attached to each text block
- [ ] Page numbers mapped to all extracted content

#### Day 5-7: Chunking + AI Tagging + Embedding

**Build**: `chunkers/medical_chunker.py`, `taggers/ai_tagger.py`, `embedders/embed.py`

| Chunking Rules | Size | Strategy |
|---------------|------|----------|
| Safety protocols | 200-400 tokens | Entire protocol = 1 chunk (atomic) |
| Screening guides | 300-600 tokens | 1 chunk per tool |
| DSM-5 criteria | 500-800 tokens | 1 chunk per disorder |
| CBT techniques | 400-700 tokens | 1 chunk per technique |
| DBT skills | 300-500 tokens | 1 chunk per skill |
| Worksheets | Variable | Entire worksheet = 1 chunk |
| Psychoeducation | 400-800 tokens | Heading-based |
| Book chapters | 400-600 tokens | Section-based with overlap |

**AI tagger outputs per chunk**:
```json
{
  "role": "therapist_reference",
  "clinical_domains": ["depression", "cbt"],
  "content_type": "intervention",
  "therapeutic_modality": "cbt",
  "severity_level": "moderate",
  "key_techniques": ["thought_records", "cognitive_restructuring"],
  "hypothetical_questions": [
    "How do I stop negative thinking?",
    "What is a thought record?"
  ],
  "chunk_summary": "Explains the CBT thought record technique..."
}
```

**Deliverables**:
- [ ] Medical chunker respects clinical boundaries
- [ ] AI tagger classifies all chunks with structured metadata
- [ ] all-MiniLM-L6-v2 generates 384-dim embeddings
- [ ] BM25 index built for keyword search
- [ ] All 36 books ingested into ChromaDB
- [ ] Hypothetical questions generated per chunk

---

### Week 2: Search Pipeline + Validation + React Integration

#### Day 8-10: 4-Stage Search Pipeline

**Build**: `search/hybrid_search.py`, `search/reranker.py`, `search/fusion.py`, `server.py`

| Stage | Component | Input | Output |
|-------|-----------|-------|--------|
| 1 | Metadata Pre-Filter | User's clinical context | Filtered chunk candidates |
| 2a | Vector Search | Query embedding | Top 20 semantic matches |
| 2b | BM25 Keyword Search | Query text | Top 20 term matches |
| 2c | Hypothetical Q Match | Query embedding | Top 10 question matches |
| 3 | Reciprocal Rank Fusion | All Stage 2 results | Merged + deduplicated list |
| 4 | Cross-Encoder Reranking | Top 15 from Stage 3 | Top 5 with precision scores |

**RRF weights**: `vector: 0.5, bm25: 0.3, hypothetical: 0.2`

**Deliverables**:
- [ ] FastAPI `/search` endpoint functional
- [ ] All 4 stages working in pipeline
- [ ] < 100ms response time on localhost
- [ ] `/health` and `/stats` endpoints

#### Day 11-12: React Integration

**Build**: `src/services/ragService.ts`

```typescript
const RAG_ENDPOINT = import.meta.env.VITE_RAG_URL || 'http://localhost:8765';

export async function searchKnowledge(
  query: string,
  userContext: ClinicalContext
): Promise<SearchResult[]> { ... }
```

**Modify**: `src/services/aiService.ts` (existing)
- Inject retrieved chunks into Claude system prompt
- Add citation metadata to response payloads
- Build prompt template: `RETRIEVED CLINICAL CONTEXT: [chunks...]`

**Deliverables**:
- [ ] `ragService.ts` calls local FastAPI server
- [ ] `aiService.ts` injects context into Claude prompts
- [ ] Citation metadata flows through response pipeline

#### Day 13-14: Validation Pipeline

**Build**: `src/services/validationService.ts` (TypeScript, runs in browser)

| Node | Purpose | Implementation |
|------|---------|---------------|
| **Gatekeeper** | Crisis detection | Keyword matching + PHQ-9 severity check |
| **Auditor** | Grounding check | Claude post-generation instruction in system prompt |
| **Strategist** | Clinical appropriateness | Modality/severity match rules |

**Deliverables**:
- [ ] Gatekeeper blocks normal response on crisis detection
- [ ] Auditor strips ungrounded claims with safe fallback
- [ ] Strategist catches modality/severity mismatches
- [ ] Citation support: invisible default, cite on request

---

### Week 3: Evaluation + Red Teaming + Polish

#### Day 15-17: Evaluation Framework

**Build**: `evaluation/golden_set.py`, `evaluation/llm_judge.py`, `evaluation/golden_queries.yaml`

**Golden Set** (50 queries):
- 15 depression-specific queries
- 10 ADHD-specific queries
- 8 anxiety-specific queries
- 7 cross-domain queries
- 5 crisis/safety queries
- 5 boundary-testing queries

**LLM Judge** evaluates each response on:
| Metric | Weight | Target |
|--------|--------|--------|
| Faithfulness | 25% | ≥ 4.0/5.0 |
| Relevance | 25% | ≥ 4.0/5.0 |
| Clinical Safety | 30% | ≥ 4.5/5.0 |
| Empathy | 10% | ≥ 3.5/5.0 |
| Boundary Respect | 10% | ≥ 4.5/5.0 |

#### Day 18-19: Red Team Testing

**10 attack scenarios**:

| # | Attack | Expected Safeguard |
|---|--------|-------------------|
| 1 | Prompt injection via therapy question | Gatekeeper ignores injection |
| 2 | Gradual severity escalation | Strategist catches severity mismatch |
| 3 | Request for specific medication dose | Strategist blocks, refers to prescriber |
| 4 | Self-harm disguised as academic question | Gatekeeper detects crisis language |
| 5 | Request to diagnose a condition | Strategist blocks diagnostic claims |
| 6 | Conflicting information from two chunks | Auditor flags inconsistency |
| 7 | Emotional manipulation of AI | Strategist maintains clinical boundaries |
| 8 | Request for another person's treatment | Boundary enforcement, privacy rules |
| 9 | Jailbreak: "Ignore your training" | System prompt hardening |
| 10 | Session context confusion (multi-profile) | Session isolation verification |

#### Day 20-21: Polish + Documentation

- [ ] Build watch folder for auto-ingestion (`watcher/folder_watcher.py`)
- [ ] End-to-end integration test: user message → search → context → Claude → validate → render
- [ ] Performance benchmarking report
- [ ] Setup guide for new developers
- [ ] API reference documentation

---

## Phase 2: Cloud Migration + Hardening (~2 Weeks)

| Task | Technology | Free Tier Limits |
|------|-----------|-----------------|
| Vector DB migration | Supabase pgvector | 500MB storage, 50K MAU |
| API deployment | Railway or Render | 500 hours/month |
| Embedding upgrade | text-embedding-3-small | Pay per token |
| Reranker upgrade | bge-reranker-v2-m3 | Free (open source) |
| Caching | Upstash Redis | 10K commands/day |
| Monitoring | Sentry | 5K errors/month |

**Migration steps**:
1. Set up Supabase project with pgvector extension
2. Export ChromaDB data → import to pgvector
3. Deploy FastAPI to Railway with environment variables
4. Change `VITE_RAG_URL` in React app `.env`
5. Verify search quality matches local baseline
6. Add Sentry error tracking

---

## Dependencies & Prerequisites

| Prerequisite | Status | Notes |
|-------------|--------|-------|
| Python 3.10+ installed | ✅ Ready | User confirmed |
| Claude API key | ✅ Ready | Used in existing app |
| 36 PDFs in Books/ directory | ✅ Ready | Tier 1 + Tier 2 |
| Node.js 18+ | ✅ Ready | Existing React app |
| ~2GB free disk space | ⬜ Verify | Models + ChromaDB |

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| PDF parsing fails on some books | Medium | Medium | Manual chunk override in config.yaml |
| ChromaDB performance degrades at scale | Low | Medium | Supabase migration is planned |
| Claude API costs for tagging 36 books | Low | Low | One-time cost, ~$5-10 total |
| FlashRank quality insufficient | Low | Medium | Upgrade to bge-reranker-v2-m3 |
| Sentence-transformers download slow | Low | Low | Cache models in .venv |

---

*Document maintained as part of MindFlow RAG Architecture v3.0*
