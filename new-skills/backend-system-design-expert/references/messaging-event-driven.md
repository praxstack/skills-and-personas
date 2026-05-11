# Messaging & Event-Driven Architecture

**When to load this file:** Load when designing async flows — choosing between queues and streams, designing pub/sub, event sourcing, CQRS, DLQ handling, ordering guarantees, or exactly-once semantics.

---

## Queue vs stream vs pub/sub

| Need | Choice | Notes |
|---|---|---|
| Work distribution with retry | SQS, RabbitMQ | Competing consumers; messages consumed once |
| Durable event log with replay | Kafka, Kinesis, Pulsar | Many consumers can read independently; retention = days to forever |
| Fan-out notification (ephemeral) | SNS, Redis pub/sub | No durability in Redis pub/sub — subscribers miss messages if offline |
| Ordered per-key stream | Kafka partition, SQS FIFO group | Order only within partition/group |
| Scheduled / delayed | SQS delay queues, Redis sorted set + timer, Temporal | Beware clock drift, scheduler SPOFs |
| Cron / periodic workflow | Temporal, Airflow, managed schedulers | Don't roll your own for critical timing |

**Heuristic:** If downstream needs replay or multi-consumer independent reads → stream (Kafka). If it's just "do this work", → queue. If truly ephemeral fan-out → pubsub.

---

## Delivery semantics

- **At-most-once** — fire and forget; losses possible. Acceptable for metrics, logs where loss is OK.
- **At-least-once** — message may be delivered multiple times; consumer must be idempotent. The default for most queues/streams.
- **Exactly-once** — delivered once and processed once. True exactly-once end-to-end is very expensive and usually an illusion.

"Exactly-once" in Kafka (EOS) is exactly-once from producer → broker → consumer within a single Kafka transaction. It doesn't extend to external side effects (DB write, email send). For those, you need:

- **Idempotent consumer** (message ID + dedup table with TTL), or
- **Transactional outbox** (commit DB write + event row in same transaction, publish from outbox).

## Idempotent consumer

Mandatory for at-least-once. Every consumer:

1. Extracts a unique message ID (given by producer or derived deterministically from payload).
2. Checks "have I processed this ID?" — DB lookup or Redis.
3. If yes → ack, skip.
4. If no → process + write ID to dedup store in the same transaction as the effect.

Dedup window = retention of the queue + safety margin (days, not seconds).

---

## Transactional outbox pattern

Problem: writing to DB and publishing an event must both happen or neither. A normal code flow can succeed at DB write and fail at publish, leaving DB updated but no event.

**Solution:** write the event to an `outbox` table in the same DB transaction as the domain change. A separate publisher reads the outbox and publishes, marking rows published on success.

```
BEGIN;
INSERT INTO orders(...) VALUES (...);
INSERT INTO outbox(event_type, payload) VALUES ('order.created', '{...}');
COMMIT;

-- Separate worker:
SELECT * FROM outbox WHERE published_at IS NULL ORDER BY id LIMIT 100;
For each: publish to broker; on success UPDATE outbox SET published_at = NOW() WHERE id = ?;
```

This gives at-least-once publish; consumers still must dedup.

Change Data Capture (Debezium, DynamoDB Streams) is an outbox-like mechanism reading from the DB log directly.

---

## Ordering

- **Within a partition / group** — guaranteed.
- **Across partitions** — no guarantee.
- **Partition key** = the field whose order you need preserved. E.g., all events for a user → hash(user_id) → same partition → ordered per user.
- Order across different users is not guaranteed and shouldn't be needed.

**If you think you need global order, you've probably designed a bottleneck.** Rethink whether per-entity order is actually enough.

---

## Dead Letter Queue (DLQ)

Mandatory, not optional.

- After N failed delivery/processing attempts, messages move to DLQ.
- DLQ is a separate queue (same broker) with no auto-processing.
- Monitor DLQ depth — alert on any growth.
- Have a replay tool — moves messages back to main queue after operator review/fix.
- Most DLQ messages are "poison pills" (malformed payloads) — inspect, fix upstream, then replay.

Without DLQ, a poison message causes infinite retry = head-of-line block = all processing stops.

---

## Backpressure

Producers faster than consumers = unbounded queue growth = OOM / disk fill.

- **Bounded queues** — reject or block when full. Block is usually better — propagates backpressure to producer.
- **Rate limiting at producer** — cap emit rate.
- **Autoscale consumers** — scale on queue depth. Reactive, usually slower than the surge.
- **Load shedding** — drop low-priority messages deliberately rather than fall over.

Unbounded queues are a disguised outage — they "work" until they don't.

---

## Publish-subscribe

**Kafka model:** producers publish to topics; consumers join consumer groups. Each message delivered to each group once (broker handles rebalance and offsets).

Single consumer group = competing consumers (work distribution).
Multiple groups on same topic = fan-out to independent consumers.

**SNS model:** publish to topic; SNS fans out to subscribers (SQS queues, HTTP endpoints, email, etc.). No retention — subscribers must be ready.

---

## Event-driven architecture patterns

### Event notification

Lightweight: "something happened, here's an ID". Consumers fetch details if needed.

- Small payload, minimal coupling.
- Consumers must call back to source, increasing read load on source.

### Event-carried state transfer

Payload includes full state needed by consumers.

- Bigger payloads; more schema coupling.
- Consumers self-sufficient — can scale reads independently of source.

**Trade-off:** coupling (state transfer ties schema) vs. load (notification creates read amplification).

### Event sourcing

Canonical data = the append-only sequence of events. Current state is a fold over the event log.

**Pros:**
- Full audit trail.
- Replay to derive new read models (CQRS).
- Temporal queries ("what was state at time T?").

**Cons:**
- Event schema evolution is hard — old events persist forever.
- Complex mental model; not every domain benefits.
- Snapshots required for large aggregates to avoid folding millions of events per read.

**Don't default to event sourcing.** Use it when you have clear need (audit, replay, temporal queries). For most CRUD apps, plain DB + outbox is sufficient.

### CQRS (Command Query Responsibility Segregation)

Write model ≠ read model. Writes go through commands (mutating the event log or write DB); reads come from denormalized projections optimized for query patterns.

- Good for systems with very different read and write shapes (heavy reads of aggregated data, structured writes).
- Adds operational complexity (two data stores, sync via events).
- Projections are eventually consistent with write model — design UX for it (show "processing…" until projection catches up).

---

## Schema evolution

Events outlive code. Schema will change.

- **Additive changes** are safe — new fields ignored by old consumers.
- **Removing or renaming fields** is not safe — breaks consumers.
- **Changing semantics** of a field is silent corruption.

**Tools:**
- Schema registry (Confluent, AWS Glue) — enforces compatibility rules at publish time.
- Avro / Protobuf — built-in evolution rules; backward-compatible by default.
- JSON with versioning — simpler but no enforcement; bugs leak through.

**Compatibility modes:**
- Backward compatible: new schema can read old data (add nullable fields, default values).
- Forward compatible: old schema can read new data (ignore unknown fields).
- Full: both.

Pick one per topic, enforce it.

---

## Saga implementation via events (choreography)

```
[Order Service] creates order → publishes "order.created"
[Payment Service] processes payment → "payment.completed" or "payment.failed"
[Inventory Service] reserves → "items.reserved" or "items.out_of_stock"
[Shipping Service] ships → "order.shipped"

On failure at any step, publish failure event → upstream services handle compensation.
```

Complexity explodes quickly — any service can listen to any event, flows scatter. Add an orchestrator (or use Temporal / Step Functions) once you have >3 participants.

---

## Gotchas by technology

### Kafka
- Partition count is set at topic create; adding later rehashes some keys. Plan partition count.
- Consumer lag = freshness metric — expose always.
- Offset commit is not the same as "processed" — commit after effect is durable.
- Rebalance storms stop the whole group temporarily; tune `session.timeout.ms`, `max.poll.interval.ms`.
- Retention (time or size) — data gone after; for audit use compacted topics.

### SQS
- Visibility timeout = time a message is hidden from other consumers after being received. Longer than your max processing time, or message gets duplicated.
- Standard queue = at-least-once, unordered. FIFO queue = ordered per group, limited throughput.
- Max message size 256KB — for larger, store in S3, pass pointer.
- No native DLQ — configure redrive policy.

### RabbitMQ
- Ack mode matters — auto-ack = at-most-once (data loss on crash). Manual ack = at-least-once.
- Publisher confirms — broker ack after durable write; without them, publisher doesn't know if message landed.
- Queue mirroring / quorum queues for HA; non-mirrored queue dies with its node.

### Redis pub/sub
- Not durable — subscribers offline miss messages.
- For durability, use Redis Streams (`XADD`/`XREADGROUP`) or Redis Queue libraries, not pub/sub.

---

## Observability for messaging

Metrics every async system must expose:

- Publish rate, publish errors, publish latency.
- Consumer lag (depth for queue, offset lag for stream).
- Processing duration, processing errors.
- DLQ depth.
- Retry count per message.
- Idempotency dedup hit rate (spotting duplicates tells you about broker behavior).

Trace correlation: propagate trace/correlation ID through message headers (`trace-id`, `idempotency-key`) so end-to-end spans cover produce → consume.
