# Six-week database performance course

**Target:** Given a slow workload, independently measure the bottleneck, interpret query plans, choose a justified change, benchmark it, and prevent regressions.

Default pace: three 45-minute sessions per week, using a local database and official documentation. Retention target: 30 days beyond week six.

| Week | Focus | Practical result |
|---|---|---|
| 1 | Baselines and measurement | Reproduce a slow query and separate latency, throughput, CPU, memory, and I/O signals |
| 2 | Indexes and access paths | Read query plans and design or reject indexes based on workload evidence |
| 3 | Joins, statistics, and query shape | Diagnose cardinality mistakes and improve a multi-table query |
| 4 | Transactions and concurrency | Investigate blocking, locking, isolation, and contention |
| 5 | Storage and system behavior | Reason about caching, buffer pools, write amplification, batching, and connection pressure |
| 6 | End-to-end tuning | Profile an unseen workload, improve it measurably, explain the tradeoffs, and add a regression check |

Each week follows: predict → run → inspect → modify → debug → explain → transfer. Reviews will revisit earlier concepts, while progress is tracked separately for recall, explanation, application, debugging, and transfer. Finishing activities alone will not count as mastery.

This is a working course map. No learner performance has been observed yet, so your database engine, current SQL fluency, and starting diagnostic gaps remain unknown. The next step after setup is one short baseline task; its evidence will determine the exact exercises and pace.

I can store your goal, practice evidence, specific misconceptions supported by your reasoning, and review schedule in `/Users/prax/Documents/Codex/2026-08-03/hey/database-performance-course` so later sessions can adapt; you can inspect, correct, export, disable, or delete it. Nothing has been written yet. You can instead take the same course ephemerally in chat with no learner-state files.

**Shall I persist this course in that location?**
