# Practical gradient-descent lesson

## Learner turn 1

Teach me gradient descent practically. Use a real two-parameter model or the smallest executable example, let me change something, and make me debug a failed step. Do not take over a project for me.

## Tutor turn 1

We’ll learn this by running a tiny two-parameter linear model, changing it, and debugging one deliberately bad step. We’ll work through host chat with the supplied Python fixture; no files will be changed.

The model is:

```text
prediction = w*x + b
loss = mean((prediction - target)^2)
```

For the first run:

```text
x       = [1, 2, 3]
target  = [1.5, 2.0, 2.5]
w       = 0.2
b       = 0.5
rate    = 0.1
```

Before we run it, predict:

1. Will the next `w` be larger or smaller than `0.2`?
2. Will the next `b` be larger or smaller than `0.5`?
3. Will the loss go up or down?

An exact calculation is optional. If you’re unsure, say “I don’t know.”

## Learner turn 2

w should be larger than 0.2, b larger than 0.5, and the loss should go down because all starting predictions are below their targets.

## Tutor turn 2

Your prediction was correct: every starting prediction was below its target, so both gradients were negative; subtracting a negative gradient increases `w` and `b`, and the loss falls.

Command run:

```bash
python3 /Users/prax/Developer/skills-and-personas/skills/teach-pro-max/references/prax-teach-v2/evidence/forward/execution/practical_gradient_descent.py rent-stable
```

Observed stdout:

```text
case=rent-stable learning_rate=0.10
before w=0.200 b=0.500 predictions=[0.70, 0.90, 1.10] loss=1.270
gradients dw=-4.800 db=-2.200
after w=0.680 b=0.720 predictions=[1.40, 2.08, 2.76] loss=0.028
```

Now make one change: increase only the learning rate from `0.10` to `1.00`, keeping the data and starting parameters unchanged.

Before we run it, predict: will the loss decrease again, or will this step fail by overshooting? What output would convince you that it failed?

## Learner turn 3

I predict overshoot. A loss much larger than 1.270 and predictions jumping far past the targets would convince me the step failed.

## Tutor turn 3

Your prediction matched the evidence exactly: predictions jumped far past the targets, and loss rose from `1.270` to `127.990`.

Command run:

```bash
python3 /Users/prax/Developer/skills-and-personas/skills/teach-pro-max/references/prax-teach-v2/evidence/forward/execution/practical_gradient_descent.py rent-overshoot
```

Observed stdout:

```text
case=rent-overshoot learning_rate=1.00
before w=0.200 b=0.500 predictions=[0.70, 0.90, 1.10] loss=1.270
gradients dw=-4.800 db=-2.200
after w=5.000 b=2.700 predictions=[7.70, 12.70, 17.70] loss=127.990
```

Debug the failed step using:

```text
w_new = w - learning_rate * dw
b_new = b - learning_rate * db
```

Calculate `w_new` and `b_new` with `learning_rate=1.00`. Then identify whether the failure is caused by the gradient direction or by the step size.

## Learner turn 4

w_new = 0.2 - 1.0(-4.8) = 5.0 and b_new = 0.5 - 1.0(-2.2) = 2.7. The gradient direction is useful; the step size is too large.

## Tutor turn 4

Exactly. The gradient direction was useful; the learning rate multiplied a valid correction into an excessively large jump.

Now transfer the rule to a new dataset:

```text
x       = [1, 2]
target  = [5, 7]
w       = 1.0
b       = 1.0
rate    = 0.1
```

Before running the fixture, predict whether `w` and `b` will increase or decrease, and whether the loss will go up or down. An exact calculation is optional.

## Learner turn 5

Both starting predictions are below their targets, so I predict w and b will increase and the loss will go down.

## Tutor turn 5

Your transfer prediction was correct.

Command run:

```bash
python3 /Users/prax/Developer/skills-and-personas/skills/teach-pro-max/references/prax-teach-v2/evidence/forward/execution/practical_gradient_descent.py delivery-transfer
```

Observed stdout:

```text
case=delivery-transfer learning_rate=0.10
before w=1.000 b=1.000 predictions=[2.00, 3.00] loss=12.500
gradients dw=-11.000 db=-7.000
after w=2.100 b=1.700 predictions=[3.80, 5.90] loss=1.325
```

The same rule held on new data: negative gradients increased both parameters, and the moderate step reduced loss. You also diagnosed the failed large-rate step by tracing it to the update magnitude.

Teach it back in one or two sentences: what do the gradient and learning rate each control?

## Learner turn 6

The gradient supplies the local direction and parameter-specific slope; the learning rate scales how far we move along that correction. A useful direction can still fail when the rate makes the step overshoot.

## Tutor turn 6

Lesson complete.

You independently:

- Predicted a stable update correctly.
- Changed the learning rate and predicted overshoot.
- Debugged the failure to excessive step size.
- Transferred the rule to new data.
- Explained the gradient and learning rate accurately.

Your summary:

> “The gradient supplies the local direction and parameter-specific slope; the learning rate scales how far we move along that correction. A useful direction can still fail when the rate makes the step overshoot.”

No files were changed. What remains untested is writing or modifying the implementation independently. For retrieval, revisit this tomorrow: choose a new starting `w`, `b`, and learning rate, predict the update before running it, then explain any mismatch.
