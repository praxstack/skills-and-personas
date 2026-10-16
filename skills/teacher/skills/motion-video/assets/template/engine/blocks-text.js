// engine/blocks-text.js: blocks made of words. title, text (a statement), steps (a walkthrough), compare, end.
// Every block builds its DOM inside ctx.el (its box), sizes its text to fit, and places every change at a line
// time. *Marked words* get a highlighter stroke when the voice says them (or right after they appear).
(function () {
  const M = window.M;
  if (!M || !M.tl) return;
  const TY = LOOK.TYPE;

  /** Words rise into place, staggered so a long line still lands in under a second. Returns when they land. */
  M.rise = (words, t, size, d = 0.62) => {
    if (!words.length) return t;
    const st = Math.min(0.055, 0.85 / words.length);
    M.init(words, { autoAlpha: 0 });
    M.fromTo(words, { autoAlpha: 0, y: size * 0.42 }, { autoAlpha: 1, y: 0, duration: d, stagger: st, ease: 'lift' }, t);
    return t + st * (words.length - 1) + d;
  };
  /** The highlighter stroke across marked words (left to right). Returns when the last stroke is drawn. */
  M.sweepTime = (marks) => (marks.length ? 0.42 + 0.09 * (marks.length - 1) : 0);
  M.sweep = (marks, t) => {
    if (!marks.length) return t;
    M.fromTo(marks, { backgroundSize: '0% 38%' }, { backgroundSize: '100% 38%', duration: 0.42, stagger: 0.09, ease: 'power2.inOut' }, t);
    return t + M.sweepTime(marks);
  };
  /** When to sweep: when the voice says the first marked word (not before the words are up), else soon after; but
   *  early enough that the stroke is drawn before the block leaves (a word said at the very end of the shot). */
  const markTime = (c, marks, landed) => {
    if (!marks.length) return landed;
    const said = c.spoken(marks[0].textContent, null);
    const t = said === null ? landed + 0.25 : Math.max(said, landed + 0.05);
    return Math.max(landed + 0.05, Math.min(t, c.leaves - M.sweepTime(marks)));
  };
  const center = (inn, el, on) => { if (on) { inn.style.alignItems = 'center'; inn.style.textAlign = 'center'; } };

  // ------------------------------------------------------------------ title
  M.block('title', {
    fields: {
      kicker: { type: 'text', help: 'small capitals above, e.g. "DAILY QUESTION · LC 787"' },
      title: { type: 'text', required: true, help: 'the headline; *word* marks a highlight' },
      sub: { type: 'text', help: 'one line under it' },
      align: { type: 'enum', options: ['left', 'center'], help: 'default left' },
    },
    weight: { row: 1, column: 0.9 },
    build(c) {
      const { el, box, props: p, u } = c;
      const inn = M.el('div', 'in', el);
      center(inn, el, p.align === 'center');
      const kick = p.kicker ? M.el('div', 'kicker', inn, null, p.kicker) : null;
      const t = M.el('div', 't', inn);
      const { words, marks } = M.rich(p.title, t);
      const rule = M.el('div', 'rule', inn);
      const sub = p.sub ? M.el('div', 'sub', inn) : null;
      const subW = sub ? M.rich(p.sub, sub).words : [];
      if (p.align === 'center') rule.style.alignSelf = 'center';
      const other = (kick ? 60 : 0) + (sub ? 150 : 0) + 40;
      const size = M.fit(t, box.w, Math.max(120 * u, box.h - other * u), (M.shape === 'tall' ? TY.titleTall : TY.title) * u, 56 * u, `${c.where} title`);
      if (sub) M.fit(sub, box.w, 150 * u, TY.sub * u, TY.min * u, `${c.where} sub`);
      return {
        enter(t0) {
          M.set(el, { autoAlpha: 1 }, t0);
          if (kick) M.fromTo(kick, { autoAlpha: 0, x: -24 * u }, { autoAlpha: 1, x: 0, duration: 0.5 }, t0);
          const landed = M.rise(words, t0 + 0.12, size, 0.7);
          M.fromTo(rule, { scaleX: 0 }, { scaleX: 1, duration: 0.6, ease: 'power3.inOut' }, landed - 0.3);
          const subIn = subW.length ? M.rise(subW, landed - 0.15, TY.sub * u, 0.5) : 0;
          const swept = M.sweep(marks, markTime(c, marks, landed));   // may wait for the voice to say the marked word
          return Math.max(landed + 0.3, subIn, swept);   // when the title, rule, subtitle and highlight are in
        },
      };
    },
  });

  // ------------------------------------------------------------------ text: a statement, with optional chips
  M.block('text', {
    fields: {
      text: { type: 'text', required: true, help: 'the statement; *word* marks a highlight' },
      kicker: { type: 'text' },
      chips: { type: 'list', help: 'small pills under it, e.g. ["O(k·E) time", "O(n) space"]' },
      font: { type: 'enum', options: ['serif', 'sans'], help: 'default serif' },
      size: { type: 'enum', options: ['xl', 'l', 'm'], help: 'default l' },
      align: { type: 'enum', options: ['left', 'center'] },
    },
    cues: ['chips', 'mark'],
    weight: { row: 1, column: 1 },
    build(c) {
      const { el, box, props: p, u } = c;
      const inn = M.el('div', 'in', el);
      center(inn, el, p.align === 'center');
      const kick = p.kicker ? M.el('div', 'kicker', inn, null, p.kicker) : null;
      const t = M.el('div', 't ' + (p.font === 'sans' ? 'sans' : 'serif'), inn);
      const { words, marks } = M.rich(p.text, t);
      const chipsEl = p.chips && p.chips.length ? M.el('div', 'chips', inn) : null;
      if (chipsEl && p.align === 'center') chipsEl.style.justifyContent = 'center';
      (p.chips || []).forEach((x, i) => { if (!(typeof x === 'string' && x.trim() !== '') && !(typeof x === 'number' && isFinite(x))) throw new Error(`chips[${i}] is ${JSON.stringify(x)}; a chip is a short text, e.g. "O(n) space"`); });
      const chips = (p.chips || []).map((x) => { const ch = M.el('span', 'chip', chipsEl); M.rich(String(x), ch); return ch; });
      const base = (M.shape === 'tall' ? TY.statementTall : TY.statement) * ({ xl: 1.3, l: 1, m: 0.72 }[p.size || 'l'] || 1) * u;
      const size = M.fit(t, box.w, box.h - (kick ? 70 * u : 0) - (chipsEl ? 110 * u : 0), base, 40 * u, `${c.where} text`);
      const cueOf = (n) => c.cues.find((x) => x.do === n);
      let landed = 0;
      return {
        enter(t0) {
          M.set(el, { autoAlpha: 1 }, t0);
          if (kick) M.fromTo(kick, { autoAlpha: 0, x: -24 * u }, { autoAlpha: 1, x: 0, duration: 0.5 }, t0);
          landed = M.rise(words, t0 + 0.1, size, 0.66);
          const swept = cueOf('mark') ? 0 : M.sweep(marks, markTime(c, marks, landed));   // may wait for the voice
          if (chips.length && !cueOf('chips')) M.fromTo(chips, { autoAlpha: 0, scale: 0.7 }, { autoAlpha: 1, scale: 1, duration: 0.5, stagger: 0.12, ease: 'back.out(2)' }, landed + 0.1);
          if (chips.length) M.init(chips, { autoAlpha: 0 });
          return Math.max(chips.length && !cueOf('chips') ? landed + 0.6 + 0.12 * (chips.length - 1) : landed, swept);
        },
        cues: {
          chips: (cue, t1) => {
            if (!chips.length) throw new Error('there are no chips to show; add "chips": ["..."] or drop the cue');
            const t = Math.max(t1, landed); M.fromTo(chips, { autoAlpha: 0, scale: 0.7 }, { autoAlpha: 1, scale: 1, duration: 0.5, stagger: 0.14, ease: 'back.out(2)' }, t);
            return { at: t, end: t + 0.5 + 0.14 * (chips.length - 1) };
          },
          mark: (cue, t1) => {
            if (!marks.length) throw new Error('the text has no *marked* words to sweep; mark some (e.g. "the *cheapest* route") or drop the cue');
            const t = Math.max(t1, landed);
            return { at: t, end: M.sweep(marks, t) };   // every marked word stroked
          },
        },
      };
    },
  });

  // ------------------------------------------------------------------ steps: a walkthrough, one step per line
  M.block('steps', {
    fields: {
      items: { type: 'list', required: true, help: 'at least one step, each "Title" or "Title | a short note"' },
      title: { type: 'text', help: 'a small heading above the steps' },
    },
    cues: ['show'],
    weight: { row: 1.1, column: 1.3 },
    build(c) {
      const { el, box, props: p, u, P } = c;
      const inn = M.el('div', 'in', el);
      const head = p.title ? M.el('div', 'kicker', inn, { marginBottom: 30 * u + 'px' }, p.title) : null;
      if (!Array.isArray(p.items) || !p.items.length) throw new Error('items: give at least one step, e.g. ["Read the input", "Relax every edge | k + 1 rounds"]');
      const items = p.items.map((x, i) => {
        // "Title | note" splits at the first bar only, so a note may hold one ("use a | b")
        const bar = typeof x === 'string' ? x.indexOf('|') : -1;
        const r = typeof x === 'string' ? (bar < 0 ? [x.trim()] : [x.slice(0, bar).trim(), x.slice(bar + 1).trim()])
          : x && typeof x === 'object' && !Array.isArray(x) ? [x.title, x.note] : [];
        if (typeof r[0] !== 'string' || !r[0].trim() || (r[1] != null && typeof r[1] !== 'string')) throw new Error(`items[${i}] is ${JSON.stringify(x)}; a step is "Title", "Title | a short note" or {"title": "...", "note": "..."}`);
        return r;
      });
      const n = items.length;
      // more than five steps in a wide box flow into two columns, so each keeps room for its note
      const cols = n > 5 && box.w >= 900 * u ? 2 : 1;
      const perCol = Math.ceil(n / cols), gapX = 48 * u, colW = (box.w - gapX * (cols - 1)) / cols;
      const avail = box.h - (head ? 80 * u : 0);
      const per = avail / perCol;
      const hs = M.clamp(per * 0.34, TY.min * u, 46 * u), ns = M.clamp(per * 0.24, TY.min * u, 34 * u), dot = M.clamp(per * 0.5, 56 * u, 76 * u);
      const grid = M.el('div', 'grid', inn, { display: 'grid', gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))`, columnGap: gapX + 'px' });
      const colEls = Array.from({ length: cols }, () => M.el('div', 'col', grid, { position: 'relative', display: 'flex', flexDirection: 'column' }));
      const rows = items.map(([h, note], i) => {
        const st = M.el('div', 'st', colEls[Math.floor(i / perCol)], { height: per + 'px' });
        const d = M.el('div', 'dot', st, { width: dot + 'px', height: dot + 'px', fontSize: Math.max(TY.min * u, dot * 0.42) + 'px' }, String(i + 1));
        const body = M.el('div', 'body', st);
        // sized from body, so M.fit shrinking body shrinks both; the note keeps the type floor
        const hh = M.el('div', 'h', body, { fontSize: '1em' });
        M.rich(h, hh);
        const nn = note ? M.el('div', 'n', body, { fontSize: `max(${TY.min * u}px, ${(ns / hs).toFixed(4)}em)` }) : null;
        if (nn) M.rich(note, nn);
        M.fit(body, colW - dot - 26 * u, per - 8 * u, hs, TY.min * u, `${c.where} step ${i + 1}`);
        return { st, d, hh, nn, col: Math.floor(i / perCol) };
      });
      // a rail behind each column's dots; it fills as the steps are reached
      const rails = colEls.map((ce, k) => {
        const mine = rows.filter((r) => r.col === k);
        const rail = M.el('div', 'rail', ce, { left: dot / 2 - 2 * u + 'px', top: mine[0].st.offsetTop + dot / 2 + 'px', height: Math.max(0, mine[mine.length - 1].st.offsetTop - mine[0].st.offsetTop) + 'px' });
        ce.insertBefore(rail, ce.firstChild);
        return { rail, fill: M.el('div', 'f', rail), n: mine.length, at: 0 };
      });
      const rail = rails.map((r) => r.rail);
      const r0 = (k) => Math.floor(k / perCol);
      const shown = new Set();
      let cur = -1;
      const show = (k, t1, activate = true) => {
        if (k < 0 || k >= n || shown.has(k)) return;
        shown.add(k);
        const r = rows[k];
        M.fromTo(r.st, { autoAlpha: 0, x: -30 * u }, { autoAlpha: 1, x: 0, duration: 0.55, ease: 'lift' }, t1);
        if (!activate) return;
        M.to(r.d, { backgroundColor: P.accent, borderColor: P.accent, color: P.onAccent, duration: 0.3 }, t1 + 0.1);
        M.fromTo(r.d, { scale: 0.6 }, { scale: 1, duration: 0.5, ease: 'back.out(2.4)' }, t1 + 0.05);
        if (cur >= 0) M.to(rows[cur].d, { backgroundColor: P.panel2, borderColor: P.good, color: P.goodInk, duration: 0.3 }, t1 + 0.1);
        rails.forEach((r, ci) => {
          const local = ci < r0(k) ? r.n - 1 : ci === r0(k) ? k - ci * perCol : 0;
          const f = r.n > 1 ? local / (r.n - 1) : 1;
          if (Math.abs(f - r.at) > 1e-3) { M.to(r.fill, { scaleY: f, duration: 0.6, ease: 'power2.inOut' }, t1); r.at = f; }
        });
        cur = k;
      };
      const cued = c.cues.some((x) => x.do === 'show');
      let entered = 0;   // when the heading and rail are in: a "show" cue waits for it
      rows.forEach((r) => M.init(r.st, { autoAlpha: 0 }));
      return {
        enter(t0) {
          M.set(el, { autoAlpha: 1 }, t0);
          if (head) M.fromTo(head, { autoAlpha: 0, x: -24 * u }, { autoAlpha: 1, x: 0, duration: 0.5 }, t0);
          M.fromTo(rail, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.4 }, t0);
          if (!cued) rows.forEach((r, k) => show(k, t0 + 0.15 + k * Math.min(0.18, 0.8 / n), false));   // all in within ~1.5 s
          entered = t0 + 0.5;
          return cued ? entered : t0 + 0.7 + (n - 1) * Math.min(0.18, 0.8 / n);
        },
        cues: {
          // the next step, or "n" (from 1); a step that does not exist or is already in is an error, not a quiet no-op
          show: (cue, t1) => {
            const given = cue.n !== undefined && cue.n !== null && cue.n !== '';
            const k = given ? (typeof cue.n === 'number' ? cue.n : typeof cue.n === 'string' && cue.n.trim() !== '' ? Number(cue.n) : NaN) - 1 : cur + 1;
            if (!Number.isInteger(k) || k < 0 || k >= n) throw new Error(given ? `n ${JSON.stringify(cue.n)} is not a step (1 to ${n})` : `every step is already shown (${n})`);
            if (shown.has(k)) throw new Error(`step ${k + 1} is already shown`);
            const t = Math.max(t1, entered);
            show(k, t);
            return { at: t, end: t + 0.6 };   // the row in, its dot lit and the rail filled to it
          },
        },
      };
    },
  });

  // ------------------------------------------------------------------ compare: two options, one wins
  M.block('compare', {
    fields: {
      left: { type: 'json', required: true, help: '{"title": "Brute force", "body": "Try every route", "chip": "O(n^(k+1))", "tone": "bad"}' },
      right: { type: 'json', required: true, help: 'the same shape' },
      winner: { type: 'enum', options: ['left', 'right'], help: 'gets a stamp on the "winner" cue' },
      stamp: { type: 'text', help: 'the winner stamp text, default "✓ BETTER"' },
    },
    cues: ['right', 'winner'],
    weight: { row: 1.2, column: 1.2 },
    build(c) {
      const { el, box, props: p, u, P } = c;
      const inn = M.el('div', 'in', el);
      const row = M.shape === 'wide' || box.w > box.h * 1.3;
      inn.style.gridTemplateColumns = row ? '1fr 1fr' : '1fr';
      inn.style.gridTemplateRows = row ? '1fr' : '1fr 1fr';
      const sides = ['left', 'right'].map((k) => {
        // a card is an object with something to read: a title, a body or a chip (text or a number)
        const s = p[k], txt = (v) => (typeof v === 'string' && v.trim() !== '') || (typeof v === 'number' && Number.isFinite(v));
        if (!s || typeof s !== 'object' || Array.isArray(s)) throw new Error(`${k} is ${JSON.stringify(s)}; give {"title": "...", "body": "...", "chip": "..."}`);
        const bad = ['title', 'body', 'chip'].find((f) => s[f] !== undefined && s[f] !== null && s[f] !== '' && !txt(s[f]));
        if (bad) throw new Error(`${k}.${bad} is ${JSON.stringify(s[bad])}; it takes text`);
        if (!['title', 'body', 'chip'].some((f) => txt(s[f]))) throw new Error(`${k} has nothing to show; give it a "title", a "body" or a "chip"`);
        const card = M.el('div', 'side card', inn);
        const hue = M.hue(s.tone || (k === 'left' ? 'warm' : 'cool'));
        const h = M.el('div', 'h', card, { color: P[hue + 'Ink'] }, txt(s.title) ? String(s.title) : '');
        const b = M.el('div', 'b', card);
        M.rich(txt(s.body) ? String(s.body) : '', b);
        const chip = txt(s.chip) ? M.el('span', 'chip num', card) : null;
        if (chip) M.rich(String(s.chip), chip);
        const cw = row ? (box.w - 28 * u) / 2 : box.w, ch = row ? box.h : (box.h - 28 * u) / 2;
        M.fit(b, cw - 68 * u, ch - 68 * u - 50 * u - (chip ? 70 * u : 0), 72 * u, 34 * u, `${c.where} ${k}`);
        return { card, h, b, chip, hue };
      });
      const cueOf = (n) => c.cues.find((x) => x.do === n);
      const stamp = M.el('div', 'stamp', null, null, p.stamp || '✓ BETTER');
      let landed = 0, rightIn = null, won = false;   // when each card has entered (the right one may wait for its cue)
      return {
        enter(t0) {
          M.set(el, { autoAlpha: 1 }, t0);
          M.fromTo(sides[0].card, { autoAlpha: 0, y: 40 * u }, { autoAlpha: 1, y: 0, duration: 0.6, ease: 'lift' }, t0);
          landed = t0 + 0.6;
          if (!cueOf('right')) { M.fromTo(sides[1].card, { autoAlpha: 0, y: 40 * u }, { autoAlpha: 1, y: 0, duration: 0.6, ease: 'lift' }, t0 + 0.25); rightIn = t0 + 0.85; }
          else M.init(sides[1].card, { autoAlpha: 0 });
          return rightIn ?? landed;
        },
        cues: {
          right: (cue, t1) => {
            if (rightIn !== null) throw new Error('the right card is already in');
            const t = Math.max(t1, landed - 0.3);
            M.fromTo(sides[1].card, { autoAlpha: 0, y: 40 * u }, { autoAlpha: 1, y: 0, duration: 0.6, ease: 'lift' }, t);
            rightIn = t + 0.6;
            return { at: t, end: rightIn };   // the card in, so a late cue is caught rather than cut off
          },
          winner: (cue, t1) => {
            if (won) throw new Error('the winner is already stamped; a compare block takes one "winner" (for a second verdict, use a new compare block)');
            won = true;
            const side = cue.side || p.winner || 'right';
            if (side !== 'left' && side !== 'right') throw new Error(`"side" is ${JSON.stringify(side)}; it takes left or right`);
            const k = side === 'left' ? 0 : 1;
            const shown = k === 0 ? landed : rightIn;
            if (shown === null) throw new Error('the right card is not in yet; put the winner cue after the "right" cue');
            const t = Math.max(t1, shown);
            const w = sides[k];
            w.card.appendChild(stamp);
            Object.assign(stamp.style, { background: P.good, color: P.onGood });
            M.init(stamp, { autoAlpha: 0 });
            M.to(w.card, { borderColor: P.good, backgroundColor: M.tint(P.good, P.panel, P.text, 0.12), duration: 0.4 }, t);
            M.fromTo(stamp, { autoAlpha: 0, scale: 1.8, rotation: -8 }, { autoAlpha: 1, scale: 1, rotation: -3, duration: 0.45, ease: 'back.out(2.2)' }, t + 0.05);
            return { at: t, end: t + 0.5 };   // the card turned and the stamp down
          },
        },
      };
    },
  });

  // ------------------------------------------------------------------ end card
  M.block('end', {
    fields: {
      title: { type: 'text', required: true, help: 'the last line, e.g. "Try it before tomorrow\'s answer"' },
      mark: { type: 'text', help: 'two letters in the badge (default: style.mark)' },
      handle: { type: 'text', help: 'e.g. "@kaimorihq"' },
      cta: { type: 'text', help: 'a pill, e.g. "Follow for a question a day"' },
    },
    weight: { row: 1, column: 1 },
    build(c) {
      const { el, box, props: p, u } = c;
      const inn = M.el('div', 'in', el);
      const mk = M.el('div', 'mk2', inn, { width: 120 * u + 'px', height: 120 * u + 'px', fontSize: 52 * u + 'px' }, p.mark || (M.style && M.style.mark) || 'KM');
      const t = M.el('div', 't', inn);
      const { words, marks } = M.rich(p.title, t);
      const size = M.fit(t, box.w, box.h - 360 * u, (M.shape === 'tall' ? 84 : 92) * u, 48 * u, `${c.where} title`);
      const h = p.handle ? M.el('div', 'h', inn, null, p.handle) : null;
      const cta = p.cta ? M.el('div', 'cta chip', inn, null, p.cta) : null;
      return {
        enter(t0) {
          M.set(el, { autoAlpha: 1 }, t0);
          M.fromTo(mk, { autoAlpha: 0, scale: 0.4, rotation: -12 }, { autoAlpha: 1, scale: 1, rotation: 0, duration: 0.7, ease: 'back.out(2)' }, t0);
          const landed = M.rise(words, t0 + 0.25, size, 0.7);
          const swept = M.sweep(marks, markTime(c, marks, landed));   // may wait for the voice to say the marked word
          if (h) M.fromTo(h, { autoAlpha: 0, y: 16 * u }, { autoAlpha: 1, y: 0, duration: 0.5 }, landed - 0.1);
          if (cta) M.fromTo(cta, { autoAlpha: 0, scale: 0.7 }, { autoAlpha: 1, scale: 1, duration: 0.55, ease: 'back.out(2)' }, landed + 0.15);
          return Math.max(cta ? landed + 0.7 : h ? landed + 0.4 : Math.max(landed, t0 + 0.7), swept);
        },
      };
    },
  });
})();
