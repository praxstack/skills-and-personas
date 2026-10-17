# Practical gradient-descent lesson

## Tutor turn 1

We’ll do this as a short live lesson: predict → run → inspect → modify → debug → explain → transfer. No files or learner state will be saved. Say **Answer now** anytime to switch to a direct walkthrough.

We’ll predict monthly rent from bedroom count:

- Data: \(x=[1,2,3]\) bedrooms
- Actual rent: \(y=[1.5,2.0,2.5]\) thousand dollars
- Model: \(\hat y=wx+b\)
- Starting parameters: \(w=0.20,\ b=0.50\)
- Loss: mean squared error
- Learning rate: \(0.10\)
- Update: parameter \(\leftarrow\) parameter \(-\) learning rate \(\times\) its gradient

This is delivered through host chat with no custom artifact controls or scripts. The complete model and data are above; host-UI keyboard, focus, reduced-motion, and assistive-technology behavior remains unverified.

**Action 1 — Predict**

Before we run anything, will one gradient-descent step make \(w\) and \(b\) each **increase**, **decrease**, or **stay unchanged**?

Reply `w: ___, b: ___`—or `I don’t know`.

## Learner turn 1

w: increase, b: increase. The predictions start below all three targets, so I expect both gradients to push the line upward.

## Tutor turn 2

Your prediction was correct. Both gradients were negative, and gradient descent subtracts them, so both parameters increased.

```text
before: w=0.200, b=0.500
predictions=[0.70, 0.90, 1.10]
loss=1.270

gradients: dw=-4.800, db=-2.200

after: w=0.680, b=0.720
predictions=[1.40, 2.08, 2.76]
loss=0.028
```

The actual updates were:

\[
w=0.20-0.10(-4.80)=0.68
\]

\[
b=0.50-0.10(-2.20)=0.72
\]

\(w\) moved more because its gradient weights each prediction error by its input \(x\); \(b\)’s gradient does not.

**Action 2 — Inspect**

Which reported number most directly shows whether the model improved overall, and what were its before-and-after values?

## Learner turn 2

The MSE loss shows overall fit. It fell from 1.270 before the step to 0.028 after it.

## Tutor turn 3

Exactly. MSE is the objective being minimized, and \(1.270 \rightarrow 0.028\) is strong evidence that this step improved the overall fit.

**Action 3 — Modify and predict**

Keep the same starting \(w=0.20\) and \(b=0.50\), but change the learning rate from \(0.10\) to \(1.00\).

Before we run it, predict the result:

- A: loss falls even further
- B: loss falls, but less effectively
- C: loss rises above \(1.270\)

Reply with `A`, `B`, or `C`—or `I don’t know`.

## Learner turn 3

C. A learning rate ten times larger may overshoot the lower-loss region, so I predict loss rises above 1.270.

## Tutor turn 4

Your overshoot prediction was confirmed by the run:

```text
learning rate=1.00

before: w=0.200, b=0.500, loss=1.270
gradients: dw=-4.800, db=-2.200

after: w=5.000, b=2.700
predictions=[7.70, 12.70, 17.70]
loss=127.990
```

The loss exploded from \(1.270\) to \(127.990\).

**Action 4 — Debug**

Compare this with the successful run. In one line, name the root cause and the smallest change you would try next.

## Learner turn 4

The learning rate is too large and overshoots; I would restore it to 0.10 and rerun from the same starting parameters.

## Tutor turn 5

Correct. You isolated the changed variable—the learning rate—and proposed the smallest repair. The existing \(0.10\) control run already validates it from the same starting parameters:

```text
learning rate 0.10 → loss 1.270 → 0.028
learning rate 1.00 → loss 1.270 → 127.990
```

**Action 5 — Explain**

In your own words, explain the gradient-descent update rule and the separate jobs of the gradient and learning rate. Two sentences are enough.

## Learner turn 5

The gradient gives the local direction and relative strength of change for each parameter, so subtracting it moves toward lower loss. The learning rate scales that move: too small is slow, while too large can jump past the useful region and increase loss.

## Tutor turn 6

That rule is correct and complete: the gradient supplies local parameter-specific information, while the learning rate controls how far we trust it.

**Action 6 — Transfer**

A delivery service models travel time from distance:

\[
\hat y=wx+b
\]

```text
distance x (km):       [1, 2]
actual time y (min):   [5, 7]
starting w=1, b=1
learning rate=0.10
```

Use:

\[
e_i=\hat y_i-y_i
\]

\[
\frac{\partial L}{\partial w}=\frac{2}{n}\sum e_ix_i,
\qquad
\frac{\partial L}{\partial b}=\frac{2}{n}\sum e_i
\]

Calculate the new \(w\) and \(b\) after one gradient-descent step. Reply `w: ___, b: ___`—or `I don’t know`.

## Learner turn 6

Predictions are 2 and 3, so errors are −3 and −4. dw = −11 and db = −7, giving w: 2.1, b: 1.7.

## Tutor turn 7

Correct. The transfer run verified your calculation:

```text
before: predictions=[2.0, 3.0], loss=12.500
gradients: dw=-11.0, db=-7.0
after:  w=2.1, b=1.7
predictions=[3.8, 5.9], loss=1.325
```

You successfully:

- Predicted a two-parameter update.
- Inspected the loss change.
- Modified the learning rate and predicted overshooting.
- Diagnosed the bad step and chose the smallest repair.
- Explained the rule in your own words.
- Applied it correctly to unseen data without corrective hints; the gradient formulas were provided.

Your rule: the gradient gives the local direction and parameter-specific strength; the learning rate scales the step, and an excessive rate can overshoot.

What remains uncertain is durable recall and whether you can reconstruct the gradients without the formulas. For a one-week retention goal, solve one fresh example from memory in about 48 hours, then again on day 7. No files or learner state were saved.
