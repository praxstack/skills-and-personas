# Performance & Load Testing

**When to load this file:** Designing load tests, interpreting performance results, setting SLOs, or diagnosing production slowness.

## Test Types — Use the Right One

| Type | Purpose | Shape |
|------|---------|-------|
| Smoke | Does the system work under tiny load? | Flat, 1-10 VUs, short |
| Load | Handle expected traffic? | Ramp to target, sustain, ramp down |
| Stress | Find breaking point | Progressive ramp past expected |
| Spike | Survive sudden surge? | Flat baseline → sudden 10x → return |
| Soak (endurance) | Memory leaks? Resource exhaustion? | Moderate load for hours / overnight |
| Breakpoint | Exact failure threshold | Slow progressive increase |

**Common mistake:** running "a load test" without specifying which type. Each answers a different question.

## Defining What "Good" Means (SLIs → SLOs)

**SLI (Service Level Indicator):** the thing you measure — p95 latency, error rate, throughput, availability.

**SLO (Service Level Objective):** target for the SLI — "p95 < 300ms, 99.9% of requests succeed."

**SLA (Service Level Agreement):** external commitment — usually SLO with penalty clauses.

Load tests validate SLOs. Without SLOs, "passed" is meaningless.

**Percentiles over averages.** Average latency can look fine while p99 users have 5-second waits. Always report p50, p95, p99.

## k6 Structure

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 20 },  // ramp up
    { duration: '2m', target: 20 },   // sustain
    { duration: '30s', target: 100 }, // ramp to peak
    { duration: '5m', target: 100 },  // sustain peak
    { duration: '30s', target: 0 },   // ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  const res = http.get('https://api.example.com/health');
  check(res, { 'status 200': (r) => r.status === 200 });
  sleep(1);
}
```

Key points:
- **Thresholds fail the build** — CI integration without intervention.
- **Stages model realistic traffic** — ramps, not instant full load.
- **`sleep()` simulates think time** — users don't hammer; be realistic.

## Artillery (YAML config, lower code)

Good for teams that prefer config-first. Weaker scripting than k6 but easier to onboard QA.

## Interpreting Results

**Latency percentiles:**
- p50 (median): typical user experience.
- p95: 19 of 20 users.
- p99: worst 1% — often reveals tail issues (GC pauses, contention).
- p99.9: extreme — the pager-duty threshold.

**Look for:**
- Latency growth as VUs increase — linear = bad scaling; flat = healthy within range.
- Error rate spike — usually means you hit a limit (DB connections, thread pool, memory).
- Latency variance widening — tail heaviness; something is contending.

**Throughput ceiling:** at some point, adding load doesn't increase throughput (req/s). That's your ceiling. Below ceiling, added load increases latency; above, requests drop/fail.

## Identifying Bottlenecks

**Layer-by-layer elimination:**
1. Is the load test client itself bottlenecking? Check CPU/network of k6 runner.
2. Network: measure latency between client and server separately.
3. LB / API gateway: CPU, connections.
4. App servers: CPU, memory, GC pauses, thread pool exhaustion.
5. DB: query time, connection pool, locking, I/O wait.
6. Cache: hit rate, eviction.
7. External services: third-party API latency.

**Flame graphs + APM** (Datadog, New Relic, Honeycomb) make this faster than guessing.

## Common Performance Issues

- **N+1 queries:** 1 query fetches list, then 1 query per item. Fix: eager-load (Prisma `include`, SQL JOIN, GraphQL DataLoader).
- **Missing indexes:** full table scans on filtered/joined columns. Check `EXPLAIN ANALYZE`.
- **Lock contention:** transactions holding locks longer than needed. Minimize transaction scope; use `SELECT FOR UPDATE SKIP LOCKED` for queue patterns.
- **Connection pool exhaustion:** too few connections configured, or requests holding connections while awaiting external calls. Size pools; release connections during I/O.
- **Thread pool starvation:** blocking I/O on sync-style web servers. Use async/non-blocking for I/O-heavy work.
- **Memory leaks:** objects retained unexpectedly. Soak tests reveal. Heap profilers (VisualVM, clinic.js, py-spy) identify.
- **Cold caches:** first request after deploy or cache eviction slow. Warm critical caches on startup.
- **GC pauses (JVM, Go):** long stop-the-world pauses on older GCs. Tune or upgrade to G1/ZGC.
- **Chatty external services:** calls added per request. Cache, batch, or parallelize.
- **Payload bloat:** API returns everything; caller needs a slice. Use field selection (GraphQL) or explicit DTOs.

## Load Test Traffic Profile — Make It Realistic

Real users:
- Think between requests (not continuous).
- Mix of read vs write (usually 80/20 or more read-heavy).
- Session-scoped: sequence of calls, not independent.
- Distribute over time zones (not all-at-once).
- Different endpoints have different frequencies.

Capture real traffic patterns from production logs (top 20 endpoints by volume + ratio) and script to match.

## Environment Considerations

- **Load test on production-like environment.** Staging smaller than prod gives optimistic results. Use production-shape data volume.
- **Isolate test runner** — running k6 on the same host as the app skews results.
- **Network realistic** — if users are on mobile 4G, test from similar conditions (throttling plugins).
- **Warm-up period excluded** from metrics — JIT, caches warm up.
- **Multiple runs** — single-run results are noisy; average 3-5 runs.

## Performance Budgets (Frontend)

- **LCP** (Largest Contentful Paint): <2.5s good.
- **INP** (Interaction to Next Paint, replaces FID): <200ms good.
- **CLS** (Cumulative Layout Shift): <0.1 good.
- **TTFB** (Time to First Byte): <200ms good.
- **FCP** (First Contentful Paint): <1.8s good.

Enforce in CI via Lighthouse CI or WebPageTest API. Fail builds that regress.

## Capacity Planning

Given load test results + production traffic:
- **Headroom:** current production runs at p95 150ms, peak 200ms. Load test shows system degrades at 3x peak. Headroom = 3x.
- **Growth planning:** at expected growth rate, headroom runs out in N months. Plan scaling.
- **Autoscaling thresholds:** scale OUT at 70% CPU (buffer for spikes); scale IN slowly (prevent flapping).
- **Database capacity:** vertical scaling limits → plan for sharding/read replicas before hitting ceiling.

## Specific Patterns

**Test auth'd user flow — script login:**
```javascript
const loginRes = http.post(url, JSON.stringify(creds), { headers });
const token = loginRes.json('accessToken');
http.get(profileUrl, { headers: { Authorization: `Bearer ${token}` } });
```

**Data churn — unique records:**
```javascript
const uniqueEmail = `user${__VU}-${__ITER}@test.com`;
```

**Graceful degradation test:**
- Overload the system deliberately.
- Verify: does it return 503 with retry-after? Partial responses from cache? Or does it crash?

**Chaos-lite during load:**
- Kill a pod mid-test.
- Throttle network to dependency.
- Verify resilience patterns (circuit breaker, retries with backoff, fallback).

## Continuous Performance Testing

- **Per-PR benchmark:** micro-benchmarks of hot paths (BenchmarkDotNet, pytest-benchmark, go test -bench). Fail if regression >10%.
- **Nightly load test:** full load run against staging on a production-shape dataset.
- **Pre-release:** full stress + soak before major releases.
- **Production synthetic monitoring:** continuous real-user-flow tests from various regions (Datadog Synthetics, Checkly).

## Reading Load Test Reports — Checklist

1. Did the test reach the intended VU count? (otherwise results are meaningless)
2. Were thresholds set, and did they pass?
3. What's the p50/p95/p99 latency shape? Any tail heaviness?
4. Error rate below threshold?
5. Throughput ceiling reached?
6. Resource utilization (CPU, memory, connections) — where are we vs headroom?
7. Did downstream (DB, cache) show signs of stress?
8. Any surprising outliers or step-function changes?
9. How does this compare to previous run?
10. What's the action item — ship, scale, optimize, abort?

## Common Mistakes

- **No baseline:** first-ever load test with no comparison point. Establish baseline early.
- **Confusing VUs with req/s:** 100 VUs with 1s think time is ~100 req/s, not 100/s raw. Be explicit.
- **No ramp-up:** instant 1000 VUs is not realistic and warps results.
- **Ignoring errors:** 500 error at p95 latency 100ms is not a pass.
- **Testing against cached/warm state:** second run looks magically fast because caches are warm from the first.
- **Not cleaning test data:** load tests leave artifacts; cleanup or use separate DBs.
- **Production load tests without safeguards:** if you must test prod (rare), use feature flags, percent rollouts, and kill switches. Prefer staging.
