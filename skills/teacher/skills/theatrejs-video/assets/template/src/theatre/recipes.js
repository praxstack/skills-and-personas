// recipes.js: the moves DSA films need, written once as shot-list helpers. Each takes the builder `s`, the timing
// helpers `T` and the world, and only adds keyframes, so everything stays keyed to line ids.
import { MOOD, P, W as FW, H as FH, SAFE, CAPTION_H, TAG_ZONE } from '../kit/tokens.js';
import { projectPoint } from '../kit/stage.js';

/** a rectangle's corners in its layer, after the panel's own rotateY (panels are flattened into their layer) */
function corners(r) {
  const [x0, y0, x1, y1] = r, t = ((r.tilt || 0) * Math.PI) / 180, pp = r.persp || 1600;
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  return [[x0, y0], [x1, y0], [x0, y1], [x1, y1]].map(([x, y]) => {
    if (!t) return [x, y];
    const dx = x - cx, dy = y - cy, X = dx * Math.cos(t), Z = -dx * Math.sin(t), w = 1 - Z / pp;
    return [cx + X / w, cy + dy / w];
  });
}

export function recipes(s, T, W) {
  const G = W.graph;
  const legs = (route) => { const ids = String(route).split('-'); return ids.slice(1).map((b, i) => [ids[i], b]); };
  const edgeKey = (a, b) => G.edgeKey(a, b);

  const R = {
    /** union of rectangles [x0, y0, x1, y1]; keeps each part (with its layer and tilt) so R.focus can project them */
    union(...rs) {
      const parts = rs.flatMap((r) => r.parts || [r]);
      return Object.assign([Math.min(...rs.map((r) => r[0])), Math.min(...rs.map((r) => r[1])), Math.max(...rs.map((r) => r[2])), Math.max(...rs.map((r) => r[3]))], { parts });
    },

    /** where a rectangle (or a union) lands on screen for a camera: [x0, y0, x1, y1] in screen px */
    screenRect(rect, cam) {
      const pts = (rect.parts || [rect]).flatMap((r) => corners(r).map(([x, y]) => projectPoint(r.layer || 'subject', x, y, cam)));
      return [Math.min(...pts.map((p) => p[0])), Math.min(...pts.map((p) => p[1])), Math.max(...pts.map((p) => p[0])), Math.max(...pts.map((p) => p[1]))];
    },

    /**
     * Point the camera at a rectangle of the subject layer (layer px, e.g. G.rect([0, 1, 3]) or W.code.rect()) so it
     * fills the safe area above the caption band. zoom > 1 pushes in further, but never so far that the rectangle
     * leaves the safe area; orbit/tilt/roll add a 2.5D angle. The rectangle is checked where it really lands: panels
     * on the nearer 'panels' layer, a panel's own tilt and the orbit's perspective are all projected (screenRect), and
     * the camera is corrected until it fits. Framing by rectangles (not raw camera numbers) keeps every panel inside
     * the frame whatever the layout.
     */
    focus(rect, t, dur = 1.2, { zoom = 1, max = 1.45, min = 0.75, orbit = 0, tilt = 0, roll = 0, pad = 30, margin = 14, tag = true, ease = 'inOut', extra = {} } = {}) {
      const [x0, y0, x1, y1] = rect;
      const solve = (top) => {
        const aw = FW - 2 * SAFE, ah = FH - CAPTION_H - top - 10;     // usable area: inside the safe margins, above captions
        let k = Math.min(aw / (x1 - x0 + 2 * pad), ah / (y1 - y0 + 2 * pad)) * zoom;
        k = Math.min(max, Math.max(min, k));
        const sy = top + ah / 2;                                      // screen y of the usable area's centre
        const cam = { x: (x0 + x1) / 2 - FW / 2, y: (y0 + y1) / 2 - FH / 2 - (sy - FH / 2) / k, z: P * (1 - 1 / k), orbit, tilt, roll };
        // project and correct: shrink until the real footprint fits (margin covers the handheld drift), then centre it
        const fw = aw - 2 * margin, fh = ah - 2 * margin;
        let box;
        for (let i = 0; i < 16; i++) {
          box = R.screenRect(rect, cam);
          const f = Math.min(1, fw / (box[2] - box[0]), fh / (box[3] - box[1]));
          if (f < 0.999) { k = Math.max(0.3, k * f * 0.998); cam.z = P * (1 - 1 / k); box = R.screenRect(rect, cam); }
          const dx = SAFE + aw / 2 - (box[0] + box[2]) / 2, dy = sy - (box[1] + box[3]) / 2;
          cam.x -= dx / k; cam.y -= dy / k;
          if (f >= 0.999 && Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5) break;
        }
        return { cam, box: R.screenRect(rect, cam) };
      };
      let { cam } = solve(SAFE);
      // the chapter tag owns the top-left corner: when a part of the rectangle (each part of an R.union is checked on
      // its own, so a tall panel on the right does not count) would run under it, everything is framed below it
      const [zx0, zy0, zx1, zy1] = TAG_ZONE;
      const hits = (rect.parts || [rect]).some((r) => {
        const [a0, b0, a1, b1] = R.screenRect(r, cam);
        return a0 < zx1 && a1 > zx0 && b0 < zy1 && b1 > zy0;
      });
      if (tag && hits) ({ cam } = solve(zy1 + 4));
      Object.assign(cam, extra);
      s.cam(cam, t, dur, ease);
      return cam;
    },

    /** Sky colours to a mood from tokens.MOOD (dusk, night, neon, ember, dawn) */
    mood(name, t, dur = 1.6) {
      const m = MOOD[name]; if (!m) throw new Error(`recipes.mood: no mood "${name}" in tokens.MOOD`);
      s.to('Sky', { top: m.top, bottom: m.bottom, glow: m.glow }, t, dur, 'inOut');
    },

    /**
     * The chapter card, in the silence between chapters, and never over content:
     *   1. the last word of the previous chapter ends (vEnd); everything on screen (subject, panels, caption, tag,
     *      bursts: Content.in) fades fully out over `fade` s,
     *   2. only then does the band swipe in over the bare sky and city, holds, and swipes out,
     *   3. once it has gone, the content fades back in, at the first line's slot start (when its caption appears),
     *      fully back by the first word.
     * If the silence is too short for a `minCard` s card, the card borrows from the first line's lead silence, and
     * as a last resort the content fade-in overlaps the first word (never the card).
     * Returns { t0, end, back, shown }: t0 = content hidden, the card starts; end = the card has gone; back = the
     * content starts to return; shown = the content is fully back. Move the camera and the graph between t0 and
     * back (nobody sees it), take the old chapter's panels off by t0 and bring the new ones in at `end` or later.
     */
    chapter(n, { tag = true, fade = 0.28, fadeIn = 0.25, minCard = 0.75 } = {}) {
      const c = T.chapter(n);
      const first = T.lines.find((l) => l.chapter === n);
      const prev = T.lines[T.lines.indexOf(first) - 1];
      const voice = first.voiceAt;
      const vEnd = prev ? prev.voiceAt + prev.voiceDur : Math.max(0, voice - 1.4);
      const t0 = vEnd + 0.02 + fade;                                // the content is fully out
      const back = Math.min(Math.max(first.start, t0 + minCard), voice); // the card has gone, content returns
      const shown = back + fadeIn;
      const span = back - t0, inDur = Math.min(0.34, span * 0.4), outDur = Math.min(0.32, span * 0.38);
      s.to('Content', { in: 0 }, vEnd + 0.02, fade, 'inOut');
      s.set('Chapter', { n }, t0 - 0.01);
      s.fromTo('Chapter', { u: 0 }, { u: 0.5 }, t0, inDur, 'expoOut');
      s.to('Chapter', { u: 1 }, back - outDur, outDur, 'in');
      s.to('Content', { in: 1 }, back, fadeIn, 'out');
      if (tag) {
        s.to('ChapterTag', { in: 0 }, vEnd + 0.02, fade, 'in');
        s.set('ChapterTag', { n }, t0 + 0.05);
        s.to('ChapterTag', { in: 1 }, back, 0.45, 'expoOut');      // returns with the content: one title at a time
      }
      return { t0, end: back, back, shown };
    },

    /** a comic burst in slot i: punch in with overshoot, hold, punch out; optional camera shake. It starts `lead` s
     *  early so it has landed (full size, readable) when the word at t is spoken, and the shake hits on the word */
    burst(i, text, t, { color = 'gold', x = 1420, y = 300, rot = -8, size = 1, hold = 1.1, shake = 0.6, lead = 0.18 } = {}) {
      const k = `Burst ${i}`, t0 = t - lead;
      s.set(k, { text, color, x, y, rot, size }, t0 - 0.01);
      s.fromTo(k, { in: 0 }, { in: 1 }, t0, 0.42, 'back');
      s.to(k, { in: 0 }, t0 + 0.42 + hold, 0.25, 'backIn');
      if (shake) s.pulse('Camera', 'shake', t - 0.05, { peak: shake, up: 0.05, hold: 0.05, down: 0.45 });
    },

    /** fly token `i` along a route ("0-1-3"): edges heat up as it passes, then settle to good or bad.
     *  rings: pulse the nodes it passes; land: pulse the last node; heat: false for ghost tokens (no edge colour) */
    fly(i, route, t, dur, { result = 'good', sum = true, rings = true, heat = true, land = true } = {}) {
      const k = G.tokenKey(i), L = legs(route), per = dur / L.length;
      s.set(k, { route, u: 0 }, t - 0.02);
      s.to(k, { in: 1 }, t - 0.3, 0.3, 'out');
      s.to(k, { u: 1 }, t, dur, 'inOut');
      if (sum) s.to(k, { sum: 1 }, t, 0.3, 'out');
      L.forEach(([a, b], j) => {
        const ta = t + j * per;
        if (heat) s.to(edgeKey(a, b), { hot: 1 }, ta, per * 0.6, 'out');
        if (rings && j > 0) s.fromTo(G.nodeKey(a), { ring: 0 }, { ring: 1 }, ta - 0.05, 0.7, 'out');
      });
      const tEnd = t + dur;
      if (heat) for (const [a, b] of L) s.to(edgeKey(a, b), result === 'hot' ? { hot: 1 } : { hot: 0, [result]: 1 }, tEnd, 0.4, 'out');
      if (land) s.fromTo(G.nodeKey(L[L.length - 1][1]), { ring: 0 }, { ring: 1 }, tEnd - 0.05, 0.7, 'out');
      return tEnd;
    },

    /** take a token off the board */
    land(i, t) { s.to(G.tokenKey(i), { in: 0, sum: 0 }, t, 0.35, 'in'); },

    /** clear route colours on edges (back to idle) */
    reset(edges, t, dur = 0.4) { for (const [a, b] of edges) s.to(edgeKey(a, b), { hot: 0, good: 0, bad: 0, dim: 0, strike: 0 }, t, dur, 'inOut'); },

    /** visibly reject a route: edges turn rose and get struck, the camera shakes */
    reject(route, t) {
      for (const [a, b] of legs(route)) s.to(edgeKey(a, b), { hot: 0, bad: 1 }, t, 0.3, 'out');
      const [a, b] = legs(route)[Math.floor(legs(route).length / 2)];
      s.fromTo(edgeKey(a, b), { strike: 0 }, { strike: 1 }, t + 0.1, 0.35, 'back');
      s.pulse('Camera', 'shake', t + 0.1, { peak: 0.7, up: 0.05, hold: 0.05, down: 0.4 });
    },

    /** the question card for line `id`, its countdown over the think pause */
    question(id, n, { flipFrom = false } = {}) {
      const th = T.think(id), t = T.at(id);
      if (flipFrom) { s.set('Question', { q: id, n, timer: 0 }, t - 0.5); s.to('Question', { flip: 0 }, t - 0.5, 0.5, 'inOut'); }
      else { s.set('Question', { q: id, n, flip: 0 }, t - 0.05); s.to('Question', { in: 1 }, t - 0.05, 0.5, 'expoOut'); }
      s.set('Question', { timer: 0 }, t);
      s.to('Question', { timer: 1 }, th.t, Math.max(0.5, th.dur), 'linear');
    },
    /** flip the card to the answer line `id` */
    answer(id) { const t = T.at(id) - 0.1; s.set('Question', { a: id }, t); s.to('Question', { flip: 1 }, t, 0.5, 'inOut'); },
  };
  return R;
}
