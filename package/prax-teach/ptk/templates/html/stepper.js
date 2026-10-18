(function () {
  'use strict';
  // Step-through explorer: shows one pre-rendered step of the captured run. It computes nothing; every
  // value on a step was written by ptk from the facts and checked against expect.py at build time.
  var D = JSON.parse(document.getElementById('ptk-stepper').textContent);
  var S = D.states, cur = 0;
  function $(id) { return document.getElementById(id); }
  function show(i) {
    cur = Math.max(0, Math.min(S.length - 1, i));
    S.forEach(function (sid, k) {
      var sec = $('step-' + sid);
      sec.classList.toggle('cur', k === cur);
      sec.hidden = k !== cur;
    });
    document.querySelectorAll('#s-steps input').forEach(function (r) { r.checked = r.value === S[cur]; });
    $('s-prev').disabled = cur === 0;
    $('s-next').disabled = cur === S.length - 1;
  }
  document.querySelectorAll('#s-steps input').forEach(function (r) {
    r.addEventListener('change', function () { if (r.checked) show(S.indexOf(r.value)); });
  });
  $('s-prev').addEventListener('click', function () {
    show(cur - 1);
    if ($('s-prev').disabled) $('s-next').focus();
  });
  $('s-next').addEventListener('click', function () {
    show(cur + 1);
    if ($('s-next').disabled) $('s-prev').focus();
  });
  document.documentElement.classList.add('js');
  show(0);
})();
