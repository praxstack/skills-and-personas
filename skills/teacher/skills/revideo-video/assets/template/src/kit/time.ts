// The film's clock. Every animation is keyed to a narration line from the timing file that
// voice.py writes (src/timing.ts), never to a hard-coded second, so the picture follows the voice.
//
//   yield* at(L.p3.voiceAt);          // wait until the voice starts line p3
//   yield* at(cue('p4', 'seven'));    // ... until the word "seven" in p4 (estimated from its position)
//   yield* at(voiceEnd('q1'));        // ... until the voice finishes q1 (the think pause starts here)
//
// at() waits for an ABSOLUTE film time. If the scene is already past it (an animation ran long), it logs
// "LATE|<label>|<seconds>" so render_revideo.mjs can report it, and continues without waiting.
import {createSignal, useThread, waitFor, ThreadGenerator} from '@revideo/core';
import {TIMING} from '../timing';

export {TIMING};
export type Line = (typeof TIMING)['lines'][number];
export type Chapter = (typeof TIMING)['chapters'][number];

export const FPS: number = TIMING.fps;
export const TOTAL: number = TIMING.total;
export const LINES: Line[] = TIMING.lines;
export const CHAPTERS: Chapter[] = TIMING.chapters;

const byId: Record<string, Line> = Object.fromEntries(LINES.map(l => [l.id, l]));

/** L.p3 is line "p3" of the script: {start, voiceAt, voiceDur, think, end, dur, cap, say, chapter, scene}. */
export const L: Record<string, Line> = new Proxy(byId, {
  get(target, id: string) {
    if (typeof id !== 'string' || id in target) return (target as any)[id];
    if (id === 'then' || id === 'toJSON' || id.startsWith('__')) return undefined;
    throw new Error(`Unknown line id "${id}". timing.ts has: ${Object.keys(target).join(', ')}`);
  },
});

/** Current absolute time of the running thread (seconds since the film started). */
export function now(): number {
  return useThread().time();
}

/** The line playing at time t (the last one that has started). */
export function lineAt(t: number): Line {
  let cur = LINES[0];
  for (const l of LINES) if (l.start <= t + 1e-6) cur = l;
  return cur;
}

/** Wait until absolute film time t. The label (default: the line playing at t) names it in LATE reports. */
export function* at(t: number, label = ''): ThreadGenerator {
  const dt = t - now();
  if (dt > 1e-6) {
    yield* waitFor(dt);
  } else if (dt < -1.5 / FPS) {
    console.warn(`LATE|${label || lineAt(t).id}@${t.toFixed(2)}|${(-dt).toFixed(2)}`);
  }
}

/** Run `task` starting at absolute time t (inside all(...) to schedule several things on one timeline). */
export function* when(t: number, task: ThreadGenerator, label = ''): ThreadGenerator {
  yield* at(t, label);
  yield* task;
}

/** The moment the voice finishes line `id` (a think pause, if any, starts here). */
export const voiceEnd = (id: string) => L[id].voiceAt + L[id].voiceDur;

/** The moment the voice says `phrase` inside line `id` (estimated from its character position). */
export function cue(id: string, phrase: string, after = 0): number {
  const l = L[id];
  const i = l.say.toLowerCase().indexOf(phrase.toLowerCase());
  if (i < 0) throw new Error(`cue: "${phrase}" is not in the say text of ${id}: "${l.say}"`);
  return l.voiceAt + l.voiceDur * (i / l.say.length) + after;
}

/** Lines of one chapter, in order. */
export const linesOf = (chapter: number) => LINES.filter(l => l.chapter === chapter);
export const chapterOf = (n: number) => CHAPTERS.find(c => c.n === n)!;

/**
 * Chapter card schedule (kit/cards.ts plays it; scenes use it to re-arrange the stage while the card
 * covers the screen, which is where hard cuts belong):
 *   inAt      the wipe starts (just before the previous chapter's last line ends)
 *   coveredAt the screen is fully covered: change layouts here
 *   outAt     the wipe-out starts
 *   clearAt   the stage is fully visible again
 */
export interface CardTimes {n: number; inAt: number; coveredAt: number; outAt: number; clearAt: number}
export const WIPE = 0.5;
export const CARD: Record<number, CardTimes> = {};
CHAPTERS.forEach((c, i) => {
  if (i === 0) return; // the first chapter opens with the title card instead
  const prevEnd = CHAPTERS[i - 1].end;
  const inAt = Math.max(prevEnd - 0.15, CHAPTERS[i - 1].start + 0.5);
  const coveredAt = inAt + WIPE;
  const outAt = Math.max(coveredAt + 0.85, c.start + 0.4);
  CARD[c.n] = {n: c.n, inAt, coveredAt, outAt, clearAt: outAt + WIPE};
});

// ---------------------------------------------------------------- per-frame clock + ticker
// Revideo gotcha: never give a Txt a function as `text` (it throws "The scene is not available in the
// current context" when the value changes during drawing). Update text from a thread instead:
//   onFrame(() => costTxt.text(`COST ${Math.round(cost())}`));
// The stage runs the ticker once per frame (kit/stage.ts), so registered updaters stay deterministic.
export const clock = createSignal(0);
const updaters: (() => void)[] = [];
export function onFrame(fn: () => void) {
  updaters.push(fn);
  return fn;
}
/** Called by setupStage: the scene function runs several times per render, so start from an empty list. */
export function resetFrameUpdaters() {
  updaters.length = 0;
}
export function* ticker(): ThreadGenerator {
  while (true) {
    clock(now());
    for (const u of updaters) u();
    yield;
  }
}

/** Deterministic pseudo-random numbers (never Math.random: every render worker must draw the same frame). */
export function rng(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Log a beat for debugging: "TL|id|time". Harmless in renders. */
export function mark(id: string) {
  console.log(`TL|${id}|${now().toFixed(3)}`);
}
