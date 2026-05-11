---
name: backend-pe-java
description: 'Principal-engineer-grade Java backend design, implementation, and review. Covers JDK 21 LTS, virtual threads, Spring Boot 3 / Micronaut / Quarkus, reactive vs. imperative, JVM tuning, concurrency primitives, and Java-specific failure modes (connection pool starvation, GC pauses, blocking in reactive, boxing in hot paths). Use when designing, building, reviewing, refactoring, hardening, profiling, or debugging Java or Kotlin backend services. Trigger keywords - Java backend, JVM, Spring Boot, Micronaut, Quarkus, virtual threads, Project Loom, JPA, Hibernate, Kafka Java, JVM tuning, GC tuning, HikariCP, G1 ZGC, Resilience4j. Not for Android work.'
---

# Java Backend Principal Engineer

**Audience:** Engineers designing, building, reviewing, or hardening Java (or Kotlin) backend services on modern JVMs.

**Goal:** Principal-engineer-grade Java - durable architecture, predictable latency under load, correct concurrency, and production-grade observability.

## Priority Model

Correctness - Reliability - Security - Performance - Observability - Data consistency - Scalability - Developer experience. In that order.

## Core Principles

1. **Virtual threads changed the calculus - imperative is back.** With JDK 21 virtual threads, the reactive cost/benefit inverted for most services. Plain imperative code with `Thread.ofVirtual()` or structured concurrency handles tens of thousands of concurrent I/O operations without the Mono/Flux complexity. Reactive (WebFlux, Reactor) remains correct for backpressure-sensitive streaming or legacy codebases - not a default.

2. **Every pool has a queue, and every queue has a failure mode.** HikariCP size, executor thread count, Kafka consumer concurrency, Tomcat max-threads - each is a bounded queue that, when full, decides who waits and who gets rejected. Pool starvation is the single most common production outage. Size from first principles (Little's Law) and document the math.

3. **Don't block inside reactive code.** A single `Thread.sleep`, synchronous JDBC call, or `.block()` inside a Reactor chain stalls the event-loop thread and kills every in-flight request on that thread. Run blocking work on `Schedulers.boundedElastic()` or rewrite.

4. **GC is a budget, not a concern.** On JDK 21+, ZGC or Generational ZGC handles most latency-sensitive workloads with sub-ms pauses. G1 is fine for throughput. Don't tune GC blindly - measure with JFR, look at allocation rate and pause distribution, then adjust. Pre-allocation in hot paths matters when allocation rate > 1 GB/s.

5. **Jackson and reflection are hot-path hazards.** Avoid reflection-based serialization in inner loops. Prefer explicit DTOs, records, or a compiled codec (Jackson's afterburner, Protobuf-generated, Avro). Streaming APIs (`JsonGenerator`) for large payloads. Never parse user input with `ObjectMapper.readValue(String.class, Map.class)` - build real types.

6. **Records and sealed types model domains correctly.** Records for immutable value objects. Sealed interfaces for closed hierarchies and exhaustive `switch` pattern matching. Pattern matching replaces instanceof chains. Banish mutable DTOs in new code.

## Decision Framework

**Spring Boot vs. Micronaut vs. Quarkus.**
- Spring Boot 3 - default ecosystem, largest talent pool, mature DI, accepts higher startup and memory cost.
- Micronaut - compile-time DI, fast startup, lower memory, strong AOT / GraalVM story.
- Quarkus - same as Micronaut goals, Jakarta EE heritage, excellent Kubernetes-native story.
- Pick based on team skill and startup/memory requirements. For serverless and fast-scaling, Micronaut or Quarkus. For teams deep in Spring, Spring Boot 3.

**Virtual threads vs. reactive.** Imperative + virtual threads for most request/response services on JDK 21+. Reactive when you need explicit backpressure, streaming processing, or the codebase is already WebFlux. Don't mix in the same service unless the boundary is crisp.

**JPA / Hibernate vs. jOOQ vs. JDBC.**
- JPA/Hibernate - OLTP CRUD, relationship-heavy models, accept the N+1 risk and manage it with fetch planning.
- jOOQ - query-heavy services, complex joins, reporting paths, type-safe SQL.
- JDBC / JdbcClient (Spring 6.1+) - simple queries, maximum control, no ORM cost.
- Don't combine all three in one module.

**Kotlin vs. Java.** Kotlin where the team wants concise syntax, coroutines, null safety, DSL building. Java where the team wants one language, no compile-step surprises, and the full JDK feature set lands first. Mixed codebases work; pick primary language per module.

**Gradle vs. Maven.** Gradle Kotlin DSL for flexible builds, convention plugins, fast incremental compile. Maven for strict conventions and reproducibility. Don't use Groovy Gradle in new projects.

## Anti-Patterns

- **Unbounded `Executors.newCachedThreadPool()`.** Thread explosion under load. Use `Executors.newVirtualThreadPerTaskExecutor()` or a bounded `ThreadPoolExecutor` with explicit rejection policy.
- **`.block()` in reactive code.** Deadlocks or event-loop starvation.
- **Catching `Exception` and swallowing.** Named exceptions only; if you can't handle it, let it propagate.
- **`synchronized` across I/O.** Holds the monitor during a network call - all callers queue.
- **`ConcurrentHashMap` used as a cache without eviction.** Unbounded growth, OOM. Use Caffeine.
- **`@Transactional` on a read path spanning external calls.** Holds a DB connection during network I/O - pool starvation. Keep transactions short and local.
- **Lombok's `@Data` on entities.** Mutable hashCode/equals on a DB row. Use `@Value` (immutable) or records.
- **`String.format` in hot logging paths.** Allocation and formatting cost even when log level is disabled. Use SLF4J parameterized `logger.info("x={}", x)`.
- **Checked exceptions tunneled through streams.** `Stream.map` can't throw checked. Either use unchecked or handle per element.
- **`new Date()` / `Calendar`.** Legacy, mutable, timezone traps. Use `java.time.Instant`, `ZonedDateTime`, `LocalDate`.
- **`SimpleDateFormat` shared across threads.** Not thread-safe. Use `DateTimeFormatter`.
- **Field injection (`@Autowired` on fields).** Breaks testability and immutability. Constructor injection always.
- **Catching `OutOfMemoryError`.** JVM is in an undefined state. Let it die and restart.
- **Infinite `CompletableFuture` chains without timeouts.** Every `thenCompose` should have a timeout somewhere in the pipeline.

## Standard Workflow

1. **Clarify SLOs and budgets** - P50/P95/P99 latency, error budget, QPS, payload sizes, cold-start budget.
2. **Choose concurrency model** - imperative + virtual threads (default JDK 21+) vs. reactive (existing WebFlux codebases or explicit backpressure needs).
3. **Map dependencies and failure modes** - what DBs, queues, external APIs; their SLAs; their failure semantics.
4. **Define contracts** - OpenAPI or Protobuf, Jakarta Bean Validation on DTOs, explicit error taxonomy with RFC 7807 `application/problem+json`.
5. **Size pools from Little's Law** - DB connection pool = (avg concurrent queries in flight). Executor size derives from CPU count and I/O ratio. Document the calculation.
6. **Wire resilience** - Resilience4j for timeouts, retries, circuit breakers, bulkheads, rate limits. Retries only on idempotent operations; add jitter.
7. **Observability** - Micrometer metrics (RED + USE + business), OpenTelemetry tracing, SLF4J + logback with JSON encoder, trace+span IDs in MDC.
8. **Test** - JUnit 5, AssertJ, Testcontainers for DB/Kafka/Redis, Mockito for unit boundaries, Gatling or k6 for load, Pact for contract.
9. **Graceful shutdown** - configure drain period (Spring Boot `lifecycle.timeout-per-shutdown-phase`), complete in-flight requests, deregister from discovery before killing the process.

## Default Stack (2026 baseline)

- JDK 21 LTS (or 25 LTS when GA); latest patch.
- Framework: Spring Boot 3.3+ (default), Micronaut 4+ (fast startup), Quarkus 3+ (K8s-native).
- Build: Gradle 8+ Kotlin DSL with BOM-managed versions; toolchain auto-provisioning.
- HTTP server: embedded Tomcat with virtual threads (`spring.threads.virtual.enabled=true`) for Spring; Netty for reactive.
- Serialization: Jackson with explicit schemas; avoid reflection-only mappings in hot paths.
- Validation: Jakarta Bean Validation (Hibernate Validator).
- Persistence: Spring Data JPA + Hibernate for OLTP; jOOQ for query-heavy; Flyway or Liquibase for migrations.
- Connection pool: HikariCP; sized from Little's Law.
- Messaging: Kafka via `spring-kafka` or native producer with idempotent + `acks=all`; transactional outbox.
- Resilience: Resilience4j.
- Caching: Caffeine (local), Redis (distributed via Lettuce).
- Observability: Micrometer + OpenTelemetry + logback JSON; Grafana/Prometheus/Tempo.
- Security: Spring Security 6 with OAuth2 Resource Server; secrets via Vault or cloud KMS.
- Testing: JUnit 5, AssertJ, Testcontainers, Mockito, Awaitility, Gatling.

## Deliverables Contract

- JDK 21+ codebase with records, sealed types, pattern matching where appropriate.
- `build.gradle.kts` with pinned versions and reproducible build config.
- Multi-stage Dockerfile (JLink or GraalVM native where warranted), non-root, `jcmd`-friendly JVM flags.
- Flyway/Liquibase migrations with rollback scripts.
- OpenAPI spec generated from springdoc or similar.
- Resilience4j policies on every outbound integration.
- HikariCP sized and documented.
- Observability: Micrometer + OpenTelemetry + structured JSON logs with trace IDs.
- Graceful shutdown configured.
- Tests: unit, integration (Testcontainers), contract, load.
- Runbook for top-N failure modes with JVM + pool + GC dashboards.

Quality gates: no unbounded executors, no `.block()` in reactive paths, no synchronized blocks across I/O, no field injection, no `@Transactional` spanning external calls, no reflection in hot paths without JIT verification, connection pool sized from Little's Law, GC strategy chosen and measured, all outbound calls have timeout + retry policy, all writes idempotent or marked non-retriable.
