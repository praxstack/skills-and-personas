# Security Methodologies — OWASP, SAST/DAST, Pentest, Review Checklists

**When to load this file:** Any security review, threat modeling, running SAST/DAST, pentest, or reviewing auth/crypto/access-control.

## OWASP Top 10 (2021) — What to Actually Look For

**A01: Broken Access Control**
- Horizontal privilege escalation: `/api/users/123/orders` accessible to user 124.
- Vertical privilege escalation: regular user hitting admin endpoints.
- IDOR (Insecure Direct Object Reference): object ID in URL/request without authorization check.
- Force-browsing: hitting pages not in UI but still served.
- JWT scope manipulation.

**Test:** for every endpoint, verify auth'n + auth'z are checked against the resource, not just "is logged in." Authorize against resource ownership / role, not user ID from client.

**A02: Cryptographic Failures**
- Passwords stored with MD5/SHA-256 plain (use bcrypt/scrypt/Argon2).
- Transport: TLS <1.2, weak ciphers, mixed content.
- At rest: sensitive data unencrypted.
- Weak random (`Math.random()`, `rand()`) for tokens, IDs — use CSPRNG.
- Hardcoded keys, IVs reused.

**A03: Injection**
- SQL: concatenating user input into queries. Fix: parameterize or use ORM.
- NoSQL: `{ "$ne": null }` as password. Fix: cast to primitive, validate.
- Command: `exec(user_input)`. Fix: never. Use safe APIs or strict allowlist.
- Template/SSTI: Jinja/Mustache rendering user-supplied templates.
- LDAP, XPath, ORM, XML (XXE) — same class.

**A04: Insecure Design**
- Missing rate limiting, no MFA option for sensitive accounts, business-logic flaws (negative quantity, race in balance checks).
- Fix requires threat modeling, not a scanner find.

**A05: Security Misconfiguration**
- Default creds, verbose error messages, debug mode in prod, unneeded features enabled, missing headers, permissive CORS.

**A06: Vulnerable and Outdated Components**
- Dependency with known CVE. Fix: patch or replace. Use Snyk, Dependabot, Renovate.
- Reachability matters — CVE in a code path you don't call is lower priority.

**A07: Identification and Authentication Failures**
- No MFA, weak password policy, credential stuffing allowed (no rate limit, no CAPTCHA), session fixation, missing logout-everywhere, bad password reset flow.

**A08: Software and Data Integrity Failures**
- Unsigned packages, no SRI (subresource integrity) on CDN assets, insecure CI/CD (unsigned builds, mutable tags), unsafe deserialization.

**A09: Security Logging and Monitoring Failures**
- No auth event logs, no privilege-escalation attempt logs, no alerting, no log integrity.
- Can you detect an attack in progress? If no → here.

**A10: Server-Side Request Forgery (SSRF)**
- App fetches URL based on user input; attacker points it at internal services (metadata endpoint 169.254.169.254 on AWS/GCP).
- Fix: allowlist destinations, block private IP ranges, use a dedicated proxy.

## Threat Modeling

**STRIDE** (per component):
- **S**poofing (impersonation): authentication.
- **T**ampering (integrity): signatures, hashes.
- **R**epudiation: audit logs.
- **I**nformation disclosure: encryption, access control.
- **D**enial of service: rate limiting, quotas.
- **E**levation of privilege: least privilege, authorization.

Walk through architecture diagram; apply STRIDE to each data flow. Document identified threats and mitigations.

**Trust boundaries** are where data crosses privilege domains. User → API, service → service across network, app → DB. Validate/sanitize at every boundary; don't trust upstream.

## SAST (Static)

**Tools:**
- **Semgrep** (free + paid): pattern-based, fast, writeable custom rules.
- **CodeQL** (GitHub): semantic, deeper analysis; security queries built-in.
- **SonarQube:** broad, includes code-quality + security.
- **Snyk Code:** dataflow analysis.
- **Bandit** (Python), **gosec** (Go), **brakeman** (Rails), **eslint-plugin-security** (JS).

**Run on every PR.** Fail build on new findings above threshold. Track trend (new vs existing).

**False-positive handling:** don't ignore — suppress with rationale + expiry date. Unexplained suppressions compound.

## DAST (Dynamic)

**Tools:**
- **OWASP ZAP:** free, scriptable (`zap-baseline.py`), CI-integrable.
- **Burp Suite Pro:** industry standard for manual + automated scanning.
- **Nuclei:** YAML-templated, fast, community template library.

**Coverage gap:** DAST needs to authenticate to cover authenticated surfaces. Configure with valid session; otherwise you're scanning public pages only.

**CI integration:** run baseline scan on every staging deploy; full active scan pre-release or nightly.

## SCA (Software Composition Analysis)

**Tools:** Snyk, Dependabot, Renovate, `npm audit`, `pip-audit`, OWASP Dependency-Check.

**Reachability:** a CVE in a library you import but never call on a reachable path is lower risk. Tools like Snyk Code or Datadog ASM do reachability analysis.

**Lockfile hygiene:** commit lockfiles; reproducible builds. Review Renovate PRs — don't auto-merge major versions.

**License compliance** bonus: SCA can flag GPL/AGPL contamination in commercial products.

## Penetration Testing

**When:**
- New major product surface.
- Compliance requirement (PCI, SOC2).
- Post-incident.
- Annual cadence for mature products.

**Phases:**
1. **Reconnaissance:** DNS, subdomains, ports, tech stack (Amass, subfinder, nmap, whatweb).
2. **Enumeration:** endpoints, parameters, directories (Burp spider, ffuf, gobuster).
3. **Vulnerability discovery:** SAST/DAST results + manual probing.
4. **Exploitation:** confirm exploitability, measure impact.
5. **Post-exploitation:** lateral movement, privilege escalation (black-box mode).
6. **Reporting:** findings with severity, PoC, remediation, retest plan.

**Engagement types:**
- **Black-box:** zero info. Most realistic but slowest.
- **Gray-box:** credentialed, some docs. Common.
- **White-box:** full source + docs. Most coverage; best for compliance.

**Internal pentest vs external firm:** internal catches known classes faster; external gets fresh eyes + less confirmation bias. Both valuable.

## Authentication Review Checklist

- Password hashing: bcrypt (cost 10+), scrypt, or Argon2id. NOT MD5/SHA.
- Password policy: 12+ chars, complexity not over-specified (length beats complexity per NIST 800-63B).
- MFA option (TOTP / WebAuthn) for high-privilege accounts.
- Account lockout or rate limit on failed attempts (exponential backoff; log + alert).
- Credential stuffing mitigation: bot detection (CAPTCHA on suspicious), IP reputation, device fingerprint.
- Password reset: token with limited lifetime, single-use, invalidated on successful reset.
- Don't reveal if email exists on signup/reset ("If this email is registered, you'll receive...").
- Email verification before sensitive actions.
- WebAuthn / passkeys support for modern auth.

## Session Management

- Server-side session or JWT — both have tradeoffs.
  - **Server session:** stateful; can invalidate instantly; requires store (Redis).
  - **JWT:** stateless; hard to invalidate before expiry (use short expiry + refresh token rotation).
- Short access-token lifetime (5-15 min); longer refresh-token (days) with rotation.
- HttpOnly, Secure, SameSite=Lax (or Strict) on cookies.
- CSRF protection: SameSite + anti-CSRF token for state-changing endpoints on cookie-auth.
- Logout invalidates token/session; logout-everywhere on password change or suspicious activity.
- Session-fixation prevention: rotate session ID on login.

## JWT Pitfalls

- Always verify signature. Reject `alg: none`.
- Verify issuer (`iss`), audience (`aud`), expiration (`exp`), not-before (`nbf`).
- Don't trust claims from client without re-verifying.
- Don't put sensitive data in JWT (anyone with token can decode).
- Use asymmetric keys (RS256, ES256) if verification happens across services.
- Rotate signing keys; support multiple active keys during rotation.
- Use `kid` header to select verification key.

## Authorization Patterns

- **RBAC:** roles → permissions. Simple, scales poorly with complex access.
- **ABAC:** attribute-based (user attrs + resource attrs + action + context). Flexible, complex to reason about.
- **ReBAC:** relationship-based (Zanzibar, OpenFGA). Best for social/collaborative (documents, orgs, shared resources).

**Common failure:** checking role at route level, forgetting row-level ownership. Example: admin route checks "is admin"; attacker as admin of one tenant reads another tenant's data. Fix: scope queries by tenant/owner even for admins.

## Cryptography Review

- TLS 1.2 minimum, 1.3 preferred. No SSL, no TLS 1.0/1.1.
- Cipher suites: forward-secure (ECDHE); no RC4, DES, export ciphers.
- Certificate management: auto-renewal (Let's Encrypt, cert-manager); monitor expiry.
- HSTS with preload for production.
- Encryption at rest for sensitive data: AES-256-GCM (authenticated).
- Key management: AWS KMS, GCP KMS, HashiCorp Vault, not `.env` files.
- Random values: use CSPRNG (`crypto.randomBytes`, `secrets.token_bytes`, `/dev/urandom`), not `Math.random()`.
- Constant-time compare for secrets (`crypto.timingSafeEqual`, `hmac.compare_digest`).

## Input Validation

- Validate at trust boundary (API input), not inside business logic.
- Allowlist > blocklist (too easy to bypass blocklists).
- Type + length + format + range.
- File uploads: validate magic bytes (not just extension); limit size; store outside web root; serve via download endpoint with content-disposition.
- Use schema validators (Zod, Pydantic, Joi) with strict mode (no extra properties).

## Output Encoding

- HTML encoding for user content rendered in HTML context.
- JS encoding for user content in JS context (but avoid inlining user content in JS; use data attributes).
- URL encoding for user content in URLs.
- Framework auto-escaping (React JSX, Vue `{{}}`, Jinja `|safe` off) — learn the escaping rules and edge cases.
- Never `innerHTML = userInput`. React's `dangerouslySetInnerHTML` is named for a reason.

## Security Headers (Web)

- `Content-Security-Policy`: strict (`default-src 'self'`, no `unsafe-inline`, no `unsafe-eval`, allowlist CDNs). Report-only mode to start.
- `Strict-Transport-Security`: `max-age=31536000; includeSubDomains; preload`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY` (or CSP `frame-ancestors`)
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy` (was Feature-Policy): restrict camera, geolocation, etc.

## API-Specific

- Rate limiting per user + per IP; separate budgets.
- Authentication on every endpoint (default-deny; opt-in public).
- Versioning strategy; deprecation policy.
- Request size limits.
- Content-Type validation (reject text/plain where JSON expected).
- Output DTOs — never return raw DB models.
- Error responses don't leak internals (no stack traces, no SQL errors to users).

## GraphQL-Specific

- Depth limit (e.g., 5-7) — prevents recursive explosion.
- Complexity limit — prevents expensive query abuse.
- Timeout per query.
- Introspection off in production (or auth-gated).
- Batching limits.

## Secrets Hygiene

- Never commit (pre-commit hook: gitleaks, trufflehog, git-secrets).
- Rotate if leaked, even in old history — history is searchable.
- Use secret managers (Vault, AWS Secrets Manager, Doppler, 1Password CLI).
- Per-environment secrets; local dev uses `.env` git-ignored.
- CI/CD secrets scoped to workflow; audit access.
- Rotate on employee departure; audit long-lived tokens quarterly.

## Logging & Monitoring

**Events that must be logged:**
- Auth events (success, failure, lockout)
- Authorization denials
- Admin actions
- Data export / bulk operations
- Privilege escalation attempts
- Payment / financial events
- Config changes

**What NOT to log:** passwords, full credit card numbers, session tokens, PHI/PII (mask at the logging boundary).

**Alerting triggers:**
- Auth failure rate above baseline
- New admin account creation
- Privilege change
- Access from new geography / device (if you track)
- Mass data export
- Error rate spike

**Log integrity:** centralize logs; use append-only stores; restrict delete permissions.

## Incident Response Quick Reference

1. **Detect:** alerts, reports, user complaints.
2. **Assess severity:** P1 breach > P2 exposure > P3 defacement > P4 failed attempt.
3. **Contain:** isolate affected systems (revoke creds, pull from LB, disable endpoints).
4. **Preserve evidence:** memory dump, disk image, log snapshot BEFORE remediation.
5. **Eradicate:** patch, rotate, close backdoors.
6. **Recover:** restore from clean state; staged reopen with monitoring.
7. **Post-mortem:** blameless, root cause, action items with owners.
8. **Communicate:** internal, customers (if breach), regulators (if required — GDPR 72h breach notification).
