// Revideo project: loads the fonts locally (@fontsource), waits for them, and renders one continuous scene
// (src/film.tsx) whose length is the voice timing's total. Size and fps come from the timing file too.
import {makeProject} from '@revideo/core';
import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';
import '@fontsource/inter/600.css';
import '@fontsource/inter/700.css';
import '@fontsource/inter/800.css';
import '@fontsource/jetbrains-mono/500.css';
import '@fontsource/jetbrains-mono/600.css';
import '@fontsource/jetbrains-mono/700.css';
import '@fontsource/jetbrains-mono/800.css';
import '@fontsource/bangers/400.css';
import {TIMING} from './timing';
import {C} from './kit/theme';
import film from './film?scene';

// Wait for every face before the first frame is measured or drawn (otherwise early frames use a fallback).
const SAMPLE = 'Aa0123456789→∞≤≥·[](){}!=<>+-';
await Promise.all([
  ...['400', '500', '600', '700', '800'].map(w => document.fonts.load(`${w} 40px "Inter"`, SAMPLE)),
  ...['500', '600', '700', '800'].map(w => document.fonts.load(`${w} 40px "JetBrains Mono"`, SAMPLE)),
  document.fonts.load('400 40px "Bangers"', 'POP!700'),
  // system Inter Display where installed (the theme falls back to Inter where it is not)
  ...['700', '800'].map(w => document.fonts.load(`${w} 40px "Inter Display"`).catch(() => [])),
]);
await document.fonts.ready;

export default makeProject({
  scenes: [film],
  settings: {
    shared: {size: {x: TIMING.width, y: TIMING.height}, background: C.bg},
    rendering: {fps: TIMING.fps},
  },
});
