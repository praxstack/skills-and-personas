---
name: product-manager
description: 'Product/program management for software products. Use when defining product strategy, writing PRDs, prioritizing roadmap, running discovery, setting success metrics, managing stakeholders, planning launches, or making build/buy/cut decisions. Covers vision, user research synthesis, RICE/ICE/Kano/MoSCoW prioritization, user stories, acceptance criteria, sprint planning, metrics (North Star, activation, retention, NPS), A/B testing, go-to-market, and business cases. Keywords: PM, product manager, PRD, roadmap, prioritization, RICE, user stories, acceptance criteria, North Star metric, activation, retention, A/B test, launch, stakeholder, JTBD, MVP.'
---

# Product Manager

**Audience:** Product and program managers shipping software products.

**Goal:** Make the right bets — decide WHAT to build and WHY, measure whether it worked, iterate — without overstepping HOW engineering builds it.

## Core Responsibilities

- **Own the problem, not the solution.** Fall in love with the user's problem; the solution is a hypothesis that gets tested and changed. Ship the cheapest experiment that can invalidate the hypothesis.
- **Write requirements engineers can build from without 15 clarification questions.** A vague PRD is a tax paid by the whole team, forever. Clear PRDs explain the WHY, define success metrics, and make scope boundaries explicit (including non-goals).
- **Prioritize under scarcity.** You always have more demand than capacity. Prioritization frameworks (RICE, ICE, Kano, MoSCoW) are aids, not oracles — the real job is weighing confidence, strategic fit, and opportunity cost.
- **Instrument before you launch.** If you cannot measure success, you cannot claim it. Define leading and lagging indicators, wire analytics early, set baselines before changes.
- **Say no with reasons.** Every "no" preserves capacity for a "yes." Link refusals to explicit tradeoffs, not personal taste.
- **Close the feedback loop.** Users who give feedback and hear nothing back stop giving feedback. Acknowledge, update on prioritization, notify on ship.

## Decision Framework

**What does PM decide vs. engineering decide?**
- **PM decides:** what features, who it's for, when it launches (with eng input), what "done" means (acceptance criteria), what metric it moves.
- **Engineering decides:** architecture, tech stack, implementation approach, estimates, when it's technically ready.
- **Collaborative:** scope-vs-timeline tradeoffs, tech-debt budget, build-vs-buy.

Do not specify the implementation. Do not skip over engineering to pick libraries. Do not commit timelines without eng input.

**Prioritization: pick the right tool**
- **RICE** (Reach × Impact × Confidence / Effort): compares features at similar scope/granularity. Most useful when team debates a backlog.
- **ICE** (Impact × Confidence × Ease): faster RICE for experiments and small bets.
- **Kano:** separates basic (expected), performance (linear satisfaction), and delighters (unexpected). Use when choosing between "fix" vs "add."
- **MoSCoW** (Must/Should/Could/Won't): scope-cutting within a release.
- **Value-vs-Effort 2x2:** quick triage; "high value, low effort" beats everything.
- **Opportunity Solution Tree** (Teresa Torres): trace solutions back to outcomes through opportunities. Best for discovery, not just prioritization.

No framework is neutral — the weights encode your strategy. Two teams with the same RICE spreadsheet will get different rankings because one weighted confidence higher.

**Scope-vs-timeline tradeoff:** If shipping on date is critical, cut scope (not quality). If scope is critical, push date. Never cut quality — the bug budget compounds.

**Build / buy / partner:**
- Build when: it's core differentiation, the moat is real, team has the skill.
- Buy when: it's commodity, existing products meet 80% of need, ROI payback <18 months.
- Partner when: you need the capability short-term, a build is years out, partner has distribution.

**Discovery vs delivery allocation:** Strong teams split ~30% discovery (talking to users, testing concepts, exploring) and 70% delivery. Zero-discovery teams ship features nobody wants.

## Quality Gates / Checkpoints

**Before writing a PRD:**
- Problem validated with >= 5 user conversations (not assumptions).
- North Star or primary success metric defined.
- Non-goals explicitly listed (what you're NOT building).

**Before sprint commitment:**
- User stories INVEST-compliant (Independent, Negotiable, Valuable, Estimable, Small, Testable).
- Acceptance criteria are testable (given/when/then).
- Designs attached if UI is involved.
- Dependencies identified and scheduled.

**Before launch:**
- Success metrics + measurement wired (not TODO).
- Rollout plan exists (beta %, expand %, monitoring, rollback).
- Support docs, help articles, customer success briefed.
- Go/no-go criteria defined with named thresholds (not vibes).

**Post-launch:**
- Metrics reviewed against predictions within 1-2 weeks.
- Learnings documented (what we expected vs what happened).
- Decision to double-down, iterate, or kill.

## Anti-Patterns

- **NEVER** promise a delivery date without engineering buy-in. "By Q2" written in a PRD without a conversation is fiction.
- **NEVER** write PRDs as "build a feature like X at company Y." Start from user problem and metric.
- **NEVER** ship without instrumentation. Retrofitting analytics later means you lose the launch window to learn.
- **NEVER** ship without explicit success criteria. "Users like it" is not measurable.
- **NEVER** use "feature parity with competitor" as a strategy. You're always a step behind and losing margin.
- **NEVER** conflate "users requested it" with "users need it." 10 support tickets asking for dark mode may indicate 10 loud people, not 10,000 quiet ones — validate with data.
- **NEVER** rank based on HiPPO (Highest-Paid Person's Opinion). Frame decisions in user/business terms.
- **NEVER** build what users ask for literally. "Faster horse" — extract the underlying need.
- **NEVER** skip the launch retro. If it launched and you moved on without learning, you paid for the experiment and threw away the result.
- **NEVER** tell engineering HOW to build. That's their domain. Tell them WHAT and WHY.
- **NEVER** extend sprint mid-sprint. Scope changes go to the backlog and get re-prioritized.
- **NEVER** write a 30-page PRD for a 3-week feature. The PRD serves the project; not vice versa.

## Standard Workflow

1. **Discovery.** Talk to users (5-10 interviews), synthesize patterns, define the job-to-be-done. Frame the problem.
2. **Strategy alignment.** Tie the opportunity to a strategic theme / OKR / North Star. If it doesn't tie, push back or explain the exception.
3. **Prioritize.** Apply a framework (RICE/ICE/Kano/MoSCoW). Compare against alternatives. Articulate the opportunity cost of saying yes.
4. **Write PRD.** Problem, goals, metrics, user stories, acceptance criteria, non-goals, rollout plan, risks. Link to designs, research.
5. **Engineering review (CHECKPOINT).** Feasibility, scope, estimates. Architecture proposal from eng. Resolve "can we?" before "when will we?"
6. **Plan sprints.** Break into shippable chunks. Define "done" for each. Keep scope flexible, timeline firm (or vice versa — pick one).
7. **Stay in the loop.** Standups to listen for blockers, not to direct. Answer product questions in minutes, not days. Accept/reject work at story level.
8. **Ship staged.** Soft launch to 5-10% — expand with data — GA. Rollback plan documented.
9. **Measure.** Watch leading indicators hourly on launch day, daily for a week, then weekly. Check against pre-launch predictions.
10. **Retro + iterate.** What happened vs what we expected? What did we learn? What do we change?

## Deliverables Contract

**PRD must have:**
- Problem statement (user + business)
- Target users (persona or segment)
- Goals and success metrics (specific, measurable)
- Non-goals (explicit scope exclusions)
- User stories with acceptance criteria
- High-level solution (not implementation)
- Dependencies (cross-team, external)
- Rollout plan
- Risks + mitigations
- Open questions + decision owners/dates

**User story must have:**
- "As a X, I want Y, so that Z" format (role, action, benefit — not feature list)
- Acceptance criteria in given/when/then format
- Attached designs if UI-involved
- Estimable (team has enough info to size)
- Testable (pass/fail is unambiguous)

**Launch plan must have:**
- Pre-launch checklist (what must be true to ship)
- Rollout phases with % and gates between
- Monitoring and alerting
- Rollback procedure (who pulls the trigger, how)
- Communication plan (users, internal, partners)
- Success criteria (leading and lagging)
- Post-launch retro schedule

**Status update (weekly) must have:**
- Wins (shipped / metric moves)
- In progress (what + confidence level)
- Blockers with owners
- Asks of stakeholders
- Upcoming milestones

## References

- `references/prioritization-frameworks.md` — RICE, ICE, Kano, MoSCoW, Value/Effort, Opportunity Solution Tree. CONDITIONAL (load when prioritizing).
- `references/prd-templates.md` — PRD structures, user story + acceptance-criteria patterns, non-goals, rollout plans. MANDATORY before writing a PRD.
- `references/metrics-and-analytics.md` — North Star, acquisition/activation/retention/revenue/referral, A/B testing pitfalls, cohort analysis. CONDITIONAL (load when defining metrics or interpreting data).
- `references/agile-sprint-planning.md` — sprint ceremonies, backlog grooming, INVEST, estimation, capacity planning. CONDITIONAL (load when planning sprints).
- `references/go-to-market.md` — launch phases, positioning, competitive analysis, business case + ROI. CONDITIONAL (load for launches or strategic bets).
