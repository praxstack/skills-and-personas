// ui.js: the overlay kit. Each piece builds its DOM once and redraws from its props (`x.p`) every frame, so
// scenes only tween props:  tl.to(code.p, { active: 9 }, at('c1', 0.3), 0.4).
//
//   frame(ui)                                   vignette + bottom fade (always on)
//   new Captions(ui)                            the current line's `cap`, bottom band, two lines max (automatic)
//   new ChapterMarks(ui)                        comic chapter banner at each chapter start + "01 THE PROBLEM" tag (automatic)
//   new TitleCard(ui, { kicker, title, title2, sub })          p: on, k (entrance 0..1)
//   new Card(ui, { kicker, big, small, top })                  p: on
//   new QuestionCard(ui, { n, text })  + .countdown(tl, lineId)  p: on, ring 1..0, num
//   new CodePanel(ui, { code, file, x, y, w, size, lh })       p: on, shown (lines revealed), active (1-based line), hl
//   new ArrayRow(ui, { label, values, heads, x, y })  .cell(i)  p: on;  cell: v, flash 0..1, tone
//   new Ladder(ui, { rungs: [{ name, time, space, cost }], x, y })  .rung(i): on, hi;  p: on, pick, pickOn
//   new Burst(ui, { text, tone, world | pos, size })            p: on (pop 0..1, use outBack), out 0..1
//   chip(ui, { world | pos, text, tone, cls })                 an Anchor: on, text, tone, scale, dx, dy
//   new Decoder(ui, rows) .row(i) .tok(id) .target(id, () => Vector3)    tok: hi, sent, fly 0..1 (flies to the target)
//   new RecTree(ui, { tree: [0, [1, [2], [3]]], title, x, y, w, h }) .node(i) .level(tl, depth, time)   node: on, tone, note, noteOn
import { el, fmt, setText, setStyle, show, Anchor } from './overlay.js';
import { C, FX, inkOf, onOf, noteOf, strokeOf, burstInkOf, plateOf } from './style.js';
import { E, clamp, lerp, rand, LINES, CHAPTERS, at, think as thinkOf } from './time.js';

const ease = (u, e = 'out') => E[e](clamp(u));

export function frame(ui) {
  el('div', 'vignette', ui.layers.world);
  el('div', 'bottomfade', ui.layers.world);
}

export const chip = (ui, o) => ui.anchor({ cls: 'chip', ...o });

// ------------------------------------------------------------------ captions
export class Captions {
  constructor(ui, { highlight = true } = {}) { this.e = el('div', 'cap', ui.layers.hud); this.hl = highlight; ui.add(this); }
  apply(t) {
    let l = null;
    // fades in at a chapter's first line (just before its voice) and out after its last; inside a chapter the
    // next caption replaces the last one at the line change (a short slide, no fade), so no frame shows a
    // half-faded caption
    let a0 = 0, a1 = 0, first = true, last = true;
    LINES.forEach((x, i) => {
      const prev = LINES[i - 1], next = LINES[i + 1];
      const f = !prev || prev.chapter !== x.chapter, z = !next || next.chapter !== x.chapter;
      const s0 = f ? x.voiceAt - 0.25 : x.start, s1 = z ? x.end - 0.05 : next.start;
      if (s0 <= t && t < s1) { l = x; a0 = s0; a1 = s1; first = f; last = z; }
    });
    if (!l) { show(this.e, 0); return; }
    const a = Math.min(first ? clamp((t - a0) / 0.15) : 1, last ? clamp((a1 - t) / 0.2) : 1);
    const slide = first ? a : Math.min(a, ease(clamp((t - a0) / 0.2)));
    // words already spoken are bright, the rest soft (estimated from the voice's progress)
    const words = l.cap.split(' '), u = this.hl ? clamp((t - l.voiceAt) / Math.max(0.3, l.voiceDur)) : 1;
    const n = Math.ceil(u * words.length + 0.5);
    const html = words.map((w, i) => (i < n ? fmt(w) : `<span class="later">${fmt(w)}</span>`)).join(' ');
    setText(this.e, html, true);
    show(this.e, a, `translateX(-50%) translateY(${((1 - ease(slide)) * 14).toFixed(1)}px)`);
  }
}

// ------------------------------------------------------------------ chapter banner + corner tag
export class ChapterMarks {
  constructor(ui, { skip = [0] } = {}) {
    this.chs = CHAPTERS.filter((c) => !skip.includes(c.n));
    this.tag = el('div', 'ltag', ui.layers.hud);
    this.num = el('span', 'num', this.tag); this.name = el('span', 'name', this.tag);
    this.card = el('div', 'ccard', ui.layers.top);
    this.band = el('div', 'band', this.card);
    this.txt = el('div', 't comic', this.card);
    ui.add(this);
  }
  apply(t) {
    let ch = null;
    for (const c of this.chs) if (c.start - 0.8 <= t) ch = c;
    if (!ch) { show(this.tag, 0); show(this.card, 0); return; }
    const label = String(ch.n).padStart(2, '0'), name = ch.name.toUpperCase();
    // banner: sweeps in during the chapter gap, holds while the first words play, sweeps out
    const a0 = ch.start - 0.78, a1 = ch.start + 0.5;
    if (t >= a0 && t < a1 + 0.3) {
      setText(this.txt, `<span class="n">${label}</span>${fmt(name)}`, true);
      const inn = ease((t - a0) / 0.3, 'outExpo'), out = ease((t - a1) / 0.3, 'in');
      setStyle(this.band, 'transform', `scaleX(${inn.toFixed(3)}) skewY(-3deg)`);
      setStyle(this.band, 'transformOrigin', '0 50%');
      const pop = ease((t - a0 - 0.12) / 0.45, 'outBack');
      setStyle(this.txt, 'transform', `translateY(-50%) scale(${(0.6 + 0.4 * pop).toFixed(3)}) rotate(-3deg)`);
      setStyle(this.txt, 'opacity', clamp(pop * 1.5).toFixed(3));
      show(this.card, 1, `translateX(${(out * 2100).toFixed(1)}px)`);
    } else show(this.card, 0);
    // corner tag: after the banner, for the rest of the chapter
    setText(this.num, label); setText(this.name, name);
    const ta = Math.min(clamp((t - (ch.start + 0.6)) / 0.4), clamp((ch.end + 0.7 - t) / 0.3));
    show(this.tag, ta, `translateX(${((1 - ease(ta)) * -40).toFixed(1)}px) rotate(-2deg)`);
  }
}

// ------------------------------------------------------------------ title card + generic card
export class TitleCard {
  constructor(ui, { kicker = '', title = '', title2 = '', sub = '' }) {
    this.e = el('div', 'title', ui.layers.hud);
    this.k = el('div', 'kick', this.e, fmt(kicker));
    this.h = el('h1', 'comic', this.e, `<span class="l1">${fmt(title)}</span><span class="l2">${fmt(title2)}</span>`);
    this.s = el('div', 'sub', this.e, fmt(sub));
    this.p = { on: 0, k: 0 }; ui.add(this);
  }
  apply() {
    const { on, k } = this.p;
    if (!show(this.e, on)) return;
    const st = (d) => ease((k - d) / 0.45, 'outBack');
    setStyle(this.k, 'transform', `translateY(${((1 - st(0)) * 30).toFixed(1)}px)`); setStyle(this.k, 'opacity', clamp(st(0)).toFixed(3));
    const l1 = this.h.children[0], l2 = this.h.children[1];
    setStyle(l1, 'display', 'block');
    setStyle(l1, 'transform', `translateX(${((1 - st(0.12)) * -80).toFixed(1)}px)`); setStyle(l1, 'opacity', clamp(st(0.12) * 1.4).toFixed(3));
    setStyle(l2, 'transform', `translateX(${((1 - st(0.24)) * -80).toFixed(1)}px)`); setStyle(l2, 'opacity', clamp(st(0.24) * 1.4).toFixed(3));
    setStyle(this.s, 'opacity', clamp((k - 0.4) / 0.4).toFixed(3));
  }
}

export class Card {
  constructor(ui, { kicker = '', big = '', small = '', top = 110 }) {
    this.e = el('div', 'card', ui.layers.hud);
    this.e.style.top = top + 'px';
    el('div', 'kick', this.e, fmt(kicker)); el('div', 'big', this.e, fmt(big)); if (small) el('div', 'small', this.e, fmt(small));
    this.p = { on: 0 }; ui.add(this);
  }
  apply() { const a = this.p.on; show(this.e, a, `translateY(${((1 - ease(a)) * 30).toFixed(1)}px) scale(${(0.94 + 0.06 * ease(a)).toFixed(3)})`); }
}

// ------------------------------------------------------------------ question card with a think countdown
export class QuestionCard {
  constructor(ui, { n = 1, text = '', label }) {
    this.e = el('div', 'qcard', ui.layers.hud);
    const q = el('div', 'q', this.e);
    el('div', 'tag', q, fmt(label || `QUESTION ${n}`)); el('div', 'text', q, fmt(text));
    const ring = el('div', 'ring', this.e);
    const R = 56, Cc = 2 * Math.PI * R;
    ring.innerHTML = `<svg viewBox="0 0 132 132"><circle cx="66" cy="66" r="${R}" fill="${C.track}" stroke="${C.trackLine}" stroke-width="10"/>` +
      `<circle class="arc" cx="66" cy="66" r="${R}" fill="none" stroke="${C.gold}" stroke-width="10" stroke-linecap="round" stroke-dasharray="${Cc.toFixed(1)}" stroke-dashoffset="0"/></svg><div class="num">?</div>`;
    this.arc = ring.querySelector('.arc'); this.num = ring.querySelector('.num'); this.Cc = Cc;
    this.p = { on: 0, ring: 1, num: -1 }; ui.add(this);
  }
  /** show the card from the question's voice (or `from`, e.g. after a chapter banner) until `until`, the ring
   *  counting down the line's think pause */
  countdown(tl, id, until, { from } = {}) {
    const [a, b] = thinkOf(id);
    tl.to(this.p, { on: 1 }, from ?? at(id) - 0.3, 0.45, 'outBack');
    tl.set(this.p, { num: Math.round(b - a) }, a);
    tl.to(this.p, { ring: 0, num: 0 }, a, b - a, 'linear');
    if (until) tl.to(this.p, { on: 0 }, until, 0.35, 'in');
    return this;
  }
  apply() {
    const { on, ring, num } = this.p;
    if (!show(this.e, on, `translateY(${((1 - clamp(on)) * -40).toFixed(1)}px) scale(${(0.9 + 0.1 * on).toFixed(3)})`)) return;
    setStyle(this.arc, 'strokeDashoffset', (this.Cc * (1 - ring)).toFixed(1));
    setText(this.num, num < 0 ? '?' : String(Math.ceil(num - 1e-6)));
  }
}

// ------------------------------------------------------------------ code panel
const KW = new Set('if else for while do return break continue const auto static new delete class struct public private using namespace template typename true false nullptr'.split(' '));
const TY = new Set('int long double float bool char void size_t vector string map unordered_map set pair queue priority_queue deque array'.split(' '));
export function highlightCpp(line) {
  const out = []; let i = 0;
  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  while (i < line.length) {
    const rest = line.slice(i);
    let m;
    if ((m = rest.match(/^\/\/.*/))) { out.push(`<span class="cm">${esc(m[0])}</span>`); break; }
    if ((m = rest.match(/^"(?:[^"\\]|\\.)*"/))) out.push(`<span class="nu">${esc(m[0])}</span>`);
    else if ((m = rest.match(/^\d+(?:\.\d+)?(?:e\d+)?/))) out.push(`<span class="nu">${m[0]}</span>`);
    else if ((m = rest.match(/^[A-Za-z_]\w*/))) {
      const w = m[0], next = line.slice(i + w.length).trimStart()[0];
      out.push(KW.has(w) ? `<span class="k">${w}</span>` : TY.has(w) ? `<span class="ty">${w}</span>` : next === '(' ? `<span class="fnc">${w}</span>` : w);
    } else if ((m = rest.match(/^(?:!=|==|<=|>=|\+\+|--|&&|\|\||->|::|[-+*/%=<>!&|?:])/))) out.push(`<span class="op">${esc(m[0])}</span>`);
    else m = [rest[0]], out.push(esc(rest[0]));
    i += m[0].length;
  }
  return out.join('');
}
export class CodePanel {
  constructor(ui, { code, file = 'solution.cpp', x = 960, y = 150, w = 864, size = 30, lh = 1.36 }) {
    this.e = el('div', 'codep', ui.layers.hud);
    Object.assign(this.e.style, { left: x + 'px', top: y + 'px', width: w + 'px' });
    this.e.style.setProperty('--code-size', size + 'px'); this.e.style.setProperty('--code-lh', String(lh));
    const bar = el('div', 'bar', this.e);
    for (const c of C.codeDots) el('i', null, bar).style.background = c;
    el('span', 'fn', bar, fmt(file));
    this.body = el('div', 'body', this.e);
    this.hl = el('div', 'hl', this.body);
    this.lines = code.replace(/\s+$/, '').split('\n').map((src, i) => {
      const ln = el('div', 'ln', this.body);
      el('span', 'no', ln, String(i + 1));
      // the indent becomes padding, so a line too long for the panel wraps 2ch right of its own indent
      const ind = src.match(/^ */)[0].length;
      const c = el('span', 'code', ln, highlightCpp(src.slice(ind)) || ' ');
      if (ind) c.style.paddingLeft = `${ind + 2}ch`;
      return ln;
    });
    this.p = { on: 0, shown: 0, active: 0, hl: 0 }; this.geo = null; ui.add(this);
  }
  /** reveal lines [from, to] (1-based) over d seconds, like a chunk being typed in */
  reveal(tl, to, time, d = 0.6) { tl.to(this.p, { shown: to }, time, d, 'out'); return this; }
  /** move the highlight to line n (1-based) */
  focus(tl, n, time, d = 0.35) { tl.to(this.p, { active: n, hl: 1 }, time, d, 'inOut'); return this; }
  apply() {
    const { on, shown, active, hl } = this.p;
    if (!show(this.e, on, `translateX(${((1 - ease(on)) * 60).toFixed(1)}px)`)) return;
    if (!this.geo) this.geo = this.lines.map((l) => [l.offsetTop, l.offsetHeight]);
    this.lines.forEach((l, i) => setStyle(l, 'opacity', clamp(shown - i).toFixed(3)));
    if (hl > 0.001 && active >= 1) {
      const i = Math.min(this.lines.length - 1, Math.floor(active - 1)), f = clamp(active - 1 - i), j = Math.min(this.lines.length - 1, i + 1);
      const top = lerp(this.geo[i][0], this.geo[j][0], f), h = lerp(this.geo[i][1], this.geo[j][1], f);
      setStyle(this.hl, 'transform', `translateY(${top.toFixed(1)}px)`); setStyle(this.hl, 'height', h.toFixed(1) + 'px');
      setStyle(this.hl, 'opacity', hl.toFixed(3)); setStyle(this.hl, 'top', '0px');
    } else setStyle(this.hl, 'opacity', '0');
  }
}

// ------------------------------------------------------------------ array row (DP state, dist/next)
export class ArrayRow {
  constructor(ui, { label = '', values = [], heads = null, headColors = C.node, x = 96, y = 700 }) {
    this.e = el('div', 'arow', ui.layers.hud);
    Object.assign(this.e.style, { left: x + 'px', top: y + 'px' });
    el('div', 'lab', this.e, fmt(label));
    this.cells = values.map((v, i) => {
      const col = el('div', 'col', this.e);
      if (heads) { const h = el('div', 'head', col, fmt(heads[i])); h.style.color = inkOf(headColors[i % headColors.length]); }
      const c = el('div', 'cell', col);
      return { e: c, p: { v: String(v), flash: 1, tone: '' } };
    });
    this.p = { on: 0 }; ui.add(this);
  }
  cell(i) { return this.cells[i].p; }
  /** write a value into cell i with a flash (and a tone for its meaning) */
  write(tl, i, v, time, tone = C.good) {
    tl.set(this.cell(i), { v: String(v), tone, flash: 0 }, time);
    tl.to(this.cell(i), { flash: 1 }, time, 0.7, 'linear');
    return this;
  }
  apply() {
    if (!show(this.e, this.p.on, `translateY(${((1 - ease(this.p.on)) * 30).toFixed(1)}px)`)) return;
    for (const c of this.cells) {
      const { v, flash, tone } = c.p, f = Math.sin(Math.PI * clamp(flash));
      setText(c.e, fmt(v), true);
      c.e.classList.toggle('inf', v === '∞' || v === '-');
      setStyle(c.e, 'borderColor', tone || C.cellLine);
      setStyle(c.e, 'background', tone ? `color-mix(in srgb, ${tone} ${Math.round(FX.cellMix[0] + FX.cellMix[1] * f)}%, transparent)` : C.cell);
      setStyle(c.e, 'transform', `scale(${(1 + 0.16 * f).toFixed(3)})`);
    }
  }
}

// ------------------------------------------------------------------ complexity ladder
export class Ladder {
  constructor(ui, { rungs, x = 960, y = 170, pickLabel = 'INTERVIEW PICK' }) {
    this.e = el('div', 'ladder', ui.layers.hud);
    Object.assign(this.e.style, { left: x + 'px', top: y + 'px' });
    el('div', 'hd', this.e, '<span>approach</span><span>time</span><span>space</span>');
    this.rungs = rungs.map((r) => {
      // a rung that is not on yet takes no room: .rwrap is a one-track grid whose row grows 0fr -> 1fr, so the
      // panel grows with each rung instead of holding empty slots for rungs still to come
      const wrap = el('div', 'rwrap', this.e), clip = el('div', 'rclip', wrap);
      const e = el('div', 'rung', clip);
      el('div', 'nm', e, fmt(r.name)); el('div', 'tm', e, fmt(r.time)); el('div', 'sp', e, fmt(r.space || ''));
      const bar = el('div', 'bar', e);
      return { wrap, clip, e, bar, cost: r.cost ?? 0.5, p: { on: 0, hi: 0, tone: r.tone || C.cool } };
    });
    this.stamp = el('div', 'stamp', null, fmt(pickLabel));
    this.p = { on: 0, pick: -1, pickOn: 0 }; ui.add(this);
  }
  rung(i) { return this.rungs[i].p; }
  apply() {
    if (!show(this.e, this.p.on, `translateX(${((1 - ease(this.p.on)) * 60).toFixed(1)}px)`)) return;
    this.rungs.forEach((r, i) => {
      const { on, hi, tone } = r.p;
      const k = ease(clamp(on / 0.6));            // room opens over the first 60% of the fade-in
      setStyle(r.wrap, 'gridTemplateRows', `${k.toFixed(4)}fr`);
      setStyle(r.clip, 'overflow', k < 1 ? 'hidden' : 'visible');
      setStyle(r.e, 'opacity', clamp(on).toFixed(3));
      setStyle(r.e, 'transform', `translateX(${((1 - ease(on)) * 40).toFixed(1)}px)`);
      setStyle(r.e, 'borderColor', hi > 0.01 ? tone : 'transparent');
      setStyle(r.e, 'background', `color-mix(in srgb, ${tone} ${Math.round(FX.rungMix[0] + FX.rungMix[1] * clamp(hi))}%, ${C.rung})`);
      r.bar.style.setProperty('--tone', tone);
      setStyle(r.bar, 'width', `${(r.cost * 100 * ease(on)).toFixed(1)}%`);
      if (i === this.p.pick && this.stamp.parentNode !== r.e) r.e.appendChild(this.stamp);
    });
    const s = this.p.pickOn;
    setStyle(this.stamp, 'opacity', clamp(s).toFixed(3));
    setStyle(this.stamp, 'transform', `rotate(6deg) scale(${(1.6 - 0.6 * s).toFixed(3)})`);
  }
}

// ------------------------------------------------------------------ comic burst ("700!", "POP!")
let burstSeed = 3;
export class Burst {
  constructor(ui, { text = 'POP!', tone = C.gold, world = null, pos = null, size = 1, rot = -8, spikes = 14 }) {
    this.ui = ui; this.world = world; this.pos = pos; this.size = size; this.rot = rot;
    this.e = el('div', 'burst', ui.layers.top);
    const R = rand(burstSeed++), pts = [], hi = [];
    for (let i = 0; i < spikes * 2; i++) {
      const a = (i / (spikes * 2)) * Math.PI * 2, r = i % 2 ? 62 + R() * 8 : 92 + R() * 18;
      pts.push(`${(Math.cos(a) * r * 1.25).toFixed(1)},${(Math.sin(a) * r).toFixed(1)}`);
      hi.push(`${(Math.cos(a) * r * 1.05).toFixed(1)},${(Math.sin(a) * r * 0.82).toFixed(1)}`);
    }
    const id = 'ht' + burstSeed;
    this.e.innerHTML = `<svg viewBox="-180 -150 360 300"><defs><pattern id="${id}" width="9" height="9" patternUnits="userSpaceOnUse"><circle cx="4.5" cy="4.5" r="2" fill="${C.halftone}"/></pattern></defs>` +
      `<polygon points="${pts.join(' ')}" fill="${C.outline}" transform="translate(7,8)"/>` +
      `<polygon points="${pts.join(' ')}" fill="${plateOf(tone)}" stroke="${C.outline}" stroke-width="7" stroke-linejoin="round"/>` +
      `<polygon points="${hi.join(' ')}" fill="url(#${id})"/></svg><div class="txt comic${/\d/.test(text) ? ' num' : ''}">${fmt(text)}</div>`;
    const ink = burstInkOf(tone), txt = this.e.querySelector('.txt');   // text ON the burst's fill
    txt.style.color = ink; txt.style.setProperty('--stroke', strokeOf(ink));
    this.p = { on: 0, out: 0 }; ui.add(this);
  }
  apply(t) {
    const { on, out } = this.p;
    const a = clamp(on) * (1 - clamp(out));
    if (a <= 0.001) { show(this.e, 0); return; }
    let x, y;
    if (this.world) { const pr = this.ui.project(typeof this.world === 'function' ? this.world() : this.world); x = pr.x; y = pr.y; } else [x, y] = this.pos;
    const s = this.size * Math.max(0.05, on) * (1 - 0.3 * clamp(out)) * (1 + 0.02 * Math.sin(t * 7));
    show(this.e, a, `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px) rotate(${(this.rot + 4 * (1 - clamp(on))).toFixed(2)}deg) scale(${s.toFixed(3)})`);
  }
  /** pop in at time, hold, pop out */
  pop(tl, time, hold = 1.6) { tl.to(this.p, { on: 1 }, time, 0.55, 'outElastic'); tl.to(this.p, { out: 1 }, time + hold, 0.3, 'in'); return this; }
}

// ------------------------------------------------------------------ input decoder
const DEC_ROW = 54; // px, the row height in film.css (.decoder .row)
// rows: array of rows; a row is an array of parts: 'plain text' or ['token text', 'id'].
export class Decoder {
  constructor(ui, rows, { x = 96, y = 150 } = {}) {
    this.ui = ui;
    this.e = el('div', 'decoder', ui.layers.hud);
    Object.assign(this.e.style, { left: x + 'px', top: y + 'px' });
    this.toks = new Map(); this.rowsE = [];
    for (const row of rows) {
      const r = el('div', 'row dec', this.e);
      for (const part of row) {
        if (typeof part === 'string') {
          // light colouring: names before '=' in blue, punctuation faint
          el('span', null, r, part.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/([A-Za-z_]\w*)(\s*=)/g, '<span class="key">$1</span>$2').replace(/([[\],])/g, '<span class="pn">$1</span>'));
        } else {
          const [txt, id] = part, s = el('span', 'tk', r, fmt(txt));
          const fly = el('div', 'flyer', ui.layers.top, fmt(txt));
          this.toks.set(id, { s, fly, target: null, p: { hi: 0, sent: 0, fly: 0 } });
        }
      }
      this.rowsE.push({ e: r, p: { on: 0 } });
    }
    this.p = { on: 0 }; ui.add(this);
  }
  row(i) { return this.rowsE[i].p; }
  tok(id) { const k = this.toks.get(id); if (!k) throw new Error(`decoder has no token "${id}"`); return k.p; }
  target(id, world) { this.toks.get(id).target = world; return this; }
  /** highlight a token, fly a copy of it into its target on the subject, mark it sent */
  send(tl, id, time, d = 0.8) {
    tl.to(this.tok(id), { hi: 1 }, time, 0.2);
    tl.to(this.tok(id), { fly: 1 }, time + 0.1, d, 'inOut');
    tl.to(this.tok(id), { hi: 0, sent: 1 }, time + 0.1 + d, 0.3);
    return this;
  }
  apply() {
    if (!show(this.e, this.p.on, `translateY(${((1 - ease(this.p.on)) * -30).toFixed(1)}px)`)) { for (const k of this.toks.values()) show(k.fly, 0); return; }
    for (const r of this.rowsE) {
      setStyle(r.e, 'opacity', clamp(r.p.on).toFixed(3)); setStyle(r.e, 'height', `${(DEC_ROW * ease(r.p.on)).toFixed(1)}px`);
      setStyle(r.e, 'transform', `translateX(${((1 - ease(r.p.on)) * 24).toFixed(1)}px)`);
    }
    const root = this.ui.root.getBoundingClientRect(), sc = this.ui.scale;
    for (const k of this.toks.values()) {
      k.s.classList.toggle('hi', k.p.hi > 0.5); k.s.classList.toggle('sent', k.p.sent > 0.5);
      const f = k.p.fly;
      if (f > 0.001 && f < 0.999 && k.target) {
        const b = k.s.getBoundingClientRect();
        const x0 = (b.left + b.width / 2 - root.left) / sc, y0 = (b.top + b.height / 2 - root.top) / sc;
        const pr = this.ui.project(typeof k.target === 'function' ? k.target() : k.target);
        const cx = (x0 + pr.x) / 2, cy = Math.min(y0, pr.y) - 120; // arc over the top
        const x = (1 - f) * (1 - f) * x0 + 2 * f * (1 - f) * cx + f * f * pr.x, y = (1 - f) * (1 - f) * y0 + 2 * f * (1 - f) * cy + f * f * pr.y;
        // opaque for the whole flight: a faded chip loses its text contrast on the board (4.5:1 rule), so the flyer
        // grows from the token's own size, lifts, and shrinks only a little (to 0.88) into its target before it hides
        const flyScale = 1 + 0.1 * Math.sin(f * Math.PI) - 0.12 * Math.max(0, (f - 0.875) / 0.125);
        show(k.fly, 1, `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px) translate(-50%, -50%) scale(${flyScale.toFixed(3)}) rotate(${(Math.sin(f * Math.PI) * -6).toFixed(2)}deg)`);
      } else show(k.fly, 0);
    }
  }
}

// ------------------------------------------------------------------ recursion tree (brute force)
// tree: nested arrays [label, child, child, ...]; nodes are numbered in breadth-first order: .node(i) props
// on 0..1, tone '#hex' ('' = node colour), note '' (text under a leaf, e.g. '700 ✓') with noteOn 0..1 (fade; set the
// note and noteOn: 0 together, then tween noteOn to 1), and the edge into it lights with on.
export class RecTree {
  constructor(ui, { tree, title = '', x = 1180, y = 170, w = 640, h = 420, colors = C.node, r = 30 }) {
    this.e = el('div', 'rtree', ui.layers.hud);
    Object.assign(this.e.style, { left: x + 'px', top: y + 'px' });
    if (title) el('div', 'ttl', this.e, fmt(title));
    // tidy layout: leaves get equal slots, parents sit over their children
    const nodes = [], depthOf = [];
    const walk = (t, d, parent) => { const n = { label: String(t[0]), d, parent, kids: [] }; nodes.push(n); if (parent) parent.kids.push(n); t.slice(1).forEach((c) => walk(c, d + 1, n)); return n; };
    const root = walk(tree, 0, null);
    let leaf = 0; const place = (n) => { if (!n.kids.length) n.x = leaf++; else { n.kids.forEach(place); n.x = (n.kids[0].x + n.kids[n.kids.length - 1].x) / 2; } };
    place(root);
    // mx: side margin wide enough for a note under the outermost leaf (a 30 px '2 stops ✗' is ~150 px wide)
    const mx = r + 60, D = Math.max(...nodes.map((n) => n.d)), sx = (w - 2 * mx) / Math.max(1, leaf - 1), sy = (h - 2 * r - 44) / Math.max(1, D);
    for (const n of nodes) { n.px = mx + n.x * sx; n.py = r + n.d * sy; depthOf.push(n.d); }
    // breadth-first numbering so .node(i) reads level by level
    const bfs = [...nodes].sort((a, b) => a.d - b.d || a.px - b.px);
    const ns = 'http://www.w3.org/2000/svg', svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('width', w); svg.setAttribute('height', h); this.e.appendChild(svg);
    const mk = (tag, attrs, parent = svg) => { const e = document.createElementNS(ns, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); parent.appendChild(e); return e; };
    this.nodes = bfs.map((n) => {
      const line = n.parent ? mk('line', { x1: n.parent.px, y1: n.parent.py, x2: n.px, y2: n.py, stroke: C.ink, 'stroke-width': 5, 'stroke-linecap': 'round' }) : null;
      return { n, line };
    });
    for (const o of this.nodes) {
      const { n } = o, col = colors[+n.label % colors.length] || C.gold;
      o.g = mk('g', { transform: `translate(${n.px},${n.py})` });
      o.c = mk('circle', { r, fill: col, stroke: C.outline, 'stroke-width': 5 }, o.g);
      o.t = mk('text', { 'text-anchor': 'middle', 'dominant-baseline': 'central', 'font-size': r * 1.1, fill: onOf(col) }, o.g); o.t.textContent = n.label;
      o.note = mk('text', { y: r + 34, 'text-anchor': 'middle', 'font-size': 30, fill: C.ink }, o.g);
      o.col = col; o.p = { on: 0, tone: '', note: '', noteOn: 1 };
    }
    this.p = { on: 0 }; ui.add(this);
  }
  node(i) { return this.nodes[i].p; }
  get size() { return this.nodes.length; }
  /** reveal every node at depth d at time (staggered) */
  level(tl, d, time, stagger = 0.08) { let k = 0; this.nodes.forEach((o) => { if (o.n.d === d) tl.to(o.p, { on: 1 }, time + stagger * k++, 0.4, 'outBack'); }); return this; }
  apply() {
    if (!show(this.e, this.p.on, `translateX(${((1 - ease(this.p.on)) * 50).toFixed(1)}px)`)) return;
    for (const o of this.nodes) {
      const a = clamp(o.p.on), s = Math.max(0.01, o.p.on);
      setStyle(o.g, 'opacity', a.toFixed(3));
      o.g.setAttribute('transform', `translate(${o.n.px},${o.n.py}) scale(${s.toFixed(3)})`);
      if (o.line) { o.line.setAttribute('opacity', (a * 0.8).toFixed(3)); o.line.setAttribute('stroke', o.p.tone || C.ink); }
      o.c.setAttribute('fill', o.p.tone || o.col);
      const tf = onOf(o.p.tone || o.col); if (o._tf !== tf) { o._tf = tf; o.t.setAttribute('fill', tf); }
      // note text in the tone lightened toward white (a red note at full saturation is only ~4.6:1 on the panel)
      if (o.note._v !== o.p.note) { o.note._v = o.p.note; o.note.textContent = o.p.note; o.note.setAttribute('fill', o.p.tone ? noteOf(o.p.tone) : C.ink); }
      o.note.setAttribute('opacity', clamp(o.p.noteOn).toFixed(3));
    }
  }
}

export { Anchor };
