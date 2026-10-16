# Course consent boundary

We’ll run this in **course mode**. By the end of six weeks, you should be able to take an unfamiliar slow database workload, measure it, identify the bottleneck, propose a change, validate the result, and explain the tradeoffs without hints.

Provisional format: three 45-minute sessions per week, engine-neutral principles with database-specific examples once we establish your stack.

| Week | Focus | Independent checkpoint |
|---|---|---|
| 1 | Measurement, latency vs. throughput, baselines, execution plans | Diagnose where a slow query spends its time |
| 2 | Storage, selectivity, B-tree and composite indexes | Design—or reject—indexes for an unseen workload |
| 3 | Joins, sorting, aggregation, statistics, cardinality estimates | Explain two competing plans and repair a misestimate |
| 4 | Caching, memory, I/O, batching, N+1 queries, connection pools | Benchmark a change and distinguish real improvement from noise |
| 5 | Transactions, MVCC, locks, contention, hotspots, scaling limits | Debug a concurrency incident |
| 6 | Production observability, regression prevention, safe tuning | Complete an end-to-end performance investigation |

Each week will use:

- Retrieval before explanation
- One focused model and worked example
- Guided practice with progressively stronger hints only when needed
- An unseen debugging or transfer task
- Spaced review based on observed performance

Progress will distinguish recall, explanation, application, debugging, and transfer. Hint-assisted success will remain labeled scaffolded; completion or one correct answer will not count as mastery.

No learner performance has been observed yet, so your starting level, database engine, and current bottlenecks remain uncertain. After setup, we’ll begin with one short diagnostic and adapt the course before fixing the detailed lesson sequence.

Nothing has been created yet. You can also continue entirely in chat without learner-state files.

I can store your goal, practice evidence, misconceptions, and review schedule in `/Users/prax/Documents/Codex/2026-08-03/hey/database-performance-course` so later sessions can adapt; you can inspect, correct, export, or delete it. Shall I persist this course?
