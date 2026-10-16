// Film chrome, driven entirely by timing.ts: captions, chapter cards, the chapter lower-third, the progress bar.
// A new film gets all of it for free:
//
//   const chrome = new Chrome(w, {show: 'LEETCODE 787 · CHEAPEST FLIGHTS WITHIN K STOPS'});
//   yield chrome.run();     // background thread: captions follow the voice, a card opens every chapter
//
// Captions show each line's `cap` from its slot start to its end, in the bottom 180 px band, wrapped to two
// lines, ending 96 px above the bottom edge. The chapter tag and the show title sit on FRAME.headerY, their
// text 96 px below the top edge. Chapter cards play in the silence between two chapters (the last word of one,
// voice.py's chapter_gap and chapter_lead, the first word of the next), are gone CARD_LEAD s before the new
// chapter's first word, and collapse into the "01 · THE PROBLEM" tag at the top left. The subject fades back in
// as the band leaves; start a chapter's first panel at `cardOut(n)` (half way through the band's exit) or at
// its first line, never under the card.
import {Gradient, Line, Node, Rect, Txt} from '@motion-canvas/2d';
import {all, chain, delay, easeInCubic, easeInOutCubic, easeOutCubic, easeOutExpo, linear, waitFor, type ThreadGenerator} from '@motion-canvas/core';
import {C, F, FRAME, LIGHT, S, THEME, alpha, glow, inkOf, rgba, shade} from './theme';
import {CHAPTERS, LINES, TOTAL, waitUntilTime} from './clock';
import type {World} from './world';

export interface ChromeOptions {
  /** small caps text at the top right, e.g. 'LEETCODE 787 · CHEAPEST FLIGHTS' */
  show?: string;
  /** chapters that get a full chapter card (default: every chapter except 0) */
  cardFor?: (n: number) => boolean;
  /** label shown in the tag for chapter n (default: '01 · THE PROBLEM' from meta.chapters) */
  label?: (n: number, name: string) => string;
  captions?: boolean;
}

const two = (n: number) => String(n).padStart(2, '0');
const CARD_IN_HOLD = 0.88; // the card wipes in (0.38 s) and holds until this many seconds after it starts
const CARD_OUT = 0.34;
// the card moves in this long after the previous chapter's last word: its cleanup (0.25 s) is finished by then
const CLEAR = 0.3;
// the band has gone this long before the chapter's first word; the subject (0.3 s fade) is back before it
const CARD_LEAD = 0.4;
const chapterStart = (n: number) => CHAPTERS.find(c => c.n === n)?.start ?? 0;

/**
 * When chapter n's card plays: inside the silence between the previous chapter's last word and this chapter's
 * first word. It moves in at t0 (CLEAR s after the last word at the earliest: the old chapter has cleared by
 * then), is half way through its exit at `out` and has gone at `clear`, CARD_LEAD s before the first word.
 * A short silence shortens the hold.
 */
export function cardWindow(n: number) {
  const first = LINES.find(l => l.chapter === n);
  const before = LINES.filter(l => l.chapter < n);
  const prev = before[before.length - 1];
  const voiceIn = first ? first.voiceAt : chapterStart(n);
  const voiceOut = prev ? prev.voiceAt + prev.voiceDur : 0;
  const end = voiceIn - CARD_LEAD;
  const t0 = Math.max(voiceOut + CLEAR, end - (CARD_IN_HOLD + CARD_OUT));
  const hold = Math.max(0.3, end - CARD_OUT - t0);
  // out: half way through the band's exit (0.17 s before it has gone): the subject starts to fade back in here
  return {t0, hold, out: t0 + hold + CARD_OUT / 2, clear: t0 + hold + CARD_OUT, voiceOut};
}
/** Half way through chapter n's card exit: the subject fades back in from here; bring the chapter's first panel in here. */
export const cardOut = (n: number) => cardWindow(n).out;

export class Chrome {
  public readonly captionTxt: Txt;
  public readonly captionBand: Rect;
  private readonly tag: Txt;
  private readonly tagNum: Txt;
  private readonly tagGroup: Node;
  private readonly progress: Line;
  private readonly card: Node;
  private readonly cardNum: Txt;
  private readonly cardTitle: Txt;
  private readonly cardBand: Rect;
  private readonly cardStripes: Rect[];
  private readonly o: ChromeOptions;

  public constructor(private readonly w: World, o: ChromeOptions = {}) {
    this.o = o;
    const layer = w.chrome;
    const W = FRAME.w;
    const H = FRAME.h;
    // caption band: a soft dark gradient so the text reads over anything
    this.captionBand = new Rect({
      position: [0, H / 2 - FRAME.captionBand / 2],
      width: W,
      height: FRAME.captionBand,
      fill: new Gradient({
        from: [0, -FRAME.captionBand / 2],
        to: [0, FRAME.captionBand / 2],
        stops: [
          {offset: 0, color: rgba(C.shade, 0)},
          {offset: 0.35, color: rgba(C.shade, 0.78)},
          {offset: 1, color: rgba(C.shade, 0.92)},
        ],
      }),
    });
    // bottom-anchored: one or two lines, the last one ends 96 px above the bottom edge (the safe area)
    this.captionTxt = new Txt({
      y: FRAME.captionBottom,
      offset: [0, 1],
      width: 1640,
      textWrap: true,
      textAlign: 'center',
      fontFamily: F.body,
      fontWeight: 500,
      fontSize: 40,
      lineHeight: 52,
      fill: C.ink,
      text: '',
      opacity: 0,
    });
    layer.add(this.captionBand);
    layer.add(this.captionTxt);

    // progress bar along the top edge
    layer.add(new Rect({position: [0, -H / 2 + 3], width: W, height: 6, fill: alpha(C.ink, 0.06)}));
    this.progress = new Line({
      points: [
        [-W / 2, -H / 2 + 3],
        [W / 2, -H / 2 + 3],
      ],
      stroke: C.accent,
      lineWidth: 6,
      end: () => w.time() / TOTAL,
      shadowColor: glow(C.accent),
      shadowBlur: 10,
    });
    layer.add(this.progress);
    for (const c of CHAPTERS.slice(1)) {
      layer.add(new Rect({position: [-W / 2 + (W * c.start) / TOTAL, -H / 2 + 3], width: 3, height: 6, fill: C.bg}));
    }

    // chapter tag (lower third, top left)
    this.tagNum = new Txt({text: '', fontFamily: F.comic, fontSize: 42, fill: inkOf(C.accent), letterSpacing: 1, offset: [-1, 0]});
    this.tag = new Txt({text: '', x: 70, fontFamily: F.body, fontWeight: 700, fontSize: 30, letterSpacing: 4, fill: C.ink, offset: [-1, 0]});
    this.tagGroup = new Node({position: [-W / 2 + FRAME.safe, FRAME.headerY], opacity: 0, children: [
      new Rect({x: 55, width: 3, height: 38, fill: alpha(C.ink, 0.3)}),
      this.tagNum,
      this.tag,
    ]});
    layer.add(this.tagGroup);
    if (o.show) {
      layer.add(new Txt({position: [W / 2 - FRAME.safe, FRAME.headerY], offset: [1, 0], text: o.show, fontFamily: F.body, fontWeight: 600, fontSize: S.small, letterSpacing: 3, fill: C.muted}));
    }

    // chapter card: a band that wipes across the middle
    this.cardBand = new Rect({
      width: W + 200,
      height: 270,
      fill: new Gradient({
        from: [-W / 2, 0],
        to: [W / 2, 0],
        stops: [
          // original: deep burnt orange (not the bright accent): white title text reads at 5.9:1 or more across
          // the band. A theme: the band is a panel (panel2 to panel) with the title in `text`.
          {offset: 0, color: C.cardA}, // opaque: nothing behind the band shows through
          {offset: 0.55, color: C.cardB},
          {offset: 1, color: C.cardC},
        ],
      }),
      shadowColor: shade(0.6),
      shadowBlur: 60,
      shadowOffset: [0, 20],
      rotation: -2.5,
    });
    this.cardNum = new Txt({x: -560, y: 6, text: '01', fontFamily: F.comic, fontSize: 210, fill: C.cardInk, letterSpacing: 2, shadowColor: shade(0.45), shadowOffset: [5, 5]});
    this.cardTitle = new Txt({x: -400, y: 4, offset: [-1, 0], text: '', fontFamily: F.display, fontWeight: 800, fontSize: 92, letterSpacing: -1, fill: C.cardInk});
    // a theme's band carries the chapter's key light (themes.md `lights`) as two edge stripes and the numeral
    this.cardStripes = THEME
      ? [-1, 1].map(sd => new Rect({y: sd * (135 - 7), width: W + 200, height: 14, fill: C.accent}))
      : [];
    this.cardBand.add(this.cardStripes);
    this.card = new Node({x: -W - 200, rotation: 0, children: [this.cardBand, new Node({rotation: -2.5, children: [this.cardNum, this.cardTitle]})]});
    layer.add(this.card);
  }

  private label(n: number, name: string) {
    return this.o.label ? this.o.label(n, name) : name.toUpperCase();
  }

  private *captions(): ThreadGenerator {
    for (const l of LINES) {
      yield* waitUntilTime(l.start, `caption ${l.id}`);
      const len = l.cap.length;
      const size = len > 160 ? 38 : 40; // quality bar: captions 38-44 px, two lines at most
      if (this.captionTxt.opacity() < 0.5) {
        this.captionTxt.text(l.cap);
        this.captionTxt.fontSize(size);
        this.captionTxt.lineHeight(size * 1.3);
        yield* this.captionTxt.opacity(1, 0.25);
      } else {
        yield* this.captionTxt.opacity(0, 0.12);
        this.captionTxt.text(l.cap);
        this.captionTxt.fontSize(size);
        this.captionTxt.lineHeight(size * 1.3);
        yield* this.captionTxt.opacity(1, 0.18);
      }
    }
    yield* waitUntilTime(TOTAL - 0.7);
    yield* this.captionTxt.opacity(0, 0.5);
  }

  private *chapterCards(): ThreadGenerator {
    for (const c of CHAPTERS) {
      const wantCard = this.o.cardFor ? this.o.cardFor(c.n) : c.n > 0;
      if (!wantCard) {
        yield* waitUntilTime(Math.max(0, c.start - 0.2), `chapter ${c.n} card`);
        this.tagNum.text(two(c.n));
        this.tag.text(this.label(c.n, c.name));
        yield* all(this.tagGroup.opacity(c.n === 0 ? 0 : 1, 0.3));
        continue;
      }
      const win = cardWindow(c.n);
      // the previous chapter's subject (the world layer) fades out after its last word, so none of it is left
      // under the band when the band moves in at win.t0 (= last word + CLEAR)
      yield* waitUntilTime(win.voiceOut, `chapter ${c.n} clear`);
      yield this.w.world.opacity(0, 0.25);
      yield* waitUntilTime(win.t0, `chapter ${c.n} card`);
      this.cardNum.text(two(c.n));
      this.cardTitle.text(this.label(c.n, c.name));
      if (THEME) {
        const key = THEME.lights[c.n % THEME.lights.length] ?? C.accent;
        this.cardStripes.forEach(r => r.fill(key));
        this.cardNum.fill(inkOf(key));
      }
      this.card.x(-FRAME.w - 200);
      // in fast, hold, out the other side
      this.cardTitle.x(-300);
      this.cardNum.x(-520);
      // in fast, drift while holding (the title moves a little faster than the band: depth), out the other side
      yield* all(
        this.card.x(0, 0.38, easeOutExpo),
        this.cardTitle.x(-420, 1.25, easeOutCubic),
        this.cardNum.x(-560, 1.25, easeOutCubic),
        this.tagGroup.opacity(0, 0.2),
        // the subject comes back as the band leaves, so it is on screen when the chapter's voice starts
        chain(waitFor(win.hold), all(this.card.x(FRAME.w + 200, CARD_OUT, easeInCubic), delay(CARD_OUT / 2, this.w.world.opacity(1, 0.3)), delay(0.12, this.tagGroup.opacity(1, 0.3)))),
        delay(Math.min(0.6, win.hold * 0.7), (function* (self: Chrome) {
          self.tagNum.text(two(c.n));
          self.tag.text(self.label(c.n, c.name));
        })(this)),
      );
    }
  }

  /** Background thread for captions and chapters: `yield chrome.run();` */
  public run(): ThreadGenerator {
    const self = this;
    return (function* () {
      yield* all(self.o.captions === false ? waitFor(0) : self.captions(), self.chapterCards());
    })();
  }
}

void easeInOutCubic;
void LIGHT;
void linear;
