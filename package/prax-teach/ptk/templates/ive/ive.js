(function () {
  'use strict';
  // ptk interactive video explorer (WP6). The video's currentTime is the only clock (D20.6).
  //
  //   FILM ──pause / "Pause and explore"──▶ EXPLORE ──"Return" / play──▶ RETURN ──playing──▶ FILM
  //    ▲  the panel follows the film's cue    │ seeded at the film's state; edits marked as yours │
  //    └──────────────────────────────────────┴── a seek while exploring re-seeds at the new time ┘
  //
  // Explanation first (AC-6.8): by default the film plays through each question and explains, straight on
  // into the answer scene (the MP4 has no think gap) and never stops. The options sit beside the film; a
  // pick is optional.
  // ASK, practice mode only (round 18; off by default, the visible "Practice mode" toggle turns it on):
  // playing into a question's pause point (its last spoken word + 0.25 s) stops the film and shows the
  // same options as the Q&A. Play holds until the learner picks; a pick shows the verdict and jumps to
  // the answer scene. Turning practice off releases the hold. A chapter title that states the answer
  // (D.questions[].sealed) shows a placeholder until the question is answered or the film has passed
  // the answer.
  //
  // Cue windows are half-open [start, next start). A time less than one frame before a boundary
  // belongs to the later window, because browsers round seek targets (to the frame or to the
  // microsecond) and a chapter seek must not land in the previous chapter.
  // Every value shown comes from a cue payload (the film) or from the switch model built and
  // checked by ptk (an edit). The cue track text lives in ive-data.js, outside the DOM, so no
  // future state or answer is in the document before its cue.
  var D = window.__ptkIveData;
  function $(id) { return document.getElementById(id); }
  var v = $('v');
  if (!D) { $('mode').textContent = $('mode').getAttribute('data-nodata'); return; }
  var U = D.ui;
  function el(tag, cls, txt) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (txt != null) e.textContent = txt;
    return e;
  }
  function fmt(s, o) { return s.replace(/\{(\w+)\}/g, function (_, k) { return String(o[k]); }); }
  function clock(t) { var m = Math.floor(t / 60), s = Math.floor(t % 60); return m + ':' + (s < 10 ? '0' : '') + s; }

  // ---- the clock rule (D20.6)
  var FRAME_US = Math.floor(1e6 / D.fps);
  function us(t) { return Math.round(t * 1e6); }
  function windowAt(list, t) {
    var T = us(t), k = -1;
    for (var i = 0; i < list.length; i++) { if (us(list[i].start) - T < FRAME_US) k = i; else break; }
    return k;
  }

  // ---- navigation events for a host bridge (AC-6.5): kind "navigation" only, never an attempt
  var nav = window.__ptkNav = [];
  function eventId() {
    var a = new Uint8Array(16); window.crypto.getRandomValues(a);
    return 'evt-' + Array.prototype.map.call(a, function (b) { return (b < 16 ? '0' : '') + b.toString(16); }).join('');
  }
  function emit(action) {
    var e = { schema_version: '2', event_type: 'navigation', event_id: eventId(), action: action,
              artifact_id: D.artifact_id, session_id: D.session_id,
              position: Math.round(v.currentTime * 1000) / 1000, timestamp: new Date().toISOString() };
    nav.push(e);
    window.parent.postMessage(e, '*');
  }

  // ---- tracks: the exact .vtt files, served as blob: URLs (file:// blocks <track src="x.vtt">, D20.9)
  var trackEls = [];
  function addTrack(kind, label, key, on) {
    var t = document.createElement('track');
    t.kind = kind; t.label = label; t.srclang = 'en';
    t.src = URL.createObjectURL(new Blob([D.tracks[key]], { type: 'text/vtt' }));
    if (on) t.default = true;
    v.appendChild(t);
    t.track.mode = on ? 'showing' : 'hidden';
    t.addEventListener('load', boot);
    trackEls.push(t);
    return t;
  }
  // captions are drawn in a band of their own under the film (never over the picture or the controls), so the
  // track stays hidden to the browser and the band shows its active cue
  var capT = addTrack('captions', D.captions_label, 'captions', false);
  var capOn = true;
  function showCaption() {
    var band = $('captext'), t = capT.track, a = t.activeCues, txt = [];
    for (var i = 0; a && i < a.length; i++) txt.push(a[i].text);
    band.textContent = capOn ? txt.join(' ') : '';
  }
  capT.track.addEventListener('cuechange', showCaption);
  var chapT = addTrack('chapters', U.chapters, 'chapters', false);
  var metaT = addTrack('metadata', 'states', 'states', false);
  function cuesOf(t) {
    var out = [], c = t.track.cues;
    for (var i = 0; i < c.length; i++) out.push({ start: c[i].startTime, end: c[i].endTime, id: c[i].id, text: c[i].text });
    return out;
  }

  var meta = [], chaps = [], caps = [], booted = false, unlockIdx = -1;
  var mode = 'film', returnTime = 0, edit = null, step = null, seed = null, quiet = false, lastKey = '';
  var Q = D.questions || [], picked = {}, passed = {}, asking = null, practice = false;

  // ---- predictions (ASK)
  function now() { return mode === 'film' || mode === 'ask' ? v.currentTime : returnTime; }
  function askAt(t) {
    if (!practice) return null;  // explanation first: the film stops for a prediction only in practice mode
    for (var i = 0; i < Q.length; i++) {
      var q = Q[i];
      if (!picked[q.scene] && t >= q.pause_at - 0.03 && t < q.resume_at) return q;
    }
    return null;
  }
  function qFor(scene) { for (var i = 0; i < Q.length; i++) if (Q[i].scene === scene) return Q[i]; return null; }
  function notePassed(t) { Q.forEach(function (q) { if (t >= q.answer_at - FRAME_US / 1e6) passed[q.scene] = true; }); }
  function sealedChapter(k) {
    return Q.some(function (q) { return q.sealed.indexOf(k) >= 0 && !picked[q.scene] && !passed[q.scene]; });
  }
  function startAsk(q) {
    asking = q; mode = 'ask';
    if (!v.paused) v.pause();
    if (Math.abs(v.currentTime - q.pause_at) > 0.04) { quiet = true; v.currentTime = q.pause_at; }
    paint();
    var first = document.querySelector('#state .opt');
    if (first) first.focus({ preventScroll: true });
  }
  function pick(q, i) {
    if (picked[q.scene]) return;
    picked[q.scene] = { i: i };
    var wasAsking = mode === 'ask' && asking === q;
    emit('reveal');
    asking = null;
    if (mode === 'ask') mode = 'film';
    if (wasAsking || (mode === 'film' && v.currentTime >= q.pause_at - 0.05 && v.currentTime < q.resume_at)) {
      quiet = true; v.currentTime = q.resume_at;
      var p = v.play(); if (p && p.catch) p.catch(function () {});
    }
    lastKey = '';
    paint();
  }
  // a frame clock while playing: the pause point is met within one display frame, not one timeupdate (250 ms)
  function tick() {
    if (v.paused || !booted) return;
    if (mode === 'film') {
      var t = v.currentTime, q = askAt(t);
      notePassed(t);
      if (q) { startAsk(q); return; }
      for (var i = 0; i < Q.length; i++) {
        var a = Q[i];
        // practice mode, already answered: go on to the answer scene as a pick does
        if (practice && picked[a.scene] && t >= a.pause_at && t < a.resume_at - 0.1) { quiet = true; v.currentTime = a.resume_at; break; }
      }
    }
    window.requestAnimationFrame(tick);
  }

  function boot() {
    if (booted || !trackEls.every(function (t) { return t.readyState === 2; })) return;
    meta = cuesOf(metaT).map(function (c) { return { start: c.start, end: c.end, p: JSON.parse(c.text) }; });
    chaps = cuesOf(chapT); caps = cuesOf(capT);
    meta.forEach(function (c, i) { if (c.p.cue === D.unlock_cue) unlockIdx = i; });
    booted = true;
    buildChapters();
    paint();
    emit('open');
  }

  // ---- views
  function filmView(i) {
    var c = meta[i], p = c.p, s = p.state;
    return { origin: 'film', at: c.start, cue: p.cue, kind: p.kind, state_id: s.state_id, label: s.label,
             program: s.program, file: s.program_path.split('/').pop(), code: s.code, path: s.path, line: s.line,
             output: s.output, vars: s.vars, question: p.question || null };
  }
  function liveView(n, brk) {
    var L = D.live, P = L.programs[brk ? L.alt : L.base], cs = P.cases, start = -1, i;
    for (i = 0; i < cs.length && start < 0; i++) if (cs[i].label === n) start = i;
    for (i = 0; i < cs.length && start < 0; i++) if (cs[i].label === 'default') start = i;
    var ran = [], exit = 'nomatch';
    if (start >= 0) {
      exit = 'end';
      for (i = start; i < cs.length; i++) { ran.push(cs[i]); if (cs[i].brk) { exit = 'break'; break; } }
    }
    var path = [P.n_line, P.switch_line], out = [], tags = {};
    ran.forEach(function (c) {
      path.push(c.line); path = path.concat(c.stmts); out = out.concat(c.out);
      if (c.brk) path.push(c.brk_line);
    });
    P.tail.forEach(function (t) { path.push(t.line); out.push(t.out); });
    function tag(line, key, tone, o) { (tags[line] = tags[line] || []).push({ key: key, tone: tone, text: o ? fmt(U[key], o) : U[key] }); }
    if (n !== P.n0) tag(P.n_line, 'x_tag_changed', 'muted', { n0: P.n0 });
    if (!ran.length) tag(P.switch_line, 'x_tag_nomatch', 'muted');
    else {
      tag(ran[0].line, 'enter_label', 'path');
      for (i = 1; i < ran.length; i++) tag(ran[i].line, 'x_tag_fall', 'warn');
      if (exit === 'break') tag(ran[ran.length - 1].brk_line, 'exit_label', 'path');
      else tag(P.close_line, 'x_tag_end', 'path');
    }
    var vars = {}; vars[L.var] = String(n);
    return { origin: 'yours', n: n, brk: brk, program: P.id, file: P.file, code: P.lines, path: path, line: null,
             output: out.map(function (o) { return { text: o }; }), vars: vars, tags: tags, exit: exit,
             ran: ran.map(function (c) { return c.label; }), nChanged: n !== P.n0, nLine: P.n_line, P: P,
             prov: n === P.n0 ? fmt(U.x_captured, { file: P.file, n: n, sha: P.sha }) : fmt(U.x_computed, { n0: P.n0 }),
             provKey: n === P.n0 ? 'x_captured' : 'x_computed' };
  }

  // ---- the knob (AC-6.6, D23.5): the lesson's own input, changed in EXPLORE. Every value comes from ive-data.js,
  // written by ptk from captured runs or ptk/expect_neuron.py; the page only picks and lays them out.
  var KN = D.knob || null;
  function knobSeed() { return KN.kind === 'neuron' ? { i: KN.start[0], j: KN.start[1] } : { v: KN.first, step: null }; }
  function knobRun(v) { for (var i = 0; i < KN.values.length; i++) if (KN.values[i].value === v) return KN.values[i]; return null; }
  function knobView(e) {
    var V = { origin: 'yours', line: null, path: [], vars: {}, knob: e };
    if (KN.kind === 'neuron') {
      var w = KN.w2[e.i], b = KN.b[e.j], row = KN.rows[w + '|' + b], chk = KN.checks[w + '|' + b];
      V.program = 'knob'; V.file = KN.file; V.code = KN.code;
      V.subst = { w2: w, b: b };
      V.output = [KN.x1 + ' * ' + KN.w1 + ' = ' + row.t1, KN.x2 + ' * ' + w + ' = ' + row.t2, 'b = ' + row.b + '  z = ' + row.z,
                  'a = ' + row.a].map(function (t, k) { return chk ? { text: t, fact: chk.facts[k] } : { text: t }; });
      V.prov = chk ? chk.prov : KN.computed; V.provKey = chk ? 'x_captured_run' : 'k_computed';
      V.row = row; V.w2 = w; V.b = b; V.check = chk;
      V.editKey = 'w2=' + w + ';b=' + b;
    } else {
      var r = knobRun(e.v);
      V.program = r.program; V.file = r.file; V.code = r.code; V.run = r;
      V.prov = r.prov; V.provKey = 'x_captured_run';
      if (KN.kind === 'calls') {
        var n = r.steps.length, k = e.step === null ? n : Math.max(1, Math.min(n, e.step));
        V.step = k; V.nsteps = n; V.frames = r.steps[k - 1].frames;
        V.output = r.steps[k - 1].printed.map(function (t) { return { text: t }; });
      } else V.output = r.output;
      V.editKey = KN.var + '=' + e.v + (KN.kind === 'calls' ? ';step=' + (V.step || '') : '');
    }
    return V;
  }
  function svgEl(tag, attrs, cls) {
    var e = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    if (cls) e.setAttribute('class', cls);
    return e;
  }
  function neuronDraw(V) {
    // the explorer knob's drawing (knob.js): bars along a number line and the gate's dot, placed from ptk's numbers
    var G = KN.geom, row = V.row;
    function X(v) { return G.pad + (v - G.lo) / (G.hi - G.lo) * (G.w - 2 * G.pad); }
    function GX(z) { return G.pad + (z - G.zlo) / (G.zhi - G.zlo) * (G.w - 2 * G.pad); }
    function GY(a) { return G.gy0 - a / G.ahi * (G.gy0 - G.gy1); }
    function axis(svg, y, ticks, map) {
      svg.appendChild(svgEl('line', { x1: G.pad, y1: y, x2: G.w - G.pad, y2: y }, 'kax'));
      ticks.forEach(function (t) {
        svg.appendChild(svgEl('line', { x1: map(t), y1: y - 4, x2: map(t), y2: y + 4 }, 'kax'));
        var tx = svgEl('text', { x: map(t), y: y + 18, 'text-anchor': 'middle', 'data-axis': 'k', 'data-tick': String(t) }, 'ktick');
        tx.textContent = String(t).replace('-', '\u2212'); svg.appendChild(tx);
      });
    }
    var add = svgEl('svg', { viewBox: '0 0 320 150', role: 'img' }), gate = svgEl('svg', { viewBox: '0 0 320 150', role: 'img' });
    var parts = [[row.t1, row.t1f], [row.t2, row.t2f], [row.b, +row.b]], s0 = 0;
    parts.forEach(function (p, k) {
      var a = s0, b = s0 + p[1], y = 26 + k * 30, cls = p[1] >= 0 ? 'kbar pos' : 'kbar neg';
      var lab = svgEl('text', { x: Math.min(X(a), X(b)), y: y - 8 }, 'klab ' + (p[1] >= 0 ? 'pos' : 'neg'));
      lab.textContent = KN.labels[k] + ' ' + p[0]; add.appendChild(lab);
      add.appendChild(svgEl('line', { x1: X(a), y1: y, x2: X(b), y2: y }, cls));
      add.appendChild(svgEl('circle', { cx: X(b), cy: y, r: 4.5 }, cls + ' end'));
      if (k) add.appendChild(svgEl('line', { x1: X(a), y1: y - 30, x2: X(a), y2: y }, 'kguide'));
      s0 = b;
    });
    axis(add, 120, G.ticks, X);
    add.appendChild(svgEl('path', { d: 'M' + X(row.zf) + ',110 l-6,-10 h12 z' }, 'kzmark'));
    gate.appendChild(svgEl('path', { d: 'M' + GX(G.zlo) + ',' + GY(0) + ' L' + GX(0) + ',' + GY(0) + ' L' + GX(G.zhi) + ',' + GY(G.zhi) }, 'krelu'));
    axis(gate, GY(0), G.zticks, GX);
    gate.appendChild(svgEl('path', { d: 'M' + GX(row.zf) + ',' + GY(0) + ' L' + GX(row.zf) + ',' + GY(row.af) }, 'kguide'));
    gate.appendChild(svgEl('circle', { cx: GX(row.zf), cy: GY(row.af), r: 7 }, 'kdot'));
    var box = el('div', 'kneuron kview'); box.setAttribute('data-key', 'knob-view');
    function col(lbl, kids) { var c = el('div', 'kn-col'); c.appendChild(el('p', 'lbl', lbl)); kids.forEach(function (k) { c.appendChild(k); }); return c; }
    function eq(parts2) { var p = el('p', 'kn-eq'); parts2.forEach(function (x) { p.appendChild(typeof x === 'string' ? document.createTextNode(x) : x); }); return p; }
    function val(t, neg) { return el('b', neg ? 'neg' : null, t); }
    box.appendChild(col(U.panel_multiply, [eq([KN.x1 + ' \u00d7 ' + KN.w1 + ' \u2192 ', val(row.t1, row.t1f < 0)]),
      eq([KN.x2 + ' \u00d7 ' + V.w2 + ' \u2192 ', val(row.t2, row.t2f < 0)]), eq([U.neuron_bias + ' ', val(row.b, +row.b < 0)])]));
    box.appendChild(col(U.panel_add, [add, eq([U.axis_z + ' = ', val(row.z, false)])]));
    box.appendChild(col(U.panel_gate, [gate, eq([U.axis_a + ' = ', val(row.a, false)])]));
    return box;
  }
  function stackDraw(V) {
    var box = el('div', 'kview kstackbox'); box.setAttribute('data-key', 'knob-view');
    box.appendChild(el('p', 'lbl', fmt(U.s_step, { k: V.step, n: V.nsteps })));
    var ol = el('ol', 'kstack');
    V.frames.forEach(function (f) {
      var li = el('li', 'kframe'); li.setAttribute('data-status', f.status);
      var head = el('span', 'kfl'); head.appendChild(el('code', null, f.label));
      if (f.status === 'returning') { head.appendChild(el('span', 'lbl', U.frame_returns)); head.appendChild(el('b', 'kret', f.ret)); }
      else head.appendChild(el('span', 'lbl', U['frame_' + f.status]));
      li.appendChild(head);
      var vs = el('span', 'kfv');
      if (f.n !== null) vs.appendChild(el('span', 'kvar', 'n = ' + f.n));
      var r = el('span', 'kvar', f.r);
      if (f.slot) { var sl = el('span', 'kslot'); sl.setAttribute('role', 'img'); sl.setAttribute('aria-label', U.k_slot); r.appendChild(sl); }
      vs.appendChild(r); li.appendChild(vs); ol.appendChild(li);
    });
    box.appendChild(ol);
    return box;
  }
  function sentences(V) {
    var box = el('div', 'ksent');
    if (KN.kind === 'neuron') {
      var T = KN.texts, f = function (t) { return t.replace(/\{(\w+)\}/g, function (_, k) { return { w2: V.w2, b: V.b, z: V.row.z, a: V.row.a }[k]; }); };
      var p = el('p', 'klive', f(T.live)); p.setAttribute('data-chrome', 'k_live'); p.setAttribute('data-claims', T.claims.live); box.appendChild(p);
      if (T.tiny && V.row.zf !== 0 && Math.abs(V.row.zf) < 1e-9) {
        var q = el('p', 'klive', f(T.tiny)); q.setAttribute('data-chrome', 'k_tiny'); q.setAttribute('data-claims', T.claims.tiny); box.appendChild(q);
      }
      if (V.check) { var c0 = el('p', null, fmt(U.k_captured_point, { file: V.check.file })); c0.setAttribute('data-chrome', 'k_captured_point'); box.appendChild(c0); }
    }
    var cl = (V.run ? V.run.claims : []).concat(KN.common || []);
    cl.forEach(function (c) {
      var p = el('p', null, c.text); p.setAttribute('data-claim', c.id);
      if (c.facts && c.facts.length) p.setAttribute('data-captured', c.facts.join(' '));  // a sentence about captured runs
      box.appendChild(p);
    });
    return box;
  }
  function buildKnob() {
    var host = $('knobctl');
    if (KN.kind === 'neuron') {
      [['w2', KN.w2, 0], ['b', KN.b, 1]].forEach(function (d) {
        var lab = el('label', 'kslider'), nm = el('span', 'lbl', fmt(U.k_slider, { name: d[0] }));
        var r = el('input'); r.type = 'range'; r.id = 'knob-' + d[0]; r.min = '0'; r.max = String(d[1].length - 1); r.step = '1';
        var o = el('output', 'kout1'); o.id = 'knob-' + d[0] + '-v';
        lab.appendChild(nm); lab.appendChild(r); lab.appendChild(o); host.appendChild(lab);
        r.addEventListener('input', function () {
          if (mode !== 'explore' || locked()) return;
          var e = edit && edit.knob ? edit.knob : knobSeed(), ne = { i: e.i, j: e.j };
          if (d[2] === 0) ne.i = +r.value; else ne.j = +r.value;
          edit = { knob: ne }; step = null; paint();
        });
      });
    } else {
      var fs = el('fieldset', 'seg'); fs.id = 'knob-v'; fs.setAttribute('data-state-var', KN.var);
      fs.appendChild(el('legend', 'lbl', KN.label));
      var opts = el('div', 'opts');
      KN.values.forEach(function (v) {
        var lab = el('label'), r = el('input'); r.type = 'radio'; r.name = 'knob-v'; r.value = v.value;
        lab.appendChild(r); lab.appendChild(el('span', null, v.value)); opts.appendChild(lab);
        r.addEventListener('change', function () {
          if (r.checked && mode === 'explore' && !locked()) { edit = { knob: { v: v.value, step: null } }; step = null; paint(); }
        });
      });
      fs.appendChild(opts); host.appendChild(fs);
    }
  }
  function syncKnob(lk) {
    var e = edit && edit.knob ? edit.knob : knobSeed();
    if (KN.kind === 'neuron') {
      [['w2', KN.w2, e.i], ['b', KN.b, e.j]].forEach(function (d) {
        var r = $('knob-' + d[0]); r.disabled = lk; r.value = String(d[2]);
        $('knob-' + d[0] + '-v').textContent = d[1][d[2]]; r.setAttribute('aria-valuetext', d[1][d[2]]);
      });
    } else document.querySelectorAll('#knob-v input').forEach(function (r) { r.disabled = lk; r.checked = r.value === e.v; });
  }

  // ---- render the panel
  function render(V) {
    var xp = $('xp'), box = $('state');
    xp.setAttribute('data-origin', V.origin);
    box.textContent = '';
    box.setAttribute('data-program', V.program);
    if (V.origin === 'film' || V.origin === 'step') {
      box.setAttribute('data-state', V.state_id); box.setAttribute('data-cue', V.cue); box.setAttribute('data-kind', V.kind);
      if (V.origin === 'step') box.setAttribute('data-edit', 'step=' + V.cue); else box.removeAttribute('data-edit');
      var lab = el('p', 'slabel', V.label); lab.setAttribute('data-trace', V.state_id); box.appendChild(lab);
    } else {
      box.removeAttribute('data-state'); box.removeAttribute('data-cue'); box.setAttribute('data-kind', 'edit');
      box.setAttribute('data-edit', V.knob ? V.editKey : 'n=' + V.n + (V.brk ? ';break' : ''));
    }
    $('origin').textContent = V.origin === 'film' ? fmt(U.ive_from_film, { time: clock(V.at) })
      : (V.origin === 'step' ? U.ive_step_back : U.ive_yours);
    var fig = el('figure', 'codepanel'); fig.setAttribute('data-key', 'code');
    var cap = el('figcaption', 'lbl'); cap.appendChild(el('span', null, U.code_label)); cap.appendChild(document.createTextNode(' · '));
    var fn = el('span', 'file', V.file); fn.setAttribute('data-label', 'program-file'); cap.appendChild(fn); fig.appendChild(cap);
    var ol = el('ol', 'code'); ol.setAttribute('data-code', V.program);
    V.code.forEach(function (row) {
      var no = row[0], li = el('li', 'ln' + (V.path.indexOf(no) >= 0 ? ' ran' : '') + (no === V.line ? ' cur' : ''));
      li.setAttribute('data-line', String(no));
      li.appendChild(el('span', 'no', String(no)));
      var body = el('span', 'body'), code = el('code', 'src');
      var sub = V.subst && KN && Object.keys(KN.subst).filter(function (k) { return KN.subst[k].line === no; })[0];
      if (V.origin === 'yours' && V.P && no === V.nLine) {
        code.appendChild(document.createTextNode(V.P.n_prefix));
        code.appendChild(el('b', 'nval' + (V.nChanged ? ' changed' : ''), String(V.n)));
        code.appendChild(document.createTextNode(V.P.n_suffix));
      } else if (sub) {
        // the slider's value in the program's own line (computed: the page says so under the output)
        var S1 = KN.subst[sub], rest = row[1].slice(S1.prefix.length);
        code.appendChild(document.createTextNode(S1.prefix));
        code.appendChild(el('b', 'nval changed', V.subst[sub]));
        code.appendChild(document.createTextNode(S1.suffix));
        void rest;
      } else code.textContent = row[1];
      body.appendChild(code);
      if (V.tags && V.tags[no]) {
        var tg = el('span', 'tags');
        V.tags[no].forEach(function (t) { var g = el('span', 'tag ' + t.tone, t.text); g.setAttribute('data-chrome', t.key); tg.appendChild(g); });
        body.appendChild(tg);
      }
      li.appendChild(body); ol.appendChild(li);
    });
    fig.appendChild(ol);
    var side = el('div', 'xside');
    var os = el('section', 'outpanel'); os.setAttribute('data-key', 'output');
    os.appendChild(el('h3', 'lbl', U.output_label));
    var out = el('ol', 'out'); out.setAttribute('data-role', 'output');
    if (!V.output.length) out.appendChild(el('li', 'empty', '—'));
    V.output.forEach(function (o, k) {
      var li = el('li'); li.appendChild(el('span', 'k', V.run && V.run.views ? V.run.views[k].label : String(k + 1)));
      var s = el('span', 'val', o.text); if (o.fact) s.setAttribute('data-fact', o.fact); li.appendChild(s); out.appendChild(li);
    });
    os.appendChild(out);
    var vars = Object.keys(V.vars || {}).map(function (k) { return k + ' = ' + V.vars[k]; }).join('   ');
    var vp = el('p', 'vars'); vp.appendChild(el('span', 'lbl', U.vars_label)); vp.appendChild(el('span', 'mono', vars));
    vp.setAttribute('data-code', V.program);
    if (vars) os.appendChild(vp);  // no empty VARIABLES heading
    side.appendChild(os);
    var P = D.panels && D.panels[V.state_id], mb = null;
    if (P && V.origin !== 'yours') {
      // the mechanism at this state (pre-drawn by ptk; CSS picks the copy for the width and colour scheme). It leads
      // the panel, above the code, so on a phone it is the first thing under the title (B3, AC-10.3)
      mb = el('figure', 'mechbox place-' + D.panel_place); mb.setAttribute('data-key', 'panel');
      mb.innerHTML = P.wl + P.wd + P.pl + P.pd;
    }
    var kv = null;
    if (V.knob) {
      kv = KN.kind === 'neuron' ? neuronDraw(V) : (KN.kind === 'calls' ? stackDraw(V) : null);
      side.appendChild(sentences(V));
    }
    var qFirst = null;
    if (V.question) {
      var q = el('div', 'q'); q.setAttribute('data-key', 'question');
      q.appendChild(el('p', 'lbl', U.question_label));
      var qt = el('p', 'qt', V.question.prompt); qt.setAttribute('data-question', V.question.scene); q.appendChild(qt);
      var QQ = qFor(V.question.scene), got = QQ && picked[QQ.scene];
      if (QQ && !got && (mode === 'ask' || mode === 'film') && V.origin === 'film') {
        // the options, as in the Q&A; in EXPLORE the learner has left the question, so only the prompt shows
        var fs = el('div', 'opts ask'); fs.setAttribute('role', 'group'); fs.setAttribute('aria-label', U.qa_choose);
        QQ.options.forEach(function (o, k) {
          var b = el('button', 'opt', o.text); b.type = 'button'; b.setAttribute('data-option', QQ.scene + '.' + k);
          b.addEventListener('click', function () { pick(QQ, k); });
          fs.appendChild(b);
        });
        q.appendChild(fs);
        if (mode === 'ask') { var h = el('p', 'askhint', U.ive_ask_hint); h.setAttribute('data-chrome', 'ive_ask_hint'); q.appendChild(h); }
        qFirst = q;  // an open question leads the panel, so its options are in view when the film stops
      }
      if (QQ && got) q.appendChild(verdict(QQ, got.i));
      side.appendChild(q);
    } else if (V.origin === 'film') {
      // the verdict stays beside the answer while it plays
      var A = Q.filter(function (x) { return picked[x.scene] && v.currentTime >= x.resume_at - 0.05 && v.currentTime < x.verdict_until; })[0];
      if (A) { var vq = el('div', 'q done'); vq.appendChild(verdict(A, picked[A.scene].i)); side.appendChild(vq); }
    }
    if (V.origin === 'yours') { var pv = el('p', 'prov', V.prov); pv.setAttribute('data-chrome', V.provKey); side.appendChild(pv); }
    var stage = el('div', 'xstage'); stage.appendChild(fig); stage.appendChild(side);
    if (qFirst) { box.appendChild(qFirst); }
    if (kv) box.appendChild(kv);
    box.appendChild(stage);
    if (mb) box.insertBefore(mb, box.firstChild);
  }

  function verdict(q, i) {
    var o = q.options[i], box = el('div', 'verdict'); box.setAttribute('data-verdict', o.correct ? 'correct' : 'wrong');
    box.appendChild(el('p', 'pick', fmt(U.ive_your_pick, { pick: o.text })));
    box.appendChild(el('p', 'vd', o.correct ? U.qa_correct : U.qa_wrong));
    if (!o.correct) {
      box.appendChild(el('p', 'belief', o.misconception));
      box.appendChild(el('p', 'lbl', U.qa_correction));
      box.appendChild(el('p', 'fix', o.correction));
    }
    return box;
  }

  function shownIdx() { return Math.max(0, windowAt(meta, now())); }
  function seedFromFilm() {
    if (!D.live) return null;
    var s = meta[shownIdx()].p.state, n = Number((s.vars || {})[D.live.var]);
    return { n: isFinite(n) ? n : D.live.n0, brk: s.program === D.live.alt };
  }
  function locked() { return unlockIdx >= 0 && windowAt(meta, returnTime) < unlockIdx; }

  function paint() {
    if (!booted) return;
    var i = shownIdx(), V;
    if (mode === 'explore' && edit && edit.knob) V = knobView(edit.knob);
    else if (mode === 'explore' && edit) V = liveView(edit.n, edit.brk);
    else if (mode === 'explore' && step !== null) { V = filmView(step); V.origin = 'step'; }
    else { V = filmView(i); V.at = now(); }
    var vkey = Q.map(function (q) { return (picked[q.scene] ? 'p' + picked[q.scene].i : '-') + (v.currentTime >= q.resume_at - 0.05 && v.currentTime < q.verdict_until ? 'v' : ''); }).join('');
    var key = [mode, V.origin, V.cue, V.state_id, V.program, edit && edit.n, edit && edit.brk, V.editKey || '', clock(V.at || 0), vkey].join('|');
    if (key !== lastKey) { render(V); lastKey = key; }
    var xp = $('xp'), exploring = mode === 'explore';
    xp.setAttribute('data-mode', mode);
    document.documentElement.setAttribute('data-ive-mode', mode);
    document.documentElement.setAttribute('data-ive-ask', mode === 'ask' ? asking.scene : '');
    document.documentElement.setAttribute('data-ive-practice', String(practice));
    $('mode-label').textContent = exploring ? U.ive_mode_label_explore : (mode === 'ask' ? U.ive_mode_label_ask : U.ive_mode_label_film);
    $('mode-text').textContent = exploring ? fmt(U.ive_mode_explore, { time: clock(returnTime) })
      : (mode === 'ask' ? fmt(U.ive_mode_ask, { time: clock(v.currentTime) }) : U.ive_mode_film);
    $('explore').hidden = exploring; $('return').hidden = !exploring;
    $('tools').hidden = !exploring;
    var cur = step !== null ? step : i;
    if (edit && edit.knob && KN.kind === 'calls') {
      // stepping through the chosen run, line by line
      $('prev').disabled = !exploring || V.step <= 1;
      $('next').disabled = !exploring || V.step >= V.nsteps;
    } else {
      $('prev').disabled = !exploring || edit !== null || cur <= 0;
      $('next').disabled = !exploring || edit !== null || cur >= i;
    }
    if (KN) {
      var klk = exploring && locked();
      $('live').setAttribute('data-locked', String(klk));
      $('locked').hidden = !klk;
      syncKnob(klk);
      $('live-reset').disabled = klk || edit === null;
    }
    if (D.live) {
      var lk = exploring && locked(), st = edit || seed || { n: D.live.n0, brk: false };
      $('live').setAttribute('data-locked', String(lk));
      $('locked').hidden = !lk;
      document.querySelectorAll('#live-n input').forEach(function (r) { r.disabled = lk; r.checked = Number(r.value) === st.n; });
      $('live-brk').disabled = lk; $('live-brk').setAttribute('aria-pressed', String(st.brk));
      $('live-brk-state').textContent = st.brk ? U.x_on : U.x_off;
      $('live-reset').disabled = lk || edit === null;
    }
    transcript();
    var ci = windowAt(chaps, now());
    document.querySelectorAll('#chapters button').forEach(function (b, k) {
      b.setAttribute('aria-current', String(k === ci));
      var s = sealedChapter(k), ttl = b.querySelector('.ttl');
      if (b.getAttribute('data-sealed') !== String(s)) {
        b.setAttribute('data-sealed', String(s));
        ttl.textContent = s ? U.ive_chapter_sealed : chaps[k].text;
      }
    });
  }

  // ---- the state machine
  function enterExplore() {
    if (!booted || mode === 'explore' || mode === 'ask') return;
    mode = 'explore'; returnTime = v.currentTime; edit = null; step = null; seed = seedFromFilm();
    if (!v.paused) v.pause();
    emit('explore');
    paint();
  }
  function returnToFilm() {
    if (mode !== 'explore') return;
    var t = returnTime;
    mode = 'return'; edit = null; step = null; seed = null;
    paint();
    emit('return');
    quiet = true;
    v.currentTime = t;
    var done = function () { if (mode === 'return') { mode = 'film'; paint(); } };
    var p = v.play();
    if (p && p.then) p.then(done, done); else done();
  }
  v.addEventListener('pause', function () {
    if (mode === 'explore' && edit === null && step === null) { returnTime = v.currentTime; paint(); }  // the settled pause position
    else if (!v.ended && mode === 'film' && v.readyState >= 1) enterExplore();
  });
  v.addEventListener('play', function () {
    if (mode === 'ask') {  // the film holds until the learner picks, at the pause point exactly
      v.pause(); quiet = true; v.currentTime = asking.pause_at; return;
    }
    if (mode === 'explore') { returnToFilm(); return; }
    var q = askAt(v.currentTime);
    if (q && mode === 'film' && v.currentTime >= q.pause_at - 0.03) { startAsk(q); return; }
    window.requestAnimationFrame(tick);
  });
  v.addEventListener('playing', function () { if (mode === 'return') { mode = 'film'; paint(); } window.requestAnimationFrame(tick); });
  v.addEventListener('seeked', function () {
    if (mode === 'ask' && (v.currentTime < asking.pause_at - 0.05 || v.currentTime >= asking.resume_at)) { mode = 'film'; asking = null; }
    if (mode !== 'explore') notePassed(v.currentTime);
    if (mode === 'explore') { returnTime = v.currentTime; edit = null; step = null; seed = seedFromFilm(); }
    if (quiet) quiet = false; else if (booted) emit('seek');
    paint();
  });
  v.addEventListener('timeupdate', function () { if (mode === 'film') notePassed(v.currentTime); paint(); showCaption(); });
  v.addEventListener('seeked', showCaption);
  v.addEventListener('ended', function () { mode = 'film'; paint(); });
  $('explore').addEventListener('click', function () { if (mode === 'ask') { mode = 'film'; asking = null; } enterExplore(); });
  $('return').addEventListener('click', returnToFilm);
  // practice mode (AC-6.8): off by default; on, the film stops at each question until a pick
  var prBtn = $('practice');
  if (prBtn) prBtn.addEventListener('click', function () {
    practice = !practice;
    prBtn.setAttribute('aria-pressed', String(practice));
    $('practice-state').textContent = practice ? U.x_on : U.x_off;
    if (!practice && mode === 'ask') { mode = 'film'; asking = null; }  // the hold ends at once
    lastKey = '';
    paint();
  });
  function seekTo(t, action) { quiet = true; v.currentTime = t; emit(action); }

  function knobStep(d) {
    var V = knobView(edit.knob), k = Math.max(1, Math.min(V.nsteps, V.step + d));
    edit = { knob: { v: edit.knob.v, step: k } }; paint();
  }
  $('prev').addEventListener('click', function () {
    if (edit && edit.knob && KN.kind === 'calls') { knobStep(-1); return; }
    var c = step !== null ? step : shownIdx(); if (c > 0) { step = c - 1; paint(); } });
  $('next').addEventListener('click', function () {
    if (edit && edit.knob && KN.kind === 'calls') { knobStep(1); return; }
    var c = step !== null ? step : shownIdx(); if (c < shownIdx()) { step = c + 1 === shownIdx() ? null : c + 1; paint(); } });
  if (KN) {
    buildKnob();
    $('live-reset').addEventListener('click', function () { edit = null; paint(); });
  }
  if (D.live) {
    // the values n can take (every case label, one below and one above), built here so the static
    // page holds no bare numbers
    D.live.domain.forEach(function (n) {
      var lab = el('label'), r = el('input'); r.type = 'radio'; r.name = 'live-n'; r.value = String(n);
      lab.appendChild(r); lab.appendChild(el('span', null, String(n))); $('live-opts').appendChild(lab);
    });
    document.querySelectorAll('#live-n input').forEach(function (r) {
      r.addEventListener('change', function () { if (r.checked && mode === 'explore' && !locked()) { edit = { n: Number(r.value), brk: (edit || seed).brk }; step = null; paint(); } });
    });
    $('live-brk').addEventListener('click', function () { if (mode === 'explore' && !locked()) { var s = edit || seed; edit = { n: s.n, brk: !s.brk }; step = null; paint(); } });
    $('live-reset').addEventListener('click', function () { edit = null; paint(); });
  }
  var capBtn = $('caps');
  capBtn.addEventListener('click', function () {
    capOn = !capOn;
    capT.track.mode = 'hidden';
    $('capband').setAttribute('data-on', String(capOn));
    capBtn.setAttribute('aria-pressed', String(capOn));
    capBtn.textContent = capOn ? U.captions_on : U.captions_off;
    showCaption();
  });

  // ---- chapters (all titles) and the transcript (only cues already reached)
  function buildChapters() {
    var list = $('chapters');
    chaps.forEach(function (c) {
      var li = el('li'), b = el('button'); b.type = 'button';
      b.appendChild(el('span', 'time', clock(c.start))); b.appendChild(el('span', 'ttl', c.text));
      b.addEventListener('click', function () { seekTo(c.start, 'chapter'); });
      li.appendChild(b); list.appendChild(li);
    });
  }
  function transcript() {
    var list = $('tx'), t = now(), n = windowAt(caps, t) + 1;
    while (list.childNodes.length > n) list.removeChild(list.lastChild);
    for (var j = list.childNodes.length; j < n; j++) (function (c) {
      var li = el('li'), b = el('button'); b.type = 'button';
      b.appendChild(el('span', 'time', clock(c.start))); b.appendChild(el('span', 'ttl', c.text));
      b.addEventListener('click', function () { seekTo(c.start, 'seek'); });
      li.appendChild(b); list.appendChild(li);
    })(caps[j]);
    for (var k = 0; k < list.childNodes.length; k++) {
      var c = caps[k];
      list.childNodes[k].firstChild.setAttribute('aria-current', String(c.start - t < FRAME_US / 1e6 && t < c.end));
    }
  }

  document.addEventListener('keydown', function (e) {
    var t = e.target, tag = t && t.tagName;
    if (e.key !== ' ' || e.altKey || e.ctrlKey || e.metaKey || (tag && tag !== 'BODY' && tag !== 'HTML')) return;
    e.preventDefault();
    if (v.paused) { var p = v.play(); if (p && p.catch) p.catch(function () {}); } else v.pause();
  });
  document.documentElement.classList.add('js');
  window.__ptkReady = function () { return booted && v.readyState >= 1; };
  window.__ptkIve = {
    resolve: function (t) { var i = windowAt(meta, t); return i < 0 ? null : meta[i].p.cue; },
    chapterAt: function (t) { return windowAt(chaps, t); },
    mode: function () { return mode; },
    practice: function () { return practice; },
    asking: function () { return asking ? asking.scene : null; },
    picked: function () { return JSON.parse(JSON.stringify(picked)); },
    questions: function () { return Q; },
    returnTime: function () { return returnTime; },
    knob: function () { return KN ? { kind: KN.kind, edit: edit && edit.knob ? JSON.parse(JSON.stringify(edit.knob)) : null } : null; },
    live: function (n, brk) { var w = liveView(n, brk); return { program: w.program, path: w.path, output: w.output.map(function (o) { return o.text; }), exit: w.exit, ran: w.ran }; },
    frameUs: FRAME_US
  };
})();
