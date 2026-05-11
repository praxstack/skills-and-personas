# Testing Strategy, Patterns & Tools

**When to load this file:** Designing test strategy, picking tools, writing test plans, handling flaky tests, or managing test data.

## Test Pyramid — Interpret, Don't Worship

Classical pyramid: ~60% unit, ~30% integration, ~10% E2E. This is a default, not gospel.

**Adjust by architecture:**
- **Monolith with heavy business logic:** classical pyramid holds.
- **Microservices:** flatten toward integration + contract tests (Pact, Spring Cloud Contract). Unit tests within service, contract tests between.
- **Frontend SPA:** component tests (Testing Library) are the middle layer; E2E covers critical flows only.
- **Data pipelines:** golden-output tests dominate; schema tests, property-based tests for transforms.
- **ML systems:** behavioral tests (known inputs → expected ranges), metamorphic tests, data drift tests.

**Adjust by risk:**
- Payment, auth, PHI/PII → heavier integration + E2E; contract tests between boundaries.
- UI polish → lighter; snapshot tests + few E2E.
- Infrastructure-as-code → `terraform validate` + `plan` review + integration tests against real cloud in isolated account.

## Unit Testing Patterns

**Arrange / Act / Assert** — make the three phases visible, separate by blank line.

**One behavior per test.** If you need "and" in the test name, split it.

**Test names describe behavior, not code:**
- Bad: `test_user_service_create_user_1`
- Good: `createUser_hashes_password_before_saving` / `createUser_rejects_duplicate_email_with_409`

**Test doubles — match the collaboration style:**
- **Dummy:** placeholder, never used (fill required arg).
- **Stub:** returns canned values.
- **Spy:** stub that also records calls.
- **Mock:** verifies interactions against expectations. Prefer stubs; over-mocking tests implementation.
- **Fake:** working implementation with simpler semantics (in-memory DB).

**Rule of thumb:** mock at architectural boundaries (network, DB, external SDK). Don't mock within your own code — that tests the test, not the system.

**Parameterized tests** for boundary cases:
```python
@pytest.mark.parametrize("email", [
    "", "no-at", "@no-local", "no-domain@", "no-tld@host"
])
def test_invalid_email_rejected(email): ...
```

**Table-driven in Go:**
```go
for _, tt := range tests {
  t.Run(tt.name, func(t *testing.T) { ... })
}
```

## Integration Testing

**Scope:** multiple units working together, often with real DB, real HTTP framework, with external systems mocked only at the process boundary.

**Use a real database container** (Testcontainers, Docker Compose). SQLite-in-memory "close enough" is a lie for Postgres/MySQL-specific features (JSON, CTEs, locking semantics).

**Isolation strategy:**
- Clean between tests (truncate + reseed): slow but simple.
- Transaction rollback per test: fast, but doesn't test commit behavior.
- Unique IDs per test: fast, enables parallelism, complicates assertions.

Pick based on test suite size: small (<100) → clean between; medium → transaction rollback; large parallel CI → unique IDs.

**Contract tests between services** (Pact, Spring Cloud Contract): consumer defines expectation, provider validates it. Prevents "we changed the API and broke 3 downstream teams" incidents.

## E2E Testing

**Cypress vs Playwright:**
- **Playwright** (preferred for new): multi-browser (Chromium/Firefox/WebKit), parallel workers, auto-wait, more reliable locators, first-class TypeScript.
- **Cypress:** great DX, time-travel debugger, wide ecosystem. Single browser per run (kinda), struggles with iframes and some cross-origin.

**Key principles:**
- E2E tests only the most critical flows (signup → first-value, checkout, login). If you have 200 E2E tests, you have a testing problem.
- **Prefer semantic locators** (`getByRole`, `getByLabel`) over CSS selectors. Resilient to style changes.
- **Set up data via API, not UI.** Logging in through the UI in every test is slow and flaky. Use programmatic login (`cy.session()` in Cypress, storage state in Playwright).
- **Run against a controlled environment.** Reset state between tests (test-only endpoint to seed/clean DB).
- **Retry, but quarantine flakes.** One retry for transient issues; mark flaky tests with a bug tag and fix them — don't normalize failure.

## Flaky Tests — The Silent Killer

If tests fail randomly, engineers learn to ignore failures. Everything else in QA is undermined.

**Common causes + fixes:**
- **Timing-dependent (waits, sleeps):** replace `sleep(1000)` with `waitFor(element-visible)` or explicit state checks.
- **Shared mutable state:** isolate per-test data; use unique IDs; truncate between.
- **Non-deterministic ordering:** sort results before assertion.
- **Environment race:** container not ready when test starts — use healthchecks.
- **External services:** mock at the boundary; don't rely on third-party uptime.
- **Time-dependent:** inject a clock or use time-travel libraries (sinon fake timers, time-machine).
- **Flaky visual snapshots:** pin viewport + fonts + animation-off; use AI-diff tools (Chromatic) that understand noise.

**Process:**
1. Detect: flag any test that fails on retry (Buildkite, GitHub Actions plugins).
2. Quarantine: mark flaky, move to separate suite, keep running but don't block PRs.
3. Fix with urgency: flakes accumulate; don't let the quarantine grow.
4. Delete if the test can't be made reliable and isn't critical.

## Test Data Management

- **Factories** (FactoryBot, Faker) for generating valid domain objects — scales better than fixtures.
- **Fixtures** for well-known seeds (admin user, known products). Version with migrations.
- **Seed scripts** idempotent: running twice must not corrupt state.
- **Test-only endpoints** for reset/seed in staging/CI. Gated behind feature flag or env check. NEVER in prod.
- **Anonymized production data** for staging only after scrubbing PII with reliable tooling.

## Performance Testing — Types

**Load test:** expected traffic. Does the system handle it? Establish baseline.

**Stress test:** beyond expected. Find the breaking point. Understand failure mode (graceful degradation vs cliff).

**Spike test:** sudden huge traffic increase. Does autoscaling work? Does the cold-start matter?

**Soak test:** sustained load over hours. Memory leaks, resource exhaustion, queue growth.

**Capacity test:** progressive load to find max throughput at acceptable latency.

Tools:
- **k6** (JS-scripted, good for engineers), **Artillery** (YAML or JS, easy ramp), **Locust** (Python), **Gatling** (Scala/Java).
- **Thresholds assert SLOs:** p95 latency, error rate, throughput — fail the build if violated.

## Testing in CI/CD

**Pipeline stages:**
1. Lint + format (fast feedback).
2. Type check.
3. Unit tests (parallel).
4. Build (artifact).
5. Integration tests (against containers).
6. Security scans (SAST, SCA, secrets).
7. E2E on a staging deploy.
8. Performance tests (smoke or full).
9. Deploy to prod (canary → full).
10. Production smoke tests + monitoring verification.

**PR checks:** lint + unit + integration + security. E2E only on main or nightly unless critical path.

**Test parallelization:** sharding (split suite across N workers) is free speed. Ensure data isolation.

**Test reports:** JUnit XML for CI integration; coverage reports (lcov, cobertura) linked in PR.

## Testing Specific Concerns

**Concurrency / race conditions:**
- Use controlled clocks (inject time).
- Use thread/goroutine synchronization primitives to reproduce.
- Property-based testing (Hypothesis, fast-check, jqwik) for interleaving coverage.

**Idempotency:**
- Run the operation twice, assert state matches running once.
- Critical for webhooks, payment, sync operations.

**Migrations:**
- Test up AND down (rollback capability).
- Test on a production-shaped dataset in staging.
- Backward-compat: run new schema with old app; old schema with new app.

**Accessibility:**
- `@axe-core/playwright` or `jest-axe` integrated into CI.
- Snapshot focus order, announce text, ARIA roles.

**i18n/l10n:**
- Pseudo-localization (`Testing → [!!T€stïñg!!]`) catches truncation, encoding issues.
- RTL snapshot tests.
- Date/number formatting per locale.

## Mocking External Services

**Don't hit real third parties in tests.** Mock with:
- **MSW** (Mock Service Worker) for HTTP — intercepts at fetch level; same code in tests and dev.
- **nock / polly.js / VCR** — record-and-replay HTTP.
- **Stubs** per SDK (OpenAI stub, Stripe test mode).
- **Testcontainers** for things with Docker (Postgres, Redis, Kafka, MinIO).

For true integration, have a separate "contract tests against sandbox" suite that runs nightly.

## Common Test Smells

- **Tests that test the mock** — change implementation, test breaks, behavior unchanged.
- **Shared setup across tests** creating hidden coupling.
- **Assertions on implementation** (calling internal methods) — brittle.
- **`it('works')`** — useless test names.
- **Tests that pass when the code is broken** — run tests against broken code once to verify they fail.
- **Setup so complex it obscures intent** — extract helpers.
- **One giant test covering many cases** — split so failures localize.

## Coverage Signals

- **Line coverage:** easy to inflate. Look at branches.
- **Branch coverage:** every conditional path hit.
- **Mutation testing** (Stryker for JS, PIT for Java, mutmut for Python): mutate code, assert tests fail. Measures assertion quality, not just execution.
- **Cyclomatic complexity:** functions with complexity >10 deserve extra test coverage.

Target: high-risk modules >90% branch + mutation score >70%. Low-risk glue code can be 60%+.
