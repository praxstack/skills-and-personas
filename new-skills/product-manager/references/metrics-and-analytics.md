# Metrics, Analytics & Experimentation

**When to load this file:** Defining success metrics, designing A/B tests, interpreting analytics, or setting OKRs.

## The Metric Hierarchy

```
Company goals (annual, revenue-level)
  ↓
Product goals (annual, user-level)
  ↓
North Star metric (ongoing, captures core value)
  ↓
Input/driver metrics (weekly, move the NSM)
  ↓
Feature metrics (per feature, adoption/engagement)
  ↓
User events (raw instrumentation)
```

Each level should be derivable from the one below.

## North Star Metric — Rules

Good NSM:
- **Measures customer value** (not revenue directly — revenue is a consequence).
- **Reflects business health** (correlates with long-term growth).
- **Actionable** — team can influence it with features.
- **Leading indicator** — moves before revenue does.

Examples:
- Airbnb: nights booked
- Spotify: time spent listening
- Slack: messages sent in teams of 3+ (qualifier matters)
- Uber: rides completed
- Netflix: hours watched
- LinkedIn: endorsements given

**Pitfall:** picking a metric that's easy to game (DAU without quality qualifier leads to notification spam).

**Good NSM has a quality qualifier:** "active users who completed a core task" beats "visits."

## AARRR (Pirate Metrics)

Dave McClure's framework — still the cleanest mental model:

1. **Acquisition** — visits, signups. Who comes in?
2. **Activation** — first value delivered. Who hits the "aha moment"?
3. **Retention** — who comes back? Day 1 / Day 7 / Day 30.
4. **Revenue** — paying, MRR, LTV.
5. **Referral** — who brings more?

Pick 1-2 metrics per stage. Obsession with acquisition + ignoring activation = leaky bucket.

## Activation: Define the Aha Moment

The aha moment is the ACTION most correlated with long-term retention.

Examples:
- Facebook: adding 7 friends in 10 days.
- Dropbox: putting one file in one folder on one device.
- Slack: team sending 2,000 messages.

**How to find it:** cohort analysis — find users who retained at Day 30, work backward to what they did in Week 1 that non-retainers didn't.

**How to move it:** design onboarding to drive users to the aha action. Measure % activated; iterate.

## Retention Curves

Plot % of cohort still active at Day N.

- **Smiling curve:** drop then flatten (healthy — found PMF for some subset).
- **Declining curve:** drops forever (no PMF — fix activation or product-market fit).
- **Crashing curve:** drops steeply then zero (novelty — no habit formed).

A healthy product has a retention curve that flattens at a non-trivial number (>=40% at Day 30+ for consumer; >=60% for B2B SaaS).

**Segment retention by:** cohort (signup week), channel (source), persona (behavior), feature adoption.

## Engagement: DAU/MAU

Ratio of daily-active to monthly-active users. Sticky = high ratio.

- 50%+: extremely sticky (WhatsApp, Facebook scale).
- 20-50%: good engagement (most social, gaming).
- 10-20%: transactional use (e-commerce, banking).
- <10%: infrequent-need product.

Compare against category norms, not absolute targets.

## A/B Testing — Do It Right

**Design:**
- Hypothesis: "IF we [change], THEN [metric] will [direction] because [user-insight-based reason]."
- Primary metric: define BEFORE running, not after.
- Guardrail metrics: what must NOT regress (retention, satisfaction).
- Sample size: use a calculator. Depends on baseline rate and detectable effect size.
- Duration: full business cycle (>= 7 days) to cover day-of-week effects.

**Running:**
- Randomize at user level (not session) for user-experience tests.
- 50/50 split unless you have a reason.
- Monitor daily; don't peek with intent to stop early (invalidates stat sig).
- Keep shipping other work — a single A/B shouldn't freeze other experiments on unrelated surfaces.

**Analysis:**
- Run stat sig at 95% confidence (or preregistered alternative).
- Check guardrails: if primary wins but retention drops, don't ship.
- Segment: does the effect differ by user type, platform, region?
- Novelty vs durable: run for >2 weeks to separate "new thing" bump from real effect.

**Shipping:**
- Winner: ramp to 100% gradually; monitor for regression.
- Inconclusive: don't ship; either refine hypothesis or move on.
- Loser: DO learn from it; negative results are valuable; document.

**Common mistakes:**
- Running too many tests simultaneously on the same surface (interaction effects).
- Stopping early because "looks significant" — wait for planned duration.
- Ignoring guardrails and celebrating primary metric wins.
- Multiple comparisons problem (testing 10 metrics, one will be "significant" by chance).
- Shipping winning variant to a different user base that wasn't tested.

## Cohort Analysis

Group users by a shared attribute (signup week is most common) and track behavior over time.

- **Retention cohorts:** D1, D7, D30, D90 retention per week cohort. Identifies if changes improve retention.
- **Behavior cohorts:** users who did X in Week 1 vs not. Predicts long-term value.
- **Revenue cohorts:** LTV by signup month, acquisition channel.

Spreadsheet shape: rows = cohorts, cols = time periods, cells = %/count.

## Funnels

Stage-by-stage progression. Identify biggest drop-off → biggest opportunity.

Example signup funnel:
```
Landing visits        100,000
Clicked signup         15,000  (15%)   ← measure this step
Email entered          12,000  (80%)
Email verified          9,500  (79%)   ← verification drop
Completed onboarding    7,000  (74%)
Day 7 active            4,500  (64%)   ← retention gap
```

Look at:
- Absolute numbers at each step (where you lose the most people).
- Conversion rates (where rates are worst vs industry).
- Segments (is the drop evenly distributed or concentrated?).

## NPS, CSAT, CES — When to Use

- **NPS** (0-10 "would recommend"): long-term loyalty signal. Survey quarterly; track trend, not absolute.
- **CSAT** (1-5 satisfaction): specific-interaction signal. Post-purchase, post-support.
- **CES** (Customer Effort Score 1-7): "how easy was it?" Best for transactional flows. Low effort correlates with loyalty better than CSAT for some categories.

NPS scores vary enormously by industry (SaaS 30+ is good; consumer 50+ is good; airlines low everywhere). Compare against yourself over time, not against absolute benchmarks.

## Attribution Models

- **First-touch:** credit to first channel. Good for understanding acquisition.
- **Last-touch:** credit to last channel. Good for conversion optimization.
- **Linear:** equal credit to all touches. Balanced but rarely matches reality.
- **Time-decay:** weight recent touches higher. Good for short sales cycles.
- **Data-driven (Google Ads, etc.):** ML-derived per-touch weights. Hardest to explain; often most accurate.

Pick the model that matches your decision: acquisition spend → first-touch; conversion UX → last-touch.

## Dashboard Hygiene

- **Primary dashboard:** <10 metrics. If you track 50, you track none.
- **WoW + MoM changes** visible, not just absolute values.
- **Annotations** on launches, outages, seasonality — so future-you remembers what moved the line.
- **Segmentation** available: by plan, by platform, by geography.
- **Anomaly alerts** on critical metrics — not polling dashboard daily.

## Common Analytics Mistakes

- **Vanity metrics:** signups, pageviews without qualification. Pretty, unactionable.
- **Average when distribution is skewed:** use medians and percentiles (p50, p90).
- **Confusing correlation with causation:** users who do X retain better; doesn't mean forcing X improves retention. A/B test to confirm.
- **Survivorship bias:** analyzing only retained users misses why others left.
- **Metric gaming:** team optimizes for the dashboard number, not the user outcome. Add quality qualifiers.
- **Too-early measurement:** reading results at Day 2 of an A/B test when design needs 2 weeks.
- **Segment-blind reporting:** total metric unchanged, but major segments moved in opposite directions — worth knowing.
