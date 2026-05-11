# Go-to-Market, Launches & Business Cases

**When to load this file:** Planning a launch, writing positioning/messaging, competitive analysis, or building a business case for a major investment.

## Launch Tiers — Pick the Right Size

- **Soft launch** (5-10% of users, limited announcement): validate the change, catch bugs, iterate. No press.
- **Public launch** (100%, full marketing, blog post, email): major feature, Product Hunt, press outreach.
- **Mega launch** (new product, pivot, rebrand): event, partnerships, paid blitz, press embargo.

Overlaunching = stakeholder disappointment. Underlaunching = wasted work. Match effort to strategic weight.

## Launch Timeline — 4 Weeks Out

**Week -4:**
- Finalize positioning and messaging
- Launch assets (blog post draft, video/screenshots, landing page)
- Support docs and FAQ
- Train customer success
- Sales enablement (if B2B)

**Week -3:**
- Beta to power users (100-500)
- Collect testimonials
- Fix critical bugs
- Draft press release + media list

**Week -2:**
- Announce launch date internally
- Email campaign scheduled
- Social/content calendar
- Product Hunt prep (hunter lined up, teaser)

**Week -1:**
- Final QA, load test
- Staging → production dry run
- Monitoring + alerting configured
- On-call schedule set
- Go/no-go meeting with explicit criteria

**Launch day (9am local):**
- Deploy (or flip flag)
- Smoke test in production
- Publish blog post, email blast, social posts, Product Hunt submission
- Monitor dashboards actively (first 4h critical)
- Respond on Product Hunt + social
- End-of-day checkpoint: metrics vs prediction

**Week 1 post-launch:**
- Daily metric review
- Urgent bug fixes
- Press + influencer follow-up
- Summary for leadership

**Weeks 2-4:**
- Iterate based on data
- Case studies from happy users
- Measure against success criteria
- Retro

## Positioning Statement (Moore / Crossing the Chasm)

```
For [target customer]
Who [need or opportunity]
Our [product] is a [category]
That [key benefit, reason to buy]
Unlike [primary competitive alternative]
Our product [primary differentiation]
```

Exercise: fill this out before any launch asset. If you can't, you haven't defined the product clearly enough to market it.

## Messaging Hierarchy

- **Tagline:** 5 words or less. Memorable. Sets the category or feeling.
- **Value proposition (primary):** one sentence. Problem → solution → benefit.
- **Proof points (3-5):** specific, quantified if possible.
- **Demo story / narrative:** "day in the life" showing the value.

Test messaging by paraphrasing back from users. If they can't restate it, rewrite.

## Category Framing

**Play in an existing category:** compete head-on. Easier to sell (users know the category) but margins compress and you're benchmarked.

**Create a new category:** harder sale (users don't know they need it) but you own the narrative. Salesforce created "CRM cloud"; Slack created "team chat."

**Reposition a competitor:** make the established player look old/wrong. Apple's "PC vs Mac." Risky but memorable.

For most products, play in an existing category with a clear differentiator. Only category creation when you have conviction + time + budget.

## Competitive Analysis

**Direct vs indirect competitors:** direct = solves same problem same way; indirect = solves same problem different way, or solves adjacent problem.

**Feature matrix** (for sales enablement, not strategy):

| Feature | Us | Competitor A | Competitor B |
|---------|-----|-------------|--------------|
| X | Strong | Weak | Missing |

**Competitive positioning (for strategy):**
- What do they DO well? (don't ignore their strengths)
- What do they DO poorly? (opportunity)
- What can you do that they STRUCTURALLY can't? (moat)
- What can you do they could copy in 6 months? (temporary advantage)

**Don't:** obsess over feature parity. Their roadmap isn't yours. Win on a clear dimension.

## Customer Acquisition

**Owned channels:**
- Website SEO, content marketing, blog
- Email list (build it from day one)
- Social (organic; inconsistent but free)

**Paid channels:**
- Google Ads (high-intent keywords)
- Facebook/Instagram (lookalike audiences for scale)
- LinkedIn (B2B targeting)
- Podcast sponsorships (brand)

**Earned channels:**
- Press coverage (PR outreach)
- Product Hunt, Hacker News, Reddit (community)
- Word of mouth (best; hardest to engineer)
- Reviews (G2, Capterra for B2B; App Store for consumer)

**Partnership channels:**
- Integration partners (cross-promote)
- Affiliates (pay for conversions)
- Resellers (especially enterprise)

Expect 2-3 channels to dominate. Don't spread thin across all.

## Unit Economics

**CAC (Customer Acquisition Cost):** total sales + marketing spend / new customers acquired (period).

**LTV (Lifetime Value):** average revenue per customer × gross margin × average retention lifetime.

**LTV:CAC ratio:**
- <1: losing money on every customer. Fix before scaling.
- 1-3: profitable but thin. Optimize.
- 3+: healthy. Scale.
- 5+: rare and suspicious — usually means you're leaving growth on the table by underinvesting in acquisition.

**Payback period:** months to recover CAC from customer revenue. <12 months for SaaS is healthy; >24 concerning.

## Business Case Template

```markdown
# Business Case: [Initiative]

**Author:** [PM] | **Decision by:** [Date]

## Executive Summary
- Proposal: [one line]
- Investment: [$ / person-months]
- Expected return: [$ / metric impact]
- Recommendation: APPROVE / HOLD / REJECT

## Problem
[Current state, pain, cost of inaction]

## Solution
[Proposed approach, scope, key features]

## Market Opportunity
- TAM / SAM / SOM
- Target segment size
- Pricing model

## Financial Projections
- Conservative / Base / Optimistic scenarios
- Year 1: revenue, users, costs
- Year 3 projection
- Break-even point
- ROI

## Risks & Mitigations
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|

## Success Metrics
- Leading (1-3 months): [...]
- Lagging (6-12 months): [...]

## Alternatives Considered
- Do nothing: [pros/cons]
- Partner: [pros/cons]
- Buy: [pros/cons]
- Build (recommended): [why]

## Recommendation
[Approve with phasing / further analysis / reject]

## Approval
- [ ] CEO / CPO
- [ ] VP Eng
- [ ] CFO
```

**Honest scenario planning:** if your "conservative" case is still optimistic, you'll lose credibility when reality hits. Model a real downside (nobody adopts; 10x slower than expected).

## OKRs vs North Stars

- **North Star:** enduring, years. "What we're fundamentally measuring."
- **OKRs:** quarterly. Ambitious, measurable, committed goals.

Good OKRs:
- 3-5 per team max.
- Objective is qualitative + aspirational; Key Results are quantitative.
- Scored 0-1.0 at end of quarter. 0.7 is success; 1.0 means sandbagged.

Bad OKRs:
- Tasks disguised as goals ("Ship feature X").
- Unmeasurable ("Improve product quality").
- Too many — dilutes focus.

## Launch Comms

**Email announcement (to users):**
- Subject line: benefit-driven, specific (not "New feature!")
- Preview text: expands subject; increases open rate
- Hero: value prop + image/screenshot
- How it works: 3 steps max
- CTA: one primary button; don't add 5 secondary links
- Footer: help link, unsubscribe

**Product Hunt:**
- Hunter lined up (relationship or paid)
- Launch 12:01am PT Tuesday/Wednesday (avoid Monday launches and weekends)
- Tagline: clear, benefit-driven
- Description: problem → solution → features → CTA
- Engage comments all day (not automated responses)

**Press release:**
- Headline: news-worthy, specific
- Dateline + hook in first paragraph
- Quote from CEO / founder
- Customer quote
- Boilerplate + contact

**Blog post:**
- Problem-first narrative
- Explain the "why now" (trend, data, user pain)
- Walkthrough with screenshots/video
- What's next / roadmap hint

## Common Launch Mistakes

- **Soft-launch as hide-and-hope:** not a launch, a release with no measurement plan.
- **No rollback plan:** when launch goes sideways, chaos.
- **Overhyping:** raising expectations the product can't meet; damages trust.
- **Launch day Friday:** no one's around to monitor weekends.
- **Ignoring compliance and legal:** data handling, claims, trademarks.
- **No post-launch measurement:** launched → moved on → no learning.
- **Trying to launch five things at once:** each dilutes the others.

## Post-Launch Retro Template

1. What did we predict? (metrics, adoption, response)
2. What actually happened?
3. Delta: surprises, over-performers, under-performers.
4. Root causes for deltas.
5. What we'd do differently next time.
6. What we keep doing.
7. Follow-up actions (owners, dates).

Store retros in a searchable place. Future launches should reference past ones.
