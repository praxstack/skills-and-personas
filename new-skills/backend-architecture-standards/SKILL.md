---
name: backend-architecture-standards
description: 'Principal-engineer standards for backend services, APIs, data modeling, distributed systems, and reliability. Use when building or reviewing REST/GraphQL/gRPC APIs, database schemas, service boundaries, caching strategies, messaging, observability, or scaling patterns. Triggers on "design an API", "database schema", "service architecture", "distributed system", "caching strategy", "rate limit", "reliability pattern", "migration plan", "message queue", "SLI/SLO", and backend production reviews. Covers API disciplines, data modeling, scaling patterns, reliability patterns, DevOps and infra, data storage, observability, and performance. Loaded by super-mode-core for backend-heavy work.'
---

# Backend Architecture Standards

**Audience:** Backend engineers and architects reviewing or designing across multiple languages and services — the cross-cutting layer above any single `backend-pe-*` skill.

**Goal:** Capture the decisions that are cross-cutting and load-bearing but not language-specific. Language-specific failure modes live in `backend-pe-{python,typescript,java,cpp,nodejs,javascript,python-ml}` — this skill only holds what they all share.

Generic best practices (define SLOs, validate inputs at boundaries, use parameterized queries, enable TLS 1.3, deny by default) are Claude-default output and are not repeated here.

## Cross-cutting decisions

### HA/DR targets with explicit RTO/RPO

Every production service needs numbers, not adjectives:

- **RTO** (recovery time objective) — how long until service is back, measured from outage declaration. Typical tiers: 15 min (payments, auth), 1 hour (core product), 4 hours (internal tools).
- **RPO** (recovery point objective) — how much data loss is acceptable, measured in wall-clock time. Typical tiers: 0 (transactions), 5 min (user content), 1 hour (analytics).

The architecture is wrong if the replication strategy cannot physically meet the RPO (async replication across regions cannot deliver RPO=0, regardless of how the runbook reads).

### Event-driven consistency patterns

- **Exactly-once semantics is a myth at the transport layer.** Build idempotency into consumers — deterministic request IDs with a dedup window sized to the retry horizon. Transport provides at-least-once; consumers make it effectively-once.
- **Sagas over distributed transactions.** Every saga step needs a compensating action that is itself idempotent and runnable out-of-order. Document the failure matrix: which step failures can be retried, which trigger compensation, which require manual intervention.
- **Outbox pattern** for write-then-publish consistency. The database transaction that writes business state also writes the event row; a separate relay ships the row to the broker. Never write to the broker directly from application code inside a database transaction.
- **Event schema evolution must be additive only.** Removed or renamed fields break consumers that redeploy on a different cadence than producers. Deprecate for at least one full consumer rollout cycle before removal.

### Migration reversibility discipline

Every migration PR is required to include:

1. The forward migration.
2. The rollback script, executed at least once in a non-prod environment before merge.
3. The read-path compatibility plan — old code reading after new migration must still work until old code is drained.
4. The write-path compatibility plan — new code writing before old code drains must produce data readable by old code (or gated behind a flag).

Irreversible migrations (column drops, table renames, type narrowings) are multi-step: deploy dual-write, backfill, verify, drop old column, deploy read-only-new. One-step destructive migrations are forbidden on any table with user data.

### Hot-path / batch separation

Hot paths (user-facing latency budgets <200ms) and batch paths (throughput-optimized, latency-tolerant) compete for the same shared resources — database connections, cache bandwidth, network egress. Separation is architectural, not configurational:

- Different DB read replicas (or different connection pools on the same replica with hard limits).
- Different queues with different consumer pools.
- Different deployment units so a batch regression cannot degrade hot-path SLOs.

Co-locating them means every batch job is a potential outage.

### Cross-service data ownership

- One service owns each table. Other services read via API, not via direct DB access — even if "just for reporting" and "just temporarily".
- Shared database for multiple services is a distributed monolith with distributed-system failure modes and none of the benefits.
- Cross-service joins happen in the application layer, with explicit pagination and timeout budgets, or via a dedicated analytics pipeline with its own copy of the data.

## Anti-patterns specific to this layer

- **NEVER** share a database across services — not "for convenience", not "temporarily", not "just for reporting".
- **NEVER** ship async processing without idempotency and a dedup strategy — at-least-once delivery is the transport default.
- **NEVER** write migrations without a tested rollback path — a migration PR without a verified rollback is not ready.
- **NEVER** claim RTO/RPO targets you have not measured with a game day.
- **NEVER** use microservices to solve a team-communication problem — the coordination cost becomes a distributed-systems cost.
- **NEVER** reuse gRPC/protobuf field numbers when evolving schemas — additive-only, forever.
- **NEVER** treat the cache as the source of truth for correctness-critical data — document the failure mode when the cache is cold or wrong.
- **NEVER** invent hard performance or cost numbers without measurement or explicit inputs.
- **NEVER** colocate hot paths and batch paths on the same connection pool.

## Cross-references

Language-specific knowledge — ownership graphs (C++), virtual threads (Java), prototype pollution (JS), train-serve skew (ML), async runtime choice (Python/TS/Node), GC tuning — lives in the appropriate `backend-pe-{language}` skill.

Security, authentication, and audit-log patterns live in `security-compliance-standards` and `qa-security-engineer`.

## Deliverables contract

Backend architecture delivery includes:

- Requirements summary — functional + non-functional with numbers where provided.
- **RTO/RPO targets** for each critical path, with the replication strategy that physically meets them.
- API contract — endpoints/schema, status codes, error formats, pagination, versioning.
- Data model — schemas, indexes, ownership per table.
- Service boundaries — what each service owns, contracts between them.
- Consistency + messaging posture — per-operation, with idempotency and dedup strategy where async.
- Caching strategy — what, TTL, invalidation, failure mode.
- **Migration plan** — reversible steps, tested rollback, read/write compatibility windows.
- Reliability plan — timeouts, retries, circuit breakers, degradation paths.
- Observability plan — SLIs/SLOs with error budgets, correlation IDs.
- Tests actually run — and what was not run, with reasons.
- Known risks and open questions.
