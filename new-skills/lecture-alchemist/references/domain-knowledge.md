# LECTURE ALCHEMIST - Domain Knowledge Base

## Purpose
This document provides domain-specific context for processing lectures in different technical fields. Lecture Alchemist uses this to adapt its processing based on the subject matter.

---

## DOMAIN DETECTION

### Auto-Detection Triggers

| Domain | Keyword Triggers |
|--------|------------------|
| **WebDev** | React, Node, Express, MongoDB, API, REST, GraphQL, CSS, HTML, deployment, Vercel, AWS, Docker, database, authentication, JWT, hooks, components |
| **AI/ML** | neural network, model, training, inference, loss function, gradient, epoch, batch, tensor, PyTorch, TensorFlow, transformer, LLM, embedding, hyperparameter |
| **Web3** | Solidity, smart contract, blockchain, Ethereum, gas, wallet, MetaMask, DeFi, NFT, token, ERC-20, ERC-721, Hardhat, Foundry, Anchor, Solana |
| **DSA** | array, linked list, tree, graph, hash, sort, search, dynamic programming, recursion, Big O, time complexity, space complexity, LeetCode |

### Override
the user can explicitly specify: `Domain: [WebDev | AI/ML | Web3 | DSA]`

---

## WEBDEV DOMAIN

### Key Concepts to Always Extract

**Frontend:**
- Component patterns
- State management approaches
- Styling methodologies
- Performance optimizations
- Accessibility considerations
- Browser APIs used

**Backend:**
- API design patterns
- Database operations
- Authentication flows
- Middleware concepts
- Error handling
- Environment configuration

**DevOps:**
- Deployment processes
- CI/CD mentions
- Environment variables
- Docker/containerization
- Cloud services

### Technical Analysis Focus

```
### WebDev Technical Analysis

**Architecture Pattern:**
[MVC, Component-based, JAMstack, etc.]

**State Management:**
[How state is handled - local, global, server state]

**API Design:**
[REST conventions, error handling, versioning]

**Performance Considerations:**
- Rendering: [SSR, CSR, ISR, SSG]
- Bundle size: [Code splitting, lazy loading]
- Caching: [Strategies mentioned]

**Security Checklist:**
- [ ] Input validation
- [ ] Authentication/Authorization
- [ ] CORS configuration
- [ ] Environment secrets handling

**Production Readiness:**
[What's needed before deploying]
```

### Common Instructor Shortcuts (Fill These)

| What They Say | What They Skip |
|---------------|----------------|
| "Just add a useEffect" | Dependency array gotchas, cleanup functions |
| "We'll use JWT" | Token storage security (httpOnly cookies vs localStorage) |
| "Deploy to Vercel" | Environment variables, build configuration |
| "Add CORS" | Specific headers, preflight requests |
| "Use async/await" | Error handling with try-catch |

### Code Extraction Priorities
1. React component patterns
2. API route definitions
3. Database queries
4. Authentication logic
5. Configuration files (package.json, .env structure)

---

## AI/ML DOMAIN

### Key Concepts to Always Extract

**Fundamentals:**
- Model architecture
- Loss functions used
- Optimization algorithms
- Activation functions
- Regularization techniques

**Training:**
- Data preprocessing steps
- Train/validation/test splits
- Hyperparameters mentioned
- Training loops
- Metrics tracked

**Inference:**
- Model loading
- Input preprocessing
- Output post-processing
- Deployment considerations

### Technical Analysis Focus

```
### AI/ML Technical Analysis

**Model Architecture:**
[Type, layers, parameters]

**Mathematical Foundation:**
| Concept | Intuition |
|---------|-----------|
| [Loss function] | [Why it works] |
| [Optimizer] | [How it updates weights] |

**Hyperparameters Discussed:**
| Parameter | Value/Range | Effect |
|-----------|-------------|--------|
| Learning rate | | |
| Batch size | | |
| Epochs | | |

**Data Considerations:**
- Input shape: [Expected dimensions]
- Preprocessing: [Steps required]
- Augmentation: [Techniques mentioned]

**Computational Requirements:**
- Training: [GPU needed? Time estimate?]
- Inference: [Can run on CPU?]

**When to Use This:**
[Problem types this model/technique suits]

**When NOT to Use:**
[Limitations, failure cases]
```

### Common Instructor Shortcuts (Fill These)

| What They Say | What They Skip |
|---------------|----------------|
| "Use Adam optimizer" | Learning rate scheduling, weight decay |
| "Add a dropout layer" | Where to place it, dropout rate selection |
| "Normalize your data" | Why (gradient stability), which normalization |
| "The model is overfitting" | How to diagnose, specific remedies |
| "Use cross-entropy loss" | Why for classification, softmax relationship |

### Intuition Builders to Always Include

For any neural network concept:
1. **What it does** (function)
2. **Why it works** (mathematical intuition, simplified)
3. **When to adjust it** (practical tuning)
4. **Visual metaphor** (how to picture it)

### Code Extraction Priorities
1. Model definitions (class or functional)
2. Training loops
3. Data loading/preprocessing
4. Evaluation code
5. Inference examples

---

## WEB3 DOMAIN

### Key Concepts to Always Extract

**Smart Contracts:**
- Contract structure
- State variables
- Functions (public, private, view, pure)
- Events and logging
- Modifiers
- Inheritance patterns

**Blockchain Concepts:**
- Transaction lifecycle
- Gas mechanics
- Block confirmations
- Network differences (testnet vs mainnet)

**Security:**
- Access control
- Reentrancy guards
- Integer overflow (historical)
- Front-running considerations

**Tooling:**
- Development frameworks (Hardhat, Foundry, Anchor)
- Testing approaches
- Deployment scripts

### Technical Analysis Focus

```
### Web3 Technical Analysis

**Contract Analysis:**
| Aspect | Details |
|--------|---------|
| Standard compliance | [ERC-20, ERC-721, etc.] |
| Storage layout | [State variables and their costs] |
| External calls | [Interactions with other contracts] |

**Gas Optimization:**
- Storage vs Memory usage
- Loop efficiency
- Batch operations
- View/Pure function usage

**Security Checklist:**
- [ ] Reentrancy protection
- [ ] Access control (onlyOwner, roles)
- [ ] Input validation
- [ ] Integer handling
- [ ] Timestamp dependence
- [ ] Front-running vulnerability

**Testing Strategy:**
- Unit tests needed: [List]
- Integration tests: [List]
- Testnet deployment checklist

**Mainnet Readiness:**
- [ ] Audit considerations
- [ ] Upgrade patterns (if applicable)
- [ ] Emergency procedures
```

### Common Instructor Shortcuts (Fill These)

| What They Say | What They Skip |
|---------------|----------------|
| "Deploy to testnet" | Getting testnet ETH, network configuration |
| "Use OpenZeppelin" | Which contracts, import patterns |
| "Add a modifier" | Common modifier patterns, gas implications |
| "Emit an event" | Indexed parameters, frontend listening |
| "Call the contract" | ABI, ethers.js/web3.js patterns |

### Security Emphasis
Web3 notes should ALWAYS include security analysis because:
- Money is directly at stake
- Bugs are often irreversible
- Audits expect certain patterns

### Code Extraction Priorities
1. Smart contract definitions
2. Deployment scripts
3. Test cases
4. Frontend integration code
5. Configuration (hardhat.config.js, foundry.toml)

---

## DSA DOMAIN

### Key Concepts to Always Extract

**Algorithm Components:**
- Approach/technique name
- Core insight/trick
- Step-by-step process
- Time complexity
- Space complexity
- Edge cases

**Data Structure Usage:**
- Why this structure was chosen
- Operations used
- Trade-offs

**Pattern Recognition:**
- What category this falls into
- Similar problems
- When to recognize this pattern

### Technical Analysis Focus

```
### DSA Technical Analysis

**Complexity Analysis:**
| Metric | Complexity | Explanation |
|--------|------------|-------------|
| Time (Best) | O(?) | [When this occurs] |
| Time (Average) | O(?) | [Typical case] |
| Time (Worst) | O(?) | [When this occurs] |
| Space | O(?) | [What uses space] |

**Pattern Classification:**
Primary: [Two Pointers | Sliding Window | BFS/DFS | DP | etc.]
Secondary: [Related patterns]

**Problem Recognition Triggers:**
- "When you see [X], think [this approach]"
- Input characteristics that suggest this pattern

**Common Variations:**
1. [Variation 1] - [How it differs]
2. [Variation 2] - [How it differs]

**Interview Context:**
- Frequency: [High/Medium/Low at FAANG]
- Companies known to ask: [If mentioned]
- Follow-up questions to expect

**Edge Cases:**
- [ ] Empty input
- [ ] Single element
- [ ] All same elements
- [ ] Maximum constraints
- [ ] [Problem-specific edges]
```

### Common Instructor Shortcuts (Fill These)

| What They Say | What They Skip |
|---------------|----------------|
| "Use two pointers" | Which pointer moves when, termination condition |
| "This is O(n)" | The constant factors, why not O(n²) |
| "DP approach" | State definition, recurrence relation derivation |
| "Sort the array first" | When sorting helps, when it doesn't |
| "Use a hash map" | Collision handling, space trade-off |

### Intuition Builders to Always Include

For any algorithm:
1. **Why it works** (correctness argument)
2. **Why it's efficient** (what work it avoids)
3. **Visual walkthrough** (trace through example)
4. **When it fails** (limitations, wrong use cases)

### Pattern Library Reference

| Pattern | Recognition Signal | Key Insight |
|---------|-------------------|-------------|
| Two Pointers | Sorted array, pair finding | Avoid nested loops |
| Sliding Window | Contiguous subarray, fixed/variable size | Maintain running state |
| Binary Search | Sorted data, min/max optimization | Eliminate half each step |
| BFS | Shortest path, level-order | Explore by distance |
| DFS | All paths, backtracking | Explore depth first |
| Dynamic Programming | Optimal substructure, overlapping subproblems | Cache computed results |
| Greedy | Local optimal → global optimal | Make best choice now |
| Divide & Conquer | Independent subproblems | Solve parts separately |
| Union Find | Connectivity, grouping | Efficient set operations |
| Monotonic Stack | Next greater/smaller | Maintain order property |

### Code Extraction Priorities
1. Core algorithm implementation
2. Helper functions
3. Test cases / examples
4. Edge case handling
5. Optimization variations

---

## CROSS-DOMAIN CONNECTIONS

Help the user see connections across his learning:

| Concept in X | Related Concept in Y |
|--------------|---------------------|
| WebDev: Memoization (useMemo) | DSA: Dynamic Programming |
| AI/ML: Gradient Descent | DSA: Optimization algorithms |
| Web3: Merkle Trees | DSA: Tree structures |
| WebDev: Event Loop | DSA: Queue data structure |
| AI/ML: Attention mechanism | DSA: Weighted graphs |
| Web3: Gas optimization | DSA: Time/Space complexity |

When processing a lecture, note if concepts connect to other domains the user is studying.

---

## RESOURCE RECOMMENDATIONS BY DOMAIN

### WebDev
- **Docs:** MDN, React docs, Node.js docs
- **Practice:** Build projects, Frontend Mentor
- **Deep Dive:** web.dev, patterns.dev

### AI/ML
- **Fundamentals:** 3Blue1Brown neural networks, StatQuest
- **Practice:** Kaggle, Papers With Code
- **Math:** Khan Academy linear algebra, calculus

### Web3
- **Docs:** Solidity docs, ethereum.org
- **Security:** Smart Contract Programmer, Secureum
- **Practice:** Ethernaut, Damn Vulnerable DeFi

### DSA
- **Practice:** LeetCode, NeetCode roadmap
- **Visualization:** VisuAlgo, Algorithm Visualizer
- **Patterns:** Grokking the Coding Interview patterns

---

## VERSION HISTORY

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | January 2026 | Initial domain knowledge base |
