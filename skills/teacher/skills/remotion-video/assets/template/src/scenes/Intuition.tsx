// Chapter 3 (intuition): each question gets a card and a visible think countdown; the answer is drawn on the
// subject (flights numbered on the map, old/new rows relaxing one flight per round).
import React from 'react';
import {Span, useF} from '../lib/span';
import {f, fEnd, fStart, fThink, sec} from '../lib/timing';
import {clamp01, ease, EASE, pop} from '../lib/motion';
import {C, FONT, halo, ink, mark, on, SIZE} from '../kit/tokens';
import {Chip, RichText} from '../kit/Panel';
import {QuestionCard} from '../kit/QuestionCard';
import {DPTable, dpLayout} from '../kit/DPTable';
import {edgeTagWorld} from '../kit/Graph';
import {MAP, PLACE} from './data';

const Q1: React.FC = () => {
  const fr = useF();
  // the chapter's first line: the card arrives with the subject as the chapter sting leaves, not on the voice
  return <QuestionCard fr={fr} label="Question 1" text="What is simpler to count than stops?" at={fStart('q1', 0.4)} think={fThink('q1')} settle={f('a1')} out={fEnd('a1')} />;
};

const Q2: React.FC = () => {
  const fr = useF();
  return <QuestionCard fr={fr} label="Question 2" text="Why read the old row while writing a new one?" at={f('q2')} think={fThink('q2')} settle={f('a2')} out={fEnd('a2')} />;
};

/** a1: the two legs of the 700 route are numbered as flights; the rule lands under the settled card */
const FlightsAnswer: React.FC = () => {
  const fr = useF();
  const a1 = f('a1');
  const out = 1 - ease(fr, fEnd('a1', -0.3), 10);
  const legs = [
    // on the outer side of each leg (up-left / up-right of its price tag), clear of node 1 and the arrow heads
    {edge: 'e01', at: a1 + sec(0.3), text: 'FLIGHT 1', dx: -95},
    {edge: 'e13', at: a1 + sec(0.8), text: 'FLIGHT 2', dx: 95},
  ];
  return (
    <>
      {legs.map((l) => {
        const p = edgeTagWorld(MAP, PLACE.question, l.edge);
        const k = pop(fr, l.at);
        if (k <= 0) return null;
        return (
          <div key={l.edge} style={{position: 'absolute', left: p.x + l.dx, top: p.y - 64, transform: `translate(-50%, -50%) scale(${k})`, opacity: out,
            fontFamily: FONT.sans, fontWeight: 900, fontSize: SIZE.small, letterSpacing: '0.08em', color: on(C.mint), background: C.mint, padding: '7px 16px', borderRadius: 12,
            boxShadow: halo(C.mint, 30, undefined, '99')}}>{l.text}</div>
        );
      })}
    </>
  );
};

/** a1 rule, in screen space under the settled question card */
const FlightsRule: React.FC = () => {
  const fr = useF();
  const rule = pop(fr, f('a1', 1.1));
  const out = 1 - ease(fr, fEnd('a1', -0.3), 10);
  if (rule <= 0) return null;
  return (
    <div style={{position: 'absolute', left: 960, top: 312, transform: `translate(-50%, 0) scale(${0.8 + 0.2 * rule})`, opacity: clamp01(rule) * out}}>
      <Chip color={C.mint} size={34}><span style={{color: C.ink}}><RichText text="k stops → k + 1 flights" num={C.mint} /></span></Chip>
    </div>
  );
};

const TX = 830;
const TY = 430;
const CW = 120;
const CH = 88;
const LW = 210;
const RG = 64; // row gap: room for the old -> new arrows

/** q2/a2: old row and new row; one relaxation lands, the chained one is blocked */
const Rows: React.FC = () => {
  const fr = useF();
  const a2 = f('a2');
  const o = ease(fr, f('q2', 0.4), 12) * (1 - ease(fr, fEnd('a2', -0.3), 10));
  const lay = dpLayout(TX, TY, 4, 2, CW, CH, LW, 12, RG);
  const from0 = lay.cell(0, 0);
  const to1 = lay.cell(1, 1);
  const from1 = lay.cell(0, 1);
  const to2 = lay.cell(1, 2);
  const arrow1 = ease(fr, a2 + sec(0.15), sec(0.45), EASE.inOut);
  const arrow2 = ease(fr, a2 + sec(0.8), sec(0.4), EASE.inOut);
  const block = pop(fr, a2 + sec(1.05));
  const rule = pop(fr, a2 + sec(1.3));
  // straight arrows from the old cell's bottom to the new cell's top, with a head
  const arrow = (a: {x: number; y: number}, b: {x: number; y: number}, k: number, col: string, dash?: string) => {
    const x1 = a.x, y1 = a.y + CH / 2 + 4, x2 = b.x - 10, y2 = b.y - CH / 2 - 8;
    const ex = x1 + (x2 - x1) * k, ey = y1 + (y2 - y1) * k;
    const ang = (Math.atan2(y2 - y1, x2 - x1) * 180) / Math.PI;
    return (
      <g>
        <line x1={x1} y1={y1} x2={ex} y2={ey} stroke={mark(col)} strokeWidth={5} strokeLinecap="round" strokeDasharray={dash} />
        {k > 0.9 && <path d="M 6 0 L -10 -8 L -6 0 L -10 8 Z" fill={mark(col)} transform={`translate(${x2} ${y2}) rotate(${ang})`} />}
      </g>
    );
  };
  return (
    <div style={{position: 'absolute', inset: 0, opacity: o}}>
      <DPTable fr={fr} x={TX} y={TY} cols={['0', '1', '2', '3']} colTitle="city" cw={CW} ch={CH} labelW={LW} rowGap={RG} rows={[
        {label: 'dist', sub: 'old row', color: C.cyan, at: f('q2', 0.5), cells: [[[0, '0']], [[0, '∞']], [[0, '∞']], [[0, '∞']]]},
        {label: 'next', sub: 'new row', color: C.accent, at: f('q2', 0.8), cells: [[[0, '0']], [[0, '∞'], [a2 + sec(0.6), '100', C.mint]], [[0, '∞'], [a2 + sec(1.05), '∞', C.rose]], [[0, '∞']]]},
      ]} />
      <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
        {arrow1 > 0 && arrow(from0, to1, arrow1, C.mint)}
        {arrow2 > 0 && arrow(from1, to2, arrow2, C.rose, '10 10')}
      </svg>
      {block > 0 && (
        <div style={{position: 'absolute', left: lay.cell(1, 3).x + CW / 2 + 22, top: to2.y - 40, transform: `scale(${block})`, transformOrigin: '0 50%', fontFamily: FONT.sans, fontWeight: 800,
          fontSize: 32, lineHeight: 1.2, color: ink(C.rose), whiteSpace: 'nowrap'}}>reads old ∞<br />no chaining</div>
      )}
      {rule > 0 && (
        <div style={{position: 'absolute', left: TX + LW, top: TY + 56 + 2 * (CH + RG) - RG + 30, opacity: clamp01(rule), transform: `translateY(${(1 - rule) * 16}px)`}}>
          <Chip color={C.mint} size={34}><span style={{color: C.ink}}>1 round = 1 more flight</span></Chip>
        </div>
      )}
    </div>
  );
};

export const IntuitionWorld: React.FC = () => (
  <>
    <Span from={f('a1')} to={fEnd('a1')} name="a1 flights">
      <FlightsAnswer />
    </Span>
    <Span from={fStart('q2')} to={fEnd('a2')} name="q2 rows">
      <Rows />
    </Span>
  </>
);

export const IntuitionHud: React.FC = () => (
  <>
    <Span from={fStart('q1')} to={fEnd('a1')} name="q1 card">
      <Q1 />
    </Span>
    <Span from={f('a1')} to={fEnd('a1')} name="a1 rule">
      <FlightsRule />
    </Span>
    <Span from={fStart('q2')} to={fEnd('a2')} name="q2 card">
      <Q2 />
    </Span>
  </>
);
