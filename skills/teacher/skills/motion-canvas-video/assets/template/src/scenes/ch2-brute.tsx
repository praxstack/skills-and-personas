// Chapter 2: brute force (line b1). The graph slides left; a fan of routes explodes on the right.
import {all, delay, sequence} from '@motion-canvas/core';
import {BranchFan, C, Chip, Counter, chapter, stamp, vanish, voiceEnd, waitUntilCue, waitUntilLine, waitUntilTime} from '../kit';
import type {Film} from './film-context';

export function* brute(f: Film) {
  const {w, g, cam} = f;
  yield* waitUntilTime(chapter(2).start - 0.6);
  yield cam.frame(g.center(), [-520, 30], 0.8, 1.2); // zoom >= 0.8 keeps the weights >= 28 px

  const fan = new BranchFan({position: [430, 30], branch: 3, depth: 3, width: 800, height: 390, rootLabel: '0'});
  w.hud.add(fan.node);
  const routes = new Counter({label: 'routes tried', position: [430, -300]});
  w.hud.add(routes.node);
  const big = new Chip('O(n^(k+1)) time', C.bad, {position: [430, 300], fontSize: 34, mono: true});
  w.hud.add(big.node);

  yield* waitUntilLine('b1');
  // every route lights up on the subject while the fan grows
  yield sequence(0.3, g.fire(0, 1, C.accent, 0.4), g.fire(1, 2, C.accent, 0.4), g.fire(1, 3, C.accent, 0.4), g.fire(2, 3, C.accent, 0.4), g.fire(2, 0, C.accent, 0.4));
  yield all(routes.show(), fan.grow(1.6, n => routes.to(n, 0.3)));
  // the stamp lands (0.28 s) just before the word is spoken, so it is fully in when the word is heard
  yield* waitUntilCue('b1', 'Exponential', -0.35);
  routes.color(C.bad);
  const st = stamp(w.top, 'EXPONENTIAL!', {at: [430, 160], color: C.bad, fontSize: 64});
  yield all(st.slam(), cam.shake(0.7), delay(0.15, big.show()));

  // cleared within 0.25 s of the last word (the chapter 3 card moves in after that)
  yield* waitUntilTime(voiceEnd('b1'));
  yield all(fan.hide(0.25), routes.hide(0.25), big.hide(0.25), vanish(st.node, 0.25), g.resetAll(0.25), delay(0.3, all(vanish(fan.node, 0), vanish(routes.node, 0))));
}
