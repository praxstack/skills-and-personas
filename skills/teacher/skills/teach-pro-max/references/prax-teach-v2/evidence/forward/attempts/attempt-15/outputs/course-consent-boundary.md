# Six-week database performance course

Course mode: six weeks, with progress memory available after consent.

**Outcome:** By the end, you’ll be able to diagnose an unfamiliar slow workload, read execution plans, choose measured fixes, validate them under representative load, and explain latency, correctness, write-cost, and rollback trade-offs.

**Six-week course**

1. **Measure before changing** — latency percentiles, throughput, workload capture, cache effects, reproducible baselines.
2. **Read query plans** — scans, joins, sorts, cardinality estimates, actual-vs-estimated rows, safe `EXPLAIN ANALYZE`.
3. **Indexes and data layout** — B-trees, composite-prefix rules, covering/partial indexes, selectivity, write and storage costs.
4. **Query and schema design** — sargability, N+1 queries, pagination, aggregation, denormalization, partitioning trade-offs.
5. **Concurrency** — transactions, locks, MVCC, isolation, deadlocks, connection pools, contention diagnosis.
6. **Production performance** — observability, load testing, regression guardrails, capacity/cost trade-offs, tuning runbook, capstone.

I’ll use engine-neutral concepts and adapt examples to your database. The default source policy is official documentation plus reproducible local labs, with a 30-day retention horizon. After persistence consent, we’ll begin with one prerequisite diagnostic rather than assuming your level.

Resolved storage location: `/Users/prax/Documents/Codex/2026-08-03/hey/state/` (not yet created). It would contain only the learner-state files needed for your goal, evidence, misconceptions, reviews, and sources.

I can store your goal, practice evidence, misconceptions, and review schedule in `/Users/prax/Documents/Codex/2026-08-03/hey/state/` so later sessions can adapt; you can inspect, correct, export, or delete it. Shall I persist this course?

Until you answer, I’ll keep the course ephemeral and create no files.
