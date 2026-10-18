r"""Interactive video explorer (IVE): the narrated MP4 plus a WebVTT `metadata` cue track.

Cue-to-state rule (D17.2, D18.2):

    time ─────────────────────────────────────────────────────────────────────────▶
    scene k-1 shown          scene k reveal   scene k shown (= reveal + 0.5 s)
          │ state cue (s_{k-1})      │ [answer cue: still s_{k-1}] │ state cue (s_k) ...
          ▼                          ▼                             ▼
    paused here → explorer at s_{k-1}   paused mid-tween → s_{k-1}    paused here → s_k

    * a cue's state is the last state already settled on screen, never a tween target;
    * a question scene adds a `question` cue (state before the answer);
    * the first reveal after a question adds an `answer` cue at the reveal time; pausing
      0.1 s before it shows no answer anywhere in the DOM, alt text or transcript.

The page reads state only from cue payloads (the VTT is fetched by the browser, it is not in
the DOM), so no future state or answer text sits in the document before its cue.
Without JS the page shows the poster sequence and the full transcript.
"""
import base64
import hashlib
import json
import os
import shutil

from .. import fonts, host, text
from . import path as rail
from ..text import esc


def _view(lesson, sid):
    st = lesson.state(sid)
    s = st["state"]
    facts = lesson.by_id("facts")
    src = lesson.program_source(s["program"]).split("\n")
    first, last = rail.body_range(src)
    return {"state_id": sid, "label": st["label"], "program": s["program"],
            "program_path": lesson.program(s["program"])["path"], "line": s["line"], "path": s.get("path", []),
            "code": [[n, src[n - 1]] for n in range(first, last + 1)],
            "output": [{"fact": f, "text": text.display(facts[f])} for f in s["output"]], "vars": s.get("vars", {})}


def cues(lesson, timing):
    """Metadata cues from the screen plan (video.plan_screen): the explorer and the frame read the
    same before/reveal/shown fields, so they cannot disagree about what is on screen."""
    out = []
    answer_pending = None
    for sc in timing["scenes"]:
        start = sc["start"]
        if sc["before"] != sc["state"]:
            kind = "answer" if answer_pending else "transition"
            if sc["reveal"] > sc["start"]:
                out.append({"kind": "state", "scene": sc["id"], "start": sc["start"], "end": sc["reveal"],
                            "state": _view(lesson, sc["before"])})
            out.append({"kind": kind, "scene": sc["id"], "start": sc["reveal"], "end": sc["shown"],
                        "state": _view(lesson, sc["before"]),
                        **({"answer_for": answer_pending} if answer_pending else {})})
            answer_pending = None
            start = sc["shown"]
        q = sc.get("question")
        cue = {"kind": "question" if q else "state", "scene": sc["id"], "start": start, "end": sc["end"],
               "state": _view(lesson, sc["state"])}
        if q:
            cue["question"] = {"prompt": q["prompt"], "scene": sc["id"]}
            answer_pending = sc["id"]
        out.append(cue)
    out.sort(key=lambda c: c["start"])
    merged = []
    for c in out:
        # a plain state cue that continues the previous cue's state (and adds no question) is the same cue
        if merged and c["kind"] == "state" and merged[-1]["kind"] in ("state", "question") \
                and merged[-1]["state"]["state_id"] == c["state"]["state_id"]:
            continue
        merged.append(c)
    for i, c in enumerate(merged):
        c["end"] = merged[i + 1]["start"] if i + 1 < len(merged) else timing["duration"]
        c["cue"] = f"m{i + 1}"
    return [c for c in merged if c["end"] - c["start"] > 0.001]


def write_metadata_vtt(path, cue_list):
    lines = ["WEBVTT", "", "NOTE ptk IVE state cues: payload = last state already shown (D18.2)", ""]
    for c in cue_list:
        payload = {k: v for k, v in c.items() if k not in ("start", "end")}
        lines += [c["cue"], f"{text.vtt_time(c['start'])} --> {text.vtt_time(c['end'])}",
                  json.dumps(payload, ensure_ascii=False, separators=(",", ":")), ""]
    path.write_text("\n".join(lines))


CSS = """
:root{--paper:%(lp)s;--card:%(lc)s;--ink:%(li)s;--soft:%(ls)s;--muted:%(lm)s;--rule:%(lr)s;--faint:%(lf)s;--blue:%(lb)s;--tint:%(lt)s;--hl:%(lh)s}
@media (prefers-color-scheme: dark){:root{--paper:%(dp)s;--card:%(dc)s;--ink:%(di)s;--soft:%(ds)s;--muted:%(dm)s;--rule:%(dr)s;--faint:%(df)s;--blue:%(db)s;--tint:%(dt)s;--hl:%(dh)s}}
*{box-sizing:border-box}
html{color-scheme:light dark}
body{margin:0;background:var(--paper);color:var(--ink);font:400 18px/1.55 'Source Serif 4',Georgia,serif;font-variant-numeric:lining-nums tabular-nums}
.wrap{max-width:1360px;margin:0 auto;padding:28px 16px 64px}
.kicker{margin:0;font:600 13px/1.4 'JetBrains Mono',monospace;letter-spacing:.14em;color:var(--blue);text-transform:uppercase}
h1{margin:6px 0 20px;font:600 clamp(28px,4vw,44px)/1.15 'Source Serif 4',serif;letter-spacing:-.01em}
.grid{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(0,1fr);gap:24px;align-items:start}
@media (max-width: 900px){.grid{grid-template-columns:minmax(0,1fr)}}
video{display:block;width:100%%;height:auto;background:#000;border-radius:12px}
.bar{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 0}
button{font:500 14px/1.2 'JetBrains Mono',monospace;color:var(--ink);background:var(--card);border:1px solid var(--rule);border-radius:8px;padding:10px 12px;min-height:44px;cursor:pointer}
button:focus-visible{outline:3px solid var(--blue);outline-offset:2px}
button[aria-pressed="true"]{background:var(--tint);border-color:var(--blue)}
button:disabled{color:var(--muted);cursor:default}
.panel{background:var(--card);border:1px solid var(--rule);border-radius:14px;padding:18px}
.plabel{margin:0 0 4px;font:600 12px/1.4 'JetBrains Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
.slabel{margin:0 0 12px;font:600 22px/1.3 'Caveat',cursive;color:var(--blue)}
.hint{margin:0 0 10px;font-size:15px;color:var(--soft)}
.code{margin:0 0 14px;padding:10px 0;border:1px solid var(--rule);border-radius:10px;overflow-x:auto;font:500 14px/1.7 'JetBrains Mono',monospace}
.ln{display:flex;white-space:pre;padding:0 10px 0 0;color:var(--muted)}
.ln .no{flex:0 0 44px;text-align:right;padding-right:12px;color:var(--faint)}
.ln.exec{color:var(--ink)}.ln.exec .no{color:var(--blue);font-weight:700}
.ln.cur{background:var(--hl);color:var(--ink);box-shadow:inset 4px 0 0 var(--blue)}
.out{margin:0 0 10px;padding:0;list-style:none;font:600 20px/1.5 'JetBrains Mono',monospace}
.out li{display:flex;gap:14px}.out .k{color:var(--faint);font-weight:500;font-size:14px;align-self:center;min-width:16px}
.out .empty{color:var(--muted);font:italic 400 16px/1.5 'Source Serif 4',serif}
.vars{margin:0;font:500 15px/1.4 'JetBrains Mono',monospace;color:var(--soft)}
.q{margin:14px 0 0;padding:14px 16px;background:var(--tint);border:2px solid var(--blue);border-radius:12px}
.q p{margin:0}.q .qt{font:500 19px/1.4 'Source Serif 4',serif}
.steps{display:flex;gap:8px;margin:12px 0 0}
section.side{display:grid;gap:18px}
h2{margin:0 0 8px;font:600 13px/1.4 'JetBrains Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
ol.chapters,ol.tx{margin:0;padding:0;list-style:none}
ol.chapters li,ol.tx li{margin:0 0 6px}
ol.chapters button,ol.tx button{width:100%%;text-align:left;font:400 16px/1.4 'Source Serif 4',serif}
ol.tx button[aria-current="true"]{background:var(--tint);border-color:var(--blue)}
.time{font:500 12px/1 'JetBrains Mono',monospace;color:var(--muted);margin-right:8px}
.prov{margin:28px 0 0;font:400 13px/1.5 'JetBrains Mono',monospace;color:var(--muted);overflow-wrap:anywhere}
.posters{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}
.posters img{width:100%%;height:auto;border-radius:8px;border:1px solid var(--rule)}
@media (prefers-reduced-motion: reduce){*{transition:none!important}}
"""

JS = r"""
(function () {
  var v = document.getElementById('v');
  var $ = function (id) { return document.getElementById(id); };
  var S = JSON.parse($('ptk-ui').textContent);
  var nav = window.__ptkNav = [];
  function log(kind, extra) { nav.push(Object.assign({ kind: 'navigation', action: kind, t: +v.currentTime.toFixed(3) }, extra || {})); }
  function track(kind) { for (var i = 0; i < v.textTracks.length; i++) if (v.textTracks[i].kind === kind) return v.textTracks[i]; return null; }
  var meta = track('metadata'), caps = track('captions'), chaps = track('chapters');
  meta.mode = 'hidden'; chaps.mode = 'hidden'; caps.mode = 'showing';
  var cues = [], shownIdx = -1, viewIdx = -1;
  function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
  function load() {
    if (!meta.cues || !meta.cues.length) return false;
    cues = [];
    for (var i = 0; i < meta.cues.length; i++) { var c = meta.cues[i]; cues.push({ start: c.startTime, end: c.endTime, p: JSON.parse(c.text) }); }
    return true;
  }
  function idxAt(t) { var k = -1; for (var i = 0; i < cues.length; i++) if (cues[i].start <= t + 1e-3) k = i; return k; }
  function render(i) {
    var box = $('state'); box.textContent = '';
    if (i < 0) return;
    var p = cues[i].p, st = p.state;
    box.dataset.state = st.state_id; box.dataset.cue = p.cue; box.dataset.kind = p.kind;
    box.appendChild(el('p', 'slabel', st.label)).setAttribute('data-trace', st.state_id);
    var code = el('div', 'code'); code.setAttribute('data-code', st.program); code.setAttribute('role', 'group'); code.setAttribute('data-key', 'code');
    code.setAttribute('aria-label', S.code_label + ': ' + st.program_path);
    st.code.forEach(function (row) {
      var ln = el('div', 'ln' + (st.path.indexOf(row[0]) >= 0 ? ' exec' : '') + (row[0] === st.line ? ' cur' : ''));
      ln.appendChild(el('span', 'no', String(row[0]))); ln.appendChild(el('span', 'src', row[1])); code.appendChild(ln);
    });
    box.appendChild(el('p', 'plabel', S.code_label)); box.appendChild(code);
    box.appendChild(el('p', 'plabel', S.output_label));
    var out = el('ol', 'out'); out.setAttribute('data-role', 'output'); out.setAttribute('data-key', 'output');
    if (!st.output.length) out.appendChild(el('li', 'empty', '—'));
    st.output.forEach(function (o, k) { var li = el('li'); li.appendChild(el('span', 'k', String(k + 1))); var s = el('span', 'val', o.text); s.setAttribute('data-fact', o.fact); li.appendChild(s); out.appendChild(li); });
    box.appendChild(out);
    var vars = Object.keys(st.vars).map(function (k) { return k + ' = ' + st.vars[k]; }).join('   ');
    var vp = el('p', 'vars', S.vars_label + ': ' + vars); vp.setAttribute('data-code', st.program); box.appendChild(vp);
    if (p.question) { var q = el('div', 'q'); q.setAttribute('data-key', 'question'); q.appendChild(el('p', 'plabel', S.question_label)); var qt = el('p', 'qt', p.question.prompt); qt.setAttribute('data-question', p.question.scene); q.appendChild(qt); box.appendChild(q); }
    $('prev').disabled = i <= 0; $('next').disabled = i >= shownIdx;
  }
  function sync(reason) {
    if (!cues.length && !load()) return;
    shownIdx = idxAt(v.currentTime); viewIdx = shownIdx; render(viewIdx); transcript();
    if (reason) log(reason);
  }
  $('prev').addEventListener('click', function () { if (viewIdx > 0) { viewIdx--; render(viewIdx); log('step-back', { state: cues[viewIdx].p.state.state_id }); } });
  $('next').addEventListener('click', function () { if (viewIdx < shownIdx) { viewIdx++; render(viewIdx); log('step-forward', { state: cues[viewIdx].p.state.state_id }); } });
  var capBtn = $('caps');
  capBtn.addEventListener('click', function () { var on = caps.mode !== 'showing'; caps.mode = on ? 'showing' : 'hidden'; capBtn.setAttribute('aria-pressed', String(on)); capBtn.textContent = on ? S.captions_on : S.captions_off; log('captions', { on: on }); });
  function chapters() {
    var list = $('chapters'); if (list.childNodes.length || !chaps.cues || !chaps.cues.length) return;
    for (var i = 0; i < chaps.cues.length; i++) (function (c) {
      var li = el('li'); var b = el('button'); b.appendChild(el('span', 'time', fmt(c.startTime))); b.appendChild(document.createTextNode(c.text));
      b.addEventListener('click', function () { v.pause(); v.currentTime = c.startTime; log('chapter', { chapter: c.id }); }); li.appendChild(b); list.appendChild(li);
    })(chaps.cues[i]);
  }
  function fmt(t) { var m = Math.floor(t / 60), s = Math.floor(t % 60); return m + ':' + (s < 10 ? '0' : '') + s; }
  var txBuilt = 0;
  function transcript() {
    // Only cues already reached are in the DOM: the transcript never runs ahead of the video.
    if (!caps.cues) return;
    var list = $('tx'), t = v.currentTime, n = 0;
    for (var i = 0; i < caps.cues.length; i++) if (caps.cues[i].startTime <= t + 1e-3) n = i + 1;
    while (list.childNodes.length > n) list.removeChild(list.lastChild);
    for (var j = list.childNodes.length; j < n; j++) (function (c) {
      var li = el('li'); var b = el('button'); b.appendChild(el('span', 'time', fmt(c.startTime))); b.appendChild(document.createTextNode(c.text));
      b.addEventListener('click', function () { v.currentTime = c.startTime; log('transcript-seek', { cue: c.id }); }); li.appendChild(b); list.appendChild(li);
    })(caps.cues[j]);
    for (var k = 0; k < list.childNodes.length; k++) { var c = caps.cues[k]; list.childNodes[k].firstChild.setAttribute('aria-current', String(c.startTime <= t && t < c.endTime)); }
  }
  ['pause', 'seeked'].forEach(function (ev) { v.addEventListener(ev, function () { sync(ev); }); });
  v.addEventListener('timeupdate', function () { var i = idxAt(v.currentTime); if (i !== shownIdx) sync(); else transcript(); });
  v.addEventListener('play', function () { log('play'); });
  [meta, chaps, caps].forEach(function (t) { t.addEventListener('cuechange', function () { chapters(); }); });
  document.querySelectorAll('track').forEach(function (t) { t.addEventListener('load', function () { chapters(); sync(); }); });
  v.addEventListener('loadedmetadata', function () { chapters(); sync(); });
  document.documentElement.classList.add('js');
  window.__ptkReady = function () { return cues.length > 0 && !!(chaps.cues && chaps.cues.length) && $('chapters').childNodes.length > 0; };
})();
"""


def _csp_hash(s):
    return "'sha256-" + base64.b64encode(hashlib.sha256(s.encode()).digest()).decode() + "'"


def page(lesson, timing, cue_list, posters):
    tk = fonts.tokens()["themes"]
    m = {}
    for p, th in (("l", "light"), ("d", "dark")):
        for k, key in (("p", "paper"), ("c", "card"), ("i", "ink"), ("s", "soft"), ("m", "muted"), ("r", "rule"),
                       ("f", "faint"), ("b", "blue"), ("t", "blue_tint"), ("h", "hl")):
            m[p + k] = tk[th][key]
    ui = {k: text.ui(k) for k in ("code_label", "output_label", "vars_label", "question_label", "captions_on",
                                  "captions_off")}
    used = " ".join([json.dumps(ui), lesson.data["title"], text.ui("kicker", topic=lesson.data["topic"]),
                     *[c["text"] for c in timing["cues"]], *[s["title"] for s in timing["scenes"]],
                     *[json.dumps(c, ensure_ascii=False) for c in cue_list], *text.chrome()["strings"].values(),
                     "0123456789:—"])
    css = fonts.face_css({"serif": used, "serif_italic": used, "mono": used, "hand": used}) + CSS % m
    ui_json = json.dumps(ui, ensure_ascii=False)
    facts = lesson.by_id("facts")
    src = lesson.program(lesson.data["figure"]["program"]) if lesson.data.get("figure") else lesson.data["programs"][0]
    f0 = next(f for f in lesson.data["facts"] if f["program"] == src["id"] and f["select"]["stream"] == "stdout")
    prov = text.provenance(lesson)
    tx_full = "".join(f'<li data-narration="{esc(c["id"])}"><span class="time" data-label="time">'
                      f'{esc(text.vtt_time(c["start"])[3:8])}</span>{esc(c["text"])}</li>' for c in timing["cues"])
    poster_html = "".join(f'<figure><img src="{esc(p["file"])}" alt="{esc(p["alt"])}" width="960" height="540">'
                          f'<figcaption data-label="scene-title">{esc(p["title"])}</figcaption></figure>' for p in posters)
    csp = (f"default-src 'none'; script-src {_csp_hash(JS)}; style-src {_csp_hash(css)}; img-src 'self' data:; "
           f"media-src 'self'; font-src data:; connect-src 'none'; base-uri 'none'; form-action 'none'")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{csp}">
<title>{esc(lesson.data['title'])}</title>
<style>{css}</style>
</head><body><div class="wrap">
<p class="kicker" data-chrome="kicker">{esc(text.ui('kicker', topic=lesson.data['topic']))}</p>
<h1 data-label="title">{esc(lesson.data['title'])}</h1>
<noscript><p data-chrome="noscript">{esc(text.ui('noscript'))}</p><div class="posters">{poster_html}</div>
<h2 data-chrome="transcript">{esc(text.ui('transcript'))}</h2><ol class="tx">{tx_full}</ol></noscript>
<div class="grid">
<section>
<video id="v" controls preload="metadata" playsinline poster="{esc(posters[0]['file'])}" aria-label="{esc(lesson.data['title'])}">
<source src="lesson.mp4" type="video/mp4">
<track kind="captions" srclang="en" label="English" src="captions.vtt" default>
<track kind="chapters" srclang="en" label="{esc(text.ui('chapters'))}" src="chapters.vtt">
<track kind="metadata" srclang="en" label="states" src="states.vtt">
</video>
<div class="bar"><button id="caps" type="button" aria-pressed="true" data-chrome="captions_on">{esc(text.ui('captions_on'))}</button></div>
<section class="panel" aria-live="polite" style-none>
<p class="plabel" data-chrome="state_label">{esc(text.ui('state_label'))}</p>
<p class="hint" data-chrome="explore_hint">{esc(text.ui('explore_hint'))}</p>
<div id="state"></div>
<div class="steps"><button id="prev" type="button" data-chrome="prev_state">{esc(text.ui('prev_state'))}</button>
<button id="next" type="button" data-chrome="next_state">{esc(text.ui('next_state'))}</button></div>
</section>
</section>
<section class="side">
<div><h2 data-chrome="chapters">{esc(text.ui('chapters'))}</h2><ol id="chapters" class="chapters"></ol></div>
<div><h2 data-chrome="transcript">{esc(text.ui('transcript'))}</h2><ol id="tx" class="tx"></ol></div>
</section>
</div>
<p class="prov" data-chrome="provenance">{esc(prov)}</p>
<p class="prov" data-role="source" data-chrome="source_link">{esc(text.ui('source_link', path=f"lessons/{lesson.id}/{src['path']}"))}</p>
</div>
<script type="application/json" id="ptk-ui">{ui_json}</script>
<script>{JS}</script>
</body></html>
""".replace(" style-none", "")


def project(lesson, out, video_dir, timing):
    out.mkdir(parents=True, exist_ok=True)
    mp4 = out / "lesson.mp4"
    if mp4.exists():
        mp4.unlink()
    os.link(video_dir / "lesson.mp4", mp4)
    for f in ("captions.vtt", "chapters.vtt"):
        shutil.copyfile(video_dir / f, out / f)
    cue_list = cues(lesson, timing)
    write_metadata_vtt(out / "states.vtt", cue_list)
    pdir = out / "posters"
    pdir.mkdir(exist_ok=True)
    ffmpeg = host.which("ffmpeg")
    posters = []
    for sc in timing["scenes"]:
        t = min(max(sc["shown"], sc["start"] + 1.0) + 0.3, sc["end"] - 0.1)
        f = pdir / f"{sc['id']}.jpg"
        host.run([ffmpeg, "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", mp4, "-frames:v", "1", "-vf", "scale=960:-2",
                  "-q:v", "3", f], check=True, timeout=120)
        posters.append({"file": f"posters/{f.name}", "title": sc["title"],
                        "alt": f"{sc['title']} ({text.vtt_time(t)[3:8]})"})
    (out / "index.html").write_text(page(lesson, timing, cue_list, posters))
    (out / "cues.json").write_text(json.dumps(cue_list, indent=1, ensure_ascii=False))
    return {"page": out / "index.html", "cues": cue_list, "posters": posters}
