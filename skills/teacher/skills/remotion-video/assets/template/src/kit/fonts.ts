// Fonts are bundled from npm (@fontsource), never fetched from Google Fonts (blocked in some sandboxes, and a
// network font can arrive after the first frames render). useFontsReady() holds the render with delayRender
// until every face below has loaded, so frame 0 is already in the right font.
import {useEffect, useState} from 'react';
import {continueRender, delayRender} from 'remotion';
import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';
import '@fontsource/inter/600.css';
import '@fontsource/inter/700.css';
import '@fontsource/inter/800.css';
import '@fontsource/inter/900.css';
import '@fontsource/inter/900-italic.css'; // numbers in comic bursts (Bangers' 7 reads as a 1)
import '@fontsource/instrument-serif/400.css';
import '@fontsource/instrument-serif/400-italic.css';
import '@fontsource/jetbrains-mono/400.css';
import '@fontsource/jetbrains-mono/700.css';
import '@fontsource/jetbrains-mono/800.css';
import '@fontsource/bangers/400.css';

const FACES = [
  '400 40px Inter', '500 40px Inter', '600 40px Inter', '700 40px Inter', '800 40px Inter', '900 40px Inter', 'italic 900 40px Inter',
  '400 40px "Instrument Serif"', 'italic 400 40px "Instrument Serif"',
  '400 40px "JetBrains Mono"', '700 40px "JetBrains Mono"', '800 40px "JetBrains Mono"',
  '400 40px Bangers',
];

export const useFontsReady = () => {
  const [handle] = useState(() => delayRender('Loading fonts'));
  useEffect(() => {
    Promise.all(FACES.map((face) => document.fonts.load(face, 'AaBb 0123 !=<=')))
      .then(() => document.fonts.ready)
      .then(() => continueRender(handle))
      .catch((e) => {
        console.error('font load failed', e);
        continueRender(handle);
      });
  }, [handle]);
};
