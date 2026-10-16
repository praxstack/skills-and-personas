# Six-week database-performance course

We’ll build this as a six-week, PostgreSQL-first course aimed at independent performance diagnosis—not memorizing tuning tricks.

1. **Measure before tuning** — latency percentiles, workloads, baselines, and safe benchmarks
2. **Indexes and data access** — selectivity, composite/partial indexes, covering indexes, write costs
3. **Query plans** — `EXPLAIN`, scans, cardinality estimates, joins, sorts, and aggregation
4. **Schema and query design** — normalization tradeoffs, pagination, batching, N+1 queries, materialization
5. **Concurrency and operations** — transactions, locks, connection pools, caching, and partitioning
6. **Capstone investigation** — diagnose a slow workload, test changes, prevent regressions, and explain tradeoffs

Each week will include a short concept lesson, prediction/retrieval, hands-on SQL, measurement, and a review scheduled from your actual performance. I’ll adapt the course to your database and experience after one baseline diagnostic.

If you decline persistence, we can continue in this chat without creating learner-state files. I can store your goal, practice evidence, misconceptions, and review schedule in `/Users/prax/Documents/Codex/2026-08-03/hey/.prax-teach/database-performance/`; you can inspect, correct, export, or delete it. Shall I persist this course?
