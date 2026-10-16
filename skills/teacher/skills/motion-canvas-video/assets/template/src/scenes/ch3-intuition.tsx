// Chapter 3: intuition through timed questions (q1, a1, q2, a2). The subject stays on the left; the
// question card sits on the right with a countdown ring for each think pause.
import {all, delay, easeInOutCubic} from '@motion-canvas/core';
import {
  C,
  Chip,
  QuestionCard,
  Table,
  burst,
  cardOut,
  chapter,
  line,
  vanish,
  waitUntilLine,
  voiceEnd,
  waitUntilThink,
  waitUntilTime,
} from '../kit';
import type {Film} from './film-context';

export function* intuition(f: Film) {
  const {w, g, cam} = f;
  yield* waitUntilTime(chapter(3).start - 0.6);
  yield cam.frame(g.center(), [-500, 0], 0.84, 1.2);

  // the card sits level with the graph for q1, then rises at q2 to make room for the table under it
  const q = new QuestionCard({position: [430, 0], width: 840});
  w.hud.add(q.node);

  // q1: the route has one stop; is there something simpler to count?
  // the card comes in as the chapter card leaves, so it is up when the voice asks
  yield* waitUntilTime(cardOut(3));
  yield q.ask(1, 'What is simpler to count than stops?');
  yield* waitUntilLine('q1');
  const r = g.route([0, 1, 3], C.accent);
  const stop = g.tag(1, 'stop', C.gold, 'top');
  yield* r.fly(1.4);
  yield all(stop.show(), g.highlightNode(1, C.gold));
  yield* waitUntilThink('q1');
  yield* q.countdown(line('q1').think);

  // a1: count flights instead
  yield* waitUntilLine('a1');
  const f1 = new Chip('flight 1', C.good, {position: g.along(0, 1).add([-120, -120]), fontSize: g.tagFont});
  const f2 = new Chip('flight 2', C.good, {position: g.along(1, 3).add([120, -120]), fontSize: g.tagFont});
  g.tokenLayer.add([f1.node, f2.node]);
  yield all(r.recolor(C.good), g.resetNode(1), stop.hide(), f1.show(), delay(0.35, f2.show()), q.answer('Flights: at most k + 1 = 2'));

  // q2: read the old row while writing a new one?
  yield* waitUntilLine('q2');
  yield all(r.fade(0.4), f1.hide(), f2.hide(), q.node.y(-170, 0.6, easeInOutCubic));
  yield q.ask(2, 'Why read the old row while writing a new one?');
  const t = new Table({
    position: [430, 215],
    cols: ['0', '1', '2', '3'],
    rows: [
      {label: 'OLD', values: ['0', '∞', '∞', '∞']},
      {label: 'NEW', values: ['0', '∞', '∞', '∞']},
    ],
    headLabel: 'CITY',
  });
  w.hud.add(t.node);
  yield delay(0.5, all(t.showHeader(), t.showRow(0), g.setValue(0, '0', C.good)));
  yield* waitUntilThink('q2');
  yield* q.countdown(line('q2').think);

  // a2: one round = one more flight. The answer lands with the voice (it is fully in before the line's
  // midpoint); the new row is copied and relaxed alongside it.
  yield* waitUntilLine('a2');
  yield all(
    q.answer('Read old, write new: one round = one more flight', C.good, 0.35),
    t.copyRow(0, 1, 0.5),
    delay(0.5, all(g.fire(0, 1, C.good, 0.5), t.flash(0, 0, C.cool, 0.2))),
    delay(0.9, all(t.set(1, 1, '100', C.good), g.setValue(1, '100', C.good))),
    delay(1.0, burst(w.top, '+1 FLIGHT', {at: [-240, -280], size: 80, hold: 0.8, rotation: -6})),
  );

  // cleared within 0.25 s of the last word (the chapter 4 card moves in after that)
  yield* waitUntilTime(voiceEnd('a2'));
  // resetAll: a2's fire left the 0 -> 1 edge mint into chapter 4
  yield all(q.hide(0.25), t.hide(0.25), g.setValue(0, '', C.ink, 0.25), g.setValue(1, '', C.ink, 0.25), g.resetAll(0.25), delay(0.3, all(vanish(q.node, 0), vanish(t.node, 0))));
}
