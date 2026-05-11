# Connection Framework — Linking Learnings to Bigger Maps

## When to load this file

Load at the "Connect" step of the Recursive Gap-Filling Loop (Step 7), or whenever a learner has mastered a concept and is ready to link it to related areas.

## Purpose

Isolated facts fade. Connected facts persist. The connection framework maps newly-mastered concepts to the maps they belong to, so the learner's mental model of the whole domain grows instead of fragmenting.

## The Three Maps

### Map 1: DSA ↔ System Design

Every data structure and algorithm has a system-design echo. When the learner masters a DSA concept, connect it to the system design pattern that uses it:

| DSA concept | System design equivalent | Why the connection matters |
|---|---|---|
| Hash table | Distributed key-value store / cache | Same idea (hash key to slot) at different scales; consistency and collision semantics change |
| Binary tree / BST | B-tree / B+-tree in databases | Disk-friendly variant of tree balance for persistent storage |
| Red-black tree / AVL | Self-balancing indices in DBMS | Same guarantee (log height) tuned for disk page size |
| LRU cache | CDN / application cache eviction | Algorithm is identical; distributed coordination adds failure modes |
| Queue (FIFO) | Message queue (Kafka, RabbitMQ) | Same ordering guarantee; durable storage and replay add complexity |
| Priority queue | Job scheduler / rate limiter | Priority semantics preserved; multi-node coordination via gossip or central broker |
| Graph BFS / DFS | Service dependency crawler / blast-radius analyzer | Graph traversal concept is identical; edge semantics change (call vs data dependency) |
| Topological sort | Build system / deployment ordering | Dependency ordering at different scales |
| Union-find (DSU) | Cluster membership / partition detection | Same merge semantics; distributed consensus wraps it |
| Trie | Router / autocomplete / DNS | Prefix-based dispatch identical from in-memory to distributed |
| Bloom filter | Cache-pre-filter / scalable membership test | Same probabilistic trick; distributed Bloom requires merge semantics |
| Consistent hashing | Load balancing / sharding | DSA concept built for distributed systems |
| Merkle tree | Git / blockchain / sync diff | Same tree-of-hashes for verification at different scales |

### Map 2: Code Smell ↔ Design Principle

When the learner fixes a code smell, connect it to the design principle violated and the principle that replaces it. This keeps SOLID and related principles grounded in concrete pain:

| Code smell | Violated principle | Principle to apply | Typical fix |
|---|---|---|---|
| Long method | SRP (Single Responsibility) | Extract Method | Break into named sub-steps |
| God class | SRP + Open/Closed | Decompose by responsibility | Split into cohesive classes |
| Feature envy | SRP | Move Method to the data's owner | Relocate logic to the class that holds the data |
| Data clump | DRY | Introduce Parameter Object | Wrap related primitives in a class |
| Primitive obsession | SRP + type safety | Replace Primitive with Object | Introduce domain types |
| Switch statement on type | OCP (Open/Closed) | Polymorphism | Replace with strategy or state |
| Duplicate code | DRY | Extract Method / Extract Class | Pull to shared abstraction |
| Shotgun surgery | SRP | Co-locate related change | Move cohesive parts together |
| Divergent change | SRP | Split by reason-to-change | Separate axes of variation |
| Parallel inheritance | DRY | Unify or decompose | Eliminate the mirrored hierarchy |
| Lazy class | YAGNI | Inline | Delete and merge |
| Speculative generality | YAGNI | Inline / simplify | Remove unused abstraction |
| Temporary field | Pragmatism | Move to subclass / strategy | Extract conditional state |
| Middle man | Minimalism | Remove Middle Man | Call target directly |
| Message chain | LoD (Demeter) | Hide Delegate | Wrap the chain |
| Inappropriate intimacy | Encapsulation | Move Method / change access | Enforce boundary |
| Alternative classes with different interfaces | LSP | Rename / extract interface | Unify the shape |
| Incomplete library class | Extensibility | Wrap library | Introduce adapter |
| Comments-as-deodorant | Clarity | Rename / refactor | Make code speak for itself |

### Map 3: Concept ↔ Interview Question

Every concept the learner masters has an interview-question family. When a learner "clicks" on a concept, connect it to the question shapes interviewers ask:

| Concept mastered | Interview question family |
|---|---|
| Two-pointer pattern | "Find pair with sum X", "reverse in place", "merge sorted arrays" |
| Sliding window | "Longest substring without repeating", "max sum subarray of size K" |
| Monotonic stack | "Next greater element", "largest rectangle", "trapping rain water" |
| Binary search on answer | "Minimum capacity", "earliest / latest date" |
| DP state design | "Count ways", "optimal subsequence", "min edit distance" |
| Graph BFS vs DFS | "Shortest path unweighted", "cycle detection", "connected components" |
| Union-find | "Account merge", "number of islands", "redundant connection" |
| LRU / LFU design | "Design cache", "design log system" |
| Rate limiter | "Design API throttling", "leaky bucket vs token bucket" |
| Consistent hashing | "Design distributed cache", "sharded data store" |
| CAP trade-offs | "Design chat / social feed / e-commerce with scale" |
| Event-driven architecture | "Design notification system", "design order pipeline" |
| Database indexing | "Query slow — what would you check?", "design schema for X" |
| Caching strategy | "Where to cache?", "cache invalidation design" |

## Connection as a teaching move

After a learner "clicks" on a concept:

1. **Name the connection.** "This hash table pattern is the same idea as a Redis cluster's key distribution."
2. **Spot-check understanding.** "If you understand hash tables, what changes when you move to distributed?" — expect answers like collision semantics, rehashing cost, consistency.
3. **Draw the map.** Show 3-5 other places the concept appears, from the tables above or your own domain knowledge.
4. **Park it for later drill.** "When we get to designing distributed caches next month, come back to this page."

## What this is NOT

- Not a memorization exercise. The maps are teaching tools; the learner shouldn't memorize them.
- Not comprehensive. These are starting points; every domain has more connections.
- Not a substitute for solving problems. Connections deepen understanding but don't replace practice.

## Signal that connections are working

- The learner starts saying "this is like..." unprompted
- The learner brings up related concepts in unrelated contexts
- The learner's questions shift from "what is X" to "how does X relate to Y"
- The learner proposes connections you didn't mention

When those happen, the learner is building a domain map, not collecting facts. That's the goal.
