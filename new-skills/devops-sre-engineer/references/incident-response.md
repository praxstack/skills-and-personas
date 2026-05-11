# Incident Response, DR, and Postmortems

**When to load this file:** Load during an incident, when designing on-call/runbook/postmortem practices, or when planning DR and chaos engineering. Covers severity ladder, incident roles, runbook structure, postmortem template, RTO/RPO planning, and backup/failover patterns.

---

## Severity ladder

| Severity | Definition | Response |
|---|---|---|
| Sev-1 | Full outage or data-loss risk for critical path; all users affected; SLA at risk | Page immediately; Incident Commander; status page; war room |
| Sev-2 | Partial outage or major degradation; subset of users affected; SLO burning | Page primary; investigation within 15min |
| Sev-3 | Minor degradation, no user-visible impact yet, but trending wrong | Ticket, investigate within business hours |
| Sev-4 | Cosmetic, informational, nuisance alert | Ticket, fix as capacity permits |

Criteria must be precise, not subjective. "User-facing" defined; "critical path" listed; "SLA at risk" tied to error budget burn.

---

## Incident roles (for Sev-1 / Sev-2)

- **Incident Commander (IC)** — runs the incident. Does not debug. Coordinates, makes decisions, maintains timeline, owns comms.
- **Operations Lead** — debugs and drives mitigation. Reports to IC.
- **Comms Lead** — external communication (status page, customer-facing updates). Internal stakeholder updates.
- **Scribe** — timeline record, decisions, hypotheses, actions. Feeds postmortem.

For smaller incidents, one person may hold multiple roles. Sev-1 requires separation.

---

## Incident flow

1. **Detect** — alert fires OR customer report OR monitoring anomaly.
2. **Acknowledge** — on-call acks within paging SLA (5 min typical).
3. **Triage / declare** — set severity, open incident channel, page additional roles if Sev-1/2.
4. **Mitigate** — stop the bleeding. Rollback, scale, failover, disable feature flag.
5. **Diagnose** — (optional concurrent) what's actually broken.
6. **Resolve** — service restored, metrics back to normal for sustained window.
7. **Postmortem** — blameless, within 5 business days.
8. **Action items** — tracked, owned, due-dated.

Mitigation before diagnosis is the rule. Restore service first, understand second.

---

## Runbook structure

Every alert links to a runbook that answers:

1. **Signal** — what triggered this, what does it mean?
2. **Impact** — is a user-visible problem happening, or is this preventive?
3. **First checks** — dashboard links, recent deploy list, known-broken dependencies.
4. **Mitigation steps** — concrete commands (scale, rollback, failover, disable flag).
5. **Diagnosis pointers** — logs to search, traces to pull, metrics to cross-check.
6. **Escalation** — who to page if mitigation fails.

### Runbook example (High Error Rate)

```markdown
# High Error Rate

**Signal:** Error rate > 5% on myapp for >5min.

**Impact:** Users seeing 500 errors. Paged on critical.

**First checks:**
- Dashboard: https://grafana/d/myapp
- Recent deploys: https://ci/myapp
- Dependencies: https://grafana/d/deps

**Mitigation:**
1. Check if a deploy landed in the last 30min. If yes: `kubectl rollout undo deployment/myapp`
2. Check DB connection pool saturation. If saturated: scale up pods `kubectl scale deploy/myapp --replicas=10`
3. Check upstream deps (payment-service, user-service). If down: enable circuit breaker fallback via feature flag `degrade_payments=true`.

**Diagnosis:**
- Kibana query: `service:myapp AND level:ERROR | timechart`
- Trace search for slow spans: tempo / jaeger
- Slow query log: `SELECT query, duration FROM pg_slow_queries WHERE ...`

**Escalation:**
- Database issues → database team oncall
- Third-party down → comms-lead post to status page
```

Runbook is a living document. After each incident, update the runbook that fired (or would have helped).

---

## Postmortem template (blameless)

```markdown
# Incident: [Title]

**Date:** YYYY-MM-DD
**Duration:** Xh Ymin
**Severity:** Sev-N
**Impact:** [users affected, requests failed, revenue impact, SLO budget consumed]

## Timeline (UTC)
- 10:00 — alert fires
- 10:02 — oncall acknowledges
- 10:05 — IC declares Sev-1, channel opened
- 10:10 — identified recent deploy as probable cause
- 10:12 — rollback initiated
- 10:17 — metrics recovering
- 10:30 — incident resolved, monitoring for stability
- 11:00 — all-clear

## Summary
One-paragraph what happened, in plain language. For stakeholders.

## Contributing factors
Not "root cause" (usually there isn't one). Causal chain, multiple factors.
- Factor A: release included a regression (code).
- Factor B: staging does not load-test the affected endpoint (process).
- Factor C: alert on latency was tuned wider than SLO (tooling).

## What went well
- Detection was fast (under 2min).
- Runbook existed, was clear, and worked.

## What went poorly
- Comms lag — status page updated 10 min after public impact started.
- Rollback took 5 min due to slow image pull.

## Action items
| Item | Owner | Due | Ticket |
|---|---|---|---|
| Add load test for affected endpoint in staging | @alice | 2024-01-22 | ENG-123 |
| Tighten latency alert to match SLO | @bob | 2024-01-22 | SRE-45 |
| Add release-landing annotation to dashboards | @carol | 2024-01-29 | SRE-46 |

## Lessons
- Detection gap: none (good).
- Response gap: comms protocol unclear under time pressure.
- Prevention gap: integration tests missed this class of bug.
```

**Blameless** means we focus on system weaknesses, not individuals. "Alice deployed the bad code" is not a cause — "the deploy pipeline did not catch this class of bug" is.

---

## DR: RTO and RPO

- **RTO (Recovery Time Objective)** — how long until service restored after disaster.
- **RPO (Recovery Point Objective)** — how much data loss (window before disaster) is acceptable.

| Tier | RTO | RPO | Implied architecture |
|---|---|---|---|
| Critical | < 1 hour | < 5 min | Multi-region active-active or hot-standby; continuous replication |
| Standard | < 4 hours | < 1 hour | Warm-standby in another region; hourly snapshots |
| Best effort | < 24 hours | < 24 hours | Daily backup; rebuild from backup |

RTO/RPO numbers must match investment. "RTO 1 hour" without multi-region infra is fiction.

---

## Backups

- **Schedule** — DB: hourly WAL + daily full (Postgres continuous archiving, similar for others). Files: daily snapshot. Config: IaC in git is backup.
- **Retention** — daily 30 days, weekly 12 weeks, monthly 12 months. Legal/compliance may mandate more.
- **Cross-region copy** — disaster = region loss. Backup in same region helps with corruption, not region loss.
- **Encryption** — KMS-encrypted at rest; decrypt key access logged.
- **Test restores** — quarterly: restore to staging, run smoke tests. Without tested restore, you don't have backup.

### Velero (Kubernetes)

```bash
velero install --provider aws --bucket velero-backups --secret-file ./creds
velero schedule create daily-backup --schedule="0 2 * * *" --include-namespaces production
velero restore create --from-backup daily-backup-20240115
```

### Postgres backup CronJob example

```yaml
apiVersion: batch/v1
kind: CronJob
metadata: { name: postgres-backup }
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:15
            env:
            - { name: PGPASSWORD, valueFrom: { secretKeyRef: { name: postgres-secrets, key: password } } }
            command: [sh, -c]
            args:
            - |
              pg_dump -h postgres -U postgres mydb | gzip > /backup/backup-$(date +%Y%m%d).sql.gz
              aws s3 cp /backup/backup-$(date +%Y%m%d).sql.gz s3://backups/postgres/
```

---

## Failover patterns

### DB failover

- **Multi-AZ (RDS, CloudSQL, etc.)** — primary + standby, synchronous replication within region, automatic failover. ~30-60s outage.
- **Read replica promotion** — async replication, potential data loss = replication lag. Manual or semi-automated promotion.
- **Cross-region replica** — async, 100+ms lag typical. Promotion is a significant decision (data loss tradeoff).

Test failover annually minimum. Untested failover = failure during the real event.

### Traffic failover

- **DNS-based** (Route53 health check → regional endpoint). Propagation lag (TTL).
- **Global load balancer** (CloudFront, Cloudflare, GCP GLB). Fast failover.
- **Anycast** — many providers' approach. Client routes to nearest; failover near-instant.

### Split-brain

In active-active multi-region: two regions accept writes to the same logical row simultaneously → conflict. Resolution:

- **Last-write-wins** — lose one side's writes (often wrong).
- **Conflict-free replicated data types (CRDTs)** — designed to merge; limited semantics.
- **Per-tenant region pinning** — tenant X always writes to region A; region B is read-only. Simple; sacrifices some availability.

Most active-active designs pin per-tenant to avoid split-brain.

---

## Chaos engineering

Proactively inject failure to verify resilience.

- Start in staging; graduate to prod game days.
- Techniques: kill pods, inject latency, block network to a dep, fill disk, CPU stress, simulate region outage.
- Tools: Chaos Mesh, Gremlin, AWS FIS, LitmusChaos.
- Every chaos experiment has a hypothesis ("service X tolerates Y dep being slow") and a bailout.

If you've never killed a production pod on purpose, you don't know what happens when one dies.

---

## Common incident playbooks

### Deploy-related outage
1. Rollback first: `helm rollback` / `kubectl rollout undo` / revert image tag.
2. Then diagnose.

### Database performance collapse
1. Check for new slow queries (recent deploy changed query patterns?).
2. Kill long-running runaway queries (`pg_terminate_backend(pid)`).
3. Scale up read replicas if read-bound.
4. Emergency index if a specific query is the culprit (`CREATE INDEX CONCURRENTLY` in Postgres).

### Third-party dependency down
1. Enable circuit breaker / fallback (feature flag).
2. Update status page if user-visible.
3. Monitor vendor status page.
4. Postmortem: was there a timeout + fallback? Why did the outage cascade?

### Region outage
1. Verify it's a regional AWS/GCP issue, not yours (provider status page).
2. Failover DNS / traffic routing to healthy region.
3. Verify data replication caught up before switching writes.
4. Status page + customer comms.

### Certificate expiry (avoidable)
1. Renew immediately (cert-manager auto-renews, but verify).
2. Push to all nodes / LBs.
3. Action item: certificate monitor that alerts 30 days before expiry.

---

## Cost optimization during/after incidents

Incidents sometimes create cost incidents:
- Auto-scaled pods during outage may not scale back down.
- Retried-forever failed jobs can burn compute.
- Log volume explodes — log pipeline bill spikes.
- Egress charges from failed cross-region retries.

Post-incident: review cost dashboards for 24-72h after. Action item if spend visibly changed.
