// rig.js: wire the kit to Theatre.js. Collects every component's objects into one schema, creates the sheet objects,
// and per frame seeks the sequence and hands each component its current values.
import { getProject, types } from '@theatre/core';
import { kindOf, schemaOf } from './keys.js';
export { schemaOf };

/** plain defaults -> Theatre prop types (rgba objects need types.rgba, or Theatre treats them as compounds) */
export function theatreProps(defaults) {
  const out = {};
  for (const [p, v] of Object.entries(defaults)) {
    const k = kindOf(v);
    out[p] = k === 'rgba' ? types.rgba(v) : k === 'number' ? types.number(v) : k === 'string' ? types.string(v) : k === 'boolean' ? types.boolean(v) : v;
  }
  return out;
}

export async function createRig({ projectId, sheetName = 'Film', state, schema }) {
  const project = getProject(projectId, { state });
  const sheet = project.sheet(sheetName);
  const objs = Object.entries(schema).map(([k, d]) => [k, sheet.object(k, theatreProps(d))]);
  await project.ready;
  const length = state?.sheetsById?.[sheetName]?.sequence?.length ?? 0;
  return {
    project, sheet, objs,
    /** seek and read every object's values at time t (deterministic: no clock, no playback) */
    values(t) {
      sheet.sequence.position = Math.max(0, Math.min(t, length));
      const V = {};
      for (const [k, o] of objs) V[k] = o.value;
      return V;
    },
    /** read the values at wherever the sequence is now (Studio scrubbing / playback); no seek */
    current() {
      const V = {};
      for (const [k, o] of objs) V[k] = o.value;
      return V;
    },
  };
}
