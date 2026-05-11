# Infrastructure as Code

**When to load this file:** Load when designing, reviewing, or refactoring Terraform/Pulumi/CDK. Covers module structure, state management, environment strategy, drift detection, and common AWS/K8s module patterns.

---

## Repository layout

```
infrastructure/
├── modules/              # reusable, versioned modules
│   ├── vpc/
│   ├── eks/
│   ├── rds/
│   ├── s3/
│   └── iam/
├── environments/         # compositions per env
│   ├── dev/
│   ├── staging/
│   └── production/
└── global/               # org-wide: route53, IAM roles, orgs
```

- **Modules** take inputs, produce outputs. No hardcoded env names.
- **Environments** call modules with per-env values. Short and declarative.
- **Version** modules (git tag or registry version). Never reference `main` from an environment.

---

## State management

- **Remote backend** (S3 + DynamoDB lock table, Terraform Cloud, GCS, Azure Storage) — never local state in a team setting.
- **One state per environment**, not one giant state for everything. Blast radius of a mistake is contained to one env.
- **Separate state for stateful vs stateless** resources — don't reapply RDS every time you touch a Lambda.
- **State locking** mandatory — DynamoDB table for S3 backend. Unlocked state = concurrent applies = corruption.
- **State encryption at rest** (S3 SSE, KMS) because state contains secrets (RDS passwords, keys).

### Managing drift

- Run `terraform plan` in CI on a schedule (nightly) and alert on non-empty diffs. Drift = someone changed infra outside of IaC.
- Don't `terraform import` blindly in response — root-cause the change, then import or revert.
- For resources managed outside IaC intentionally (ad hoc dev sandboxes), tag them and filter plan output — don't fight their presence.

---

## Workspaces vs directories

- **Workspaces** (Terraform native) — same module, different state per workspace. Concise but easy to mis-target (apply dev to prod).
- **Directory-per-env** — explicit, hard to mis-target, easy code review. Usually preferred for prod workloads.
- CDK's `Stack` + context achieves similar isolation with typing help.

---

## Module design

- **Single purpose** — VPC module does VPC + subnets + route tables + NAT. Not also EKS.
- **Inputs explicit** — required vs optional, sane defaults.
- **Outputs are the contract** — every value other modules depend on is an output. No reaching into module internals.
- **Tag everything** — `environment`, `service`, `owner`, `cost-center`, `managed-by=terraform`. Cost allocation and ownership depend on this.
- **Lifecycle rules** — `prevent_destroy = true` on RDS, stateful disks, Route53 zones. Stops accidental `destroy`.

### Resource naming

- `${env}-${service}-${resource}` — `production-api-alb`, `staging-users-db`.
- Consistent, searchable in cloud console and bills.
- Don't rely on Terraform-generated random names in human-facing places.

---

## Secrets in IaC

- **Never** in code or state plain-text.
- Source secrets from the secret manager at apply time (data source) or runtime (application reads directly).
- Mark sensitive outputs `sensitive = true` — still stored in state, but hidden in CLI.
- If possible, let the application pull secrets at runtime from IAM/Workload Identity rather than Terraform writing them to k8s Secrets.

---

## Common module patterns (AWS)

### VPC

- 3 AZs minimum for HA; some services require ≥3.
- Public + private subnets per AZ. Database subnets separate from workload subnets (some services require this).
- NAT gateway per AZ (HA); single NAT is a SPOF + cross-AZ data transfer charge.
- VPC endpoints for S3, DynamoDB, ECR — cheaper than NAT for AWS-service traffic.
- Flow logs to S3 for security/audit.

### EKS

- Private API endpoint if accessed from bastion/VPN; public + restricted CIDRs otherwise.
- `enabled_cluster_log_types` = `["api","audit","authenticator","controllerManager","scheduler"]`.
- Managed node groups for most workloads; Fargate for opinionated serverless pods.
- KMS encryption for Kubernetes Secrets at etcd level.
- Separate node groups by workload (system vs application vs spot). Use taints to steer scheduling.
- IRSA (IAM Roles for Service Accounts) — workloads get IAM via annotated ServiceAccount, no static keys.
- Upgrade plan: minor versions within N months of EKS release; skip none.

### RDS

- Multi-AZ for HA (primary + standby in another AZ).
- Read replicas for read scaling. Lag is real, measure.
- `deletion_protection = true`, `skip_final_snapshot = false` for prod.
- Automated backups ≥ 7 days for prod, 30+ for compliance workloads.
- Parameter groups in IaC — don't hand-edit in console.
- Master password from Secrets Manager; rotation enabled.
- Encryption at rest (KMS); enforce TLS in transit with `rds.force_ssl` parameter.

### S3

- `block_public_access_*` all `true` by default; explicit exceptions documented.
- Versioning on for buckets holding durable data; MFA delete for crown jewels.
- Lifecycle: transition to IA → Glacier → expire, per data class.
- Server-side encryption default (SSE-S3 or SSE-KMS); enforce with bucket policy.
- Access logs to a separate bucket (preventing cycles).

---

## Common module patterns (Kubernetes)

### Deployment baseline

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: production
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels: { app: myapp }
  template:
    metadata:
      labels: { app: myapp }
    spec:
      containers:
      - name: myapp
        image: registry/myapp:<git-sha>
        ports:
        - containerPort: 3000
        resources:
          requests: { memory: 256Mi, cpu: 250m }
          limits:   { memory: 512Mi, cpu: 500m }
        livenessProbe:
          httpGet: { path: /health, port: 3000 }
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet: { path: /ready, port: 3000 }
          initialDelaySeconds: 5
          periodSeconds: 5
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef: { name: myapp-secrets, key: database-url }
        securityContext:
          runAsNonRoot: true
          readOnlyRootFilesystem: true
          allowPrivilegeEscalation: false
          capabilities: { drop: [ALL] }
```

- Immutable image tag (git SHA or semver).
- Resource requests and limits.
- Both liveness and readiness probes, separate logic.
- Non-root, read-only FS, no privilege escalation.
- Secrets via `secretKeyRef`, not env literal.

### HPA baseline

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata: { name: myapp }
spec:
  scaleTargetRef: { apiVersion: apps/v1, kind: Deployment, name: myapp }
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target: { type: Utilization, averageUtilization: 70 }
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies: [{ type: Percent, value: 50, periodSeconds: 60 }]
    scaleUp:
      stabilizationWindowSeconds: 30
      policies: [{ type: Percent, value: 100, periodSeconds: 30 }]
```

- `minReplicas ≥ 2` for HA.
- Scale up aggressively, scale down slowly — avoid flapping.
- Consider custom metrics (request rate, queue depth) for request-bound workloads; CPU is often a poor proxy.

### PodDisruptionBudget (mandatory for critical workloads)

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata: { name: myapp }
spec:
  minAvailable: 2   # or: maxUnavailable: 1
  selector: { matchLabels: { app: myapp } }
```

- Without PDB, a node drain can evict all pods simultaneously.

### NetworkPolicy (default deny + explicit allow)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: default-deny-all, namespace: production }
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: myapp-allow }
spec:
  podSelector: { matchLabels: { app: myapp } }
  policyTypes: [Ingress, Egress]
  ingress:
  - from: [{ namespaceSelector: { matchLabels: { name: ingress-nginx } } }]
    ports: [{ protocol: TCP, port: 3000 }]
  egress:
  - to: [{ podSelector: { matchLabels: { app: postgres } } }]
    ports: [{ protocol: TCP, port: 5432 }]
  - to: [{ podSelector: { matchLabels: { app: redis } } }]
    ports: [{ protocol: TCP, port: 6379 }]
```

- Requires a CNI plugin that enforces NetworkPolicy (Calico, Cilium). Default flannel does not.

### Helm structure

```
chart/
├── Chart.yaml
├── values.yaml          # defaults
├── values-prod.yaml     # prod overrides
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── hpa.yaml
│   ├── pdb.yaml
│   └── _helpers.tpl
└── tests/               # helm test hooks
```

- Use `helm template --debug` to review rendered manifests before apply.
- `helm diff` plugin shows what will change on upgrade.
- Pin chart versions via `Chart.yaml` dependencies or Helmfile / Argo CD.

---

## Tools cheat

| Tool | Purpose |
|---|---|
| Terraform | General-purpose IaC, multi-cloud, HCL |
| Pulumi | IaC in a real language (TS, Go, Python) — preferred for loops/conditionals |
| CDK | AWS-native IaC in TS/Python, compiles to CloudFormation |
| tflint, tfsec, Checkov | Static analysis, security policy checks — run in CI |
| terraform-docs | Auto-generate README from module inputs/outputs |
| Atlantis, Terraform Cloud | PR-driven Terraform workflow with plan comments |
| Helm | Kubernetes package manager; templates + values |
| Kustomize | K8s YAML overlays without templating (purely additive patches) |
| Argo CD, Flux | GitOps controllers — reconcile cluster from git automatically |

GitOps: git is the declarative source of truth; a controller in the cluster pulls and reconciles. Prefer this over push-from-CI for cluster state. CI still runs tests/builds; deploy = merge.
