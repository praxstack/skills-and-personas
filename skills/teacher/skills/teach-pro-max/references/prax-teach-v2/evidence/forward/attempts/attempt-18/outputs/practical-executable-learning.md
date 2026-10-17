# Practical gradient-descent lesson

## Learner turn 1

Teach me one gradient-descent update on tiny rent-price data. Make me predict before execution, show the exact command and complete output, let me change one input, help me debug a bad result, then give me a transfer task on delivery-time data.

## Tutor turn 1

We’ll use a small linear model:

\[
\hat y = wx+b
\]

Data: `x = [1, 2, 3]`, targets `y = [1.5, 2.0, 2.5]`
Current parameters: `w = 0.2`, `b = 0.5`, learning rate `0.1`.

Before running it, predict:

**After one gradient-descent step, will `w` increase or decrease, will `b` increase or decrease, and will the loss go up or down?** Include rough new values if you can.

## Learner turn 2

All three predictions are below their targets, so I expect negative gradients; subtracting them should increase both w and b, and the loss should fall. Roughly I expect w near 0.68 and b near 0.72. Please run the stable case and show the exact command and complete output so I can inspect it.

## Tutor turn 2

Your prediction was correct, including the rough values.

Command:

```bash
python3 /Users/prax/Developer/skills-and-personas/skills/teach-pro-max/references/prax-teach-v2/evidence/forward/execution/practical_gradient_descent.py rent-stable
```

Complete output:

```text
case=rent-stable learning_rate=0.10
before w=0.200 b=0.500 predictions=[0.70, 0.90, 1.10] loss=1.270
gradients dw=-4.800 db=-2.200
after w=0.680 b=0.720 predictions=[1.40, 2.08, 2.76] loss=0.028
```

Inspect the result: **which example is still farthest from its target after the step?**

## Learner turn 3

The third example is farthest from its target: 2.76 versus 2.5, an absolute error of 0.26. The first two absolute errors are only 0.10 and 0.08.

## Tutor turn 3

Correct. Changing `w` affects larger `x` values more, while changing `b` shifts every prediction equally.

Now make one deliberate change: raise the learning rate from `0.1` to `1.0` while keeping everything else the same.

**Before running `rent-overshoot`, predict whether the loss will decrease or increase, and why.**

## Learner turn 4

I predict the loss will increase sharply because the gradient direction is useful but a ten-times-larger step will overshoot the low-loss region. Please run rent-overshoot and show the exact command and complete output.

## Tutor turn 4

Your prediction was correct.

Command:

```bash
python3 /Users/prax/Developer/skills-and-personas/skills/teach-pro-max/references/prax-teach-v2/evidence/forward/execution/practical_gradient_descent.py rent-overshoot
```

Complete output:

```text
case=rent-overshoot learning_rate=1.00
before w=0.200 b=0.500 predictions=[0.70, 0.90, 1.10] loss=1.270
gradients dw=-4.800 db=-2.200
after w=5.000 b=2.700 predictions=[7.70, 12.70, 17.70] loss=127.990
```

Compare this with the stable run: **what single changed input explains the huge jump in loss?**

## Learner turn 5

Only the learning rate changed, from 0.10 to 1.00; the gradients stayed dw=-4.800 and db=-2.200. The direction was useful, but the larger step overshot. I would reduce only the learning rate first, then rerun before changing the model or data.

## Tutor turn 5

Exactly: the gradients were fine; the learning rate amplified the update too much. Reducing the rate is the right first debugging move.

Transfer the rule to new data:

- `x = [1, 2]`
- targets `y = [5, 7]`
- current `w = 1.0`, `b = 1.0`
- learning rate `0.1`

**Before running `delivery-transfer`, predict whether `w`, `b`, and the loss will increase or decrease.**

## Learner turn 6

The current predictions are [2, 3], so the errors are [-3, -4]. With n=2, dw=(-3*1)+(-4*2)=-11 and db=-3+-4=-7. Subtracting those gradients at 0.1 gives w=2.1 and b=1.7. Both parameters increase and I predict the loss decreases because the new predictions move toward [5, 7]. Please run delivery-transfer and show the exact command and complete output.

## Tutor turn 6

Your transfer prediction was correct.

Command:

```bash
python3 /Users/prax/Developer/skills-and-personas/skills/teach-pro-max/references/prax-teach-v2/evidence/forward/execution/practical_gradient_descent.py delivery-transfer
```

Complete output:

```text
case=delivery-transfer learning_rate=0.10
before w=1.000 b=1.000 predictions=[2.00, 3.00] loss=12.500
gradients dw=-11.000 db=-7.000
after w=2.100 b=1.700 predictions=[3.80, 5.90] loss=1.325
```

Final teach-back: **in one or two sentences, explain how gradient descent uses the gradients and learning rate to update `w` and `b`, and why a learning rate that is too large can make loss increase.**

## Learner turn 7

The gradients provide the local downhill direction for w and b, and the learning rate controls how far we move along that direction: new parameter = old parameter - learning_rate * gradient. If the rate is too large, the step can cross the low-loss region and land uphill, so the observed loss increases even when the gradient sign was useful.

## Tutor turn 7

You completed the practical loop:

- Predicted parameter direction and loss change.
- Ran and inspected three cases.
- Diagnosed overshooting as a learning-rate problem.
- Transferred the rule to new data.
- Explained the update rule accurately.

Evidence observed: unassisted prediction, debugging, transfer, and teach-back. The program outputs verified the calculations; no files or learner state were changed. Mastery beyond this lesson remains untested.

Provisional next retrieval: in 2 days, predict one gradient-descent step on unseen data before calculating it.
