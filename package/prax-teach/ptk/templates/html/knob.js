(function () {
  'use strict';
  // The explorer's knob (round 18). Every value shown was written by ptk: the captured runs (values, calls)
  // or ptk/expect_neuron.py (the neuron grid). This script picks which part to show and, for the neuron,
  // places bars and the dot from the numbers in the grid. It computes no value of its own.
  var K = JSON.parse(document.getElementById('ptk-stepper').textContent).knob;
  if (!K) return;
  function $(id) { return document.getElementById(id); }
  function all(s) { return Array.prototype.slice.call(document.querySelectorAll(s)); }
  var NS = 'http://www.w3.org/2000/svg';
  function svgEl(tag, attrs, cls) {
    var e = document.createElementNS(NS, tag);
    Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    if (cls) e.setAttribute('class', cls);
    return e;
  }

  if (K.kind === 'values' || K.kind === 'calls') {
    var cur = K.first, stepAt = {};
    var block = function (v) { return document.querySelector('.kcalls[data-value="' + v + '"]'); };
    var showStep = function (v, i) {
      var b = block(v), n = +b.getAttribute('data-steps');
      i = Math.max(1, Math.min(n, i));
      stepAt[v] = i;
      all('.kcalls[data-value="' + v + '"] .kstep').forEach(function (s) { s.hidden = +s.getAttribute('data-step') !== i; });
      $('k-prev').disabled = i === 1;
      $('k-next').disabled = i === n;
    };
    var show = function (v) {
      cur = v;
      all('#k-vals input').forEach(function (r) { r.checked = r.value === v; });
      if (K.kind === 'values') {
        all('#k-table [data-value]').forEach(function (c) { c.classList.toggle('sel', c.getAttribute('data-value') === v); });
        all('.kprose[data-value]').forEach(function (p) { p.hidden = p.getAttribute('data-value') !== v; });
      } else {
        all('.kcalls').forEach(function (b) { b.hidden = b.getAttribute('data-value') !== v; });
        showStep(v, stepAt[v] || 1);
      }
    };
    all('#k-vals input').forEach(function (r) {
      r.addEventListener('change', function () { if (r.checked) show(r.value); });
    });
    if (K.kind === 'calls') {
      $('k-prev').addEventListener('click', function () { showStep(cur, stepAt[cur] - 1); if ($('k-prev').disabled) $('k-next').focus(); });
      $('k-next').addEventListener('click', function () { showStep(cur, stepAt[cur] + 1); if ($('k-next').disabled) $('k-prev').focus(); });
    }
    show(cur);
    window.__ptkKnob = { pick: show, step: function (i) { showStep(cur, i); } };
    return;
  }

  // ---- neuron: two sliders over the grid
  var G = K.geom, iw = $('k-w2'), ib = $('k-b');
  function X(v) { return G.pad + (v - G.lo) / (G.hi - G.lo) * (G.w - 2 * G.pad); }
  function GX(z) { return G.pad + (z - G.zlo) / (G.zhi - G.zlo) * (G.w - 2 * G.pad); }
  function GY(a) { return G.gy0 - a / G.ahi * (G.gy0 - G.gy1); }
  function axis(svg, x0, x1, y, ticks, map) {
    svg.appendChild(svgEl('line', { x1: x0, y1: y, x2: x1, y2: y }, 'kax'));
    ticks.forEach(function (t) {
      svg.appendChild(svgEl('line', { x1: map(t), y1: y - 4, x2: map(t), y2: y + 4 }, 'kax'));
      var tx = svgEl('text', { x: map(t), y: y + 18, 'text-anchor': 'middle' }, 'ktick');
      tx.textContent = String(t).replace('-', '−');
      svg.appendChild(tx);
    });
  }
  function draw(row) {
    var add = $('k-add'), gate = $('k-gate');
    add.textContent = ''; gate.textContent = '';
    var parts = [[row.t1, row.t1f], [row.t2, row.t2f], [row.b, +row.b]], s = 0;
    parts.forEach(function (p, k) {
      var a = s, b = s + p[1], y = 26 + k * 30, cls = p[1] >= 0 ? 'kbar pos' : 'kbar neg';
      var lab = svgEl('text', { x: Math.min(X(a), X(b)), y: y - 8 }, 'klab ' + (p[1] >= 0 ? 'pos' : 'neg'));
      lab.textContent = K.labels[k] + ' ' + p[0];
      add.appendChild(lab);
      add.appendChild(svgEl('line', { x1: X(a), y1: y, x2: X(b), y2: y }, cls));
      add.appendChild(svgEl('circle', { cx: X(b), cy: y, r: 4.5 }, cls + ' end'));
      if (k) add.appendChild(svgEl('line', { x1: X(a), y1: y - 30, x2: X(a), y2: y }, 'kguide'));
      s = b;
    });
    axis(add, G.pad, G.w - G.pad, 120, G.ticks, X);
    add.appendChild(svgEl('path', { d: 'M' + X(row.zf) + ',110 l-6,-10 h12 z' }, 'kzmark'));  // z marked on the axis, clear of the labels
    gate.appendChild(svgEl('path', { d: 'M' + GX(G.zlo) + ',' + GY(0) + ' L' + GX(0) + ',' + GY(0) + ' L' + GX(G.zhi) + ',' + GY(G.zhi) }, 'krelu'));
    axis(gate, G.pad, G.w - G.pad, GY(0), G.zticks, GX);
    var dot = svgEl('circle', { cx: GX(row.zf), cy: GY(row.af), r: 7, 'data-z': row.z, 'data-a': row.a }, 'kdot');
    dot.id = 'k-dot';
    gate.appendChild(svgEl('path', { d: 'M' + GX(row.zf) + ',' + GY(0) + ' L' + GX(row.zf) + ',' + GY(row.af) }, 'kguide'));
    gate.appendChild(dot);
  }
  function update() {
    var w = K.w2[+iw.value], b = K.b[+ib.value], row = K.rows[w + '|' + b];
    $('k-w2-v').textContent = w; iw.setAttribute('aria-valuetext', w);
    $('k-b-v').textContent = b; ib.setAttribute('aria-valuetext', b);
    $('k-t1').textContent = row.t1; $('k-w2s').textContent = w; $('k-t2').textContent = row.t2;
    $('k-bs').textContent = row.b; $('k-z').textContent = row.z; $('k-a').textContent = row.a;
    $('k-t2').className = row.t2f < 0 ? 'neg' : 'pos';
    $('k-bs').className = +row.b < 0 ? 'neg' : 'pos';
    $('k-a').className = row.af > 0 ? 'pos' : 'zero';
    draw(row);
  }
  iw.addEventListener('input', update);
  ib.addEventListener('input', update);
  update();
  window.__ptkKnob = { set: function (i, j) { iw.value = String(i); ib.value = String(j); update(); } };
})();
