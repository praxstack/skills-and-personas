# API Reference — MindFlow RAG Server

> **Version**: 3.0 · **Date**: February 12, 2026 · **Base URL**: `http://localhost:8765`

---

## Overview

The MindFlow RAG Server is a FastAPI application providing hybrid clinical knowledge search. It runs locally at `localhost:8765` (Phase 1) or at a cloud endpoint (Phase 2). The React frontend communicates with it via the `ragService.ts` abstraction layer.

**Base URL**:
- Phase 1 (local): `http://localhost:8765`
- Phase 2 (cloud): Set via `VITE_RAG_URL` environment variable

---

## Endpoints

### `POST /search`

Perform hybrid search across the clinical knowledge base.

**Request Body**:

```json
{
  "query": "I scored 22 on the PHQ-9 and I can't get out of bed",
  "user_context": {
    "diagnoses": ["MDD"],
    "therapeutic_modality": "cbt",
    "severity_level": "severe",
    "clinical_domains": ["depression"],
    "phq9_score": 22,
    "gad7_score": null,
    "session_number": 4
  },
  "top_k": 5,
  "include_metadata": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | ✅ | User's message or search query |
| `user_context` | object | ❌ | Clinical context for metadata filtering |
| `user_context.diagnoses` | string[] | ❌ | Active diagnoses (e.g., `["MDD", "ADHD"]`) |
| `user_context.therapeutic_modality` | string | ❌ | Active modality: `cbt`, `dbt`, `act`, `mbct`, `general` |
| `user_context.severity_level` | string | ❌ | Current severity: `mild`, `moderate`, `severe`, `crisis` |
| `user_context.clinical_domains` | string[] | ❌ | Relevant domains for filtering |
| `user_context.phq9_score` | int | ❌ | Latest PHQ-9 score (0-27) |
| `user_context.gad7_score` | int | ❌ | Latest GAD-7 score (0-21) |
| `user_context.session_number` | int | ❌ | Current session number |
| `top_k` | int | ❌ | Number of results (default: 5, max: 10) |
| `include_metadata` | bool | ❌ | Include full metadata in response (default: true) |

**Response (200 OK)**:

```json
{
  "results": [
    {
      "chunk_id": "beck_cog_therapy_ch3_p45_001",
      "text": "PHQ-9 SCORING INTERPRETATION: A total score of 20-27 indicates severe depression. Clinical action: Consider combination therapy (medication + psychotherapy). Immediate safety assessment recommended if Question 9 score ≥ 1...",
      "score": 0.924,
      "search_scores": {
        "vector": 0.87,
        "bm25": 0.95,
        "hypothetical": 0.82,
        "reranked": 0.924
      },
      "metadata": {
        "source": {
          "book_title": "Cognitive Therapy of Depression",
          "author": "Aaron T. Beck",
          "chapter": "Chapter 3: Assessment and Measurement",
          "page_range": "44-48",
          "short_title": "Cognitive Therapy of Depression"
        },
        "role": "therapist_reference",
        "clinical_domains": ["depression", "cbt"],
        "content_type": "screening_guide",
        "therapeutic_modality": "cbt",
        "severity_level": "severe",
        "key_techniques": ["phq9_interpretation", "severity_assessment"],
        "hypothetical_questions": [
          "What does a PHQ-9 score of 22 mean?",
          "How severe is my depression based on the PHQ-9?"
        ],
        "chunk_summary": "PHQ-9 scoring guide with clinical action recommendations by severity level."
      }
    }
  ],
  "query_info": {
    "original_query": "I scored 22 on the PHQ-9 and I can't get out of bed",
    "filters_applied": {
      "clinical_domains": ["depression"],
      "severity_level": ["severe", "crisis"]
    },
    "search_stages": {
      "vector_candidates": 20,
      "bm25_candidates": 20,
      "hypothetical_candidates": 10,
      "after_fusion": 15,
      "after_reranking": 5
    },
    "latency_ms": 47
  }
}
```

**Error Responses**:

| Status | Body | Cause |
|--------|------|-------|
| `400` | `{"error": "Query is required"}` | Missing query field |
| `503` | `{"error": "Knowledge base not initialized"}` | ChromaDB not loaded |
| `500` | `{"error": "Search failed", "detail": "..."}` | Internal server error |

---

### `GET /health`

Health check endpoint for monitoring.

**Response (200 OK)**:

```json
{
  "status": "healthy",
  "version": "3.0.0",
  "uptime_seconds": 3600,
  "chromadb": "connected",
  "bm25_index": "loaded",
  "reranker": "loaded",
  "embedding_model": "loaded"
}
```

---

### `GET /stats`

Corpus statistics and search engine status.

**Response (200 OK)**:

```json
{
  "corpus": {
    "total_books": 36,
    "total_chunks": 6247,
    "total_hypothetical_questions": 18741,
    "books_by_role": {
      "therapist_reference": 13,
      "recommend_to_user": 23
    },
    "chunks_by_domain": {
      "depression": 1842,
      "adhd": 1654,
      "anxiety": 987,
      "cbt": 1432,
      "dbt": 654,
      "act": 487,
      "executive_function": 723,
      "behavior_change": 468
    }
  },
  "search_engine": {
    "vector_db": "chromadb",
    "embedding_model": "all-MiniLM-L6-v2",
    "embedding_dimension": 384,
    "reranker": "flashrank",
    "bm25_vocabulary_size": 42891
  }
}
```

---

### `POST /ingest`

Trigger ingestion of a new book. Requires the book file to be present in the configured `Books/` directory.

**Request Body**:

```json
{
  "filename": "New Book Title (Author Name).pdf",
  "role": "therapist_reference",
  "clinical_domains": ["depression", "cbt"],
  "short_title": "New Book Title",
  "author": "Author Name"
}
```

**Response (202 Accepted)**:

```json
{
  "status": "ingestion_started",
  "filename": "New Book Title (Author Name).pdf",
  "estimated_chunks": 180,
  "job_id": "ingest_2026-02-12_001"
}
```

---

### `GET /ingest/{job_id}`

Check status of an ingestion job.

**Response (200 OK)**:

```json
{
  "job_id": "ingest_2026-02-12_001",
  "status": "completed",
  "progress": {
    "pages_parsed": 320,
    "chunks_created": 187,
    "chunks_tagged": 187,
    "chunks_embedded": 187
  },
  "duration_seconds": 124,
  "errors": []
}
```

---

## TypeScript Client: `ragService.ts`

```typescript
// src/services/ragService.ts

export interface ClinicalContext {
  diagnoses?: string[];
  therapeutic_modality?: string;
  severity_level?: string;
  clinical_domains?: string[];
  phq9_score?: number | null;
  gad7_score?: number | null;
  session_number?: number;
}

export interface ChunkMetadata {
  source: {
    book_title: string;
    author: string;
    chapter: string;
    page_range: string;
    short_title: string;
  };
  role: 'therapist_reference' | 'recommend_to_user';
  clinical_domains: string[];
  content_type: string;
  therapeutic_modality: string;
  severity_level: string;
  key_techniques: string[];
  hypothetical_questions: string[];
  chunk_summary: string;
}

export interface SearchResult {
  chunk_id: string;
  text: string;
  score: number;
  search_scores: {
    vector: number;
    bm25: number;
    hypothetical: number;
    reranked: number;
  };
  metadata: ChunkMetadata;
}

export interface SearchResponse {
  results: SearchResult[];
  query_info: {
    original_query: string;
    filters_applied: Record<string, string[]>;
    search_stages: Record<string, number>;
    latency_ms: number;
  };
}

const RAG_ENDPOINT = import.meta.env.VITE_RAG_URL || 'http://localhost:8765';

export async function searchKnowledge(
  query: string,
  userContext: ClinicalContext,
  topK: number = 5
): Promise<SearchResponse> {
  const response = await fetch(`${RAG_ENDPOINT}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      user_context: userContext,
      top_k: topK,
      include_metadata: true
    })
  });

  if (!response.ok) {
    throw new Error(`RAG search failed: ${response.statusText}`);
  }

  return response.json();
}

export async function getServerHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${RAG_ENDPOINT}/health`);
    return response.ok;
  } catch {
    return false;
  }
}
```

---

## Context Injection Template

When search results are injected into the Claude system prompt:

```
RETRIEVED CLINICAL CONTEXT (from evidence-based sources):

[Chunk 1 | Score: 0.924 | Source: Cognitive Therapy of Depression, Beck, Ch.3]
PHQ-9 SCORING INTERPRETATION: A total score of 20-27 indicates severe depression...

[Chunk 2 | Score: 0.891 | Source: Feeling Good, Burns, Ch.5]
When experiencing severe depressive symptoms, behavioral activation is the first...

[Chunk 3 | ...]
...

GROUNDING RULES:
1. Every clinical technique you describe MUST come from the context above.
2. If the context doesn't contain relevant information, say: "That's an important
   question. Based on what I know, I'd suggest we explore..."
3. NEVER recommend specific medications or diagnoses.
4. For citations, default to invisible sourcing. If user asks "where did you learn
   that?", cite: "According to [Book Title] by [Author]..."
```

---

*Document maintained as part of MindFlow RAG Architecture v3.0*
