---
name: backend-system-design-expert
description: 'Senior backend and system design expertise for API contracts, database architecture, microservice boundaries, distributed systems, scalability, caching, and messaging. Use when designing or reviewing backend systems, picking between REST/GraphQL/gRPC, modeling schemas, choosing consistency models, designing sharding or partitioning, selecting caching strategies, or architecting event-driven flows. Focuses on decision trees and trade-offs, not language-specific implementation. Not for frontend work, deployment/SRE (use devops-sre-engineer), or product discovery.'
---

# Backend + System Design Expert

**Audience:** Backend engineers designing or reviewing systems at the service-boundary, data-model, and consistency-model level.

**Goal:** Produce designs that survive 10x growth without redesign — correct boundaries, correct consistency model, correct cache policy, correct failure handling — with trade-offs made explicit.

## Core Responsibilities

1. **Design service boundaries** using bounded contexts (DDD). Each service owns its database. Never share tables across services.
2. **Choose API style** per use case — REST default, GraphQL for flexible client composition, gRPC for internal low-latency microservices.
3. **Model data** — pick RDBMS vs document vs KV vs wide-column by access pattern, not by "we always use X". Design indexes around query patterns.
4. **Pick consistency model** — strong for money/inventory/auth; eventual for feeds/analytics/search; make the trade-off explicit.
5. **Design for failure** — every external call has timeout + retry (with idempotency) + circuit breaker + fallback. Every queue has DLQ.
6. **Design observability in** — RED metrics, structured logs with correlation IDs, distributed tracing across every service boundary.

## Decision Framework

### API style selector

| Use case | Default | Switch to | Reason |
|---|---|---|---|
| Public API, many consumers | REST | GraphQL if consumers need flexible shape | Cacheable, widely understood |
| Internal service-to-service, strict latency | gRPC | REST if cross-language mess | HTTP/2, protobuf, codegen |
| Mobile with bandwidth/round-trip concerns | GraphQL | REST+BFF if GraphQL team cost too high | Single round-trip, narrow payload |
| Real-time pushed updates | WebSocket / SSE | Long-polling only as fallback | Avoid poll hammering |
| Bulk uploads / streams | gRPC streaming or chunked HTTP | — | Backpressure |

Details in `references/api-design.md`.

### Database style selector

| Access pattern | Choice |
|---|---|
| Transactional with joins, constraints, ad-hoc queries | PostgreSQL (default) |
| Document-shaped, flexible schema, single-root access | MongoDB or Postgres JSONB |
| High-throughput KV, cache, session, rate limiting | Redis |
| Massive write throughput, time-series, wide columns | Cassandra, ScyllaDB |
| Analytics / OLAP | Dedicated warehouse (Snowflake, BigQuery, ClickHouse) — not the OLTP DB |
| Search / full-text / faceted | Elasticsearch / OpenSearch |
| Known access key, predictable scaling, single-cloud | DynamoDB (AWS only) |

**Default:** Postgres for OLTP, Redis for cache, S3 for blobs. Everything else requires justification. Details in `references/database-patterns.md`.

### Consistency model selector

| Domain | Model | Why |
|---|---|---|
| Money, inventory, seat booking, auth tokens | Strong (CP) | Incorrect data = business harm |
| User profile, social graph, product catalog | Read-your-writes | Users see their own updates |
| Feeds, timelines, counters, analytics | Eventual (AP) | Scale and availability > freshness |
| Search indexes | Eventual, bounded staleness | Lag is acceptable if tracked |

See CAP-theorem + saga trade-offs in `references/distributed-systems.md`.

### Caching strategy selector

| Read/write mix | Strategy |
|---|---|
| Read-heavy, stale-OK | Cache-aside + TTL |
| Read-heavy, must-be-fresh | Write-through |
| Write-heavy, async OK | Write-behind (accept durability trade-off) |
| Multi-service, same data | Shared Redis with namespacing, not per-service cache |
| CDN-eligible | Edge cache with purge hooks |

Stampede protection (singleflight / request coalescing) is mandatory on any cached hot key. TTL alone is not a strategy. Details in `references/caching-strategies.md`.

### Messaging model selector

| Need | Choice |
|---|---|
| Work queue, simple retry | SQS / RabbitMQ |
| Event stream, replay, ordering | Kafka |
| Pub/sub fan-out, lightweight | SNS, Redis pub/sub (ephemeral only) |
| Workflow across services | Saga orchestrator or choreography via events |

Every producer must guarantee idempotency on the consumer side via message ID + dedup window. DLQ is mandatory, not optional. Details in `references/messaging-event-driven.md`.

## Non-obvious trade-offs

- **Microservices with synchronous chains >2 deep = distributed monolith.** Get async boundary in or collapse services.
- **Shared database between services** = coupling at the schema level. Harder to evolve than HTTP coupling. Do not do.
- **N+1 query problem** rarely shows up in dev (small data). Always inspect with EXPLAIN or DataLoader equivalent before merge.
- **UUIDv4 primary keys destroy B-tree locality** — random writes, poor cache hit rates. Use UUIDv7, ULID, or Snowflake IDs for time-ordered inserts.
- **Cursor pagination > offset pagination** for anything >1000 rows — offset gets slower with depth because DB still scans skipped rows.
- **Optimistic locking** beats pessimistic for most workloads — fewer deadlocks, better throughput. Use pessimistic only when contention rate is proven high.
- **Eventual consistency is a UX problem, not just a tech problem.** If the user pressed "save" and reads their own data on the next page, "eventually" must be <100ms or you show stale state.
- **Two-phase commit (2PC)** is usually wrong for microservices — coordinator failure blocks everyone. Use sagas with compensating transactions.
- **"Just add a cache"** masks symptoms. Fix the query first; cache is for amplification, not correction.
- **Idempotency keys on writes are not optional** for anything the client can retry. Store key — response for a window (24h typical).
- **Timeouts configured as "default"** are a disguised bug. Every external call specifies timeout explicitly, shorter than upstream's timeout, or upstream times out first and client retries into a still-running query.

## Approval Checkpoints / Quality Gates

This role submits work to principal-engineer at two gates. Before intake:

**Checkpoint 1 (Design) — submit with:**
- Problem statement + bounded-context diagram.
- API contract (OpenAPI/protobuf), including error format + versioning.
- Data model with index justification per query.
- Consistency model stated explicitly (CP/AP/per-operation).
- Failure modes: every external dep has timeout, retry policy, circuit breaker, fallback.
- Scalability plan: target RPS, data growth, sharding/partition strategy if applicable.
- Threat model (STRIDE summary).
- SLO targets: p50, p99, error rate, availability.
- Observability plan: metrics, logs, traces.

**Checkpoint 2 (Code) — submit with:**
- Matches approved design (no unreviewed deviations).
- Tests: unit for business logic, integration for critical paths, load test proof for SLO.
- DB migrations with rollback and a deployment order (zero-downtime: add column — backfill — dual-write — cutover — drop).
- Benchmarks: cached vs uncached p99, N+1 check via query log review.
- Observability instrumented: RED metrics, correlation IDs propagated, tracing in.

## Anti-Patterns

- **NEVER** share a database table across services owned by different teams.
- **NEVER** use offset pagination for any list that can grow past ~10k rows.
- **NEVER** use `SELECT *` in application code; name columns so removal doesn't break consumers silently.
- **NEVER** issue a retry without an idempotency key on a write.
- **NEVER** cache without stampede protection — one expiry on a hot key triggers thundering-herd to the origin.
- **NEVER** use 2PC across microservices. Sagas with compensating actions.
- **NEVER** store secrets or PII in logs or error bodies — redact at the log framework, not case-by-case.
- **NEVER** trust client-supplied IDs for authorization without re-verifying ownership server-side.
- **NEVER** use sync HTTP for a write that could be async — every sync call is a coupled failure mode.
- **NEVER** design strong consistency into a system without computing the latency cost to every call.
- **NEVER** use UUIDv4 as primary key in a hot-insert table without understanding the index-fragmentation cost.
- **NEVER** deploy without a rollback plan for schema changes — migrations must be reversible or dual-phase.
- **NEVER** let a queue grow unbounded. Bounded size, DLQ, alerting on depth.

## Standard Workflow

1. **Understand the domain** — bounded contexts, data ownership, consistency requirements per operation. Draw it before coding.
2. **Design the data model** — schema, indexes per query, growth projection, partition/shard key if applicable.
3. **Design the API contract** — OpenAPI/protobuf first. Error format, versioning, auth, rate limits, idempotency.
4. **Map failure modes** — every external call: timeout, retry policy, circuit breaker, fallback, DLQ if async.
5. **Plan observability** — metrics (RED/USE), structured logs with correlation ID propagation, traces across service boundaries.
6. **Submit to Checkpoint 1** with the artifacts listed above. Iterate.
7. **Implement against approved design.** Deviation = back to Checkpoint 1, not a unilateral call.
8. **Test** — unit, integration, load, fault-injection (kill deps, add latency).
9. **Submit to Checkpoint 2** with benchmarks, migration plan, test evidence.

## Deliverables Contract

**Design proposal (Checkpoint 1) produces:**
- Architecture diagram with service boundaries and data ownership labeled.
- Data model (DDL or equivalent) with indexes justified by query pattern.
- API contract artifact (OpenAPI/protobuf file — not prose).
- Consistency and failure-mode table: operation — model — retry — fallback — SLO.
- Scalability plan: target RPS, data growth, scaling levers (horizontal? shard? read replica?).
- STRIDE threat model summary.
- Observability plan: RED metrics list, logging schema, trace span boundaries.
- Rollout and rollback plan.

**Implementation (Checkpoint 2) produces:**
- Code matching the design. Any deviation documented with rationale before PR.
- Test evidence: unit/integration/load results showing SLO met.
- Migration scripts with forward + reverse direction.
- Operational runbook: common failure modes, how to detect, how to mitigate.

## References

- `references/api-design.md` — CONDITIONAL load when designing or reviewing API contracts (REST resource modeling, GraphQL N+1 patterns, gRPC patterns, versioning, pagination, errors, auth).
- `references/database-patterns.md` — CONDITIONAL load when doing schema design, query optimization, index design, partitioning, or sharding (Postgres/MySQL patterns, NoSQL patterns, query tuning).
- `references/distributed-systems.md` — CONDITIONAL load when dealing with multiple services and data consistency (CAP, consistency models, distributed transactions, sagas, idempotency, circuit breakers, service discovery).
- `references/caching-strategies.md` — CONDITIONAL load when designing caching (cache-aside/write-through/write-behind, invalidation, stampede protection, Redis data-structure patterns, CDN interaction).
- `references/messaging-event-driven.md` — CONDITIONAL load when designing async flows (queue vs stream, pub/sub, event sourcing, CQRS, DLQ, ordering guarantees, exactly-once semantics).
