# Distributed Systems

**When to load this file:** Load when designing or reviewing systems with multiple services and data-consistency decisions. Covers CAP, consistency models, distributed transactions, sagas, idempotency, circuit breakers, and service discovery.

---

## CAP theorem — the practical version

Network partitions happen. You pick **C**onsistency + **P**artition-tolerance (CP) or **A**vailability + **P** (AP).

| Profile | Systems | Use for |
|---|---|---|
| CP | PostgreSQL primary, MongoDB (with majority writes), HBase, Zookeeper, etcd | Money, inventory, locks, auth, config |
| AP | Cassandra, DynamoDB, Couchbase, Riak | Feeds, analytics, session, caches, search |

**Single-node databases are not "CA" in practice** — they just haven't experienced a partition yet. Plan for failure.

## Consistency models (weakest to strongest)

- **Eventual consistency** — all replicas converge "eventually". Reads may see stale or out-of-order values.
- **Read-your-writes** — a client that wrote sees its own write next read. Implementable via session affinity or replica-lag token.
- **Monotonic reads** — successive reads by one client never go backwards.
- **Causal consistency** — causally related operations seen in order; concurrent ops may reorder.
- **Sequential consistency** — all processes see operations in same order, matching some serial schedule.
- **Linearizability (strong)** — operations appear to happen instantaneously at some point between start and end. Requires consensus (Paxos, Raft).

**The right model is per-operation, not per-system.** A user-profile update may be linearizable, feed reads eventual.

## Latency cost

| Model | Round trips | Typical cost |
|---|---|---|
| Local read | 0 | μs |
| Single-DC replica read | 1 | ~1ms |
| Cross-AZ replicated write | 2-3 (RTT × quorum) | ~5-15ms |
| Cross-region replicated write | 2-3 × 50-150ms RTT | 100-500ms |
| Global consensus (linearizable) | 2 RTT to majority | 100ms+ |

Strong consistency across regions is very slow. Often you want "strong within region, async replicate cross-region".

---

## Distributed transactions

### Two-phase commit (2PC)

Coordinator asks each participant "can you commit?" (prepare), then "commit" or "abort". If coordinator fails between phases, participants block holding locks.

**Don't use across microservices.** Blocking failure mode, couples service lifetimes. Acceptable inside a single RDBMS cluster (XA) for rare cases.

### Saga pattern (preferred)

A saga is a sequence of local transactions; failures trigger compensating transactions in reverse order.

**Choreography (event-driven):** each service listens for events, does its work, emits next event. No central brain. Downsides: hard to reason about, cycles possible, flow spread across code.

**Orchestration:** a saga orchestrator calls each step, handles compensation. Easier to debug and change, adds one more service.

```typescript
class OrderSaga {
  async execute(order: Order) {
    const steps = [
      { action: () => this.reserveInventory(order), compensate: () => this.releaseInventory(order) },
      { action: () => this.processPayment(order),   compensate: () => this.refundPayment(order) },
      { action: () => this.shipOrder(order),        compensate: () => this.cancelShipment(order) }
    ];

    const completed = [];
    try {
      for (const s of steps) { await s.action(); completed.push(s); }
    } catch (err) {
      for (const s of completed.reverse()) {
        try { await s.compensate(); }
        catch (cErr) { logger.error('compensation failed', { step: s, cErr }); /* alert */ }
      }
      throw err;
    }
  }
}
```

**Compensation is not rollback.** A refund is semantically different from "undo the debit". Design compensating operations that are correct even if the original side-effected something already visible.

**Isolation is weaker.** Intermediate saga states are visible to other transactions — design around it (reserved-vs-confirmed states, flags, etc.).

---

## Idempotency

Every retryable write needs idempotency. The network will duplicate requests.

**Pattern:**
1. Client generates `Idempotency-Key: <uuid>` per logical operation.
2. Server looks up key in a store (Redis + TTL, or DB table) under a lock.
3. If present: return cached response, do not re-execute.
4. If absent: execute, store `key → response` with TTL (typically 24h), return response.
5. Failure mid-execute: retry (same key → cached failure response, or re-execute depending on policy).

Idempotency keys are scoped per-endpoint per-user to prevent collision. Store response code + body.

**Natural idempotency:** some operations are idempotent by structure — `PUT /users/{id}` with full body. `DELETE /users/{id}`. These still benefit from keys for log dedup.

---

## Retry and backoff

- **Exponential backoff:** `delay = base * 2^attempt` capped at max.
- **Jitter:** randomize within the window to break thundering herds. "Full jitter" = `random(0, delay)`.
- **Retry only idempotent operations**, or operations with an idempotency key.
- **Retry only on retriable errors** — `503 Service Unavailable`, `504 Gateway Timeout`, `UNAVAILABLE`, `DEADLINE_EXCEEDED`. Not on `400`, `401`, `403`, `404`, `422`, `INVALID_ARGUMENT`.
- **Budget** retries — if 5% of calls need retries, something is broken, not being robust. Alert on retry rate.
- **Retry cascade** — a retrying caller behind a retrying caller multiplies load during an outage. Cap total attempts across the chain.

## Timeouts

- Every IO operation has an explicit timeout. "Default" is not a timeout.
- Timeouts shorter than upstream's timeout — if upstream gives up at 30s, yours at 25s, theirs at 20s, etc. Otherwise the caller times out while upstream still works and retries into a running query (load multiplied).
- Connection timeout and read timeout are separate; set both.
- Hedged requests (send two, take first) reduce tail latency but multiply load; only for critical reads.

---

## Circuit breaker

Prevents cascading failure when a dependency is down.

**States:**
- **CLOSED** — normal, requests pass through. Failures counted.
- **OPEN** — too many failures, requests short-circuit immediately without calling dep. After timeout, move to HALF_OPEN.
- **HALF_OPEN** — limited probe requests; on success → CLOSED, on failure → OPEN.

```typescript
class CircuitBreaker {
  private failureCount = 0;
  private successCount = 0;
  private lastFailureTime: number | null = null;
  private state: 'CLOSED' | 'OPEN' | 'HALF_OPEN' = 'CLOSED';

  constructor(
    private threshold = 5,        // trip after N failures
    private timeout = 60_000,     // probe again after Tms
    private successThreshold = 2  // close after N probes
  ) {}

  async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (this.state === 'OPEN') {
      if (Date.now() - this.lastFailureTime! < this.timeout) throw new Error('Circuit OPEN');
      this.state = 'HALF_OPEN';
    }
    try {
      const r = await fn();
      this.onSuccess();
      return r;
    } catch (e) {
      this.onFailure();
      throw e;
    }
  }
  // onSuccess resets counts; in HALF_OPEN, counts probes, closes after threshold
  // onFailure increments count; trips OPEN at threshold, stamps lastFailureTime
}
```

**Gotchas:**
- Count timeouts as failures, not just exceptions.
- Per-dependency breaker, not global — one slow dep shouldn't trip calls to another.
- Fallback strategy matters — cached stale data, default values, or fast fail. Decide per use case.
- Don't trip on client-error 4xx — those aren't the dep being down.

---

## Service discovery & load balancing

### Discovery options

- **DNS-based** — service name resolves to list of IPs. Simple; stale for ~TTL.
- **Client-side registry** — Consul, etcd, Eureka. Client queries, maintains instance list. Client does load balancing.
- **Server-side (proxy)** — API gateway, service mesh (Istio, Linkerd). Transparent to service.
- **Kubernetes** — built-in via kube-proxy + Service. Usually sufficient within a cluster.

### Load balancing strategies

- **Round-robin** — fair for similar nodes, bad under heterogeneous load.
- **Least connections** — better under variable request durations.
- **Weighted** — for mixed-capacity fleets (e.g., post-canary).
- **Consistent hashing** — for cache affinity, session stickiness.
- **Latency-weighted (P2C)** — pick 2 random, choose less loaded. Good general default.

### Health checks

- Liveness — is the process up? Restart if not.
- Readiness — is it accepting traffic? Remove from LB if not (warming caches, migrations, etc.).
- Startup — is initial bootstrap done? Prevents kills during slow cold start.

Liveness ≠ readiness. Conflating them causes restart loops.

---

## Concurrency control

### Optimistic locking

- Add `version` column, increment on update. `UPDATE ... WHERE id = ? AND version = ?` — zero rows = someone else updated, retry or fail.
- Works under low contention. Fast (no locks held).

### Pessimistic locking

- `SELECT ... FOR UPDATE` — takes row-level lock, blocks others until commit/rollback.
- Use when contention is high and retry cost is expensive. Beware deadlocks (lock rows in consistent order).

### Distributed locks

- Redis `SET key value NX EX ttl` — acquire with timeout. Release with Lua script to avoid releasing someone else's lock.
- Redlock algorithm is controversial; simpler single-node Redis lock is often sufficient for non-critical mutual exclusion.
- ZooKeeper / etcd provide correct distributed locks with lease semantics.
- **Fencing token** — every lock issues an incrementing token; operations gated by "token must be >= last-seen". Protects against lock-held-past-expiry scenarios.

### Leader election

- Use etcd / ZooKeeper / Consul lease — don't roll your own with Redis for correctness-critical work.
- Leader epoch / fencing token required for safe leader handover.

---

## Event ordering

- **Within a partition / shard** — guaranteed order (Kafka partition, SQS FIFO group).
- **Across partitions** — no order guarantee. Don't assume.
- **Vector clocks / Lamport timestamps** — track causality without global clock.
- **Logical clocks** — cheaper, track "happens-before" relations.

If you need total order across events, you need a single ordering service or consensus. That's a bottleneck.
