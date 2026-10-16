// Chapter 0 (title) and chapter 1 (the problem): decode every input onto the map, then walk example 1.
import React from 'react';
import {Span, useF} from '../lib/span';
import {chapterStart, f, fEnd, fPhrase, fStart, sec} from '../lib/timing';
import {clamp01, ease, EASE, pop} from '../lib/motion';
import {C, FONT, halo, ink, mark, on, S, sh, SIZE} from '../kit/tokens';
import {Chip, RichText} from '../kit/Panel';
import {InputDecoder, type InputFly, type InputHL} from '../kit/InputDecoder';
import {edgeTagWorld, nodeWorld} from '../kit/Graph';
import {TitleCard} from '../kit/TitleCard';
import {Burst} from '../kit/Burst';
import {toScreen, type Cam} from '../kit/Camera';
import {INPUT, MAP, PLACE, ENTRY_EDGE} from './data';
import {BEAT} from './director';

const INPUT_X = 96;
const INPUT_Y = 196;

const Decoder: React.FC = () => {
  const fr = useF();
  const out = ease(fr, f('p3', 0.25), sec(0.6), EASE.inOut);
  const hl: InputHL[] = [
    {id: 'n', from: f('p1', -0.1), to: f('p1', 1.3), color: C.accent},
    ...['f0', 'f1', 'f2', 'f3', 'f4'].map((id, i) => ({id, from: BEAT.entryFly(i) - 3, to: BEAT.entryFly(i) + BEAT.entryDur + 8, color: C.amberHi})),
    // the worked entry, colour-coded like the labels on the map: from (cyan), to (mint), price (amber); each
    // lands with its label, just before the word (BEAT.labelLead)
    {id: 'f0', char: 1, len: 1, from: fPhrase('p1', 'from', BEAT.labelLead), to: f('p2', -0.1), color: C.cyan},
    {id: 'f0', char: 3, len: 1, from: fPhrase('p1', 'to,', BEAT.labelLead), to: f('p2', -0.1), color: C.mint},
    {id: 'f0', char: 5, len: 3, from: fPhrase('p1', 'price', BEAT.labelLead), to: f('p2', -0.1), color: C.amber},
    {id: 'src', from: BEAT.srcAt() - 4, to: BEAT.srcAt() + sec(1.3), color: C.cyan},
    {id: 'dst', from: BEAT.dstAt() - 4, to: BEAT.dstAt() + sec(1.3), color: C.mint},
    {id: 'k', from: f('p3', -0.1), to: f('p3', 2.0), color: C.accent},
  ];
  const fly: InputFly[] = [
    ...['f0', 'f1', 'f2', 'f3', 'f4'].map((id, i) => ({
      id, at: BEAT.entryFly(i), dur: BEAT.entryDur, to: edgeTagWorld(MAP, PLACE.decode, ENTRY_EDGE[id]),
      char: 5, len: 3, color: C.amber, scale: 0.85, fromEnd: true, // the price leaves from the end of its row (never over "],") and lands as the edge's tag
    })),
    {id: 'src', at: BEAT.srcAt(), dur: sec(0.5), to: nodeWorld(MAP, PLACE.decode, '0'), color: C.cyan, lift: 60},
    {id: 'dst', at: BEAT.dstAt(), dur: sec(0.5), to: nodeWorld(MAP, PLACE.decode, '3'), color: C.mint, lift: 60},
  ];
  return (
    <div style={{position: 'absolute', inset: 0, transform: `translateX(${-out * 760}px)`, opacity: 1 - out}}>
      <InputDecoder fr={fr} x={INPUT_X} y={INPUT_Y} spec={INPUT} o={ease(fr, fStart('p1'), 12)} hl={hl} fly={fly}
        done={['f0', 'f1', 'f2', 'f3', 'f4'].map((id, i) => ({id, at: BEAT.entryFly(i) + BEAT.entryDur + 8}))} />
    </div>
  );
};

/** FROM / TO / PRICE labels on the map while the voice says them (colour-matched to the text). Each pop starts
 *  BEAT.labelLead before its word, so the label has landed (the spring settles in about 0.25 s) when it is heard. */
const EntryLabels: React.FC = () => {
  const fr = useF();
  const end = f('p2', -0.1);
  const items = [
    {at: fPhrase('p1', 'from', BEAT.labelLead), p: nodeWorld(MAP, PLACE.decode, '0'), dy: -100, text: 'FROM', c: C.cyan},
    {at: fPhrase('p1', 'to,', BEAT.labelLead), p: nodeWorld(MAP, PLACE.decode, '1'), dy: -100, text: 'TO', c: C.mint},
    {at: fPhrase('p1', 'price', BEAT.labelLead), p: edgeTagWorld(MAP, PLACE.decode, 'e01'), dy: -62, text: 'PRICE', c: C.amber},
  ];
  return (
    <>
      {items.map((it) => {
        const k = pop(fr, it.at) * (1 - ease(fr, end, 8));
        if (k <= 0) return null;
        return (
          <div key={it.text} style={{position: 'absolute', left: it.p.x, top: it.p.y + it.dy, transform: `translate(-50%, -50%) scale(${k})`,
            fontFamily: FONT.sans, fontWeight: 900, fontSize: SIZE.small, letterSpacing: '0.1em', color: on(it.c), background: it.c, padding: '7px 16px', borderRadius: 12,
            boxShadow: halo(it.c, 26, undefined, '88')}}>{it.text}</div>
        );
      })}
    </>
  );
};

/** k = 1 means at most one stop (p3), then a fare receipt for 0 -> 1 -> 3 (p4). Screen space (HUD), so the
 *  camera push on the answer never crops it: k chip top-left, receipt in the free left column. */
const StopsAndFare: React.FC = () => {
  const fr = useF();
  const kIn = pop(fr, f('p3', 0.35));
  const out = 1 - ease(fr, fEnd('p4', -0.4), 10);
  const r0 = BEAT.routeStart();
  const leg1 = BEAT.leg1();
  const leg2 = BEAT.leg2();
  const total = BEAT.totalAt();
  const ans = BEAT.answerAt();
  const meter = pop(fr, r0);
  const show = (at: number) => clamp01(pop(fr, at));
  const won = fr >= ans;
  // labels are there from the start (no empty box); each fare pops in when the plane lands
  const row = (label: string, value: string, labelAt: number, at: number, color: string, big = false) => (
    <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', fontFamily: FONT.mono, fontWeight: 800, fontSize: big ? 44 : 36, lineHeight: 1.5}}>
      <span style={{opacity: show(labelAt), color: big ? C.muted : C.ink, fontSize: big ? 30 : 36, fontFamily: big ? FONT.sans : FONT.mono, letterSpacing: big ? '0.12em' : 0}}>
        {big ? 'TOTAL' : <RichText text={label} num={C.ink} />}
      </span>
      <span style={{color: ink(color), opacity: show(at), display: 'inline-block', transform: `scale(${(big ? 0.6 : 0.8) + (big ? 0.4 : 0.2) * show(at)})`, transformOrigin: '100% 60%'}}>{value}</span>
    </div>
  );
  return (
    <>
      {kIn > 0 && (
        <div style={{position: 'absolute', left: 96, top: 176, opacity: clamp01(kIn) * out, transform: `translateY(${(1 - kIn) * -20}px)`}}>
          <Chip color={C.accent} size={34}><span style={{fontFamily: FONT.mono}}>k = 1</span><span style={{color: C.muted}}>·</span><span style={{color: C.ink, fontWeight: 700}}>at most 1 stop</span></Chip>
        </div>
      )}
      {meter > 0 && (
        <div style={{position: 'absolute', left: 96, top: 548, width: 300, padding: '22px 30px 18px', borderRadius: 22, background: S.card,
          opacity: clamp01(meter) * out, transform: `translateY(${(1 - meter) * 24}px)`,
          border: `2px solid ${won ? mark(C.mint) : C.line2}`, boxShadow: won ? halo(C.mint, 44, -8) : `0 20px 40px -18px ${sh(1)}`}}>
          <div style={{fontFamily: FONT.sans, fontWeight: 800, fontSize: SIZE.label, letterSpacing: '0.14em', color: C.muted, marginBottom: 6}}>FARE</div>
          {row('0 → 1', '100', r0 + 4, leg1, C.amber)}
          {row('1 → 3', '600', r0 + 8, leg2, C.amber)}
          <div style={{height: 3, borderRadius: 2, margin: '8px 0 4px', background: won ? mark(C.mint) : C.line2, opacity: show(r0 + 12)}} />
          {row('', '700', r0 + 12, total, C.mint, true)}
        </div>
      )}
    </>
  );
};

export const ProblemWorld: React.FC = () => (
  <>
    <Span from={fStart('p1')} to={f('p3', 1.2)} name="decoder">
      <Decoder />
    </Span>
    <Span from={fStart('p1')} to={f('p2')} name="entry labels">
      <EntryLabels />
    </Span>
  </>
);

export const ProblemHud: React.FC<{cam: Cam}> = ({cam}) => {
  const n3 = toScreen(cam, nodeWorld(MAP, PLACE.center, '3'));
  return (
    <>
      <Span from={0} to={chapterStart(1)} name="title">
        <TitleHud />
      </Span>
      <Span from={fStart('p3')} to={fEnd('p4')} name="stops and fare">
        <StopsAndFare />
      </Span>
      <Span from={BEAT.answerAt()} to={fEnd('p4')} name="burst 700">
        {/* up and to the right of the node, clear of its END badge (top) and 700 pill (bottom) */}
        <BurstAt at={BEAT.answerAt() + sec(0.15)} text="700!" x={n3.x + 215} y={n3.y - 190} size={240} />
      </Span>
    </>
  );
};

const TitleHud: React.FC = () => {
  const fr = useF();
  return <TitleCard fr={fr} from={fStart('i1')} to={fEnd('i1')} kicker="LeetCode 787 · medium" lines={['Cheapest Flights', 'Within K Stops']} accent="K" />;
};

export const BurstAt: React.FC<{at: number; text: string; x: number; y: number; size?: number; color?: string; rot?: number}> = (p) => {
  const fr = useF();
  return <Burst fr={fr} {...p} />;
};
