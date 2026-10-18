// Saved progress is indexed by step number, so it is only valid for the step
// layout it was saved against. Each step gets a key (its `id` when the lesson
// gives one, else a short hash of its title and question), the keys are saved
// with the progress, and on load the progress follows its step to wherever it
// now sits. Steps that are new start fresh; steps that are gone drop their
// state. Progress saved before keys existed can't be matched, so its
// step-indexed parts are dropped (notes and the curiosity list are kept).

function shortHash(text) {
  // FNV-1a, 32 bit: stable across browsers and Node, no crypto needed.
  let h = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0).toString(36);
}

export function stepKeys(steps) {
  const seen = {};
  return (steps || []).map((st) => {
    const ask = st.ask || {};
    const base = st.id ? `id:${st.id}` : shortHash([st.title, ask.kind, ask.q].map((x) => (typeof x === "string" ? x : "")).join("\u0001"));
    seen[base] = (seen[base] || 0) + 1;
    return seen[base] > 1 ? `${base}#${seen[base]}` : base;
  });
}

const isObj = (v) => v !== null && typeof v === "object" && !Array.isArray(v);

// stored: whatever was in storage (may be anything). keys: stepKeys(L.steps).
export function restoreProgress(stored, keys) {
  const s = isObj(stored) ? stored : {};
  const out = {
    step: 0,
    done: [],
    attempts: {},
    tried: {},
    explained: {},
    notes: typeof s.notes === "string" ? s.notes : "",
    curious: Array.isArray(s.curious) ? s.curious.filter((q) => typeof q === "string") : [],
  };
  if (!Array.isArray(s.steps)) return out;
  const now = new Map(keys.map((k, i) => [k, i]));
  // Steps that share a key are told apart only by their order (#2, #3), so
  // when that group grew or shrank, which saved step is which is a guess:
  // its progress is dropped rather than handed to the wrong step.
  const group = (k) => k.replace(/#\d+$/, "");
  const sizes = (list) => list.reduce((m, k) => (typeof k === "string" ? m.set(group(k), (m.get(group(k)) || 0) + 1) : m), new Map());
  const was = sizes(s.steps), is = sizes(keys);
  const move = (oldIndex) => {
    const k = s.steps[Number(oldIndex)];
    return typeof k === "string" && now.has(k) && was.get(group(k)) === is.get(group(k)) ? now.get(k) : undefined;
  };
  if (Array.isArray(s.done)) for (const i of s.done) if (move(i) !== undefined) out.done.push(move(i));
  // Each entry is reshaped to what the page reads (report() reads x.right and
  // e.covered.length); one it can't use is dropped.
  const shape = {
    attempts: (v) => (Array.isArray(v) ? v.filter((x) => isObj(x) && typeof x.right === "boolean") : undefined),
    tried: (v) => (Array.isArray(v) ? v.filter((x) => typeof x === "string") : undefined),
    explained: (v) =>
      isObj(v) && typeof v.text === "string"
        ? { text: v.text, covered: Array.isArray(v.covered) ? v.covered.filter((n) => Number.isInteger(n) && n >= 0) : [] }
        : undefined,
  };
  for (const [field, fix] of Object.entries(shape)) {
    if (!isObj(s[field])) continue;
    for (const [i, v] of Object.entries(s[field])) {
      const ok = fix(v);
      if (ok !== undefined && move(i) !== undefined) out[field][move(i)] = ok;
    }
  }
  out.step = move(s.step) ?? 0;
  return out;
}
