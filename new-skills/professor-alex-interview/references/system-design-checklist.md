# System Design Interview Checklist

The standard stages of a 45-60 minute system design interview, with what to push on in each. The mentor's job is to act as interviewer — guide the candidate through stages, push back on vagueness, and draw the architecture only after they've described their design (so they see their own design visualized).

---

## Stage 1: Clarify Requirements (5-8 min)

Push the candidate to split into:

**Functional requirements:**
- Core features (1-3 must-haves)
- Nice-to-haves (explicitly deferred)
- Out of scope (explicitly deferred)

**Non-functional requirements:**
- Scale (users, requests/sec, data volume)
- Latency (P50 / P95 / P99)
- Availability (3 nines? 4?)
- Consistency model (strong? eventual? read-your-writes?)
- Durability
- Security / compliance

**Push-back prompts:**
- "You said 'lots of users' — what's 'lots'? Give me a number."
- "What's the read-to-write ratio?"
- "Is this global or regional?"
- "What's the tolerable data loss window?"

**Red flag:** Candidate dives into architecture before clarifying. Stop them.

---

## Stage 2: Back-of-Envelope Estimation (5-8 min)

Candidate does the math, not the mentor.

**Estimate:**
- QPS (read and write separately)
- Storage per day / year
- Bandwidth in/out
- Memory footprint if caching

**Cheat numbers to know:**
- 1 day ≈ 100K seconds (actually 86.4K, but this simplifies math)
- 1 million requests/day ≈ 12 requests/sec
- 1 billion requests/day ≈ 12K requests/sec
- 1 KB per record × 1 billion records = 1 TB
- HDD seek ≈ 10 ms, SSD seek ≈ 0.1 ms, memory access ≈ 100 ns, L1 cache ≈ 1 ns
- Data center round trip ≈ 500 µs; cross-country ≈ 30-50 ms; cross-continent ≈ 150-250 ms
- Read from memory is ~100x faster than SSD, ~10,000x faster than HDD

**Push-back prompts:**
- "You assumed 1 KB per message. What about metadata, media URLs, timestamps?"
- "Recalculate with those added."
- "At 10K writes/sec with X storage, how long before you outgrow one disk?"

**Red flag:** Candidate waves away numbers. Force them to commit.

---

## Stage 3: API & Data Model (5-10 min)

Candidate proposes endpoints and schema.

**API shape:**
- REST / gRPC / GraphQL — why?
- Endpoint signatures (method, path, request, response)
- Pagination strategy (cursor / offset / page)
- Idempotency (especially for writes)
- Error model

**Data model:**
- Entities and their relationships
- Primary keys and access patterns
- What goes in SQL vs NoSQL vs KV vs search index
- Indexes and their cost

**Push-back prompts:**
- "Why REST over gRPC here?"
- "Why DynamoDB over Postgres? What access patterns drove that?"
- "Your schema has this join — at 1 billion rows, how does that perform?"
- "What's the primary key? What's the partition key? Do they match your access pattern?"

**Red flag:** Generic "use a database" without choice justification.

---

## Stage 4: High-Level Architecture (10-15 min)

Candidate describes components. Mentor draws the Mermaid diagram based on the candidate's description so they see their own design and spot gaps.

**Standard components to expect:**
- Client → CDN / edge
- API gateway / load balancer
- Service layer (monolith vs microservices — why?)
- Cache layer (where? Redis? what's cached?)
- Database(s) — primary + replica, sharded?
- Async / queue — when? what tech?
- Storage (blob, object store) — what goes there?
- Observability — how is this monitored?

**Push-back prompts:**
- "Walk me through a single write request end-to-end."
- "Walk me through a single read request end-to-end."
- "Where's the bottleneck in this design?"
- "What fails if the cache goes down?"

**Red flag:** Candidate hand-waves at components without connecting them.

---

## Stage 5: Deep Dives (10-15 min)

Pick 1-2 bottlenecks and push hard.

**Common deep-dive areas:**

### Caching
- What's the hit rate? How did you estimate it?
- Cache invalidation strategy?
- Thundering herd — what happens when the cache dies and 100K requests hit the DB?
- Cache-aside vs write-through vs write-back?

### Database sharding
- Shard key choice?
- Hot-spot risk?
- Cross-shard queries?
- Rebalancing strategy?
- Consistent hashing?

### Message queue
- At-least-once vs exactly-once?
- Dead letter queue?
- Backpressure — what happens when producers outpace consumers?
- Ordering guarantees?

### Consistency
- Strong vs eventual?
- Quorum reads/writes (N, R, W)?
- CAP trade-off articulation?
- What do users see during a failover?

### Availability
- Single points of failure?
- Failover strategy?
- Health checks?
- Circuit breakers?

**Push-back prompts:**
- "This component handles 50K writes/sec. How do you scale it? What fails first?"
- "Your cache dies at 2am on Black Friday. Walk me through what happens."
- "You need to add a new field to every record. How?"

---

## Stage 6: Trade-offs & Wrap-up (5 min)

Candidate summarizes key trade-offs in their design. Mentor adds anything missed.

**Key trade-offs to surface:**
- Consistency ↔ availability
- Latency ↔ throughput
- Cost ↔ performance
- Simplicity ↔ flexibility
- Build ↔ buy

**Push-back prompts:**
- "What would you build differently if you had 10x the budget?"
- "What's the first thing that would fail if usage doubled overnight?"
- "Six months after launch, what tech debt do you predict?"

---

## Interviewer Mode Checklist (for the mentor)

- [ ] Let the candidate drive. Don't solve for them.
- [ ] Push back on vagueness at every stage.
- [ ] Draw the diagram *after* they describe, not before.
- [ ] Pause the mock to teach if a fundamental gap blocks progress.
- [ ] Keep pace — don't let any stage run over.
- [ ] End with a concrete trade-off summary.
- [ ] Score the candidate privately on: clarifying, estimation, API/data, HLD, deep dives, communication.

---

## Common Candidate Mistakes

- Diving into architecture before clarifying requirements
- Vague on numbers, then architecture decisions can't be justified
- Picking technologies (Kafka, Cassandra, Redis) without connecting to requirements
- Not distinguishing read path from write path
- Ignoring failure modes
- Over-engineering for hypothetical scale
- Under-engineering for stated scale
- Can't articulate trade-offs — everything is "the best approach"

---

## Pacing Guide (45 min)

- 0-8 min: Requirements + clarification
- 8-15 min: Estimation
- 15-25 min: API + data model + high-level architecture
- 25-40 min: Deep dives (1-2)
- 40-45 min: Trade-offs + wrap-up

Adjust for 60 min interviews (more deep dives) or 30 min interviews (tighter everything).
