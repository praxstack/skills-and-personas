// scenes.js: THIS film's data and scenes. A new film replaces this file (and timing.js); the kit stays.
// Demo: examples/mini/script.json (LC 787 in one minute, 14 lines). Every tween is placed at a line's time:
//   L.p1.voiceAt      the voice starts the line        L.p1.at('each flight')  when that phrase is spoken
//   L.p1.vEnd         the voice ends the line          L.p1.end / L.p1.start   the line's slot
// World space (moves with the camera): the graph G and the input decoder. Screen space: everything else.
window.Film = {
  build(K) {
    const { L, C } = K;

    // ------------------------------------------------------------------ data: example 1
    const G = K.graph({
      nodes: [{ id: '0', x: 780, y: 500 }, { id: '1', x: 1130, y: 280 }, { id: '2', x: 1130, y: 720 }, { id: '3', x: 1480, y: 500 }],
      edges: [{ from: '0', to: '1', w: 100 }, { from: '1', to: '2', w: 100 }, { from: '2', to: '0', w: 100 },
        { from: '1', to: '3', w: 600 }, { from: '2', to: '3', w: 200 }],
    });
    const FLIGHTS = ['01', '12', '20', '13', '23'];
    const dec = K.decoder({
      x: 130, y: 225, title: 'Input · example 1',
      lines: ['n = 4', 'flights = [', '  [0, 1, 100],', '  [1, 2, 100],', '  [2, 0, 100],', '  [1, 3, 600],', '  [2, 3, 200] ]', 'src = 0, dst = 3', 'k = 1'],
    });
    const CODE = `
int findCheapestPrice(
    int n, vector<vector<int>>& flights,
    int src, int dst, int k) {
  const int INF = 1e9;
  vector<int> dist(n, INF);
  dist[src] = 0;
  for (int round = 0; round <= k; ++round) {
    vector<int> next = dist;
    for (auto& f : flights) {
      int u = f[0], v = f[1], w = f[2];
      if (dist[u] != INF && dist[u] + w < next[v])
        next[v] = dist[u] + w;
    }
    dist = next;
  }
  return dist[dst] == INF ? -1 : dist[dst];
}`;
    const LINE = { dist0: 6, round: 7, copy: 8, each: 9, relax: 11, write: 12, swap: 14, ret: 16 };

    // flags first: G.bbox() includes them, so every camera framing below keeps SRC and DST on screen
    G.flag('0', 'SRC', 'accent', L.p2.at('city zero'), 'bottom');
    G.flag('3', 'DST', 'mint', L.p2.at('city three'), 'bottom');

    // ------------------------------------------------------------------ film-wide: lights, chapter cards, camera
    K.autoMoods();
    // Chapter cards cover the left 900 px from K.cardIn(n) to K.cardClear(n): left-side panels leave before
    // the first and arrive after the second (see the chapter changes below).
    K.chapterCards();
    // World text (weights 36 px, SRC/DST 36 px, badges 32 px) must stay >= 26 px on screen, so no view frames
    // the graph at a scale below about 0.8: each box below leaves the graph at least 0.8 (gsap_check warns < 26 px).
    const VIEW = {
      title: { x: 0, y: 0, s: 1 },
      inputs: { x: 120, y: 175, w: 1600, h: 640 },              // world rects the camera frames
      graph: G.bbox(),
      left: [G.bbox(), { box: { x: 96, y: 190, w: 880, h: 690 } }],
      right: [G.bbox(), { box: { x: 940, y: 190, w: 884, h: 690 } }],
      upperRight: [G.bbox(null, 70), { box: { x: 980, y: 172, w: 844, h: 494 }, pad: 10 }],
      corner: [G.bbox(null, 70), { box: { x: 1110, y: 190, w: 714, h: 690 }, pad: 10 }],
      code: [G.bbox(null, 70), { box: { x: 1120, y: 160, w: 704, h: 500 }, pad: 10 }],
      outro: [G.bbox(), { box: { x: 96, y: 170, w: 1060, h: 720 } }],
    };
    const cam = (t, v, o = {}) => (Array.isArray(v) ? K.cam.to(t, v[0], { ...v[1], ...o }) : K.cam.to(t, v, o));
    K.cam.start(K.cam.frame(VIEW.inputs, null, { maxS: 1 }));

    // ------------------------------------------------------------------ 0 · title (i1)
    {
      // the title is gone before chapter 1's card starts to come in
      K.titleCard({ kicker: 'LeetCode 787 · graphs', title: 'Cheapest Flights\nWithin K Stops', sub: 'The problem · brute force · intuition · every approach · C++ dry run' }, 0.05, K.cardIn(1) - 0.5);
      // the mascot: a paper plane crosses the frame on a glowing flight path
      // the arc passes under the subtitle (screen y > 700 where the text is) and above the caption band
      const [p0, c1, c2, p1] = [[-140, 900], [760, 960], [1380, 800], [2080, 380]].map((q) => K.cam.toWorld(q, 0));
      const path = K.svg('path', { d: `M${p0} C${c1} ${c2} ${p1}`, class: 'trail-core', stroke: K.vis('accent'), 'stroke-width': 3, opacity: 0.7 }, K.layer.back);
      const plane = G.makeToken('accent', 1.4);
      K.init(path, { drawSVG: '0%' });
      K.set(plane.g, { autoAlpha: 1 }, 0.1);
      K.to(plane.g, { motionPath: { path, autoRotate: true }, duration: 2.6, ease: 'power1.inOut' }, 0.1);
      K.to(path, { drawSVG: '100%', duration: 2.6, ease: 'power1.inOut' }, 0.1);
      K.set(plane.g, { autoAlpha: 0 }, 2.75);
      K.to(path, { autoAlpha: 0, duration: 0.6 }, L.p1.start - 0.6);
    }

    // ------------------------------------------------------------------ 1 · the problem
    // p1: four cities pop in as the card leaves (so the subject is on screen when the voice starts, a second into
    // the chapter); "n = 4" lights on the word, then each [from, to, price] entry flies from the input into its edge
    G.showNodes(['0', '1', '2', '3'], K.cardClear(1) - 0.1, 0.14);   // node 0 is on the card's side
    dec.show(Math.min(L.p1.voiceAt, K.cardClear(1) + 0.2));
    dec.mark(0, L.p1.at('four') + 0.3, { until: L.p1.at('each flight') - 0.2 });
    FLIGHTS.forEach((id, i) => {
      const t = L.p1.at('each flight') + i * 0.32;
      dec.mark(2 + i, t, { until: t + 0.9 });
      const land = dec.chip(2 + i, t, G.edge(id).mid, { text: `[${id[0]}, ${id[1]}, ${G.edge(id).w}]`, dur: 0.75 });
      G.drawEdge(id, land - 0.35, 0.6);
    });
    // above node 1, not beside the edge: 520 px wide, it would cross the decoder panel and touch node 1 there
    G.badgeAt([G.edge('01').mid[0] + 20, G.node('1').p[1] - 100], 'from 0 · to 1 · price 100', L.p1.at('from, to') + 0.2, { color: 'amber', until: L.p2.voiceAt + 0.8 });

    // p2: src and dst
    dec.mark(7, L.p2.voiceAt, { until: L.p2.end - 0.2 });
    G.lightNode('0', L.p2.at('city zero'), 'accent');
    G.lightNode('3', L.p2.at('city three'), 'mint');

    // p3: k = 1, what a stop is
    dec.mark(8, L.p3.voiceAt, { until: L.p3.end });
    const kMeter = K.meter({ right: 96, y: 96, label: 'max stops  k', value: 1, color: 'amber' });
    kMeter.show(L.p3.voiceAt + 0.1);
    const stopA = G.badge('1', 'a stop?', L.p3.at('one stop'), { color: 'amber', until: L.p4.voiceAt + 0.2 });
    const stopB = G.badge('2', 'a stop?', L.p3.at('one stop') + 0.15, { color: 'amber', dy: 100, until: L.p4.voiceAt + 0.2 });

    // p4: push in, fly 0 → 1 → 3, the cost ticks to 700, burst
    dec.hide(L.p3.end - 0.5);
    cam(L.p3.end - 0.6, VIEW.graph, { dur: 1.6, maxS: 1.22 });
    const cost = K.meter({ right: 96, y: 176, label: 'cost', value: 0, color: 'accent' });
    cost.show(L.p4.voiceAt);
    const fly = G.route(L.p4.voiceAt + 0.1, ['0', '1', '3'], { leg: 1.05, color: 'accent' });
    cost.to(fly.arrive[0], 100, 0.4);
    cost.to(fly.arrive[1], 700, 0.6);
    G.lightNode('1', fly.arrive[0], 'amber');
    G.badge('1', 'stop 1', fly.arrive[0], { color: 'amber', until: L.p4.end });
    G.lightNode('3', fly.arrive[1], 'accent');
    K.callout('700!', L.p4.at('the answer'), { at: G.pos('3'), dx: 220, dy: -150, color: 'amber', rot: 8, size: 96 });

    // ------------------------------------------------------------------ 2 · brute force (b1)
    G.clearTrails(L.b1.start - 0.7);
    [kMeter, cost].forEach((m) => m.hide(L.b1.start - 0.7));
    ['1', '3'].forEach((id) => G.unlightNode(id, L.b1.start - 0.7));
    G.hideToken(L.b1.start - 0.7);
    cam(L.b1.start - 0.75, VIEW.left[0], { ...VIEW.left[1], dur: 1.5 });
    // the graph stands where chapter 2's card lands, and the camera reframes it behind the card: it fades out before
    // the card arrives and back in once the card has gone, so the card never cuts across drawn content
    const graphBehindCard = (n) => { G.fade(K.cardIn(n) - 0.35, 0, 0.3); G.fade(K.cardClear(n), 1, 0.45); };
    graphBehindCard(2);
    const tree = K.fanTree({ x: 1010, y: 230, w: 800, h: 500, branching: 3, depth: 4, rootLabel: '0', r: (d) => [28, 15, 10, 7, 5][d], heat: ['amber', 'accent', 'rose'] });
    const grown = tree.grow(L.b1.voiceAt + 0.1, 0.42);
    const routes = K.meter({ x: 1010, y: 790, label: 'routes', value: 1, color: 'rose' });
    routes.show(L.b1.voiceAt);
    [3, 9, 27, 81].forEach((n, i) => routes.to(grown[i + 1] - 0.3, n, 0.3));
    const bigO = K.note('O(n^(k+1)) time', L.b1.at('exponential') - 0.1, { x: 1460, y: 790, color: 'rose', size: 40 });
    const expo = K.stamp('Exponential', L.b1.at('exponential') + 0.5, { x: 1410, y: 545, color: 'rose', rot: -8 });

    // ------------------------------------------------------------------ 3 · intuition
    // q1: question card left, the graph right; the viewer counts on it during the think pause
    const outB = L.q1.start - 0.75;
    tree.hide(outB);
    routes.hide(outB);
    K.fadeOut(expo, outB);
    K.fadeOut(bigO, outB);
    cam(outB, VIEW.right[0], { ...VIEW.right[1], dur: 1.5 });
    graphBehindCard(3);   // the graph is in the left half (VIEW.left) when chapter 3's card arrives
    K.question(L.q1, { n: 1, x: 96, w: 800 });
    G.route(L.q1.at('count') - 0.2, ['0', '1', '3'], { leg: 0.7, color: 'violet', trail: true });
    const qStop = G.badge('1', 'stop', L.q1.at('stops'), { color: 'amber' });

    // a1: the answer drawn: count flights, not stops
    const f1 = G.badgeAt(G.beside('01'), 'flight 1', L.a1.voiceAt + 0.05, { color: 'mint' });
    const f2 = G.badgeAt(G.beside('13'), 'flight 2', L.a1.voiceAt + 0.35, { color: 'mint' });
    G.trail('01', L.a1.voiceAt, 'mint', 0.4);
    G.trail('13', L.a1.voiceAt + 0.3, 'mint', 0.4);
    K.note('k stops → at most k + 1 flights', L.a1.at('at most'), { x: 96, y: 330, size: 44, color: 'mint', until: L.a1.end - 0.1 });
    K.callout('k + 1', L.a1.at('k plus one'), { x: 640, y: 560, color: 'mint', size: 92, rot: -6, hold: 0.7 });

    // q2: the table appears under the graph: the old row and the new row
    const outA = L.q2.start;
    [qStop, f1, f2].forEach((b) => K.fadeOut(b, outA));
    G.clearTrails(outA);
    G.hideToken(outA);
    cam(outA, VIEW.upperRight[0], { ...VIEW.upperRight[1], dur: 1.2 });
    const tb = K.table({ x: 1030, y: 676, cols: ['0', '1', '2', '3'], colHead: 'city', cw: 120, ch: 72,
      rows: [{ id: 'old', label: 'old', values: ['0', '∞', '∞', '∞'] }, { id: 'new', label: 'new', values: ['0', '∞', '∞', '∞'], hidden: true }] });
    tb.show(L.q2.voiceAt + 0.2);
    tb.showRow('new', L.q2.at('new one'));
    K.question(L.q2, { n: 2, x: 96, w: 820 });

    // a2: one round: every flight reads the OLD row, so only 0 → 1 lands; 1 → 2 must wait a round
    tb.ring('old', 0, L.a2.voiceAt, { color: 'accent', dur: 1.0 });
    G.fire('01', L.a2.voiceAt, 'accent', 0.7);
    tb.set('new', 1, '100', L.a2.voiceAt + 0.6, { color: 'accent' });
    G.fire('12', L.a2.at('exactly') - 0.1, 'rose', 0.6);
    tb.ring('old', 1, L.a2.at('exactly'), { color: 'rose', dur: 0.9 });
    // left-side notes and the burst are gone before chapter 4's card sweeps in over the left half
    K.note('read old → write new', L.a2.voiceAt + 0.1, { x: 96, y: 380, size: 48, color: 'accent', until: K.cardIn(4) - 0.4 });
    K.note('one round = one more flight', L.a2.at('one round'), { x: 96, y: 480, size: 48, color: 'mint', until: K.cardIn(4) - 0.4 });
    K.callout('+1 FLIGHT', L.a2.at('exactly one flight'), { x: 430, y: 720, color: 'mint', size: 70, rot: 6, hold: 0.6 });   // the empty left half, under the notes

    // ------------------------------------------------------------------ 4 · every approach
    const outQ = L.x1.start - 0.75;
    tb.hide(outQ);
    cam(outQ, VIEW.corner[0], { ...VIEW.corner[1], dur: 1.5 });
    // 990 px wide so the graph beside it keeps scale 0.8; it arrives once chapter 4's card has gone
    const ladder = K.ladder({ x: 96, y: 215, w: 990, title: 'Every approach', rungs: [
      { name: 'Brute-force DFS', time: 'O(n^(k+1))', space: 'O(k)', cost: 0.95 },
      { name: 'DFS + memo', time: 'O(k·E)', space: 'O(n·k)', cost: 0.42 },
      { name: 'Bellman-Ford, k + 1 rounds', time: 'O(k·E)', space: 'O(n)', cost: 0.36 },
    ] });
    const in4 = K.cardClear(4);
    ladder.show(in4);
    ladder.rung(0, in4 + 0.1);
    ladder.rung(1, Math.max(L.x1.voiceAt + 0.5, in4 + 0.35));
    ladder.focus(1, Math.max(L.x1.voiceAt + 0.6, in4 + 0.45));
    // x2: Bellman-Ford: every flight relaxes once per round, k + 1 rounds
    ladder.rung(2, L.x2.voiceAt);
    ladder.focus(2, L.x2.voiceAt + 0.2);
    [0, 1].forEach((r) => FLIGHTS.forEach((id, i) => G.fire(id, L.x2.at('k plus one') + r * 1.1 + i * 0.13, r ? 'mint' : 'amber', 0.6)));
    ladder.pick(2, L.x2.at('order k times'));   // early enough to hold well over a second before the ladder leaves

    // ------------------------------------------------------------------ 5 · C++ and the dry run (c1)
    const outL = L.c1.start - 0.75;
    ladder.hide(K.cardIn(5) - 0.4, 0.35);   // gone before chapter 5's card covers the left half
    cam(outL, VIEW.code[0], { ...VIEW.code[1], dur: 1.5 });
    const code = K.codePanel({ x: 96, y: 188, w: 1000, code: CODE, size: 30, maxLines: 14 });
    code.show(K.cardClear(5));
    code.revealAll(K.cardClear(5) + 0.15, 0.03);
    const dt = K.table({ x: 1150, y: 680, cols: ['0', '1', '2', '3'], colHead: 'city', cw: 116, ch: 72, labelW: 120,
      rows: [{ id: 'dist', label: 'dist', values: ['0', '∞', '∞', '∞'] }, { id: 'next', label: 'next', values: ['0', '∞', '∞', '∞'], hidden: true }] });
    dt.show(L.c1.voiceAt - 0.1);
    code.focus(L.c1.voiceAt, LINE.dist0);
    // round 0: copy, then only 0 → 1 relaxes
    const r0 = L.c1.at('round zero');
    code.focus(r0, LINE.round);
    code.focus(r0 + 0.3, LINE.copy);
    dt.showRow('next', r0 + 0.3);
    code.focus(L.c1.at('reaches city one') - 0.15, LINE.relax, LINE.write);
    G.fire('01', L.c1.at('reaches city one'), 'accent', 0.6);
    dt.ring('dist', 0, L.c1.at('reaches city one'), { dur: 0.8 });
    dt.set('next', 1, '100', L.c1.at('one hundred'), { color: 'accent' });
    code.focus(L.c1.at('round one') - 0.55, LINE.swap);
    dt.set('dist', 1, '100', L.c1.at('round one') - 0.45, { color: 'ink', flash: 'faint' });
    // round 1: 1 → 2 and 1 → 3 relax; 2 → 3 is skipped because the old dist[2] is still ∞
    const r1 = L.c1.at('round one');
    code.focus(r1, LINE.round);
    code.focus(r1 + 0.35, LINE.relax, LINE.write);
    G.fire('12', r1 + 0.35, 'accent', 0.6);
    dt.set('next', 2, '200', r1 + 0.85, { color: 'accent' });
    G.fire('13', L.c1.at('city three') - 0.1, 'accent', 0.6);
    dt.set('next', 3, '700', L.c1.at('city three') + 0.4, { color: 'accent' });
    G.fire('23', L.c1.at('seven hundred') - 0.35, 'rose', 0.5);
    dt.ring('dist', 2, L.c1.at('seven hundred') - 0.3, { color: 'rose', dur: 0.8 });
    code.focus(L.c1.vEnd - 0.5, LINE.swap);
    dt.copyRow('next', 'dist', L.c1.vEnd - 0.45, 0.06);
    // the burst lands as the voice says the answer, in the free corner above the graph, and is gone before the outro
    K.callout('700!', L.c1.at('seven hundred') + 0.1, { x: 1700, y: 172, color: 'amber', size: 50, rot: 6, hold: 0.6 });

    // ------------------------------------------------------------------ outro (o1)
    code.hide(L.o1.start);
    dt.hide(L.o1.start);
    cam(L.o1.start, VIEW.outro[0], { ...VIEW.outro[1], dur: 1.6 });
    G.clearTrails(L.o1.start);
    G.unlightNode('0', L.o1.start);
    const win = G.route(L.o1.voiceAt + 0.3, ['0', '1', '3'], { leg: 0.8, color: 'mint' });
    G.lightNode('3', win.end, 'mint');
    K.resultCard({ x: 1210, y: 215, w: 610, kicker: 'Bellman-Ford', big: '700', color: 'mint',
      lines: ['k stops → k + 1 rounds', 'copy before you update', 'O(k·E) time · O(n) space'] }, L.o1.voiceAt + 0.1);   // lands while the line is read
  },
};
