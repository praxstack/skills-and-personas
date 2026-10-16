// Code panel: monospace with ligatures off, syntax colours from the palette, line numbers, chunked reveal and
// an active-line highlight that glides between ranges as the narration moves through the code. The active
// range gets the highlight bar, an accent line number and bold type; the other lines stay readable (opacity
// 0.8, every colour above 4.5:1 on the panel), never faded out.
//   <CodePanel fr={fr} x={96} y={150} code={CPP} fs={30} title="solution.cpp"
//     reveal={[[0, 4, f('c1')], [5, 12, f('c2')]]}               // [firstLine, lastLine, frame]
//     active={[[f('c1'), 2, 4], [f('c2', 1.0), 6, 6]]}             // [frame, firstLine, lastLine]; -1 hides
//     pulse={[[f('c3', 0.5), 11]]} />                              // [frame, line]: a flash on that line
import React from 'react';
import {clamp01, ease, EASE, track, bump} from '../lib/motion';
import {mix} from './color';
import {C, CODE_DIM_OPACITY, CODE_INK, FONT, halo, hlEdge, ink, inkOn, mark, MONO_ADVANCE, NO_LIGA, S, SHADOW, SIZE} from './tokens';
import {Dots} from './Panel';

const KW = new Set(['int', 'long', 'const', 'for', 'while', 'if', 'else', 'return', 'auto', 'void', 'bool', 'true', 'false', 'class', 'struct', 'public', 'private', 'using', 'namespace', 'new', 'delete', 'break', 'continue', 'static', 'unsigned', 'char', 'double', 'float', 'def', 'in', 'and', 'or', 'not', 'None', 'let', 'var', 'function']);
const TYPES = new Set(['vector', 'string', 'map', 'unordered_map', 'set', 'pair', 'queue', 'priority_queue', 'deque', 'array', 'size_t', 'list', 'dict']);

// every colour keeps >= 4.5:1 on the panel even on a dimmed (0.8) line; comments are set apart by italics.
// They are inks (tokens.CODE_INK), never fills; under a theme the other lines stay at full strength (CODE_DIM 1).
export const CODE_COL = CODE_INK;
/** opacity of the lines outside the active range */
export const CODE_DIM = CODE_DIM_OPACITY;
type CodeCols = typeof CODE_COL;
/** the code colours lifted to 4.6:1 on a tinted bar (theme only; the original is unchanged) */
const colsOn = (surface: string): CodeCols =>
  Object.fromEntries(Object.entries(CODE_COL).map(([k, v]) => [k, inkOn(v, surface)])) as CodeCols;
const colsOnAll = (surfaces: string[]): CodeCols =>
  Object.fromEntries(Object.entries(CODE_COL).map(([k, v]) => [k, inkOn(v, surfaces)])) as CodeCols;

/** tokenise one line into coloured spans (C++/Python/JS-ish; good enough for explainers) */
export const highlight = (line: string, cols: CodeCols = CODE_COL): React.ReactNode[] => {
  const CODE_COL = cols;
  const out: React.ReactNode[] = [];
  const ci = line.search(/\/\/|#(?!include)/);
  const code = ci >= 0 ? line.slice(0, ci) : line;
  const re = /("[^"]*"|'[^']*')|([A-Za-z_][A-Za-z_0-9]*)(\s*\()?|(\d+e\d+|\d+\.?\d*)|(\s+)|([^\sA-Za-z_0-9"']+)/g;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = re.exec(code))) {
    const [tok, str, id, call, num] = m;
    let col = CODE_COL.punct;
    if (str) col = CODE_COL.str;
    else if (id) col = KW.has(id) ? CODE_COL.kw : TYPES.has(id) ? CODE_COL.type : call ? CODE_COL.fn : CODE_COL.txt;
    else if (num) col = CODE_COL.num;
    else if (m[5]) col = CODE_COL.txt;
    if (id && call) {
      out.push(<span key={i++} style={{color: col}}>{id}</span>);
      out.push(<span key={i++} style={{color: CODE_COL.punct}}>{call}</span>);
    } else out.push(<span key={i++} style={{color: col}}>{tok}</span>);
  }
  if (ci >= 0) out.push(<span key={i++} style={{color: CODE_COL.com, fontStyle: 'italic'}}>{line.slice(ci)}</span>);
  return out;
};

/** panel geometry: header bar 66 px, code from `top`; w and h are the panel's outer size */
export const codeLayout = (code: string, x: number, y: number, fs = 30, lh = Math.round(fs * 1.38)) => {
  const lines = code.replace(/\n$/, '').split('\n');
  const cols = Math.max(...lines.map((l) => l.length));
  const gutter = fs * 2.4;
  const padL = 34;
  const top = 76;
  const w = padL + gutter + cols * fs * MONO_ADVANCE + 30;
  const h = top + lines.length * lh + 16;
  /** world point at the left/centre of line i (to aim arrows or the camera at a line) */
  const lineAt = (i: number) => ({x: x + padL + gutter, y: y + top + i * lh + lh / 2});
  return {lines, cols, gutter, padL, top, w, h, lh, fs, lineAt};
};

export const CodePanel: React.FC<{
  fr: number; x: number; y: number; code: string; fs?: number; lh?: number; title?: string; badge?: string; o?: number;
  reveal?: [number, number, number][]; active?: [number, number, number][]; pulse?: [number, number][]; dimOthers?: boolean;
}> = ({fr, x, y, code, fs = 30, lh, title = 'solution.cpp', badge, o = 1, reveal, active = [], pulse = [], dimOthers = true}) => {
  const lay = codeLayout(code, x, y, fs, lh);
  if (o <= 0.002) return null;
  const shown = (i: number) => {
    if (!reveal) return 1;
    const r = reveal.find(([a, b]) => i >= a && i <= b);
    if (!r) return 0;
    return ease(fr, r[2] + (i - r[0]) * 2, 10, EASE.out);
  };
  // active range: glide between keyed ranges
  const keys: [number, {a: number; b: number; o: number}][] = [[0, {a: 0, b: 0, o: 0}]];
  for (const [at, a, b] of active) keys.push([at, b < 0 ? {a: keys[keys.length - 1][1].a, b: keys[keys.length - 1][1].b, o: 0} : {a, b, o: 1}]);
  const act = track(fr, keys, 9, EASE.inOut);
  const anyActive = act.o > 0.02;
  // the surfaces under an active line (accent bar, strongest at its left end) and a pulsed one (mint flash)
  const barSurface = mix(S.codeTop, C.accent, 0x38 / 255);
  const barCols = colsOn(barSurface);
  // a pulse can sit on the active bar or on a plain line, and fades in and out: its text clears all of them
  const pa = parseInt(S.pulseA, 16) / 255;
  const pulseCols = colsOnAll([barSurface, S.codeTop, mix(barSurface, C.mint, pa), mix(S.codeTop, C.mint, pa)]);
  return (
    <div style={{position: 'absolute', left: x, top: y, width: lay.w, height: lay.h, opacity: o, borderRadius: 26,
      background: `linear-gradient(180deg, ${S.codeTop}, ${S.codeBot})`, border: `1.5px solid ${C.line}`, boxShadow: SHADOW.card,
      fontFeatureSettings: NO_LIGA, fontVariantLigatures: 'none'}}>
      <div style={{position: 'absolute', left: 28, top: 0, height: 66, display: 'flex', alignItems: 'center', gap: 22}}>
        <Dots />
        <div style={{fontFamily: FONT.mono, fontWeight: 700, fontSize: SIZE.small, color: C.ink}}>{title}</div>
        {badge && <div style={{fontFamily: FONT.mono, fontWeight: 700, fontSize: SIZE.small, color: inkOn(C.accentText, mix(S.codeTop, C.accent, 0x22 / 255)), padding: '2px 12px', borderRadius: 8, background: C.accent + '22'}}>{badge}</div>}
      </div>
      <div style={{position: 'absolute', left: 0, top: 66, width: lay.w, height: 1.5, background: C.line}} />
      {anyActive && (
        <div style={{position: 'absolute', left: 14, top: lay.top + act.a * lay.lh - 3, width: lay.w - 28, height: (act.b - act.a + 1) * lay.lh + 6, borderRadius: 10, opacity: act.o,
          background: `linear-gradient(90deg, ${C.accent}38, ${C.accent}0C)`, borderLeft: `5px solid ${mark(C.accent)}`, boxShadow: halo(C.accent, 30, -8, '88')}} />
      )}
      {pulse.map(([at, li], k) => {
        const b = bump(fr, at, 10, 4, 14);
        if (b <= 0) return null;
        return <div key={k} style={{position: 'absolute', left: 14, top: lay.top + li * lay.lh - 3, width: lay.w - 28, height: lay.lh + 6, borderRadius: 10, opacity: b, background: `${C.mint}${S.pulseA}`, border: `2px solid ${hlEdge(C.mint)}`}} />;
      })}
      {lay.lines.map((ln, i) => {
        const r = shown(i);
        const inAct = i >= Math.round(act.a) && i <= Math.round(act.b);
        const dim = dimOthers && anyActive && !inAct ? (1 - CODE_DIM) * act.o : 0;
        const on = inAct && anyActive;
        const pulsed = pulse.some(([at, li]) => li === i && bump(fr, at, 10, 4, 14) > 0);
        return (
          <div key={i} style={{position: 'absolute', left: lay.padL, top: lay.top + i * lay.lh, height: lay.lh, display: 'flex', alignItems: 'center',
            fontFamily: FONT.mono, fontSize: fs, fontWeight: on ? 700 : 500, whiteSpace: 'pre', letterSpacing: 0, opacity: clamp01(r), transform: `translateX(${(1 - r) * -18}px)`}}>
            <span style={{color: on ? inkOn(ink(C.accent), barSurface) : C.faint, width: lay.gutter - fs * 0.8, display: 'inline-block', textAlign: 'right', marginRight: fs * 0.8, fontWeight: 700}}>{i + 1}</span>
            <span style={{opacity: 1 - dim}}>{highlight(ln, pulsed ? pulseCols : on ? barCols : CODE_COL)}</span>
          </div>
        );
      })}
    </div>
  );
};
