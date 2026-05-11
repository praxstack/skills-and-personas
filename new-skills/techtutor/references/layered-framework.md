# The 6-Layer Explanation Framework

The heart of TechTutor's method. For any non-trivial technical concept, build understanding in this order:

---

## The Six Layers

### Layer 1 — WHY does this exist?

What problem does this thing solve? Told through analogy or real scenario, not formal definition.

**Length:** 2-3 sentences.

**Bad:** "A HashMap is a data structure that stores key-value pairs using a hash function to compute an index into an array of buckets."

**Good:** "Imagine a library with 10,000 books but no catalog. Finding a book means checking every shelf. Now imagine each book has a code that tells you exactly which shelf to check. That's a HashMap — the code is the hash, the shelf is the bucket."

---

### Layer 2 — HOW does it work?

Walk through a tiny example. Use the smallest possible input. Trace step by step.

**Show state changes explicitly.**

---

### Layer 3 — VISUALIZE it

Show what's happening internally. **Mandatory** for non-trivial concepts.

Pick the format that best fits:
- Mermaid diagrams for flows, sequences, architecture
- ASCII state tables for algorithm traces
- ASCII art for memory layouts, trees, linked structures, tensor shapes

See `visual-guidelines.md` for concrete templates and when to use each.

---

### Layer 4 — REAL CODE (or MATH)

Show it running. Working code, not pseudocode.

**Language selection:** Java / Python / JavaScript based on context. Prefer real language over pseudocode.

**Keep it focused** — no boilerplate, unnecessary imports, or wrapper main methods unless they're part of the lesson.

**For AI/ML:** Use math notation and tensor shape diagrams over full PyTorch/TensorFlow code unless implementation is specifically requested. `Attention(Q,K,V) = softmax(QK^T / √d_k)V` with a shape walkthrough teaches more than 40 lines of PyTorch.

---

### Layer 5 — WHERE is this used at scale?

Real-world systems with real numbers where possible.

Examples:
- "Redis uses this for..."
- "Google Maps does this because..."
- "Twitter handles ~500K tweets/sec — here's how fanout-on-write vs fanout-on-read works at that scale..."
- "GPT uses multi-head self-attention across 96 layers..."

2-4 anchors is usually enough.

---

### Layer 6 — CONNECT to the bigger picture

Related patterns, interview follow-ups, design trade-offs. Use `connection-framework.md` for domain-specific mappings.

---

## Depth Calibration

| Question type | Layers |
|---------------|--------|
| "What's the time complexity of X?" | Direct answer — no layers needed |
| "What is X?" (simple topic) | Layers 1-3 minimum |
| "How does X work internally?" | Layers 1-5 |
| Deep-dive / interview prep | All 6 layers, clearly sectioned |
| "Skip the basics, go deeper" | Jump to internal mechanics / advanced layer, no recap |

**Default to detailed.** The learner wants to *understand*, not get a summary. When in doubt, include more depth with clear structure rather than cutting short. Go deep on the asked topic. Don't go wide into tangential topics they didn't ask about.

---

## Gold Standard Example

This is the quality bar for a complete response.

> **Question:** "How does a Queue work and where is it used?"

### Layer 1 — Why it exists

Think of a line at a movie theater. First person in line gets the ticket first. Nobody cuts. That's a Queue — First In, First Out (FIFO). It exists because many real problems need fair ordering: process tasks in the order they arrived, handle requests one by one, etc.

### Layer 2 — How it works (tiny example)

```
Operations on an empty queue:

enqueue(10)  → Queue: [10]         (10 enters the back)
enqueue(20)  → Queue: [10, 20]     (20 enters the back)
enqueue(30)  → Queue: [10, 20, 30] (30 enters the back)
dequeue()    → returns 10          Queue: [20, 30]  (front removed)
peek()       → returns 20          Queue: [20, 30]  (front seen, not removed)
dequeue()    → returns 20          Queue: [30]
```

Two operations: **enqueue** (add to back), **dequeue** (remove from front). Both O(1).

### Layer 3 — Visualize it

```
enqueue(10):   front → [10] ← back
enqueue(20):   front → [10, 20] ← back
enqueue(30):   front → [10, 20, 30] ← back
dequeue():     front → [20, 30] ← back       (10 removed from front)

Internally (LinkedList-based):
  head → Node(20) → Node(30) → null
                                 ↑ tail

Internally (Array-based / circular):
  [_, _, 20, 30, _, _]
       ↑ front    ↑ back
  When back hits end, it wraps to index 0 (circular buffer)
```

### Layer 4 — Real code

```java
// Java's built-in Queue (LinkedList implementation)
Queue<Integer> queue = new LinkedList<>();
queue.offer(10);    // enqueue
queue.offer(20);
queue.offer(30);

queue.poll();       // dequeue → 10
queue.peek();       // front element → 20 (doesn't remove)

// Why offer/poll instead of add/remove?
// add/remove throw exceptions on failure
// offer/poll return false/null — safer for bounded queues
```

### Layer 5 — Where it's used at scale

- **Message brokers (Kafka, SQS, RabbitMQ):** Millions of events queued and processed in order.
- **BFS traversal:** Every BFS uses a queue to explore level by level — this is how Google Maps finds shortest paths.
- **Task scheduling:** OS process schedulers use queues (with priority variants) to decide which process runs next.
- **Print spoolers, request buffers, rate limiters** — all FIFO at their core.

### Layer 6 — Bigger picture

Queue is the gateway to: Priority Queues (heaps), Deques (double-ended), Blocking Queues (concurrency), distributed message queues. In interviews, if you hear "process in order" or "BFS" — a Queue is almost certainly involved.

*Quick check — what's the difference between a Queue and a Stack, and when would you pick one over the other?*
