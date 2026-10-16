# Six-week database performance course

This is a six-week course with cross-session progress tracking.

**Outcome:** By the end, you’ll be able to measure database latency, read query plans, choose or reject indexes, diagnose joins/sorts/locks, improve a real workload, and validate the change without regressing correctness.

**Provisional course**

1. **Performance fundamentals:** workload, baselines, p50/p95/p99 latency, `EXPLAIN`; produce a baseline report.
2. **Indexes:** single-column, composite, covering, partial; choose indexes from query patterns and explain tradeoffs.
3. **Query planners:** cardinality estimates, statistics, access paths, and plan changes.
4. **Query execution:** joins, aggregation, sorting, temporary work, and query rewrites.
5. **Concurrency:** transactions, isolation, locks, contention, connection pools, and deadlocks.
6. **Capstone:** optimize one representative workload, benchmark it, explain the causal changes, and add regression guardrails.

Each week will include a worked example, a guided attempt, an unseen transfer problem, and spaced retrieval. Progress will be recorded separately for recall, explanation, application, debugging/discrimination, and transfer; completion alone won’t count as mastery.

Before tailoring Week 1, tell me your primary database and level: **PostgreSQL, MySQL, SQLite, or mixed; beginner, intermediate, or production experience.**

I can store your goal, practice evidence, misconceptions, and review schedule in `/Users/prax/Documents/Codex/2026-08-03/hey/` so later sessions can adapt; you can inspect, correct, export, or delete it. Shall I persist this course? You can also continue ephemerally without learner-state files.
