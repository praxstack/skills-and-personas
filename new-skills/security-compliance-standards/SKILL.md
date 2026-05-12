---
name: security-compliance-standards
description: 'Principal-engineer standards for security, privacy, and compliance across the application stack. Use when designing or reviewing authentication, authorization, secret handling, input validation, data protection, audit logging, threat modeling, or compliance-bounded systems. Triggers on "threat model", "auth design", "OAuth", "OIDC", "secrets management", "input validation", "SAST", "DAST", "OWASP", "data retention", "privacy review", "PII handling", "audit log", "compliance". Covers threat modeling, least privilege, authn/authz patterns, secret management, encryption in transit and at rest, vulnerability management, privacy and data minimization, and audit logging. Loaded by super-mode-core for security-critical work.'
---

# Security and Compliance Standards

**Audience:** Engineers and architects reviewing cross-cutting security and compliance posture. The methodology for attacking and defending specific surfaces (OWASP Top 10, injection classes, severity calibration, SAST/DAST/IAST/SCA matrix) lives in `qa-security-engineer` — this skill is for the high-level decision trees that shape architecture.

**Goal:** Give the non-obvious calls: which auth protocol for which context, when encryption-at-rest moves from KMS to HSM to app-level, how to make audit logs actually tamper-evident. Every control traces to a threat; every exception is explicit.

Generic best practices (use TLS, don't hardcode secrets, validate inputs, deny by default, rotate tokens) are Claude-default output and are not repeated here.

## Authentication protocol decision tree

Picking the wrong protocol is the error that compounds. Pick from this tree, not by familiarity:

```
Is this user-to-service or service-to-service?
├─ User-to-service
│  ├─ Browser/SPA with federated identity  → OIDC (OAuth2 Authorization Code + PKCE)
│  ├─ Enterprise SSO, existing IdP is SAML → SAML 2.0 (only; do not mix with OIDC in one flow)
│  ├─ Native mobile app                    → OIDC + PKCE + system browser (never embedded webview)
│  └─ Internal tools behind IdP proxy      → IAP/zero-trust proxy; app trusts signed header
└─ Service-to-service
   ├─ Same trust zone, low-latency critical → mTLS with short-lived SPIFFE/SPIRE identities
   ├─ Cross-zone or untrusted path          → Signed JWTs with `aud` validation + mTLS underlay
   ├─ Cloud-native same-VPC                 → Cloud IAM (workload identity, AWS IAM roles, GCP service accounts)
   └─ Webhook receiver from 3rd party       → HMAC signature + replay protection (timestamp + nonce)
```

Common misapplications:

- OIDC for service-to-service — works but forces human-auth flows into machine paths. Prefer mTLS or cloud IAM.
- SAML for SPAs — the redirect dance and XML parsing are a larger attack surface than OIDC.
- Mixing OIDC and SAML in the same flow — fail open in practice; a bug in either breaks both.

## Encryption-at-rest criteria

The question is not "should we encrypt at rest" (yes, usually) but "at which layer".

| Layer | When | Trade-off |
|---|---|---|
| **Cloud KMS + managed encryption** (default) | PII, payment data, credentials, health data | Transparent; encryption is automatic. Attacker with DB creds still reads plaintext via the DB. |
| **Application-level field encryption** | Regulated high-sensitivity fields within a larger non-sensitive table | Breaks indexing/search on those fields; query patterns must be redesigned around deterministic or searchable-encryption schemes. |
| **Dedicated HSM** (CloudHSM, nShield) | Compliance mandate (FIPS 140-2 Level 3, some PCI scopes), high-value signing keys | Operational overhead (key ceremonies, HSM failure modes); cost is 10–100x KMS. |
| **Envelope encryption** (DEK per row/object, KEK in KMS) | Massive data volumes where per-record key isolation matters | Key-rotation rotates the KEK, not every DEK — plan for two-phase re-encryption. |

Default: cloud KMS. Escalate to app-level only when the threat model names an attacker with DB read access; escalate to HSM only when compliance mandates it explicitly.

## Audit-log tamper-evidence

An audit log that can be silently edited is not an audit log.

- **Append-only storage** (WORM, S3 Object Lock in compliance mode, immutable ledger DBs) — the minimum bar. Attacker with admin creds cannot edit past entries.
- **Cryptographic chaining** — each record contains a hash of the previous record. Detects deletion or reordering after the fact. Implement as a Merkle chain for efficient proof of inclusion; a plain hash chain works for smaller volumes.
- **External anchoring** — periodically publish the chain head to a write-once external system (another cloud account, a blockchain, a trusted time-stamping service). Detects coordinated tampering where the attacker owns the primary log store.
- **Signed records** — per-record HMAC or signature with a key the log writer cannot reach after writing (KMS sign-only grant, ratcheted keys). Detects individual-record forgery.

For SOX/HIPAA/PCI scope, append-only is insufficient on its own; pair with chaining and external anchoring. Document the tamper-evidence posture explicitly in the threat model.

## Authorization calibration

- **Per-resource authorization**, not just per-route — the route-level check tells you the caller is authenticated; the resource-level check tells you the caller owns *that specific* resource. Every `/users/:id/...` route needs both.
- **Tenant isolation is tested, never assumed.** The integration test suite must contain explicit cross-tenant attempts that are expected to fail. A system without these tests has unknown tenant-isolation posture.
- **Default-deny with explicit grants** — an unknown permission check fails closed. A `role.can('undefined_action')` that returns `true` is a vulnerability, not a convenience.

## Anti-patterns specific to this layer

- **NEVER** issue long-lived bearer tokens without rotation — session tokens >24h without re-auth are a credential on the loose.
- **NEVER** assume tenant isolation without explicit cross-tenant test coverage.
- **NEVER** rely on append-only storage alone for high-compliance audit logs — pair with chaining or external anchoring.
- **NEVER** use OIDC for pure service-to-service authentication when mTLS or cloud IAM fits.
- **NEVER** mix SAML and OIDC in the same authentication flow — a bug in either breaks both.
- **NEVER** disable TLS certificate verification in production code — not even "temporarily for debugging".
- **NEVER** claim compliance posture (SOC 2, HIPAA, PCI, GDPR) you are not actively measuring and attesting.
- **NEVER** log passwords, tokens, API keys, full PANs, or full payment data — redact at log-emission time, not at ingestion time.
- **NEVER** store field-level encryption keys in the same blast radius as the data they protect.

## Cross-references

- `qa-security-engineer` — the attack-surface methodology: OWASP Top 10 coverage, SAST/DAST/IAST/SCA matrix, severity classification with CVSS-plus-context, password-hashing choice (bcrypt/scrypt/Argon2), JWT `alg:none` class attacks, constant-time compare.
- `backend-architecture-standards` — event-driven consistency, HA/DR targets, migration reversibility. Security decisions often hinge on these architectural calls.

## Deliverables contract

Security and compliance delivery includes:

- **Threat model** — assets, actors, entry points, trust boundaries; in-scope vs out-of-scope threats.
- **Authentication design** — protocol chosen from the decision tree, with the reason; token lifetimes, key rotation, service-to-service strategy.
- **Authorization design** — per-resource checks, tenant isolation strategy, test coverage for cross-tenant access.
- **Encryption plan** — in-transit posture, at-rest layer chosen from the criteria table, key rotation schedule.
- **Audit-log posture** — tamper-evidence approach (append-only, chaining, anchoring, signing), retention period, access controls on the audit system itself.
- **Privacy plan** — data minimization, redaction-at-emission, retention, deletion, regulated-data-specific controls.
- **Known risks and accepted risks** — with owner and review date.
- **Tests actually run** — SAST/DAST/dependency scan results; what was not run, with reasons.
