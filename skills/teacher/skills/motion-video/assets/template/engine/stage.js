// engine/stage.js: turns film.json into the film. The backdrop (light that shifts with each shot), the persistent
// frame (brand, tag, progress), captions with the spoken word lit, and the shot manager: each shot lays out its
// blocks, enters them on its line, plays their cues, and hands any block with the same id on to the next shot
// (the block glides to its new place instead of leaving and coming back).
(function () {
  const M = window.M;
  if (!M || !M.tl) return;   // core.js stopped the boot (BOOT_ERROR is set)
  M.blocks = Object.create(null);   // keyed by names from film.json, so no inherited keys ("constructor")
  /** Register a block type. def = {fields, weight: {row, column}, build(ctx) -> {enter?, exit?, cues?}}. */
  M.block = (type, def) => { M.blocks[type] = def; };
  const COMMON = new Set(['type', 'id', 'cues', 'weight', 'note']);

  let stage, bg, bgx, world, chromeEl, progFill, grain, shotsRt = [];

  // ------------------------------------------------------------------ film.json -> shots
  function normalize(film) {
    if (!film || !Array.isArray(film.shots) || !film.shots.length) throw new Error('film.json needs "shots": [{"at": "<line id>", "blocks": [...]}]');
    const seen = Object.create(null);   // block ids from film.json: "constructor" is a valid id
    return film.shots.map((s, i) => {
      const where = `film.json shots[${i}]`;
      if (!s.at) throw new Error(`${where}: "at" names the line the shot starts on`);
      const prev = i && film.shots[i - 1].at;   // shots run in the order their lines are spoken, one per line at most
      if (prev && M.line(s.at, where).start <= M.line(prev, where).start + 0.01) throw new Error(`${where}: starts on "${s.at}", which is not after the shot before it ("${prev}"); list shots in spoken order, at most one per line`);
      M.line(s.at, where);
      // the first shot is on screen from 0 s, so it names the first line: a later one would still show it from the start
      if (i === 0 && s.at !== M.lines[0].id) throw new Error(`${where}: the first shot starts the film, so "at" is the first line ("${M.lines[0].id}"), not "${s.at}"; open on the first line (a title shot, say) and start this shot on "${s.at}"`);
      let blocks = s.blocks;
      if (!blocks) {   // shorthand: a shot that is one block
        const { at, layout, split, light, ...b } = s;
        blocks = [b];
      }
      if (!Array.isArray(blocks) || !blocks.length) throw new Error(`${where}: "blocks" must list at least one block`);
      if (blocks.length > 3) throw new Error(`${where}: ${blocks.length} blocks; a shot holds one to three (move the rest into a shot of their own)`);
      if (s.split !== undefined && !(Array.isArray(s.split) && s.split.length === blocks.length && s.split.every((x) => typeof x === 'number' && isFinite(x) && x > 0)))
        throw new Error(`${where}: "split" needs one share above 0 per block (${blocks.length} here), e.g. [1.2, 1]`);
      const unset = (v) => v === undefined || v === null || v === '';
      if (!unset(s.layout) && s.layout !== 'row' && s.layout !== 'column') throw new Error(`${where}: "layout" is ${JSON.stringify(s.layout)}; it takes row or column (leave it out to follow the frame's shape)`);
      if (!unset(s.light) && !LOOK.HUES.includes(s.light)) throw new Error(`${where}: "light" is ${JSON.stringify(s.light)}; it takes ${LOOK.HUES.join(', ')}`);
      return {
        ...s, i, where,
        blocks: blocks.map((b, j) => {
          // an id is a name, and a number is one too: "id": 0 is the block "0", not a block with no id (the checks
          // below read a missing id as falsy). Anything else would carry or match the wrong block
          if (typeof b.id === 'number' && isFinite(b.id)) b = { ...b, id: String(b.id) };
          else if (b.id === '' || b.id === null) { const { id, ...rest } = b; b = rest; }
          else if (b.id !== undefined && (typeof b.id !== 'string' || !b.id.trim())) throw new Error(`${where}.blocks[${j}]: "id" is ${JSON.stringify(b.id)}; it takes a name, e.g. "graph"`);
          // a block carried on from an earlier shot needs only its id (and any new cues); the rest is inherited
          const first = b.id && seen[b.id];
          if (first && b.type && b.type !== first.type) throw new Error(`${where}.blocks[${j}]: "${b.id}" is a ${first.type} where it first appears; a carried block keeps its type (give the ${b.type} an id of its own)`);
          if (first) {
            const set = Object.keys(b).filter((k) => !['id', 'type', 'cues', 'weight'].includes(k) && JSON.stringify(b[k]) !== JSON.stringify(first[k]));
            if (set.length) M.warnings.push(`${where}.blocks[${j}] (${b.id}): ${set.join(', ')} ${set.length > 1 ? 'are' : 'is'} set where the block first appears; a carried block only takes new cues here`);
          }
          const full = first ? { ...first, ...b, type: b.type || first.type, cues: b.cues || [] } : b;
          if (b.id && !first) { const { cues, ...rest } = b; seen[b.id] = rest; }
          return { ...full, where: `${where}.blocks[${j}] (${full.type || '?'}${b.id ? ' ' + b.id : ''})` };
        }),
      };
    });
  }

  function validate(b) {
    const def = M.blocks[b.type];
    if (!def) throw new Error(`${b.where}: unknown block type "${b.type}". Blocks: ${Object.keys(M.blocks).join(', ')}`);
    const fields = def.fields || {};
    for (const [k, f] of Object.entries(fields)) {
      if (f.required && (b[k] === undefined || b[k] === null || b[k] === '')) M.errors.push(`${b.where}: "${k}" is required (${f.help || f.type})`);
      if (f.type === 'enum' && f.options && b[k] !== undefined && b[k] !== null && b[k] !== '' && !f.options.includes(b[k])) M.errors.push(`${b.where}: "${k}" is ${JSON.stringify(b[k])}; it takes ${f.options.join(', ')}`);
      if (f.type === 'bool' && b[k] !== undefined && b[k] !== null && typeof b[k] !== 'boolean') M.errors.push(`${b.where}: "${k}" is ${JSON.stringify(b[k])}; it takes true or false (no quotes)`);
      // text is drawn as written: an object or a list would show as "[object Object]" or "a,b", and a required one
      // that is only spaces shows nothing
      if (f.type === 'text' && b[k] !== undefined && b[k] !== null && b[k] !== '') {
        if (typeof b[k] !== 'string' && !(typeof b[k] === 'number' && isFinite(b[k]))) M.errors.push(`${b.where}: "${k}" is ${JSON.stringify(b[k])}; it takes text`);
        else if (f.required && String(b[k]).trim() === '') M.errors.push(`${b.where}: "${k}" is blank; it is required (${f.help || f.type})`);
        else b[k] = String(b[k]);   // a number is drawn as written, so 0 is text like any other, not "left out"
      }
      if (f.type === 'list' && b[k] !== undefined && b[k] !== null && !Array.isArray(b[k])) M.errors.push(`${b.where}: "${k}" is ${JSON.stringify(b[k])}; it takes a list, e.g. ["a", "b"]`);
    }
    for (const k of Object.keys(b)) {
      if (k !== 'where' && !COMMON.has(k) && !(k in fields)) M.warnings.push(`${b.where}: "${k}" is not a field of ${b.type} (fields: ${Object.keys(fields).join(', ')})`);
    }
    if (b.weight !== undefined && !(typeof b.weight === 'number' && isFinite(b.weight) && b.weight > 0)) M.errors.push(`${b.where}: "weight" must be a number above 0`);
    for (const c of b.cues || []) {
      if (!c.do || !(def.cues || []).includes(c.do)) M.errors.push(`${b.where}: cue "${c.do}" is not one ${b.type} knows (${(def.cues || []).join(', ') || 'none'})`);
      if (!c.at) M.errors.push(`${b.where}: cue "${c.do}" needs "at" (a line, like "q3" or "q3:phrase")`);
    }
    return def;
  }

  /** Boxes for a shot's blocks inside the content area: side by side on a wide frame, stacked on tall and square
   *  ones (shot.layout "row" or "column" overrides), sized by shot.split or each block's weight. */
  M.layout = (shot, C) => {
    const n = shot.blocks.length;
    const dir = shot.layout || (M.shape === 'wide' ? 'row' : 'column');
    const gap = (dir === 'row' ? 72 : 44) * M.u;
    const ws = shot.split && shot.split.length === n ? shot.split
      : shot.blocks.map((b) => +b.weight || ((M.blocks[b.type] || {}).weight || {})[dir] || 1);
    const sum = ws.reduce((a, b) => a + b, 0);
    const span = (dir === 'row' ? C.w : C.h) - gap * (n - 1);
    let p = dir === 'row' ? C.x : C.y;
    return ws.map((w) => {
      const len = (span * w) / sum;
      const box = dir === 'row' ? { x: p, y: C.y, w: len, h: C.h } : { x: C.x, y: p, w: C.w, h: len };
      p += len + gap;
      return box;
    });
  };

  // ------------------------------------------------------------------ build
  M.build = (film) => {
    M.reset();
    M.film = film;
    let style = film.style === undefined || film.style === null ? {} : film.style;
    // "style": "ink" would read every setting as missing and quietly build the default look
    if (typeof style !== 'object' || Array.isArray(style)) throw new Error(`film.json style is ${JSON.stringify(film.style)}; it is an object of settings, e.g. "style": { "look": "ink", "brand": "Kai Mori" }`);
    for (const k of ['captions', 'karaoke']) {
      if (style[k] !== undefined && style[k] !== null && typeof style[k] !== 'boolean') throw new Error(`film.json style.${k} is ${JSON.stringify(style[k])}; it takes true or false (no quotes)`);
    }
    // the frame's labels are drawn as text: an object or a list would show as [object Object] or a comma list
    const said = { brand: 'Kai Mori', mark: 'KM', tag: 'LC 787 · daily' };
    for (const k of Object.keys(said)) {
      const v = style[k];
      if (v !== undefined && v !== null && v !== false && typeof v !== 'string' && !(typeof v === 'number' && Number.isFinite(v))) {
        throw new Error(`film.json style.${k} is ${JSON.stringify(v)}; it takes text, e.g. "${k}": "${said[k]}"${k === 'brand' ? ' (or false: no brand row)' : ''}`);
      }
    }
    // a number is shown as written, 0 included (the frame tests these labels for presence by truthiness)
    const num = Object.keys(said).filter((k) => typeof style[k] === 'number');
    if (num.length) style = Object.assign({}, style, Object.fromEntries(num.map((k) => [k, String(style[k])])));
    M.style = style;
    M.P = LOOK.palette(style);
    M.dark = M.P.tone === 'dark';
    M.G = M.geometry(style.captions !== false);
    stage = document.getElementById('stage');
    stage.innerHTML = '';
    Object.assign(stage.style, { width: M.W + 'px', height: M.H + 'px' });
    stage.dataset.tone = M.P.tone;
    stage.dataset.shape = M.shape;
    bg = M.el('canvas', 'bg', stage);
    bg.width = Math.round(M.W / 2); bg.height = Math.round(M.H / 2);
    bgx = bg.getContext('2d');
    grain = makeGrain(bg.width, bg.height);
    world = M.el('div', 'world', stage);
    M.world = world;
    const shots = normalize(film);
    shots.forEach((s) => s.blocks.forEach(validate));
    if (M.errors.length) throw new Error(M.errors.join('\n'));
    // each shot's start and the colour of its light, then make every ink hold 4.6:1 on the lit backdrop
    shotsRt = shots.map((s, i) => ({
      t0: i === 0 ? 0 : M.line(s.at).start,
      light: s.light ? M.P[M.hue(s.light)] : M.P.lights[(i + 1) % M.P.lights.length],
    }));
    guardInks();
    const P = M.P;
    const vars = { '--u': M.u, '--serif': LOOK.TYPE.serif, '--sans': LOOK.TYPE.sans, '--mono': LOOK.TYPE.mono };
    for (const k of ['bg', 'bg2', 'deep', 'panel', 'panel2', 'line', 'line2', 'text', 'muted', 'dim', 'shadow', ...LOOK.HUES.flatMap((h) => [h, h + 'Ink', 'on' + h[0].toUpperCase() + h.slice(1)])])
      vars['--' + k] = P[k];
    // a highlighter mark behind text: the strongest accent tint that keeps body text at 4.7:1 on it
    vars['--mark'] = M.tint(P.accent, P.bg, P.text, 0.34);
    vars['--markp'] = M.tint(P.accent, P.panel, P.text, 0.34);
    for (const [k, v] of Object.entries(vars)) stage.style.setProperty(k, v);
    buildChrome(style);
    buildShots(shots);
    if (style.captions !== false) buildCaptions(style);
    if (M.errors.length) throw new Error(M.errors.join('\n'));
    M.tl.set({}, {}, M.TOTAL);
    if (M.tl.duration() > M.TOTAL + 0.001) M.warnings.push(`timeline runs ${M.tl.duration().toFixed(2)} s, past the voice (${M.TOTAL.toFixed(2)} s)`);
  };

  // ------------------------------------------------------------------ shots
  function buildShots(shots) {
    const u = M.u;
    shots.forEach((s, i) => { s.t0 = shotsRt[i].t0; s.t1 = i + 1 < shots.length ? shotsRt[i + 1].t0 : M.TOTAL; });
    // which shots each block id appears in (a block carried across shots must appear in consecutive ones)
    const span = Object.create(null);
    shots.forEach((s, i) => s.blocks.forEach((b) => {
      if (!b.id) return;
      const sp = span[b.id];
      if (sp && sp.last !== i - 1) M.errors.push(`${b.where}: block id "${b.id}" reappears after a gap; a block is carried only into the very next shot`);
      span[b.id] = { first: sp ? sp.first : i, last: i };
    }));
    // every cue a block gets in any of its shots, so it can plan for them when it is built (room for route
    // chips, whether a countdown is placed by hand)
    const cuesOf = Object.create(null);
    shots.forEach((s) => s.blocks.forEach((b) => { if (b.id) (cuesOf[b.id] = cuesOf[b.id] || []).push(...(b.cues || [])); }));
    const live = Object.create(null);
    shots.forEach((s, i) => {
      const boxes = M.layout(s, M.G.content);
      const tIn = i === 0 ? 0.12 : s.t0 + 0.04;
      s.blocks.forEach((b, j) => {
        const box = boxes[j];
        let inst = b.id && live[b.id];
        // the block leaves at the end of its last shot (a carried block, the last shot it is in)
        const lastShot = b.id ? shots[span[b.id].last] : s;
        const leaves = lastShot.t1 < M.TOTAL - 0.01 ? lastShot.t1 - 0.3 : M.TOTAL;
        const fin = (x) => typeof x === 'number' && Number.isFinite(x);
        if (inst) {
          // carried over: glide to the new box, keep everything already on it
          const sc = Math.min(box.w / inst.box.w, box.h / inst.box.h);
          if (sc < 0.85) M.warnings.push(`${b.where}: "${b.id}" is carried into a box ${Math.round(sc * 100)}% of its first one, so all its text shrinks with it; give it the same share (split) in every shot it is in`);
          const x = box.x + (box.w - inst.box.w * sc) / 2 - inst.box.x, y = box.y + (box.h - inst.box.h * sc) / 2 - inst.box.y;
          if (Math.abs(x - inst.pos.x) > 0.5 || Math.abs(y - inst.pos.y) > 0.5 || Math.abs(sc - inst.pos.s) > 0.002) {
            M.to(inst.el, { x, y, scale: sc, duration: 0.75, ease: 'power3.inOut' }, s.t0 - 0.12);
            M.event(s.t0, `move ${b.id}`);
          }
          inst.pos = { x, y, s: sc };
          if (inst.api.onShot) inst.api.onShot(b, s, tIn);
        } else {
          const def = M.blocks[b.type];
          const el = M.el('div', `blk blk-${b.type}`, world, { left: box.x + 'px', top: box.y + 'px', width: box.w + 'px', height: box.h + 'px' });
          el.dataset.k = b.id || `${b.type}${i}.${j}`;
          el.dataset.block = b.type;
          M.init(el, { autoAlpha: 0, transformOrigin: '0 0' });
          const ctx = {
            M, P: M.P, u, el, box: { w: box.w, h: box.h }, props: b, shot: s, tIn: tIn + j * 0.12, leaves, where: b.where,
            cues: b.id ? cuesOf[b.id] : (b.cues || []),
            time: (ref) => M.time(ref, b.where), value: (ref) => M.data.value(ref, b.where), rows: (spec) => M.data.rows(spec, b.where),
            /** When the voice says `phrase` during this shot (the first line that has it), else `fallback`. */
            spoken: (phrase, fallback) => {
              const w = String(phrase).replace(/[*`]/g, '').toLowerCase().trim();
              for (const l of M.lines) {
                if (l.start < s.t0 - 0.01 || l.start >= s.t1 - 0.01) continue;
                if (w && l.say.toLowerCase().includes(w)) return l.at(w);
              }
              return fallback;
            },
          };
          let api;
          try { api = def.build(ctx) || {}; } catch (e) { M.errors.push(e.message.startsWith(b.where) ? e.message : `${b.where}: ${e.message}`); return; }   // data errors already name the block
          inst = { el, box, pos: { x: 0, y: 0, s: 1 }, api, def, ctx };
          // enter() returns when its entrance has landed (the last label, value or row in): it must land before
          // the block leaves, or the shot hands over while the block is still arriving
          let ready = ctx.tIn + 0.7;
          try {
            if (api.enter) { ready = api.enter(ctx.tIn); if (!fin(ready)) throw new Error(`${b.type}'s enter() must return when its entrance lands, in seconds (it returned ${JSON.stringify(ready)}); see "Adding a block" in the guide`); }
            else M.fromTo(el, { autoAlpha: 0, y: 30 * u }, { autoAlpha: 1, y: 0, duration: 0.7, ease: 'lift' }, ctx.tIn);
            if (ready > leaves + 0.01) throw new Error(`it takes until ${ready.toFixed(2)} s to enter (from ${ctx.tIn.toFixed(2)} s), but it leaves at ${leaves.toFixed(2)} s; give the shot more time (a longer line, or more lines), carry the block (same id) into the next shot, or use a lighter block`);
          } catch (e) { M.errors.push(e.message.startsWith(b.where) ? e.message : `${b.where}: ${e.message}`); return; }
          M.event(ctx.tIn, `enter ${el.dataset.k}`, ready);
          if (b.id) live[b.id] = inst;
        }
        // a cue lands in the shot that lists it (a carried block takes the cues of each of its shots), and cues run
        // in spoken order whatever their order in film.json: handlers keep state (a route clears the one before).
        // One that waits for its block to land must still start before the block leaves.
        const timed = (b.cues || []).map((c, k) => {
          try { return { c, k, t: M.time(c.at, `${b.where} cue ${c.do}`) }; } catch (e) { return { c, k, t: -1, err: e }; }
        }).sort((x, y) => x.t - y.t || x.k - y.k);
        for (const { c, t, err } of timed) {
          const fn = inst.api.cues && inst.api.cues[c.do];
          if (!fn) { M.errors.push(`${b.where}: ${b.type} has no cue "${c.do}"`); continue; }
          try {
            if (err) throw err;
            if (t < s.t0 - 0.01 || t >= s.t1) throw new Error(`"at": "${c.at}" (${t.toFixed(2)} s) is outside its shot (${s.t0.toFixed(2)}-${s.t1.toFixed(2)} s); put it on a line of this shot, or carry the block (same id) into the next shot and list the cue there`);
            // every cue returns { at, end, off }: at when it really starts (it may wait for its block to land), end
            // when what it shows has landed (a route's chip, a count's last number, a card in; its still is taken
            // then), and optionally off when it is over (a focus halo has held and faded). Both must come before the
            // block leaves
            const r = fn(c, t);
            if (!r || !fin(r.at) || !fin(r.end)) throw new Error(`${b.type}'s "${c.do}" cue must return { at, end }, when it starts and when it lands (it returned ${JSON.stringify(r)}); see "Adding a block" in the guide`);
            const at = r.at, end = r.end, over = Math.max(end, fin(r.off) ? r.off : end);
            if (at >= leaves - 0.01) throw new Error(`"at": "${c.at}" waits for the block to finish entering, so it starts at ${at.toFixed(2)} s, but the block leaves at ${leaves.toFixed(2)} s; give the shot more time (a longer line, or more lines) or carry the block (same id) into the next shot`);
            if (over > leaves + 0.01) throw new Error(`"at": "${c.at}" starts at ${at.toFixed(2)} s and plays until ${over.toFixed(2)} s, but the block leaves at ${leaves.toFixed(2)} s; start it on an earlier line, make it shorter, give the shot more time or carry the block (same id) into the next shot`);
            M.event(at, `${c.do} ${inst.el.dataset.k}`, end);
          } catch (e) { M.errors.push(e.message.startsWith(b.where) ? e.message : `${b.where} cue "${c.do}": ${e.message}`); }
        }
        // leaves at the end of its last shot
        if (lastShot === s && s.t1 < M.TOTAL - 0.01) {
          const tOut = s.t1 - 0.3;
          if (inst.api.exit) inst.api.exit(tOut);
          else M.to(inst.el, { autoAlpha: 0, y: inst.pos.y - 24 * u, duration: 0.3, ease: 'power2.in' }, tOut);
          if (b.id) delete live[b.id];
        }
      });
    });
    M.shots = shots;
  }

  /** The backdrop's light and vignette darken a light ground (and brighten a dark one) beyond the bg the palette's
   *  inks were solved on. Draw the backdrop once per shot, find the worst ground under the content (blurred, so the
   *  grain does not count), and push any ink that falls under 4.6:1 there toward black (light) or white (dark)
   *  until it holds. Panels are unaffected: text on a card keeps the theme's own colours. */
  function guardInks() {
    const P = M.P, keys = ['text', 'muted', 'dim', ...LOOK.HUES.map((h) => h + 'Ink')];
    const small = document.createElement('canvas');
    small.width = 64; small.height = Math.max(8, Math.round((64 * M.H) / M.W));
    const sx = small.getContext('2d');
    const C = M.G.content, f = small.width / M.W;
    let worst = null, wl = M.dark ? -1 : 2;
    const L = (r, g, b) => { const c = [r, g, b].map((v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }); return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]; };
    shotsRt.forEach((r, i) => {
      const t1 = i + 1 < shotsRt.length ? shotsRt[i + 1].t0 : M.TOTAL;
      for (const t of [r.t0 + 0.2, (r.t0 + t1) / 2]) {
        M.ambient(Math.min(t, M.TOTAL));
        sx.clearRect(0, 0, small.width, small.height);
        sx.drawImage(bg, 0, 0, small.width, small.height);
        const d = sx.getImageData(Math.floor(C.x * f), Math.floor(C.y * f), Math.max(1, Math.floor(C.w * f)), Math.max(1, Math.floor(C.h * f))).data;
        for (let k = 0; k < d.length; k += 4) {
          const l = L(d[k], d[k + 1], d[k + 2]);
          if (M.dark ? l > wl : l < wl) { wl = l; worst = '#' + [d[k], d[k + 1], d[k + 2]].map((v) => v.toString(16).padStart(2, '0')).join(''); }
        }
      }
    });
    if (!worst) return;
    M.ground = worst;
    const toward = M.dark ? '#ffffff' : '#000000';
    for (const k of keys) {
      if (!P[k]) continue;
      let c = P[k], n = 0;
      while (M.contrast(c, worst) < 4.6 && n++ < 40) c = M.mix(c, toward, 0.03);
      if (c !== P[k]) { M.notes.push(`${k} ${P[k]} -> ${c} (holds 4.6:1 on the lit ground ${worst})`); P[k] = c; }
    }
  }

  // ------------------------------------------------------------------ the persistent frame
  function buildChrome(style) {
    const G = M.G, u = M.u;
    chromeEl = M.el('div', 'chrome', stage, { left: G.chrome.x + 'px', top: G.chrome.y + 'px', width: G.chrome.w + 'px', height: G.chrome.h + 'px' });
    const left = M.el('div', 'brand', chromeEl);
    if (style.brand !== false) {
      const mark = style.mark || String(style.brand || 'Motion').split(/\s+/).map((w) => w[0]).join('').slice(0, 2).toUpperCase();
      M.el('span', 'mark', left, null, mark);
      M.el('span', 'name', left, null, style.brand || 'Motion');
    }
    if (style.tag) M.el('div', 'tag', chromeEl, null, style.tag);
    const track = M.el('div', 'prog', chromeEl);
    progFill = M.el('div', 'fill', track);
    M.fromTo(chromeEl, { autoAlpha: 0, y: -12 * u }, { autoAlpha: 1, y: 0, duration: 0.6 }, 0.05);
  }

  // ------------------------------------------------------------------ captions: the line's cap, the spoken word lit
  /** Where each caption word starts in the narration, 0..1 along its `say` text (the voice has no word timings).
   *  cap may differ from say ("700" is "seven hundred"): words found in say, in order, take their place there;
   *  a run of words that are not found takes the say words between its found neighbours. No say: by length. */
  function wordAt(capWords, say) {
    const norm = (x) => x.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, '');
    const text = String(say || ''), sw = [...text.matchAll(/\S+/g)].map((m) => ({ k: norm(m[0]), x: m.index / text.length }));
    if (!sw.length) {
      const total = capWords.reduce((s, w) => s + w.length + 1, 0);
      let acc = 0;
      return capWords.map((w) => { const x = acc / total; acc += w.length + 1; return x; });
    }
    const q = capWords.map(() => -1), x = capWords.map(() => 0);
    let j = 0;
    capWords.forEach((w, n) => {
      const k = norm(w);
      for (let s = j; k && s < Math.min(sw.length, j + 6); s++) if (sw[s].k === k) { q[n] = s; x[n] = sw[s].x; j = s + 1; return; }
    });
    const at = (s) => (s < sw.length ? sw[s].x : 1);
    for (let n = 0; n < q.length;) {
      if (q[n] >= 0) { n++; continue; }
      let e = n;
      while (e < q.length && q[e] < 0) e++;
      const lo = n ? q[n - 1] + 1 : 0, hi = e < q.length ? q[e] : sw.length;   // say words [lo, hi) are not taken
      for (let r = n; r < e; r++) {
        if (hi > lo) x[r] = at(lo + Math.floor(((r - n) * (hi - lo)) / (e - n)));
        else { const a = n ? x[n - 1] : 0, b = at(hi); x[r] = a + ((b - a) * (r - n + 1)) / (e - n + 1); }
      }
      n = e;
    }
    return x;
  }

  function buildCaptions(style) {
    const G = M.G, u = M.u, P = M.P;
    const band = M.el('div', 'caps', stage, { left: G.cap.x + 'px', top: G.cap.y + 'px', width: G.cap.w + 'px', height: G.cap.h + 'px' });
    const size = (M.shape === 'tall' ? LOOK.TYPE.captionTall : LOOK.TYPE.caption) * u;
    const karaoke = style.karaoke !== false;
    M.lines.forEach((l, i) => {
      const cap = M.el('div', 'cap', band);
      cap.dataset.k = `cap-${l.id}`;
      const txt = M.el('div', 'txt', cap);
      const { words } = M.rich(l.cap.replace(/\*([^*\s](?:[^*]*[^*\s])?)\*/g, '$1'), txt);
      M.fit(txt, G.cap.w, G.cap.h, size, LOOK.TYPE.min * u, `caption ${l.id}`);
      M.init(cap, { autoAlpha: 0 });
      const tIn = i === 0 ? Math.max(0.1, l.start) : l.start;
      // the caption fades once the voice has finished it (a short pad or outro would otherwise hide the last words),
      // and is gone by the end of the film
      const tOut = Math.min(Math.max(l.vEnd, l.next ? l.end - 0.14 : M.TOTAL - 0.35), M.TOTAL - 0.01);
      M.fromTo(cap, { autoAlpha: 0, y: 14 * u }, { autoAlpha: 1, y: 0, duration: 0.24, ease: 'power2.out' }, tIn);
      M.to(cap, { autoAlpha: 0, duration: Math.min(0.14, M.TOTAL - tOut), ease: 'power1.in' }, tOut);
      if (!karaoke || !words.length) return;
      // each word lights (accent ink) when the voice reaches it, then settles to the body colour
      const times = wordAt(words.map((w) => w.textContent), l.say).map((x) => l.voiceAt + l.voiceDur * x);
      words.forEach((w, k) => {
        M.init(w, { color: P.dim });
        M.set(w, { color: P.accentInk }, Math.max(tIn + 0.01, times[k]));
        M.set(w, { color: P.text }, k + 1 < words.length ? Math.max(tIn + 0.02, times[k + 1]) : Math.min(l.vEnd, M.TOTAL - 0.01));
      });
    });
  }

  // ------------------------------------------------------------------ the backdrop and per-frame things
  function makeGrain(w, h) {
    const c = document.createElement('canvas');
    c.width = w; c.height = h;
    const x = c.getContext('2d'), img = x.createImageData(w, h), r = M.rng(7);
    for (let i = 0; i < img.data.length; i += 4) {
      const v = r() < 0.5 ? 0 : 255;
      img.data[i] = img.data[i + 1] = img.data[i + 2] = v;
      img.data[i + 3] = Math.round(r() * 26);
    }
    x.putImageData(img, 0, 0);
    return c;
  }
  const hexA = (c, a) => M.rgba(c, M.clamp(a, 0, 1));
  /** Everything that is a pure function of t but not a tween: the backdrop light, the drift, the progress bar. */
  M.ambient = (t) => {
    if (!bgx) return;
    const P = M.P, w = bg.width, h = bg.height, x = bgx;
    const g = x.createLinearGradient(0, 0, w * 0.3, h);
    g.addColorStop(0, P.bg2); g.addColorStop(0.55, P.bg); g.addColorStop(1, P.bg);
    x.globalCompositeOperation = 'source-over';
    x.globalAlpha = 1;
    x.fillStyle = g; x.fillRect(0, 0, w, h);
    // the shot's light, cross-faded over ~1 s at each shot change
    let k = 0;
    while (k + 1 < shotsRt.length && t >= shotsRt[k + 1].t0 - 0.4) k++;
    const f = k === 0 ? 1 : M.smooth((t - (shotsRt[k].t0 - 0.4)) / 1.1);
    const strength = M.dark ? 0.2 : 0.12;   // multiply darkens a light ground fast; keep it gentle
    x.globalCompositeOperation = M.dark ? 'screen' : 'multiply';
    const blob = (col, a, cx, cy, r) => {
      const rg = x.createRadialGradient(cx, cy, 0, cx, cy, r);
      rg.addColorStop(0, hexA(col, a)); rg.addColorStop(1, hexA(col, 0));
      x.fillStyle = rg; x.fillRect(0, 0, w, h);
    };
    const R = Math.max(w, h) * 0.62;
    const drift = (ph) => [Math.sin(t * 0.11 + ph) * w * 0.06, Math.cos(t * 0.09 + ph) * h * 0.05];
    const [ax, ay] = drift(0), [bx, by] = drift(2.1);
    const pairs = k > 0 && f < 1 ? [[shotsRt[k - 1].light, 1 - f], [shotsRt[k].light, f]] : [[shotsRt[k] ? shotsRt[k].light : P.accent, 1]];
    for (const [col, a] of pairs) {
      blob(col, strength * a, w * 0.12 + ax, h * 0.1 + ay, R);
      blob(M.dark ? P.cool : P.gold, strength * 0.55 * a, w * 0.95 + bx, h * 0.92 + by, R * 0.9);
    }
    // vignette toward `deep`, then static grain
    x.globalCompositeOperation = 'source-over';
    const vg = x.createRadialGradient(w / 2, h / 2, Math.min(w, h) * 0.35, w / 2, h / 2, Math.max(w, h) * 0.75);
    vg.addColorStop(0, hexA(P.deep, 0)); vg.addColorStop(1, hexA(P.deep, M.dark ? 0.75 : 0.6));
    x.fillStyle = vg; x.fillRect(0, 0, w, h);
    x.globalCompositeOperation = M.dark ? 'screen' : 'multiply';
    x.globalAlpha = M.dark ? 0.35 : 0.5;
    x.drawImage(grain, 0, 0);
    x.globalAlpha = 1;
    x.globalCompositeOperation = 'source-over';
    // a slow camera breath on the content (continuous, never a jump)
    const s = 1 + 0.006 * (1 - Math.cos(t * 0.42));
    world.style.transform = `translate(${(Math.sin(t * 0.23) * 4 * M.u).toFixed(2)}px, ${(Math.cos(t * 0.19) * 3 * M.u).toFixed(2)}px) scale(${s.toFixed(5)})`;
    if (progFill) progFill.style.transform = `scaleX(${M.clamp(t / M.TOTAL).toFixed(5)})`;
  };
})();
