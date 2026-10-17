// Title card: kicker chip, a two-line display title with one accent word, a growing rule, and a plane
// flying a dotted arc behind it (character). Exits by pushing toward the camera.
//   <TitleCard fr={fr} from={fStart('i1')} to={fEnd('i1')} kicker="LeetCode 787 · medium"
//              lines={['Cheapest Flights', 'Within K Stops']} accent="K" />
import React from 'react';
import {AbsoluteFill} from 'remotion';
import {clamp01, ease, EASE, pop, SPRING} from '../lib/motion';
import {C, FONT, halo, ink, mark, on, S, SIZE} from './tokens';

const PLANE = 'M 18 0 L 6 -3.4 L -1 -16 L -7 -16 L -2.4 -3.4 L -11 -2.8 L -14.5 -9 L -18 -9 L -15.5 0 L -18 9 L -14.5 9 L -11 2.8 L -2.4 3.4 L -7 16 L -1 16 L 6 3.4 Z';

export const TitleCard: React.FC<{fr: number; from: number; to: number; kicker?: string; lines: string[]; accent?: string; sub?: string}> = ({fr, from, to, kicker, lines, accent, sub}) => {
  if (fr < from - 2 || fr > to) return null;
  const out = ease(fr, to - 20, 14, EASE.in); // gone before `to`, where the first chapter sting starts
  const arcP = ease(fr, from, Math.max(30, to - from), EASE.inOut);
  // the flight path loops OVER the title block (apex near y 90), never through the words
  const arc = (u: number) => ({x: (1 - u) ** 2 * 60 + 2 * (1 - u) * u * 900 + u * u * 1880, y: (1 - u) ** 2 * 760 + 2 * (1 - u) * u * -520 + u * u * 640});
  const q = arc(arcP);
  const q2 = arc(Math.min(1, arcP + 0.01));
  const ang = (Math.atan2(q2.y - q.y, q2.x - q.x) * 180) / Math.PI;
  let wi = 0;
  return (
    <AbsoluteFill style={{opacity: 1 - out, transform: `scale(${1 + out * 0.12})`}}>
      <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0}}>
        {Array.from({length: 90}, (_, i) => i / 89).filter((u) => u <= arcP).map((u, i) => {
          const a = arc(u);
          return <circle key={i} cx={a.x} cy={a.y} r={3.2} fill={mark(C.amber)} opacity={0.12 + 0.5 * (u / Math.max(arcP, 0.01))} />;
        })}
        {arcP > 0 && arcP < 1 && (
          <g transform={`translate(${q.x} ${q.y}) rotate(${ang})`}>
            <circle r={40} fill={C.accent} opacity={0.25} />
            <path d={PLANE} fill={S.plane} transform="scale(2.1)" />
          </g>
        )}
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 0, bottom: 120, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
        {kicker && (
          <div style={{opacity: clamp01(pop(fr, from)), transform: `translateY(${(1 - pop(fr, from)) * 20}px)`, marginBottom: 34,
            fontFamily: FONT.mono, fontWeight: 800, fontSize: 30, letterSpacing: '0.12em', textTransform: 'uppercase', color: on(C.amber),
            background: C.amber, padding: '8px 22px', borderRadius: 10}}>{kicker}</div>
        )}
        {lines.map((ln, li) => (
          <div key={li} style={{display: 'flex', gap: '0.26em', fontFamily: FONT.sans, fontWeight: 900, fontSize: SIZE.title, letterSpacing: '-0.035em', lineHeight: 1.02, color: C.ink}}>
            {ln.split(' ').map((w) => {
              const k = pop(fr, from + 4 + wi++ * 3, SPRING.calm);
              const isAcc = accent && w === accent;
              return (
                <span key={w + wi} style={{display: 'inline-block', opacity: clamp01(k), transform: `translateY(${(1 - k) * 50}px)`,
                  color: isAcc ? ink(C.accent) : C.ink, textShadow: isAcc ? halo(C.accent, 40, undefined, '88') : S.title}}>{w}</span>
              );
            })}
          </div>
        ))}
        <div style={{marginTop: 34, height: 6, borderRadius: 3, width: 420 * ease(fr, from + 14, 20), background: `linear-gradient(90deg, ${C.accent}, ${C.amber})`}} />
        {sub && <div style={{marginTop: 26, fontFamily: FONT.sans, fontWeight: 600, fontSize: 36, color: C.muted, opacity: ease(fr, from + 18, 14)}}>{sub}</div>}
      </div>
    </AbsoluteFill>
  );
};
