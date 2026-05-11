# Resource Enrichment — Authenticated Flow

## When to load this file

Load when the pipeline needs to enrich transcript notes with links to authenticated resources (Notion pages, Canva designs, Google Drive files, company wiki entries) that the learner or team maintains.

## Purpose

Raw notes are complete but isolated. Enrichment connects each major topic to its canonical resource so the learner can dive deeper, and so the note becomes a navigational hub.

## Preconditions

- The user has access tokens / credentials for the target systems (Notion, Canva, Google Drive, Confluence, etc.)
- The pipeline runs in a context that can make authenticated requests (local machine with tokens, CI with secrets, or authorized agent)
- The notes have topic placeholders marked from Stage 3/4

## Flow

### 1. Discover candidate resources per topic

For each major topic in the notes:

- Search the user's Notion workspace for matching page titles and content
- Search Google Drive for files with matching keywords
- Search Canva for designs with matching project names
- Search the team wiki / Confluence for pages on the concept

Collect top 3-5 candidates per topic with:
- URL
- Title
- Last modified date
- Snippet / first-paragraph preview
- Access level (who can see it)

### 2. Rank candidates

Ranking signals:
- **Recency** — last modified within 90 days scores higher than 2 years old
- **Author match** — resources authored by the learner or their team score higher
- **Title match** — exact topic phrase in title outranks fuzzy match
- **Content depth** — resources with substantial content outrank one-line placeholders
- **Access level** — resources the learner can actually open outrank restricted ones

### 3. Human-in-the-loop selection

Present candidates to the user per topic:

```
## Topic: Distributed consensus (Raft)
Candidates:
1. [Notion] "Raft implementation notes" (updated 2026-03-12, you) — 3000 words
2. [Drive] "systems-design-week3.pdf" (updated 2026-01-08, team) — 42 pages
3. [Canva] "Raft state diagram v4" (updated 2026-03-14, you) — diagram

Select 1-3 to attach, or [s]kip, or [n]ew search.
```

Default: auto-select top 1 per topic if confidence > 0.8; otherwise ask.

### 4. Inject links into notes

Replace placeholder slots with actual links:

```markdown
Before: 🔗 [resource slot: distributed consensus]
After:  🔗 **Related resources:**
        - [Raft implementation notes (Notion)](https://notion.so/...)
        - [Raft state diagram (Canva)](https://canva.com/...)
```

### 5. Verify link accessibility

After injection, verify the user can actually open each link:
- HTTP 200 response
- Expected title in page metadata matches notes context
- Access level check — if the link requires auth the learner doesn't have, flag it

## Security and privacy

- **Never log tokens or credentials.** Redact bearer tokens from any error messages.
- **Respect resource privacy.** If a candidate resource is shared with the user but not public, note the access scope in the injected link.
- **Don't embed private content inline.** Link to the resource; don't copy its content into the notes (the note may be shared more broadly than the source).
- **Obey workspace data-residency rules.** If the Notion workspace is EU-region, don't route queries through non-EU services.
- **Audit log.** Record which resources were searched, which were selected, and what got injected — so the flow is auditable.

## Failure modes

| Failure | Fix |
|---|---|
| Token expired | Surface to user with re-auth instructions; don't silently skip enrichment |
| No candidates found for a topic | Leave placeholder with `[enrichment slot empty — add manually]` |
| Too many candidates (>10) | Tighten search with title-match weighting |
| Private candidates for a shared note | Flag the link with `(private — you may need to share)` |
| Rate limit | Queue and retry with exponential backoff |

## Output contract

The enriched notes file:
- Has every Stage 3/4 topic either linked to at least one resource or explicitly marked `(no enrichment)`
- Preserves all source content and enhancement markers
- Adds a "Related resources" section at the bottom listing all linked resources grouped by source system

## Integration with other stages

- Runs after Stage 4 validation (so the note is canonical before enrichment)
- Produces `final-notes-enriched.md`
- Should be re-runnable (idempotent): re-running should update stale links, not duplicate them
