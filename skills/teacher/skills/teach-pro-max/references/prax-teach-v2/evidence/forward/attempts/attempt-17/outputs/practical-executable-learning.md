# Practical gradient-descent lesson

## Learner turn 1

Teach me gradient descent with a real two-parameter model. I should predict what one step will do, run it, inspect the result, change something, debug a bad step, explain the rule, and transfer it to new data.

## Tutor turn 1

We’ll train a real two-parameter line:

\[
\hat y = wx+b
\]

Data: \(x=[1,2,3]\), targets \(y=[1.5,2.0,2.5]\).  
Start: \(w=0.2,\ b=0.5\), learning rate \(0.1\).

Current predictions are \([0.7,0.9,1.1]\)—all below their targets.

Before we run one gradient-descent step, predict:

- Does \(w\) increase, decrease, or stay unchanged?
- Does \(b\) increase, decrease, or stay unchanged?
- Does the mean squared error probably rise or fall?

No exact arithmetic needed. Explain your reasoning in one sentence—or say “I don’t know.”

## Learner turn 2

Because every prediction is below its target, I expect negative gradients, so subtracting them increases both w and b; the loss should fall. Please run the stable case and show the exact command and complete output so I can inspect it.

## Tutor turn 2

Your prediction was correct: both gradients were negative, so subtracting them increased \(w\) and \(b\). The loss fell from `1.270` to `0.028`.

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

Now change only the learning rate from `0.10` to `1.00`. Before we run it, predict: will the new loss be lower than `0.028`, between `0.028` and `1.270`, or greater than `1.270`? Why?

## Learner turn 3

I predict the new loss will be greater than 1.270 because the ten-times-larger rate will overshoot even though the gradient direction is useful. Please run the changed case and show the exact command and output.

## Tutor turn 3

Your prediction was confirmed: the useful gradient direction was overwhelmed by an excessive step size, and loss jumped from `1.270` to `127.990`.

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

Debug the bad step: name the cause, propose the smallest fix, and cite one observed number supporting your diagnosis.

## Learner turn 4

The cause is an excessive learning rate: the direction was useful, but a 1.00 step increased loss from 1.270 to 127.990. The smallest fix is to reduce only the learning rate back toward 0.10 and rerun before changing the model or data.

## Tutor turn 4

Correct diagnosis and minimal fix. The unchanged gradients (`dw=-4.800`, `db=-2.200`) show the direction did not change; increasing only the learning rate made the parameter jump and raised loss to `127.990`.

Teach it back: why must we evaluate gradient direction and learning-rate magnitude separately when deciding whether a gradient-descent step will reduce loss? Explain it as if to someone new to the update rule.

## Learner turn 5

The gradient tells us which direction is locally downhill, while the learning rate scales how far we move in that direction. Subtracting a negative gradient correctly increases the parameters here, but a step can be so large that it crosses the low-loss region and lands uphill. So we must inspect both the gradient sign and the observed before/after loss, then tune step size without blaming the useful direction.

## Tutor turn 5

Your explanation correctly separates local direction from travel distance and uses observed loss as the check.

Transfer task: A delivery-time model uses \(\hat y=wx+b\) with \(x=[1,2]\), targets \(y=[5,7]\), initial \(w=1,\ b=1\), and learning rate \(0.1\).

Before execution, calculate the current predictions, errors \(e=\hat y-y\), gradients

\[
dw=\frac{2}{n}\sum ex,\qquad db=\frac{2}{n}\sum e,
\]

then predict the new \(w\), new \(b\), and whether loss will rise or fall.

## Learner turn 6

The current predictions are [2, 3], so the errors are [-3, -4]. With n=2, dw=(-3*1)+(-4*2)=-11 and db=-3+-4=-7. Therefore w becomes 2.1 and b becomes 1.7. I predict loss falls because the step moves both predictions toward their targets. Please run the delivery-transfer case and show the exact command and complete stdout so I can verify it.

## Tutor turn 6

Your transfer calculation was confirmed exactly.

Command:

```bash
python3 /Users/prax/Developer/skills-and-personas/skills/teach-pro-max/references/prax-teach-v2/evidence/forward/execution/practical_gradient_descent.py delivery-transfer
```

Complete stdout:

```text
case=delivery-transfer learning_rate=0.10
before w=1.000 b=1.000 predictions=[2.00, 3.00] loss=12.500
gradients dw=-11.000 db=-7.000
after w=2.100 b=1.700 predictions=[3.80, 5.90] loss=1.325
```

Evidence observed: you correctly predicted a stable step, diagnosed an overshoot, explained direction versus magnitude, and independently calculated an unseen transfer case using the supplied formulas. This supports immediate application, debugging, explanation, and transfer—not durable mastery; no delayed retrieval was observed. No files or learner state were changed.
