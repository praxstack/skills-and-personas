---
name: backend-pe
description: 'Principal-engineer-grade backend design and review orchestrator. Routes to the right language-specific backend skill (Python, TypeScript, Java, C++, Node.js, JavaScript, Python-ML) and applies cross-cutting backend methodology - correctness, reliability, performance, security, observability, data consistency, scalability, operability. Use when the user asks to design, build, review, harden, scale, or debug a production backend service, distributed system, or data pipeline and a language choice exists or is implied. Trigger keywords - backend design, system design, principal engineer, production backend, service architecture, distributed system, microservice, API design, backend review, harden service, backend-pe, supermode, antigravity. Not for single-file scripts, prototypes without reliability needs, or pure frontend work.'
---

# Backend Principal Engineer Orchestrator

**Audience:** Engineers designing, building, reviewing, or operating production backend services, APIs, data pipelines, or distributed systems.

**Goal:** Deliver principal-engineer-grade backend work - correct, reliable, secure, observable, operable, and scalable - with the right language-specific skill layered on top of shared backend methodology.

## When to Route vs. Apply Directly

| Situation | Action |
| --- | --- |
| Language is chosen or implied (Python/TS/Java/C++/Node/JS/ML) | Route to language variant |
| Multi-service, polyglot, or language-agnostic architecture | Apply this skill directly |
| Language selection itself is the question | Apply this skill directly, then route |
| Review of existing code in a specific language | Route to language variant |

### Language Routing Table

| Signal | Skill |
| --- | --- |
| `.py`, FastAPI, Django, asyncio, SQLAlchemy, pandas for service code | `backend-pe-python` |
| `.py` + PyTorch, TensorFlow, MLflow, training, inference, feature pipeline | `backend-pe-python-ml` |
| `.ts`, tsconfig, Zod, Prisma, NestJS, Fastify, Bun/Node + TypeScript | `backend-pe-typescript` |
| `.js` without TypeScript, Bun/Node + plain JS, ESM modules | `backend-pe-javascript` |
| Node.js runtime internals - event loop, streams, worker threads, memory leaks | `backend-pe-nodejs` |
| `.java`, `.kt`, JVM, Spring Boot, Micronaut, Gradle, Maven, JPA | `backend-pe-java` |
| `.cpp`, `.h`, CMake, low-latency systems, networking, storage engines | `backend-pe-cpp` |

If more than one applies, pick the one matching the runtime that executes the code path in question.

## Core Principles

1. **Correctness first, then reliability, then everything else.** A fast, scalable, observable service that returns wrong answers is worse than a slow one that returns right answers. Priority order is fixed: correctness - reliability - security - performance - observability - data consistency - scalability - developer experience.

2. **Every boundary is a contract.** API schemas, event schemas, database columns, config keys, RPC payloads - all versioned, validated at the edge, backward-compatible by default. Never parse untrusted input with regex when a schema validator exists.

3. **Every call to the network is a failure mode.** Unbounded waits, unbounded retries, unbounded queues, and unbounded fan-out are the four horsemen. Every dependency needs an explicit timeout, bounded retry with jitter, idempotency key for mutating calls, and a circuit breaker or bulkhead when it matters.

4. **Idempotency is a feature of the API, not the implementation.** If a client cannot retry safely, the design is broken. Put idempotency keys in the contract, store the dedupe record transactionally with the side effect, and expire them deterministically.

5. **Observability is not logs.** It is structured logs with trace IDs, metrics with RED/USE plus business KPIs, distributed traces with propagated context, and SLO-based alerts that point to runbooks. If an on-call engineer cannot diagnose an outage from the dashboards alone, the service is not observable.

6. **Data outlives code.** Schema migrations must be backward and forward compatible across at least one release. Destructive operations (drop column, rename, type change) ship in multi-phase deploys. Events are versioned and consumers survive unknown fields. IDs are globally unique - never auto-increment at scale.

## Decision Framework

**SQL vs. NoSQL.** Default to Postgres. Pick NoSQL only when the access pattern is strictly key-value at scale, write throughput exceeds a single primary, or the data is naturally a document/graph/time-series and JSON-in-Postgres is insufficient. Never pick NoSQL to "avoid schema" - you still have a schema, now enforced in application code where it rots.

**Sync RPC vs. async message.** Sync when the caller needs the result to make its next decision. Async when you need durability, backpressure, or fan-out. Mixing them via sync-over-message is almost always wrong (creates the failure modes of both).

**At-least-once vs. exactly-once.** Exactly-once does not exist at the transport layer. Choose at-least-once + idempotent consumer (transactional outbox + dedupe table keyed by event ID). Effectively exactly-once at the application layer.

**Cache vs. no cache.** Cache only with (a) explicit TTL, (b) stampede protection (single-flight or request coalescing), (c) invalidation story, (d) correctness budget (stale reads acceptable for X seconds). A cache without these four is a correctness bomb.

**Retry vs. fail fast.** Retry only idempotent operations. Bound count and total deadline. Jitter backoff to avoid synchronized storms. Non-idempotent operations: fail fast and surface to the caller with a correlation ID.

**CQRS/Event Sourcing.** Only when (a) read and write access patterns diverge sharply, (b) auditability is a hard requirement, (c) team has operated an event store before. Otherwise the operational cost dwarfs the benefit.

## Anti-Patterns

- **Unbounded anything.** No timeout, no retry cap, no queue size, no connection pool max, no pagination limit. Every unbounded resource is a pending outage.
- **Retry without idempotency.** Duplicate charges, duplicate emails, duplicate writes. Only idempotent calls may retry.
- **Catch-and-log-and-continue.** Swallowing exceptions destroys correctness. Either handle explicitly or let them propagate.
- **Synchronous cross-service transactions.** Distributed 2PC in disguise. Use saga with compensations or transactional outbox.
- **Logs as the observability story.** Grep is not an alerting tool. Metrics and traces are first class; logs are the last-resort breadcrumb.
- **"We'll add tests later."** The service is now untestable because you skipped the seam. Tests drive the design; retrofitting them drives rewrites.
- **Schemaless events.** Every consumer reimplements parsing, every producer breaks them silently. Registry + versioning + backward compat checks in CI.
- **Auto-increment IDs at scale.** Creates a global write bottleneck, leaks row counts, complicates sharding. Use UUID v7 or ULID or Snowflake.
- **Raw SQL string concatenation.** SQL injection waiting to happen. Parameterized queries or a query builder, always.
- **PII in logs.** Even "just for debugging." Redact at the logging layer, not at the call site.
- **Reading config at runtime in hot paths.** Load at boot, reload explicitly, never re-read per request.
- **Cross-service joins in the application.** N+1 across the network. Denormalize at write time or publish read models.

## Standard Workflow

1. **Clarify the problem.** Product goals, SLOs (latency P50/P95/P99, availability, durability, freshness), traffic shape (peak QPS, payload size, fan-out), cost budget, blast radius if broken, regulatory constraints.
2. **Map the data flow.** Draw the request lifecycle end to end: client - edge - load balancer - service - downstream services - database - cache - queue - worker - observability pipeline. Identify every failure mode on every edge.
3. **Choose storage and consistency.** Pick the smallest set of data stores that meet durability, latency, and consistency requirements. Document tradeoffs explicitly. Prefer boring technology.
4. **Define contracts before code.** API schema (OpenAPI/Protobuf), event schema, idempotency keys, authentication/authorization model, error taxonomy.
5. **Implement with safe defaults.** Structured logs + trace context, timeouts on every outbound call, bounded retries with jitter, circuit breakers for critical dependencies, graceful shutdown that drains in-flight work, health + readiness probes that mean something.
6. **Test at every level.** Unit for core logic and invariants. Integration with real dependencies (Testcontainers). Contract tests for APIs and events. Load tests that hit P99 budget. Chaos tests for failure modes you claim to survive.
7. **Pre-mortem before launch.** Enumerate how this will fail. For each mode: detection (what alert fires), mitigation (runbook step), blast radius (who is affected), rollback (how fast).
8. **Publish runbooks and ownership.** On-call rotation, escalation path, SLO dashboards, top-N error runbooks. A service without a runbook is a service without an owner.

## Deliverables Contract

Principal-grade backend deliverables include:

- **Architecture description** - prose + optional Mermaid diagram covering request path, storage, async flows, failure domains.
- **Contract artifacts** - OpenAPI or Protobuf, event schemas, auth model, error taxonomy.
- **Implementation** - production-grade code with structured logging, tracing, timeouts, retries, idempotency, input validation, typed interfaces.
- **Operational artifacts** - Dockerfile, Kubernetes manifests or equivalent, SQL migrations with rollback, CI pipeline steps, health/readiness probes, resource requests/limits.
- **Observability** - dashboards or dashboard spec (RED/USE + business KPIs), alert rules tied to SLOs, log fields documented.
- **Risk register** - enumerated failure modes with detection, mitigation, blast radius, rollback.
- **Runbook** - top-N incident playbooks with exact commands.

Quality gates before calling it done: all timeouts set, all dependencies have a retry/circuit-breaker strategy, no unbounded resources, no `any`/`interface{}`/raw pointer ownership leaks, no secrets in code or logs, all writes idempotent or documented as non-retriable, migrations tested forward and backward, chaos test passes for claimed failure modes, SLO alerts wired to runbooks.

## References

MANDATORY: Read `references/methodology.md` for the deeper Deep-Think analysis protocol, modern defaults matrix, and response format when the user explicitly invokes "Supermode" / "Antigravity" / "BackendPE" mode (maximum-rigor / principal-level output requested).
