# HFT / Quant Topics

Technical topic coverage for HFT and quantitative interview paths. Use to structure prep plans, surface unfamiliar territory, and generate practice questions.

---

## Low-Latency Programming

### Memory & Cache
- Cache line (64 bytes typically). Avoid false sharing.
- Hot vs cold data separation. Structure of arrays vs array of structures.
- NUMA awareness. Memory access across sockets.
- Prefetching — hardware and software hints.

**Sample question:** "You have a struct with a frequently-read field and a frequently-written field. Why is this a performance problem? How would you restructure it?"

### Branch Prediction
- Likely / unlikely hints (`__builtin_expect`, `[[likely]]`, `[[unlikely]]`)
- Branchless programming patterns
- Branch target buffers

**Sample question:** "Rewrite this conditional accumulation loop to be branchless. When is the branchless version slower?"

### CPU Pipelines & Instruction-Level Parallelism
- Superscalar execution
- Out-of-order execution
- Data hazards, pipeline stalls
- Speculative execution

### SIMD & Vectorization
- SSE / AVX / AVX-512
- When compilers auto-vectorize; when they don't
- Intrinsics vs compiler-driven vectorization

### Kernel Bypass & Networking
- Kernel bypass (DPDK, Solarflare, Mellanox)
- RDMA
- TCP vs UDP trade-offs for market data
- Timestamping (hardware vs software)

### Profiling & Measurement
- rdtsc for nanosecond-level timing
- perf, VTune, Linux perf counters
- Cache miss rates, branch mispredict rates

---

## Concurrency (HFT flavor)

### Lock-Free Programming
- Compare-and-swap (CAS)
- ABA problem
- Memory ordering: acquire, release, seq_cst, relaxed
- Lock-free queues (SPSC, MPMC)
- Hazard pointers, epoch-based reclamation

**Sample question:** "Implement a single-producer single-consumer lock-free queue. What memory ordering do you need on the producer? On the consumer?"

### Wait-Free Programming
- Difference from lock-free
- When wait-free is worth the extra complexity

### Atomics
- Atomic types (std::atomic in C++)
- Atomic operations: load, store, exchange, compare_exchange
- Fetch-and-add, fetch-and-or

### Data Races & UB
- Data race definition (C++ memory model)
- Undefined behavior consequences
- Tools: ThreadSanitizer, Helgrind

---

## Quantitative Mathematics

### Probability
- Conditional probability, Bayes' rule
- Expected value, variance, covariance
- Distributions: uniform, normal, exponential, Poisson, binomial, geometric
- Law of large numbers, central limit theorem

**Sample question:** "You're told a coin has 0.6 probability of heads. You flip it 10 times and get 7 heads. What's the probability the coin is fair given this data? Use Bayes."

### Statistics
- Hypothesis testing (p-values, confidence intervals)
- Linear regression, R²
- Correlation vs causation
- Overfitting, cross-validation

### Stochastic Processes
- Random walks
- Martingales
- Brownian motion (continuous-time)
- Markov chains

**Sample question:** "A random walk starts at 0. What's the expected number of steps to reach +10?"

### Options & Derivatives
- Put-call parity
- Black-Scholes intuition (not full derivation, but the inputs)
- Greeks: delta, gamma, vega, theta, rho — what each means
- Binomial tree pricing

**Sample question:** "A call option and a put option with the same strike and expiry — what's the relationship between their prices?"

### Portfolio Theory
- Expected return vs variance
- Efficient frontier
- Sharpe ratio, Sortino ratio
- CAPM intuition

---

## Market Microstructure

### Order Book Mechanics
- Limit orders vs market orders
- Bid-ask spread
- Price-time priority
- Matching engine logic
- Order types: limit, market, IOC, FOK, stop, iceberg

**Sample question:** "Design a matching engine. What data structure holds the bids? The asks? What happens when a market order arrives?"

### Market Making
- Bid-ask spread as compensation for risk
- Inventory management
- Adverse selection
- Tick size and its effect on spreads

### Execution Algorithms
- VWAP (volume-weighted average price)
- TWAP (time-weighted average price)
- Implementation shortfall
- POV (percentage of volume)

### Market Impact
- Linear vs square-root models
- Temporary vs permanent impact
- Why large orders are split

### Latency Arbitrage
- Geographic arbitrage (NYC — Chicago link)
- Speed advantages and their decay
- Co-location economics

---

## Quant Research Methodology

### Backtesting
- Look-ahead bias
- Survivorship bias
- Data-snooping bias
- Transaction cost modeling
- Out-of-sample testing

**Sample question:** "Your backtest shows a 3.0 Sharpe strategy. What are 5 things that could make this number misleading?"

### Alpha Research
- Signal construction
- Signal decay
- Factor models (Fama-French, etc.)
- Risk-neutral vs real-world probability

### Statistical Rigor
- Multiple hypothesis testing and Bonferroni correction
- Effect size vs statistical significance
- Bootstrap confidence intervals

---

## Programming Languages by Focus

### C++ (HFT production)
- Template metaprogramming
- RAII, move semantics, perfect forwarding
- constexpr, compile-time evaluation
- Custom allocators
- No exceptions / no RTTI in hot paths (common policy)

### Python (research)
- NumPy, Pandas
- SciPy, scikit-learn
- Vectorization vs loops (orders of magnitude)
- Cython / Numba for speed-up

### R (quant research at some firms)
- Data manipulation (dplyr, data.table)
- Time series (xts, zoo)
- Statistical packages

---

## Sample Interview Problem Types

### Puzzles (common at HFT)
- Probability puzzles ("you roll two dice, what's the probability the sum is 7 given it's odd?")
- Information theory puzzles (weighing problems, 12 balls)
- Estimation problems (how many ping-pong balls fit in a 747?)

### Coding in C++
- Implement a lock-free SPSC queue
- Fix a subtle race condition in this code
- Optimize this hot loop (cache, branch, vectorization)
- Implement a fixed-size memory pool allocator

### Math / Stats Oral
- Expected value of max of n uniform random variables
- Variance of sum of correlated random variables
- Derivation of central limit theorem (intuition, not full proof)

### System Design (HFT flavor)
- Design a market data feed handler
- Design an order management system with sub-100µs latency
- Design a backtester that handles 10 years of tick data

---

## Topic Prioritization by Firm Type

### Market Makers (Virtu, Tower, HRT, Flow Traders)
1. Market microstructure — heavy
2. Puzzles — heavy
3. Low-latency C++ — heavy
4. Math/probability — medium
5. System design — medium

### Stat-Arb / Research-Heavy (Two Sigma, DRW, Citadel Securities)
1. Statistics & probability — heavy
2. Research methodology — heavy
3. Python/R for data work — heavy
4. C++ for production — medium
5. Market microstructure — medium

### Ultra-Low-Latency (Jump Trading, Hudson River, Optiver)
1. Low-latency C++ — heavy
2. Concurrency & lock-free — heavy
3. Market microstructure — heavy
4. Math/probability — medium
5. Puzzles — medium

Tailor prep plan based on target firm type.
