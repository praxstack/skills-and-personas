// The director: what the persistent subject and the camera do at every frame, written as cues keyed to line
// ids. The graph is never re-created per scene; it moves (placeAt), lights up (graphAt) and the camera
// pushes in and pulls back (cameraAt). Read this file top to bottom alongside script.json.
import {C} from '../kit/tokens';
import {camera, CAM_HOME, type Cam} from '../kit/Camera';
import {GraphState, nodeWorld, type Place} from '../kit/Graph';
import {bump, ease, EASE, pop, span, track} from '../lib/motion';
import {chapterStart, f, fEnd, fPhrase, fStart, sec} from '../lib/timing';
import {gapMove, subjectShown} from '../kit/Chapter';
import {MAP, PLACE, ENTRY_EDGE} from './data';

const NODES = ['0', '1', '2', '3'];
const ALL_EDGES = MAP.edges.map((e) => e.id);
const ENTRIES = ['f0', 'f1', 'f2', 'f3', 'f4'];

// ---------------------------------------------------------------- shared beats (other scenes use these too)
export const BEAT = {
  // decode: entries start flying when the voice says "Each flight"; one every 0.28 s
  entryFly: (i: number) => fPhrase('p1', 'Each flight', 0.1 + i * 0.28),
  entryDur: sec(0.75),
  labelLead: -0.25, // seconds: a word's label pops this far ahead of the word, so it has landed when it is heard
  srcAt: () => fPhrase('p2', 'city zero', -0.1),
  dstAt: () => fPhrase('p2', 'city three', -0.1),
  // p4: the plane flies 0 -> 1 -> 3 while the voice lists the cities; it lands on 1 and on 3 at these frames
  // (routeAt eases in-out over 2.35 legs: 47% and 67% of routeDur), and the fare total lands on "seven hundred"
  routeStart: () => f('p4', -0.05),
  routeDur: sec(1.7),
  leg1: () => BEAT.routeStart() + sec(0.8),
  leg2: () => BEAT.routeStart() + sec(1.15),
  totalAt: () => Math.max(BEAT.leg2() + sec(0.15), fPhrase('p4', 'seven hundred', -0.1)),
  answerAt: () => fPhrase('p4', 'The answer'),
  dryR0: () => fPhrase('c1', 'Round zero'),
  dryR1: () => fPhrase('c1', 'Round one'),
  dry700: () => fPhrase('c1', 'seven hundred', -0.2),
};

// ---------------------------------------------------------------- where the graph sits
// Between chapters the subject fades out at the last word, moves while invisible under the sting (gapMove) and
// fades back in at its new place after the band has left (subjectShown), so the band never covers it.
export const placeAt = (fr: number): Place => {
  const p = track(fr, [
    [0, PLACE.hidden],
    [fStart('p1'), PLACE.decode, sec(0.6)],
    [f('p3', 0.3), PLACE.center, sec(0.9)],
    gapMove(2, PLACE.left),
    gapMove(3, PLACE.question),
    [fStart('q2'), PLACE.question2, sec(0.9)],
    gapMove(4, PLACE.ladder), // settled before the ladder fades in, so it never crosses a rung
    gapMove(5, PLACE.code),
    [fStart('o1'), PLACE.outro, sec(1.1)],
  ], sec(0.9), EASE.inOut);
  return {...p, o: p.o * subjectShown(fr)};
};

// ---------------------------------------------------------------- the camera
export const cameraAt = (fr: number): Cam => {
  const n3 = nodeWorld(MAP, PLACE.center, '3');
  return camera(fr, [
    [0, {...CAM_HOME, z: 1.04}],
    [fStart('p1'), {x: 960, y: 540, z: 0.98}, sec(1.2)],
    [f('p2'), {x: 975, y: 535, z: 1.02}, sec(2.0)],
    [f('p3'), {x: 960, y: 540, z: 1.0}, sec(1.0)],
    [BEAT.answerAt() - sec(0.3), {x: 930, y: n3.y - 5, z: 1.1}, sec(0.9)], // push in on the answer (HUD receipt and k chip stay put)
    [fEnd('p4', -0.55), CAM_HOME, sec(0.7)],
    [f('b1', 1.0), {x: 1000, y: 520, z: 1.05}, sec(1.4)],
    [fEnd('b1', -0.4), CAM_HOME, sec(0.6)],
    [f('a1'), {x: 960, y: 610, z: 1.1}, sec(0.9)],
    [fEnd('a1', -0.4), CAM_HOME, sec(0.6)],
    [f('a2'), {x: 1040, y: 580, z: 1.05}, sec(0.9)], // keeps node 0 (left) and the 'no chaining' note (right) 96 px in
    [fEnd('a2', -0.4), CAM_HOME, sec(0.6)],
    [fPhrase('x2', 'order n space', 0.3), {x: 960, y: 430, z: 1.04}, sec(0.9)], // the ladder and the map span the frame: push gently, centred
    [fEnd('x2', -0.4), CAM_HOME, sec(0.6)],
    [fStart('o1'), {x: 960, y: 540, z: 1.03}, sec(0.8)], // the recap card reaches x 1820: a gentle push keeps its text inside
    [f('o1', 0.8), {x: 960, y: 540, z: 0.98}, sec(4.0)],
  ]);
};

// ---------------------------------------------------------------- the graph, cue by cue
export const graphAt = (fr: number): GraphState => {
  const g = new GraphState(MAP);

  // p1: the four cities pop in as the chapter sting leaves (the subject is on screen when the voice says "Four
  // cities"); then each flight entry flies in and draws its edge
  g.nodes(NODES, (_, i) => ({show: pop(fr, fStart('p1', 0.3 + i * 0.13))}));
  ENTRIES.forEach((id, i) => {
    const at = BEAT.entryFly(i);
    const e = g.edge(ENTRY_EDGE[id]);
    e.draw = ease(fr, at + BEAT.entryDur * 0.25, BEAT.entryDur * 0.8, EASE.inOut);
    e.tag = pop(fr, at + BEAT.entryDur);
  });
  // the first entry is the worked example: its edge glows while the notes explain from/to/price
  g.fire('e01', fr, BEAT.entryFly(0) + BEAT.entryDur, sec(0.5), C.amber);

  // p2: start and end
  const endDecode = fEnd('p4', -0.45); // the p1-p4 marks are gone when chapter 1 ends (the sting runs in the gap)
  g.ring('0', C.cyan, ease(fr, BEAT.srcAt() + sec(0.5), 8) * (1 - ease(fr, endDecode, 10)));
  g.badge('0', 'START', C.cyan, pop(fr, BEAT.srcAt() + sec(0.5)) * (1 - ease(fr, endDecode, 10)));
  g.ring('3', C.mint, ease(fr, BEAT.dstAt() + sec(0.5), 8) * (1 - ease(fr, endDecode, 10)));
  g.badge('3', 'END', C.mint, pop(fr, BEAT.dstAt() + sec(0.5)) * (1 - ease(fr, endDecode, 10)));
  g.pulse('0', fr, BEAT.srcAt() + sec(0.5), C.cyan).pulse('3', fr, BEAT.dstAt() + sec(0.5), C.mint);

  // p3: "a stop is a city you land in on the way": cities 1 and 2 are the possible stops
  const stopQ = fPhrase('p3', 'one stop', -0.3);
  g.ring('1', C.amber, bump(fr, stopQ, sec(1.1), 6, 10) * 0.8).ring('2', C.amber, bump(fr, stopQ + 4, sec(1.1), 6, 10) * 0.8);
  g.badge('1', 'STOP?', C.amber, bump(fr, stopQ, sec(1.1), 6, 10)).badge('2', 'STOP?', C.amber, bump(fr, stopQ + 4, sec(1.1), 6, 10));

  // p4: fly 0 -> 1 -> 3, then it becomes the answer
  const r0 = BEAT.routeStart();
  const answer = BEAT.answerAt();
  const keepRoute = 1 - ease(fr, endDecode, 12);
  g.routeAt(fr, ['e01', 'e13'], r0, BEAT.routeDur, C.accent, {token: 'plane', o: keepRoute});
  g.routeAt(fr, ['e01', 'e13'], answer - sec(0.1), sec(0.6), C.mint, {o: keepRoute}); // re-drawn in the answer colour
  g.badge('1', 'STOP', C.amber, pop(fr, BEAT.leg1() - sec(0.05)) * keepRoute);
  g.value('3', '700', C.mint, pop(fr, answer), ease(fr, answer, 6) * keepRoute);
  g.pulse('3', fr, answer, C.mint);

  // b1: brute force walks every route on the map in sync with the tree (see Brute.tsx)
  const b = f('b1');
  const bOut = 1 - ease(fr, fEnd('b1', -0.3), 10);
  if (fr >= fStart('b1') && fr < fEnd('b1')) {
    g.routeAt(fr, ['e01'], fStart('b1', 0.6), sec(0.4), C.amber, {o: bOut}); // the first flight (0 -> 1) as the sting leaves, with the tree's first level
    g.routeAt(fr, ['e01', 'e13'], b + sec(0.6), sec(0.6), C.mint, {o: bOut});
    g.routeAt(fr, ['e01', 'e12', 'e23'], b + sec(1.0), sec(0.7), C.rose, {o: bOut * (1 - 0.6 * ease(fr, b + sec(1.6), 10))});
    g.strike('e23', pop(fr, b + sec(1.5)) * bOut);
  }

  // q1/a1: the 700 route with its stop, then the answer counts flights instead
  const q1 = f('q1');
  const a1 = f('a1');
  const qOut = 1 - ease(fr, fEnd('a1', -0.3), 10);
  if (fr >= q1 - sec(0.5) && fr < fEnd('a1')) {
    g.route(['e01', 'e13'], 2 * ease(fr, q1, sec(0.8)), C.amber, {o: qOut});
    g.badge('1', 'STOP', C.amber, ease(fr, q1 + sec(0.6), 8) * (1 - ease(fr, a1, 8)));
    g.fire('e01', fr, a1 + sec(0.2), sec(0.45), C.mint).fire('e13', fr, a1 + sec(0.7), sec(0.45), C.mint);
  }

  // q2/a2: one round, read old / write new: 0 -> 1 relaxes, 1 -> 2 cannot chain in the same round
  const a2 = f('a2');
  if (fr >= fStart('q2') && fr < fEnd('a2')) {
    const out = 1 - ease(fr, fEnd('a2', -0.3), 10);
    g.ring('0', C.cyan, ease(fr, f('q2', 0.6), 10) * out);
    g.fire('e01', fr, a2 + sec(0.1), sec(0.5), C.mint);
    g.value('1', '100', C.mint, pop(fr, a2 + sec(0.6)), ease(fr, a2 + sec(0.6), 6) * out);
    g.strike('e12', pop(fr, a2 + sec(1.0)) * out);
  }

  // x2: Bellman-Ford = k + 1 rounds; every flight relaxes once per round
  const x2 = f('x2');
  if (fr >= x2 && fr < fEnd('x2')) {
    [0, 1].forEach((round) => ALL_EDGES.forEach((id, i) => g.fire(id, fr, x2 + sec(0.5 + round * 1.6 + i * 0.16), sec(0.4), round ? C.mint : C.amber)));
  }

  // c1: the dry run writes dist onto the map as the table fills (see Code.tsx)
  const R0 = BEAT.dryR0();
  const R1 = BEAT.dryR1();
  const v700 = BEAT.dry700();
  const dOut = 1 - ease(fr, fStart('o1'), 10);
  if (fr >= f('c1', -0.3) && fr < fStart('o1') + sec(0.5)) {
    g.value('0', '0', C.cyan, pop(fr, f('c1', 0.2)), ease(fr, f('c1', 0.2), 6) * dOut);
    g.fire('e01', fr, R0 + sec(0.2), sec(0.5), C.mint);
    g.value('1', '100', C.mint, pop(fr, R0 + sec(0.7)), ease(fr, R0 + sec(0.7), 6) * dOut);
    g.fire('e12', fr, R1 - sec(0.2), sec(0.4), C.mint); // lands with the table cell (Code.tsx), well before "seven hundred"
    g.value('2', '200', C.mint, pop(fr, R1 + sec(0.2)), ease(fr, R1 + sec(0.2), 6) * dOut);
    g.fire('e13', fr, v700 - sec(0.5), sec(0.45), C.mint);
    g.value('3', '700', C.mint, pop(fr, v700), ease(fr, v700, 6) * dOut);
    g.strike('e23', pop(fr, R1 + sec(1.0)) * dOut);
  }

  // o1: the answer route glows while the recap plays
  const o1 = fStart('o1');
  if (fr >= o1) {
    g.route(['e01', 'e13'], 2.0 * ease(fr, o1 + sec(0.6), sec(1.0)), C.mint, {o: span(fr, o1, fEnd('o1') + 30)});
    g.value('3', '700', C.mint, pop(fr, o1 + sec(1.5)), ease(fr, o1 + sec(1.5), 8));
  }

  return g;
};
