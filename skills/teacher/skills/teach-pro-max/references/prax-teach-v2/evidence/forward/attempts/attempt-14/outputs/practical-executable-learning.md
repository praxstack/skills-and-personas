# Practical gradient-descent lesson

## Learner turn 1

Teach me gradient descent practically. Use a real two-parameter model or the smallest executable example, let me change something, and make me debug a failed step. Do not take over a project for me.

## Tutor turn 1

Prediction first—don’t run anything yet.

We’ll fit the two-parameter model:

```text
ŷ = w·x + b
x       = [1, 2, 3]
targets = [1.5, 2.0, 2.5]
starting w = 0.2, b = 0.5
learning rate = 0.1
```

Using mean squared error, predict what one gradient-descent step will do: will the loss increase or decrease, and roughly what will the new `w` and `b` be? Give your reasoning—or say “I don’t know.”

## Learner turn 2

Starting predictions are 0.7, 0.9, and 1.1, all below the targets. I expect negative gradients, so w and b increase; using the MSE gradients I predict w = 0.68, b = 0.72, and lower loss.

## Tutor turn 2

Correct. All predictions were below targets, so the gradients are negative; subtracting them increases `w` and `b`.

Run:

```bash
python3 /Users/prax/Developer/skills-and-personas/skills/teach-pro-max/references/prax-teach-v2/evidence/forward/execution/practical_gradient_descent.py rent-stable
```

Actual stdout:

```text
case=rent-stable learning_rate=0.10
before w=0.200 b=0.500 predictions=[0.70, 0.90, 1.10] loss=1.270
gradients dw=-4.800 db=-2.200
after w=0.680 b=0.720 predictions=[1.40, 2.08, 2.76] loss=0.028
```

Now make one purposeful change: use the same model and data with `learning_rate=1.0` by running the `rent-overshoot` case. Before running it, predict: will the loss improve or get worse, and what might that tell you about the step size?

## Learner turn 3

I predict the loss gets much worse because the ten-times-larger rate overshoots; predictions should jump far beyond the targets, showing the step size—not the gradient direction—is the problem.

## Tutor turn 3

Exactly: the direction is still right, but the step is too large.

Run:

```bash
python3 /Users/prax/Developer/skills-and-personas/skills/teach-pro-max/references/prax-teach-v2/evidence/forward/execution/practical_gradient_descent.py rent-overshoot
```

Actual stdout:

```text
case=rent-overshoot learning_rate=1.00
before w=0.200 b=0.500 predictions=[0.70, 0.90, 1.10] loss=1.270
gradients dw=-4.800 db=-2.200
after w=5.000 b=2.700 predictions=[7.70, 12.70, 17.70] loss=127.990
```

Debug the failed step: the gradients are identical to the stable run, but the loss explodes. Is the update direction wrong, or is its magnitude wrong? Name the single change you’d make, then predict the next `w`, `b`, and loss before rerunning.

## Learner turn 4

The magnitude is wrong, not the direction. I would change only the learning rate back to 0.1; from the same start I predict w = 0.68, b = 0.72, and loss about 0.028.

## Tutor turn 4

Right. The gradients stayed valid; reducing the learning rate fixes the update magnitude.

Rerun:

```bash
python3 /Users/prax/Developer/skills-and-personas/skills/teach-pro-max/references/prax-teach-v2/evidence/forward/execution/practical_gradient_descent.py rent-stable
```

Actual stdout:

```text
case=rent-stable learning_rate=0.10
before w=0.200 b=0.500 predictions=[0.70, 0.90, 1.10] loss=1.270
gradients dw=-4.800 db=-2.200
after w=0.680 b=0.720 predictions=[1.40, 2.08, 2.76] loss=0.028
```

Transfer task—new data, same rule:

```text
x       = [1, 2]
targets = [5, 7]
starting w = 1.0, b = 1.0
learning rate = 0.1
```

Before running `delivery-transfer`, predict the signs of `dw` and `db`, then estimate the next `w`, `b`, and loss. Stop there; don’t run it yet.

## Learner turn 5

Starting predictions are 2 and 3, so residuals are -3 and -4. I predict dw = -11, db = -7, then w = 2.1, b = 1.7, and loss around 1.325.

## Tutor turn 5

Your transfer prediction was correct: both gradients are negative because both predictions are too low, so both parameters increase.

Run:

```bash
python3 /Users/prax/Developer/skills-and-personas/skills/teach-pro-max/references/prax-teach-v2/evidence/forward/execution/practical_gradient_descent.py delivery-transfer
```

Actual stdout:

```text
case=delivery-transfer learning_rate=0.10
before w=1.000 b=1.000 predictions=[2.00, 3.00] loss=12.500
gradients dw=-11.000 db=-7.000
after w=2.100 b=1.700 predictions=[3.80, 5.90] loss=1.325
```

Teach it back in two sentences: why do negative gradients increase `w` and `b`, and why can a learning rate that is too large make the loss worse?

## Learner turn 6

Gradient descent subtracts each gradient, so a negative gradient increases its parameter. The learning rate scales that update; if it is too large, a useful direction can jump past the low-loss region and make loss worse.

## Tutor turn 6

You reached the target for this small model:

- Predicted parameter updates before each run.
- Used actual stdout to verify the stable and overshooting steps.
- Diagnosed the failed step as excessive update magnitude.
- Applied the fix and transferred the rule to new data.
- Teach-back was accurate.

This demonstrates the rule on this fixture, not broad mastery yet. No files or learner state were changed.

Provisional retention horizon: 3 days. Recompute one unseen update then, and diagnose whether a bad result comes from gradient direction or learning-rate magnitude.
