# CI/CD Pipelines

**When to load this file:** Load when designing or reviewing CI/CD pipelines. Covers pipeline stages, security gates, image building, progressive delivery, rollback, and artifact/secrets patterns.

---

## Pipeline stages (mandatory gates)

1. **Lint / format** — fast feedback; < 30s.
2. **Unit tests** — < 5min typical; run on every commit.
3. **Integration tests** — with ephemeral DB/Redis; < 15min.
4. **Static security analysis** — SAST (Snyk, Semgrep, CodeQL).
5. **Dependency scan** — SCA (Snyk, Dependabot, Trivy).
6. **Build artifact** — container image, tagged with immutable ID (git SHA or semver).
7. **Container scan** — Trivy, Grype, or registry-native scanner. Fail on Critical/High CVEs.
8. **Sign image** — cosign or Notation. Policy engine verifies on deploy (Sigstore Policy Controller, Kyverno).
9. **Push to registry** — ECR, GCR, GHCR, Artifactory.
10. **Deploy to staging** — automatic.
11. **Smoke + end-to-end tests** in staging.
12. **Deploy to production** — manual approval OR progressive rollout with metric gates.
13. **Post-deploy verification** — smoke test, SLO check over N minutes, auto-rollback if regressed.

Stages 1-5 block PR merge. Stages 6-13 run on main after merge.

---

## Branch and merge strategy

- **Trunk-based** — short-lived feature branches, PRs, merge to `main`, deploy from `main`. Preferred for most teams.
- **GitFlow** — release branches, hotfix branches. Heavier; appropriate for versioned products with long support windows.
- Release tags (`v1.2.3`) for traceability. Git SHA for immutable deploy reference.
- Require green CI + ≥1 approving review + no unresolved comments to merge.

---

## Image build patterns

### Dockerfile hygiene

- Multi-stage: build stage installs deps and compiles; runtime stage copies only artifact.
- Pin base image by digest (`FROM node:20-alpine@sha256:...`), not just tag.
- Non-root user (`USER 1000:1000`).
- No secrets in layers — use build-time mounts or build-args never baked into final stage.
- `.dockerignore` to exclude node_modules, tests, docs, `.git`.
- `HEALTHCHECK` for plain Docker runtimes; K8s uses probes instead.
- Smallest viable base: `distroless` or `alpine`, not `ubuntu:latest` (smaller attack surface + faster pulls).

### Tagging

- **Immutable tag** per build — git SHA (short or long). Required for reproducibility and rollback.
- **Aliases** — `latest`, `staging`, `production` — move across immutable tags. Never deploy from alias in prod.
- Retention: keep last N tags per service + all tags actively running in any env.

### Build caching

- Order Dockerfile instructions from least-changing (deps install) to most-changing (source copy). Max cache reuse.
- CI cache mount for package managers (`npm ci`, `pip install`, `go mod download`).
- Registry cache (`--cache-from`, `--cache-to`) across runners.

---

## Progressive delivery

### Rolling (K8s default)

- `maxSurge: 1 / maxUnavailable: 0` — over-provision by 1, never under.
- Brief window of mixed versions in prod. Must tolerate it (backward-compatible APIs, schemas).
- Rollback: `kubectl rollout undo` — moves to previous replicaset.

### Blue/Green

- Two identical environments. Traffic switches all-at-once via LB / Service selector / Ingress.
- Zero mixed-version window. Costly — 2x infra during transition.
- Rollback: flip traffic back. Instant.

### Canary

- Deploy new version to a small fraction (5%). Compare metrics vs stable (error rate, latency). Promote in stages.
- Tools: Argo Rollouts, Flagger, service mesh traffic splitting (Istio, Linkerd).
- Metric gates: promote only if error rate ≤ stable + tolerance, p99 latency within tolerance.
- Requires **comparable traffic** — hash-based routing (by user ID) beats random for variance.

### Feature flags

- Decouple deploy from release. Deploy dark; enable per-cohort at runtime.
- Tools: LaunchDarkly, Unleash, Split, in-house.
- **Flag debt** — every flag has an expiry date and a cleanup ticket. Expired flags force cleanup.
- Test both branches in CI (one canary build flag on, one off, both pass).

---

## Rollback

Every release must have a tested rollback. Types:

- **Image rollback** (stateless) — `kubectl set image ...:<previous-sha>` or `helm rollback`. Seconds.
- **Schema rollback** — only if migration is reversible (see database-patterns: zero-downtime migrations). Often not reversible; roll forward with a fix.
- **Data rollback** — restore from backup. Usually last resort, has RPO loss.
- **Feature flag flip** — instant mitigation if the change is behind a flag.

Rollback criteria defined in runbook:
- Error rate > X% sustained Y minutes.
- p99 latency > Z sustained Y minutes.
- SLO burn rate > 14.4x (fast burn, will exhaust monthly budget in 2h) — page + auto-rollback.

---

## Example pipeline (GitHub Actions)

```yaml
name: CI/CD

on:
  push: { branches: [main, develop] }
  pull_request: { branches: [main, develop] }

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres: { image: postgres:15, env: { POSTGRES_PASSWORD: postgres }, ports: ["5432:5432"] }
      redis: { image: redis:7, ports: ["6379:6379"] }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "npm" }
      - run: npm ci
      - run: npm run lint
      - run: npm test -- --coverage
      - uses: codecov/codecov-action@v3

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: snyk/actions/node@master
        env: { SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }} }
      - uses: aquasecurity/trivy-action@master
        with: { scan-type: fs, severity: CRITICAL,HIGH, exit-code: "1" }

  build:
    needs: [test, security]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    permissions: { id-token: write, contents: read }
    outputs:
      image: ${{ steps.build.outputs.image }}
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE }}   # OIDC, not static keys
          aws-region: us-east-1
      - uses: aws-actions/amazon-ecr-login@v2
        id: ecr
      - id: build
        run: |
          IMG=${{ steps.ecr.outputs.registry }}/myapp:${GITHUB_SHA}
          docker build -t $IMG .
          trivy image --exit-code 1 --severity CRITICAL,HIGH $IMG
          cosign sign --yes $IMG
          docker push $IMG
          echo "image=$IMG" >> $GITHUB_OUTPUT

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - run: aws eks update-kubeconfig --name staging-eks
      - run: kubectl set image deployment/myapp myapp=${{ needs.build.outputs.image }}
      - run: kubectl rollout status deployment/myapp --timeout=5m
      - run: curl -f https://staging.myapp.com/health

  deploy-prod:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production   # GitHub env gate = manual approval
    steps:
      - run: aws eks update-kubeconfig --name production-eks
      - run: kubectl set image deployment/myapp myapp=${{ needs.build.outputs.image }}
      - run: kubectl rollout status deployment/myapp --timeout=10m
      - run: ./scripts/smoke-test.sh https://myapp.com
```

Key properties:
- OIDC to cloud (no static keys in CI secrets).
- Security scan gate on merge AND on image.
- Image immutable (git SHA), signed.
- Staging before production.
- Manual approval via GitHub environment on prod.

---

## Secrets in CI

- Use OIDC trust between CI and cloud (AWS STS, GCP Workload Identity Federation) — no static keys.
- Mask secret values in logs (most CIs do automatically — verify).
- Scope secrets per environment (staging secret ≠ production secret).
- Rotate secrets on a schedule; alert on age.
- Never print secrets in scripts — `set +x` around the section.

---

## Ephemeral environments

For each PR, spin up a preview env:
- Namespace per PR in a shared cluster (lower cost than per-PR cluster).
- Subdomain per PR (`pr-123.preview.myapp.com`).
- Auto-destroy on PR close or after 7 days idle.
- Share infra dependencies (DB, Redis) where possible; isolate data with schema-per-PR or prefix-per-PR.

Enables product review on real environment before merge.

---

## Monorepo vs polyrepo pipelines

- **Monorepo:** path filters to run only affected projects' pipelines. Tools: Nx, Turborepo, Bazel. Requires discipline to keep CI tractable.
- **Polyrepo:** one pipeline per repo. Cross-repo changes span PRs — coordination cost.

Neither is free. Default to the team's existing shape unless the cost is concrete.

---

## Common failures

- **Flaky tests** — quarantine and track, don't ignore. Flaky test in CI = ignored CI = no CI.
- **Slow pipeline** — parallelize stages, cache deps, split heavy tests into suite groups with parallel runners.
- **"Works in CI, fails in prod"** — environment drift; minimize. Use same container image from CI in prod (don't re-build).
- **Silent gate failures** — ensure every job has `continue-on-error: false` (default) unless intentionally non-blocking.
- **No rollback tested** — rollback plan that never executed is not a rollback plan. Practice in staging.
