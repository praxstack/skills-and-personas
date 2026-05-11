---
name: backend-pe-typescript
description: 'Principal-engineer-grade TypeScript backend design, implementation, and review. Covers strict tsconfig, Zod schemas, Fastify/NestJS/tRPC/Hono, Prisma/Drizzle, ESM, Bun/Node 20 LTS runtimes, and TypeScript-specific failure modes (any leakage, narrow-type erosion, module resolution). Use when designing, building, reviewing, refactoring, hardening, or debugging TypeScript services and APIs. Trigger keywords - TypeScript backend, tsconfig strict, Zod, Fastify, NestJS, tRPC, Hono, Prisma, Drizzle, Bun backend, Node TypeScript, TS review, TS performance, type safety review. Not for TS frontend work, pure Node runtime internals (use backend-pe-nodejs), or plain JavaScript (use backend-pe-javascript).'
---

# TypeScript Backend Principal Engineer

**Audience:** Engineers designing, building, reviewing, or hardening TypeScript backend services on Bun or Node 20+ LTS.

**Goal:** Principal-engineer-grade TypeScript - type safety that catches bugs at compile time, runtime validation at every boundary, and production hardening by default.

## Priority Model

Correctness - Reliability - Security - Performance - Observability - Data consistency - Scalability - Developer experience. In that order.

## Core Principles

1. **Types you can trust end at the network edge - Zod/Valibot begins there.** TypeScript types are erased at runtime. Any data crossing a boundary (HTTP request, message, env var, DB row, external API response) is `unknown` until parsed by a schema validator. Never cast untrusted JSON to a type. Zod schemas are the contract; types flow from `z.infer`.

2. **Strict mode is non-negotiable.** `"strict": true`, `"noUncheckedIndexedAccess": true`, `"exactOptionalPropertyTypes": true`, `"noImplicitOverride": true`, `"noFallthroughCasesInSwitch": true`. `any` leaks erase the value of every other type. Ban it with ESLint `@typescript-eslint/no-explicit-any`. Use `unknown` + narrowing instead.

3. **Discriminated unions over optional chaining.** Model state as `type State = {kind: 'loading'} | {kind: 'ok', data: T} | {kind: 'err', error: E}`. Exhaustive switches with `assertNever` catch new cases at compile time. Optional-chain chains (`a?.b?.c?.d`) are a smell - they hide missing state handling.

4. **Async errors don't propagate like sync errors.** Unhandled promise rejections crash Node by default (good), but `async` functions that throw inside a non-awaited call silently swallow. Always `await` or `.catch`. Never fire-and-forget a promise that touches a DB or external service.

5. **ESM only. CommonJS is legacy.** `"type": "module"`, `.ts` source with explicit `.js` extensions in imports (per TS 5+ NodeNext). Dual packages are a tax nobody should pay. Runtime: Bun or Node 20+ LTS, never older.

6. **One source of truth, generated types downstream.** OpenAPI/GraphQL schema/Protobuf generates client + server types. Drizzle schema generates DB types. Zod schema generates API types. Stop hand-writing parallel type hierarchies that drift.

## Decision Framework

**Fastify vs. NestJS vs. tRPC vs. Hono.**
- Fastify - high-throughput REST with minimal magic, explicit schema-driven serialization.
- NestJS - large teams, DI-heavy services, explicit modularity, microservices with MS/transport abstractions.
- tRPC - internal APIs where client and server share a monorepo; end-to-end type safety without codegen.
- Hono - edge runtimes (Cloudflare Workers, Bun, Deno), lightweight, standards-based.
- Express - legacy only. Don't start new services on it.

**Prisma vs. Drizzle vs. Kysely vs. raw SQL.**
- Drizzle - type-safe SQL, minimal overhead, best for SQL-literate teams, supports edge.
- Prisma - productive ORM, strong migrations, overhead in query engine, large install footprint.
- Kysely - query builder only, no migrations or schema inference, composable.
- Raw SQL via `pg` / `postgres.js` - when you need exact control and can own the types.

**Bun vs. Node 20+ LTS.** Bun for new services where speed matters and your dependency tree is Bun-compatible. Node 20+ for mature ecosystems and anything touching native modules that haven't verified Bun support. Never target Node < 20 for new code.

**Zod vs. Valibot vs. Typia.** Zod - default, largest ecosystem, TS-first. Valibot - tree-shakeable, smaller bundle. Typia - compile-time validation via transformer, fastest runtime but requires build-step config.

**Effect vs. neverthrow vs. try/catch.** Plain try/catch + typed errors is usually enough. `neverthrow` for Result types without the ecosystem cost. Effect when the team commits to it fully and treats it as the runtime.

## Anti-Patterns

- **`any` anywhere in a public signature.** Defeats the compiler. `unknown` + Zod parse or a precise union.
- **Type assertion (`as Foo`) on network data.** No runtime check. Use `schema.parse()`.
- **`@ts-ignore` without a comment.** Hides real bugs. Use `@ts-expect-error` with explanation, and make it fail when the error goes away.
- **Implicit `any` from missing return types on exported functions.** Always annotate public signatures.
- **`Object`, `Function`, `{}` as types.** Meaningless. Use `object`, `(args) => ret`, `Record<string, unknown>`.
- **Throwing strings or plain objects.** Errors must extend `Error` with a typed `cause` chain.
- **`JSON.parse` without validation.** Parse then validate with a schema.
- **`setTimeout` / `setInterval` without `unref()` in shutdown logic.** Keeps the process alive.
- **Awaiting inside a `for` loop when the iterations are independent.** Use `Promise.all` with bounded concurrency via `p-limit`.
- **`Promise.all` with unbounded input.** Thundering herd on downstream services. `pMap(items, fn, {concurrency: N})`.
- **Unhandled rejection handlers that swallow.** `process.on('unhandledRejection', ...)` should log and exit, not absorb.
- **Mutating request objects across middleware.** Use explicit context objects. Express's mutable `req` is a footgun.
- **Env vars read inline (`process.env.FOO`).** Parse once into typed `env` object with Zod at startup.
- **`Date.now()` for deadlines across async boundaries.** Use `AbortSignal.timeout` or `AbortController`.

## Standard Workflow

1. **Clarify SLOs and traffic shape** - P50/P95/P99 latency, QPS, payload sizes, runtime target (Node/Bun/edge).
2. **Choose framework and ORM** - see decision tables above. Document tradeoffs.
3. **Define schemas first** - Zod (or OpenAPI/Protobuf) for external contracts, Drizzle/Prisma schema for DB.
4. **Generate types from schemas** - do not hand-write parallel type hierarchies.
5. **Implement handlers as pure functions of parsed input** - validation at the edge, domain logic stays type-clean.
6. **Wire observability** - OpenTelemetry SDK + `@opentelemetry/instrumentation-*`, pino/bunyan structured logs with trace IDs, Prometheus via `prom-client`.
7. **Configure timeouts + retries** - `AbortSignal.timeout` on every outbound fetch, bounded retries via `cockatiel` or manual with jitter.
8. **Test** - Vitest (or Bun test) with Testcontainers, supertest/fetch for HTTP, contract tests, load test in CI.
9. **Ship** - multi-stage Docker, non-root user, `node --enable-source-maps`, `NODE_ENV=production`, health/readiness probes.

## Default Stack (2026 baseline)

- Runtime: Bun latest or Node 22 LTS (20 LTS minimum).
- Language: TypeScript 5.5+, `"module": "NodeNext"`, `"target": "ES2022"`, strict flags all on.
- Framework: Fastify (REST), NestJS (DI-heavy), tRPC (monorepo internal), Hono (edge).
- Validation: Zod v3 (default), Valibot (bundle-size sensitive).
- ORM / DB: Drizzle (default) or Prisma; `postgres.js` or `pg` with `@types/pg`.
- Clients: native `fetch` with `AbortSignal`; `undici` for advanced pooling.
- Logging: pino with pino-pretty in dev.
- Metrics: `prom-client`.
- Tracing: `@opentelemetry/sdk-node` with OTLP exporter.
- Testing: Vitest or `bun test`, Testcontainers, `msw` for HTTP mocking.
- Tooling: biome or eslint+prettier, tsc for type-check, `tsup` or `unbuild` for building libraries, `tsx` for dev.

## Deliverables Contract

- `tsconfig.json` with strict + noUncheckedIndexedAccess + exactOptionalPropertyTypes.
- Zod schemas for every external boundary (request, response, event, env).
- Type-safe ORM layer (Drizzle/Prisma) with migrations and rollback.
- OpenAPI or GraphQL schema generated from code where applicable.
- Structured logging with PII redaction and trace context.
- Metrics + traces wired via OpenTelemetry.
- Timeouts on every outbound fetch (`AbortSignal.timeout(ms)`).
- Bounded concurrency on all fan-out operations.
- Graceful shutdown with SIGTERM handler that drains in-flight work.
- Multi-stage Dockerfile, non-root, health endpoint.
- Tests: unit (pure domain), integration (Testcontainers), contract, load.

Quality gates: zero `any` in public signatures, zero `@ts-ignore` without justification, zero `as` casts on untrusted data, all env vars parsed through Zod, all writes idempotent or marked non-retriable, connection pools sized and documented, no unbounded Promise.all, no fire-and-forget promises touching IO.
