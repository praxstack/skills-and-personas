# Prioritization Frameworks

**When to load this file:** Comparing features, ordering a backlog, deciding between competing investments, or defending scope decisions.

## RICE (Intercom)

`Score = (Reach × Impact × Confidence) / Effort`

- **Reach:** how many people, per time period (e.g., per quarter). Be specific — "all users" is almost never the honest answer.
- **Impact:** per-user impact on the primary metric. Scale: 3 (massive), 2 (high), 1 (medium), 0.5 (low), 0.25 (minimal).
- **Confidence:** as a percentage. 100% = have data, 80% = strong evidence, 50% = informed guess, 20% = gut.
- **Effort:** person-months (or whatever unit is consistent).

**When to use:** comparing features of roughly similar scope. Useful for quarterly planning.

**Pitfalls:**
- Effort is gameable by eng (intentionally or not). Get estimates from the team, not the PM.
- Confidence is often anchored at 80% for everything — discipline to rate honestly.
- Reach × Impact × Confidence × Effort = 4 variables; small differences in each can flip rankings. Don't treat 1.1x differences as meaningful.
- RICE does not capture strategic fit, platform leverage, or risk reduction. Augment with qualitative judgment.

## ICE (Sean Ellis)

`Score = Impact × Confidence × Ease` (each 1-10).

Faster than RICE, less rigorous. Good for growth experiments and small bets.

**When to use:** rapid triage of experiment ideas, weekly prioritization of small items.

## Kano Model

Categorize features by user perception:

- **Basic / Must-Have:** users expect these. Presence causes no delight; absence causes dissatisfaction. (App doesn't crash. Data saves.)
- **Performance / Linear:** more is better. Satisfaction scales with investment. (Speed. Feature coverage.)
- **Delighters / Excitement:** unexpected positives. Absence causes no harm; presence creates enthusiasm. (A thoughtful animation, an automation nobody asked for that saves 10 minutes.)
- **Indifferent:** users don't care. Often over-invested in by teams who think they're delighters.
- **Reverse:** some users love, others hate. Make optional.

**When to use:** when debating "add delight" vs "fix what's broken." Basics come first. Delighters decay into performance and then into basics over time (what delighted in 2015 is table stakes now).

**Survey method:** ask pairs — "How would you feel if the product HAD this feature?" / "...DIDN'T have this feature?" Five answers each (like, expect, neutral, tolerate, dislike). Plot into Kano quadrant.

## MoSCoW

For scoping within a release or sprint:

- **Must:** core, non-negotiable. Release fails without them.
- **Should:** important but has workaround. Ship without if tight.
- **Could:** nice-to-have. First to cut.
- **Won't (this release):** explicitly out of scope — document so expectations are set.

**When to use:** final scope-cutting conversations with stakeholders. Forces explicit tradeoffs.

**Pitfall:** everything becomes "Must" if you let it. Force yourself to limit Musts to <60% of capacity.

## Value vs. Effort 2x2

| | Low Effort | High Effort |
|---|---|---|
| **High Value** | Do first (quick wins) | Strategic bets — plan carefully |
| **Low Value** | Fill-ins when blocked | Don't do |

**When to use:** weekly triage, fast decisions, visual tool for stakeholder alignment.

**Pitfall:** effort is known; value is estimated. Be suspicious of your own "high value" labels.

## Opportunity Solution Tree (Teresa Torres)

Outcome → Opportunities → Solutions → Experiments.

Traces every solution back to a desired outcome through validated opportunities (unmet needs observed from users).

Structure:
```
Outcome: Increase Day-7 retention from 35% → 45%
├── Opportunity: Users abandon after first task (observed 15 interviews)
│   ├── Solution: Onboarding tutorial
│   │   └── Experiment: A/B test tutorial completion → D7 retention
│   └── Solution: Smart default setup
└── Opportunity: Users can't find key feature (3 support tickets/week)
    └── Solution: Progressive disclosure with cue
```

**When to use:** for discovery-heavy teams, outcome-oriented roadmapping, and avoiding solution-jumping.

**Benefit:** prevents ranking solutions without validating the opportunity they address.

## WSJF (SAFe)

`Cost of Delay / Job Size` where Cost of Delay = User/Business Value + Time Criticality + Risk Reduction.

**When to use:** enterprise/regulated environments; programs with cost-of-delay reasoning. Not essential for most product teams.

## Choosing Between Frameworks

- Arguing over backlog order → RICE.
- Planning experiments fast → ICE.
- Debating quality fixes vs new features → Kano.
- Scope-cutting a release → MoSCoW.
- Stakeholder alignment in a meeting → Value/Effort 2x2.
- Outcome-driven discovery → Opportunity Solution Tree.
- Large programs, regulated environments → WSJF.

Pick one per decision type and stick with it for the quarter. Switching frameworks mid-quarter creates noise.

## Common Mistakes

- **Precision theater:** calculating RICE scores to 2 decimals and treating differences <20% as meaningful. RICE is an ordering aid, not a decimal-precise ranking.
- **Reach laziness:** "all users" for everything. If every feature has the same reach, reach isn't helping you rank.
- **Confidence inflation:** calling guesses 80% confident. Discipline yourself — 50% is often honest.
- **Ignoring strategic fit:** something can score high on RICE and still be wrong (distracts from core bet). Always a final strategic-fit gate.
- **Ignoring dependencies:** a high-RICE feature that requires another team's unprioritized work has lower true priority than the math shows.
- **Ignoring opportunity cost:** RICE compares features but not "do this" vs "do nothing and compound on existing work."

## Saying No (With Framework Backing)

Template:
> "Great idea. Here's how we prioritized it: [framework + score]. It ranks below [list of 3 items above it] because [reach/impact/effort reasoning]. If this is more urgent than one of those, here's which we'd defer. Otherwise, adding it to Q[X] roadmap — I'll update you when it moves up."

Not:
> "No, we're busy."

Or:
> "Sure, we'll add it" (and then not).

The goal is a real tradeoff conversation, not consent or avoidance.
