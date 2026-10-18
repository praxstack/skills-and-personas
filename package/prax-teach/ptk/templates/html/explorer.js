(function () {
  'use strict';
  // Every visible word comes from D.ui (templates/chrome.json) or D.claims (lesson claims); every
  // value from D.programs, which ptk checked against the program source and expect.py at build time.
  var D = JSON.parse(document.getElementById('ptk-explorer').textContent);
  var U = D.ui;
  var st = { n: D.n0, brk: false };
  function $(id) { return document.getElementById(id); }
  function fmt(t, o) { return t.replace(/\{(\w+)\}/g, function (_, k) { return String(o[k]); }); }
  function el(tag, cls, txt) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (txt != null) e.textContent = txt;
    return e;
  }
  function program() { return D.programs[st.brk ? D.alt : D.base]; }

  // C17 6.8.4.2p5: enter at the matching label, else default, else skip the body.
  // C17 6.8.1p4: a label does not stop control. C17 6.8.6.3p2: break ends the switch.
  function run(P, n) {
    var cs = P.cases, i, start = -1;
    for (i = 0; i < cs.length && start < 0; i++) if (cs[i].label === n) start = i;
    for (i = 0; i < cs.length && start < 0; i++) if (cs[i].label === 'default') start = i;
    if (start < 0) return { enter: null, ran: [], exit: 'nomatch' };
    var ran = [], exit = 'end';
    for (i = start; i < cs.length; i++) {
      ran.push(cs[i]);
      if (cs[i].brk) { exit = 'break'; break; }
    }
    return { enter: cs[start], ran: ran, exit: exit };
  }

  function view(P, n) {
    var r = run(P, n), path = [P.n_line, P.switch_line], out = [], tags = {}, prose = [];
    r.ran.forEach(function (c) {
      path.push(c.line);
      path = path.concat(c.stmts);
      out = out.concat(c.out);
      if (c.brk) path.push(c.brk_line);
    });
    P.tail.forEach(function (t) { path.push(t.line); out.push(t.out); });
    function tag(line, key, tone, o) { (tags[line] = tags[line] || []).push({ key: key, tone: tone, text: fmt(U[key], o || {}) }); }
    function say(key, role, o) { prose.push({ key: key, claims: D.roles[role], text: fmt(U[key], o) }); }
    if (n !== P.n0) tag(P.n_line, 'x_tag_changed', 'muted', { n0: P.n0 });
    if (!r.enter) {
      tag(P.switch_line, 'x_tag_nomatch', 'muted');
      say('x_nomatch', 'nomatch', { n: n });
    } else {
      tag(r.enter.line, 'enter_label', 'path');
      say('x_match', 'match', { n: n, k: r.enter.label, line: r.enter.stmts.length ? r.enter.stmts[0] : r.enter.line });
      for (var i = 1; i < r.ran.length; i++) {
        tag(r.ran[i].line, 'x_tag_fall', 'warn');
        say('x_fall', 'labels', { a: r.ran[i - 1].label, b: r.ran[i].label, line: r.ran[i].line });
      }
      var last = r.ran[r.ran.length - 1];
      if (r.exit === 'break') {
        tag(last.brk_line, 'exit_label', 'path');
        say('x_break', 'brk', { line: last.brk_line });
      } else {
        tag(P.close_line, 'x_tag_end', 'path');
        say('x_end', 'bodyend', { k: last.label, line: P.close_line });
      }
    }
    prose.push({ claim: D.claims.tail.id, text: D.claims.tail.text });
    var prov = n === P.n0 ? { key: 'x_captured', text: fmt(U.x_captured, { file: P.file, n: n, sha: P.sha }) }
      : { key: 'x_computed', text: fmt(U.x_computed, { n0: P.n0 }) };
    return { r: r, path: path, out: out, tags: tags, prose: prose, prov: prov };
  }

  function render() {
    var P = program(), V = view(P, st.n);
    var s = $('x-state');
    s.setAttribute('data-n', String(st.n));
    s.setAttribute('data-brk', String(st.brk));
    s.setAttribute('data-program', P.id);
    s.setAttribute('data-enter', V.r.enter ? String(V.r.enter.label) : '');
    s.setAttribute('data-exit', V.r.exit);
    s.setAttribute('data-ran', V.r.ran.map(function (c) { return c.label; }).join(','));
    $('x-file').textContent = P.file;
    var ol = $('x-code');
    ol.textContent = '';
    ol.setAttribute('data-code', P.id);
    P.lines.forEach(function (row) {
      var no = row[0], li = el('li', 'ln' + (V.path.indexOf(no) >= 0 ? ' ran' : ''));
      li.setAttribute('data-line', String(no));
      li.appendChild(el('span', 'no', String(no)));
      var code = el('code', 'src');
      if (no === P.n_line) {
        code.appendChild(document.createTextNode(P.n_prefix));
        var b = el('b', 'nval' + (st.n !== P.n0 ? ' changed' : ''), String(st.n));
        b.setAttribute('data-n', '');
        code.appendChild(b);
        code.appendChild(document.createTextNode(P.n_suffix));
      } else {
        code.textContent = row[1];
      }
      var body = el('span', 'body');
      body.appendChild(code);
      li.appendChild(body);
      if (V.tags[no]) {
        var box = el('span', 'tags');
        V.tags[no].forEach(function (t) {
          var g = el('span', 'tag ' + t.tone, t.text);
          g.setAttribute('data-chrome', t.key);
          box.appendChild(g);
        });
        body.appendChild(box);
      }
      ol.appendChild(li);
    });
    var out = $('x-out');
    out.textContent = '';
    V.out.forEach(function (line, k) {
      var li = el('li');
      li.appendChild(el('span', 'k', String(k + 1)));
      var v = el('span', 'val', line);
      v.setAttribute('data-value', '');
      li.appendChild(v);
      out.appendChild(li);
    });
    var live = $('x-live');
    live.textContent = '';
    V.prose.forEach(function (p) {
      var sp = el('span', null, p.text);
      if (p.key) { sp.setAttribute('data-chrome', p.key); sp.setAttribute('data-claims', p.claims); }
      else sp.setAttribute('data-claim', p.claim);
      live.appendChild(sp);
    });
    var prov = $('x-prov');
    prov.textContent = V.prov.text;
    prov.setAttribute('data-chrome', V.prov.key);
    document.querySelectorAll('#x-n input').forEach(function (i) { i.checked = Number(i.value) === st.n; });
    var t = $('x-brk');
    t.setAttribute('aria-pressed', String(st.brk));
    var oo = $('x-brk-state');
    oo.textContent = st.brk ? U.x_on : U.x_off;
    oo.setAttribute('data-chrome', st.brk ? 'x_on' : 'x_off');
    $('x-reset').disabled = st.n === D.n0 && !st.brk;
  }

  document.querySelectorAll('#x-n input').forEach(function (i) {
    i.addEventListener('change', function () { if (i.checked) { st.n = Number(i.value); render(); } });
  });
  $('x-brk').addEventListener('click', function () { st.brk = !st.brk; render(); });
  $('x-reset').addEventListener('click', function () { st = { n: D.n0, brk: false }; render(); });
  document.documentElement.classList.add('js');
  render();
})();
