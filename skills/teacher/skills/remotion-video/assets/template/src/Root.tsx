import React from 'react';
import {Composition} from 'remotion';
import {Film} from './Film';
import {FPS, HEIGHT, TOTAL_FRAMES, WIDTH} from './lib/timing';

// One composition: the whole film. Its length is the voice timing's total, exactly.
export const Root: React.FC = () => (
  <Composition id="Film" component={Film} durationInFrames={TOTAL_FRAMES} fps={FPS} width={WIDTH} height={HEIGHT} />
);
