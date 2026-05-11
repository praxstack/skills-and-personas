---
name: backend-pe-nodejs
description: 'Principal-engineer-grade guidance for the Node.js runtime itself - event loop, streams, worker threads, cluster, memory, GC, native addons, and runtime-level failure modes. Covers diagnosing event-loop lag, heap leaks, CPU profiling, AsyncLocalStorage, AbortController, and production-grade process lifecycle on Node 20+ LTS or Bun. Use when debugging or tuning Node runtime behavior, investigating latency spikes, memory leaks, throughput regressions, or designing at the runtime level. Trigger keywords - Node.js runtime, event loop, event loop lag, worker threads, cluster, streams backpressure, AsyncLocalStorage, heap snapshot, clinic.js, flamegraph, node --prof, memory leak Node, V8 tuning, AbortController, graceful shutdown Node. Not for language-level concerns (use backend-pe-javascript or backend-pe-typescript).'
---

# Node.js Runtime Principal Engineer

**Audience:** Engineers diagnosing, tuning, or designing against the Node.js runtime itself - event loop behavior, streams, worker threads, memory, GC, native addons, process lifecycle.

**Goal:** Principal-engineer-grade understanding of Node internals sufficient to diagnose any production issue, tune for predictable tail latency, and design services that exploit the runtime correctly.

## Priority Model

Correctness - Reliability - Security - Performance (event-loop health) - Observability - Scalability - Operability. In that order.

## Core Principles

1. **Node is single-threaded by design - the event loop is your critical section.** Every request, timer, and I/O callback shares one JS execution context. A 50ms sync function at 100 QPS produces 100% event-loop utilization. Measure event-loop lag continuously (`perf_hooks.monitorEventLoopDelay`). P99 lag budget: sub-10ms for latency-sensitive services, sub-100ms for batch.

2. **Blocking work belongs off the main thread.** CPU-bound hashing, cryptography, image processing, parsing megabyte payloads - move to `worker_threads` with a pool pattern (piscina). Never `crypto.pbkdf2Sync`, `zlib.gzipSync`, `JSON.parse` on multi-MB payloads, or heavy regexes on the main thread. libuv's thread pool (default size 4) handles file I/O and some crypto - tune `UV_THREADPOOL_SIZE` only with measurement.

3. **Streams with backpressure, or memory fails.** Reading a file or HTTP body into a string/buffer for any non-trivial size is an OOM waiting. Use Node streams, `stream/promises.pipeline`, or Web Streams. Respect the pause/resume signal. `for await (const chunk of stream)` is the idiomatic consumer. `Transform` streams for pipeline processing.

4. **Memory leaks come from references, not from allocation.** Common leak sources: module-level Maps growing unbounded, event listeners never removed, `setInterval` without cleanup, closures retaining large objects, cached `Buffer`s. Every cache needs an eviction policy (LRU via `lru-cache`). Take heap snapshots with `--inspect` + Chrome DevTools or `v8.writeHeapSnapshot()`; compare two points in time.

5. **Context propagation is AsyncLocalStorage.** Trace IDs, tenant IDs, user context across async boundaries - `AsyncLocalStorage` from `node:async_hooks`. Don't thread context through every function parameter. Don't use `cls-hooked` in new code (legacy). Beware that some native addons don't preserve async context.

6. **Signals and graceful shutdown are first-class.** SIGTERM starts a drain: stop accepting new connections, finish in-flight, close DB pools, close Kafka consumers, flush logs/traces, then exit. Use a `shutdown()` coordinator with a deadline. Kubernetes gives you `terminationGracePeriodSeconds` - use it.

## Decision Framework

**`cluster` vs. worker threads vs. horizontal scaling.**
- Horizontal scaling (multiple pods/processes) - default for most deployments. Let the orchestrator handle it.
- `cluster` module - single-box multi-core utilization when you can't add pods. Node 20+'s default `scheduling` is OK. Sticky sessions are your problem.
- `worker_threads` - CPU-bound work offloaded from main thread within the same process, shared memory via `SharedArrayBuffer` when needed.

**PM2 / forever / systemd / Kubernetes.** Kubernetes + container for production. Systemd for single-box services. PM2 only for non-containerized environments; its clustering is inferior to k8s orchestration.

**Native fetch vs. undici vs. axios vs. got.** Native `fetch` (Node 18+) for simple cases. `undici` directly when you need keep-alive pool tuning, HTTP/2, or dispatcher control. `axios` and `got` are legacy ergonomics layers - not needed in modern Node.

**Bun vs. Node 20+ LTS.** Bun for speed-sensitive new services where the dep tree is compatible. Node 20+ LTS for mature ecosystems and native-module-heavy code. Don't mix in production without isolation.

**V8 heap tuning.** Default heap is ~1.7 GB on 64-bit. Increase via `--max-old-space-size=NNNN` (MB) when profiling shows legitimate need, not when plugging leaks. Remember containers: set the flag based on the cgroup limit, not the host RAM.

**Logging: pino vs. winston vs. bunyan.** pino for performance (the only serious choice for hot paths), winston for flexibility/transports in non-hot paths. bunyan is legacy.

## Anti-Patterns

- **`JSON.parse` on a multi-MB body in a request handler.** Blocks the event loop for tens of milliseconds. Stream-parse or move to a worker.
- **Sync crypto (`crypto.pbkdf2Sync`, bcrypt sync) on the main thread.** Use async variants or worker threads.
- **`fs.readFileSync` at request time.** Cache results at startup or use async.
- **Unbounded caches.** `Map` or plain object growing per unique key. Use `lru-cache`.
- **`setInterval` without `unref()` or cleanup.** Keeps process alive and leaks memory.
- **Event listeners not removed on disposal.** Classic leak - 11+ listener warning, then OOM.
- **Not handling `unhandledRejection` and `uncaughtException`.** Default in Node 20+ is terminate on unhandled rejection (good). Install a handler that logs then exits; never absorb.
- **`process.exit(0)` without flushing logs/traces.** Stdout is not flushed; telemetry batched; data loss. Use a `shutdown()` coordinator.
- **Bundling a service with webpack/rollup.** Usually unnecessary. Node runs `.js`/`.ts` (with tsx/ts-node) directly. Bundling can break source maps and native modules.
- **`--experimental-*` flags in production.** Experimental means it may change or crash. Pin to stable.
- **Sharing state across `cluster` workers via filesystem or globals.** Use Redis or a real shared store.
- **Ignoring `process.memoryUsage().rss` vs. `heapUsed`.** RSS includes native allocations; heap is only V8. Both matter.
- **Logging Buffers or full objects.** Massive log lines, PII leaks, I/O cost. Redact and truncate.
- **Using `child_process.exec` with user input.** Shell injection. Use `execFile` with argv.

## Diagnostic Workflow

### Event-loop lag spike
1. `perf_hooks.monitorEventLoopDelay()` in prod continuously.
2. Correlate lag spikes with request rate, GC pauses, and specific endpoints.
3. Capture CPU profile for the spike window (`--cpu-prof` or `0x` flamegraph).
4. Look for long sync functions. Move them to worker threads.

### Memory leak
1. Stable load test; RSS and heap over time via `process.memoryUsage()`.
2. Two heap snapshots (baseline + after 10 min load). Compare retainers.
3. Common suspects: closures, module-level Maps, unremoved listeners, pending timers.
4. `--heap-prof` for sampling heap profile.

### CPU pegged at 100%
1. `--cpu-prof` or `0x` flamegraph during the load.
2. Look for JSON parse/stringify, regex, crypto sync calls.
3. Measure event-loop lag; a CPU-bound service without lag is probably I/O-bound downstream.

### Throughput regression
1. Diff of event-loop utilization, GC time, and libuv thread pool saturation.
2. Measure before and after a suspected commit with the same load profile (k6, autocannon).
3. Node's `--trace-gc` for GC behavior.

## Runtime Defaults (2026 baseline)

- Runtime: Node 22 LTS (or Node 20 LTS minimum); Bun where validated.
- Flags: `--enable-source-maps` in production; `--max-old-space-size` set from cgroup limit; `--heapsnapshot-near-heap-limit=3` for post-mortem leak analysis; avoid `--experimental-*`.
- Environment: `NODE_ENV=production`, `UV_THREADPOOL_SIZE` default unless measured.
- Observability: OpenTelemetry SDK for Node with auto-instrumentation of http, fs, dns, net, pg, mysql, redis; pino for logs; `prom-client` for metrics; `perf_hooks.monitorEventLoopDelay` for lag.
- HTTP: `undici` for client control; Fastify for server.
- Streams: Web Streams for edge, Node streams for traditional; `stream/promises.pipeline` for composition.
- Workers: `piscina` for worker thread pools.
- Shutdown: SIGTERM handler with deadline-bounded drain of HTTP server, DB pools, queue consumers, trace/log exporters.

## Deliverables Contract

- Process lifecycle: SIGTERM handler that drains HTTP, DB, and queue connections within `terminationGracePeriodSeconds`.
- Event-loop lag monitoring in production with SLO alert.
- Heap and RSS monitoring; alert when heap > 80% of limit.
- CPU profiling and heap snapshot tooling documented in runbook.
- Worker thread pool for any CPU-bound work >5ms.
- Bounded concurrency on all fan-out; bounded queues on all back-pressure paths.
- Streams with pipeline for all large-payload I/O.
- AsyncLocalStorage for trace/tenant context propagation.
- Pinned runtime (`engines` + Dockerfile).
- Multi-stage Docker, non-root user, explicit heap limit.
- Runbook covering event-loop lag, memory leak, CPU saturation, throughput regression diagnostic playbooks.

Quality gates: event-loop lag P99 within budget under peak load, no sync crypto/compression/parsing on main thread, no unbounded caches or listeners, all timers cleaned up on shutdown, signal handlers installed, graceful shutdown drains within deadline, logs and traces flushed before exit.
