# Practical gradient-descent lesson

## User

Teach me gradient descent with a real two-parameter model. I should predict what one step will do, run it, inspect the result, change something, debug a bad step, explain the rule, and transfer it to new data.

## Assistant

We’ll fit \(\hat y=wx+b\) to rent data: \(x=[1,2,3]\), \(y=[1.5,2.0,2.5]\), starting at \(w=0.2\), \(b=0.5\), with learning rate \(0.1\).

The predictions are below every target. Before running anything, predict: will one gradient-descent step increase or decrease \(w\) and \(b\), and should the loss rise or fall?

## User

Both \(w\) and \(b\) should increase, pushing the predictions up, so the loss should fall.

## Assistant

Run this exact command:

```bash
python3 /Users/prax/Developer/skills-and-personas/skills/teach-pro-max/references/prax-teach-v2/evidence/forward/execution/practical_gradient_descent.py rent-stable
```

Exact stdout:

```text
case=rent-stable learning_rate=0.10
before w=0.200 b=0.500 predictions=[0.70, 0.90, 1.10] loss=1.270
gradients dw=-4.800 db=-2.200
after w=0.680 b=0.720 predictions=[1.40, 2.08, 2.76] loss=0.028
```

Inspect it: which numbers confirm your prediction, and what makes this a stable step?

## User

\(w\) and \(b\) increased, the predictions moved near the targets, and loss dropped from 1.270 to 0.028. That looks stable because the update improved the fit without jumping far past it.

## Assistant

Exactly. Now modify one thing—not the data, starting parameters, or gradient calculation—to deliberately make this same step overshoot. What would you change?

## User

Increase the learning rate from 0.1 to 1.0.

## Assistant

Run the modified case exactly:

```bash
python3 /Users/prax/Developer/skills-and-personas/skills/teach-pro-max/references/prax-teach-v2/evidence/forward/execution/practical_gradient_descent.py rent-overshoot
```

Exact stdout:

```text
case=rent-overshoot learning_rate=1.00
before w=0.200 b=0.500 predictions=[0.70, 0.90, 1.10] loss=1.270
gradients dw=-4.800 db=-2.200
after w=5.000 b=2.700 predictions=[7.70, 12.70, 17.70] loss=127.990
```

Debug the bad step: is the gradient direction wrong, or is the step size wrong? Use the matching “before” state and gradients as evidence.

## User

The direction is not the bug because both runs have the same starting state and gradients. The learning rate made the update ten times larger, so it shot past the low-loss region and raised loss to 127.990.

## Assistant

Correct: you isolated the learning rate because it was the only changed input. Now explain the reusable rule in your own words: what does the gradient tell us, why do we subtract it, and what role does the learning rate play?

## User

The gradient gives the direction of increasing loss for each parameter. Subtracting it moves \(w\) and \(b\) toward lower loss. The learning rate scales that move: too small is slow, while too large can overshoot and increase loss.

## Assistant

Good. Now transfer that rule to delivery data, not rent data.

Suppose distance is \(x=[1,2]\), delivery time is \(y=[5,7]\), and the model starts at \(w=1\), \(b=1\) with learning rate \(0.1\). Its predictions are below both targets. Predict the signs of \(dw\) and \(db\), the directions \(w\) and \(b\) will move, and whether the loss should fall.

## User

Both gradients should be negative because the predictions are too low. Subtracting them should increase both \(w\) and \(b\), raise the predicted times, and lower the loss.

## Assistant

Run the delivery-data transfer exactly:

```bash
python3 /Users/prax/Developer/skills-and-personas/skills/teach-pro-max/references/prax-teach-v2/evidence/forward/execution/practical_gradient_descent.py delivery-transfer
```

Exact stdout:

```text
case=delivery-transfer learning_rate=0.10
before w=1.000 b=1.000 predictions=[2.00, 3.00] loss=12.500
gradients dw=-11.000 db=-7.000
after w=2.100 b=1.700 predictions=[3.80, 5.90] loss=1.325
```

Your transfer prediction held: both gradients were negative, both parameters increased, and loss fell from 12.500 to 1.325. You demonstrated prediction, inspection, controlled modification, debugging, explanation, and one unassisted transfer; later retrieval remains untested.
