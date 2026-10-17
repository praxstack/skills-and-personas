// shots.js: WHEN things happen. Every keyframe of the film, keyed to narration line ids (never to raw seconds), so
// re-voicing re-times the whole film on the next `npm run build`. tools/build.mjs compiles this into
// theatre-state.json (Theatre.js keyframes with bezier handles). This demo implements all 14 lines of
// examples/mini/script.json; a new film rewrites this file and world.js.
//
//   s.to(obj, props, t, dur, ease)   tween        s.set(obj, props, t)        jump / hold (text, numbers that step)
//   s.fromTo(obj, from, to, t, ...)  reset+tween  s.pulse(obj, prop, t, {...}) up and back down
//   s.stagger([objs], props, t, dur, gap, ease)   s.cam(props, t, dur, ease)  raw Camera moves
//   T.at(id, frac)  T.after(id, sec)  T.word(id, 'phrase')  T.start(id)  T.end(id)  T.think(id)  T.chapter(n)
//   R.* recipes (src/theatre/recipes.js): R.focus(rect) camera framing, R.chapter(n) card (content out, card, content
//       back: { t0, end, back, shown }; re-frame between t0 and back, while nothing is visible), R.burst, R.fly a route,
//       R.reject, R.question / R.answer, R.mood (sky), R.reset, R.land
import { recipes } from '../theatre/recipes.js';
import { MOOD } from '../kit/tokens.js';

export default function shots(s, T, W) {
  const R = recipes(s, T, W);
  const G = W.graph, node = (i) => G.nodeKey(i), edge = (a, b) => G.edgeKey(a, b);
  const ALL = G.edges.map((e) => [e.from, e.to]);
  // where the graph sits in each part of the film (it never leaves; it moves and shrinks to make room)
  const PLACE = {
    full: { x: 0, y: 0, s: 1 },
    question: { x: 60, y: 130, s: 0.82 },
    rows: { x: 240, y: 130, s: 0.82 },
    ladder: { x: -560, y: 40, s: 0.7 },
    code: { x: -722, y: -72, s: 0.6 },   // the left column of the chapter-5 desk, above the dry-run table
  };
  const place = (p, t, dur = 1.0) => s.to('Graph', p, t, dur, 'inOut');
  const hidden = (c) => Math.max(0.3, c.back - c.t0 - 0.05); // re-frame while the chapter card is up: done before the content returns

  // ------------------------------------------------------------------ 0 · intro: title over a dolly-in
  s.set('Sky', { ...MOOD.dusk }, 0);
  s.set('Camera', { z: -340, y: -70, dof: 0.15 }, 0);
  s.cam({ z: 30, y: 0, dof: 0.75 }, 0, T.after('i1', 0.7), 'inOut');
  s.set('Caption', { in: 0 }, 0);
  s.to('Title', { in: 1 }, 0.25, 1.1, 'expoOut');
  s.to('Caption', { in: 1 }, T.at('i1', 0.3), 0.5, 'out');

  // ------------------------------------------------------------------ 1 · the problem: decode the input
  const c1 = R.chapter(1);
  // the title flies out as the content fades, before the card arrives (a title peeking out past the band reads as ghost text)
  s.to('Title', { out: 1 }, Math.max(T.after('i1', 0), c1.t0 - 0.3), 0.3, 'in');
  R.mood('night', T.start('p1'), 2.5);
  const wide = R.union(W.decoder.rect(), G.rect());
  R.focus(wide, T.start('p1'), 1.6, { orbit: -2 });
  s.stagger([0, 1, 2, 3].map(node), { in: 1 }, c1.back, 0.55, 0.12, 'back'); // the cities come in as the card leaves: up before the voice
  const each = T.word('p1', 'each flight');
  s.to('Decoder', { in: 1 }, each - 0.45, 0.6, 'expoOut');
  s.to('Decoder', { rows: 8 }, each - 0.25, 0.9, 'out');
  // each flight's price lifts off its row and flies into the map; its arrow draws under it and the weight
  // appears on the arrow as the chip lands (the chip is gone that frame: no cross-fade, no ghost text)
  const flyAt = each + 0.35;
  [2, 3, 4, 5, 6].forEach((row, j) => {
    const t = flyAt + j * 0.24, [a, b] = W.decoder.rows[row].to.edge.split('-');
    s.to('Decoder', { hl: row }, t - 0.1, 0.18, 'out');
    s.to(`Decoder / fly ${row}`, { u: 1 }, t, 0.7, 'inOut');
    s.to(edge(a, b), { draw: 1 }, t + 0.15, 0.55, 'inOut');
  });
  s.to('Decoder', { hl: -1 }, flyAt + 5 * 0.24 + 0.3, 0.3, 'in');

  // src and dst land on their cities
  s.to('Decoder', { rows: 11 }, T.at('p2') - 0.25, 0.5, 'out');
  s.to('Decoder', { hl: 8 }, T.at('p2'), 0.3, 'out');
  s.to('Decoder / fly 8', { u: 1 }, T.at('p2', 0.05), 0.65, 'inOut');
  s.set(node(0), { tag: 'START' }, T.at('p2', 0.3));
  s.to(node(0), { tagIn: 1, glow: 0.9 }, T.at('p2', 0.3), 0.45, 'back');
  s.fromTo(node(0), { ring: 0 }, { ring: 1 }, T.at('p2', 0.3), 0.8, 'out');
  const endAt = T.word('p2', 'end at');
  s.to('Decoder', { hl: 9 }, endAt, 0.3, 'inOut');
  s.to('Decoder / fly 9', { u: 1 }, endAt + 0.05, 0.75, 'inOut');
  s.set(node(3), { tag: 'GOAL' }, endAt + 0.6);
  s.to(node(3), { tagIn: 1, glow: 0.9 }, endAt + 0.6, 0.45, 'back');
  s.fromTo(node(3), { ring: 0 }, { ring: 1 }, endAt + 0.6, 0.8, 'out');
  R.focus(wide, T.at('p2'), 2.4, { orbit: 2, zoom: 1.04 });

  // k = 1: a stop is a city in between
  s.to('Decoder', { hl: 10 }, T.at('p3'), 0.3, 'inOut');
  for (const i of [1, 2]) {
    s.set(node(i), { tag: 'STOP?' }, T.at('p3', 0.45));
    s.to(node(i), { tagIn: 1, glow: 0.6 }, T.at('p3', 0.45), 0.4, 'back');
    s.fromTo(node(i), { ring: 0 }, { ring: 1 }, T.at('p3', 0.45), 0.8, 'out');
  }
  R.burst(0, 'MAX 1 STOP', T.word('p3', 'one stop'), { color: 'gold', x: 400, y: 340, size: 0.5, rot: -6, hold: 1.2, shake: 0.3 }); // upper left, the one corner the push leaves empty (lower right would cover node 2's tag)
  R.focus(G.rect([1, 2]), T.at('p3', 0.3), 1.8, { orbit: 3, tilt: 1.5, max: 1.25 });
  // the input is decoded: fade it as the camera pushes past it (a panel half off the frame reads as a mistake)
  s.to('Decoder', { hl: -1, in: 0 }, T.at('p3', 0.4), 0.5, 'inOut');

  // the route 0 -> 1 -> 3 flies: one stop, 700
  s.to(node(2), { tagIn: 0, glow: 0 }, T.at('p4'), 0.3, 'in');
  s.to(node(1), { glow: 0 }, T.at('p4'), 0.3, 'in');
  s.set(node(1), { tag: 'STOP 1' }, T.at('p4', 0.3));
  for (const [a, b] of [[1, 2], [2, 0], [2, 3]]) s.to(edge(a, b), { dim: 1 }, T.at('p4'), 0.5, 'inOut');
  const landed = R.fly(0, '0-1-3', T.at('p4', 0.04), 2.3);
  s.to(node(3), { good: 1 }, landed, 0.4, 'out');
  R.burst(1, '700!', T.word('p4', 'the answer'), { color: 'good', x: 1500, y: 740, size: 0.85, hold: 1.3, shake: 0.8 }); // lower right: the camera pulls back and leaves room there
  // the whole map stays in frame (node 2 is the road not taken; the caption band must not cover it)
  R.focus(G.rect(), T.at('p4', 0.04), 2.3, { orbit: -4, zoom: 1.1 });
  R.focus(G.rect(), landed + 0.3, 1.6, { orbit: 0 });

  // ------------------------------------------------------------------ 2 · brute force: every route at once
  const c2 = R.chapter(2);
  R.mood('ember', c2.t0, 1.6);
  R.land(0, c2.t0);
  s.to('Decoder', { in: 0 }, c2.t0, 0.4, 'in');
  for (const i of [0, 1, 2, 3]) s.to(node(i), { tagIn: 0, good: 0, glow: 0 }, c2.t0, 0.3, 'in');
  R.reset(ALL, c2.t0 + 0.2);
  R.focus(G.rect(), c2.t0, hidden(c2));
  const b = T.at('b1', 0.02);
  R.fly(0, '0-1-3', b, 1.5, { result: 'hot', sum: false, rings: false });
  R.fly(1, '0-1-2-3', b + 0.25, 1.9, { sum: false, rings: false, heat: false, land: false });
  R.fly(2, '0-1-2-0-1', b + 0.5, 2.2, { sum: false, rings: false, heat: false, land: false });
  for (const [a, c] of [[1, 2], [2, 3], [2, 0]]) s.to(edge(a, c), { hot: 1 }, b + 0.9, 0.5, 'out');
  ALL.forEach(([a, c], j) => { for (const k of [0, 1]) s.fromTo(edge(a, c), { fire: 0 }, { fire: 1 }, b + 0.3 + j * 0.18 + k * 1.0, 0.7, 'inOut'); });
  // the burst gets a band of its own above the graph (framed in as headroom), so it never covers a node or a weight
  const gr = G.rect(), headroom = Object.assign([gr[0] + 0.4 * (gr[2] - gr[0]), gr[1] - 190, gr[2], gr[1]], { layer: gr.layer });
  R.burst(0, 'EXPONENTIAL!', T.word('b1', 'exponential'), { color: 'bad', x: 1400, y: 190, size: 0.64, hold: 1.0, shake: 0.9 });
  R.focus(R.union(gr, headroom), b, 3.0, { orbit: 6, tilt: 2, zoom: 1.12 });

  // ------------------------------------------------------------------ 3 · intuition: questions with a countdown
  const c3 = R.chapter(3);
  R.mood('night', c3.t0, 1.6);
  for (const i of [0, 1, 2]) R.land(i, c3.t0);
  R.reset(ALL, c3.t0 + 0.2);
  place(PLACE.question, c3.t0, hidden(c3));
  R.focus(R.union(W.question.rect(), G.rect(null, PLACE.question)), c3.t0, hidden(c3), { extra: { scrim: 0.3, dof: 1 } });
  R.question('q1', 1);
  R.focus(R.union(W.question.rect(), G.rect(null, PLACE.question)), T.think('q1').t, T.think('q1').dur + 0.4, { zoom: 1.06, orbit: -2, ease: 'soft' });
  // answer 1: count flights, not stops
  R.answer('a1');
  s.to('Camera', { scrim: 0 }, T.at('a1'), 0.5, 'inOut');
  R.fly(0, '0-1-3', T.at('a1', 0.05), 1.6, { sum: false });
  s.set(node(1), { badge: 'flight 1' }, T.at('a1', 0.3));
  s.to(node(1), { badgeIn: 1 }, T.at('a1', 0.3), 0.4, 'back');
  s.set(node(3), { badge: 'flight 2', badgeAt: 'tr' }, T.at('a1', 0.75)); // top right: 'above' would crowd the 600 chip
  s.to(node(3), { badgeIn: 1 }, T.at('a1', 0.75), 0.4, 'back');
  // question 2: read the old row, write a new one
  R.land(0, T.start('q2'));
  s.to(node(1), { badgeIn: 0 }, T.start('q2'), 0.3, 'in');
  s.to(node(3), { badgeIn: 0 }, T.start('q2'), 0.3, 'in');
  s.set(node(3), { badgeAt: '' }, T.start('q2') + 0.35); // back to the node's own placement once it is hidden
  R.reset([[0, 1], [1, 3]], T.start('q2'));
  R.question('q2', 2, { flipFrom: true });
  s.to('Camera', { scrim: 0.25 }, T.at('q2'), 0.5, 'inOut');
  place(PLACE.rows, T.at('q2'), 0.9);
  s.to('Rows', { in: 1 }, T.at('q2', 0.4), 0.6, 'expoOut');
  R.focus(R.union(W.question.rect(), W.rows.rect(), G.rect(null, PLACE.rows)), T.at('q2'), 2.0, { orbit: 2 });
  R.answer('a2');
  s.to('Camera', { scrim: 0 }, T.at('a2'), 0.5, 'inOut');
  s.fromTo(edge(0, 1), { fire: 0 }, { fire: 1 }, T.at('a2', 0.1), 0.8, 'inOut');
  s.to(edge(0, 1), { good: 1 }, T.at('a2', 0.45), 0.4, 'out');
  s.set('Rows', { step: 1 }, T.at('a2', 0.5));
  s.set('Rows', { col: 1 }, T.at('a2', 0.45)); // set, not to: a glide from -1 would sweep in from the row label
  s.pulse('Rows', 'flash', T.at('a2', 0.5), { up: 0.15, hold: 0.6, down: 0.6 });
  s.set(node(1), { badge: '100' }, T.at('a2', 0.5));
  s.to(node(1), { badgeIn: 1, good: 1 }, T.at('a2', 0.5), 0.4, 'back');
  R.focus(R.union(W.question.rect(), W.rows.rect(), G.rect(null, PLACE.rows)), T.at('a2', 0.3), 1.6, { zoom: 1.06, orbit: -1 });

  // ------------------------------------------------------------------ 4 · every approach: the ladder
  const c4 = R.chapter(4);
  R.mood('neon', c4.t0, 1.6);
  // the panels leave with the content fade, before the card arrives
  const clear4 = Math.max(T.after('a2', 0), c4.t0 - 0.3);
  s.to('Question', { in: 0 }, clear4, 0.3, 'in');
  s.to('Rows', { in: 0 }, clear4, 0.3, 'in');
  s.to(node(1), { badgeIn: 0, good: 0 }, clear4, 0.3, 'in');
  R.reset(ALL, c4.t0);
  place(PLACE.ladder, c4.t0, hidden(c4));
  const ladderWide = R.union(W.ladder.rect(), G.rect(null, PLACE.ladder));
  R.focus(ladderWide, c4.t0, hidden(c4), { extra: { scrim: 0, dof: 0.7 } });
  const ladderIn = Math.max(T.at('x1') - 0.5, c4.end); // after the card has gone, landed before the second rung
  s.to('Ladder', { in: 1, shown: 1, hl: 0 }, ladderIn, Math.min(0.6, T.at('x1', 0.1) - ladderIn - 0.02), 'expoOut');
  s.to('Ladder', { shown: 2 }, T.at('x1', 0.1), 0.7, 'out');
  s.to('Ladder', { hl: 1 }, T.at('x1', 0.1), 0.5, 'inOut');
  R.focus(ladderWide, T.at('x1'), 2.6, { orbit: -3, zoom: 1.05 });
  s.to('Ladder', { shown: 3 }, T.at('x2', 0.02), 0.7, 'out');
  s.to('Ladder', { hl: 2 }, T.at('x2', 0.02), 0.5, 'inOut');
  for (let r = 0; r < 2; r++) ALL.forEach(([a, c], j) => s.fromTo(edge(a, c), { fire: 0 }, { fire: 1 }, T.at('x2', 0.1) + r * 1.1 + j * 0.06, 0.8, 'inOut'));
  s.to('Ladder', { pick: 1 }, T.word('x2', 'order n space'), 0.45, 'back');
  s.pulse('Camera', 'shake', T.word('x2', 'order n space') + 0.1, { peak: 0.5, up: 0.05, hold: 0.05, down: 0.4 });
  R.focus(ladderWide, T.at('x2', 0.3), 2.6, { orbit: -5, zoom: 1.06 }); // the whole graph stays in frame

  // ------------------------------------------------------------------ 5 · C++ and the dry run
  const c5 = R.chapter(5);
  R.mood('night', c5.t0, 1.6);
  s.to('Ladder', { in: 0 }, Math.max(T.after('x2', 0), c5.t0 - 0.3), 0.3, 'in'); // gone before the card arrives
  place(PLACE.code, c5.t0, hidden(c5));
  const desk = R.union(W.code.rect(), W.table.rect(), G.rect(null, PLACE.code));
  const tight = { pad: 12 }; // the 17-line code panel is the tallest thing in the film: frame it snugly so it stays 30 px
  R.focus(desk, c5.t0, hidden(c5), { ...tight, extra: { dof: 0.85 } });
  const code = W.code, ln = (txt) => code.find(txt);
  s.to('Code', { in: 1 }, Math.max(T.start('c1'), c5.end), 0.7, 'expoOut'); // after the card: no panel shows behind it
  s.to('Code', { reveal: code.lines.length }, Math.max(T.start('c1'), c5.end) + 0.1, 1.4, 'out');
  s.set('Code', { line: ln('dist[src] = 0') }, T.start('c1'));
  s.to('Table', { in: 1 }, T.at('c1', 0.05), 0.6, 'expoOut');
  s.set(node(0), { badge: '0' }, T.at('c1', 0.05));
  s.to(node(0), { badgeIn: 1 }, T.at('c1', 0.05), 0.4, 'back');
  // round 0: only 0 -> 1 fires
  const r0 = T.word('c1', 'round zero');
  s.to('Code', { line: ln('if (dist[u] != INF') }, r0 - 0.1, 0.5, 'inOut');
  s.fromTo(edge(0, 1), { fire: 0 }, { fire: 1 }, r0, 0.7, 'inOut');
  s.to(edge(0, 1), { good: 1 }, r0 + 0.6, 0.3, 'out');
  s.set('Table', { step: 1, col: 1 }, r0 + 0.65);
  s.pulse('Table', 'flash', r0 + 0.65, { up: 0.12, hold: 0.5, down: 0.5 });
  s.set(node(1), { badge: '100' }, r0 + 0.65);
  s.to(node(1), { badgeIn: 1 }, r0 + 0.65, 0.4, 'back');
  R.focus(desk, r0 - 0.2, 2.2, { ...tight, zoom: 1.07, orbit: 2 });
  // round 1: 1 -> 2 and 1 -> 3 fire; 2 -> 3 is skipped (the old dist[2] was still infinity)
  const r1 = T.word('c1', 'round one');
  s.to('Code', { line: ln('next[v] = dist[u] + w') }, r1 - 0.1, 0.5, 'inOut');
  for (const [a, c] of [[1, 2], [1, 3]]) {
    s.fromTo(edge(a, c), { fire: 0 }, { fire: 1 }, r1, 0.7, 'inOut');
    s.to(edge(a, c), { good: 1 }, r1 + 0.6, 0.3, 'out');
  }
  s.set('Table', { step: 2 }, r1 + 0.65);
  s.pulse('Table', 'flash', r1 + 0.65, { up: 0.12, hold: 0.7, down: 0.5 });
  s.set(node(2), { badge: '200' }, r1 + 0.65);
  s.set(node(3), { badge: '700' }, r1 + 0.65);
  s.to(node(2), { badgeIn: 1 }, r1 + 0.65, 0.4, 'back');
  s.to(node(3), { badgeIn: 1, good: 1 }, r1 + 0.65, 0.4, 'back');
  s.to('Table', { col: 3 }, r1 + 0.7, 0.4, 'out');
  // (no "700!" burst here: chapter 5's one burst is COPY FIRST!, and every spot on this desk would cover text;
  //  the 700 lands in the table, on node 3's badge and in the caption)

  // outro: the one line to remember, then pull back to the whole desk. The dry run is done (its result is in the
  // caption of c1), so the table makes way for the burst: a burst over the graph or the code would cover their text
  R.mood('dawn', T.start('o1'), 2.0);
  s.to('Table', { in: 0 }, T.start('o1'), 0.5, 'inOut');
  R.focus(desk, T.start('o1'), 1.6, { ...tight, zoom: 1.1, orbit: 0 }); // square on: an orbit shrinks the far side of the code
  s.to('Code', { line: ln('vector<int> next = dist') }, T.word('o1', 'copy') - 0.35, 0.5, 'inOut'); // on the line as "copy" is said
  R.burst(0, 'COPY FIRST!', T.word('o1', 'copy'), { color: 'accent', x: 380, y: 770, size: 0.45, rot: -6, hold: 1.8, shake: 0.5 }); // where the table was
  for (const [a, c] of [[0, 1], [1, 3]]) s.to(edge(a, c), { glow: 1 }, T.at('o1'), 0.6, 'out');
  R.focus(desk, T.after('o1', -0.6), T.total - T.after('o1', -0.6) - 0.1, { ...tight, orbit: 1.5 }); // a slow drift, not a pull-back: the code stays 30 px
  s.to('ChapterTag', { in: 0 }, T.total - 1.0, 0.5, 'in');
}
