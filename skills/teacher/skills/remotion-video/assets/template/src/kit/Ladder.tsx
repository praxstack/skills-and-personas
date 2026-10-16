// Complexity ladder: one rung per approach, climbing upward as approaches improve. Each rung shows time and
// space in O(...) and a bar whose length reflects cost; the interview pick gets a glow and a stamp. The rung in
// focus is marked by its colour, border, glow and white title; the others step back to muted type but stay at
// full opacity, so every rung stays readable (4.5:1 or better).
//   <Ladder fr={fr} x={96} y={170} w={1100} rungs={[
//     {name: 'Brute-force DFS', time: 'O(n^(k+1))', space: 'O(k)', cost: 1, color: C.rose, at: chapterStart(4)},
//     {name: 'DFS + memo', time: 'O(k·E)', space: 'O(n·k)', cost: 0.38, color: C.amber, at: f('x1')},
//   ]} pick={{i: 2, at: f('x2', 2.4)}} focus={[[f('x1'), 1], [f('x2'), 2]]} />
import React from 'react';
import {clamp01, ease, EASE, pop, SPRING, steps} from '../lib/motion';
import {alpha, mix} from './color';
import {C, FONT, halo, ink, inkOn, mark, on as onFill, S, sh, SIZE} from './tokens';
import {BigO} from './Panel';

export type Rung = {name: string; time: string; space: string; cost: number; color: string; at: number; note?: string};

export const Ladder: React.FC<{
  fr: number; x: number; y: number; w: number; rungs: Rung[]; pick?: {i: number; at: number; label?: string}; focus?: [number, number][]; rungH?: number; gap?: number; o?: number;
}> = ({fr, x, y, w, rungs, pick, focus = [], rungH = 150, gap = 26, o = 1}) => {
  const n = rungs.length;
  const H = n * rungH + (n - 1) * gap;
  const cur = steps(fr, focus).v;
  if (o <= 0.002) return null;
  const barX = w * 0.63; // TIME/SPACE need about 0.6 w at 38 px
  const barW = w - barX - 40;
  return (
    <div style={{position: 'absolute', left: x, top: y, width: w, height: H, opacity: o}}>
      {/* rails */}
      {[18, w - 18].map((rx, i) => (
        <div key={i} style={{position: 'absolute', left: rx - 3, top: -30, width: 6, height: H + 60, borderRadius: 3,
          background: `linear-gradient(180deg, ${alpha(S.tree, 0)}, ${alpha(S.tree, 0.16)} 15%, ${alpha(S.tree, 0.16)} 85%, ${alpha(S.tree, 0)})`}} />
      ))}
      {rungs.map((r, i) => {
        const k = pop(fr, r.at, SPRING.calm);
        const ry = (n - 1 - i) * (rungH + gap); // first rung at the bottom: climbing = improving
        // a rung that has not landed yet is not drawn: an empty dashed slot reads as a missing card on screen
        if (k <= 0) return null;
        const on = cur === i;
        const isPick = pick && pick.i === i && fr >= pick.at;
        const pk = pick && pick.i === i ? pop(fr, pick.at) : 0;
        const edge = isPick ? C.mint : on ? r.color : C.line2;
        // a rung in focus is tinted toward its colour at the left end: its texts are lifted to 4.6:1 there (theme only)
        const tinted = on || isPick ? mix(S.rungOn, edge, 0x26 / 255) : S.rung;
        const rungSurf = [tinted, S.rung];
        const lit = cur == null || on || isPick; // in focus (or nothing is): full colour; otherwise muted type
        const bar = ease(fr, r.at + 6, 22, EASE.out) * r.cost;
        return (
          <div key={i} style={{position: 'absolute', left: 0, top: ry, width: w, height: rungH, borderRadius: 24, opacity: clamp01(k),
            transform: `translateY(${(1 - k) * 40}px) scale(${1 + 0.02 * pk})`,
            background: on || isPick ? `linear-gradient(90deg, ${edge}26, ${S.rungOn} 55%)` : S.rung,
            border: `2.5px solid ${on || isPick ? mark(edge) : edge}`, boxShadow: on || isPick ? `${halo(edge, 50, -12)}, 0 20px 40px -18px ${sh(0.9)}` : `0 20px 40px -18px ${sh(0.9)}`}}>
            <div style={{position: 'absolute', left: 28, top: rungH / 2 - 32, width: 64, height: 64, borderRadius: 32, display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontFamily: FONT.mono, fontWeight: 800, fontSize: 32, background: on || isPick ? edge : alpha(C.ink, 0.08), color: on || isPick ? onFill(edge) : C.ink}}>{i + 1}</div>
            <div style={{position: 'absolute', left: 116, top: 18, fontFamily: FONT.sans, fontWeight: 800, fontSize: 42, color: inkOn(lit ? C.ink : C.muted, rungSurf), letterSpacing: '-0.01em', whiteSpace: 'nowrap'}}>{r.name}</div>
            <div style={{position: 'absolute', left: 116, top: 78, display: 'flex', gap: 30, fontFamily: FONT.sans, fontWeight: 800, fontSize: SIZE.label, color: inkOn(C.muted, rungSurf), letterSpacing: '0.1em', alignItems: 'baseline', whiteSpace: 'nowrap'}}>
              <span>TIME <BigO s={r.time} color={inkOn(ink(r.color), rungSurf)} style={{fontSize: 38, letterSpacing: 0, marginLeft: 8}} /></span>
              <span>SPACE <BigO s={r.space} color={inkOn(lit ? C.ink : C.muted, rungSurf)} style={{fontSize: 38, letterSpacing: 0, marginLeft: 8}} /></span>
            </div>
            <div style={{position: 'absolute', left: barX, top: rungH / 2 - 16, width: barW, height: 22, borderRadius: 11, background: alpha(C.ink, 0.06)}}>
              <div style={{width: `${bar * 100}%`, height: '100%', borderRadius: 11, background: `linear-gradient(90deg, ${r.color}88, ${r.color})`, boxShadow: lit ? halo(r.color, 20, undefined, '66') : 'none', opacity: lit ? 1 : 0.6}} />
            </div>
            <div style={{position: 'absolute', left: barX, top: rungH / 2 + 16, fontFamily: FONT.sans, fontWeight: 700, fontSize: SIZE.small, color: lit ? C.ink : C.muted, opacity: ease(fr, r.at + 14, 10), whiteSpace: 'nowrap'}}>
              {r.note ?? 'cost'}
            </div>
            {pk > 0 && (
              <div style={{position: 'absolute', right: 36, top: -34, transform: `rotate(-7deg) scale(${pk})`, fontFamily: FONT.comic, fontSize: 46, letterSpacing: '0.04em',
                color: onFill(C.mint), background: C.mint, padding: '6px 20px 2px', borderRadius: 10, border: `4px solid ${S.burstLine}`, boxShadow: `${halo(C.mint, 40, undefined, 'AA')}, 6px 6px 0 ${S.burstLine}`}}>
                {pick?.label ?? 'INTERVIEW PICK'}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
