# Company-Specific Playbooks

What each target company actually optimizes for in interviews. Use to frame feedback, pick which edge cases to drill, and calibrate tone.

---

## Google

**Core rubric emphasis:**
- Code quality (clean, readable, idiomatic)
- Optimization mindset (not satisfied with first correct solution; asks "can we do better?")
- Scalable thinking (what happens at 10x? 100x? 1000x?)
- Analytical problem-solving (trace through edge cases systematically)

**What to push on:**
- "Is there a more efficient approach?"
- "How would this behave on a stream of 10 billion elements?"
- "What's the space complexity if we memoize?"

**Behavioral emphasis:** Googleyness — humility, collaboration, comfort with ambiguity, bar-raising.

**Coding environment:** Google Docs / collab-style whiteboard. Code must compile in your head.

**System Design:** Push on scale numbers, data models, storage layer, and consistency guarantees.

---

## Meta (Facebook)

**Core rubric emphasis:**
- Product impact (how does this improve user experience?)
- System reliability (what happens when X fails?)
- Rapid iteration (bias toward shipping, measuring, iterating)
- Execution speed — pace matters

**What to push on:**
- "How do you measure success here?"
- "What fails if this service goes down? What's the blast radius?"
- "You have 2 weeks to ship — what's the MVP cut?"

**Behavioral emphasis:** "Move fast", impact, execution, ownership. Impact framing on every project.

**Coding environment:** Fast pace, 2 problems in 45 minutes is common. Favor pragmatic solutions.

**System Design:** Often product-feature-flavored (design Newsfeed ranking, design Instagram Stories). Weave product thinking into the architecture.

---

## Amazon

**Core rubric emphasis:**
- Leadership Principles (every behavioral answer must map to one or more LPs)
- Customer focus (who is the customer, what do they need?)
- Operational excellence (how do you monitor, alert, recover?)
- Bias for action — concrete decisions over analysis paralysis

**What to push on:**
- "What's the customer impact of this approach?"
- "Which Leadership Principle does this story demonstrate?"
- "How would you operationalize this? Dashboards, alerts, runbooks?"

**Leadership Principles to know cold:** Customer Obsession, Ownership, Invent and Simplify, Are Right A Lot, Learn and Be Curious, Hire and Develop the Best, Insist on the Highest Standards, Think Big, Bias for Action, Frugality, Earn Trust, Dive Deep, Have Backbone (Disagree and Commit), Deliver Results, Strive to be Earth's Best Employer, Success and Scale Bring Broad Responsibility.

**Behavioral emphasis:** STAR format, 2-4 stories per LP, specific metrics, your individual contribution (not the team's).

**System Design:** Heavy on operational concerns. AWS services are fair game (SQS, DynamoDB, Lambda, etc.).

---

## Apple

**Core rubric emphasis:**
- Attention to detail
- Domain-specific depth (OS, low-level systems, hardware-software interface, graphics, audio)
- Team fit within specific org (ML, Services, Silicon, etc.)

**What to push on:**
- Specificity — Apple interviewers often go deep on one topic rather than wide
- Real experience with the domain (iOS / macOS / Metal / Core ML / whatever matches the team)

**Behavioral emphasis:** Craft, quality, focus. Less LP-style.

---

## Microsoft

**Core rubric emphasis:**
- Solid fundamentals (OS, networking, databases)
- Collaboration and inclusivity
- Growth mindset (learning from failure)

**What to push on:**
- "Walk me through what happens at each layer of the stack when X occurs."
- "Tell me about a time you were wrong — what did you learn?"

**Behavioral emphasis:** Growth mindset, inclusivity, customer/partner focus.

---

## Netflix

**Core rubric emphasis:**
- Senior-plus-level problem solving from day one
- Judgment over process
- Extremely high bar — fewer rounds, higher difficulty per round

**What to push on:**
- Ownership of ambiguous problems
- Trade-off justification at architectural level

**Behavioral emphasis:** Keeper test, high performance culture, judgment.

---

## Uber / Stripe / Airbnb

**Core rubric emphasis:**
- Product thinking + systems (full-stack reasoning)
- Scale (millions of users, real-time constraints)
- Pragmatism

**What to push on:**
- End-to-end trace: client → backend → storage → async
- Real-time constraints (trips, payments, bookings all have tight SLAs)

---

## HFT — Citadel / Jump Trading

**Core rubric emphasis:**
- Ultra-low latency (microsecond / nanosecond thinking)
- Mathematical precision (expected value, variance, probability)
- Attention to detail (one wrong sign flip costs millions)

**What to push on:**
- "What's the latency budget for this operation?"
- "If this branch is taken 99% of the time, how would you help the CPU?"
- "Compute the expected value, not just the worst case."

**Technical topics:**
- Lock-free data structures
- Cache line awareness, false sharing
- Branch prediction hints
- Memory layout, SIMD
- Network stack (kernel bypass, RDMA)

**Quant math topics:**
- Probability (conditional, Bayes, expected value)
- Statistics (hypothesis testing, confidence intervals)
- Stochastic processes (Brownian motion, martingales)
- Options pricing (Black-Scholes intuition, greeks)

---

## HFT — Two Sigma / DRW / AQR

**Core rubric emphasis:**
- Research methodology
- Statistical rigor
- Long-horizon thinking (alphas, factors, backtesting)

**What to push on:**
- "How did you validate this finding statistically?"
- "What biases are in your backtest?"
- "Is this alpha robust or overfit?"

**Technical topics:**
- Python, R, C++ for research and production
- Pandas, NumPy, statistical libraries
- Time series analysis
- Machine learning applied to finance

---

## Market-Making Firms — Virtu, Tower, HRT, Flow Traders

**Core rubric emphasis:**
- Market microstructure (order books, matching engines, queue priority)
- Execution quality (slippage, fill rates)
- Fast mental math, puzzles, probability questions

**What to push on:**
- Order book mechanics
- Market impact models
- Execution algorithm design (VWAP, TWAP, implementation shortfall)

---

## Cross-company signals

Some signals matter everywhere:

| Signal | Why it matters |
|--------|----------------|
| Clarifying questions up front | Shows candidate won't dive into wrong interpretation |
| Complexity analysis without prompting | Shows senior-level habit |
| Edge case enumeration | Empty input, single element, max constraints, overflow |
| Trade-off articulation | "X is faster but uses more memory; Y is slower but cache-friendly" |
| Test case generation | Writing tests before/after implementation |
| Acknowledging uncertainty | "I'm not 100% sure about this, let me verify" beats fabricating |

---

## Behavioral Framing Pivots

Use the candidate's target company to reframe behavioral answers:

| Company | Pivot the story to emphasize |
|---------|------------------------------|
| Google | Bar-raising, collaboration, technical depth |
| Meta | Impact, speed, product thinking |
| Amazon | Customer, ownership, specific LPs |
| Apple | Craft, focus, user experience |
| Netflix | Judgment, high performance, autonomy |
| HFT | Precision, math, calm under pressure, time-sensitive decisions |
