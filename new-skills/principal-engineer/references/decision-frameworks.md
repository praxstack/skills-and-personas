# Decision Frameworks

**When to load this file:** Load when running a code review (need severity rubric + code-smell catalog + feedback template) or when arbitrating a technology-selection decision (scoring framework + standards by domain).

---

## Severity rubric

| Label | Definition | Merge action |
|---|---|---|
| Critical | Security vuln, data corruption risk, approved-design violation, production outage vector | MUST fix before merge |
| High | Performance regression in hot path, broken core functionality, missing error handling on external call, untested money/auth edge case | SHOULD fix before merge |
| Medium | Maintainability concern, missing structured logging, weak test naming, minor duplication | Can merge with tracked follow-up ticket |
| Low | Style preference, micro-optimization, bikeshedding territory | Optional; note and move on |

**Calibration rule:** if everything in a review is Critical, you've lost meaning. Reserve Critical for "I would revert this from production". Reserve High for "this breaks the SLO". Everything else is Medium/Low.

---

## Feedback format (required for every blocking comment)

```
## Issue: [specific title]

**Severity:** Critical | High | Medium | Low

**Location:** path/to/file.ts:line-range

**Current code:**
[quote the problematic code]

**Problem:** [WHY this is an issue — security, perf, maintainability, correctness. Not "it's ugly".]

**Suggested fix:**
[concrete replacement code]

**Reasoning:** [WHY this fix is better. What invariant does it preserve or restore?]

**References:** [ADR, docs, previous decision if relevant]
```

"Fix this" without Problem + Suggested fix + Reasoning is rejected as feedback. Train the team by modeling good reviews.

---

## Code-smell catalog (flag these)

**Complexity**
- Function > 50 lines (usually split-candidate).
- Cyclomatic complexity > 10.
- Nesting > 3 levels.
- Parameter list > 4.

**Naming**
- Single-letter vars outside loop counters / well-known math.
- `data`, `temp`, `result`, `info` — too generic.
- Inconsistent with codebase (camelCase vs snake_case mixed).

**Structure**
- God class > 300 lines doing multiple things.
- Feature envy — method mostly operates on another class's data.
- Primitive obsession — passing `string, string, string` instead of a value object.
- Shotgun surgery — one logical change touches many files.

**Logic**
- Duplicated code (3+ copies).
- Dead / unreachable code.
- Speculative generality — abstraction with one implementation.
- Temporary fields used only sometimes.

**Error handling**
- Empty catch.
- `catch (Exception)` / `catch (Throwable)` in business logic.
- Catch and log without rethrow or recovery.
- No error messages, or messages that leak internals.
- Silent failures (`try { … } catch { return null }`).

**Performance**
- N+1 query in a loop.
- SELECT * on wide tables.
- Unbounded result set (no LIMIT, no pagination).
- String concatenation in a loop (use builder).
- Unnecessary serialization round-trips.

**Concurrency**
- Shared mutable state without synchronization.
- Double-checked locking without memory barrier.
- Blocking calls inside async handlers.
- Missing timeouts on IO.

---

## Technology evaluation framework

Score 1-10 on each. Weighted sum; document in an ADR.

| Dimension | What to score | Weight |
|---|---|---|
| Technical fit | Does it solve the actual problem; perf, scale, security characteristics | 3x |
| Team expertise | Current knowledge, ramp time, hiring market | 2x |
| Ecosystem maturity | Community size, library availability, doc quality, bus factor | 2x |
| Operational complexity | Deployment, monitoring, debugging, ops burden | 2x |
| Cost | Licensing, infrastructure, training, migration | 1x |
| Risk | Vendor lock-in, breaking-change history, security track record | 2x |

**Red flags regardless of score:**
- Single-maintainer project for a critical path.
- No public security-incident history / no security contact.
- "New and shiny" with no 1+ year production track record.
- Requires forking to fix bugs (sign of abandonment).

**Green flags:**
- Boring. "Boring" = predictable, well-understood failure modes.
- Used by organizations larger than yours in similar conditions.
- Clear upgrade path and deprecation policy.

---

## Default technology standards

Use these as defaults. Deviation requires an ADR.

**Frontend**
- TypeScript strict mode (mandatory for new code).
- Vite or Next.js for build.
- Vitest / Jest + Testing Library + Playwright.
- Tailwind or CSS Modules.

**Backend**
- TypeScript (Node), Python (FastAPI), Go, or Java/Kotlin (Spring Boot) — choose by team + perf requirements.
- REST as default API style; GraphQL when client needs flexible composition; gRPC for internal microservices with strict latency.
- PostgreSQL as default RDBMS.
- Redis for cache, rate-limiting, ephemeral state.

**Infrastructure**
- Docker for build/run parity (mandatory).
- Kubernetes for microservices at scale; docker-compose for small/monolith/dev.
- Terraform for multi-cloud; CloudFormation/CDK for AWS-only shops.
- GitHub Actions or GitLab CI for pipelines.
- Prometheus + Grafana + Loki/ELK + Jaeger/Tempo for o11y.

**Messaging**
- SQS/RabbitMQ for work queues.
- Kafka for event streaming with replay / ordering requirements.
- WebSockets for bidirectional real-time; Server-Sent Events for server-push.

**Auth**
- OAuth 2.1 + OIDC for user auth.
- JWT for stateless tokens, with short expiry + refresh.
- Session cookies for browser apps (httpOnly, Secure, SameSite).
- mTLS or signed service tokens for service-to-service.

---

## Cross-domain integration rules

API contract = single source of truth. OpenAPI/GraphQL-SDL/protobuf is the contract. Hand-written API docs are not.

- Shared types generated from schema (not maintained by hand on both sides).
- Error response format is consistent across services: `{ code, message, details[], requestId, timestamp }`.
- Versioning strategy agreed before first consumer ships (URL `/v1`, header, or content-negotiation).
- Breaking changes require major-version bump + dual-serve period.
- CORS configured explicitly per-origin, never `*` for authenticated endpoints.
- Timestamps in ISO 8601 with timezone, money in minor units (integer cents), IDs as strings (avoid JS-number precision loss).

---

## Performance budgets (reject designs that don't target these)

- Frontend: LCP < 2.5s, INP < 200ms, CLS < 0.1.
- API: p50 < 100ms, p99 < 500ms for CRUD; higher only with justification.
- DB: simple query < 100ms, complex < 1s, else needs index/rewrite/cache.

## Availability targets

- Critical (login, checkout, payments): 99.9% = ~43 min/month allowed.
- Standard: 99% = ~7 hours/month.
- Internal tools: 95% or best-effort documented.

Budget must match effort: 99.99% is not free — requires multi-region, chaos testing, game days, on-call.
