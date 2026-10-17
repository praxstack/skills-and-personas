// Small building blocks: glass Panel, Label, Chip, Arrow glyph, RichText (O(...) with real superscripts,
// arrays in mono, → drawn as a vector arrow so it looks the same on every machine).
import React from 'react';
import {C, FONT, halo, ink, mark, on, S, SHADOW, SIZE, THEMED} from './tokens';

export const abs = (x: number, y: number, extra: React.CSSProperties = {}): React.CSSProperties => ({position: 'absolute', left: x, top: y, ...extra});

/** glass card with depth: gradient fill, top highlight, long soft shadow */
export const Panel: React.FC<{
  x: number; y: number; w: number; h?: number; accent?: string; style?: React.CSSProperties; children?: React.ReactNode;
}> = ({x, y, w, h, accent, style, children}) => (
  <div
    style={{
      ...abs(x, y), width: w, height: h, borderRadius: 26,
      background: `linear-gradient(180deg, ${C.panelTop}, ${C.panel})`,
      border: `1.5px solid ${accent ? mark(accent) + '88' : C.line}`,
      boxShadow: SHADOW.card + (accent ? `, ${halo(accent, 60, -18, 'AA')}` : ''),
      ...style,
    }}
  >
    {children}
  </div>
);

export const Label: React.FC<{color?: string; size?: number; style?: React.CSSProperties; children?: React.ReactNode}> = ({color = C.muted, size = SIZE.label, style, children}) => (
  <div style={{fontFamily: FONT.sans, fontSize: size, fontWeight: 800, letterSpacing: '0.16em', textTransform: 'uppercase', color: ink(color), lineHeight: 1, ...style}}>
    {children}
  </div>
);

/** window dots for code / input panels */
export const Dots: React.FC = () => (
  <div style={{display: 'flex', gap: 10}}>
    {S.dots.map((c) => (
      <div key={c} style={{width: 15, height: 15, borderRadius: 8, background: c, opacity: 0.8}} />
    ))}
  </div>
);

export const Chip: React.FC<{color: string; size?: number; solid?: boolean; style?: React.CSSProperties; children?: React.ReactNode}> = ({color, size = 30, solid, style, children}) => (
  <div
    style={{
      display: 'inline-flex', alignItems: 'center', gap: 12, padding: `${size * 0.32}px ${size * 0.7}px`, borderRadius: 999,
      background: solid ? color : chipFill(color), border: `2px solid ${solid ? color : mark(color)}`, color: solid ? on(color) : ink(color),
      fontFamily: FONT.sans, fontWeight: 800, fontSize: size, lineHeight: 1, whiteSpace: 'nowrap',
      boxShadow: halo(color, 30, -8, '88'), ...style,
    }}
  >
    {children}
  </div>
);

/** a chip's fill: a tint of its colour; under a theme the plain panel, so the inks inside keep their 4.6:1 */
const chipFill = (color: string) => (THEMED ? C.panel : color + '22');

/** a right arrow drawn as a vector (font fallback glyphs vary between machines) */
export const ArrowGlyph: React.FC<{color?: string; size?: number}> = ({color = 'currentColor', size = 1}) => (
  <svg width={`${0.95 * size}em`} height={`${0.6 * size}em`} viewBox="0 0 38 24" style={{display: 'inline-block', margin: '0 0.18em', verticalAlign: '0.02em'}}>
    <path d="M2 12 H31 M22 3 L33 12 L22 21" fill="none" stroke={color} strokeWidth={3.6} strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

/** O(n^(k+1)) -> O(n<sup>k+1</sup>), in mono. The superscript is 0.7 em: give BigO 38 px or more wherever it has
 *  one, so the exponent stays at 26 px or above. */
export const BigO: React.FC<{s: string; color?: string; style?: React.CSSProperties}> = ({s, color, style}) => {
  const parts = s.split(/\^\(([^)]*)\)|\^([A-Za-z0-9]+)/);
  const out: React.ReactNode[] = [];
  for (let i = 0; i < parts.length; i += 3) {
    if (parts[i]) out.push(<span key={i}>{parts[i]}</span>);
    const sup = parts[i + 1] ?? parts[i + 2];
    if (sup) out.push(<sup key={i + 'u'} style={{fontSize: '0.7em', marginLeft: '0.05em', verticalAlign: '0.6em', lineHeight: 0}}>{sup}</sup>);
  }
  return <span style={{fontFamily: FONT.mono, fontWeight: 700, color: color && ink(color), whiteSpace: 'nowrap', ...style}}>{out}</span>;
};

const TOKEN = /(O\((?:[^()]|\([^()]*\))*\))|(\[[^\]]*\])|(→)|(−?\d+(?:\.\d+)?)/g;

/**
 * Text with the film's typography rules: O(...) in mono with superscripts, [arrays] in mono, numbers tinted,
 * → as a vector arrow. Used by captions, cards and chips.
 */
export const RichText: React.FC<{text: string; num?: string; bigO?: string; arr?: string; arrow?: string}> = ({text, num = C.amber, bigO = C.amber, arr = C.ink, arrow = C.muted}) => {
  const out: React.ReactNode[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  let k = 0;
  TOKEN.lastIndex = 0;
  while ((m = TOKEN.exec(text))) {
    if (m.index > last) out.push(<span key={k++}>{text.slice(last, m.index)}</span>);
    if (m[1]) out.push(<BigO key={k++} s={m[1]} color={bigO} />);
    else if (m[2]) out.push(<span key={k++} style={{fontFamily: FONT.mono, fontWeight: 700, color: ink(arr), fontSize: '0.92em', whiteSpace: 'nowrap'}}>{m[2]}</span>);
    else if (m[3]) out.push(<ArrowGlyph key={k++} color={ink(arrow)} />);
    else if (m[4]) out.push(<span key={k++} style={{color: ink(num), fontWeight: 700, fontVariantNumeric: 'tabular-nums'}}>{m[4]}</span>);
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push(<span key={k++}>{text.slice(last)}</span>);
  return <>{out}</>;
};
