# Architecture Decision Records — MindFlow RAG System

> **Version**: 3.0 · **Date**: February 12, 2026 · **Classification**: Decision Log

---

## ADR Format

Each ADR follows the format: **Context → Decision → Consequences → Alternatives Considered**.

---

## ADR-001: ChromaDB as Local Vector Database

**Date**: February 12, 2026 · **Status**: ✅ Accepted

### Context

Need a vector database that runs locally with zero configuration for Phase 1, supports metadata filtering, and can be replaced with pgvector in Phase 2.

### Decision

Use **ChromaDB** (SQLite-backed) as the local vector database.

### Consequences

| ✅ Positive | ⚠️ Trade-offs |
|------------|--------------|
| `pip install chromadb` — zero config | Limited to single-process access |
| SQLite persistence — survives restarts | No built-in replication |
| Native metadata filtering with `where` clauses | Performance ceiling at ~100K vectors |
| Python-first API matches our stack | Requires migration to pgvector for cloud |

### Alternatives Considered

| Alternative | Why Rejected |
|------------|-------------|
| **Qdrant (local)** | Requires Docker for persistent mode; more complex setup |
| **Pinecone** | Cloud-only; requires API key for every search; adds latency |
| **LanceDB** | Less mature metadata filtering; smaller community |
| **FAISS** | No metadata filtering; raw vector operations only |
| **pgvector (local Postgres)** | Requires PostgreSQL installation; overkill for single-user local |

---

## ADR-002: FlashRank as Cross-Encoder Reranker

**Date**: February 12, 2026 · **Status**: ✅ Accepted

### Context

Initial retrieval (vector + BM25) returns candidate chunks that need precision reranking. Need a cross-encoder that runs on CPU without GPU requirements.

### Decision

Use **FlashRank** — a lightweight, CPU-friendly cross-encoder reranker.

### Consequences

| ✅ Positive | ⚠️ Trade-offs |
|------------|--------------|
| ~4ms per query — effectively instant | Lower quality than bge-reranker-v2-m3 |
| No GPU required — runs on any laptop | Less community benchmarking |
| ~70MB model size — small footprint | May need upgrade for Phase 2 |
| Apache 2.0 license | — |

### Alternatives Considered

| Alternative | Why Rejected |
|------------|-------------|
| **bge-reranker-v2-m3** | ~600M params, requires GPU or slow on CPU; Phase 2 candidate |
| **cross-encoder/ms-marco-MiniLM-L-6-v2** | Good quality but ~5x slower than FlashRank; 82MB |
| **Cohere Rerank API** | Cloud-only; per-request cost; adds dependency |
| **No reranking** | Significantly lower precision at top-5 |

---

## ADR-003: all-MiniLM-L6-v2 as Embedding Model

**Date**: February 12, 2026 · **Status**: ✅ Accepted

### Context

Need an embedding model that runs locally on CPU, produces quality vectors for semantic search, and is fast enough for batch ingestion of 36 books.

### Decision

Use **all-MiniLM-L6-v2** from sentence-transformers (384 dimensions).

### Consequences

| ✅ Positive | ⚠️ Trade-offs |
|------------|--------------|
| ~80MB model — small download | 384-dim vs 1536-dim (OpenAI) = lower capacity |
| ~200 chunks/sec on CPU | Not the best for medical terminology specifically |
| Well-benchmarked on MTEB | No domain-specific fine-tuning (acceptable for Phase 1) |
| Free, local, no API calls | — |

### Alternatives Considered

| Alternative | Why Rejected |
|------------|-------------|
| **text-embedding-3-small** (OpenAI) | API call per embed = cost during ingestion + latency at query time; Phase 2 candidate |
| **all-mpnet-base-v2** | Better quality but ~420MB, slower; marginal improvement |
| **PubMedBERT** | Medical domain but not designed for retrieval; no sentence-transformers integration |
| **BGE-large-en-v1.5** | 1.3GB; excessive for local embedding |

---

## ADR-004: FastAPI as RAG Server Framework

**Date**: February 12, 2026 · **Status**: ✅ Accepted

### Context

Need a lightweight HTTP server to expose search functionality to the React frontend. Must support async operations and auto-generated API documentation.

### Decision

Use **FastAPI** with Uvicorn.

### Consequences

| ✅ Positive | ⚠️ Trade-offs |
|------------|--------------|
| Async out of the box | Python process = additional resource usage |
| Auto-generated Swagger/OpenAPI docs at `/docs` | Cold start time for model loading |
| Pydantic validation ensures type safety | Need to manage Python process lifecycle |
| Same language as ingestion pipeline | — |

### Alternatives Considered

| Alternative | Why Rejected |
|------------|-------------|
| **Flask** | Synchronous by default; no auto-docs; no Pydantic |
| **Express.js** | Would require bridging to Python for ChromaDB/embeddings |
| **In-browser search** | Limited by browser memory; no BM25/reranking |
| **gRPC** | Overkill for single-client local communication |

---

## ADR-005: Hybrid Search (Vector + BM25 + Hypothetical Q) with RRF

**Date**: February 12, 2026 · **Status**: ✅ Accepted

### Context

Vector search alone fails for clinical exact terms (e.g., "PHQ-9", "TIPP skills"). BM25 alone fails for semantic paraphrases. Need to combine both.

### Decision

Use a **4-stage hybrid search pipeline**: metadata pre-filter → parallel vector/BM25/hypothetical Q search → Reciprocal Rank Fusion → FlashRank reranking.

### Consequences

| ✅ Positive | ⚠️ Trade-offs |
|------------|--------------|
| Catches both semantic and exact-term matches | More complex pipeline to debug |
| Hypothetical Q matching bridges patient→clinical language gap | Additional storage (~3x hypothetical questions) |
| RRF is parameter-light (only ranking constant k) | — |
| FlashRank reranking adds precision | — |

### RRF Configuration

```python
RRF_K = 60  # Standard constant
WEIGHTS = {
    "vector": 0.5,
    "bm25": 0.3,
    "hypothetical": 0.2
}
```

---

## ADR-006: 3-Node Validation Pipeline Over Single-Pass Validation

**Date**: February 12, 2026 · **Status**: ✅ Accepted

### Context

Medical AI requires rigorous output validation. A single validation pass could miss category-specific issues (crisis vs. grounding vs. appropriateness).

### Decision

Use **3 sequential, specialized validation nodes**: Gatekeeper → Auditor → Strategist.

### Consequences

| ✅ Positive | ⚠️ Trade-offs |
|------------|--------------|
| Each node has single responsibility | 3 validation steps add latency (~90ms total) |
| Gatekeeper runs first — crisis can't be missed | More code to maintain |
| Nodes can be independently tested | May over-filter in edge cases |
| Clear failure modes per node | — |

### Alternatives Considered

| Alternative | Why Rejected |
|------------|-------------|
| **Single Claude call for all validation** | Conflating crisis detection with grounding; harder to guarantee crisis never missed |
| **No validation** | Unacceptable for medical AI |
| **External validation service** | Adds latency; cloud dependency |

---

## ADR-007: Local-First Architecture with Cloud Migration Path

**Date**: February 12, 2026 · **Status**: ✅ Accepted

### Context

User requires maximum-quality Phase 1 that runs entirely locally (except Claude API). Phase 2 should migrate to cloud with zero code changes.

### Decision

Architecture uses **environment-variable-based endpoint switching** (`VITE_RAG_URL`). Phase 1 runs at `localhost:8765`; Phase 2 swaps to cloud URL.

### Consequences

| ✅ Positive | ⚠️ Trade-offs |
|------------|--------------|
| Zero cloud costs in Phase 1 | Single-user only in Phase 1 |
| Full control over all components | Must manage local Python processes |
| Privacy-preserving (nothing leaves the machine) | Can't access from other devices |
| Cloud migration = env var change | — |

---

## ADR-008: Invisible Citations as Default

**Date**: February 12, 2026 · **Status**: ✅ Accepted

### Context

Real therapists don't cite textbook references mid-conversation. But users may want to know sources for trust or further reading.

### Decision

**Invisible by default**: Dr. Alex never names sources unprompted. When user asks "where did you learn that?" or "what's your source?", citations appear with book title, author, and chapter.

### Consequences

| ✅ Positive | ⚠️ Trade-offs |
|------------|--------------|
| Natural conversational flow | Users may not know citations are available |
| Maintains therapist persona authenticity | Slightly less transparent by default |
| Source traceable when requested | — |

### Citation Format (On Request)

```
"That technique comes from 'Feeling Good' by David Burns (Chapter 5).
If you'd like to explore it further, that book has excellent exercises
you could work through on your own."
```

---

*Document maintained as part of MindFlow RAG Architecture v3.0*
