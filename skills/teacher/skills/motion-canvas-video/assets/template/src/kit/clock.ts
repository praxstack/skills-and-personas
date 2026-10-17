// The film's clock. Every animation is keyed to a narration line id from timing.ts (written by voice.py),
// never to a hard-coded second, so re-voicing re-times the whole film.
//
//   yield* waitUntilLine('p3');               // the moment the voice starts line p3
//   yield* waitUntilLine('p3', 0.4);          // 0.4 s after that
//   yield* waitUntilCue('p4', 'seven hundred'); // when the voice reaches that phrase (estimated)
//   yield* waitUntilThink('q1');              // the voice finished q1: the think pause starts
//   yield* waitUntilLineEnd('p4', -0.3);      // 0.3 s before p4's slot ends
//   yield* waitUntilTime(TIMING.total);       // the last statement of the film
//
// If an animation runs long and the next cue has already passed, the cue logs "[timing] late ..." once (the
// render page prints it) instead of silently drifting.
import {useThread, waitFor, all, type Thread, type ThreadGenerator} from '@motion-canvas/core';
import {TIMING} from '../timing';

export type Line = (typeof TIMING.lines)[number];
export type Chapter = (typeof TIMING.chapters)[number];

export {TIMING};
export const FPS = TIMING.fps;
export const TOTAL = TIMING.total;
export const LINES: Line[] = TIMING.lines;
export const CHAPTERS: Chapter[] = TIMING.chapters;
const byId = new Map(LINES.map(l => [l.id, l]));

/** The timing record of a line: start, voiceAt, voiceDur, think, end, dur, cap, say, chapter, scene. */
export function line(id: string): Line {
  const l = byId.get(id);
  if (!l) throw new Error(`unknown line id '${id}'. Ids in timing.ts: ${LINES.map(x => x.id).join(', ')}`);
  return l;
}
export const voiceAt = (id: string) => line(id).voiceAt;
export const voiceEnd = (id: string) => line(id).voiceAt + line(id).voiceDur;
export const lineEnd = (id: string) => line(id).end;
/** Seconds from the voice start of `id` to the end of its slot: the room an animation keyed to it has. */
export const room = (id: string) => line(id).end - line(id).voiceAt;

/** When the voice reaches `phrase` inside line `id` (estimated from the character position in `say`). */
export function cueTime(id: string, phrase: string) {
  const l = line(id);
  const i = l.say.toLowerCase().indexOf(phrase.toLowerCase());
  if (i < 0) throw new Error(`phrase '${phrase}' is not in the say text of line '${id}': "${l.say}"`);
  return l.voiceAt + (l.voiceDur * i) / Math.max(1, l.say.length);
}

/** The chapter record for a chapter number (index into meta.chapters). */
export function chapter(n: number): Chapter {
  const c = CHAPTERS.find(x => x.n === n);
  if (!c) throw new Error(`no chapter ${n} in timing.ts`);
  return c;
}

const warned = new Set<string>();
function late(what: string, by: number) {
  const msg = `[timing] late by ${by.toFixed(2)} s at ${what}: an earlier animation ran past this cue. Shorten it or key it to a later line.`;
  if (!warned.has(msg)) {
    warned.add(msg);
    console.error(msg);
  }
}

/** Wait until an absolute film time (seconds). */
export function* waitUntilTime(t: number, what = `t=${t.toFixed(2)}`): ThreadGenerator {
  const now = useThread().time();
  if (t > now) yield* waitFor(t - now);
  else if (now - t > 1.5 / FPS) late(what, now - t);
}
/** Wait until the voice starts line `id` (+ offset seconds). */
export function* waitUntilLine(id: string, offset = 0): ThreadGenerator {
  yield* waitUntilTime(voiceAt(id) + offset, `${id}${offset ? (offset > 0 ? '+' : '') + offset : ''}`);
}
/** Wait until the slot of line `id` starts (before its lead-in silence) (+ offset). */
export function* waitUntilLineStart(id: string, offset = 0): ThreadGenerator {
  yield* waitUntilTime(line(id).start + offset, `${id} start`);
}
/** Wait until the voice reaches `phrase` in line `id` (+ offset). */
export function* waitUntilCue(id: string, phrase: string, offset = 0): ThreadGenerator {
  yield* waitUntilTime(cueTime(id, phrase) + offset, `${id} "${phrase}"`);
}
/** Wait until the voice of line `id` ends (the think pause, if any, starts here). */
export function* waitUntilThink(id: string, offset = 0): ThreadGenerator {
  yield* waitUntilTime(voiceEnd(id) + offset, `${id} voice end`);
}
/** Wait until the slot of line `id` ends (+ offset, usually negative). */
export function* waitUntilLineEnd(id: string, offset = 0): ThreadGenerator {
  yield* waitUntilTime(lineEnd(id) + offset, `${id} end`);
}

/** Wait for line `id` (+ offset), then run the animations together. The usual way to write a beat. */
export function* beat(id: string, ...anims: ThreadGenerator[]): ThreadGenerator {
  yield* waitUntilLine(id);
  yield* all(...anims);
}

// ------------------------------------------------------------------ background tasks
let filmThread: Thread | null = null;
/** Called by createWorld() from the film's top level: background() tasks attach to this thread. */
export function setFilmThread(t: Thread) {
  filmThread = t;
}
/**
 * Run a task in the background for as long as the film runs, without waiting for it.
 *
 * Motion Canvas cancels a thread's spawned children when that thread ends, and every argument of all(),
 * sequence() and delay() runs in its own short-lived thread. A plain `yield task` inside such a generator
 * is cut off early; background(task) is not (the task starts on the next frame).
 */
export function background(task: ThreadGenerator) {
  (filmThread ?? useThread()).spawn(task);
}
