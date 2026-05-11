# API Design

**When to load this file:** Load when designing or reviewing API contracts — REST, GraphQL, or gRPC. Covers resource modeling, pagination, errors, versioning, auth, and rate limiting.

---

## REST — resource modeling

- URLs name resources (nouns), verbs are HTTP methods.
- `POST /orders` creates, `GET /orders/{id}` reads, `PATCH /orders/{id}` partial update, `PUT /orders/{id}` full replace, `DELETE /orders/{id}` removes.
- Sub-resources for ownership: `GET /users/{id}/orders`. Do not invent `/getUserOrders`.
- Use HTTP status correctly: 201 for create with Location header; 204 for delete with empty body; 409 for conflict; 422 for validation failure.
- PUT and DELETE are idempotent — clients may retry safely. POST is not; require an idempotency key for retry-safe creates.

## Error format (single source of truth across services)

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": [
      { "field": "email", "message": "Email format is invalid" }
    ],
    "requestId": "req_abc123",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

- `code` is machine-parseable, stable across versions.
- `message` is human-readable, safe to display.
- `details` optional, per-field.
- `requestId` correlates to logs/traces.
- Do not leak stack traces or internal paths.
- 5xx body does not contain internal details.

## Pagination

- **Offset pagination** (`?limit=20&offset=40`): simple, cacheable, but DB still scans skipped rows. Fine up to a few thousand rows. Show total count only if cheap.
- **Cursor pagination** (`?limit=20&cursor=opaque`): required for large/unbounded lists. Cursor encodes (sort key, tie-breaker). Opaque to clients; server owns encoding.
- Never return unbounded lists. Default page size 20-50, max 100.
- Include `hasMore` or `nextCursor`; absence indicates end.

## Versioning

- URL path versioning (`/v1/`, `/v2/`) is simplest and most-cached; pick it unless you have a reason.
- Header versioning (`Accept: application/vnd.myapi.v2+json`) is cleaner semantically but breaks naive caching and browser debugging.
- Query-param versioning is fragile — caches, proxies, and human errors strip query params. Avoid.
- Breaking changes require new major version + dual-serve window (≥3 months typical).
- Add fields: not breaking (clients ignore). Remove or rename fields: breaking.
- Change semantics of a field (units, meaning, nullability): breaking.

## Filtering, sorting, field selection

- Filter: `GET /users?status=active&role=admin`. Combine with AND.
- Sort: `?sort=-createdAt,name` — leading `-` = desc.
- Sparse fieldset: `?fields=id,name,email` (reduces payload but complicates caching).
- Full-text search: `?q=...` or `?search=...`, one param name, consistent across resources.

## Authentication

- **Session cookies** for browser apps: `HttpOnly`, `Secure`, `SameSite=Lax` or `Strict`, short lifetime + refresh.
- **Bearer tokens (JWT)** for APIs and mobile: access token short (15m), refresh token long (7-30d) stored securely (Keychain/Keystore), not localStorage in browsers.
- **mTLS** or signed service tokens for service-to-service.
- Never put secrets in URL query string (proxies log them).
- Rotate signing keys with overlapping validity windows; don't flag-day.

## Authorization (RBAC / ABAC)

- Authorize per-resource, not just per-endpoint. `GET /orders/{id}` must check that the requester owns or has grant for order `{id}`.
- Two checks, always: authenticated (who) + authorized (what can they do to this specific resource).
- Wildcard permissions (`orders:*`) save config at admin layer but make audit harder — use sparingly.
- Never trust client-supplied user ID — derive from the auth token.

## Rate limiting

- Token-bucket (steady rate + burst) is typical. Sliding-window for stricter fairness.
- Per-key (API key, user ID, IP) not just global.
- Return `429 Too Many Requests` with `Retry-After` header and `X-RateLimit-*` counters.
- Store counters in Redis (atomic INCR + EXPIRE) or use a managed rate limiter.
- Tier limits (free vs paid) belong in config, not code.

## Idempotency keys (required on retryable writes)

- Client sends `Idempotency-Key: <uuid>` header.
- Server stores `key → response` for a window (24h typical).
- On repeat, return cached response; do not re-execute side effects.
- Key is scoped per-endpoint + per-user to avoid collision.

---

## GraphQL — schema-first

- Schema is the contract. Generate types for clients, don't maintain them by hand.
- Define `input` types for mutations, separate from query types.
- Use `!` (non-null) deliberately — over-use causes null-propagation surprises; under-use pushes null-checking to every client.

## N+1 problem

The default "resolve posts for each user" walks the DB per-user. Mandatory defense:

- **DataLoader** per request: batches IDs within one tick, de-dupes, caches per-request.
- Resolvers take `(parent, args, context)` where `context` holds loaders.

```typescript
const postsByUserLoader = new DataLoader(async (userIds) => {
  const posts = await db.posts.findMany({ where: { authorId: { in: userIds } } });
  return userIds.map(id => posts.filter(p => p.authorId === id));
});

const resolvers = {
  User: { posts: (user, _, ctx) => ctx.postsByUserLoader.load(user.id) }
};
```

Without DataLoader, do not ship GraphQL — you've signed up for production outages.

## Connection pagination (Relay spec)

- `first`/`after` and `last`/`before`.
- Returns `{ edges: [{ node, cursor }], pageInfo: { hasNextPage, hasPreviousPage, startCursor, endCursor }, totalCount }`.
- `totalCount` is optional and often omitted for performance.

## Depth and complexity limiting (mandatory)

- Depth limit (e.g., 10) prevents `posts { author { posts { author { ... } } } }` blowup.
- Complexity limit (e.g., 1000) assigns cost per field; rejects queries whose total exceeds budget.
- Without these, GraphQL is a DoS vector.

## Errors in GraphQL

- Partial results + `errors` array. Clients must handle both.
- Use `extensions.code` for machine-parseable category (`NOT_FOUND`, `FORBIDDEN`, `VALIDATION`).
- Never return raw stack traces in `extensions`.

---

## gRPC — protobuf patterns

- Service methods return a message or stream of messages. Streaming (server, client, bidi) for large/ordered results.
- Add fields with new field numbers — never reuse retired numbers (protobuf wire-format backwards compat depends on this).
- Deprecate fields with `[deprecated = true]`, keep for one major cycle.
- Use `google.protobuf.Timestamp` for times, `Duration` for intervals, `Empty` for void returns.
- Always configure deadlines (client side) — gRPC hangs forever otherwise.

```protobuf
service UserService {
  rpc GetUser(GetUserRequest) returns (User);
  rpc ListUsers(ListUsersRequest) returns (ListUsersResponse);
  rpc StreamUsers(StreamUsersRequest) returns (stream User);
  rpc UploadData(stream DataChunk) returns (UploadResponse);
  rpc Chat(stream ChatMessage) returns (stream ChatMessage);
}
```

## Interceptors

- Auth (extract metadata → verify token).
- Logging + correlation ID propagation (`trace-id` from incoming, pass to outgoing).
- Error mapping (domain errors → gRPC status codes).
- Retry with exponential backoff on retriable status codes only (`UNAVAILABLE`, `DEADLINE_EXCEEDED`, not `INVALID_ARGUMENT`).

## Status codes (not HTTP codes)

- `OK`, `CANCELLED`, `UNKNOWN`, `INVALID_ARGUMENT`, `DEADLINE_EXCEEDED`, `NOT_FOUND`, `ALREADY_EXISTS`, `PERMISSION_DENIED`, `UNAUTHENTICATED`, `RESOURCE_EXHAUSTED`, `FAILED_PRECONDITION`, `ABORTED`, `UNAVAILABLE`, `INTERNAL`, `UNIMPLEMENTED`.
- Map carefully: `UNAVAILABLE` retries, `FAILED_PRECONDITION` does not.

---

## Input validation

- Validate at the API boundary; do not trust middleware to have done it.
- Use a schema library (Zod, Pydantic, protobuf with constraints) — don't hand-roll per-field.
- Reject unknown fields when payload shape is fixed.
- Size limits per field and overall payload.
- Format validation (email, URL, UUID) — don't just check "is string".

```typescript
const createUserSchema = z.object({
  name: z.string().min(2).max(50),
  email: z.string().email(),
  age: z.number().int().min(18).max(120),
  role: z.enum(['admin', 'editor', 'viewer']).optional()
});
```

## CORS

- Never `Access-Control-Allow-Origin: *` with `Access-Control-Allow-Credentials: true` — browsers refuse the combo anyway.
- Explicit allow-list per origin.
- Preflight caching (`Access-Control-Max-Age`) to reduce OPTIONS hit.
