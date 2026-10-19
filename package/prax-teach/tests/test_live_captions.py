"""AC-10.4 (SPEC v1.4 WP10): every explorer and IVE sentence that describes state matches the state on screen
after every control step, and a tiny nonzero z such as 1.11022e-16 is explained as binary64 rounding.

How it measures (in the page, in Playwright):
  controls    every visible range slider (each value), radio group (each option), aria-pressed toggle and
              checkbox (both states) in the scope. Controls in one region are combined: when their combinations
              number 1500 or fewer, every combination is visited (the neuron's 41 x 21 grid is); otherwise each
              control is swept alone. Then every other button (Next, Previous, ...) is pressed until it is
              disabled, at most 12 times; with 12 or fewer combinations, at every combination. The explorer page is
              the scope; in the IVE, the explore panel (#xp) after "Pause and explore" near the end of the film.
              Each page runs at 1440 x 900 light and 390 x 844 dark.
  prose       any visible block (any tag, SVG text included) whose own inline text has 3 or more words. Control
              labels, buttons and code listings are not prose.
  drawn state read after each step only from what is drawn outside prose, never from a data flag: "name = value"
              pairs, a slider's visible readout named by its label, a checked radio's visible label named by its
              fieldset legend ("Value of a"), and elements marked data-state-var="<name>". A data-state-var inside
              a sentence is part of the sentence, not state. A name drawn only in a code listing is compared with
              that listing (the source's initialiser).
  sentences   each prose block split into sentences. A sentence asserts "name = value" and, for a name the region
              draws, "name prints as value". Each assertion must match the drawn value of its own region (the
              closest [data-role="explore"], .knob, .step, #xp or main). An "=" assertion about a name the region
              does not draw fails as unbound. A block marked data-captured="<fact ids>" describes captured runs: it
              is not compared with live state, but every number in it must appear in those facts' captured values.
  model       on the neuron lesson, the drawn z and a are recomputed from the drawn w2 and b with the program's
              formula in binary64 (z = x1*w1 + x2*w2 + b, a = fmax(0, z), x1, w1, x2 from the capture) and
              compared after %g rounding, at every step.
  rounding    when a drawn value is nonzero with magnitude below 1e-9, a visible sentence in the same innermost
              region must mention binary64 or double, and rounding. On the neuron lesson that state must be reached.
  IVE         the IVE part is not-run when its explore panel has no controls or no assertions, unless the explorer
              has assertions: then the IVE must have them too, or the test fails.
"""
import json

import _b0
from selftest_support import NotRun

WALK_JS = r"""async (opts) => {
  opts = opts || {};
  const scope = opts.scope ? document.querySelector(opts.scope) : document.body;
  if (!scope) return { error: 'no scope ' + opts.scope };
  const FACTS = opts.facts || {};
  const vis = (el) => { if (!el || el.closest('noscript')) return false; if (!el.getClientRects().length) return false;
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) { const s = getComputedStyle(e);
      if (s.display === 'none' || s.visibility === 'hidden' || parseFloat(s.opacity) === 0) return false; } return true; };
  const tick = () => new Promise((r) => requestAnimationFrame(() => setTimeout(r, opts.settle || 0)));
  const REGION = '[data-role="explore"], .knob, .step, #xp, main, body';
  const NOT_PROSE = 'button, label, legend, select, option, noscript, [data-code], code, pre, script, style';
  const NUM = String.raw`[-+−]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?`;
  const ID = String.raw`[A-Za-z_]\w*(?:\(-?\d+\))?`;
  const pairRe = () => new RegExp(String.raw`(?<![\w.])(${ID})\s*=\s*(${NUM})(?!\w|\.\d)`, 'g');
  const sayRe = () => new RegExp(String.raw`(?<![\w.])(${ID})\s+prints as\s+(${NUM})(?!\w|\.\d)`, 'g');
  const numRe = () => new RegExp(String.raw`(?<![\w.])${NUM}(?!\w|\.\d)`, 'g');
  const key = (v) => String(parseFloat(String(v).replace('−', '-')));
  const words = (t) => (t.match(/[A-Za-z]{2,}/g) || []).length;
  const sentences = (t) => t.replace(/\s+/g, ' ').trim().split(/(?<=[.!?])\s+(?=[A-Z0-9"'(])/);
  const isBlock = (e) => e.tagName === 'text' || /block|flex|grid|list-item|table|flow-root/.test(getComputedStyle(e).display);
  const ownInline = (el) => { let t = ''; for (const n of el.childNodes) {
      if (n.nodeType === 3) t += n.textContent;
      else if (n.nodeType === 1 && getComputedStyle(n).display !== 'none' && getComputedStyle(n).visibility !== 'hidden'
               && !(n.tagName !== 'tspan' && isBlock(n))) t += ownInline(n); } return t; };
  // prose: any visible block whose own inline text has 3+ words, whatever its tag
  const proseBlocks = () => [...scope.querySelectorAll('*')].filter((el) => (el.tagName === 'text' || !(el instanceof SVGElement))
    && isBlock(el) && !el.closest(NOT_PROSE) && vis(el) && words(ownInline(el)) >= 3);
  const radioName = (r) => {
    const fs = r.closest('fieldset'), lg = fs && fs.querySelector('legend');
    const m = lg && lg.textContent.trim().match(/([A-Za-z_]\w*)$/);
    return (fs && fs.dataset.stateVar) || r.dataset.stateVar || (m && m[1].length <= 3 ? m[1] : r.name.replace(/^.*-/, ''));
  };
  const drawn = (region, prose) => {
    const st = {}, code = {};
    const inProse = (el) => prose.some((p) => p === el || p.contains(el) || el.contains(p));
    const add = (n, v, into) => { if (!/^[A-Za-z_]\w*(\(-?\d+\))?$/.test(n)) return; const t = into || st; (t[n] = t[n] || new Set()).add(key(v)); };
    for (const el of region.querySelectorAll('[data-state-var]')) if (vis(el) && !inProse(el)) add(el.dataset.stateVar, el.textContent.trim());
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
    for (const el of region.querySelectorAll('*')) {
      if (!vis(el) || el.closest('noscript, script, style') || inProse(el)) continue;
      if (![...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim()) && el.tagName !== 'text') continue;
      const host = el.tagName === 'text' ? el : (el.closest('p, li, td, th, dd, dt, output, h1, h2, h3, h4, h5, h6, figcaption, div, text') || el);
      if (inProse(host)) continue;
      const inCode = !!el.closest('[data-code], code, pre');
      for (const m of host.textContent.replace(/\s+/g, ' ').matchAll(pairRe())) add(m[1], m[2], inCode ? code : st);
    }
    const live = Object.assign({}, st);
    for (const [n, vs] of Object.entries(code)) if (!st[n]) st[n] = vs;
    Object.defineProperty(st, '__live', { value: live, enumerable: false });
    return st;
  };
  const res = { steps: 0, assertions: 0, captured_checked: 0, model_checked: 0, problems: [], problem_count: 0,
                tiny: { reached: 0, explained: 0, examples: [] }, controls: [] };
  res.kinds = {};
  const report = (p) => { res.problem_count++; res.kinds[p.kind] = (res.kinds[p.kind] || 0) + 1; if (res.problems.length < 40) res.problems.push(p); };
  const M = opts.model;
  const g6 = (x) => Number(x.toPrecision(6));
  const check = async (label) => {
    await tick();
    res.steps++;
    const prose = proseBlocks();
    const regions = new Map();
    const region = (el) => { const r = el.closest(REGION) || scope; if (!regions.has(r)) regions.set(r, drawn(r, prose)); return [r, regions.get(r)]; };
    for (const blk of prose) {
      const capt = blk.closest('[data-captured]');
      if (capt) {
        const ids = capt.getAttribute('data-captured').split(/[\s,]+/).filter(Boolean);
        const pool = new Set(ids.flatMap((i) => (String(FACTS[i] || '').match(numRe()) || []).map(key)));
        res.captured_checked++;
        const missing = (ownInline(blk).match(numRe()) || []).filter((x) => !pool.has(key(x)));
        if (!ids.length || ids.some((i) => !(i in FACTS)) || missing.length)
          report({ kind: 'captured-mismatch', step: label, facts: ids, numbers_not_captured: missing, sentence: ownInline(blk).trim().slice(0, 160) });
        continue;
      }
      const [, st] = region(blk);
      for (const s of sentences(ownInline(blk))) {
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
    const cands = [scope, ...scope.querySelectorAll(REGION)].filter((r) => r === scope || vis(r));
    const leaves = cands.filter((r) => !cands.some((o) => o !== r && r.contains(o)));
    let modelled = false;
    for (const r of leaves) {
      const st = region(r)[1], lv = st.__live;
      if (M && M.kind === 'neuron' && lv.w2 && lv.b && lv.w2.size === 1 && lv.b.size === 1) {
        modelled = true; res.model_checked++;
        const w2 = parseFloat([...lv.w2][0]), b = parseFloat([...lv.b][0]);
        const z = M.x1 * M.w1 + M.x2 * w2 + b, a = Math.max(0, z);
        for (const [n, want] of [['z', g6(z)], ['a', g6(a)]]) {
          const got = lv[n] ? [...lv[n]].map(parseFloat) : [];
          if (got.length !== 1 || got[0] !== want) report({ kind: 'model-mismatch', step: label, name: n, drawn: got, model: want, w2, b });
        }
      }
      const tiny = Object.entries(st).filter(([, vs]) => [...vs].some((v) => { const x = parseFloat(v); return x !== 0 && Math.abs(x) < 1e-9; }));
      if (!tiny.length) continue;
      res.tiny.reached++;
      const text = prose.filter((b) => (b.closest(REGION) || scope) === r).map((b) => ownInline(b)).join(' ');
      const ok = /binary64|double/i.test(text) && /round/i.test(text);
      if (ok) res.tiny.explained++;
      if (res.tiny.examples.length < 3) res.tiny.examples.push({ step: label, values: tiny.map(([n, vs]) => n + '=' + [...vs].join('|')), explained: ok });
      if (!ok) report({ kind: 'tiny-unexplained', step: label, values: tiny.map(([n, vs]) => n + '=' + [...vs].join('|')) });
    }
    if (M && !modelled) report({ kind: 'model-not-applied', step: label, why: 'no region draws exactly one w2 and one b' });
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


def walk_job(jid, url, scope=None, pre=None, width=1440, height=900, scheme="light", facts=None, model=None):
    opts = {"scope": scope, "facts": facts or {}, "model": model}
    steps = list(pre or []) + [{"eval": f"({WALK_JS})({json.dumps(opts)})", "as": "walk"}]
    return {"id": jid, "type": "script", "url": url, "width": width, "height": height, "scheme": scheme, "steps": steps}


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
        shown = {p["kind"] for p in w["problems"]}
        for k, n in (w.get("kinds") or {}).items():
            if k not in shown:
                probs.append({"kind": k, "page": jid, "count": n, "note": "beyond the first 40 problems"})
        if w["problem_count"] > len(w["problems"]):
            probs.append({"kind": "more-problems", "page": jid, "count": w["problem_count"] - len(w["problems"])})
    if need_tiny and not any(w.get("tiny", {}).get("reached") for w in walks.values() if not w.get("error")):
        probs.append({"kind": "tiny-case-not-reached"})
    return probs


def ive_status(walks):
    """'ok', 'not-run' (the IVE panel has nothing to check and the explorer has no bound sentences either), or a
    problem when the explorer binds sentences and the IVE does not."""
    ex = [w for j, w in walks.items() if j.startswith("explorer") and not w.get("error")]
    iv = [w for j, w in walks.items() if j.startswith("ive") and not w.get("error")]
    ex_bound = any(w["assertions"] for w in ex)
    empty = [w for w in iv if not w["controls"] or not w["assertions"]]
    if not empty:
        return "ok", []
    if ex_bound:
        return "failed", [{"kind": "ive-has-no-bound-sentences", "explorer_assertions": max(w["assertions"] for w in ex),
                           "ive": [{"controls": len(w["controls"]), "assertions": w["assertions"]} for w in iv]}]
    return "not-run", []


def _summary(walks):
    return {jid: ({"error": w["error"]} if w.get("error") else
                  {"controls": w["controls"], "combinations": w.get("combinations"), "steps": w["steps"],
                   "assertions": w["assertions"], "captured_checked": w.get("captured_checked"),
                   "model_checked": w.get("model_checked"), "problems": w["problem_count"], "tiny": w["tiny"]})
            for jid, w in walks.items()}


# ---------------------------------------------------------------- fixtures

FIX_FACTS = {"f.k1.z": "b = -1  z = -0.2", "f.k1.a": "a = 0"}
FIX_MODEL = {"kind": "neuron", "x1": 0.8, "w1": 1.5, "x2": 0.4}


def _fx(name, path):
    return walk_job(name, (_b0.FIXTURES / path).resolve().as_uri(), facts=FIX_FACTS, model=FIX_MODEL)


def test_fixture_live_sentence_passes():
    """Two sliders with a sentence rebuilt from the drawn state, a captured-run sentence bound to its facts, the
    model agreeing at every step, and a binary64 note at the tiny values: all 861 combinations pass."""
    walks = run_walks([_fx("pass", "explorer-pass.html")], "live-pass")
    probs = problems_of(walks, need_tiny=True)
    assert not probs, probs[:5]
    w = walks["pass"]
    assert w["steps"] >= 861 and w["tiny"]["reached"] >= 1 and w["tiny"]["explained"] == w["tiny"]["reached"], w
    assert w["captured_checked"] >= 861 and w["model_checked"] >= 861, w
    return _summary(walks)


def test_fixture_fixed_sentence_fails():
    """The same sliders under a fixed sentence (the rc1 neuron pattern), a captured-run sentence with a number its
    facts do not hold, and a drawn z that disagrees with the model: each fails."""
    walks = run_walks([_fx("fail", "explorer-fail.html")], "live-fail")
    probs = problems_of(walks, need_tiny=True)
    kinds = {p["kind"] for p in probs}
    assert {"mismatch", "tiny-unexplained", "captured-mismatch", "model-mismatch"} <= kinds, (sorted(kinds), probs[:5])
    assert any(p.get("step") == "initial" for p in probs if p["kind"] == "mismatch"), probs[:5]
    return {"kinds": sorted(kinds), **_summary(walks)}


ADVERSARIAL = ("live-div-prose.html", "live-state-var-in-sentence.html", "live-captured-word.html")


def test_fixture_adversarial_captions_fail():
    """The review's crafted pages: the stale sentence in a <div>, bound to itself with data-state-var, and behind
    the word "captured". Each is now read as prose and fails against the drawn state."""
    walks = run_walks([_fx(p, f"adversarial/{p}") for p in ADVERSARIAL], "live-adv")
    got = {}
    for p in ADVERSARIAL:
        kinds = {x["kind"] for x in problems_of({p: walks[p]})}
        assert "mismatch" in kinds, (p, sorted(kinds), walks[p].get("problems", [])[:3])
        got[p] = sorted(kinds)
    return got


def test_ive_rule():
    """The IVE part is not-run when nothing binds anywhere, and fails when the explorer binds and the IVE does not."""
    w = lambda c, a: {"controls": ["x"] * c, "assertions": a, "problems": [], "problem_count": 0}
    assert ive_status({"explorer": w(2, 5), "ive": w(1, 3)})[0] == "ok"
    assert ive_status({"explorer": w(2, 0), "ive": w(0, 0)})[0] == "not-run"
    assert ive_status({"explorer": w(2, 5), "ive": w(3, 0)})[0] == "failed"
    return "ok"


# ---------------------------------------------------------------- the built lessons

def neuron_model(lesson, facts):
    pan = (lesson.data.get("figure") or {}).get("panel") or {}
    terms = pan.get("terms") or []
    if pan.get("kind") != "neuron" or len(terms) < 2:
        return None
    try:
        return {"kind": "neuron", "x1": float(facts[terms[0]["x"]]), "w1": float(facts[terms[0]["w"]]),
                "x2": float(facts[terms[1]["x"]])}
    except (KeyError, TypeError, ValueError):
        return None


def _lesson(slug):
    b = _b0.need(slug, "explorer/index.html", "ive/index.html", "capture")
    lesson = _b0.load(slug)
    facts, _ = _b0.captured_facts(lesson.data, b / "capture")
    facts = {k: v for k, v in facts.items() if v is not None}
    model = neuron_model(lesson, facts)
    ex, ive = (b / "explorer" / "index.html").resolve().as_uri(), (b / "ive" / "index.html").resolve().as_uri()
    kw = {"facts": facts, "model": model}
    jobs = [walk_job("explorer-1440-light", ex, **kw),
            walk_job("explorer-390-dark", ex, width=390, height=844, scheme="dark", **kw),
            walk_job("ive-1440-light", ive, scope="#xp", pre=ive_pre(), facts=facts),
            walk_job("ive-390-dark", ive, scope="#xp", pre=ive_pre(), width=390, height=844, scheme="dark", facts=facts)]
    walks = run_walks(jobs, f"live-{slug}", lesson.sha256())
    explore = (lesson.data.get("figure") or {}).get("explore") or {}
    probs = problems_of(walks, need_tiny=explore.get("kind") == "neuron")
    if explore.get("kind") == "neuron" and not model:
        probs.append({"kind": "model-unavailable"})
    status, iprobs = ive_status(walks)
    probs += iprobs
    rec = _b0.record(f"ac10.4-{slug}", {"lesson": slug, "walks": walks, "ive": status, "problems": probs})
    counts = {}
    for p in probs:
        counts[f"{p.get('page', 'lesson')}:{p['kind']}"] = counts.get(f"{p.get('page', 'lesson')}:{p['kind']}", 0) + 1
    first = next((p for p in probs if p["kind"] in ("mismatch", "unbound", "model-mismatch")), None)
    short = {jid: ("error" if w.get("error") else
                   f"steps {w['steps']}, assertions {w['assertions']}, model {w.get('model_checked')}, "
                   f"problems {w['problem_count']}, tiny {w['tiny']['reached']}/{w['tiny']['explained']} explained")
             for jid, w in walks.items()}
    assert not probs, json.dumps({"problems": counts, "first": first, "pages": short, "record": rec})
    if status == "not-run":
        raise NotRun(f"explorer passes; the IVE explore panel has no controls or no bound sentences ({short})")
    return {"summary": _summary(walks), "ive": status, "record": rec}


_b0.lesson_tests(globals(), "AC-10.4 live captions", _lesson)
