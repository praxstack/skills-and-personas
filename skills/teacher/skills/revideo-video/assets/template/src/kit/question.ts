// Question card with a countdown ring for the think pause. The subject stays visible below it.
//
//   const q = new QuestionCard({n: 1, text: 'What is simpler to count than stops?'});
//   st.fg.add(q.root);
//   yield* q.in();
//   yield* q.think('q1');                 // waits for the voice to end, counts down the pause, resolves on time
// or the steps one by one:
//   yield* at(voiceEnd('q1')); yield* q.countdown(L.q1.think - 0.1); yield* q.resolve();
import {Circle, Line, Node, Rect, Txt} from '@revideo/2d';
import {all, delay, easeInCubic, easeOutCubic, ThreadGenerator, tween} from '@revideo/core';
import {C, drop, F, glow, inkOf, lineOf, S} from './theme';
import {at, L, voiceEnd} from './time';

export class QuestionCard {
  readonly root: Node;
  /** The card body (a layout row: accent bar, kicker + question, a slot for the ring). */
  readonly panel: Rect;
  readonly kicker: Txt;
  readonly text: Txt;
  readonly track: Circle;
  readonly arc: Circle;
  readonly digit: Txt;
  readonly check: Line;
  private y0: number;

  constructor(o: {n: number | string; text: string; x?: number; y?: number; width?: number; kicker?: string}) {
    const width = o.width ?? 1380;
    this.y0 = o.y ?? -250;
    this.root = new Node({x: o.x ?? 0, y: this.y0, opacity: 0});
    this.panel = new Rect({
      layout: true, direction: 'row', alignItems: 'center', gap: 36, padding: [30, 40, 30, 0],
      width, radius: 24, fill: C.card, stroke: C.line, lineWidth: 2,
      shadowColor: drop(0.6), shadowBlur: 50, shadowOffset: [0, 20],
    });
    const bar = new Rect({width: 10, height: 150, fill: lineOf(C.acc), radius: [0, 6, 6, 0], shrink: 0});
    const col = new Rect({layout: true, direction: 'column', gap: 10, grow: 1});
    this.kicker = new Txt({text: o.kicker ?? `QUESTION ${o.n}`, fontFamily: F.mono, fontWeight: 800, fontSize: S.tiny, fill: inkOf(C.acc), letterSpacing: 3});
    this.text = new Txt({text: o.text, fontFamily: F.display, fontWeight: 700, fontSize: S.h3, lineHeight: S.h3 * 1.18, fill: C.ink,
      textWrap: true, width: width - 280});
    col.add(this.kicker);
    col.add(this.text);
    // The ring is NOT inside the layout (layout would squash the circles); a fixed slot keeps its place.
    const slot = new Rect({width: 150, height: 150, shrink: 0});
    this.panel.add(bar);
    this.panel.add(col);
    this.panel.add(slot);
    this.root.add(this.panel);
    const ring = new Node({x: width / 2 - 40 - 75});
    this.track = new Circle({size: 128, stroke: C.dim, lineWidth: 10});
    this.arc = new Circle({size: 128, stroke: lineOf(C.sky), lineWidth: 10, lineCap: 'round', startAngle: -90, endAngle: 270,
      shadowColor: glow(C.sky), shadowBlur: 16, opacity: 0});
    this.digit = new Txt({text: '', fontFamily: F.mono, fontWeight: 800, fontSize: 54, fill: C.ink, letterSpacing: 0.01});
    this.check = new Line({points: [[-26, 2], [-8, 22], [28, -20]], stroke: lineOf(C.mint), lineWidth: 10, lineCap: 'round', lineJoin: 'round',
      end: 0, opacity: 0}); // a zero-length round-capped line still draws a dot: keep it hidden until resolve()
    ring.add(this.track);
    ring.add(this.arc);
    ring.add(this.digit);
    ring.add(this.check);
    this.root.add(ring);
  }

  *in(d = 0.5): ThreadGenerator {
    this.root.y(this.y0 - 40);
    yield* all(this.root.opacity(1, d * 0.6), this.root.y(this.y0, d, easeOutCubic));
  }
  *out(d = 0.3): ThreadGenerator {
    yield* all(this.root.opacity(0, d, easeInCubic), this.root.y(this.y0 - 30, d, easeInCubic));
  }
  /** The ring empties over `seconds` while the digits count down. */
  *countdown(seconds: number): ThreadGenerator {
    this.arc.opacity(1);
    this.arc.endAngle(270);
    let last = -1;
    yield* tween(seconds, t => {
      this.arc.endAngle(270 - 360 * t);
      const left = Math.max(1, Math.ceil(seconds * (1 - t) - 1e-6));
      if (left !== last) {
        last = left;
        this.digit.text(String(left));
      }
    });
    this.arc.endAngle(-90);
    this.digit.text('');
  }
  /** The whole think pause of line `id`: wait for its voice to end, count down, resolve as the pause ends. */
  *think(id: string): ThreadGenerator {
    yield* at(voiceEnd(id), `${id}:think`);
    yield* this.countdown(Math.max(0.5, L[id].think - 0.1));
    yield* this.resolve(); // 0.45 s: lands as the next line starts
  }
  /** Ring fills mint with a check mark (the answer is coming). */
  *resolve(): ThreadGenerator {
    this.arc.stroke(lineOf(C.mint)).shadowColor(glow(C.mint));
    this.check.opacity(1);
    yield* all(this.arc.endAngle(270, 0.4, easeOutCubic), delay(0.15, this.check.end(1, 0.3, easeOutCubic)),
      this.panel.stroke(lineOf(C.mint), 0.3));
  }
}
