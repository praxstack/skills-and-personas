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
      box.setAttribute('data-edit', 'n=' + V.n + (V.brk ? ';break' : ''));
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
      if (V.origin === 'yours' && no === V.nLine) {
        code.appendChild(document.createTextNode(V.P.n_prefix));
        code.appendChild(el('b', 'nval' + (V.nChanged ? ' changed' : ''), String(V.n)));
        code.appendChild(document.createTextNode(V.P.n_suffix));
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
      var li = el('li'); li.appendChild(el('span', 'k', String(k + 1)));
      var s = el('span', 'val', o.text); if (o.fact) s.setAttribute('data-fact', o.fact); li.appendChild(s); out.appendChild(li);
    });
    os.appendChild(out);
    var vars = Object.keys(V.vars).map(function (k) { return k + ' = ' + V.vars[k]; }).join('   ');
    var vp = el('p', 'vars'); vp.appendChild(el('span', 'lbl', U.vars_label)); vp.appendChild(el('span', 'mono', vars));
    vp.setAttribute('data-code', V.program); os.appendChild(vp);
    side.appendChild(os);
    var P = D.panels && D.panels[V.state_id];
    if (P && V.origin !== 'yours') {
      // the mechanism panel at this state (pre-drawn by ptk; CSS picks the copy for the width and colour scheme)
      var mb = el('figure', 'mechbox place-' + D.panel_place); mb.setAttribute('data-key', 'panel');
      mb.innerHTML = P.wl + P.wd + P.pl + P.pd;
      side.insertBefore(mb, os);
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
    if (qFirst) { box.insertBefore(qFirst, box.firstChild.nextSibling); }
    box.appendChild(stage);
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
    if (mode === 'explore' && edit) V = liveView(edit.n, edit.brk);
    else if (mode === 'explore' && step !== null) { V = filmView(step); V.origin = 'step'; }
    else { V = filmView(i); V.at = now(); }
    var vkey = Q.map(function (q) { return (picked[q.scene] ? 'p' + picked[q.scene].i : '-') + (v.currentTime >= q.resume_at - 0.05 && v.currentTime < q.verdict_until ? 'v' : ''); }).join('');
    var key = [mode, V.origin, V.cue, V.state_id, V.program, edit && edit.n, edit && edit.brk, clock(V.at || 0), vkey].join('|');
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
    $('prev').disabled = !exploring || edit !== null || cur <= 0;
    $('next').disabled = !exploring || edit !== null || cur >= i;
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

  $('prev').addEventListener('click', function () { var c = step !== null ? step : shownIdx(); if (c > 0) { step = c - 1; paint(); } });
  $('next').addEventListener('click', function () { var c = step !== null ? step : shownIdx(); if (c < shownIdx()) { step = c + 1 === shownIdx() ? null : c + 1; paint(); } });
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
    live: function (n, brk) { var w = liveView(n, brk); return { program: w.program, path: w.path, output: w.output.map(function (o) { return o.text; }), exit: w.exit, ran: w.ran }; },
    frameUs: FRAME_US
  };
})();
