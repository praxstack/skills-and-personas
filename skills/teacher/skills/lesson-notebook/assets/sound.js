// The sound of the pen: chalk on a board or pencil on paper. It plays real
// recordings (CC0, see sounds/SOUNDS.md) in small overlapping grains, so no
// two strokes sound the same, and shapes each stroke by how it's drawn:
//   direction  horizontal strokes sound a touch higher, vertical ones lower
//   position   panned left or right by where it is on the board
//   speed      faster strokes are louder and brighter
// Chalk also taps when it lands. Until the recordings are decoded (or if a
// browser can't decode them) a friction synth stands in: sparse clicks over
// broadband noise, matching the recordings' measured spectrum and grit.
// Browsers only allow sound after the learner interacts, so the first click
// or key press anywhere unlocks it. The learner can switch it off; the choice
// is remembered. Reduced motion means no drawing, so no drawing sounds.

import { PEN_SAMPLES } from "./pen-samples.js";

const SOUND_KEY = "notebook:sound";
let audio = null; // { ctx, noise, out, samples: { chalk: [...], paper: [...] } }
let soundOn = (() => {
  try {
    return localStorage.getItem(SOUND_KEY) === "on"; // off unless the learner turns it on
  } catch {
    return false;
  }
})();
const listeners = new Set();
// Counts for tests and QA: how many scratches were actually scheduled.
const stats = { scratches: 0, taps: 0, grains: 0, decoded: 0, synth: 0 };
if (typeof window !== "undefined") window.__notebookSound = { stats, state: () => (audio ? audio.ctx.state : "none") };

function boardKind() {
  const root = document.documentElement;
  if (root.dataset.board === "chalk") return "chalk";
  if (root.dataset.board === "paper") return "paper";
  if (root.dataset.theme === "dark") return "chalk";
  if (root.dataset.theme === "light") return "paper";
  try {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "chalk" : "paper";
  } catch {
    return "paper";
  }
}

function makeAudio() {
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx) return null;
  const ctx = new Ctx();
  // Two seconds of friction noise for the fallback synth: a soft hiss with
  // sparse sharp clicks, like a tip catching and slipping on the surface.
  const noise = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
  const data = noise.getChannelData(0);
  for (let i = 0; i < data.length; i += 1) {
    const click = Math.random() < 0.012 ? (Math.random() * 2 - 1) * 3.2 : 0;
    data[i] = (Math.random() * 2 - 1) * 0.45 + click;
  }
  const out = ctx.createGain();
  out.gain.value = 0.9;
  const comp = ctx.createDynamicsCompressor();
  comp.connect(ctx.destination);
  out.connect(comp);
  const a = { ctx, noise, out, comp, samples: { chalk: [], paper: [] } };
  decodeSamples(a);
  return a;
}

function decodeB64(ctx, b64) {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i += 1) bytes[i] = bin.charCodeAt(i);
  // The callback form works in older Safari, where decodeAudioData has no promise.
  return new Promise((resolve, reject) => {
    const p = ctx.decodeAudioData(bytes.buffer, resolve, reject);
    if (p && p.catch) p.catch(reject);
  });
}

/** Where a recording is actually making sound: offsets (s) worth starting a grain at. */
function activeStarts(buffer, grain) {
  const d = buffer.getChannelData(0);
  const hop = Math.round(buffer.sampleRate * 0.01);
  const rms = [];
  for (let i = 0; i + hop < d.length; i += hop) {
    let e = 0;
    for (let j = i; j < i + hop; j += 1) e += d[j] * d[j];
    rms.push(Math.sqrt(e / hop));
  }
  const top = Math.max(...rms, 1e-6);
  const last = buffer.duration - grain;
  const starts = rms.map((v, k) => [v, (k * hop) / buffer.sampleRate]).filter(([v, t]) => v > top * 0.3 && t < last).map(([, t]) => t);
  return starts.length ? starts : [0];
}

function decodeSamples(a) {
  for (const kind of Object.keys(a.samples)) {
    for (const b64 of PEN_SAMPLES[kind] || []) {
      decodeB64(a.ctx, b64)
        .then((buffer) => {
          a.samples[kind].push({ buffer, starts: activeStarts(buffer, GRAIN) });
          stats.decoded += 1;
        })
        .catch(() => {
          /* this browser can't decode MP3: the synth stands in */
        });
    }
  }
}

const GRAIN = 0.085; // seconds per grain; grains overlap by about half

function unlock() {
  if (!soundOn) return;
  if (!audio) audio = makeAudio();
  if (audio && audio.ctx.state === "suspended") audio.ctx.resume().catch(() => {});
}
if (typeof window !== "undefined") {
  for (const ev of ["pointerdown", "keydown", "touchstart"]) window.addEventListener(ev, unlock, { capture: true, passive: true });
}

export function soundEnabled() {
  return soundOn;
}

export function setSound(on) {
  soundOn = Boolean(on);
  try {
    localStorage.setItem(SOUND_KEY, soundOn ? "on" : "off");
  } catch {
    /* storage blocked */
  }
  if (soundOn) unlock();
  else if (audio) audio.ctx.suspend().catch(() => {});
  listeners.forEach((fn) => fn(soundOn));
}

export function onSoundChange(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

/** A small button that switches the drawing sounds on and off. */
export function soundButton(className = "nb-btn nb-btn-quiet") {
  const b = document.createElement("button");
  b.type = "button";
  b.className = className;
  const paint = () => {
    b.textContent = soundOn ? "Sound on" : "Sound off";
    b.setAttribute("aria-pressed", String(soundOn));
    b.title = soundOn ? "Turn off the chalk and pencil sounds" : "Turn on the chalk and pencil sounds";
  };
  b.addEventListener("click", () => setSound(!soundOn));
  onSoundChange(paint);
  paint();
  return b;
}

function ready() {
  return soundOn && audio && audio.ctx.state === "running";
}

/** The shape of a stroke on screen: length, angle and horizontal position (0..1). */
export function strokeShape(path) {
  try {
    const len = path.getTotalLength();
    const a = path.getPointAtLength(0);
    const b = path.getPointAtLength(len);
    const m = path.getScreenCTM();
    const toScreen = (p) => (m ? { x: p.x * m.a + p.y * m.c + m.e, y: p.x * m.b + p.y * m.d + m.f } : p);
    const sa = toScreen(a);
    const sb = toScreen(b);
    const px = Math.hypot(sb.x - sa.x, sb.y - sa.y) || len;
    return { length: px, angle: Math.atan2(sb.y - sa.y, sb.x - sa.x), x: Math.min(1, Math.max(0, ((sa.x + sb.x) / 2) / (window.innerWidth || 1))) };
  } catch {
    return { length: 120, angle: 0, x: 0.5 };
  }
}

/**
 * Play one stroke's scratch, starting `delayMs` from now and lasting `durMs`.
 * shape: { length, angle, x } in screen pixels and radians (see strokeShape).
 */
export function scratch(delayMs, durMs, shape = {}, { kind = boardKind(), gain = 1 } = {}) {
  if (!ready()) return;
  stats.scratches += 1;
  const { ctx } = audio;
  const t0 = ctx.currentTime + Math.max(0, delayMs) / 1000;
  const dur = Math.max(0.05, durMs / 1000);
  const chalk = kind === "chalk";
  const horiz = Math.abs(Math.cos(shape.angle ?? 0)); // 1 horizontal, 0 vertical
  const speed = Math.min(1.6, Math.max(0.4, (shape.length ?? 120) / (durMs || 300) / 0.35)); // px per ms, around 1
  const pan = ctx.createStereoPanner ? ctx.createStereoPanner() : null;
  if (pan) {
    pan.pan.value = ((shape.x ?? 0.5) - 0.5) * 1.2;
    pan.connect(audio.out);
  }
  const dest = pan || audio.out;
  const bank = audio.samples[chalk ? "chalk" : "paper"];
  if (bank.length) grains(t0, dur, bank, dest, { chalk, horiz, speed, gain });
  else friction(t0, dur, dest, { chalk, horiz, speed, gain });
  if (chalk) tap(t0, gain, dest);
}

/** Real recordings, cut into short overlapping grains from where they're loudest. */
function grains(t0, dur, bank, dest, { chalk, horiz, speed, gain }) {
  const { ctx } = audio;
  const tone = ctx.createBiquadFilter();
  tone.type = "lowpass";
  tone.frequency.value = (chalk ? 6500 : 9000) + 4000 * Math.min(1, speed - 0.4);
  tone.Q.value = 0.4;
  tone.connect(dest);
  const level = (chalk ? 1.0 : 0.62) * gain * Math.min(1.3, 0.6 + 0.4 * speed);
  const rate = (0.9 + 0.14 * horiz) * (0.97 + 0.06 * Math.min(1, speed - 0.4));
  const end = t0 + dur;
  for (let t = t0; t < end; t += GRAIN * (0.4 + Math.random() * 0.2)) {
    const s = bank[Math.floor(Math.random() * bank.length)];
    const src = ctx.createBufferSource();
    src.buffer = s.buffer;
    src.playbackRate.value = rate * (0.95 + Math.random() * 0.1);
    // Fade the whole stroke in over 25 ms and out over the last 15%.
    const edge = Math.min(1, (t - t0) / 0.025 + 0.15, (end - t) / (dur * 0.15) + 0.1);
    const peak = level * edge * (0.65 + Math.random() * 0.35);
    const env = ctx.createGain();
    env.gain.setValueAtTime(0, t);
    env.gain.linearRampToValueAtTime(peak, t + GRAIN * 0.3);
    env.gain.linearRampToValueAtTime(0, t + GRAIN);
    src.connect(env).connect(tone);
    src.start(t, s.starts[Math.floor(Math.random() * s.starts.length)]);
    src.stop(t + GRAIN + 0.01);
    stats.grains += 1;
  }
}

/** The fallback: friction noise shaped like the recordings (broad, gritty, pulsing). */
function friction(t0, dur, dest, { chalk, horiz, speed, gain }) {
  stats.synth += 1;
  const { ctx, noise } = audio;
  const src = ctx.createBufferSource();
  src.buffer = noise;
  src.loop = true;
  src.playbackRate.value = 0.9 + 0.14 * horiz;
  const band = ctx.createBiquadFilter();
  band.type = "bandpass";
  band.frequency.value = (chalk ? 4200 + 1200 * horiz : 5200 + 1800 * horiz) * (0.85 + 0.3 * speed) * (0.94 + Math.random() * 0.12);
  band.Q.value = chalk ? 0.55 : 0.35;
  const env = ctx.createGain();
  const level = (chalk ? 0.4 : 0.2) * gain * Math.min(1.3, 0.6 + 0.4 * speed);
  env.gain.setValueAtTime(0.0001, t0);
  env.gain.exponentialRampToValueAtTime(level, t0 + Math.min(0.03, dur / 4));
  // The tip catches and slips about every 20 ms; chalk also skips now and then.
  for (let t = t0 + 0.03; t < t0 + dur * 0.9; t += 0.018 + Math.random() * 0.008) {
    const skip = chalk && Math.random() < 0.12 ? 0.35 : 1;
    env.gain.setValueAtTime(level * skip * (0.6 + Math.random() * 0.4), t);
  }
  env.gain.setValueAtTime(level * 0.9, t0 + dur * 0.92);
  env.gain.exponentialRampToValueAtTime(0.0001, t0 + dur + 0.06);
  src.connect(band).connect(env).connect(dest);
  src.start(t0, Math.random() * 1.5);
  src.stop(t0 + dur + 0.1);
}

/** The click of chalk landing on the board. */
function tap(t0, gain, dest) {
  stats.taps += 1;
  const { ctx, noise } = audio;
  const src = ctx.createBufferSource();
  src.buffer = noise;
  const hp = ctx.createBiquadFilter();
  hp.type = "highpass";
  hp.frequency.value = 2400;
  const env = ctx.createGain();
  env.gain.setValueAtTime(0.0001, t0);
  env.gain.exponentialRampToValueAtTime(0.22 * gain, t0 + 0.004);
  env.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.05);
  src.connect(hp).connect(env).connect(dest);
  src.start(t0, Math.random());
  src.stop(t0 + 0.08);
}

/** Stop every sound already scheduled (the drawing was finished or cancelled). */
export function hush() {
  if (!audio) return;
  const { ctx, out, comp } = audio;
  const fresh = ctx.createGain();
  fresh.gain.value = 0.9;
  fresh.connect(comp);
  out.gain.setTargetAtTime(0, ctx.currentTime, 0.015);
  setTimeout(() => out.disconnect(), 120);
  audio.out = fresh;
}

/** Handwriting: a run of short scratches, one per word. */
export function writing(delayMs, durMs, words = 4, { kind = boardKind() } = {}) {
  if (!ready()) return;
  const per = durMs / Math.max(1, words);
  for (let i = 0; i < words; i += 1) {
    scratch(delayMs + i * per, per * 0.75, { length: 40, angle: (Math.random() - 0.5) * 1.2, x: 0.5 }, { kind, gain: 0.55 });
  }
}
