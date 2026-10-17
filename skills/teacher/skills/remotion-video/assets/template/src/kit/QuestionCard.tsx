// Question card with a countdown ring for the line's `think` pause. The subject stays visible below it so the
// viewer can reason on it. When the answer line starts, the card settles smaller (scale 0.74) so the answer has
// the stage; its label is counter-scaled so it stays at SIZE.label on screen.
//   const [t0, t1] = fThink('q1');
//   <QuestionCard fr={fr} label="Question 1" text="What is simpler to count than stops?"
//                 at={f('q1')} think={[t0, t1]} settle={f('a1')} out={fEnd('a1')} />
import React from 'react';
import {clamp01, ease, EASE, lerp, pop, SPRING} from '../lib/motion';
import {FPS} from '../lib/timing';
import {alpha} from './color';
import {C, FONT, halo, ink, mark, S, SHADOW, SIZE} from './tokens';

export const CountdownRing: React.FC<{fr: number; from: number; to: number; size?: number; color?: string}> = ({fr, from, to, size = 104, color = C.accent}) => {
  const p = clamp01((fr - from) / Math.max(1, to - from));
  const left = Math.max(0, (to - fr) / FPS);
  const done = fr >= to;
  const r = size / 2 - 8;
  const circ = 2 * Math.PI * r;
  const flash = done ? pop(fr, to) : 0;
  const col = done ? C.mint : color;
  return (
    <div style={{position: 'relative', width: size, height: size, transform: `scale(${1 + 0.12 * Math.sin(flash * Math.PI)})`}}>
      <svg width={size} height={size}>
        <circle cx={size / 2} cy={size / 2} r={r} fill={S.well} stroke={alpha(C.ink, 0.16)} strokeWidth={8} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={mark(col)} strokeWidth={8} strokeLinecap="round"
          strokeDasharray={`${circ * (done ? 1 : 1 - p)} ${circ}`} transform={`rotate(-90 ${size / 2} ${size / 2})`} />
      </svg>
      <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontFamily: FONT.mono, fontWeight: 800, fontSize: size * 0.4, color: ink(col)}}>{done ? '✓' : Math.ceil(left - 0.001)}</div>
    </div>
  );
};

export const QuestionCard: React.FC<{
  fr: number; label: string; text: string; at: number; think: [number, number]; settle?: number; out?: number; y?: number; width?: number;
}> = ({fr, label, text, at, think, settle, out, y = 150, width = 1480}) => {
  const k = pop(fr, at, SPRING.calm);
  const o = out ? 1 - ease(fr, out - 10, 10, EASE.in) : 1;
  if (k <= 0 || o <= 0) return null;
  const st = settle ? ease(fr, settle, 18, EASE.inOut) : 0;
  const thinking = fr >= think[0] && fr < think[1];
  const glowK = thinking ? 0.5 + 0.5 * Math.sin(((fr - think[0]) / FPS) * Math.PI * 2) : 0;
  const ringO = ease(fr, think[0] - 8, 10) * (1 - ease(fr, (settle ?? think[1] + 30) + 4, 10));
  const words = text.split(' ');
  const scale = lerp(0.94 + 0.06 * k, 0.74, st);
  return (
    <div style={{position: 'absolute', left: 960 - width / 2, top: y, width, opacity: clamp01(k) * o,
      transform: `translateY(${(1 - k) * -30 + lerp(0, -8, st)}px) scale(${scale})`, transformOrigin: '50% 0%'}}>
      <div style={{position: 'relative', borderRadius: 30, padding: '30px 160px 36px 52px',
        background: `linear-gradient(180deg, ${S.qTop}, ${S.qBot})`,
        border: `2px solid ${thinking ? mark(C.accent) : C.line2}`, boxShadow: SHADOW.card + `, ${halo(C.accent, 40 + glowK * 30, -10, thinking ? '99' : '00')}`}}>
        <div style={{fontFamily: FONT.sans, fontWeight: 900, fontSize: SIZE.label / Math.max(0.5, scale), letterSpacing: '0.2em', textTransform: 'uppercase', color: ink(C.accent), lineHeight: 1.2}}>{label}</div>
        <div style={{marginTop: 12, fontFamily: FONT.serif, fontStyle: 'italic', fontSize: 70, lineHeight: 1.1, color: C.ink}}>
          {words.map((w, i) => {
            const wk = pop(fr, at + 4 + i * 2, SPRING.calm);
            return <span key={i} style={{display: 'inline-block', marginRight: '0.24em', opacity: clamp01(wk), transform: `translateY(${(1 - wk) * 24}px)`}}>{w}</span>;
          })}
        </div>
        {ringO > 0 && (
          <div style={{position: 'absolute', right: 34, top: '50%', transform: 'translateY(-50%)', opacity: ringO, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8}}>
            <CountdownRing fr={fr} from={think[0]} to={think[1]} />
            <div style={{fontFamily: FONT.sans, fontWeight: 800, fontSize: SIZE.label, letterSpacing: '0.14em', color: C.muted}}>THINK</div>
          </div>
        )}
      </div>
    </div>
  );
};
