# MindFlow RAG System — Documentation Index

> **Version**: 3.0 · **Date**: February 12, 2026 · **Status**: ✅ Architecture Approved

---

## Purpose

This documentation suite covers the **complete Retrieval-Augmented Generation (RAG) system** for MindFlow's AI Therapy Assistant. It transforms Dr. Alex Morgan from a stateless LLM wrapper into a **knowledge-grounded clinical tool** backed by 36+ curated therapy textbooks.

## Document Map

| # | Document | Purpose | Audience |
|---|----------|---------|----------|
| 01 | [Architecture HLD](./01-ARCHITECTURE-HLD.md) | High-Level Design — system topology, data flows, component diagrams | Engineering, Architecture |
| 02 | [Tech BRD](./02-TECH-BRD.md) | Technical Requirements — NFRs, constraints, tech decisions, stack justification | Engineering, Product |
| 03 | [Implementation Plan](./03-IMPLEMENTATION-PLAN.md) | Week-by-week build roadmap with deliverables and dependencies | Engineering |
| 04 | [API Reference](./04-API-REFERENCE.md) | RAG server endpoints, request/response schemas, error codes | Engineering |
| 05 | [Data Architecture](./05-DATA-ARCHITECTURE.md) | Chunk schemas, metadata taxonomy, embedding strategy, storage design | Engineering, Data |
| 06 | [Validation Pipeline](./06-VALIDATION-PIPELINE.md) | Anti-hallucination shield — Gatekeeper, Auditor, Strategist nodes | Engineering, Clinical Safety |
| 07 | [Evaluation Framework](./07-EVALUATION-FRAMEWORK.md) | Golden Set testing, LLM judges, red teaming, quantitative metrics | QA, Engineering |
| 08 | [ADR Log](./08-ADR-LOG.md) | Architecture Decision Records — why we chose what we chose | Engineering, Architecture |
| 09 | [Production BRD](./09-PRODUCTION-BRD.md) | Business requirements for productionization + cloud migration | Product, Business |

## Core Principle

> **Bad retrieval is worse than no retrieval** — especially in medical AI. When given poor context, LLMs become *more* confident, not less, fabricating clinical advice that sounds authoritative. This architecture treats anti-hallucination as a **patient safety** concern, not a nice-to-have.

## Quick Reference

```
Phase 1:  Full production-grade, local-first (~3 weeks)
          ChromaDB + rank-bm25 + FlashRank + FastAPI + All 3 validation nodes
Phase 2:  Cloud migration + hardening (~2 weeks)
          Supabase pgvector + Railway/Render + monitoring
```

---

*Maintained by the MindFlow Engineering Team · Last updated: February 2026*
