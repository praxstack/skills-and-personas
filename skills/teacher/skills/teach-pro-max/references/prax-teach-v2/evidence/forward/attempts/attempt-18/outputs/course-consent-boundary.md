# Course consent boundary

## Six-week database-performance course

**Target outcome:** Given an unfamiliar schema, workload, and query plan, diagnose the bottleneck, choose and justify a change, measure its impact, and explain trade-offs or rollback criteria.

1. **Measure first:** latency, throughput, baselines, profiling, `EXPLAIN`.
2. **Indexes:** B-trees, composite indexes, covering indexes, write/storage costs.
3. **Query plans:** joins, sorts, aggregation, cardinality, statistics.
4. **Data layout:** schema choices, partitioning, pagination, materialized views.
5. **System effects:** transactions, locks, connection pools, caching, contention.
6. **Capstone:** profile → hypothesize → change → benchmark → regression guardrail.

**Review policy:** retrieval at each session start, repair within 48 hours after a miss, cumulative transfer practice, and a provisional retention horizon of 30 days after week six. Sources will be official documentation for your chosen database/version plus reproducible local measurements.

I can store your goal, practice evidence, misconceptions, and review schedule in `/Users/prax/Documents/Codex/2026-08-03/hey/database-performance-course` so later sessions can adapt; you can inspect, correct, export, or delete it. Shall I persist this course?

To tailor the syllabus, reply with: `database/version | current experience | access needs (text/code, pace, reduced motion)` and, for calibration, say what you would inspect first when a query suddenly becomes slow—or say “I don’t know.”
