// The composition: layers from back to front. Generic: a new film changes scenes/, not this file.
//   Backdrop (light, parallax grid) -> World (camera: subject + world scenes) -> Dust (parallax > 1)
//   -> HUD scenes -> chapter tag/progress -> chapter stings -> captions -> grain + vignette
import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {useFontsReady} from './kit/fonts';
import {C, FONT, NO_LIGA} from './kit/tokens';
import {Backdrop, Dust, Finish} from './kit/Backdrop';
import {World} from './kit/Camera';
import {Captions} from './kit/Captions';
import {ChapterProgress, ChapterStings, ChapterTag} from './kit/Chapter';
import {cameraAt, SceneHud, SceneWorld, Subject} from './scenes';

export const Film: React.FC = () => {
  useFontsReady();
  const fr = useCurrentFrame();
  const cam = cameraAt(fr);
  return (
    <AbsoluteFill style={{background: C.bg, fontFamily: FONT.sans, fontFeatureSettings: NO_LIGA, fontVariantLigatures: 'none', overflow: 'hidden'}}>
      <style>{'*, *::before, *::after { box-sizing: border-box; }'}</style>
      <Backdrop fr={fr} cam={cam} />
      <World cam={cam}>
        <Subject />
        <SceneWorld />
      </World>
      <Dust fr={fr} cam={cam} />
      <SceneHud cam={cam} />
      <ChapterTag />
      <ChapterProgress />
      <ChapterStings />
      <Captions />
      <Finish fr={fr} />
    </AbsoluteFill>
  );
};
