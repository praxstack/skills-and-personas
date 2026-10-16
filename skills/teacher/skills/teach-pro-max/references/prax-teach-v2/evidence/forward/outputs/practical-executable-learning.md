# Practical gradient-descent lesson

## User

Teach me gradient descent with a real two-parameter model. I should predict what one step will do, run it, inspect the result, change something, debug a bad step, explain the rule, and transfer it to new data.

## Assistant

We’ll train the two-parameter model \(\hat y = wx+b\).

Start with \(w=1\), \(b=1\), one data point \(x=2,\ y=7\), loss \(L=\tfrac12(\hat y-y)^2\), and learning rate \(0.1\). The current prediction is \(3\).

Before running it: will one gradient-descent step make \(w\) and \(b\) increase, decrease, or move in opposite directions? Briefly explain your prediction—or say “I don’t know.”

## User

Both should increase because the prediction is below the target. For replayable evidence, use the checked-in fixture at `/Users/prax/Developer/skills-and-personas/skills/teach-pro-max/references/prax-teach-v2/evidence/forward/execution/practical_gradient_descent.py`; run its `rent-stable` case with the exact absolute command and show complete stdout.

## Assistant

Correct: for this case, both gradients are negative, so subtracting them increases both parameters.

```text
$ /Users/prax/.local/share/mise/installs/python/3.13/bin/python3 /Users/prax/Developer/skills-and-personas/skills/teach-pro-max/references/prax-teach-v2/evidence/forward/execution/practical_gradient_descent.py rent-stable
case=rent-stable learning_rate=0.10
before w=0.200 b=0.500 predictions=[0.70, 0.90, 1.10] loss=1.270
gradients dw=-4.800 db=-2.200
after w=0.680 b=0.720 predictions=[1.40, 2.08, 2.76] loss=0.028
```

Which number is the clearest evidence that this was a good step, and how much did it change?

## User

The clearest evidence is loss: it fell from 1.270 to 0.028, a decrease of 1.242. The predictions also moved close to the targets. I want to change only the learning rate to 1.0 next to see whether the same gradient direction overshoots.

## Assistant

Exactly: the loss decreased by \(1.242\). Changing only the learning rate isolates step size while keeping the starting point and gradient unchanged.

```text
$ /Users/prax/.local/share/mise/installs/python/3.13/bin/python3 /Users/prax/Developer/skills-and-personas/skills/teach-pro-max/references/prax-teach-v2/evidence/forward/execution/practical_gradient_descent.py rent-overshoot
case=rent-overshoot learning_rate=1.00
before w=0.200 b=0.500 predictions=[0.70, 0.90, 1.10] loss=1.270
gradients dw=-4.800 db=-2.200
after w=5.000 b=2.700 predictions=[7.70, 12.70, 17.70] loss=127.990
```

Debug this bad step: was the problem the gradient direction or the step size? Justify your answer from the two runs.

## User

The step size was wrong, not the gradient direction: both runs began at the same parameters and had the same negative gradients, but the ten-times-larger learning rate sent the loss from 1.270 to 127.990. The reusable rule is `new parameter = old parameter - learning_rate * gradient`: the gradient points uphill, subtraction moves downhill, and the learning rate controls how far; too large can cross the low-loss region.

## Assistant

That diagnosis and rule are correct: the controlled comparison isolates the learning rate, and your “cross the low-loss region” explanation captures overshooting.

Transfer to a delivery-time model \(\hat y=wx+b\): all distances \(x\) are positive, and every current prediction is above its observed delivery time. Before running anything, predict the signs of \(dw\) and \(db\), then say whether \(w\) and \(b\) should increase or decrease. Explain using your update rule.

## User

For your stated above-target scenario, both gradients should be positive and subtracting them should decrease both parameters. The checked-in `delivery-transfer` fixture is the opposite case—its initial predictions are below the targets—so for that runnable transfer I predict negative `dw` and `db`, increases in both `w` and `b`, and lower loss. Please run that exact case with the absolute command and complete stdout.

## Assistant

Correct distinction: above-target errors would produce positive gradients here, while this below-target transfer case predicts negative gradients and parameter increases.

```text
$ /Users/prax/.local/share/mise/installs/python/3.13/bin/python3 /Users/prax/Developer/skills-and-personas/skills/teach-pro-max/references/prax-teach-v2/evidence/forward/execution/practical_gradient_descent.py delivery-transfer
case=delivery-transfer learning_rate=0.10
before w=1.000 b=1.000 predictions=[2.00, 3.00] loss=12.500
gradients dw=-11.000 db=-7.000
after w=2.100 b=1.700 predictions=[3.80, 5.90] loss=1.325
```

Did the run confirm every part of your prediction? Cite the gradient signs, parameter changes, and loss change.

## User

Yes. `dw=-11` and `db=-7` are both negative; subtracting them increased `w` from 1.0 to 2.1 and `b` from 1.0 to 1.7. Loss fell from 12.500 to 1.325, so the step improved the new model. This also confirms the direction reverses when errors reverse.

## Assistant

Yes—your interpretation matches every observed value.

You independently predicted, ran, inspected, modified, debugged, explained, and transferred one gradient-descent step. Your reusable rule was correct: subtract the gradient, while the learning rate controls distance and can cause overshooting.

Remaining uncertainty: durable recall and calculating gradients directly from raw data rather than reading them from the program.

Retention horizon: 1 week. In 3 days, retrieve the rule without notes and compute one two-parameter update from fresh data before running it.
