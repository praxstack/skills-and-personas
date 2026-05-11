# Agile, Sprint Planning & Backlog

**When to load this file:** Planning a sprint, grooming backlog, running ceremonies, or coaching a team on agile practices.

## Sprint Cadence — 2 Weeks Is the Default

1-week sprints: too much overhead relative to work; ceremonies eat too much.
3-week+: feedback loop too slow; changes accumulate.
2-week: sweet spot for most product teams.

Exceptions:
- Heavy infra/research projects: monthly "cycles" (Shape Up style) can work better.
- Critical incident weeks: suspend sprint, go to incident-response cadence.

## Sprint Ceremonies

**Sprint planning (90-120 min, once per sprint):**
1. Review previous sprint (15 min): what landed, what carried over, velocity.
2. Present sprint goal (10 min): one sentence capturing the why.
3. Story walkthrough (60 min): PM explains each, team questions, engineering estimates.
4. Capacity check (15 min): PTOs, carryover, buffer for unknowns.
5. Commit (10 min): team commits to scope, not PM alone.

PM rules during planning: do NOT anchor estimates ("this should be 3 points"). Let engineering discover.

**Daily standup (15 min max):**
Each person: yesterday, today, blockers. Keep tight; take detailed discussion offline.

PM role: listen for blockers, answer product questions in real time if possible, capture async.

Anti-pattern: standup as status meeting for leadership. That's a different meeting.

**Sprint review / demo (60 min):**
Demo what shipped to stakeholders. Not a progress report — a demonstration of working software.
Capture feedback; add to backlog if relevant. Don't redesign in the meeting.

**Retrospective (60 min):**
Format: went well / to improve / action items.
Private to team; safe space for honest critique.
Action items have owners and deadlines. Without them, retros are catharsis theater.

Every 4-6 sprints, run a "meta-retro" on the retro itself — are action items actually happening?

## Capacity & Estimation

**Story points, not hours:** points reflect relative complexity; hours create false precision and pressure.

Scale: Fibonacci (1, 2, 3, 5, 8, 13). Past 13, break down.

**Velocity:** rolling 3-sprint average of completed points. Use for capacity planning, not performance.

**Anti-patterns:**
- Estimating in hours then calling them "points" — loses the abstraction benefit.
- Using velocity as a team performance metric — gameable; creates incentive to inflate.
- Planning to 100% velocity — leaves no buffer for bugs, support, unknowns. Target 70-80%.
- Rolling over partial stories sprint after sprint — either finish or reset the estimate.

## Backlog Hygiene

**Structure:**
- **Now (next 2 sprints):** groomed, estimated, designs attached, ready to pull.
- **Next (2-4 sprints):** rough estimates, goals clear, details TBD.
- **Later (quarter+):** themes and initiatives, not stories yet.
- **Icebox:** considered and deprioritized; revisit on trigger events.

**Grooming criteria — story is "ready" if:**
- User story written (role/action/benefit)
- Acceptance criteria defined and testable
- Designs attached (if UI)
- Dependencies identified
- Estimated by team (not PM)
- Open questions answered
- Engineering has reviewed for feasibility

Run grooming 1-2x per sprint (30-60 min). Keep the "Now" column >= 1.5 sprints of ready work so team is never blocked on missing specs.

**Backlog bloat:** if your backlog has 500 items, half are noise. Prune ruthlessly — stale items never become priorities. Archive > 6 months old.

## Definition of Done

Team-wide standard for "complete":
- Code merged to main
- Unit tests written, coverage >= team threshold
- Integration/E2E tests updated
- Code reviewed
- Security scan passed
- Documentation updated (changelog, API docs, help content)
- Deployed to staging
- PM has accepted (matches acceptance criteria)
- Analytics wired and reporting

If any are deferred ("we'll write tests later"), that's debt. Log it explicitly.

## Handling Mid-Sprint Scope Changes

Default: no. Scope is fixed when sprint starts.

Exceptions:
- P0 bug (production outage, security incident).
- Customer-blocking issue requiring < 1 day.
- Small swap: remove something equivalent to make room.

How to say no to mid-sprint requests:
> "That's important. It goes into next sprint's planning — I'll prioritize it against what else is there. If it's urgent enough to replace something in this sprint, tell me what to cut."

## Sprint Goal

One sentence that captures WHY this sprint matters. Team can invoke it when deciding tradeoffs.

Good: "Ship smart prioritization MVP to 5% beta users with the minimum needed to test engagement."

Bad: "Complete stories 101-108."

The goal survives even if individual stories shift.

## Team Working Agreements

Written norms the team commits to. Examples:
- Standup at 10am sharp, no late starts.
- PR review within 24 hours.
- No merges on Fridays after 3pm.
- Focus-time blocks Wed afternoons.
- Pair programming encouraged for tricky bits.

Violations addressed in retro, not in the moment.

## Common Sprint Failures

- **Overcommitment:** team pulls more than capacity; ends sprint with carryover; morale suffers.
- **Context-switching overload:** team works on 5 features at once; nothing ships; cycle time long.
- **Unclear acceptance criteria:** stories bounce back and forth; rework kills velocity.
- **PM unavailable mid-sprint:** engineering blocks on questions, context-switches.
- **Silent design review:** designs change without engineering awareness, causing late rework.
- **Retros without action items:** team vents but nothing improves.

## Beyond Scrum: Kanban & Shape Up

**Kanban:** continuous flow, WIP limits, no fixed sprints. Better for ops-like teams or heavy support load.

**Shape Up** (Basecamp): 6-week cycles with 2-week cooldown. "Shaped" work is scoped before engineers see it. No retros per cycle but a bigger "appetite" check. Works for product teams that can tolerate longer commit cycles.

Neither is magic. Pick based on work type:
- Continuous, interrupt-heavy → Kanban.
- Project-based, bounded → Scrum or Shape Up.
- Mixed → dual-track (Kanban for support + scrum for projects).

## PM's Role in Sprint

- Available for product questions (minutes, not days).
- Accept or reject stories against acceptance criteria — not vague "feels off."
- Protect team from mid-sprint scope attacks.
- Prepare the next sprint's backlog continuously, not the night before planning.
- Participate in standup as listener; don't turn it into status reporting.
- Attend retros with a learning mindset — your process errors surface there.
- Advocate for the user voice when engineering wants to cut scope they shouldn't.

## Escalation Patterns

**Team says "can't finish all P0 by sprint end":**
- Which P0 would you cut?
- Can we swap P0 for P1 if it's less risky?
- Is the estimate wrong or is there an unexpected blocker?

**Stakeholder wants feature added mid-sprint:**
- RICE score the new request vs current sprint items.
- If it wins, negotiate what to cut.
- If it doesn't, schedule for next sprint with clear commitment.

**Engineering pushes back on scope:**
- Listen. They usually have information PM lacks.
- Ask: what's the underlying concern? (complexity, unknown, architecture risk)
- Offer reduced scope or split story. Don't insist on original scope by authority.
