// Depth and light: stage gradient, drifting warm/cool key lights (per chapter under a theme), a dot grid with camera parallax, floating
// dust in front (parallax > 1), film grain and a vignette. Cheap to render: gradients and one tiled PNG,
// no blur filters.
import React from 'react';
import {AbsoluteFill, staticFile} from 'remotion';
import {FPS, TIMING, toF} from '../lib/timing';
import {ease, rand} from '../lib/motion';
import {mix} from './color';
import {C, keyLights, S, THEMED} from './tokens';
import type {Cam} from './Camera';

/** the key lights at frame fr: a theme gives each chapter its own pair (tokens.keyLights), cross-fading over the
 *  0.8 s chapter gap; the original keeps accent and cyan throughout */
const lightsAt = (fr: number): [string, string] => {
  if (!THEMED) return keyLights(0);
  let n = 0;
  let k = 1;
  for (const c of TIMING.chapters) {
    const at = toF(c.start);
    if (fr >= at - toF(0.8)) {
      n = c.n;
      k = ease(fr, at - toF(0.8), toF(0.8));
    }
  }
  const [w0, c0] = keyLights(Math.max(0, n - 1));
  const [w1, c1] = keyLights(n);
  return [mix(w0, w1, k), mix(c0, c1, k)];
};

export const Backdrop: React.FC<{fr: number; cam: Cam; warm?: string; cool?: string}> = ({fr, cam, ...lit}) => {
  const [w, c] = lightsAt(fr);
  const warm = lit.warm ?? w;
  const cool = lit.cool ?? c;
  const t = fr / FPS;
  const px = -(cam.x - 960) * 0.35;
  const py = -(cam.y - 540) * 0.35;
  const ps = 1 + (cam.z - 1) * 0.35;
  return (
    <AbsoluteFill style={{background: `radial-gradient(ellipse 80% 70% at 55% 45%, ${C.bgLift} 0%, ${C.bg} 70%)`, overflow: 'hidden'}}>
      {/* key lights */}
      <div style={{position: 'absolute', left: -520 + Math.sin(t * 0.09) * 140 + px * 0.5, top: -760 + Math.cos(t * 0.07) * 90 + py * 0.5, width: 1800, height: 1800, borderRadius: '50%',
        background: `radial-gradient(circle, ${warm}24 0%, ${warm}0D 35%, ${warm}00 65%)`}} />
      <div style={{position: 'absolute', right: -700 + Math.cos(t * 0.06) * 150 - px * 0.5, bottom: -900 + Math.sin(t * 0.05) * 100 - py * 0.5, width: 2000, height: 2000, borderRadius: '50%',
        background: `radial-gradient(circle, ${cool}1C 0%, ${cool}0A 35%, ${cool}00 65%)`}} />
      {/* dot grid, moves with the camera at 0.35x (parallax) */}
      <div style={{position: 'absolute', inset: -200, transform: `translate(${px}px, ${py}px) scale(${ps})`,
        backgroundImage: `radial-gradient(${S.dotGrid} 1.6px, transparent 2px)`, backgroundSize: '44px 44px',
        WebkitMaskImage: 'radial-gradient(ellipse 65% 60% at 50% 48%, black 10%, transparent 80%)'}} />
      {/* horizon line for a sense of floor */}
      <div style={{position: 'absolute', left: 0, right: 0, top: 820 + py * 0.6, height: 260,
        background: S.horizon}} />
      {S.groundVignette !== 'none' && <AbsoluteFill style={{background: S.groundVignette}} />}
    </AbsoluteFill>
  );
};

/** floating dust in front of the subject: parallax 1.3x, slow rise */
export const Dust: React.FC<{fr: number; cam: Cam; n?: number; color?: string}> = ({fr, cam, n = 18, color = S.dust}) => {
  const t = fr / FPS;
  const px = -(cam.x - 960) * 1.3;
  const py = -(cam.y - 540) * 1.3;
  return (
    <AbsoluteFill style={{pointerEvents: 'none', overflow: 'hidden'}}>
      {Array.from({length: n}, (_, i) => {
        const r = 2 + rand(i, 1) * 7;
        const x = ((rand(i, 2) * 2200 + px + Math.sin(t * 0.3 + i) * 30) % 2200 + 2200) % 2200 - 140;
        const y = ((rand(i, 3) * 1300 - t * (8 + rand(i, 4) * 16) + py) % 1300 + 1300) % 1300 - 110;
        const o = 0.08 + rand(i, 5) * 0.18;
        return <div key={i} style={{position: 'absolute', left: x, top: y, width: r * 2, height: r * 2, borderRadius: '50%', opacity: o,
          background: `radial-gradient(circle, ${color} 0%, ${color}00 70%)`}} />;
      })}
    </AbsoluteFill>
  );
};

/**
 * grain and vignette: the last layers, over everything. Under a theme the vignette moves onto the ground (Backdrop,
 * toward `deep`) so it never washes out text, and on a light theme the grain multiplies (brightened so it only adds
 * dark specks). The grain is a static texture on purpose: animated
 * noise multiplies the H.264 bitrate several times over (every frame differs everywhere).
 */
export const Finish: React.FC<{fr: number; grain?: number}> = ({grain = S.grain}) => (
  <AbsoluteFill style={{pointerEvents: 'none'}}>
    {S.vignette !== 'none' && <AbsoluteFill style={{background: S.vignette}} />}
    <AbsoluteFill style={{opacity: grain, backgroundImage: `url(${staticFile('grain.png')})`, backgroundSize: '256px 256px',
      mixBlendMode: S.grainBlend as React.CSSProperties['mixBlendMode'], ...(S.grainFilter !== 'none' ? {filter: S.grainFilter} : {})}} />
  </AbsoluteFill>
);
