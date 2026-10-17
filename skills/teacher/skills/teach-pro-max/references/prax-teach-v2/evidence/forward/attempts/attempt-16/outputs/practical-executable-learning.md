# Practical gradient-descent lesson

## Learner turn 1

Teach me gradient descent with a real two-parameter model. I should predict what one step will do, run it, inspect the result, change something, debug a bad step, explain the rule, and transfer it to new data.

## Tutor turn 1

We’ll use a real linear model:

\[
\hat y = wx+b
\]

Data: \(x=[1,2,3]\), \(y=[1.5,2.0,2.5]\)  
Start: \(w=0.2,\ b=0.5\), learning rate \(=0.1\)  
Current predictions: \([0.7,0.9,1.1]\)

Before I run one gradient-descent step, predict: will \(w\) increase or decrease, will \(b\) increase or decrease, and will the loss rise or fall? “I don’t know” is welcome.

## Learner turn 2

All three predictions are below their targets, so I expect both gradients to be negative and subtracting them to increase w and b. I predict roughly w = 0.68, b = 0.72, and a much lower loss.

## Tutor turn 2

Exactly right.

```text
before: w=0.200, b=0.500, loss=1.270
gradient: dw=-4.800, db=-2.200
after:  w=0.680, b=0.720, loss=0.028
```

The rule is \(\theta_{\text{new}}=\theta-\eta\nabla L\): subtracting negative gradients increased both parameters. Your numerical prediction was exact.

Now change only the learning rate from \(0.1\) to \(1.0\). Where will \(w\) and \(b\) land, and do you expect the new loss to be below or above \(1.270\)?

## Learner turn 3

Using the same gradients, I get w = 5.0 and b = 2.7. I expect the loss to rise far above 1.270 because the step overshoots. Please run it and show me the exact command and output so I can inspect the changed case.

## Tutor turn 3

Your prediction was exact.

```bash
python3 /Users/prax/Developer/skills-and-personas/skills/teach-pro-max/references/prax-teach-v2/evidence/forward/execution/practical_gradient_descent.py rent-overshoot
```

```text
case=rent-overshoot learning_rate=1.00
before w=0.200 b=0.500 predictions=[0.70, 0.90, 1.10] loss=1.270
gradients dw=-4.800 db=-2.200
after w=5.000 b=2.700 predictions=[7.70, 12.70, 17.70] loss=127.990
```

The update followed the computed gradient but the loss exploded from \(1.270\) to \(127.990\).

As the debugger, would you fix the gradient formula or reduce the learning rate first—and what evidence in this run supports your choice?

## Learner turn 4

I would reduce the learning rate first. The gradients are identical to the stable case and point in the useful direction; only the ten-times-larger rate changed, and the loss explosion shows the step magnitude overshot. I would restore 0.1, expecting w = 0.68, b = 0.72, and loss about 0.028.

## Tutor turn 4

Correct. You isolated the changed variable, used the stable run as a control, and distinguished a bad direction from an excessive step size. Restoring \(0.1\) reproduces the observed stable result: \(w=0.68\), \(b=0.72\), loss \(=0.028\).

Now teach the debugging rule back in one sentence: how do the gradient, learning rate, and before/after loss tell you whether a gradient-descent step was healthy?

## Learner turn 5

A healthy step uses the gradient sign for direction and the learning rate for magnitude, then confirms the choice by checking that loss decreases; if the same gradient with a larger rate makes loss explode, the direction may be sound but the step size is too large.

## Tutor turn 5

That is a correct, causal debugging rule.

Transfer it to unseen data:

\[
x=[1,2],\quad y=[5,7],\quad w=1,\quad b=1,\quad \eta=0.1
\]

Use:

\[
e_i=\hat y_i-y_i,\quad
dw=\frac{2}{n}\sum e_ix_i,\quad
db=\frac{2}{n}\sum e_i
\]

Predict the next \(w\) and \(b\), and whether the loss will decrease. Show your calculation so we can run and check it.

## Learner turn 6

The predictions are 2 and 3, so errors are -3 and -4. With n = 2, dw = (-3*1) + (-4*2) = -11 and db = -3 + -4 = -7. Therefore w becomes 2.1 and b becomes 1.7; I expect loss to decrease. Please run the transfer case and show the exact command and output.

## Tutor turn 6

Your transfer calculation was correct.

```bash
python3 /Users/prax/Developer/skills-and-personas/skills/teach-pro-max/references/prax-teach-v2/evidence/forward/execution/practical_gradient_descent.py delivery-transfer
```

```text
case=delivery-transfer learning_rate=0.10
before w=1.000 b=1.000 predictions=[2.00, 3.00] loss=12.500
gradients dw=-11.000 db=-7.000
after w=2.100 b=1.700 predictions=[3.80, 5.90] loss=1.325
```

You successfully predicted, ran, inspected, modified, debugged, explained, and transferred one gradient-descent step. The transfer used the supplied formulas but required no corrective hints. The loss fell from \(12.500\) to \(1.325\), confirming your prediction.

Remaining uncertainty: whether you can reconstruct the formulas and diagnose another bad step after a delay.

Retention horizon: provisionally one week. In two days, retrieve the update rule from memory and solve one fresh two-parameter step without the formulas shown.
