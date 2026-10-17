// engine/data.js: datasets for the chart and number blocks, so a revised number flows through the film.
//
// film.json "data": {"speeds": "data/render-speed.csv", "week": [{"day": "Mon", "solved": 3}, ...]}
//   a path (CSV with a header row, or JSON rows) relative to source/, or rows written inline.
// Blocks read it in two ways:
//   a value:  "=speeds.fps:max"        dataset.column:aggregate (sum avg min max first last over numbers; count: rows with a value)
//             "=speeds.fps[kit=gsap]"  the column in the first row where kit is gsap
//   rows:     {"from": "speeds", "x": "kit", "y": "fps", "sort": "desc", "limit": 6}
// motion_fill.py reads the same references in script.json ("{{speeds.fps:max|words}}"), so the narration
// says the new number too.
(function () {
  const M = window.M;
  const D = (M.data = { sets: {} });

  /** RFC 4180-ish CSV: quoted fields, doubled quotes, commas and newlines inside quotes. Numbers become numbers. */
  D.parseCSV = (text) => {
    const rows = [];
    let row = [], f = '', q = false;
    const s = String(text).replace(/\r\n?/g, '\n');
    for (let i = 0; i < s.length; i++) {
      const c = s[i];
      if (q) {
        if (c === '"' && s[i + 1] === '"') { f += '"'; i++; } else if (c === '"') q = false; else f += c;
      } else if (c === '"') q = true;
      else if (c === ',') { row.push(f); f = ''; } else if (c === '\n') { row.push(f); rows.push(row); row = []; f = ''; } else f += c;
    }
    if (f !== '' || row.length) { row.push(f); rows.push(row); }
    const body = rows.filter((r) => r.some((x) => x.trim() !== ''));
    if (!body.length) return [];
    const head = body[0].map((h) => h.trim());
    return body.slice(1).map((r) => Object.fromEntries(head.map((h, i) => [h, D.cell(r[i])])));
  };
  D.cell = (x) => {
    const v = String(x ?? '').trim();
    return v !== '' && /^-?\d+(\.\d+)?([eE][+-]?\d+)?$/.test(v.replace(/,/g, '')) ? parseFloat(v.replace(/,/g, '')) : v;
  };

  /** Load every dataset film.json names (fetch over the page's own server; capture.mjs serves source/). */
  D.load = async (spec = {}) => {
    D.sets = {};
    for (const [name, src] of Object.entries(spec)) {
      const norm = (rows) => rows.map((r) => Object.fromEntries(Object.entries(r).map(([k, v]) => [k, typeof v === 'string' ? D.cell(v) : v])));
      if (Array.isArray(src)) { D.sets[name] = norm(src); continue; }
      if (typeof src !== 'string') throw new Error(`film.json data.${name}: give a path (data/x.csv) or rows`);
      if (/^[a-z]+:|^[\/\\]|(^|[\/\\])\.\.([\/\\]|$)/i.test(src)) throw new Error(`film.json data.${name}: "${src}" must be a relative path inside source/ (no URLs, no ..)`);
      const r = await fetch(src, { cache: 'no-store' });
      if (!r.ok) throw new Error(`film.json data.${name}: could not read ${src} (${r.status}); preview through a local server, not file://`);
      const txt = await r.text();
      D.sets[name] = /\.json$/i.test(src) ? norm(JSON.parse(txt)) : D.parseCSV(txt);
    }
    return D.sets;
  };

  const set = (name, where) => {
    if (!(name in D.sets)) throw new Error(`${where}: no dataset "${name}" (film.json data has: ${Object.keys(D.sets).join(', ') || 'none'})`);
    return D.sets[name];
  };
  const AGG = {
    sum: (a) => a.reduce((s, x) => s + x, 0), avg: (a) => a.reduce((s, x) => s + x, 0) / (a.length || 1),
    min: (a) => Math.min(...a), max: (a) => Math.max(...a), first: (a) => a[0], last: (a) => a[a.length - 1], count: (a) => a.length,
  };
  /** A value: a number or text as is, or "=set.col:agg" / "=set.col[key=value]". */
  D.value = (ref, where = 'film.json') => {
    if (typeof ref !== 'string' || !ref.startsWith('=')) return ref;
    const m = /^=([A-Za-z0-9_-]+)\.([^:\[\]]+)(?::(sum|avg|min|max|first|last|count)|\[([^=\]]+)=([^\]]+)\])?$/.exec(ref.trim());
    if (!m) throw new Error(`${where}: cannot read "${ref}" (use "=set.column:max" or "=set.column[key=value]")`);
    const rows = set(m[1], where), col = m[2].trim();
    if (rows.length && !(col in rows[0])) throw new Error(`${where}: dataset "${m[1]}" has no column "${col}" (columns: ${Object.keys(rows[0]).join(', ')})`);
    if (m[4]) {
      const want = m[5].trim(), wn = D.cell(want);  // "001" and "1.0" find the row CSV parsing made 1, as motion_fill.py does
      const row = rows.find((r) => String(r[m[4].trim()]) === want || (typeof r[m[4].trim()] === 'number' && r[m[4].trim()] === wn));
      if (!row) throw new Error(`${where}: no row in "${m[1]}" where ${m[4]} = ${m[5]}`);
      return row[col];
    }
    if (m[3] === 'count') return rows.filter((r) => r[col] !== '' && r[col] !== null && r[col] !== undefined).length;   // rows with a value, numbers or not
    const vals = rows.map((r) => r[col]).filter((v) => typeof v === 'number');
    if (!vals.length) throw new Error(`${where}: column "${col}" of "${m[1]}" has no numbers for "${m[3] || 'last'}"`);   // as motion_fill.py says
    return AGG[m[3] || 'last'](vals);
  };
  /** A number as a chart or stat reads it: a number, or text that is one ("1,200"). Blank, null and true/false are
   *  not numbers (unary + would make them 0 or 1), as motion_fill.py leaves them out of sums. */
  D.num = (v) => (typeof v === 'number' ? v : typeof v === 'string' && typeof D.cell(v) === 'number' ? D.cell(v) : NaN);
  /** Rows for a chart: inline [{label, value}] (or [[label, value]]), or {from, x, y, sort, limit}.
   *  Returns [{label, value, row}]. */
  D.rows = (spec, where = 'film.json') => {
    let out;
    // a label is drawn on the chart and named by highlights and annotations: a short text or a number, not blank,
    // an object or a list (which would draw as "", "[object Object]" or "a,b")
    const label = (v, i) => {
      if ((typeof v === 'string' && v.trim() !== '') || (typeof v === 'number' && isFinite(v))) return String(v);
      throw new Error(`${where}: row ${i + 1}'s label is ${JSON.stringify(v) ?? 'missing'}; a label is a short text or a number`);
    };
    if (Array.isArray(spec)) {
      out = spec.map((r, i) => (Array.isArray(r) ? { label: label(r[0], i), value: D.num(r[1]), row: r }
        : { label: label(r && (r.label ?? r.x), i), value: D.num(D.value(r.value ?? r.y, where)), row: r }));
    } else if (spec && spec.from) {
      const rows = set(spec.from, where);
      const x = spec.x, y = spec.y;
      if (rows.length && (!(x in rows[0]) || !(y in rows[0]))) throw new Error(`${where}: dataset "${spec.from}" needs columns "${x}" and "${y}" (has: ${Object.keys(rows[0]).join(', ')})`);
      out = rows.map((r, i) => ({ label: label(r[x], i), value: D.num(r[y]), row: r }));
    } else throw new Error(`${where}: give rows as [{"label": "...", "value": 3}] or {"from": "set", "x": "col", "y": "col"}`);
    const bad = out.filter((r) => !isFinite(r.value));
    if (bad.length) throw new Error(`${where}: blank or non-numeric values for ${bad.map((r) => r.label).join(', ')}`);
    if (spec && !Array.isArray(spec)) {   // (an array's .sort is its method, not a setting)
      const set_ = (v) => v !== undefined && v !== null && v !== '';
      if (set_(spec.sort) && spec.sort !== 'asc' && spec.sort !== 'desc') throw new Error(`${where}: "sort" is ${JSON.stringify(spec.sort)}; it takes asc or desc`);
      if (set_(spec.limit) && !(Number.isInteger(spec.limit) && spec.limit > 0)) throw new Error(`${where}: "limit" is ${JSON.stringify(spec.limit)}; it takes a whole number above 0`);
    }
    if (spec && spec.sort === 'desc') out.sort((a, b) => b.value - a.value);
    if (spec && spec.sort === 'asc') out.sort((a, b) => a.value - b.value);
    if (spec && spec.limit) out = out.slice(0, spec.limit);
    return out;
  };
})();
