// Chapter 4: every approach on a complexity ladder (x1, x2). The subject shrinks to the top right corner
// (its small print hidden) and still reacts: one round of Bellman-Ford relaxes every edge.
import {all, delay, sequence} from '@motion-canvas/core';
import {C, Ladder, cardOut, chapter, vanish, voiceEnd, waitUntilCue, waitUntilLine, waitUntilTime} from '../kit';
import {EDGES, RUNGS} from './data';
import type {Film} from './film-context';

export function* approaches(f: Film) {
  const {w, g, cam} = f;
  yield* waitUntilTime(chapter(4).start - 0.6);
  yield all(cam.frame(g.center(), [650, -255], 0.5, 1.2), g.labels(false, 0.4));

  const lad = new Ladder({position: [40, 110], rungs: RUNGS, width: 1540, rungH: 116});
  w.hud.add(lad.node);

  // the brute-force rung (the last chapter's recap) comes in as the chapter card leaves; x1 adds the next one
  yield* waitUntilTime(cardOut(4));
  yield lad.show(0, 0.45);
  yield* waitUntilLine('x1');
  yield lad.show(1);

  yield* waitUntilLine('x2');
  yield lad.show(2);
  // k + 1 rounds: each round relaxes every edge once
  yield delay(0.5, sequence(0.14, ...EDGES.map(e => g.fire(e.from, e.to, C.good, 0.45, false))));
  yield* waitUntilCue('x2', 'order n space', -0.2);
  yield lad.pick(2);

  // cleared within 0.25 s of the last word (the chapter 5 card moves in after that)
  yield* waitUntilTime(voiceEnd('x2'));
  yield all(lad.hide(0.25), g.resetAll(0.25), delay(0.3, vanish(lad.node, 0)));
}
