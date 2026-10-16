// Chapter 0: title card (line i1).
import {TitleCard, voiceEnd, waitUntilLineStart, waitUntilTime} from '../kit';
import type {Film} from './film-context';

export function* intro(f: Film) {
  const title = new TitleCard({
    kicker: 'LEETCODE 787  ·  GRAPHS  ·  MEDIUM',
    lines: ['Cheapest Flights', 'Within K Stops'],
    accent: 'K',
  });
  f.w.hud.add(title.node);
  f.cam.set({focus: f.g.center(), anchor: [0, 66], zoom: 0.86}); // chapter 1's framing: under the input panel

  yield* waitUntilLineStart('i1', -0.1);
  yield title.in(0.7, 2.2);
  // leave at the last word; gone before the chapter 1 card moves in (last word + CLEAR)
  yield* waitUntilTime(voiceEnd('i1'));
  yield* title.out(0.28);
}
