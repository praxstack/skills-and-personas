---
name: backend-pe-cpp
description: 'Principal-engineer-grade C++ backend design, implementation, and review for performance-critical services, networking, storage, and infrastructure. Covers C++20/23, RAII, ownership, modern concurrency (std::jthread, std::atomic, lock-free where proven), sanitizers, fuzzing, hardening, and C++-specific failure modes (UB, lifetime bugs, data races, false sharing, allocator pressure). Use when designing, building, reviewing, refactoring, profiling, hardening, or debugging C++ backend systems, low-latency services, network daemons, or storage engines. Trigger keywords - C++ backend, C++20, C++23, CMake, low-latency, RAII, smart pointers, sanitizers, ASan UBSan TSan, fuzzing, lock-free, zero-copy, performance review, memory safety review.'
---

# C++ Backend Principal Engineer

**Audience:** Engineers designing, building, reviewing, or hardening C++ backend systems - low-latency services, network daemons, storage engines, trading systems, infrastructure components.

**Goal:** Principal-engineer-grade C++ - no undefined behavior, deterministic resource management, predictable tail latency, and hardened against both memory safety and supply-chain attacks.

## Priority Model

Correctness and UB avoidance - Reliability - Security - Performance and tail latency - Observability - Scalability - Tooling and testing. In that order.

## Core Principles

1. **Ownership is the API.** Every API declares who owns the memory. Prefer values and views. Use `std::unique_ptr` for single ownership, `std::shared_ptr` only when true shared lifetime exists (rare). Raw pointers and raw references are **non-owning** only. `std::span`, `std::string_view`, and reference parameters for non-owning borrows. If a function takes a raw pointer and deletes it, the API is broken.

2. **UB is correctness, not performance.** A single undefined behavior (unsigned overflow, data race, use-after-free, strict-aliasing violation, null deref) invalidates the entire program's reasoning. Optimizers exploit UB aggressively. Build with `-fsanitize=address,undefined` in CI; `-fsanitize=thread` for concurrent code. Fuzz every parser.

3. **RAII everywhere, manual cleanup never.** Every resource - memory, file, mutex, socket, DB handle, GPU buffer - wrapped in a type whose destructor releases it. Never `new`/`delete` in new code. `std::scoped_lock` over `std::mutex::lock`/`unlock`. `FILE*`, `pthread_t`, sockets - wrap them.

4. **Concurrency is message passing first, shared memory last.** Lock-free data structures are hard to write, harder to verify. Prefer `std::jthread` + channels (mpmc queue, `concurrentqueue`, or custom SPSC) for coordination. Shared mutable state requires a documented invariant, a mutex, and ideally TSan in CI. `std::atomic` without understanding memory_order is UB in waiting.

5. **Measure, then optimize.** Allocations, cache misses, branch mispredictions, and TLB misses dominate performance beyond the algorithmic level. `perf`, VTune, or `pmu-tools` before any optimization. Micro-benchmarks with `google/benchmark`; `nanobench` for tight loops. Never optimize on a guess.

6. **The build is part of the binary.** Release flags (`-O2` or `-O3`, `-flto`, `-fno-omit-frame-pointer` for profiling, hardening flags), reproducible builds, pinned toolchain, deterministic dependency resolution (Conan or vcpkg with a lockfile). `-Wall -Wextra -Wpedantic -Wconversion -Wshadow` warnings-as-errors. Clang-tidy + clang-format in CI.

## Decision Framework

**C++20 vs. C++23 vs. older.** C++20 baseline. C++23 where your toolchain supports it (concepts, `std::expected`, `std::print`, `std::mdspan`, `if consteval`). C++17 only for legacy integration. Never C++14 or earlier in new code.

**`std::shared_ptr` vs. `std::unique_ptr` vs. raw pointer.**
- `unique_ptr` - default for owning pointers.
- `shared_ptr` - only when true shared ownership exists (e.g., async callbacks, graph nodes with cycles broken by `weak_ptr`).
- Raw pointer - non-owning observer, lifetime guaranteed by caller.
- Passing `shared_ptr` by value when ownership isn't transferred is a performance and coupling smell.

**`std::vector` vs. `std::array` vs. `std::span`.**
- `array` - compile-time fixed size.
- `vector` - dynamic, default dynamic storage.
- `span` - non-owning view over contiguous memory; function parameters that accept a range.

**`std::expected` vs. exceptions vs. error codes.** C++23 `std::expected<T, E>` or Boost.Outcome for recoverable errors on hot paths where exceptions cost is unacceptable. Exceptions for exceptional conditions (OOM, invariant violations, I/O catastrophic). Error codes are legacy; avoid.

**Allocator strategy.** Default allocator for most code. Arena/monotonic allocator (`std::pmr::monotonic_buffer_resource`) for request-scoped short-lived objects. Pool allocator for fixed-size objects with high churn. Custom allocators only with measurement showing the default is the bottleneck.

**Coroutines vs. threads vs. callbacks.** `std::jthread` for CPU-bound work. C++20 coroutines with a proven executor (cppcoro, Asio, Unifex) for I/O-bound concurrency when you can commit to the model. Callbacks and hand-rolled state machines only for legacy. Mixing coroutines and raw threads carelessly causes lifetime bugs.

**Networking: Asio vs. io_uring vs. epoll direct.** Asio (standalone or Boost) for cross-platform async I/O with a mature model. io_uring (via liburing) for Linux-only, maximum throughput, willing to manage complexity. Raw epoll only if you're writing a library others will use.

## Anti-Patterns

- **`new`/`delete` in new code.** Use `make_unique`/`make_shared` and RAII containers.
- **Raw pointer as owning parameter.** API is lying about ownership.
- **`std::shared_ptr` as default.** Atomic refcount per copy, cache-line ping-pong. Use `unique_ptr` unless sharing is real.
- **Returning a raw pointer or reference to a local.** Classic UB. Compilers diagnose sometimes, not always.
- **`const_cast` on something genuinely const.** UB to modify.
- **`reinterpret_cast` to read bits.** Violates strict aliasing. Use `std::bit_cast` (C++20) or `memcpy`.
- **`std::string` constructed per log call.** Allocation in the hot path. Use `string_view` or preallocated buffers.
- **Inheritance for code reuse.** Prefer composition; inheritance only for runtime polymorphism with a stable interface.
- **Virtual functions in hot loops.** Indirect call cost + optimizer opacity. Use templates, CRTP, or `std::variant` + visitor.
- **Unbounded queue in a producer/consumer pipeline.** Memory growth unbounded. Bounded MPMC with backpressure.
- **`sleep` or `usleep` for synchronization.** Condition variables or futures.
- **Manual `pthread_*` API in new code.** Use `std::jthread`, `std::mutex`, `std::condition_variable`, `std::stop_token`.
- **Ignoring `-Wconversion` and `-Wsign-compare`.** Silent narrowing is a real bug source.
- **Catching `...` and swallowing.** If you can't handle it, let it propagate - the process restart is the last line.
- **`std::lock` without `scoped_lock`.** Exception-safe unlock matters.
- **Assuming `unsigned` overflow is defined AND using it for logic.** Defined, but usually a bug indicator.
- **Running tests without sanitizers in CI.** The bug is there; you just don't see it yet.

## Standard Workflow

1. **Clarify latency/throughput/cost budgets** - P99 target in microseconds, QPS, memory ceiling, cold-start acceptable.
2. **Pick toolchain and standard** - Clang or GCC, pinned; C++20 or C++23; reproducible build (Conan/vcpkg + lockfile).
3. **Design ownership graph** - draw who owns what. Annotate non-owning borrows. Identify shared state and its invariants.
4. **Choose concurrency model** - threads + channels, coroutines, or single-threaded event loop. Don't mix without a clear boundary.
5. **Define interfaces** - header-only where sensible, PIMPL where ABI matters. Pure functions for testability.
6. **Implement with hardening** - `-fsanitize=address,undefined` debug builds; `-fsanitize=thread` for concurrent; hardening flags (`-fstack-protector-strong`, `-D_FORTIFY_SOURCE=2`, `-fPIE`, `-Wl,-z,now,-z,relro`).
7. **Test exhaustively** - unit with GoogleTest or Catch2, property with rapidcheck, fuzz with libFuzzer on every parser and protocol handler, integration with realistic deps.
8. **Profile before optimizing** - `perf record` + `perf report`, flamegraphs, `pmu-tools` for cache and branch analysis.
9. **Observability** - structured logs (spdlog with JSON formatter), Prometheus metrics (prometheus-cpp), tracing (OpenTelemetry C++).
10. **Crash diagnostics** - core dumps enabled, symbolized traces, minidump if cross-platform; log crash reason and rotation policy for PII.

## Default Toolchain (2026 baseline)

- Language: C++20 (baseline), C++23 where toolchain supports.
- Compiler: Clang 17+ (preferred), GCC 13+.
- Build: CMake 3.28+ with Ninja; `FetchContent` or Conan 2 / vcpkg for deps with lockfile.
- LTO + PGO for release binaries.
- Static analysis: clang-tidy (with project `.clang-tidy`), include-what-you-use.
- Formatting: clang-format with project `.clang-format`.
- Testing: GoogleTest or Catch2; rapidcheck for property tests; libFuzzer / AFL++ for fuzzing.
- Sanitizers: ASan + UBSan in every CI config; TSan in a dedicated CI lane; MSan (Clang) where available.
- Benchmarks: google/benchmark; nanobench for tight loops.
- Observability: spdlog (JSON), prometheus-cpp, OpenTelemetry-cpp.
- Networking: Asio (standalone or Boost) or liburing (Linux-only for max throughput).
- Serialization: Protobuf (default), FlatBuffers (zero-copy needs), Cap'n Proto (strict zero-copy).

## Security Hardening Checklist

- Compiler: `-D_FORTIFY_SOURCE=2`, `-fstack-protector-strong`, `-fPIE`, `-fstack-clash-protection`, `-fcf-protection` (CET).
- Linker: `-Wl,-z,relro -Wl,-z,now -Wl,-z,noexecstack`.
- Runtime: ASLR enabled (default), seccomp-bpf sandboxing for risky subsystems, drop privileges, `chroot` or namespaces.
- Build: reproducible builds, pinned toolchain, SBOM produced, dependency CVE scanning.
- Code: no `strcpy`, `sprintf`, `gets`, `atoi`; use `snprintf`, `std::from_chars`, `std::format`. Validate all lengths. Constant-time crypto primitives only.

## Deliverables Contract

- CMakeLists.txt with warnings-as-errors, sanitizer CI configs, LTO for release.
- Ownership documented in headers; PIMPL for ABI-stable libraries.
- Hardening flags enabled in release builds.
- GoogleTest/Catch2 unit tests; libFuzzer harnesses for every parser.
- Sanitizer CI: ASan+UBSan always, TSan on concurrency modules.
- spdlog JSON logs with trace context; prometheus-cpp metrics; OpenTelemetry-cpp tracing.
- Graceful shutdown with deadline-bounded drain; signal handlers installed once at startup.
- Multi-stage Dockerfile with distroless or scratch base where possible; non-root.
- Benchmarks in CI with regression gates.
- Runbook covering crash analysis, core dump location, symbolization command.

Quality gates: sanitizers clean in CI, no `new`/`delete` outside RAII wrappers, no owning raw pointers in public APIs, no UB warnings, no fuzzer crashes after N hours, bounded queues everywhere, all external inputs validated for length and shape, allocation rate in hot paths measured and bounded, tail latency P99 measured and within budget.
