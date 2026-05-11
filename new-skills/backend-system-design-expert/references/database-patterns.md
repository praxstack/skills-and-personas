# Database Patterns

**When to load this file:** Load when doing schema design, query optimization, index design, partitioning, or sharding. Covers Postgres/MySQL patterns, NoSQL access patterns, and query tuning.

---

## Schema design (RDBMS)

### Primary keys

| Choice | When |
|---|---|
| `SERIAL` / `BIGSERIAL` | Single-writer DB, never need to merge shards, insertion order matters |
| UUIDv4 | Distributed inserts, but accept B-tree fragmentation and index bloat |
| UUIDv7 / ULID | Distributed inserts with time-ordered prefix — keeps B-tree locality |
| Snowflake-style | High-throughput distributed with ordered generation in application layer |

UUIDv4 as PK in a high-insert table destroys index cache locality. Use UUIDv7/ULID unless you have a specific reason.

### Indexes

- Create indexes to support query patterns, not out of habit. Every index costs on writes.
- Multi-column index order matters: `(a, b)` supports `WHERE a=?`, `WHERE a=? AND b=?`, not `WHERE b=?`.
- Covering index (index includes all selected columns) → index-only scan → skips table fetch.
- Partial index: `CREATE INDEX ON users(email) WHERE deleted_at IS NULL` — smaller, only when predicate is common.
- Unique index enforces uniqueness AND serves reads.
- `gin` for full-text, array membership, JSONB containment. `brin` for append-only time-series (tiny, fits in RAM).
- Never add an index without checking query plans — some queries ignore indexes (e.g., `WHERE lower(email) = ?` won't use index on `email` unless you create an expression index).

### Soft delete vs hard delete

- Soft delete (`deleted_at TIMESTAMP NULL`) — keeps audit trail, enables "undelete", but every query must filter `WHERE deleted_at IS NULL` or use a view.
- Hard delete — simple, reclaims space, but loses history. Pair with an `audit_log` table if history matters.
- Partial index on non-deleted rows avoids bloating the "active" index with tombstones.

### Constraints belong in the database

- `NOT NULL`, `CHECK`, `UNIQUE`, `FOREIGN KEY` — enforce in schema.
- Application-level validation is a convenience, not a guarantee. Two apps, one schema: the schema is the only truth.
- `ON DELETE CASCADE` vs `RESTRICT` is a policy choice — be explicit. Default to `RESTRICT` and think about each case.

---

## Query optimization

### EXPLAIN ANALYZE signals

- **Seq Scan** on a large table → likely missing index (or selective scan over the whole table where WHERE matches too many rows).
- **Index Scan** / **Index-Only Scan** → good, especially index-only.
- **Nested Loop** → OK for small outer inputs; bad if outer is large. Often an unindexed join.
- **Hash Join** → usually fine for larger inputs.
- **Rows estimate vs actual** dramatically off → statistics stale, run `ANALYZE`.
- **Sort** spilling to disk → `work_mem` too low, or query producing too much intermediate data.

### N+1 detection

- Review code for loops over query results that issue further queries. Use query log in dev to count queries per request.
- In ORMs: use eager-load / include / preload. Avoid "lazy" collections in hot paths.
- For GraphQL, DataLoader is mandatory (see `api-design.md`).

### Common anti-patterns

- `SELECT *` in application code — returning new columns breaks consumers silently; larger payload than needed.
- `SELECT COUNT(*)` for existence check — use `EXISTS(SELECT 1 …)`.
- Unbounded `ORDER BY created_at DESC` without `LIMIT`.
- Sub-queries in SELECT list — often an implicit N+1.
- `LIKE '%foo%'` — can't use B-tree index. Use full-text or trigram index.
- Implicit type casts — `WHERE id = '123'` where `id` is int may skip index.

### Batch writes

- `INSERT INTO t VALUES (...), (...), (...)` — one round trip, one WAL flush.
- Bulk update via `UPDATE t SET x = v.x FROM (VALUES ...) AS v(id, x) WHERE t.id = v.id`.
- `COPY` for bulk loads (Postgres) is 10-100x faster than individual INSERTs.

---

## Migrations (zero-downtime)

Schema changes in production follow this pattern:

1. **Add** new column/table, nullable or with default.
2. **Backfill** in batches (rate-limited, resumable). Monitor replication lag.
3. **Dual-write** from application: new code writes to both old and new.
4. **Dual-read / cutover** — new code reads from new; old code still reads from old.
5. **Drop** old column/table after all readers migrated and monitoring clean for N days.

Any step that requires a lock beyond milliseconds needs staging test first. Postgres: `ALTER TABLE ADD COLUMN` without default is instant; WITH default is a rewrite on old Postgres (pre-11).

Renames are expensive: prefer add-new + deprecate-old over rename.

### Rollback plan

Every migration has a reverse. If the reverse is destructive (e.g., dropping data), the migration is not rolled back — it's rolled forward with a new migration.

---

## Partitioning

Partitioning splits one logical table into physical partitions in the same DB.

- **Range:** `PARTITION BY RANGE (created_at)` — one partition per month/quarter. Drop old partitions as O(1) DDL instead of slow DELETE.
- **List:** `PARTITION BY LIST (region)` — partition per region. Good when queries filter by the partition key.
- **Hash:** `PARTITION BY HASH (user_id)` — even distribution, no locality benefit but balances writes.

Every query should include the partition key in the WHERE clause, or the planner must scan every partition (defeats the purpose).

---

## Sharding

Sharding splits data across physical databases. Do this when a single DB can't handle the write load or data size.

| Strategy | Pros | Cons |
|---|---|---|
| Range-based (`user_id 1-1M`) | Simple | Hotspots if keys are uneven |
| Hash-based (`hash(key) % N`) | Even distribution | Adding shards = rehashing everything (use consistent hashing to mitigate) |
| Directory-based (lookup table) | Flexible, per-tenant | Extra lookup, directory is a new SPOF |

**Cross-shard joins are expensive or impossible** — design to keep related data on the same shard (co-locate user + user's orders by `user_id`).

**Global uniqueness** is harder: use Snowflake/ULID IDs instead of per-shard sequences.

**Rebalancing** is the hardest operation — plan for it up front (consistent hashing, virtual shards).

---

## NoSQL patterns

### MongoDB (document)

- **Embed** 1-to-few, read-together data: addresses in user doc.
- **Reference** 1-to-many with large "many" side, or many-to-many: posts reference user, not embedded.
- Document size limit 16MB — long-growing arrays don't embed.
- Indexes behave like SQL: single, compound, unique, partial, text, geo.
- Compound index order matters identically to SQL.
- `$lookup` (join) exists but is slow vs co-located embed. Design schema around access pattern, not normalization.

### Redis (KV + structures)

- **String** — session, serialized JSON, counters (`INCR`).
- **Hash** — a single object's fields; cheaper than JSON round-trip when you update one field.
- **List** — queue (`LPUSH`/`RPOP`), timeline (cap with `LTRIM`).
- **Set** — unique-member collections, tag indexes, relationship lists.
- **Sorted set** — leaderboards, rate-limit windows, priority queues (`ZADD`/`ZRANGEBYSCORE`).
- **Stream** — durable append-only log; for pub-sub with consumer groups, prefer Kafka at scale.
- **HyperLogLog (`PFADD`/`PFCOUNT`)** — approximate unique count, constant memory.

Gotchas:
- Keys have no namespacing — use `domain:type:id` convention.
- `KEYS *` is O(N) and blocks — use `SCAN`.
- Eviction policy (`maxmemory-policy`) — `allkeys-lru` for cache, `noeviction` for primary store.
- Persistence modes (RDB/AOF) — cache should usually run without persistence.

### DynamoDB (single-table design)

- Design around access patterns first, not normalization. Every query knows its partition key.
- `PK`/`SK` + GSIs. Different item types share the same table: `PK=USER#123 SK=PROFILE`, `PK=USER#123 SK=ORDER#...`.
- `Query` (fast, uses PK) vs `Scan` (slow, reads whole table) — Scan is almost always wrong.
- Hot partitions are a real problem — design PK to distribute write load.
- Write-sharding pattern: suffix PK with `#0..#N` when one logical key takes too much throughput.
- Transactions (TransactWriteItems) limited to 100 items, single region.

---

## Connection pooling

- Every DB has a hard upper bound on connections. Postgres default is 100 — easily exhausted by naive app servers.
- Application pool + external pooler (PgBouncer) for Postgres — pooler shares connections across app processes.
- Pool size tuning: start with `connections ≈ (cores × 2 + effective_io)`, tune under load. Excess connections increase contention.
- Per-request / per-tenant pool accounting prevents one tenant from starving others.

## Replication

- Read replicas scale read throughput; lag is real (measure it, expose as metric).
- Writes always go to primary. Reading from a replica right after a write can see stale data.
- **Read-your-writes** — route requests for recently-mutated data to primary for a window, or use replica-lag token.
- Failover is not automatic in all setups — test it in staging.
