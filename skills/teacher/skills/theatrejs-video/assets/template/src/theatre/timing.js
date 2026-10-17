// timing.js: helpers that turn narration line ids into seconds. Every time in src/film/shots.js comes from here,
// so the picture follows the voice: re-voice, rebuild, and every keyframe moves with its line.
//
//   T.at('p3')          the moment the voice starts line p3
//   T.at('p3', 0.5)     halfway through the spoken words of p3
//   T.after('p3', 0.2)  0.2 s after the voice of p3 finishes (think pauses start here)
//   T.start('p3') / T.end('p3')   the line's whole slot (lead, voice, pad, think)
//   T.word('p4', 'seven hundred')  when that phrase is spoken (estimated from its position in `say`)
//   T.think('q1')       { t, dur }: the silent pause after a question
//   T.chapter(2)        { n, name, start, end }
export function timeline(TIMING) {
  const byId = new Map(TIMING.lines.map((l) => [l.id, l]));
  const line = (id) => {
    const l = byId.get(id);
    if (!l) throw new Error(`shots: unknown line id "${id}". Lines in timing.js: ${[...byId.keys()].join(', ')}`);
    return l;
  };
  const T = {
    total: TIMING.total, fps: TIMING.fps || 30, title: TIMING.title || "", hash: TIMING.hash, lines: TIMING.lines, chapters: TIMING.chapters, scenes: TIMING.scenes,
    line, has: (id) => byId.has(id),
    at: (id, frac = 0) => line(id).voiceAt + frac * line(id).voiceDur,
    after: (id, sec = 0) => line(id).voiceAt + line(id).voiceDur + sec,
    start: (id, sec = 0) => line(id).start + sec,
    end: (id, sec = 0) => line(id).end + sec,
    dur: (id) => line(id).voiceDur,
    think: (id) => ({ t: line(id).voiceAt + line(id).voiceDur, dur: line(id).think || 0 }),
    word(id, phrase) {
      const l = line(id), say = l.say.toLowerCase(), i = say.indexOf(phrase.toLowerCase());
      if (i < 0) throw new Error(`shots: T.word: "${phrase}" is not in the say text of ${id}: "${l.say}"`);
      return l.voiceAt + l.voiceDur * (i / Math.max(1, say.length));
    },
    chapter(n) {
      const c = TIMING.chapters.find((x) => x.n === n);
      if (!c) throw new Error(`shots: no chapter ${n}`);
      return c;
    },
    scene(id) {
      const s = TIMING.scenes.find((x) => x.id === id);
      if (!s) throw new Error(`shots: no scene "${id}"`);
      return s;
    },
    /** the line on screen at time t (the last line that has started) */
    lineAt(t) {
      let cur = null;
      for (const l of TIMING.lines) { if (l.start <= t + 1e-6) cur = l; else break; }
      return cur;
    },
    chapterAt(t) {
      let cur = TIMING.chapters[0];
      for (const c of TIMING.chapters) if (c.start <= t + 1e-6) cur = c;
      return cur;
    },
  };
  return T;
}
