// scenes.js: THE FILM. This is the file you replace for a new video; the kit (kit/*.js) stays.
// It implements examples/mini/script.json (14 lines, ~71 s): LC 787 Cheapest Flights Within K Stops.
//
// How to read it: buildFilm() declares everything once. Every time is taken from the voice timing by line id
// (vAt('p4', 0.5) = halfway through line p4's words, sayAt('p4', 'answer') = when the word is spoken), so a
// re-voiced script re-times the picture by itself. Coordinates are world units on a 1920x1080 board; the
// camera moves over it. Keep text inside x 96..1824, y 96..900 (the caption band owns the bottom 180 px).
'use strict';

const FLIGHTS = [[0, 1, 100], [1, 2, 100], [2, 0, 100], [1, 3, 600], [2, 3, 200]];
// 2-space indent and a 3-line signature keep the card 52 columns wide, so code stays at 32 px beside the dry run
const CODE = `int findCheapestPrice(int n,
    vector<vector<int>>& flights,
    int src, int dst, int k) {
  const int INF = 1e9;
  vector<int> dist(n, INF);
  dist[src] = 0;
  for (int round = 0; round <= k; ++round) {
    vector<int> next = dist;  // read old, write new
    for (auto& f : flights) {
      int u = f[0], v = f[1], w = f[2];
      if (dist[u] != INF && dist[u] + w < next[v])
        next[v] = dist[u] + w;
    }
    dist = next;
  }
  return dist[dst] == INF ? -1 : dist[dst];
}`;

function buildFilm() {
  const ch = (n) => chapterStart(n); // chapter n starts (its corner label pops in 0.5 s earlier and is written by then)

  // ---------------------------------------------------------------- the persistent subject: Example 1's map
  const g = graph({
    nodes: [{ x: -400, y: 10 }, { x: -20, y: -235 }, { x: 20, y: 240 }, { x: 400, y: -10 }],
    edges: FLIGHTS, r: 46, z: 30,
  });
  // where the map sits on the board, chapter by chapter (t, x, y, scale)
  g.place([
    [0, 1200, 505, 1],
    [ch(2) - 0.6, 1200, 505, 1], [ch(2) + 0.3, 1450, 470, 0.72],          // brute force: map steps aside for the tree
    [ch(3) - 0.5, 1450, 470, 0.72], [ch(3) + 0.4, 960, 655, 0.8],         // intuition: centred under the question card
    [lStart('q2') - 0.1, 960, 655, 0.8], [lStart('q2') + 0.7, 590, 640, 0.76], // q2: room for the old/new rows
    [ch(4) - 0.5, 590, 640, 0.76], [ch(4) + 0.4, 1420, 565, 0.74],         // approaches: ladder on the left
    [ch(5) - 0.5, 1420, 565, 0.74], [ch(5) + 0.3, 1540, 335, 0.62],        // code: small, top right
    [lStart('o1') + 0.1, 1540, 335, 0.62], [lStart('o1') + 1.0, 960, 610, 0.9], // recap: back to the centre
  ]);
  const gw = (x, y) => (t) => { const f = g.xf(t); return [f.x + x * f.s, f.y + y * f.s]; }; // a point in map space
  const plane = token(g);

  // ---------------------------------------------------------------- camera (world point at the centre, zoom)
  camera([
    [0, 960, 540, 1.0], [2.6, 960, 525, 1.05], [ch(1) - 0.6, 960, 540, 1.0],
    [vAt('p4') - 0.5, 960, 540, 1.0], [vAt('p4') + 0.6, 985, 515, 1.06],                      // push in for the route
    [lEnd('p4') - 0.5, 985, 515, 1.06], [ch(2) - 0.4, 960, 540, 1.0],
    [vEnd('b1'), 930, 520, 1.04], [ch(3) - 0.5, 960, 540, 1.0],
    [vAt('a1'), 960, 540, 1.0], [vAt('a1') + 0.7, 1010, 610, 1.06], [lEnd('a1') - 0.3, 1010, 610, 1.06], [lStart('q2') + 0.3, 960, 540, 1.0],
    [vAt('a2'), 960, 540, 1.0], [vAt('a2') + 0.6, 1000, 560, 1.05], [ch(4) - 0.5, 960, 540, 1.0],
    [vAt('x2', 0.3), 960, 540, 1.0], [vAt('x2', 0.6), 960, 520, 1.05], [ch(5) - 0.5, 960, 548, 1.0],
    [lStart('o1'), 960, 530, 1.0], [lStart('o1') + 0.8, 960, 540, 1.0],   // code chapter: a slow tilt only (the code card is wide)
    [vEnd('o1'), 960, 560, 1.06],
  ]);

  // ---------------------------------------------------------------- automatic furniture
  scenery();
  captionBand();
  chapterLabels({ skip: [0] });

  // ================================================================ 0 · intro
  titleCard({ lines: ['Cheapest Flights', 'Within K Stops'], kicker: 'LeetCode 787', at: 0, until: lEnd('i1') - 0.3, stamp: 'MEDIUM', stampAt: vAt('i1', 0.45) });
  // Pip loops across the title in the paper plane, leaving a dashed trail
  const loop = curvePts([[-120, 860], [420, 760], [760, 880], [980, 760], [880, 640], [760, 720], [1180, 820], [1560, 700], [2080, 560]], 10);
  world(45, (ctx, t) => {
    const a = 0.25, b = lEnd('i1') + 0.2; if (t < a || t > b + 0.2) return;
    const u = Ease.inOut(clamp((t - a) / (b - a))), [x, y, ang] = polyAt(loop, u);
    inkLine(ctx, loop, { from: Math.max(0, u - 0.45), prog: u, color: S.accent, w: 4, dash: [12, 12], alpha: 0.75, seed: 'loop', t });
    drawPlane(ctx, x, y, ang, 1.2, { t, pip: S.mascot, expr: 'cheer' });
  });

  // ================================================================ 1 · the problem
  // the raw input, written by hand; every flight flies from the note to its arrow on the map
  const nt = note({ w: 560, h: 690, rule: 56, first: 108, keys: slideKeys(96, 196, ch(1) - 0.3, lStart('b1') - 0.75, [-900, 40], [-950, 60]) });
  g.showNodes(ch(1) + 0.2, 0.14); // as the chapter change lifts, so the cities are on the board before the voice starts
  nt.line(0, 'n = 4', vAt('p1', 0.0), { dur: 0.5 });
  nt.line(1, 'flights:', sayAt('p1', 'Each flight') - 0.1, { dur: 0.4 });
  nt.line(1, '[from, to, price]', sayAt('p1', 'Each flight') + 0.3, { x: 230, color: S.accent, size: 40, dur: 0.5 }); // written as "Each flight is" is said
  const fly0 = sayAt('p1', 'price') + 0.15;
  FLIGHTS.forEach(([u, v, w], e) => {
    const te = fly0 + e * 0.48, text = `[${u}, ${v}, ${w}]`;
    nt.line(2 + e, text, te - 0.35, { x: 130, dur: 0.35 });
    nt.hl(2 + e, { at: te, until: te + 0.7 });
    chip(String(w), (t) => nt.spanXY(2 + e, text.lastIndexOf(' ') + 1, text.length - 1, t), (t) => g.tagXY(e, t), { at: te + 0.05, dur: 0.6 });
    g.showEdge(e, te + 0.1, 0.55, te + 0.62);
  });
  nt.line(7, 'src = 0', sayAt('p2', 'city zero') - 0.15, { dur: 0.45 });
  nt.line(7, 'dst = 3', sayAt('p2', 'city three') - 0.15, { x: 300, dur: 0.45 });
  g.mark(0, 'src', { at: sayAt('p2', 'city zero'), color: S.cool });
  g.mark(3, 'dst', { at: sayAt('p2', 'city three'), color: S.accent });
  g.glow(3, { at: sayAt('p2', 'city three'), until: lEnd('p4') });
  plane.park(0, { at: vAt('p2', 0.1), until: vAt('p4'), side: 'up' });
  nt.line(8, 'k = 1', vAt('p3', 0.0), { dur: 0.4 });
  nt.line(8, '(max stops)', sayAt('p3', 'at most'), { x: 190, size: 40, color: S.inkSoft, dur: 0.5 });
  [1, 2].forEach((i) => { g.ring(i, { at: sayAt('p3', 'one stop') + i * 0.12, until: lEnd('p3'), color: S.gold, dash: true }); });
  g.mark(1, 'a stop?', { at: sayAt('p3', 'one stop') - 0.3, until: lEnd('p3'), side: 'up', color: S.inkSoft, size: S.size.label });
  // the answer: fly 0 -> 1 -> 3 with a running total, then reject the cheaper route with 2 stops
  const land = plane.fly([0, 1, 3], { at: vAt('p4', 0.0), legDur: 0.8, pause: 0.3, trail: S.accent, until: lEnd('p4') - 0.3, hold: lEnd('p4') - 0.4, cost: true, stopLabel: 'stop' });
  const tA = sayAt('p4', 'The answer'), gone = lEnd('p4') - 0.3;
  callout('700!', gw(440, -270), { at: land + 0.05, until: tA - 0.1, size: 70 });
  // the tempting cheaper route has two stops: draw it, price it, strike it, stamp it
  g.hl(g.route([0, 1, 2, 3]), { at: land + 0.35, dur: 0.25, color: S.bad, dash: true, until: gone, glow: false, w: 6 });
  const lab = land + 0.45, struck = Math.max(tA + 0.25, lab + 1.1); // written in 0.7 s, struck once readable
  label('400 · 2 stops', gw(255, 300), { at: lab, until: gone, color: S.bad, size: 40, align: 'left', halo: S.halo, strikeAt: struck, dur: 0.7 });
  stamp('TOO MANY STOPS', gw(-235, 285), { at: struck + 0.3, until: gone, size: 36, shake: 6 });
  nt.line(9, 'answer =  700', tA + 0.2, { color: S.good, dur: 0.6 }); // two spaces: the ring round 700 clears the '='
  nt.ring(9, { at: tA + 0.7, until: lEnd('p4'), from: 10, color: S.good });

  // ================================================================ 2 · brute force: the tree of every route
  const tb = Math.min(vAt('b1'), ch(2)); // the tree grows as the map steps aside and the chapter label lands, before the voice
  const TREE = [ // [city, x, y, parent, appear offset]
    [0, 540, 250, -1, 0.0], [1, 540, 410, 0, 0.35], [2, 400, 570, 1, 0.75], [3, 680, 570, 1, 0.9], [0, 330, 730, 2, 1.15], [3, 490, 730, 2, 1.3],
  ];
  const treeOut = ch(3) - 0.6;
  world(34, (ctx, t) => {
    if (t < tb - 0.1 || t > treeOut + 0.4) return;
    const fade = 1 - P(t, treeOut, 0.4);
    ctx.save(); ctx.globalAlpha *= fade;
    TREE.forEach(([c, x, y, p, o], i) => {
      if (p < 0) return; const [, px, py] = TREE[p], pr = P(t, tb + o - 0.25, 0.3);
      inkArrow(ctx, [[px, py + 34], [(px + x) / 2 + (x - px) * 0.1, (py + y) / 2], [x, y - 36]], { prog: pr, w: 3.4, seed: 'tree' + i, t, head: 13 });
      const tg = tagSprite('+' + FLIGHTS[g.edgeIndex(TREE[p][0], c)][2]), k = pop(t, tb + o + 0.05, 0.45), sd = x > px ? 1 : x < px ? -1 : 1;
      if (k.s > 0) blit(ctx, tg, (px + x) / 2 + sd * (tg.w / 2 + 2), (py + y) / 2 - 16, { sx: k.sx, sy: k.sy, t, jit: 'tt' + i }); // beside the branch, clear of its arrowhead
    });
    // the explosion: more and more branches below
    const fan = P(t, tb + 1.45, 0.9, Ease.out);
    for (let k = 0; k < 18; k++) { const x0 = 330 + (k % 2) * 160, x1 = 210 + k * 26, pr = clamp(fan * 1.6 - k * 0.04); if (pr > 0) inkLine(ctx, [[x0, 762], [x1, 850]], { prog: pr, w: 2, alpha: 0.45, seed: 'fan' + k, t, passes: 1 }); }
    TREE.forEach(([c, x, y, , o], i) => { const k = pop(t, tb + o, 0.5); if (k.s > 0) blit(ctx, discSprite(String(c), S.node[c], S.nodeInk[c], 32), x, y, { sx: k.sx, sy: k.sy, t, jit: 'tn' + i }); });
    ['1 flight', '2 flights', '3 flights'].forEach((s, j) => drawText(ctx, s, 110, 424 + j * 160, { size: S.size.label, color: S.inkSoft, write: P(t, tb + 0.4 + j * 0.4, 0.4, Ease.lin), align: 'left' }));
    ctx.restore();
  });
  // as each branch grows, the same flight fires on the map
  TREE.forEach(([c, , , p, o]) => { if (p >= 0) g.fire(g.edgeIndex(TREE[p][0], c), { at: tb + o - 0.2, color: S.gold }); });
  const tH = sayAt('b1', 'every route') - 0.15;
  label('O(n^{k+1})', [800, 300], { at: tH, until: treeOut, font: 'brush', size: 84, color: S.bad, align: 'left', dur: 0.55, boil: 1 });
  label('every route, every time', [805, 372], { at: tH + 0.2, until: treeOut, size: S.size.label, color: S.inkSoft, align: 'left', dur: 0.55 });

  // ================================================================ 3 · intuition
  questionCard('q1', 'a1', { n: 1 });
  g.hl(g.route([0, 1, 3]), { at: vAt('q1', 0.3), dur: 0.45, color: S.accent, until: lEnd('a1') - 0.2 });
  g.ring(1, { at: vAt('q1', 0.7), until: lEnd('q1'), color: S.gold, dash: true });
  g.mark(1, 'stop', { at: vAt('q1', 0.75), until: lEnd('q1'), side: 'up', color: S.gold, size: S.size.label });
  // a1 "Flights. At most k plus one of them.": both flights are labelled on "Flights", the rule lands on "k plus one"
  // on the inner side of each leg (the weight tags own the outer side)
  label('flight 1', gw(-188, -78), { at: vAt('a1', 0.0), until: lEnd('a1') - 0.2, color: S.accent, size: 42, rot: -0.57, halo: S.halo, dur: 0.45 });
  label('flight 2', gw(166, -82), { at: vAt('a1', 0.15), until: lEnd('a1') - 0.2, color: S.accent, size: 42, rot: 0.5, halo: S.halo, dur: 0.45 });
  label('k stops → k + 1 flights', gw(470, 40), { at: vAt('a1', 0.3), until: lEnd('a1') - 0.2, font: 'brush', size: 54, color: S.ink, align: 'left', dur: 0.5 });

  questionCard('q2', 'a2', { n: 2 });
  const rows = table({ cols: ['city 0', 'city 1', 'city 2', 'city 3'], rows: ['old', 'new'], cw: 140, rh: 84, labelW: 140, labelSize: 44, at: vAt('q2', 0.2),
    keys: slideKeys(1060, 470, vAt('q2', 0.0) - 0.4, ch(4) - 0.75, [900, 0], [950, 0]) });
  rows.row(0, ['0', '∞', '∞', '∞'], sayAt('q2', 'old row') - 0.35, 0.1); // the old row is there as "old row" is said
  [0, 1, 2, 3].forEach((c) => rows.cell(1, c, '?', vEnd('q2') + c * 0.1, { color: S.inkSoft, dur: 0.2 }));
  const ta2 = vAt('a2');
  g.fire(0, { at: ta2, color: S.gold });
  rows.cell(1, 0, '0', ta2 + 0.1);
  // a2 "So one round adds exactly one flight.": the new row fills in the first half, then holds
  chip('100', (t) => g.tagXY(0, t), (t) => rows.cellXY(1, 1, t), { at: ta2 + 0.25, dur: 0.55 });
  rows.cell(1, 1, '100', ta2 + 0.8, { color: S.accent, ring: true });
  g.fire(1, { at: ta2 + 0.45, color: S.inkSoft });
  rows.cell(1, 2, '∞', ta2 + 0.75); rows.cell(1, 3, '∞', ta2 + 0.85);
  label('reads the old ∞', (t) => { const [x, y] = rows.cellXY(1, 2, t); return [x + 40, y + 112]; }, { at: ta2 + 0.8, until: ch(4) - 0.75, size: S.size.label, color: S.inkSoft, dur: 0.45 });
  stamp('+1 FLIGHT PER ROUND', [1330, 842], { at: ta2 + 1.0, until: ch(4) - 0.8, size: 38, color: S.good, rot: -0.06 });

  // ================================================================ 4 · every approach
  const lad = ladder({ w: 820, rungH: 112, gap: 30, n: 3, keys: slideKeys(130, 276, ch(4) - 0.4, ch(5) - 0.75, [-1000, 0], [-1100, 0]) });
  lad.rung(0, { name: 'Brute force DFS', cx: 'O(n^{k+1})', cost: 1.0, at: lStart('x1') + 0.05, color: S.bad });
  lad.rung(1, { name: 'DFS + memo', cx: 'O(k·E) time', cost: 0.42, at: vAt('x1', 0.05), color: S.gold });
  lad.rung(2, { name: 'Bellman-Ford, k+1 rounds', cx: 'O(k·E) · O(n)', cost: 0.42, at: vAt('x2', 0.05), color: S.good });
  lad.pick(2, sayAt('x2', 'order k') + 0.2); // after its cost is heard, so the pick holds ~2 s before the ladder leaves
  g.fire([0, 1, 2, 3, 4], { at: sayAt('x1', 'Order'), gap: 0.16, color: S.gold });
  const r1 = sayAt('x2', 'rounds') - 0.4;
  g.fire([0, 1, 2, 3, 4], { at: r1, gap: 0, color: S.gold, dur: 0.6 });
  g.fire([0, 1, 2, 3, 4], { at: r1 + 0.9, gap: 0, color: S.accent, dur: 0.6 });
  label('round 1', gw(0, -330), { at: r1, until: r1 + 0.85, font: 'brush', size: 58, color: S.gold });
  label('round 2', gw(0, -330), { at: r1 + 0.9, until: ch(5) - 0.8, font: 'brush', size: 58, color: S.accent });

  // ================================================================ 5 · C++ and the dry run
  const code = codeCard({ code: CODE, size: 32, lh: 38, padT: 76, title: 'C++', keys: slideKeys(96, 198, ch(5) - 0.45, lStart('o1'), [-1300, 0], [-1400, 0], -0.008) });
  code.reveal(1, 6, ch(5) + 0.6, 0.4).reveal(7, 17, ch(5) + 0.95, 1.1); // written once the chapter-change dim has lifted (ch + 0.6): text under it is < 4.5:1
  const dry = table({ cols: ['city 0', 'city 1', 'city 2', 'city 3'], rows: ['start', 'round 0', 'round 1'], cw: 108, rh: 74, labelW: 128, at: ch(5) + 0.2,
    keys: slideKeys(1226, 556, ch(5) - 0.3, lStart('o1') + 0.1, [800, 0], [900, 0], 0.01) });
  const c0 = vAt('c1', 0.0), rz = sayAt('c1', 'Round zero'), ro = sayAt('c1', 'Round one');
  code.focus(4, 6, { at: c0, until: rz - 0.1 });
  dry.row(0, ['0', '∞', '∞', '∞'], c0 + 0.1, 0.12);
  dry.hlRow(1, { at: rz, until: ro - 0.1 });
  code.focus(7, 12, { at: rz, until: ro - 0.1 });
  // round 0: flights in array order; only 0 -> 1 improves anything
  FLIGHTS.forEach((_, e) => g.fire(e, { at: rz + 0.1 + e * 0.22, color: e === 0 ? S.gold : S.inkFaint, dur: 0.45 }));
  chip('100', (t) => g.tagXY(0, t), (t) => dry.cellXY(1, 1, t), { at: rz + 0.3, dur: 0.6 });
  dry.row(1, ['0', null, '∞', '∞'], rz + 0.2, 0.25);
  dry.cell(1, 1, '100', rz + 0.9, { color: S.accent, ring: true });
  // round 1: 1 -> 2 gives 200, 1 -> 3 gives 700; 2 -> 3 is skipped because the old dist[2] is still ∞
  dry.hlRow(2, { at: ro, until: lStart('o1') });
  code.focus(11, 12, { at: ro, until: lStart('o1') - 0.1 });
  const r3 = sayAt('c1', 'city three') - 0.4;
  g.fire(1, { at: ro + 0.2, color: S.gold }); g.fire(3, { at: r3, color: S.gold }); g.fire(4, { at: r3 + 0.45, color: S.inkFaint });
  dry.row(2, ['0', '100'], ro + 0.15, 0.2);
  chip('200', (t) => g.tagXY(1, t), (t) => dry.cellXY(2, 2, t), { at: ro + 0.4, dur: 0.6 });
  dry.cell(2, 2, '200', ro + 1.0, { color: S.accent });
  chip('700', (t) => g.nodeXY(3, t), (t) => dry.cellXY(2, 3, t), { at: r3 + 0.2, dur: 0.6 });
  dry.cell(2, 3, '700', r3 + 0.8, { color: S.good, ring: S.good });

  // ---------------------------------------------------------------- recap: the winning route again
  const to = vAt('o1');
  label('k stops → k + 1 rounds', [960, 225], { at: to, until: TIMING_.total + 1, font: 'brush', size: 84, color: S.ink, dur: 1.0, boil: 1 });
  label('copy before you update', [960, 300], { at: sayAt('o1', 'Copy') - 0.6, until: TIMING_.total + 1, size: 50, color: S.accent, dur: 0.6 });
  const land2 = plane.fly([0, 1, 3], { at: lStart('o1') + 1.0, legDur: 0.75, pause: 0.25, trail: S.good, cost: true, hold: TIMING_.total + 1 });
  callout('700 ✓', gw(560, -300), { at: land2 + 0.05, until: TIMING_.total + 1, size: 66, colors: [S.good, S.goodSoft] });
}
