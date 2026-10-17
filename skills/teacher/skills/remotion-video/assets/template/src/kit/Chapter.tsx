// Chapter furniture, all driven by TIMING.chapters (no props needed):
//   <ChapterStings />  a comic band ("02 · BRUTE FORCE") that lives in the gap between chapters: it sweeps in when
//                      the previous chapter ends and is gone the frame before the next one starts. It only ever
//                      sweeps over empty ground: the subject fades out at the previous chapter's last word, moves
//                      while invisible (gapMove) and fades back in at its new place once the band has left
//                      (subjectShown, applied to placeAt's opacity). So end a chapter's content by chapterEnd (fEnd of
//                      its last line) and start the next chapter's content at chapterStart(n) or later.
//   <ChapterTag />     the persistent lower third in the top-left corner ("02  BRUTE FORCE"); its box spans
//                      y 88-138 and its text starts below y 96 (SAFE.top), so scenes start at y 150; it fades out
//                      when the next chapter's sting arrives
//   <ChapterProgress /> one bar per chapter in the top-right corner, filling as the chapter plays
import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {FPS, TIMING, chapterAt, toF} from '../lib/timing';
import {clamp01, ease, EASE, lerp, pop, rand} from '../lib/motion';
import {alpha} from './color';
import {C, FONT, S, SAFE, SIZE, STING_END, ink, mark, sh} from './tokens';

const num = (n: number) => String(n).padStart(2, '0');
/** the corner tag's box: its text is centred, so the glyphs start at about SAFE.top */
const TAG = {top: SAFE.top - 8, h: 50};
const chapters = () => TIMING.chapters.filter((c) => c.n > 0);

/** when chapter n's sting runs (frames): inside the gap between chapters (voice.py --chapter-gap, 0.8 s by
 *  default; used up to 1 s). It sweeps in when the previous chapter ends, holds, then wipes left to right and is
 *  gone the frame before chapterStart(n), so it never covers content of either chapter that is still on screen. */
export const stingTimes = (n: number) => {
  const c = TIMING.chapters.find((x) => x.n === n);
  const at = toF(c ? c.start : 0);
  const prev = TIMING.chapters.find((x) => x.n === n - 1);
  const gap = prev ? at - toF(prev.end) : toF(0.8);
  const a = at - Math.min(toF(1.0), Math.max(toF(0.6), gap));
  const gone = at - 1;
  return {a, hold: gone - 7, gone};
};

/** the subject's fade around chapter n's sting: out from the previous chapter's last word until the band arrives,
 *  back in over 0.4 s once the band has gone (frames). Chapter 1's sting needs none: the subject is not on yet. */
const subjectGap = (n: number) => {
  const {a, gone} = stingTimes(n);
  const prev = TIMING.lines.filter((l) => l.chapter === n - 1).pop();
  const said = prev ? toF(prev.voiceAt + prev.voiceDur) : a - toF(0.3);
  const out0 = Math.min(a - 4, Math.max(a - toF(0.5), said)); // at least 4 frames, at most 0.5 s of fade
  return {out0, a, in0: gone + 1, in1: gone + 1 + toF(0.4)};
};

/** 0..1 opacity factor for the persistent subject: 0 whenever a chapter sting is on screen (chapters 2 and up), so
 *  the band never covers it. Multiply the subject's place.o by it. */
export const subjectShown = (fr: number) =>
  chapters().filter((c) => c.n >= 2).reduce((k, c) => {
    const g = subjectGap(c.n);
    const out = ease(fr, g.out0, g.a - g.out0, EASE.in);
    const back = ease(fr, g.in0, g.in1 - g.in0, EASE.out);
    return k * (1 - out * (1 - back));
  }, 1);

/** a placeAt key that moves the subject to `place` while it is invisible under chapter n's sting */
export const gapMove = <T,>(n: number, place: T): [number, T, number] => {
  const {a, gone} = stingTimes(n);
  return [a, place, Math.max(1, gone - a)];
};

export const Sting: React.FC<{fr: number; n: number; name: string; color?: string}> = ({fr, n, name, color = C.accent}) => {
  const {a, hold, gone} = stingTimes(n);
  if (fr < a || fr > gone + 1) return null;
  const kin = ease(fr, a, 6, EASE.out);
  const kout = ease(fr, hold, gone - hold, EASE.in);
  const dim = kin * (1 - kout);
  const txt = pop(fr, a + 1);
  // the text fades where it is, drifting a little toward the corner tag that takes over; it never flies across
  // the new chapter's content (a flying title crossed the question card and the code panel)
  const fly = ease(fr, hold, 4, EASE.in);
  const tx = lerp(0, -60, fly);
  const ty = lerp(0, -30, fly);
  const ts = lerp(1, 0.9, fly);
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      {/* a light dim: the subject under the band keeps 4.5:1 (amber, mint and ink text on it) */}
      <AbsoluteFill style={{background: S.stingDim, opacity: dim}} />
      <div style={{position: 'absolute', left: -60, right: -60, top: 350, height: 300, transform: 'rotate(-3.5deg)',
        clipPath: `inset(0 ${(1 - kin) * 100}% 0 ${kout * 100}%)`,
        background: `linear-gradient(90deg, ${color} 0%, ${S.stingMid} 60%, ${STING_END} 130%)`, borderTop: `9px solid ${C.bg}`, borderBottom: `9px solid ${C.bg}`,
        boxShadow: `0 30px 80px ${sh(0.6)}`}}>
        <AbsoluteFill style={{backgroundImage: `radial-gradient(${S.stingDots} 3px, transparent 3.6px)`, backgroundSize: '18px 18px'}} />
        {Array.from({length: 9}, (_, i) => {
          const y = 20 + rand(i, n) * 240;
          const w = 160 + rand(i, n + 3) * 380;
          const x = ((1 - ((fr - a) / 26 + rand(i, n + 7))) % 1) * 2400 - 300;
          return <div key={i} style={{position: 'absolute', left: x, top: y, width: w, height: 5, borderRadius: 3, background: S.stingStreak}} />;
        })}
      </div>
      <div style={{position: 'absolute', left: 0, right: 0, top: 350, height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 44,
        transform: `translate(${tx}px, ${ty}px) rotate(-3.5deg) scale(${ts})`, opacity: clamp01(txt) * (1 - fly)}}>
        <div style={{fontFamily: FONT.comic, fontSize: 250, lineHeight: 1, color: S.stingText, transform: `translateX(${(1 - txt) * -80}px)`,
          textShadow: `7px 7px 0 ${S.stingShadow}`, paddingTop: 30}}>{num(n)}</div>
        <div style={{fontFamily: FONT.sans, fontWeight: 900, fontStyle: 'italic', fontSize: 112, letterSpacing: '-0.02em', textTransform: 'uppercase',
          color: S.stingText, lineHeight: 0.95, maxWidth: 1250, transform: `translateX(${(1 - pop(fr, a + 3)) * 120}px)`}}>{name}</div>
      </div>
    </AbsoluteFill>
  );
};

export const ChapterStings: React.FC<{color?: string}> = ({color}) => {
  const fr = useCurrentFrame();
  return <>{chapters().map((c) => <Sting key={c.n} fr={fr} n={c.n} name={c.name} color={color} />)}</>;
};

export const ChapterTag: React.FC = () => {
  const fr = useCurrentFrame();
  const c = chapterAt(fr);
  if (c.n === 0) return null;
  const at = toF(c.start); // pops in as the sting has wiped away
  const next = TIMING.chapters.find((x) => x.n === c.n + 1);
  const leave = next ? ease(fr, stingTimes(next.n).a, 6, EASE.in) : 0; // gone as the next sting sweeps in
  const k = pop(fr, at) * (1 - leave);
  if (k <= 0) return null;
  return (
    <div style={{position: 'absolute', left: SAFE.x, top: TAG.top, height: TAG.h, display: 'flex', alignItems: 'center', gap: 16, padding: '0 26px 0 18px',
      borderRadius: 14, background: S.glass, border: `1.5px solid ${C.line2}`, boxShadow: `0 12px 30px -10px ${sh(0.8)}`,
      opacity: clamp01(k), transform: `translateX(${(1 - k) * -30}px)`}}>
      <div style={{width: 6, alignSelf: 'stretch', margin: '10px 0', borderRadius: 3, background: C.accent}} />
      {/* accentText, not the plain accent: under the corner vignette #FF5B2E measured 3.6:1 (a theme maps both to the same ink) */}
      <div style={{fontFamily: FONT.comic, fontSize: 40, color: C.accentText, lineHeight: 1, paddingTop: 4}}>{num(c.n)}</div>
      <div style={{fontFamily: FONT.sans, fontWeight: 800, fontSize: SIZE.label, letterSpacing: '0.12em', textTransform: 'uppercase', color: C.ink, lineHeight: 1}}>{c.name}</div>
    </div>
  );
};

export const ChapterProgress: React.FC = () => {
  const fr = useCurrentFrame();
  const t = fr / FPS;
  const cs = chapters();
  const first = cs[0];
  if (!first) return null;
  const o = ease(fr, toF(first.start) + toF(0.8), 15);
  if (o <= 0) return null;
  return (
    <div style={{position: 'absolute', right: SAFE.x, top: TAG.top + TAG.h / 2 - 4, display: 'flex', gap: 10, opacity: o}}>
      {cs.map((c) => {
        const p = clamp01((t - c.start) / Math.max(0.01, c.end - c.start));
        const on = t >= c.start && t < c.end;
        return (
          <div key={c.n} style={{width: 64, height: 9, borderRadius: 5, background: alpha(C.ink, 0.14), overflow: 'hidden'}}>
            <div style={{width: `${p * 100}%`, height: '100%', background: on ? mark(C.accent) : alpha(mark(C.accent), 0.55)}} />
          </div>
        );
      })}
    </div>
  );
};
