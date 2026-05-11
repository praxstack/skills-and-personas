---
name: backend-pe-javascript
description: 'Principal-engineer-grade JavaScript (non-TypeScript) backend design, implementation, and review. Covers Node 20+ LTS / Bun, modern ESM, runtime validation (Zod/Ajv), JSDoc types, Fastify/Hono/Express, Prisma/Drizzle, and JavaScript-specific failure modes (untyped boundaries, prototype pollution, async leaks, event-loop blocking). Use when designing, building, reviewing, refactoring, hardening, or debugging plain JavaScript backend services where adopting TypeScript is not an option. Trigger keywords - JavaScript backend, Node.js service, Fastify, Hono, ESM, Bun JavaScript, JSDoc types, Zod validation, Ajv, plain JS. Not for TypeScript code (use backend-pe-typescript), Node runtime internals (use backend-pe-nodejs), or frontend work.'
---

# JavaScript Backend Principal Engineer

**Audience:** Engineers designing, building, reviewing, or hardening plain JavaScript (non-TypeScript) backend services on Bun or Node 20+ LTS.

**Goal:** Principal-engineer-grade JavaScript - correctness maintained without a compiler, runtime validation at every boundary, JSDoc typing where it helps, and production hardening by default.

## Priority Model

Correctness - Reliability - Security - Performance - Observability - Data consistency - Scalability - Developer experience. In that order.

## Core Principles

1. **Without TypeScript, runtime validation is not optional.** Every external input - HTTP request, queue message, DB result, env var, file - parsed through Zod or Ajv before touching business logic. There is no compiler to catch a missing field or wrong type; the schema is the only source of truth.

2. **JSDoc + `checkJs` gives you 70% of TypeScript at 0% migration cost.** Add `"checkJs": true` in `jsconfig.json`, annotate public functions with JSDoc types, and VSCode + `tsc --noEmit` will catch most type bugs. Document why you chose plain JS over TS; if the reason evaporates, migrate.

3. **ESM only. CommonJS is legacy.** `"type": "module"`, `import`/`export`, explicit `.js` extensions in imports, top-level `await` where useful. Dual packages (ESM + CJS) are a tax; avoid unless publishing a library. Avoid `require` in new code.

4. **Prototype pollution is a real vulnerability.** `Object.assign(target, userInput)`, `_.merge`, `JSON.parse` of user-controlled strings written to `__proto__` - all can pollute `Object.prototype` globally. Freeze critical prototypes (`Object.freeze(Object.prototype)`), use `Object.create(null)` for lookup maps, validate user input shape before merging.

5. **Async errors are the leading cause of silent bugs.** An async function whose promise is not awaited or `.catch`ed will reject silently (Node 20+ default: crash, but only if nothing handled it). Always await or chain `.catch`. Never fire-and-forget a promise that performs I/O. Use `unhandledRejection` to crash-and-restart, not to absorb.

6. **Pin your runtime.** `package.json` `"engines"` field, matching Dockerfile `FROM node:20.x-slim` (exact minor), `npm`/`pnpm`/`bun` lockfile committed. "Works on my machine" is a runtime mismatch 90% of the time.

## Decision Framework

**Plain JS vs. TypeScript.** Default is TypeScript. Justify plain JS: small surface, no team expertise, tight runtime constraints, existing large JS codebase not ready to migrate. Document the decision. If choosing JS, commit to JSDoc + `checkJs`.

**Fastify vs. Hono vs. Express.**
- Fastify - high throughput, JSON schema validation built in (Ajv), mature plugin system.
- Hono - edge runtimes (Cloudflare Workers, Bun, Deno), lightweight.
- Express - legacy only. Don't start new services on it.

**Zod vs. Ajv vs. Joi.**
- Ajv - JSON Schema, fastest, Fastify's native choice, large ecosystem.
- Zod - ergonomic, composable, TS-first but works fine in JS.
- Joi - legacy; avoid for new code.

**Bun vs. Node 20+ LTS.** Bun for new services where speed matters and the dependency tree is Bun-compatible. Node 20+ for mature ecosystems and native-module-heavy code. Never target Node < 20 for new code.

**Prisma vs. Drizzle vs. pg / postgres.js.**
- Prisma - productive ORM, strong migrations, heavier install, runtime query engine.
- Drizzle - type-safe SQL with JSDoc fallback, lighter.
- `postgres.js` or `pg` - raw SQL control, smaller surface.

**Package manager.** pnpm (default for speed and correct hoisting), npm (universal baseline), bun install (if on Bun). Avoid yarn classic in new projects.

## Anti-Patterns

- **`JSON.parse` without validation.** Parse then validate.
- **`Object.assign(existing, userInput)` or spread merge with user data.** Prototype pollution vector. Validate shape first, use `Object.create(null)` for maps.
- **`eval` / `new Function` with any user data.** RCE. Never.
- **`for...in` over an object expecting only own properties.** Iterates inherited too. Use `Object.keys`/`entries` or `for...of`.
- **`==` anywhere.** Always `===`. Enforce with lint.
- **`var`.** `const` by default, `let` when reassignment is required.
- **Mutating function parameters that are objects.** Surprising side effects. Return new.
- **Unhandled promise rejections.** Crash-and-restart; do not absorb.
- **Awaiting inside a `for` loop when iterations are independent.** `Promise.all` with bounded concurrency via `p-limit`.
- **`Promise.all` with unbounded input.** `pMap(items, fn, {concurrency: N})`.
- **Global state modules.** Hard to test. Use explicit construction and DI.
- **Reading `process.env.FOO` scattered.** Parse once at boot into a typed config.
- **Ignoring the event loop.** `setImmediate` + heavy sync work blocks other requests. Profile with `--prof` or clinic.js.
- **`setTimeout` callbacks without `unref()` in shutdown logic.** Keeps the process alive.
- **Manual SQL string concatenation.** Injection. Parameterized queries always.
- **Storing secrets in environment strings that get logged.** Redact at the logging layer.

## Standard Workflow

1. **Clarify SLOs and traffic shape** - P50/P95/P99 latency, QPS, payload sizes, runtime target (Node/Bun/edge).
2. **Declare typing strategy** - plain JS + JSDoc + `checkJs`, or migrate to TS. Commit to one.
3. **Choose framework and ORM** - see decision tables. Document tradeoffs.
4. **Define schemas at boundaries** - Ajv (JSON Schema) for Fastify-native, Zod for composability. Keep schema as source of truth.
5. **Implement handlers as pure functions of parsed input** - validate at edge, logic stays clean.
6. **Wire observability** - OpenTelemetry SDK + auto-instrumentation, pino structured logs with trace IDs, `prom-client` metrics.
7. **Timeouts + retries** - `AbortSignal.timeout` on every outbound fetch, bounded retries with jitter.
8. **Test** - Vitest or node's built-in `node:test`, Testcontainers for dependencies, supertest or fetch for HTTP, load test in CI.
9. **Ship** - multi-stage Docker pinned to exact Node/Bun minor, non-root user, `NODE_ENV=production`, health/readiness probes.

## Default Stack (2026 baseline)

- Runtime: Bun latest or Node 22 LTS (20 LTS minimum), pinned in `engines` + Dockerfile.
- Module system: ESM only, `"type": "module"`.
- Type checking: JSDoc + `"checkJs": true` in `jsconfig.json`, `tsc --noEmit` in CI.
- Framework: Fastify (REST default), Hono (edge).
- Validation: Ajv (JSON Schema, Fastify-native) or Zod (composable).
- ORM / DB: Drizzle (default), Prisma (mature), `postgres.js` / `pg` (raw).
- Clients: native `fetch` with `AbortSignal`; `undici` for advanced pooling.
- Logging: pino with pino-pretty in dev.
- Metrics: `prom-client`.
- Tracing: `@opentelemetry/sdk-node` with OTLP exporter.
- Testing: Vitest, `node:test`, Testcontainers, `msw` for HTTP mocking.
- Package manager: pnpm (default), npm, or bun install.
- Tooling: biome (default) or eslint + prettier; `tsc --noEmit` for JSDoc type checking.

## Deliverables Contract

- `package.json` with `"engines"` pinned, lockfile committed.
- `jsconfig.json` with `"checkJs": true`, `"strict": true`, `"noUncheckedIndexedAccess": true`.
- JSDoc types on all exported public functions.
- Schemas (Ajv or Zod) for every external boundary.
- Typed ORM layer with migrations and rollback.
- Structured logging with PII redaction and trace context.
- Metrics + traces via OpenTelemetry.
- Timeouts on every outbound call (`AbortSignal.timeout(ms)`).
- Bounded concurrency on all fan-out.
- Graceful shutdown with SIGTERM handler and drain.
- Multi-stage Dockerfile, non-root, health endpoint.
- Tests: unit (pure domain), integration (Testcontainers), contract, load.

Quality gates: `tsc --noEmit` passes with `checkJs`, all env vars parsed via schema at boot, no `eval`/`new Function`, no prototype-pollution-prone merges, all outbound calls timed, all writes idempotent or marked non-retriable, no unbounded `Promise.all`, no fire-and-forget promises touching I/O.
