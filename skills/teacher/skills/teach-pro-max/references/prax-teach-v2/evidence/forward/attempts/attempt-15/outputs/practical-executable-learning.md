# Practical gradient-descent lesson

## Learner turn 1

Teach me gradient descent with a real two-parameter model. I should predict what one step will do, run it, inspect the result, change something, debug a bad step, explain the rule, and transfer it to new data.

## Tutor turn 1

Let’s start with a prediction before any explanation.

We’ll fit `ŷ = wx + b` to:

- `x = [1, 2, 3]`
- targets `y = [1.5, 2.0, 2.5]`
- current `w = 0.2`, `b = 0.5`
- learning rate `0.10`

I’ll run:

```bash
python3 '/Users/prax/Developer/skills-and-personas/skills/teach-pro-max/references/prax-teach-v2/evidence/forward/execution/practical_gradient_descent.py' rent-stable
```

Predict the next state: will `w`, `b`, and the loss move up or down? Give rough next values for `(w, b)` if you can—or say “I don’t know.”

## Learner turn 2

Starting predictions are 0.7, 0.9, and 1.1, all below the targets. I expect negative gradients, so subtracting them increases w and b; I predict w = 0.68, b = 0.72, and lower loss.

## Tutor turn 2

Your prediction matched the run: both parameters increased, and the loss decreased. The observed output was:

```text
case=rent-stable learning_rate=0.10
before w=0.200 b=0.500 predictions=[0.70, 0.90, 1.10] loss=1.270
gradients dw=-4.800 db=-2.200
after w=0.680 b=0.720 predictions=[1.40, 2.08, 2.76] loss=0.028
```

You correctly connected negative gradients with increasing parameters. Notice that one step improved the predictions without making them perfect.

Now change one thing: keep the data and starting parameters fixed, but use learning rate `1.00` via the fixed `rent-overshoot` case. Before I run it, predict whether the loss will be lower or higher than `1.270`, and why.

## Learner turn 3

I predict the loss will be much higher than 1.270 because the ten-times-larger rate overshoots: the gradient direction is useful, but the update magnitude is too large.

## Tutor turn 3

Your prediction was right. The observed output was:

```text
case=rent-overshoot learning_rate=1.00
before w=0.200 b=0.500 predictions=[0.70, 0.90, 1.10] loss=1.270
gradients dw=-4.800 db=-2.200
after w=5.000 b=2.700 predictions=[7.70, 12.70, 17.70] loss=127.990
```

The gradients are unchanged from the first run; the learning rate alone changed. The update went far past the target region.

Debug this step: what would you change to repair it, and what relationship in the update rule tells you that change should work?

## Learner turn 4

I would change only the learning rate from 1.0 back to 0.1. The update is parameter minus learning-rate times gradient, so the same gradient direction produces a ten-times-smaller step; from the same start I predict w = 0.68, b = 0.72, and loss about 0.028.

## Tutor turn 4

Your diagnosis is correct: changing only `learning_rate` scales both parameter updates while preserving their direction, so `0.1` repairs the overshoot.

Teach the rule back in one or two sentences: how do the gradient’s sign and the learning rate’s size jointly determine a parameter update, and what signal tells you the step was too large?

## Learner turn 5

Gradient descent subtracts learning-rate times gradient, so the gradient sign sets the update direction and the learning rate scales its magnitude. If the direction is unchanged but a larger rate makes loss explode, the step overshot and the magnitude—not the gradient direction—is the problem.

## Tutor turn 5

That explanation is accurate: direction comes from the gradient sign, magnitude from the learning rate, and an exploding loss signals overshoot.

Now transfer the rule to new data:

- `x = [1, 2]`
- targets `y = [5, 7]`
- initial `w = 1.0`, `b = 1.0`
- learning rate `0.10`

Before I run:

```bash
python3 '/Users/prax/Developer/skills-and-personas/skills/teach-pro-max/references/prax-teach-v2/evidence/forward/execution/practical_gradient_descent.py' delivery-transfer
```

predict the directions of `w` and `b`, whether the loss decreases, and rough next values if you can.

## Learner turn 6

Starting predictions are 2 and 3, so residuals are -3 and -4. I predict dw = -11 and db = -7, so w rises to 2.1, b rises to 1.7, and loss falls to about 1.325.

## Tutor turn 6

Your transfer prediction matched the observed run exactly:

```text
case=delivery-transfer learning_rate=0.10
before w=1.000 b=1.000 predictions=[2.00, 3.00] loss=12.500
gradients dw=-11.000 db=-7.000
after w=2.100 b=1.700 predictions=[3.80, 5.90] loss=1.325
```

You successfully predicted, inspected, modified, debugged, explained, and transferred the rule without hints. Your teach-back was accurate: gradient sign determines direction; learning rate determines magnitude; exploding loss indicates overshoot.

Remaining uncertainty: delayed recall is untested. Retrieval target: in one week, predict a gradient step on fresh data before seeing the result. No files or learner state were changed.
