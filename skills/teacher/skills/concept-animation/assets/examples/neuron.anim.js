// One artificial neuron: weigh, add, squash. Every frame comes from the model,
// so the numbers on screen are always the real ones.
const sigmoid = (s) => 1 / (1 + Math.exp(-s));
const signed = (v) => `${v < 0 ? "−" : "+"} ${Math.abs(v).toFixed(2)}`;

window.ANIMATION = {
  id: "neuron-v1",
  title: "What one neuron does",
  kicker: "Neural networks · first intuition",
  subtitle: "Weigh the inputs, add them up, squash the sum into 0 to 1.",
  // Wide for video and desktop; on phones the curve stacks under the network.
  viewBox: (narrow) => (narrow ? "0 0 540 980" : "0 0 960 540"),
  narrowText: 1.5,
  params: { x1: 1, x2: 0.5, w1: 0, w2: 0, b: 0 },
  model: ({ x1, x2, w1, w2, b }) => {
    const s = w1 * x1 + w2 * x2 + b;
    return { s, y: sigmoid(s), parts: [w1 * x1, w2 * x2] };
  },
  label: (m, p) => `A neuron with inputs ${p.x1} and ${p.x2}, weights ${p.w1.toFixed(2)} and ${p.w2.toFixed(2)}, bias ${p.b.toFixed(2)}: the sum is ${m.s.toFixed(2)} and the output is ${m.y.toFixed(2)}.`,
  keys: [
    { at: 0, say: "A neuron starts with numbers coming in. Here there are two inputs." },
    { at: 3, set: { w1: 0.8, w2: 1.2 }, say: "Each input is multiplied by a weight. A thicker line means a bigger weight." },
    { at: 7.5, set: { b: -0.2 }, say: "The neuron adds the weighted inputs and a bias: s = w₁x₁ + w₂x₂ + b." },
    { at: 11.5, say: "Then it squashes s through an S-shaped curve, so the output always lands between 0 and 1." },
    { at: 16, set: { b: 2 }, say: "Raise the bias and the sum moves right along the curve. The output climbs toward 1." },
    { at: 20, set: { w2: -2.5 }, say: "Make a weight negative and that input now pulls the output down." },
    { at: 24, say: "That's one neuron: weigh, add, squash. A network is thousands of these, each feeding the next." },
  ],
  duration: 28,
  draw(g, m, p, kit) {
    const { el, mark, hand, ink, seed, since, narrow } = kit;
    const L = narrow
      ? { in: [[80, 120], [80, 360]], sum: [350, 220], wl: [[215, 150], [225, 330]], curve: { x0: 60, x1: 430, y0: 610, y1: 870 }, sumText: [330, 440], arrow: [[330, 505], [330, 580]] }
      : { in: [[120, 170], [120, 380]], sum: [410, 275], wl: [[180, 124], [180, 444]], curve: { x0: 560, x1: 910, y0: 90, y1: 430 }, sumText: [410, 363], arrow: [[468, 275], [542, 275]] };
    const inputs = [
      { x: L.in[0][0], y: L.in[0][1], v: p.x1, w: p.w1, name: "x₁", wname: "w₁" },
      { x: L.in[1][0], y: L.in[1][1], v: p.x2, w: p.w2, name: "x₂", wname: "w₂" },
    ];
    const sum = { x: L.sum[0], y: L.sum[1], r: 50 };
    // Inputs, circled by the coach as they're introduced.
    for (const [i, n] of inputs.entries()) {
      el("circle", { cx: n.x, cy: n.y, r: 40, class: "f-paper s-ink" });
      el("text", { x: n.x, y: n.y + 7, class: "t-book", "text-anchor": "middle", "font-size": 22, text: n.v.toFixed(1) });
      el("text", { x: n.x - 40, y: n.y - 56, class: "t-print", "font-size": 16, text: `INPUT ${n.name}` });
      mark([ink.loop(n.x, n.y, 50, 50, { seed: seed(`in${i}`) })], { tone: "red", progress: kit.key === 0 ? Math.min(1, kit.t / 2.6 * 2 - i) : 1 });
      // The weighted connection: thickness is |w|, blue pushes up, red pulls down.
      const show = since(1);
      if (show > 0) {
        const edge = el("line", { x1: n.x + 40, y1: n.y, x2: n.x + 40 + (sum.x - sum.r - n.x - 40) * show, y2: n.y + (sum.y - n.y) * show, class: n.w >= 0 ? "s-blue" : "s-red" });
        edge.style.strokeWidth = String(1.5 + 6 * Math.min(1.5, Math.abs(n.w)));
        if (show === 1) hand(L.wl[i][0], L.wl[i][1], `${n.wname} = ${n.w.toFixed(1)}`, { tone: n.w >= 0 ? "blue" : "red", size: 22 });
      }
    }
    // The sum.
    el("circle", { cx: sum.x, cy: sum.y, r: sum.r, class: "f-paper s-ink" });
    el("text", { x: sum.x, y: sum.y + 12, class: "t-book", "text-anchor": "middle", "font-size": 36, text: "Σ" });
    const showSum = since(2);
    if (showSum > 0) {
      const [tx, ty] = L.sumText;
      el("text", { x: tx, y: ty, class: "t-print", "text-anchor": "middle", "font-size": 18, text: `s = ${m.parts[0].toFixed(2)} ${signed(m.parts[1])} ${signed(p.b)}` });
      el("text", { x: tx, y: ty + 26 * kit.textScale, class: "t-print", "text-anchor": "middle", "font-size": 18, text: `= ${m.s.toFixed(2)}` });
      mark([ink.loop(tx, ty + 19 * kit.textScale, 58 * kit.textScale, 14 * kit.textScale, { seed: seed("s") })], { tone: "red", progress: kit.key === 2 ? showSum : 1 });
    }
    // The squash: the sigmoid from s = -6 to 6.
    const box = L.curve;
    const X = (s) => box.x0 + ((s + 6) / 12) * (box.x1 - box.x0);
    const Y = (y) => box.y1 - y * (box.y1 - box.y0);
    const showCurve = since(3);
    if (showCurve > 0) {
      mark(ink.arrow(L.arrow, { seed: seed("to-curve"), head: 12 }), { tone: "graphite", progress: kit.key === 3 ? Math.min(1, showCurve * 2) : 1 });
      el("line", { x1: box.x0, y1: box.y1, x2: box.x1, y2: box.y1, class: "s-ink" });
      el("line", { x1: X(0), y1: box.y0 - 10, x2: X(0), y2: box.y1, class: "s-rule" });
      for (const yv of [0, 0.5, 1]) el("text", { x: box.x1 + 10, y: Y(yv) + 5, class: "t-print", text: yv.toFixed(1) });
      el("text", { x: box.x1 + 10, y: box.y0 - 18, class: "t-print", text: "OUT" });
      for (const sv of [-6, 0, 6]) el("text", { x: X(sv), y: box.y1 + 24 * kit.textScale, class: "t-print", "text-anchor": "middle", text: String(sv) });
      el("text", { x: (box.x0 + box.x1) / 2, y: box.y1 + 50 * kit.textScale, class: "t-print", "text-anchor": "middle", text: "SUM s" });
      const pts = [];
      for (let s = -6; s <= 6.001; s += 0.25) pts.push([X(s), Y(sigmoid(s))]);
      mark([ink.smoothPath(pts)], { tone: "blue", progress: kit.key === 3 ? showCurve : 1 });
      if (kit.key > 3 || showCurve === 1) {
        const sx = X(Math.max(-6, Math.min(6, m.s)));
        const sy = Y(m.y);
        el("line", { x1: sx, y1: box.y1, x2: sx, y2: sy, class: "s-graphite", "stroke-dasharray": "5 5" });
        el("line", { x1: box.x0, y1: sy, x2: sx, y2: sy, class: "s-graphite", "stroke-dasharray": "5 5" });
        el("circle", { cx: sx, cy: sy, r: 8, class: "f-red" });
        const right = sx + 14 + 150 * kit.textScale < box.x1 + 40;
        hand(right ? sx + 14 : sx - 14, sy - 16, `output ${m.y.toFixed(2)}`, { tone: "red", size: 24, anchor: right ? "start" : "end" });
      }
    }
  },
};
