# Course consent boundary

We’ll build this as an adaptive six-week course. The outline is provisional until I assess your baseline and learn which database engine you use.

**Target outcome:** By week 6, you’ll be able to take an unfamiliar slow workload, establish a baseline, interpret its execution plan, identify the bottleneck, choose a safe intervention, and verify both the improvement and possible regressions. We’ll aim to retain the core skills for at least 90 days after the course.

| Week | Focus | Performance task |
|---|---|---|
| 1 | Measuring performance | Separate latency, throughput, database time, and application time; capture a trustworthy baseline |
| 2 | Execution plans | Read scans, joins, estimates, sorts, and spills; explain why a query is slow |
| 3 | Index design | Choose composite, covering, or partial indexes and defend their read/write tradeoffs |
| 4 | Query and schema tuning | Repair non-sargable predicates, expensive joins, pagination, N+1 access, and harmful schema choices |
| 5 | Concurrency and resources | Diagnose locks, transactions, connection pressure, memory, caching, and I/O bottlenecks |
| 6 | Production tuning | Use observability and load tests to make a safe change; complete an unseen capstone diagnosis |

Default cadence: three 45-minute sessions per week—one concept-and-prediction session, one hands-on lab, and one unassisted retrieval or debugging challenge. Later lessons will adapt to your questions and performance. I’ll distinguish recall, explanation, application, debugging, and transfer; hinted success will remain labeled as scaffolded rather than treated as mastery. No learner performance has been observed yet.

Once persistence is settled, I’ll ask one short diagnostic about your database, experience, and available practice environment. Engine-specific material will use primary official documentation. Delivery will be text-first, with tables or diagrams only when they materially help; accessibility preferences can be incorporated before the first lesson.

Nothing has been stored yet. We can continue ephemerally in this chat without creating learner-state files.

I can store your goal, practice evidence, misconceptions, and review schedule in `/Users/prax/Documents/Codex/2026-08-03/hey/outputs/prax-teach-v2/workspaces/database-performance` so later sessions can adapt; you can inspect, correct, export, or delete it. Shall I persist this course?
