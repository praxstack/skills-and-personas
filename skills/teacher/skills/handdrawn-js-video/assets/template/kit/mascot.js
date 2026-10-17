// kit/mascot.js: Pip (a small paper-cut traveller) and the paper plane Pip flies in. The plane is the token that
// travels routes on the graph (kit/graph.js token()). In the chalk and blueprint styles the plane is line work
// and Pip stays home (S.mascot = false). Drawn live each frame (cheap), so poses can change at any t.
'use strict';
const PIP = Object.assign({}, PIP_COLOURS, S.pip || {}); // style.js: a registry theme recolours the clothes, never the face
const ARMS = { down: [[0.18, 0.1], [-0.12, -0.05]], point: [[0.25, 0.1], [1.35, 1.55]], wave: [[0.2, 0.1], [2.2, 2.9]], cheer: [[-2.5, -2.8], [2.5, 2.8]], chin: [[0.2, 0.1], [0.55, -2.6]] };
// o: {t, face: 1|-1, expr: 'happy'|'cheer'|'wow'|'think'|'sad', arms: key of ARMS, walk (phase), look: [dx,dy], shadow}
function drawPip(ctx, x, y, s, o = {}) {
  const t = o.t || 0, expr = o.expr || 'happy', arms = ARMS[o.arms || 'down'], walk = o.walk || 0;
  ctx.save(); ctx.translate(x, y); ctx.scale(s * (o.face || 1), s); if (o.alpha != null) ctx.globalAlpha *= o.alpha;
  if (o.shadow !== false) { ctx.fillStyle = S.pipShadow; ctx.beginPath(); ctx.ellipse(0, 0, 26, 5, 0, 0, TAU); ctx.fill(); }
  const legA = Math.sin(walk) * 0.55, hop = walk ? Math.abs(Math.cos(walk)) * 3 : 0, bob = Math.sin(t * 2.2) * 1.2;
  ctx.translate(0, -hop + bob * 0.3);
  const wave = o.arms === 'wave' ? Math.sin(t * 9) * 0.35 : 0, swing = walk ? Math.sin(walk) * 0.5 : 0;
  const backArm = [arms[0][0] - swing, arms[0][1] - swing], frontArm = [arms[1][0] + swing + wave, arms[1][1] + swing + wave * 1.4];
  const parts = (out) => {
    const fill = (col) => (out ? PIP.rim : col);
    const shape = (fn, col) => { fn(); if (out) { ctx.lineWidth = 9; ctx.strokeStyle = PIP.rim; ctx.lineJoin = 'round'; ctx.stroke(); } ctx.fillStyle = fill(col); ctx.fill(); };
    shape(() => pathPts(ctx, rrPts(-33, -76, 22, 42, 8)), PIP.pack);
    [[-8, -legA], [8, legA]].forEach(([lx, a]) => { ctx.save(); ctx.translate(lx, -32); ctx.rotate(a); shape(() => pathPts(ctx, rrPts(-7, 0, 14, 30, 6)), PIP.legs); shape(() => { ctx.beginPath(); ctx.ellipse(3, 30, 10, 6, 0, 0, TAU); }, PIP.boots); ctx.restore(); });
    const arm = (sx, a) => {
      const ex = sx + Math.sin(a[0]) * 17, ey = -66 + Math.cos(a[0]) * 17, hx = ex + Math.sin(a[1]) * 17, hy = ey + Math.cos(a[1]) * 17;
      ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.beginPath(); ctx.moveTo(sx, -66); ctx.lineTo(ex, ey); ctx.lineTo(hx, hy);
      ctx.lineWidth = out ? 21 : 12; ctx.strokeStyle = out ? PIP.rim : PIP.coat2; ctx.stroke();
      ctx.beginPath(); ctx.arc(hx, hy, out ? 10.5 : 6.5, 0, TAU); ctx.fillStyle = fill(PIP.skin); ctx.fill();
    };
    arm(-10, backArm);
    shape(() => { ctx.beginPath(); ctx.moveTo(-19, -74); ctx.quadraticCurveTo(0, -78, 19, -74); ctx.lineTo(26, -30); ctx.quadraticCurveTo(0, -26, -26, -30); ctx.closePath(); }, PIP.coat);
    if (!out) { ctx.fillStyle = PIP.rim; ctx.beginPath(); ctx.arc(6, -56, 2.6, 0, TAU); ctx.arc(6, -44, 2.6, 0, TAU); ctx.fill(); }
    shape(() => pathPts(ctx, rrPts(-20, -80, 40, 12, 6)), PIP.scarf);
    shape(() => pathPts(ctx, rrPts(-18, -74, 10, 24 + Math.sin(t * 4) * 2, 4)), PIP.scarf);
    shape(() => { ctx.beginPath(); ctx.ellipse(-7, -95, 25, 23, 0, 0, TAU); }, PIP.hair);
    shape(() => { ctx.beginPath(); ctx.arc(3, -97, 26, 0, TAU); }, PIP.skin);
    shape(() => { ctx.beginPath(); ctx.ellipse(2, -106, 29, 25, 0, Math.PI, 0); ctx.closePath(); }, PIP.hat);
    shape(() => pathPts(ctx, rrPts(-27, -112, 58, 12, 6)), PIP.hat2);
    shape(() => { ctx.beginPath(); ctx.arc(2, -133, 8, 0, TAU); }, PIP.rim);
    arm(12, frontArm);
  };
  parts(true); parts(false);
  const [lx, ly] = o.look || (expr === 'think' ? [3, -3] : [0, 0]), blink = ((t + (o.seed || 0)) % 3.7) < 0.12;
  ctx.fillStyle = PIP.cheek; ctx.globalAlpha *= 0.85; ctx.beginPath(); ctx.ellipse(-8, -88, 5.5, 3.6, 0, 0, TAU); ctx.ellipse(21, -88, 5.5, 3.6, 0, 0, TAU); ctx.fill(); ctx.globalAlpha /= 0.85;
  ctx.fillStyle = PIP.eye; ctx.strokeStyle = PIP.eye; ctx.lineWidth = 2.6; ctx.lineCap = 'round';
  const eyes = [[-1 + lx, -97 + ly], [14 + lx, -97 + ly]];
  if (expr === 'cheer') eyes.forEach(([ex, ey]) => { ctx.beginPath(); ctx.arc(ex, ey + 2, 4.5, Math.PI * 1.15, Math.PI * 1.85); ctx.stroke(); });
  else if (blink) eyes.forEach(([ex, ey]) => { ctx.beginPath(); ctx.moveTo(ex - 3.5, ey); ctx.lineTo(ex + 3.5, ey); ctx.stroke(); });
  else { const er = expr === 'wow' ? 4.4 : 3.5; eyes.forEach(([ex, ey]) => { ctx.beginPath(); ctx.arc(ex, ey, er, 0, TAU); ctx.fill(); ctx.fillStyle = PIP.shine; ctx.beginPath(); ctx.arc(ex + 1.2, ey - 1.3, er * 0.34, 0, TAU); ctx.fill(); ctx.fillStyle = PIP.eye; }); }
  if (expr === 'sad') { ctx.beginPath(); ctx.moveTo(-5, -105); ctx.lineTo(2, -107); ctx.moveTo(11, -107); ctx.lineTo(18, -105); ctx.stroke(); }
  ctx.beginPath();
  if (expr === 'wow') { ctx.ellipse(7, -85, 3.6, 4.6, 0, 0, TAU); ctx.stroke(); }
  else if (expr === 'cheer') { ctx.moveTo(0, -88); ctx.quadraticCurveTo(7, -77, 14, -88); ctx.closePath(); ctx.fill(); }
  else if (expr === 'think') { ctx.moveTo(4, -85); ctx.lineTo(11, -86.5); ctx.stroke(); }
  else if (expr === 'sad') { ctx.arc(7, -81, 5, Math.PI * 1.2, Math.PI * 1.8); ctx.stroke(); }
  else { ctx.arc(7, -90, 5.5, Math.PI * 0.2, Math.PI * 0.8); ctx.stroke(); }
  ctx.restore();
}

// paper plane, nose along `ang`; optionally carrying Pip. o: {t, pip, alpha, expr}
function drawPlane(ctx, x, y, ang, s, o = {}) {
  if (s <= 0.01 || (o.alpha ?? 1) <= 0.01) return;
  ctx.save(); ctx.translate(x, y);
  if (Math.cos(ang) < 0) { ctx.scale(-1, 1); ang = Math.PI - ang; }
  ctx.rotate(ang + Math.sin((o.t || 0) * 5) * 0.04); ctx.scale(s, s); ctx.globalAlpha *= o.alpha ?? 1;
  if (o.noseAt) ctx.translate(-62, 0); // the path point is the nose, not the middle
  if (STYLE.plane) { STYLE.plane(ctx, o); ctx.restore(); return; }
  if (S.kind !== 'paper') {
    const c = S.ink;
    inkLine(ctx, [[66, 0], [-50, -26], [-30, -1], [66, 0], [-34, -2], [-46, 20], [-22, 9]], { color: c, w: 3, seed: 'plane', t: o.t, ends: false, amp: 0.6 });
    ctx.restore(); return;
  }
  const poly = (p, col) => { pathPts(ctx, p); ctx.fillStyle = col; ctx.fill(); };
  ctx.save(); ctx.shadowColor = S.shadow; ctx.shadowBlur = 12; ctx.shadowOffsetY = 10; poly([[66, 0], [-34, -2], [-46, 20]], S.plane.under); ctx.restore();
  if (o.pip) { ctx.save(); ctx.beginPath(); ctx.rect(-80, -200, 200, 196); ctx.clip(); drawPip(ctx, -8, 26, 0.62, { t: o.t, expr: o.expr || 'happy', shadow: false, seed: 1 }); ctx.restore(); }
  poly([[66, 0], [-34, -2], [-22, 9]], S.plane.mid);
  poly([[66, 0], [-50, -26], [-30, -1]], S.plane.top);
  ctx.strokeStyle = S.plane.crease; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(66, 0); ctx.lineTo(-30, -1); ctx.stroke();
  ctx.strokeStyle = S.plane.wind; ctx.lineWidth = 2.5; ctx.lineCap = 'round';
  for (let k = 0; k < 3; k++) { const ph = ((o.t || 0) * 3 + k * 0.33) % 1; ctx.globalAlpha = (o.alpha ?? 1) * 0.6 * (1 - ph); ctx.beginPath(); ctx.moveTo(-60 - ph * 40, -14 + k * 12); ctx.lineTo(-84 - ph * 40, -14 + k * 12); ctx.stroke(); }
  ctx.restore();
}
