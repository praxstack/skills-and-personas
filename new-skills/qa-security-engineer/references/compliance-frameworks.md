# Compliance: GDPR, SOC 2, PCI DSS, HIPAA

**When to load this file:** Determining if a framework applies, mapping controls to code/infra, preparing for audits, or designing features that touch regulated data.

## Which Framework Applies?

| You handle... | In these regions... | Likely need... |
|---|---|---|
| EU/UK personal data | Anywhere | GDPR / UK GDPR |
| California resident data | Anywhere (size thresholds) | CCPA/CPRA |
| Health info (US) | US | HIPAA |
| Cardholder data | Anywhere processing cards | PCI DSS |
| B2B SaaS with enterprise customers | Global | SOC 2 (customer-driven) |
| Children's data (under 13 in US) | US | COPPA |
| Publicly traded company IT controls | US | SOX ITGC |

Multiple frameworks often apply simultaneously. Map once, satisfy many.

## GDPR (and UK GDPR, CCPA/CPRA)

**Core principles:**
- **Lawful basis** for processing (consent, contract, legal obligation, vital interest, public task, legitimate interest).
- **Data minimization:** collect only what you need.
- **Purpose limitation:** use data only for the stated purpose.
- **Storage limitation:** delete when no longer needed.
- **Integrity + confidentiality:** secure it.
- **Accountability:** prove compliance.

**User rights (engineer's perspective):**
- **Access** — user requests all their data. Build an export endpoint or on-demand ZIP.
- **Rectification** — user corrects their data. Standard profile update.
- **Erasure ("right to be forgotten")** — DELETE on request. Cascade properly; beware of backups and logs.
- **Portability** — machine-readable export (JSON, CSV).
- **Restrict / Object to processing** — halt automated processing on request.
- **Automated decision-making** — explain algorithmic decisions; allow human review for significant decisions.

**Implementation patterns:**
- **Account deletion:** soft delete (mark deleted, anonymize) vs hard delete. Soft allows recovery but harder for GDPR true deletion. Hybrid: soft for 30 days for recovery, then hard.
- **Cascade deletion:** posts, comments, files, logs. Anonymize (not delete) audit logs needed for legal hold.
- **Backups:** backups may contain deleted users; document retention (e.g., 35 days) and deletion in backup rotation.
- **Analytics:** pseudonymize where possible; drop PII from event streams.
- **Cookies/tracking:** consent banner with granular options (necessary / preferences / analytics / marketing); default OFF for non-essential.
- **Subprocessors list** — publicly maintain list of third parties handling user data.

**Data breach notification:** 72 hours to supervisory authority. Have a runbook. Know who notifies which authority.

**Test patterns:**
- Create user → submit right-to-access request → verify export contains all records from all tables.
- Create user → delete → verify across all user-owned data.
- Create user → restrict processing flag → verify automated processes skip.

## SOC 2 (Type I and Type II)

**Type I:** controls exist at a point in time.
**Type II:** controls operate effectively over 3-12 months. What enterprise buyers ask for.

**Trust Services Criteria (TSC):**
- **Security** (mandatory): common criteria — access, change management, risk, etc.
- **Availability:** uptime, disaster recovery.
- **Confidentiality:** protect designated-confidential info.
- **Processing Integrity:** data processed accurately, timely.
- **Privacy:** handling of personal info.

Pick the criteria that match commitments you make to customers.

**Common controls engineers implement:**
- **Access management:** SSO, MFA, least privilege, quarterly access reviews.
- **Change management:** PR reviews, approvals, audit trail.
- **Logging:** central, immutable, retained (usually 1 year).
- **Monitoring + alerting:** defined thresholds, documented response.
- **Vulnerability management:** scan cadence, patch SLAs, tracked remediation.
- **Backup + DR:** tested restores, RTO/RPO defined.
- **Incident response:** runbook, communication, post-mortem.
- **Vendor management:** subprocessor reviews, data processing agreements.
- **Security awareness training:** annual; tracked.
- **Encryption:** at rest + in transit.

**Evidence collection** is the audit pain point. Automate where possible:
- Drata, Vanta, Secureframe — control mapping + evidence collection.
- Direct CI/CD evidence: PR approval records, scan results, deploy logs.
- Access review dashboards (Okta, Google Workspace, AWS IAM).

**Auditor interactions:**
- Scoping: define the in-scope systems.
- Walkthroughs: explain controls.
- Evidence requests: automate.
- Testing: they'll sample; expect to produce evidence quickly.

## PCI DSS

Applies if you store, process, or transmit cardholder data.

**Key strategy: REDUCE SCOPE.** Every system that touches card data is in scope. Minimize by:
- Use a PCI-compliant processor (Stripe, Braintree, Adyen) with hosted fields / iframe.
- Tokenize — your systems never see the PAN (Primary Account Number) directly.
- Segment networks — PCI-scope systems isolated from non-scope.

**12 requirements (summary):**
1. Firewalls and network segmentation.
2. Change default passwords.
3. Protect stored cardholder data (if you store — encryption + key management; avoid storing if possible).
4. Encrypt transmission over public networks (TLS 1.2+).
5. Anti-malware on applicable systems.
6. Secure development (SDL, change control, patch management).
7. Restrict access by need-to-know.
8. Unique auth per user, MFA for admin access.
9. Physical access restrictions (applies to data centers).
10. Track and monitor access to network + cardholder data (audit logs).
11. Regular security testing (quarterly ASV scans, annual pentest).
12. Maintain security policy.

**Compliance levels** (merchant-side, by card volume):
- Level 1 (>6M card transactions/year): on-site QSA audit annually.
- Level 2-4: self-assessment questionnaire (SAQ) varies.

**Testing patterns:**
- Verify no cardholder data in logs, databases you don't intend, client-side storage.
- TLS config on all card-handling endpoints.
- Access logging for any system with card data access.
- Data retention: PAN must not be retained after authorization unless business-justified.

## HIPAA (US Healthcare)

Applies if you're a Covered Entity (healthcare provider/plan) or Business Associate (vendor handling PHI — Protected Health Information).

**Three rules:**
- **Privacy Rule:** who can access PHI, for what purpose.
- **Security Rule:** administrative, physical, technical safeguards for ePHI (electronic PHI).
- **Breach Notification Rule:** notify individuals, HHS, sometimes media within 60 days.

**PHI:** anything linking a person to their health. Medical record, billing, appointment, lab, insurance — all PHI. Even "John Smith visited clinic X" alone can be PHI.

**Technical safeguards:**
- **Access control:** unique user ID, automatic logoff, encryption/decryption.
- **Audit controls:** record and examine activity in systems with PHI.
- **Integrity:** PHI not altered or destroyed improperly.
- **Person or entity authentication:** verify identity.
- **Transmission security:** encryption over networks (TLS).

**Business Associate Agreement (BAA):** contract required between Covered Entity and any Business Associate. Subprocessors need BAAs too. No BAA = HIPAA violation.

**Test patterns:**
- PHI access logging: every read + write logged with who, what, when, from where.
- Encryption at rest: ePHI in DB, backups, S3 — all encrypted.
- Encryption in transit: all endpoints TLS 1.2+.
- De-identification: Safe Harbor (remove 18 identifiers) or Expert Determination for research/analytics.
- Minimum necessary: queries return only fields needed; no `SELECT *` for PHI.

## Designing Features for Compliance

**Data classification** — tag fields:
- Public (marketing copy)
- Internal (non-sensitive business)
- Confidential (customer data not PII)
- Restricted (PII, PHI, PAN, secrets)

Use ORM/schema tags to enforce encryption, logging, access at the class level.

**Privacy-by-design defaults:**
- Opt-in, not opt-out, for non-essential tracking.
- Data minimization: collect only what's needed.
- Retention limits: automatic deletion after X days/months.
- Access restricted by role + need.

**Audit log requirements across frameworks:**
| Framework | Retention |
|---|---|
| GDPR | Sufficient for obligations; typically 1-3 years |
| SOC 2 | Usually 1 year (document your policy) |
| PCI DSS | 1 year (3 months immediately available) |
| HIPAA | 6 years |

Plan for longest applicable. Use cheap archive storage for older data (S3 Glacier).

## Common Compliance Engineering Mistakes

- **Treating compliance as "the auditor's problem."** Engineering owns the implementation; legal/compliance owns the interpretation.
- **"We'll get compliant before launch."** Compliance is an ongoing property, not a one-shot. Build it in.
- **Manual evidence collection.** Automating evidence is the ROI of a compliance program.
- **Data stores you forgot.** Spreadsheets, Notion pages, Slack — PII ends up there. Inventory + restrict.
- **Vendors without DPAs/BAAs.** Using Slack, Datadog, etc. for customer data without agreements.
- **No data map.** Don't know what data flows where. Fix: DPIA (Data Protection Impact Assessment) and data-flow diagrams.
- **Logs contain secrets/PII.** Mask at the logging boundary.
- **Tests run against production data.** Create synthetic or scrubbed test datasets.

## Cross-Framework Control Mapping (Indicative)

| Control | GDPR | SOC 2 | PCI DSS | HIPAA |
|---|---|---|---|---|
| Encryption in transit | ✓ | ✓ | ✓ Req 4 | ✓ |
| Encryption at rest | ✓ | ✓ | ✓ Req 3 | ✓ |
| Access control / MFA | ✓ | CC6 | ✓ Req 7,8 | ✓ |
| Audit logging | ✓ | CC7 | ✓ Req 10 | ✓ |
| Vulnerability mgmt | ✓ | CC7 | ✓ Req 6,11 | ✓ |
| Backup / DR | ✓ | A1 | ✓ | ✓ |
| Incident response | ✓ 72h | CC7 | ✓ Req 12 | ✓ 60d breach |
| Vendor mgmt (BAAs/DPAs) | ✓ | CC9 | ✓ | ✓ |
| Training | ✓ | CC1 | ✓ | ✓ |

One well-designed control program can satisfy multiple frameworks with one set of evidence.

## Audit Readiness Playbook

1. **Pick frameworks** applicable to your business + customer commitments.
2. **Do a gap assessment** — where current state meets/fails each control.
3. **Close gaps** with engineering + process changes.
4. **Document policies** — written, approved, versioned.
5. **Automate evidence** — Drata/Vanta/Secureframe or custom.
6. **Run internally** — dry-run with a consultant before the auditor.
7. **Audit** — formal with QSA (PCI), CPA firm (SOC 2), DPO review (GDPR).
8. **Maintain** — controls must operate continuously; not a one-time effort.
