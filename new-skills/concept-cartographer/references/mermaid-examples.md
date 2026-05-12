**When to load this file:** Only if you need a syntax reminder for a specific diagram type. One example per type — not a reference manual.

## Concept Hierarchy

```mermaid
graph TD
    A[Neural Networks] --> B[Architecture]
    A --> C[Training]
    B --> B1[Input Layer]
    B --> B2[Hidden Layers]
    C --> C1[Forward Pass]
    C --> C2[Backpropagation]
```

## Process Flowchart

```mermaid
flowchart LR
    A[Input Data] --> B[Forward Pass]
    B --> C{Loss acceptable?}
    C -->|No| D[Backprop + Update]
    D --> B
    C -->|Yes| E[Model Ready]
```

## Architecture (with subgraphs)

```mermaid
graph LR
    subgraph Input
        I1[x1] & I2[x2]
    end
    subgraph Hidden
        H1[h1] & H2[h2]
    end
    subgraph Output
        O1[y]
    end
    I1 & I2 --> H1 & H2
    H1 & H2 --> O1
```

## Sequence

```mermaid
sequenceDiagram
    participant D as Data
    participant N as Network
    participant L as Loss
    D->>N: Forward pass
    N->>L: Predictions
    L->>N: Gradients
```

## State

```mermaid
stateDiagram-v2
    [*] --> Untrained
    Untrained --> Training: Start
    Training --> Evaluating: Each epoch
    Evaluating --> Training: Loss high
    Evaluating --> Trained: Loss OK
```

## Learning-path

```mermaid
graph LR
    A[Linear Algebra] --> B[Neural Basics]
    A --> C[Gradient Descent]
    B --> D[Backpropagation]
    C --> D
```

## Quadrant

```mermaid
quadrantChart
    title Concept Difficulty vs Importance
    x-axis Low --> High Difficulty
    y-axis Low --> High Importance
    Neuron anatomy: [0.3, 0.7]
    Backpropagation: [0.8, 0.9]
```
