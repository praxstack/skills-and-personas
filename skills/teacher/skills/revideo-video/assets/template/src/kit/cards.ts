// Chapter cards (full-frame orange wipe: "02 · Brute force"), the HUD (film tag, chapter pill, progress)
// and the lower third. Chapter cards and the HUD run by themselves from the timing (stage.run()).
import {Img, Node, Rect, Txt} from '@revideo/2d';
import {
  all, delay, easeInCubic, easeInOutCubic, easeOutBack, easeOutCubic, ThreadGenerator, waitFor,
} from '@revideo/core';
import {C, F, H, lineOf, onOf, S, W, wipeOf} from './theme';
import {at, CARD, CHAPTERS, clock, onFrame, TOTAL, WIPE} from './time';
import {kinetic, label, measure} from './text';
import type {Stage} from './stage';
import {halftoneTex} from './textures';

const pad2 = (n: number) => String(n).padStart(2, '0');
const parts = () => CHAPTERS.filter(c => c.n > 0).length;

// ---------------------------------------------------------------- HUD
export class Hud {
  readonly root = new Node({opacity: 0});
  readonly kicker: Txt;
  readonly title: Txt;
  readonly pillNum: Txt;
  readonly pillName: Txt;
  readonly pill: Rect;
  readonly segs: Rect[] = [];
  readonly progress: Rect;
  constructor(parent: Node, o: {kicker: string; title: string}) {
    parent.add(this.root);
    const y = -H / 2 + 104;
    this.kicker = label(o.kicker, {x: -W / 2 + 96, y, fill: C.ink, weight: 700, anchor: 'left'});
    // the title starts after the kicker: its measured width plus label()'s 2 px letter spacing per glyph
    const kw = o.kicker ? measure(o.kicker, S.tiny, F.mono, 700) + o.kicker.length * 2 + 28 : 0;
    this.title = label(o.title.toUpperCase(), {x: -W / 2 + 96 + kw, y, anchor: 'left'});
    this.root.add(this.kicker);
    this.root.add(this.title);
    // chapter pill, right aligned
    this.pill = new Rect({layout: true, x: W / 2 - 96, y, offset: [1, 0], gap: 14, alignItems: 'center'});
    const num = new Rect({fill: C.acc, radius: 6, padding: [4, 10]});
    this.pillNum = new Txt({text: '00', fontFamily: F.mono, fontWeight: 800, fontSize: S.tiny, fill: onOf(C.acc), letterSpacing: 1});
    num.add(this.pillNum);
    this.pillName = new Txt({text: '', fontFamily: F.mono, fontWeight: 600, fontSize: S.tiny, fill: C.ink, letterSpacing: 2});
    this.pill.add(num);
    this.pill.add(this.pillName);
    this.root.add(this.pill);
    const n = parts();
    for (let i = 0; i < n; i++) {
      const s = new Rect({x: W / 2 - 96 - (n - 1 - i) * 46 - 18, y: y + 34, width: 36, height: 4, radius: 2, fill: C.dim});
      this.root.add(s);
      this.segs.push(s);
    }
    this.progress = new Rect({x: -W / 2, y: H / 2 - 2, width: 0, height: 4, fill: lineOf(C.acc), offset: [-1, 0], opacity: 0.85});
    parent.add(this.progress);
    onFrame(() => this.progress.width(W * Math.min(1, clock() / TOTAL)));
  }
  setChapter(n: number) {
    const c = CHAPTERS.find(x => x.n === n);
    if (!c) return;
    this.pillNum.text(pad2(n));
    this.pillName.text(c.name.toUpperCase());
    this.segs.forEach((s, i) => s.fill(i < n - 1 ? C.ink : i === n - 1 ? lineOf(C.acc) : C.dim));
  }
  *track(): ThreadGenerator {
    for (const c of CHAPTERS) {
      if (c.n === 0) continue;
      const t = CARD[c.n];
      yield* at(t.coveredAt);
      this.setChapter(c.n);
      if (this.root.opacity() < 0.5) {
        yield* at(t.clearAt - 0.1);
        yield* this.root.opacity(1, 0.5);
      } else {
        yield* at(t.clearAt - 0.1);
        yield* this.pill.scale(1.08, 0.15, easeOutCubic).to(1, 0.25);
      }
    }
  }
}

// ---------------------------------------------------------------- chapter cards
/** One chapter card: an angled orange panel (a theme: the chapter's key light) with halftone dots sweeps across, holds, sweeps off. */
export function* chapterCard(st: Stage, n: number, name: string): ThreadGenerator {
  const t = CARD[n];
  yield* at(t.inAt);
  const box = new Node({x: -W * 1.35});
  st.cards.add(box);
  const wp = wipeOf(n);
  const back = new Rect({width: W * 1.3, height: H * 1.3, fill: wp.back, skew: [-12, 0], x: 120});
  const panel = new Rect({width: W * 1.3, height: H * 1.3, fill: wp.fill, skew: [-12, 0], clip: true});
  panel.add(new Img({src: halftoneTex(), width: 1200 * 1.6, height: 700 * 1.6, x: 260, y: 140, opacity: 0.9}));
  box.add(back);
  box.add(panel);
  const content = new Node({x: 0});
  box.add(content);
  const num = new Txt({text: pad2(n), fontFamily: F.display, fontWeight: 800, fontSize: 300, fill: wp.ink, y: -110, x: -40});
  const kick = label(`PART ${n} OF ${parts()}`, {y: 66, fill: wp.ink, size: 30, weight: 800});
  const ttl = kinetic(name, {size: S.h1, fill: wp.ink, y: 168, shadow: false});
  content.add(num);
  content.add(kick);
  content.add(ttl.root);
  num.opacity(0);
  num.scale(0.8);
  kick.opacity(0);
  yield* all(
    box.x(0, WIPE, easeInOutCubic),
    delay(WIPE * 0.55, all(num.opacity(1, 0.3), num.scale(1, 0.55, easeOutBack))),
    delay(WIPE * 0.75, all(ttl.in(0.55, 0.07), kick.opacity(1, 0.3))),
  );
  yield* at(t.outAt);
  yield* all(
    box.x(W * 1.4, WIPE, easeInOutCubic),
    content.x(-200, WIPE, easeInCubic),
  );
  box.remove();
}

export function* chapterCards(st: Stage): ThreadGenerator {
  for (const c of CHAPTERS) {
    if (c.n === 0 || !CARD[c.n]) continue;
    yield* chapterCard(st, c.n, c.name);
  }
}

// ---------------------------------------------------------------- lower third
/**
 * Lower third in the style of the reference film's "7:00 AM  RISE AND SHINE": a coloured block with a short
 * tag and a title, sliding in from the left above the caption band. Add it to `st.lower` (above the caption
 * scrim): in st.fg the scrim darkens it, and the orange block measured 3.7:1 instead of 6:1.
 *   const lt = lowerThird('EX 1', 'k = 1  ·  src 0 → dst 3'); st.lower.add(lt.root); yield* lt.in(); ... yield* lt.out();
 */
export function lowerThird(tag: string, title: string, o: {x?: number; y?: number; color?: string} = {}) {
  const root = new Rect({layout: true, x: o.x ?? -W / 2 + 96, y: o.y ?? H / 2 - 236, offset: [-1, 0], gap: 0,
    alignItems: 'center', clip: true, radius: 8});
  const block = new Rect({fill: o.color ?? C.acc, padding: [10, 16]});
  block.add(new Txt({text: tag, fontFamily: F.mono, fontWeight: 800, fontSize: S.small, fill: onOf(o.color ?? C.acc), letterSpacing: 1}));
  const body = new Rect({fill: C.strip, padding: [10, 18], stroke: C.line, lineWidth: 1});
  body.add(new Txt({text: title, fontFamily: F.mono, fontWeight: 600, fontSize: S.small, fill: C.ink, letterSpacing: 1}));
  root.add(block);
  root.add(body);
  root.opacity(0);
  return {
    root,
    *in(): ThreadGenerator {
      root.x(root.x() - 40);
      yield* all(root.opacity(1, 0.35), root.x(root.x() + 40, 0.5, easeOutCubic));
    },
    *out(): ThreadGenerator {
      yield* root.opacity(0, 0.25);
    },
  };
}

// ---------------------------------------------------------------- title card
/**
 * Title card for the intro: a big masked headline, a subtitle line and a mono kicker.
 *   const tc = titleCard('Cheapest\nflights.', 'within *k* stops.', 'LEETCODE 787 · GRAPHS · MEDIUM');
 *   st.fg.add(tc.root); yield* tc.in(); ... yield* tc.out();
 */
export function titleCard(headline: string, sub: string, kicker: string, o: {y?: number} = {}) {
  const root = new Node({y: o.y ?? -40});
  const h = kinetic(headline, {size: S.hero, lead: S.hero * 1.0, y: -70});
  const lines = headline.split('\n').length;
  const s = kinetic(sub, {size: 64, fill: C.muted, y: -70 + (lines * S.hero) / 2 + 70});
  const k = label(kicker, {y: -70 + (lines * S.hero) / 2 + 160, size: S.tiny});
  const bar = new Rect({width: 0, height: 6, fill: lineOf(C.acc), y: -70 - (lines * S.hero) / 2 - 40, radius: 3});
  k.opacity(0);
  root.add(bar);
  root.add(h.root);
  root.add(s.root);
  root.add(k);
  return {
    root, headline: h, sub: s, kicker: k,
    *in(): ThreadGenerator {
      yield* all(bar.width(160, 0.6, easeOutCubic), h.in(0.75, 0.1), delay(0.35, s.in(0.6, 0.06)), delay(0.7, k.opacity(1, 0.4)));
    },
    *out(): ThreadGenerator {
      yield* all(h.out(), s.out(), k.opacity(0, 0.25), bar.width(0, 0.3));
    },
  };
}

export {waitFor};
