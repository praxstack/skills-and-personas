// engine/blocks-screen.js: screen, a block that plays real screen recordings of a product, frame by frame.
//
// A product demo needs the product: this block shows recorded footage (frames extracted to JPEG files, one per
// recorded frame) inside a rounded screen, plays chosen stretches of it at any speed on spoken phrases, moves a
// camera over it (push in on what the line is about, pull back to show the whole), and lets a pen draw
// on it: circles and underlines that stay on the footage as the camera moves, and handwritten notes that keep their
// size. Everything is a tween on M.tl or a pure function of t, so any frame can be drawn on any worker in any order.
//
//   { "type": "screen", "id": "app",
//     "clips": { "review": { "dir": "footage/02-review", "fps": 30, "frames": 1990 } },
//     "clip": "review", "from": 0.5, "view": [960, 540, 1920],
//     "cues": [
//       { "do": "play", "at": "r1", "from": 4.0, "to": 52.0, "until": "r2.end -0.4" },  (48 s of footage over the line)
//       { "do": "view", "at": "r2:opening", "box": [1500, 300, 900] },                    (centre x, y and width, px)
//       { "do": "circle", "at": "k1:blunder", "box": [1560, 330, 160, 50], "tone": "bad" },
//       { "do": "note", "at": "k2", "text": "mate in 2", "near": [1700, 420], "tone": "bad" } ] }
//
// Footage time and camera are plain objects tweened on the timeline; an ambient hook applies them to the DOM on
// every frame and sets each image's source. renderFrame (screen-sync.js) waits until those images have decoded.
// M.footage() tells capture.mjs where the recording is on the frame, so legibility.py can hold the film's own
// words to the 26 px / 4.5:1 rule and report the product's recorded UI separately.
(function () {
  const M = window.M;
  if (!M || !M.tl) return;
  const TY = LOOK.TYPE;
  let screens = [];
  const pending = new Set();

  // every build starts with no screens; the ambient hook keeps them in step with the timeline
  const baseBuild = M.build;
  M.build = (film) => { screens = []; return baseBuild(film); };
  const baseAmbient = M.ambient;
  M.ambient = (t) => { baseAmbient(t); for (const s of screens) s.sync(t); };
  /** Resolves when every frame image set by the last draw has decoded (capture waits for it). */
  M.screenFrames = async () => { const all = [...pending]; pending.clear(); await Promise.all(all); };
  /** Where recorded footage shows on the frame right now: {rects, keep}, in frame px. rects: each visible
   *  screen; keep: the film's own text drawn over it (the notes), which the legibility rules still apply to. */
  M.footage = () => {
    const stage = document.getElementById('stage').getBoundingClientRect();
    const k = M.W / stage.width;   // 1 in a render; the preview scales the stage
    const rel = (r) => [(r.left - stage.left) * k, (r.top - stage.top) * k, r.width * k, r.height * k].map((v) => Math.round(v * 10) / 10);
    // seen at all: visible, and its opacity times every ancestor's (a shot fading out fades its parent) above 2%
    const shown = (e) => {
      if (getComputedStyle(e).visibility === 'hidden') return false;
      let o = 1;
      for (let n = e; n && n.nodeType === 1; n = n.parentElement) o *= parseFloat(getComputedStyle(n).opacity);
      return o > 0.02;
    };
    const out = { rects: [], keep: [] };
    for (const s of screens) {
      if (!shown(s.el)) continue;
      out.rects.push(rel(s.vp.getBoundingClientRect()));
      for (const n of s.notes) if (shown(n.el)) out.keep.push(rel(n.el.getBoundingClientRect()));
    }
    return out;
  };

  const TONES = { bad: '#FF5446', accent: '#6E9BFF', cool: '#6E9BFF', good: '#3FD08C', gold: '#FFD84A', warm: '#FF9F43', violet: '#B39CFF' };
  const INK = (P, tone) => P[(tone || 'accent') + 'Ink'] || P.accentInk;

  M.block('screen', {
    fields: {
      clips: { type: 'json', required: true, help: '{"review": {"dir": "footage/02-review", "fps": 30, "frames": 1990}}: frames dir/f00001.jpg ...' },
      clip: { type: 'text', required: true, help: 'the clip on screen first' },
      from: { type: 'number', help: 'its second on screen first (default 0)' },
      view: { type: 'json', help: '[x, y, w]: the centre and width (recording px) framed first; default the whole recording' },
      size: { type: 'json', help: '[w, h] of the recording in px (default [1920, 1080])' },
    },
    cues: ['play', 'view', 'circle', 'underline', 'note'],
    weight: { row: 2.3, column: 1.6 },
    build(c) {
      const { el, box, props: p, u, P } = c;
      const [SW, SH] = Array.isArray(p.size) && p.size.length === 2 ? p.size.map(Number) : [1920, 1080];
      if (!(SW > 0 && SH > 0)) throw new Error('"size" is [w, h] in px, e.g. [1920, 1080]');
      if (!p.clips || typeof p.clips !== 'object' || Array.isArray(p.clips) || !Object.keys(p.clips).length) throw new Error('"clips" names at least one clip: {"name": {"dir": "footage/name", "fps": 30, "frames": 900}}');
      const names = Object.keys(p.clips);
      const clips = names.map((n) => {
        const k = p.clips[n] || {};
        if (typeof k.dir !== 'string' || !k.dir || /^(\/|[a-z]+:)|\.\./i.test(k.dir)) throw new Error(`clips.${n}.dir is ${JSON.stringify(k.dir)}; a folder inside source/, e.g. "footage/${n}"`);
        if (!(k.fps > 0) || !(Number.isInteger(k.frames) && k.frames > 0)) throw new Error(`clips.${n} needs "fps" (above 0) and "frames" (how many files, a whole number)`);
        return { name: n, dir: k.dir.replace(/\/$/, ''), fps: +k.fps, frames: k.frames, len: k.frames / k.fps };
      });
      const idx = (n, what) => { const i = names.indexOf(String(n)); if (i < 0) throw new Error(`${what}: no clip "${n}" (clips: ${names.join(', ')})`); return i; };
      const secs = (v, k, what) => { if (typeof v !== 'number' || !isFinite(v) || v < 0 || v > clips[k].len + 1e-6) throw new Error(`${what} is ${JSON.stringify(v)}; a second of "${names[k]}" from 0 to ${clips[k].len.toFixed(2)}`); return v; };

      // the screen: the largest SW:SH rectangle in the box, centred, with the recording in a camera layer
      const s0 = Math.min(box.w / SW, box.h / SH), vw = SW * s0, vh = SH * s0;
      const vp = M.el('div', 'vp', el, { left: (box.w - vw) / 2 + 'px', top: (box.h - vh) / 2 + 'px', width: vw + 'px', height: vh + 'px' });
      const cam = M.el('div', 'cam', vp, { width: SW + 'px', height: SH + 'px' });
      const imgA = M.el('img', 'fr', cam), imgB = M.el('img', 'fr', cam);
      imgA.alt = imgB.alt = '';
      cam.style.width = SW + 'px'; cam.style.height = SH + 'px';
      const pen = M.svg('svg', { class: 'pen', width: SW, height: SH, viewBox: `0 0 ${SW} ${SH}` }, cam);
      const noteLayer = M.el('div', 'notes', vp);

      // state on the timeline: the footage shown (S), the frame held during a cut's crossfade (B), the camera (C)
      const S = { clip: idx(p.clip, '"clip"'), ft: 0 };
      S.ft = secs(p.from ?? 0, S.clip, '"from"');
      const B = { clip: S.clip, ft: S.ft, o: 0 };
      const view = (v, what) => {
        if (!Array.isArray(v) || v.length !== 3 || !v.every((x) => typeof x === 'number' && isFinite(x))) throw new Error(`${what} is ${JSON.stringify(v)}; it is [x, y, w]: the centre and the width framed, in recording px`);
        if (v[2] < SW * 0.2 || v[2] > SW) throw new Error(`${what}: the width ${v[2]} is outside ${Math.round(SW * 0.2)}-${SW} px (a closer push in blurs the recording)`);
        return { x: v[0], y: v[1], w: v[2] };
      };
      const C = p.view ? view(p.view, '"view"') : { x: SW / 2, y: SH / 2, w: SW };
      const frame = () => {   // C, clamped to the recording
        const w = Math.min(SW, Math.max(SW * 0.2, C.w)), h = (w * SH) / SW;
        return { x0: M.clamp(C.x - w / 2, 0, SW - w), y0: M.clamp(C.y - h / 2, 0, SH - h), s: vw / w };
      };
      const notes = [];
      const api = { el, vp, notes };

      let curShot = c.shot;
      // a mark stays to the end of its shot and fades as the next one starts (the screen is carried, so it stays put)
      const shotEnd = () => (curShot.t1 < M.TOTAL - 0.01 ? curShot.t1 : M.TOTAL);
      let landed = 0;
      // what is on screen when each cue starts, kept in spoken order (the stage runs cues in that order)
      let now = { clip: S.clip, ft: S.ft, until: 0 }, cam0 = { ...C };
            const leave = (els, t) => { M.to(els, { autoAlpha: 0, duration: 0.25, ease: 'power1.in' }, t); };
      const outAt = (cue, at, end) => {
        const t = cue.out ? c.time(cue.out) : shotEnd() - 0.05;
        if (t < end + 0.3) throw new Error(`"out" (${t.toFixed(2)} s) comes before the mark has been on screen for 0.3 s (it lands at ${end.toFixed(2)} s)`);
        return Math.min(t, c.leaves - 0.25);
      };
      const rng = M.rng(7);
      const wob = (a) => (rng() - 0.5) * 2 * a;

      function setFrame(img, k, ft) {
        const cl = clips[k];
        const n = Math.min(cl.frames - 1, Math.max(0, Math.round(ft * cl.fps)));
        const src = `${cl.dir}/f${String(n + 1).padStart(5, '0')}.jpg`;
        if (img.dataset.src === src) return;
        img.dataset.src = src;
        img.src = src;
        pending.add(img.decode().catch(() => {}));
      }

      api.sync = () => {
        const { x0, y0, s } = frame();
        cam.style.transform = `translate(${(-x0 * s).toFixed(2)}px, ${(-y0 * s).toFixed(2)}px) scale(${s.toFixed(5)})`;
        setFrame(imgA, Math.round(S.clip), S.ft);
        if (B.o > 0.002) { imgB.style.opacity = B.o.toFixed(3); setFrame(imgB, Math.round(B.clip), B.ft); }
        else imgB.style.opacity = '0';
        for (const n of notes) {
          const x = (n.near[0] - x0) * s, y = (n.near[1] - y0) * s;
          n.el.style.left = M.clamp(x - n.w / 2, 8 * u, vw - n.w - 8 * u).toFixed(1) + 'px';
          n.el.style.top = M.clamp(y - n.h / 2, 8 * u, vh - n.h - 8 * u).toFixed(1) + 'px';
        }
      };
      screens.push(api);

      /** A hand-drawn loop around a box: an ellipse that starts a little past where it ends, with a wobble. */
      function loopPath(x, y, w, h) {
        const cx = x + w / 2, cy = y + h / 2, rx = w / 2 + 18 + w * 0.06, ry = h / 2 + 14 + h * 0.12;
        const a0 = -2.6 + wob(0.2), turn = Math.PI * 2 + 0.55, n = 28;
        let d = '';
        for (let i = 0; i <= n; i++) {
          const a = a0 + (turn * i) / n, f = 1 + 0.035 * Math.sin(i * 1.7) + wob(0.012) + (i / n) * 0.07;
          d += `${i ? 'L' : 'M'}${(cx + Math.cos(a) * rx * f).toFixed(1)} ${(cy + Math.sin(a) * ry * f).toFixed(1)} `;
        }
        return d;
      }
      function underPath(x, y, w, h) {
        const yy = y + h + 8, n = 12;
        let d = '';
        for (let i = 0; i <= n; i++) d += `${i ? 'L' : 'M'}${(x - 6 + ((w + 12) * i) / n).toFixed(1)} ${(yy + Math.sin(i * 0.9) * 2.2 + wob(1.2) + (i / n) * 3).toFixed(1)} `;
        return d;
      }
      function stroke(d, tone, width) {
        const g = M.svg('g', { class: 'mark' }, pen);
        M.svg('path', { d, class: 'halo', 'stroke-width': width + 7 }, g);
        const path = M.svg('path', { d, class: 'ink', stroke: TONES[M.hue(tone || 'bad')] || TONES.bad, 'stroke-width': width }, g);
        M.init(g, { autoAlpha: 0 });
        return { g, paths: g.querySelectorAll('path'), path };
      }
      const boxOf = (b, what) => {
        if (!Array.isArray(b) || b.length !== 4 || !b.every((x) => typeof x === 'number' && isFinite(x)) || b[2] <= 0 || b[3] <= 0) throw new Error(`${what} is ${JSON.stringify(b)}; it is [x, y, w, h] in recording px`);
        if (b[0] < 0 || b[1] < 0 || b[0] + b[2] > SW || b[1] + b[3] > SH) throw new Error(`${what} ${JSON.stringify(b)} runs off the ${SW}x${SH} recording`);
        return b;
      };
      const strokeWidth = () => 5.5 / Math.max(0.6, Math.min(1.6, vw / cam0.w));   // about 5.5 px on screen at the camera of the moment

      return {
        onShot(b, s) { curShot = s; },
        enter(t0) {
          M.fromTo(el, { autoAlpha: 0, y: 36 * u }, { autoAlpha: 1, y: 0, duration: 0.8, ease: 'lift' }, t0);
          landed = t0 + 0.8;
          return landed;
        },
        cues: {
          /** Play footage from `from` to `to` (seconds of the clip), over until-at (or at speed, default 1).
           *  A different clip, or a jump within one, crossfades from the frame on screen over 0.3 s. */
          play(cue, t1) {
            const t = Math.max(t1, landed - 0.6);
            const k = cue.clip !== undefined ? idx(cue.clip, '"clip"') : now.clip;
            const from = secs(cue.from ?? (k === now.clip ? now.ft : 0), k, '"from"');
            const to = secs(cue.to, k, '"to"');
            if (to < from) throw new Error(`"to" (${to}) comes before "from" (${from}); footage plays forwards`);
            if (t < now.until - 0.01) throw new Error(`starts at ${t.toFixed(2)} s, while the play before it runs until ${now.until.toFixed(2)} s; start it later or end the other sooner`);
            let d;
            if (cue.until) d = c.time(cue.until) - t;
            else d = (to - from) / (cue.speed || 1);
            if (!(d > 0.05)) throw new Error(`plays for ${d.toFixed(2)} s; give it a later "until" or a lower "speed"`);
            if (cue.speed !== undefined && !(cue.speed > 0)) throw new Error('"speed" is above 0, e.g. 2 for twice as fast');
            if (k !== now.clip || Math.abs(from - now.ft) > 0.05) {
              M.set(B, { clip: now.clip, ft: now.ft }, t);
              M.fromTo(B, { o: 1 }, { o: 0, duration: 0.3, ease: 'power1.out' }, t);
              M.set(S, { clip: k }, t);
            }
            M.fromTo(S, { ft: from }, { ft: to, duration: d, ease: 'none' }, t);
            now = { clip: k, ft: to, until: t + d };
            M.event(t, 'play', t + Math.min(d, 0.5));
            return { at: t, end: t + Math.min(d, 0.5), off: t + d };
          },
          /** Move the camera: "box": [x, y, w] (centre and width in recording px), over "d" seconds (default 0.9). */
          view(cue, t1) {
            const t = Math.max(t1, landed);
            const v = view(cue.box, '"box"'), d = cue.d ?? 0.9;
            if (!(d >= 0.2 && d <= 4)) throw new Error('"d" is 0.2 to 4 seconds');
            M.fromTo(C, { ...cam0 }, { ...v, duration: d, ease: 'power2.inOut' }, t);
            cam0 = v;
            return { at: t, end: t + d };
          },
          /** Circle something on the footage: "box": [x, y, w, h] in recording px, "tone" (default bad). */
          circle(cue, t1) {
            const t = Math.max(t1, landed);
            const [x, y, w, h] = boxOf(cue.box, '"box"');
            const m = stroke(loopPath(x, y, w, h), cue.tone || 'bad', strokeWidth());
            const d = M.clamp(0.0008 * (w + h) * 2.2, 0.4, 0.75);
            M.set(m.g, { autoAlpha: 1 }, t);
            M.fromTo(m.paths, { drawSVG: '0%' }, { drawSVG: '100%', duration: d, ease: 'power2.inOut' }, t);
            const off = outAt(cue, t, t + d);
            leave(m.g, off);
            return { at: t, end: t + d, off: off + 0.25 };
          },
          /** Underline something: "box": [x, y, w, h] in recording px (the stroke runs under it). */
          underline(cue, t1) {
            const t = Math.max(t1, landed);
            const [x, y, w, h] = boxOf(cue.box, '"box"');
            const m = stroke(underPath(x, y, w, h), cue.tone || 'bad', strokeWidth());
            const d = M.clamp(0.0011 * w, 0.3, 0.8);
            M.set(m.g, { autoAlpha: 1 }, t);
            M.fromTo(m.paths, { drawSVG: '0%' }, { drawSVG: '100%', duration: d, ease: 'power2.inOut' }, t);
            const off = outAt(cue, t, t + d);
            leave(m.g, off);
            return { at: t, end: t + d, off: off + 0.25 };
          },
          /** A handwritten note on a paper slip, centred on "near": [x, y] (recording px), that keeps its size as
           *  the camera moves; written word by word (34 ms a character). "tone": accent (default) or bad. */
          note(cue, t1) {
            const t = Math.max(t1, landed);
            if (typeof cue.text !== 'string' || !cue.text.trim()) throw new Error('"text" is the note, e.g. "mate in 2"');
            const near = cue.near;
            if (!Array.isArray(near) || near.length !== 2 || !near.every((x) => typeof x === 'number' && isFinite(x))) throw new Error('"near" is [x, y] in recording px, where the note sits');
            const n = M.el('div', 'note', noteLayer);
            n.style.color = INK(P, cue.tone || 'accent');
            n.style.fontSize = 44 * u + 'px';
            n.style.setProperty('--tilt', (cue.tilt ?? -2) + 'deg');
            const tx = M.el('span', 'tx', n, null, cue.text);
            const w = n.offsetWidth, h = n.offsetHeight;
            if (w > vw * 0.9) throw new Error(`the note "${cue.text}" is wider than the screen; shorten it`);
            const rec = { el: n, near, w, h };
            notes.push(rec);
            M.init(n, { autoAlpha: 0 });
            M.init(tx, { clipPath: 'inset(-10% 100% -10% 0%)' });
            M.fromTo(n, { autoAlpha: 0, scale: 0.92 }, { autoAlpha: 1, scale: 1, duration: 0.22, ease: 'power2.out' }, t);
            const d = M.clamp(cue.text.length * 0.034, 0.4, 2.5);
            M.fromTo(tx, { clipPath: 'inset(-10% 100% -10% 0%)' }, { clipPath: 'inset(-10% 0% -10% 0%)', duration: d, ease: 'none' }, t + 0.12);
            const off = outAt(cue, t, t + 0.12 + d);
            leave(n, off);
            return { at: t, end: t + 0.12 + d, off: off + 0.25 };
          },
        },
      };
    },
  });
})();
