# Worked example: from "what's a neuron?" to backprop, over four sessions

This shows the loop, the medium choices, a confusion repair and a learner-closed thread. The animation it uses is real: `skills/concept-animation/assets/examples/neuron.anim.js` (built and exported in the test run). The other figures are described, not built.

## Session 1: first intuition (L0)

**Learner**: "I keep hearing about neural networks. What does a neuron actually do?"

- Style: `visual-explain` ("what does it do" is a teach-me request, not a drill).
- Outcome: "You'll be able to say what one neuron computes and why the output stays between 0 and 1."
- Medium: the idea is a change the learner should watch (inputs weighted, summed, squashed), so a concept animation. `find_tool.py --job change --job math` ranks concept-animation and explorable on top; the animation is cheaper and the learner hasn't asked to drive anything yet.
- Built: `neuron.anim.js`, 28 seconds, 7 keys, captions. Exported to MP4 and GIF for the learner to rewatch, with a contact sheet checked by eye.
- Check (fresh case): "If both weights were negative and the inputs positive, where would the dot sit on the curve?" Learner: "Left side, near 0." Right, with a reason.
- Where to next? Learner picks "go deeper".
- Journal (learner said yes to keeping one):

```sh
series.py init --learner Sam --goal "understand how a small neural network learns"
series.py thread add neuron --title "What one neuron computes" --level L0
series.py log neuron --did "concept animation: weigh, add, squash" --note "fresh-case check right"
series.py recall add neuron "a neuron multiplies inputs by weights, adds a bias, squashes the sum"
series.py level neuron L1
```

## Session 2: mechanism (L1), and a repair

`series.py resume` lists the recall point. Asked unaided: Sam gets it right. Recorded with `--right --unaided`, so it's demonstrated (a later session than the teaching).

- Medium: now Sam should drive it. An explorable with sliders for w1, w2 and b, the same model as the animation, and a second panel showing the decision line in input space.
- Sam misses twice on "which way does the line move when b goes up?". The page teaches it directly, and the report says: `2 misses, tried other explanations: thermostat analogy`.
- Repair: the analogy didn't land, so change the representation instead. A still with three copies of the line at b = -1, 0, 1, each labelled with the sum at the origin. Sam: "Oh, the bias is the sum when the inputs are zero." That's the gap closed.

```sh
series.py log neuron --did "explorable: weights and bias move the decision line" --missed "bias direction" --tried "thermostat analogy" --tried "three-line still"
```

## Session 3: formal model (L2) and a second thread

- Sam asks how the weights get chosen. New thread, `learning`, at L1.
- Medium: an explorable of gradient descent on one weight: the loss curve, a ball on it, a learning-rate slider. Turning the rate too high makes the ball bounce out: Sam finds it before being told.
- Formal line, mapped to the picture: `w ← w − η · dL/dw`, where each symbol has a mark on the figure.
- The pending `neuron` recall is due and answered right.

## Session 4: Sam closes a thread

- Recall on `learning` is right but helped, so it isn't demonstrated yet. It stays due.
- Sam: "I'm good on the single neuron. Let's do backprop next time."
- `series.py satisfied neuron --note "said: good on the single neuron"`. Only now, because Sam said it.
- Recap for `neuron`: the animation's poster frame, the claim (weigh, add, squash), the why (the squash keeps outputs comparable and gives a smooth slope to learn from) and the formula.
- Next session starts `backprop` at L1, with a concept map (explain-diagram) showing where it sits between `neuron` and `learning`.

## What to notice

- The medium changed with the job: watch (animation), then drive (explorable), then compare (still).
- The repair changed one thing, the representation, after the analogy failed. It didn't repeat the analogy louder.
- Quiz answers fed the next step. They never ended the lesson.
- The thread closed when the learner closed it, not when the scores looked good.
