// Chapter 2 (brute force): the recursion tree grows next to the map; routes flash on the map in sync
// (director.ts), branches past k + 1 flights are cut, the blow-up gets its O(...) and a burst.
import React from 'react';
import {Span, useF} from '../lib/span';
import {f, fEnd, fPhrase, fStart, sec} from '../lib/timing';
import {clamp01, ease, pop} from '../lib/motion';
import {C, mark} from '../kit/tokens';
import {Chip, BigO} from '../kit/Panel';
import {Tree, treeLayout, type TNode} from '../kit/Tree';
import {Burst} from '../kit/Burst';

const TX = 1010;
const TY = 196;
const TW = 760;
const LH = 140; // four levels end at y 654; the ghost fan below them ends at y 756, the O(...) chip sits under it

const nodes = (): TNode[] => {
  const b = f('b1');
  return [
    // the root and its only flight (0 -> 1) arrive with the map as the sting leaves; the tree branches on the voice
    {id: 'r', label: '0', at: fStart('b1', 0.4)},
    {id: 'a', parent: 'r', label: '1', sub: '100', at: fStart('b1', 0.65)},
    {id: 'b', parent: 'a', label: '2', sub: '200', at: b + sec(0.65)},
    {id: 'c', parent: 'a', label: '3', sub: '700', at: b + sec(0.65), tone: 'win', toneAt: b + sec(1.7)},
    {id: 'd', parent: 'b', label: '0', sub: '300', at: b + sec(1.0), tone: 'cut', toneAt: b + sec(1.45)},
    {id: 'e', parent: 'b', label: '3', sub: '400', at: b + sec(1.0), tone: 'cut', toneAt: b + sec(1.45)},
  ];
};

const BruteTree: React.FC = () => {
  const fr = useF();
  const ns = nodes();
  const o = ease(fr, fStart('b1'), 10) * (1 - ease(fr, fEnd('b1', -0.3), 10));
  const blow = fPhrase('b1', 'Exponential', -0.15);
  const {pos} = treeLayout(ns, TX, TY, TW, LH);
  // the blow-up: ghost branches fanning out below the cut nodes as the voice says "exponential"
  const fan = ease(fr, blow, sec(0.7));
  return (
    <div style={{position: 'absolute', inset: 0, opacity: o}}>
      <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
        {fan > 0 && ['d', 'e'].map((id) =>
          Array.from({length: 6}, (_, i) => {
            const p = pos[id];
            const tx = p.x + (i - 2.5) * 34 * fan;
            const ty = p.y + 84 + 56 * fan;
            return <line key={id + i} x1={p.x} y1={p.y + 84} x2={tx} y2={ty} stroke={mark(C.rose)} strokeWidth={3} opacity={0.45 * fan} strokeDasharray="6 6" />;
          }),
        )}
      </svg>
      <Tree fr={fr} x={TX} y={TY} w={TW} nodes={ns} levelH={LH} limit={{depth: 2, label: 'k + 1 = 2 flights max', at: f('b1', 1.25)}} />
      {(() => {
        const k = pop(fr, blow);
        if (k <= 0) return null;
        return (
          <div style={{position: 'absolute', left: TX + 40, top: 772, display: 'flex', opacity: clamp01(k), transform: `scale(${0.7 + 0.3 * k})`, transformOrigin: '0 50%'}}>
            <Chip color={C.rose} size={38}><BigO s="O(n^(k+1))" /><span style={{color: C.ink}}>time</span></Chip>
          </div>
        );
      })()}
    </div>
  );
};

export const BruteWorld: React.FC = () => (
  <Span from={fStart('b1')} to={fEnd('b1')} name="brute tree">
    <BruteTree />
  </Span>
);

const BruteBurst: React.FC = () => {
  const fr = useF();
  return <Burst fr={fr} at={fPhrase('b1', 'Exponential', 0.05)} text="BOOM!" x={1690} y={262} size={200} rot={8} seed={5} hold={40} />;
};

export const BruteHud: React.FC = () => (
  <Span from={f('b1')} to={fEnd('b1')} name="brute burst">
    <BruteBurst />
  </Span>
);
