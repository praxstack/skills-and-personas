// Recursion tree (brute force drawn): nodes appear level by level, edges draw from parent to child, branches
// past a limit are cut (rose, struck), the winning leaf glows mint. Layout is computed from the list order.
//   <Tree fr={fr} x={900} y={200} w={860} nodes={[
//     {id: 'r', label: '0', at: f('b1')},
//     {id: 'a', parent: 'r', label: '1', sub: '100', at: f('b1', 0.5)},
//     {id: 'c', parent: 'a', label: '3', sub: '700', at: f('b1', 1.0), tone: 'win', toneAt: f('b1', 2)},
//   ]} limit={{depth: 2, label: 'k + 1 = 2 flights', at: f('b1', 1.4)}} />
// `sub` (a running cost) sits to the right of its node; a cut node gets a rose X badge.
import React from 'react';
import {clamp01, ease, EASE, pop} from '../lib/motion';
import {alpha} from './color';
import {C, FONT, halo, ink, mark, on, S, sh, SIZE} from './tokens';

export type TNode = {id: string; parent?: string; label: string; sub?: string; at: number; tone?: 'ok' | 'cut' | 'win' | 'dim'; toneAt?: number};

export const treeLayout = (nodes: TNode[], x: number, y: number, w: number, levelH: number) => {
  const kids: Record<string, string[]> = {};
  const depth: Record<string, number> = {};
  for (const n of nodes) {
    depth[n.id] = n.parent ? depth[n.parent] + 1 : 0;
    if (n.parent) (kids[n.parent] = kids[n.parent] ?? []).push(n.id);
  }
  const leaves: string[] = [];
  const walk = (id: string) => (kids[id]?.length ? kids[id].forEach(walk) : leaves.push(id));
  nodes.filter((n) => !n.parent).forEach((n) => walk(n.id));
  const pos: Record<string, {x: number; y: number}> = {};
  const step = w / Math.max(1, leaves.length);
  leaves.forEach((id, i) => (pos[id] = {x: x + step * (i + 0.5), y: y + depth[id] * levelH}));
  const place = (id: string): number => {
    if (pos[id]) return pos[id].x;
    const xs = kids[id].map(place);
    pos[id] = {x: (Math.min(...xs) + Math.max(...xs)) / 2, y: y + depth[id] * levelH};
    return pos[id].x;
  };
  nodes.filter((n) => !n.parent).forEach((n) => place(n.id));
  return {pos, depth, kids};
};

export const Tree: React.FC<{
  fr: number; x: number; y: number; w: number; nodes: TNode[]; levelH?: number; r?: number; o?: number;
  limit?: {depth: number; label: string; at: number};
}> = ({fr, x, y, w, nodes, levelH = 150, r = 38, o = 1, limit}) => {
  const {pos} = treeLayout(nodes, 0, 0, w, levelH);
  const maxDepth = Math.max(...nodes.map((n) => pos[n.id].y)) / levelH;
  if (o <= 0.002) return null;
  const toneOf = (n: TNode) => (n.tone && fr >= (n.toneAt ?? n.at) ? n.tone : 'ok');
  return (
    <div style={{position: 'absolute', left: x, top: y, width: w, height: (maxDepth + 1) * levelH, opacity: o}}>
      <svg width={w} height={(maxDepth + 1) * levelH} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
        {limit && (() => {
          const k = ease(fr, limit.at, 14);
          if (k <= 0) return null;
          const ly = limit.depth * levelH + levelH / 2;
          return (
            <g opacity={k}>
              <line x1={-40} x2={-40 + (w + 80) * k} y1={ly} y2={ly} stroke={mark(C.rose)} strokeWidth={4} strokeDasharray="16 12" />
            </g>
          );
        })()}
        {nodes.map((n) => {
          if (!n.parent) return null;
          const a = pos[n.parent];
          const b = pos[n.id];
          const k = ease(fr, n.at - 6, 10, EASE.out);
          if (k <= 0) return null;
          const tone = toneOf(n);
          const col = tone === 'cut' ? mark(C.rose) : tone === 'win' ? mark(C.mint) : tone === 'dim' ? alpha(S.tree, 0.15) : alpha(S.tree, 0.35);
          const ex = a.x + (b.x - a.x) * k;
          const ey = a.y + r + (b.y - r - a.y - r) * k;
          return <line key={n.id} x1={a.x} y1={a.y + r} x2={ex} y2={ey} stroke={col} strokeWidth={tone === 'win' ? 6 : 4} strokeLinecap="round" strokeDasharray={tone === 'cut' ? '10 9' : undefined} />;
        })}
      </svg>
      {limit && ease(fr, limit.at, 14) > 0 && (
        <div style={{position: 'absolute', right: -40, top: limit.depth * levelH + levelH / 2 + 10, fontFamily: FONT.sans, fontWeight: 800, fontSize: SIZE.small, color: ink(C.rose),
          opacity: ease(fr, limit.at + 8, 10), whiteSpace: 'nowrap'}}>{limit.label}</div>
      )}
      {nodes.map((n) => {
        const k = pop(fr, n.at);
        if (k <= 0) return null;
        const p = pos[n.id];
        const tone = toneOf(n);
        const col = tone === 'cut' ? C.rose : tone === 'win' ? C.mint : C.ink;
        const txt = ink(col);
        const tk = n.toneAt ? pop(fr, n.toneAt) : 0;
        return (
          <div key={n.id} style={{position: 'absolute', left: p.x - r, top: p.y - r, width: r * 2, height: r * 2, transform: `scale(${k})`, opacity: tone === 'dim' ? 0.35 : 1}}>
            <div style={{position: 'absolute', inset: 0, borderRadius: '50%', background: `radial-gradient(circle at 38% 30%, ${S.nodeHi}, ${S.treeLo} 75%)`,
              border: `3px solid ${tone === 'ok' ? alpha(S.tree, 0.3) : mark(col)}`, boxShadow: tone === 'win' ? halo(C.mint, 34, undefined, 'AA') : `0 10px 20px -8px ${sh(0.8)}`,
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: FONT.mono, fontWeight: 800, fontSize: r * 0.95, color: txt}}>{n.label}</div>
            {n.sub && (
              <div style={{position: 'absolute', left: r * 2 + 10, top: r - 19, fontFamily: FONT.mono, fontWeight: 800, fontSize: SIZE.small, lineHeight: 1.25,
                color: ink(tone === 'cut' ? C.rose : tone === 'win' ? C.mint : C.amber), whiteSpace: 'nowrap'}}>{n.sub}</div>
            )}
            {tone === 'cut' && (
              <svg width={40} height={40} viewBox="-20 -20 40 40" style={{position: 'absolute', left: -8, top: -14, overflow: 'visible', transform: `scale(${clamp01(tk) * 1.1})`}}>
                <circle r={19} fill={C.rose} stroke={C.bg} strokeWidth={3} />
                <path d="M -7 -7 L 7 7 M 7 -7 L -7 7" stroke={on(C.rose)} strokeWidth={4.5} strokeLinecap="round" />
              </svg>
            )}
          </div>
        );
      })}
    </div>
  );
};
