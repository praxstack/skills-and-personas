// kit/styles/index.js: the style interface. A style changes HOW things are drawn (strokes, fills, textures,
// labels, motion); the scenes and the subject stay the same, so one scenes.js serves every style.
//
// The built-in styles 'paper' (default), 'chalk' and 'blueprint' live in style.js and need no file here. Every
// other style is one file, kit/styles/<name>.js, loaded by index.html before style.js:
//
//   defineStyle('whiteboard', {
//     base: 'paper',                    // built-in palette it starts from (default 'paper')
//     palette(P, T, Colour) { ... },    // REQUIRED. P = the base palette, already recoloured when a registry theme is
//                                       //   on (T = window.THEME, or null for 'original'); returns the full S token set.
//                                       //   Derive every colour from P/T with Colour.mix/alpha/ensure: no new literals.
//     font: { hand, brush },            // optional CSS family names (code always stays JetBrains Mono)
//     size: { ... },                    // optional overrides of SIZE in style.js (e.g. chapterCorner)
//     // optional hooks: the kit calls each one in place of its own drawing when the style defines it
//     beginFrame(t)                     // start of every frame (reset per-frame state; never carry state across frames)
//     stroke(ctx, pts, o)               // replaces inkLine: every rough line, edge, arrow, ring, hatch and grid line
//     penTip(ctx, x, y, color, write)   // drawText's pen position while a word is being written (local coordinates)
//     cutout(g, pts, color, o)          // replaces the paper cut-out piece (tags, bursts, stars), returns the outline
//     card(g, w, h, kind, color, seed, o) // draws a board/card sprite body (kind: note, plain, sticky, kraft, label)
//     disc(g, label, color, ink, r, font) // draws a disc sprite (chapter numbers, Q badges, tree nodes)
//     node(ctx, x, y, r, label, color, t, t0, alpha) // draws one graph node live (t0 = when it appears)
//     backdrop(g, pw, ph, rand)         // paints the padded backdrop canvas once at boot
//     overlay(ctx, t)                   // last thing drawn each frame, in screen units (after light and grain)
//     plane(ctx, o)                     // the travelling token, already placed and rotated
//     chapterLabels(o)                  // replaces the chapter-label furniture (o as in parts.js chapterLabels)
//     pop(t, t0, d)                     // replaces core.js pop(): returns {s, sx, sy} and optionally rot (radians),
//                                       //   which every piece that pops applies (papercraft-riso: a stepped drop)
//     glow(ctx, x, y, r, color, k, t, t0) // replaces a graph node's glow (r = glow radius, k = its fade, t0 = when it
//                                       //   starts; watercolor: a halo wash that blooms)
//   });
//
// Palette tokens a style may add beyond the paper set (S reads them; absent means the paper behaviour):
//   fontFiles {hand, brush}  font files for opentype lettering     fontSize(font, size)  the size a font is drawn at
//   textStroke  extra outline on settled letters, in em (marker weight)   textBoil  letter shiver multiplier
//   backDepth  backdrop parallax (1 = locked to the world)          float  graph node bob in px (paper 3)
//   stepFps  boards move on steps of this rate (stop motion; absent = smooth)
// Pick a style with STYLE_NAME in style.js (and record it: vstate.py set style=<name>); preview with ?style=<name>.
'use strict';
const STYLE_DEFS = {};
function defineStyle(name, def) { STYLE_DEFS[name] = Object.assign({ name, base: 'paper' }, def); }
