// engine/blocks-dsa.js: blocks for coding questions. question (options, a think countdown, the reveal),
// graph (nodes, weighted edges, routes a token travels), code (a panel with a focus bar), array (cells, pointers).
(function () {
  const M = window.M;
  if (!M || !M.tl) return;
  const TY = LOOK.TYPE;
  const given = (v) => v !== undefined && v !== null && v !== '';   // a cue setting the author wrote down
  // a short text the author wrote (a number reads as itself); an object or a list would show as "[object Object]"
  const isText = (v) => (typeof v === 'string' && v.trim() !== '') || (typeof v === 'number' && Number.isFinite(v));
  const textOr = (v, what) => { if (given(v) && !isText(v)) throw new Error(`${what} is ${JSON.stringify(v)}; it takes a short text`); return given(v); };
  const toneOf = (P, t) => { const h = M.hue(t || 'accent'); return { fill: P[h], ink: P[h + 'Ink'], on: P['on' + h[0].toUpperCase() + h.slice(1)] }; };

  // ------------------------------------------------------------------ question
  M.block('question', {
    fields: {
      prompt: { type: 'text', required: true, help: 'the question; *word* marks a highlight' },
      options: { type: 'list', required: true, help: '2 to 4 answers' },
      answer: { type: 'number', required: true, help: 'index of the right option, a whole number (0 = first)' },
      trap: { type: 'number', help: 'index of the tempting wrong option (marked ✗ on reveal); not the answer' },
      notes: { type: 'list', help: 'one short note per option, shown on reveal (e.g. "2 stops")' },
      letters: { type: 'bool', help: 'A B C D badges (default true)' },
    },
    cues: ['think', 'reveal', 'pick'],
    weight: { row: 1.2, column: 1.25 },
    build(c) {
      const { el, box, props: p, u, P, shot } = c;
      const n = Array.isArray(p.options) ? p.options.length : 0;
      if (n < 2 || n > 4) throw new Error('options: give a list of 2 to 4');
      // an option is text or a number the viewer reads; an object, null or blank would show as "[object Object]" or nothing
      const shown = (v) => (typeof v === 'string' && v.trim() !== '') || (typeof v === 'number' && Number.isFinite(v));
      p.options.forEach((o, i) => { if (!shown(o)) throw new Error(`options[${i}] is ${JSON.stringify(o)}; an option is a text or a number, e.g. "700"`); });
      if (p.notes !== undefined && p.notes !== null && !Array.isArray(p.notes)) throw new Error('notes: give a list, one short note per option');
      (p.notes || []).forEach((o, i) => { if (o !== null && o !== '' && !shown(o)) throw new Error(`notes[${i}] is ${JSON.stringify(o)}; a note is a short text, or "" for none`); });
      // an option index: a whole number from 0 to n-1 (a "1" from a form is read as 1; 1.5, "" or true are refused)
      const idx = (v, what) => {
        const k = typeof v === 'number' ? v : typeof v === 'string' && v.trim() !== '' ? Number(v) : NaN;
        if (!Number.isInteger(k) || k < 0 || k >= n) throw new Error(`${what} ${JSON.stringify(v)} is not an option index (0 to ${n - 1})`);
        return k;
      };
      const answer = idx(p.answer, 'answer');
      const trap = p.trap === undefined || p.trap === null || p.trap === '' ? null : idx(p.trap, 'trap');
      if (trap === answer) throw new Error(`trap ${trap} is the answer`);
      const inn = M.el('div', 'in', el);
      const timerR = 50 * u;
      const prompt = M.el('div', 'prompt', inn, { paddingRight: timerR * 2 + 20 * u + 'px' });
      const { words, marks } = M.rich(p.prompt, prompt);
      // two columns on a wide frame, or anywhere the answers are short ("700", "No route")
      const short = p.options.every((o) => String(o).replace(/[*`]/g, '').length <= 14);
      const cols = n > 2 && (short || (M.shape === 'wide' && box.w > 1200 * u)) ? 2 : 1;
      const opts = M.el('div', 'opts', inn, { gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` });
      const rowsN = Math.ceil(n / cols);
      const optH = M.clamp((box.h * 0.58) / rowsN - 18 * u, 78 * u, 118 * u);
      const ofs = M.clamp(optH * 0.4, TY.min * u, 42 * u);
      const items = p.options.map((o, i) => {
        const it = M.el('div', 'opt', opts, { minHeight: optH + 'px', fontSize: ofs + 'px' });
        const lt = p.letters === false ? null : M.el('span', 'lt', it, null, 'ABCD'[i]);
        const ot = M.el('span', 'ot num', it);
        M.rich(String(o), ot);
        return { it, lt, ot, badge: null };
      });
      const psize = M.fit(prompt, box.w, box.h - (optH + 18 * u) * rowsN - 40 * u, (M.shape === 'tall' ? 66 : 64) * u, 40 * u, `${c.where} prompt`);
      // the think timer: a ring that drains while the viewer thinks, with the seconds left
      const tsvg = M.svg('svg', { class: 'timer', width: timerR * 2, height: timerR * 2, viewBox: `${-timerR} ${-timerR} ${timerR * 2} ${timerR * 2}` }, el);
      M.svg('circle', { r: timerR - 6 * u, fill: P.panel, stroke: P.line, 'stroke-width': 8 * u }, tsvg);
      const tarc = M.svg('circle', { r: timerR - 6 * u, fill: 'none', stroke: P.accent, 'stroke-width': 8 * u, 'stroke-linecap': 'round', transform: 'rotate(-90)' }, tsvg);
      const tnum = M.svg('text', { 'text-anchor': 'middle', 'dominant-baseline': 'central', 'font-size': 36 * u, 'font-weight': 760, fill: P.text, 'font-family': 'Inter' }, tsvg);
      M.init(tsvg, { autoAlpha: 0 });
      M.init(items.map((x) => x.it), { autoAlpha: 0 });
      // thinkEnd: when the countdown runs out (the answer may not show before it); revealed: when the answer showed;
      // picked: the option the last pick lit and its note (the same pick again would change nothing)
      let landed = 0, thinkDone = false, thinkEnd = 0, revealed = null, picked = null;
      const think = (t1, secs) => {
        if (thinkDone || !(secs > 0.4)) return;
        if (revealed !== null) throw new Error(`the countdown at ${t1.toFixed(2)} s would run after the answer is revealed (${revealed.toFixed(2)} s); put the "think" cue before the "reveal"`);
        thinkDone = true;
        thinkEnd = t1 + secs;
        const o = { s: secs };
        tnum.textContent = String(Math.ceil(secs));
        M.fromTo(tsvg, { autoAlpha: 0, scale: 0.6, transformOrigin: '50% 50%' }, { autoAlpha: 1, scale: 1, duration: 0.35, ease: 'back.out(2.4)' }, t1);
        M.fromTo(tarc, { drawSVG: '0% 100%' }, { drawSVG: '0% 0%', duration: secs, ease: 'none' }, t1);
        M.fromTo(o, { s: secs }, { s: 0, duration: secs, ease: 'none', onUpdate: () => { tnum.textContent = String(Math.max(1, Math.ceil(o.s - 1e-6))); } }, t1);
        M.to(tsvg, { autoAlpha: 0, scale: 0.8, duration: 0.25 }, t1 + secs);
        M.event(t1, 'think');
      };
      // a badge per call (a pick, then the reveal), so each keeps its own text; the previous one leaves at t
      const badge = (k, text, tone, t1) => {
        const tc = toneOf(P, tone);
        const b = M.el('span', 'badge', items[k].it, { background: tc.fill, color: tc.on }, text);
        M.init(b, { autoAlpha: 0, display: 'none' });   // takes no room until it shows
        M.set(b, { display: 'inline-block' }, t1);
        if (items[k].badge) { M.to(items[k].badge, { autoAlpha: 0, duration: 0.15 }, t1 - 0.15); M.set(items[k].badge, { display: 'none' }, t1); }
        items[k].badge = b;
        return b;
      };
      return {
        enter(t0) {
          M.set(el, { autoAlpha: 1 }, t0);
          landed = M.rise(words, t0 + 0.05, psize, 0.62);
          // the prompt's highlight waits for the voice, but is drawn before the block leaves
          const swept = M.sweep(marks, Math.max(landed, Math.min(c.spoken(marks[0] ? marks[0].textContent : '', landed), c.leaves - M.sweepTime(marks))));
          const tOpts = Math.max(landed - 0.2, t0 + 0.4);
          M.fromTo(items.map((x) => x.it), { autoAlpha: 0, y: 26 * u }, { autoAlpha: 1, y: 0, duration: 0.5, stagger: 0.12, ease: 'lift' }, tOpts);
          landed = tOpts + 0.12 * (n - 1) + 0.5;
          // the countdown runs in the first think pause of this shot that still has room once the options are in,
          // unless a "think" cue places it; a shot whose pauses are all too short for it is an error, not a quiet skip
          if (!c.cues.some((x) => x.do === 'think')) {
            const pauses = M.lines.filter((x) => x.start >= shot.t0 - 0.01 && x.start < shot.t1 - 0.01 && x.think > 0.4);
            const room = (l) => l.end - Math.max(l.vEnd, landed) - 0.1;
            const l = pauses.find((x) => room(x) > 0.4);
            if (l) think(Math.max(l.vEnd, landed), room(l));
            else if (pauses.length) { const q = pauses[0]; throw new Error(`the countdown would run in line ${q.id}'s pause, ${q.vEnd.toFixed(2)} to ${q.end.toFixed(2)} s, but with the options in at ${landed.toFixed(2)} s only ${Math.max(0, room(q)).toFixed(2)} s are left (it needs more than 0.4); lengthen that pause ("think"), or place the countdown with a "think" cue and "secs"`); }
          }
          return Math.max(landed, swept);   // the prompt, every option and the prompt's highlight in
        },
        cues: {
          // the countdown starts once the options are in, and by default runs to the end of the cue's line
          think: (cue, t1) => {
            if (thinkDone) throw new Error('the countdown already ran; a question takes one "think"');
            const l = M.lineAt(t1 + 0.01), t = Math.max(t1, landed);
            const gave = given(cue.secs);
            const secs = gave ? M.data.num(cue.secs) : l ? l.end - t - 0.1 : 2.5;
            if (!(secs > 0.4 && Number.isFinite(secs))) throw new Error(gave ? `"secs" ${JSON.stringify(cue.secs)} must be a number above 0.4` : `only ${Math.max(0, secs).toFixed(2)} s are left on line ${l.id} to count down; put the cue earlier, on a line with a pause, or give "secs"`);
            think(t, secs);
            return { at: t, end: t + secs - 0.3 };   // the last 0.3 s of the countdown may run into the block's exit
          },
          pick: (cue, t1) => {
            if (revealed !== null) throw new Error('the answer is already revealed; a pick after it would recolour the result (put the pick before the "reveal")');
            t1 = Math.max(t1, landed);
            const k = idx(cue.n, 'n'), note = textOr(cue.note, '"note"');
            const was = JSON.stringify([k, note ? String(cue.note) : null]);
            if (picked === was) throw new Error(`option ${k} is already picked${note ? ' with that note' : ''}; a pick must change something (another option, or a new "note")`);
            picked = was;
            M.to(items[k].it, { borderColor: P.accent, duration: 0.3 }, t1);
            if (note) M.fromTo(badge(k, String(cue.note), 'accent', t1 + 0.1), { autoAlpha: 0, scale: 0.6 }, { autoAlpha: 1, scale: 1, duration: 0.4, ease: 'back.out(2.4)' }, t1 + 0.1);
            return { at: t1, end: t1 + (note ? 0.5 : 0.3) };   // the border lit and the badge in
          },
          reveal: (cue, t1) => {
            const lead = trap !== null ? 0.2 : 0;   // the trap turns red just before the answer turns green
            if (revealed !== null) throw new Error('the answer is already revealed; a question takes one "reveal"');
            t1 = Math.max(t1, landed + lead);
            if (t1 - lead < thinkEnd - 0.01) throw new Error(`the reveal at ${(t1 - lead).toFixed(2)} s comes while the countdown still runs (to ${thinkEnd.toFixed(2)} s); put it on a later line, or give the "think" cue fewer "secs"`);
            revealed = t1 - lead;
            const notes = p.notes || [];
            const noteOr = (k, d) => (notes[k] === undefined || notes[k] === null || String(notes[k]).trim() === '' ? d : String(notes[k]));   // a note of 0 stays 0
            items.forEach((x, k) => {
              if (k === answer) {
                M.to(x.it, { borderColor: P.good, backgroundColor: M.tint(P.good, P.panel, P.text, 0.16), duration: 0.4, overlapOk: true }, t1);
                if (x.lt) M.to(x.lt, { backgroundColor: P.good, borderColor: P.good, color: P.onGood, duration: 0.3 }, t1);
                M.fromTo(x.it, { scale: 1 }, { scale: 1.035, duration: 0.22, yoyo: true, repeat: 1, ease: 'power2.out' }, t1 + 0.05);
                M.fromTo(badge(k, '✓ ' + noteOr(k, 'right'), 'good', t1 + 0.15), { autoAlpha: 0, scale: 0.5 }, { autoAlpha: 1, scale: 1, duration: 0.45, ease: 'back.out(2.6)', overlapOk: true }, t1 + 0.15);
              } else if (k === trap) {
                M.to(x.it, { borderColor: P.bad, duration: 0.4, overlapOk: true }, t1 - 0.2);
                if (x.lt) M.to(x.lt, { backgroundColor: P.bad, borderColor: P.bad, color: P.onBad, duration: 0.3 }, t1 - 0.2);
                M.fromTo(badge(k, '✗ ' + noteOr(k, 'trap'), 'bad', t1 - 0.1), { autoAlpha: 0, scale: 0.5 }, { autoAlpha: 1, scale: 1, duration: 0.45, ease: 'back.out(2.6)', overlapOk: true }, t1 - 0.1);
              }
            });
            return { at: t1 - lead, end: t1 + 0.6 };   // the trap marked, then the answer lit and its badge in
          },
        },
      };
    },
  });

  // ------------------------------------------------------------------ graph
  M.block('graph', {
    fields: {
      nodes: { type: 'json', required: true, help: '[{"id": 0, "x": 0.1, "y": 0.5}, ...] x and y from 0 to 1 inside the block; "label" optional; ids unique, no two at one point' },
      edges: { type: 'json', required: true, help: '[[0, 1, 100], ...] from, to, weight (or {"from", "to", "w"}); a weight is optional, a number when given; one edge per pair (per direction when directed)' },
      directed: { type: 'bool', help: 'arrowheads (default true)' },
      src: { type: 'text', help: 'node id flagged FROM (one of the nodes)' }, dst: { type: 'text', help: 'node id flagged TO (one of the nodes)' },
    },
    cues: ['route', 'clear', 'focus'],
    weight: { row: 1.3, column: 1.5 },
    build(c) {
      const { el, box, props: p, u, P } = c;
      const routes = c.cues.filter((x) => x.do === 'route');
      const strip = routes.length ? 92 * u : 0;
      const R = M.clamp(Math.min(box.w, box.h - strip) * 0.1, 36 * u, 54 * u);
      const pad = R + 40 * u;
      const gw = box.w - pad * 2, gh = box.h - strip - pad * 2;
      const svg = M.svg('svg', { width: box.w, height: box.h, viewBox: `0 0 ${box.w} ${box.h}` }, el);
      if (!Array.isArray(p.nodes) || !p.nodes.length) throw new Error('nodes: give [{"id": 0, "x": 0.1, "y": 0.5}, ...]');
      if (!Array.isArray(p.edges)) throw new Error('edges: give [[0, 1, 100], ...]');
      const nodes = Object.create(null);   // ids from film.json: "constructor" is a valid one
      p.nodes.forEach((nd, k) => {
        if (!nd || !isText(nd.id)) throw new Error(`nodes[${k}] needs an "id", a short text or a number (got ${JSON.stringify(nd && nd.id)})`);
        const id = String(nd.id);
        textOr(nd.label, `node ${id} "label"`);   // drawn in the node instead of the id
        if (id in nodes) throw new Error(`node ${id} is listed twice`);
        for (const a of ['x', 'y']) if (!(typeof nd[a] === 'number' && nd[a] >= 0 && nd[a] <= 1)) throw new Error(`node ${id}: "${a}" must be a number from 0 to 1 (got ${JSON.stringify(nd[a])})`);
        const same = Object.values(nodes).find((o) => o.x === nd.x && o.y === nd.y);
        if (same) throw new Error(`nodes ${same.id} and ${id} are both at x ${nd.x}, y ${nd.y}; move one`);
        nodes[id] = { ...nd, cx: pad + nd.x * gw, cy: pad + nd.y * gh };
      });
      const edges = p.edges.map((e) => {
        const r = Array.isArray(e) ? { from: String(e[0]), to: String(e[1]), w: e[2] } : { from: String(e && e.from), to: String(e && e.to), w: e && e.w };
        const w = r.w === undefined || r.w === null || r.w === '' ? null : M.data.num(r.w);   // a weight is optional, but a number when given
        if (w !== null && !isFinite(w)) throw new Error(`edge ${r.from} -> ${r.to}: weight ${JSON.stringify(r.w)} is not a number`);
        return { ...r, w };
      });
      const directed = p.directed !== false;
      const pairs = new Set();
      edges.forEach((e) => {
        const key = JSON.stringify(directed ? [e.from, e.to] : [e.from, e.to].sort());
        if (pairs.has(key)) throw new Error(`edge ${e.from} -> ${e.to} is listed twice${directed ? '' : ' (undirected: b -> a is the same edge)'}; a route could only ever take the first`);
        pairs.add(key);
      });
      const gE = M.svg('g', {}, svg), gN = M.svg('g', {}, svg), gP = M.svg('g', {}, svg);
      const ew = 6 * u, ahL = 22 * u;
      edges.forEach((e) => {
        const a = nodes[e.from], b = nodes[e.to];
        if (!a || !b) throw new Error(`edge ${e.from} -> ${e.to} names a node that is not in nodes`);
        if (a === b) throw new Error(`edge ${e.from} -> ${e.to} is a loop to itself, which the graph does not draw`);
        if (Math.hypot(b.cx - a.cx, b.cy - a.cy) < 1) throw new Error(`edge ${e.from} -> ${e.to}: the two nodes are at the same x and y; move one`);
        const twin = edges.some((f) => f.from === e.to && f.to === e.from);
        const dx = b.cx - a.cx, dy = b.cy - a.cy, L = Math.hypot(dx, dy), nx = -dy / L, ny = dx / L;
        const bend = twin ? 0.16 * L : 0;
        const ctl = { x: (a.cx + b.cx) / 2 + nx * bend, y: (a.cy + b.cy) / 2 + ny * bend };
        const trim = (from, to, d) => { const vx = to.x - from.cx, vy = to.y - from.cy, l = Math.hypot(vx, vy); return { x: from.cx + (vx / l) * d, y: from.cy + (vy / l) * d }; };
        const s = trim(a, ctl, R + 6 * u), t = trim(b, ctl, R + 6 * u + (directed ? ahL * 0.6 : 0));
        e.d = `M${s.x.toFixed(1)},${s.y.toFixed(1)} Q${ctl.x.toFixed(1)},${ctl.y.toFixed(1)} ${t.x.toFixed(1)},${t.y.toFixed(1)}`;
        const g = M.svg('g', { class: 'eg' }, gE);
        e.ln = M.svg('path', { class: 'ln', d: e.d, 'stroke-width': ew }, g);
        if (directed) {
          const ang = Math.atan2(t.y - ctl.y, t.x - ctl.x) * 180 / Math.PI;
          const tip = trim(b, ctl, R + 6 * u);
          e.ah = M.svg('path', { d: `M0,0 L${-ahL},${-ahL * 0.5} L${-ahL * 0.78},0 L${-ahL},${ahL * 0.5} Z`, fill: P.line2, transform: `translate(${tip.x.toFixed(1)},${tip.y.toFixed(1)}) rotate(${ang.toFixed(1)})` }, g);
        }
        if (e.w !== null) {
          const mx = 0.25 * s.x + 0.5 * ctl.x + 0.25 * t.x, my = 0.25 * s.y + 0.5 * ctl.y + 0.25 * t.y;
          const fs = 32 * u, txt = M.fmtNum(e.w), pw = M.textW(txt, `700 ${fs}px Inter`) + 30 * u, ph = 50 * u;
          e.pill = M.svg('g', { class: 'pill', transform: `translate(${mx.toFixed(1)},${my.toFixed(1)})` }, gP);
          M.svg('rect', { x: -pw / 2, y: -ph / 2, width: pw, height: ph, rx: ph / 2, 'stroke-width': 3 * u }, e.pill);
          const tx = M.svg('text', { 'text-anchor': 'middle', 'dominant-baseline': 'central', 'font-size': fs }, e.pill);
          tx.textContent = txt;
          e.pillRect = e.pill.firstChild;
          e.pillText = tx;
        }
      });
      Object.values(nodes).forEach((nd) => {
        const g = M.svg('g', { class: 'nd', transform: `translate(${nd.cx.toFixed(1)},${nd.cy.toFixed(1)})` }, gN);
        nd.halo = M.svg('circle', { r: R + 12 * u, fill: 'none', stroke: P.accent, 'stroke-width': 6 * u, opacity: 0 }, g);
        nd.body = M.svg('circle', { class: 'body', r: R, 'stroke-width': 4 * u }, g);
        const name = String(given(nd.label) ? nd.label : nd.id);
        const tx = M.svg('text', { 'text-anchor': 'middle', 'dominant-baseline': 'central', 'font-size': M.clamp(R * (name.length > 2 ? 0.52 : 0.8), TY.min * u, 44 * u) }, g);
        tx.textContent = name;
        nd.g = g;
      });
      const flags = [];
      [[p.src, 'FROM', 'accent', 'src'], [p.dst, 'TO', 'good', 'dst']].forEach(([id, word, tone, k]) => {
        if (id === undefined || id === null || id === '') return;
        if (!nodes[String(id)]) throw new Error(`"${k}" ${JSON.stringify(id)} is not a node (${Object.keys(nodes).join(', ')})`);
        const nd = nodes[String(id)], tc = toneOf(P, tone);
        const below = nd.cy + R + 44 * u < box.h - strip;
        // the outer group places the flag; the inner one is what moves (a tween's y would replace the translate)
        const at = M.svg('g', { transform: `translate(${nd.cx.toFixed(1)},${(below ? nd.cy + R + 34 * u : nd.cy - R - 34 * u).toFixed(1)})` }, svg);
        const g = M.svg('g', { class: 'flag' }, at);
        const tx = M.svg('text', { 'text-anchor': 'middle', 'dominant-baseline': 'central', 'font-size': 28 * u, fill: tc.ink }, g);
        tx.textContent = word;
        flags.push(g);
      });
      // route chips along the bottom: "0 → 1 → 3 = 700"
      const chipsBox = M.el('div', 'routes', el, { position: 'absolute', left: 0, right: 0, bottom: 0, height: strip + 'px', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 20 * u + 'px' });
      const token = M.svg('circle', { r: 15 * u, fill: P.accent, stroke: P.panel, 'stroke-width': 5 * u }, svg);
      M.init(token, { autoAlpha: 0, transformOrigin: '50% 50%' });   // set once, before any x/y, so seeking backwards cannot shift it
      const edgeOf = (a, b) => {
        const e = edges.find((x) => x.from === String(a) && x.to === String(b)) || (!directed && edges.find((x) => x.from === String(b) && x.to === String(a)));
        if (!e) throw new Error(`route: there is no edge ${a} -> ${b}`);
        return e;
      };
      let landed = 0, colored = new Set(), chipN = 0;
      const neutral = (t1) => {
        colored.forEach((e) => {
          M.to(e.ln, { stroke: P.line2, strokeWidth: ew, duration: 0.35 }, t1);
          if (e.ah) M.to(e.ah, { fill: P.line2, duration: 0.35 }, t1);
        });
        colored = new Set();
        Object.values(nodes).forEach((nd) => { if (nd.lit) { M.to(nd.body, { stroke: P.line2, duration: 0.35 }, t1); nd.lit = false; } });
      };
      return {
        enter(t0) {
          M.set(el, { autoAlpha: 1 }, t0);
          const ns = Object.values(nodes);
          M.fromTo(ns.map((x) => x.g), { autoAlpha: 0, scale: 0.3, transformOrigin: '50% 50%' }, { autoAlpha: 1, scale: 1, duration: 0.55, stagger: 0.09, ease: 'back.out(2.2)' }, t0);
          const te = t0 + 0.3 + 0.09 * ns.length;
          const st = Math.min(0.16, 1.2 / edges.length);
          edges.forEach((e, i) => {
            M.fromTo(e.ln, { drawSVG: '0%' }, { drawSVG: '100%', duration: 0.55, ease: 'power2.inOut' }, te + i * st);
            if (e.ah) M.fromTo(e.ah, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.15 }, te + i * st + 0.45);
            if (e.pill) M.fromTo(e.pill, { autoAlpha: 0, scale: 0.4, transformOrigin: '50% 50%' }, { autoAlpha: 1, scale: 1, duration: 0.4, ease: 'back.out(2.4)' }, te + i * st + 0.35);
          });
          landed = te + (edges.length - 1) * st + 0.8;
          if (flags.length) M.fromTo(flags, { autoAlpha: 0, y: 10 * u }, { autoAlpha: 1, y: 0, duration: 0.4, stagger: 0.12 }, landed - 0.3);
          return Math.max(landed, flags.length ? landed + 0.1 + 0.12 * (flags.length - 1) : 0);   // nodes, edges and flags in
        },
        cues: {
          route: (cue, t1) => {
            t1 = Math.max(t1, landed);
            const path = (cue.path || []).map(String);
            if (path.length < 2) throw new Error('route needs "path": [from, ..., to]');
            const own = textOr(cue.total, '"total"'), note = textOr(cue.note, '"note"');   // the chip's sum and remark
            const tc = toneOf(P, cue.tone);
            neutral(t1 - 0.45);   // the last route fades out before this one starts colouring
            const hop = given(cue.hop) ? M.data.num(cue.hop) : 0.5;
            if (!(hop >= 0.25 && hop <= 1.2)) throw new Error(`"hop" ${JSON.stringify(cue.hop)} is the seconds each hop takes, a number from 0.25 to 1.2`);
            let total = 0;
            // an undirected edge may be stored b -> a; then the hop runs its path backwards
            const along = (e, a) => (e.from === a ? { start: 0, end: 1 } : { start: 1, end: 0 });
            const e0 = edgeOf(path[0], path[1]), p0 = e0.ln.getPointAtLength(along(e0, path[0]).start * e0.ln.getTotalLength());
            M.set(token, { fill: tc.fill, x: p0.x, y: p0.y }, t1);   // appear where the first hop starts
            M.fromTo(token, { autoAlpha: 0, scale: 0.4 }, { autoAlpha: 1, scale: 1, duration: 0.25 }, t1);
            path.slice(1).forEach((b, i) => {
              const e = edgeOf(path[i], b);
              total += e.w ?? 0;
              const ti = t1 + 0.1 + i * hop;
              M.to(e.ln, { stroke: tc.fill, strokeWidth: ew * 1.9, duration: 0.3 }, ti);
              if (e.ah) M.to(e.ah, { fill: tc.fill, duration: 0.3 }, ti);
              colored.add(e);
              M.to(token, { motionPath: { path: e.ln, align: e.ln, alignOrigin: [0.5, 0.5], ...along(e, path[i]) }, duration: hop * 0.94, ease: 'power1.inOut' }, ti);
              const nd = nodes[b];
              M.to(nd.body, { stroke: tc.fill, duration: 0.25 }, ti + hop * 0.85);
              nd.lit = true;
              if (e.pill) M.fromTo(e.pill, { scale: 1 }, { scale: 1.18, duration: 0.18, yoyo: true, repeat: 1 }, ti + hop * 0.4);
            });
            const a0 = nodes[path[0]];
            M.to(a0.body, { stroke: tc.fill, duration: 0.25 }, t1);
            a0.lit = true;
            const tEnd = t1 + 0.1 + (path.length - 1) * hop;
            M.to(token, { autoAlpha: 0, scale: 0.4, duration: 0.3 }, tEnd + 0.35);
            if (cue.chip !== false) {
              const ch = M.el('div', 'chip num', chipsBox, { fontSize: 32 * u + 'px', borderColor: tc.fill, color: tc.ink });
              ch.textContent = `${path.join(' → ')} = ${own ? cue.total : M.fmtNum(total)}${note ? '  ' + cue.note : ''}`;
              M.init(ch, { autoAlpha: 0 });
              M.fromTo(ch, { autoAlpha: 0, y: 20 * u, scale: 0.8 }, { autoAlpha: 1, y: 0, scale: 1, duration: 0.45, ease: 'back.out(2)' }, tEnd);
              chipN++;
            }
            return { at: t1, end: tEnd + (cue.chip !== false ? 0.45 : 0.25) };   // the stage checks the route lands before the block leaves
          },
          clear: (cue, t1) => {
            if (!colored.size && !Object.values(nodes).some((nd) => nd.lit)) throw new Error('nothing is lit to clear; a "clear" follows a "route"');
            t1 = Math.max(t1, landed);
            neutral(t1);
            return { at: t1, end: t1 + 0.35 };   // every lit edge and node back to grey
          },
          focus: (cue, t1) => {
            t1 = Math.max(t1, landed);
            const tc = toneOf(P, cue.tone);
            if (!Array.isArray(cue.nodes) || !cue.nodes.length) throw new Error('focus needs "nodes": [id, ...], at least one');
            const hold = given(cue.hold) ? M.data.num(cue.hold) : 2;   // the halo fades after hold seconds
            if (!(hold >= 0.4 && Number.isFinite(hold))) throw new Error(`"hold" ${JSON.stringify(cue.hold)} is the seconds the halo stays, a number of 0.4 or more`);
            cue.nodes.map(String).forEach((id, i) => {
              const nd = nodes[id];
              if (!nd) throw new Error(`focus: no node ${id}`);
              M.set(nd.halo, { attr: { stroke: tc.fill } }, t1);
              M.fromTo(nd.halo, { opacity: 0, scale: 0.7, transformOrigin: '50% 50%' }, { opacity: 1, scale: 1, duration: 0.4, ease: 'back.out(2)' }, t1 + i * 0.1);
              M.to(nd.halo, { opacity: 0, duration: 0.4 }, t1 + hold + i * 0.1);
            });
            const last = (cue.nodes.length - 1) * 0.1;
            return { at: t1, end: t1 + 0.4 + last, off: t1 + hold + 0.4 + last };   // every halo in; every halo held and faded
          },
        },
      };
    },
  });

  // ------------------------------------------------------------------ code
  const KW = new Set(('auto break case catch class const continue default delete do else enum explicit for friend if inline namespace new ' +
    'operator private protected public return sizeof static struct switch template this throw try typedef typename using virtual while ' +
    'def elif except finally from import in is lambda not or and pass raise with yield let var function of extends implements interface package super').split(' '));
  const TYPES = new Set('int long short char bool float double void string vector map set unordered_map unordered_set pair queue deque stack priority_queue size_t array list dict tuple String Integer boolean true false nullptr None True False null'.split(' '));
  M.block('code', {
    fields: {
      code: { type: 'code', required: true, help: 'the code, as one string with \\n or a list of lines' },
      title: { type: 'text', help: 'the file name in the header, e.g. "solution.cpp"' },
    },
    cues: ['focus'],
    weight: { row: 1.4, column: 1.5 },
    build(c) {
      const { el, box, props: p, u, P } = c;
      // one string with \n, or a list of lines; at least one line with something on it
      if (typeof p.code !== 'string' && !Array.isArray(p.code)) throw new Error(`code is ${JSON.stringify(p.code)}; give the code as one string with \\n or a list of lines`);
      const src = Array.isArray(p.code) ? p.code : p.code.split('\n');
      const odd = src.findIndex((x) => typeof x !== 'string');
      if (odd >= 0) throw new Error(`code line ${odd + 1} is ${JSON.stringify(src[odd])}; each line is a text`);
      if (!src.some((x) => x.trim() !== '')) throw new Error('code has no lines with code on them');
      const panel = M.el('div', 'panel card', el);
      const head = M.el('div', 'head', panel);
      M.el('i', '', head); M.el('i', '', head); M.el('i', '', head);
      M.el('span', '', head, null, p.title || 'solution.cpp');
      const body = M.el('div', 'lines', panel);
      const ink = { kw: P.violetInk, ty: P.coolInk, nu: P.warmInk, cm: P.dim, st: P.goodInk };
      el.style.setProperty('--codebar', M.tint(P.accent, P.panel, P.violetInk, 0.14));
      const bar = M.el('div', 'bar', body);
      const lns = src.map((line, i) => {
        const d = M.el('div', 'ln', body);
        M.el('span', 'no', d, null, String(i + 1));
        const re = /(\/\/.*$|#.*$|"[^"]*"|'[^']*'|\b\d+(?:\.\d+)?\b|\b[A-Za-z_]\w*\b|\s+|.)/g;
        let m;
        while ((m = re.exec(line)) !== null) {
          const tok = m[1];
          const kind = /^(\/\/|#)/.test(tok) ? 'cm' : /^["']/.test(tok) ? 'st' : /^\d/.test(tok) ? 'nu' : KW.has(tok) ? 'kw' : TYPES.has(tok) ? 'ty' : null;
          const s = M.el('span', '', d, kind ? { color: ink[kind] } : null);
          s.textContent = tok;
        }
        return d;
      });
      // size: the code font that fits every line in the panel (never under the floor)
      const availH = box.h - 76 * u - 40 * u, availW = box.w - 60 * u;
      const longest = src.reduce((a, b) => (b.length > a.length ? b : a), '');
      let fs = Math.min(TY.code * u * 1.1, availH / (src.length * 1.42));
      while (fs > TY.min * u && M.textW('000 ' + longest, `400 ${fs}px "JetBrains Mono"`) + 2.2 * fs > availW) fs -= 1;
      if (fs < TY.min * u) { fs = TY.min * u; M.warnings.push(`${c.where}: the code needs more room than the block has; it is drawn at the ${TY.min} px floor`); }
      body.style.fontSize = fs + 'px';
      body.style.lineHeight = '1.42';
      const lh = fs * 1.42;
      Object.assign(bar.style, { top: 18 * u + 'px', height: lh + 'px' });
      M.init(bar, { autoAlpha: 0 });
      M.init(lns, { autoAlpha: 0 });
      let landed = 0, barOn = false, focused = null;
      return {
        enter(t0) {
          M.fromTo(el, { autoAlpha: 0, y: 30 * u }, { autoAlpha: 1, y: 0, duration: 0.6, ease: 'lift' }, t0);
          const st = Math.min(0.07, 1.0 / lns.length);
          M.fromTo(lns, { autoAlpha: 0, x: -14 * u }, { autoAlpha: 1, x: 0, duration: 0.35, stagger: st, ease: 'power2.out' }, t0 + 0.25);
          landed = Math.max(t0 + 0.6, t0 + 0.25 + st * (lns.length - 1) + 0.35);
          return landed;   // the panel and every line in
        },
        cues: {
          focus: (cue, t1) => {
            t1 = Math.max(t1, landed);
            // whole line numbers of the code, counting from 1 ("lines": [5, 7] marks 5 to 7)
            const raw = cue.lines !== undefined ? [].concat(cue.lines) : [cue.line ?? 1];
            const ls = raw.map((x) => (typeof x === 'string' && x.trim() !== '' ? Number(x) : x));
            if (!ls.length) throw new Error('give "line": 4 or "lines": [5, 7]');
            const k = ls.findIndex((x) => !Number.isInteger(x) || x < 1 || x > src.length);
            if (k >= 0) throw new Error(`line ${JSON.stringify(raw[k])} is not a line of the code (1 to ${src.length})`);
            const a = Math.min(...ls) - 1, b = Math.max(...ls);
            if (focused === `${a}-${b}`) throw new Error(`line${b - a > 1 ? 's ' + (a + 1) + ' to ' + b + ' are' : ' ' + b + ' is'} already in focus`);
            focused = `${a}-${b}`;
            const top = 18 * u + a * lh, h = (b - a) * lh;
            const first = !barOn;
            if (first) { M.set(bar, { top, height: h }, t1); M.fromTo(bar, { autoAlpha: 0, scaleX: 0.3, transformOrigin: '0 50%' }, { autoAlpha: 1, scaleX: 1, duration: 0.35 }, t1); barOn = true; }
            else M.to(bar, { top, height: h, duration: 0.45, ease: 'power3.inOut' }, t1);
            return { at: t1, end: t1 + (first ? 0.35 : 0.45) };   // the bar on its lines
          },
        },
      };
    },
  });

  // ------------------------------------------------------------------ array
  M.block('array', {
    fields: {
      values: { type: 'list', required: true, help: 'the cells, at least one, each a number or a short text ("" for an empty cell), e.g. [2, 7, 11, 15]' },
      name: { type: 'text', help: 'shown before the cells, e.g. "nums"' },
      index: { type: 'bool', help: 'index numbers under the cells (default true)' },
    },
    cues: ['point', 'range', 'set', 'clear'],
    weight: { row: 1, column: 0.9 },
    build(c) {
      const { el, box, props: p, u, P } = c;
      if (!Array.isArray(p.values) || !p.values.length) throw new Error('values: give at least one cell, e.g. [2, 7, 11, 15]');
      // what a cell shows: a number or a text ("" leaves it empty); an object, a list, null or true would show as
      // "[object Object]", "null" or "true"
      const shows = (v) => typeof v === 'string' || (typeof v === 'number' && Number.isFinite(v));
      p.values.forEach((v, i) => { if (!shows(v)) throw new Error(`values[${i}] is ${JSON.stringify(v)}; a cell holds a number or a text ("" for an empty cell)`); });
      const n = p.values.length;
      const nameW = p.name ? M.textW(p.name + ' =', `700 ${40 * u}px Inter`) + 24 * u : 0;
      const cw = Math.min(150 * u, (box.w - nameW) / n);
      const fs = M.clamp(cw * 0.4, TY.min * u, 54 * u);
      const top = box.h / 2 - cw / 2;
      if (p.name) M.el('div', '', el, { position: 'absolute', left: 0, top: top + cw / 2 - 26 * u + 'px', fontSize: 40 * u + 'px', fontWeight: 700, color: P.muted }, p.name + ' =');
      const row = M.el('div', 'cells', el, { left: nameW + (box.w - nameW - cw * n) / 2 + 'px', top: top + 'px' });
      const cells = p.values.map((v, i) => {
        const ce = M.el('div', 'cell', row, { width: cw + 'px', height: cw + 'px', fontSize: fs + 'px' });
        const tv = M.el('span', '', ce, null, String(v));
        if (p.index !== false) M.el('span', 'ix', ce, { fontSize: Math.max(TY.min * u, fs * 0.6) + 'px' }, String(i));
        return { ce, tv };
      });
      const x0 = nameW + (box.w - nameW - cw * n) / 2;
      // a cell index: a whole number from 0 to n-1 ("2" reads as 2)
      const cell = (v, what) => {
        const k = typeof v === 'number' ? v : typeof v === 'string' && v.trim() !== '' ? Number(v) : NaN;
        if (!Number.isInteger(k) || k < 0 || k >= n) throw new Error(`${what} ${JSON.stringify(v)} is not a cell index (0 to ${n - 1})`);
        return k;
      };
      const ptrs = Object.create(null);   // pointer names come from film.json
      const ptr = (name, tone) => {
        if (ptrs[name]) return ptrs[name];
        const tc = toneOf(P, tone);
        const d = M.el('div', 'ptr', el, { top: top - 100 * u + 'px', width: cw + 'px', color: tc.ink, fontSize: 36 * u + 'px' });
        d.innerHTML = `<span>${M.esc(name)}</span><span style="font-size:${28 * u}px">▼</span>`;
        M.init(d, { autoAlpha: 0 });
        return (ptrs[name] = { d, at: null });
      };
      M.init(cells.map((x) => x.ce), { autoAlpha: 0 });
      let landed = 0;
      const tint = p.values.map(() => null);   // each cell's range colour, so a range that changes nothing is caught
      return {
        enter(t0) {
          M.set(el, { autoAlpha: 1 }, t0);
          M.fromTo(cells.map((x) => x.ce), { autoAlpha: 0, y: 30 * u }, { autoAlpha: 1, y: 0, duration: 0.45, stagger: Math.min(0.08, 0.8 / n), ease: 'back.out(1.8)' }, t0 + 0.1);
          landed = t0 + 0.6 + Math.min(0.08, 0.8 / n) * n;
          return landed;   // every cell in
        },
        cues: {
          point: (cue, t1) => {
            t1 = Math.max(t1, landed);
            const ix = cell(cue.index, 'index');
            const name = given(cue.name) ? cue.name : 'i';   // drawn over the cell, and the key later cues move it by
            if (!isText(name)) throw new Error(`pointer "name" is ${JSON.stringify(cue.name)}; it takes a short text, e.g. "lo"`);
            const pt = ptr(String(name), cue.tone);
            if (pt.at === ix) throw new Error(`pointer "${name}" is already at index ${ix}`);
            const x = x0 + ix * cw;
            if (pt.at === null) { M.set(pt.d, { left: x }, t1); M.fromTo(pt.d, { autoAlpha: 0, y: -20 * u }, { autoAlpha: 1, y: 0, duration: 0.4, ease: 'back.out(2)' }, t1); }
            else M.to(pt.d, { left: x, duration: 0.45, ease: 'power3.inOut' }, t1);
            const end = t1 + (pt.at === null ? 0.4 : 0.45);   // the pointer in, or moved
            pt.at = ix;
            return { at: t1, end };
          },
          range: (cue, t1) => {
            const tc = toneOf(P, cue.tone), t = Math.max(t1, landed);
            const a = cell(cue.from, 'from'), z = cell(cue.to ?? cue.from, 'to');
            if (z < a) throw new Error(`from ${a} is after to ${z}`);
            if (tint.slice(a, z + 1).every((x) => x === tc.fill)) throw new Error(`cells ${a} to ${z} are already tinted ${cue.tone || 'accent'}; a range must change some cell (another range or tone, or a "clear" first)`);
            for (let i = a; i <= z; i++) { M.to(cells[i].ce, { backgroundColor: M.tint(tc.fill, P.panel, P.text, 0.3), borderColor: tc.fill, duration: 0.3 }, t + (i - a) * 0.05); tint[i] = tc.fill; }
            return { at: t, end: t + 0.3 + (z - a) * 0.05 };
          },
          set: (cue, t1) => {
            if (cue.value === undefined || cue.value === null) throw new Error('set needs "value" (what the cell now holds)');
            if (!shows(cue.value)) throw new Error(`"value" ${JSON.stringify(cue.value)} is not something a cell can show; give a number or a text`);
            const ce = cells[cell(cue.index, 'index')], t = Math.max(t1, landed);
            M.set(ce.tv, { textContent: String(cue.value) }, t);
            M.fromTo(ce.ce, { scale: 1.2 }, { scale: 1, duration: 0.4, ease: 'back.out(2)' }, t);
            return { at: t, end: t + 0.4 };
          },
          clear: (cue, t1) => {
            if (!tint.some((x) => x !== null)) throw new Error('no range is tinted to clear; a "clear" follows a "range"');
            const t = Math.max(t1, landed);
            cells.forEach((x) => M.to(x.ce, { backgroundColor: P.panel, borderColor: P.line2, duration: 0.3 }, t));
            tint.fill(null);
            return { at: t, end: t + 0.3 };
          },
        },
      };
    },
  });
})();
