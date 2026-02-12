# Technical BRD — MindFlow RAG System

> **Version**: 3.0 · **Date**: February 12, 2026 · **Classification**: Technical Business Requirements

---

## 1. Purpose

This document defines the **technical requirements, constraints, and quality attributes** for the MindFlow RAG system. It bridges the business-level BRD (which defines *what* MindFlow does) with the Architecture HLD (which defines *how* it's built).

---

## 2. System Scope

### 2.1 In Scope (Phase 1)

| Capability | Description |
|-----------|------------|
| **PDF Ingestion Pipeline** | Parse, chunk, tag, embed 36+ therapy textbooks |
| **Hybrid Search Server** | 4-stage pipeline: vector + BM25 + hypothetical Q + reranking |
| **Clinical Validation** | 3-node pipeline: Gatekeeper, Auditor, Strategist |
| **Evaluation Framework** | Golden Set (50 queries), LLM judges, red team (10 scenarios) |
| **Citation System** | Invisible default; cite with book/author/chapter on request |
| **Watch Folder** | Auto-detect and ingest new PDFs |
| **React Integration** | `ragService.ts` abstraction with env-based backend swap |

### 2.2 Out of Scope (Phase 1)

| Capability | Deferred To |
|-----------|-------------|
| Cloud-hosted vector DB | Phase 2 |
| Multi-user authentication | Phase 2 |
| Real-time collaborative editing | Future |
| Voice input/output for RAG | Future |
| Multi-language corpus support | Future |

---

## 3. Technical Requirements

### 3.1 Performance Requirements

| Metric | Requirement | Measurement Method |
|--------|------------|-------------------|
| **Search latency** (localhost) | < 100ms p95 | FastAPI response timer |
| **Search latency** (cloud, Phase 2) | < 300ms p95 | API response timer + caching |
| **Ingestion throughput** | ≥ 5 pages/second | Batch processing timer |
| **Embedding generation** | ≥ 50 chunks/second | sentence-transformers batch |
| **Reranking latency** | < 10ms per query | FlashRank benchmarking |
| **Full pipeline** (user message → validated response) | < 5s total | End-to-end timer |
| **ChromaDB cold start** | < 2s | First query after server start |
| **Memory footprint** (server) | < 500MB RSS | Process monitoring |

### 3.2 Quality Requirements

| Metric | Requirement | Measurement Method |
|--------|------------|-------------------|
| **Retrieval precision@5** | ≥ 80% | Golden Set testing |
| **Retrieval recall (P0 content)** | ≥ 90% | Safety protocol retrieval rate |
| **Hallucination rate** | < 2% | LLM judge evaluation |
| **Crisis detection rate** | 100% (zero misses) | Red team testing |
| **Citation accuracy** | ≥ 95% | Manual review of cited sources |
| **Grounding rate** | ≥ 90% | Auditor pass rate |

### 3.3 Reliability Requirements

| Requirement | Specification |
|------------|--------------|
| **Server availability** (local) | Always available when Mac is running |
| **Graceful degradation** | If RAG server is down, fallback to ungrounded Claude response with warning |
| **Data durability** | ChromaDB persistence to disk (SQLite) |
| **Ingestion idempotency** | Re-running ingestion on same book = no duplicates |
| **Error recovery** | Failed chunk processing skips chunk, logs error, continues |

### 3.4 Security & Privacy Requirements

| Requirement | Implementation |
|------------|---------------|
| **User data isolation** | All user data in browser localStorage only |
| **No user data to RAG server** | Search API receives query text + clinical context (condition, severity) — never PII |
| **API key protection** | Claude API key in `.env`, gitignored |
| **Book content protection** | Embedded chunks stored locally, never transmitted externally |
| **Audit trail** | Log all search queries + results for evaluation (local only) |

### 3.5 Compatibility Requirements

| Target | Requirement |
|--------|-----------|
| **Python** | 3.10+ (for match statements, typing improvements) |
| **Node.js** | 18+ (for React/Vite app) |
| **Browsers** | Chrome 90+, Firefox 88+, Safari 14+, Edge 90+ |
| **macOS** | 12+ (Monterey and later) |
| **Disk space** | ~2GB (models + ChromaDB + PDFs) |

---

## 4. Technology Stack Decisions

### 4.1 Stack Overview

| Layer | Technology | Version | License | Justification |
|-------|-----------|---------|---------|--------------|
| **Vector DB** | ChromaDB | 0.5+ | Apache 2.0 | Zero-config SQLite-backed, pip install, native metadata filtering |
| **BM25 Search** | rank-bm25 | 0.2+ | Apache 2.0 | Pure Python, no external deps, battle-tested |
| **Embeddings** | all-MiniLM-L6-v2 | - | Apache 2.0 | 80MB, 384-dim, runs on CPU, well-benchmarked |
| **Reranking** | FlashRank | 0.2+ | Apache 2.0 | ~4ms/query, no GPU, lightweight cross-encoder |
| **API Server** | FastAPI + Uvicorn | 0.110+ | MIT | Async, auto OpenAPI docs, Pydantic validation |
| **PDF Parsing** | PyMuPDF + pdfplumber | 1.24+ | AGPL / MIT | Best text + table extraction combo |
| **AI Tagging** | Claude API (Anthropic) | - | Commercial | Superior instruction-following for clinical classification |
| **Watch Folder** | watchdog | 4.0+ | Apache 2.0 | Cross-platform filesystem monitoring |
| **Frontend** | React + TypeScript + Vite | 18+ | MIT | Existing MindFlow stack |

### 4.2 Phase 2 Technology Upgrades

| Component | Phase 1 | Phase 2 | Why Upgrade |
|-----------|---------|---------|-------------|
| Vector DB | ChromaDB (local) | Supabase pgvector (500MB free) | Multi-user, always-on, managed |
| Embedding | all-MiniLM-L6-v2 (local) | text-embedding-3-small (API) | Higher quality, 1536-dim |
| Reranker | FlashRank | bge-reranker-v2-m3 | State-of-art open-source, ~600M params |
| Hosting | localhost | Railway/Render (free tier) | Accessible from anywhere |
| Caching | None | Upstash Redis (free tier) | Reduce redundant searches |
| Monitoring | Console logs | Sentry (free tier) | Error tracking + alerting |

---

## 5. Integration Requirements

### 5.1 Existing MindFlow Integrations

| System | Integration Type | Data Exchanged |
|--------|-----------------|----------------|
| **Claude API** | REST (existing) | System prompt + user message + retrieved context |
| **localStorage** | Browser API (existing) | Clinical file, session history, screening scores |
| **clinicalFileStore** | Zustand store (existing) | Diagnoses, modality, severity for search filtering |
| **sessionStore** | Zustand store (existing) | Conversation context for deduplication |

### 5.2 New Integrations (Phase 1)

| System | Integration Type | Purpose |
|--------|-----------------|---------|
| **FastAPI server** | REST (localhost:8765) | Search API for RAG |
| **ragService.ts** | TypeScript module | Abstraction layer for search |
| **Validation pipeline** | TypeScript module | Gatekeeper + Auditor + Strategist |

---

## 6. Data Requirements

### 6.1 Knowledge Corpus

| Attribute | Specification |
|-----------|--------------|
| **Source format** | PDF (therapy textbooks) |
| **Corpus size (Phase 1)** | 36 books, ~15,000 pages |
| **Expected chunk count** | ~5,000-8,000 chunks |
| **Chunk size range** | 200-800 tokens (variable by type) |
| **Embedding dimension** | 384 (all-MiniLM-L6-v2) |
| **Estimated storage** | ~50MB (ChromaDB) |

### 6.2 Metadata Taxonomy

Each chunk carries structured metadata for filtering and citation:

| Field | Type | Values |
|-------|------|--------|
| `role` | enum | `therapist_reference`, `recommend_to_user` |
| `clinical_domains` | array | `depression`, `adhd`, `anxiety`, `trauma`, `procrastination`, etc. |
| `content_type` | enum | `diagnostic_criteria`, `intervention`, `worksheet`, `psychoeducation`, `screening_guide`, `safety_protocol`, `exercise`, `case_study` |
| `therapeutic_modality` | enum | `cbt`, `dbt`, `act`, `mbct`, `mi`, `ba`, `general` |
| `severity_level` | enum | `mild`, `moderate`, `severe`, `crisis`, `all` |
| `key_techniques` | array | `thought_records`, `behavioral_activation`, `mindfulness`, etc. |
| `hypothetical_questions` | array | Patient-language questions this chunk answers |

---

## 7. Constraints

### 7.1 Hard Constraints

| Constraint | Detail |
|-----------|--------|
| **No user PII in RAG server** | Search queries contain clinical context (condition, severity) but never names, emails, or identifiable data |
| **No medication recommendations** | System must refuse to recommend specific drugs — validated by Strategist node |
| **No diagnostic claims** | System must refuse to diagnose — validated by Strategist node |
| **Crisis detection = 100%** | Zero tolerance for missed crisis signals — validated by Gatekeeper |
| **Local-first execution** | Phase 1 must work entirely offline except for Claude API calls |

### 7.2 Soft Constraints

| Constraint | Detail | Flexibility |
|-----------|--------|-------------|
| **Free-tier cloud services** | Phase 2 uses free tiers only | Can upgrade if revenue justifies |
| **Single-user local mode** | Phase 1 runs on developer's Mac | Multi-user in Phase 2 |
| **36-book corpus** | Current library | Expandable to 200+ |

---

## 8. Acceptance Criteria

### 8.1 Phase 1 Acceptance

| # | Criterion | Verification |
|---|----------|-------------|
| AC-1 | All 36 books ingested with correct metadata | config.yaml audit + manual spot check |
| AC-2 | Hybrid search returns relevant results for all Golden Set queries | Golden Set precision ≥ 80% |
| AC-3 | Crisis queries trigger Gatekeeper 100% of the time | Red team test suite |
| AC-4 | No hallucinated clinical claims in evaluation set | LLM judge hallucination rate < 2% |
| AC-5 | Citations are accurate when requested | Manual review of 20 cited responses |
| AC-6 | Search latency < 100ms on localhost | Automated benchmark |
| AC-7 | New PDF auto-ingestion works via watch folder | Drop test PDF → verify in ChromaDB |
| AC-8 | `VITE_RAG_URL` swap to cloud endpoint works | Integration test with mock cloud |

---

*Document maintained as part of MindFlow RAG Architecture v3.0*
