// The film: one continuous scene so the subject (the flight map) persists across chapters.
// Each chapter is a function that waits for its own lines (at / cue / when) and acts on the stage.
// For a new film: replace data.ts and the chapter functions below; keep setupStage() and the kit.
import {makeScene2D, Node, Rect, Txt} from '@revideo/2d';
import {
  all, delay, easeInOutCubic, easeOutBack, easeOutCubic, linear, sequence, ThreadGenerator, waitFor,
} from '@revideo/core';
import {
  ArrayRow, at, bigO, burst, C, CARD, CodePanel, counter, cue, Decoder, F, Fan, Graph, H, kinetic, L, label,
  Ladder, lowerThird, now, QuestionCard, S, setupStage, Stage, Table, textOf, titleCard, TOTAL, voiceEnd, W, when,
} from './kit';
import {CODE_LINES as CL, CPP, DRY, FLIGHTS, GRAPH, KICKER, RUNGS} from './data';

export default makeScene2D('film', function* (view) {
  const st = setupStage(view, {kicker: KICKER});
  const g = new Graph(GRAPH);
  st.world.add(g.root);
  yield st.run(); // background: captions, chapter cards, HUD, grain/drift clock

  yield* intro(st);
  yield* problem(st, g);
  yield* bruteForce(st, g);
  yield* intuition(st, g);
  yield* approaches(st, g);
  yield* codeAndDryRun(st, g);
  yield* at(TOTAL, 'end'); // the film is exactly as long as the voice timing
});

// ------------------------------------------------------------------------------------------ 0 intro
function* intro(st: Stage): ThreadGenerator {
  const tc = titleCard('Cheapest\nflights.', 'within *k* stops.', 'LEETCODE 787  ·  GRAPHS  ·  MEDIUM');
  st.world.add(tc.root);
  st.cam.set({zoom: 0.97});
  // the title lands before the voice starts (a still or a viewer never catches it half risen)
  yield* at(Math.max(0.05, L.i1.start - 0.3));
  yield* all(tc.in(), st.cam.to({zoom: 1.05}, CARD[1].coveredAt - now(), linear));
  yield* at(CARD[1].coveredAt);
  tc.root.remove();
  st.cam.set({zoom: 1});
}

// ------------------------------------------------------------------------------------------ 1 problem
function* problem(st: Stage, g: Graph): ThreadGenerator {
  yield* g.place(0, 70, 0.95);
  const dec = new Decoder({name: 'flights', items: FLIGHTS.map(f => `[${f.join(', ')}]`), y: -318, size: 34});
  st.fg.add(dec.root);
  const left = new Node({x: -650, y: 30});
  st.fg.add(left);
  const nBig = kinetic('*n* = 4', {size: 104});
  const nSub = label('CITIES 0 · 1 · 2 · 3', {y: 96});
  nSub.opacity(0);
  left.add(nBig.root);
  left.add(nSub);
  const srcB = g.badge(0, 'SRC', C.acc), dstB = g.badge(3, 'DST', C.mint);
  const ex = lowerThird('EXAMPLE 1', 'src 0  →  dst 3,  k = 1');
  st.lower.add(ex.root); // above the caption scrim, which would darken the orange block

  // p3: k = 1, a stop is a city in the middle
  const kBig = kinetic('*k* = 1', {size: 104});
  const kSub = new Txt({text: 'stop = a city in between', fontFamily: F.text, fontWeight: 500, fontSize: 32, fill: C.muted, y: 96, opacity: 0});
  left.add(kBig.root);
  left.add(kSub);
  // p4: fly 0 -> 1 -> 3: cost ticks to 700 with one stop; the answer lands
  const ro = new Rect({layout: true, direction: 'column', gap: 6, x: -660, y: 250, padding: [14, 22], radius: 14,
    fill: C.cardSoft, stroke: C.line, lineWidth: 2, opacity: 0, alignItems: 'start'});
  const roRoute = new Txt({text: 'ROUTE  0 → 1 → 3', fontFamily: F.mono, fontWeight: 600, fontSize: S.small, fill: C.ink, letterSpacing: 0.01});
  const roCost = new Txt({text: '', fontFamily: F.mono, fontWeight: 700, fontSize: S.small, fill: C.ink, letterSpacing: 0.01});
  const roStops = new Txt({text: 'STOPS  0', fontFamily: F.mono, fontWeight: 600, fontSize: S.small, fill: C.ink, letterSpacing: 0.01});
  ro.add(roRoute); ro.add(roCost); ro.add(roStops);
  st.fg.add(ro);
  const cost = counter(roCost, v => `COST   ${Math.round(v)}`);
  const stopB = g.badge(1, 'STOP 1', C.acc);
  // Dense lines: schedule each beat at its own cue, in parallel, so one long animation never delays the next.
  yield* all(
    // p1: the four cities and n = 4 are in as the chapter card leaves (on screen when the voice starts), then the
    // input types in, entry 0 is decoded and every entry flies into the map
    when(CARD[1].outAt, all(g.popNodes(undefined, 0.1), delay(0.15, nBig.in()), delay(0.5, nSub.opacity(1, 0.4)))),
    when(cue('p1', 'each flight') - 0.2, dec.type(0.06, 0.22)),
    // FROM / TO / PRICE land together just before the voice says "from" (no label still fading in mid-line)
    when(cue('p1', 'from,') - 0.6, dec.annotate(0, ['FROM', 'TO', 'PRICE'], C.acc, 0.12)),
    when(voiceEnd('p1') - 0.5, all(
      delay(0.5, dec.clearNotes(0.3)),
      sequence(0.3, ...FLIGHTS.map(([u, v, w], i) => all(
        dec.mark(i, C.acc, 0.2),
        dec.send(st, i, g.edge(u, v).tag!, String(w), C.acc, 0.7),
        delay(0.25, g.drawEdge(u, v, 0.5, false)),
        delay(0.66, g.showTag(u, v, 0.3)),
      ))),
    )),
    when(voiceEnd('p1') + 2.4, dec.unmark()),
    // p2: where you start and where you must end
    when(cue('p2', 'zero') - 0.25, all(srcB.in(), g.state(0, 'active'))),
    when(cue('p2', 'three') - 0.25, all(dstB.in(), g.state(3, 'good'), delay(0.3, ex.in()))),
    // n = 4 -> k = 1 swaps in the gap before the line, so "k = 1" has landed when the voice says it
    when(L.p3.start - 0.3, all(nBig.out(), nSub.opacity(0, 0.2), delay(0.15, kBig.in(0.5, 0.05)))),
    when(cue('p3', 'one stop') - 0.25, all(kSub.opacity(1, 0.3), g.ring(1), delay(0.12, g.ring(2)),
      st.cam.to({x: 0, y: 10, zoom: 1.05}, 1.4))),
    when(L.p4.voiceAt - 0.15, all(
      ex.out(), delay(0.3, ro.opacity(1, 0.3)), kSub.opacity(0, 0.3), g.ring(2, C.acc, false), g.ring(1, C.acc, false),
      st.cam.to({x: 60, y: -10, zoom: 1.1}, 2.4),
      g.travel([0, 1, 3], C.acc, 0.8, function* (i) {
        if (i === 1) yield* all(cost(100, 0.45, easeOutCubic), stopB.in(), (function* () { roStops.text('STOPS  1'); yield* roStops.fill(C.accText, 0.2); })());
        if (i === 2) yield* cost(700, 0.6, easeOutCubic);
      }),
    )),
    when(cue('p4', 'the answer') - 0.25, all(
      g.light(0, 1, C.mint), g.light(1, 3, C.mint), g.state(3, 'good'), roCost.fill(textOf(C.mint), 0.3),
      burst(st.fx, '700!', {x: 630, y: 175, size: 80, rot: 8}),
      st.cam.to({x: 0, y: 0, zoom: 1.02}, 1.6),
    )),
  );

  // chapter card covers: clear the stage for brute force
  yield* at(CARD[2].coveredAt);
  dec.root.remove(); left.remove(); ro.remove(); ex.root.remove();
  g.removeAttachments();
  g.reset();
  st.cam.set({x: 0, y: 0, zoom: 1});
}

// ------------------------------------------------------------------------------------------ 2 brute force
function* bruteForce(st: Stage, g: Graph): ThreadGenerator {
  yield* g.place(-470, 30, 0.6);
  const fan = new Fan({levels: 5, branch: 3, width: 1000, step: 96, x: 370, y: -290, hot: 2});
  st.world.add(fan.root);
  const bo = bigO('n', 'k+1', {size: 112, fill: textOf(C.acc)});
  bo.position([370, 196]); // with boSub, clear of the caption scrim even under the 1.04 push (at y 312 the scrim took the label to 4.1:1)
  bo.opacity(0);
  bo.scale(0.8);
  st.world.add(bo);
  const boSub = label('EVERY ROUTE, AGAIN AND AGAIN', {x: 370, y: 274});
  boSub.opacity(0);
  st.world.add(boSub);
  yield* all(
    // the fan grows as the card leaves and is whole when the voice starts (the subject is on screen at the first word)
    when(CARD[2].outAt, fan.grow(0.08, 0.25)),
    when(CARD[2].clearAt - 0.4, all(
      st.cam.to({x: 90, y: 0, zoom: 1.04}, 2.6),
      sequence(0.4, g.light(0, 1, C.mint, 0.3), g.light(1, 3, C.mint, 0.3)),
    )),
    // the note goes above city 1: beside the crossed edge it covered city 0 and a weight tag
    when(cue('b1', 'tries'), g.reject([0, 1, 2, 3], '2 STOPS', C.rose, 0.6, 1)),
    when(cue('b1', 'exponential') - 0.2, all(bo.opacity(1, 0.3), bo.scale(1, 0.55, easeOutBack), delay(0.35, boSub.opacity(1, 0.3)))),
    when(cue('b1', 'exponential') + 0.3, fan.ringRepeats(3, [2, 5, 8, 11, 14, 17, 20], C.mint)),
  );
  yield* at(CARD[3].coveredAt);
  fan.root.remove(); bo.remove(); boSub.remove();
  g.removeAttachments();
  g.reset();
  st.cam.set({x: 0, y: 0, zoom: 1});
}

// ------------------------------------------------------------------------------------------ 3 intuition
function* intuition(st: Stage, g: Graph): ThreadGenerator {
  yield* g.place(-430, 110, 0.7);
  // q1: what is simpler to count than stops? (the card counts down the think pause, then resolves)
  const q1 = new QuestionCard({n: 1, text: 'What is simpler to count than stops?', y: -262});
  st.fg.add(q1.root);
  yield* all(
    when(CARD[3].clearAt - 0.3, q1.in()),
    when(cue('q1', 'stops') - 0.3, all(g.ring(1), delay(0.12, g.ring(2)))),
    q1.think('q1'),
  );

  // a1: flights, at most k + 1 of them
  // flight badges on the outer side of their edges (inside, they covered the middle edge's tag and city 3's arrow)
  const f1 = g.edgeBadge(0, 1, 'FLIGHT 1', C.acc, 0.5, -134), f2 = g.edgeBadge(1, 3, 'FLIGHT 2', C.acc, 0.5, -134);
  const fl = kinetic('at most *k + 1*\nflights', {size: 72, x: 440, y: 60});
  st.fg.add(fl.root);
  yield* at(L.a1.voiceAt - 0.2);
  yield* all(
    q1.out(), g.ring(1, C.acc, false), g.ring(2, C.acc, false),
    g.travel([0, 1, 3], C.acc, 0.45, function* (i) { yield* (i === 1 ? f1.in() : f2.in()); }),
    delay(0.35, fl.in()),
    st.cam.to({x: -120, y: 30, zoom: 1.06}, 1.8),
  );

  // q2: why read the old row while writing a new one?
  const q2 = new QuestionCard({n: 2, text: 'Why read the old row while writing a new one?', y: -262});
  st.fg.add(q2.root);
  const dist = new ArrayRow({label: 'dist', values: DRY[0], x: 500, y: 40, cell: 100});
  const next = new ArrayRow({label: 'next', values: ['', '', '', ''], x: 500, y: 190, cell: 100, index: false});
  st.fg.add(dist.root);
  st.fg.add(next.root);
  yield* all(
    when(L.q2.start, all(fl.out(), f1.out(), f2.out(), g.clear(0.35), q2.in(), st.cam.to({x: 0, y: 0, zoom: 1}, 1.2))),
    when(cue('q2', 'old row') - 0.3, dist.in()),
    when(cue('q2', 'new one') - 0.3, next.in()),
    q2.think('q2'),
  );

  // a2: one round adds exactly one flight (read dist, write next)
  const r0 = g.edgeBadge(0, 1, 'ROUND 0', C.mint, 0.5, -134);
  const one = kinetic('one round  =  ~one more flight~', {size: 64, y: -290});
  st.fg.add(one.root);
  yield* all(
    when(L.a2.voiceAt - 0.25, all(q2.out(), delay(0.2, one.in()), next.copyFrom(dist, 0.4, 0.04))),
    when(cue('a2', 'adds') - 0.2, all(g.fire(0, 1, C.mint), delay(0.3, g.light(0, 1, C.mint, 0.4)),
      delay(0.35, next.set(1, '100')), delay(0.2, r0.in()), g.state(1, 'good'))),
  );

  yield* at(CARD[4].coveredAt);
  q1.root.remove(); q2.root.remove(); fl.root.remove(); dist.root.remove(); next.root.remove(); one.root.remove();
  g.removeAttachments();
  g.reset();
  st.cam.set({x: 0, y: 0, zoom: 1});
}

// ------------------------------------------------------------------------------------------ 4 approaches
function* approaches(st: Stage, g: Graph): ThreadGenerator {
  yield* g.place(620, -238, 0.42);
  // a small decorative thumbnail here (the lines are about complexity, not prices): its weight tags would be
  // 30 px boxes crowding 45 px nodes, so they are hidden for this chapter and come back for the dry run
  g.showTags(false);
  const lad = new Ladder({rungs: RUNGS, y: 100, width: 1600, rowH: 104});
  st.fg.add(lad.root);
  yield* all(
    when(CARD[4].clearAt - 0.35, all(lad.show(0), st.cam.to({zoom: 1.05, y: 10}, L.x2.end - CARD[4].clearAt, linear))),
    when(cue('x1', 'memo') - 0.3, lad.show(1)),
    when(cue('x2', 'bellman') - 0.2, lad.show(2)),
    // k + 1 rounds: every edge relaxes once per round, shown on the subject
    when(cue('x2', 'rounds') - 0.1, sequence(0.9,
      sequence(0.08, ...FLIGHTS.map(([u, v]) => g.fire(u, v, C.acc, 0.4))),
      sequence(0.08, ...FLIGHTS.map(([u, v]) => g.fire(u, v, C.mint, 0.4))),
    )),
    when(cue('x2', 'order n space') - 0.25, lad.pick(2)),
  );

  yield* at(CARD[5].coveredAt);
  lad.root.remove();
  g.showTags(true);
  g.reset();
  st.cam.set({x: 0, y: 0, zoom: 1});
}

// ------------------------------------------------------------------------------------------ 5 code + dry run
function* codeAndDryRun(st: Stage, g: Graph): ThreadGenerator {
  // left: the code at 30 px (1188 px wide); right column (x 1324-1824): the map on top, the dry-run table below
  yield* g.place(614, -236, 0.5);
  // o1 (recap): the map comes back to the centre with the answer route; two lines to remember
  const l1 = kinetic('k stops  →  *k + 1* rounds.', {size: 76, y: -318});
  const l2 = kinetic('~Copy~ before you update.', {size: 76, y: -218});
  const foot = label('BELLMAN-FORD  ·  O(k·E) TIME  ·  O(n) SPACE', {y: -134});
  foot.opacity(0);
  st.fg.add(l1.root); st.fg.add(l2.root); st.fg.add(foot);
  const code = new CodePanel({code: CPP, y: -24, lineHeight: 37});
  code.root.x(-W / 2 + 96 + code.root.width() / 2);
  code.root.opacity(1);
  code.revealAll();
  st.fg.add(code.root);
  const tbl = new Table({x: 674, y: 46, cell: 78, rowGap: 20});
  st.fg.add(tbl.root);
  const rInit = tbl.addRow('init', DRY[0]);
  rInit.cells.forEach(c => { c.opacity(1); c.scale(1); });
  rInit.idx.forEach(t => t.opacity(1));
  rInit.head!.opacity(1);
  yield* code.focus(CL.init, 2, 0.01);
  const r0 = tbl.addRow('r = 0', ['', '', '', '']);
  const r1 = tbl.addRow('r = 1', ['', '', '', '']);

  yield* all(
    // round 0: copy, then 0 -> 1 relaxes to 100
    when(cue('c1', 'round zero') - 0.15, all(
      code.focus(CL.loop, 2), r0.in(0.04),
      delay(0.35, r0.copyFrom(rInit, 0.3, 0.03)),
      delay(0.9, all(code.focus(CL.relax, 2), g.fire(0, 1, C.mint), delay(0.35, r0.set(1, '100')))),
    )),
    // round 1: copy, then 1 -> 2 gives 200 and 1 -> 3 gives 700
    when(cue('c1', 'round one') - 0.15, all(
      code.focus(CL.loop, 2), r1.in(0.04),
      delay(0.35, r1.copyFrom(r0, 0.3, 0.03)),
      delay(0.9, all(code.focus(CL.relax, 2), g.fire(1, 2, C.mint), delay(0.35, r1.set(2, '200')))),
    )),
    when(cue('c1', 'seven hundred') - 0.45, sequence(0.7,
      all(g.fire(1, 3, C.mint), delay(0.35, r1.set(3, '700'))),
      // the burst sits in the empty lower right of the code panel, beside the return statement it answers
      all(code.focus(CL.ret), g.state(3, 'good'), burst(st.fx, '700!', {x: 180, y: 195, size: 56, rot: -6, rays: false})),
    )),
    when(L.o1.start - 0.1, all(
      code.out(), tbl.root.opacity(0, 0.3),
      g.place(0, 120, 0.74, 1.3), g.state(3, 'idle'),
      st.cam.to({zoom: 1.08}, 1.3),
      delay(0.5, l1.in()),
      delay(1.3, all(g.light(0, 1, C.mint, 0.45), delay(0.3, g.light(1, 3, C.mint, 0.45)), g.state(3, 'good'))),
    )),
    when(cue('o1', 'copy') - 0.55, all(l2.in(0.5, 0.05), delay(0.3, foot.opacity(1, 0.4)), st.cam.to({zoom: 1.0}, 3.0))),
  );
}
