"""AC-10.4 (SPEC v1.4 WP10): every explorer and IVE sentence that describes state matches the state on screen
after every control step, and a tiny nonzero z such as 1.11022e-16 is explained as binary64 rounding.

How it measures (in the page, in Playwright):
  controls    every visible range slider (each value), radio group (each option), aria-pressed toggle and
              checkbox (both states) in the scope. Controls in one region are combined: when their combinations
              number 1500 or fewer, every combination is visited (the neuron's 41 x 21 grid is); otherwise each
              control is swept alone. Then every other
              button (Next, Previous, ...) is pressed until it is disabled, at most 12 times; with 12 or fewer
              combinations, at every combination. The explorer page is the scope; in the IVE, the explore panel
              (#xp) after "Pause and explore" near the end of the film.
  drawn state read after each step from what is drawn, never from a data flag: "name = value" pairs in visible
              text that is not prose, a slider's visible readout named by its label, a checked radio's visible
              label named by its fieldset legend ("Value of a"), and any element marked data-state-var="<name>"
              (its text).
  sentences   visible prose (p, li, figcaption, caption, dd, [data-claim], [data-claims], [data-describes],
              [aria-live]; 3+ words), split into sentences. A sentence asserts "name = value" and, for a name
              the region draws, "name prints as value". Each assertion must
              match the drawn value of its own region (the closest [data-role="explore"], .knob, .step, #xp or
              main). An "=" assertion about a name the region does not draw fails as unbound. Sentences that say
              "captured" describe the captured run, not live state, and are skipped.
  rounding    when any drawn value is nonzero with magnitude below 1e-9, a visible sentence in that region
              must mention binary64 or double and rounding. On the neuron lesson that state must be reached.
"""
import json

import _b0

WALK_JS = r"""async (opts) => {
  opts = opts || {};
  const scope = opts.scope ? document.querySelector(opts.scope) : document.body;
  if (!scope) return { error: 'no scope ' + opts.scope };
  const vis = (el) => { if (!el || el.closest('noscript')) return false; if (!el.getClientRects().length) return false;
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) { const s = getComputedStyle(e);
      if (s.display === 'none' || s.visibility === 'hidden' || parseFloat(s.opacity) === 0) return false; } return true; };
  const tick = () => new Promise((r) => requestAnimationFrame(() => setTimeout(r, opts.settle || 0)));
  const REGION = '[data-role="explore"], .knob, .step, #xp, main, body';
  const PROSE = 'p, li, figcaption, caption, dd, [data-claim], [data-claims], [data-describes], [aria-live]';
  const NOT_PROSE = '[data-code], code, pre, svg, .out, [data-role="output"], button, label, legend, select, option, noscript, table, [data-state-var]';
  const NUM = String.raw`[-+−]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?`;
  const ID = String.raw`[A-Za-z_]\w*(?:\(-?\d+\))?`;
  const pairRe = () => new RegExp(String.raw`(?<![\w.])(${ID})\s*=\s*(${NUM})(?!\w|\.\d)`, 'g');
  const sayRe = () => new RegExp(String.raw`(?<![\w.])(${ID})\s+prints as\s+(${NUM})(?!\w|\.\d)`, 'g');
  const key = (v) => String(parseFloat(String(v).replace('−', '-')));
  const words = (t) => (t.match(/[A-Za-z]{2,}/g) || []).length;
  const sentences = (t) => t.replace(/\s+/g, ' ').trim().split(/(?<=[.!?])\s+(?=[A-Z0-9"'(])/);
  const proseBlocks = () => {
    const c = [...scope.querySelectorAll(PROSE)].filter((el) => vis(el) && !el.closest(NOT_PROSE) && words(el.textContent) >= 3);
    return c.filter((el) => !c.some((o) => o !== el && o.contains(el)));
  };
  const radioName = (r) => {
    const fs = r.closest('fieldset'), lg = fs && fs.querySelector('legend');
    const m = lg && lg.textContent.trim().match(/([A-Za-z_]\w*)$/);
    return (fs && fs.dataset.stateVar) || r.dataset.stateVar || (m && m[1].length <= 3 ? m[1] : r.name.replace(/^.*-/, ''));
  };
  const drawn = (region, prose) => {
    const st = {}, code = {};
    const add = (n, v, into) => { if (!/^[A-Za-z_]\w*(\(-?\d+\))?$/.test(n)) return; const t = into || st; (t[n] = t[n] || new Set()).add(key(v)); };
    for (const el of region.querySelectorAll('[data-state-var]')) if (vis(el)) add(el.dataset.stateVar, el.textContent.trim());
    for (const r of region.querySelectorAll('input[type=range]')) {
      if (!vis(r)) continue;
      const lab = r.closest('label') || r.parentElement, out = lab.querySelector('output');
      const nm = lab.querySelector('.lbl, [data-chrome]');
      const name = ((nm && nm.textContent) || r.getAttribute('aria-label') || '').trim();
      add(name, out ? out.textContent.trim() : (r.getAttribute('aria-valuetext') || r.value));
    }
    for (const r of region.querySelectorAll('input[type=radio]:checked')) {
      const lab = r.closest('label');
      if (!vis(lab || r)) continue;
      const v = (lab ? lab.textContent : r.value).trim();
      if (/^-?\d+(\.\d+)?$/.test(v)) add(radioName(r), v);
    }
    for (const el of region.querySelectorAll('p, li, td, dd, output, b, span, text, div, h3, h4, figcaption, code, th')) {
      if (!vis(el) || el.closest('noscript')) continue;
      if (prose.some((p) => p.contains(el) || el.contains(p))) continue;
      const inCode = !!el.closest('[data-code], code, pre');
      for (const m of el.textContent.replace(/\s+/g, ' ').matchAll(pairRe())) add(m[1], m[2], inCode ? code : st);
    }
    // a name drawn only in a code listing (the source's initialiser) is compared with the code
    for (const [n, vs] of Object.entries(code)) if (!st[n]) st[n] = vs;
    return st;
  };
  const res = { steps: 0, assertions: 0, problems: [], problem_count: 0, tiny: { reached: 0, explained: 0, examples: [] }, controls: [] };
  const report = (p) => { res.problem_count++; if (res.problems.length < 40) res.problems.push(p); };
  const check = async (label) => {
    await tick();
    res.steps++;
    const prose = proseBlocks();
    const regions = new Map();
    const region = (el) => { const r = el.closest(REGION) || scope; if (!regions.has(r)) regions.set(r, drawn(r, prose)); return [r, regions.get(r)]; };
    for (const blk of prose) {
      const [, st] = region(blk);
      for (const s of sentences(blk.textContent)) {
        if (/captured/i.test(s)) continue;
        const seen = new Set();
        for (const [re, needBound] of [[pairRe(), false], [sayRe(), true]]) {
          for (const m of s.matchAll(re)) {
            const name = m[1], val = m[2], id = name + '=' + key(val);
            if (seen.has(id)) continue; seen.add(id);
            if (!st[name]) { if (!needBound) { res.assertions++; report({ kind: 'unbound', step: label, name, said: val, sentence: s.slice(0, 160) }); } continue; }
            res.assertions++;
            if (!st[name].has(key(val))) report({ kind: 'mismatch', step: label, name, said: val, drawn: [...st[name]], sentence: s.slice(0, 160) });
          }
        }
      }
    }
    // the rounding note is looked for in each innermost region (a region holding no other visible region)
    const cands = [scope, ...scope.querySelectorAll(REGION)].filter((r) => r === scope || vis(r));
    const leaves = cands.filter((r) => !cands.some((o) => o !== r && r.contains(o)));
    for (const r of leaves) {
      const st = region(r)[1];
      const tiny = Object.entries(st).filter(([, vs]) => [...vs].some((v) => { const x = parseFloat(v); return x !== 0 && Math.abs(x) < 1e-9; }));
      if (!tiny.length) continue;
      res.tiny.reached++;
      const text = prose.filter((b) => (b.closest(REGION) || scope) === r).map((b) => b.textContent).join(' ');
      const ok = /binary64|double/i.test(text) && /round/i.test(text);
      if (ok) res.tiny.explained++;
      if (res.tiny.examples.length < 3) res.tiny.examples.push({ step: label, values: tiny.map(([n, vs]) => n + '=' + [...vs].join('|')), explained: ok });
      if (!ok) report({ kind: 'tiny-unexplained', step: label, values: tiny.map(([n, vs]) => n + '=' + [...vs].join('|')) });
    }
  };
  const name = (c) => c.id || c.name || (c.textContent || '').trim().slice(0, 30) || c.type;
  const usable = (c) => !c.closest('noscript') && !c.disabled && (vis(c) || ((c.type === 'radio' || c.type === 'checkbox') && vis(c.closest('label') || c.parentElement)));
  const all = [...scope.querySelectorAll('input, button, select')].filter(usable);
  const dims = [];
  const regionOf = (c) => c.closest(REGION) || scope;
  for (const r of all.filter((c) => c.type === 'range')) {
    const lo = parseFloat(r.min || 0), hi = parseFloat(r.max || 100), st = parseFloat(r.step || 1) || 1;
    const vals = []; for (let i = 0; i <= Math.round((hi - lo) / st) && i < 400; i++) vals.push(+(lo + i * st).toFixed(10));
    dims.push({ region: regionOf(r), name: name(r), values: vals, set: (v) => { if (String(+r.value) === String(v)) return; r.value = String(v);
      r.dispatchEvent(new Event('input', { bubbles: true })); r.dispatchEvent(new Event('change', { bubbles: true })); } });
  }
  const groups = {};
  for (const r of all.filter((c) => c.type === 'radio')) (groups[r.name] = groups[r.name] || []).push(r);
  for (const [g, rs] of Object.entries(groups)) dims.push({ region: regionOf(rs[0]), name: g, values: rs.map((r) => r.value), set: (v) => { const r = rs.find((x) => x.value === v); if (r && !r.checked && !r.disabled) r.click(); } });
  for (const b of all.filter((c) => c.tagName === 'BUTTON' && c.hasAttribute('aria-pressed')))
    dims.push({ region: regionOf(b), name: name(b), values: ['false', 'true'], set: (v) => { if (b.getAttribute('aria-pressed') !== v && !b.disabled) b.click(); } });
  for (const c of all.filter((c) => c.type === 'checkbox'))
    dims.push({ region: regionOf(c), name: name(c), values: [false, true], set: (v) => { if (c.checked !== v) c.click(); } });
  const buttons = all.filter((c) => c.tagName === 'BUTTON' && !c.hasAttribute('aria-pressed'));
  res.controls = dims.map((d) => d.name + ' x' + d.values.length).concat(buttons.map((b) => 'button ' + name(b)));
  const walkButtons = async (tag) => {
    for (const b of buttons) { let n = 0; while (n < 12 && vis(b) && !b.disabled) { b.click(); n++; await check(tag + ' ' + name(b) + ' #' + n); } }
  };
  await check('initial');
  // controls in one region are combined; regions are independent of each other
  const byRegion = new Map();
  for (const d of dims) { if (!byRegion.has(d.region)) byRegion.set(d.region, []); byRegion.get(d.region).push(d); }
  res.combinations = 0;
  let small = true;
  for (const ds of byRegion.values()) {
    const product = ds.reduce((a, d) => a * d.values.length, 1);
    res.combinations += product;
    small = small && product <= 12;
    if (product <= (opts.maxProduct || 1500)) {
      for (let k = 0; k < product; k++) {
        let rest = k; const label = [];
        for (const d of ds) { const v = d.values[rest % d.values.length]; rest = Math.floor(rest / d.values.length); d.set(v); label.push(d.name + '=' + v); }
        await check(label.join(' '));
        if (product <= 12) await walkButtons(label.join(' '));
      }
    } else {
      for (const d of ds) { for (const v of d.values) { d.set(v); await check(d.name + '=' + v); } d.set(d.values[0]); }
    }
  }
  if (!dims.length || !small) await walkButtons('');
  return res;
}"""


def walk_job(jid, url, scope=None, pre=None, width=1440, height=900):
    steps = list(pre or []) + [{"eval": f"({WALK_JS})({json.dumps({'scope': scope})})", "as": "walk"}]
    return {"id": jid, "type": "script", "url": url, "width": width, "height": height, "steps": steps}


def ive_pre():
    drive = {"eval": _b0.visual.IVE_DRIVE.read_text(), "as": "drive"}
    ready = {"waitFor": "window.__ptkReady && window.__ptkReady()", "timeout": 30000}
    enter = {"eval": "(async () => { const D = window.__iveDrive; const v = D.v(); await D.seek(Math.max(0, v.duration - 0.4)); "
                     "document.getElementById('explore').click(); await D.sleep(150); return window.__ptkIve.mode(); })()",
             "as": "mode"}
    return [ready, drive, enter]


def run_walks(jobs, name, lesson_sha=None):
    res = _b0.shoot(jobs, name, lesson_sha, timeout=1800)
    out = {}
    for r in res["results"]:
        vals = r.get("values") or {}
        w = vals.get("walk")
        if not r.get("ok") or not w or w.get("error"):
            out[r["id"]] = {"error": (r.get("error") or (w or {}).get("error") or "no result")[:500]}
        else:
            out[r["id"]] = {**w, "mode": vals.get("mode")}
    return out


def problems_of(walks, need_tiny=False):
    probs = []
    for jid, w in walks.items():
        if w.get("error"):
            probs.append({"kind": "walk-failed", "page": jid, "error": w["error"]})
            continue
        if "mode" in w and w["mode"] not in (None, "explore"):
            probs.append({"kind": "ive-not-in-explore", "page": jid, "mode": w["mode"]})
        probs += [{**p, "page": jid} for p in w["problems"]]
        if w["problem_count"] > len(w["problems"]):
            probs.append({"kind": "more-problems", "page": jid, "count": w["problem_count"] - len(w["problems"])})
    if need_tiny and not any(w.get("tiny", {}).get("reached") for w in walks.values() if not w.get("error")):
        probs.append({"kind": "tiny-case-not-reached"})
    return probs


def _summary(walks):
    return {jid: ({"error": w["error"]} if w.get("error") else
                  {"controls": w["controls"], "combinations": w.get("combinations"), "steps": w["steps"],
                   "assertions": w["assertions"], "problems": w["problem_count"], "tiny": w["tiny"]})
            for jid, w in walks.items()}


# ---------------------------------------------------------------- fixtures

def test_fixture_live_sentence_passes():
    """Two sliders with a sentence rebuilt from the drawn state and a binary64 note at 1.11022e-16: every one of
    the 861 combinations passes, and the tiny case is reached and explained."""
    walks = run_walks([walk_job("pass", (_b0.FIXTURES / "explorer-pass.html").resolve().as_uri())], "live-pass")
    probs = problems_of(walks, need_tiny=True)
    assert not probs, probs[:5]
    w = walks["pass"]
    assert w["steps"] >= 861 and w["tiny"]["reached"] >= 1 and w["tiny"]["explained"] == w["tiny"]["reached"], w
    return _summary(walks)


def test_fixture_fixed_sentence_fails():
    """The same sliders under a fixed sentence (the rc1 neuron pattern) fail at load and at the tiny case."""
    walks = run_walks([walk_job("fail", (_b0.FIXTURES / "explorer-fail.html").resolve().as_uri())], "live-fail")
    probs = problems_of(walks, need_tiny=True)
    kinds = {p["kind"] for p in probs}
    assert {"mismatch", "tiny-unexplained"} <= kinds, (sorted(kinds), probs[:5])
    assert any(p.get("step") == "initial" for p in probs if p["kind"] == "mismatch"), probs[:5]
    return {"kinds": sorted(kinds), **_summary(walks)}


# ---------------------------------------------------------------- the built lessons

def _lesson(slug):
    b = _b0.need(slug, "explorer/index.html", "ive/index.html")
    lesson = _b0.load(slug)
    jobs = [walk_job("explorer", (b / "explorer" / "index.html").resolve().as_uri()),
            walk_job("ive", (b / "ive" / "index.html").resolve().as_uri(), scope="#xp", pre=ive_pre())]
    walks = run_walks(jobs, f"live-{slug}", lesson.sha256())
    explore = (lesson.data.get("figure") or {}).get("explore") or {}
    probs = problems_of(walks, need_tiny=explore.get("kind") == "neuron")
    rec = _b0.record(f"ac10.4-{slug}", {"lesson": slug, "walks": walks, "problems": probs})
    counts = {}
    for p in probs:
        counts[f"{p.get('page', 'lesson')}:{p['kind']}"] = counts.get(f"{p.get('page', 'lesson')}:{p['kind']}", 0) + 1
    first = next((p for p in probs if p["kind"] in ("mismatch", "unbound")), None)
    assert not probs, json.dumps({"summary": _summary(walks), "problems": counts, "first": first, "record": rec})
    return {"summary": _summary(walks), "record": rec}


_b0.lesson_tests(globals(), "AC-10.4 live captions", _lesson)
