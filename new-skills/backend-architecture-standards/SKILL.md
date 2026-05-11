---
name: backend-architecture-standards
description: 'Principal-engineer standards for backend services, APIs, data modeling, distributed systems, and reliability. Use when building or reviewing REST/GraphQL/gRPC APIs, database schemas, service boundaries, caching strategies, messaging, observability, or scaling patterns. Triggers on "design an API", "database schema", "service architecture", "distributed system", "caching strategy", "rate limit", "reliability pattern", "migration plan", "message queue", "SLI/SLO", and backend production reviews. Covers API disciplines, data modeling, scaling patterns, reliability patterns, DevOps and infra, data storage, observability, and performance. Loaded by super-mode-core for backend-heavy work.'
---

# Backend Architecture Standards

**Audience:** Backend engineers and architects building or reviewing production services — APIs, data layers, distributed systems, and the operational plumbing around them.

**Goal:** Produce backend designs and code that are correct under failure, maintainable at scale, and operationally honest. Every choice traces to a specific access pattern, failure mode, or growth assumption — never "because it's standard".

## Core Principles

- Design schemas around access patterns and constraints, not the other way around.
- Validate inputs at boundaries; sanitize and log failures.
- Use migrations that are reversible and tested.
- Choose consistency models explicitly — strong vs eventual, per operation.
- Separate hot paths from batch workloads.
- Observability from day one: structured logs with correlation IDs, metrics, traces.
- Define SLIs, SLOs, and error budgets per service.
- Plan for HA and DR with clear RTO/RPO targets.

## Decision Framework

### Monolith vs Microservices

Choose based on team size and domain complexity — not on resume-driven architecture.

- Single team, tight domain: start monolithic, split later along proven seams.
- Multiple teams with independent release cycles, distinct data ownership, or extreme scaling asymmetry: services make sense.
- Never split because "microservices are modern". Split when coordination cost exceeds service cost.

### API Style

- **REST** — use nouns, HTTP verbs, and status codes correctly. Document pagination, filtering, versioning.
- **GraphQL** — schema-first design, depth limits, query complexity limits, persisted queries for untrusted clients.
- **gRPC** — protobuf with versioned backward-compatible evolution (never reuse field numbers, additive-only for shared protos).

Pick one per service boundary and stay consistent.

### Data Store Selection

- Relational when transactions and constraints matter.
- Document when schema is emergent and access is document-shaped.
- Key-value when access is by primary key and scale dominates.
- Normalize for transactions; denormalize for read-heavy paths only when reads dominate and the write amplification is acceptable.
- Avoid cross-service database sharing — each service owns its data.

### Consistency and Messaging

- Choose consistency models explicitly (strong vs eventual) per operation.
- Async processing must be idempotent and retry-safe.
- Document message ordering and deduplication rules.
- Use async messaging only when it simplifies coupling or throughput — not as a default.

### Caching

- Cache-aside where correctness matters.
- Define TTLs and invalidation strategies up front.
- Avoid schema drift between cache and source of truth; document ownership.
- Never treat the cache as the source of truth for correctness-sensitive paths.

### Scaling

- Horizontal scaling for stateless services.
- Vertical scaling for stateful storage.
- Load balancing with health checks and backoff.
- Apply caching tiers and rate limits to protect core systems.

### Reliability Patterns

- Timeouts and retries with exponential backoff.
- Circuit breakers and bulkheads for dependency isolation.
- Graceful degradation when upstreams fail.

## Anti-Patterns

- **NEVER** share a database across services.
- **NEVER** ship async processing without idempotency and a dedup strategy.
- **NEVER** write migrations without a tested rollback path.
- **NEVER** invent hard performance or cost numbers without measurement or explicit inputs.
- **NEVER** return untyped 200s for errors; use correct HTTP status codes.
- **NEVER** use microservices to solve a team-communication problem.
- **NEVER** let the cache become the source of truth for correctness-critical data.
- **NEVER** skip input validation at the boundary.
- **NEVER** reuse gRPC/protobuf field numbers when evolving schemas.
- **NEVER** claim SLOs you are not measuring.

## Standard Workflow

1. **Define requirements.** Functional requirements plus non-functional: throughput, latency, availability targets, data volume, growth, compliance.

2. **Identify critical paths and failure domains.** What is the blast radius if component X fails? What is the recovery path?

3. **Specify the data model.** Schemas designed around actual access patterns. Indexes and constraints with intent. Document table ownership.

4. **Design service boundaries and contracts.** Clear data ownership per service. API style chosen and justified. Version strategy defined.

5. **Pick consistency, caching, and messaging posture.** Explicit per operation. TTLs and invalidation written down. Idempotency guaranteed where async is used.

6. **Plan reliability.** Timeouts, retries with backoff, circuit breakers, bulkheads. Graceful degradation paths for each upstream.

7. **Plan operations.** CI/CD with rollback. Blue-green or canary for risky changes. Immutable deploys. Config separated from build artifacts. Secrets in secret stores. Resource requests and limits in orchestrators.

8. **Plan observability.** SLIs and SLOs per service with error budgets. Structured logs with correlation IDs. Metrics and traces. Alert thresholds tied to SLOs.

9. **Define migration and rollout.** Reversible migrations. Feature flags for risky paths. Rollback criteria documented.

10. **Validate.** Load test or profile before claiming performance. Run integration tests at boundaries. Report what was actually run.

## Deliverables Contract

Backend delivery includes:

- **Requirements summary** — functional plus non-functional with numbers where provided.
- **API contract** — endpoints or schema, status codes, error formats, pagination, filtering, versioning.
- **Data model** — schemas, indexes, constraints, ownership per table.
- **Service boundaries** — what each service owns, contracts between them.
- **Consistency and messaging posture** — per-operation choices with justification.
- **Caching strategy** — what is cached, TTLs, invalidation, failure mode.
- **Reliability plan** — timeouts, retries, circuit breakers, graceful degradation.
- **Operational plan** — deploy strategy, rollback criteria, monitoring, alert thresholds.
- **Observability plan** — SLIs, SLOs, error budgets, correlation ID strategy.
- **Migration plan** — reversible steps, rollback path, feature-flag strategy.
- **Tests actually run** — listed with results. What was not run is listed too.
- **Known risks and open questions.**

## Documentation Expectations

- Public APIs and system boundaries are documented.
- Major architectural decisions captured as ADRs.
- Architecture diagrams maintained for critical flows.
- Runbooks exist for deploy, rollback, and incident response.
- API docs and examples stay in sync with implementation.

## Performance and Cost

- Identify bottlenecks with measurement or profiling — not intuition.
- Separate steady-state costs from peak-load costs.
- Prefer simple scaling over premature optimization.
- State cost assumptions explicitly; avoid hard numbers without inputs.
