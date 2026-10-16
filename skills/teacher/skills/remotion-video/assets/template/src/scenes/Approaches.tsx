// Chapter 4 (every approach): the complexity ladder climbs one rung per approach; the map beside it shows
// what Bellman-Ford does (every flight relaxes once per round, k + 1 rounds; see director.ts).
import React from 'react';
import {Span, useF} from '../lib/span';
import {chapterStart, f, fEnd, fPhrase, sec} from '../lib/timing';
import {clamp01, ease, steps} from '../lib/motion';
import {C} from '../kit/tokens';
import {Chip} from '../kit/Panel';
import {Ladder} from '../kit/Ladder';
import {PLACE} from './data';
import {BEAT} from './director';

// x1's rung (the chapter's first line) lands just before its words (BEAT.labelLead): the voice starts on a full stage
const LadderScene: React.FC = () => {
  const fr = useF();
  const o = ease(fr, chapterStart(4), 12) * (1 - ease(fr, fEnd('x2', -0.3), 10)); // after the chapter sting, never under it
  return (
    <Ladder fr={fr} x={96} y={226} w={1080} o={o} rungs={[
      {name: 'Brute-force DFS', time: 'O(n^(k+1))', space: 'O(k)', cost: 1, color: C.rose, at: chapterStart(4), note: 'every route'},
      {name: 'DFS + memo', time: 'O(k·E)', space: 'O(n·k)', cost: 0.36, color: C.amber, at: f('x1', BEAT.labelLead), note: 'each (city, flights) once'},
      {name: 'Bellman-Ford, k + 1 rounds', time: 'O(k·E)', space: 'O(n)', cost: 0.3, color: C.mint, at: f('x2', 0.1), note: 'one row, k + 1 passes'},
    ]} focus={[[chapterStart(4), 0], [f('x1'), 1], [f('x2'), 2]]} pick={{i: 2, at: fPhrase('x2', 'order n space', 0.3)}} />
  );
};

/** round counter above the map while the relaxation waves run */
const Rounds: React.FC = () => {
  const fr = useF();
  const x2 = f('x2');
  const r = steps(fr, [[x2 + sec(0.4), 'round 1 of 2'], [x2 + sec(2.0), 'round 2 of 2']]);
  const o = ease(fr, x2 + sec(0.3), 10) * (1 - ease(fr, fEnd('x2', -0.3), 10));
  if (!r.v) return null;
  return (
    <div style={{position: 'absolute', left: PLACE.ladder.x, top: PLACE.ladder.y - 230, transform: `translate(-50%, 0) scale(${0.85 + 0.15 * r.pop})`, opacity: o * clamp01(r.pop + 0.5)}}>
      <Chip color={r.i === 0 ? C.amber : C.mint} size={32}>{r.v}</Chip>
    </div>
  );
};

export const ApproachesWorld: React.FC = () => (
  <>
    <Span from={chapterStart(4) - sec(0.4)} to={fEnd('x2')} name="ladder">
      <LadderScene />
    </Span>
    <Span from={f('x2')} to={fEnd('x2')} name="rounds">
      <Rounds />
    </Span>
  </>
);
