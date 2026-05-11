# Observability

**When to load this file:** Load when designing or reviewing metrics, logs, traces, dashboards, alerts, or SLOs. Covers Prometheus/Grafana patterns, log and trace pipelines, SLO math, and alert routing.

---

## The three pillars

- **Metrics** — aggregates over time. Low cardinality. Alerting, dashboards, trends.
- **Logs** — individual events with context. High cardinality. Debugging, audit.
- **Traces** — per-request paths across services. High cardinality. Performance debugging, dependency mapping.

Each answers different questions; pick the right tool per question. Don't log what should be a metric. Don't metric what should be a trace span.

---

## RED metrics (per service)

- **R**ate — requests per second.
- **E**rrors — error rate.
- **D**uration — latency distribution (p50, p95, p99).

Measure at service boundary for every endpoint/method/route. These drive SLOs.

## USE metrics (per resource)

- **U**tilization — % busy.
- **S**aturation — queued work waiting.
- **E**rrors — hardware/driver errors.

For CPU, memory, disk, network, connection pools, queues.

---

## Prometheus patterns

### Metric types

- **Counter** — monotonic increment. `http_requests_total{method,route,status}`. Rate-of-change interesting, not value.
- **Gauge** — up and down. `goroutines_in_flight`, `queue_depth`.
- **Histogram** — bucketed observations. `http_request_duration_seconds_bucket{le=...}`. Enables `histogram_quantile` for percentiles.
- **Summary** — client-side percentile. Can't aggregate across instances. Prefer histogram.

### Naming

- `<namespace>_<subsystem>_<name>_<unit>` — `http_requests_total`, `http_request_duration_seconds`.
- Base units: seconds (not milliseconds), bytes (not kilobytes).
- Label keys are low cardinality — `method`, `status`, `route`. Never `user_id`, never free-form request paths.

### Cardinality control

- Every unique label combo is a new time series. Cost scales with cardinality.
- Budget ~100k active series per service typical; 1M = expensive. Measure before adding a label.
- Collapse high-cardinality fields (URL path with IDs) into templates (`/users/:id`).

### Alert rules

```yaml
groups:
- name: app_alerts
  interval: 30s
  rules:
  - alert: HighErrorRate
    expr: |
      sum(rate(http_requests_total{status=~"5.."}[5m]))
      /
      sum(rate(http_requests_total[5m]))
      > 0.05
    for: 5m
    labels: { severity: critical }
    annotations:
      summary: "Error rate {{ $value | humanizePercentage }}"
      runbook: "https://runbooks.example.com/high-error-rate"

  - alert: HighLatencyP99
    expr: |
      histogram_quantile(0.99,
        sum by (le) (rate(http_request_duration_seconds_bucket[5m]))
      ) > 1
    for: 10m
    labels: { severity: warning }

  - alert: PodCrashLooping
    expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
    for: 5m
    labels: { severity: critical }
```

Every alert has:
- `for:` duration — reject flapping.
- `severity:` label for routing.
- `runbook:` annotation linking to playbook. No runbook, no alert.

---

## SLOs and error budgets

### Formalism

- SLI: measurable signal (e.g., "fraction of requests returning 2xx").
- SLO: target for SLI (e.g., "99.9% over rolling 28 days").
- Error budget: `(1 - SLO) × total requests`. The permitted failure budget.

### Burn-rate alerts

Raw threshold alerts (`error rate > 1%`) fire for brief spikes that don't matter and miss slow erosion that does. Use multi-window, multi-burn-rate alerts:

- **Fast burn:** 14.4x normal rate sustained 5min ∧ 1h → page. Would exhaust monthly budget in ~2 days.
- **Slow burn:** 6x normal rate sustained 6h ∧ 3 days → ticket. Erosion.

SRE Book Chapter 5 has formulas; most tools (Prometheus + sloth/pyrra, Grafana SLO, Datadog SLO) generate these correctly.

### Error budget policy

When budget exhausted:
- Freeze feature deploys on that service.
- Allocate work to reliability (fix alerts, fix flakes, add tests).
- Re-open deploys when budget regenerates.

Without this consequence, SLOs are decoration.

---

## Grafana dashboard design

Three tiers:

1. **Service overview** — RED for each service endpoint; SLO burn; key dependencies.
2. **Operational** — resource utilization, pod health, pool saturation.
3. **Debug** — slow query list, top errors, log + trace jumps.

Tips:
- Every panel has a unit. "500 what?" = bad panel.
- Links from panels to relevant logs/traces (templated URLs with time range).
- Annotations for deploys (stamp release events onto time series).
- No more than ~12 panels per dashboard — visual cognitive load.

---

## Logs

### Structure

- **JSON structured logs**, not free text. Downstream parsers demand it.
- Required fields: `timestamp` (ISO 8601 UTC), `level`, `service`, `trace_id`, `span_id`, `request_id`, `user_id` (when known), `message`.
- Event-style: what happened (`"user.created"`), with structured context. Avoid "string formatting" logs.

```json
{"ts":"2024-01-15T10:30:00.123Z","level":"INFO","service":"api","trace_id":"abc","request_id":"req_1","event":"order.created","order_id":"o_123","user_id":"u_456","amount_cents":9900}
```

### Log levels

- **ERROR** — something broke, action required. Paged-on-count.
- **WARN** — something recovered or suspicious. Trend-monitored.
- **INFO** — business events (order created, user logged in). Kept, indexed.
- **DEBUG** — development noise. Off in prod, on for selective requests via header/sampling.

Over-logging INFO = expensive + useless. Under-logging ERROR = blind during incident. Review log levels in code review.

### Pipelines

- **Sidecar / daemonset** log collector (Fluent Bit, Fluentd, Vector) reads container logs, forwards to backend.
- Backends: Loki (cheap, log-only), Elasticsearch/OpenSearch (fast search, expensive), Datadog / Splunk / Honeycomb (managed).
- Sample success logs (1%), keep all error logs.
- Retention: hot (7-14 days queryable) + cold (90 days for audit).
- PII redaction at collection, not in app code — enforced by pipeline.

---

## Distributed tracing

- Generate / propagate `trace_id` at the edge. W3C Trace Context (`traceparent` header) is the standard.
- Every service boundary is a span. Every external call is a span.
- Spans carry attributes: `http.method`, `http.status`, `db.statement`, etc. OpenTelemetry semantic conventions.
- Sampling: head-based (decide at start) is cheap but misses rare slow requests; tail-based (decide after span) captures rare slow/error traces but needs buffering infra.

### Common backends

- **Jaeger** — open-source, familiar UI.
- **Tempo** — open-source, cheap (only traces; search via log grep).
- **Honeycomb, Lightstep, Datadog APM, Grafana Cloud Traces** — managed.

### Trace-log correlation

- Log line includes `trace_id`. UI jumps from log → trace and back.
- Without correlation, traces and logs are two separate tools.

---

## Alert routing (AlertManager / PagerDuty / OpsGenie)

```yaml
route:
  group_by: [alertname, cluster]
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: slack-notifications
  routes:
  - match: { severity: critical }
    receiver: pagerduty
    continue: true
```

- **Critical** → page on-call primary; 24/7 response required.
- **Warning** → ticket / Slack; next-business-day response.
- **Info** → channel only; FYI.

### Alert hygiene

- Every alert has a runbook.
- Every page that didn't need action gets reviewed. Recurring → tune or delete.
- Silence during known work (deploys, maintenance) via calendar-aware routing.
- Deduplicate — don't alert on CPU high AND on error rate high when they're the same incident.

---

## ServiceMonitor / scrape targets

For Prometheus Operator on Kubernetes:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: myapp
  labels: { prometheus: kube-prometheus }
spec:
  selector: { matchLabels: { app: myapp } }
  endpoints:
  - port: http-metrics
    path: /metrics
    interval: 30s
    scrapeTimeout: 10s
```

- Pods expose `/metrics` endpoint via Prometheus client library.
- Port named `http-metrics` in Service.
- `interval` 15-60s typical.

---

## Synthetic monitoring

Active probing against production, not just reactive metrics:

- Health checks against critical paths (login, checkout).
- Global probe points (multi-region) to catch regional outages.
- Tools: Pingdom, UptimeRobot, Grafana Synthetic Monitoring, self-hosted Blackbox Exporter.

Catches "DNS dead" / "TLS cert expired" / "third-party dependency unavailable" scenarios that internal metrics miss.

---

## On-call tooling

- PagerDuty / OpsGenie / VictorOps — rotation, escalation, dedup.
- Schedules documented in IaC (e.g., PagerDuty Terraform provider).
- Primary + secondary rotation. Timezone-aware handoff.
- Incident commander role on Sev-1 — coordinates, does not debug.
- Slack channel per incident, auto-created from PagerDuty integration.
