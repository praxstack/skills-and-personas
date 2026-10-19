(function () {
  'use strict';
  // Every word on the page is already in the document (from the lesson model and chrome.json);
  // this script only decides which parts are open. Explanation first: layer 2 opens with no answer,
  // and layer k+1 opens only after layer k. The check after the last layer is optional. A title that
  // states the answer shows when its layer opens, or once an answer is checked.
  function $(id) { return document.getElementById(id); }
  var layers = [].slice.call(document.querySelectorAll('[data-layer]'));
  var check = $('qa-check');
  var answered = false;
  function chosen() { return document.querySelector('#qa-options input:checked'); }
  function sync() {
    layers.forEach(function (l, i) {
      var b = l.querySelector('button.reveal');
      if (!b) return;
      var prevOpen = i === 0 ? true : layers[i - 1].getAttribute('data-open') === 'true';
      var ready = prevOpen;
      b.disabled = !ready;
      b.setAttribute('aria-expanded', l.getAttribute('data-open'));
    });
    check.disabled = !chosen();
  }
  document.querySelectorAll('#qa-options input').forEach(function (i) { i.addEventListener('change', sync); });
  check.addEventListener('click', function () {
    var c = chosen();
    if (!c) return;
    answered = true;
    document.querySelectorAll('[data-sealed]').forEach(function (h) { h.setAttribute('data-sealed', 'false'); });
    var key = $('qa-feedback');
    key.querySelectorAll('li[data-opt]').forEach(function (li) {
      li.setAttribute('data-shown', String(li.getAttribute('data-opt') === c.value));
    });
    key.setAttribute('data-kind', c.getAttribute('data-correct') === 'true' ? 'correct' : 'wrong');
    sync();
  });
  layers.forEach(function (l, i) {
    var b = l.querySelector('button.reveal');
    if (!b) return;
    b.addEventListener('click', function () {
      if (b.disabled) return;
      l.setAttribute('data-open', 'true');
      l.querySelectorAll('[data-sealed]').forEach(function (h) { h.setAttribute('data-sealed', 'false'); });
      sync();
      var next = layers[i + 1] && layers[i + 1].querySelector('button.reveal');
      if (next) next.focus(); else l.querySelector('.layer-body').focus();
    });
  });
  document.documentElement.classList.add('js');
  layers.forEach(function (l, i) { if (i > 0) l.setAttribute('data-open', 'false'); });
  sync();
})();
