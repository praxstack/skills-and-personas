# Lesson attempt before transfer answer

## Goal

Given a two-thread schedule, you’ll be able to prove whether a lost update occurred, identify the overwritten update, and choose the correct synchronization boundary.

A source line such as `x = x + 5` is usually three operations:

1. Read `x` into a thread-local value.
2. Compute the new value.
3. Write it back.

A lost update occurs when both threads compute from state that excludes the other thread’s change, and a later write replaces an earlier update.

### Worked example

Initially, `x = 10`.

- Thread A performs `x = x + 5`.
- Thread B performs `x = x - 2`.

| Step | Operation | A’s local value | B’s local value | Shared `x` |
|---:|---|---:|---:|---:|
| 0 | Initial state | — | — | 10 |
| 1 | A reads `x` | 10 | — | 10 |
| 2 | B reads `x` | 10 | 10 | 10 |
| 3 | A computes `10 + 5` | 15 | 10 | 10 |
| 4 | A writes | 15 | 10 | 15 |
| 5 | B computes `10 - 2` | 15 | 8 | 15 |
| 6 | B writes | 15 | 8 | 8 |

Both serial orders would finish at `13`. Instead, B writes a value derived from the stale `10`, so A’s `+5` disappears.

Use this diagnostic:

- Expand each update into read, compute, and write.
- Trace shared and thread-local state in schedule order.
- Check whether each write incorporates the other completed update.
- Compare the result with valid serial executions.
- Identify the precise write that overwrote an effect.
- Protect the entire read–compute–write operation—not merely the final write—with a mutex, atomic read-modify-write, or versioned compare-and-swap retry.

If you get stuck, reply `Hint 1`. You can also say **Answer now**.

## Unseen transfer task

Initially:

```text
profile = { theme: "light", language: "en" }
```

Each thread reads a private copy and later replaces the entire shared record:

```text
1. A reads profile into a
2. B reads profile into b
3. A sets a.theme = "dark"
4. B sets b.language = "fr"
5. A writes profile = a
6. B writes profile = b
```

Trace the shared record after each write, decide whether this is a lost update, identify the lost logical change, and propose the smallest safe synchronization or update strategy. What is your diagnosis?
