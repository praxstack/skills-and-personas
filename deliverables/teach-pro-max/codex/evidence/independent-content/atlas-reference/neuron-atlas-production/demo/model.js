/* Neuron Atlas — authoritative dimensionless toy model, version 1.0.0. */
(function expose(root) {
  'use strict';
  const BASE = Object.freeze({x1:0.8, x2:0.4, w1:1.5, w2:-1, b:-0.2, target:1, eta:0.5});
  const ranges = Object.freeze({x1:[-2,2], x2:[-2,2], w1:[-3,3], w2:[-3,3], b:[-3,3], target:[-2,2], eta:[0,1]});

  function validate(state) {
    if (state === null || typeof state !== 'object') throw new TypeError('Provide a numeric neuron state.');
    for (const [key, [low, high]] of Object.entries(ranges)) {
      const value = state[key];
      if (typeof value !== 'number') throw new TypeError(`${key} must be a number.`);
      if (!Number.isFinite(value) || value < low || value > high) {
        throw new RangeError(`${key} must be finite and between ${low} and ${high}.`);
      }
    }
    return state;
  }

  function evaluate(state) {
    validate(state);
    const c1 = state.x1 * state.w1;
    const c2 = state.x2 * state.w2;
    const z = c1 + c2 + state.b;
    const a = Math.max(0,z);
    const error = a - state.target;
    const localGradient = z > 0 ? error : 0; // Explicit derivative convention at z=0.
    return Object.freeze({c1,c2,z,a,error,loss:0.5*error*error,
      grad:Object.freeze({w1:localGradient*state.x1,w2:localGradient*state.x2,b:localGradient})});
  }

  function step(state) {
    const {grad} = evaluate(state);
    const next = {...state,
      w1:state.w1-state.eta*grad.w1,
      w2:state.w2-state.eta*grad.w2,
      b:state.b-state.eta*grad.b};
    validate(next); // Reject an out-of-domain step atomically; never partially update or clamp.
    return Object.freeze(next);
  }

  const API = Object.freeze({BASE,evaluate,step,validate});
  if (typeof module !== 'undefined' && module.exports) module.exports=API;
  root.NeuronAtlas=API;
})(typeof window !== 'undefined' ? window : globalThis);
