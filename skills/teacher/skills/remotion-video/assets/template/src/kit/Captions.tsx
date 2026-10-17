// Caption band: the bottom 180 px; the text is bottom-anchored 96 px above the frame edge. Shows the current line's `cap` from just before its voice starts until the
// next line takes over; wraps to at most two balanced lines. Reads TIMING directly, so it needs no props.
import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {FPS, TIMING} from '../lib/timing';
import {clamp01} from '../lib/motion';
import {C, FONT, S, SAFE, SIZE} from './tokens';
import {RichText} from './Panel';

export const Captions: React.FC<{size?: number}> = ({size = SIZE.caption}) => {
  const fr = useCurrentFrame();
  const t = fr / FPS;
  const lines = TIMING.lines;
  let i = -1;
  for (let k = 0; k < lines.length; k++) if (t >= lines[k].voiceAt - 0.12) i = k;
  const band = clamp01((t - (lines[0]?.voiceAt ?? 0) + 0.4) / 0.4);
  if (i < 0) return null;
  const ln = lines[i];
  const next = lines[i + 1];
  const until = next ? Math.min(ln.end, next.voiceAt - 0.12) : ln.end;
  const inK = clamp01((t - (ln.voiceAt - 0.12)) / 0.18);
  const outK = clamp01((until - t) / 0.15);
  const o = Math.min(inK, outK);
  const long = ln.cap.length > 96;
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: 210, opacity: band,
        background: S.capBand}} />
      {/* bottom-anchored at SAFE.bottom (y 984, 96 px above the edge): one line sits at y 929-980, two lines reach up to y 878 */}
      <div style={{position: 'absolute', left: 120, right: 120, top: SAFE.captionTop - 60, bottom: 1080 - SAFE.bottom + 4, display: 'flex', alignItems: 'flex-end', justifyContent: 'center'}}>
        <div style={{opacity: o, transform: `translateY(${(1 - inK) * 10}px)`, maxWidth: 1640, textAlign: 'center', textWrap: 'balance',
          fontFamily: FONT.sans, fontWeight: 600, fontSize: long ? size - 4 : size, lineHeight: 1.28, color: C.ink, letterSpacing: '-0.005em',
          textShadow: S.capHalo} as React.CSSProperties}>
          <RichText text={ln.cap} />
        </div>
      </div>
    </AbsoluteFill>
  );
};
