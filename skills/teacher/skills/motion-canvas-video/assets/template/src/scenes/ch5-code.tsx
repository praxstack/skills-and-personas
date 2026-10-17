// Chapter 5: the C++ and a dry run on Example 1 (c1, o1). Code on the left with the active line
// highlighted; the subject top right fires the edge that each table cell comes from.
import {all, chain, delay} from '@motion-canvas/core';
import {C, Chip, CodePanel, Table, burst, cardOut, chapter, waitUntilCue, waitUntilLine, waitUntilTime} from '../kit';
import {CODE, CPP} from './data';
import type {Film} from './film-context';

export function* codeAndDryRun(f: Film) {
  const {w, g, cam} = f;
  yield* waitUntilTime(chapter(5).start - 0.6);
  yield cam.frame(g.center(), [562, -217], 0.6, 1.2);

  // 17 lines at 30 px (the bar's code size): 1090 x 706 fills the left of the content area
  const cp = new CodePanel({position: [-319, -27], width: 1090, height: 706, title: 'solution.cpp', code: CPP, fontSize: 30});
  w.hud.add(cp.node);
  const t = new Table({
    position: [562, 190],
    cols: ['0', '1', '2', '3'],
    rows: [{label: 'START', values: ['0', '∞', '∞', '∞']}, {label: 'ROUND 0'}, {label: 'ROUND 1'}],
    cellW: 100,
    cellH: 60,
    gap: 10,
    labelW: 150,
    headLabel: 'dist',
  });
  w.hud.add(t.node);
  // the panel (code already in it) fades in as the chapter card leaves, with the subject
  yield* cp.reveal(Infinity, 0);
  yield* waitUntilTime(cardOut(5));
  yield cp.show(0.35);

  // c1: start row, round 0, round 1 (each cell lands as its edge fires on the graph). The start row pops in
  // quickly so it has settled before round 0 slides out of it.
  yield* waitUntilLine('c1');
  yield all(cp.focus(CODE.init), t.showHeader(0.3), t.showRow(0, 0.05, 0.3), g.highlightNode(0, C.good));

  yield* waitUntilCue('c1', 'Round zero');
  yield chain(
    all(cp.focus(CODE.copy, 0.3), t.copyRow(0, 1, 0.45)),
    all(cp.focus(CODE.relax, 0.3), g.fire(0, 1, C.good, 0.45), delay(0.35, all(t.set(1, 1, '100'), g.highlightNode(1, C.good)))),
  );

  yield* waitUntilCue('c1', 'Round one', -0.25);
  yield chain(
    all(cp.focus(CODE.copy, 0.3), t.copyRow(1, 2, 0.45)),
    all(cp.focus(CODE.relax, 0.3), g.fire(1, 2, C.good, 0.4), delay(0.3, all(t.set(2, 2, '200'), g.highlightNode(2, C.good)))),
    all(g.fire(1, 3, C.good, 0.4), delay(0.3, all(t.set(2, 3, '700'), g.highlightNode(3, C.good)))),
    // 2 -> 3 is skipped: the old row still has dist[2] = ∞
    all(g.fire(2, 3, C.bad, 0.4, false), t.flash(1, 2, C.bad, 0.3)),
  );

  // o1: the recap
  yield* waitUntilLine('o1');
  const rounds = new Chip('k + 1 = 2 rounds', C.gold, {position: [562, 8], fontSize: 30, mono: true});
  w.hud.add(rounds.node);
  const r = g.route([0, 1, 3], C.good, 'none');
  yield all(cp.focus(CODE.loop), rounds.show(), t.mark(2, 3, C.good), r.fly(0.8));
  yield* waitUntilCue('o1', 'Copy before', -0.15);
  // the burst sits in the empty top-right corner of the code panel (right of the short lines 0-5), over no text
  yield all(cp.focus(CODE.copy), burst(w.top, 'COPY FIRST!', {at: [70, -205], size: 82, hold: 1.2, rotation: -6}));
}
