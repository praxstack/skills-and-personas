// Camera for a 2D film: the world (subject + panels that live "on the table") is one 1920x1080 layer that the
// camera pushes into, pulls out of and drifts across. HUD layers (captions, cards, bursts) are not moved.
//
//   const cam = camera(fr, [
//     [0,              CAM_HOME],
//     [f('p4', 2.2),   {x: 1500, y: 480, z: 1.25}],      // push in on the answer
//     [fEnd('p4', -0.6), CAM_HOME, 20],                   // pull back (20-frame move)
//   ]);
//   <World cam={cam}>...</World>
import React from 'react';
import {AbsoluteFill} from 'remotion';
import {drift, track} from '../lib/motion';

/** x, y: the world point at the centre of the screen; z: zoom; r: roll in degrees */
export type Cam = {x: number; y: number; z: number; r: number};
export const CAM_HOME: Cam = {x: 960, y: 540, z: 1, r: 0};

type CamKey = [number, Partial<Cam>, number?];

/** keyframed camera (eased, continuous) plus a slow drift so holds never look frozen */
export const camera = (fr: number, keys: CamKey[], driftAmp = 7): Cam => {
  const full = keys.map(([at, c, d]) => [at, {...CAM_HOME, ...c}, d] as [number, Cam, number?]);
  const c = track(fr, full, 36);
  const d = drift(fr, driftAmp, 1, 1.7);
  return {x: c.x + d.x, y: c.y + d.y, z: c.z * (1 + 0.006 * Math.sin(fr / 30 * 0.21)), r: c.r};
};

/** the camera-transformed world layer */
export const World: React.FC<{cam: Cam; children: React.ReactNode}> = ({cam, children}) => (
  <AbsoluteFill
    style={{
      transformOrigin: '0 0',
      transform: `translate(960px, 540px) rotate(${cam.r}deg) scale(${cam.z}) translate(${-cam.x}px, ${-cam.y}px)`,
    }}
  >
    {children}
  </AbsoluteFill>
);

/** world point -> screen point under a camera (to anchor HUD things, e.g. a burst, on a world object) */
export const toScreen = (cam: Cam, p: {x: number; y: number}) => {
  const a = (cam.r * Math.PI) / 180;
  const dx = (p.x - cam.x) * cam.z;
  const dy = (p.y - cam.y) * cam.z;
  return {x: 960 + dx * Math.cos(a) - dy * Math.sin(a), y: 540 + dx * Math.sin(a) + dy * Math.cos(a)};
};
