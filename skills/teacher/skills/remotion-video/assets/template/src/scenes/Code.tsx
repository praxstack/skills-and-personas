// Chapter 5 (C++ and dry run): the compiled solution with the active line following the narration, the dry-run
// table filling cell by cell while the map writes the same values (director.ts), then the recap.
import React from 'react';
import {Span, useF} from '../lib/span';
import {chapterStart, f, fEnd, fPhrase, fStart, sec} from '../lib/timing';
import {clamp01, ease, EASE, pop} from '../lib/motion';
import {C, FONT, ink, S, SHADOW} from '../kit/tokens';
import {Chip, BigO, Label, RichText} from '../kit/Panel';
import {CodePanel} from '../kit/CodePanel';
import {DPTable, dpLayout} from '../kit/DPTable';
import {Burst} from '../kit/Burst';
import {toScreen, type Cam} from '../kit/Camera';
import {CPP, CODE_LINE} from './data';
import {BEAT} from './director';

// Layout at 1080p: the code panel fills the left (x 96-1276, y 150-890: 18 lines of 30 px code at 36 px pitch),
// the right column (x 1300-1824) holds the map (PLACE.code, top) and the dry-run table (bottom).
const CODE_X = 96;
const CODE_Y = 150;
const CODE_FS = 30;
const CODE_LH = 36;
const T = {x: 1300, y: 556, cw: 82, ch: 70, lw: 150};

const Solution: React.FC = () => {
  const fr = useF();
  const c1 = f('c1');
  const R0 = BEAT.dryR0();
  const R1 = BEAT.dryR1();
  const v700 = BEAT.dry700();
  // appears as the chapter sting wipes away (chapterStart), never under it
  const o = ease(fr, chapterStart(5), 12) * (1 - ease(fr, fStart('o1'), 12, EASE.in));
  const L = CODE_LINE;
  return (
    <CodePanel fr={fr} x={CODE_X} y={CODE_Y} code={CPP} fs={CODE_FS} lh={CODE_LH} o={o} title="solution.cpp" badge="k + 1 rounds"
      reveal={[[0, 17, chapterStart(5) + sec(0.05)]]}
      active={[
        [c1, L.init[0], L.init[1]],
        [R0 - sec(0.2), L.round[0], L.round[1]],
        [R0 + sec(0.35), L.relax[0], L.relax[1]],
        [R1 - sec(0.2), L.round[0], L.round[1]],
        [R1 + sec(0.05), L.relax[0], L.relax[1]],
        [v700 + sec(0.5), L.swap[0], L.swap[1]],
        [v700 + sec(1.1), L.ret[0], L.ret[1]],
      ]}
      pulse={[[R0 + sec(0.65), L.relax[1]], [R1 + sec(0.2), L.relax[1]], [v700, L.relax[1]]]} />
  );
};

const DryTable: React.FC = () => {
  const fr = useF();
  const c1 = f('c1');
  const R0 = BEAT.dryR0();
  const R1 = BEAT.dryR1();
  const v700 = BEAT.dry700();
  const o = ease(fr, c1 - sec(0.1), 12) * (1 - ease(fr, fStart('o1'), 12, EASE.in));
  const INF = '∞';
  return (
    <DPTable fr={fr} x={T.x} y={T.y} cols={['0', '1', '2', '3']} colTitle="city" cw={T.cw} ch={T.ch} labelW={T.lw} fs={36} labelFs={30} o={o} rows={[
      {label: 'start', at: c1 + sec(0.1), cells: [[[0, '0', C.cyan]], [[0, INF]], [[0, INF]], [[0, INF]]]},
      {label: 'round 0', at: R0, cells: [[[0, '0']], [[0, INF], [R0 + sec(0.7), '100', C.mint]], [[0, INF]], [[0, INF]]]},
      {label: 'round 1', at: R1, cells: [[[0, '0']], [[0, '100']], [[0, INF], [R1 + sec(0.2), '200', C.mint]], [[0, INF], [v700, '700', C.mint]]]},
    ]} />
  );
};

const Recap: React.FC = () => {
  const fr = useF();
  const o1 = f('o1');
  const copy = fPhrase('o1', 'Copy');
  const k = pop(fr, fStart('o1') + sec(0.2));
  const l1 = pop(fr, o1);
  const l2 = pop(fr, copy);
  const chips = pop(fr, o1 + sec(1.0)); // the cost of the rule, right under it, before the closing line
  return (
    <div style={{position: 'absolute', left: 1070, top: 230, width: 750, padding: '40px 46px', borderRadius: 30, opacity: clamp01(k), transform: `translateX(${(1 - k) * 60}px)`,
      background: `linear-gradient(180deg, ${S.recapTop}, ${S.recapBot})`, border: `1.5px solid ${C.line2}`, boxShadow: SHADOW.card}}>
      <Label color={C.accent}>Remember</Label>
      <div style={{marginTop: 26, fontFamily: FONT.sans, fontWeight: 800, fontSize: 54, lineHeight: 1.15, color: C.ink, opacity: clamp01(l1), transform: `translateY(${(1 - l1) * 20}px)`}}>
        <RichText text="k stops → k + 1 rounds" num={C.amber} arrow={C.accent} />
      </div>
      <div style={{marginTop: 24, display: 'flex', gap: 18, opacity: clamp01(chips), transform: `translateY(${(1 - chips) * 14}px)`}}>
        <Chip color={C.amber} size={36}><BigO s="O(k·E)" /><span style={{color: C.ink}}>time</span></Chip>
        <Chip color={C.cyan} size={36}><BigO s="O(n)" /><span style={{color: C.ink}}>space</span></Chip>
      </div>
      <div style={{marginTop: 30, fontFamily: FONT.serif, fontStyle: 'italic', fontSize: 66, lineHeight: 1.1, color: ink(C.mint), opacity: clamp01(l2), transform: `translateY(${(1 - l2) * 20}px)`}}>
        Copy before you update.
      </div>
    </div>
  );
};

export const CodeWorld: React.FC = () => (
  <>
    <Span from={chapterStart(5) - sec(0.6)} to={fStart('o1') + sec(0.6)} name="code">
      <Solution />
    </Span>
    <Span from={f('c1', -0.4)} to={fStart('o1') + sec(0.6)} name="dry table">
      <DryTable />
    </Span>
    <Span from={fStart('o1')} to={fEnd('o1') + 1} name="recap">
      <Recap />
    </Span>
  </>
);

export const CodeHud: React.FC<{cam: Cam}> = ({cam}) => {
  // over the short lines at the code panel's lower right (swap / closing braces), right of where their text ends
  // and left of the table: the only free pocket on this busy frame; never over a cell, code text or the relax line
  const at = toScreen(cam, {x: 1140, y: 778});
  return (
    <Span from={BEAT.dry700()} to={fStart('o1')} name="burst 700">
      <DryBurst x={at.x} y={at.y} />
    </Span>
  );
};

const DryBurst: React.FC<{x: number; y: number}> = ({x, y}) => {
  const fr = useF();
  return <Burst fr={fr} at={BEAT.dry700() + sec(0.1)} text="700!" x={x} y={y} size={150} rot={-10} seed={9} hold={42} />;
};
