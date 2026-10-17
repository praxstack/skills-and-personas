// The film's clock. voice.py writes ../timing.json from the real voice clips; everything on screen is keyed
// to line ids through the helpers below, never to hard-coded seconds or frames.
//
//   f('p3')            frame the voice starts line p3 (L.p3.voiceAt)
//   f('p3', 0.4)       0.4 s after that
//   fSaid('p3')        frame the voice finishes p3 (voiceAt + voiceDur); a question's think pause starts here
//   fPhrase('p4', 'seven hundred')   frame the voice reaches that phrase (estimated from its character position)
//   fStart / fEnd      the line's whole slot (lead + voice + pad + think)
//   chapterStart(n) / chapterEnd(n)  frames of chapter n
import RAW from '../timing.json';

export type TLine = {
  id: string; chapter: number; scene: string; start: number; voiceAt: number; voiceDur: number;
  think: number; end: number; dur: number; cap: string; say: string;
};
export type TChapter = {n: number; name: string; start: number; end: number};
export type TScene = {id: string; chapter: number; start: number; end: number; lines: string[]};
export type Timing = {
  hash: string; total: number; fps: number; width: number; height: number; title: string;
  chapters: TChapter[]; scenes: TScene[]; lines: TLine[];
};

export const TIMING = RAW as unknown as Timing;
export const FPS: number = TIMING.fps || 30;
export const WIDTH: number = TIMING.width || 1920;
export const HEIGHT: number = TIMING.height || 1080;
// The render gate allows +/- 1 s; rounding keeps us within one frame of the voice timing.
export const TOTAL_FRAMES = Math.max(1, Math.round(TIMING.total * FPS));

export const L: Record<string, TLine> = Object.fromEntries(TIMING.lines.map((l) => [l.id, l]));

const line = (id: string): TLine => {
  const l = L[id];
  if (!l) throw new Error(`timing: unknown line id "${id}". Ids in timing.json: ${TIMING.lines.map((x) => x.id).join(', ')}`);
  return l;
};

export const toF = (seconds: number) => Math.round(seconds * FPS);
/** seconds -> frames, for durations ("sec(0.4)") */
export const sec = (seconds: number) => Math.round(seconds * FPS);

/** frame at which the voice starts line `id`, plus `off` seconds */
export const f = (id: string, off = 0) => toF(line(id).voiceAt + off);
/** frame at which the voice finishes line `id` (the think pause, if any, starts here) */
export const fSaid = (id: string, off = 0) => toF(line(id).voiceAt + line(id).voiceDur + off);
/** first frame of the line's slot (before the lead-in silence) */
export const fStart = (id: string, off = 0) => toF(line(id).start + off);
/** last frame of the line's slot (after pad and think) */
export const fEnd = (id: string, off = 0) => toF(line(id).end + off);
/** think pause: [start, end] frames */
export const fThink = (id: string): [number, number] => [fSaid(id), toF(line(id).voiceAt + line(id).voiceDur + line(id).think)];
/** frame where the voice reaches `phrase` inside `say` (estimated by character position; within a few hundred ms) */
export const fPhrase = (id: string, phrase: string, off = 0) => {
  const l = line(id);
  const i = l.say.toLowerCase().indexOf(phrase.toLowerCase());
  if (i < 0) throw new Error(`timing: phrase "${phrase}" not in say of ${id}: "${l.say}"`);
  return toF(l.voiceAt + (l.voiceDur * i) / Math.max(1, l.say.length) + off);
};

export const chapter = (n: number) => {
  const c = TIMING.chapters.find((x) => x.n === n);
  if (!c) throw new Error(`timing: no chapter ${n}`);
  return c;
};
export const chapterStart = (n: number) => toF(chapter(n).start);
export const chapterEnd = (n: number) => toF(chapter(n).end);

/** the line whose slot contains frame `fr` (null in the gaps between chapters) */
export const lineAt = (fr: number): TLine | null => {
  const t = fr / FPS;
  for (const l of TIMING.lines) if (t >= l.start && t < l.end) return l;
  return null;
};
/** the chapter whose span contains frame `fr` (the previous one during a gap) */
export const chapterAt = (fr: number): TChapter => {
  const t = fr / FPS;
  let c = TIMING.chapters[0];
  for (const x of TIMING.chapters) if (t >= x.start - 0.0001) c = x;
  return c;
};
