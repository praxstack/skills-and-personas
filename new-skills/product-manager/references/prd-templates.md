# PRD Templates & User Story Patterns

**When to load this file:** Writing a PRD, breaking scope into user stories, or defining acceptance criteria.

## PRD Structure (Full Version — Use for Significant Features)

```markdown
# PRD: [Feature Name]

**Author:** [PM] | **Status:** Draft/Review/Approved | **Target:** Q[X]

## Overview

### Problem Statement
[One paragraph. What user/business problem are we solving? Include data.]

### Goals
- [Goal 1, measurable]
- [Goal 2, measurable]

### Success Metrics
- **Primary:** [metric] — baseline [X], target [Y]
- **Secondary:** [metric, metric]
- **Guardrails:** [metric that must NOT degrade]

### Non-Goals
- [Thing we are explicitly NOT doing, with rationale]
- [Thing that might seem in-scope but isn't]

## User Research
### Target Users
[Segment, persona, size of opportunity]

### Insights
[Quotes, survey data, behavioral evidence — the WHY]

### User Stories
1. As [role], I want [action], so [benefit]
2. ...

## Solution

### Approach
[High-level. Not implementation. Describe WHAT, let eng decide HOW.]

### UX
[Link to designs. Key screens/flows.]

### Requirements
**P0 (must-have):**
- [Requirement, with acceptance criteria]

**P1 (should-have):**
- [...]

**P2 (could-have / next iteration):**
- [...]

### Non-Functional
- Performance: [p95 latency, throughput]
- Scalability: [user load, data volume]
- Accessibility: WCAG 2.1 AA
- Security/privacy: [data classification, compliance constraints]

## Dependencies
- [Other teams, external services, feature flags, migrations]

## Rollout
- Phase 1 (Week 1): 5% beta, power users
- Phase 2 (Week 2): 25%, A/B vs baseline
- Phase 3 (Week 3): 100%, opt-out available
- Rollback plan: [condition, who decides, procedure]

## Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|------------|------------|

## Open Questions
- [Question, owner, decision needed by]

## Appendix
- Competitive analysis
- Analytics baseline
- User quotes
```

## Lightweight PRD (for smaller features)

```markdown
# [Feature]

**PM:** [Name] | **Status:** [Draft/Approved] | **Target:** [Sprint / Date]

## Problem
[What user problem? Include evidence.]

## Solution
[High-level approach.]

## Goals & Metrics
- [Metric]: [baseline → target]

## Requirements
**Must:**
- [...]
**Nice-to-have:**
- [...]

## Non-Goals
- [...]

## Design
[Figma link]

## Rollout
[Simple: ship → 100% or flag]
```

Match depth to risk. A 3-week bug-fix doesn't need a 30-page PRD.

## User Story Template

```
As a [specific role]
I want [action/capability]
So that [benefit / outcome]
```

**Good:**
> As a busy professional, I want my tasks auto-prioritized, so I can start on what matters without deciding.

**Bad (feature list, not role/benefit):**
> As a user, I want a priority column that sorts by deadline.

The story captures the WHY. The acceptance criteria capture the WHAT.

## Acceptance Criteria — Given/When/Then

```
Given [preconditions]
When [user action]
Then [expected outcome]
And [additional outcome]
```

Example:
```
Given I have 20+ tasks with varied deadlines
When I open the app
Then I see my top 3 tasks displayed prominently
And each task shows its priority score (0-100)
And tasks are ranked by deadline urgency + user importance
And the ranking updates in real-time when I edit a task
```

**Rules:**
- One concrete, testable assertion per criterion.
- Cover happy path, error paths, edge cases.
- Include performance and accessibility where relevant ("Load within 500ms at p95" / "Screen reader announces priority change").
- Match exactly what QA would test.

## INVEST Check

Every story should be:
- **Independent:** can be built/shipped without blocking on another story (unless explicit dependency documented).
- **Negotiable:** details can flex; scope can shrink.
- **Valuable:** delivers user or business value on its own.
- **Estimable:** team has enough info to size it.
- **Small:** fits within one sprint (ideally 2-5 days of work).
- **Testable:** clear pass/fail; acceptance criteria written.

If a story fails INVEST, decompose or clarify before committing.

## Edge Case Checklist (Always Cover)

- Empty state — first-time user, no data
- Error state — API fails, network dies, validation errors
- Loading state — slow network, long operations
- Offline — if applicable, what's supported
- Long content — text overflow, many items
- Permissions / auth — logged out, insufficient role
- Concurrent actions — two tabs, two devices
- Back/forward navigation — state preserved or reset?
- Onboarding / first use — tooltips, guided moment?

Design only covering happy path is half-done. PRD that doesn't enumerate edge cases is fiction.

## Non-Goals Section (Underused)

List things that might seem in-scope but aren't, and explain why. Prevents:
- Scope creep mid-sprint
- Stakeholder disappointment
- Misaligned expectations with support/marketing

Example non-goals for smart prioritization feature:
- Team task assignment → future iteration
- Time tracking → separate feature area
- Calendar event creation → integration only, not creation
- Mobile widget → next release

## Rollout Plans That Work

**Staged rollout (safer):**
1. Internal (dogfood) → 100% for employees.
2. Beta → 5-10% opt-in power users or high-engagement cohort.
3. Gradual GA → 25% → 50% → 100% with gates between (error rate, adoption, CSAT).
4. Feature flag retained for 2+ weeks post-GA for fast rollback.

**Gate criteria at each phase:**
- Crash rate <X%
- Error rate <Y%
- Adoption by target segment >Z%
- No P0/P1 bug reports
- CSAT within 10% of baseline

**Rollback triggers must be pre-defined.** "We'll see how it goes" is not a plan.

## Common PRD Mistakes

- **No success metric.** PRD ships a feature but no one can tell if it worked.
- **No non-goals.** Scope balloons silently.
- **Solution prescribed.** PRD dictates implementation, engineers feel boxed, worse outcome.
- **No rollout plan.** Launch = 100% on a Friday. Disaster.
- **No rollback plan.** When things break, chaos.
- **Research-free.** Reads like a PM's opinion. Engineering pushes back hard when they should.
- **Walls of prose.** No one reads >5 pages. Use tables, bullets, subheadings.
- **No owner on open questions.** Decisions don't get made.
- **Review comments unresolved.** Signed off without addressing concerns.

## Acceptance Review (PM's Job After Engineering Ships)

Before accepting:
- Does it meet ALL P0 acceptance criteria?
- Do all states work (empty, error, loading, success)?
- Is it accessible (keyboard, screen reader, contrast)?
- Does it hit performance targets?
- Are edge cases handled?
- Is analytics wired and reporting?
- Is the success metric measurable now?

If yes → accept, ship.
If minor issues only → accept with logged follow-ups.
If blockers → reject with specific list; don't send vague "doesn't feel right."
