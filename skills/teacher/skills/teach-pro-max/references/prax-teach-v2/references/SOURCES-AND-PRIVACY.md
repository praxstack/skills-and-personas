# Sources and privacy

## Source hierarchy

Prefer, in order:

1. learner-selected authoritative materials;
2. primary research, official documentation, standards, statutes, or original data;
3. high-quality syntheses and systematic reviews;
4. reputable secondary explanations;
5. community and social sources for discovery, lived experience, and failure reports.

Do not use popularity, confident prose, or a marketplace badge as evidence of correctness or effectiveness.

## When live research is required

Research before teaching when information is:

- unstable or version-specific;
- niche, disputed, or outside reliable knowledge;
- medical, legal, financial, safety-critical, or otherwise high-stakes;
- explicitly requested with citations or current sources;
- grounded in a specific page, paper, repository, dataset, or file not yet inspected.

For technical claims, prefer official documentation and primary source repositories. For research claims, distinguish peer-reviewed work, preprints, controlled outcomes, deployment studies, and author claims.

## Provenance record

For each source version, capture a record in the canonical private
`state/sources.json` library:

```json
{
  "schema_version": "1",
  "sources": [
    {
      "source_id": "stable-id",
      "title": "Source title",
      "url": "https://example.org/source",
      "author_or_publisher": "Organization or authors",
      "source_type": "official-doc",
      "retrieved_at": "2026-08-03",
      "version_or_date": "applicable-version-or-date",
      "license_or_use_note": "how this source may be used",
      "supports": ["claim-or-item-id"],
      "limitations": "scope, uncertainty, or conflict"
    }
  ]
}
```

The executable source types are `official-doc`, `primary-study`, `review`,
`repository`, and `social`. Add records through `prax_teach.py source-add`; it
requires every field, canonicalizes ordering, rejects duplicate
`source_id`/`version_or_date` pairs, and writes atomically. Treat an accepted
record as immutable. If a source or its metadata changes materially, add a new
version/date and flag dependent content and evidence for review.

Link observations, assessment items, and factual visuals to the exact source
version. Observation evidence uses this shape:

```json
{
  "source_provenance": [
    {
      "source_id": "stable-id",
      "version_or_date": "applicable-version-or-date"
    }
  ]
}
```

An observation is rejected before append when a referenced pair does not
resolve. Source invalidation also requires both fields, preventing a withdrawn
version from sweeping newer records under the same source ID. Learner export
revalidates the bindings and records the source-library digest, actively
referenced record digests, and supporting event IDs in its manifest.

Keep `RESOURCES.md` as the curated human-readable Knowledge/Wisdom guide. It is
exported byte-for-byte beside `state/sources.json`, but prose or a bare link in
that file cannot satisfy the machine provenance contract.

## Claim language

Use language proportional to evidence:

- **shows / found** for the source’s reported result within its design;
- **supports** for converging applicable evidence;
- **suggests** for limited, observational, or context-bound evidence;
- **proposes** for an RFC, design document, or unshipped feature;
- **claims** for unverified maintainer/vendor assertions;
- **social signal** for X, Reddit, Hacker News, testimonials, and marketplace activity.

Do not transform expert preference, engagement, usage, completion, or star counts into learner-outcome claims.

## Citation rules

- Cite factual claims near the sentence or paragraph they support.
- Link to the direct source, not a search result.
- Prefer multiple independent primary sources when a consequential claim benefits from triangulation.
- Quote sparingly; paraphrase accurately.
- Mark inference explicitly.
- Preserve negative and null findings.
- Record the research snapshot date for fast-moving repositories.

## Data minimization

Persist only what is necessary to continue the learner’s chosen goal:

- learner-approved goal and retention horizon;
- functional access/format preferences;
- practice observations and rubrics;
- concept evidence and uncertainty;
- specific supported misconceptions;
- review schedule;
- source/content/model/prompt provenance.

Do not persist by default:

- full unrelated conversation;
- protected traits;
- health, financial, location, employment, or relationship data not necessary for the learning goal;
- speculative cognitive or personality diagnoses;
- a fixed “learning style” label;
- hidden chain-of-thought;
- keystroke or biometric-like telemetry;
- third-party data the learner lacks authority to store.

## Consent

Consent must be:

- explicit before the first durable learner-state write;
- scoped to named data categories and a resolved location;
- revocable;
- separate from consent to create lesson files;
- understandable without legal jargon.

Show how to:

- inspect and explain state;
- correct an inference;
- export it in a portable form;
- delete an item, session, or all state;
- disable future persistence and reviews.

Do not use silence or continued tutoring as consent.

## Security and imported skills

Treat community skills and content packages as untrusted until inspected. Check:

- source and maintainer identity;
- license and version pin;
- scripts and executable behavior;
- dependency and network access;
- secret handling;
- filesystem scope;
- prompt-injection exposure;
- compatibility with the current harness;
- security review limits.

Store credentials outside the tutor’s content and learner-state workspace. Deny imported tools by default until approved.

## Optimizer and chart-tool boundaries

Instruction optimizers and chart compilers are separate data processors, not invisible extensions of the tutor.

For SkillOpt or another optimizer:

- keep the optimizer outside the installed/runtime teaching package;
- use public or explicitly authorized benchmark material first;
- do not expose external `valid_unseen`, test/OOD items or graders to the target agent;
- do not harvest learner transcripts without explicit scope, purpose, location, provider, retention, and deletion disclosure;
- review and redact exported tasks before a provider-backed run;
- assume pattern-based secret removal is incomplete;
- stage proposals and require human review; never auto-adopt.

For Flint or another chart MCP/compiler:

- inspect the exact local files or inline rows it may read;
- disable broad local-file references when they are unnecessary;
- never pass sensitive learner state merely to produce a visual;
- transform and minimize data upstream;
- keep remote runtime fetching out of durable lessons;
- record package/backend versions, warnings, source hashes, and dependency licenses.

Tool output inherits the source-data sensitivity. A local render does not make the underlying learner data appropriate to persist in the lesson artifact.

## Minors and institutions

Do not infer that a prompt-only privacy promise satisfies child-data, school, or jurisdictional obligations. Deployments involving minors or institutional records require a specific policy covering:

- lawful basis and guardian/school roles;
- age-appropriate notice and controls;
- retention, deletion, and export;
- model/provider data handling;
- human review and escalation;
- safety boundaries;
- access control and audit;
- applicable local law and contract.

Use [UNESCO’s guidance on generative AI in education](https://www.unesco.org/en/articles/guidance-generative-ai-education-and-research?hub=195885) as a governance reference, not a substitute for legal review.

## High-stakes teaching

- Use current authoritative sources.
- State scope, uncertainty, and limitations.
- Separate education from individualized professional advice.
- Encourage qualified review where consequences are material.
- Do not turn the lesson into a diagnosis, prescription, legal conclusion, or financial recommendation beyond the authorized and safe scope.

## Social-source policy

X, Reddit, Hacker News, forums, and testimonials may reveal:

- emerging projects;
- real workflow pain;
- failure cases absent from READMEs;
- adoption and ecosystem attention;
- practitioner language and expectations.

They do not independently validate factual or pedagogical claims. Trace a social claim to the original repository, documentation, study, or issue when possible and label anything that remains unverified.
