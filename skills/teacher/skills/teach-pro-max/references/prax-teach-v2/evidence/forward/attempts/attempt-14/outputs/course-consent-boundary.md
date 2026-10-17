# Six-week database performance course

This is a six-week course in course mode. I’ll keep it stack-neutral initially, then adapt the labs to your database and current level.

**Outcome**

By the end, you should be able to measure a slow workload, interpret its execution plan, choose and validate improvements, explain read/write and consistency tradeoffs, and add regression safeguards—without tutor hints.

**Six-week plan**

1. **Measure before changing** — latency, throughput, workload shape, baselines, `EXPLAIN`.
2. **Indexes** — B-trees, composite/covering indexes, selectivity, prefix rules, write costs.
3. **Query plans** — joins, cardinality estimates, statistics, sargability, pagination, N+1 queries.
4. **Concurrency** — transactions, isolation, locks, MVCC, deadlocks, contention.
5. **Runtime and operations** — buffers/cache, I/O, maintenance, connection pools, replicas, capacity.
6. **Capstone** — diagnose a realistic workload, benchmark alternatives, document tradeoffs, and create a regression checklist.

Each week will use retrieval, a small authentic experiment, guided practice, an unseen transfer case, and a review item.
Provisional retention horizon: **three months**, with reviews adjusted from your actual evidence.

I can store your goal, practice evidence, misconceptions, and review schedule in `/Users/prax/Documents/Codex/2026-08-03/hey/.prax-teach/database-performance/learner-state.json` so later sessions can adapt; you can inspect, correct, export, or delete it. Shall I persist this course?

Nothing has been written yet. Reply **Persist** or **Ephemeral**; then I’ll ask one setup question about your database and experience.
