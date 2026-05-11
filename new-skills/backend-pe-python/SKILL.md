---
name: backend-pe-python
description: 'Principal-engineer-grade Python backend design, implementation, and review. Covers asyncio, FastAPI/Django, SQLAlchemy, Pydantic, type hints, packaging, and Python-specific failure modes (GIL, blocking-in-async, subprocess, multiprocessing). Use when designing, building, reviewing, refactoring, hardening, profiling, or debugging Python services, APIs, workers, and data pipelines in production. Trigger keywords - Python backend, FastAPI, Django, asyncio, SQLAlchemy, Pydantic, uvicorn, gunicorn, aiohttp, Celery, Python service review, Python API design, Python performance, blocking event loop, GIL contention. Not for Python ML/training code (use backend-pe-python-ml) or pure frontend work.'
---

# Python Backend Principal Engineer

**Audience:** Engineers designing, building, reviewing, or hardening Python backend services, APIs, and data pipelines.

**Goal:** Principal-engineer-grade Python code - correct, reliable, secure, observable, operable, and scalable - with Python-specific failure modes explicitly handled.

## Priority Model

Correctness - Reliability - Security - Performance - Observability - Data consistency - Scalability - Developer experience. In that order. Never trade down.

## Core Principles

1. **Async is infectious - and it's a typed contract.** Calling a blocking function inside an `async def` corrupts the entire event loop. `requests`, `psycopg2` (sync), `time.sleep`, CPU-bound loops, file I/O without `aiofiles` - all forbidden in async handlers. Use `asyncio.to_thread` for unavoidable sync calls. If the codebase mixes sync and async, draw the boundary explicitly and do not cross it casually.

2. **Pydantic at every boundary, dataclasses inside.** `BaseModel` for every API input/output, event payload, config, and external-call result. Internal domain objects use `@dataclass(slots=True, frozen=True)` or `attrs` for cheap construction. `dict[str, Any]` crossing a function signature is a design smell.

3. **Type hints are not documentation, they are the contract.** Strict `pyright` or `mypy --strict` on the service surface and core domain. `Any`, bare `dict`, bare `list`, `Optional` without check, and `# type: ignore` without reason are code smells. Protocols over ABCs. `typing.assert_never` in exhaustive matches.

4. **The GIL is still here.** Threads help I/O, not CPU. For CPU-bound work use `multiprocessing`, `concurrent.futures.ProcessPoolExecutor`, or shell out to a native library (NumPy, Polars, Rust extension). Free-threaded Python (3.13t) is an experiment, not a plan.

5. **Package and deploy deterministically.** Lockfile in source control (`uv.lock`, `poetry.lock`, `pip-compile`). Pinned base image. Immutable tags. No `pip install` at container start. Reproducible builds or it doesn't exist.

6. **The DB driver is the bottleneck.** Async SQLAlchemy 2.0 with a real async driver (`asyncpg`, `aiomysql`). Connection pool sized to (worker count * concurrent queries per worker), not larger - an oversized pool starves the database. `pool_pre_ping=True`, `pool_recycle` under the DB's idle timeout.

## Decision Framework

**FastAPI vs. Django.** FastAPI for APIs, async-first services, ML serving, webhooks. Django when you need admin, ORM-heavy CRUD, opinionated batteries, and sync is acceptable. Django + async is possible but not the happy path - don't adopt it for new async-heavy services.

**SQLAlchemy vs. raw SQL / query builder.** SQLAlchemy 2.0 async Core (not the legacy 1.x ORM) for most services. Raw SQL via `asyncpg` when you need the last 20% of performance or a feature the ORM doesn't expose (window functions with advanced framing, partial indexes with expressions). Never hand-concatenate SQL strings.

**Pydantic v1 vs. v2.** v2 always for new code. v1 is legacy. If migrating, use the `pydantic.v1` compatibility shim to move one model at a time.

**Threads vs. processes vs. asyncio.** asyncio for I/O-bound concurrency. Processes for CPU-bound. Threads only for I/O when asyncio isn't usable (legacy sync code you can't rewrite). Never mix all three casually - pick one axis per service.

**Celery vs. asyncio task vs. a real queue.** Celery for existing codebases. For new services: RQ for simple cases, Arq for async-native, or Kafka/SQS + workers for anything requiring durability and scale. Avoid `asyncio.create_task` for work that must survive a pod restart - it will not.

**uv vs. poetry vs. pip-tools.** uv for new projects (10-100x faster, drop-in lockfile). Poetry for existing projects already on it. pip-tools for minimal tooling. Never `pip install` into a requirements file by hand.

## Anti-Patterns

- **`requests` inside `async def`.** Blocks the event loop. Use `httpx.AsyncClient` or `aiohttp`.
- **Creating a new `httpx.AsyncClient` per request.** TCP handshake + connection pool wasted. One client per service, lifespan-managed.
- **`except Exception: pass` / bare `except:`.** Hides bugs, corrupts state, breaks observability. Name the exception.
- **Mutable default arguments.** `def f(x=[])` - the list is shared. Use `None` sentinel.
- **`os.environ.get("X")` scattered in code.** Config is read once at boot into a typed `Settings` (pydantic-settings). Re-reading at runtime is a bug.
- **Logging with f-strings.** `logger.info(f"{user=}")` evaluates always. Use `logger.info("user", extra={"user": user})` and redact PII in the formatter.
- **`datetime.now()` without tz.** Always `datetime.now(tz=timezone.utc)`. Store UTC. Use `time.monotonic()` for durations.
- **`random.random()` for tokens, IDs, or anything security-adjacent.** Use `secrets`.
- **Subclassing `Thread` / `Process` instead of composing.** Awkward lifecycle, bad testability. Use `concurrent.futures`.
- **`eval` / `exec` / `pickle` on untrusted input.** RCE. Use `json`, `msgpack`, Protobuf.
- **Globals holding state.** Breaks testing and concurrency. Dependency injection via FastAPI `Depends` or a container.
- **`@app.on_event("startup")` in new FastAPI code.** Deprecated. Use `lifespan` context manager.
- **`asyncio.gather` with unbounded concurrency.** Fans out to thousands of concurrent DB queries. Use `asyncio.Semaphore` or a bounded `TaskGroup`.
- **Relying on CPython reference counting for cleanup.** File handles, DB connections - use `with`/`async with` explicitly.

## Standard Workflow

1. **Clarify SLOs** - P50/P95/P99 latency, error budget, peak QPS, payload sizes, dependencies' SLAs.
2. **Map dependencies** - what DBs, queues, external APIs; their failure modes; their idempotency guarantees.
3. **Choose the async boundary** - fully async service or sync service; if mixed, draw the line and enforce it.
4. **Define contracts** - Pydantic models for request/response/events, OpenAPI generated from them, explicit error responses.
5. **Implement with safe defaults** - lifespan-managed clients, per-dependency timeout, bounded retries, structured logging with `structlog` or stdlib + JSON formatter, OpenTelemetry auto-instrumentation, `slowapi` or equivalent rate limit, CORS locked to known origins.
6. **Test at every level** - pytest + `pytest-asyncio` + `anyio`, Testcontainers for Postgres/Redis/Kafka, contract tests for APIs, `locust` or `k6` for load, `hypothesis` for property tests on pure logic.
7. **Profile before optimizing** - `py-spy` for CPU, `memray` for memory, `asyncio.debug` + `PYTHONASYNCIODEBUG=1` for async issues.
8. **Pre-mortem + runbook** - top failure modes, detection signals, mitigation steps.

## Default Stack (2026 baseline)

- Python 3.12 or 3.13 (3.11 acceptable; avoid <= 3.10 for new code).
- Framework: FastAPI (default), Django (admin-heavy monoliths), Starlette (library-level), Litestar (opinionated async).
- Server: `uvicorn` with `--workers` under a process manager (Gunicorn with `uvicorn.workers.UvicornWorker`, or systemd, or direct in Kubernetes).
- Data: SQLAlchemy 2.0 async + `asyncpg`; Alembic for migrations; `redis-py` async; `aiokafka` or `confluent-kafka` for Kafka.
- Validation: Pydantic v2.
- Clients: `httpx` with `AsyncClient`, connection pooling, timeouts, retries via `tenacity` or `stamina`.
- Workers: Arq, Celery (legacy), Dramatiq, or raw Kafka/SQS consumers.
- Observability: OpenTelemetry SDK + `opentelemetry-instrumentation-*` packages, `prometheus-client`, `structlog`.
- Testing: pytest, pytest-asyncio, Testcontainers, hypothesis, respx (HTTP mocking).
- Tooling: `uv` (package + venv), `ruff` (lint + format), `pyright` (types), `pre-commit`.

## Deliverables Contract

- Type-checked code (`pyright` strict on service surface) with Pydantic v2 contracts.
- `pyproject.toml` with pinned dependencies and a lockfile.
- Multi-stage Dockerfile, non-root user, `python -m` invocation, healthcheck endpoint.
- `alembic` migrations with `downgrade` populated.
- OpenAPI spec generated from code.
- OpenTelemetry wired (traces + metrics + logs).
- Structured logging with PII redaction.
- Timeouts on every outbound call; bounded retries with jitter; idempotency for writes.
- Graceful shutdown via FastAPI `lifespan`.
- Tests: unit, integration with Testcontainers, contract, load.
- Runbook for top-N failure modes.

Quality gates: no blocking call in async path, no `dict[str, Any]` at public boundaries, no `# type: ignore` without justification, no bare `except`, no secrets in logs, connection pool sized and documented, all outbound calls timed, all writes idempotent or explicitly marked non-retriable.
