// film.js: THE SCENES. This is the file a new film replaces (the kit in src/kit/ stays).
// It implements examples/mini/script.json (LC 787 in one minute) line by line: every animation is keyed to a
// line id from timing.js (at('p4', 0.5) = halfway through line p4's voice), never to a hard-coded second.
//
// Shape of a film:
//   1. data for the persistent subject (here the Example 1 flight map) and the code
//   2. camera shots (named, reused)
//   3. buildFilm(): create the subject, the overlay pieces, then one block per chapter registering tweens
//   4. return { tl, things }: main.js seeks tl and applies things every frame
import { Vector3 } from 'three';
import { Timeline, at, word, start, end, TOTAL } from './kit/time.js';
import { C, GLOW } from './kit/style.js';
import { Graph } from './kit/graph3d.js';
import { Token } from './kit/token.js';
import { CameraRig } from './kit/camera.js';
import { frame, Captions, ChapterMarks, TitleCard, Card, QuestionCard, CodePanel, ArrayRow, Ladder, Burst, Decoder, RecTree, chip } from './kit/ui.js';

// ------------------------------------------------------------------ 1. data
const NODES = [{ id: 0, pos: [-9, 1.6] }, { id: 1, pos: [-2.2, -5] }, { id: 2, pos: [-1.4, 5.1] }, { id: 3, pos: [8.6, 0.2] }];
const EDGES = [[0, 1, 100], [1, 2, 100, { labelAt: 0.74 }], [2, 0, 100, { labelAt: 0.6 }], [1, 3, 600], [2, 3, 200]];
// The exact code that was compiled (brief.md, Facts), re-indented with 2 spaces so it fits the panel at 30 px
// (only whitespace changed). Lines too long for the panel wrap 2ch right of their own indent.
const CODE = `int findCheapestPrice(int n, vector<vector<int>>& flights, int src, int dst, int k) {
  const int INF = 1e9;
  vector<int> dist(n, INF);
  dist[src] = 0;
  for (int round = 0; round <= k; ++round) {  // k stops = k+1 flights
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
const INF = '∞';

// ------------------------------------------------------------------ 2. camera shots
// target = what the camera looks at, dist = how far, az = degrees around (0 = front), el = degrees above
const SHOT = {
  establish: { target: [0, 0, 0], dist: 66, az: -42, el: 33, fov: 30 },
  title: { target: [-5, 0.5, 0.5], dist: 44, az: -26, el: 27, fov: 30 },
  decode: { target: [-6.2, 2.4, 1.2], dist: 38, az: -8, el: 47, fov: 30 },   // graph right of the input card
};
// shots that share the screen with a panel: the whole graph (with its weight tags) is fitted into a box of the
// 1920x1080 frame [left, top, right, bottom] seen from az/el; cam.fit() solves target, dist and frame (see
// buildFilm). Keep boxes inside the safe area (96 px from the edges, bottom above the 880 caption band).
const FIT = {
  ends: { box: [640, 170, 1824, 880], az: 7, el: 38 },        // right of the input card
  limit: { box: [640, 300, 1824, 880], az: -5, el: 44 },      // right of the input card, under the k chip
  route: { box: [640, 220, 1824, 880], az: -14, el: 38 },     // right of the input card, room for the cost chip
  answer: { box: [200, 330, 1800, 880], az: 30, el: 32 },     // the input is gone: orbit round, room for the burst
  brute: { box: [96, 160, 1140, 860], az: -16, el: 52 },      // graph left, recursion tree right
  question: { box: [260, 410, 1660, 880], az: -4, el: 42 },   // graph under the question card
  ask2: { box: [820, 470, 1824, 880], az: -8, el: 46 },       // right of the rows, under the question card
  rows: { box: [820, 160, 1824, 880], az: -8, el: 46 },       // right of the rows
  ladder: { box: [96, 170, 900, 880], az: -10, el: 48 },      // graph left, ladder right
  code: { box: [96, 170, 740, 690], az: -8, el: 56 },         // graph top-left, code right, dist row bottom-left
  outro: { box: [300, 430, 1620, 880], az: 20, el: 31 },      // graph under the recap card
};

// ------------------------------------------------------------------ 3. the film
export function buildFilm({ stage, ui }) {
  const tl = new Timeline();
  const g = new Graph(stage, ui, { nodes: NODES, edges: EDGES });
  const tok = new Token(stage, g);
  const ghosts = [0, 1, 2, 3].map(() => new Token(stage, g, { ghost: true, color: C.cool, size: 0.8 }));
  const cam = new CameraRig(stage, SHOT.establish);
  for (const [k, { box, ...o }] of Object.entries(FIT)) SHOT[k] = cam.fit(g.bounds(null, { flags: [0, 3] }), box, { fov: 30, ...o });   // START, GOAL flags
  frame(ui);
  new Captions(ui);
  new ChapterMarks(ui);

  // ---- small verbs used by every chapter
  const allEdges = EDGES.map(([a, b]) => [a, b]);
  const edge = (a, b) => g.e(a, b);
  /** light edges a->b in a meaning (hot, good, bad, cool, idle, dim) */
  const light = (pairs, kind, time, d = 0.35) => {
    for (const [a, b] of pairs) tl.to(edge(a, b), { tone: kind === 'idle' || kind === 'dim' ? C.edge : C[kind], glow: GLOW[kind], dim: kind === 'dim' ? 1 : 0 }, time, d);
  };
  const fire = (a, b, time, d = 0.6, tone = C.hot) => {
    tl.set(edge(a, b), { fire: 0 }, time); tl.to(edge(a, b), { fire: 1 }, time, d, 'inOut');
    tl.to(edge(a, b), { tone, glow: GLOW.hot }, time, 0.15);
  };
  /** fly the token along a route of node ids in d seconds */
  const fly = (t, route, time, d) => { tl.set(t.p, { route, u: 0 }, time); tl.to(t.p, { u: route.length - 1 }, time, d, 'inOut'); };
  /** shrink the token away and pop it back at a node */
  const teleport = (t, node, time) => { tl.to(t.p, { on: 0 }, time, 0.22, 'in'); tl.set(t.p, { route: [node], u: 0 }, time + 0.24); tl.to(t.p, { on: 1 }, time + 0.26, 0.45, 'outBack'); };
  const resetEdges = (time) => { for (const [a, b, w] of EDGES) tl.to(edge(a, b), { tone: C.edge, glow: GLOW.idle, dim: 0, label: String(w), labelTone: '' }, time, 0.4); };
  /** show a badge above node i: its text switches at once (a string tween would switch at the end, after the
   *  badge has already faded in with the old text), then it grows in; `more` tweens other node props alongside */
  const badge = (i, value, tone, time, more = {}, d = 0.4) => {
    tl.set(g.n(i), { value: String(value), valueTone: tone }, time);
    tl.to(g.n(i), { valueOn: 1, ...more }, time, d, 'outBack');
  };
  const badges = (vals, time, tone = '') => vals.forEach((v, i) => (v === null ? tl.to(g.n(i), { valueOn: 0 }, time, 0.3) : badge(i, v, tone, time, {}, 0.3)));
  /** change an edge's weight tag (switch at once, with a small pop) */
  const relabel = (a, b, label, tone, time) => { tl.set(edge(a, b), { label, labelTone: tone }, time); tl.pulse(edge(a, b), { labelPop: 1 }, time, 0.45); };
  const badgesOff = (time) => NODES.forEach((n) => tl.to(g.n(n.id), { valueOn: 0 }, time, 0.25, 'in'));
  // ---- the chapter banner (ChapterMarks) sweeps in 0.78 s before a chapter starts and sweeps out 0.5-0.8 s into
  // it. Nothing may sit under it: a chapter's panels and badges leave by the end of its last line (leave(id), with
  // a fade of 0.3 s or less) and the next chapter's panels enter once the banner has gone (enter(id)), never
  // earlier. The 3D subject (pillars, token, arcs) may change behind the banner.
  const enter = (id) => start(id) + 0.7;
  const leave = (id) => end(id) - 0.35;

  // ---- the subject starts flat: pads only, the token waiting on city 0
  for (const n of NODES) tl.set(g.n(n.id), { rise: 0 }, 0);

  // =========================================================== 0 Intro: i1
  {
    cam.shot(tl, 0, SHOT.title, at('i1', 1) + 0.6, 'inOut');
    const title = new TitleCard(ui, { kicker: 'LEETCODE 787 · MEDIUM · GRAPHS', title: 'Cheapest Flights', title2: 'Within K Stops', sub: 'decode it, then build the idea' });
    tl.to(title.p, { on: 1 }, 0.1, 0.4);
    tl.to(title.p, { k: 1 }, 0.15, 1.3, 'linear');
    tl.to(title.p, { on: 0 }, leave('i1'), 0.3, 'in');
  }

  // =========================================================== 1 The problem: p1 p2 p3 p4
  const dec = new Decoder(ui, [
    ['n = ', ['4', 'n']],
    ['flights = ['],
    ['  ', ['[0, 1, 100]', 'f0']], ['  ', ['[1, 2, 100]', 'f1']], ['  ', ['[2, 0, 100]', 'f2']],
    ['  ', ['[1, 3, 600]', 'f3']], ['  ', ['[2, 3, 200]', 'f4']],
    [']'],
    ['src = ', ['0', 'src'], '   dst = ', ['3', 'dst']],
    ['k = ', ['1', 'k']],
  ], { x: 96, y: 176 });
  {
    // p1: four cities rise out of the board; each flight flies from the input text into its arc
    cam.shot(tl, start('p1') - 0.2, SHOT.decode, 1.6);
    tl.to(dec.p, { on: 1 }, enter('p1'), 0.4);
    tl.to(dec.row(0), { on: 1 }, enter('p1') + 0.05, 0.35);
    dec.target('n', new Vector3(0, 0.5, 0)).send(tl, 'n', enter('p1') + 0.15, 0.55);
    NODES.forEach((n, i) => tl.to(g.n(n.id), { rise: 1 }, start('p1') + 0.1 + i * 0.13, 0.65, 'outBack'));   // behind the banner, up before the voice
    // the flight rows land first (quick stagger), then each flight flies from its row into its arc
    tl.to(dec.row(1), { on: 1 }, word('p1', 'Each flight') - 0.3, 0.3);
    EDGES.forEach((_, i) => tl.to(dec.row(2 + i), { on: 1 }, word('p1', 'Each flight') - 0.2 + i * 0.08, 0.3));
    tl.to(dec.row(7), { on: 1 }, word('p1', 'Each flight') + 0.2, 0.3);
    EDGES.forEach(([a, b], i) => {
      const t0 = word('p1', 'Each flight') + 0.15 + i * 0.32;
      dec.target(`f${i}`, () => g.mid(a, b)).send(tl, `f${i}`, t0, 0.65);
      tl.to(edge(a, b), { draw: 1 }, t0 + 0.6, 0.55, 'out');
      tl.to(edge(a, b), { labelOn: 1 }, t0 + 0.8, 0.4, 'outBack');
    });

    // p2: src and dst land on cities 0 and 3 as START and GOAL flags
    cam.shot(tl, start('p2'), SHOT.ends, 2.2);
    tl.to(dec.row(8), { on: 1 }, at('p2') - 0.1, 0.3);
    dec.target('src', () => g.top(0)).send(tl, 'src', at('p2', 0.02), 0.6);
    tl.to(g.n(0), { tag: 'START', tagOn: 1, tagTone: C.good, glow: 1, tone: C.good }, at('p2', 0.3), 0.45, 'outBack');
    tl.to(tok.p, { jump: 1 }, at('p2', 0.3), 0.55, 'linear');
    dec.target('dst', () => g.top(3)).send(tl, 'dst', word('p2', 'end at'), 0.6);
    tl.to(g.n(3), { tag: 'GOAL', tagOn: 1, tagTone: C.gold, glow: 1, tone: C.gold }, word('p2', 'end at') + 0.65, 0.45, 'outBack');

    // p3: k = 1, the cities in between are "stops"; at most one of them
    cam.shot(tl, start('p3'), SHOT.limit, 2.0);
    tl.to(dec.row(9), { on: 1 }, at('p3') - 0.1, 0.3);
    tl.to(dec.tok('k'), { hi: 1 }, at('p3'), 0.2);
    for (const i of [1, 2]) badge(i, 'stop?', C.cool, word('p3', 'one stop') - 0.3 + (i - 1) * 0.15, { glow: 1, tone: C.cool });
    const kchip = chip(ui, { pos: [1232, 262], text: 'k = 1  →  at most **1** stop', tone: C.gold, cls: 'chip big' });
    tl.to(kchip, { on: 1 }, word('p3', 'at most'), 0.45, 'outBack');
    tl.to(kchip, { on: 0 }, end('p3') - 0.1, 0.3, 'in');
    tl.to(dec.tok('k'), { hi: 0 }, end('p3') - 0.2, 0.2);

    // p4: the token flies 0 -> 1 -> 3; the cost ticks up; 700 lands with a burst
    const t0 = at('p4', 0.02), legA = 0.9, dwell = 0.35, legB = 1.0;
    cam.shot(tl, start('p4'), SHOT.route, 1.4);
    for (const i of [1, 2]) tl.to(g.n(i), { glow: 0, valueOn: 0 }, start('p4'), 0.3);
    tl.set(tok.p, { route: [0, 1, 3], u: 0 }, t0);
    tl.to(tok.p, { u: 1 }, t0, legA, 'inOut');
    fire(0, 1, t0, legA);
    tl.to(tok.p, { u: 2 }, t0 + legA + dwell, legB, 'inOut');
    fire(1, 3, t0 + legA + dwell, legB);
    badge(1, '1 stop', C.gold, t0 + legA - 0.1, { glow: 1, tone: C.gold });
    const cost = chip(ui, { world: () => tok.where(), offset: [0, -30], format: (n) => `cost **${Math.round(n)}**`, tone: C.hot });
    tl.to(cost, { on: 1 }, t0 + 0.1, 0.35, 'outBack');
    tl.to(cost, { n: 100 }, t0 + legA - 0.2, 0.3);
    tl.to(cost, { n: 700 }, t0 + legA + dwell + legB - 0.4, 0.45);
    const land = t0 + legA + dwell + legB;
    light([[0, 1], [1, 3]], 'good', land, 0.4);
    tl.to(g.n(3), { glow: 1.4, tone: C.good }, land, 0.3);
    tl.to(cost, { tone: C.good }, land, 0.2);
    tl.to(tok.p, { jump: 0 }, land - 0.01, 0.01).to(tok.p, { jump: 1 }, land, 0.5, 'linear');
    cam.shot(tl, land - 0.4, SHOT.answer, 1.6);
    tl.to(dec.p, { on: 0 }, land - 0.4, 0.4, 'in');   // the input has done its job: the answer gets the whole frame
    const b700 = new Burst(ui, { text: '700!', tone: C.good, world: () => g.top(3).add({ x: 0, y: 4.2, z: 0 }), size: 1.05 });
    b700.pop(tl, word('p4', 'The answer'), end('p4') - word('p4', 'The answer') - 0.5);
    cam.shake(tl, word('p4', 'The answer'), 0.45);
    tl.to(cost, { on: 0 }, word('p4', 'The answer') + 0.05, 0.25, 'in');   // the burst takes over its number; it would sit under it
    badgesOff(leave('p4'));
  }

  // =========================================================== 2 Brute force: b1
  {
    const t = start('b1');
    cam.shot(tl, t - 0.8, SHOT.brute, 2.0);
    resetEdges(t - 0.6);
    for (const n of NODES) tl.to(g.n(n.id), { glow: 0 }, t - 0.6, 0.3);
    teleport(tok, 0, t - 0.6);
    // ghosts explore every route out of city 0 while the recursion tree grows level by level
    const tree = new RecTree(ui, { tree: [0, [1, [2, [0], [3]], [3]]], title: 'EVERY ROUTE FROM 0', x: 1196, y: 176, w: 560, h: 400 });
    const routes = [[0, 1, 2, 0], [0, 1, 3], [0, 1, 2, 3], [0, 1, 2]];
    const t1 = at('b1', 0.02), hop = 0.5;
    tl.to(tree.p, { on: 1 }, enter('b1'), 0.4);   // the root pops inside it as it fades in
    [0, 1, 2, 3].forEach((d) => tree.level(tl, d, t1 + d * hop));
    // a leaf's verdict appears with the leaf (tree nodes are numbered level by level; both are 2nd on their level)
    const note = (i, text, tone, time) => { tl.set(tree.node(i), { note: text, tone, noteOn: 0 }, time); tl.to(tree.node(i), { noteOn: 1 }, time, 0.18); };
    note(3, '700 ✓', C.good, t1 + 2 * hop + 0.08);
    note(5, '2 stops ✗', C.bad, t1 + 3 * hop + 0.08);
    ghosts.forEach((gh, i) => {
      tl.set(gh.p, { route: [0], u: 0, on: 0 }, 0);
      tl.to(gh.p, { on: 1 }, t1 + i * 0.1, 0.3, 'outBack');
      fly(gh, routes[i], t1 + 0.15 + i * 0.1, (routes[i].length - 1) * hop);
      tl.to(gh.p, { on: 0 }, end('b1') - 0.4, 0.3, 'in');
    });
    [[0, 1, 0], [1, 2, 1], [1, 3, 1], [2, 0, 2], [2, 3, 2]].forEach(([a, b, lvl]) => fire(a, b, t1 + 0.15 + lvl * hop, hop, C.cool));
    light(allEdges, 'cool', t1 + 0.3, 0.3);
    const big = chip(ui, { pos: [1476, 800], text: 'O(n^(k+1)) time', tone: C.bad, cls: 'chip big' });
    tl.to(big, { on: 1 }, word('b1', 'Exponential') - 0.5, 0.45, 'outBack');   // in place as the word is spoken
    tl.to(big, { on: 0 }, leave('b1'), 0.3, 'in');
    tl.to(tree.p, { on: 0 }, leave('b1'), 0.3, 'in');
    light(allEdges, 'idle', end('b1') - 0.3, 0.4);
  }

  // =========================================================== 3 Intuition: q1 a1 q2 a2
  {
    // q1: what is simpler to count than stops? (the route 0 -> 1 -> 3 waits on the board)
    const q1 = new QuestionCard(ui, { n: 1, text: 'What is simpler to count than stops?' }).countdown(tl, 'q1', at('a1') - 0.1, { from: enter('q1') });
    cam.shot(tl, start('q1') - 0.6, SHOT.question, 1.8);
    light([[0, 1], [1, 3]], 'hot', at('q1', 0.5), 0.5);
    badge(1, 'stop', C.gold, at('q1', 0.6), { glow: 1, tone: C.gold });

    // a1: count flights instead: the same route is 2 flights, k + 1
    fly(tok, [0, 1, 3], at('a1'), 1.6);
    tl.to(g.n(1), { valueOn: 0 }, at('a1') - 0.1, 0.3, 'in');   // q1's "stop" steps aside for the flight labels
    relabel(0, 1, 'flight 1', C.gold, at('a1', 0.1));
    relabel(1, 3, 'flight 2', C.gold, at('a1', 0.1) + 0.8);
    const fl = chip(ui, { pos: [960, 240], text: 'k + 1 = **2** flights', tone: C.gold, cls: 'chip big' });
    tl.to(fl, { on: 1 }, word('a1', 'at most'), 0.45, 'outBack');
    tl.to(fl, { on: 0 }, end('a1') - 0.15, 0.3, 'in');

    // q2: why read the old row while writing the new one? dist and next appear under the board
    const dist = new ArrayRow(ui, { label: 'dist', values: [0, INF, INF, INF], heads: ['0', '1', '2', '3'], x: 96, y: 560 });
    const next = new ArrayRow(ui, { label: 'next', values: [0, INF, INF, INF], heads: ['0', '1', '2', '3'], x: 96, y: 722 });
    new QuestionCard(ui, { n: 2, text: 'Why read the old row while writing a new one?' }).countdown(tl, 'q2', at('a2') - 0.1);
    cam.shot(tl, start('q2') - 0.3, SHOT.ask2, 1.6);
    cam.shot(tl, at('a2') - 0.4, SHOT.rows, 1.1);
    resetEdges(start('q2'));
    teleport(tok, 0, start('q2'));
    tl.to(g.n(1), { glow: 0, valueOn: 0 }, start('q2'), 0.3);
    tl.to(dist.p, { on: 1 }, at('q2', 0.35), 0.45, 'outBack');
    tl.to(next.p, { on: 1 }, at('q2', 0.55), 0.45, 'outBack');
    badges([0, INF, INF, INF], at('q2', 0.4));

    // a2: one round: 0 -> 1 fires (reads old dist[0] = 0); 1 -> 3 cannot use the new 100 until the next round
    const r0 = at('a2', 0.05);
    fire(0, 1, r0, 0.6, C.good);
    next.write(tl, 1, 100, r0 + 0.6);
    tl.to(g.n(1), { value: '100', valueTone: C.good, glow: 1, tone: C.good }, r0 + 0.6, 0.3, 'outBack');
    fire(1, 3, r0 + 0.75, 0.5, C.bad);
    light([[1, 3]], 'dim', r0 + 1.3, 0.3);
    const one = chip(ui, { world: () => g.mid(1, 3), offset: [0, 22], text: 'not this round', tone: C.bad, pivot: [-50, 0] });
    tl.to(one, { on: 1 }, r0 + 1.15, 0.35, 'outBack');
    tl.to(one, { on: 0 }, leave('a2'), 0.3, 'in');
    const rchip = chip(ui, { pos: [408, 470], text: 'one round = **+1 flight**', tone: C.good, cls: 'chip big' });
    tl.to(rchip, { on: 1 }, word('a2', 'exactly'), 0.45, 'outBack');
    tl.to(rchip, { on: 0 }, leave('a2'), 0.3, 'in');
    dist.write(tl, 1, 100, at('a2', 0.95));
    for (const r of [dist, next]) tl.to(r.p, { on: 0 }, leave('a2'), 0.3, 'in');
    badgesOff(leave('a2'));
  }

  // =========================================================== 4 Every approach: x1 x2
  {
    const lad = new Ladder(ui, {
      x: 944, y: 196, rungs: [
        { name: 'Brute-force DFS', time: 'O(n^(k+1))', space: 'O(k)', cost: 1.0, tone: C.bad },
        { name: 'DFS + memo', time: 'O(k·E)', space: 'O(n·k)', cost: 0.42, tone: C.cool },
        { name: 'Bellman-Ford, k+1 rounds', time: 'O(k·E)', space: 'O(n)', cost: 0.38, tone: C.good },
      ],
    });
    cam.shot(tl, start('x1') - 0.8, SHOT.ladder, 1.8);
    resetEdges(start('x1') - 0.6);
    for (const n of NODES) tl.to(g.n(n.id), { glow: 0 }, start('x1') - 0.6, 0.3);
    tl.to(lad.p, { on: 1 }, enter('x1'), 0.4);
    tl.to(lad.rung(0), { on: 1 }, enter('x1') + 0.05, 0.4);
    // x1: DFS + memo: every (city, flights left) pair once: each edge is relaxed k times
    tl.to(lad.rung(1), { on: 1, hi: 1 }, enter('x1') + 0.3, 0.45);
    for (let lap = 0; lap < 2; lap++) EDGES.forEach(([a, b], i) => fire(a, b, at('x1', 0.25) + lap * 0.9 + i * 0.12, 0.55, C.cool));
    const ek = chip(ui, { pos: [1430, 640], text: 'every edge, k times', tone: C.cool });
    tl.to(ek, { on: 1 }, at('x1', 0.3), 0.4, 'outBack');
    tl.to(ek, { on: 0 }, end('x1') - 0.2, 0.3, 'in');
    light(allEdges, 'idle', end('x1') - 0.2, 0.3);
    // x2: Bellman-Ford: k + 1 rounds over all edges, one number per city
    tl.to(lad.rung(1), { hi: 0 }, at('x2'), 0.3);
    tl.to(lad.rung(2), { on: 1, hi: 1 }, at('x2', 0.02), 0.45);
    [0, 1].forEach((r) => {
      const tr = word('x2', 'k plus one') + r * 1.0;
      EDGES.forEach(([a, b]) => fire(a, b, tr, 0.6, C.good));
      const rc = chip(ui, { world: () => g.top(0), offset: [0, -70], text: `round ${r}`, tone: C.good });
      tl.to(rc, { on: 1 }, tr, 0.3, 'outBack'); tl.to(rc, { on: 0 }, tr + 0.9, 0.2, 'in');
    });
    badges([0, 100, 200, 700], word('x2', 'order n space') - 0.45, C.good);   // one number per city, in place as it is said
    tl.set(lad.p, { pick: 2 }, 0);
    tl.to(lad.p, { pickOn: 1 }, word('x2', 'Order k times E') + 0.3, 0.4, 'outBack');   // after the rounds, held to the end
    light(allEdges, 'idle', end('x2') - 0.3, 0.3);
    tl.to(lad.p, { on: 0 }, leave('x2'), 0.3, 'in');
    badgesOff(leave('x2'));
  }

  // =========================================================== 5 C++ and dry run: c1 o1
  {
    const code = new CodePanel(ui, { code: CODE, x: 784, y: 96, w: 1040, size: 30, lh: 1.34 });
    const dist = new ArrayRow(ui, { label: 'dist', values: [0, INF, INF, INF], heads: ['0', '1', '2', '3'], x: 96, y: 712 });
    const c = start('c1');
    cam.shot(tl, c - 0.8, SHOT.code, 1.8);
    tl.to(code.p, { on: 1 }, enter('c1'), 0.4);
    code.reveal(tl, 15, enter('c1') + 0.05, 0.6);   // lines cascade in top to bottom, all shown before the focus reaches line 9
    tl.to(dist.p, { on: 1 }, enter('c1'), 0.45, 'outBack');
    badges([0, INF, INF, INF], enter('c1') + 0.2);
    code.focus(tl, 3, at('c1', 0.0));
    // round 0 (k stops = k+1 flights): 0 -> 1 relaxes
    const r0 = word('c1', 'Round zero');
    code.focus(tl, 5, r0 - 0.3);
    code.focus(tl, 9, r0 + 0.15);
    fire(0, 1, r0 + 0.2, 0.6, C.good);
    dist.write(tl, 1, 100, r0 + 0.8);
    tl.to(g.n(1), { value: '100', valueTone: C.good }, r0 + 0.8, 0.3, 'outBack');
    code.focus(tl, 12, r0 + 1.1);
    // round 1: 1 -> 2 and 1 -> 3 relax; 2 -> 3 is skipped (old dist[2] is still infinity)
    const r1 = word('c1', 'Round one');
    code.focus(tl, 5, r1 - 0.3);
    code.focus(tl, 9, r1 + 0.1);
    fire(1, 2, r1 + 0.15, 0.55, C.good);
    dist.write(tl, 2, 200, r1 + 0.7);
    tl.to(g.n(2), { value: '200', valueTone: C.good }, r1 + 0.7, 0.3, 'outBack');
    fire(1, 3, r1 + 0.45, 0.6, C.good);
    dist.write(tl, 3, 700, r1 + 1.05);
    tl.to(g.n(3), { value: '700', valueTone: C.good, glow: 1.3, tone: C.good }, r1 + 1.05, 0.3, 'outBack');
    fire(2, 3, r1 + 0.8, 0.5, C.bad);
    light([[2, 3]], 'dim', r1 + 1.3, 0.3);
    code.focus(tl, 14, at('c1', 0.93));
    const b = new Burst(ui, { text: '700', tone: C.good, world: () => g.top(3).add({ x: 0, y: 4, z: 0 }), size: 0.8 });
    b.pop(tl, at('c1', 0.95), end('c1') - at('c1', 0.95) - 0.2);

    // o1: pull back; recap card; the token celebrates on the goal
    const o = start('o1');
    cam.shot(tl, o - 0.2, SHOT.outro, 2.6);
    tl.to(code.p, { on: 0 }, o - 0.2, 0.4, 'in');
    tl.to(dist.p, { on: 0 }, o - 0.2, 0.4, 'in');
    light(allEdges, 'idle', o, 0.3);
    light([[0, 1], [1, 3]], 'good', o + 0.1, 0.4);
    const recap = new Card(ui, { kicker: 'RECAP', big: 'k stops → k + 1 rounds', small: 'Copy before you update · O(k·E) time · O(n) space', top: 150 });
    tl.to(recap.p, { on: 1 }, at('o1') + 1.0, 0.5, 'outBack'); // after the pull-back clears the labels: under the card they read 1.4:1
    fly(tok, [0, 1, 3], at('o1', 0.1), 1.8);
    tl.to(tok.p, { jump: 0 }, at('o1', 0.75) - 0.01, 0.01).to(tok.p, { jump: 1 }, at('o1', 0.75), 0.55, 'linear');
    tl.to(tok.p, { jump: 0 }, at('o1', 0.75) + 0.6, 0.01).to(tok.p, { jump: 1 }, at('o1', 0.75) + 0.62, 0.55, 'linear');
    tl.to(recap.p, { on: 0 }, TOTAL - 0.5, 0.4, 'in');
  }

  // keep the camera alive between shots, and settle at the end
  tl.set(cam.p, { drift: 1 }, 0);
  return { tl, things: [cam, g, tok, ...ghosts] };
}
