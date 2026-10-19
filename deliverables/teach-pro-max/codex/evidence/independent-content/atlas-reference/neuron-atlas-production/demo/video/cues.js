window.NeuronFilmCues = [
  {
    "id": "contributions",
    "start": 0,
    "end": 19.266666666666666,
    "title": "Signed contributions",
    "text": "A neuron starts with contributions, not votes. The first input, zero point eight, is multiplied by one point five. Its contribution grows to positive one point two. The second input is zero point four. A negative weight reverses it, giving negative zero point four.",
    "preset": "baseline"
  },
  {
    "id": "sum",
    "start": 19.266666666666666,
    "end": 36.0,
    "title": "Add the signed lengths",
    "text": "Now place those contributions head to tail on one shared scale. Start at zero. Move right by one point two, then left by zero point four. The bias subtracts another zero point two. The endpoint is zero point six. That signed sum is z.",
    "preset": "baseline"
  },
  {
    "id": "gate-active",
    "start": 36.0,
    "end": 46.9,
    "title": "ReLU: positive sums pass",
    "text": "ReLU keeps positive sums and clips negative sums to zero. Here, zero point six passes through unchanged.",
    "preset": "baseline"
  },
  {
    "id": "gate-inactive",
    "start": 46.9,
    "end": 56.833333333333336,
    "title": "ReLU: negative sums stop",
    "text": "Change only the bias to negative one. The sum becomes negative zero point two, but the output is zero. In this example, the derivative at zero and below is defined as zero.",
    "preset": "inactive"
  },
  {
    "id": "learning-step",
    "start": 56.833333333333336,
    "end": 73.03333333333333,
    "title": "Apply the baseline gradients",
    "text": "Return to the active example. The target is one; the squared loss is zero point zero eight. Multiply each baseline gradient by one half, then subtract those amounts from all three parameters simultaneously.",
    "preset": "baseline"
  },
  {
    "id": "learning-result",
    "start": 73.03333333333333,
    "end": 82.966667,
    "title": "The updated prediction",
    "text": "The new prediction is zero point nine six. The remaining error is ten times smaller; its squared loss is one hundred times smaller: zero point zero zero zero eight.",
    "preset": "trained"
  }
];
window.NeuronFilmCaptions = [
  {
    "start": 0.0,
    "end": 2.986667,
    "text": "A neuron starts with contributions, not votes."
  },
  {
    "start": 3.4,
    "end": 8.417600199999999,
    "text": "The first input, zero point eight, is multiplied by one point five."
  },
  {
    "start": 8.417600199999999,
    "end": 11.762667,
    "text": "Its contribution grows to positive one point two."
  },
  {
    "start": 12.166666666666668,
    "end": 16.89513749019608,
    "text": "The second input is zero point four. A negative weight reverses it,"
  },
  {
    "start": 16.89513749019608,
    "end": 18.865333666666668,
    "text": "giving negative zero point four."
  },
  {
    "start": 19.266666666666666,
    "end": 23.127999666666668,
    "text": "Now place those contributions head to tail on one shared scale."
  },
  {
    "start": 23.53333333333333,
    "end": 27.561066933333333,
    "text": "Start at zero. Move right by one point two, then left by"
  },
  {
    "start": 27.561066933333333,
    "end": 28.56800033333333,
    "text": "zero point four."
  },
  {
    "start": 29.0,
    "end": 33.394666666666666,
    "text": "The bias subtracts another zero point two. The endpoint is zero point"
  },
  {
    "start": 33.394666666666666,
    "end": 35.592,
    "text": "six. That signed sum is z."
  },
  {
    "start": 36.0,
    "end": 41.58682376470588,
    "text": "ReLU keeps positive sums and clips negative sums to zero. Here, zero"
  },
  {
    "start": 41.58682376470588,
    "end": 43.914667,
    "text": "point six passes through unchanged."
  },
  {
    "start": 44.333333333333336,
    "end": 48.8200701754386,
    "text": "Change only the bias to negative one. The sum becomes negative zero"
  },
  {
    "start": 48.8200701754386,
    "end": 51.437333333333335,
    "text": "point two, but the output is zero."
  },
  {
    "start": 51.86666666666667,
    "end": 56.061128205128206,
    "text": "In this example, the derivative at zero and below is defined as"
  },
  {
    "start": 56.061128205128206,
    "end": 56.410666666666664,
    "text": "zero."
  },
  {
    "start": 56.833333333333336,
    "end": 60.95945074509804,
    "text": "Return to the active example. The target is one; the squared loss"
  },
  {
    "start": 60.95945074509804,
    "end": 62.67866633333334,
    "text": "is zero point zero eight."
  },
  {
    "start": 63.1,
    "end": 69.06799975,
    "text": "Multiply each baseline gradient by one half, then subtract those amounts from"
  },
  {
    "start": 69.06799975,
    "end": 71.057333,
    "text": "all three parameters simultaneously."
  },
  {
    "start": 71.46666666666667,
    "end": 76.0658392183908,
    "text": "The new prediction is zero point nine six. The remaining error is"
  },
  {
    "start": 76.0658392183908,
    "end": 80.66501177011494,
    "text": "ten times smaller; its squared loss is one hundred times smaller: zero"
  },
  {
    "start": 80.66501177011494,
    "end": 82.58133366666667,
    "text": "point zero zero zero eight."
  }
];
