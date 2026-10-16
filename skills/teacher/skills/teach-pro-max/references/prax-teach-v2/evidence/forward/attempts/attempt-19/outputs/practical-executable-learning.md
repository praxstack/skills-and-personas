# Practical gradient-descent lesson

## Learner turn 1

Teach me gradient descent with a real two-parameter model. I should predict what one step will do, run it, inspect the result, change something, debug a bad step, explain the rule, and transfer it to new data.

## Tutor turn 1

We’ll use a two-parameter linear model, \(\hat y = wx+b\), with mean-squared error.

For the first run, use \(x=[1,2,3]\), targets \([1.5,2.0,2.5]\), starting \(w=0.2,\ b=0.5\), and learning rate \(0.1\).

Before we run it, predict:

- Will \(w\) increase or decrease?
- Will \(b\) increase or decrease?
- Will the loss rise or fall?

Give your best reasoning—or say “I don’t know.”

## Learner turn 2

All three predictions are below their targets, so the gradients should be negative. Subtracting them should increase both w and b, and the loss should fall. Roughly I expect w near 0.68 and b near 0.72. Please run the stable case and show the exact command and complete output so I can inspect it.

## Tutor turn 2

Your prediction was exactly right: both parameters increased, and the loss fell from 1.270 to 0.028.

Command executed:

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

Inspect it: what does the sign of each gradient tell you about the direction of the update, and how does the loss confirm whether that step helped?

## Learner turn 3

Both gradients are negative, so subtracting learning_rate times each gradient increases w and b. The loss dropping from 1.270 to 0.028 confirms that this step moved the predictions much closer to the targets; the third prediction remains farthest away at 2.76 versus 2.5.

## Tutor turn 3

Correct. You connected the gradient signs to the update rule, and used the loss as the diagnostic.

Now change only the learning rate from `0.1` to `1.0`—the intentionally aggressive case. Before we run it, predict: will the new loss be lower or higher than `1.270`, and will the step still improve the model or overshoot? Explain briefly.

## Learner turn 4

I predict the loss will be much higher than 1.270 because the gradient direction remains useful but a ten-times-larger step will overshoot the low-loss region. Please run rent-overshoot and show the exact command and complete output.

## Tutor turn 4

Your prediction was correct: the ten-times-larger step overshot badly.

Command executed:

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

Debug this bad step: what single change would you make to recover stable learning, and what evidence in the output supports that diagnosis?

## Learner turn 5

I would reduce only the learning rate first, not reverse the gradient or change the data. The gradients are identical to the stable run, and the failure appears only when the step size grows tenfold, so the output supports overshooting as the cause. The rule is new parameter = old parameter - learning_rate * gradient; an excessive rate can cross the low-loss region and land uphill.

## Tutor turn 5

Exactly. The gradients did not change; the learning rate did. Your rule is correct:

\[
\text{new parameter}=\text{old parameter}-\text{learning rate}\times\text{gradient}
\]

Now transfer the idea to new data:

- \(x=[1,2]\)
- targets \(=[5,7]\)
- starting \(w=1,\ b=1\)
- learning rate \(=0.1\)

Before running it, predict the signs of \(dw\) and \(db\), the directions of \(w\) and \(b\), and whether the loss will decrease. Explain your reasoning.

## Learner turn 6

The current predictions are [2, 3], so errors are [-3, -4]. With n=2, dw=(-3*1)+(-4*2)=-11 and db=-3+-4=-7. Both gradients are negative, so w and b increase to 2.1 and 1.7, and I predict the loss decreases because the new predictions move toward [5, 7]. Please run delivery-transfer and show the exact command and complete output.

## Tutor turn 6

Your transfer prediction was correct.

Command executed:

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

You completed the practical loop:

- Predicted gradient signs, update directions, and loss changes.
- Inspected real runs.
- Diagnosed overshooting as a learning-rate problem.
- Explained the rule: `new = old − learning_rate × gradient`.
- Transferred it to new data successfully.

Observed evidence: unassisted prediction, debugging explanation, and successful transfer. No files or learner state were changed.

Provisional retention horizon: 1 week. Next retrieval: predict gradient signs and whether loss changes before calculating exact values on a fresh two-parameter dataset.
