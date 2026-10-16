# Course consent boundary

We’ll make this a hands-on, six-week course. By the end, you should be able to diagnose a slow database workload, interpret query plans, choose and validate improvements, and explain the production tradeoffs without hints.

| Week | Focus | Performance task |
|---|---|---|
| 1 | Measurement: latency, throughput, percentiles, baselines, bottlenecks | Build a reproducible investigation from a vague “database is slow” report |
| 2 | Execution plans: scans, joins, sorts, cardinality, statistics | Explain a plan and identify the most useful next measurement |
| 3 | Indexes: composite, covering, partial, selectivity, write cost | Design or reject indexes for an unseen workload |
| 4 | Query and schema optimization: sargability, batching, pagination, data shape | Rewrite a workload and verify the improvement experimentally |
| 5 | Production behavior: transactions, locks, MVCC, pooling, cache, memory, I/O | Diagnose a contention or saturation incident |
| 6 | End-to-end performance engineering | Complete a capstone: baseline, hypothesis, change, benchmark, tradeoffs, and rollback plan |

Each week will include a short concept session, a guided investigation, an independent lab, and later retrieval. Progress will be tracked separately for recall, explanation, application, debugging, and transfer; completing a lesson alone will not count as mastery. The syllabus will adapt after an initial diagnostic, and examples will default to PostgreSQL unless you name another engine.

No state has been written yet. I can store your goal, practice evidence, specific misconception inferences, and adaptive review schedule in `/Users/prax/Documents/Codex/2026-08-03/hey/database-performance-course` so later sessions can resume and adapt; you can inspect, correct, export, disable reviews, or delete it. Shall I persist this course? Reply with `yes` or `no`, optionally followed by your database engine, current level, available hours per week, desired retention period, and any accessibility or format needs.
