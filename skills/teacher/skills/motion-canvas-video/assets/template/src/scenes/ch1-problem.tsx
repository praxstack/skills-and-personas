// Chapter 1: decode the problem (lines p1 to p4). The graph is built from the input text, entry by entry.
//
// Pattern used in every chapter: wait for a cue with `yield* waitUntil...`, then start that beat's
// animations without blocking (`yield all(...)` runs them alongside), so a long animation can never push
// the next cue late. Use `yield*` only when the next step must wait for the animation to finish.
import {all, chain, delay, sequence} from '@motion-canvas/core';
import {C, Chip, Counter, burst, cardOut, floatUp, pointIn, vanish, voiceEnd, waitUntilCue, waitUntilLine, waitUntilTime} from '../kit';
import {EDGES} from './data';
import type {Film} from './film-context';

export function* problem(f: Film) {
  const {w, g, cam, input} = f;

  // p1: the whole input and four cities come in as the chapter card leaves (on screen when "Four cities" is
  // said); each flight entry flies from the input text onto its arrow
  yield* waitUntilTime(cardOut(1));
  yield all(input.showRow(1), input.showRow(0), delay(0.2, input.mark(1, 0, C.accent)), g.popNodes(0.12, 0.5));
  yield* waitUntilCue('p1', 'Each flight', -0.15);
  // 0.32 s apart: at most two flights are in the air at once, and they never cross
  yield sequence(
    0.32,
    // the arrow draws under the flight; its pill pops (0.25 s into drawEdge, 0.33 s into the 0.5 s flight)
    // while the entry fades onto it, so the number hands over from text to pill without a gap
    ...EDGES.map((e, i) => all(input.fly(0, i, w.top, g.edge(e.from, e.to).pill, 0.5), delay(0.08, g.drawEdge(e.from, e.to, 0.45)))),
  );

  // p2: src and dst
  yield* waitUntilLine('p2');
  const src = g.tag(0, 'src', C.cool, 'top');
  const dst = g.tag(3, 'dst', C.accent, 'top');
  yield all(input.mark(1, 0, C.ink), input.mark(1, 1, C.cool), g.highlightNode(0, C.cool), src.show(), g.ripple(0, C.cool));
  yield* waitUntilCue('p2', 'end at', -0.1);
  yield all(input.mark(1, 2, C.accent), g.highlightNode(3, C.accent), dst.show(), g.ripple(3, C.accent));

  // p3: k = 1, one stop allowed: the plane lands at city 1 (a stop); the cheaper 0 -> 1 -> 2 -> 3 makes
  // two stops and is rejected
  yield* waitUntilLine('p3');
  const budget = new Chip('at most 1 stop', C.gold, {position: [-640, 70], fontSize: 32});
  w.hud.add(budget.node);
  const hop = g.route([0, 1], C.gold);
  const stop = g.tag(1, 'stop', C.gold, 'top');
  const illegal = g.route([0, 1, 2, 3], C.accent, 'dot');
  yield all(input.mark(1, 3, C.gold), budget.show());
  yield chain(
    hop.fly(0.6, undefined, true),
    all(stop.show(), g.highlightNode(1, C.gold), illegal.fly(0.8)),
    illegal.reject(2, '2 stops > k'),
  );

  // p4: fly 0 -> 1 -> 3, the cost ticks up, 700 lands
  yield* waitUntilLine('p4');
  const cost = new Counter({label: 'cost', position: [650, 120]});
  w.hud.add(cost.node);
  const answer = new Chip('answer = 700', C.good, {position: [650, 250], fontSize: 32, mono: true});
  w.hud.add(answer.node);
  const route = g.route([0, 1, 3], C.good);
  yield all(hop.fade(0.3), illegal.fade(0.3), cost.show(), cam.to({anchor: [-40, 100], zoom: 0.92}, 2.2));
  yield route.fly(2.2, i =>
    i === 1
      ? all(cost.to(100, 0.5), floatUp(w.top, '+100', pointIn(w.top, g.root, g.along(0, 1).add([0, -40]))))
      : all(cost.to(700, 0.6), floatUp(w.top, '+600', pointIn(w.top, g.root, g.along(1, 3).add([40, -40])))),
  );
  yield* waitUntilCue('p4', 'The answer', -0.1);
  cost.color(C.good);
  yield all(burst(w.top, '700!', {at: [610, -95], size: 118, hold: 1.0}), answer.show());

  // clear the chapter's extras while the next chapter card is up
  // cleared within 0.25 s of the last word, so the chapter card moves in over an empty subject
  yield* waitUntilTime(voiceEnd('p4'));
  yield all(
    input.hide(0.25),
    budget.hide(0.25),
    stop.hide(0.25),
    src.hide(0.25),
    dst.hide(0.25),
    answer.hide(0.25),
    cost.hide(0.25),
    route.fade(0.25),
    g.resetAll(0.25),
    delay(0.3, all(vanish(cost.node, 0), vanish(input.node, 0))),
  );
}
