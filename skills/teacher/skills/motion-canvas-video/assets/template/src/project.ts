import {makeProject} from '@motion-canvas/core';
import '@fontsource/inter/400.css';
import '@fontsource/inter/600.css';
import '@fontsource/inter/800.css';
import '@fontsource/jetbrains-mono/400.css';
import '@fontsource/jetbrains-mono/700.css';
import '@fontsource/bangers/400.css';
import film from './scenes/film?scene';

await Promise.all(
  ['400 40px Inter', '600 40px Inter', '800 40px Inter', '400 40px "JetBrains Mono"', '700 40px "JetBrains Mono"', '400 40px Bangers'].map(f =>
    document.fonts.load(f),
  ),
);

export default makeProject({
  scenes: [film],
  experimentalFeatures: true, // Code drawHooks (unselected code lines stay readable)
  audio: import.meta.env.DEV ? '/narration.wav' : undefined,
});
