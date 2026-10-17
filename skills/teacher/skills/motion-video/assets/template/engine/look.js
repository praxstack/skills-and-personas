// engine/look.js: the palette and the type scale. The ONE place colours and sizes are decided.
//
// Colours have the same keys as a registry theme (references/themes.md), so a theme drops in unchanged:
//   surfaces  bg, bg2, deep, panel, panel2, line, line2
//   text      text > muted > dim (all pass 4.5:1 on every surface; text passes 7:1)
//   fills     accent, warm, good, bad, cool, gold, violet      areas and thick strokes, never text
//   inks      accentInk ... violetInk                           text and thin strokes in a hue
//   on-fills  onAccent ... onViolet                             a label sitting on that fill
//
// window.THEME (theme.js, loaded first) is null in the template: the film then uses one of the two original
// looks below, picked by film.json "style.look" ("paper", light, the default; or "ink", dark). Both were solved
// with theme.py's own rules, so every ink clears its target on every surface. A registry theme
// (`theme.py emit <id> --format global --out source/theme.js`) replaces them entirely.
(function () {
  const LOOKS = {
    paper: {
      id: 'paper', name: 'Paper', tone: 'light',
      bg: '#F4EFE6', bg2: '#F1E6DB', deep: '#ECE5D9', panel: '#FFFCF6', panel2: '#F1EEE9', line: '#E2D9CA', line2: '#B7AFA3',
      text: '#1D1B18', muted: '#5A5348', dim: '#6B655D',
      accent: '#C4512F', accentInk: '#AA4629', onAccent: '#FFFFFF',
      warm: '#E0892E', warmInk: '#945616', onWarm: '#1D1B18',
      good: '#2F7D57', goodInk: '#2B714F', onGood: '#F7F7F7',
      bad: '#C23B3B', badInk: '#B73838', onBad: '#F4EFE6',
      cool: '#2C6E91', coolInk: '#2B6C8E', onCool: '#F4EFE6',
      gold: '#D9A332', goldInk: '#815F18', onGold: '#1D1B18',
      violet: '#6A55B0', violetInk: '#6A55B0', onViolet: '#F4EFE6',
      lights: ['#E0892E', '#D9A332', '#C23B3B', '#C4512F', '#6A55B0', '#2F7D57'],
      shadow: '#2A2219',
    },
    ink: {
      id: 'ink', name: 'Ink', tone: 'dark',
      bg: '#111214', bg2: '#1E1817', deep: '#0B0C0D', panel: '#1B1D22', panel2: '#282A2E', line: '#2C3038', line2: '#585A5E',
      text: '#F3EFE7', muted: '#B8B1A5', dim: '#96928B',
      accent: '#F0714A', accentInk: '#F0714A', onAccent: '#111214',
      warm: '#F5A75A', warmInk: '#F5A75A', onWarm: '#111214',
      good: '#5FC795', goodInk: '#5FC795', onGood: '#111214',
      bad: '#F06A6A', badInk: '#F06A6A', onBad: '#111214',
      cool: '#5DB3E6', coolInk: '#5DB3E6', onCool: '#111214',
      gold: '#F2C55C', goldInk: '#F2C55C', onGold: '#111214',
      violet: '#A996F2', violetInk: '#A996F2', onViolet: '#111214',
      lights: ['#F5A75A', '#F2C55C', '#F06A6A', '#F0714A', '#A996F2', '#5FC795'],
      shadow: '#000000',
    },
  };
  const HUES = ['accent', 'warm', 'good', 'bad', 'cool', 'gold', 'violet'];

  // Type: sizes in px at 1080 on the frame's short side (the engine multiplies by M.u). Nothing below 28:
  // the gate's floor is 26 px, and a block that has to shrink text to fit stops at its own floor and warns.
  const TYPE = {
    serif: '"Fraunces", Georgia, serif',
    sans: '"Inter", system-ui, sans-serif',
    mono: '"JetBrains Mono", ui-monospace, monospace',
    kicker: 30, title: 104, titleTall: 112, sub: 44, statement: 76, statementTall: 70, body: 44, label: 34,
    small: 30, caption: 44, captionTall: 50, code: 34, stat: 210, statTall: 190, chart: 32, chrome: 28, min: 28,
  };

  window.LOOK = {
    LOOKS, HUES, TYPE,
    /** The palette for this film: the registry theme if theme.js set one, else the original look it names. */
    palette(style) {
      const name = (style && style.look) || 'paper';
      if (window.THEME) return { ...window.THEME, registry: true };
      if (!LOOKS[name]) throw new Error(`film.json style.look "${name}" is not a look (paper or ink); for the 30 registry themes use theme.py emit`);
      return { ...LOOKS[name], registry: false };
    },
  };
})();
