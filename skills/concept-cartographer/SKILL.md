---
name: concept-cartographer
description: "Generate visual concept maps, flowcharts, architecture diagrams, and relationship diagrams from structured notes or technical content using Mermaid syntax. Use when the user has lecture notes, study materials, or technical documentation and wants visual diagrams to aid understanding. Produces multiple diagram types: concept hierarchy maps, process flowcharts, architecture diagrams, comparison matrices, timeline diagrams, and mind maps. Trigger phrases: 'create diagrams from notes', 'visualize concepts', 'concept map', 'make flowcharts', 'diagram this', 'visual notes'."
---

# Concept Cartographer - Visual Knowledge Mapper

Generate visual diagrams from structured notes and technical content using Mermaid syntax.

## Core Purpose

Transform text-based knowledge into visual maps that reveal structure, relationships, and flow. Produce multiple diagram types tuned to different learning needs -- from high-level concept hierarchies to detailed process flows.

## Diagram Types

For each set of notes, generate the most relevant subset of these diagram types:

### 1. Concept Hierarchy Map
Shows how topics relate parent-child.

```mermaid
graph TD
    A[Neural Networks] --> B[Architecture]
    A --> C[Training]
    A --> D[Activation Functions]
    B --> B1[Input Layer]
    B --> B2[Hidden Layers]
    B --> B3[Output Layer]
    C --> C1[Forward Pass]
    C --> C2[Loss Calculation]
    C --> C3[Backpropagation]
    C --> C4[Weight Update]
    D --> D1[Sigmoid]
    D --> D2[ReLU]
```

**Use when:** Content has clear topic hierarchy (most lectures).

### 2. Process Flowchart
Shows step-by-step procedures and decision points.

```mermaid
flowchart LR
    A[Input Data] --> B[Forward Pass]
    B --> C[Calculate Loss]
    C --> D{Loss acceptable?}
    D -->|No| E[Backpropagation]
    E --> F[Update Weights]
    F --> B
    D -->|Yes| G[Model Ready]
```

**Use when:** Content describes processes, algorithms, or workflows.

### 3. Architecture Diagram
Shows system components and data flow.

```mermaid
graph LR
    subgraph Input Layer
        I1[x1] & I2[x2]
    end
    subgraph Hidden Layer
        H1[h1] & H2[h2] & H3[h3]
    end
    subgraph Output
        O1[y]
    end
    I1 & I2 --> H1 & H2 & H3
    H1 & H2 & H3 --> O1
```

**Use when:** Content describes architectures, systems, or component relationships.

### 4. Comparison Diagram
Shows differences between concepts side by side.

```mermaid
graph TD
    A[Activation Functions] --> B[Sigmoid]
    A --> C[ReLU]
    B --> B1["Range: 0 to 1"]
    B --> B2["Use: Output layer"]
    B --> B3["Problem: Vanishing gradient"]
    C --> C1["Range: 0 to infinity"]
    C --> C2["Use: Hidden layers"]
    C --> C3["Problem: Dead neurons"]
```

**Use when:** Content compares alternatives, trade-offs, or choices.

### 5. Timeline / Sequence Diagram
Shows order of events or data flow over time.

```mermaid
sequenceDiagram
    participant D as Data
    participant N as Network
    participant L as Loss Function
    participant O as Optimizer
    D->>N: Forward pass
    N->>L: Predictions
    L->>L: Calculate error
    L->>N: Gradients (backprop)
    N->>O: Current weights + gradients
    O->>N: Updated weights
```

**Use when:** Content describes interactions, API flows, or sequential processes.

### 6. State Diagram
Shows states and transitions.

```mermaid
stateDiagram-v2
    [*] --> Untrained
    Untrained --> Training: Start training
    Training --> Evaluating: Each epoch
    Evaluating --> Training: Loss too high
    Evaluating --> Trained: Loss acceptable
    Trained --> Deployed: Deploy
    Deployed --> Training: Retrain
```

**Use when:** Content describes lifecycle, states, or mode changes.

## Domain-Specific Focus

| Domain | Priority Diagrams | Special Elements |
|--------|------------------|-----------------|
| **AI/ML** | Architecture, process flow, comparison | Layer structures, training loops, model pipelines |
| **WebDev** | Architecture, sequence, flowchart | Request/response flows, component trees, state management |
| **Web3** | Sequence, architecture, state | Transaction flows, smart contract interactions, token flows |
| **DSA** | Flowchart, state, comparison | Algorithm steps, tree/graph structures, complexity comparisons |

## Output Format

For each set of notes, produce a markdown document with:

```markdown
# Visual Concept Maps: [Topic]

## Overview Map
[Concept hierarchy - always include this one]

## [Diagram Type 2 title]
[Most relevant additional diagram]

## [Diagram Type 3 title]
[Second most relevant]

## Key Relationships Summary
- [Concept A] depends on [Concept B] because...
- [Concept C] is an alternative to [Concept D] when...
- [Process X] feeds into [Process Y] via...
```

## Rules

1. **Every diagram must be valid Mermaid syntax** - test mentally before output
2. **Always include concept hierarchy** - this is the minimum output
3. **Pick 2-4 diagram types** per set of notes based on content
4. **Label nodes clearly** - use short but descriptive text
5. **Don't overcrowd** - split large diagrams into focused sub-diagrams (max ~15 nodes per diagram)
6. **Use subgraphs** for grouping related concepts
7. **Add a text summary** of key relationships below diagrams
8. **Match the domain** - use domain-appropriate terminology and diagram choices

## Pipeline Position

This skill is **Stage 3** in the lecture processing pipeline:
1. **transcribe-refiner** → clean transcript
2. **lecture-alchemist** → structured study notes
3. **concept-cartographer** (this) → visual diagrams
4. **obsidian-markdown** → Obsidian vault formatting
