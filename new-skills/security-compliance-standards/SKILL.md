---
name: security-compliance-standards
description: 'Principal-engineer standards for security, privacy, and compliance across the application stack. Use when designing or reviewing authentication, authorization, secret handling, input validation, data protection, audit logging, threat modeling, or compliance-bounded systems. Triggers on "threat model", "auth design", "OAuth", "OIDC", "secrets management", "input validation", "SAST", "DAST", "OWASP", "data retention", "privacy review", "PII handling", "audit log", "compliance". Covers threat modeling, least privilege, authn/authz patterns, secret management, encryption in transit and at rest, vulnerability management, privacy and data minimization, and audit logging. Loaded by super-mode-core for security-critical work.'
---

# Security and Compliance Standards

**Audience:** Engineers and architects building or reviewing systems where authentication, data protection, and compliance boundaries matter — which is most production systems.

**Goal:** Deliver designs and code that defend against plausible attackers, handle secrets correctly, minimize data collection, preserve audit trails, and meet the compliance posture the workload demands. Every control traces to a threat; every exception is explicit.

## Core Principles

- Perform lightweight threat modeling before building: assets, actors, entry points.
- Enforce least privilege everywhere — identities, services, database roles, CI tokens.
- Strong authentication and authorization on every trust boundary.
- Never hardcode secrets; use a secret store.
- Encrypt data in transit; encrypt data at rest when required by sensitivity or regulation.
- Log security events with enough detail to investigate; preserve audit trails.
- Minimize data collection to what is actually required.
- Mask or redact sensitive fields in logs.
- Follow retention and deletion policies.

## Decision Framework

### Threat Modeling (Lightweight)

Before any significant design, enumerate:

- **Assets.** What is valuable? Credentials, PII, payment data, proprietary data, availability of the service itself.
- **Actors.** External attackers, malicious insiders, compromised dependencies, accidental misuse.
- **Entry points.** Every ingress: public endpoints, webhooks, message queues, file uploads, admin surfaces, CI/CD.
- **Trust boundaries.** Where does untrusted data become trusted? That is where validation and authorization live.

Document the threats you are defending against and the ones you are explicitly not.

### Authentication Patterns

- Prefer OAuth2 or OIDC for user authentication when applicable.
- Use short-lived access tokens with refresh token rotation.
- Validate tokens on every request — never cache a trust decision longer than the token's effective lifetime.
- Rotate signing keys on a schedule; support multiple active keys during rotation.
- Service-to-service auth: mTLS or signed tokens with audience validation.

### Authorization

- Enforce least privilege at every layer: application roles, database roles, cloud IAM, object ACLs.
- Deny by default; allow explicitly.
- Check authorization on every request at the resource level — not only at route level.
- For multi-tenant systems, tenant isolation must be tested, not assumed.

### Input Validation

- Validate inputs at every trust boundary.
- Use schema validators rather than ad-hoc regex.
- Reject, sanitize, or encode as appropriate for the sink — SQL, HTML, shell, LDAP, XPath all have different escape rules.
- Size-limit every input to prevent resource exhaustion.

### Secret Management

- Secrets live in a secret store (cloud KMS, HashiCorp Vault, 1Password, AWS Secrets Manager, equivalent).
- Never check secrets into source control — pre-commit and CI scanning enforce this.
- Rotate on a schedule; automate rotation where the system supports it.
- Separate secrets per environment; production secrets never appear in dev.
- Secrets delivered to workloads via environment variables or mounted files from the store — never baked into images.

### Encryption

- TLS for everything on the wire — internal and external. Disable legacy protocol versions.
- At rest: encrypt when the workload handles PII, payment data, credentials, or regulated data. Cloud-managed KMS is usually enough; application-layer encryption adds complexity, reserve for fields with heightened sensitivity.
- Key rotation planned and tested.

### Vulnerability Management

- Dependency scanning in CI; patch high-risk issues on a defined SLA.
- Input validation prevents injection and XSS.
- Rate limits and abuse detection on public endpoints and sensitive actions.
- Use SAST and DAST where available; document findings and remediation.

### Privacy and Data Handling

- Minimize data collection to what the feature actually needs.
- Mask or redact sensitive fields in logs — PII, credentials, tokens, payment data.
- Define retention and deletion policies; implement them, do not just document them.
- For regulated data (GDPR, HIPAA, PCI DSS, SOC 2 scope), confirm the control posture before shipping.

### Audit Logging

- Log authentication events, authorization decisions, privileged actions, and security-relevant configuration changes.
- Include actor, resource, action, timestamp, source IP, and correlation ID.
- Make audit logs tamper-evident — append-only storage or signed logs.
- Retain for the period the compliance regime requires.

## Anti-Patterns

- **NEVER** hardcode secrets in code, config, or CI pipeline definitions.
- **NEVER** commit `.env` files or plaintext credentials to source control.
- **NEVER** log passwords, tokens, API keys, or full payment data.
- **NEVER** trust client-side validation alone — server re-validates every input.
- **NEVER** issue long-lived bearer tokens without rotation.
- **NEVER** assume tenant isolation without explicit test coverage.
- **NEVER** use string concatenation for SQL, shell, or any injection-sensitive sink — use parameterized APIs.
- **NEVER** expose internal errors or stack traces to untrusted clients.
- **NEVER** skip authorization at the resource level because the route is "protected".
- **NEVER** claim compliance posture you are not measuring.
- **NEVER** disable TLS certificate verification in production code.

## Standard Workflow

1. **Threat model first.** Enumerate assets, actors, entry points, trust boundaries. Write down what is in scope and what is explicitly not.

2. **Classify the data.** Public, internal, confidential, regulated. The classification drives encryption, logging, retention, and access-control choices.

3. **Design authentication.** Pick the protocol (OAuth2, OIDC, mTLS). Define token lifetimes, rotation, and key management.

4. **Design authorization.** Per-resource checks. Deny by default. Tenant isolation if multi-tenant.

5. **Plan input validation.** Schema-based, size-limited, sink-aware encoding.

6. **Plan secret management.** Store, rotation schedule, delivery mechanism, per-environment separation.

7. **Plan encryption.** In transit always; at rest per classification; key rotation schedule.

8. **Plan logging and audit.** What events, what fields, how masked, how retained, how tamper-evident.

9. **Plan privacy posture.** Data minimization, redaction, retention, deletion, right-to-access or right-to-delete if regulated.

10. **Plan vulnerability management.** Dependency scanning, SAST/DAST, rate limits, abuse detection, patch SLA.

11. **Validate.** Run the checks that exist (SAST, DAST, dependency scan). Explicitly list what was run and what was not. Never claim a test result that did not execute.

## Deliverables Contract

Security and compliance delivery includes:

- **Threat model** — assets, actors, entry points, trust boundaries, in-scope vs out-of-scope threats.
- **Data classification** — what data is collected, its classification, and the resulting controls.
- **Authn design** — protocol, token strategy, key rotation, service-to-service plan.
- **Authz design** — role model, per-resource checks, tenant isolation strategy if applicable.
- **Input validation plan** — what is validated where, what is rejected vs sanitized vs encoded.
- **Secret management plan** — store, rotation, delivery, per-environment separation.
- **Encryption plan** — in transit posture, at rest posture, key rotation.
- **Logging and audit plan** — what is logged, what is masked, retention, tamper-evidence.
- **Privacy plan** — minimization, redaction, retention, deletion, regulated-data-specific controls.
- **Vulnerability management plan** — scanning cadence, patch SLA, SAST/DAST coverage, rate limits.
- **Tests actually run** — and what was not run, with reasons.
- **Known risks and accepted risks** — with owner and review date.

## Compliance Posture

If the workload is in scope for a compliance regime (SOC 2, GDPR, HIPAA, PCI DSS, ISO 27001, etc.), confirm the specific controls the regime requires and map them to the design. Do not claim compliance posture that is not being measured or attested.
