# Course consent boundary

We’ll use course mode. The goal is independent performance: given a slow workload, measure the bottleneck, choose the highest-value database change, validate it safely, and explain the trade-offs.

Provisional format: two 75-minute sessions per week, PostgreSQL-based labs with engine-neutral principles, and a 90-day retention horizon.

- Week 1 — Measurement: latency, throughput, percentiles, baselines, and execution plans
- Week 2 — Indexes: selectivity, composite indexes, covering indexes, and write costs
- Week 3 — Query optimization: joins, cardinality estimates, sorting, aggregation, and plan mistakes
- Week 4 — Storage and concurrency: memory, caching, I/O, transactions, locking, and contention
- Week 5 — Production diagnosis: connection pressure, slow-query evidence, workload testing, and safe tuning
- Week 6 — Capstone: diagnose and improve an unseen workload, then defend the changes with before/after evidence

Each week will follow: predict → run → inspect → modify → explain → transfer. Reviews will adapt to your actual answers and hint use; completion alone will not count as mastery. After persistence is approved, I’ll begin with one short prerequisite diagnostic and adjust the syllabus before fixing the detailed lessons.

I can store your goal, exact practice evidence, misconceptions, and review schedule in `/Users/prax/Documents/Codex/2026-08-03/hey/database-performance-course` so later sessions can adapt; you can inspect, correct, export, or delete it. I can also run the entire course ephemerally in chat with no learner-state files. Shall I persist this course?
