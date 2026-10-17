// Table / array rows for DP state and dry runs. Each cell is keyed: a list of [frame, value, colour?]; the cell
// shows the latest value, pops when it changes and glows for a second so the eye finds the change. One row
// is an array; rounds as rows and nodes as columns is a dry-run table. A row's `sub` (a note under its label,
// such as "old row") is set in small caps like every other label, so it reads at its full size.
//   <DPTable fr={fr} x={1240} y={560} cols={['0', '1', '2', '3']} rows={[
//     {label: 'dist', at: f('c1'), cells: [[[f('c1'), '0']], [[f('c1'), '∞'], [f('c1', 1.4), '100', C.mint]], ...]},
//   ]} />
import React from 'react';
import {clamp01, ease, pop, SPRING} from '../lib/motion';
import {alpha, mix, over} from './color';
import {C, FONT, halo, ink, inkOn, mark, S, SIZE} from './tokens';

export type CellKey = [number, string, string?];
export type DPRow = {label: string; sub?: string; at: number; cells: CellKey[][]; color?: string};

const cellAt = (fr: number, keys: CellKey[]) => {
  let cur: CellKey | null = null;
  for (const k of keys) if (fr >= k[0]) cur = k;
  return cur;
};

export const dpLayout = (x: number, y: number, ncols: number, nrows: number, cw = 112, ch = 84, labelW = 200, gap = 12, rowGap = gap) => ({
  w: labelW + ncols * (cw + gap), h: 56 + nrows * (ch + rowGap),
  /** world-space centre of a cell (to aim arrows, bursts or the camera at it) */
  cell: (r: number, c: number) => ({x: x + labelW + c * (cw + gap) + cw / 2, y: y + 56 + r * (ch + rowGap) + ch / 2}),
});

export const DPTable: React.FC<{
  fr: number; x: number; y: number; cols: string[]; rows: DPRow[]; colTitle?: string;
  cw?: number; ch?: number; fs?: number; labelW?: number; labelFs?: number; o?: number; headAt?: number; rowGap?: number;
}> = ({fr, x, y, cols, rows, colTitle, cw = 112, ch = 84, fs = 38, labelW = 200, labelFs = 34, o = 1, headAt, rowGap = 12}) => {
  const gap = 12;
  if (o <= 0.002) return null;
  const head = ease(fr, headAt ?? rows[0]?.at ?? 0, 12);
  return (
    <div style={{position: 'absolute', left: x, top: y, opacity: o}}>
      {colTitle && <div style={{position: 'absolute', left: 0, top: 4, width: labelW - 16, textAlign: 'right', fontFamily: FONT.sans, fontWeight: 800, fontSize: SIZE.label,
        letterSpacing: '0.12em', textTransform: 'uppercase', color: C.muted, opacity: head, lineHeight: 1.1}}>{colTitle}</div>}
      {cols.map((c, i) => (
        <div key={i} style={{position: 'absolute', left: labelW + i * (cw + gap), top: 0, width: cw, textAlign: 'center', fontFamily: FONT.mono, fontWeight: 800,
          fontSize: 32, color: C.muted, opacity: head, lineHeight: 1.1}}>{c}</div>
      ))}
      {rows.map((row, r) => {
        const k = pop(fr, row.at, SPRING.calm);
        if (k <= 0) return null;
        const ry = 56 + r * (ch + rowGap);
        return (
          <div key={r} style={{position: 'absolute', left: 0, top: ry, opacity: clamp01(k), transform: `translateY(${(1 - k) * 24}px)`}}>
            <div style={{position: 'absolute', left: 0, top: 0, width: labelW - 22, height: ch, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', justifyContent: 'center'}}>
              <div style={{fontFamily: FONT.mono, fontWeight: 800, fontSize: labelFs, color: ink(row.color ?? C.ink), lineHeight: 1, whiteSpace: 'nowrap'}}>{row.label}</div>
              {row.sub && <div style={{fontFamily: FONT.sans, fontWeight: 800, fontSize: 28, letterSpacing: '0.08em', textTransform: 'uppercase', color: C.muted, marginTop: 8, lineHeight: 1, whiteSpace: 'nowrap'}}>{row.sub}</div>}
            </div>
            {row.cells.map((keys, c) => {
              const cur = cellAt(fr, keys);
              const changed = cur ? keys.indexOf(cur) > 0 : false;
              const pk = cur ? pop(fr, cur[0]) : 0;
              const hot = cur && changed ? clamp01(1 - (fr - cur[0]) / 36) : 0;
              const col = cur?.[2] ?? C.ink;
              const tintA = hot > 0 ? (0x14 + hot * 0x20) / 255 : 0;
              // the value is an ink, lifted (theme only) so it keeps its contrast on the hot cell's tint
              const cellBg = over(alpha(C.ink, 0.045), C.bg);
              const valueC = inkOn(ink(col), hot > 0 ? mix(cellBg, col, tintA) : cellBg, 5.8); // popping text measures lighter
              return (
                <div key={c} style={{position: 'absolute', left: labelW + c * (cw + gap), top: 0, width: cw, height: ch, borderRadius: 16,
                  background: hot > 0 ? `${col}${Math.round(0x14 + hot * 0x20).toString(16)}` : alpha(C.ink, 0.045),
                  border: `2.5px solid ${hot > 0.05 ? mark(col) : C.line2}`, boxShadow: hot > 0 ? halo(col, 24 * hot, undefined, '99') : `inset 0 2px 0 ${S.hiSoft}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
                  {cur && (
                    <span style={{fontFamily: FONT.mono, fontWeight: 800, fontSize: cur[1].length > 3 ? fs * 0.82 : fs, color: valueC,
                      transform: `scale(${0.5 + 0.5 * pk})`, display: 'inline-block'}}>{cur[1]}</span>
                  )}
                </div>
              );
            })}
          </div>
        );
      })}
    </div>
  );
};
