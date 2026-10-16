// Input decoder: the raw input as text, with tagged entries that light up and FLY into the subject, so the
// viewer sees the mapping from text to picture. Tag an entry with {{id|text}}:
//
//   const INPUT: InputSpec = {title: 'input · example 1', fs: 34, lines: [
//     'n = {{n|4}}',
//     'flights = [{{f0|[0,1,100]}},',  ...
//   ]};
//   <InputDecoder x={96} y={190} spec={INPUT}
//     hl={[{id: 'n', from: f('p1'), to: f('p1', 1.2), color: C.accent}]}
//     fly={[{id: 'f0', at: f('p1', 0.8), dur: sec(0.7), to: edgeTagWorld(MAP, PLACE, 'e01'), text: '100'}]}
//     notes={[{id: 'f0', char: 1, text: 'from', at: f('p1', 1.4)}]} />
//
// Positions come from monospace metrics (no DOM measuring), so inputPoint() can aim camera moves and arcs.
import React from 'react';
import {clamp01, ease, EASE, pop, span} from '../lib/motion';
import {mix} from './color';
import {C, FONT, halo, hlEdge, ink, inkOn, mark, MONO_ADVANCE, on, S, SHADOW, sh, SIZE} from './tokens';
import {Dots, Label} from './Panel';

export type InputSpec = {lines: string[]; title?: string; fs?: number; lh?: number; padX?: number; top?: number; minCols?: number};
type Seg = {text: string; id?: string; col: number};

const TAG = /\{\{([A-Za-z0-9_-]+)\|([^}]*)\}\}/g;
const parse = (line: string): Seg[] => {
  const segs: Seg[] = [];
  let last = 0;
  let col = 0;
  let m: RegExpExecArray | null;
  TAG.lastIndex = 0;
  while ((m = TAG.exec(line))) {
    if (m.index > last) {
      const t = line.slice(last, m.index);
      segs.push({text: t, col});
      col += t.length;
    }
    segs.push({text: m[2], id: m[1], col});
    col += m[2].length;
    last = m.index + m[0].length;
  }
  if (last < line.length) segs.push({text: line.slice(last), col});
  return segs;
};

export const inputLayout = (spec: InputSpec, x: number, y: number) => {
  const fs = spec.fs ?? 34;
  const lh = spec.lh ?? Math.round(fs * 1.5);
  const padX = spec.padX ?? 40;
  const top = spec.top ?? 96;
  const cw = fs * MONO_ADVANCE;
  const rows = spec.lines.map(parse);
  const cols = Math.max(spec.minCols ?? 0, ...rows.map((r) => r.reduce((n, s) => n + s.text.length, 0)));
  const tokens: Record<string, {row: number; col: number; len: number; text: string}> = {};
  rows.forEach((r, row) => r.forEach((s) => s.id && (tokens[s.id] = {row, col: s.col, len: s.text.length, text: s.text})));
  const w = padX * 2 + cols * cw;
  const h = top + rows.length * lh + 34;
  /** world-space box of a token (or of `char`..`char+len` inside it) */
  const box = (id: string, char = 0, len?: number) => {
    const t = tokens[id];
    if (!t) throw new Error(`input: no token ${id}`);
    const n = len ?? t.len - char;
    return {x: x + padX + (t.col + char) * cw, y: y + top + t.row * lh, w: n * cw, h: lh};
  };
  const center = (id: string, char = 0, len?: number) => {
    const b = box(id, char, len);
    return {x: b.x + b.w / 2, y: b.y + b.h / 2};
  };
  return {fs, lh, padX, top, cw, rows, tokens, w, h, box, center};
};

/** paint one plain segment with light syntax colours: names before '=' cyan, numbers ink, punctuation muted */
const Plain: React.FC<{text: string}> = ({text}) => {
  const out: React.ReactNode[] = [];
  const re = /([A-Za-z_][A-Za-z_0-9]*)|(-?\d+)|([^A-Za-z_0-9-]+|-)/g;
  let m: RegExpExecArray | null;
  let k = 0;
  while ((m = re.exec(text))) {
    const isName = !!m[1] && /^\s*=/.test(text.slice(m.index + m[0].length));
    const col = isName ? ink(C.cyan) : m[1] ? C.ink : m[2] ? C.ink : C.muted;
    out.push(<span key={k++} style={{color: col}}>{m[0]}</span>);
  }
  return <>{out}</>;
};

export type InputHL = {id: string; from: number; to: number; color?: string; char?: number; len?: number};
/** fromEnd: the copy starts just past the last character of its row (and fades in) instead of on the token, so it
 *  never crosses the rest of the row ("]," after a price) on its way out */
export type InputFly = {id: string; at: number; dur: number; to: {x: number; y: number}; text?: string; color?: string; scale?: number; lift?: number; char?: number; len?: number; fromEnd?: boolean};
export type InputNote = {id: string; at: number; text: string; char?: number; len?: number; color?: string; until?: number};

export const InputDecoder: React.FC<{
  fr: number; x: number; y: number; spec: InputSpec; o?: number;
  hl?: InputHL[]; fly?: InputFly[]; notes?: InputNote[]; done?: {id: string; at: number}[];
}> = ({fr, x, y, spec, o = 1, hl = [], fly = [], notes = [], done = []}) => {
  const lay = inputLayout(spec, x, y);
  const {fs, lh, padX, top, cw, rows, w, h} = lay;
  if (o <= 0.002) return null;
  return (
    <>
      <div style={{position: 'absolute', left: x, top: y, width: w, height: h, opacity: o, borderRadius: 26,
        background: `linear-gradient(180deg, ${C.panelTop}, ${C.panel})`, border: `1.5px solid ${C.line}`, boxShadow: SHADOW.card}}>
        <div style={{position: 'absolute', left: 30, top: 30, display: 'flex', alignItems: 'center', gap: 24}}>
          <Dots />
          {spec.title && <Label>{spec.title}</Label>}
        </div>
        <div style={{position: 'absolute', left: 0, top: 76, width: w, height: 1.5, background: C.line}} />
        {/* highlights behind text */}
        {hl.map((hh, i) => {
          const k = span(fr, hh.from, hh.to, 8, 10);
          if (k <= 0) return null;
          const b = lay.box(hh.id, hh.char ?? 0, hh.len);
          const col = hh.color ?? C.accent;
          return <div key={i} style={{position: 'absolute', left: b.x - x - 8, top: b.y - y + lh * 0.08, width: b.w + 16, height: lh * 0.84, borderRadius: 10,
            background: col + '2E', border: `2.5px solid ${hlEdge(col)}`, boxShadow: halo(col, 26, -4, S.hlGlow), opacity: k, transform: `scale(${0.96 + 0.04 * k})`}} />;
        })}
        {rows.map((r, row) => (
          <div key={row} style={{position: 'absolute', left: padX, top: top + row * lh, height: lh, display: 'flex', alignItems: 'center',
            fontFamily: FONT.mono, fontSize: fs, fontWeight: 700, whiteSpace: 'pre', letterSpacing: 0}}>
            {r.map((s, i) => {
              if (!s.id) return <Plain key={i} text={s.text} />;
              const isDone = done.find((d) => d.id === s.id && fr >= d.at);
              const lit = hl.find((hh) => hh.id === s.id && fr >= hh.from && fr < hh.to);
              // a lit entry sits on its highlight's tint: lifted to 4.6:1 there (theme only)
              const litC = lit ? inkOn(C.ink, mix(C.panel, lit.color ?? C.accent, 0x2E / 255)) : C.ink;
              return <span key={i} style={{color: lit ? litC : isDone ? C.faint : C.ink, transition: 'none'}}>{s.text}</span>;
            })}
          </div>
        ))}
        {/* notes: small labels under a token, with a tick */}
        {notes.map((nt, i) => {
          const k = pop(fr, nt.at);
          const out = nt.until ? 1 - ease(fr, nt.until, 8, EASE.in) : 1;
          if (k <= 0 || out <= 0) return null;
          const b = lay.box(nt.id, nt.char ?? 0, nt.len ?? 1);
          const col = nt.color ?? C.amber;
          return (
            <div key={i} style={{position: 'absolute', left: b.x - x + b.w / 2, top: b.y - y + lh * 0.9, transform: `translateX(-50%) translateY(${(1 - k) * -10}px)`,
              opacity: clamp01(k) * out, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
              <div style={{width: 3, height: 16, background: mark(col), borderRadius: 2}} />
              <div style={{fontFamily: FONT.sans, fontWeight: 800, fontSize: SIZE.small, color: on(col), background: col, padding: '4px 12px', borderRadius: 10, whiteSpace: 'nowrap'}}>{nt.text}</div>
            </div>
          );
        })}
      </div>
      {/* flying copies travel in world space from the token to their destination */}
      {fly.map((fl, i) => {
        const p = ease(fr, fl.at, fl.dur, EASE.inOut);
        if (fr < fl.at || p >= 1) return null;
        const tok = lay.tokens[fl.id];
        const text = fl.text ?? (fl.char != null ? tok.text.slice(fl.char, fl.char + (fl.len ?? tok.len - fl.char)) : tok.text);
        let a = lay.center(fl.id, fl.char ?? 0, fl.len);
        if (fl.fromEnd) {
          const rowLen = rows[tok.row].reduce((n, s) => n + s.text.length, 0);
          const half = ((text.length * cw + 28) / 2) * 1.25; // the chip's half width at its largest (sc <= 1.25)
          a = {x: x + padX + rowLen * cw + 14 + half, y: a.y};
        }
        const b = fl.to;
        const lift = fl.lift ?? 140;
        const cx = (a.x + b.x) / 2;
        const cy = Math.min(a.y, b.y) - lift;
        const px = (1 - p) ** 2 * a.x + 2 * (1 - p) * p * cx + p * p * b.x;
        const py = (1 - p) ** 2 * a.y + 2 * (1 - p) * p * cy + p * p * b.y;
        const s1 = fl.scale ?? 1;
        const sc = 1 + (s1 - 1) * p + Math.sin(p * Math.PI) * 0.25;
        const col = fl.color ?? C.amber;
        // a price leaving the end of its row lifts off at full opacity and grows from 0.9 over 3 frames: faded in on
        // the eased p it sat near-transparent for 0.2 s, and the faint chips of consecutive entries read as one
        // unreadable label to qa.py's moving-text check
        const lift0 = fl.fromEnd ? 0.9 + 0.1 * clamp01((fr - fl.at) / 3) : 1;
        return (
          <div key={'fl' + i} style={{position: 'absolute', left: px, top: py, transform: `translate(-50%, -50%) scale(${sc * lift0})`, opacity: clamp01((1 - p) / 0.12),
            fontFamily: FONT.mono, fontWeight: 800, fontSize: fs, color: on(col), background: col, padding: '4px 14px', borderRadius: 12, whiteSpace: 'pre',
            boxShadow: `${halo(col, 34, undefined, 'AA')}, 0 16px 30px -10px ${sh(0.8)}`}}>
            {text}
          </div>
        );
      })}
    </>
  );
};
