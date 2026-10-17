# Six-week database performance course

Great—this is a six-week course. Target outcome: independently diagnose database bottlenecks from workload evidence, choose and validate improvements, explain trade-offs, and transfer the method to an unseen system.

Provisional sequence:

1. Baselines: latency, throughput, percentiles, reproducible workloads  
2. Query plans: `EXPLAIN`, cardinality estimates, scans, joins, and sorts  
3. Indexes: composite, covering, partial, selectivity, and write costs  
4. Query/schema design: sargability, joins, N+1 patterns, pagination, statistics  
5. System behavior: locks, transactions, connection pools, caching, CPU, and I/O  
6. Capstone: hypothesis → benchmark → change → verify → rollback

I’ll default to PostgreSQL examples, terminal/text practice, and a six-week retention horizon with a 30-day follow-up. No learner performance has been observed yet, so the plan will adapt after the initial diagnostic.

We can continue ephemerally in host chat with no learner-state files. Proposed storage location: `/Users/prax/Documents/Codex/2026-08-03/hey/.prax-teach/database-performance-course/`; nothing will be written yet. I can store your goal, practice evidence, misconceptions, and review schedule there so later sessions can adapt; you can inspect, correct, export, or delete it. Shall I persist this course?

Diagnostic—answer briefly, or say “I don’t know”: A query filters `orders` by `customer_id`, sorts by `created_at DESC`, and returns 20 rows. What would you inspect first to explain its latency, and what evidence would change your next move?
