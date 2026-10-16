# Practical gradient-descent lesson

## Learner turn 1

Teach me gradient descent practically. Use a real two-parameter model or the smallest executable example, let me change something, and make me debug a failed step. Do not take over a project for me.

## Tutor turn 1

Let’s work toward one concrete skill: use a two-parameter model, \(\hat y = wx+b\), to predict whether a gradient step improves the loss, change a parameter yourself, and debug an overshoot.

We’ll do this through host chat using the supplied executable fixture; you’ll choose the modification.

**Prediction — don’t run anything yet**

- Inputs: `x = [1, 2, 3]`
- Targets: `y = [1.5, 2.0, 2.5]`
- Start: `w = 0.2`, `b = 0.5`
- Learning rate: `0.1`

What do you predict after one gradient-descent step? Include the three starting predictions, whether MSE goes up or down, and whether `w` and `b` move up or down.

Reply with your prediction, or **“I don’t know.”**

## Learner turn 2

The starting predictions are 0.7, 0.9, and 1.1. I expect the MSE to go down, with both w and b increasing.

## Tutor turn 2

Your prediction was correct: the starting predictions are `[0.70, 0.90, 1.10]`, the loss falls, and both parameters increase. Because both gradients are negative, subtracting the gradient moves `w` and `b` upward.

Command run:

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

Now change exactly one thing: choose a new learning rate while keeping the data, `w`, and `b` fixed. What value will you use, and do you predict the next loss will be lower or higher? Don’t run it yet.

## Learner turn 3

Let’s change the learning rate to 0.5. I predict the next loss will be higher because the same gradient produces a five-times-larger step and overshoots.

## Learner turn 4

Correction from learner before you run: use the fixture’s overshoot case at learning rate 1.0 instead. I predict the loss will be much higher because the same gradient produces a ten-times-larger step and overshoots.

## Tutor turn 3

Good correction. The fixture’s overshoot case uses a learning rate of `1.0`, ten times the stable run’s rate.

Command run:

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

Your prediction was correct: the loss jumped from `1.270` to `127.990`.

Debug this failed step: what would you inspect first, and what single change would you make to recover? Point to the output evidence that supports your diagnosis.

## Learner turn 5

I would inspect the learning rate first. The gradients are unchanged, but w jumps from 0.2 to 5.0 and the loss from 1.270 to 127.990, which supports overshoot. I would restore the learning rate to 0.10.

## Tutor turn 4

That diagnosis is correct. You used the key rule:

```text
parameter_new = parameter_old - learning_rate * gradient
```

The gradient direction was still useful; the learning rate made the step too large. You identified the failure from the parameter jump and the loss increase, then chose the repair.

Now transfer the idea to a new case—don’t run it yet:

- Inputs: `x = [1, 2]`
- Targets: `y = [5, 7]`
- Start: `w = 1.0`, `b = 1.0`
- Learning rate: `0.1`

Predict the starting outputs, whether the loss will go up or down after one step, and whether `w` and `b` move up or down.

## Learner turn 6

The starting outputs are 2.0 and 3.0. Both are below the targets, so I expect negative gradients, w and b to increase, and the loss to go down after one step.

## Tutor turn 5

Your transfer prediction was correct: both outputs were below their targets, so both gradients were negative, `w` and `b` increased, and the loss fell.

Command run:

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

Teach it back in one or two sentences: how do gradient sign and learning-rate magnitude determine the update, and what output evidence tells you a step overshot?

## Learner turn 7

Subtracting a negative gradient increases a parameter and subtracting a positive one decreases it; the learning rate scales how far it moves. A sharp loss increase together with predictions jumping far past the targets is evidence that the step overshot.

## Tutor turn 6

That teach-back is accurate.

You demonstrated:

- prediction of parameter direction and loss change;
- debugging an oversize learning rate from observable output;
- transfer to a new dataset and model state;
- an accurate causal explanation without hints.

No files or learner state were created or changed; the fixture was run read-only.

For retrieval, within 24 hours, compute one fresh update by hand and check whether the loss should decrease before running it.
