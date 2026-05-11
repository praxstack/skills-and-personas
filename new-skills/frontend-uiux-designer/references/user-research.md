# User Research & Testing

**When to load this file:** Running interviews, planning usability tests, writing personas, or interpreting research data.

## What Research To Run When

| Goal | Method | Sample size |
|------|--------|-------------|
| Understand motivations, mental models | 1:1 interviews | 5-10 per segment |
| Observe actual behavior, find workarounds | Contextual inquiry (shadow at work) | 3-5 |
| Validate a solution concept | Usability testing on prototype | 5-8 |
| Compare two designs | A/B test | Thousands (stat sig) |
| Measure satisfaction, track over time | NPS/CSAT | 100+ responses |
| Map content to user mental models | Card sorting (Optimal Workshop) | 15-30 |
| Find friction on live product | Session recordings (Hotjar, FullStory) | Browse hundreds, analyze tens |
| Quantify a specific question | Survey | 100+ |

**5-user rule (Nielsen):** 5 users uncover ~85% of usability issues in moderated testing. Past 8, you're rediscovering the same issues. Run a second round of 5 after iterating.

## Interview Protocol

Structure (60 min):
1. Intro + consent + recording setup (5)
2. Warm-up: role, day-to-day, tools used (5)
3. Current behavior walkthrough: "Show me how you [do task]" (20)
4. Needs/motivations: "What would make this easier?" "What matters most?" (15)
5. Concept testing if applicable: "What do you think this is?" "How would you use it?" (10)
6. Wrap: "Anything else?" "Can we follow up?" (5)

**Good questions:**
- "Tell me about the last time you..."  (specific episode, not hypothetical)
- "Walk me through how you..." (behavior, not opinion)
- "What's most frustrating about..." (pain, not features)
- "Why is that important to you?" (probe motivation)
- "Can you show me?" (artifact-based, not recollection)

**Avoid:**
- Leading: "Don't you think X is better?"
- Hypothetical: "Would you use this?" (people overestimate intent)
- Multiple in one: "Do you like X and would you pay for it?"
- Yes/no: Prefer open-ended for qualitative.

**Silence is a tool.** After the user stops talking, wait 3-5 seconds. They often add the more important part.

## Personas — Only If You'll Actually Use Them

Personas fail when they become demographic fiction no one reads. Make them behavior-based and reference them in design reviews.

Include only what changes decisions:
- **Jobs to be done** (functional, emotional, social)
- **Pain points** that design can address
- **Behaviors and context** (devices, frequency, environment)
- **Motivations** that drive choice
- **Tech-savviness level** (affects how much guidance to provide)

Skip unless relevant: age ranges, generic demographics, stock photos.

## Jobs To Be Done (JTBD)

Framing: "When [situation], I want to [motivation], so I can [expected outcome]."

Good JTBD:
- "When I get a new task, I want to know if it's urgent, so I can decide whether to handle it now or later."

Bad JTBD (too specific to a solution):
- "When I use the task app, I want an urgent label, so I can see priority."

JTBD separates problem from solution. Many solutions can satisfy one JTBD.

**Forced ranking survey** — ask users to rank 5-10 JTBDs by importance. Reveals priorities beyond what they volunteer unprompted.

## Usability Testing

**Moderated** (with facilitator): deeper insights, slower, more expensive. Best for new concepts, ambiguous UX.

**Unmoderated** (tools like UserTesting, Maze): faster, cheaper, scales. Best for validation, specific task success.

**Think-aloud protocol:** Ask users to narrate their thoughts. Reveals confusion even when they complete tasks.

**Tasks must be realistic scenarios, not commands.**
- Good: "You just got a new project at work — use this tool to get started."
- Bad: "Click the 'New Project' button."

**Metrics:**
- Task success rate (target >80% for core flows)
- Time on task (compare against baseline)
- Error rate (<3 errors is healthy)
- Post-task satisfaction (1-5 rating)
- System Usability Scale (SUS) — 10 questions, 0-100; >68 above average, >80 excellent

**Severity rating for findings:**
- Critical: user cannot complete task
- High: significant delay/frustration, users recover
- Medium: minor friction, workaround found
- Low: cosmetic or preference

Prioritize fixes by impact × frequency, not severity alone.

## Analytics & Quant Research

**Funnel analysis:** Identify stage-to-stage drop-offs. Big drop = friction point to investigate qualitatively.

**Cohort analysis:** Retention by signup week. Reveals whether changes affect specific cohorts or all users.

**Heatmaps / click maps:** Where users click, scroll, pause. Hotjar, Microsoft Clarity. Useful for validating attention, limited for causation.

**Session recordings:** Watch 10-20 real sessions of a specific flow before making a design change. Qualitative insight at quantitative scale.

**A/B testing rules:**
- One variable per test. Multivariate only if you have traffic for it.
- Define primary metric BEFORE running, not after.
- Reach statistical significance (>95% confidence), and minimum sample size (use calculators).
- Run for full business cycle (usually >= 7 days) to cover weekday/weekend effects.
- Don't peek and stop early — p-values aren't valid if you do.
- Monitor guardrail metrics (don't improve primary at the cost of retention).

## Survey Design

- Start with easy questions (warm-up), then harder, then demographics last.
- Use 5- or 7-point Likert scales (odd so neutral exists).
- NPS: "How likely are you to recommend X?" on 0-10. Calculate: %promoters (9-10) − %detractors (0-6).
- Avoid double-barreled questions ("Is it easy to use and fast?").
- Keep surveys <5 minutes; completion rates crater past that.
- Open-ended questions at the end — they drop off those but complete the quant first.

## Journey Mapping

For each stage (awareness → consideration → onboarding → usage → retention → churn):
- User actions
- Thoughts
- Emotions (feel/happy/frustrated)
- Pain points
- Opportunities
- Touchpoints (where interaction happens — product, email, support)

Use to prioritize fixes by emotional low points (frustration spikes).

## Research Operations

- **Recruiting:** Existing users (segmented by behavior), customer list, User Interviews / Respondent.io, social recruiting, screen with a pre-survey.
- **Incentives:** $50-150 per hour for consumer; $200-400 for enterprise/specialized roles.
- **Consent + recording:** Always get explicit consent for recording and sharing clips.
- **Privacy:** Don't share PII. Redact or pseudonymize in notes shared with broader team.
- **Triangulation:** Confirm findings across methods. A single interview is a hypothesis, not a fact.

## Common Pitfalls

- Asking users what they want instead of observing what they do. ("Faster horse.")
- Leading the witness by reacting positively to certain answers.
- Recruiting only happy users (survivorship bias). Talk to churned users too.
- Small sample qualitative → quantitative conclusions. 5 interviews cannot tell you "60% of users...".
- Research theater: doing research to justify a decision already made.
- Not synthesizing: hours of interviews with no themes, insights, or actions.
