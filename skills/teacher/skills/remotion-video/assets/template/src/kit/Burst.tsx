// Comic callout burst ("700!", "POP!", "NOPE!"): a jagged star with a hard offset shadow, halftone dots, comic
// lettering, spring overshoot and a wobble. Use on events (the answer lands, a route is rejected), 3-5 per film.
//   <Burst fr={fr} at={f('p4', 3.1)} text="700!" x={1500} y={330} />
import React from 'react';
import {clamp01, ease, EASE, pop, rand} from '../lib/motion';
import {fit} from './color';
import {C, FONT, S, THEMED} from './tokens';

export const Burst: React.FC<{
  fr: number; at: number; text: string; x: number; y: number; size?: number; color?: string; ink?: string; hold?: number; rot?: number; seed?: number; spikes?: number;
}> = ({fr, at, text, x, y, size = 260, color = C.burst, ink = S.burstLine, hold = 50, rot = -8, seed = 3, spikes = 14}) => {
  // The lettering reads by its outline (light letters, dark outline, or the reverse), so in a theme the outline is
  // moved until it holds 5.2:1 on the fill (rosepine-dawn's outline read 3.54:1 on its salmon gold; at 4.6:1 the
  // halftone dots over the fill still took everforest-light's to 4.43:1). fit() leaves a colour that already holds
  // it unchanged; the original palette is as shipped.
  const word = S.burstText;
  const wordLine = THEMED && /^#[0-9a-f]{6}$/i.test(color) && /^#[0-9a-f]{6}$/i.test(ink) ? fit(ink, color, 5.2) : ink;
  if (fr < at || fr > at + hold + 14) return null;
  const k = pop(fr, at, {damping: 9, stiffness: 190, mass: 0.6});
  const out = ease(fr, at + hold, 12, EASE.in);
  const wob = Math.sin((fr - at) * 0.35) * 2.5 * (1 - clamp01((fr - at) / 40));
  const R = size / 2;
  const pts: string[] = [];
  for (let i = 0; i < spikes * 2; i++) {
    const a = (i / (spikes * 2)) * Math.PI * 2;
    const r = i % 2 === 0 ? R * (0.9 + rand(i, seed) * 0.16) : R * (0.6 + rand(i, seed + 1) * 0.1);
    pts.push(`${Math.cos(a) * r},${Math.sin(a) * r}`);
  }
  const poly = pts.join(' ');
  // Bangers draws 7 almost like 1, so anything with digits uses Inter 900 italic (wider: smaller size)
  const numeric = /\d/.test(text);
  const fs = Math.min(size * 0.42, (size * 1.5) / Math.max(2.2, text.length * 0.62)) * (numeric ? 0.8 : 1);
  return (
    <div style={{position: 'absolute', left: x - R * 1.3, top: y - R * 1.3, width: R * 2.6, height: R * 2.6,
      transform: `rotate(${rot + wob}deg) scale(${k * (1 - out * 0.6)})`, opacity: 1 - out, pointerEvents: 'none'}}>
      <svg width={R * 2.6} height={R * 2.6} viewBox={`${-R * 1.3} ${-R * 1.3} ${R * 2.6} ${R * 2.6}`} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
        <defs>
          <pattern id={`ht-${seed}`} width={14} height={14} patternUnits="userSpaceOnUse">
            <circle cx={7} cy={7} r={2.6} fill={C.accent} opacity={0.35} />
          </pattern>
        </defs>
        {/* speed lines */}
        {Array.from({length: 12}, (_, i) => {
          const a = (i / 12) * Math.PI * 2 + 0.2;
          const r0 = R * 1.02;
          const r1 = R * (1.15 + 0.12 * rand(i, seed + 5)) + ease(fr, at, 10) * 14;
          return <line key={i} x1={Math.cos(a) * r0} y1={Math.sin(a) * r0} x2={Math.cos(a) * r1} y2={Math.sin(a) * r1} stroke={color} strokeWidth={6} strokeLinecap="round" opacity={0.9 * (1 - ease(fr, at + 12, 16))} />;
        })}
        <polygon points={poly} fill={ink} transform="translate(10 12)" />
        <polygon points={poly} fill={color} stroke={ink} strokeWidth={7} strokeLinejoin="round" />
        <polygon points={poly} fill={`url(#ht-${seed})`} />
      </svg>
      <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontFamily: numeric ? FONT.sans : FONT.comic, fontWeight: numeric ? 900 : 400, fontStyle: numeric ? 'italic' : 'normal', fontSize: fs, color: word,
        letterSpacing: numeric ? '-0.02em' : '0.02em', lineHeight: 1, paddingTop: numeric ? 0 : fs * 0.08,
        WebkitTextStroke: `${Math.max(4, fs * 0.07)}px ${wordLine}`, paintOrder: 'stroke fill', textShadow: `5px 6px 0 ${wordLine}`} as React.CSSProperties}>
        {text}
      </div>
    </div>
  );
};
