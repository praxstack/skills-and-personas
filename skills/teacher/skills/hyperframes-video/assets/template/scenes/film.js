/* scenes/film.js: the choreography of THIS film, chapter by chapter, keyed to line ids from timing.js.
   Replace it for a new film (keep the shape: build the world, then one block per chapter / line).

   Every time below comes from a line: L.p4.voiceAt (voice starts), L.p4.voiceEnd (voice stops), L.q1.thinkEnd,
   L.p4.end (slot ends), K.cue(L.p4, 'the answer') (when a phrase is spoken). Small offsets (+0.2) are fine; a
   bare number of seconds is not: re-voicing would leave the picture behind. Chapter starts: K.chapter(n).start.
   Land text before the review still of its line (65% into the voice): an entrance still popping or fading at that
   moment reads as small, faint text (legibility.py measures it), so entrances below finish a beat early. */
KIT.film = function () {
  const K = KIT, L = K.L, F = window.FILM, S = F.shots;
  const ch = (n) => K.chapter(n).start;

  // ---------------------------------------------------------------- the world (lives for the whole film)
  K.background();
  K.chrome(F.brand);
  K.chapterCards({ skip: [0] });
  K.captions();
  K.cam.init(S.title);
  K.cam.drift(9);
  const G = K.graph(F.graph);
  const E = (u, v) => G.idx(u, v);
  [L.i1.voiceAt + 0.4, L.p2.end - 0.4, L.b1.voiceAt + 1.0, L.q1.voiceEnd + 0.5, L.x1.voiceAt + 0.6, L.c1.voiceAt + 1.6, L.o1.voiceAt + 0.9]
    .forEach((t) => G.blink(t));

  // ---------------------------------------------------------------- 0 · intro: title card
  const title = K.titleCard({
    kicker: 'LEETCODE 787 · MEDIUM',
    lines: ['Cheapest Flights', `Within <span style="color:${K.ink('accent')}">K Stops</span>`],
    at: L.i1.voiceAt - 0.4,
  });
  title.out(L.i1.voiceEnd - 0.25); // gone by the intro's last word + 0.3, when the chapter 1 card comes in
  K.cam(L.i1.voiceAt, S.inputs, ch(1) + 0.4 - L.i1.voiceAt, 'sine.inOut');

  // ---------------------------------------------------------------- 1 · the problem: decode the input
  const D = K.decoder({ rows: F.input, y: 206, fs: 30 });
  D.tok('n', 0, 'n = 4'); D.tok('src', 0, 'src = 0'); D.tok('dst', 0, 'dst = 3'); D.tok('k', 0, 'k = 1');
  const trip = ['[0,1,100]', '[1,2,100]', '[2,0,100]', '[1,3,600]', '[2,3,200]'];
  trip.forEach((s, i) => D.tok('e' + i, 1, s));
  D.show(ch(1) - 0.2);

  // p1: "Four cities. Each flight is from, to, price."
  D.hl('n', L.p1.voiceAt + 0.05);
  G.nodesIn(K.cardClear(1), 0.12); // as the chapter card leaves, so the cities are there when the voice starts
  D.unhl('n', L.p1.voiceEnd - 0.1);
  // the copies leave as "each flight" is said, 0.3 s apart; the third is in the air at the line's still
  const tFly = K.cue(L.p1, 'each flight') - 0.15;
  const fromTo = K.note('[ from, to, price ]', tFly + 0.1, { x: D.pos('e0')[0] + 4, y: D.y + D.h + 42, tone: 'accent', size: 32 });
  K.hide(fromTo, L.p2.voiceAt, 0.3);
  trip.forEach((_, i) => {
    const t = tFly + i * 0.3, e = G.edges[i], land = t + 0.6;
    D.hl('e' + i, t, 'accent', 0.2);
    D.fly('e' + i, t, 0.6, K.cam.toScreen(e.mx, e.my, land));
    G.edgeIn(i, land - 0.3, 0.5);
    D.unhl('e' + i, land + 0.1);
  });

  // p2: "Start at city zero, end at city three."
  const tStart = K.cue(L.p2, 'start');
  D.hl('src', tStart, 'accent');
  const tagStart = G.tag(0, 'START', tStart + 0.2, 'accent', 'left');
  G.light(0, tStart + 0.2, 'accent');
  G.mascotAt(0, tStart + 0.35);
  const tEnd = K.cue(L.p2, 'end at');
  D.hl('dst', tEnd - 0.2, 'good');
  const tagGoal = G.tag(3, 'GOAL', tEnd - 0.15, 'good', 'right');
  G.light(3, tEnd - 0.15, 'good');
  G.ring(3, tEnd - 0.05, 'good');
  D.unhl('src', L.p2.end - 0.2); D.unhl('dst', L.p2.end - 0.2);

  // p3: "k is one. At most one stop on the way."
  K.cam(L.p3.start - 0.1, S.ex1, 1.0);
  D.hl('k', L.p3.voiceAt, 'gold');
  const stops = K.pips({ x: 1500, y: 470, label: 'STOPS ≤ k', max: 1, caption: 'k = 1' });
  const cost = K.meter({ x: 1500, y: 660, label: 'COST', value: '0', w: 250 });
  stops.show(L.p3.voiceAt + 0.3);
  const tStop = K.cue(L.p3, 'one stop') - 0.25;
  [1, 2].forEach((n, i) => G.ring(n, tStop + i * 0.2, 'gold'));
  const maybe1 = G.tag(1, 'STOP?', tStop, 'gold', 'right');
  const maybe2 = G.tag(2, 'STOP?', tStop + 0.2, 'gold', 'right');
  K.hide([maybe1, maybe2], L.p4.voiceAt + 0.2, 0.25);

  // p4: "Zero, one, three costs seven hundred with one stop. The answer is seven hundred."
  D.hide(L.p4.voiceAt - 0.3);
  cost.show(L.p4.voiceAt - 0.2);
  K.cam(L.p4.voiceAt - 0.25, S.ex1close, 1.2);
  const hop = G.hop([0, 1, 3], L.p4.voiceAt + 0.5, 1.0, {
    trail: 'good', pause: 0.25,
    onLand: (n, t) => {
      if (n === 1) { stops.fill(0, t, 'accent'); K.hide(G.tag(1, 'STOP 1', t + 0.05, 'accent', 'top'), ch(2) - 0.9, 0.3); }
    },
  });
  cost.count(L.p4.voiceAt + 0.65, 0.9, 0, 100);
  cost.count(hop.lands[0] + 0.4, 0.95, 100, 700);
  const tAns = K.cue(L.p4, 'the answer');
  cost.to(tAns + 0.03, '700', 'good'); // just after the line's still, which shows the finished count
  const p3s = K.cam.toScreen(1360, 560, tAns);
  K.burst('700!', tAns + 0.1, { x: p3s[0] + 40, y: p3s[1] - 275, tone: 'gold', size: 0.85, hold: 1.4, rot: 8 });

  // ---------------------------------------------------------------- 2 · brute force
  const c2 = ch(2);
  stops.out(c2 - 0.9); cost.out(c2 - 0.9);
  K.hide([tagStart, tagGoal], c2 - 0.9, 0.3);
  hop.trail.clear(c2 - 0.9);
  G.lightAll(c2 - 0.9);
  K.cam(c2 - 0.5, S.brute, 1.1);
  const tree = K.fanTree({ x: 870, y: 300, w: 820, h: 400, branch: 3, depth: 2, r: 30 });
  const tGrow = K.cardClear(2); // the tree grows as the card leaves, before the voice starts
  const per = 0.2; // fast: the whole tree is up by the time the voice starts
  tree.grow(tGrow, per, 'bad');
  ['1', 'n', 'n<sup style="font-size:0.62em;vertical-align:0.7em;margin-left:2px">2</sup>'].forEach((s, i) => {
    const lab = K.el('div', 'lbl abs', K.layer.hud, { left: 1730, top: 300 + i * 200 - 21, fontSize: 34, letterSpacing: 0, color: K.tok.color.mute }, s);
    K.hidden(lab); K.show(lab, tGrow + i * per + 0.1, 0.35, { x: -10 });
    K.hide(lab, ch(3) - 0.9, 0.3);
  });
  // the subject acts too: route after route lights up
  [[0, 1, 3], [0, 1, 2, 3], [0, 1, 2, 0], [0, 1, 2, 0, 1]].forEach((r, i) => {
    const t = L.b1.voiceAt + 0.5 + i * 0.62;
    G.route(r, t, 0.5, i % 2 ? 'cool' : 'accent', { tint: false }).clear(t + 0.62, 0.25);
  });
  const tExp = K.cue(L.b1, 'exponential') - 0.45; // lands as "exponential" is said
  const big = K.note(`<span class="mono" style="font-weight:700;font-size:44px;color:${K.ink('gold')}">${K.fmtO('O(n^(k+1))')}</span>&nbsp; time`, tExp, { x: 1280, y: 800, tone: 'bad', size: 36 });
  K.hide(big, ch(3) - 0.9, 0.3);
  tree.out(ch(3) - 0.9);

  // ---------------------------------------------------------------- 3 · intuition
  K.cam(ch(3) - 0.5, S.q1, 1.1);
  const q1 = K.question({ n: 1, line: L.q1, text: 'What is simpler to count than stops?' });
  const r013 = G.route([0, 1, 3], K.cardClear(3) + 0.1, 1.0, 'accent'); // a route with one stop, drawn as the card leaves
  const stopTag = G.tag(1, '1 STOP', L.q1.voiceAt + 0.9, 'gold', 'top');
  // a1: "Flights. At most k plus one of them."
  q1.answer(L.a1.voiceAt);
  K.hide(stopTag, L.a1.voiceAt, 0.25);
  const f1 = G.edgeTag(E(0, 1), 'FLIGHT 1', L.a1.voiceAt + 0.3, 'good');
  const f2 = G.edgeTag(E(1, 3), 'FLIGHT 2', L.a1.voiceAt + 0.7, 'good');
  G.fire(E(0, 1), L.a1.voiceAt + 0.2, 'good', 0.5);
  G.fire(E(1, 3), L.a1.voiceAt + 0.6, 'good', 0.5);
  const kk = K.note(`flights ≤ <b style="color:${K.ink('gold')}">k + 1</b> = 2`, K.cue(L.a1, 'k plus one') - 0.2, { x: 1560, y: 520, tone: 'good', size: 36 });
  q1.out(L.q2.start - 0.35);
  K.hide([f1, f2, kk], L.q2.start - 0.35, 0.3);
  r013.clear(L.q2.start - 0.35);

  // q2: "Why read the old row while writing a new one?"
  K.cam(L.q2.start - 0.4, S.q2, 1.1);
  const q2 = K.question({ n: 2, line: L.q2, text: 'Why read the old row while writing a new one?' });
  const TB = K.table({ x: 1130, y: 450, cols: ['0', '1', '2', '3'], colTitle: 'city', rows: ['old', 'new'], cw: 112, rh: 80, rowGap: 58, labelFs: 36 });
  TB.show(L.q2.voiceAt + 0.4);
  TB.rowIn(0, L.q2.voiceAt + 0.5);
  TB.fill(0, ['0', '∞', '∞', '∞'], L.q2.voiceAt + 0.7, 0.1);
  TB.rowIn(1, L.q2.voiceAt + 1.0);
  // a2: "So one round adds exactly one flight."
  const a = L.a2.voiceAt;
  q2.answer(a);
  G.fire(E(0, 1), a + 0.05, 'good', 0.55);
  const ar1 = TB.arrow([0, 0], [1, 1], a + 0.25, 'good', '+100', { labelDx: 18, labelDy: 0 });
  TB.set(1, 1, '100', a + 0.6, { tone: 'good' });
  TB.set(1, 0, '0', a + 0.6, { flash: false });
  G.fire(E(1, 2), a + 0.95, 'bad', 0.55);
  const ar2 = TB.arrow([1, 1], [1, 2], a + 1.1, 'bad', null, { bend: 34 }); // an arc under the new row
  TB.strike(1, 2, a + 1.5);
  const [nx, ny] = TB.center(1, 2);
  K.burst('NOPE!', a + 1.55, { x: nx + 110, y: ny + 190, tone: 'badDeep', tone2: 'accent', size: 0.62, hold: 0.7, rot: -6 }); // clear of the arc, gone before the chapter 4 sting
  TB.set(1, 2, '∞', a + 1.9, { tone: 'mute', flash: false });
  TB.set(1, 3, '∞', a + 1.95, { tone: 'mute', flash: false });
  const one = K.note('one round = one more flight', a + 1.7, { x: 1440, y: 384, tone: 'good', size: 30 });
  q2.out(ch(4) - 0.9);
  TB.out(ch(4) - 0.9);
  ar1.out(ch(4) - 0.9); ar2.out(ch(4) - 0.9);
  K.hide(one, ch(4) - 0.9, 0.3);

  // ---------------------------------------------------------------- 4 · every approach
  K.cam(ch(4) - 0.5, S.ladder, 1.1);
  const LD = K.ladder({
    x: 790, y: 236, w: 1000,
    rungs: [
      { name: 'Brute-force DFS', time: 'O(n^(k+1))', space: 'O(k)', cost: 1.0 },
      { name: 'DFS + memo on (city, flights)', time: 'O(k·E)', space: 'O(n·k)', cost: 0.34 },
      { name: 'Dijkstra on (city, stops)', time: 'O(E·k·log(E·k))', space: 'O(n·k)', cost: 0.5 },
      { name: 'Bellman-Ford, k + 1 rounds', time: 'O(k·E)', space: 'O(n)', cost: 0.3 },
    ],
  });
  LD.show(K.cardClear(4), 0.13); // rungs 2 and 3 sit where the sting was: they slide in as it leaves, before the voice
  LD.focus(0, L.x1.voiceAt + 0.6, 'bad');
  LD.strike(0, K.cue(L.x1, 'memo') - 0.3);
  LD.focus(1, K.cue(L.x1, 'memo'), 'accent');
  G.edges.forEach((e, i) => G.fire(i, K.cue(L.x1, 'order') + i * 0.12, 'cool', 0.5));
  // x2: Bellman-Ford, k + 1 rounds, the pick. The subject runs its two rounds.
  LD.focus(3, L.x2.voiceAt, 'good');
  const rTag = K.note('round 1 of 2', L.x2.voiceAt + 0.3, { x: 380, y: 840, tone: 'cool', size: 32 });
  G.edges.forEach((e, i) => G.fire(i, L.x2.voiceAt + 0.4 + i * 0.12, 'cool', 0.5));
  const rTag2 = K.note('round 2 of 2', K.cue(L.x2, 'rounds') + 0.4, { x: 380, y: 840, tone: 'good', size: 32 });
  K.hide(rTag, K.cue(L.x2, 'rounds') + 0.3, 0.15);
  G.edges.forEach((e, i) => G.fire(i, K.cue(L.x2, 'rounds') + 0.5 + i * 0.12, 'good', 0.5));
  LD.pick(3, K.cue(L.x2, 'order n space'), 'INTERVIEW PICK');
  K.hide(rTag2, ch(5) - 0.9, 0.3);
  LD.out(ch(5) - 0.9);

  // ---------------------------------------------------------------- 5 · C++ and dry run
  K.cam(ch(5) - 0.5, S.code, 1.1);
  // 30 px code (quality bar: 30 to 36): 58 columns wide, line 6's trailing comment soft-wraps; the subject and the
  // dry-run table share the 566 px column to its right
  const P = K.code({ code: F.code, x: 96, y: 196, fs: 30, lh: 1.2, wrap: 58, title: 'cheapest_flights.cpp' });
  // the panel lies under the chapter sting: it comes in as the sting leaves, and the code is written before the voice
  const in5 = K.cardClear(5);
  P.show(in5);
  P.reveal(in5 + 0.1, 1, 5, 0.05);
  P.reveal(in5 + 0.35, 6, 13, 0.04);
  P.reveal(in5 + 0.7, 14, 16, 0.05);
  const DT = K.table({ x: 1282, y: 568, cols: ['0', '1', '2', '3'], colTitle: 'city', rows: ['start', 'round 0', 'round 1'], cw: 92, rh: 58, gap: 8, rowGap: 10, labelW: 150, fs: 30 });
  const c = L.c1;
  // "Dry run."
  P.focus(c.voiceAt + 0.65, [3, 5]);
  DT.show(c.voiceAt);
  DT.rowIn(0, c.voiceAt + 0.1);
  DT.fill(0, ['0', '∞', '∞', '∞'], c.voiceAt + 0.3, 0.08);
  G.light(0, c.voiceAt + 0.3, 'good');
  // "Round zero reaches city one for one hundred."
  const r0 = K.cue(c, 'round zero');
  P.focus(r0 + 0.3, [6, 7]); // lines 6-7 have just revealed
  DT.rowIn(1, r0);
  DT.fill(1, ['0', '∞', '∞', '∞'], r0 + 0.2, 0.06, { tone: 'mute' }); // copied from the old row: quieter, still 4.5:1
  P.focus(r0 + 0.8, [10, 11]);
  G.fire(E(0, 1), r0 + 0.8, 'accent', 0.6);
  DT.set(1, 1, '100', r0 + 1.35, { tone: 'good' });
  P.focus(r0 + 1.9, 13);
  // "Round one reaches city three for seven hundred."
  const r1 = K.cue(c, 'round one');
  P.focus(r1 - 0.25, [6, 7]);
  DT.rowIn(2, r1 - 0.25);
  DT.fill(2, ['0', '100', '∞', '∞'], r1 - 0.1, 0.05, { tone: 'mute' });
  P.focus(r1 + 0.7, [10, 11]);
  G.fire(E(1, 2), r1 + 0.7, 'accent', 0.55);
  DT.set(2, 2, '200', r1 + 1.2, { tone: 'good' });
  const t700 = K.cue(c, 'seven hundred') - 0.6;
  G.fire(E(1, 3), t700, 'accent', 0.55);
  DT.set(2, 3, '700', t700 + 0.5, { tone: 'good' });
  G.fire(E(2, 3), t700 + 0.7, 'bad', 0.5);
  const skip = K.note('2→3 skipped: old dist[2] = ∞', t700 + 0.9, { x: 1552, y: 860, tone: 'bad', size: 30 });
  DT.mark(2, 3, c.voiceEnd - 0.2, 'good');
  P.focus(c.voiceEnd - 0.2, 15);
  K.hide(skip, L.o1.voiceAt - 0.2, 0.3);
  P.out(L.o1.voiceAt - 0.4);
  DT.out(L.o1.voiceAt - 0.4);

  // o1: "k stops means k plus one rounds. Copy before you update."
  K.cam(L.o1.voiceAt - 0.45, S.outro, 1.3);
  G.light(0, L.o1.voiceAt, 'accent');
  const fin = G.route([0, 1, 3], L.o1.voiceAt + 0.3, 1.1, 'good', { lightNodes: true });
  const h1 = K.headline(`k stops <span style="color:${K.tok.color.mute}">→</span> <span style="color:${K.ink('gold')}">k + 1</span> rounds`, L.o1.voiceAt, { y: 190, size: 76 });
  const h2 = K.headline('Copy before you update.', K.cue(L.o1, 'copy') - 0.6, { y: 286, size: 56, tone: 'accentText' });
  K.note(`<span class="mono">${K.fmtO('O(k·E)')}</span> time · <span class="mono">O(n)</span> space`, K.cue(L.o1, 'copy') + 0.6, { x: 1590, y: 640, tone: 'good', size: 30 });
  G.pulse(3, K.cue(L.o1, 'copy') + 0.2, 1.15);
  K.cam.push(L.o1.voiceEnd - 0.2, Math.max(1, K.T.total - L.o1.voiceEnd), 0.95);
  return K.finish();
};
