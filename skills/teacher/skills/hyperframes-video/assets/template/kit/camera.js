/* kit/camera.js: a continuous camera over the world layer.

   #cam   tilt (rotationX, perspective) : the world is a tabletop seen from slightly above, for depth
   #drift slow wander, always on          : nothing is ever perfectly still (qa.py flags frozen shots)
   #world pan + zoom                      : a shot puts world point (cx, cy) at screen point (sx, sy), scaled by zoom

   KIT.cam.init({cx, cy, zoom, sx, sy, tilt})      the state at t = 0
   KIT.cam(t, {cx, cy, zoom, sx, sy, tilt}, d, ease) move to a shot (only the keys you pass change)
   KIT.cam.push(t, d, factor)                      slow push-in (or pull-out with factor < 1) on the current shot
   KIT.cam.toScreen(wx, wy, t)                     where a world point is on screen at time t (fly-ins aim here)
   KIT.cam.drift(amp)                              start the wander (called once by the film)
   Moves must not overlap in time; a hard cut is d = 0 (use it only under a chapter sting).
   Every move also eases the CSS variable --inv (= 1 / zoom) on #world, with the same timing. World labels read it
   (KIT.wfs, KIT.wscale) so they keep at least KIT.tok.size.world px on screen however far the camera pulls back. */
(function () {
  'use strict';
  const K = window.KIT, tl = K.tl;
  const W = 1920, H = 1080, P = 2600;
  const L = K.layer;
  let state = { cx: W / 2, cy: H / 2, zoom: 1, sx: W / 2, sy: H / 2, tilt: 0 };
  let start = state;
  const moves = [];
  const wv = (s) => ({ x: s.sx - s.cx * s.zoom, y: s.sy - s.cy * s.zoom, scale: s.zoom, '--inv': +(1 / s.zoom).toFixed(5) });
  const cv = (s) => ({ rotationX: s.tilt, transformPerspective: P });

  function cam(t, shot, d = 1.2, ease = 'power3.inOut') {
    const to = Object.assign({}, state, shot);
    const last = moves[moves.length - 1];
    if (last && t < last.t + last.d - 1e-3) console.warn(`camera: move at ${t.toFixed(2)} overlaps the move at ${last.t.toFixed(2)}`);
    if (d <= 0) {
      tl.set(L.world, wv(to), t);
      tl.set(L.cam, cv(to), t);
    } else {
      tl.to(L.world, Object.assign(wv(to), { duration: d, ease }), t);
      tl.to(L.cam, Object.assign(cv(to), { duration: d, ease }), t);
    }
    moves.push({ t, d: Math.max(0, d), ease, from: state, to });
    state = to;
    return to;
  }
  cam.init = (shot) => {
    state = start = Object.assign({}, state, shot);
    gsap.set(L.world, wv(state));
    gsap.set(L.cam, cv(state));
    gsap.set([L.cam, L.drift], { transformOrigin: '50% 50%' });
    return state;
  };
  cam.state = () => Object.assign({}, state);
  cam.push = (t, d, factor = 1.06, ease = 'sine.inOut') => cam(t, { zoom: state.zoom * factor }, d, ease);

  function stateAt(t) {
    let s = start, from = null, p = 1;
    for (const m of moves) {
      if (t >= m.t + m.d) { s = m.to; continue; }
      if (t > m.t) { from = m.from; s = m.to; p = gsap.parseEase(m.ease)((t - m.t) / m.d); }
      break;
    }
    if (!from) return { ...wv(s), tilt: s.tilt };
    const a = wv(from), b = wv(s), lerp = (x, y) => x + (y - x) * p;
    return { x: lerp(a.x, b.x), y: lerp(a.y, b.y), scale: lerp(a.scale, b.scale), tilt: lerp(from.tilt, s.tilt) };
  }
  cam.toScreen = (wx, wy, t) => {
    const s = stateAt(t);
    const X = s.x + wx * s.scale - W / 2, Y = s.y + wy * s.scale - H / 2;
    const a = (s.tilt * Math.PI) / 180, w = 1 - (Y * Math.sin(a)) / P;
    return [W / 2 + X / w, H / 2 + (Y * Math.cos(a)) / w];
  };
  cam.drift = (amp = 10, seed = 7) => {
    const r = K.rand(seed), total = K.T.total;
    let t = 0;
    while (t < total) {
      const d = 5 + r() * 3;
      tl.to(L.drift, { x: (r() - 0.5) * 2 * amp, y: (r() - 0.5) * 1.4 * amp, rotation: (r() - 0.5) * 0.5, duration: d, ease: 'sine.inOut' }, t);
      t += d;
    }
  };
  K.cam = cam;
})();
