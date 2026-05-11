# Caching Strategies

**When to load this file:** Load when designing or reviewing cache layers — policy selection, invalidation, stampede protection, Redis patterns, CDN interaction.

---

## Strategy selection

| Pattern | Read | Write | Freshness | Use when |
|---|---|---|---|---|
| Cache-aside (lazy) | App reads cache, miss → reads DB, writes cache | App writes DB; invalidates/updates cache | Slightly stale until invalidation | Read-heavy, tolerant of short staleness |
| Read-through | Cache auto-loads on miss (provider-backed) | App writes DB; cache invalidates | As above | Cache sits in library/provider, simpler app code |
| Write-through | Reads from cache | Writes go to cache AND DB synchronously | Fresh | Must-be-fresh, write latency acceptable |
| Write-behind (write-back) | Reads from cache | Writes to cache; async flush to DB | Fresh read, durability risk | Write-heavy, can tolerate loss window |
| Refresh-ahead | Reads from cache | Cache proactively re-fetches near expiry | Fresh, predictable | Hot keys with known demand |

**Default:** cache-aside with TTL + stampede protection. Simple, well-understood, easy to reason about failures.

---

## Invalidation (the hard problem)

Pick an invalidation strategy deliberately:

- **TTL only** — data refreshes on expiry. Always stale up to TTL. Works for catalog, prices, settings where "a few minutes old" is fine.
- **TTL + explicit invalidation on write** — writer publishes invalidation event, readers respect. Combines bounds with point-in-time correctness.
- **Versioned keys** — include version or generation in key (`user:123:v7`); write bumps version. Old values age out naturally.
- **Event-driven pub/sub** — DB change feed → cache invalidation. Requires reliable change capture (Debezium, DynamoDB Streams, Postgres logical replication).

**Write-through** sidesteps invalidation at the cost of write latency.

**Cache coherence across multiple caches** (per-service local caches) is very hard. Prefer a shared cache (Redis) or accept eventual convergence.

---

## Cache stampede (thundering herd)

When a hot key expires, every concurrent reader triggers a DB fetch simultaneously. Origin gets hit hard, often brownout.

**Mitigations:**

1. **Singleflight / request coalescing** — first miss takes the lock, others wait for the result. Many libraries offer this.
2. **Probabilistic early expiration** — each reader independently decides to refresh before TTL with small probability proportional to remaining TTL.
3. **Lock-based refresh** — first miss sets a refresh lock, recomputes, others serve stale.
4. **Two-tier TTL** — "soft" TTL triggers refresh in background; "hard" TTL blocks reads.

Without one of these, cache-aside is a latent outage.

---

## Negative caching

Cache misses matter too. If a key doesn't exist in DB and every miss costs a query, the miss is a DoS vector.

- Cache the "not found" result with a short TTL.
- Watch for key-enumeration attacks — bloom filter in front of cache, or rate-limit miss rate per client.

---

## TTL selection

- Too long → staleness complaints, inconsistency bugs.
- Too short → high origin load, cache-hit rate tanks.
- Start with "max staleness the product can tolerate", shorten only if proven issue.
- Add jitter to TTL to prevent synchronized expiry across keys.

## Key naming

- Include a version prefix: `v2:user:123:profile` — bump on schema change to invalidate everything.
- Namespace by service + type + id: `orderservice:order:456:summary`.
- Include locale, currency, variant in key if response varies: `product:123:en-US:USD`.
- Avoid keys derived from user input without sanitization — key injection is a thing.

---

## What to cache — and what not to

**Cache:**
- Expensive computations (rendering, aggregations).
- Remote API responses with known rate limits.
- DB results that are read far more than written.
- Session data.
- Rendered fragments / pages with low personalization.

**Don't cache:**
- Per-user data under low re-access (one-shot data).
- Rapidly changing data with strict freshness.
- Sensitive data in shared caches without proper isolation.
- Unbounded result sets — the cache becomes as big as the DB.

**Consider if cache actually helps:** If the hit rate is below ~50%, you're paying the overhead and gaining little. Measure before adding.

---

## Redis patterns per data structure

| Structure | Use case |
|---|---|
| String | JSON blob, counter, session blob |
| Hash | Object with independently-updatable fields |
| List | FIFO queue (`LPUSH`/`RPOP`), timeline (`LTRIM` to cap) |
| Set | Unique membership (tags, relationships), set ops |
| Sorted set | Leaderboards, priority queues, rate-limit windows (score = timestamp) |
| Stream | Durable append log, consumer groups |
| Bitmap | Daily actives (`SETBIT` per user-day, `BITCOUNT`) |
| HyperLogLog | Approximate unique count at constant memory |
| Geo | Location-based queries (`GEOADD`, `GEOSEARCH`) |

### Gotchas

- Keys are a flat namespace — convention-namespace with `type:id:subfield`.
- `KEYS *` is O(N) and blocks — use `SCAN` with cursor.
- Single-threaded command execution — long Lua scripts block everything.
- Persistence (RDB/AOF) is optional; a cache Redis should usually run without persistence. A "primary storage" Redis needs AOF with `appendfsync everysec` at minimum.
- Memory: set `maxmemory` + eviction policy (`allkeys-lru` for cache, `noeviction` if you want writes to fail rather than evict). Without this, OOMs.
- Replication lag real; `WAIT` command forces a minimum replica count before ack.
- Cluster mode: keys in same slot for multi-key ops — use hash tags `{user:123}:orders` and `{user:123}:profile` to co-locate.

### Rate limiting with sorted set

```
Key: rl:<user_id>
Op (per request):
  ZADD key <now> <unique_id>
  ZREMRANGEBYSCORE key 0 <now - window>
  ZCARD key   # count in window
  EXPIRE key <window seconds>
If ZCARD > limit → reject 429
```

Atomic via Lua script to prevent races.

---

## Multi-layer caching

Common stack:

1. **Browser / client cache** (HTTP caching headers).
2. **CDN / edge cache** (Cloudflare, CloudFront, Fastly) — shared across all users near the edge.
3. **Application cache** (Redis) — shared across app instances.
4. **In-process cache** (local memory, `lru-cache`) — per-instance, fastest, small.
5. **Database buffer pool** — last line.

Each layer has different invalidation semantics. In-process caches can't be invalidated centrally — keep TTL short and accept drift.

### HTTP caching headers (for CDN/browser)

- `Cache-Control: public, max-age=3600` — 1 hour cache.
- `Cache-Control: private, max-age=0, must-revalidate` — browser only, always revalidate.
- `ETag: "hash"` + `If-None-Match` — 304 Not Modified on match, saves bytes.
- `stale-while-revalidate=86400` — serve stale while refreshing in background (good for CDN).
- `Vary: Accept-Language, Authorization` — cache separately per header value; over-use kills hit rate.

### CDN purge vs versioned URLs

- **Purge** — tell CDN to drop a key. Propagation delay (seconds to minutes). Good for small changes.
- **Versioned URLs** — `/static/app.a7f3.js` — deploy = new hash = new URL. Never stale, caches forever. Preferred for assets.

---

## Cache consistency models for multi-region

- **Per-region cache with cross-region pubsub** — invalidation broadcast, each region's cache drops key. Minutes of skew possible.
- **Anti-entropy sweep** — periodic consistency check, fix drift. Last line of defense.
- **Don't try to keep caches globally strongly consistent.** Accept region-local correctness with bounded staleness.

---

## Observability for caches

- Hit rate per key pattern / per route.
- Miss rate.
- Evictions per second (high = undersized cache or TTL too long).
- Latency p99 on cache ops.
- Origin load before vs after caching (the whole point — measure it).
- Stampede events (coalesced requests per key).

Without metrics, you have no idea whether the cache is helping or hurting.
